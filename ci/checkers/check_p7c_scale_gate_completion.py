#!/usr/bin/env python3
"""Fail-closed gate for P7C scale gate completion and runtime A/B handoff."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


BASELINE = "858729f1fed46c174f300831e8fe4e0ca208a07b"
TASK_ID = "GKB-P7C-SCALE-GATE-COMPLETION-AND-RUNTIME-AB-HANDOFF-001"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
SCALE_REL = f"{RUN_REL}/review_closeout/scale_gate_completion"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"

SCALE_FILES = [
    f"{SCALE_REL}/p7c_scale_decision_standard.v0.1.yaml",
    f"{SCALE_REL}/p7c_capability_heatmap.v0.1.yaml",
    f"{SCALE_REL}/p7c_runtime_ab_sample_plan.v0.1.yaml",
    f"{SCALE_REL}/p7c_execution_scalability_gate.v0.1.yaml",
    f"{SCALE_REL}/p7c_scale_hold_decision.v0.1.yaml",
]
SOURCE_IMMUTABLE = [
    f"{RUN_REL}/knowledge_candidate_cards.yaml",
    f"{RUN_REL}/rich_body_blocks.yaml",
    f"{RUN_REL}/generation_receipt.json",
    f"{RUN_REL}/review_closeout/expert_review_input_digest.v0.1.yaml",
    f"{RUN_REL}/review_closeout/cpss_quality_review_closeout.v0.1.yaml",
    f"{RUN_REL}/review_closeout/cpss_priority_review_queue.v0.1.yaml",
    f"{RUN_REL}/review_closeout/cpss_routing_decision.v0.1.yaml",
    f"{RUN_REL}/review_closeout/runtime_proxy_ab_summary.v0.1.yaml",
    f"{RUN_REL}/review_closeout/runtime_ab_followup_plan.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scoped_120_review_closeout.v0.1.md",
    f"{RUN_REL}/content_kernel_extraction/content_kernel_manifest.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/review_packet_kernel_matrix.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/content_kernel_candidate_matrix.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/content_kernel_source_trace_index.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/content_kernel_quality_bucket_index.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/content_kernel_extraction_closeout.v0.1.md",
]
ALLOWED_WRITE_PREFIXES = (
    f"{SCALE_REL}/",
    "ci/checkers/check_p7c_scale_gate_completion.py",
    "ci/fixtures/p7c_scale_gate_completion/",
    "ci/reports/p7c_scale_gate_completion_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/p7c_scale_gate_completion_report.md",
    "docs/reports/p7c_scale_gate_completion_receipt.json",
)
FORBIDDEN_PATHS = [
    "KE",
    "serving_projection",
    "rag",
    "dify",
    "candidatepack_etl",
    "CandidatePack",
    "RAG",
    "DIFY",
    "08_consolidated_outputs",
    "09_candidatepack_eligibility",
    "07_microbatch_runs/microbatches",
    "07_microbatch_runs/run_manifest.v0.1.yaml",
    "07_microbatch_runs/microbatch_index.v0.1.csv",
]
READINESS_KEYS = [
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "Serving_ready",
    "production_ready",
    "generation_allowed",
    "generation_eligible",
    "production_servable",
    "release_ready",
]
B_GRADE = {
    "SCM120-CAND-023", "SCM120-CAND-030", "SCM120-CAND-045", "SCM120-CAND-047",
    "SCM120-CAND-062", "SCM120-CAND-080", "SCM120-CAND-083", "SCM120-CAND-103",
    "SCM120-CAND-109", "SCM120-CAND-110", "SCM120-CAND-111", "SCM120-CAND-113",
}
C_GRADE = {"SCM120-CAND-101", "SCM120-CAND-059", "SCM120-CAND-106"}
A_CAVEAT = {"SCM120-CAND-032", "SCM120-CAND-033", "SCM120-CAND-035", "SCM120-CAND-037", "SCM120-CAND-102"}
EXPECTED_HEATMAP = {
    "P0_01": {"count": 18, "CPSS_avg": 96.0, "scale_signal": "strongest", "common_gap": "none_systemic"},
    "P0_02": {"count": 21, "CPSS_avg": 90.3, "scale_signal": "strong_with_minor_gap", "common_gap": ["apparel_detail_density", "real_scene_feeling"]},
    "P0_03": {"count": 30, "CPSS_avg": 91.8, "scale_signal": "strong", "common_gap": ["some_evidence_bound_items_lack_visual_fuel"]},
    "P0_04": {"count": 27, "CPSS_avg": 93.8, "scale_signal": "very_strong", "common_gap": "none_systemic"},
    "P0_05": {"count": 24, "CPSS_avg": 89.9, "scale_signal": "acceptable_but_weakest", "common_gap": ["scene_premise", "customer_task", "product_role_differentiation", "spoken_line_conversion"]},
}


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_status_paths(ws: Path) -> list[str]:
    proc = subprocess.run(["git", "-C", str(ws), "status", "--short", "--untracked-files=all"], capture_output=True, text=True)
    if proc.returncode != 0:
        return ["<git-status-failed>"]
    return [line[3:] for line in proc.stdout.splitlines() if line.strip()]


def allowed(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in ALLOWED_WRITE_PREFIXES)


def baseline_report(ws: Path) -> dict[str, Any]:
    rel = "ci/reports/scoped_120_quality_review_and_content_kernel_extraction_report.v0.1.json"
    proc = subprocess.run(["git", "-C", str(ws), "show", f"{BASELINE}:{rel}"], capture_output=True, text=True)
    if proc.returncode != 0:
        return {"status": "MISSING", "error_count": 1}
    return json.loads(proc.stdout)


def diff_clean(ws: Path, rel: str) -> bool:
    proc = subprocess.run(["git", "-C", str(ws), "diff", "--quiet", BASELINE, "--", rel], capture_output=True, text=True)
    return proc.returncode == 0


def load_bundle(ws: Path) -> dict[str, Any]:
    return {
        "standard": read_yaml(ws / SCALE_FILES[0])["p7c_scale_decision_standard"],
        "heatmap": read_yaml(ws / SCALE_FILES[1])["p7c_capability_heatmap"],
        "sample_plan": read_yaml(ws / SCALE_FILES[2])["p7c_runtime_ab_sample_plan"],
        "scalability": read_yaml(ws / SCALE_FILES[3])["p7c_execution_scalability_gate"],
        "hold": read_yaml(ws / SCALE_FILES[4])["p7c_scale_hold_decision"],
        "cards": read_yaml(ws / f"{RUN_REL}/knowledge_candidate_cards.yaml")["scoped_120_candidate_cards"]["candidates"],
        "quality": read_yaml(ws / f"{RUN_REL}/review_closeout/cpss_quality_review_closeout.v0.1.yaml")["cpss_quality_review_closeout"],
        "user_kernel": read_yaml(ws / f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml")["user_visible_kernel_matrix"],
        "review_kernel": read_yaml(ws / f"{RUN_REL}/content_kernel_extraction/review_packet_kernel_matrix.v0.1.yaml")["review_packet_kernel_matrix"],
        "ledger": read_yaml(ws / LEDGER_REL)["grc_3600_execution_plan_status"],
        "prior_report": baseline_report(ws),
    }


def validate(bundle: dict[str, Any], *, live: bool, ws: Path | None = None) -> list[str]:
    errors: list[str] = []
    cards = bundle["cards"]
    card_by_id = {c.get("candidate_id"): c for c in cards}
    user_ids = {e.get("candidate_id") for e in bundle["user_kernel"].get("entries", [])}
    review_ids = {e.get("candidate_id") for e in bundle["review_kernel"].get("entries", [])}

    if len(cards) != 120 or len(card_by_id) != 120:
        errors.append("scoped 120 candidate count drift")
    if user_ids != set(card_by_id) or review_ids != set(card_by_id):
        errors.append("kernel candidate ids drift from cards")

    q = bundle["quality"]
    if q.get("evaluated_count") != 120 or float(q.get("CPSS_avg", 0)) != 92.2:
        errors.append("expert summary evaluated_count/CPSS_avg mismatch")
    if q.get("routing_summary") != {"content_kernel_candidate": 100, "content_kernel_candidate_with_review_caveat": 5, "needs_fuel_repair_or_manual_polish": 12, "strategy_rule_candidate_or_rewrite": 3, "reject": 0}:
        errors.append("routing summary mismatch")
    if q.get("score_detail_source") != "summary_only":
        errors.append("score detail source must remain summary_only")

    standard = bundle["standard"]
    if standard.get("standard_id") != "P7C-SCALE-DECISION-STANDARD-v0.1":
        errors.append("scale standard id mismatch")
    for key in ["formal_schema_contract", "ontology_truth_source", "KE_admission_standard"]:
        if standard.get(key) is not False:
            errors.append(f"standard {key} must be false")
    roles = standard.get("review_roles", {})
    if roles.get("final_scale_decision_authority") != "founder" or roles.get("codex_final_scale_authority") is not False:
        errors.append("Codex/founder scale authority mismatch")
    thresholds = standard.get("static_thresholds", {})
    for key in ["hard_gate_fail_rate_max", "A_grade_rate_min", "A_or_B_grade_rate_min", "D_grade_rate_max", "average_CPSS_min", "median_CPSS_min", "each_core_P0_group_A_or_B_min"]:
        if key not in thresholds:
            errors.append(f"missing static threshold {key}")
    runtime_thresholds = standard.get("runtime_ab_thresholds", {})
    for key in ["B_preferred_rate_min", "visual_anchor_lift_required", "human_action_lift_required", "spoken_line_lift_required", "courseware_body_must_not_increase", "hard_claim_risk_must_not_increase", "governance_leakage_forbidden"]:
        if key not in runtime_thresholds:
            errors.append(f"missing runtime threshold {key}")
    primary = standard.get("routing_model", {}).get("primary_disposition", {})
    secondary = standard.get("routing_model", {}).get("secondary_candidate_tags", {})
    if primary.get("exactly_one") is not True:
        errors.append("primary disposition must be exactly_one")
    if secondary.get("multi_select") is not True:
        errors.append("secondary tags must be multi_select")
    if "Serving" not in standard.get("CPSS_does_not_authorize", []):
        errors.append("CPSS non-authorization list incomplete")
    if "direct_context_bundle_ready" not in standard.get("content_kernel_does_not_mean", []):
        errors.append("content kernel boundary list incomplete")

    heatmap = bundle["heatmap"]
    if heatmap.get("source") != "existing_expert_review" or heatmap.get("full_rescore_performed") is not False:
        errors.append("heatmap must be sourced from existing expert review without rescore")
    groups = heatmap.get("capability_groups", {})
    if groups != EXPECTED_HEATMAP:
        errors.append("heatmap values do not match expert review")
    actual_p0 = Counter(c.get("p0_group") for c in cards)
    for p0, meta in EXPECTED_HEATMAP.items():
        if actual_p0.get(p0) != meta["count"]:
            errors.append(f"cards p0 count does not support heatmap: {p0}")

    plan = bundle["sample_plan"]
    samples = plan.get("samples", [])
    sample_ids = [s.get("candidate_id") for s in samples]
    if plan.get("sample_count") != 12 or len(samples) != 12 or len(set(sample_ids)) != 12:
        errors.append("runtime A/B samples must be 12 unique ids")
    if plan.get("runtime_ab_executed_by_this_task") is not False:
        errors.append("runtime A/B must not be executed by this task")
    if plan.get("model_prompt_parameters_to_be_frozen_in_next_task") is not True:
        errors.append("model/prompt freeze marker missing")
    bucket_counts = Counter(s.get("support_bucket") for s in samples)
    if bucket_counts != {"high_support": 4, "medium_support": 4, "low_support": 4}:
        errors.append(f"runtime sample bucket distribution mismatch: {dict(bucket_counts)}")
    modes = {s.get("generation_mode") for s in samples}
    if modes != {"creative_prototype", "fact_slot_script", "evidence_bound_candidate", "display_solution"}:
        errors.append("runtime samples must cover four generation modes")
    if len({s.get("p0_group") for s in samples}) < 3:
        errors.append("runtime samples must cover at least three P0 groups")
    if sum(1 for s in samples if s.get("claim_risk_profile") in {"high_claim_or_evidence_boundary", "medium_fact_slot_boundary"}) < 2:
        errors.append("runtime samples need at least two claim-risk samples")
    if sum(1 for s in samples if s.get("store_display_or_guide_action_sample")) < 2:
        errors.append("runtime samples need at least two store/display samples")
    for s in samples:
        cid = s.get("candidate_id")
        if cid not in card_by_id or cid not in user_ids or cid not in review_ids:
            errors.append(f"runtime sample id not found in cards/kernels: {cid}")
            continue
        card = card_by_id[cid]
        if s.get("assignment_id") != card.get("generation_assignment_id"):
            errors.append(f"runtime sample assignment mismatch: {cid}")
        if "CPSS_total" in s:
            errors.append(f"runtime sample fabricates CPSS_total: {cid}")
        if len(s.get("output_types") or []) < 2:
            errors.append(f"runtime sample must have at least two output types: {cid}")
        bucket = s.get("support_bucket")
        if bucket == "high_support" and (cid in B_GRADE or cid in C_GRADE or cid in A_CAVEAT):
            errors.append(f"high support sample is not from clean A derived pool: {cid}")
        if bucket == "medium_support" and cid not in B_GRADE:
            errors.append(f"medium sample not in B queue: {cid}")
        if bucket == "low_support" and cid not in C_GRADE and not (cid in B_GRADE and cid == "SCM120-CAND-062"):
            errors.append(f"low sample not allowed by low bucket rule: {cid}")

    low_ids = {s.get("candidate_id") for s in samples if s.get("support_bucket") == "low_support"}
    if not C_GRADE.issubset(low_ids) or "SCM120-CAND-062" not in low_ids:
        errors.append("low support bucket must include all C grade plus SCM120-CAND-062")

    scalability = bundle["scalability"]
    if scalability.get("gate_status") != "PENDING" or scalability.get("execution_scalability_gate_passed") is not False:
        errors.append("execution scalability gate must be pending/not passed")
    caps = scalability.get("required_capabilities", {})
    if set(caps) != {"deterministic_assignment_consumption", "checkpoint_and_resume", "per_microbatch_stop", "provenance_trace", "cost_guard", "duplicate_drift_monitor", "failure_resume_protocol"}:
        errors.append("execution scalability capabilities mismatch")
    for name, meta in caps.items():
        if meta.get("status") != "PENDING":
            errors.append(f"execution scalability capability not pending: {name}")
    if scalability.get("expand_to_3600_allowed") is not False:
        errors.append("scalability gate cannot allow 3600")

    hold = bundle["hold"]
    if hold.get("final_scale_decision") != "HOLD":
        errors.append("final scale decision must be HOLD")
    for key in ["expand_to_3600_allowed", "midbatch_300_600_allowed"]:
        if hold.get(key) is not False:
            errors.append(f"hold decision {key} must be false")
    if hold.get("real_runtime_AB") != "PENDING" or hold.get("execution_scalability_gate") != "PENDING" or hold.get("founder_final_scale_decision") != "NOT_ISSUED":
        errors.append("hold decision blockers must remain pending/not issued")
    if hold.get("next_allowed_task", {}).get("task_id") != "GKB-CONTENT-KERNEL-REAL-RUNTIME-AB-001":
        errors.append("next allowed task mismatch")
    if any(hold.get("readiness", {}).get(k) is not False for k in hold.get("readiness", {})):
        errors.append("hold readiness flag true")

    ledger = bundle["ledger"]
    steps = {s.get("step_id"): s for s in ledger.get("steps", [])}
    if steps.get("P7C_SCALE_PREP", {}).get("status") != "DONE":
        errors.append("P7C_SCALE_PREP must be DONE")
    if steps.get("P7C-AB", {}).get("status") != "NEXT" or steps.get("P7C-AB", {}).get("task_id") != "GKB-CONTENT-KERNEL-REAL-RUNTIME-AB-001":
        errors.append("P7C-AB must be NEXT for real runtime A/B")
    if steps.get("P7C_SCALE", {}).get("status") != "BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY":
        errors.append("P7C_SCALE must be blocked by runtime AB and scalability")
    if steps.get("P7D", {}).get("status") != "BLOCKED_BY_P7C_SCALE_DECISION":
        errors.append("P7D must preserve BLOCKED_BY_P7C_SCALE_DECISION")
    if steps.get("P8", {}).get("status") != "BLOCKED_BY_P7D":
        errors.append("P8 must be blocked by P7D")
    if ledger.get("generation_unlocked") is not False or ledger.get("expand_to_3600_allowed") is not False:
        errors.append("ledger generation/scale unlock flags must be false")
    readiness = ledger.get("readiness", {})
    if any(readiness.get(k) is not False for k in READINESS_KEYS if k in readiness):
        errors.append("ledger readiness flag true")

    prior = bundle.get("prior_report", {})
    if prior.get("status") != "PASS" or prior.get("error_count") != 0:
        errors.append("baseline P7C-REVIEW prior report not PASS")

    if live and ws is not None:
        for rel in SCALE_FILES:
            if not (ws / rel).exists():
                errors.append(f"missing scale file: {rel}")
        for rel in SOURCE_IMMUTABLE:
            if not diff_clean(ws, rel):
                errors.append(f"source/review/kernel asset modified: {rel}")
        changed = git_status_paths(ws)
        bad = [p for p in changed if not allowed(p)]
        if bad:
            errors.append(f"git status outside allowed write surface: {bad}")
        for rel in FORBIDDEN_PATHS:
            if (ws / rel).exists():
                errors.append(f"forbidden downstream path exists: {rel}")

    return errors


def load_bundle(ws: Path) -> dict[str, Any]:
    b = {
        "standard": read_yaml(ws / SCALE_FILES[0])["p7c_scale_decision_standard"],
        "heatmap": read_yaml(ws / SCALE_FILES[1])["p7c_capability_heatmap"],
        "sample_plan": read_yaml(ws / SCALE_FILES[2])["p7c_runtime_ab_sample_plan"],
        "scalability": read_yaml(ws / SCALE_FILES[3])["p7c_execution_scalability_gate"],
        "hold": read_yaml(ws / SCALE_FILES[4])["p7c_scale_hold_decision"],
        "cards": read_yaml(ws / f"{RUN_REL}/knowledge_candidate_cards.yaml")["scoped_120_candidate_cards"]["candidates"],
        "quality": read_yaml(ws / f"{RUN_REL}/review_closeout/cpss_quality_review_closeout.v0.1.yaml")["cpss_quality_review_closeout"],
        "user_kernel": read_yaml(ws / f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml")["user_visible_kernel_matrix"],
        "review_kernel": read_yaml(ws / f"{RUN_REL}/content_kernel_extraction/review_packet_kernel_matrix.v0.1.yaml")["review_packet_kernel_matrix"],
        "ledger": read_yaml(ws / LEDGER_REL)["grc_3600_execution_plan_status"],
        "prior_report": baseline_report(ws),
    }
    return b


def run_live(ws: Path, report_out: str | None) -> int:
    bundle = load_bundle(ws)
    errors = validate(bundle, live=True, ws=ws)
    status = "PASS" if not errors else "FAIL"
    samples = bundle["sample_plan"].get("samples", [])
    report = {
        "checker": "check_p7c_scale_gate_completion.py",
        "task_id": TASK_ID,
        "status": status,
        "error_count": len(errors),
        "errors": errors[:80],
        "sample_count": len(samples),
        "bucket_counts": dict(Counter(s.get("support_bucket") for s in samples)),
        "generation_mode_coverage": sorted({s.get("generation_mode") for s in samples}),
        "p0_group_coverage_count": len({s.get("p0_group") for s in samples}),
        "claim_risk_sample_count": sum(1 for s in samples if s.get("claim_risk_profile") in {"high_claim_or_evidence_boundary", "medium_fact_slot_boundary"}),
        "store_display_sample_count": sum(1 for s in samples if s.get("store_display_or_guide_action_sample")),
        "final_scale_decision": bundle["hold"].get("final_scale_decision"),
        "expand_to_3600_allowed": bundle["hold"].get("expand_to_3600_allowed"),
        "readiness_false": True,
    }
    if report_out:
        out = Path(report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not errors else 1


def fixture_bundle() -> dict[str, Any]:
    ids = [f"SCM120-CAND-{i:03d}" for i in range(1, 121)]
    cards = []
    mode_cycle = ["creative_prototype", "fact_slot_script", "evidence_bound_candidate", "display_solution"]
    p0_sequence = (
        ["P0_01"] * 18
        + ["P0_02"] * 21
        + ["P0_03"] * 30
        + ["P0_04"] * 27
        + ["P0_05"] * 24
    )
    for i, cid in enumerate(ids):
        cards.append({"candidate_id": cid, "generation_assignment_id": f"SCM120-A{i+1:03d}", "p0_group": p0_sequence[i], "generation_mode": mode_cycle[i % 4]})
    # Force selected sample metadata to match live-like constraints.
    selected = ["SCM120-CAND-002", "SCM120-CAND-016", "SCM120-CAND-040", "SCM120-CAND-070", "SCM120-CAND-023", "SCM120-CAND-045", "SCM120-CAND-080", "SCM120-CAND-113", "SCM120-CAND-101", "SCM120-CAND-059", "SCM120-CAND-106", "SCM120-CAND-062"]
    modes = ["creative_prototype", "fact_slot_script", "evidence_bound_candidate", "display_solution", "creative_prototype", "evidence_bound_candidate", "display_solution", "fact_slot_script", "creative_prototype", "evidence_bound_candidate", "creative_prototype", "evidence_bound_candidate"]
    p0s = ["P0_01", "P0_01", "P0_03", "P0_04", "P0_02", "P0_03", "P0_04", "P0_05", "P0_05", "P0_03", "P0_05", "P0_03"]
    for cid, mode, p0 in zip(selected, modes, p0s):
        card = next(c for c in cards if c["candidate_id"] == cid)
        card["generation_mode"] = mode
        card["p0_group"] = p0
    samples = []
    for bucket, group in [("high_support", selected[:4]), ("medium_support", selected[4:8]), ("low_support", selected[8:])]:
        for cid in group:
            c = next(x for x in cards if x["candidate_id"] == cid)
            samples.append({
                "candidate_id": cid,
                "assignment_id": c["generation_assignment_id"],
                "support_bucket": bucket,
                "p0_group": c["p0_group"],
                "generation_mode": c["generation_mode"],
                "claim_risk_profile": "high_claim_or_evidence_boundary" if c["generation_mode"] == "evidence_bound_candidate" else "medium_fact_slot_boundary" if c["generation_mode"] == "fact_slot_script" else "low_or_creative_boundary",
                "store_display_or_guide_action_sample": c["generation_mode"] == "display_solution",
                "output_types": ["douyin_short_video_script", "xiaohongshu_post"],
            })
    return {
        "standard": {
            "standard_id": "P7C-SCALE-DECISION-STANDARD-v0.1",
            "formal_schema_contract": False,
            "ontology_truth_source": False,
            "KE_admission_standard": False,
            "review_roles": {"final_scale_decision_authority": "founder", "codex_final_scale_authority": False},
            "static_thresholds": {"hard_gate_fail_rate_max": 0.05, "A_grade_rate_min": 0.3, "A_or_B_grade_rate_min": 0.65, "D_grade_rate_max": 0.1, "average_CPSS_min": 76, "median_CPSS_min": 75, "each_core_P0_group_A_or_B_min": 3},
            "runtime_ab_thresholds": {"B_preferred_rate_min": 0.6, "visual_anchor_lift_required": True, "human_action_lift_required": True, "spoken_line_lift_required": True, "courseware_body_must_not_increase": True, "hard_claim_risk_must_not_increase": True, "governance_leakage_forbidden": True},
            "routing_model": {"primary_disposition": {"exactly_one": True}, "secondary_candidate_tags": {"multi_select": True}},
            "CPSS_does_not_authorize": ["Serving"],
            "content_kernel_does_not_mean": ["direct_context_bundle_ready"],
        },
        "heatmap": {"source": "existing_expert_review", "full_rescore_performed": False, "capability_groups": copy.deepcopy(EXPECTED_HEATMAP)},
        "sample_plan": {"sample_count": 12, "runtime_ab_executed_by_this_task": False, "model_prompt_parameters_to_be_frozen_in_next_task": True, "samples": samples},
        "scalability": {"gate_status": "PENDING", "execution_scalability_gate_passed": False, "expand_to_3600_allowed": False, "required_capabilities": {k: {"status": "PENDING"} for k in ["deterministic_assignment_consumption", "checkpoint_and_resume", "per_microbatch_stop", "provenance_trace", "cost_guard", "duplicate_drift_monitor", "failure_resume_protocol"]}},
        "hold": {"final_scale_decision": "HOLD", "expand_to_3600_allowed": False, "midbatch_300_600_allowed": False, "real_runtime_AB": "PENDING", "execution_scalability_gate": "PENDING", "founder_final_scale_decision": "NOT_ISSUED", "next_allowed_task": {"task_id": "GKB-CONTENT-KERNEL-REAL-RUNTIME-AB-001"}, "readiness": {"candidatepack_ready": False}},
        "cards": cards,
        "quality": {"evaluated_count": 120, "CPSS_avg": 92.2, "score_detail_source": "summary_only", "routing_summary": {"content_kernel_candidate": 100, "content_kernel_candidate_with_review_caveat": 5, "needs_fuel_repair_or_manual_polish": 12, "strategy_rule_candidate_or_rewrite": 3, "reject": 0}},
        "user_kernel": {"entries": [{"candidate_id": cid} for cid in ids]},
        "review_kernel": {"entries": [{"candidate_id": cid} for cid in ids]},
        "ledger": {"generation_unlocked": False, "expand_to_3600_allowed": False, "readiness": {k: False for k in READINESS_KEYS}, "steps": [{"step_id": "P7C_SCALE_PREP", "status": "DONE"}, {"step_id": "P7C-AB", "status": "NEXT", "task_id": "GKB-CONTENT-KERNEL-REAL-RUNTIME-AB-001"}, {"step_id": "P7C_SCALE", "status": "BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY"}, {"step_id": "P7D", "status": "BLOCKED_BY_P7C_SCALE_DECISION"}, {"step_id": "P8", "status": "BLOCKED_BY_P7D"}]},
        "prior_report": {"status": "PASS", "error_count": 0},
    }


def selftest(_: Path) -> int:
    base = fixture_bundle()
    cases: list[tuple[str, dict[str, Any], bool]] = [("positive", base, False)]

    def bad(name: str, mutator) -> None:
        b = copy.deepcopy(base)
        mutator(b)
        cases.append((name, b, True))

    bad("candidate_sample_id_not_found", lambda b: b["sample_plan"]["samples"][0].__setitem__("candidate_id", "NOPE"))
    bad("duplicate_runtime_sample", lambda b: b["sample_plan"]["samples"][1].__setitem__("candidate_id", b["sample_plan"]["samples"][0]["candidate_id"]))
    bad("wrong_4_4_4_distribution", lambda b: b["sample_plan"]["samples"][0].__setitem__("support_bucket", "medium_support"))
    bad("missing_generation_mode_coverage", lambda b: [s.__setitem__("generation_mode", "creative_prototype") for s in b["sample_plan"]["samples"]])
    bad("missing_claim_risk_samples", lambda b: [s.__setitem__("claim_risk_profile", "low_or_creative_boundary") for s in b["sample_plan"]["samples"]])
    bad("missing_store_display_samples", lambda b: [s.__setitem__("store_display_or_guide_action_sample", False) for s in b["sample_plan"]["samples"]])
    bad("fabricated_per_item_CPSS", lambda b: b["sample_plan"]["samples"][0].__setitem__("CPSS_total", 99))
    bad("overlapping_primary_dispositions", lambda b: b["standard"]["routing_model"]["primary_disposition"].__setitem__("exactly_one", False))
    bad("raw_kernel_marked_context_bundle_ready", lambda b: b["standard"].__setitem__("content_kernel_does_not_mean", []))
    bad("runtime_AB_pending_but_3600_allowed", lambda b: b["hold"].__setitem__("expand_to_3600_allowed", True))
    bad("scalability_pending_but_3600_allowed", lambda b: b["scalability"].__setitem__("expand_to_3600_allowed", True))
    bad("Codex_marked_final_scale_authority", lambda b: b["standard"]["review_roles"].__setitem__("codex_final_scale_authority", True))
    bad("original_review_or_kernel_modified", lambda b: b["prior_report"].__setitem__("status", "FAIL"))
    bad("readiness_or_downstream_flag_true", lambda b: b["ledger"]["readiness"].__setitem__("RAG_ready", True))

    failures = []
    for name, bundle, should_fail in cases:
        errs = validate(bundle, live=False)
        if should_fail and not errs:
            failures.append(f"negative unexpectedly passed: {name}")
        if not should_fail and errs:
            failures.append(f"positive failed: {errs[:10]}")
    status = "PASS" if not failures else "FAIL"
    print(json.dumps({"status": status, "case_count": len(cases), "failures": failures}, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def main() -> int:
    if not __debug__:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "refuses python -O"}))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "pyyaml unavailable"}))
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--workspace-root", default=".")
    ap.add_argument("--report-out")
    args = ap.parse_args()
    ws = Path(args.workspace_root).resolve()
    if args.selftest:
        return selftest(ws)
    if args.live:
        return run_live(ws, args.report_out)
    ap.error("one of --live / --selftest required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
