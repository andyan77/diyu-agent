#!/usr/bin/env python3
"""Task Card Schema Validator - CI gate script.

Validates all task cards against task-card-schema-v1.0.md rules.
Supports three enforcement modes: warning, incremental, full.

Usage:
    python scripts/check_task_schema.py [--mode warning|incremental|full] [--json]
    python scripts/check_task_schema.py --filter-file docs/task-cards/01-Brain/brain.md
    python scripts/check_task_schema.py --mode full --verbose

Exit codes:
    0: All checks pass (or warning mode)
    1: BLOCK-level violations found (incremental/full mode)
    2: Configuration error
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

TASK_CARDS_DIR = Path("docs/task-cards")
MATRIX_FILES = [
    Path("docs/governance/milestone-matrix-backend.md"),
    Path("docs/governance/milestone-matrix-frontend.md"),
    Path("docs/governance/milestone-matrix-crosscutting.md"),
]

TASK_HEADING_RE = re.compile(r"^###\s+(TASK-\S+)")
MATRIX_REF_RE = re.compile(r">\s*矩阵条目:\s*(\S+)")
EXCEPTION_RE = re.compile(
    r">\s*EXCEPTION:\s*(EXC-\S+)\s*\|\s*Field:\s*(\S+)\s*\|\s*Owner:\s*(\S+)\s*\|\s*Deadline:\s*(.+?)\s*\|\s*Alt:\s*(.+)"
)

# Result-oriented keywords for WARNING-level check
RESULT_KEYWORDS = [
    "可用",
    "通过",
    "成功",
    "非空",
    "可回滚",
    "PASS",
    "pass",
    "启动",
    "可访问",
    "完成",
    "覆盖",
    "满足",
    "达到",
    "就绪",
    "健康",
    "正常",
    "生效",
    "可验证",
    "zero",
    "Zero",
    "0",
]

# Cross-layer prefixes for Tier determination
LAYER_PREFIXES = {"B", "MC", "K", "S", "T", "G", "I", "D", "OS", "FW", "FA", "MM"}


class Severity(Enum):
    BLOCK = "BLOCK"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Violation:
    card_id: str
    file: str
    line: int
    severity: Severity
    rule: str
    message: str


@dataclass
class CardInfo:
    task_id: str
    title: str
    file: str
    line: int
    tier: str
    phase: int
    fields: dict = field(default_factory=dict)
    matrix_refs: list = field(default_factory=list)
    exceptions: list = field(default_factory=list)
    raw_lines: list = field(default_factory=list)


def extract_phase(task_id: str) -> int:
    """Extract phase number from task ID."""
    match = re.search(r"TASK-\w+-?(\d+)-", task_id) or re.search(r"TASK-[A-Z]+-?(\d+)", task_id)
    if match:
        return int(match.group(1))
    if "DEPLOY-FE" in task_id:
        return 3
    return -1


def extract_layer_prefix(task_id: str) -> str:
    """Extract layer prefix from task ID."""
    rest = task_id.replace("TASK-", "")
    for prefix in sorted(LAYER_PREFIXES, key=len, reverse=True):
        if rest.startswith(prefix):
            return prefix
    return ""


def determine_tier(task_id: str, scope_text: str, dep_text: str) -> str:
    """Determine card tier: A (full) or B (light)."""
    phase = extract_phase(task_id)
    if phase >= 2:
        return "A"

    own_prefix = extract_layer_prefix(task_id)
    if dep_text and dep_text not in ("--", ""):
        for prefix in LAYER_PREFIXES:
            if prefix != own_prefix and re.search(rf"\b{prefix}\d", dep_text):
                return "A"

    port_patterns = ["ports/", "_port.py", "adapters/", "alembic/", "migrations/"]
    for pattern in port_patterns:
        if pattern in scope_text.lower():
            return "A"

    if task_id.startswith("TASK-OS"):
        return "A"

    return "B"


def parse_card(lines: list[str], heading_idx: int, filepath: str) -> CardInfo:
    """Parse a single task card."""
    match = TASK_HEADING_RE.match(lines[heading_idx])
    task_id = match.group(1).rstrip(":")
    title = lines[heading_idx].split(":", 1)[1].strip() if ":" in lines[heading_idx] else ""

    fields = {}
    matrix_refs = []
    exceptions = []
    raw_lines = []

    end_idx = min(heading_idx + 30, len(lines))
    for i in range(heading_idx + 1, end_idx):
        line = lines[i]
        raw_lines.append(line)

        # Stop at next task heading
        if i > heading_idx + 1 and TASK_HEADING_RE.match(line):
            break
        # Stop at phase heading
        if line.startswith("## Phase") or line.startswith("## ---"):
            break

        # Matrix reference (accumulate -- one ID per line)
        mat_match = MATRIX_REF_RE.search(line)
        if mat_match:
            matrix_refs.append(mat_match.group(1))

        # Exception declaration
        exc_match = EXCEPTION_RE.search(line)
        if exc_match:
            exceptions.append(
                {
                    "id": exc_match.group(1),
                    "field": exc_match.group(2),
                    "owner": exc_match.group(3),
                    "deadline": exc_match.group(4).strip(),
                    "alt": exc_match.group(5).strip(),
                }
            )

        # Field detection - supports both old format (**范围**) and new format (**范围 (In Scope)**)
        field_map = {
            "目标": [r"\*\*目标\*\*"],
            "范围": [r"\*\*范围\s*(\(In Scope\))?\*\*", r"\bIn Scope\b"],
            "范围外": [r"\*\*范围外\s*(\(Out of Scope\))?\*\*", r"\bOut of Scope\b"],
            "依赖": [r"\*\*依赖\*\*"],
            "风险": [r"\*\*风险\*\*"],
            "兼容策略": [r"\*\*兼容策略\*\*"],
            "验收命令": [r"\*\*验收命令\*\*"],
            "回滚方案": [r"\*\*回滚方案\*\*"],
            "证据": [r"\*\*证据\*\*"],
            "决策记录": [r"\*\*决策记录\*\*"],
        }
        for field_name, patterns in field_map.items():
            if field_name in fields:
                continue  # already found
            for pattern in patterns:
                if re.search(pattern, line):
                    # Extract value (content after the field name in table cell)
                    value = line.split("|")[-2].strip() if "|" in line else ""
                    fields[field_name] = value
                    break

    scope_text = fields.get("范围", "")
    dep_text = fields.get("依赖", "")
    tier = determine_tier(task_id, scope_text, dep_text)

    return CardInfo(
        task_id=task_id,
        title=title,
        file=filepath,
        line=heading_idx + 1,
        tier=tier,
        phase=extract_phase(task_id),
        fields=fields,
        matrix_refs=matrix_refs,
        exceptions=exceptions,
        raw_lines=raw_lines,
    )


def collect_matrix_ids() -> set[str]:
    """Collect valid matrix entry IDs."""
    ids = set()
    id_re = re.compile(r"\b([A-Z]+\d+-\d+)\b")
    for mf in MATRIX_FILES:
        if mf.exists():
            text = mf.read_text(encoding="utf-8")
            ids.update(id_re.findall(text))
    return ids


def get_modified_files(diff_base: str) -> set[str]:
    """Get list of files modified since diff_base."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "diff", "--name-only", diff_base, "--", "docs/task-cards/"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        )
        return set(result.stdout.strip().splitlines())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()


def validate_card(card: CardInfo, matrix_ids: set[str]) -> list[Violation]:
    """Validate a single card against schema rules."""
    violations = []
    excepted_fields = {exc["field"] for exc in card.exceptions}

    # --- BLOCK-level checks ---

    # Required fields based on tier
    if card.tier == "A":
        required = [
            "目标",
            "范围",
            "范围外",
            "依赖",
            "兼容策略",
            "验收命令",
            "回滚方案",
            "证据",
            "决策记录",
        ]
    else:
        required = ["目标", "范围", "范围外", "依赖", "兼容策略", "验收命令", "回滚方案", "证据"]

    for req in required:
        if req not in card.fields and req not in excepted_fields:
            violations.append(
                Violation(
                    card_id=card.task_id,
                    file=card.file,
                    line=card.line,
                    severity=Severity.BLOCK,
                    rule="required-field",
                    message=f"Missing required field: {req} (Tier-{card.tier})",
                )
            )

    # Risk field: Tier-A must have it with categories
    if card.tier == "A" and "风险" not in card.fields and "风险" not in excepted_fields:
        violations.append(
            Violation(
                card_id=card.task_id,
                file=card.file,
                line=card.line,
                severity=Severity.BLOCK,
                rule="risk-field-required",
                message="Tier-A card missing risk field (4 categories expected)",
            )
        )

    # Matrix reference (list -- one ID per "> 矩阵条目:" line)
    if not card.matrix_refs:
        violations.append(
            Violation(
                card_id=card.task_id,
                file=card.file,
                line=card.line,
                severity=Severity.BLOCK,
                rule="matrix-orphan",
                message="No matrix reference found within 20 lines of heading",
            )
        )
    elif matrix_ids:
        for ref in card.matrix_refs:
            # Allow sub-references like "D3-2 (前端子实现)"
            base_ref = ref.split()[0] if " " in ref else ref
            if base_ref not in matrix_ids:
                violations.append(
                    Violation(
                        card_id=card.task_id,
                        file=card.file,
                        line=card.line,
                        severity=Severity.BLOCK,
                        rule="matrix-invalid",
                        message=f"Matrix reference '{ref}' not found in milestone-matrix files",
                    )
                )

    # Acceptance command validation
    acc = card.fields.get("验收命令", "")
    if acc:
        # Check for natural language without tags
        has_backtick = "`" in acc
        has_tag = any(tag in acc for tag in ["[ENV-DEP]", "[MANUAL-VERIFY]", "[E2E]"])
        if not has_backtick and not has_tag:
            violations.append(
                Violation(
                    card_id=card.task_id,
                    file=card.file,
                    line=card.line,
                    severity=Severity.BLOCK,
                    rule="acceptance-not-executable",
                    message=(
                        "Acceptance command appears to be natural language"
                        f" without tags: {acc[:80]}"
                    ),
                )
            )
    elif "验收命令" not in excepted_fields:
        violations.append(
            Violation(
                card_id=card.task_id,
                file=card.file,
                line=card.line,
                severity=Severity.BLOCK,
                rule="acceptance-empty",
                message="Acceptance command is empty",
            )
        )

    # Out of Scope non-empty check
    oos = card.fields.get("范围外", "")
    if "范围外" in card.fields and not oos.strip():
        violations.append(
            Violation(
                card_id=card.task_id,
                file=card.file,
                line=card.line,
                severity=Severity.BLOCK,
                rule="out-of-scope-empty",
                message="Out of Scope field exists but is empty",
            )
        )

    # Exception completeness
    for exc in card.exceptions:
        missing = [k for k in ["id", "field", "owner", "deadline", "alt"] if not exc.get(k)]
        if missing:
            violations.append(
                Violation(
                    card_id=card.task_id,
                    file=card.file,
                    line=card.line,
                    severity=Severity.BLOCK,
                    rule="exception-incomplete",
                    message=f"Exception {exc.get('id', '?')} missing: {', '.join(missing)}",
                )
            )
        if exc.get("owner") == "TBD":
            violations.append(
                Violation(
                    card_id=card.task_id,
                    file=card.file,
                    line=card.line,
                    severity=Severity.BLOCK,
                    rule="exception-tbd-owner",
                    message=f"Exception {exc.get('id', '?')} has TBD owner",
                )
            )

    # --- WARNING-level checks ---

    # Objective result-orientation
    obj = card.fields.get("目标", "")
    if obj and not any(kw in obj for kw in RESULT_KEYWORDS):
        violations.append(
            Violation(
                card_id=card.task_id,
                file=card.file,
                line=card.line,
                severity=Severity.WARNING,
                rule="objective-not-result-oriented",
                message=(
                    f"Objective may not be result-oriented (no result keywords found): {obj[:60]}"
                ),
            )
        )

    # [ENV-DEP] commands should have corresponding CI job note
    if "[ENV-DEP]" in acc:
        violations.append(
            Violation(
                card_id=card.task_id,
                file=card.file,
                line=card.line,
                severity=Severity.INFO,
                rule="env-dep-ci-mapping",
                message="[ENV-DEP] command detected - ensure CI job mapping exists",
            )
        )

    # [MANUAL-VERIFY] must have alternative verification (text after the tag)
    if "[MANUAL-VERIFY]" in acc:
        # Extract text after [MANUAL-VERIFY] tag
        mv_idx = acc.index("[MANUAL-VERIFY]") + len("[MANUAL-VERIFY]")
        alt_text = acc[mv_idx:].strip().strip("|").strip()
        # Check for meaningful alternative (not just whitespace or backticks)
        alt_text_clean = alt_text.replace("`", "").strip()
        if len(alt_text_clean) < 5:
            violations.append(
                Violation(
                    card_id=card.task_id,
                    file=card.file,
                    line=card.line,
                    severity=Severity.BLOCK,
                    rule="manual-verify-no-alt",
                    message=(
                        "[MANUAL-VERIFY] must include alternative"
                        " verification description (>= 5 chars)"
                    ),
                )
            )

    return violations


def scan_and_validate(
    base_dir: Path,
    mode: str,
    diff_base: str | None,
    filter_file: Path | None = None,
) -> tuple[list[CardInfo], list[Violation]]:
    """Scan all cards and validate."""
    cards = []
    all_violations = []
    matrix_ids = collect_matrix_ids()

    modified_files = get_modified_files(diff_base) if diff_base else set()

    if filter_file:
        md_files = [filter_file] if filter_file.exists() else []
    else:
        md_files = sorted(base_dir.rglob("*.md"))

    for md_file in md_files:
        lines = md_file.read_text(encoding="utf-8").splitlines()
        filepath = str(md_file)

        for i, line in enumerate(lines):
            if TASK_HEADING_RE.match(line):
                card = parse_card(lines, i, filepath)
                cards.append(card)

                violations = validate_card(card, matrix_ids)

                # Apply mode filtering
                if mode == "incremental" and diff_base:
                    rel_path = str(md_file)
                    if rel_path not in modified_files:
                        # Downgrade BLOCK to WARNING for unmodified files
                        for v in violations:
                            if v.severity == Severity.BLOCK:
                                v.severity = Severity.WARNING
                elif mode == "warning":
                    for v in violations:
                        if v.severity == Severity.BLOCK:
                            v.severity = Severity.WARNING

                all_violations.extend(violations)

    return cards, all_violations


def print_report(cards: list[CardInfo], violations: list[Violation], verbose: bool = False):
    """Print human-readable validation report."""
    blocks = [v for v in violations if v.severity == Severity.BLOCK]
    warnings = [v for v in violations if v.severity == Severity.WARNING]
    infos = [v for v in violations if v.severity == Severity.INFO]

    print("=" * 70)
    print("  DIYU Agent Task Card Schema Validation Report")
    print("=" * 70)
    print()
    print(f"  Cards scanned:  {len(cards)}")
    print(f"  BLOCK:          {len(blocks)}")
    print(f"  WARNING:        {len(warnings)}")
    print(f"  INFO:           {len(infos)}")
    print()

    # Tier distribution
    tier_a = sum(1 for c in cards if c.tier == "A")
    tier_b = sum(1 for c in cards if c.tier == "B")
    print(f"  Tier-A (Full):  {tier_a}")
    print(f"  Tier-B (Light): {tier_b}")
    print()

    if blocks:
        print("-" * 70)
        print("  BLOCK Violations (must fix):")
        print("-" * 70)
        by_rule = defaultdict(list)
        for v in blocks:
            by_rule[v.rule].append(v)

        for rule, vs in sorted(by_rule.items()):
            print(f"\n  [{rule}] ({len(vs)} violations)")
            for v in vs[:10]:  # Show max 10 per rule
                print(f"    {v.file}:{v.line} {v.card_id}")
                print(f"      {v.message}")
            if len(vs) > 10:
                print(f"    ... and {len(vs) - 10} more")
        print()

    if warnings and verbose:
        print("-" * 70)
        print("  WARNING Violations (review recommended):")
        print("-" * 70)
        for v in warnings[:20]:
            print(f"    [{v.rule}] {v.file}:{v.line} {v.card_id}")
            print(f"      {v.message}")
        if len(warnings) > 20:
            print(f"    ... and {len(warnings) - 20} more")
        print()

    # Summary by file
    file_blocks = defaultdict(int)
    for v in blocks:
        file_blocks[v.file] += 1

    if file_blocks:
        print("-" * 70)
        print("  BLOCK count by file:")
        print("-" * 70)
        for f, count in sorted(file_blocks.items(), key=lambda x: -x[1]):
            short = str(Path(f).relative_to("docs/task-cards")) if "docs/task-cards" in f else f
            print(f"    {short:50s} {count:4d}")
        print()

    # Exception summary
    all_exceptions = [exc for c in cards for exc in c.exceptions]
    if all_exceptions:
        print("-" * 70)
        print(f"  Active Exceptions: {len(all_exceptions)}")
        print("-" * 70)
        for exc in all_exceptions:
            card = next(c for c in cards if any(e["id"] == exc["id"] for e in c.exceptions))
            print(
                f"    {exc['id']} | {card.task_id}"
                f" | Field: {exc['field']}"
                f" | Owner: {exc['owner']}"
                f" | Deadline: {exc['deadline']}"
            )
        print()

    print("=" * 70)
    if blocks:
        print(f"  RESULT: FAIL ({len(blocks)} blocking violations)")
    else:
        print(f"  RESULT: PASS (0 blocking violations, {len(warnings)} warnings)")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="DIYU Agent Task Card Schema Validator")
    parser.add_argument(
        "--mode",
        choices=["warning", "incremental", "full"],
        default="warning",
        help="Enforcement mode (default: warning)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all violations")
    parser.add_argument(
        "--diff-base",
        default=None,
        help="Git ref for incremental mode (e.g., main, HEAD~1)",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=TASK_CARDS_DIR,
        help="Base directory for task cards",
    )
    parser.add_argument(
        "--filter-file",
        type=Path,
        default=None,
        help="Validate only a specific task card file",
    )
    args = parser.parse_args()

    if not args.base_dir.exists():
        print(f"Error: {args.base_dir} does not exist", file=sys.stderr)
        sys.exit(2)

    if args.mode == "incremental" and not args.diff_base:
        print(
            "Warning: --diff-base not set for incremental mode, defaulting to 'main'",
            file=sys.stderr,
        )
        args.diff_base = "main"

    cards, violations = scan_and_validate(
        args.base_dir,
        args.mode,
        args.diff_base,
        args.filter_file,
    )

    if args.json:
        output = {
            "mode": args.mode,
            "total_cards": len(cards),
            "violations": [
                {
                    "card_id": v.card_id,
                    "file": v.file,
                    "line": v.line,
                    "severity": v.severity.value,
                    "rule": v.rule,
                    "message": v.message,
                }
                for v in violations
            ],
            "summary": {
                "block": sum(1 for v in violations if v.severity == Severity.BLOCK),
                "warning": sum(1 for v in violations if v.severity == Severity.WARNING),
                "info": sum(1 for v in violations if v.severity == Severity.INFO),
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(cards, violations, verbose=args.verbose)

    # Exit code
    blocks = sum(1 for v in violations if v.severity == Severity.BLOCK)
    sys.exit(1 if blocks > 0 else 0)


if __name__ == "__main__":
    main()
