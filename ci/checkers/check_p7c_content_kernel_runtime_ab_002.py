#!/usr/bin/env python3
"""Fail-closed checker for the P7C fair content-kernel A/B rerun."""

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


BASELINE = "34b977dab8ab536078f81323b3b7f57ad9d9f60f"
TASK_ID = "GKB-CONTENT-KERNEL-FAIR-RERUN-AB-002"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
AB_REL = f"{RUN_REL}/review_closeout/runtime_ab_002"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
KERNEL_COPY_CEILING = 17

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
    f"{RUN_REL}/review_closeout/runtime_ab_001/runtime_ab_result.v0.1.yaml",
    f"{RUN_REL}/review_closeout/runtime_ab_001/runtime_ab_generation_records.v0.1.jsonl",
    f"{RUN_REL}/review_closeout/runtime_ab_001/runtime_ab_blind_review_packet.v0.1.jsonl",
    f"{RUN_REL}/review_closeout/runtime_ab_001/runtime_ab_arm_key.v0.1.yaml",
    f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_runtime_ab_sample_plan.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml",
    f"{RUN_REL}/content_kernel_extraction/review_packet_kernel_matrix.v0.1.yaml",
]

ALLOWED_WRITE_PREFIXES = (
    f"{AB_REL}/",
    "ci/checkers/check_p7c_content_kernel_runtime_ab_002.py",
    "ci/fixtures/p7c_content_kernel_runtime_ab_002/",
    "ci/reports/p7c_content_kernel_runtime_ab_002_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/p7c_content_kernel_runtime_ab_002_report.md",
    "docs/reports/p7c_content_kernel_runtime_ab_002_receipt.json",
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
            rows.append(json.loads(line))
        except Exception as exc:
            raise ValueError(f"malformed jsonl {path}:{line_no}: {exc}") from exc
    return rows


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lcs_len(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = [0] * (len(b) + 1)
    best = 0
    for ca in a:
        cur = [0] * (len(b) + 1)
        for j, cb in enumerate(b, start=1):
            if ca == cb:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def kernel_text(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ["object_anchor", "business_judgment", "tradeoff_or_tension", "spoken_line_seed", "output_asset_hint"]:
        val = entry.get(key)
        if isinstance(val, str):
            parts.append(val)
    for key in ["human_subject", "human_action", "scene_premise"]:
        val = entry.get(key)
        if isinstance(val, list):
            parts.extend(str(item) for item in val)
    return "\n".join(parts)


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


def run_prior_at_baseline(ws: Path, checker: str) -> int:
    with tempfile.TemporaryDirectory(prefix="p7c_ab002_prior_") as tmp:
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


def load_samples(ws: Path) -> list[dict[str, Any]]:
    plan = read_yaml(ws / f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_runtime_ab_sample_plan.v0.1.yaml")
    return plan["p7c_runtime_ab_sample_plan"]["samples"]


def load_kernel_by_id(ws: Path) -> dict[str, dict[str, Any]]:
    matrix = read_yaml(ws / f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml")
    return {entry["candidate_id"]: entry for entry in matrix["user_visible_kernel_matrix"]["entries"]}


def load_ledger(ws: Path) -> dict[str, Any]:
    return read_yaml(ws / LEDGER_REL)["grc_3600_execution_plan_status"]


def validate_bundle(ws: Path, *, run_priors: bool = True) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    report: dict[str, Any] = {"checker": "check_p7c_content_kernel_runtime_ab_002.py", "task_id": TASK_ID, "status": "FAIL"}

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
        kernel_by_id = load_kernel_by_id(ws)
        ledger = load_ledger(ws)
    except Exception as exc:
        return [f"parse failure: {exc}"], report

    sample_ids = [s["candidate_id"] for s in samples]
    if len(sample_ids) != 12 or len(set(sample_ids)) != 12:
        errors.append("frozen sample count must be 12 unique ids")

    if manifest.get("task_id") != TASK_ID or manifest.get("run_id") != "runtime_ab_002":
        errors.append("manifest task/run id mismatch")
    if manifest.get("supersedes_evidence_status_of") != "runtime_ab_001_confounded_not_confirmed":
        errors.append("manifest must record AB-001 confounding supersession")
    if manifest.get("external_LLM_called") is not False or manifest.get("secret_accessed") is not False:
        errors.append("manifest must record no external LLM and no secret")
    if manifest.get("actual_output_count") != 24 or manifest.get("control_count") != 12 or manifest.get("treatment_count") != 12:
        errors.append("manifest count mismatch")
    if "treatment_kernel_exact_overlap_lt_18_chars" not in manifest.get("fairness_fixes", []):
        errors.append("manifest missing kernel-copy fairness fix")

    if len(records) != 24:
        errors.append("generation records must contain exactly 24 rows")
    ids = [row.get("arm_output_id") for row in records]
    if len(ids) != len(set(ids)):
        errors.append("arm_output_id must be unique")
    digests = [row.get("output_digest") for row in records]
    if len(digests) != len(set(digests)):
        errors.append("all output digests must be unique")

    by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    controls: list[str] = []
    max_kernel_overlap = 0
    for row in records:
        by_sample[row.get("sample_id")].append(row)
        if row.get("runtime_kind") != "codex_native_agent_execution":
            errors.append(f"bad runtime kind: {row.get('arm_output_id')}")
        if row.get("created_by") != "Codex":
            errors.append(f"created_by must be Codex: {row.get('arm_output_id')}")
        if row.get("external_LLM_called") is not False:
            errors.append(f"external LLM called: {row.get('arm_output_id')}")
        if row.get("review_packet_consumed") is not False:
            errors.append(f"review packet consumed: {row.get('arm_output_id')}")
        if row.get("output_digest") != digest_text(row.get("output_text", "")):
            errors.append(f"output digest mismatch: {row.get('arm_output_id')}")
        if row.get("arm") == "control":
            controls.append(row.get("output_text", ""))
            if row.get("kernel_body_consumed") is not False:
                errors.append(f"control consumed kernel: {row.get('sample_id')}")
        if row.get("arm") == "treatment":
            if row.get("kernel_body_consumed") is not True:
                errors.append(f"treatment did not consume kernel: {row.get('sample_id')}")
            kernel = kernel_by_id.get(row.get("sample_id"))
            if not kernel:
                errors.append(f"missing kernel for treatment: {row.get('sample_id')}")
            else:
                overlap = lcs_len(row.get("output_text", ""), kernel_text(kernel))
                max_kernel_overlap = max(max_kernel_overlap, overlap)
                if overlap > KERNEL_COPY_CEILING:
                    errors.append(f"treatment kernel exact overlap too long: {row.get('sample_id')}={overlap}")
                if row.get("kernel_max_exact_overlap_chars") != overlap:
                    errors.append(f"recorded kernel overlap mismatch: {row.get('sample_id')}")

    if len(set(controls)) != 12:
        errors.append("control outputs must be 12 distinct texts")
    max_control_lcs = 0
    for i in range(len(controls)):
        for j in range(i + 1, len(controls)):
            max_control_lcs = max(max_control_lcs, lcs_len(controls[i], controls[j]))
    if max_control_lcs > 60:
        errors.append(f"control template reuse too high: max_lcs={max_control_lcs}")

    for sid in sample_ids:
        rows = by_sample.get(sid, [])
        if len(rows) != 2:
            errors.append(f"sample must have exactly two outputs: {sid}")
            continue
        if {row.get("arm") for row in rows} != {"control", "treatment"}:
            errors.append(f"sample arms mismatch: {sid}")
    control_max = max((row["generation_sequence"] for row in records if row.get("arm") == "control"), default=0)
    treatment_min = min((row["generation_sequence"] for row in records if row.get("arm") == "treatment"), default=999)
    if control_max >= treatment_min:
        errors.append("all controls must be frozen before treatments")

    if len(blind) != 12:
        errors.append("blind packet must contain 12 rows")
    forbidden_blind_terms = ("control", "treatment", "kernel_body_consumed", "kernel_consumed")
    for row in blind:
        raw = json.dumps(row, ensure_ascii=False)
        for term in forbidden_blind_terms:
            if term in raw:
                errors.append(f"blind packet leaks arm/kernel term: {row.get('blind_pair_id')}:{term}")

    key_by_pair = {row.get("blind_pair_id"): row for row in arm_key}
    if len(key_by_pair) != 12:
        errors.append("arm key must contain 12 unique pairs")
    rec_by_output = {row["arm_output_id"]: row for row in records}
    for row in blind:
        key = key_by_pair.get(row.get("blind_pair_id"))
        if not key:
            errors.append(f"blind pair missing arm key: {row.get('blind_pair_id')}")
            continue
        if {key.get("X"), key.get("Y")} != {"control", "treatment"}:
            errors.append(f"arm key X/Y mismatch: {row.get('blind_pair_id')}")
        control = rec_by_output.get(key.get("control_output_id"))
        treatment = rec_by_output.get(key.get("treatment_output_id"))
        if not control or not treatment:
            errors.append(f"arm key references missing output: {row.get('blind_pair_id')}")
            continue
        x_expected = control if key.get("X") == "control" else treatment
        y_expected = control if key.get("Y") == "control" else treatment
        if row["output_X"].get("output_digest") != x_expected.get("output_digest"):
            errors.append(f"blind X digest mismatch: {row.get('blind_pair_id')}")
        if row["output_Y"].get("output_digest") != y_expected.get("output_digest"):
            errors.append(f"blind Y digest mismatch: {row.get('blind_pair_id')}")

    if metrics.get("max_treatment_kernel_exact_overlap_chars") != max_kernel_overlap:
        errors.append("metrics max treatment/kernel overlap mismatch")
    if metrics.get("control_outputs_unique") is not True or metrics.get("codex_quality_score_written") is not False:
        errors.append("metrics fairness flags mismatch")
    if provenance.get("review_guardian_issue_addressed") != [
        "runtime_ab_001 treatment copied kernel business_judgment too closely",
        "runtime_ab_001 control used mode-level templates instead of candidate-specific generation",
    ]:
        errors.append("provenance must record Guardian issues addressed")
    if result.get("result_status") != "CODEX_NATIVE_FAIR_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN":
        errors.append("result must remain pending Guardian")
    if result.get("fairness_gates", {}).get("max_treatment_kernel_exact_overlap_chars") != max_kernel_overlap:
        errors.append("result fairness max overlap mismatch")
    if result.get("real_runtime_AB_evidence", {}).get("status") != "NOT_YET_CONFIRMED":
        errors.append("Codex must not confirm runtime AB evidence")
    if result.get("execution_scalability_gate") != "PENDING" or result.get("final_scale_decision") != "HOLD":
        errors.append("scale gate must remain pending/HOLD")
    for key in ["expand_to_3600_allowed", "midbatch_300_600_allowed", "candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "production_ready"]:
        if result.get(key) is not False:
            errors.append(f"result {key} must remain false")

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
            errors.append(f"ledger {step}.status drifted")
    if ledger.get("route_migration_7", {}).get("run_id") != "runtime_ab_002":
        errors.append("ledger route_migration_7 missing")
    if ledger.get("generation_unlocked") is not False:
        errors.append("ledger generation_unlocked must remain false")
    for key in READINESS_KEYS:
        if ledger.get("readiness", {}).get(key) is not False:
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
        prior_results["p7c_ab_001"] = run_prior_at_baseline(ws, "ci/checkers/check_p7c_content_kernel_runtime_ab.py")
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
            "run_id": "runtime_ab_002",
            "sample_count": len(sample_ids),
            "actual_output_count": len(records),
            "control_count": sum(1 for row in records if row.get("arm") == "control"),
            "treatment_count": sum(1 for row in records if row.get("arm") == "treatment"),
            "max_treatment_kernel_exact_overlap_chars": max_kernel_overlap,
            "max_control_pair_lcs_chars": max_control_lcs,
            "result_status": result.get("result_status"),
            "external_LLM_called": False,
            "readiness_false": not any("readiness" in error for error in errors),
            "prior_results": prior_results,
        }
    )
    return errors, report


def make_positive() -> dict[str, Any]:
    return {
        "records": [
            {"arm": "control", "text": "控制臂是一段候选专属文字", "kernel": False, "seq": 1},
            {"arm": "treatment", "text": "处理臂改写燃料意思但不照抄", "kernel": True, "seq": 2, "source": "燃料原文完全不同的一长段"},
        ],
        "status": "CODEX_NATIVE_FAIR_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN",
    }


def validate_fixture(fx: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = fx.get("records", [])
    if len(records) != 2:
        errors.append("count")
        return errors
    arms = {row.get("arm") for row in records}
    if arms != {"control", "treatment"}:
        errors.append("arms")
        return errors
    control = next(row for row in records if row.get("arm") == "control")
    treatment = next(row for row in records if row.get("arm") == "treatment")
    if control.get("kernel") is not False:
        errors.append("control kernel")
    if treatment.get("kernel") is not True:
        errors.append("treatment kernel")
    if control.get("seq", 99) >= treatment.get("seq", 0):
        errors.append("sequence")
    if lcs_len(treatment.get("text", ""), treatment.get("source", "")) > KERNEL_COPY_CEILING:
        errors.append("kernel copy")
    if control.get("text") == treatment.get("text"):
        errors.append("duplicate")
    if fx.get("status") != "CODEX_NATIVE_FAIR_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN":
        errors.append("status")
    return errors


def selftest() -> int:
    positive = make_positive()
    cases: list[tuple[str, dict[str, Any], bool]] = [("positive", positive, True)]

    def mutated(name: str, fn) -> None:
        fx = copy.deepcopy(positive)
        fn(fx)
        cases.append((name, fx, False))

    mutated("missing_record", lambda fx: fx["records"].pop())
    mutated("duplicate_arm", lambda fx: fx["records"][1].update({"arm": "control"}))
    mutated("control_consumes_kernel", lambda fx: fx["records"][0].update({"kernel": True}))
    mutated("treatment_no_kernel", lambda fx: fx["records"][1].update({"kernel": False}))
    mutated("bad_sequence", lambda fx: fx["records"][0].update({"seq": 3}))
    copied = "这是一段超过十八个汉字的燃料原文复制内容"
    mutated("kernel_copy", lambda fx: fx["records"][1].update({"text": copied, "source": copied}))
    mutated("duplicate_text", lambda fx: fx["records"][1].update({"text": fx["records"][0]["text"]}))
    mutated("confirmed_status", lambda fx: fx.update({"status": "CONFIRMED_PASS"}))

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
