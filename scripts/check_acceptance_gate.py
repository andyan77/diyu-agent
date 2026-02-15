#!/usr/bin/env python3
"""Acceptance command hard gate -- CI-blocking validation.

Validates task card acceptance commands for:
  1. acceptance-not-executable: natural language without tags or backticks
  2. acceptance-empty: acceptance field present but empty
  3. manual-verify-no-alt: [MANUAL-VERIFY] without alternative (>= 5 chars)
  4. env-dep-no-mapping: [ENV-DEP] without a resolvable CI/staging job reference

Fail-closed: any parse error -> exit 2 (configuration error).

Usage:
    python scripts/check_acceptance_gate.py --json
    python scripts/check_acceptance_gate.py --json --filter-file docs/task-cards/01-Brain/brain.md

Exit codes:
    0: All acceptance commands valid
    1: Blocking violations found
    2: Configuration error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TASK_CARDS_DIR = Path("docs/task-cards")

TASK_HEADING_RE = re.compile(r"^###\s+(TASK-\S+)")
EXCEPTION_RE = re.compile(r">\s*EXCEPTION:\s*(EXC-\S+)\s*\|\s*Field:\s*(\S+)")

# Known CI job identifiers that [ENV-DEP] can map to
CI_JOB_PATTERNS = [
    r"docker",
    r"docker-compose",
    r"docker compose",
    r"gh\s",
    r"curl\s+.*localhost",
    r"make\s+deploy",
    r"make\s+test-isolation",
    r"k6\s",
    r"artillery\s",
    r"playwright",
    r"pytest\s+tests/isolation",
    r"alembic\s",
    r"redis-cli",
    r"psql\s",
    r"CI-job:",
    r"staging:",
    r"workflow:",
]
CI_JOB_RE = re.compile("|".join(CI_JOB_PATTERNS), re.IGNORECASE)


@dataclass
class Violation:
    card_id: str
    file: str
    line: int
    rule: str
    message: str


@dataclass
class CardAcceptance:
    task_id: str
    file: str
    line: int
    acceptance: str
    excepted_fields: set = field(default_factory=set)


def parse_cards(filepath: Path) -> list[CardAcceptance]:
    """Parse task cards from a single file, extracting acceptance fields."""
    cards: list[CardAcceptance] = []
    lines = filepath.read_text(encoding="utf-8").splitlines()

    i = 0
    while i < len(lines):
        match = TASK_HEADING_RE.match(lines[i])
        if not match:
            i += 1
            continue

        task_id = match.group(1).rstrip(":")
        heading_line = i + 1  # 1-indexed
        acceptance = ""
        excepted: set[str] = set()

        end_idx = min(i + 30, len(lines))
        for j in range(i + 1, end_idx):
            line = lines[j]
            # Stop at next task heading
            if j > i + 1 and TASK_HEADING_RE.match(line):
                break
            if line.startswith("## Phase") or line.startswith("## ---"):
                break

            # Exception for acceptance field
            exc_match = EXCEPTION_RE.search(line)
            if exc_match and exc_match.group(2) in ("验收命令", "acceptance"):
                excepted.add("验收命令")

            # Acceptance field detection
            if re.search(r"\*\*验收命令\*\*", line):
                value = line.split("|")[-2].strip() if "|" in line else ""
                acceptance = value

        cards.append(
            CardAcceptance(
                task_id=task_id,
                file=str(filepath),
                line=heading_line,
                acceptance=acceptance,
                excepted_fields=excepted,
            )
        )
        i += 1

    return cards


def validate_acceptance(card: CardAcceptance) -> list[Violation]:
    """Validate a single card's acceptance command. Fail-closed."""
    violations: list[Violation] = []
    acc = card.acceptance

    if "验收命令" in card.excepted_fields:
        return violations

    # Rule 1: acceptance-empty
    if not acc.strip():
        violations.append(
            Violation(
                card_id=card.task_id,
                file=card.file,
                line=card.line,
                rule="acceptance-empty",
                message="Acceptance command is empty",
            )
        )
        return violations  # No point checking further

    # Rule 2: acceptance-not-executable
    has_backtick = "`" in acc
    has_tag = any(tag in acc for tag in ["[ENV-DEP]", "[MANUAL-VERIFY]", "[E2E]"])
    if not has_backtick and not has_tag:
        violations.append(
            Violation(
                card_id=card.task_id,
                file=card.file,
                line=card.line,
                rule="acceptance-not-executable",
                message=f"Acceptance command is natural language without tags: {acc[:80]}",
            )
        )

    # Rule 3: manual-verify-no-alt
    if "[MANUAL-VERIFY]" in acc:
        mv_idx = acc.index("[MANUAL-VERIFY]") + len("[MANUAL-VERIFY]")
        alt_text = acc[mv_idx:].strip().strip("|").strip()
        alt_clean = alt_text.replace("`", "").strip()
        if len(alt_clean) < 5:
            violations.append(
                Violation(
                    card_id=card.task_id,
                    file=card.file,
                    line=card.line,
                    rule="manual-verify-no-alt",
                    message="[MANUAL-VERIFY] must include alternative verification (>= 5 chars)",
                )
            )

    # Rule 4: env-dep-no-mapping
    if "[ENV-DEP]" in acc:
        # Extract the command content after [ENV-DEP]
        ed_idx = acc.index("[ENV-DEP]") + len("[ENV-DEP]")
        cmd_text = acc[ed_idx:].strip()
        if not CI_JOB_RE.search(cmd_text) and "`" not in cmd_text:
            violations.append(
                Violation(
                    card_id=card.task_id,
                    file=card.file,
                    line=card.line,
                    rule="env-dep-no-mapping",
                    message=(
                        "[ENV-DEP] command has no resolvable CI/staging job reference: "
                        f"{cmd_text[:80]}"
                    ),
                )
            )

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="Acceptance command hard gate")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument(
        "--filter-file",
        type=Path,
        default=None,
        help="Validate only a specific file",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=TASK_CARDS_DIR,
        help="Base directory for task cards",
    )
    args = parser.parse_args()

    if not args.base_dir.exists():
        print(f"ERROR: {args.base_dir} does not exist", file=sys.stderr)
        sys.exit(2)

    if args.filter_file:
        if not args.filter_file.exists():
            print(f"ERROR: {args.filter_file} does not exist", file=sys.stderr)
            sys.exit(2)
        md_files = [args.filter_file]
    else:
        md_files = sorted(args.base_dir.rglob("*.md"))

    all_cards: list[CardAcceptance] = []
    all_violations: list[Violation] = []

    for md_file in md_files:
        try:
            cards = parse_cards(md_file)
        except Exception as e:
            print(f"ERROR: Failed to parse {md_file}: {e}", file=sys.stderr)
            sys.exit(2)  # fail-closed

        all_cards.extend(cards)
        for card in cards:
            all_violations.extend(validate_acceptance(card))

    # Group violations by rule
    by_rule: dict[str, int] = {}
    for v in all_violations:
        by_rule[v.rule] = by_rule.get(v.rule, 0) + 1

    report = {
        "total_cards": len(all_cards),
        "total_violations": len(all_violations),
        "violations_by_rule": by_rule,
        "violations": [
            {
                "card_id": v.card_id,
                "file": v.file,
                "line": v.line,
                "rule": v.rule,
                "message": v.message,
            }
            for v in all_violations
        ],
        "status": "FAIL" if all_violations else "PASS",
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Acceptance Gate: {report['status']}")
        print(f"  Cards: {len(all_cards)}, Violations: {len(all_violations)}")
        if by_rule:
            for rule, count in sorted(by_rule.items()):
                print(f"    {rule}: {count}")
        if all_violations:
            print()
            for v in all_violations[:20]:
                print(f"  [{v.rule}] {v.file}:{v.line} {v.card_id}")
                print(f"    {v.message}")
            if len(all_violations) > 20:
                print(f"  ... and {len(all_violations) - 20} more")

    sys.exit(1 if all_violations else 0)


if __name__ == "__main__":
    main()
