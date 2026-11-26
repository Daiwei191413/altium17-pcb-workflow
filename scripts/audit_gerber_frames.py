"""Check straight-sided top silkscreen frames against actual Gerber artwork."""
import argparse
import csv
import math
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

try:
    from gerbonara import GerberFile
    from gerbonara.utils import MM
    from shapely import affinity
    from shapely.geometry import LineString, Point, Polygon, box
    from shapely.ops import polygonize, unary_union
except ImportError as error:
    if __name__ == "__main__":
        print(f"Audit dependencies unavailable: {error}", file=sys.stderr)
        sys.exit(2)
    raise


def read_pads(path, encoding):
    components = {}
    with path.open(encoding=encoding, newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["kind", "refdes", "pin", "x_adcoord", "y_adcoord"]:
            raise ValueError("Expected the ExportTopPadCenters CSV header")
        for row in reader:
            ref = row["refdes"]
            if not ref:
                raise ValueError("Empty component designator")
            if row["kind"] == "component" and ref not in components:
                components[ref] = []
            elif row["kind"] == "pad" and ref in components:
                coordinates = [int(row[key]) * 0.00000254 for key in ("x_adcoord", "y_adcoord")]
                components[ref].append(Point(*coordinates))
            else:
                raise ValueError(f"Invalid or duplicate inventory record on line {reader.line_num}")
    if not components:
        raise ValueError("Empty top component inventory")
    return components


def read_layer(archive, suffix, member):
    names = [name for name in archive.namelist()
             if (name == member if member else name.lower().endswith(suffix))]
    if len(names) != 1:
        raise ValueError(f"Expected exactly one {member or suffix} layer, found {names}")
    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)
        artwork = GerberFile.from_string(archive.read(names[0]).decode("utf-8-sig"), filename=names[0])
    for obj in artwork.objects:
        for primitive in obj.to_primitives(MM):
            if not primitive.polarity_dark:
                raise ValueError(f"{names[0]} contains clear polarity, review in CAM")
            yield primitive


def opening(p):
    if type(p).__name__ == "Circle":
        # Circumscribed polygon bounds the true circular opening conservatively.
        return Point(p.x, p.y).buffer(p.r / math.cos(math.pi / 256), quad_segs=64)
    if type(p).__name__ == "Rectangle":
        rect = box(p.x-p.w/2, p.y-p.h/2, p.x+p.w/2, p.y+p.h/2)
        return affinity.rotate(rect, -p.rotation, origin=(p.x, p.y), use_radians=True)
    raise ValueError(f"Unsupported mask opening {type(p).__name__}, review in CAM")


def inspect_frames(segments, widths, openings, pads, manual, clearance):
    unknown = set(manual) - set(pads)
    if unknown or not set(pads) - set(manual):
        raise ValueError(f"Check manual exceptions against the component inventory: {sorted(unknown)}")
    owners = defaultdict(set)
    assigned = {}
    for ref, centers in pads.items():
        indices = set()
        for point in centers:
            matches = [i for i, shape in enumerate(openings) if shape.covers(point)]
            if len(matches) != 1:
                raise ValueError(f"{ref}: expected one mask opening at {point.wkt}, found {len(matches)}")
            indices.update(matches)
        if not indices and ref not in manual:
            raise ValueError(f"{ref}: no mapped top opening")
        assigned[ref] = indices
        for i in indices:
            owners[i].add(ref)

    faces = list(polygonize(unary_union(segments)))
    mask = unary_union(openings)
    half_width = max(widths, default=0) / 2
    rows = []
    for ref, indices in assigned.items():
        if ref in manual:
            rows.append((ref, "manual", len(indices), ""))
            continue
        result, gap = "open_or_unverified", ""
        for face in faces:
            boundary = Polygon(face.exterior)
            if not all(boundary.covers(openings[i]) for i in indices):
                continue
            if any(other != ref for i, refs in owners.items()
                   if boundary.intersects(openings[i]) for other in refs):
                continue
            distance = boundary.exterior.distance(mask) - half_width
            result = "closed" if distance >= clearance else "clearance_failed"
            gap = f"{distance:.6f}"
            break
        rows.append((ref, result, len(indices), gap))
    return sorted(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("pads", type=Path)
    parser.add_argument("output", type=Path, help="New per-component CSV")
    parser.add_argument("--width-mm", type=float, required=True)
    parser.add_argument("--clearance-mm", type=float, required=True)
    parser.add_argument("--manual", nargs="*", default=[], metavar="REF")
    parser.add_argument("--silk-member", help="Exact ZIP member name, default unique .GTO")
    parser.add_argument("--mask-member", help="Exact ZIP member name, default unique .GTS")
    parser.add_argument("--encoding", default="utf-8-sig", help="AD inventory CSV encoding")
    args = parser.parse_args()
    if not (math.isfinite(args.width_mm) and args.width_mm > 0 and
            math.isfinite(args.clearance_mm) and args.clearance_mm >= 0):
        parser.error("Invalid line width or clearance")
    try:
        pads = read_pads(args.pads, args.encoding)
        segments, widths = [], []
        with ZipFile(args.archive) as archive:
            for p in read_layer(archive, ".gto", args.silk_member):
                if type(p).__name__ != "Line":
                    raise ValueError("Only straight-line positive silkscreen artwork is supported")
                if math.isclose(p.width, args.width_mm, abs_tol=0.0005):
                    segments.append(LineString([(p.x1, p.y1), (p.x2, p.y2)]))
                    widths.append(p.width)
            openings = [opening(p) for p in read_layer(archive, ".gts", args.mask_member)]
        rows = inspect_frames(segments, widths, openings, pads, args.manual, args.clearance_mm)
        with args.output.open("x", encoding="utf-8-sig", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(["refdes", "status", "mapped_openings", "min_gap_mm"])
            writer.writerows(rows)
        counts = Counter(row[1] for row in rows)
        print(f"{len(rows)} components: {dict(sorted(counts.items()))}")
        return int(any(status not in ("closed", "manual") for status in counts))
    except Exception as error:
        print(f"Audit incomplete: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
