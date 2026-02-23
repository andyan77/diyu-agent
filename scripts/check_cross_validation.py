#!/usr/bin/env python3
"""Cross-Validation Diagnostic Script.

Detects disconnections between gate scripts, task cards, milestone matrix,
and design docs -- each self-certifying without cross-verification.

8-Category Diagnostic:
  1. Gate Coverage: Are "done" milestones covered by exit_criteria?
  2. Acceptance Execution: Do task card acceptance commands actually run?
  3. Gate-vs-Acceptance Consistency: Do gate and acceptance point to same things?
  4. Architecture Boundary: AST-based layer import validation (extends check_layer_deps.sh)
  5. Design Claim Audit: Are architecture promises verified by any gate/test?
  6. Call Graph: Do business layers import infra directly? (should use Ports)
  7. Stub Detection: AST scan for pass-only bodies, NotImplementedError, TODO/FIXME
  8. LLM Call Verification: Do business layers import LLM libraries directly?

Usage:
    python scripts/check_cross_validation.py --json
    python scripts/check_cross_validation.py --skip-execution --json
    python scripts/check_cross_validation.py --json --archive

Exit codes:
    0: PASS or WARN (informational only)
    1: FAIL (critical findings)
    2: Configuration error
"""

from __future__ import annotations

import ast
import json
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UTC = timezone.utc  # noqa: UP017 -- compat with Python <3.11 runtime

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")
TASK_CARDS_DIR = Path("docs/task-cards")
SRC_DIR = Path("src")
EVIDENCE_DIR = Path("evidence/cross-validation")

# Reuse regex patterns compatible with existing scripts
FILE_PATH_RE = re.compile(r"(?:^|\s)((?:tests|scripts|frontend/tests|src)/\S+\.(?:py|ts|sh|mjs))")
TASK_HEADING_RE = re.compile(r"^###\s+(TASK-\S+)")
MATRIX_REF_RE = re.compile(r">\s*(?:矩阵条目|[Mm]atrix\s*\S*?):\s*(\S+)")
GATE_REF_RE = re.compile(r">\s*Gate:\s*(.+)")
ACCEPTANCE_RE = re.compile(r"\|\s*\*{0,2}验收命令\*{0,2}\s*\|\s*(.+?)\s*\|", re.IGNORECASE)
BACKTICK_CMD_RE = re.compile(r"`([^`]+)`")

# Tags that mark non-executable acceptance commands
SKIP_TAGS = {"[ENV-DEP]", "[MANUAL-VERIFY]", "[E2E]"}

# Shell meta chars that require shell=True
_CD_PREFIX_RE = re.compile(r"^cd\s+(\S+)\s*&&\s*(.+)$")
_SHELL_META_RE = re.compile(r"[|&;$`<>]")

# ---------------------------------------------------------------------------
# Layer rules for Check 4 (AST-based)
# ---------------------------------------------------------------------------

# Maps: layer_name -> set of forbidden import prefixes
# Extends check_layer_deps.sh with memory/ and infra/ rules + privacy boundary
LAYER_RULES: dict[str, set[str]] = {
    "brain": {"src.infra", "src.gateway", "src.tool"},
    "knowledge": {"src.infra", "src.gateway", "src.brain", "src.memory"},
    "skill": {"src.infra", "src.gateway"},
    "tool": {"src.infra", "src.brain", "src.knowledge"},
    "gateway": {"src.brain", "src.knowledge", "src.skill"},
    "memory": {"src.infra", "src.gateway", "src.tool", "src.skill"},
    "infra": {"src.brain", "src.knowledge", "src.skill", "src.tool"},
    "shared": {
        "src.brain",
        "src.gateway",
        "src.knowledge",
        "src.memory",
        "src.skill",
        "src.tool",
        "src.infra",
    },
}

# Privacy boundary: knowledge cannot import src.memory (dual-SSOT hard boundary)
PRIVACY_BOUNDARY = ("knowledge", "src.memory")

# ---------------------------------------------------------------------------
# Design claims for Check 5
# ---------------------------------------------------------------------------

DESIGN_CLAIMS: list[dict[str, str]] = [
    # --- Original DC-1~8 (source paths corrected) ---
    {
        "id": "DC-1",
        "claim": "Dual-SSOT: Memory Core (hard dep) + Knowledge Stores (soft dep)",
        "source": "docs/architecture/00-系统定位与架构总览.md",
        "risk": "HIGH",
        "verification_pattern": r"memory.*core|dual.?ssot|hard.?dep",
    },
    {
        "id": "DC-2",
        "claim": "RLS org_id isolation on all tenant tables",
        "source": "docs/architecture/06-基础设施层.md",
        "risk": "HIGH",
        "verification_pattern": r"rls|row.?level|org_id.*isol",
    },
    {
        "id": "DC-3",
        "claim": (
            "6 Day-1 Ports: MemoryCorePort, KnowledgePort, LLMCallPort,"
            " SkillRegistry, OrgContext, StoragePort"
        ),
        "source": "docs/architecture/00-系统定位与架构总览.md",
        "risk": "MEDIUM",
        "verification_pattern": r"port.*compat|check_port",
    },
    {
        "id": "DC-4",
        "claim": "Circuit breaker + degradation matrix + provider fallback (LLM)",
        "source": "docs/architecture/01-对话Agent层-Brain.md",
        "risk": "HIGH",
        "verification_pattern": r"circuit.?break|fallback|degradat",
    },
    {
        "id": "DC-5",
        "claim": "Transactional outbox for event delivery (Level 1 events)",
        "source": "docs/architecture/06-基础设施层.md",
        "risk": "MEDIUM",
        "verification_pattern": r"outbox|event.*deliver",
    },
    {
        "id": "DC-6",
        "claim": "Media upload: S3 presigned + ClamAV scan + EXIF strip",
        "source": "docs/architecture/05-Gateway层.md",
        "risk": "HIGH",
        "verification_pattern": r"clamav|exif|presign|media.*safe",
    },
    {
        "id": "DC-7",
        "claim": "Performance SLI: Context assembly P95 < 200ms",
        "source": "docs/architecture/01-对话Agent层-Brain.md",
        "risk": "MEDIUM",
        "verification_pattern": r"p95|assembl.*latenc|perf.*baseline",
    },
    {
        "id": "DC-8",
        "claim": "No cross-layer imports bypassing Ports",
        "source": "CLAUDE.md",
        "risk": "HIGH",
        "verification_pattern": r"layer.*dep|check_layer|import.*violat",
    },
    # --- DC-9~28: Expanded claims (aligned with guardian-system-completion-plan-v1.0.md §4 B3) ---
    {
        "id": "DC-9",
        "claim": (
            "Privacy hard boundary: Knowledge never imports src.memory;"
            " Context Assembler is the ONLY reader of both SSOT-A and SSOT-B (ADR-018)"
        ),
        "source": "docs/architecture/01-对话Agent层-Brain.md",
        "risk": "HIGH",
        "verification_pattern": r"context.*assembler|privacy.*hard.*boundary|adr.?018",
    },
    {
        "id": "DC-10",
        "claim": "Provenance confidence 3 tiers: observation(0.6)/analysis(0.8)/confirmed(1.0)",
        "source": "docs/architecture/01-对话Agent层-Brain.md",
        "risk": "MEDIUM",
        "verification_pattern": r"provenance|observation.*0\.6|confirmed.*1\.0",
    },
    {
        "id": "DC-11",
        "claim": "Memory items versioned: version + valid_from/valid_to + superseded_by",
        "source": "docs/architecture/01-对话Agent层-Brain.md",
        "risk": "MEDIUM",
        "verification_pattern": r"memory.*version|superseded_by|valid_from",
    },
    {
        "id": "DC-12",
        "claim": (
            "security_status 6-state: pending/scanning/safe/rejected/quarantined/expired (ADR-051)"
        ),
        "source": "docs/architecture/05-Gateway层.md",
        "risk": "HIGH",
        "verification_pattern": r"security_status|quarantined|adr.?051",
    },
    {
        "id": "DC-13",
        "claim": "Token budget + Tool budget dual-dimension pre-check (Loop D)",
        "source": "docs/architecture/05-Gateway层.md",
        "risk": "MEDIUM",
        "verification_pattern": r"budget_tool|token.*budget|loop.?d|pre.?check",
    },
    {
        "id": "DC-14",
        "claim": "PIPL/GDPR deletion: legal_profiles table with configurable deletion_sla",
        "source": "docs/architecture/06-基础设施层.md",
        "risk": "HIGH",
        "verification_pattern": r"legal_profiles|deletion_sla|pipl|gdpr",
    },
    {
        "id": "DC-15",
        "claim": "Three-step upload: init -> S3 direct upload -> complete (ADR-045)",
        "source": "docs/architecture/05-Gateway层.md",
        "risk": "HIGH",
        "verification_pattern": r"three.*step.*upload|init.*complete|adr.?045",
    },
    {
        "id": "DC-16",
        "claim": "LAW/RULE/BRIDGE constraint classification for org settings (ADR-029)",
        "source": "docs/architecture/06-基础设施层.md",
        "risk": "HIGH",
        "verification_pattern": r"law.*rule.*bridge|is_locked|adr.?029",
    },
    {
        "id": "DC-17",
        "claim": "Skill pluggability: Brain must work without any Skills (ADR-016)",
        "source": "docs/architecture/03-Skill层.md",
        "risk": "MEDIUM",
        "verification_pattern": r"skill.*plug|brain.*without.*skill|adr.?016",
    },
    {
        "id": "DC-18",
        "claim": "Checksum: MUST use S3 x-amz-checksum-sha256, NOT ETag (ADR-052, LAW)",
        "source": "docs/architecture/05-Gateway层.md",
        "risk": "HIGH",
        "verification_pattern": r"checksum.*sha256|x.amz.checksum|adr.?052",
    },
    {
        "id": "DC-19",
        "claim": "FK linkage: Neo4j graph_node_id <-> Qdrant point_id with sync_status (ADR-024)",
        "source": "docs/architecture/02-Knowledge层.md",
        "risk": "HIGH",
        "verification_pattern": r"fk.*registr|graph_node_id|sync_status|reconcil",
    },
    {
        "id": "DC-20",
        "claim": "Three-layer version separation: DB/WS/event (ADR-050)",
        "source": "docs/architecture/08-附录.md",
        "risk": "MEDIUM",
        "verification_pattern": r"three.*layer.*version|db.*ws.*event|adr.?050",
    },
    {
        "id": "DC-21",
        "claim": "Hybrid Retrieval: pgvector + FTS -> RRF fusion (ADR-042)",
        "source": "docs/architecture/01-对话Agent层-Brain.md",
        "risk": "MEDIUM",
        "verification_pattern": r"hybrid.*retrieval|rrf|adr.?042",
    },
    {
        "id": "DC-22",
        "claim": "Deletion pipeline 8-state state machine (ADR-039)",
        "source": "docs/architecture/01-对话Agent层-Brain.md",
        "risk": "HIGH",
        "verification_pattern": r"tombstone|deletion.*state|adr.?039",
    },
    {
        "id": "DC-23",
        "claim": "ContentBlock Schema v1.1: text_fallback mandatory (ADR-043)",
        "source": "docs/architecture/08-附录.md",
        "risk": "MEDIUM",
        "verification_pattern": r"contentblock|text_fallback|adr.?043",
    },
    {
        "id": "DC-24",
        "claim": "7 unified SLI for Brain+Memory (ADR-038)",
        "source": "docs/architecture/01-对话Agent层-Brain.md",
        "risk": "MEDIUM",
        "verification_pattern": r"7.*sli|staleness_rate|adr.?038",
    },
    {
        "id": "DC-25",
        "claim": (
            "Deletion domain separation: personal->tombstone(SSOT-A), enterprise->ChangeSet(SSOT-B)"
            " (ADR-044)"
        ),
        "source": "docs/architecture/06-基础设施层.md",
        "risk": "HIGH",
        "verification_pattern": r"personal.*tombstone|enterprise.*changeset|adr.?044",
    },
    {
        "id": "DC-26",
        "claim": "JWT auth + RBAC with 5 fixed roles (owner/admin/editor/reviewer/viewer)",
        "source": "docs/architecture/05-Gateway层.md",
        "risk": "HIGH",
        "verification_pattern": r"jwt.*auth|rbac|role.*(owner|admin|editor|reviewer|viewer)",
    },
    {
        "id": "DC-27",
        "claim": "Organization tree max depth 5 layers (LAW constraint)",
        "source": "docs/architecture/06-基础设施层.md",
        "risk": "HIGH",
        "verification_pattern": r"org.*tree.*5|max.*depth.*5|tier.*5",
    },
    {
        "id": "DC-28",
        "claim": (
            "Memory Core HA: RPO<1s, RTO<30s, Knowledge precedence:"
            " enterprise rules > personal preferences (ADR-022, ADR-027)"
        ),
        "source": "docs/architecture/07-部署与安全.md",
        "risk": "HIGH",
        "verification_pattern": r"rpo.*1s|rto.*30s|patroni|adr.?027|enterprise.*personal|adr.?022",
    },
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ValidationContext:
    """Shared context for all checks."""

    matrix: dict = field(default_factory=dict)
    phases: dict = field(default_factory=dict)
    task_cards: list[dict] = field(default_factory=list)
    skip_execution: bool = False


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""

    name: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.data


# ---------------------------------------------------------------------------
# Data loading (reuses patterns from existing scripts)
# ---------------------------------------------------------------------------


def load_matrix() -> dict:
    """Load milestone-matrix.yaml."""
    if not MATRIX_PATH.exists():
        print(f"ERROR: {MATRIX_PATH} not found", file=sys.stderr)
        sys.exit(2)
    with open(MATRIX_PATH) as f:
        return yaml.safe_load(f)


def get_done_milestones(matrix: dict) -> list[dict]:
    """Extract all milestones with status='done' across all phases."""
    done = []
    for phase_key, phase_data in matrix.get("phases", {}).items():
        if not isinstance(phase_data, dict):
            continue
        for ms in phase_data.get("milestones", []):
            if ms.get("status") == "done":
                done.append({**ms, "_phase": phase_key})
    return done


def get_exit_criteria(matrix: dict) -> list[dict]:
    """Extract all exit_criteria (hard + soft) across all phases."""
    criteria = []
    for phase_key, phase_data in matrix.get("phases", {}).items():
        if not isinstance(phase_data, dict):
            continue
        ec = phase_data.get("exit_criteria", {})
        for tier in ("hard", "soft"):
            for crit in ec.get(tier, []):
                criteria.append({**crit, "_phase": phase_key, "_tier": tier})
    return criteria


def parse_task_cards(*, task_cards_dir: Path | None = None) -> list[dict]:
    """Parse task cards from docs/task-cards/, extracting key fields."""
    effective_dir = task_cards_dir if task_cards_dir is not None else TASK_CARDS_DIR
    cards: list[dict] = []
    if not effective_dir.exists():
        return cards

    for md_file in sorted(effective_dir.rglob("*.md")):
        lines = md_file.read_text(encoding="utf-8").splitlines()
        current_task: dict | None = None

        for i, line in enumerate(lines):
            # Detect task heading
            m = TASK_HEADING_RE.match(line)
            if m:
                if current_task:
                    cards.append(current_task)
                current_task = {
                    "task_id": m.group(1).rstrip(":"),
                    "file": str(md_file),
                    "line": i + 1,
                    "matrix_refs": [],
                    "gate_refs": [],
                    "acceptance": "",
                }
                continue

            if current_task is None:
                continue

            # Matrix reference
            m = MATRIX_REF_RE.match(line)
            if m:
                current_task["matrix_refs"].append(m.group(1))

            # Gate reference
            m = GATE_REF_RE.match(line)
            if m:
                for g in m.group(1).split(","):
                    g = g.strip()
                    if g:
                        current_task["gate_refs"].append(g)

            # Acceptance command
            m = ACCEPTANCE_RE.search(line)
            if m:
                current_task["acceptance"] = m.group(1).strip()

        if current_task:
            cards.append(current_task)

    return cards


# ---------------------------------------------------------------------------
# Command execution helpers (adapted from verify_phase.py)
# ---------------------------------------------------------------------------


def _needs_shell(cmd: str) -> bool:
    return bool(_SHELL_META_RE.search(cmd))


def _run_check(check_cmd: str, timeout: int = 120) -> dict:
    """Execute a single check command, return {status, duration_ms, error?}."""
    start = time.monotonic()
    try:
        cmd = check_cmd.strip()
        cwd = Path.cwd()
        use_shell = _needs_shell(cmd)

        m = _CD_PREFIX_RE.match(cmd)
        if m:
            cwd = Path.cwd() / m.group(1)
            cmd = m.group(2).strip()
            use_shell = _needs_shell(cmd)

        args: list[str] | str = cmd if use_shell else shlex.split(cmd)
        result = subprocess.run(  # noqa: S603
            args,
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        if result.returncode == 0:
            return {"status": "PASS", "duration_ms": duration_ms}
        return {
            "status": "FAIL",
            "duration_ms": duration_ms,
            "error": (
                result.stderr.strip() or result.stdout.strip()[:200] or f"exit {result.returncode}"
            ),
        }
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {"status": "TIMEOUT", "duration_ms": duration_ms, "error": "timeout"}
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {"status": "ERROR", "duration_ms": duration_ms, "error": str(e)}


# ---------------------------------------------------------------------------
# Check 1: Gate Coverage
# ---------------------------------------------------------------------------


def check_gate_coverage(ctx: ValidationContext) -> CheckResult:
    """For each 'done' milestone, check if any exit_criteria covers it."""
    done_milestones = get_done_milestones(ctx.matrix)
    all_criteria = get_exit_criteria(ctx.matrix)

    # Build a set of milestone IDs that are referenced by exit criteria
    # Heuristic: criterion description or check command references the milestone ID,
    # or the criterion is in the same phase and references the milestone's layer/test path
    covered_ids: set[str] = set()

    # Build lookup: phase -> set of criterion check paths
    phase_criteria_paths: dict[str, set[str]] = {}
    phase_criterion_descs: dict[str, list[str]] = {}
    for crit in all_criteria:
        phase = crit["_phase"]
        phase_criteria_paths.setdefault(phase, set())
        phase_criterion_descs.setdefault(phase, [])
        check_cmd = crit.get("check", "")
        desc = crit.get("description", "")
        phase_criterion_descs[phase].append(desc.lower())
        # Extract file paths from check command
        for match in FILE_PATH_RE.finditer(check_cmd):
            phase_criteria_paths[phase].add(match.group(1))

    # Layer name -> test directory mapping heuristic
    layer_test_dirs = {
        "Brain": "tests/unit/brain/",
        "MemoryCore": "tests/unit/memory/",
        "Knowledge": "tests/unit/knowledge/",
        "Skill": "tests/unit/skill/",
        "Tool": "tests/unit/tool/",
        "Gateway": "tests/unit/gateway/",
        "Infrastructure": "tests/unit/infra/",
    }

    uncovered: list[dict] = []
    for ms in done_milestones:
        ms_id = ms["id"]
        phase = ms["_phase"]
        layer = ms.get("layer", "")

        # Direct ID match in descriptions
        descs = phase_criterion_descs.get(phase, [])
        if any(ms_id.lower() in d for d in descs):
            covered_ids.add(ms_id)
            continue

        # Layer-level heuristic: if any criterion tests files in the layer's test dir
        test_dir = layer_test_dirs.get(layer, "")
        paths = phase_criteria_paths.get(phase, set())
        if test_dir and any(p.startswith(test_dir) for p in paths):
            covered_ids.add(ms_id)
            continue

        # Check if the summary keywords appear in criterion descriptions
        summary_words = ms.get("summary", "").lower().split()
        significant_words = [w for w in summary_words if len(w) > 3]
        if significant_words and any(all(w in d for w in significant_words[:2]) for d in descs):
            covered_ids.add(ms_id)
            continue

        uncovered.append(
            {"id": ms_id, "phase": phase, "layer": layer, "summary": ms.get("summary", "")}
        )

    total = len(done_milestones)
    covered_count = total - len(uncovered)
    coverage_rate = covered_count / total if total > 0 else 1.0

    return CheckResult(
        name="gate_coverage",
        data={
            "total_done_milestones": total,
            "covered": covered_count,
            "uncovered": uncovered,
            "coverage_rate": round(coverage_rate, 4),
        },
    )


# ---------------------------------------------------------------------------
# Check 2: Acceptance Command Execution
# ---------------------------------------------------------------------------


def _extract_command(acceptance: str) -> str | None:
    """Extract executable command from acceptance field."""
    if not acceptance:
        return None

    # Skip tagged commands
    for tag in SKIP_TAGS:
        if tag in acceptance:
            return None

    # Extract from backticks
    m = BACKTICK_CMD_RE.search(acceptance)
    if m:
        return m.group(1).strip()

    # If no backticks, check if the whole string looks like a command
    if acceptance.startswith(("uv ", "pytest ", "bash ", "make ", "cd ", "python ")):
        return acceptance.strip()

    return None


def check_acceptance_execution(ctx: ValidationContext) -> CheckResult:
    """Extract and execute acceptance commands from task cards."""
    results: list[dict] = []
    executed = 0
    passed = 0
    failed = 0
    skipped = 0

    for card in ctx.task_cards:
        task_id = card["task_id"]
        acceptance = card.get("acceptance", "")

        cmd = _extract_command(acceptance)
        if cmd is None:
            skip_reason = "no_command"
            for tag in SKIP_TAGS:
                if tag in acceptance:
                    skip_reason = tag
                    break
            if not acceptance:
                skip_reason = "empty"
            results.append({"task_id": task_id, "status": "SKIP", "reason": skip_reason})
            skipped += 1
            continue

        if ctx.skip_execution:
            results.append(
                {"task_id": task_id, "status": "SKIP", "reason": "skip-execution", "command": cmd}
            )
            skipped += 1
            continue

        # Execute
        run_result = _run_check(cmd, timeout=120)
        entry = {
            "task_id": task_id,
            "status": run_result["status"],
            "command": cmd,
            "duration_ms": run_result["duration_ms"],
        }
        if run_result.get("error"):
            entry["error"] = run_result["error"]

        results.append(entry)
        executed += 1
        if run_result["status"] == "PASS":
            passed += 1
        else:
            failed += 1

    return CheckResult(
        name="acceptance_execution",
        data={
            "total": len(ctx.task_cards),
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "results": results,
        },
    )


# ---------------------------------------------------------------------------
# Check 3: Gate-vs-Acceptance Consistency
# ---------------------------------------------------------------------------


def check_consistency(ctx: ValidationContext) -> CheckResult:
    """Compare gate check and acceptance command file paths for the same milestone."""
    all_criteria = get_exit_criteria(ctx.matrix)

    # Build gate_id -> file paths
    gate_paths: dict[str, set[str]] = {}
    for crit in all_criteria:
        cid = crit.get("id", "")
        check_cmd = crit.get("check", "")
        paths = set()
        for m in FILE_PATH_RE.finditer(check_cmd):
            paths.add(m.group(1))
        if paths:
            gate_paths[cid] = paths

    # Build task card gate_ref -> acceptance file paths
    card_paths: dict[str, set[str]] = {}
    for card in ctx.task_cards:
        acceptance = card.get("acceptance", "")
        cmd = _extract_command(acceptance)
        if not cmd:
            continue
        paths = set()
        for m in FILE_PATH_RE.finditer(cmd):
            paths.add(m.group(1))
        if not paths:
            continue
        for gref in card.get("gate_refs", []):
            card_paths.setdefault(gref, set()).update(paths)

    # Find comparable pairs (both have file paths)
    comparable_gates = set(gate_paths.keys()) & set(card_paths.keys())
    mismatches: list[dict] = []
    consistent = 0

    for gate_id in sorted(comparable_gates):
        gp = gate_paths[gate_id]
        cp = card_paths[gate_id]
        if gp == cp:
            consistent += 1
        elif gp & cp:
            # Partial overlap
            consistent += 1
        else:
            mismatches.append(
                {
                    "gate_id": gate_id,
                    "gate_paths": sorted(gp),
                    "card_paths": sorted(cp),
                }
            )

    return CheckResult(
        name="consistency",
        data={
            "total_comparable": len(comparable_gates),
            "consistent": consistent,
            "mismatched": mismatches,
        },
    )


# ---------------------------------------------------------------------------
# Check 4: Architecture Boundary (AST-based)
# ---------------------------------------------------------------------------


def _extract_imports(filepath: Path) -> list[tuple[str, int]]:
    """Parse Python file via AST and extract all import module paths.

    Returns list of (module_path, line_number).
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))
    return imports


def check_architecture_boundary(
    ctx: ValidationContext, *, src_dir: Path | None = None
) -> CheckResult:
    """AST-based layer import validation, extending check_layer_deps.sh."""
    effective_src = src_dir if src_dir is not None else SRC_DIR
    violations: list[dict] = []
    layers_checked: list[str] = []
    privacy_intact = True

    if not effective_src.exists():
        return CheckResult(
            name="architecture_boundary",
            data={
                "violations": [],
                "layers_checked": [],
                "privacy_boundary_intact": True,
                "note": "src/ not found",
            },
        )

    for layer_name, forbidden_prefixes in LAYER_RULES.items():
        layer_dir = effective_src / layer_name
        if not layer_dir.exists():
            continue
        layers_checked.append(layer_name)

        for py_file in layer_dir.rglob("*.py"):
            imports = _extract_imports(py_file)
            for module_path, lineno in imports:
                for forbidden in forbidden_prefixes:
                    if module_path.startswith(forbidden):
                        violation = {
                            "file": str(py_file),
                            "line": lineno,
                            "layer": layer_name,
                            "import": module_path,
                            "forbidden_prefix": forbidden,
                        }
                        violations.append(violation)

                        # Check privacy boundary specifically
                        if (layer_name, forbidden) == PRIVACY_BOUNDARY:
                            privacy_intact = False

    return CheckResult(
        name="architecture_boundary",
        data={
            "violations": violations,
            "layers_checked": sorted(layers_checked),
            "privacy_boundary_intact": privacy_intact,
        },
    )


# ---------------------------------------------------------------------------
# Check 5: Design Claim Audit
# ---------------------------------------------------------------------------


def check_design_claims(ctx: ValidationContext) -> CheckResult:
    """Check if design claims have any gate/test verification."""
    all_criteria = get_exit_criteria(ctx.matrix)

    # Collect all check commands and descriptions for matching
    all_checks_text = ""
    for crit in all_criteria:
        all_checks_text += " " + crit.get("check", "")
        all_checks_text += " " + crit.get("description", "")
    all_checks_text = all_checks_text.lower()

    # Also scan test file names for additional coverage signals
    test_files: list[str] = []
    for test_dir in (Path("tests"), Path("frontend/tests")):
        if test_dir.exists():
            test_files.extend(str(f) for f in test_dir.rglob("*test*"))

    test_files_text = " ".join(test_files).lower()

    verified: list[dict] = []
    unverified: list[dict] = []

    for claim in DESIGN_CLAIMS:
        pattern = re.compile(claim["verification_pattern"], re.IGNORECASE)
        found_in_gates = bool(pattern.search(all_checks_text))
        found_in_tests = bool(pattern.search(test_files_text))

        entry = {
            "id": claim["id"],
            "claim": claim["claim"],
            "source": claim["source"],
            "risk": claim["risk"],
            "gate_verified": found_in_gates,
            "test_verified": found_in_tests,
        }

        if found_in_gates or found_in_tests:
            verified.append(entry)
        else:
            unverified.append(entry)

    return CheckResult(
        name="design_claims",
        data={
            "total_claims": len(DESIGN_CLAIMS),
            "verified": len(verified),
            "unverified": unverified,
            "verified_details": verified,
        },
    )


# ---------------------------------------------------------------------------
# Check 6: Call Graph Verification
# ---------------------------------------------------------------------------


# Infra module prefixes that should NOT be directly imported by business layers
_INFRA_DIRECT_IMPORTS = {
    "src.infra.db",
    "src.infra.cache",
    "src.infra.storage",
    "src.infra.vector",
    "src.infra.graph",
    "src.infra.events",
    "src.infra.tasks",
}

# Layers that MUST use Ports, never direct infra imports
_PORT_REQUIRED_LAYERS = {"brain", "knowledge", "skill"}


def check_call_graph(
    ctx: ValidationContext,
    *,
    src_dir: Path | None = None,
) -> CheckResult:
    """Verify business layers call infra through Port interfaces, not directly."""
    effective_src = src_dir if src_dir is not None else SRC_DIR
    violations: list[dict] = []

    if not effective_src.exists():
        return CheckResult(
            name="call_graph",
            data={"violations": [], "layers_checked": [], "note": "src/ not found"},
        )

    layers_checked: list[str] = []
    for layer_name in _PORT_REQUIRED_LAYERS:
        layer_dir = effective_src / layer_name
        if not layer_dir.exists():
            continue
        layers_checked.append(layer_name)

        for py_file in layer_dir.rglob("*.py"):
            imports = _extract_imports(py_file)
            for module_path, lineno in imports:
                for infra_prefix in _INFRA_DIRECT_IMPORTS:
                    if module_path.startswith(infra_prefix):
                        violations.append(
                            {
                                "file": str(py_file),
                                "line": lineno,
                                "layer": layer_name,
                                "import": module_path,
                                "infra_module": infra_prefix,
                                "recommendation": "Use Port interface instead"
                                " of direct infra import",
                            }
                        )

    return CheckResult(
        name="call_graph",
        data={
            "violations": violations,
            "layers_checked": sorted(layers_checked),
        },
    )


# ---------------------------------------------------------------------------
# Check 7: Stub Detection
# ---------------------------------------------------------------------------

# Patterns indicating stub/placeholder code
_STUB_AST_PATTERNS = {
    "pass_body",  # function/method with only `pass`
    "not_implemented",  # raise NotImplementedError
}

_COMMENT_STUB_RE = re.compile(
    r"#\s*(?:TODO|FIXME|HACK|Placeholder|STUB)\b",
    re.IGNORECASE,
)


def check_stub_detection(
    ctx: ValidationContext,
    *,
    src_dir: Path | None = None,
) -> CheckResult:
    """AST scan production code for stub/placeholder patterns."""
    effective_src = src_dir if src_dir is not None else SRC_DIR
    stubs: list[dict] = []

    if not effective_src.exists():
        return CheckResult(
            name="stub_detection",
            data={"stubs": [], "total_stubs": 0, "total_files_scanned": 0},
        )

    files_scanned = 0
    for layer_name in LAYER_RULES:
        layer_dir = effective_src / layer_name
        if not layer_dir.exists():
            continue

        for py_file in layer_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            files_scanned += 1

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            # AST checks: pass-only bodies and NotImplementedError
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body = node.body
                    # pass-only body (excluding docstrings)
                    non_doc = [
                        n
                        for n in body
                        if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
                    ]
                    if len(non_doc) == 1 and isinstance(non_doc[0], ast.Pass):
                        stubs.append(
                            {
                                "file": str(py_file),
                                "line": node.lineno,
                                "name": node.name,
                                "type": "pass_body",
                                "layer": layer_name,
                            }
                        )

                    # raise NotImplementedError
                    for child in body:
                        if (
                            isinstance(child, ast.Raise)
                            and child.exc
                            and isinstance(child.exc, ast.Call)
                            and isinstance(child.exc.func, ast.Name)
                            and child.exc.func.id == "NotImplementedError"
                        ):
                            stubs.append(
                                {
                                    "file": str(py_file),
                                    "line": child.lineno,
                                    "name": node.name,
                                    "type": "not_implemented",
                                    "layer": layer_name,
                                }
                            )

            # Comment-based stubs
            lines = source.splitlines()
            for i, line in enumerate(lines, 1):
                if _COMMENT_STUB_RE.search(line):
                    stubs.append(
                        {
                            "file": str(py_file),
                            "line": i,
                            "name": line.strip()[:60],
                            "type": "comment_stub",
                            "layer": layer_name,
                        }
                    )

    return CheckResult(
        name="stub_detection",
        data={
            "stubs": stubs,
            "total_stubs": len(stubs),
            "total_files_scanned": files_scanned,
        },
    )


# ---------------------------------------------------------------------------
# Check 8: LLM Call Verification
# ---------------------------------------------------------------------------

# Direct LLM library imports that should NOT appear in business layers
_LLM_DIRECT_IMPORTS = {
    "openai",
    "anthropic",
    "litellm",
    "httpx",
}

# Only brain/knowledge/skill layers are checked (tool layer legitimately wraps LLM)
_LLM_CHECK_LAYERS = {"brain", "knowledge", "skill"}


def check_llm_calls(
    ctx: ValidationContext,
    *,
    src_dir: Path | None = None,
) -> CheckResult:
    """Verify all LLM calls go through LLMCallPort, not direct imports."""
    effective_src = src_dir if src_dir is not None else SRC_DIR
    violations: list[dict] = []

    if not effective_src.exists():
        return CheckResult(
            name="llm_call_verification",
            data={"violations": [], "layers_checked": []},
        )

    layers_checked: list[str] = []
    for layer_name in _LLM_CHECK_LAYERS:
        layer_dir = effective_src / layer_name
        if not layer_dir.exists():
            continue
        layers_checked.append(layer_name)

        for py_file in layer_dir.rglob("*.py"):
            imports = _extract_imports(py_file)
            for module_path, lineno in imports:
                # Check top-level module
                top_module = module_path.split(".")[0]
                if top_module in _LLM_DIRECT_IMPORTS:
                    violations.append(
                        {
                            "file": str(py_file),
                            "line": lineno,
                            "layer": layer_name,
                            "import": module_path,
                            "recommendation": "Use LLMCallPort instead"
                            " of direct LLM library import",
                        }
                    )

    return CheckResult(
        name="llm_call_verification",
        data={
            "violations": violations,
            "layers_checked": sorted(layers_checked),
        },
    )


# ---------------------------------------------------------------------------
# Report Assembly
# ---------------------------------------------------------------------------


def determine_status(checks: dict[str, dict]) -> tuple[str, int, list[str]]:
    """Determine overall status and count critical findings."""
    critical = 0
    recommendations: list[str] = []

    # Gate coverage < 50% is critical
    gc = checks.get("gate_coverage", {})
    coverage_rate = gc.get("coverage_rate", 1.0)
    if coverage_rate < 0.5:
        critical += 1
        recommendations.append(
            f"Gate coverage is {coverage_rate:.0%}"
            " -- add exit_criteria for uncovered done milestones"
        )
    elif coverage_rate < 0.8:
        recommendations.append(
            f"Gate coverage is {coverage_rate:.0%} -- consider improving coverage"
        )

    # Architecture violations are critical
    ab = checks.get("architecture_boundary", {})
    violations = ab.get("violations", [])
    if violations:
        critical += len(violations)
        recommendations.append(f"{len(violations)} architecture boundary violation(s) detected")
    if not ab.get("privacy_boundary_intact", True):
        critical += 1
        recommendations.append("Privacy boundary violated: knowledge imports memory")

    # Failed acceptance commands
    ae = checks.get("acceptance_execution", {})
    if ae.get("failed", 0) > 0:
        recommendations.append(f"{ae['failed']} acceptance command(s) failed execution")

    # Unverified HIGH-risk claims are critical
    dc = checks.get("design_claims", {})
    for claim in dc.get("unverified", []):
        if claim.get("risk") == "HIGH":
            critical += 1
    unverified_high = sum(1 for c in dc.get("unverified", []) if c.get("risk") == "HIGH")
    if unverified_high:
        recommendations.append(f"{unverified_high} HIGH-risk design claim(s) have no verification")

    # Consistency mismatches
    con = checks.get("consistency", {})
    if con.get("mismatched"):
        recommendations.append(f"{len(con['mismatched'])} gate-vs-acceptance path mismatch(es)")

    # Call graph violations (direct infra imports from business layers)
    cg = checks.get("call_graph", {})
    cg_violations = cg.get("violations", [])
    if cg_violations:
        critical += len(cg_violations)
        recommendations.append(
            f"{len(cg_violations)} call-graph violation(s): business layer imports infra directly"
        )

    # Stub detection (informational, not critical)
    sd = checks.get("stub_detection", {})
    total_stubs = sd.get("total_stubs", 0)
    if total_stubs > 0:
        recommendations.append(f"{total_stubs} stub(s)/placeholder(s) detected in production code")

    # LLM call violations (direct LLM library imports)
    lc = checks.get("llm_call_verification", {})
    lc_violations = lc.get("violations", [])
    if lc_violations:
        critical += len(lc_violations)
        recommendations.append(
            f"{len(lc_violations)} direct LLM library import(s) bypassing LLMCallPort"
        )

    if critical > 0:
        status = "FAIL"
    elif recommendations:
        status = "WARN"
    else:
        status = "PASS"

    return status, critical, recommendations


def build_report(
    checks: dict[str, dict],
    current_phase: str,
) -> dict:
    """Assemble the final JSON report."""
    status, critical, recommendations = determine_status(checks)

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "phase": current_phase,
        "checks": checks,
        "summary": {
            "status": status,
            "critical_findings": critical,
            "recommendations": recommendations,
        },
    }


def archive_report(report: dict) -> Path:
    """Save report to evidence/cross-validation/."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = EVIDENCE_DIR / f"cross-validation-{ts}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    use_json = "--json" in sys.argv
    use_archive = "--archive" in sys.argv
    skip_execution = "--skip-execution" in sys.argv

    # Load data
    matrix = load_matrix()
    current_phase = matrix.get("current_phase", "phase_0")
    task_cards = parse_task_cards()

    ctx = ValidationContext(
        matrix=matrix,
        phases=matrix.get("phases", {}),
        task_cards=task_cards,
        skip_execution=skip_execution,
    )

    if not use_json:
        print("=== Cross-Validation Diagnostic ===")
        print(f"Phase: {current_phase}")
        print(f"Task cards: {len(task_cards)}")
        print()

    # Run all 8 checks
    checks: dict[str, dict] = {}

    if not use_json:
        print("[1/8] Gate Coverage...")
    result1 = check_gate_coverage(ctx)
    checks[result1.name] = result1.to_dict()

    if not use_json:
        gc = result1.to_dict()
        print(
            f"  {gc['covered']}/{gc['total_done_milestones']} done milestones covered "
            f"({gc['coverage_rate']:.0%})"
        )
        print()

    if not use_json:
        print("[2/8] Acceptance Command Execution...")
    result2 = check_acceptance_execution(ctx)
    checks[result2.name] = result2.to_dict()

    if not use_json:
        ae = result2.to_dict()
        print(
            f"  Executed: {ae['executed']}, Passed: {ae['passed']}, "
            f"Failed: {ae['failed']}, Skipped: {ae['skipped']}"
        )
        print()

    if not use_json:
        print("[3/8] Gate-vs-Acceptance Consistency...")
    result3 = check_consistency(ctx)
    checks[result3.name] = result3.to_dict()

    if not use_json:
        con = result3.to_dict()
        print(
            f"  Comparable: {con['total_comparable']}, Consistent: {con['consistent']}, "
            f"Mismatched: {len(con['mismatched'])}"
        )
        print()

    if not use_json:
        print("[4/8] Architecture Boundary (AST)...")
    result4 = check_architecture_boundary(ctx)
    checks[result4.name] = result4.to_dict()

    if not use_json:
        ab = result4.to_dict()
        print(
            f"  Layers checked: {len(ab['layers_checked'])}, "
            f"Violations: {len(ab['violations'])}, "
            f"Privacy boundary: {'INTACT' if ab['privacy_boundary_intact'] else 'VIOLATED'}"
        )
        print()

    if not use_json:
        print("[5/8] Design Claim Audit...")
    result5 = check_design_claims(ctx)
    checks[result5.name] = result5.to_dict()

    if not use_json:
        dc = result5.to_dict()
        print(
            f"  Claims: {dc['total_claims']}, Verified: {dc['verified']}, "
            f"Unverified: {len(dc['unverified'])}"
        )
        print()

    if not use_json:
        print("[6/8] Call Graph (Business->Infra)...")
    result6 = check_call_graph(ctx)
    checks[result6.name] = result6.to_dict()

    if not use_json:
        cg = result6.to_dict()
        print(f"  Layers checked: {len(cg['layers_checked'])}, Violations: {len(cg['violations'])}")
        print()

    if not use_json:
        print("[7/8] Stub Detection...")
    result7 = check_stub_detection(ctx)
    checks[result7.name] = result7.to_dict()

    if not use_json:
        sd = result7.to_dict()
        print(f"  Files scanned: {sd['total_files_scanned']}, Stubs found: {sd['total_stubs']}")
        print()

    if not use_json:
        print("[8/8] LLM Call Verification...")
    result8 = check_llm_calls(ctx)
    checks[result8.name] = result8.to_dict()

    if not use_json:
        lc = result8.to_dict()
        print(f"  Layers checked: {len(lc['layers_checked'])}, Violations: {len(lc['violations'])}")
        print()

    # Assemble report
    report = build_report(checks, current_phase)

    if use_archive:
        archive_path = archive_report(report)
        if not use_json:
            print(f"Archived: {archive_path}")

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print(f"=== Result: {s['status']} ===")
        print(f"Critical findings: {s['critical_findings']}")
        if s["recommendations"]:
            print("Recommendations:")
            for r in s["recommendations"]:
                print(f"  - {r}")

    # Exit code: 0 for PASS/WARN, 1 for FAIL
    if report["summary"]["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
