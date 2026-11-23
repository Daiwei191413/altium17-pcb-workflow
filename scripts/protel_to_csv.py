"""Normalize classic Protel text netlists exported from a schematic project."""
import argparse
import csv
import sys
from pathlib import Path


def parse(text):
    parts = set()
    nets = set()
    blocks = []
    opener = None
    lines = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if opener is None:
            if line not in ("[", "("):
                raise ValueError(f"line {number}: expected [ or (")
            opener = line
            lines = []
        elif line in ("[", "(", "]", ")"):
            if (opener, line) not in (("[", "]"), ("(", ")")) or not lines:
                raise ValueError(f"line {number}: malformed block")
            if opener == "[":
                ref = lines[0].upper()
                if ref in parts:
                    raise ValueError(f"duplicate component: {ref}")
                parts.add(ref)
            else:
                name = lines[0]
                if name in nets or len(lines) < 2:
                    raise ValueError(f"empty or repeated net: {name}")
                nets.add(name)
                blocks.append((name, lines[1:]))
            opener = None
        else:
            lines.append(line)
    if opener is not None or not blocks:
        raise ValueError("incomplete file or no net blocks")
    endpoints = {}
    for net, members in blocks:
        for member in members:
            candidates = []
            for index, char in enumerate(member):
                if char == "-":
                    ref = member[:index].upper()
                    pin = member[index + 1:]
                    if ref and pin and (ref in parts or (not parts and member.count("-") == 1)):
                        candidates.append((ref, pin))
            if len(candidates) != 1:
                raise ValueError(f"unknown or ambiguous endpoint: {member}")
            endpoint = candidates[0]
            if endpoint in endpoints:
                raise ValueError(f"duplicate endpoint: {member}")
            endpoints[endpoint] = net
    return [(ref, pin, net) for (ref, pin), net in sorted(endpoints.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--encoding", default="utf-8-sig")
    args = parser.parse_args()
    try:
        rows = parse(args.source.read_text(encoding=args.encoding))
        with args.output.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("refdes", "pin", "net"))
            writer.writerows(rows)
    except (OSError, ValueError, LookupError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"{len(rows)} endpoints")
    return 0


if __name__ == "__main__":
    sys.exit(main())
