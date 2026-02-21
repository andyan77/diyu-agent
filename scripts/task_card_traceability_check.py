#!/usr/bin/env python3
"""Task Card Traceability Check.

Verifies bidirectional traceability between milestone-matrix entries
(milestone-matrix.yaml milestones[]) and task cards (docs/task-cards/).

Checks:
  1. Every milestone ID in YAML has at least one task card referencing it.
  2. Every task card's matrix_ref points to a valid milestone ID.

Outputs dual coverage metrics:
  - main_coverage: only primary "> 矩阵条目:" / "> Matrix" refs
  - all_coverage:  primary refs + M-Track cross-references

Independent from check_task_schema.py (schema compliance) and
milestone_aggregator.py (coverage statistics).

Usage:
    python3 scripts/task_card_traceability_check.py          # human
    python3 scripts/task_card_traceability_check.py --json   # JSON
    python3 scripts/task_card_traceability_check.py --phase 0  # filter
    python3 scripts/task_card_traceability_check.py --threshold 98  # custom

Exit codes:
    0: All checks pass (or no milestones defined yet)
    1: Traceability gaps found
    2: Configuration error
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")
TASK_CARDS_DIR = Path("docs/task-cards")
CROSSCUTTING_PATH = Path("docs/governance/milestone-matrix-crosscutting.md")

# Primary matrix reference: Chinese or English format
MATRIX_REF_RE = re.compile(r">\s*(?:矩阵条目|[Mm]atrix\s*\S*?):\s*(\S+)")
TASK_HEADING_RE = re.compile(r"^###\s+(TASK-\S+)")
PHASE_HEADING_RE = re.compile(r"^##\s+Phase\s+(\d+)")
# M-Track cross-reference within a line
M_TRACK_RE = re.compile(r"M-Track:\s*(MM\S+)")
# X/XF/XM node IDs in crosscutting Section 4
XNODE_RE = re.compile(r"\|\s*(X[FM]?\d+-\d+)\s*\|")

DEFAULT_THRESHOLD = 98.0


def load_xnode_ids(
    *,
    crosscutting_path: Path | None = None,
) -> set[str]:
    """Extract X/XF/XM node IDs from crosscutting.md Section 4.

    Used ONLY for dangling_refs whitelist -- not merged into milestone_ids
    to avoid inflating the coverage denominator.
    """
    path = crosscutting_path or CROSSCUTTING_PATH
    if not path.exists():
        return set()
    ids: set[str] = set()
    in_section4 = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## 4."):
            in_section4 = True
        elif line.startswith("## ") and not line.startswith("## 4.") and in_section4:
            break
        if in_section4:
            for m in XNODE_RE.finditer(line):
                ids.add(m.group(1))
    return ids


def load_milestone_ids(
    phase_filter: int | None = None,
    *,
    matrix_path: Path | None = None,
) -> set[str]:
    """Extract all milestone IDs from YAML milestones[] arrays."""
    path = matrix_path or MATRIX_PATH
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(2)
    with path.open() as f:
        data = yaml.safe_load(f)

    ids: set[str] = set()
    for phase_key, phase in data.get("phases", {}).items():
        if phase_filter is not None:
            phase_num = int(phase_key.replace("phase_", ""))
            if phase_num != phase_filter:
                continue
        for m in phase.get("milestones", []):
            mid = m.get("id")
            if mid:
                ids.add(mid)
    return ids


def _extract_phase_from_filename(md_file: Path) -> int | None:
    """Extract phase number from cross-layer integration filenames.

    e.g. phase-3-integration.md -> 3
    """
    m = re.match(r"phase-(\d+)", md_file.stem)
    return int(m.group(1)) if m else None


def scan_task_cards(
    *,
    cards_dir: Path | None = None,
    phase_filter: int | None = None,
) -> dict[str, dict[str, list[str]]]:
    """Scan task cards for primary refs and M-Track cross-refs.

    When phase_filter is set, only refs from tasks belonging to that phase
    are included. Phase membership is determined by:
      1. ``## Phase N`` headings within multi-phase files, or
      2. Filename pattern (e.g. ``phase-3-integration.md``).

    Returns:
        {
            "main_refs": {milestone_id: [task_card_ids...]},
            "m_track_refs": {milestone_id: [task_card_ids...]},
        }
    """
    main_refs: dict[str, list[str]] = {}
    m_track_refs: dict[str, list[str]] = {}

    base = cards_dir or TASK_CARDS_DIR
    if not base.exists():
        return {"main_refs": main_refs, "m_track_refs": m_track_refs}

    for md_file in base.rglob("*.md"):
        file_phase = _extract_phase_from_filename(md_file)
        current_task: str | None = None
        current_section_phase: int | None = file_phase
        for line in md_file.read_text(errors="replace").splitlines():
            # Track ## Phase N section headings
            phase_match = PHASE_HEADING_RE.match(line)
            if phase_match:
                current_section_phase = int(phase_match.group(1))

            heading = TASK_HEADING_RE.match(line)
            if heading:
                current_task = heading.group(1)

            # Skip refs not in the requested phase
            if phase_filter is not None and current_section_phase != phase_filter:
                continue

            ref_match = MATRIX_REF_RE.match(line)
            if ref_match:
                ref_id = ref_match.group(1)
                source = current_task or md_file.stem
                main_refs.setdefault(ref_id, []).append(source)

            m_track_match = M_TRACK_RE.search(line)
            if m_track_match:
                m_id = m_track_match.group(1)
                source = current_task or md_file.stem
                m_track_refs.setdefault(m_id, []).append(source)

    return {"main_refs": main_refs, "m_track_refs": m_track_refs}


def _coverage_block(
    milestone_ids: set[str],
    covered_ids: set[str],
) -> dict:
    orphans = sorted(milestone_ids - covered_ids)
    total = len(milestone_ids)
    covered = total - len(orphans)
    pct = (covered / total * 100) if total > 0 else 0.0
    return {
        "total": total,
        "covered": covered,
        "coverage_pct": round(pct, 1),
        "orphan_milestones": orphans,
    }


def compute_result(
    milestone_ids: set[str],
    card_data: dict[str, dict[str, list[str]]],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """Compute dual coverage result.

    Returns dict with main_coverage, all_coverage, status, dangling_refs.
    """
    main_refs = card_data["main_refs"]
    m_track_refs = card_data["m_track_refs"]

    main_covered = milestone_ids & set(main_refs.keys())
    all_covered = main_covered | (milestone_ids & set(m_track_refs.keys()))

    main_block = _coverage_block(milestone_ids, main_covered)
    all_block = _coverage_block(milestone_ids, all_covered)

    # Dangling: refs in cards that point to no known ID.
    # Whitelist includes milestone_ids + xnode_ids (X/XF/XM from crosscutting).
    # xnode_ids is NOT merged into milestone_ids to preserve coverage denominator.
    xnode_ids = load_xnode_ids()
    known_valid_ids = milestone_ids | xnode_ids
    all_card_refs = set(main_refs.keys()) | set(m_track_refs.keys())
    dangling = sorted(all_card_refs - known_valid_ids)

    # Status based on all_coverage (main + M-Track) threshold
    status = "FAIL" if all_block["coverage_pct"] < threshold else "PASS"

    return {
        "status": status,
        "threshold": threshold,
        "main_coverage": main_block,
        "all_coverage": all_block,
        "dangling_refs": dangling,
    }


def main() -> None:
    json_mode = "--json" in sys.argv
    phase_filter: int | None = None
    threshold = DEFAULT_THRESHOLD

    if "--phase" in sys.argv:
        idx = sys.argv.index("--phase")
        if idx + 1 < len(sys.argv):
            try:
                phase_filter = int(sys.argv[idx + 1])
            except ValueError:
                print("ERROR: --phase requires integer", file=sys.stderr)
                sys.exit(2)

    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        if idx + 1 < len(sys.argv):
            try:
                threshold = float(sys.argv[idx + 1])
            except ValueError:
                print("ERROR: --threshold requires number", file=sys.stderr)
                sys.exit(2)

    milestone_ids = load_milestone_ids(phase_filter)
    if not milestone_ids:
        msg = "No milestones defined"
        if phase_filter is not None:
            msg += f" for phase_{phase_filter}"
        if json_mode:
            json.dump({"status": "ERROR", "detail": msg}, sys.stdout)
            print()
        else:
            print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(2)

    card_data = scan_task_cards(phase_filter=phase_filter)
    result = compute_result(milestone_ids, card_data, threshold)

    if phase_filter is not None:
        result["phase_filter"] = phase_filter

    if json_mode:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        mc = result["main_coverage"]
        ac = result["all_coverage"]
        status = result["status"]
        print(
            f"{status}: main {mc['covered']}/{mc['total']} "
            f"({mc['coverage_pct']:.1f}%), "
            f"all {ac['covered']}/{ac['total']} "
            f"({ac['coverage_pct']:.1f}%) "
            f"[threshold: {threshold}%]"
        )
        if mc["orphan_milestones"]:
            print("\n  Orphan milestones (no primary task card ref):")
            for mid in mc["orphan_milestones"]:
                print(f"    - {mid}")
        if result["dangling_refs"]:
            print("\n  Dangling refs (card -> unknown milestone):")
            for ref in result["dangling_refs"]:
                print(f"    - {ref}")

    sys.exit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
