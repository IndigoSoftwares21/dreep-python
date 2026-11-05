"""Runs every repository rule and enforces the baseline ratchet.

    python scripts/verify_rules.py                  # check
    python scripts/verify_rules.py --summary        # counts only
    python scripts/verify_rules.py --rule=RULE-004  # one rule (baseline ignored)
    python scripts/verify_rules.py --strict         # warnings fail too
    python scripts/verify_rules.py --update-baseline

The baseline (``scripts/rules-baseline.json``) records, per rule, how many
errors and warnings are tolerated. A count above it fails; a count below it
fails too, asking you to lower the baseline -- debt only ever shrinks.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rules import load_rules
from rules.base import ERROR, WARN, ProjectRule, Violation, build_context, walk_python_files

BASELINE: Final = Path(__file__).resolve().parent / "rules-baseline.json"
RED, YELLOW, GREEN, RESET = "\033[31m", "\033[33m", "\033[32m", "\033[0m"
COLOR: Final = {ERROR: RED, WARN: YELLOW}
Counts = dict[str, dict[str, int]]


def run(rule_filter: str | None) -> tuple[list[Violation], int, list[str]]:
    rules = load_rules()
    if rule_filter:
        rules = [r for r in rules if r.id.upper() == rule_filter.upper()]
        if not rules:
            sys.exit(f"Unknown rule {rule_filter!r}.")
    files = [build_context(path) for path in walk_python_files()]
    violations = [v for file in files for rule in rules for v in rule.check(file)]
    violations += [v for rule in rules if isinstance(rule, ProjectRule) for v in rule.finish()]
    return violations, len(files), [r.id for r in rules]


def count(violations: list[Violation], rule_ids: list[str]) -> Counts:
    tally = Counter((v.rule_id, v.severity) for v in violations)
    return {
        rid: {"errors": tally[(rid, ERROR)], "warnings": tally[(rid, WARN)]} for rid in rule_ids
    }


def report(violations: list[Violation]) -> None:
    for v in sorted(violations, key=lambda v: (v.path, v.line, v.rule_id)):
        print(f"{COLOR[v.severity]}[{v.severity}]{RESET} {v.rule_id}: {v.path}:{v.line}")
        print(f"        Message:     {v.message}")
        print(f"        Remediation: {v.remediation}")
        if v.snippet:
            print(f"        Snippet:     {v.snippet}")


def compare(current: Counts, baseline: Counts) -> list[str]:
    """Every difference from the baseline -- regressions *and* stale headroom."""
    problems = []
    for rid, counts in current.items():
        recorded = baseline.get(rid, {"errors": 0, "warnings": 0})
        for kind in ("errors", "warnings"):
            if counts[kind] > recorded.get(kind, 0):
                problems.append(
                    f"{rid} {kind} {recorded.get(kind, 0)} -> {counts[kind]} (regression)"
                )
            elif counts[kind] < recorded.get(kind, 0):
                problems.append(
                    f"{rid} {kind} {recorded[kind]} -> {counts[kind]} (lower the baseline)"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify repository rules.")
    parser.add_argument("--strict", action="store_true", help="fail on any warning")
    parser.add_argument("--summary", action="store_true", help="print counts only")
    parser.add_argument("--rule", help="run a single rule, e.g. RULE-004")
    parser.add_argument("--update-baseline", action="store_true", help="record current counts")
    args = parser.parse_args()

    started = time.perf_counter()
    violations, file_count, rule_ids = run(args.rule)
    if not args.summary:
        report(violations)
    current = count(violations, rule_ids)
    for rid, c in current.items():
        status = (
            f"{RED}FAIL" if c["errors"] else f"{YELLOW}WARN" if c["warnings"] else f"{GREEN}PASS"
        )
        print(f"{rid} {status}{RESET}: {c['errors']} errors, {c['warnings']} warnings")
    print(f"{file_count} files, {len(violations)} violations, {time.perf_counter() - started:.2f}s")

    if args.update_baseline:
        BASELINE.write_text(json.dumps(current, indent=2) + "\n")
        print(f"Baseline written to {BASELINE.name}.")
        return 0
    problems = [] if args.rule else compare(current, _load_baseline())
    warnings = sum(c["warnings"] for c in current.values())
    for problem in problems:
        print(f"{RED}{problem}{RESET}")
    if problems or (args.strict and warnings):
        print(f"{RED}FAILED{RESET}")
        return 1
    print(f"{GREEN}PASSED{RESET}")
    return 0


def _load_baseline() -> Counts:
    try:
        data = json.loads(BASELINE.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    sys.exit(main())
