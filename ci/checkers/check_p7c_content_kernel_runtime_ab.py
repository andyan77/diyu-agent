#!/usr/bin/env python3
"""Fail-closed checker for the P7C Codex-native content-kernel paired A/B."""

from __future__ import annotations

import argparse
import copy
import hashlib
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


BASELINE = "1d333342e01bc57294e7df7f989b84c17330e0db"
TASK_ID = "GKB-CONTENT-KERNEL-REAL-RUNTIME-AB-001"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
AB_REL = f"{RUN_REL}/review_closeout/runtime_ab_001"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"

REQUIRED_FILES = [
    f"{AB_REL}/runtime_ab_run_manifest.v0.1.yaml",
    f"{AB_REL}/runtime_ab_generation_records.v0.1.jsonl",
    f"{AB_REL}/runtime_ab_blind_review_packet.v0.1.jsonl",
    f"{AB_REL}/runtime_ab_arm_key.v0.1.yaml",
    f"{AB_REL}/runtime_ab_deterministic_metrics.v0.1.yaml",
    f"{AB_REL}/runtime_ab_execution_provenance.v0.1.yaml",
    f"{AB_REL}/runtime_ab_result.v0.1.yaml",
]

IMMUTABLE_RELS = [
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
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_scale_decision_standard.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_capability_heatmap.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_runtime_ab_sample_plan.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_execution_scalability_gate.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_scale_hold_decision.v0.1.yaml",
]

ALLOWED_WRITE_PREFIXES = (
    f"{AB_REL}/",
    "ci/checkers/check_p7c_content_kernel_runtime_ab.py",
    "ci/fixtures/p7c_content_kernel_runtime_ab/",
    "ci/reports/p7c_content_kernel_runtime_ab_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/p7c_content_kernel_runtime_ab_report.md",
    "docs/reports/p7c_content_kernel_runtime_ab_receipt.json",
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


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"malformed jsonl {path}:{line_no}: {exc}") from exc
        rows.append(row)
    return rows


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_cmd(cmd: list[str], ws: Path) -> int:
    proc = subprocess.run(cmd, cwd=ws, capture_output=True, text=True)
    return proc.returncode


def run_prior_at_baseline(ws: Path, checker: str) -> int:
    with tempfile.TemporaryDirectory(prefix="p7c_ab_prior_") as tmp:
        tmp_path = Path(tmp)
        add = subprocess.run(
            ["git", "-C", str(ws), "worktree", "add", "--detach", "--quiet", str(tmp_path), BASELINE],
            capture_output=True,
            text=True,
        )
        if add.returncode != 0:
            return 90
        try:
            proc = subprocess.run(["python3", checker, "--live"], cwd=tmp_path, capture_output=True, text=True)
            return proc.returncode
        finally:
            subprocess.run(["git", "-C", str(ws), "worktree", "remove", "--force", str(tmp_path)], capture_output=True, text=True)


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


def load_samples(ws: Path) -> list[dict[str, Any]]:
    plan = read_yaml(ws / f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_runtime_ab_sample_plan.v0.1.yaml")
    return plan["p7c_runtime_ab_sample_plan"]["samples"]


def load_ledger(ws: Path) -> dict[str, Any]:
    return read_yaml(ws / LEDGER_REL)["grc_3600_execution_plan_status"]


def validate_bundle(ws: Path, *, run_priors: bool = True) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    report: dict[str, Any] = {
        "checker": "check_p7c_content_kernel_runtime_ab.py",
        "task_id": TASK_ID,
        "status": "FAIL",
    }

    for rel in REQUIRED_FILES:
        if not (ws / rel).exists():
            errors.append(f"missing required artifact: {rel}")

    if errors:
        return errors, report

    try:
        manifest = read_yaml(ws / REQUIRED_FILES[0])["runtime_ab_run_manifest"]
        records = read_jsonl(ws / REQUIRED_FILES[1])
        blind = read_jsonl(ws / REQUIRED_FILES[2])
        arm_key = read_yaml(ws / REQUIRED_FILES[3])["runtime_ab_arm_key"]["arm_key"]
        metrics = read_yaml(ws / REQUIRED_FILES[4])["runtime_ab_deterministic_metrics"]
        provenance = read_yaml(ws / REQUIRED_FILES[5])["runtime_ab_execution_provenance"]
        result = read_yaml(ws / REQUIRED_FILES[6])["runtime_ab_result"]
        samples = load_samples(ws)
        ledger = load_ledger(ws)
    except Exception as exc:
        return [f"parse failure: {exc}"], report

    sample_ids = [s["candidate_id"] for s in samples]
    if len(sample_ids) != 12 or len(set(sample_ids)) != 12:
        errors.append("frozen sample count must be 12 unique ids")

    if manifest.get("runtime_kind") != "codex_native_agent_execution":
        errors.append("manifest runtime_kind must be codex_native_agent_execution")
    if manifest.get("external_LLM_called") is not False or manifest.get("secret_accessed") is not False:
        errors.append("manifest must record no external LLM and no secret access")
    if manifest.get("expected_output_count") != 24 or manifest.get("actual_output_count") != 24:
        errors.append("manifest output count must be 24")
    if manifest.get("methodology_caveat", {}).get("not_unbiased_RCT") is not True:
        errors.append("manifest must record non-RCT methodology caveat")

    if len(records) != 24:
        errors.append("generation records must contain exactly 24 rows")
    ids = [r.get("arm_output_id") for r in records]
    if len(ids) != len(set(ids)):
        errors.append("arm_output_id must be unique")

    by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_sample[row.get("sample_id")].append(row)
        if row.get("runtime_kind") != "codex_native_agent_execution":
            errors.append(f"wrong runtime kind: {row.get('arm_output_id')}")
        if row.get("created_by") != "Codex":
            errors.append(f"created_by must be Codex: {row.get('arm_output_id')}")
        if row.get("external_LLM_called") is not False:
            errors.append(f"external LLM called: {row.get('arm_output_id')}")
        if row.get("review_packet_consumed") is not False:
            errors.append(f"review packet consumed: {row.get('arm_output_id')}")
        if row.get("output_digest") != digest_text(row.get("output_text", "")):
            errors.append(f"output digest mismatch: {row.get('arm_output_id')}")
        if row.get("semantic_regeneration_count") != 0 or row.get("transport_retry_count") != 0:
            errors.append(f"retry/regeneration must be zero: {row.get('arm_output_id')}")

    for sid in sample_ids:
        rows = by_sample.get(sid, [])
        if len(rows) != 2:
            errors.append(f"sample must have exactly two outputs: {sid}")
            continue
        arms = {r.get("arm") for r in rows}
        if arms != {"control", "treatment"}:
            errors.append(f"sample arms mismatch: {sid}")
        for row in rows:
            if row.get("arm") == "control" and row.get("kernel_body_consumed") is not False:
                errors.append(f"control consumed kernel: {sid}")
            if row.get("arm") == "treatment" and row.get("kernel_body_consumed") is not True:
                errors.append(f"treatment did not consume kernel: {sid}")

    control_max = max((r["generation_sequence"] for r in records if r.get("arm") == "control"), default=0)
    treatment_min = min((r["generation_sequence"] for r in records if r.get("arm") == "treatment"), default=999)
    if not (control_max < treatment_min):
        errors.append("all controls must be frozen before treatments")

    if len(blind) != 12:
        errors.append("blind packet must contain 12 rows")
    forbidden_blind_terms = ("control", "treatment", "kernel_body_consumed", "kernel_consumed")
    for row in blind:
        raw = json.dumps(row, ensure_ascii=False)
        for term in forbidden_blind_terms:
            if term in raw:
                errors.append(f"blind packet leaks arm/kernel term: {row.get('blind_pair_id')}:{term}")
        if "output_X" not in row or "output_Y" not in row:
            errors.append(f"blind row missing X/Y: {row.get('blind_pair_id')}")

    key_by_pair = {k.get("blind_pair_id"): k for k in arm_key}
    if len(key_by_pair) != 12:
        errors.append("arm key must contain 12 unique pairs")
    rec_by_output = {r["arm_output_id"]: r for r in records}
    for row in blind:
        pair = row.get("blind_pair_id")
        key = key_by_pair.get(pair)
        if not key:
            errors.append(f"blind pair missing from arm key: {pair}")
            continue
        if {key.get("X"), key.get("Y")} != {"control", "treatment"}:
            errors.append(f"arm key X/Y must map to control/treatment: {pair}")
        control = rec_by_output.get(key.get("control_output_id"))
        treatment = rec_by_output.get(key.get("treatment_output_id"))
        if not control or not treatment:
            errors.append(f"arm key references missing output: {pair}")
            continue
        x_expected = control if key.get("X") == "control" else treatment
        y_expected = control if key.get("Y") == "control" else treatment
        if row["output_X"].get("output_digest") != x_expected.get("output_digest"):
            errors.append(f"blind X digest mismatch: {pair}")
        if row["output_Y"].get("output_digest") != y_expected.get("output_digest"):
            errors.append(f"blind Y digest mismatch: {pair}")

    if metrics.get("actual_output_count") != 24 or metrics.get("control_count") != 12 or metrics.get("treatment_count") != 12:
        errors.append("deterministic metrics count mismatch")
    if metrics.get("codex_quality_score_written") is not False:
        errors.append("Codex must not write quality score")
    if provenance.get("external_LLM_called") is not False or provenance.get("secret_accessed") is not False:
        errors.append("provenance must record no external LLM/secret")
    if "both arms authored by Codex, and treatment identity is known to author" not in provenance.get("methodology_limitations", []):
        errors.append("provenance must record same-author limitation")

    if result.get("result_status") != "CODEX_NATIVE_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN":
        errors.append("result status must remain pending Claude guardian")
    if result.get("real_runtime_AB_evidence", {}).get("status") != "NOT_YET_CONFIRMED":
        errors.append("real_runtime_AB_evidence must not be confirmed by Codex")
    if result.get("execution_scalability_gate") != "PENDING" or result.get("final_scale_decision") != "HOLD":
        errors.append("scale gate must remain pending/HOLD")
    for key in ["expand_to_3600_allowed", "midbatch_300_600_allowed", "candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "production_ready"]:
        if result.get(key) is not False:
            errors.append(f"result {key} must remain false")

    steps = {s.get("step_id"): s for s in ledger.get("steps", [])}
    expected_status = {
        "P7C-AB": "NEXT",
        "P7C_SCALE": "BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY",
        "P7C_SCALE_PREP": "DONE",
        "P7D": "BLOCKED_BY_P7C_SCALE_DECISION",
        "P8": "BLOCKED_BY_P7D",
    }
    for step, status in expected_status.items():
        if steps.get(step, {}).get("status") != status:
            errors.append(f"ledger {step}.status drifted")
    if ledger.get("route_migration_6", {}).get("runtime_kind") != "codex_native_agent_execution":
        errors.append("ledger route_migration_6 missing or wrong runtime_kind")
    if ledger.get("route_migration_6", {}).get("status_recorded") != "CODEX_NATIVE_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN":
        errors.append("ledger route_migration_6 status mismatch")
    if ledger.get("generation_unlocked") is not False:
        errors.append("ledger generation_unlocked must remain false")
    readiness = ledger.get("readiness", {})
    for key in READINESS_KEYS:
        if readiness.get(key) is not False:
            errors.append(f"ledger readiness not false: {key}")

    for rel in IMMUTABLE_RELS:
        if not git_diff_clean(ws, rel):
            errors.append(f"baseline immutable asset drifted: {rel}")

    for path in git_status_paths(ws):
        if not allowed(path):
            errors.append(f"dirty path outside allowed write surface: {path}")
    for forbidden in FORBIDDEN_PATHS:
        if (ws / forbidden).exists():
            errors.append(f"forbidden path exists: {forbidden}")

    prior_results: dict[str, int] = {}
    if run_priors:
        prior_results["p7c_review"] = run_prior_at_baseline(ws, "ci/checkers/check_scoped_120_quality_review_and_content_kernel_extraction.py")
        prior_results["p7c_scale_prep"] = run_prior_at_baseline(ws, "ci/checkers/check_p7c_scale_gate_completion.py")
        for name, code in prior_results.items():
            if code != 0:
                errors.append(f"prior checker failed: {name}={code}")

    report.update(
        {
            "status": "PASS" if not errors else "FAIL",
            "error_count": len(errors),
            "errors": errors,
            "runtime_kind": "codex_native_agent_execution",
            "sample_count": len(sample_ids),
            "actual_output_count": len(records),
            "control_count": sum(1 for r in records if r.get("arm") == "control"),
            "treatment_count": sum(1 for r in records if r.get("arm") == "treatment"),
            "support_bucket_distribution": dict(Counter(s.get("support_bucket") for s in samples)),
            "generation_mode_coverage": sorted({s.get("generation_mode") for s in samples}),
            "p0_group_coverage_count": len({s.get("p0_group") for s in samples}),
            "claim_risk_sample_count": sum(1 for s in samples if s.get("claim_risk_profile") in {"high_claim_or_evidence_boundary", "medium_fact_slot_boundary"}),
            "store_display_sample_count": sum(1 for s in samples if s.get("store_display_or_guide_action_sample")),
            "result_status": result.get("result_status"),
            "external_LLM_called": False,
            "readiness_false": not errors or all("readiness" not in e for e in errors),
            "prior_results": prior_results,
        }
    )
    return errors, report


def make_positive() -> dict[str, Any]:
    return {
        "manifest": {
            "runtime_kind": "codex_native_agent_execution",
            "external_LLM_called": False,
            "secret_accessed": False,
            "expected_output_count": 2,
            "actual_output_count": 2,
        },
        "records": [
            {"sample_id": "S1", "arm_output_id": "C1", "arm": "control", "output_text": "control", "output_digest": digest_text("control"), "generation_sequence": 1, "kernel_body_consumed": False, "review_packet_consumed": False},
            {"sample_id": "S1", "arm_output_id": "T1", "arm": "treatment", "output_text": "treatment", "output_digest": digest_text("treatment"), "generation_sequence": 2, "kernel_body_consumed": True, "review_packet_consumed": False},
        ],
        "blind": [{"blind_pair_id": "P1", "output_X": {"output_digest": digest_text("control")}, "output_Y": {"output_digest": digest_text("treatment")}}],
        "arm_key": [{"blind_pair_id": "P1", "X": "control", "Y": "treatment", "control_output_id": "C1", "treatment_output_id": "T1"}],
        "result_status": "CODEX_NATIVE_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN",
    }


def validate_fixture(fx: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = fx.get("records", [])
    if fx.get("manifest", {}).get("external_LLM_called") is not False:
        errors.append("external LLM called")
    if len(records) != 2:
        errors.append("fixture count mismatch")
    arms = {r.get("arm") for r in records}
    if arms != {"control", "treatment"}:
        errors.append("missing arm")
    if any(r.get("output_digest") != digest_text(r.get("output_text", "")) for r in records):
        errors.append("digest mismatch")
    control = next((r for r in records if r.get("arm") == "control"), {})
    treatment = next((r for r in records if r.get("arm") == "treatment"), {})
    if control.get("kernel_body_consumed") is not False:
        errors.append("control kernel")
    if treatment.get("kernel_body_consumed") is not True:
        errors.append("treatment kernel")
    if control.get("generation_sequence", 99) >= treatment.get("generation_sequence", 0):
        errors.append("sequence")
    if "control" in json.dumps(fx.get("blind", []), ensure_ascii=False) or "treatment" in json.dumps(fx.get("blind", []), ensure_ascii=False):
        errors.append("blind leak")
    if fx.get("result_status") != "CODEX_NATIVE_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN":
        errors.append("bad status")
    return errors


def selftest() -> int:
    positive = make_positive()
    cases: list[tuple[str, dict[str, Any], bool]] = [("positive", positive, True)]

    def mutated(name: str, fn) -> None:
        fx = copy.deepcopy(positive)
        fn(fx)
        cases.append((name, fx, False))

    mutated("external_llm_called", lambda fx: fx["manifest"].update({"external_LLM_called": True}))
    mutated("missing_record", lambda fx: fx["records"].pop())
    mutated("duplicate_control", lambda fx: fx["records"][1].update({"arm": "control"}))
    mutated("digest_mismatch", lambda fx: fx["records"][0].update({"output_digest": "bad"}))
    mutated("control_consumed_kernel", lambda fx: fx["records"][0].update({"kernel_body_consumed": True}))
    mutated("treatment_missing_kernel", lambda fx: fx["records"][1].update({"kernel_body_consumed": False}))
    mutated("wrong_sequence", lambda fx: fx["records"][0].update({"generation_sequence": 3}))
    mutated("blind_leak", lambda fx: fx["blind"][0].update({"arm": "control"}))
    mutated("confirmed_status", lambda fx: fx.update({"result_status": "CONFIRMED_PASS"}))

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
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "python -O disables assertions/debug mode"}, ensure_ascii=False))
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

    ws = Path.cwd()
    errors, report = validate_bundle(ws)
    if args.write_report:
        out = Path(args.write_report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
