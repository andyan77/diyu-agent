#!/usr/bin/env python3
"""Full Milestone Delivery Guard Ruling Table.

Produces a guard ruling for every milestone in milestone-matrix.yaml,
using evidence-chain-based judgment rather than simple status mapping.

Ruling model (3 dimensions per milestone):
  1. status_claim: YAML-annotated status field (done / no_status)
  2. gate_evidence: phase-level gate evidence grade (A/B/C/D/F)
  3. guard_ruling: composite verdict

Guard ruling logic:
  - status=done + phase has gates + best_evidence_grade >= C -> delivered
  - status=done + phase has gates + best_evidence_grade < C  -> guarded
  - status=done + phase has NO gates                         -> unguarded
  - no status / empty                                        -> no_claim

Guard fields (milestone-level):
  gate_result, deep_verdict, evidence_scope, evidence_grade,
  status_basis, verdict_reason, promotion_rule

  V1 (no gate_criteria): Derived from phase-level gate profiles (proxy).
  V2 (with gate_criteria): Derived from per-milestone gate bindings.
  Selection is automatic: milestone has gate_criteria -> V2, else V1.

Evidence grade taxonomy (by gate command TYPE):
  A = runtime/E2E/playwright (pytest e2e, playwright, lighthouse)
  B = integration test (pytest integration)
  C = unit test (pytest unit)
  D = static analysis (test -f, grep -q, ruff, scripts/)
  F = no gate binding

Usage:
    python scripts/check_milestone_ruling.py --json
    python scripts/check_milestone_ruling.py --json --verbose
    python scripts/check_milestone_ruling.py --json --ci-baseline 192

Exit codes:
    0: PASS (all claimed milestones are delivered, or within ci-baseline)
    1: FAIL (unguarded milestones exist, or no_claim exceeds ci-baseline)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")

# Evidence grade ranking: lower = stronger evidence
_GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}

# Minimum grade for "delivered" ruling (C = unit test)
_DELIVERED_THRESHOLD = "C"

# Controlled vocabulary for evidence_scope (V1)
_EVIDENCE_SCOPE_BY_GRADE = {
    "A": "phase-level test-backed (runtime/E2E)",
    "B": "phase-level test-backed (integration)",
    "C": "phase-level test-backed (unit)",
    "D": "phase-level static",
    "F": "none",
}


# ---------------------------------------------------------------------------
# Evidence grade classification
# ---------------------------------------------------------------------------


def classify_evidence_grade(check_cmd: str) -> str:
    """Classify a gate check command into evidence grade A/B/C/D/F.

    Classification rules (by gate command TYPE):
      A: runtime/E2E/playwright — command runs real pytest e2e/smoke/cross tests
         or playwright/lighthouse
      B: integration test — command runs pytest with 'integration' in path
      C: unit test — command runs pytest with 'unit' in path or general pytest
      D: static analysis — test -f, grep -q, ruff, wc, bash scripts/
      F: no command
    """
    if not check_cmd or not check_cmd.strip():
        return "F"

    cmd = check_cmd.strip().lower()

    # A: E2E / Playwright / Lighthouse
    if "playwright" in cmd or "lighthouse" in cmd:
        return "A"
    if "pytest" in cmd and any(p in cmd for p in ("e2e", "smoke", "cross")):
        return "A"

    # B: Integration
    if "pytest" in cmd and "integration" in cmd:
        return "B"

    # C: Unit test (pytest without e2e/integration/smoke/cross markers)
    if "pytest" in cmd:
        return "C"

    # D: Static / script-based
    if any(
        p in cmd
        for p in (
            "test -f",
            "test -d",
            "test -e",
            "grep -q",
            "grep -c",
            "ruff",
            "wc -l",
            "bash scripts/",
            "python scripts/",
            "uv run python scripts/",
            "make lint",
            "pnpm run build",
            "pnpm run lint",
            "node ",
        )
    ):
        return "D"

    # Default: anything with actual content is at least D
    return "D"


def _best_grade(grades: list[str]) -> str:
    """Return the best (lowest rank) grade from a list."""
    if not grades:
        return "F"
    return min(grades, key=lambda g: _GRADE_RANK.get(g, 99))


# ---------------------------------------------------------------------------
# Phase gate profile computation
# ---------------------------------------------------------------------------


def compute_phase_gate_profiles(
    *,
    matrix_path: Path | None = None,
) -> dict[str, dict]:
    """Compute gate evidence profiles for each phase.

    Returns dict keyed by phase_key with:
      total_gates: int
      gate_ids: list[str]
      gate_grades: list[str]  (evidence grade per gate)
      best_evidence_grade: str (A/B/C/D/F)
      has_xnode_coverage: bool (any gate has xnode bindings)
    """
    path = matrix_path or MATRIX_PATH
    if not path.exists():
        return {}

    with path.open(encoding="utf-8") as f:
        matrix = yaml.safe_load(f)

    if not isinstance(matrix, dict):
        return {}

    profiles: dict[str, dict] = {}
    for phase_key, phase_data in matrix.get("phases", {}).items():
        if not isinstance(phase_data, dict):
            continue

        ec = phase_data.get("exit_criteria", {})
        gate_ids: list[str] = []
        gate_grades: list[str] = []
        has_xnode = False

        for tier in ("hard", "soft"):
            for crit in ec.get(tier, []):
                gid = crit.get("id", "")
                cmd = crit.get("check", "")
                xnodes = crit.get("xnodes", [])

                gate_ids.append(gid)
                gate_grades.append(classify_evidence_grade(cmd))
                if xnodes:
                    has_xnode = True

        profiles[phase_key] = {
            "total_gates": len(gate_ids),
            "gate_ids": gate_ids,
            "gate_grades": gate_grades,
            "best_evidence_grade": _best_grade(gate_grades),
            "has_xnode_coverage": has_xnode,
        }

    return profiles


# ---------------------------------------------------------------------------
# Per-milestone ruling
# ---------------------------------------------------------------------------


def _derive_guard_fields(
    *,
    guard_ruling: str,
    best_grade: str,
    total_gates: int,
    ruling_basis: str,
) -> dict:
    """Derive V1 guard fields from phase-level profile (proxy model).

    Returns 7 fields matching xnode_registry schema, derived at
    milestone-level using phase_gate_profile_proxy.
    """
    # gate_result: enum {pass, fail, not_bound, not_executed}
    gate_result = "not_bound" if total_gates == 0 else "not_executed"

    # deep_verdict: V1 always unverified (no per-milestone deep verify)
    deep_verdict = "unverified"

    # evidence_scope: controlled vocabulary by grade
    evidence_scope = _EVIDENCE_SCOPE_BY_GRADE.get(best_grade, "none")

    # evidence_grade: mirror phase-level best grade to milestone
    evidence_grade = best_grade

    # status_basis: always proxy in V1
    status_basis = "phase_gate_profile_proxy"

    # verdict_reason: human-readable, derived from ruling_basis
    verdict_reason = ruling_basis

    # promotion_rule: based on Appendix A Rule 2
    if guard_ruling == "delivered":
        promotion_rule = "maintain: deep_verdict=pass + evidence_grade>=C"
    elif guard_ruling in ("guarded", "unguarded"):
        promotion_rule = "bind to gate + deep verify + evidence_grade >= C"
    else:
        promotion_rule = "claim status=done first"

    return {
        "gate_result": gate_result,
        "deep_verdict": deep_verdict,
        "evidence_scope": evidence_scope,
        "evidence_grade": evidence_grade,
        "status_basis": status_basis,
        "verdict_reason": verdict_reason,
        "promotion_rule": promotion_rule,
    }


# ---------------------------------------------------------------------------
# V2: Per-milestone gate binding
# ---------------------------------------------------------------------------


# Controlled vocabulary for V2 evidence_scope
_V2_EVIDENCE_SCOPE_BY_GRADE = {
    "A": "milestone-bound test-backed (runtime/E2E)",
    "B": "milestone-bound test-backed (integration)",
    "C": "milestone-bound test-backed (unit)",
    "D": "milestone-bound static",
    "F": "milestone-bound (no gate command)",
}


def resolve_milestone_gates(
    milestone: dict,
    phase_exit_criteria: dict,
) -> list[dict]:
    """Resolve gate_criteria IDs to actual exit_criteria entries.

    Args:
        milestone: Milestone dict (must have 'gate_criteria' list of IDs).
        phase_exit_criteria: Phase exit_criteria dict with 'hard' and 'soft' lists.

    Returns:
        List of matching criterion dicts (with id, check, xnodes fields).
        Unresolvable IDs are silently skipped (reported via validate_gate_bindings).
    """
    gate_ids = milestone.get("gate_criteria", [])
    if not gate_ids:
        return []

    # Build lookup from exit_criteria
    criteria_by_id: dict[str, dict] = {}
    for tier in ("hard", "soft"):
        for crit in phase_exit_criteria.get(tier, []):
            crit_id = crit.get("id", "")
            if crit_id:
                criteria_by_id[crit_id] = crit

    return [criteria_by_id[gid] for gid in gate_ids if gid in criteria_by_id]


def lookup_xnode_verdicts(
    bound_gates: list[dict],
    xnode_registry: dict,
) -> dict:
    """Follow gate -> xnodes -> xnode_registry chain.

    Returns dict with:
        deep_verdict: str ('pass', 'fail', 'unverified', 'stale', or None)
        gate_result: str ('pass', 'fail', 'not_bound', 'not_executed')
        xnode_ids: list[str]  (xnode IDs found in chain)
    """
    xnode_ids: list[str] = []
    for gate in bound_gates:
        xnode_ids.extend(gate.get("xnodes", []))

    if not xnode_ids:
        return {
            "deep_verdict": None,
            "gate_result": None,
            "xnode_ids": [],
        }

    # Collect verdicts from registry
    verdicts: list[str] = []
    gate_results: list[str] = []
    for xid in xnode_ids:
        entry = xnode_registry.get(xid, {})
        if entry:
            dv = entry.get("deep_verdict", "unverified")
            gr = entry.get("gate_result", "not_executed")
            verdicts.append(dv)
            gate_results.append(gr)

    if not verdicts:
        return {
            "deep_verdict": None,
            "gate_result": None,
            "xnode_ids": xnode_ids,
        }

    # Aggregate: worst verdict wins
    verdict_priority = {"fail": 0, "stale": 1, "unverified": 2, "pass": 3}
    deep_verdict = min(verdicts, key=lambda v: verdict_priority.get(v, 99))

    # Aggregate gate_result: fail > not_executed > not_bound > pass
    gr_priority = {"fail": 0, "not_executed": 1, "not_bound": 2, "pass": 3}
    gate_result = min(gate_results, key=lambda g: gr_priority.get(g, 99))

    return {
        "deep_verdict": deep_verdict,
        "gate_result": gate_result,
        "xnode_ids": xnode_ids,
    }


def _derive_guard_fields_v2(
    *,
    guard_ruling: str,
    bound_gates: list[dict],
    xnode_lookup: dict,
    ruling_basis: str,
) -> dict:
    """Derive V2 guard fields from per-milestone gate binding.

    Uses actual gate bindings and xnode_registry data when available.
    """
    # gate_result: from xnode chain if available, else by gate presence
    if xnode_lookup.get("gate_result"):
        gate_result = xnode_lookup["gate_result"]
    elif not bound_gates:
        gate_result = "not_bound"
    else:
        gate_result = "not_executed"

    # deep_verdict: from xnode chain if available
    deep_verdict = xnode_lookup.get("deep_verdict") or "unverified"

    # evidence_grade: based on bound gate commands (per-milestone)
    gate_grades = [classify_evidence_grade(g.get("check", "")) for g in bound_gates]
    evidence_grade = _best_grade(gate_grades)

    # evidence_scope: V2 controlled vocabulary
    evidence_scope = _V2_EVIDENCE_SCOPE_BY_GRADE.get(evidence_grade, "none")

    # status_basis: V2 source
    status_basis = "xnode_registry" if xnode_lookup.get("xnode_ids") else "milestone_gate_binding"

    # verdict_reason: enhanced with xnode detail
    xnode_ids = xnode_lookup.get("xnode_ids", [])
    if xnode_ids:
        verdict_reason = (
            f"{ruling_basis}; xnode chain: {','.join(xnode_ids)} -> deep_verdict={deep_verdict}"
        )
    else:
        gate_ids = [g.get("id", "?") for g in bound_gates]
        verdict_reason = f"{ruling_basis}; bound gates: {','.join(gate_ids)}"

    # promotion_rule
    if guard_ruling == "delivered":
        promotion_rule = "maintain: deep_verdict=pass + evidence_grade>=C"
    elif guard_ruling in ("guarded", "unguarded"):
        promotion_rule = "bind to gate + deep verify + evidence_grade >= C"
    else:
        promotion_rule = "claim status=done first"

    return {
        "gate_result": gate_result,
        "deep_verdict": deep_verdict,
        "evidence_scope": evidence_scope,
        "evidence_grade": evidence_grade,
        "status_basis": status_basis,
        "verdict_reason": verdict_reason,
        "promotion_rule": promotion_rule,
    }


def validate_gate_bindings(
    milestones_raw: list[tuple[dict, str]],
    phases: dict,
) -> list[dict]:
    """Validate gate_criteria bindings for correctness.

    Args:
        milestones_raw: List of (milestone_dict, phase_key) tuples.
        phases: Full phases dict from YAML.

    Returns list of finding dicts for invalid bindings.
    """
    findings: list[dict] = []

    for ms, phase_key in milestones_raw:
        gate_criteria = ms.get("gate_criteria", [])
        if not gate_criteria:
            continue

        ms_id = ms.get("id", "unknown")
        phase_data = phases.get(phase_key, {})
        ec = phase_data.get("exit_criteria", {})

        # Collect valid IDs for this phase
        valid_ids: set[str] = set()
        for tier in ("hard", "soft"):
            for crit in ec.get(tier, []):
                valid_ids.add(crit.get("id", ""))

        # Check each binding
        seen: set[str] = set()
        for gid in gate_criteria:
            if gid in seen:
                findings.append(
                    {
                        "type": "duplicate_binding",
                        "milestone": ms_id,
                        "gate_id": gid,
                        "message": f"Duplicate gate_criteria entry '{gid}' in {ms_id}",
                    }
                )
            seen.add(gid)

            if gid not in valid_ids:
                findings.append(
                    {
                        "type": "invalid_binding",
                        "milestone": ms_id,
                        "gate_id": gid,
                        "message": (
                            f"gate_criteria '{gid}' in {ms_id} not found in "
                            f"{phase_key} exit_criteria"
                        ),
                    }
                )

    return findings


def rule_milestone(
    *,
    status: str,
    phase_key: str,
    phase_profiles: dict[str, dict],
) -> dict:
    """Produce a guard ruling for a single milestone.

    Returns dict with (5 core + 7 V1 guard fields = 12 total):
      Core: guard_ruling, best_evidence_grade, phase_gate_count,
            has_xnode_coverage, ruling_basis
      V1 guard: gate_result, deep_verdict, evidence_scope, evidence_grade,
                status_basis, verdict_reason, promotion_rule
    """
    profile = phase_profiles.get(phase_key, {})
    total_gates = profile.get("total_gates", 0)
    best_grade = profile.get("best_evidence_grade", "F")
    has_xnode = profile.get("has_xnode_coverage", False)

    # No status claim -> no_claim regardless of gate coverage
    if status != "done":
        ruling_basis = f"status={status}, no delivery claim"
        core = {
            "guard_ruling": "no_claim",
            "best_evidence_grade": best_grade,
            "phase_gate_count": total_gates,
            "has_xnode_coverage": has_xnode,
            "ruling_basis": ruling_basis,
        }
        return {
            **core,
            **_derive_guard_fields(
                guard_ruling="no_claim",
                best_grade=best_grade,
                total_gates=total_gates,
                ruling_basis=ruling_basis,
            ),
        }

    # status=done but no gate coverage -> unguarded
    if total_gates == 0:
        ruling_basis = "status=done but phase has 0 gates, no guard verification"
        core = {
            "guard_ruling": "unguarded",
            "best_evidence_grade": "F",
            "phase_gate_count": 0,
            "has_xnode_coverage": False,
            "ruling_basis": ruling_basis,
        }
        return {
            **core,
            **_derive_guard_fields(
                guard_ruling="unguarded",
                best_grade="F",
                total_gates=0,
                ruling_basis=ruling_basis,
            ),
        }

    # status=done with gate coverage -> check evidence grade threshold
    threshold_rank = _GRADE_RANK.get(_DELIVERED_THRESHOLD, 2)
    best_rank = _GRADE_RANK.get(best_grade, 99)

    if best_rank <= threshold_rank:
        ruling_basis = (
            f"status=done, {total_gates} gates, best_grade={best_grade} >= {_DELIVERED_THRESHOLD}"
        )
        core = {
            "guard_ruling": "delivered",
            "best_evidence_grade": best_grade,
            "phase_gate_count": total_gates,
            "has_xnode_coverage": has_xnode,
            "ruling_basis": ruling_basis,
        }
        return {
            **core,
            **_derive_guard_fields(
                guard_ruling="delivered",
                best_grade=best_grade,
                total_gates=total_gates,
                ruling_basis=ruling_basis,
            ),
        }

    ruling_basis = (
        f"status=done, {total_gates} gates, "
        f"best_grade={best_grade} < {_DELIVERED_THRESHOLD} (weak evidence)"
    )
    core = {
        "guard_ruling": "guarded",
        "best_evidence_grade": best_grade,
        "phase_gate_count": total_gates,
        "has_xnode_coverage": has_xnode,
        "ruling_basis": ruling_basis,
    }
    return {
        **core,
        **_derive_guard_fields(
            guard_ruling="guarded",
            best_grade=best_grade,
            total_gates=total_gates,
            ruling_basis=ruling_basis,
        ),
    }


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def parse_milestones(*, matrix_path: Path | None = None) -> list[dict]:
    """Parse all milestones and apply guard rulings.

    Returns a list of dicts with 17 fields:
        Base (5): id, phase, layer, summary, status
        Core ruling (5): guard_ruling, best_evidence_grade, phase_gate_count,
                         has_xnode_coverage, ruling_basis
        Guard (7): gate_result, deep_verdict, evidence_scope,
                   evidence_grade, status_basis, verdict_reason,
                   promotion_rule

    Guard fields use V2 (milestone_gate_binding) when gate_criteria is
    present, otherwise V1 (phase_gate_profile_proxy).
    """
    path = matrix_path or MATRIX_PATH
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as f:
        matrix = yaml.safe_load(f)

    if not isinstance(matrix, dict):
        return []

    profiles = compute_phase_gate_profiles(matrix_path=path)
    xnode_registry = matrix.get("xnode_registry", {})
    if not isinstance(xnode_registry, dict):
        xnode_registry = {}

    milestones: list[dict] = []
    for phase_key, phase_data in matrix.get("phases", {}).items():
        if not isinstance(phase_data, dict):
            continue

        ec = phase_data.get("exit_criteria", {})

        for ms in phase_data.get("milestones", []):
            if not isinstance(ms, dict):
                continue
            raw_status = ms.get("status", "")
            status = str(raw_status).strip().lower() if raw_status else "no_status"

            # Core ruling (always phase-level — determines guard_ruling)
            ruling = rule_milestone(
                status=status,
                phase_key=phase_key,
                phase_profiles=profiles,
            )

            # V2 override: if milestone has gate_criteria, replace guard fields
            gate_criteria = ms.get("gate_criteria")
            if gate_criteria:
                bound_gates = resolve_milestone_gates(ms, ec)
                xnode_lookup = lookup_xnode_verdicts(bound_gates, xnode_registry)
                v2_fields = _derive_guard_fields_v2(
                    guard_ruling=ruling["guard_ruling"],
                    bound_gates=bound_gates,
                    xnode_lookup=xnode_lookup,
                    ruling_basis=ruling["ruling_basis"],
                )
                ruling.update(v2_fields)

            milestones.append(
                {
                    "id": ms.get("id", ""),
                    "phase": phase_key,
                    "layer": ms.get("layer", ""),
                    "summary": ms.get("summary", ""),
                    "status": status,
                    **ruling,
                }
            )

    return milestones


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    milestones: list[dict],
    *,
    verbose: bool = False,
    binding_findings: list[dict] | None = None,
) -> dict:
    """Build the JSON report with per-milestone guard rulings."""
    total = len(milestones)
    delivered = [m for m in milestones if m["guard_ruling"] == "delivered"]
    guarded = [m for m in milestones if m["guard_ruling"] == "guarded"]
    unguarded = [m for m in milestones if m["guard_ruling"] == "unguarded"]
    no_claim = [m for m in milestones if m["guard_ruling"] == "no_claim"]

    # Phase breakdown with per-ruling counts
    phase_breakdown: dict[str, dict] = {}
    for m in milestones:
        pk = m["phase"]
        if pk not in phase_breakdown:
            phase_breakdown[pk] = {
                "total": 0,
                "delivered": 0,
                "guarded": 0,
                "unguarded": 0,
                "no_claim": 0,
            }
        phase_breakdown[pk]["total"] += 1
        ruling = m["guard_ruling"]
        if ruling in phase_breakdown[pk]:
            phase_breakdown[pk][ruling] += 1

    # Layer breakdown
    layer_breakdown: dict[str, dict] = {}
    for m in milestones:
        layer = m["layer"]
        if layer not in layer_breakdown:
            layer_breakdown[layer] = {"total": 0, "delivered": 0, "guarded": 0}
        layer_breakdown[layer]["total"] += 1
        if m["guard_ruling"] == "delivered":
            layer_breakdown[layer]["delivered"] += 1
        elif m["guard_ruling"] == "guarded":
            layer_breakdown[layer]["guarded"] += 1

    # Findings = everything not delivered
    findings = [m for m in milestones if m["guard_ruling"] != "delivered"]

    # Status determination
    if unguarded:
        status = "FAIL"  # Claims done but no guard verification
    elif no_claim and len(no_claim) > total * 0.5:
        status = "FAIL"
    elif guarded or no_claim:
        status = "WARN"
    else:
        status = "PASS"

    delivery_rate = round(len(delivered) / total, 4) if total else 0.0

    # V2 stats
    v2_count = sum(1 for m in milestones if m.get("status_basis") != "phase_gate_profile_proxy")

    report: dict = {
        "status": status,
        "summary": {
            "total_milestones": total,
            "delivered_count": len(delivered),
            "guarded_count": len(guarded),
            "unguarded_count": len(unguarded),
            "no_claim_count": len(no_claim),
            "delivery_rate": delivery_rate,
            "v2_bound_count": v2_count,
            "phase_breakdown": phase_breakdown,
            "layer_breakdown": layer_breakdown,
            "findings_count": len(findings),
        },
        "milestones": milestones if verbose else [],
        "findings": findings,
    }

    if binding_findings:
        report["binding_findings"] = binding_findings

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _run_binding_validation(
    matrix_path: Path | None = None,
) -> list[dict]:
    """Run gate_criteria binding validation on real YAML."""
    path = matrix_path or MATRIX_PATH
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as f:
        matrix = yaml.safe_load(f)

    if not isinstance(matrix, dict):
        return []

    phases = matrix.get("phases", {})
    milestones_raw: list[tuple[dict, str]] = []
    for phase_key, phase_data in phases.items():
        if not isinstance(phase_data, dict):
            continue
        for ms in phase_data.get("milestones", []):
            if isinstance(ms, dict):
                milestones_raw.append((ms, phase_key))

    return validate_gate_bindings(milestones_raw, phases)


def _parse_ci_baseline(argv: list[str]) -> int | None:
    """Parse --ci-baseline N from argv. Returns N or None."""
    for i, arg in enumerate(argv):
        if arg == "--ci-baseline" and i + 1 < len(argv):
            try:
                return int(argv[i + 1])
            except ValueError:
                return None
    return None


def apply_ci_baseline(report: dict, baseline: int) -> str:
    """Apply CI baseline logic to determine exit status.

    Rules:
      - unguarded_count > 0 → always FAIL (not eligible for baseline)
      - no_claim_count > baseline → FAIL
      - no_claim_count <= baseline → PASS (within known baseline)

    Returns adjusted status string.
    """
    s = report["summary"]
    if s["unguarded_count"] > 0:
        return "FAIL"
    if s["no_claim_count"] > baseline:
        return "FAIL"
    return "PASS"


def main() -> None:
    use_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv
    ci_baseline = _parse_ci_baseline(sys.argv)

    if not use_json:
        print("=== Full Milestone Delivery Guard Ruling ===")

    milestones = parse_milestones()

    # Run binding validation
    binding_findings = _run_binding_validation()

    if not use_json:
        print(f"Total milestones: {len(milestones)}")

    report = generate_report(
        milestones,
        verbose=verbose,
        binding_findings=binding_findings,
    )

    # Apply CI baseline if provided
    if ci_baseline is not None:
        ci_status = apply_ci_baseline(report, ci_baseline)
        report["ci_baseline"] = ci_baseline
        report["ci_status"] = ci_status

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print("\nRuling distribution:")
        print(
            f"  delivered:  {s['delivered_count']}/{s['total_milestones']}"
            f" ({s['delivery_rate']:.1%})"
        )
        print(f"  guarded:    {s['guarded_count']}")
        print(f"  unguarded:  {s['unguarded_count']}")
        print(f"  no_claim:   {s['no_claim_count']}")

        print("\nPhase breakdown:")
        for pk in sorted(s["phase_breakdown"]):
            pb = s["phase_breakdown"][pk]
            print(
                f"  {pk}: {pb['delivered']} delivered, "
                f"{pb['guarded']} guarded, "
                f"{pb['unguarded']} unguarded, "
                f"{pb['no_claim']} no_claim "
                f"(total {pb['total']})"
            )

        if report["findings"]:
            # Show only unguarded findings (most critical)
            ug = [f for f in report["findings"] if f["guard_ruling"] == "unguarded"]
            if ug:
                print("\nUnguarded milestones (done but no gates):")
                for f in ug[:10]:
                    print(f"  {f['id']} [{f['layer']}]: {f['summary']}")

        if ci_baseline is not None:
            print(f"\nCI baseline: {ci_baseline} (ci_status={report['ci_status']})")

        print(f"\n=== Result: {report['status']} ===")

    # Exit code: use ci_status if baseline is set, otherwise raw status
    effective_status = report.get("ci_status", report["status"])
    if effective_status == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
