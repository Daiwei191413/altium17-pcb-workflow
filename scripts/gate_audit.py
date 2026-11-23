"""Audit a version-bound G0-G6 project state without judging PCB correctness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


GATE_IDS = [f"G{number}" for number in range(7)]
STATUSES = {"pending", "pass", "hold", "not_applicable"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _nonempty_strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def audit(document: object) -> list[str]:
    issues: list[str] = []
    if not isinstance(document, dict):
        return ["root must be a JSON object"]
    if document.get("schema") != 1:
        issues.append("schema must equal 1")
    if not isinstance(document.get("project_id"), str) or not document["project_id"].strip():
        issues.append("project_id must be a non-empty string")

    digest = document.get("input_digest")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        issues.append("input_digest must be a lowercase SHA-256 value")

    gates = document.get("gates")
    if not isinstance(gates, list):
        return issues + ["gates must be a list"]
    if len(gates) != len(GATE_IDS):
        issues.append("gates must contain exactly G0 through G6")

    by_id: dict[str, dict] = {}
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict):
            issues.append(f"gates[{index}] must be an object")
            continue
        gate_id = gate.get("id")
        if gate_id not in GATE_IDS:
            issues.append(f"gates[{index}].id is invalid")
            continue
        if gate_id in by_id:
            issues.append(f"duplicate gate: {gate_id}")
            continue
        by_id[gate_id] = gate

    for gate_id in GATE_IDS:
        gate = by_id.get(gate_id)
        if gate is None:
            issues.append(f"missing gate: {gate_id}")
            continue
        status = gate.get("status")
        if status not in STATUSES:
            issues.append(f"{gate_id}.status is invalid")
            continue
        if status == "pass":
            if not _nonempty_strings(gate.get("evidence")):
                issues.append(f"{gate_id} pass requires non-empty evidence")
            if gate.get("reviewed_input") != digest:
                issues.append(f"{gate_id} pass is stale or lacks reviewed_input")
            predecessors = GATE_IDS[: GATE_IDS.index(gate_id)]
            for predecessor in predecessors:
                prior = by_id.get(predecessor, {}).get("status")
                if prior not in {"pass", "not_applicable"}:
                    issues.append(f"{gate_id} cannot pass while {predecessor} is {prior or 'missing'}")
                    break
        elif status in {"hold", "not_applicable"} and not _nonempty_strings(gate.get("reasons")):
            issues.append(f"{gate_id} {status} requires non-empty reasons")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path, help="Path to project-state.json")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.state.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    issues = audit(document)
    if issues:
        for issue in issues:
            print(f"ISSUE: {issue}")
        return 1
    print("PASS: gate state is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

