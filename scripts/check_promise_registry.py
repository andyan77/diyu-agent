#!/usr/bin/env python3
"""check_promise_registry.py - Architecture Promise Traceability Audit

Builds and verifies the full chain:
  Architecture Promise -> Phase -> Task Card -> AC -> Gate -> Evidence -> Owner

Detects:
  - Unmapped promises (architecture section with no task card linkage)
  - Orphaned task cards (task card with no architecture source)
  - Phase mismatches (architecture says Phase N, task card in Phase M)
  - Missing gate coverage (promises with no exit_criteria check)
  - Missing evidence (gate exists but no evidence artifact)

Usage:
    python scripts/check_promise_registry.py [--json] [--verbose]
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARCH_DIR = Path("docs/architecture")
FE_ARCH_DIR = Path("docs/frontend")
DELIVERY_MAP = Path("docs/governance/architecture-phase-delivery-map.md")
TASK_CARD_DIR = Path("docs/task-cards")
MILESTONE_MATRIX = Path("delivery/milestone-matrix.yaml")
EVIDENCE_DIR = Path("evidence")

# Architecture doc numbering: filename prefix -> doc number
DOC_NUMBER_MAP = {
    "00": "00",
    "01": "01",
    "02": "02",
    "03": "03",
    "04": "04",
    "05": "05",  # 05-Gateway层.md  AND  05a-API-Contract.md
    "06": "06",
    "07": "07",
    "08": "08",
}

# Frontend architecture docs use "FE-NN" numbering in delivery map
FE_DOC_PREFIX_MAP = {
    "00": "FE-00",
    "01": "FE-01",
    "02": "FE-02",
    "03": "FE-03",
    "04": "FE-04",
    "05": "FE-05",
    "06": "FE-06",
    "07": "FE-07",
    "08": "FE-08",
}

# Regex patterns
RE_SECTION_HEADER = re.compile(r"^(#{2,})\s+([\d.]+)\s*(.*)", re.MULTILINE)
RE_ADR_REF = re.compile(r"ADR-(\d{3})")
RE_PHASE_MARKER = re.compile(r"Phase\s+(\d)", re.IGNORECASE)
RE_LAW_RULE = re.compile(r"\b(LAW|RULE|BRIDGE)\b")
RE_TASK_ID = re.compile(r"TASK-([A-Z]+)(\d+)-(\d+)")
RE_TABLE_ROW = re.compile(r"^\|(.+)\|$", re.MULTILINE)
RE_DELIVERY_MAP_ROW = re.compile(
    r"\|\s*\*{0,2}"  # opening | + optional bold
    r"((?:FE-)?\d{2}[a]?\s*§[\d.]+(?:[\u2013-][\d.]+)?)"  # "01 §6", "FE-01 §1-2"
    r"[^|]*"  # trailing text in column
    r"\*{0,2}\s*\|"  # optional bold close + |
    r"\s*([A-Z]+\d+-\d+)\s*\|"  # matrix node: "B0-1"
    r"\s*(TASK-[A-Z]+\d+-\d+)\s*\|"  # task card ID: "TASK-B0-1"
    r"\s*(.*?)\s*\|",  # description
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ArchPromise:
    """An architecture promise extracted from docs."""

    promise_id: str
    source_doc: str
    source_section: str
    description: str
    phase_markers: list[int] = field(default_factory=list)
    adr_refs: list[str] = field(default_factory=list)
    constraint_level: str = ""  # LAW / RULE / BRIDGE / ""


@dataclass
class DeliveryMapEntry:
    """A row from the delivery map Table 2."""

    arch_section: str  # e.g., "01 §2.1"
    matrix_node: str  # e.g., "B2-1"
    task_card_id: str  # e.g., "TASK-B2-1"
    description: str


@dataclass
class TaskCard:
    """A task card extracted from docs/task-cards/."""

    task_id: str
    phase: int
    layer: str
    file_path: str
    has_acceptance_cmd: bool = False


@dataclass
class PromiseTraceResult:
    """Traceability result for a single promise."""

    promise_id: str
    source_doc: str
    source_section: str
    description: str
    mapped_task_cards: list[str] = field(default_factory=list)
    mapped_gates: list[str] = field(default_factory=list)
    evidence_paths: list[str] = field(default_factory=list)
    owner: str = ""  # layer/team that owns this promise
    phase_mismatches: list[str] = field(default_factory=list)
    missing_acceptance_cmds: list[str] = field(default_factory=list)  # task cards without AC
    coverage_grade: str = "F"  # A=full, B=task+gate, C=task-only, D=gate-only, F=none


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _doc_number(doc_path: Path, is_frontend: bool = False) -> str:
    """Derive the canonical doc number from a doc file path.

    Backend: "00", "01", ..., "08", "05a"
    Frontend: "FE-00", "FE-01", ..., "FE-08"
    """
    stem = doc_path.stem  # e.g., "05a-API-Contract" or "01-monorepo-infrastructure"
    # Extract prefix before first dash: "05a", "01", etc.
    m = re.match(r"^(\d{2}[a-z]?)", stem)
    if not m:
        return stem[:2]
    prefix = m.group(1)

    if is_frontend:
        return FE_DOC_PREFIX_MAP.get(prefix[:2], f"FE-{prefix}")
    return DOC_NUMBER_MAP.get(prefix, prefix)


def parse_architecture_promises(
    arch_dir: Path, fe_arch_dir: Path | None = None
) -> list[ArchPromise]:
    """Extract promises from architecture doc section headers and content."""
    promises: list[ArchPromise] = []

    dirs_to_scan: list[tuple[Path, bool]] = []
    if arch_dir.exists():
        dirs_to_scan.append((arch_dir, False))
    if fe_arch_dir and fe_arch_dir.exists():
        dirs_to_scan.append((fe_arch_dir, True))

    for scan_dir, is_fe in dirs_to_scan:
        for doc_path in sorted(scan_dir.glob("*.md")):
            if doc_path.name == "README.md":
                continue
            doc_num = _doc_number(doc_path, is_frontend=is_fe)
            content = doc_path.read_text(encoding="utf-8")

            # Extract section-level promises
            for match in RE_SECTION_HEADER.finditer(content):
                level = len(match.group(1))
                section_num = match.group(2).rstrip(".")
                title = match.group(3).strip()

                if level > 4:  # Skip very deep subsections
                    continue

                promise_id = f"{doc_num}-§{section_num}"

                # Look at surrounding context (next 500 chars) for markers
                start = match.end()
                context = content[start : start + 500]

                phase_markers = [int(m) for m in RE_PHASE_MARKER.findall(context)]
                adr_refs = [f"ADR-{m}" for m in RE_ADR_REF.findall(context)]
                constraints = RE_LAW_RULE.findall(context)
                constraint_level = constraints[0] if constraints else ""

                promises.append(
                    ArchPromise(
                        promise_id=promise_id,
                        source_doc=doc_path.name,
                        source_section=section_num,
                        description=title,
                        phase_markers=phase_markers,
                        adr_refs=adr_refs,
                        constraint_level=constraint_level,
                    )
                )

    return promises


def parse_delivery_map(map_path: Path) -> list[DeliveryMapEntry]:
    """Parse the architecture-phase-delivery-map Table 2 rows."""
    entries: list[DeliveryMapEntry] = []

    if not map_path.exists():
        return entries

    content = map_path.read_text(encoding="utf-8")

    for match in RE_DELIVERY_MAP_ROW.finditer(content):
        entries.append(
            DeliveryMapEntry(
                arch_section=match.group(1).strip(),
                matrix_node=match.group(2).strip(),
                task_card_id=match.group(3).strip(),
                description=match.group(4).strip(),
            )
        )

    return entries


def parse_task_cards(task_dir: Path) -> list[TaskCard]:
    """Parse all task card files to extract task IDs and metadata."""
    cards: list[TaskCard] = []

    if not task_dir.exists():
        return cards

    for md_file in sorted(task_dir.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")

        for match in RE_TASK_ID.finditer(content):
            prefix = match.group(1)
            phase = int(match.group(2))
            task_id = match.group(0)

            # Check if this is a heading (actual task definition, not just a reference)
            line_start = content.rfind("\n", 0, match.start()) + 1
            line = content[line_start : match.end() + 50]
            if "###" not in line and "TASK-" not in line[:10]:
                continue

            has_ac = bool(
                re.search(
                    r"验收命令|acceptance|check.*command",
                    content[match.start() : match.start() + 2000],
                    re.IGNORECASE,
                )
            )

            cards.append(
                TaskCard(
                    task_id=task_id,
                    phase=phase,
                    layer=prefix,
                    file_path=str(md_file),
                    has_acceptance_cmd=has_ac,
                )
            )

    # Deduplicate by task_id
    seen: set[str] = set()
    unique: list[TaskCard] = []
    for card in cards:
        if card.task_id not in seen:
            seen.add(card.task_id)
            unique.append(card)

    return unique


def parse_gate_checks(matrix_path: Path) -> dict[str, list[str]]:
    """Parse milestone-matrix.yaml to extract exit_criteria per phase.

    Returns: {phase_key: [check_id, ...]}
    """
    gates: dict[str, list[str]] = {}

    if not matrix_path.exists():
        return gates

    try:
        import yaml

        data = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    except Exception:
        return gates

    phases = data.get("phases", {})
    for phase_key, phase_data in phases.items():
        criteria = phase_data.get("exit_criteria", {})
        check_ids: list[str] = []
        for tier in ("hard", "soft"):
            for item in criteria.get(tier, []):
                if isinstance(item, dict) and "id" in item:
                    check_ids.append(item["id"])
        gates[phase_key] = check_ids

    return gates


# ---------------------------------------------------------------------------
# Traceability Engine
# ---------------------------------------------------------------------------


def _normalize_section_key(raw: str) -> str:
    """Normalize a section reference to a canonical form for matching.

    Examples:
        "01 §6"     -> "01§6"
        "01-§6"     -> "01§6"
        "05a §1.1"  -> "05a§1.1"
        "FE-01 §1"  -> "FE-01§1"
        "FE-08-§2"  -> "FE-08§2"
    """
    s = raw.replace(" ", "")
    # Collapse "NN-§" to "NN§" but preserve "FE-NN§"
    # "01-§6" -> "01§6", "FE-01-§1" -> "FE-01§1"
    s = re.sub(r"(\d{2}[a]?)-§", r"\1§", s)
    return s


def _derive_owner(promise_id: str, source_doc: str) -> str:
    """Derive the owning layer/team from promise prefix or doc name."""
    # Frontend promises are identified by the FE- prefix (check first)
    if promise_id.startswith("FE-"):
        return "Frontend"
    doc_lower = source_doc.lower()
    if "brain" in doc_lower or "01-" in doc_lower:
        return "Brain"
    if "knowledge" in doc_lower or "02-" in doc_lower:
        return "Knowledge"
    if "skill" in doc_lower or "03-" in doc_lower:
        return "Skill"
    if "tool" in doc_lower or "04-" in doc_lower:
        return "Tool"
    if "gateway" in doc_lower or "05-" in doc_lower or "05a-" in doc_lower:
        return "Gateway"
    if "基础设施" in doc_lower or "06-" in doc_lower:
        return "Infrastructure"
    if "部署" in doc_lower or "07-" in doc_lower:
        return "Delivery"
    if "附录" in doc_lower or "08-" in doc_lower:
        return "Cross-cutting"
    if "总览" in doc_lower or "00-" in doc_lower:
        return "Architecture"
    return "Unknown"


def _find_evidence(gate_ids: list[str], evidence_dir: Path) -> list[str]:
    """Find evidence files related to gate check IDs."""
    evidence_paths: list[str] = []
    if not evidence_dir.exists():
        return evidence_paths

    all_evidence = list(evidence_dir.rglob("*.json")) + list(evidence_dir.rglob("*.txt"))
    for gate_id in gate_ids:
        # Normalize gate_id for matching: "p1-rls" -> search for "rls" or "p1-rls"
        gate_lower = gate_id.lower().replace("-", "_")
        for ev_path in all_evidence:
            if gate_lower in ev_path.stem.lower().replace("-", "_"):
                evidence_paths.append(str(ev_path))
                break

    return evidence_paths


def build_trace(
    promises: list[ArchPromise],
    delivery_entries: list[DeliveryMapEntry],
    task_cards: list[TaskCard],
    gates: dict[str, list[str]],
) -> list[PromiseTraceResult]:
    """Build traceability chain for each architecture promise."""
    # Index delivery map by architecture section (normalized)
    section_to_tasks: dict[str, list[str]] = {}
    for entry in delivery_entries:
        norm = _normalize_section_key(entry.arch_section)
        section_to_tasks.setdefault(norm, []).append(entry.task_card_id)

    # Index delivery map entries by task card ID for phase extraction
    delivery_by_task: dict[str, DeliveryMapEntry] = {}
    for entry in delivery_entries:
        delivery_by_task[entry.task_card_id] = entry

    # Index task cards by ID
    task_card_map: dict[str, TaskCard] = {card.task_id: card for card in task_cards}
    task_card_ids = set(task_card_map.keys())

    # All gate check IDs (flattened)
    all_gate_ids = set()
    for check_ids in gates.values():
        all_gate_ids.update(check_ids)

    results: list[PromiseTraceResult] = []

    for promise in promises:
        # Find matching delivery map entries
        mapped_tasks: list[str] = []
        norm_promise = _normalize_section_key(promise.promise_id)

        # Direct match
        if norm_promise in section_to_tasks:
            mapped_tasks.extend(section_to_tasks[norm_promise])

        # Subsection match: "01§2" matches "01§2.1", "01§2.2" but NOT "01§21"
        for section_key, tasks in section_to_tasks.items():
            if (
                section_key.startswith(norm_promise)
                and section_key != norm_promise
                and section_key[len(norm_promise) :].startswith(".")
            ):
                mapped_tasks.extend(tasks)

        # Verify mapped tasks actually exist as task cards
        verified_tasks = [t for t in mapped_tasks if t in task_card_ids]

        # Phase mismatch detection
        phase_mismatches: list[str] = []
        if promise.phase_markers:
            arch_phases = set(promise.phase_markers)
            for task_id in verified_tasks:
                card = task_card_map.get(task_id)
                if card and card.phase not in arch_phases:
                    phase_mismatches.append(
                        f"{task_id} is Phase {card.phase},"
                        f" but architecture says Phase {sorted(arch_phases)}"
                    )

        # Acceptance command (AC) linkage check
        missing_ac: list[str] = []
        for task_id in verified_tasks:
            card = task_card_map.get(task_id)
            if card and not card.has_acceptance_cmd:
                missing_ac.append(task_id)

        # Find gate coverage
        mapped_gates: list[str] = []
        for gate_id in all_gate_ids:
            for task_id in verified_tasks:
                task_match = RE_TASK_ID.match(task_id)
                if task_match:
                    prefix = task_match.group(1).lower()
                    if prefix in gate_id.lower():
                        mapped_gates.append(gate_id)
                        break

        # Find evidence
        evidence_paths = _find_evidence(mapped_gates, EVIDENCE_DIR)

        # Derive owner
        owner = _derive_owner(promise.promise_id, promise.source_doc)

        # Determine coverage grade
        # Full chain: Task Card -> AC -> Gate -> Evidence -> Owner
        has_tasks = len(verified_tasks) > 0
        has_ac = has_tasks and len(missing_ac) < len(verified_tasks)  # at least one task has AC
        has_gates = len(mapped_gates) > 0
        has_evidence = len(evidence_paths) > 0

        if has_tasks and has_ac and has_gates and has_evidence:
            grade = "A"  # Full chain with evidence
        elif has_tasks and has_ac and has_gates:
            grade = "B"  # Task + AC + gate, no evidence
        elif has_tasks and has_gates:
            grade = "B-"  # Task + gate but AC gap (chain incomplete)
        elif has_tasks:
            grade = "C"  # Task card exists but no gate
        elif has_gates:
            grade = "D"  # Gate exists but no task card
        else:
            grade = "F"  # No coverage

        results.append(
            PromiseTraceResult(
                promise_id=promise.promise_id,
                source_doc=promise.source_doc,
                source_section=promise.source_section,
                description=promise.description,
                mapped_task_cards=list(set(verified_tasks)),
                mapped_gates=list(set(mapped_gates)),
                evidence_paths=evidence_paths,
                owner=owner,
                phase_mismatches=phase_mismatches,
                missing_acceptance_cmds=missing_ac,
                coverage_grade=grade,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def generate_report(
    results: list[PromiseTraceResult],
    delivery_entries: list[DeliveryMapEntry],
    task_cards: list[TaskCard],
    use_json: bool = False,
    verbose: bool = False,
) -> dict:
    """Generate the audit report."""
    # Summary stats
    total = len(results)
    by_grade: dict[str, int] = {"A": 0, "B": 0, "B-": 0, "C": 0, "D": 0, "F": 0}
    for r in results:
        by_grade[r.coverage_grade] = by_grade.get(r.coverage_grade, 0) + 1

    unmapped = [r for r in results if r.coverage_grade == "F"]
    task_only = [r for r in results if r.coverage_grade == "C"]

    # Orphaned task cards (in task cards but not referenced by any delivery map entry)
    mapped_task_ids = {e.task_card_id for e in delivery_entries}
    all_task_ids = {c.task_id for c in task_cards}
    orphaned_tasks = sorted(all_task_ids - mapped_task_ids)

    # Phase mismatches
    all_mismatches = [
        {"promise_id": r.promise_id, "mismatches": r.phase_mismatches}
        for r in results
        if r.phase_mismatches
    ]

    # Missing acceptance commands (AC gap in chain)
    all_missing_ac = [
        {"promise_id": r.promise_id, "missing_ac_tasks": r.missing_acceptance_cmds}
        for r in results
        if r.missing_acceptance_cmds
    ]

    report = {
        "status": "pass" if len(unmapped) == 0 else "warn",
        "summary": {
            "total_promises": total,
            "grade_distribution": by_grade,
            "unmapped_count": len(unmapped),
            "task_only_count": len(task_only),
            "orphaned_task_cards": len(orphaned_tasks),
            "phase_mismatches": len(all_mismatches),
            "missing_acceptance_cmds": len(all_missing_ac),
        },
        "unmapped_promises": [
            {
                "promise_id": r.promise_id,
                "source_doc": r.source_doc,
                "description": r.description,
            }
            for r in unmapped
        ],
        "orphaned_task_cards": orphaned_tasks[:20],
        "phase_mismatches": all_mismatches[:20],
        "missing_acceptance_cmds": all_missing_ac[:20],
    }

    if verbose:
        report["all_results"] = [
            {
                "promise_id": r.promise_id,
                "source_doc": r.source_doc,
                "source_section": r.source_section,
                "description": r.description,
                "mapped_task_cards": r.mapped_task_cards,
                "mapped_gates": r.mapped_gates,
                "evidence_paths": r.evidence_paths,
                "owner": r.owner,
                "phase_mismatches": r.phase_mismatches,
                "missing_acceptance_cmds": r.missing_acceptance_cmds,
                "coverage_grade": r.coverage_grade,
            }
            for r in results
        ]

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    use_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv

    # Parse all sources
    promises = parse_architecture_promises(ARCH_DIR, FE_ARCH_DIR)
    delivery_entries = parse_delivery_map(DELIVERY_MAP)
    task_cards = parse_task_cards(TASK_CARD_DIR)
    gates = parse_gate_checks(MILESTONE_MATRIX)

    # Build traceability
    results = build_trace(promises, delivery_entries, task_cards, gates)

    # Generate report
    report = generate_report(results, delivery_entries, task_cards, use_json, verbose)

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print(f"Promise Registry: {s['total_promises']} promises found")
        print(f"  Grade distribution: {s['grade_distribution']}")
        print(f"  Unmapped (F): {s['unmapped_count']}")
        print(f"  Task-only, no gate (C): {s['task_only_count']}")
        print(f"  Orphaned task cards: {s['orphaned_task_cards']}")
        print(f"  Phase mismatches: {s['phase_mismatches']}")
        print(f"  Missing acceptance cmds: {s['missing_acceptance_cmds']}")

        if report["unmapped_promises"]:
            print(f"\n  Top unmapped promises ({min(10, len(report['unmapped_promises']))}):")
            for item in report["unmapped_promises"][:10]:
                print(f"    {item['promise_id']} [{item['source_doc']}]: {item['description']}")

        if report["phase_mismatches"]:
            print(f"\n  Phase mismatches ({len(report['phase_mismatches'])}):")
            for item in report["phase_mismatches"][:10]:
                for mm in item["mismatches"]:
                    print(f"    {item['promise_id']}: {mm}")

        if report["missing_acceptance_cmds"]:
            print(f"\n  Missing AC ({len(report['missing_acceptance_cmds'])}):")
            for item in report["missing_acceptance_cmds"][:10]:
                tasks = ", ".join(item["missing_ac_tasks"][:3])
                print(f"    {item['promise_id']}: {tasks}")

    sys.exit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
