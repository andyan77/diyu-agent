#!/usr/bin/env python3
"""Fail-closed checker for the founder-authorized P7D 320-draft midbatch."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


TASK_ID = "GKB-P7D-CONDITIONAL-MIDBATCH-320-GENERATION-AND-REVIEW-HANDOFF-001"
BASELINE_HEAD = "3254e8546c10edb26dea52ada4b6b0c2b760471d"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
OUT_REL = f"{RUN_REL}/midbatch_320_001"
SCALE_REL = f"{RUN_REL}/review_closeout/execution_scalability_001"
ASSIGNMENT_REL = "07_microbatch_briefing/scoped_content_microbatch_120/scoped_120_assignment_plan.v0.1.yaml"
KERNEL_REL = f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml"
SAMPLE_PLAN_REL = f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_runtime_ab_sample_plan.v0.1.yaml"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
SELECTION_ORDINAL_INDEXES = (0, 11, 22, 33, 45, 56, 67, 78)
SHINGLE_SIZE = 5
SHINGLE_FAIL_THRESHOLD = 0.62
PRIOR_CHECKERS = (
    "ci/checkers/check_scoped_120_quality_review_and_content_kernel_extraction.py",
    "ci/checkers/check_p7c_scale_gate_completion.py",
    "ci/checkers/check_p7c_content_kernel_runtime_ab.py",
    "ci/checkers/check_p7c_content_kernel_runtime_ab_002.py",
    "ci/checkers/check_p7c_execution_scalability.py",
)
REQUIRED_FILES = (
    "founder_conditional_midbatch_decision.v0.1.yaml",
    "midbatch_320_selection_manifest.v0.1.jsonl",
    "midbatch_320_selection_summary.v0.1.yaml",
    "midbatch_320_generation_records.v0.1.jsonl",
    "midbatch_320_checkpoint_ledger.v0.1.jsonl",
    "midbatch_320_event_ledger.v0.1.jsonl",
    "midbatch_320_failure_ledger.v0.1.jsonl",
    "midbatch_320_fingerprint_index.v0.1.jsonl",
    "midbatch_320_duplicate_drift_report.v0.1.yaml",
    "midbatch_320_kernel_overlap_report.v0.1.yaml",
    "midbatch_320_capability_quality_summary.v0.1.yaml",
    "midbatch_320_execution_summary.v0.1.yaml",
    "midbatch_320_guardian_review_packet.v0.1.jsonl",
    "midbatch_320_founder_review_packet.v0.1.yaml",
    "midbatch_320_result.v0.1.yaml",
    "midbatch_320_prior_checker_evidence.v0.1.yaml",
)
ALLOWED_PREFIXES = (
    f"{OUT_REL}/",
    "ci/runners/run_p7d_midbatch_320.py",
    "ci/checkers/check_p7d_midbatch_320.py",
    "ci/fixtures/p7d_midbatch_320/",
    "ci/reports/p7d_midbatch_320_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/p7d_midbatch_320_report.md",
    "docs/reports/p7d_midbatch_320_receipt.json",
)
IMMUTABLE_PATHS = (
    f"{RUN_REL}/knowledge_candidate_cards.yaml",
    f"{RUN_REL}/rich_body_blocks.yaml",
    f"{RUN_REL}/content_kernel_extraction",
    f"{RUN_REL}/review_closeout/runtime_ab_001",
    f"{RUN_REL}/review_closeout/runtime_ab_002",
    f"{RUN_REL}/review_closeout/scale_gate_completion",
    SCALE_REL,
    "ci/checkers/check_scoped_120_quality_review_and_content_kernel_extraction.py",
    "ci/checkers/check_p7c_scale_gate_completion.py",
    "ci/checkers/check_p7c_content_kernel_runtime_ab.py",
    "ci/checkers/check_p7c_content_kernel_runtime_ab_002.py",
    "ci/checkers/check_p7c_execution_scalability.py",
)
FORBIDDEN_DIFF_PREFIXES = (
    "CandidatePack/",
    "KE/",
    "serving_projection/",
    "rag/",
    "RAG/",
    "dify/",
    "DIFY/",
    "candidatepack_etl/",
    "08_consolidated_outputs/",
    "09_candidatepack_eligibility/",
    "project-infra/",
    "01_generation_contracts/",
    "03_pilot/",
    "06_canary_runs/",
)
READINESS_KEYS = (
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
)


def stable_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL row {path}:{line_no}")
        rows.append(value)
    return rows


def normalize_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def shingles(text: str, size: int = SHINGLE_SIZE) -> set[str]:
    normalized = normalize_text(text)
    if len(normalized) < size:
        return {normalized} if normalized else set()
    return {
        normalized[index : index + size] for index in range(len(normalized) - size + 1)
    }


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def kernel_segments(kernel: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key in (
        "object_anchor",
        "business_judgment",
        "tradeoff_or_tension",
        "spoken_line_seed",
        "output_asset_hint",
    ):
        value = kernel.get(key)
        if isinstance(value, str) and value:
            result.append(value)
    for key in ("human_subject", "human_action", "scene_premise"):
        value = kernel.get(key)
        if isinstance(value, list):
            result.extend(str(item) for item in value if item)
    return result


def build_overlap_index(
    kernels: list[dict[str, Any]], max_size: int = 18
) -> dict[int, dict[str, set[str]]]:
    index: dict[int, dict[str, set[str]]] = {
        size: defaultdict(set) for size in range(1, max_size + 1)
    }
    for kernel in kernels:
        candidate_id = str(kernel["candidate_id"])
        for segment in kernel_segments(kernel):
            normalized = normalize_text(segment)
            for size in range(1, min(max_size, len(normalized)) + 1):
                for offset in range(len(normalized) - size + 1):
                    index[size][normalized[offset : offset + size]].add(candidate_id)
    return index


def max_kernel_overlap(
    body: str, index: dict[int, dict[str, set[str]]]
) -> tuple[int, list[str], str]:
    normalized = normalize_text(body)
    for size in range(max(index), 0, -1):
        for offset in range(max(0, len(normalized) - size + 1)):
            fragment = normalized[offset : offset + size]
            matches = index[size].get(fragment)
            if matches:
                return size, sorted(matches), fragment
    return 0, [], ""


def expected_selection(
    scale_items: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    kernels: list[dict[str, Any]],
    sample_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_assignments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    kernel_by_assignment = {
        str(row["generation_assignment_id"]): row for row in kernels
    }
    sample_axes = {str(row["assignment_id"]): row for row in sample_rows}
    for row in scale_items:
        grouped_items[str(row["cluster_id"])].append(row)
    for row in assignments:
        grouped_assignments[str(row["canonical_cluster_id"])].append(row)
    result: list[dict[str, Any]] = []
    for cluster_id in sorted(grouped_items):
        items = sorted(
            grouped_items[cluster_id],
            key=lambda row: (int(row["ordinal"]), str(row["work_item_id"])),
        )
        seeds = sorted(
            grouped_assignments[cluster_id], key=lambda row: str(row["assignment_id"])
        )
        if len(items) != 90 or len(seeds) != 3:
            raise ValueError(
                f"source cannot derive {cluster_id}: expected 90 work items and 3 seeds"
            )
        for rank, source_index in enumerate(SELECTION_ORDINAL_INDEXES):
            item = items[source_index]
            assignment = seeds[rank % 3]
            kernel = kernel_by_assignment[str(assignment["assignment_id"])]
            axis = sample_axes.get(str(assignment["assignment_id"]), {})
            result.append(
                {
                    **item,
                    "selection_rank_within_cluster": rank + 1,
                    "selection_source_index_zero_based": source_index,
                    "selection_sort_key": [
                        cluster_id,
                        int(item["ordinal"]),
                        str(item["work_item_id"]),
                    ],
                    "selection_rule": "per_cluster_sorted_quantile_breakpoints_v0.1",
                    "selection_baseline_head": BASELINE_HEAD,
                    "bound_assignment_id": assignment["assignment_id"],
                    "bound_assignment_payload_digest": stable_digest(assignment),
                    "bound_kernel_candidate_id": kernel["candidate_id"],
                    "bound_kernel_payload_digest": stable_digest(kernel),
                    "binding_rule": "same_cluster_sorted_seed_cycle_rank_mod_3",
                    "seed_reuse_pressure": "3_3_2_per_cluster_across_three_seeds",
                    "claim_risk_profile": axis.get(
                        "claim_risk_profile", "not_tagged_by_existing_sample_plan"
                    ),
                    "store_display_or_guide_action_sample": axis.get(
                        "store_display_or_guide_action_sample", False
                    ),
                }
            )
    return result


def expected_founder_samples(records: list[dict[str, Any]]) -> list[str]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[str(row["cluster_id"])].append(row)
    result: list[str] = []
    for cluster_id in sorted(grouped):
        rows = sorted(
            grouped[cluster_id],
            key=lambda row: int(row["selection_rank_within_cluster"]),
        )
        high_risk = [
            row
            for row in rows
            if row.get("claim_risk_profile") == "high_claim_or_evidence_boundary"
        ]
        chosen = (
            high_risk[0]
            if high_risk
            else rows[int(stable_digest(cluster_id)[:8], 16) % len(rows)]
        )
        result.append(str(chosen["work_item_id"]))
    return result


def git_changed_paths(ws: Path) -> list[str]:
    paths: set[str] = set()
    for command in (
        ["git", "diff", "--name-only", BASELINE_HEAD],
        ["git", "status", "--porcelain", "--untracked-files=all"],
    ):
        proc = subprocess.run(command, cwd=ws, capture_output=True, text=True)
        if proc.returncode != 0:
            return ["<git-command-failed>"]
        for line in proc.stdout.splitlines():
            value = line[3:] if command[1] == "status" else line
            if value:
                paths.add(value)
    return sorted(paths)


def allowed_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def baseline_immutable(ws: Path, path: str) -> bool:
    proc = subprocess.run(["git", "diff", "--quiet", BASELINE_HEAD, "--", path], cwd=ws)
    return proc.returncode == 0


def validate_live(ws: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    out = ws / OUT_REL
    for name in REQUIRED_FILES:
        if not (out / name).is_file():
            errors.append(f"missing artifact: {name}")
    if errors:
        return errors, {
            "checker": Path(__file__).name,
            "task_id": TASK_ID,
            "status": "FAIL",
            "errors": errors,
        }
    try:
        decision = read_yaml(out / REQUIRED_FILES[0])[
            "founder_conditional_midbatch_decision"
        ]
        selected = read_jsonl(out / REQUIRED_FILES[1])
        selection_summary = read_yaml(out / REQUIRED_FILES[2])[
            "midbatch_320_selection_summary"
        ]
        records = read_jsonl(out / REQUIRED_FILES[3])
        checkpoints = read_jsonl(out / REQUIRED_FILES[4])
        events = read_jsonl(out / REQUIRED_FILES[5])
        failures = read_jsonl(out / REQUIRED_FILES[6])
        fingerprints = read_jsonl(out / REQUIRED_FILES[7])
        duplicate_report = read_yaml(out / REQUIRED_FILES[8])[
            "midbatch_320_duplicate_drift_report"
        ]
        overlap_report = read_yaml(out / REQUIRED_FILES[9])[
            "midbatch_320_kernel_overlap_report"
        ]
        quality_summary = read_yaml(out / REQUIRED_FILES[10])[
            "midbatch_320_capability_quality_summary"
        ]
        execution_summary = read_yaml(out / REQUIRED_FILES[11])[
            "midbatch_320_execution_summary"
        ]
        guardian_packet = read_jsonl(out / REQUIRED_FILES[12])
        founder_packet = read_yaml(out / REQUIRED_FILES[13])[
            "midbatch_320_founder_review_packet"
        ]
        result = read_yaml(out / REQUIRED_FILES[14])["midbatch_320_result"]
        prior_evidence = read_yaml(out / REQUIRED_FILES[15])[
            "midbatch_320_prior_checker_evidence"
        ]
        scale_items = read_jsonl(ws / SCALE_REL / "scale_work_item_manifest.v0.1.jsonl")
        assignments = read_yaml(ws / ASSIGNMENT_REL)["scoped_120_assignment_plan"][
            "assignments"
        ]
        kernels = read_yaml(ws / KERNEL_REL)["user_visible_kernel_matrix"]["entries"]
        sample_rows = read_yaml(ws / SAMPLE_PLAN_REL)["p7c_runtime_ab_sample_plan"][
            "samples"
        ]
        ledger = read_yaml(ws / LEDGER_REL)["grc_3600_execution_plan_status"]
    except Exception as exc:
        errors.append(f"parse failure: {exc}")
        return errors, {
            "checker": Path(__file__).name,
            "task_id": TASK_ID,
            "status": "FAIL",
            "errors": errors,
        }

    expected = expected_selection(scale_items, assignments, kernels, sample_rows)
    expected_ids = [str(row["work_item_id"]) for row in expected]
    selected_ids = [str(row.get("work_item_id")) for row in selected]
    if selected != expected:
        errors.append("selection does not match independent 3600-source recomputation")
    if len(selected) != 320 or len(set(selected_ids)) != 320:
        errors.append("selection must contain exactly 320 unique work items")
    cluster_counts = Counter(str(row.get("cluster_id")) for row in selected)
    if len(cluster_counts) != 40 or set(cluster_counts.values()) != {8}:
        errors.append("selection must be 40 clusters x 8")
    if selection_summary.get("selection_digest") != stable_digest(expected):
        errors.append("selection summary digest mismatch")
    if (
        decision.get("decision") != "CONDITIONAL_MIDBATCH_300_600"
        or decision.get("authorized_output_count") != 320
    ):
        errors.append("founder decision or authorization count mismatch")
    if (
        decision.get("prior_runtime_ab_evidence_use", {}).get("AB_001")
        != "anti_gold_protocol_failure_only_not_positive_quality_evidence"
    ):
        errors.append("AB-001 must remain anti-gold only")

    record_by_id = {str(row.get("work_item_id")): row for row in records}
    if len(records) != 320 or set(record_by_id) != set(expected_ids):
        errors.append("accepted generation records must map one-to-one to selected IDs")
    assignment_map = {str(row["assignment_id"]): row for row in assignments}
    kernel_map = {str(row["candidate_id"]): row for row in kernels}
    for selected_row in expected:
        work_item_id = str(selected_row["work_item_id"])
        record = record_by_id.get(work_item_id, {})
        assignment = assignment_map.get(str(selected_row["bound_assignment_id"]), {})
        kernel = kernel_map.get(str(selected_row["bound_kernel_candidate_id"]), {})
        if record.get("bound_assignment_id") != selected_row["bound_assignment_id"]:
            errors.append(f"assignment binding mismatch: {work_item_id}")
        if (
            record.get("bound_kernel_candidate_id")
            != selected_row["bound_kernel_candidate_id"]
        ):
            errors.append(f"kernel binding mismatch: {work_item_id}")
        if record.get("bound_assignment_payload_digest") != stable_digest(assignment):
            errors.append(f"assignment digest mismatch: {work_item_id}")
        if record.get("bound_kernel_payload_digest") != stable_digest(kernel):
            errors.append(f"kernel digest mismatch: {work_item_id}")
        body = record.get("body")
        if (
            not isinstance(body, str)
            or len(body.strip()) < 220
            or "PLANNED_NO_CONTENT" in body
        ):
            errors.append(f"empty, short, or placeholder body: {work_item_id}")
        if (
            record.get("generation_status") != "gpt_generated_structured_draft"
            or record.get("accepted") is not True
        ):
            errors.append(f"generation status mismatch: {work_item_id}")
        if record.get("narrative_fabrication_machine_proven_absent") is not False:
            errors.append(
                f"narrative fabrication machine scope overclaimed: {work_item_id}"
            )
        if record.get("candidate_specificity_machine_proven") is not False:
            errors.append(
                f"candidate specificity machine scope overclaimed: {work_item_id}"
            )
        for key in (
            "accepted_domain_knowledge",
            "candidatepack_ready",
            "production_servable",
            "serving_ready",
            "rag_ready",
            "dify_ready",
            "generation_allowed",
        ):
            if record.get(key) is not False:
                errors.append(f"forbidden readiness true: {work_item_id}:{key}")
        for key in READINESS_KEYS:
            if record.get("readiness_flags", {}).get(key) is not False:
                errors.append(f"readiness flag not false: {work_item_id}:{key}")

    overlap_index = build_overlap_index(kernels)
    recomputed_overlaps: dict[str, tuple[int, list[str], str]] = {}
    for row in records:
        body = str(row.get("body", ""))
        value = max_kernel_overlap(body, overlap_index)
        work_item_id = str(row.get("work_item_id"))
        recomputed_overlaps[work_item_id] = value
        if value[0] > 17:
            errors.append(
                f"all-kernel exact overlap exceeds 17: {work_item_id}:{value[0]}"
            )
        if row.get("kernel_overlap_max_chars_all_120") != value[0]:
            errors.append(f"self-reported overlap mismatch: {work_item_id}")
        if row.get("kernel_overlap_max_candidate_ids") != value[1]:
            errors.append(f"overlap source kernel mismatch: {work_item_id}")
    observed_overlap = max(
        (value[0] for value in recomputed_overlaps.values()), default=0
    )
    if (
        overlap_report.get("observed_max_chars") != observed_overlap
        or overlap_report.get("kernel_count") != 120
    ):
        errors.append("kernel overlap summary mismatch")
    serialized_records = json.dumps(records, ensure_ascii=False)
    if "review_packet_kernel" in serialized_records:
        errors.append("review-packet kernel leaked into generation records")

    body_digests = [stable_digest(str(row.get("body", ""))) for row in records]
    normalized_digests = [
        stable_digest(normalize_text(str(row.get("body", "")))) for row in records
    ]
    if len(set(body_digests)) != 320:
        errors.append("exact duplicate body detected")
    if len(set(normalized_digests)) != 320:
        errors.append("normalized duplicate body detected")
    grouped_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped_records[str(row.get("cluster_id"))].append(row)
    max_jaccard = 0.0
    for rows in grouped_records.values():
        for left_index, left in enumerate(rows):
            for right in rows[left_index + 1 :]:
                score = jaccard(
                    shingles(str(left.get("body", ""))),
                    shingles(str(right.get("body", ""))),
                )
                max_jaccard = max(max_jaccard, score)
                if score >= SHINGLE_FAIL_THRESHOLD:
                    errors.append(
                        f"within-cluster near duplicate: {left.get('work_item_id')}:{right.get('work_item_id')}:{score:.6f}"
                    )
    if (
        abs(
            float(duplicate_report.get("within_cluster_char_5_shingle_max_jaccard", -1))
            - round(max_jaccard, 6)
        )
        > 0.000001
    ):
        errors.append("near-duplicate summary mismatch")
    if duplicate_report.get("candidate_specificity_machine_proven") is not False:
        errors.append("duplicate report overclaims candidate specificity")
    if duplicate_report.get("semantic_duplicate_zero_claimed") is not False:
        errors.append("duplicate report overclaims semantic duplicate absence")

    fingerprint_map = {str(row.get("work_item_id")): row for row in fingerprints}
    if len(fingerprint_map) != 320:
        errors.append("fingerprint count mismatch")
    for row in records:
        work_item_id = str(row.get("work_item_id"))
        fingerprint = fingerprint_map.get(work_item_id, {})
        if fingerprint.get("body_digest") != stable_digest(str(row.get("body", ""))):
            errors.append(f"body fingerprint mismatch: {work_item_id}")
        if fingerprint.get("normalized_body_digest") != stable_digest(
            normalize_text(str(row.get("body", "")))
        ):
            errors.append(f"normalized fingerprint mismatch: {work_item_id}")

    if len(checkpoints) != 40:
        errors.append("checkpoint count must be 40")
    completed_from_checkpoints: set[str] = set()
    previous_count = 0
    for checkpoint in checkpoints:
        payload = {
            key: value
            for key, value in checkpoint.items()
            if key != "checkpoint_digest"
        }
        completed = [
            str(value) for value in checkpoint.get("completed_work_item_ids", [])
        ]
        if checkpoint.get("checkpoint_digest") != stable_digest(payload):
            errors.append(
                f"checkpoint digest mismatch: {checkpoint.get('checkpoint_id')}"
            )
        if (
            len(completed) != int(checkpoint.get("completed_count", -1))
            or len(completed) != previous_count + 8
        ):
            errors.append(
                f"checkpoint count progression mismatch: {checkpoint.get('checkpoint_id')}"
            )
        if len(set(completed)) != len(completed):
            errors.append(
                f"checkpoint duplicate completion: {checkpoint.get('checkpoint_id')}"
            )
        completed_from_checkpoints = set(completed)
        previous_count = len(completed)
    if completed_from_checkpoints != set(expected_ids):
        errors.append("checkpoint final set missing or adds work items")
    accepted_events = [
        row for row in events if row.get("event") == "GENERATION_ACCEPTED"
    ]
    accepted_event_ids = [str(row.get("work_item_id")) for row in accepted_events]
    if (
        len(accepted_events) != 320
        or set(accepted_event_ids) != set(expected_ids)
        or len(set(accepted_event_ids)) != 320
    ):
        errors.append("generation event set mismatch")
    resume_events = [
        row for row in events if row.get("event") == "RESUME_FROM_CHECKPOINT"
    ]
    if (
        len(resume_events) != 1
        or resume_events[0].get("resume_did_not_rewrite_completed_outputs") is not True
    ):
        errors.append("bounded resume evidence missing")
    budget_events = [
        row for row in events if row.get("event") == "NATIVE_BUDGET_HARD_STOP"
    ]
    if (
        len(budget_events) != 1
        or budget_events[0].get("accepted_output_count") != 320
        or budget_events[0].get("attempted_321st_output") is not False
    ):
        errors.append("native budget hard stop mismatch")
    failure_event_ids = {
        str(row.get("work_item_id"))
        for row in events
        if row.get("event") == "GENERATION_FAILED"
    }
    failure_ledger_ids = {str(row.get("work_item_id")) for row in failures}
    if failure_event_ids != failure_ledger_ids:
        errors.append("failure ledger does not match failure events")
    if failures:
        errors.append(
            "complete PASS package must not contain unresolved generation failures"
        )

    guardian_map = {str(row.get("work_item_id")): row for row in guardian_packet}
    if len(guardian_map) != 320:
        errors.append("guardian packet count mismatch")
    for row in records:
        packet_row = guardian_map.get(str(row.get("work_item_id")), {})
        if packet_row.get("body_digest") != row.get("body_digest") or packet_row.get(
            "body"
        ) != row.get("body"):
            errors.append(f"guardian packet body mismatch: {row.get('work_item_id')}")
    founder_samples = founder_packet.get("samples", [])
    founder_ids = [str(row.get("work_item_id")) for row in founder_samples]
    if len(founder_samples) != 40 or founder_ids != expected_founder_samples(records):
        errors.append("founder sample is not deterministic one-per-cluster selection")
    if founder_packet.get("codex_does_not_fill_founder_verdict") is not True:
        errors.append("Codex must not fill founder verdict")
    if {str(row.get("cluster_id")) for row in founder_samples} != set(grouped_records):
        errors.append("founder packet does not cover every cluster")
    if not any(
        row.get("claim_risk_profile") == "high_claim_or_evidence_boundary"
        for row in founder_samples
    ):
        errors.append("founder packet lacks high claim-risk sample")
    if not any(
        row.get("generation_mode") == "display_solution" for row in founder_samples
    ):
        errors.append("founder packet lacks store/display sample")
    if not any(row.get("P0_group") == "P0_05" for row in founder_samples):
        errors.append("founder packet lacks P0-05 sample")

    quality_fact = quality_summary.get("fact_boundary", {})
    if (
        quality_fact.get("narrative_fabrication_machine_proven_absent") is not False
        or quality_fact.get("human_review_required") is not True
    ):
        errors.append("fact-boundary machine limitation not preserved")
    if quality_summary.get("does_not_prove_kernel_supply_for_3600") is not True:
        errors.append("2.67x evidence scope is overstated")
    if quality_summary.get("P0_05", {}).get("human_review_required") is not True:
        errors.append("P0-05 human review requirement missing")
    if (
        execution_summary.get("actual_accepted_output_count") != 320
        or execution_summary.get("attempted_321st_output") is not False
    ):
        errors.append("execution summary count mismatch")
    if (
        result.get("result")
        != "MIDBATCH_320_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW"
    ):
        errors.append("result semantics mismatch")
    if (
        result.get("guardian_review") != "PENDING"
        or result.get("founder_human_review") != "PENDING"
    ):
        errors.append("human/guardian review must remain PENDING")
    if (
        result.get("full_scale_3600", {}).get("status") != "HOLD"
        or result.get("full_scale_3600", {}).get("expand_to_3600_allowed") is not False
    ):
        errors.append("full-scale 3600 must remain HOLD")

    old_events = read_jsonl(ws / SCALE_REL / "full_manifest_dry_run_events.v0.1.jsonl")
    scale_ids = {str(row["work_item_id"]) for row in scale_items}
    for run_id in ("clean_full_run_a", "clean_full_run_b"):
        run_ids = [
            str(row.get("work_item_id"))
            for row in old_events
            if row.get("event") == "WORK_ITEM_ACK" and row.get("run_id") == run_id
        ]
        if (
            len(run_ids) != 3600
            or set(run_ids) != scale_ids
            or len(set(run_ids)) != 3600
        ):
            errors.append(
                f"execution-scalability original event recomputation failed: {run_id}"
            )

    steps = {str(row.get("step_id")): row for row in ledger.get("steps", [])}
    expected_statuses = {
        "P7C-AB": "NEXT",
        "P7C_SCALE": "BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY",
        "P7C_SCALE_PREP": "DONE",
        "P7D": "BLOCKED_BY_P7C_SCALE_DECISION",
        "P8": "BLOCKED_BY_P7D",
    }
    for step_id, status in expected_statuses.items():
        if steps.get(step_id, {}).get("status") != status:
            errors.append(f"ledger status literal drifted: {step_id}")
    route_8 = ledger.get("route_migration_8", {})
    if route_8.get("founder_final_decision", {}).get("status") != "PENDING":
        errors.append(
            "route_migration_8 founder PENDING must remain byte-semantic frozen"
        )
    route_9 = ledger.get("route_migration_9", {})
    if (
        route_9.get("founder_scale_decision", {}).get("decision")
        != "CONDITIONAL_MIDBATCH_300_600"
    ):
        errors.append("route_migration_9 founder decision missing")
    if route_9.get("founder_scale_decision", {}).get("authorized_count") != 320:
        errors.append("route_migration_9 authorized count mismatch")
    if (
        route_9.get("P7D_MIDBATCH_320", {}).get("operational_state")
        != "EXECUTED_PENDING_REVIEW"
    ):
        errors.append("route_migration_9 midbatch operational state mismatch")
    if route_9.get("full_scale_3600", {}).get("operational_state") != "HOLD":
        errors.append("route_migration_9 full scale must remain HOLD")
    if (
        ledger.get("expand_to_3600_allowed") is not False
        or ledger.get("generation_unlocked") is not False
    ):
        errors.append("ledger generation or expansion unlocked")
    for key in READINESS_KEYS:
        if ledger.get("readiness", {}).get(key) is not False:
            errors.append(f"ledger readiness drifted: {key}")

    for path in IMMUTABLE_PATHS:
        if not baseline_immutable(ws, path):
            errors.append(f"immutable source changed from baseline: {path}")
    for path in git_changed_paths(ws):
        if not allowed_path(path):
            errors.append(f"changed path outside allowlist: {path}")
        if any(path.startswith(prefix) for prefix in FORBIDDEN_DIFF_PREFIXES):
            errors.append(f"forbidden scope changed: {path}")

    prior_results = {
        str(row.get("checker_path")): int(row.get("exit_code", -1))
        for row in prior_evidence.get("checks", [])
    }
    if (
        prior_evidence.get("baseline_head") != BASELINE_HEAD
        or prior_evidence.get("execution_mode") != "isolated_clean_baseline_clone"
    ):
        errors.append("prior checker evidence baseline or mode mismatch")
    if set(prior_results) != set(PRIOR_CHECKERS):
        errors.append("prior checker evidence set mismatch")
    for row in prior_evidence.get("checks", []):
        path = str(row.get("checker_path"))
        if (
            row.get("exit_code") != 0
            or row.get("reported_status") != "PASS"
            or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("stdout_sha256", "")))
        ):
            errors.append(f"baseline-pinned prior checker evidence failed: {path}")
    report = {
        "checker": Path(__file__).name,
        "task_id": TASK_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "selected_count": len(selected),
        "accepted_output_count": len(records),
        "cluster_count": len(cluster_counts),
        "per_cluster_counts": dict(cluster_counts),
        "selection_digest": stable_digest(expected),
        "kernel_overlap_max": observed_overlap,
        "exact_duplicate_count": len(body_digests) - len(set(body_digests)),
        "normalized_duplicate_count": len(normalized_digests)
        - len(set(normalized_digests)),
        "within_cluster_shingle_max_jaccard": round(max_jaccard, 6),
        "checkpoint_count": len(checkpoints),
        "resume_event_count": len(resume_events),
        "founder_review_sample_count": len(founder_samples),
        "guardian_packet_count": len(guardian_packet),
        "failure_count": len(failures),
        "prior_checker_mode": "isolated_clean_baseline_clone_evidence_plus_immutable_checker_bytes",
        "prior_results": prior_results,
        "readiness_false": not any("readiness" in error for error in errors),
        "full_scale_3600": "HOLD",
        "expand_to_3600_allowed": False,
    }
    return errors, report


def fixture_errors(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    selected = fixture["selected"]
    records = fixture["records"]
    if selected != fixture["expected_selection"]:
        errors.append("selection")
    if len(records) != fixture["authorized_count"]:
        errors.append("count")
    if len({row["work_item_id"] for row in records}) != len(records):
        errors.append("duplicate_work_item")
    if any(
        row["assignment_id"] != selected[index]["assignment_id"]
        for index, row in enumerate(records)
    ):
        errors.append("binding")
    if any(row["kernel_overlap_all"] > 17 for row in records):
        errors.append("overlap")
    if len({normalize_text(row["body"]) for row in records}) != len(records):
        errors.append("duplicate_body")
    if fixture["near_duplicate_jaccard"] >= SHINGLE_FAIL_THRESHOLD:
        errors.append("near_duplicate")
    if (
        fixture["narrative_absence_proven"] is not False
        or fixture["human_review_count"] < 1
    ):
        errors.append("human_review_scope")
    if fixture["route_8_pending"] is not True:
        errors.append("route_8")
    if fixture["expand_to_3600_allowed"] is not False:
        errors.append("scale")
    if fixture["founder_verdict_filled"] is not False:
        errors.append("founder_verdict")
    return errors


def selftest() -> int:
    positive = {
        "expected_selection": [
            {"work_item_id": "W1", "assignment_id": "A1"},
            {"work_item_id": "W2", "assignment_id": "A2"},
        ],
        "selected": [
            {"work_item_id": "W1", "assignment_id": "A1"},
            {"work_item_id": "W2", "assignment_id": "A2"},
        ],
        "records": [
            {
                "work_item_id": "W1",
                "assignment_id": "A1",
                "kernel_overlap_all": 8,
                "body": "第一条有具体场景",
            },
            {
                "work_item_id": "W2",
                "assignment_id": "A2",
                "kernel_overlap_all": 9,
                "body": "第二条有服装动作",
            },
        ],
        "authorized_count": 2,
        "near_duplicate_jaccard": 0.2,
        "narrative_absence_proven": False,
        "human_review_count": 1,
        "route_8_pending": True,
        "expand_to_3600_allowed": False,
        "founder_verdict_filled": False,
    }
    cases: list[tuple[str, dict[str, Any], bool]] = [("positive", positive, True)]

    def add_case(name: str, mutate: Any) -> None:
        value = copy.deepcopy(positive)
        mutate(value)
        cases.append((name, value, False))

    add_case("selection_tamper", lambda value: value["selected"].reverse())
    add_case(
        "count_321_equivalent", lambda value: value.update({"authorized_count": 1})
    )
    add_case(
        "duplicate_work_item",
        lambda value: value["records"][1].update({"work_item_id": "W1"}),
    )
    add_case(
        "wrong_binding",
        lambda value: value["records"][0].update({"assignment_id": "A2"}),
    )
    add_case(
        "other_kernel_overlap",
        lambda value: value["records"][0].update({"kernel_overlap_all": 18}),
    )
    add_case(
        "normalized_duplicate",
        lambda value: value["records"][1].update({"body": "第一条，有具体场景"}),
    )
    add_case(
        "within_cluster_sister_draft",
        lambda value: value.update({"near_duplicate_jaccard": 0.8}),
    )
    add_case(
        "narrative_fabrication_overclaim",
        lambda value: value.update({"narrative_absence_proven": True}),
    )
    add_case(
        "missing_human_sample", lambda value: value.update({"human_review_count": 0})
    )
    add_case(
        "route_8_rewritten", lambda value: value.update({"route_8_pending": False})
    )
    add_case(
        "expand_3600", lambda value: value.update({"expand_to_3600_allowed": True})
    )
    add_case(
        "codex_fills_founder_verdict",
        lambda value: value.update({"founder_verdict_filled": True}),
    )
    failed: list[str] = []
    for name, value, should_pass in cases:
        passed = not fixture_errors(value)
        if passed != should_pass:
            failed.append(name)
    if failed:
        sys.stdout.write(
            json.dumps({"status": "FAIL", "failed_cases": failed}, ensure_ascii=False)
            + "\n"
        )
        return 1
    sys.stdout.write(
        json.dumps(
            {"status": "PASS", "positive": 1, "negative": len(cases) - 1},
            ensure_ascii=False,
        )
        + "\n"
    )
    return 0


def main() -> int:
    if not __debug__:
        sys.stdout.write(
            json.dumps(
                {"status": "FAIL_CLOSED", "reason": "python -O disables debug mode"},
                ensure_ascii=False,
            )
            + "\n"
        )
        return 2
    if yaml is None:
        sys.stdout.write(
            json.dumps(
                {"status": "FAIL_CLOSED", "reason": "PyYAML unavailable"},
                ensure_ascii=False,
            )
            + "\n"
        )
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--write-report")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.live:
        sys.stdout.write(
            json.dumps(
                {"status": "FAIL_CLOSED", "reason": "--live or --selftest required"},
                ensure_ascii=False,
            )
            + "\n"
        )
        return 2
    try:
        errors, report = validate_live(Path.cwd())
    except Exception as exc:  # pragma: no cover
        report = {
            "checker": Path(__file__).name,
            "task_id": TASK_ID,
            "status": "FAIL",
            "errors": [str(exc)],
        }
        errors = [str(exc)]
    if args.write_report:
        target = Path(args.write_report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    sys.stdout.write(json.dumps(report, ensure_ascii=False) + "\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
