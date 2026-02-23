#!/usr/bin/env python3
"""check_adr_consistency.py - ADR Consistency Audit

Verifies ADR (Architecture Decision Record) integrity across docs,
task cards, gate checks, test files, and code patterns.

Detects:
  - Phantom references: ADR cited in docs but not in the index
  - Deprecated-still-active: deprecated ADR referenced without caveat
  - Broken amends chain: ADR-X amends ADR-Y but Y is missing
  - Gap in numbering: missing ADR numbers in sequence
  - Standalone file mismatch: ADR file exists but not in index
  - Zero-gate-coverage: ADR has no gate check in milestone-matrix
  - Zero-task-card-refs: ADR not referenced by any task card
  - Code violations: ADR decisions contradicted by code patterns

Output per ADR:
  {adr_id, status, defined_in, task_card_refs[], gate_refs[],
   test_refs[], code_violations[]}

Usage:
    python scripts/check_adr_consistency.py [--json] [--verbose]
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARCH_DIR = Path("docs/architecture")
FE_ARCH_DIR = Path("docs/frontend")
ADR_DIR = Path("docs/adr")
APPENDIX_DOC = Path("docs/architecture/08-附录.md")
TASK_CARD_DIR = Path("docs/task-cards")
MILESTONE_MATRIX = Path("delivery/milestone-matrix.yaml")
TEST_DIR = Path("tests")
SRC_DIR = Path("src")
REVIEWS_DIR = Path("docs/reviews")
GOVERNANCE_DIR = Path("docs/governance")

# Regex patterns
RE_ADR_REF = re.compile(r"ADR-(\d{3})")
RE_ADR_INDEX_ROW = re.compile(
    r"\|\s*[~*]{0,4}(ADR-\d{3})[~*]{0,4}\s*\|"  # ADR number (may be bold or struck)
    r"\s*[~*]{0,4}(.*?)[~*]{0,4}\s*\|"  # title column
    r"\s*[~*]{0,4}(.*?)[~*]{0,4}\s*\|",  # version column
)
RE_ADR_RANGE = re.compile(r"ADR-(\d{3})\s*[~\uff5e]\s*ADR-(\d{3})")
RE_DEPRECATED = re.compile(r"~~ADR-(\d{3})~~|废弃|deprecated", re.IGNORECASE)
RE_AMENDS = re.compile(r"amends\s+ADR-(\d{3})", re.IGNORECASE)
RE_SUPERSEDED = re.compile(
    r"废弃[\uff0c,\s]*见\s*ADR-(\d{3})|superseded\s+by\s+ADR-(\d{3})",
    re.IGNORECASE,
)

# Code violation patterns: ADR ID -> (pattern_that_violates, description)
# These check that code does NOT contain patterns that contradict the ADR decision.
ADR_CODE_VIOLATIONS: dict[str, list[tuple[str, str, str]]] = {
    # ADR-018: Knowledge never reads Memory Core
    "ADR-018": [
        (
            r"from\s+src\.memory|import\s+src\.memory",
            "src/knowledge/",
            "Knowledge layer imports src.memory (violates privacy hard boundary)",
        ),
    ],
    # ADR-052: No ETag, must use SHA-256 checksum
    "ADR-052": [
        (
            r'["\']ETag["\']|etag',
            "src/",
            "ETag usage found (ADR-052 mandates x-amz-checksum-sha256)",
        ),
    ],
    # ADR-008: LiteLLM SDK integration, no standalone proxy
    "ADR-008": [
        (
            r"from\s+openai\s+import|import\s+openai(?!.*litellm)",
            "src/brain/",
            "Direct openai import in Brain (should go through LiteLLM/LLMCallPort)",
        ),
        (
            r"from\s+anthropic\s+import|import\s+anthropic",
            "src/brain/",
            "Direct anthropic import in Brain (should go through LiteLLM/LLMCallPort)",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ADREntry:
    """An ADR from the index table."""

    adr_id: str  # "ADR-001"
    adr_num: int  # 1
    title: str
    version: str
    is_deprecated: bool = False
    superseded_by: str | None = None  # "ADR-017" if deprecated
    amends: list[str] = field(default_factory=list)


@dataclass
class ADRReference:
    """A reference to an ADR found in a document."""

    adr_id: str
    source_file: str
    line_num: int
    context: str  # surrounding text


@dataclass
class ADRAuditResult:
    """Full audit result for a single ADR."""

    adr_id: str
    status: str  # "indexed" | "standalone" | "orphaned"
    defined_in: str  # file where ADR is defined
    task_card_refs: list[str] = field(default_factory=list)
    gate_refs: list[str] = field(default_factory=list)
    test_refs: list[str] = field(default_factory=list)
    code_violations: list[str] = field(default_factory=list)


@dataclass
class Finding:
    """An audit finding."""

    severity: str  # "error" | "warning" | "info"
    category: str
    message: str
    details: dict | None = None


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_adr_index(appendix_path: Path) -> dict[str, ADREntry]:
    """Parse the ADR index table from 08-附录.md."""
    adrs: dict[str, ADREntry] = {}

    if not appendix_path.exists():
        return adrs

    content = appendix_path.read_text(encoding="utf-8")

    for match in RE_ADR_INDEX_ROW.finditer(content):
        adr_id = match.group(1).strip()
        title = match.group(2).strip()
        version = match.group(3).strip()

        # Clean up strikethrough markers
        clean_id = adr_id.replace("~~", "")
        adr_num_match = RE_ADR_REF.search(clean_id)
        if not adr_num_match:
            continue

        adr_num = int(adr_num_match.group(1))

        # Check if deprecated
        row_text = match.group(0)
        is_deprecated = bool(RE_DEPRECATED.search(row_text))

        # Check superseded_by
        superseded = RE_SUPERSEDED.search(title) or RE_SUPERSEDED.search(row_text)
        superseded_by = None
        if superseded:
            superseded_by = f"ADR-{superseded.group(1) or superseded.group(2)}"

        # Check amends
        amends_refs = [f"ADR-{m}" for m in RE_AMENDS.findall(title) + RE_AMENDS.findall(row_text)]

        canonical_id = f"ADR-{adr_num:03d}"
        adrs[canonical_id] = ADREntry(
            adr_id=canonical_id,
            adr_num=adr_num,
            title=title,
            version=version,
            is_deprecated=is_deprecated,
            superseded_by=superseded_by,
            amends=amends_refs,
        )

    return adrs


def parse_standalone_adrs(adr_dir: Path) -> dict[str, Path]:
    """Find standalone ADR files (e.g., ADR-053)."""
    files: dict[str, Path] = {}
    if not adr_dir.exists():
        return files

    for f in adr_dir.glob("ADR-*.md"):
        m = RE_ADR_REF.search(f.stem)
        if m:
            adr_id = f"ADR-{int(m.group(1)):03d}"
            files[adr_id] = f

    return files


def find_adr_references(
    *dirs: Path,
) -> list[ADRReference]:
    """Find all ADR references across docs."""
    refs: list[ADRReference] = []

    for scan_dir in dirs:
        if not scan_dir.exists():
            continue
        for doc_path in sorted(scan_dir.rglob("*.md")):
            content = doc_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                for match in RE_ADR_REF.finditer(line):
                    adr_num = int(match.group(1))
                    adr_id = f"ADR-{adr_num:03d}"
                    # Get context (trim line around match)
                    start = max(0, match.start() - 30)
                    end = min(len(line), match.end() + 30)
                    context = line[start:end].strip()

                    refs.append(
                        ADRReference(
                            adr_id=adr_id,
                            source_file=str(doc_path),
                            line_num=line_num,
                            context=context,
                        )
                    )

    return refs


def find_task_card_adr_refs(task_card_dir: Path) -> dict[str, list[str]]:
    """Find ADR references in task cards.

    Returns: {adr_id: [task_card_file, ...]}
    """
    refs: dict[str, list[str]] = {}
    if not task_card_dir.exists():
        return refs

    for md_file in sorted(task_card_dir.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        found_adrs = set(RE_ADR_REF.findall(content))
        for adr_num_str in found_adrs:
            adr_id = f"ADR-{int(adr_num_str):03d}"
            refs.setdefault(adr_id, []).append(str(md_file))

    return refs


def find_gate_adr_refs(matrix_path: Path) -> dict[str, list[str]]:
    """Find ADR references in milestone-matrix gate checks.

    Returns: {adr_id: [gate_check_id, ...]}
    """
    refs: dict[str, list[str]] = {}
    if not matrix_path.exists():
        return refs

    try:
        import yaml

        data = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    except Exception:
        return refs

    phases = data.get("phases", {})
    for _phase_key, phase_data in phases.items():
        criteria = phase_data.get("exit_criteria", {})
        for tier in ("hard", "soft"):
            for item in criteria.get(tier, []):
                if not isinstance(item, dict):
                    continue
                gate_id = item.get("id", "")
                desc = item.get("description", "")
                check = item.get("check", "")
                combined = f"{gate_id} {desc} {check}"
                for adr_num_str in RE_ADR_REF.findall(combined):
                    adr_id = f"ADR-{int(adr_num_str):03d}"
                    refs.setdefault(adr_id, []).append(gate_id)

        # Also check milestone descriptions for ADR refs
        for milestone in phase_data.get("milestones", []):
            if isinstance(milestone, dict):
                summary = milestone.get("summary", "")
                mid = milestone.get("id", "")
                for adr_num_str in RE_ADR_REF.findall(summary):
                    adr_id = f"ADR-{int(adr_num_str):03d}"
                    refs.setdefault(adr_id, []).append(mid)

    return refs


def find_test_adr_refs(test_dir: Path) -> dict[str, list[str]]:
    """Find ADR references in test files.

    Returns: {adr_id: [test_file, ...]}
    """
    refs: dict[str, list[str]] = {}
    if not test_dir.exists():
        return refs

    for py_file in sorted(test_dir.rglob("*.py")):
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            logger.debug("Could not read %s, skipping", py_file)
            continue
        found_adrs = set(RE_ADR_REF.findall(content))
        for adr_num_str in found_adrs:
            adr_id = f"ADR-{int(adr_num_str):03d}"
            refs.setdefault(adr_id, []).append(str(py_file))

    return refs


def check_code_violations(src_dir: Path) -> dict[str, list[str]]:
    """Check code patterns that violate ADR decisions.

    Returns: {adr_id: [violation_description, ...]}
    """
    violations: dict[str, list[str]] = {}
    if not src_dir.exists():
        return violations

    for adr_id, patterns in ADR_CODE_VIOLATIONS.items():
        for pattern, dir_prefix, description in patterns:
            scan_dir = src_dir.parent / dir_prefix.rstrip("/")
            if not scan_dir.exists():
                continue
            compiled = re.compile(pattern, re.IGNORECASE)
            for py_file in sorted(scan_dir.rglob("*.py")):
                # Skip test files and __pycache__
                if "__pycache__" in str(py_file):
                    continue
                try:
                    content = py_file.read_text(encoding="utf-8")
                except Exception:
                    logger.debug("Could not read %s, skipping", py_file)
                    continue
                for line_num, line in enumerate(content.split("\n"), 1):
                    if compiled.search(line):
                        violations.setdefault(adr_id, []).append(
                            f"{description} ({py_file}:{line_num})"
                        )

    return violations


# ---------------------------------------------------------------------------
# Audit Engine
# ---------------------------------------------------------------------------


def run_audit(
    index: dict[str, ADREntry],
    standalone_files: dict[str, Path],
    references: list[ADRReference],
    task_card_refs: dict[str, list[str]],
    gate_refs: dict[str, list[str]],
    test_refs: dict[str, list[str]],
    code_violations: dict[str, list[str]],
) -> tuple[list[Finding], list[ADRAuditResult]]:
    """Run all consistency checks."""
    findings: list[Finding] = []
    adr_results: list[ADRAuditResult] = []

    # Build full known ADR set (index + standalone)
    all_known = set(index.keys()) | set(standalone_files.keys())

    # Also add the README range (ADR-001~052 bulk entry)
    for i in range(1, 53):
        all_known.add(f"ADR-{i:03d}")

    # 1. Phantom references: ADR cited but not in index
    external_refs = [r for r in references if "08-附录" not in r.source_file]
    external_ref_ids = {r.adr_id for r in external_refs}

    phantoms = external_ref_ids - all_known
    for phantom_id in sorted(phantoms):
        examples = [r for r in external_refs if r.adr_id == phantom_id][:3]
        findings.append(
            Finding(
                severity="error",
                category="phantom",
                message=f"{phantom_id} referenced but not in ADR index",
                details={
                    "adr_id": phantom_id,
                    "example_refs": [{"file": e.source_file, "line": e.line_num} for e in examples],
                },
            )
        )

    # 2. Deprecated ADRs still referenced without caveat
    deprecated_ids = {adr_id for adr_id, entry in index.items() if entry.is_deprecated}
    for dep_id in sorted(deprecated_ids):
        active_refs = [
            r
            for r in external_refs
            if r.adr_id == dep_id and "废弃" not in r.context and "~~" not in r.context
        ]
        if active_refs:
            findings.append(
                Finding(
                    severity="warning",
                    category="deprecated_active",
                    message=(
                        f"{dep_id} is deprecated but referenced "
                        f"without caveat in {len(active_refs)} location(s)"
                    ),
                    details={
                        "adr_id": dep_id,
                        "superseded_by": index[dep_id].superseded_by,
                        "refs": [
                            {"file": r.source_file, "line": r.line_num} for r in active_refs[:5]
                        ],
                    },
                )
            )

    # 3. Broken amends chain
    for adr_id, entry in index.items():
        for amended_id in entry.amends:
            if amended_id not in all_known:
                findings.append(
                    Finding(
                        severity="error",
                        category="broken_amends",
                        message=f"{adr_id} amends {amended_id} but {amended_id} not found",
                        details={
                            "adr_id": adr_id,
                            "amends": amended_id,
                        },
                    )
                )

    # 4. Numbering gap detection
    if index:
        max_num = max(e.adr_num for e in index.values())
        known_nums = {e.adr_num for e in index.values()}
        for adr_id in standalone_files:
            m = RE_ADR_REF.search(adr_id)
            if m:
                known_nums.add(int(m.group(1)))
                max_num = max(max_num, int(m.group(1)))

        gaps = []
        for i in range(1, max_num + 1):
            if i not in known_nums:
                gaps.append(f"ADR-{i:03d}")

        if gaps:
            findings.append(
                Finding(
                    severity="info",
                    category="numbering_gap",
                    message=f"{len(gaps)} gap(s) in ADR numbering",
                    details={"gaps": gaps[:20]},
                )
            )

    # 5. Standalone files not in index
    for adr_id, file_path in standalone_files.items():
        if adr_id not in index:
            m = RE_ADR_REF.search(adr_id)
            if m and int(m.group(1)) <= 52:
                continue
            findings.append(
                Finding(
                    severity="info",
                    category="standalone_not_indexed",
                    message=f"{adr_id} has standalone file but not individually listed in index",
                    details={
                        "adr_id": adr_id,
                        "file": str(file_path),
                    },
                )
            )

    # 6. Build per-ADR audit results + linkage findings
    for adr_id in sorted(all_known):
        # Determine where it is defined
        if adr_id in index:
            defined_in = str(APPENDIX_DOC)
            status = "indexed"
        elif adr_id in standalone_files:
            defined_in = str(standalone_files[adr_id])
            status = "standalone"
        else:
            defined_in = "bulk-range"
            status = "indexed"

        # Check if ADR appears only outside the canonical index (orphaned)
        # ADR-040/041 appear in docs/reviews/ but not in 08-附录.md index
        if adr_id not in index:
            m = RE_ADR_REF.search(adr_id)
            if m:
                num = int(m.group(1))
                # If it's in the 1-52 range but NOT individually in the index,
                # check if it's referenced outside the main architecture docs
                if 1 <= num <= 52 and adr_id not in standalone_files:
                    # Collect all references to this ADR
                    all_refs_for_adr = [
                        r
                        for r in references
                        if r.adr_id == adr_id and "08-附录" not in r.source_file
                    ]
                    # Check if it has refs in architecture docs proper
                    arch_refs = [
                        r
                        for r in all_refs_for_adr
                        if r.source_file.startswith(str(ARCH_DIR))
                        or r.source_file.startswith(str(FE_ARCH_DIR))
                    ]
                    # Non-architecture refs (reviews, governance, etc.)
                    non_arch_refs = [
                        r
                        for r in all_refs_for_adr
                        if not r.source_file.startswith(str(ARCH_DIR))
                        and not r.source_file.startswith(str(FE_ARCH_DIR))
                    ]
                    # Orphaned: has refs somewhere but NOT in index AND NOT in arch docs
                    if non_arch_refs and not arch_refs:
                        status = "orphaned"
                        defined_in = non_arch_refs[0].source_file
                        findings.append(
                            Finding(
                                severity="warning",
                                category="orphaned",
                                message=(
                                    f"{adr_id} referenced outside architecture docs"
                                    " but not in 08-附录.md index"
                                ),
                                details={
                                    "adr_id": adr_id,
                                    "found_in": list({r.source_file for r in non_arch_refs}),
                                },
                            )
                        )

        tc_refs = task_card_refs.get(adr_id, [])
        g_refs = gate_refs.get(adr_id, [])
        t_refs = test_refs.get(adr_id, [])
        c_violations = code_violations.get(adr_id, [])

        result = ADRAuditResult(
            adr_id=adr_id,
            status=status,
            defined_in=defined_in,
            task_card_refs=tc_refs,
            gate_refs=g_refs,
            test_refs=t_refs,
            code_violations=c_violations,
        )
        adr_results.append(result)

        # Skip deprecated ADRs for coverage checks
        if adr_id in index and index[adr_id].is_deprecated:
            continue

        # 7. Zero-gate-coverage: not deprecated, has no gate ref
        if not g_refs:
            findings.append(
                Finding(
                    severity="warning",
                    category="zero_gate_coverage",
                    message=f"{adr_id} has no gate check in milestone-matrix",
                    details={"adr_id": adr_id},
                )
            )

        # 8. Code violations
        for violation in c_violations:
            findings.append(
                Finding(
                    severity="error",
                    category="code_violation",
                    message=f"{adr_id} code violation: {violation}",
                    details={"adr_id": adr_id, "violation": violation},
                )
            )

    return findings, adr_results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def generate_report(
    index: dict[str, ADREntry],
    standalone_files: dict[str, Path],
    references: list[ADRReference],
    findings: list[Finding],
    adr_results: list[ADRAuditResult],
    verbose: bool = False,
) -> dict:
    """Generate the audit report."""
    error_count = sum(1 for f in findings if f.severity == "error")
    warning_count = sum(1 for f in findings if f.severity == "warning")

    # Reference stats
    external_refs = [r for r in references if "08-附录" not in r.source_file]
    external_ref_ids = {r.adr_id for r in external_refs}

    # Coverage stats
    zero_gate = sum(1 for f in findings if f.category == "zero_gate_coverage")
    orphaned = sum(1 for f in findings if f.category == "orphaned")
    violation_count = sum(1 for f in findings if f.category == "code_violation")

    report: dict = {
        "status": "pass" if error_count == 0 else "fail",
        "summary": {
            "indexed_adrs": len(index),
            "standalone_files": len(standalone_files),
            "total_references": len(external_refs),
            "unique_adrs_referenced": len(external_ref_ids),
            "deprecated_count": sum(1 for e in index.values() if e.is_deprecated),
            "zero_gate_coverage": zero_gate,
            "orphaned_adrs": orphaned,
            "code_violations": violation_count,
            "errors": error_count,
            "warnings": warning_count,
        },
        "findings": [
            {
                "severity": f.severity,
                "category": f.category,
                "message": f.message,
                **({"details": f.details} if f.details else {}),
            }
            for f in findings
        ],
    }

    if verbose:
        report["adr_results"] = [
            {
                "adr_id": r.adr_id,
                "status": r.status,
                "defined_in": r.defined_in,
                "task_card_refs": r.task_card_refs,
                "gate_refs": r.gate_refs,
                "test_refs": r.test_refs,
                "code_violations": r.code_violations,
            }
            for r in adr_results
        ]

        report["index"] = {
            adr_id: {
                "title": e.title[:80],
                "version": e.version,
                "deprecated": e.is_deprecated,
                "superseded_by": e.superseded_by,
                "amends": e.amends,
            }
            for adr_id, e in sorted(index.items())
        }

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    use_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv

    # Parse sources
    index = parse_adr_index(APPENDIX_DOC)
    standalone_files = parse_standalone_adrs(ADR_DIR)
    references = find_adr_references(ARCH_DIR, FE_ARCH_DIR, ADR_DIR, REVIEWS_DIR, GOVERNANCE_DIR)

    # Parse linkage sources
    task_card_refs = find_task_card_adr_refs(TASK_CARD_DIR)
    gate_refs = find_gate_adr_refs(MILESTONE_MATRIX)
    test_refs = find_test_adr_refs(TEST_DIR)
    code_violations = check_code_violations(SRC_DIR)

    # Audit
    findings, adr_results = run_audit(
        index,
        standalone_files,
        references,
        task_card_refs,
        gate_refs,
        test_refs,
        code_violations,
    )

    # Report
    report = generate_report(
        index,
        standalone_files,
        references,
        findings,
        adr_results,
        verbose,
    )

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print(f"ADR Consistency: {s['indexed_adrs']} indexed ADRs")
        print(f"  Standalone files: {s['standalone_files']}")
        print(f"  References found: {s['total_references']} ({s['unique_adrs_referenced']} unique)")
        print(f"  Deprecated: {s['deprecated_count']}")
        print(f"  Zero gate coverage: {s['zero_gate_coverage']}")
        print(f"  Orphaned ADRs: {s['orphaned_adrs']}")
        print(f"  Code violations: {s['code_violations']}")
        print(f"  Errors: {s['errors']}, Warnings: {s['warnings']}")

        if findings:
            print("\nFindings:")
            for f in findings:
                icon = {"error": "E", "warning": "W", "info": "I"}[f.severity]
                print(f"  [{icon}] {f.message}")

    sys.exit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
