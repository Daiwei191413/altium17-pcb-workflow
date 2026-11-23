"""Compare two endpoint-level CSV netlists exported from an engineering flow."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


REQUIRED_COLUMNS = {"refdes", "pin", "net"}


def load_connections(path: Path) -> dict[tuple[str, str], str]:
    connections: dict[tuple[str, str], str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"{path}: required columns are refdes,pin,net")
        for row_number, row in enumerate(reader, start=2):
            refdes = row["refdes"].strip().upper()
            pin = row["pin"].strip()
            net = row["net"].strip()
            if not refdes or not pin or not net:
                raise ValueError(f"{path}:{row_number}: blank endpoint field")
            endpoint = (refdes, pin)
            if endpoint in connections:
                raise ValueError(f"{path}:{row_number}: duplicate endpoint {refdes}.{pin}")
            connections[endpoint] = net
    if not connections:
        raise ValueError(f"{path}: no connection rows")
    return connections


def compare(before: dict[tuple[str, str], str], after: dict[tuple[str, str], str]) -> dict:
    before_keys = set(before)
    after_keys = set(after)
    added = [
        {"refdes": refdes, "pin": pin, "net": after[(refdes, pin)]}
        for refdes, pin in sorted(after_keys - before_keys)
    ]
    removed = [
        {"refdes": refdes, "pin": pin, "net": before[(refdes, pin)]}
        for refdes, pin in sorted(before_keys - after_keys)
    ]
    changed = [
        {
            "refdes": refdes,
            "pin": pin,
            "before_net": before[(refdes, pin)],
            "after_net": after[(refdes, pin)],
        }
        for refdes, pin in sorted(before_keys & after_keys)
        if before[(refdes, pin)] != after[(refdes, pin)]
    ]
    return {"added": added, "removed": removed, "changed": changed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON output; existing files are not overwritten")
    args = parser.parse_args(argv)
    try:
        delta = compare(load_connections(args.before), load_connections(args.after))
        body = json.dumps(delta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(body)
        else:
            print(body, end="")
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1 if any(delta.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())

