#!/usr/bin/env python3
"""Task Card Counter - Stage 0 calibration script.

Produces an exact count of all TASK-* cards across docs/task-cards/,
broken down by layer, phase, tier, and file.

Usage:
    python scripts/count_task_cards.py [--json] [--verbose]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

TASK_CARDS_DIR = Path("docs/task-cards")
MATRIX_FILES = [
    Path("docs/governance/milestone-matrix-backend.md"),
    Path("docs/governance/milestone-matrix-frontend.md"),
    Path("docs/governance/milestone-matrix-crosscutting.md"),
]

TASK_HEADING_RE = re.compile(r"^###\s+(TASK-\S+)")
MATRIX_REF_RE = re.compile(r">\s*矩阵条目:\s*(\S+)")

LAYER_PREFIX_MAP = {
    "B": "Brain",
    "MC": "MemoryCore",
    "K": "Knowledge",
    "S": "Skill",
    "T": "Tool",
    "G": "Gateway",
    "I": "Infrastructure",
    "D": "Delivery",
    "OS": "ObsSecurity",
    "FW": "FrontendWeb",
    "FA": "FrontendAdmin",
    "MM": "MultimodalTrack",
    "DEPLOY-FE": "FrontendDeploy",
    "QE": "QualityEngineering",
    "D2": "Delivery",
}

# Tier-A trigger: Phase >= 2 or cross-layer dependency or port/migration scope
CROSS_LAYER_PREFIXES = {"B", "MC", "K", "S", "T", "G", "I", "D", "OS", "FW", "FA"}


def extract_phase(task_id: str) -> int:
    """Extract phase number from task ID like TASK-B2-3 -> 2."""
    match = re.search(r"TASK-\w+-?(\d+)-", task_id) or re.search(r"TASK-[A-Z]+-?(\d+)", task_id)
    if match:
        return int(match.group(1))
    # Handle special patterns like TASK-DEPLOY-FE-1
    match = re.search(r"TASK-DEPLOY-FE-(\d+)", task_id)
    if match:
        return 3  # Deploy tasks are Phase 3
    return -1


def extract_layer(task_id: str) -> str:
    """Extract layer prefix from task ID."""
    # Remove TASK- prefix
    rest = task_id.replace("TASK-", "")
    # Try longest prefix first
    for prefix in sorted(LAYER_PREFIX_MAP.keys(), key=len, reverse=True):
        if rest.startswith(prefix):
            return LAYER_PREFIX_MAP[prefix]
    return "Unknown"


def determine_tier(task_id: str, scope_text: str, dep_text: str) -> str:
    """Determine if a card is Tier-A or Tier-B based on characteristics."""
    phase = extract_phase(task_id)

    # Phase >= 2 -> Tier-A
    if phase >= 2:
        return "A"

    # Cross-layer dependency
    if dep_text and dep_text != "--":
        dep_prefixes = set()
        own_layer = extract_layer(task_id)
        for prefix in CROSS_LAYER_PREFIXES:
            if re.search(rf"\b{prefix}\d", dep_text):
                dep_layer = LAYER_PREFIX_MAP.get(prefix, "")
                if dep_layer and dep_layer != own_layer:
                    dep_prefixes.add(dep_layer)
        if dep_prefixes:
            return "A"

    # Port/Adapter/Migration scope
    port_patterns = ["ports/", "_port.py", "adapters/", "alembic/", "migrations/"]
    if scope_text:
        for pattern in port_patterns:
            if pattern in scope_text.lower():
                return "A"

    # Security-related
    if task_id.startswith("TASK-OS"):
        return "A"

    return "B"


def parse_task_card(lines: list[str], heading_idx: int) -> dict:
    """Parse a single task card starting from the heading line."""
    task_id_match = TASK_HEADING_RE.match(lines[heading_idx])
    if not task_id_match:
        return {}

    task_id = task_id_match.group(1).rstrip(":")
    title = lines[heading_idx].split(":", 1)[1].strip() if ":" in lines[heading_idx] else ""

    # Scan next 25 lines for fields and matrix reference
    fields_found = set()
    matrix_ref = None
    scope_text = ""
    dep_text = ""
    acceptance_text = ""
    has_env_dep = False
    has_manual_verify = False
    has_out_of_scope = False
    has_risk = False
    has_decision = False

    end_idx = min(heading_idx + 25, len(lines))
    for i in range(heading_idx + 1, end_idx):
        line = lines[i]

        # Check for matrix reference
        mat_match = MATRIX_REF_RE.search(line)
        if mat_match:
            matrix_ref = mat_match.group(1)

        # Check for table fields
        if "**目标**" in line:
            fields_found.add("目标")
        if "**范围**" in line or "**范围 (In Scope)**" in line or "In Scope" in line:
            fields_found.add("范围")
            scope_text = line
        if "**范围外**" in line or "Out of Scope" in line:
            fields_found.add("范围外")
            has_out_of_scope = True
        if "**依赖**" in line:
            fields_found.add("依赖")
            dep_text = line
        if "**风险**" in line:
            fields_found.add("风险")
            has_risk = True
        if "**兼容策略**" in line:
            fields_found.add("兼容策略")
        if "**验收命令**" in line:
            fields_found.add("验收命令")
            acceptance_text = line
            if "[ENV-DEP]" in line:
                has_env_dep = True
            if "[MANUAL-VERIFY]" in line:
                has_manual_verify = True
        if "**回滚方案**" in line:
            fields_found.add("回滚方案")
        if "**证据**" in line:
            fields_found.add("证据")
        if "**决策记录**" in line:
            fields_found.add("决策记录")
            has_decision = True

        # Check for EXCEPTION
        if "EXCEPTION:" in line:
            fields_found.add("_exception")

        # Stop at next heading
        if i > heading_idx + 1 and line.startswith("###"):
            break

    tier = determine_tier(task_id, scope_text, dep_text)

    return {
        "id": task_id,
        "title": title,
        "layer": extract_layer(task_id),
        "phase": extract_phase(task_id),
        "tier": tier,
        "matrix_ref": matrix_ref,
        "fields_found": sorted(fields_found),
        "field_count": len(fields_found - {"_exception"}),
        "has_out_of_scope": has_out_of_scope,
        "has_risk": has_risk,
        "has_decision": has_decision,
        "has_env_dep": has_env_dep,
        "has_manual_verify": has_manual_verify,
        "acceptance_text": acceptance_text.strip(),
    }


def scan_all_cards(base_dir: Path) -> list[dict]:
    """Scan all task card files and return parsed cards."""
    cards = []
    for md_file in sorted(base_dir.rglob("*.md")):
        lines = md_file.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if TASK_HEADING_RE.match(line):
                card = parse_task_card(lines, i)
                if card:
                    card["file"] = str(md_file)
                    card["line"] = i + 1
                    cards.append(card)
    return cards


def collect_matrix_ids(matrix_files: list[Path]) -> set[str]:
    """Collect all matrix entry IDs from milestone-matrix files."""
    ids = set()
    id_re = re.compile(r"\b([A-Z]+\d+-\d+)\b")
    for mf in matrix_files:
        if mf.exists():
            text = mf.read_text(encoding="utf-8")
            ids.update(id_re.findall(text))
    return ids


def build_summary(cards: list[dict]) -> dict:
    """Build summary aggregation from card list.

    Returns dict with by_layer, by_phase, by_tier, by_file, gaps.
    Used by both print_report() and --json output.
    """
    by_layer: dict[str, int] = defaultdict(int)
    by_phase: dict[int, int] = defaultdict(int)
    by_tier: dict[str, int] = defaultdict(int)
    by_file: dict[str, int] = defaultdict(int)
    orphans: list[str] = []
    missing_out_of_scope = 0
    missing_risk = 0
    missing_decision_tier_a = 0
    env_dep_count = 0
    manual_verify_count = 0

    for c in cards:
        by_layer[c["layer"]] += 1
        by_phase[c["phase"]] += 1
        by_tier[c["tier"]] += 1
        by_file[c.get("file", "unknown")] += 1
        if not c.get("matrix_ref"):
            orphans.append(c["id"])
        if not c.get("has_out_of_scope"):
            missing_out_of_scope += 1
        if not c.get("has_risk"):
            missing_risk += 1
        if c.get("tier") == "A" and not c.get("has_decision"):
            missing_decision_tier_a += 1
        if c.get("has_env_dep"):
            env_dep_count += 1
        if c.get("has_manual_verify"):
            manual_verify_count += 1

    return {
        "by_layer": dict(by_layer),
        "by_phase": dict(by_phase),
        "by_tier": dict(by_tier),
        "by_file": dict(by_file),
        "gaps": {
            "missing_out_of_scope": missing_out_of_scope,
            "missing_risk": missing_risk,
            "missing_decision_tier_a": missing_decision_tier_a,
            "orphan_count": len(orphans),
            "orphan_ids": orphans,
            "env_dep_count": env_dep_count,
            "manual_verify_count": manual_verify_count,
        },
    }


def print_report(cards: list[dict], verbose: bool = False) -> dict:
    """Print human-readable report and return summary dict."""
    summary = build_summary(cards)
    total = len(cards)
    by_layer = summary["by_layer"]
    by_phase = summary["by_phase"]
    by_tier = summary["by_tier"]
    by_file = summary["by_file"]
    orphans = summary["gaps"]["orphan_ids"]
    missing_out_of_scope = summary["gaps"]["missing_out_of_scope"]
    missing_risk = summary["gaps"]["missing_risk"]
    missing_decision_tier_a = summary["gaps"]["missing_decision_tier_a"]
    env_dep_count = summary["gaps"]["env_dep_count"]
    manual_verify_count = summary["gaps"]["manual_verify_count"]

    print("=" * 60)
    print("  DIYU Agent Task Card Census Report")
    print("=" * 60)
    print()
    print(f"  Total cards: {total}")
    print()

    print("  By Layer:")
    for layer in sorted(by_layer.keys()):
        print(f"    {layer:20s} {by_layer[layer]:4d}")
    print()

    print("  By Phase:")
    for phase in sorted(by_phase.keys()):
        label = f"Phase {phase}" if phase >= 0 else "Unknown"
        print(f"    {label:20s} {by_phase[phase]:4d}")
    print()

    print("  By Tier:")
    for tier in sorted(by_tier.keys()):
        print(f"    Tier-{tier:17s} {by_tier[tier]:4d}")
    print()

    print("  By File:")
    for f in sorted(by_file.keys()):
        short = str(Path(f).relative_to("docs/task-cards"))
        print(f"    {short:45s} {by_file[f]:4d}")
    print()

    print("  Gap Analysis:")
    print(f"    Missing Out of Scope:          {missing_out_of_scope:4d} / {total}")
    print(f"    Missing Risk:                  {missing_risk:4d} / {total}")
    tier_a_count = by_tier.get("A", 0)
    print(f"    Missing Decision (Tier-A):     {missing_decision_tier_a:4d} / {tier_a_count}")
    print(f"    Orphan cards (no matrix ref):  {len(orphans):4d} / {total}")
    print(f"    [ENV-DEP] tagged:              {env_dep_count:4d} / {total}")
    print(f"    [MANUAL-VERIFY] tagged:        {manual_verify_count:4d} / {total}")
    print()

    if orphans and verbose:
        print("  Orphan Card IDs:")
        for oid in orphans:
            print(f"    - {oid}")
        print()

    if verbose:
        print("  All Cards:")
        for c in cards:
            print(
                f"    [{c['tier']}] {c['id']:25s} Phase {c['phase']} | {c['layer']:15s} | "
                f"Fields: {c['field_count']} | Matrix: {c['matrix_ref'] or 'ORPHAN'}"
            )
        print()

    print("=" * 60)
    return summary


def main():
    parser = argparse.ArgumentParser(description="DIYU Agent Task Card Counter")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=TASK_CARDS_DIR,
        help="Base directory for task cards",
    )
    args = parser.parse_args()

    if not args.base_dir.exists():
        print(f"Error: {args.base_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    cards = scan_all_cards(args.base_dir)

    if args.json:
        output = {
            "total": len(cards),
            "cards": cards,
            "summary": build_summary(cards),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(cards, verbose=args.verbose)


if __name__ == "__main__":
    main()
