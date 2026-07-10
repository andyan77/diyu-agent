#!/usr/bin/env python3
"""
P7C-REVIEW checker.

This gates GKB-SCOPED-120-QUALITY-REVIEW-AND-CONTENT-KERNEL-EXTRACTION-001.
It consumes the already committed scoped-120 generation outputs plus external
CPSS expert-review artifacts, then verifies review closeout and content-kernel
extraction. It must not generate drafts, rewrite the original 120 rich bodies,
or materialize Serving/RAG/DIFY/CandidatePack/KE.

Important route note: the immutable P7C-GEN baseline report at
022324017c7c761495a4d56e6f51adda8efd72f9 is treated as the prior bundle
source. That report was produced by the committed P7C-GEN checker and records
P1..P7C-BRIEF + contract-lock all PASS. This checker verifies that report and
then independently verifies the original P7C-GEN artifacts are still unchanged.
This keeps the route idempotent without editing sealed prior checkers.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - fail-closed in main
    yaml = None


BASELINE = "022324017c7c761495a4d56e6f51adda8efd72f9"
TASK_ID = "GKB-SCOPED-120-QUALITY-REVIEW-AND-CONTENT-KERNEL-EXTRACTION-001"
STEP_ID = "P7C-REVIEW"
RUN_ID = "scoped_content_microbatch_120_001"
RUN_REL = f"07_microbatch_runs/{RUN_ID}"
REVIEW_REL = f"{RUN_REL}/review_closeout"
KERNEL_REL = f"{RUN_REL}/content_kernel_extraction"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
P7C_GEN_CHECKER = "ci/checkers/check_scoped_120_content_production_microbatch_generation.py"

ORIGINAL_120_RELS = [
    f"{RUN_REL}/knowledge_candidate_cards.yaml",
    f"{RUN_REL}/rich_body_blocks.yaml",
    f"{RUN_REL}/relation_candidates.csv",
    f"{RUN_REL}/semantic_alignment_report.json",
    f"{RUN_REL}/body_entailment_report.json",
    f"{RUN_REL}/governance_gate_report.json",
    f"{RUN_REL}/creative_gate_report.json",
    f"{RUN_REL}/generation_mode_report.json",
    f"{RUN_REL}/fact_binding_report.json",
    f"{RUN_REL}/cso_overlay_report.json",
    f"{RUN_REL}/dedupe_report.json",
    f"{RUN_REL}/style_copy_report.json",
    f"{RUN_REL}/generation_receipt.json",
    f"{RUN_REL}/scoped_120_closeout.v0.1.md",
]

REVIEW_FILES = [
    f"{REVIEW_REL}/expert_review_input_digest.v0.1.yaml",
    f"{REVIEW_REL}/cpss_quality_review_closeout.v0.1.yaml",
    f"{REVIEW_REL}/cpss_priority_review_queue.v0.1.yaml",
    f"{REVIEW_REL}/cpss_routing_decision.v0.1.yaml",
    f"{REVIEW_REL}/runtime_proxy_ab_summary.v0.1.yaml",
    f"{REVIEW_REL}/runtime_ab_followup_plan.v0.1.yaml",
    f"{REVIEW_REL}/scoped_120_review_closeout.v0.1.md",
]
KERNEL_FILES = [
    f"{KERNEL_REL}/content_kernel_manifest.v0.1.yaml",
    f"{KERNEL_REL}/user_visible_kernel_matrix.v0.1.yaml",
    f"{KERNEL_REL}/review_packet_kernel_matrix.v0.1.yaml",
    f"{KERNEL_REL}/content_kernel_candidate_matrix.v0.1.yaml",
    f"{KERNEL_REL}/content_kernel_source_trace_index.v0.1.yaml",
    f"{KERNEL_REL}/content_kernel_quality_bucket_index.v0.1.yaml",
    f"{KERNEL_REL}/content_kernel_extraction_closeout.v0.1.md",
]

ALLOWED_WRITE_PREFIXES = (
    f"{REVIEW_REL}/",
    f"{KERNEL_REL}/",
    "ci/checkers/check_scoped_120_quality_review_and_content_kernel_extraction.py",
    "ci/fixtures/scoped_120_quality_review_and_content_kernel_extraction/",
    "ci/reports/scoped_120_quality_review_and_content_kernel_extraction_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/grc_scoped_120_quality_review_and_content_kernel_extraction_report.md",
    "docs/reports/grc_scoped_120_quality_review_and_content_kernel_extraction_receipt.json",
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
    "07_microbatch_runs/batch_summaries",
    "07_microbatch_runs/run_manifest.v0.1.yaml",
    "07_microbatch_runs/microbatch_index.v0.1.csv",
]
READINESS_KEYS = [
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_ready",
    "generation_allowed",
    "generation_eligible",
    "production_servable",
    "release_ready",
]
C_GRADE = {"SCM120-CAND-101", "SCM120-CAND-059", "SCM120-CAND-106"}
B_GRADE = {
    "SCM120-CAND-023",
    "SCM120-CAND-030",
    "SCM120-CAND-045",
    "SCM120-CAND-047",
    "SCM120-CAND-062",
    "SCM120-CAND-080",
    "SCM120-CAND-083",
    "SCM120-CAND-103",
    "SCM120-CAND-109",
    "SCM120-CAND-110",
    "SCM120-CAND-111",
    "SCM120-CAND-113",
}
RECEIPT_ASSIGNMENTS = {
    "SCM120-A032",
    "SCM120-A033",
    "SCM120-A035",
    "SCM120-A037",
    "SCM120-A059",
    "SCM120-A062",
    "SCM120-A101",
    "SCM120-A102",
    "SCM120-A106",
}


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_report(path: str | None, report: dict[str, Any]) -> None:
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _status_paths(ws: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(ws), "status", "--short", "--untracked-files=all"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ["<git-status-failed>"]
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        paths.append(line[3:] if len(line) > 3 else line.strip())
    return paths


def _allowed(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in ALLOWED_WRITE_PREFIXES)


def _git_show(ws: Path, commit: str, rel: str) -> bytes | None:
    proc = subprocess.run(["git", "-C", str(ws), "show", f"{commit}:{rel}"], capture_output=True)
    if proc.returncode != 0:
        return None
    return proc.stdout


def _run_p7c_gen_prior_bundle(ws: Path) -> dict[str, Any]:
    rel = "ci/reports/scoped_120_content_production_microbatch_generation_report.v0.1.json"
    proc = subprocess.run(["git", "-C", str(ws), "show", f"{BASELINE}:{rel}"], capture_output=True, text=True)
    if proc.returncode != 0:
        return {"p7c_gen": 97, "error": proc.stderr[-1000:], "source": "baseline_committed_report_missing"}
    try:
        data = json.loads(proc.stdout)
    except Exception as exc:
        return {"p7c_gen": 96, "error": str(exc), "source": "baseline_committed_report_malformed"}
    ok = (
        data.get("status") == "PASS"
        and data.get("error_count") == 0
        and all(code == 0 for code in (data.get("prior_checkers") or {}).values())
    )
    return {
        "p7c_gen": 0 if ok else 1,
        "prior_checkers": data.get("prior_checkers", {}),
        "source": f"{BASELINE}:{rel}",
        "draft_count": data.get("draft_count"),
        "assignment_count": data.get("assignment_count"),
    }


def _load_live_bundle(ws: Path) -> dict[str, Any]:
    cards = _read_yaml(ws / f"{RUN_REL}/knowledge_candidate_cards.yaml")["scoped_120_candidate_cards"]["candidates"]
    blocks = _read_yaml(ws / f"{RUN_REL}/rich_body_blocks.yaml")["scoped_120_rich_body_blocks"]["blocks"]
    receipt = _read_json(ws / f"{RUN_REL}/generation_receipt.json")
    digest = _read_yaml(ws / f"{REVIEW_REL}/expert_review_input_digest.v0.1.yaml")["expert_review_input_digest"]
    closeout = _read_yaml(ws / f"{REVIEW_REL}/cpss_quality_review_closeout.v0.1.yaml")["cpss_quality_review_closeout"]
    queue = _read_yaml(ws / f"{REVIEW_REL}/cpss_priority_review_queue.v0.1.yaml")["cpss_priority_review_queue"]
    routing = _read_yaml(ws / f"{REVIEW_REL}/cpss_routing_decision.v0.1.yaml")["cpss_routing_decision"]
    runtime = _read_yaml(ws / f"{REVIEW_REL}/runtime_proxy_ab_summary.v0.1.yaml")["runtime_proxy_ab_summary"]
    manifest = _read_yaml(ws / f"{KERNEL_REL}/content_kernel_manifest.v0.1.yaml")["content_kernel_manifest"]
    user = _read_yaml(ws / f"{KERNEL_REL}/user_visible_kernel_matrix.v0.1.yaml")["user_visible_kernel_matrix"]
    review = _read_yaml(ws / f"{KERNEL_REL}/review_packet_kernel_matrix.v0.1.yaml")["review_packet_kernel_matrix"]
    matrix = _read_yaml(ws / f"{KERNEL_REL}/content_kernel_candidate_matrix.v0.1.yaml")["content_kernel_candidate_matrix"]
    trace = _read_yaml(ws / f"{KERNEL_REL}/content_kernel_source_trace_index.v0.1.yaml")["content_kernel_source_trace_index"]
    buckets = _read_yaml(ws / f"{KERNEL_REL}/content_kernel_quality_bucket_index.v0.1.yaml")["content_kernel_quality_bucket_index"]
    ledger = _read_yaml(ws / LEDGER_REL)["grc_3600_execution_plan_status"]
    receipt_doc = _read_json(ws / "docs/reports/grc_scoped_120_quality_review_and_content_kernel_extraction_receipt.json")
    return {
        "cards": cards,
        "blocks": blocks,
        "receipt": receipt,
        "digest": digest,
        "closeout": closeout,
        "queue": queue,
        "routing": routing,
        "runtime": runtime,
        "manifest": manifest,
        "user": user,
        "review": review,
        "matrix": matrix,
        "trace": trace,
        "buckets": buckets,
        "ledger": ledger,
        "receipt_doc": receipt_doc,
    }


def _validate_bundle(bundle: dict[str, Any], *, live: bool) -> list[str]:
    errors: list[str] = []

    cards = bundle["cards"]
    blocks = bundle["blocks"]
    ids = {c.get("candidate_id") for c in cards}
    assign_to_cand = {c.get("generation_assignment_id"): c.get("candidate_id") for c in cards}
    if len(cards) != 120 or len(blocks) != 120 or len(ids) != 120:
        errors.append("source scoped 120 card/body count mismatch")

    digest = bundle["digest"]
    if digest.get("review_id") != "EXPERT-REVIEW-SCOPED-120-CPSS-001":
        errors.append("expert review id mismatch")
    if digest.get("repo_head_reviewed") != BASELINE:
        errors.append("expert digest repo head mismatch")
    if digest.get("evaluated_count") != 120 or float(digest.get("CPSS_avg", 0)) != 92.2:
        errors.append("expert CPSS summary mismatch")
    if digest.get("grade_distribution") != {"A_85_plus": 105, "B_75_84": 12, "C_60_74": 3, "D_below_60": 0}:
        errors.append("grade distribution mismatch")
    for src in digest.get("source_files", []):
        if src.get("provenance") != "external_tmp_read_only_unversioned":
            errors.append("expert source provenance must be external_tmp_read_only_unversioned")

    closeout = bundle["closeout"]
    expected_summary = {
        "content_kernel_candidate": 100,
        "content_kernel_candidate_with_review_caveat": 5,
        "needs_fuel_repair_or_manual_polish": 12,
        "strategy_rule_candidate_or_rewrite": 3,
        "reject": 0,
    }
    if closeout.get("routing_summary") != expected_summary:
        errors.append("quality closeout routing summary mismatch")
    for k in ["new_draft_generated", "original_120_modified", "runtime_ab_executed_by_this_task",
              "ready_for_direct_serving_or_DIFY", "ready_for_raw_context_bundle_ingestion"]:
        if closeout.get(k) is not False:
            errors.append(f"closeout {k} must be false")
    if closeout.get("score_detail_source") != "summary_only" or closeout.get("needs_score_detail_reconciliation") is not True:
        errors.append("CPSS detail source must be summary_only with reconciliation flag")

    queue = bundle["queue"]
    c_queue = {x.get("candidate_id") for x in queue.get("c_grade_must_review_first", [])}
    b_queue = {x.get("candidate_id") for x in queue.get("b_grade_manual_review_queue", [])}
    receipt_assign = {x.get("assignment_id") for x in queue.get("receipt_review_first", [])}
    if c_queue != C_GRADE:
        errors.append("C grade queue mismatch")
    if b_queue != B_GRADE:
        errors.append("B grade queue mismatch")
    if receipt_assign != RECEIPT_ASSIGNMENTS:
        errors.append("receipt first-review queue mismatch")
    for aid in RECEIPT_ASSIGNMENTS:
        if aid not in assign_to_cand:
            errors.append(f"receipt assignment has no candidate mapping: {aid}")

    runtime = bundle["runtime"]
    if runtime.get("sample_count") != 12 or runtime.get("runtime_ab_executed_by_this_task") is not False:
        errors.append("runtime proxy summary must remain 12-sample and not executed by this task")
    if "DIFY" in str(runtime.get("conclusion", "")) and runtime.get("runtime_ab_executed_by_this_task") is not False:
        errors.append("runtime proxy cannot claim DIFY validation")

    manifest = bundle["manifest"]
    if manifest.get("extraction_counts") != {"user_visible_kernel_count": 120, "review_packet_kernel_count": 120, "source_trace_count": 120}:
        errors.append("kernel manifest counts mismatch")
    for k in ["formal_schema_contract", "ontology_truth_source", "serving_projection", "rag_context_bundle",
              "dify_workflow", "candidatepack_ready"]:
        if manifest.get(k) is not False:
            errors.append(f"kernel manifest {k} must be false")

    user = bundle["user"]
    review = bundle["review"]
    if user.get("kernel_count") != 120 or len(user.get("entries", [])) != 120:
        errors.append("user visible kernel count mismatch")
    if review.get("kernel_count") != 120 or len(review.get("entries", [])) != 120:
        errors.append("review packet kernel count mismatch")
    user_ids = {e.get("candidate_id") for e in user.get("entries", [])}
    review_ids = {e.get("candidate_id") for e in review.get("entries", [])}
    if user_ids != ids or review_ids != ids:
        errors.append("kernel ids must match source candidate ids")
    forbidden_user_keys = {"forbidden_claims", "required_fact_slots", "evidence_boundary", "downgrade_path", "release_status"}
    for e in user.get("entries", []):
        if forbidden_user_keys & set(e):
            errors.append(f"user_visible_kernel has review-only keys: {e.get('candidate_id')}")
        if e.get("visibility") != "user_visible_kernel_candidate":
            errors.append("user_visible_kernel visibility mismatch")
        if not e.get("source_trace"):
            errors.append(f"user_visible_kernel missing source_trace: {e.get('candidate_id')}")
        if e.get("not_serving_projection") is not True or e.get("not_rag_context_bundle") is not True:
            errors.append(f"user_visible_kernel must not be serving/rag: {e.get('candidate_id')}")
    for e in review.get("entries", []):
        if e.get("visibility_status") != "review_only" or e.get("must_not_be_user_visible_as_written") is not True:
            errors.append(f"review_packet visibility failure: {e.get('candidate_id')}")
        rel = e.get("release_status", {})
        if any(rel.get(k) is not False for k in ["accepted_domain_knowledge", "candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "production_servable"]):
            errors.append(f"review_packet release flag true: {e.get('candidate_id')}")
        if e.get("generation_mode") in {"fact_slot_script", "evidence_bound_candidate", "display_solution"} and e.get("fact_slot_preservation_required") is not True:
            errors.append(f"mode fact/slot preservation missing: {e.get('candidate_id')}")

    matrix = bundle["matrix"]
    buckets = matrix.get("routing_buckets", {})
    if matrix.get("score_detail_source") != "summary_only" or matrix.get("needs_score_detail_reconciliation") is not True:
        errors.append("candidate matrix must be summary_only")
    if matrix.get("total_candidates") != 120:
        errors.append("candidate matrix total mismatch")
    if buckets.get("content_kernel_candidate", {}).get("count") != 100:
        errors.append("clean content kernel count mismatch")
    if "candidate_ids" in buckets.get("content_kernel_candidate", {}):
        errors.append("clean A pool must not materialize invented per-item candidate_ids")
    if set(buckets.get("content_kernel_candidate_with_review_caveat", {}).get("candidate_ids", [])) != {
        "SCM120-CAND-032", "SCM120-CAND-033", "SCM120-CAND-035", "SCM120-CAND-037", "SCM120-CAND-102"
    }:
        errors.append("A caveat candidate ids mismatch")
    if set(buckets.get("needs_fuel_repair_or_manual_polish", {}).get("candidate_ids", [])) != B_GRADE:
        errors.append("B routing ids mismatch")
    if set(buckets.get("strategy_rule_candidate_or_rewrite", {}).get("candidate_ids", [])) != C_GRADE:
        errors.append("C routing ids mismatch")

    trace = bundle["trace"]
    if trace.get("trace_count") != 120 or len(trace.get("entries", [])) != 120:
        errors.append("source trace count mismatch")
    if {e.get("candidate_id") for e in trace.get("entries", [])} != ids:
        errors.append("source trace ids mismatch")

    bucket_index = bundle["buckets"]
    if bucket_index.get("grade_distribution_summary") != {"A_85_plus": 105, "B_75_84": 12, "C_60_74": 3, "D_below_60": 0}:
        errors.append("quality bucket grade distribution mismatch")

    ledger = bundle["ledger"]
    steps = {s.get("step_id"): s for s in ledger.get("steps", [])}
    if steps.get("P7A", {}).get("status") != "DONE":
        errors.append("P7A.status must remain DONE")
    if steps.get("P7A", {}).get("classification") != "agent_authored_quality_probe_pass":
        errors.append("P7A.classification mismatch")
    if steps.get("P7C-REVIEW", {}).get("status") != "DONE" or steps.get("P7C-REVIEW", {}).get("task_id") != TASK_ID:
        errors.append("P7C-REVIEW must be DONE for this task")
    if steps.get("P7C-AB", {}).get("status") != "NEXT":
        errors.append("P7C-AB must be NEXT")
    if steps.get("P7D", {}).get("status") != "BLOCKED_BY_P7C_SCALE_DECISION":
        errors.append("P7D must be blocked by P7C scale decision")
    readiness = ledger.get("readiness", {})
    if any(readiness.get(k) is not False for k in READINESS_KEYS if k in readiness):
        errors.append("ledger readiness flag true")
    if ledger.get("generation_unlocked") is not False:
        errors.append("ledger generation_unlocked must be false")
    if not ledger.get("route_migration_4", {}).get("no_old_checker_edited"):
        errors.append("route_migration_4 missing no_old_checker_edited")

    receipt_doc = bundle["receipt_doc"]
    for k in ["runtime_ab_executed_by_this_task", "direct_serving_ready", "raw_context_bundle_ready",
              "new_draft_generated", "original_120_modified", "candidatepack_created", "KE_RAG_DIFY_touched"]:
        if receipt_doc.get(k) is not False:
            errors.append(f"receipt {k} must be false")
    if receipt_doc.get("evaluated_count") != 120 or receipt_doc.get("CPSS_avg") != 92.2:
        errors.append("receipt summary mismatch")

    if live:
        prior = bundle.get("prior_results", {})
        if prior.get("p7c_gen") != 0:
            errors.append(f"P7C-GEN baseline prior bundle failed: {prior}")
        for name, code in (prior.get("prior_checkers") or {}).items():
            if code != 0:
                errors.append(f"baseline prior checker failed: {name}={code}")
        for rel in ORIGINAL_120_RELS:
            now_path = bundle["workspace"] / rel
            diff = subprocess.run(
                ["git", "-C", str(bundle["workspace"]), "diff", "--quiet", BASELINE, "--", rel],
                capture_output=True,
                text=True,
            )
            if not now_path.exists() or diff.returncode != 0:
                errors.append(f"original P7C-GEN artifact modified or missing: {rel}")
        for rel in REVIEW_FILES + KERNEL_FILES:
            if not (bundle["workspace"] / rel).exists():
                errors.append(f"required output missing: {rel}")
        status_paths = _status_paths(bundle["workspace"])
        outside = [p for p in status_paths if p != "<git-status-failed>" and not _allowed(p)]
        if outside:
            errors.append(f"git status outside allowed write surface: {outside}")
        for rel in FORBIDDEN_PATHS:
            if (bundle["workspace"] / rel).exists():
                errors.append(f"forbidden downstream path exists/created: {rel}")

    return errors


def run_live(ws: Path, report_out: str | None) -> int:
    bundle = _load_live_bundle(ws)
    bundle["workspace"] = ws
    bundle["prior_results"] = _run_p7c_gen_prior_bundle(ws)
    errors = _validate_bundle(bundle, live=True)
    status = "PASS" if not errors else "FAIL"
    report = {
        "checker": Path(__file__).name,
        "task_id": TASK_ID,
        "step_id": STEP_ID,
        "status": status,
        "error_count": len(errors),
        "errors": errors[:80],
        "evaluated_count": bundle["closeout"].get("evaluated_count"),
        "CPSS_avg": bundle["closeout"].get("CPSS_avg"),
        "user_visible_kernel_count": bundle["user"].get("kernel_count"),
        "review_packet_kernel_count": bundle["review"].get("kernel_count"),
        "content_kernel_candidate_count": bundle["matrix"].get("routing_buckets", {}).get("content_kernel_candidate", {}).get("count"),
        "prior_results": bundle.get("prior_results"),
        "readiness_false": True,
    }
    _write_report(report_out, report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not errors else 1


def _fixture_bundle() -> dict[str, Any]:
    ids = {f"SCM120-CAND-{i:03d}" for i in range(1, 121)}
    assignments = {f"SCM120-A{i:03d}": f"SCM120-CAND-{i:03d}" for i in range(1, 121)}
    cards = [{"candidate_id": cid, "generation_assignment_id": f"SCM120-A{int(cid[-3:]):03d}"} for cid in sorted(ids)]
    entries = [
        {
            "candidate_id": cid,
            "generation_assignment_id": f"SCM120-A{int(cid[-3:]):03d}",
            "visibility": "user_visible_kernel_candidate",
            "source_trace": {"body": "ok"},
            "not_serving_projection": True,
            "not_rag_context_bundle": True,
        }
        for cid in sorted(ids)
    ]
    review_entries = [
        {
            "candidate_id": cid,
            "generation_assignment_id": f"SCM120-A{int(cid[-3:]):03d}",
            "generation_mode": "fact_slot_script",
            "visibility_status": "review_only",
            "must_not_be_user_visible_as_written": True,
            "fact_slot_preservation_required": True,
            "release_status": {
                "accepted_domain_knowledge": False,
                "candidatepack_ready": False,
                "KE_ready": False,
                "RAG_ready": False,
                "DIFY_ready": False,
                "production_servable": False,
            },
        }
        for cid in sorted(ids)
    ]
    steps = [
        {"step_id": "P7A", "status": "DONE", "classification": "agent_authored_quality_probe_pass"},
        {"step_id": "P7C-REVIEW", "status": "DONE", "task_id": TASK_ID},
        {"step_id": "P7C-AB", "status": "NEXT"},
        {"step_id": "P7D", "status": "BLOCKED_BY_P7C_SCALE_DECISION"},
    ]
    return {
        "cards": cards,
        "blocks": [{"candidate_id": cid} for cid in sorted(ids)],
        "receipt": {},
        "digest": {
            "review_id": "EXPERT-REVIEW-SCOPED-120-CPSS-001",
            "repo_head_reviewed": BASELINE,
            "evaluated_count": 120,
            "CPSS_avg": 92.2,
            "grade_distribution": {"A_85_plus": 105, "B_75_84": 12, "C_60_74": 3, "D_below_60": 0},
            "source_files": [{"provenance": "external_tmp_read_only_unversioned"}],
        },
        "closeout": {
            "routing_summary": {
                "content_kernel_candidate": 100,
                "content_kernel_candidate_with_review_caveat": 5,
                "needs_fuel_repair_or_manual_polish": 12,
                "strategy_rule_candidate_or_rewrite": 3,
                "reject": 0,
            },
            "new_draft_generated": False,
            "original_120_modified": False,
            "runtime_ab_executed_by_this_task": False,
            "ready_for_direct_serving_or_DIFY": False,
            "ready_for_raw_context_bundle_ingestion": False,
            "score_detail_source": "summary_only",
            "needs_score_detail_reconciliation": True,
        },
        "queue": {
            "c_grade_must_review_first": [{"candidate_id": cid} for cid in C_GRADE],
            "b_grade_manual_review_queue": [{"candidate_id": cid} for cid in B_GRADE],
            "receipt_review_first": [{"assignment_id": aid} for aid in RECEIPT_ASSIGNMENTS],
        },
        "routing": {},
        "runtime": {"sample_count": 12, "runtime_ab_executed_by_this_task": False, "conclusion": "proxy"},
        "manifest": {
            "extraction_counts": {"user_visible_kernel_count": 120, "review_packet_kernel_count": 120, "source_trace_count": 120},
            "formal_schema_contract": False,
            "ontology_truth_source": False,
            "serving_projection": False,
            "rag_context_bundle": False,
            "dify_workflow": False,
            "candidatepack_ready": False,
        },
        "user": {"kernel_count": 120, "entries": entries},
        "review": {"kernel_count": 120, "entries": review_entries},
        "matrix": {
            "score_detail_source": "summary_only",
            "needs_score_detail_reconciliation": True,
            "total_candidates": 120,
            "routing_buckets": {
                "content_kernel_candidate": {"count": 100, "member_materialization": "derived_pool_not_listed_to_avoid_invented_per_item_scores"},
                "content_kernel_candidate_with_review_caveat": {
                    "candidate_ids": ["SCM120-CAND-032", "SCM120-CAND-033", "SCM120-CAND-035", "SCM120-CAND-037", "SCM120-CAND-102"]
                },
                "needs_fuel_repair_or_manual_polish": {"candidate_ids": sorted(B_GRADE)},
                "strategy_rule_candidate_or_rewrite": {"candidate_ids": sorted(C_GRADE)},
            },
        },
        "trace": {"trace_count": 120, "entries": [{"candidate_id": cid} for cid in sorted(ids)]},
        "buckets": {"grade_distribution_summary": {"A_85_plus": 105, "B_75_84": 12, "C_60_74": 3, "D_below_60": 0}},
        "ledger": {"steps": steps, "readiness": {k: False for k in READINESS_KEYS}, "generation_unlocked": False, "route_migration_4": {"no_old_checker_edited": True}},
        "receipt_doc": {
            "runtime_ab_executed_by_this_task": False,
            "direct_serving_ready": False,
            "raw_context_bundle_ready": False,
            "new_draft_generated": False,
            "original_120_modified": False,
            "candidatepack_created": False,
            "KE_RAG_DIFY_touched": False,
            "evaluated_count": 120,
            "CPSS_avg": 92.2,
        },
    }


def selftest(_: Path) -> int:
    base = _fixture_bundle()
    cases: list[tuple[str, dict[str, Any], bool]] = [("positive", base, False)]

    def bad(name: str, mutator) -> None:
        b = copy.deepcopy(base)
        mutator(b)
        cases.append((name, b, True))

    bad("new_draft_generated", lambda b: b["closeout"].__setitem__("new_draft_generated", True))
    bad("original_120_modified", lambda b: b["closeout"].__setitem__("original_120_modified", True))
    bad("serving_ready", lambda b: b["closeout"].__setitem__("ready_for_direct_serving_or_DIFY", True))
    bad("wrong_cpss", lambda b: b["digest"].__setitem__("CPSS_avg", 100))
    bad("missing_c_queue", lambda b: b["queue"].__setitem__("c_grade_must_review_first", []))
    bad("invented_a_ids", lambda b: b["matrix"]["routing_buckets"]["content_kernel_candidate"].__setitem__("candidate_ids", ["SCM120-CAND-001"]))
    bad("user_contains_forbidden_claims", lambda b: b["user"]["entries"][0].__setitem__("forbidden_claims", "bad"))
    bad("review_packet_user_visible", lambda b: b["review"]["entries"][0].__setitem__("visibility_status", "user_visible"))
    bad("release_flag_true", lambda b: b["review"]["entries"][0]["release_status"].__setitem__("candidatepack_ready", True))
    bad("missing_kernel", lambda b: b["user"].__setitem__("kernel_count", 119))
    bad("runtime_executed", lambda b: b["runtime"].__setitem__("runtime_ab_executed_by_this_task", True))
    bad("p7a_status_changed", lambda b: b["ledger"]["steps"][0].__setitem__("status", "DONE_AS_QUALITY_PROBE"))
    bad("p7d_unblocked", lambda b: b["ledger"]["steps"][3].__setitem__("status", "NEXT"))
    bad("readiness_true", lambda b: b["ledger"]["readiness"].__setitem__("RAG_ready", True))

    failures = []
    for name, bundle, should_fail in cases:
        errs = _validate_bundle(bundle, live=False)
        if should_fail and not errs:
            failures.append(f"negative unexpectedly passed: {name}")
        if not should_fail and errs:
            failures.append(f"positive failed: {errs[:10]}")
    status = "PASS" if not failures else "FAIL"
    print(json.dumps({"status": status, "case_count": len(cases), "failures": failures}, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def main() -> int:
    if not __debug__:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "refuses to run under python -O"}))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "pyyaml unavailable"}))
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--report-out")
    args = parser.parse_args()
    ws = Path(args.workspace_root).resolve()
    if args.selftest:
        return selftest(ws)
    if args.live:
        return run_live(ws, args.report_out)
    parser.error("one of --live / --selftest required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
