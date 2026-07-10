#!/usr/bin/env python3
"""Fail-closed checker for P7C execution scalability proof."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


BASELINE = "acfd19494aa0f69ee15582f9dbcef596ff80c1e6"
TASK_ID = "GKB-P7C-EXECUTION-SCALABILITY-PROOF-AND-SCALE-DECISION-PACKET-001"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
OUT_REL = f"{RUN_REL}/review_closeout/execution_scalability_001"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
RUNNER = "ci/runners/run_p7c_execution_scalability_probe.py"

REQUIRED_FILES = [
    f"{OUT_REL}/p7c_ab_002_guardian_evidence.v0.1.yaml",
    f"{OUT_REL}/execution_scalability_contract.v0.1.yaml",
    f"{OUT_REL}/scale_work_item_manifest.v0.1.jsonl",
    f"{OUT_REL}/scale_work_item_manifest_summary.v0.1.yaml",
    f"{OUT_REL}/full_manifest_dry_run_events.v0.1.jsonl",
    f"{OUT_REL}/checkpoint_resume_results.v0.1.yaml",
    f"{OUT_REL}/fault_injection_results.v0.1.yaml",
    f"{OUT_REL}/duplicate_drift_monitor_results.v0.1.yaml",
    f"{OUT_REL}/native_execution_budget_guard_results.v0.1.yaml",
    f"{OUT_REL}/execution_scalability_result.v0.1.yaml",
    f"{OUT_REL}/founder_scale_decision_packet.v0.1.yaml",
]

IMMUTABLE_RELS = [
    f"{RUN_REL}/knowledge_candidate_cards.yaml",
    f"{RUN_REL}/rich_body_blocks.yaml",
    f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/review_packet_kernel_matrix.v0.1.yaml",
    f"{RUN_REL}/review_closeout/runtime_ab_001/runtime_ab_result.v0.1.yaml",
    f"{RUN_REL}/review_closeout/runtime_ab_002/runtime_ab_result.v0.1.yaml",
    f"{RUN_REL}/review_closeout/runtime_ab_002/runtime_ab_generation_records.v0.1.jsonl",
    f"{RUN_REL}/review_closeout/runtime_ab_002/runtime_ab_blind_review_packet.v0.1.jsonl",
    f"{RUN_REL}/review_closeout/runtime_ab_002/runtime_ab_arm_key.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_scale_decision_standard.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_capability_heatmap.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_runtime_ab_sample_plan.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_execution_scalability_gate.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_scale_hold_decision.v0.1.yaml",
]

ALLOWED_WRITE_PREFIXES = (
    f"{OUT_REL}/",
    "ci/runners/run_p7c_execution_scalability_probe.py",
    "ci/checkers/check_p7c_execution_scalability.py",
    "ci/fixtures/p7c_execution_scalability/",
    "ci/reports/p7c_execution_scalability_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/p7c_execution_scalability_report.md",
    "docs/reports/p7c_execution_scalability_receipt.json",
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
    "Serving_ready",
    "production_ready",
    "generation_allowed",
    "generation_eligible",
    "production_servable",
    "release_ready",
]

CAPABILITIES = [
    "deterministic_assignment_consumption",
    "checkpoint_and_resume",
    "per_microbatch_stop",
    "provenance_trace",
    "native_execution_budget_guard",
    "duplicate_drift_monitor",
    "failure_resume_protocol",
]


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            raise ValueError(f"malformed jsonl {path}:{line_no}: {exc}") from exc
    return rows


def git_status_paths(ws: Path) -> list[str]:
    proc = subprocess.run(["git", "-C", str(ws), "status", "--short", "--untracked-files=all"], capture_output=True, text=True)
    if proc.returncode != 0:
        return ["<git-status-failed>"]
    return [line[3:] for line in proc.stdout.splitlines() if line.strip()]


def allowed(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_WRITE_PREFIXES)


def git_diff_clean(ws: Path, rel: str) -> bool:
    proc = subprocess.run(["git", "-C", str(ws), "diff", "--quiet", BASELINE, "--", rel], capture_output=True, text=True)
    return proc.returncode == 0


def run_checker(ws: Path, checker: str) -> int:
    proc = subprocess.run(["python3", checker, "--live"], cwd=ws, capture_output=True, text=True)
    return proc.returncode


def run_prior_at_baseline(ws: Path, checker: str) -> int:
    with tempfile.TemporaryDirectory(prefix="p7c_exec_prior_") as tmp:
        tmp_path = Path(tmp)
        add = subprocess.run(["git", "-C", str(ws), "worktree", "add", "--detach", "--quiet", str(tmp_path), BASELINE], capture_output=True, text=True)
        if add.returncode != 0:
            return 90
        try:
            return run_checker(tmp_path, checker)
        finally:
            subprocess.run(["git", "-C", str(ws), "worktree", "remove", "--force", str(tmp_path)], capture_output=True, text=True)


def run_priors(ws: Path) -> dict[str, int]:
    checkers = {
        "p7c_review": "ci/checkers/check_scoped_120_quality_review_and_content_kernel_extraction.py",
        "p7c_scale_prep": "ci/checkers/check_p7c_scale_gate_completion.py",
        "p7c_ab_001": "ci/checkers/check_p7c_content_kernel_runtime_ab.py",
        "p7c_ab_002": "ci/checkers/check_p7c_content_kernel_runtime_ab_002.py",
    }
    if git_status_paths(ws):
        return {name: run_prior_at_baseline(ws, checker) for name, checker in checkers.items()}
    return {name: run_checker(ws, checker) for name, checker in checkers.items()}


def rerun_runner(ws: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p7c_exec_rerun_") as tmp:
        out = Path(tmp) / "out"
        proc = subprocess.run(["python3", RUNNER, "--write-artifacts", "--output-dir", str(out)], cwd=ws, capture_output=True, text=True)
        if proc.returncode != 0:
            return {"status": "FAIL", "error": proc.stderr[-1000:] or proc.stdout[-1000:]}
        result = read_yaml(out / "execution_scalability_result.v0.1.yaml")["execution_scalability_result"]
        summary = read_yaml(out / "scale_work_item_manifest_summary.v0.1.yaml")["scale_work_item_manifest_summary"]
        events = read_jsonl(out / "full_manifest_dry_run_events.v0.1.jsonl")
        return {
            "status": result.get("status"),
            "work_item_count": summary.get("work_item_count"),
            "manifest_digest": summary.get("manifest_digest"),
            "clean_run_a_digest": result.get("clean_run_a_digest"),
            "clean_run_b_digest": result.get("clean_run_b_digest"),
            "event_count": len(events),
        }


def validate_bundle(ws: Path, *, run_external: bool = True) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    report: dict[str, Any] = {"checker": "check_p7c_execution_scalability.py", "task_id": TASK_ID, "status": "FAIL"}

    for rel in REQUIRED_FILES:
        if not (ws / rel).exists():
            errors.append(f"missing required artifact: {rel}")
    if not (ws / RUNNER).exists():
        errors.append("missing runner")
    if errors:
        return errors, report

    try:
        guardian = read_yaml(ws / REQUIRED_FILES[0])["p7c_ab_002_guardian_evidence"]
        contract = read_yaml(ws / REQUIRED_FILES[1])["execution_scalability_contract"]
        manifest = read_jsonl(ws / REQUIRED_FILES[2])
        summary = read_yaml(ws / REQUIRED_FILES[3])["scale_work_item_manifest_summary"]
        events = read_jsonl(ws / REQUIRED_FILES[4])
        checkpoint = read_yaml(ws / REQUIRED_FILES[5])["checkpoint_resume_results"]
        fault = read_yaml(ws / REQUIRED_FILES[6])["fault_injection_results"]
        duplicate = read_yaml(ws / REQUIRED_FILES[7])["duplicate_drift_monitor_results"]
        budget = read_yaml(ws / REQUIRED_FILES[8])["native_execution_budget_guard_results"]
        result = read_yaml(ws / REQUIRED_FILES[9])["execution_scalability_result"]
        packet = read_yaml(ws / REQUIRED_FILES[10])["founder_scale_decision_packet"]
        ledger = read_yaml(ws / LEDGER_REL)["grc_3600_execution_plan_status"]
    except Exception as exc:
        return [f"parse failure: {exc}"], report

    if guardian.get("source_kind") != "founder_supplied_claude_code_guardian_review" or guardian.get("transcription_only") is not True:
        errors.append("guardian evidence transcription boundary mismatch")
    if guardian.get("ab_001_evidence_status") != "invalidated_confounded_not_positive_evidence":
        errors.append("AB-001 must remain invalidated/confounded")
    if guardian.get("ab_002_execution") != "CONFIRMED_PASS" or guardian.get("combined_votes") != "72_of_72_treatment":
        errors.append("AB-002 Guardian result not transcribed")
    for key in ["not_production_ready", "not_customer_validation", "not_execution_scalability_evidence", "global_hold"]:
        if guardian.get(key) is not True:
            errors.append(f"guardian caveat missing: {key}")

    if contract.get("content_generation_allowed") is not False or contract.get("ack_value") != "NO_CONTENT_EXECUTION_ACK":
        errors.append("contract must be no-content ACK only")
    if contract.get("semantic_body_dedup_not_claimed") is not True:
        errors.append("semantic body dedup caveat missing")

    if len(manifest) != 3600:
        errors.append("manifest must contain 3600 work items")
    ids = [row.get("work_item_id") for row in manifest]
    if len(ids) != len(set(ids)):
        errors.append("work_item_id must be unique")
    cluster_counts = Counter(row.get("cluster_id") for row in manifest)
    expected_clusters = [f"mkc_{idx:03d}" for idx in range(7, 47)]
    if set(cluster_counts) != set(expected_clusters) or any(cluster_counts[cid] != 90 for cid in expected_clusters):
        errors.append("manifest must be 40 clusters x 90")
    forbidden_keys = {"draft_body_text", "generated_content", "CandidatePack body", "KE assertion", "approved_passage_text", "context_bundle", "BrandKB facts"}
    for row in manifest:
        if any(key in row for key in forbidden_keys):
            errors.append(f"manifest contains forbidden content key: {row.get('work_item_id')}")
            break
        if row.get("content_generated") is not False or row.get("candidatepack_created") is not False or row.get("production_servable") is not False:
            errors.append(f"manifest readiness/content flag drift: {row.get('work_item_id')}")
            break
        trace = row.get("provenance_trace") or {}
        if not all(trace.get(key) for key in ["canonical_scale_plan", "management_batch", "microbatch", "cluster", "P0_group", "generation_mode", "assignment_digest", "runner_version", "commit"]):
            errors.append(f"provenance trace incomplete: {row.get('work_item_id')}")
            break

    if summary.get("work_item_count") != 3600 or summary.get("content_generated") is not False:
        errors.append("manifest summary mismatch")
    if summary.get("manifest_digest") is None:
        errors.append("manifest digest missing")

    clean_a = [row for row in events if row.get("run_id") == "clean_full_run_a" and row.get("event") == "WORK_ITEM_ACK"]
    clean_b = [row for row in events if row.get("run_id") == "clean_full_run_b" and row.get("event") == "WORK_ITEM_ACK"]
    if len(clean_a) != 3600 or len(clean_b) != 3600:
        errors.append("clean dry-runs must consume 3600 items each")
    if any(row.get("ack") != "NO_CONTENT_EXECUTION_ACK" or row.get("content_generated") is not False for row in clean_a + clean_b):
        errors.append("dry-run generated content or wrong ACK")
    if len({row.get("work_item_id") for row in clean_a}) != 3600 or len({row.get("work_item_id") for row in clean_b}) != 3600:
        errors.append("dry-run duplicate/missing item")

    if checkpoint.get("status") != "PASS" or checkpoint.get("duplicate_count") != 0 or checkpoint.get("missing_count") != 0 or checkpoint.get("corrupted_checkpoint_rejected") is not True:
        errors.append("checkpoint/resume proof failed")
    if fault.get("status") != "PASS" or any(status != "PASS" for status in (fault.get("scenarios") or {}).values()):
        errors.append("fault injection proof failed")
    for key in [
        "duplicate_work_item_id_rejected",
        "duplicate_assignment_digest_rejected",
        "same_work_item_id_different_payload_rejected",
        "checkpoint_manifest_digest_mismatch_rejected",
        "completed_work_item_resubmit_rejected",
        "wrong_output_hook_work_item_id_rejected",
        "semantic_body_dedup_not_claimed",
    ]:
        if duplicate.get(key) is not True:
            errors.append(f"duplicate/drift check missing: {key}")
    for key in [
        "work_item_limit_triggered",
        "microbatch_limit_triggered",
        "retry_limit_per_item_triggered",
        "total_retry_limit_triggered",
        "hard_stop_before_next_microbatch",
        "resume_cannot_bypass_budget",
    ]:
        if budget.get(key) is not True:
            errors.append(f"budget guard missing: {key}")
    if budget.get("monetary_API_cost_applicable") is not False or budget.get("fake_api_cost_recorded") is not False:
        errors.append("budget guard must not claim monetary API cost")

    if result.get("status") != "PASS" or result.get("work_item_count") != 3600 or result.get("actual_consumed_count") != 3600:
        errors.append("execution scalability result count/status mismatch")
    if result.get("deterministic_second_run_match") is not True:
        errors.append("second deterministic run mismatch")
    caps = result.get("capabilities") or {}
    for cap in CAPABILITIES:
        if caps.get(cap) != "PASS":
            errors.append(f"capability not PASS: {cap}")
    if result.get("execution_key", {}).get("status") != "PASS":
        errors.append("execution key must be PASS when all capabilities pass")
    if result.get("founder_final_decision", {}).get("status") != "PENDING":
        errors.append("founder decision must stay PENDING")
    if result.get("final_scale_decision") != "HOLD" or result.get("expand_to_3600_allowed") is not False or result.get("midbatch_300_600_allowed") is not False:
        errors.append("scale decision must remain HOLD/false")
    if result.get("content_generated") is not False:
        errors.append("result claims content generated")

    if packet.get("founder_final_decision") != "PENDING" or packet.get("final_scale_decision") != "HOLD":
        errors.append("founder packet must keep decision pending/HOLD")
    if packet.get("execution_key", {}).get("status") != "PASS" or len(packet.get("eligible_options", [])) != 3:
        errors.append("founder packet options/execution key mismatch")
    if "external_API_cost_not_validated" not in packet.get("unverified_risks", []):
        errors.append("native budget caveat missing from founder packet")

    migration = ledger.get("route_migration_8") or {}
    if migration.get("P7C_EXECUTION_SCALE", {}).get("operational_state") != "PASS":
        errors.append("route_migration_8 missing execution PASS operational state")
    if migration.get("founder_final_decision", {}).get("status") != "PENDING":
        errors.append("route_migration_8 founder decision must be PENDING")
    steps = {step.get("step_id"): step for step in ledger.get("steps", [])}
    expected_status = {
        "P7C-AB": "NEXT",
        "P7C_SCALE": "BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY",
        "P7C_SCALE_PREP": "DONE",
        "P7D": "BLOCKED_BY_P7C_SCALE_DECISION",
        "P8": "BLOCKED_BY_P7D",
    }
    for step, status in expected_status.items():
        if steps.get(step, {}).get("status") != status:
            errors.append(f"historical step status drifted: {step}")
    if ledger.get("generation_unlocked") is not False:
        errors.append("generation_unlocked must remain false")
    for key in READINESS_KEYS:
        if ledger.get("readiness", {}).get(key) is not False:
            errors.append(f"readiness not false: {key}")

    for rel in IMMUTABLE_RELS:
        if not git_diff_clean(ws, rel):
            errors.append(f"immutable baseline asset drifted: {rel}")
    for path in git_status_paths(ws):
        if not allowed(path):
            errors.append(f"dirty path outside allowed write surface: {path}")
    for forbidden in FORBIDDEN_PATHS:
        if (ws / forbidden).exists():
            errors.append(f"forbidden path exists: {forbidden}")

    prior_results: dict[str, int] = {}
    rerun: dict[str, Any] = {}
    if run_external:
        prior_results = run_priors(ws)
        for name, code in prior_results.items():
            if code != 0:
                errors.append(f"prior checker failed: {name}={code}")
        rerun = rerun_runner(ws)
        if rerun.get("status") != "PASS":
            errors.append("runner rerun failed")
        if rerun.get("work_item_count") != summary.get("work_item_count"):
            errors.append("runner rerun work item count mismatch")
        if rerun.get("manifest_digest") != summary.get("manifest_digest"):
            errors.append("runner rerun manifest digest mismatch")
        if rerun.get("clean_run_a_digest") != result.get("clean_run_a_digest"):
            errors.append("runner rerun clean digest mismatch")

    report.update(
        {
            "status": "PASS" if not errors else "FAIL",
            "error_count": len(errors),
            "errors": errors,
            "planned_work_item_count": len(manifest),
            "actual_consumed_count": result.get("actual_consumed_count"),
            "event_count": len(events),
            "capabilities": caps,
            "execution_key": result.get("execution_key", {}).get("status"),
            "quality_key": result.get("quality_key", {}).get("status"),
            "founder_final_decision": packet.get("founder_final_decision"),
            "final_scale_decision": result.get("final_scale_decision"),
            "expand_to_3600_allowed": result.get("expand_to_3600_allowed"),
            "content_generated": False,
            "prior_results": prior_results,
            "runner_rerun": rerun,
            "readiness_false": not any("readiness" in err for err in errors),
        }
    )
    return errors, report


def make_positive() -> dict[str, Any]:
    return {
        "manifest_count": 3600,
        "unique_ids": True,
        "clean_digests_match": True,
        "checkpoint": "PASS",
        "budget": "PASS",
        "duplicate": "PASS",
        "failure": "PASS",
        "founder": "PENDING",
        "scale": "HOLD",
    }


def validate_fixture(fx: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if fx.get("manifest_count") != 3600:
        errors.append("manifest_count")
    if fx.get("unique_ids") is not True:
        errors.append("unique_ids")
    if fx.get("clean_digests_match") is not True:
        errors.append("determinism")
    for key in ["checkpoint", "budget", "duplicate", "failure"]:
        if fx.get(key) != "PASS":
            errors.append(key)
    if fx.get("founder") != "PENDING" or fx.get("scale") != "HOLD":
        errors.append("decision")
    return errors


def selftest() -> int:
    positive = make_positive()
    cases: list[tuple[str, dict[str, Any], bool]] = [("positive", positive, True)]

    def mutated(name: str, fn) -> None:
        fx = dict(positive)
        fn(fx)
        cases.append((name, fx, False))

    mutated("count_mismatch", lambda fx: fx.update({"manifest_count": 3599}))
    mutated("duplicate_id", lambda fx: fx.update({"unique_ids": False}))
    mutated("determinism_fail", lambda fx: fx.update({"clean_digests_match": False}))
    mutated("checkpoint_fail", lambda fx: fx.update({"checkpoint": "FAIL"}))
    mutated("budget_fail", lambda fx: fx.update({"budget": "FAIL"}))
    mutated("duplicate_monitor_fail", lambda fx: fx.update({"duplicate": "FAIL"}))
    mutated("failure_protocol_fail", lambda fx: fx.update({"failure": "FAIL"}))
    mutated("founder_decided", lambda fx: fx.update({"founder": "ALLOW"}))
    mutated("scale_allowed", lambda fx: fx.update({"scale": "ALLOW_3600"}))

    failures: list[str] = []
    for name, fx, should_pass in cases:
        ok = not validate_fixture(fx)
        if ok != should_pass:
            failures.append(name)
    if failures:
        print(json.dumps({"status": "FAIL", "failed_cases": failures}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "positive": 1, "negative": len(cases) - 1}, ensure_ascii=False))
    return 0


def main() -> int:
    if not __debug__:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "python -O disables debug mode"}, ensure_ascii=False))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "PyYAML unavailable"}, ensure_ascii=False))
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--write-report")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.live:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "must pass --live or --selftest"}, ensure_ascii=False))
        return 2
    errors, report = validate_bundle(Path.cwd())
    if args.write_report:
        out = Path(args.write_report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
