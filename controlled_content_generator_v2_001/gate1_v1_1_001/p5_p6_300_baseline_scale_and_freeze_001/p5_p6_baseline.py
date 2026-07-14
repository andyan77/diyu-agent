#!/usr/bin/env python3
"""Recoverable Gate 1 v1.1 240+60 quality-baseline materializer."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("p5_p6_baseline refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_300_BASELINE_SCALE_AND_INDEPENDENT_FREEZE_001"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p5_p6_300_baseline_scale_and_freeze_001"
)
P4_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_third_sealed_hidden_probe40_001"
)
P4_SUCCESSOR = P4_ROOT / "review_successor"
P1B_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001"
)
P2_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
P3_ROUTE_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p3_route_input_compiler_recovery_001"
)
AUTHOR_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_author_output_contract_recovery_001"
)
LEGACY_ROUTE_ROOT = Path(
    "controlled_content_generator_v2_001/"
    "creative_authoring_route_oracle_convergence_001"
)
REFERENCE_CORPUS = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)

CONTRACT = TASK_ROOT / "contract/baseline_contract.v1.0.yaml"
P4_DECISION = P4_SUCCESSOR / "qualification_decision.v1.0.json"
P4_MAPPING = P4_SUCCESSOR / "neutral_blind_mapping.v1.0.jsonl"
P4_OUTPUTS = P4_ROOT / "run/positive_20_first_outputs.v1.0.jsonl"
P4_REQUESTS = P4_ROOT / "freeze/positive_author_requests_20.v1.0.jsonl"
P4_CONTENT_REVIEW = P4_SUCCESSOR / "signed_content_value_review.v1.0.json"
P4_FACT_REVIEW = P4_SUCCESSOR / "signed_fact_authorization_review.v1.0.json"
P4_ADJUDICATION = P4_SUCCESSOR / "targeted_adjudication.v1.0.json"
P4_REVIEW_METRICS = P4_SUCCESSOR / "review_metrics.v1.0.yaml"
P4_DECISION_PACKET = P4_SUCCESSOR / "qualification_decision_packet.v1.0.yaml"
P4_FINAL_RESULT = P4_SUCCESSOR / "final_result.v1.0.yaml"
DISPOSITIONS = P1B_ROOT / "content/reference_120_final_dispositions.v0.1.jsonl"
ROUTE_GOLD = P1B_ROOT / "route/route_60_gold_answers.v0.1.jsonl"
LEGACY_ROUTE_INPUTS = LEGACY_ROUTE_ROOT / "route/route_inputs.v0.1.jsonl"
ROUTE_MODULE_PATH = P3_ROUTE_ROOT / "route_contract.py"
AUTHOR_MODULE_PATH = AUTHOR_ROOT / "author_contract.py"

ACTIVE_COMPONENTS = P2_ROOT / "component/active_gate1_components.v0.1.jsonl"
ACTIVE_RULES = P2_ROOT / "component/active_control_rules.v0.1.jsonl"
ACTIVE_EDGES = P2_ROOT / "component/active_gate1_edges.v0.1.jsonl"
ACTIVE_AB_PATHS = P2_ROOT / "ab/active_ab_structural_paths.v0.1.jsonl"
GENERATOR_CORE = P2_ROOT / "p2_generator_core_r6.py"
GENERATOR_REGISTRY = P2_ROOT / "generator/active_gate1_generator_registry.v0.1.yaml"
AUTHOR_INSTRUCTION = AUTHOR_ROOT / "contract/controlled_author_instruction.v1.0.md"
AUTHOR_CONTRACT = AUTHOR_ROOT / "contract/author_semantic_output_contract.v1.0.json"
PRODUCTION_AUTHOR_INSTRUCTION = (
    TASK_ROOT / "contract/production_author_instruction.v1.0.md"
)

REFERENCE_APPROVED = TASK_ROOT / "production/reference_approved.v1.0.jsonl"
P4_APPROVED = TASK_ROOT / "production/p4_approved.v1.0.jsonl"
ALLOCATION = TASK_ROOT / "production/allocation.v1.0.jsonl"
CURATION_GLOB = "production/curation/scenarios.*.jsonl"
AUTHOR_ROLE_MANIFEST = TASK_ROOT / "production/author_role_manifest.v1.0.json"
AUTHOR_REQUESTS = TASK_ROOT / "production/author_requests.v1.0.jsonl"
BATCH_LEDGER = TASK_ROOT / "production/batch_ledger.v1.0.jsonl"
PRODUCTION_FREEZE = TASK_ROOT / "freeze/production_basis_manifest.v1.0.yaml"
RAW_OUTPUT_GLOB = "production/author_raw/raw.*.jsonl"
FIRST_OUTPUTS = TASK_ROOT / "production/positive_first_outputs.v1.0.jsonl"
OUTPUT_FREEZE = TASK_ROOT / "freeze/positive_first_output_freeze.v1.0.yaml"
EXTERNAL_EXIT_AUDIT = TASK_ROOT / "production/external_exit_audit.v1.0.yaml"
PRODUCTION_CONTENT_REVIEW_GLOB = "review/production/content.*.jsonl"
PRODUCTION_FACT_REVIEW_GLOB = "review/production/fact.*.jsonl"
PRODUCTION_REVIEW_RESULT = TASK_ROOT / "review/production/review_result.v1.0.yaml"
APPROVED_POSITIVES = TASK_ROOT / "candidate/approved_positive_240.v1.0.jsonl"
PRODUCTION_FAILURES = TASK_ROOT / "candidate/production_failures.v1.0.jsonl"
CANDIDATE_MANIFEST = TASK_ROOT / "freeze/candidate_300_manifest.v1.0.yaml"

FINAL_CONTENT_REVIEW = TASK_ROOT / "review/final/signed_content_value_review.v1.0.json"
FINAL_FACT_REVIEW = TASK_ROOT / "review/final/signed_fact_authorization_review.v1.0.json"
FINAL_ADJUDICATION = TASK_ROOT / "review/final/targeted_adjudication.v1.0.json"
FINAL_REVIEW_METRICS = TASK_ROOT / "review/final/review_metrics.v1.0.yaml"
FINAL_DECISION_PACKET = TASK_ROOT / "review/final/decision_packet.v1.0.yaml"
FINAL_DECISION = TASK_ROOT / "review/final/coordinator_decision.v1.0.json"
FINAL_BASELINE_MANIFEST = TASK_ROOT / "freeze/final_300_baseline_manifest.v1.0.yaml"
FINAL_RESULT = TASK_ROOT / "result/final_300_baseline_result.v1.0.yaml"
EXECUTION_REVIEW_REQUEST = TASK_ROOT / "result/execution_review_request.v1.0.md"

ROUTE_INPUTS = TASK_ROOT / "route/route_inputs.v1.0.jsonl"
ROUTE_COMPILED = TASK_ROOT / "route/route_compiled.v1.0.jsonl"
ROUTE_ACTUALS = TASK_ROOT / "route/route_actuals.v1.0.jsonl"
ROUTE_ACTUAL_FREEZE = TASK_ROOT / "freeze/route_actual_freeze.v1.0.yaml"
ROUTE_COMPARISONS = TASK_ROOT / "route/route_comparisons.v1.0.jsonl"
ROUTE_RESULT = TASK_ROOT / "route/route_result.v1.0.yaml"

PROFILE_RE = re.compile(r"^CP(?:0[1-9]|1\d|20)$")
SCENARIO_ID_RE = re.compile(r"^P5-CUR-CP(?:0[1-9]|1\d|20)-\d{3}$")
AUDIENCE_INTERNAL_ID_RE = re.compile(
    r"(?:G1V11-P5|P5-CUR|\bCP(?:0[1-9]|1\d|20)\b|"
    r"(?:^|[^A-Za-z])(?:FACT|AUTH|SRC)-[A-Za-z0-9-]+)"
)
AUDIENCE_GOVERNANCE_PHRASES = (
    "仅限本请求",
    "不得发布",
    "不可发布",
    "仅供资格测试",
    "本资格测试",
    "内部事件编号",
    "product_core_requirements",
    "claim_boundary",
    "synthetic_qualification_only",
    "assigned_variant",
)
PROFILE_IDS = tuple(f"CP{number:02d}" for number in range(1, 21))
MODEL_CAPABILITY = "gpt-5.6-sol"
REASONING_EFFORT = "high"
SERVICE_TIER = "priority"


class BaselineError(ValueError):
    """Stable fail-closed pipeline error."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise BaselineError(f"{code}{suffix}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def digest_object(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    return digest_object({key: child for key, child in value.items() if key != digest_key})


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), "E_JSONL_OBJECT", f"{path}:{number}")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(canonical_json(row) for row in rows) + "\n"
    path.write_text(payload, encoding="utf-8")


def read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "E_YAML_OBJECT", path.as_posix())
    return value


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "E_JSON_OBJECT", path.as_posix())
    return value


def write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    require(spec is not None and spec.loader is not None, "E_IMPORT_SPEC", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def approved_reference_rows() -> list[dict[str, Any]]:
    dispositions = read_jsonl(ROOT / DISPOSITIONS)
    source_by_id = {
        str(row["asset_id"]): row for row in read_jsonl(ROOT / REFERENCE_CORPUS)
    }
    selected = [
        row
        for row in dispositions
        if row.get("final_disposition") == "COUNT_TOWARD_FINAL_300_POSITIVE"
    ]
    require(len(dispositions) == 120, "E_REFERENCE_DISPOSITION_COUNT")
    require(len(selected) == 29, "E_REFERENCE_APPROVED_RECOMPUTE")
    result: list[dict[str, Any]] = []
    for row in selected:
        asset_id = str(row["asset_id"])
        source = source_by_id.get(asset_id)
        require(source is not None, "E_REFERENCE_SOURCE", asset_id)
        require(
            row.get("source_record_sha256") == digest_object(source),
            "E_REFERENCE_SOURCE_DIGEST",
            asset_id,
        )
        result.append(
            {
                "baseline_item_id": f"G1V11-REF-{asset_id}",
                "source_asset_id": asset_id,
                "profile_id": row["final_content_product_id"],
                "body_text": source["body_text"],
                "historical_generation_version": source.get("generation_mode"),
                "historical_source_record_sha256": row["source_record_sha256"],
                "approval_source": "P1B_SIGNED_MECHANICAL_DISPOSITION",
                "first_acceptable": True,
                "reclassified_as_current_generation": False,
                "publishable": False,
                "runtime_consumable": False,
            }
        )
    return sorted(result, key=lambda item: str(item["baseline_item_id"]))


def _validate_p4_review(
    path: Path,
    expected_track: str,
    mapping: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    review = read_json(ROOT / path)
    require(
        review.get("schema_version")
        == "gate1-p4t3-successor-independent-review-v1.0",
        "E_P4_REVIEW_SCHEMA",
        expected_track,
    )
    require(review.get("task_id") == TASK_ID, "E_P4_REVIEW_TASK", expected_track)
    require(review.get("review_track") == expected_track, "E_P4_REVIEW_TRACK")
    require(review.get("blank_context") is True, "E_P4_REVIEW_CONTEXT")
    require(
        review.get("mapping_revealed_after_blind_freeze") is True,
        "E_P4_REVIEW_REVEAL_ORDER",
    )
    require(
        review.get("model_capability_id") == MODEL_CAPABILITY
        and review.get("reasoning_effort") == REASONING_EFFORT,
        "E_P4_REVIEW_MODEL",
    )
    blind_path = Path(str(review.get("blind_choices_path", "")))
    require((ROOT / blind_path).is_file(), "E_P4_BLIND_CHOICES_PATH")
    require(
        review.get("blind_choices_sha256") == sha256_file(ROOT / blind_path),
        "E_P4_BLIND_CHOICES_DIGEST",
    )
    require(
        review.get("review_digest") == object_digest(review, "review_digest"),
        "E_P4_REVIEW_DIGEST",
        expected_track,
    )
    judgments = review.get("judgments")
    require(isinstance(judgments, list) and len(judgments) == 20, "E_P4_REVIEW_COUNT")
    per_item: dict[str, dict[str, Any]] = {}
    for judgment in judgments:
        require(isinstance(judgment, dict), "E_P4_REVIEW_ITEM")
        blind_id = str(judgment.get("blind_item_id"))
        require(blind_id in mapping and blind_id not in per_item, "E_P4_REVIEW_ITEM_ID")
        require(
            judgment.get("chosen_profile_id") == mapping[blind_id]["profile_id"],
            "E_P4_REVIEW_BLIND_CHOICE",
            blind_id,
        )
        require(isinstance(judgment.get("first_acceptable"), bool), "E_P4_REVIEW_ACCEPT")
        require(isinstance(judgment.get("hard_error_codes"), list), "E_P4_REVIEW_HARD")
        require(
            isinstance(judgment.get("formulaic_or_near_duplicate"), bool),
            "E_P4_REVIEW_FORMULA",
        )
        require(
            isinstance(judgment.get("rationale"), str)
            and bool(str(judgment["rationale"]).strip())
            and isinstance(judgment.get("evidence"), list)
            and bool(judgment["evidence"]),
            "E_P4_REVIEW_EVIDENCE",
        )
        per_item[blind_id] = judgment
    require(set(per_item) == set(mapping), "E_P4_REVIEW_COVERAGE")
    route_gate = review.get("route_gate")
    require(
        isinstance(route_gate, dict)
        and route_gate.get("action_match_count") == 20
        and route_gate.get("reason_match_count") == 20
        and route_gate.get("audience_leak_count") == 0
        and route_gate.get("pass") is True,
        "E_P4_REVIEW_ROUTE_GATE",
    )
    return {"document": review, "per_item": per_item}


def prepare_p4_decision_packet() -> None:
    require(not (ROOT / P4_DECISION).exists(), "E_P4_DECISION_ALREADY_EXISTS")
    mapping_rows = read_jsonl(ROOT / P4_MAPPING)
    mapping = {str(row["blind_item_id"]): row for row in mapping_rows}
    require(len(mapping) == len(mapping_rows) == 20, "E_P4_MAPPING_COUNT")
    for row in mapping_rows:
        require(
            row.get("mapping_digest") == object_digest(row, "mapping_digest"),
            "E_P4_MAPPING_DIGEST",
        )
    content = _validate_p4_review(P4_CONTENT_REVIEW, "CONTENT_VALUE", mapping)
    fact = _validate_p4_review(P4_FACT_REVIEW, "FACT_AUTHORIZATION", mapping)
    content_doc = content["document"]
    fact_doc = fact["document"]
    review_identity_fields = (
        "reviewer_identity",
        "reviewer_session_logical_id",
        "reviewer_platform_agent_id",
    )
    for field in review_identity_fields:
        require(content_doc.get(field) != fact_doc.get(field), "E_P4_REVIEW_IDENTITY_COLLISION", field)
    disagreements = sorted(
        blind_id
        for blind_id in mapping
        if (
            content["per_item"][blind_id]["first_acceptable"]
            != fact["per_item"][blind_id]["first_acceptable"]
            or bool(content["per_item"][blind_id]["hard_error_codes"])
            != bool(fact["per_item"][blind_id]["hard_error_codes"])
        )
    )
    require(disagreements, "E_P4_NO_SUBSTANTIVE_DISAGREEMENT")
    adjudication = read_json(ROOT / P4_ADJUDICATION)
    require(
        adjudication.get("schema_version")
        == "gate1-p4t3-targeted-adjudication-v1.0"
        and adjudication.get("task_id") == TASK_ID,
        "E_P4_ADJUDICATION_SCHEMA",
    )
    require(adjudication.get("blank_context") is True, "E_P4_ADJUDICATION_CONTEXT")
    require(
        adjudication.get("model_capability_id") == MODEL_CAPABILITY
        and adjudication.get("reasoning_effort") == REASONING_EFFORT,
        "E_P4_ADJUDICATION_MODEL",
    )
    require(
        adjudication.get("review_digest") == object_digest(adjudication, "review_digest"),
        "E_P4_ADJUDICATION_DIGEST",
    )
    adjudicator_identity_values = {
        str(adjudication.get("adjudicator_identity")),
        str(adjudication.get("adjudicator_session_logical_id")),
        str(adjudication.get("adjudicator_platform_agent_id")),
    }
    review_identity_values = {
        str(content_doc.get(field)) for field in review_identity_fields
    } | {str(fact_doc.get(field)) for field in review_identity_fields}
    require(not adjudicator_identity_values.intersection(review_identity_values), "E_P4_ADJUDICATOR_COLLISION")
    items = adjudication.get("items")
    require(isinstance(items, list) and len(items) == len(disagreements), "E_P4_ADJUDICATION_COUNT")
    adjudicated: dict[str, dict[str, Any]] = {}
    for item in items:
        require(isinstance(item, dict), "E_P4_ADJUDICATION_ITEM")
        blind_id = str(item.get("blind_item_id"))
        require(blind_id in disagreements and blind_id not in adjudicated, "E_P4_ADJUDICATION_SCOPE")
        require(item.get("profile_id") == mapping[blind_id]["profile_id"], "E_P4_ADJUDICATION_PROFILE")
        verdict = item.get("adjudication_verdict")
        approved = item.get("approved_original_first_output")
        require(
            verdict in {"APPROVE_ORIGINAL_FIRST_OUTPUT", "REJECT_ORIGINAL_FIRST_OUTPUT"}
            and isinstance(approved, bool)
            and approved == (verdict == "APPROVE_ORIGINAL_FIRST_OUTPUT"),
            "E_P4_ADJUDICATION_VERDICT",
        )
        require(
            isinstance(item.get("rationale"), str)
            and bool(str(item["rationale"]).strip())
            and isinstance(item.get("evidence"), list)
            and bool(item["evidence"]),
            "E_P4_ADJUDICATION_EVIDENCE",
        )
        require(isinstance(item.get("hard_error_codes"), list), "E_P4_ADJUDICATION_HARD")
        adjudicated[blind_id] = item
    require(set(adjudicated) == set(disagreements), "E_P4_ADJUDICATION_COVERAGE")
    eligible_request_ids = sorted(
        str(mapping[blind_id]["request_id"])
        for blind_id, item in adjudicated.items()
        if item["approved_original_first_output"]
    )
    metrics = {
        "schema_version": "gate1-p4t3-successor-review-metrics-v1.0",
        "task_id": TASK_ID,
        "content_review_sha256": sha256_file(ROOT / P4_CONTENT_REVIEW),
        "fact_review_sha256": sha256_file(ROOT / P4_FACT_REVIEW),
        "targeted_adjudication_sha256": sha256_file(ROOT / P4_ADJUDICATION),
        "content_first_acceptable_count": sum(
            item["first_acceptable"] for item in content["per_item"].values()
        ),
        "fact_first_acceptable_count": sum(
            item["first_acceptable"] for item in fact["per_item"].values()
        ),
        "substantive_disagreement_blind_item_ids": disagreements,
        "adjudicated_approved_count": len(eligible_request_ids),
        "adjudicated_rejected_count": len(disagreements) - len(eligible_request_ids),
        "eligible_request_ids": eligible_request_ids,
        "metrics_digest": "",
    }
    metrics["metrics_digest"] = object_digest(metrics, "metrics_digest")
    write_yaml(ROOT / P4_REVIEW_METRICS, metrics)
    packet = {
        "schema_version": "gate1-p4t3-successor-qualification-packet-v1.0",
        "task_id": TASK_ID,
        "decision_authority": "EXTERNAL_INDEPENDENT_QUALIFICATION_COORDINATOR",
        "review_metrics_digest": metrics["metrics_digest"],
        "review_metrics_sha256": sha256_file(ROOT / P4_REVIEW_METRICS),
        "eligible_request_ids": eligible_request_ids,
        "H_before_decision": 0,
        "generator_qualified_before_decision": False,
        "legacy_p5_allowed_before_decision": False,
        "nonblocking_quality_baseline_authorized": True,
        "packet_digest": "",
    }
    packet["packet_digest"] = object_digest(packet, "packet_digest")
    write_yaml(ROOT / P4_DECISION_PACKET, packet)


def apply_p4_decision() -> None:
    metrics = read_yaml(ROOT / P4_REVIEW_METRICS)
    packet = read_yaml(ROOT / P4_DECISION_PACKET)
    require(metrics.get("metrics_digest") == object_digest(metrics, "metrics_digest"), "E_P4_METRICS_DIGEST")
    require(packet.get("packet_digest") == object_digest(packet, "packet_digest"), "E_P4_PACKET_DIGEST")
    require(packet.get("review_metrics_digest") == metrics["metrics_digest"], "E_P4_PACKET_METRICS")
    decision = read_json(ROOT / P4_DECISION)
    require(
        decision.get("schema_version")
        == "gate1-p4t3-successor-qualification-decision-v1.0"
        and decision.get("task_id") == TASK_ID,
        "E_P4_DECISION_SCHEMA",
    )
    require(
        decision.get("decision_authority")
        == "EXTERNAL_INDEPENDENT_QUALIFICATION_COORDINATOR",
        "E_P4_DECISION_AUTHORITY",
    )
    require(
        decision.get("review_metrics_digest") == metrics["metrics_digest"],
        "E_P4_DECISION_METRICS",
    )
    require(decision.get("decision_digest") == object_digest(decision, "decision_digest"), "E_P4_DECISION_DIGEST")
    score = decision.get("qualification_score")
    hard_veto = decision.get("hard_veto")
    verdict = decision.get("qualification_verdict")
    approved = list(map(str, decision.get("approved_first_output_request_ids", [])))
    require(isinstance(score, int) and 0 <= score <= 100, "E_P4_DECISION_SCORE")
    require(isinstance(hard_veto, bool), "E_P4_DECISION_HARD_VETO")
    require(len(approved) == len(set(approved)), "E_P4_DECISION_APPROVED_DUPLICATE")
    require(set(approved).issubset(set(metrics["eligible_request_ids"])), "E_P4_DECISION_APPROVED_SCOPE")
    require(
        isinstance(decision.get("decision_reason_codes"), list)
        and bool(decision["decision_reason_codes"]),
        "E_P4_DECISION_REASONS",
    )
    coordinator_values = {
        str(decision.get("coordinator_identity")),
        str(decision.get("coordinator_session_logical_id")),
        str(decision.get("coordinator_platform_agent_id")),
    }
    require(len(coordinator_values) == 3 and all(value and value != "None" for value in coordinator_values), "E_P4_COORDINATOR_IDENTITY")
    prior_roles = []
    for path in (P4_CONTENT_REVIEW, P4_FACT_REVIEW, P4_ADJUDICATION):
        prior_roles.append(read_json(ROOT / path))
    prior_values = {
        str(value)
        for role in prior_roles
        for key, value in role.items()
        if key.endswith(("identity", "session_logical_id", "platform_agent_id"))
    }
    require(not coordinator_values.intersection(prior_values), "E_P4_COORDINATOR_COLLISION")
    if verdict == "APPROVE":
        require(hard_veto is False and score >= 90 and len(approved) >= 18, "E_P4_DECISION_APPROVE_GATE")
        result_state = "PASS_TO_NONBLOCKING_QUALITY_BASELINE"
    else:
        require(verdict == "REJECT" and not approved, "E_P4_DECISION_REJECT_GATE")
        result_state = "STOPPED_QUALIFICATION_REJECTED_NONBLOCKING_BASELINE_CONTINUES"
    final = {
        "schema_version": "gate1-p4t3-successor-final-result-v1.0",
        "task_id": TASK_ID,
        "result_state": result_state,
        "qualification_score": score,
        "hard_veto": hard_veto,
        "qualification_verdict": verdict,
        "approved_first_output_request_ids": approved,
        "H": len(approved),
        "generator_qualified": verdict == "APPROVE",
        "legacy_p5_allowed": verdict == "APPROVE",
        "nonblocking_quality_baseline_authorized": True,
        "readiness_true_keys": [],
        "decision_sha256": sha256_file(ROOT / P4_DECISION),
        "result_digest": "",
    }
    final["result_digest"] = object_digest(final, "result_digest")
    write_yaml(ROOT / P4_FINAL_RESULT, final)


def approved_p4_rows() -> list[dict[str, Any]]:
    require((ROOT / P4_DECISION).is_file(), "E_P4_DECISION_MISSING")
    decision = read_json(ROOT / P4_DECISION)
    require(decision.get("decision_digest") == object_digest(decision, "decision_digest"), "E_P4_DECISION_DIGEST")
    require(decision.get("qualification_verdict") in {"APPROVE", "REJECT"}, "E_P4_DECISION")
    if decision["qualification_verdict"] == "REJECT":
        require(decision.get("approved_first_output_request_ids") == [], "E_P4_REJECT_APPROVED")
        return []
    require(decision.get("hard_veto") is False, "E_P4_HARD_VETO")
    approved = set(map(str, decision.get("approved_first_output_request_ids", [])))
    outputs = {str(row["request_id"]): row for row in read_jsonl(ROOT / P4_OUTPUTS)}
    mapping = {str(row["request_id"]): row for row in read_jsonl(ROOT / P4_MAPPING)}
    require(approved.issubset(outputs) and approved.issubset(mapping), "E_P4_APPROVED_REF")
    result = []
    for request_id in sorted(approved):
        output = outputs[request_id]
        result.append(
            {
                "baseline_item_id": f"G1V11-H-{request_id}",
                "request_id": request_id,
                "profile_id": output["profile_id"],
                "title": output["title"],
                "body": output["body"],
                "output_digest": output["output_digest"],
                "approval_source": "P4_INDEPENDENT_QUALIFICATION_DECISION",
                "first_acceptable": True,
                "original_first_output_unchanged": True,
                "publishable": False,
                "runtime_consumable": False,
            }
        )
    return result


def build_allocation(
    references: Sequence[Mapping[str, Any]],
    p4_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    existing = Counter(str(row["profile_id"]) for row in [*references, *p4_rows])
    require(set(existing).issubset(PROFILE_IDS), "E_ALLOCATION_PROFILE")
    rows = []
    for profile_id in PROFILE_IDS:
        count = existing[profile_id]
        require(0 <= count <= 12, "E_ALLOCATION_EXISTING", profile_id)
        rows.append(
            {
                "profile_id": profile_id,
                "approved_reference_count": sum(
                    row["profile_id"] == profile_id for row in references
                ),
                "approved_p4_count": sum(
                    row["profile_id"] == profile_id for row in p4_rows
                ),
                "initial_new_candidate_count": 12 - count,
                "approved_positive_target": 12,
            }
        )
    require(sum(row["initial_new_candidate_count"] for row in rows) == 240 - len(references) - len(p4_rows), "E_ALLOCATION_TOTAL")
    return rows


def _normalized_route_record(
    old: Mapping[str, Any], route: ModuleType
) -> dict[str, Any]:
    profile = route.profile_by_id(ROOT)[str(old["profile_id"])]
    required = route.required_slots(profile)
    payload = old.get("actual_input_payload")
    require(isinstance(payload, Mapping), "E_LEGACY_ROUTE_PAYLOAD")
    present = {
        slot_class: sorted(map(str, payload[f"present_{slot_class}_slots"]))
        for slot_class in ("source", "fact", "authorization")
    }
    missing = {
        slot_class: sorted(set(required[slot_class]) - set(present[slot_class]))
        for slot_class in present
    }
    allowed_risks = route.allowed_risk_codes(ROOT)
    risks: set[str] = set()
    guards = set(map(str, payload.get("hard_guard_hits", [])))
    for raw_risk in map(str, payload.get("risk_points", [])):
        if raw_risk in allowed_risks:
            risks.add(raw_risk)
        elif raw_risk.startswith("hard_guard:AGR_"):
            guards.add(raw_risk.split(":", 1)[1])
        elif raw_risk.startswith("AGR_"):
            guards.add(raw_risk)
        else:
            raise BaselineError(f"E_LEGACY_RISK_UNKNOWN:{raw_risk}")
    case_id = str(old["case_id"])
    provided: dict[str, list[dict[str, str]]] = {}
    for slot_class, slot_ids in present.items():
        provided[slot_class] = []
        for slot_id in slot_ids:
            value_ref = f"{case_id}#{slot_class}:{slot_id}"
            provided[slot_class].append(
                {
                    "slot_id": slot_id,
                    "value_ref": value_ref,
                    "value_digest": sha256_bytes(value_ref.encode("utf-8")),
                }
            )
    partial_safe = payload.get("partial_safe") is True
    record: dict[str, Any] = {
        "schema_version": route.CONTRACT_VERSION,
        "task_id": route.TASK_ID,
        "case_id": case_id,
        "profile_id": old["profile_id"],
        "provided": provided,
        "missing": missing,
        "risk_codes": sorted(risks),
        "hard_guard_hits": sorted(guards),
        "degrade_request": {
            "enabled": partial_safe,
            "artifact_type": str(payload.get("requested_degraded_output", "")) if partial_safe else "",
            "payload": dict(payload.get("partial_artifact_payload", {})) if partial_safe else {},
        },
        "provenance": {
            "source_kind": "SYNTHETIC_OPEN_DEVELOPMENT",
            "record_refs": [
                f"{LEGACY_ROUTE_INPUTS.as_posix()}#{case_id}",
            ],
        },
    }
    record["input_digest"] = route.object_digest(record, "input_digest")
    return record


def prepare_routes() -> None:
    require(not (ROOT / ROUTE_ACTUALS).exists(), "E_ROUTE_ACTUAL_ALREADY_FROZEN")
    route = load_module(ROUTE_MODULE_PATH, "gate1_p5_route_contract")
    legacy = read_jsonl(ROOT / LEGACY_ROUTE_INPUTS)
    require(len(legacy) == 60, "E_ROUTE_INPUT_COUNT")
    inputs = [_normalized_route_record(row, route) for row in legacy]
    compiled = [route.compile_route_input(row, ROOT) for row in inputs]
    actuals = [route.evaluate_compiled_route(row, ROOT) for row in compiled]
    require(len(actuals) == 60, "E_ROUTE_ACTUAL_COUNT")
    write_jsonl(ROOT / ROUTE_INPUTS, inputs)
    write_jsonl(ROOT / ROUTE_COMPILED, compiled)
    write_jsonl(ROOT / ROUTE_ACTUALS, actuals)
    freeze = {
        "schema_version": "gate1-v1.1-route-60-actual-freeze-v1.0",
        "task_id": TASK_ID,
        "input_count": 60,
        "compiled_count": 60,
        "actual_count": 60,
        "route_contract_path": ROUTE_MODULE_PATH.as_posix(),
        "route_contract_sha256": sha256_file(ROOT / ROUTE_MODULE_PATH),
        "route_inputs_sha256": sha256_file(ROOT / ROUTE_INPUTS),
        "route_compiled_sha256": sha256_file(ROOT / ROUTE_COMPILED),
        "route_actuals_sha256": sha256_file(ROOT / ROUTE_ACTUALS),
        "gold_answer_loaded_by_actual_runner": False,
        "actuals_frozen_before_gold_comparison": True,
        "audience_content_created_count": sum(
            any(
                row.get(field)
                for field in (
                    "audience_title_created",
                    "audience_body_created",
                    "spoken_script_created",
                )
            )
            for row in actuals
        ),
    }
    freeze["freeze_digest"] = object_digest(freeze, "freeze_digest")
    write_yaml(ROOT / ROUTE_ACTUAL_FREEZE, freeze)


def compare_routes() -> None:
    freeze = read_yaml(ROOT / ROUTE_ACTUAL_FREEZE)
    require(freeze.get("route_actuals_sha256") == sha256_file(ROOT / ROUTE_ACTUALS), "E_ROUTE_ACTUAL_DRIFT")
    actuals = {str(row["case_id"]): row for row in read_jsonl(ROOT / ROUTE_ACTUALS)}
    gold = {str(row["case_id"]): row for row in read_jsonl(ROOT / ROUTE_GOLD)}
    require(len(actuals) == len(gold) == 60 and set(actuals) == set(gold), "E_ROUTE_GOLD_COVERAGE")
    comparisons = []
    for case_id in sorted(actuals):
        actual = actuals[case_id]
        expected = gold[case_id]
        comparisons.append(
            {
                "case_id": case_id,
                "profile_id": actual["profile_id"],
                "actual_primary_action": actual["actual_primary_action"],
                "actual_primary_reason_category": actual["actual_primary_reason_category"],
                "gold_primary_action": expected["gold_primary_action"],
                "gold_primary_reason_category": expected["gold_reason_code"],
                "primary_action_matches_gold": actual["actual_primary_action"] == expected["gold_primary_action"],
                "primary_reason_matches_gold": actual["actual_primary_reason_category"] == expected["gold_reason_code"],
                "audience_content_created": any(
                    actual.get(field)
                    for field in (
                        "audience_title_created",
                        "audience_body_created",
                        "spoken_script_created",
                    )
                ),
            }
        )
    write_jsonl(ROOT / ROUTE_COMPARISONS, comparisons)
    result = {
        "schema_version": "gate1-v1.1-route-60-result-v1.0",
        "task_id": TASK_ID,
        "action_match_count": sum(row["primary_action_matches_gold"] for row in comparisons),
        "reason_match_count": sum(row["primary_reason_matches_gold"] for row in comparisons),
        "audience_content_created_count": sum(row["audience_content_created"] for row in comparisons),
        "actuals_sha256": sha256_file(ROOT / ROUTE_ACTUALS),
        "gold_sha256": sha256_file(ROOT / ROUTE_GOLD),
        "comparison_sha256": sha256_file(ROOT / ROUTE_COMPARISONS),
    }
    result["pass"] = (
        result["action_match_count"] == 60
        and result["reason_match_count"] == 60
        and result["audience_content_created_count"] == 0
    )
    require(result["pass"], "E_ROUTE_60_GATE")
    result["result_digest"] = object_digest(result, "result_digest")
    write_yaml(ROOT / ROUTE_RESULT, result)


def _validate_scenario(row: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "scenario_id",
        "profile_id",
        "scenario_label",
        "core_fact",
        "object_truth",
        "claim_boundary",
        "role_truth",
        "user_goal",
        "assigned_variant",
        "lane_id",
        "source_summary_a",
        "source_summary_b",
        "authorization_scope",
        "curator_identity",
        "curator_session_logical_id",
        "curator_platform_agent_id",
        "synthetic_test_only",
        "scenario_digest",
    }
    require(set(row) == required, "E_SCENARIO_FIELDS")
    require(row.get("schema_version") == "gate1-v1.1-curated-scenario-v1.0", "E_SCENARIO_SCHEMA")
    require(isinstance(row.get("scenario_id"), str) and SCENARIO_ID_RE.fullmatch(str(row["scenario_id"])) is not None, "E_SCENARIO_ID")
    require(isinstance(row.get("profile_id"), str) and PROFILE_RE.fullmatch(str(row["profile_id"])) is not None, "E_SCENARIO_PROFILE")
    require(str(row["scenario_id"])[7:11] == row["profile_id"], "E_SCENARIO_ID_PROFILE")
    for key in (
        "scenario_label",
        "core_fact",
        "object_truth",
        "claim_boundary",
        "user_goal",
        "source_summary_a",
        "source_summary_b",
        "authorization_scope",
        "curator_identity",
        "curator_session_logical_id",
        "curator_platform_agent_id",
    ):
        require(isinstance(row.get(key), str) and bool(str(row[key]).strip()), "E_SCENARIO_TEXT", key)
    require(isinstance(row.get("role_truth"), str), "E_SCENARIO_ROLE_TRUTH")
    require(row.get("assigned_variant") in {"A1", "A2", "B1", "B2"}, "E_SCENARIO_VARIANT")
    require(row.get("lane_id") in {"A", "B"}, "E_SCENARIO_LANE")
    require(str(row["assigned_variant"]).startswith(str(row["lane_id"])), "E_SCENARIO_LANE_VARIANT")
    require(row.get("synthetic_test_only") is True, "E_SCENARIO_NAMESPACE")
    require(row.get("scenario_digest") == object_digest(row, "scenario_digest"), "E_SCENARIO_DIGEST")


def _request_from_scenario(
    scenario: Mapping[str, Any],
    template: Mapping[str, Any],
    author: Mapping[str, Any],
    run_order: int,
) -> dict[str, Any]:
    profile_id = str(scenario["profile_id"])
    suffix = str(scenario["scenario_id"]).rsplit("-", 1)[1]
    prefix = f"G1V11-P5-{profile_id}-{suffix}"
    source_ids = [f"{prefix}-SRC-01", f"{prefix}-SRC-02"]
    authorization_id = f"{prefix}-AUTH-01"
    template_facts = template["typed_material"]["facts"]
    value_by_slot = {
        f"{profile_id.lower()}_core_input_signature": scenario["core_fact"],
        "real_event_or_object_truth": scenario["object_truth"],
        "claim_boundary": scenario["claim_boundary"],
        "real_role_or_person_truth": scenario["role_truth"],
    }
    facts = []
    for index, old_fact in enumerate(template_facts, 1):
        slot_id = str(old_fact["slot_id"])
        require(slot_id in value_by_slot, "E_SCENARIO_SLOT_UNSUPPORTED", f"{profile_id}:{slot_id}")
        value = str(value_by_slot[slot_id])
        require(bool(value.strip()), "E_SCENARIO_SLOT_VALUE", f"{profile_id}:{slot_id}")
        facts.append(
            {
                "authorization_ids": [authorization_id],
                "claim_boundary": scenario["claim_boundary"],
                "fact_id": f"{prefix}-FACT-{index:02d}",
                "fact_value": value,
                "fact_value_digest": sha256_bytes(value.encode("utf-8")),
                "slot_id": slot_id,
                "source_ids": source_ids,
                "synthetic_test_only": True,
            }
        )
    request = copy.deepcopy(dict(template))
    request.update(
        {
            "schema_version": "gate1-v1.1-p5-author-request-v1.0",
            "task_id": TASK_ID,
            "request_id": f"G1V11-P5-POS-{profile_id}-{suffix}",
            "profile_id": profile_id,
            "assigned_variant": scenario["assigned_variant"],
            "run_order": run_order,
            "author_identity": author["author_identity"],
            "author_session_logical_id": author["author_session_logical_id"],
            "author_platform_agent_id": author["author_platform_agent_id"],
            "model_capability_id": MODEL_CAPABILITY,
            "reasoning_effort": REASONING_EFFORT,
            "service_tier": SERVICE_TIER,
            "typed_material": {
                "sources": [
                    {
                        "slot_id": "usable_source_materials",
                        "source_id": source_ids[0],
                        "source_summary": scenario["source_summary_a"],
                        "synthetic_test_only": True,
                    },
                    {
                        "slot_id": "product_or_scene_reference",
                        "source_id": source_ids[1],
                        "source_summary": scenario["source_summary_b"],
                        "synthetic_test_only": True,
                    },
                ],
                "facts": facts,
                "authorizations": [
                    {
                        "authorization_id": authorization_id,
                        "scope_summary": scenario["authorization_scope"],
                        "slot_id": "publication_scope_authorization",
                        "synthetic_test_only": True,
                    }
                ],
                "claim_boundary": scenario["claim_boundary"],
            },
            # Object-truth and boundary facts constrain claims but are not audience
            # copy requirements. The failed third P4 forced those governance facts
            # onto the audience surface; this successor keeps only product content
            # and an applicable human-role fact in the author-visible core.
            "product_core_requirements": [
                {
                    "requirement_id": f"{prefix}-CORE-{index:02d}",
                    "fact_ids": [fact["fact_id"]],
                }
                for index, fact in enumerate(facts, 1)
                if fact["slot_id"]
                in {
                    f"{profile_id.lower()}_core_input_signature",
                    "real_role_or_person_truth",
                }
            ],
            "user_goal": scenario["user_goal"],
            "synthetic_qualification_only": True,
            "publishable": False,
            "runtime_consumable": False,
            "counts_toward_300": False,
            "counts_toward_H": False,
            "author_instruction_path": PRODUCTION_AUTHOR_INSTRUCTION.as_posix(),
            "author_instruction_sha256": sha256_file(
                ROOT / PRODUCTION_AUTHOR_INSTRUCTION
            ),
        }
    )
    request["request_digest"] = object_digest(request, "request_digest")
    return request


def prepare_production() -> None:
    require(not (ROOT / FIRST_OUTPUTS).exists(), "E_PRODUCTION_OUTPUT_ALREADY_EXISTS")
    references = approved_reference_rows()
    p4_rows = approved_p4_rows()
    allocation = build_allocation(references, p4_rows)
    scenario_paths = sorted((ROOT / TASK_ROOT).glob(CURATION_GLOB.split("production/", 1)[1]))
    scenarios = [row for path in scenario_paths for row in read_jsonl(path)]
    for scenario in scenarios:
        _validate_scenario(scenario)
    expected = sum(row["initial_new_candidate_count"] for row in allocation)
    require(len(scenarios) == expected, "E_SCENARIO_COUNT", f"{len(scenarios)}!={expected}")
    scenario_ids = [str(row["scenario_id"]) for row in scenarios]
    require(len(scenario_ids) == len(set(scenario_ids)), "E_SCENARIO_ID_DUPLICATE")
    expected_by_profile = {
        str(row["profile_id"]): int(row["initial_new_candidate_count"])
        for row in allocation
    }
    require(Counter(str(row["profile_id"]) for row in scenarios) == Counter(expected_by_profile), "E_SCENARIO_PROFILE_COUNTS")
    role_manifest = json.loads((ROOT / AUTHOR_ROLE_MANIFEST).read_text(encoding="utf-8"))
    require(isinstance(role_manifest, dict), "E_AUTHOR_ROLE_MANIFEST")
    authors = role_manifest.get("authors")
    require(isinstance(authors, list) and authors, "E_AUTHOR_ROLES")
    author_by_profile: dict[str, dict[str, Any]] = {}
    for author in authors:
        require(isinstance(author, dict), "E_AUTHOR_ROLE_OBJECT")
        require(author.get("model_capability_id") == MODEL_CAPABILITY, "E_AUTHOR_MODEL")
        require(author.get("reasoning_effort") == REASONING_EFFORT, "E_AUTHOR_REASONING")
        require(author.get("service_tier") == SERVICE_TIER, "E_AUTHOR_SERVICE")
        require(author.get("may_review_or_freeze") is False, "E_AUTHOR_REVIEW_BOUNDARY")
        for profile_id in author.get("assigned_profile_ids", []):
            require(profile_id not in author_by_profile, "E_AUTHOR_PROFILE_DUPLICATE", str(profile_id))
            author_by_profile[str(profile_id)] = dict(author)
    require(set(author_by_profile) == set(PROFILE_IDS), "E_AUTHOR_PROFILE_COVERAGE")
    templates = {str(row["profile_id"]): row for row in read_jsonl(ROOT / P4_REQUESTS)}
    require(set(templates) == set(PROFILE_IDS), "E_TEMPLATE_PROFILE_COVERAGE")
    scenarios = sorted(scenarios, key=lambda item: (str(item["profile_id"]), str(item["scenario_id"])))
    requests = [
        _request_from_scenario(
            scenario,
            templates[str(scenario["profile_id"])],
            author_by_profile[str(scenario["profile_id"])],
            index,
        )
        for index, scenario in enumerate(scenarios, 1)
    ]
    requests_by_author: dict[str, list[dict[str, Any]]] = {}
    for request in requests:
        requests_by_author.setdefault(str(request["author_platform_agent_id"]), []).append(request)
    require(
        all(1 <= len(rows) <= 40 for rows in requests_by_author.values()),
        "E_AUTHOR_BATCH_SIZE",
    )
    author_contract = load_module(AUTHOR_MODULE_PATH, "gate1_p5_author_contract")
    author_contract.TASK_ID = TASK_ID
    for request in requests:
        author_contract.validate_request(request)
    write_jsonl(ROOT / REFERENCE_APPROVED, references)
    write_jsonl(ROOT / P4_APPROVED, p4_rows)
    write_jsonl(ROOT / ALLOCATION, allocation)
    write_jsonl(ROOT / AUTHOR_REQUESTS, requests)
    batch_rows = []
    for batch_number, (agent_id, batch_requests) in enumerate(
        sorted(requests_by_author.items()), 1
    ):
        batch = {
            "schema_version": "gate1-v1.1-production-batch-ledger-v1.0",
            "task_id": TASK_ID,
            "batch_id": f"P5-BATCH-{batch_number:03d}",
            "author_platform_agent_id": agent_id,
            "request_ids": sorted(str(row["request_id"]) for row in batch_requests),
            "request_count": len(batch_requests),
            "maximum_candidate_count": 40,
            "first_candidate_only": True,
            "append_only": True,
            "batch_digest": "",
        }
        batch["batch_digest"] = object_digest(batch, "batch_digest")
        batch_rows.append(batch)
    write_jsonl(ROOT / BATCH_LEDGER, batch_rows)
    basis_paths = {
        "active_components": ACTIVE_COMPONENTS,
        "active_control_rules": ACTIVE_RULES,
        "active_component_profile_edges": ACTIVE_EDGES,
        "active_ab_structural_paths": ACTIVE_AB_PATHS,
        "generator_core": GENERATOR_CORE,
        "generator_registry": GENERATOR_REGISTRY,
        "inherited_author_instruction": AUTHOR_INSTRUCTION,
        "production_author_instruction": PRODUCTION_AUTHOR_INSTRUCTION,
        "author_output_contract": AUTHOR_CONTRACT,
        "author_request_template": P4_REQUESTS,
        "route_input_compiler": ROUTE_MODULE_PATH,
        "baseline_contract": CONTRACT,
        "baseline_runner": TASK_ROOT / "p5_p6_baseline.py",
        "author_role_manifest": AUTHOR_ROLE_MANIFEST,
        "curated_scenarios": scenario_paths[0] if len(scenario_paths) == 1 else None,
    }
    hashes = {
        name: sha256_file(ROOT / path)
        for name, path in basis_paths.items()
        if path is not None
    }
    if len(scenario_paths) > 1:
        hashes["curated_scenarios"] = digest_object(
            {path.as_posix(): sha256_file(path) for path in scenario_paths}
        )
    freeze = {
        "schema_version": "gate1-v1.1-production-basis-freeze-v1.0",
        "task_id": TASK_ID,
        "model_capability_id": MODEL_CAPABILITY,
        "reasoning_effort": REASONING_EFFORT,
        "service_tier": SERVICE_TIER,
        "external_provider_allowed": False,
        "approved_reference_count": len(references),
        "approved_p4_count": len(p4_rows),
        "initial_new_candidate_count": len(requests),
        "component_count": len(read_jsonl(ROOT / ACTIVE_COMPONENTS)),
        "control_rule_count": len(read_jsonl(ROOT / ACTIVE_RULES)),
        "component_profile_edge_count": len(read_jsonl(ROOT / ACTIVE_EDGES)),
        "basis_sha256": hashes,
        "reference_approved_sha256": sha256_file(ROOT / REFERENCE_APPROVED),
        "p4_approved_sha256": sha256_file(ROOT / P4_APPROVED),
        "allocation_sha256": sha256_file(ROOT / ALLOCATION),
        "author_requests_sha256": sha256_file(ROOT / AUTHOR_REQUESTS),
        "batch_ledger_sha256": sha256_file(ROOT / BATCH_LEDGER),
        "semantic_candidate_created": False,
        "readiness_changed": False,
    }
    require(freeze["component_count"] == 68, "E_COMPONENT_COUNT")
    require(freeze["control_rule_count"] == 8, "E_CONTROL_RULE_COUNT")
    require(freeze["component_profile_edge_count"] == 85, "E_EDGE_COUNT")
    freeze["freeze_digest"] = object_digest(freeze, "freeze_digest")
    write_yaml(ROOT / PRODUCTION_FREEZE, freeze)


def serialize_author_outputs() -> None:
    freeze = read_yaml(ROOT / PRODUCTION_FREEZE)
    require(freeze.get("author_requests_sha256") == sha256_file(ROOT / AUTHOR_REQUESTS), "E_AUTHOR_REQUEST_DRIFT")
    requests = read_jsonl(ROOT / AUTHOR_REQUESTS)
    raw_paths = sorted((ROOT / TASK_ROOT).glob(RAW_OUTPUT_GLOB.split("production/", 1)[1]))
    raws = [row for path in raw_paths for row in read_jsonl(path)]
    require(len(raws) == len(requests), "E_RAW_OUTPUT_COUNT")
    request_by_id = {str(row["request_id"]): row for row in requests}
    require(len(request_by_id) == len(requests), "E_REQUEST_ID_DUPLICATE")
    author_contract = load_module(AUTHOR_MODULE_PATH, "gate1_p5_author_serializer")
    author_contract.TASK_ID = TASK_ID
    strict = author_contract.frozen_strict_module()
    strict.TASK_ID = TASK_ID
    outputs = []
    external_service_events = []
    seen_request_ids: set[str] = set()
    seen_run_ids: set[str] = set()
    for raw in raws:
        request_id = str(raw.get("request_id"))
        require(request_id in request_by_id, "E_RAW_REQUEST_UNKNOWN", request_id)
        require(request_id not in seen_request_ids, "E_RAW_REQUEST_DUPLICATE", request_id)
        run_id = str(raw.get("run_id"))
        require(run_id not in seen_run_ids, "E_RAW_RUN_ID_DUPLICATE", run_id)
        output = author_contract.serialize(raw, request_by_id[request_id])
        attestation = raw.get("author_attestation")
        require(isinstance(attestation, dict), "E_AUTHOR_ATTESTATION", request_id)
        if attestation.get("external_service_called") is not False:
            external_service_events.append(request_id)
        audience_texts = [
            str(output["title"]),
            *map(str, output["body"]),
            *map(str, output["spoken_lines"]),
            str(output["cta"]),
            *map(str, output["visual_execution"]),
            *map(str, output["audio_execution"]),
        ]
        for text in audience_texts:
            require(
                AUDIENCE_INTERNAL_ID_RE.search(text) is None,
                "E_AUDIENCE_INTERNAL_ID",
                request_id,
            )
            require(
                not any(phrase in text for phrase in AUDIENCE_GOVERNANCE_PHRASES),
                "E_AUDIENCE_GOVERNANCE_PROSE",
                request_id,
            )
        strict.validate_positive_output(output, request_by_id[request_id])
        outputs.append(output)
        seen_request_ids.add(request_id)
        seen_run_ids.add(run_id)
    require(seen_request_ids == set(request_by_id), "E_RAW_REQUEST_COVERAGE")
    outputs.sort(key=lambda row: int(row["run_order"]))
    write_jsonl(ROOT / FIRST_OUTPUTS, outputs)
    exit_audit = {
        "schema_version": "gate1-v1.1-external-exit-audit-v1.0",
        "task_id": TASK_ID,
        "audited_author_output_count": len(raws),
        "external_content_provider_event_request_ids": external_service_events,
        "external_content_provider_call_count": len(external_service_events),
        "execution_agent_is_local_controlled_author": True,
        "git_transport_excluded_from_content_provider_count": True,
        "audit_source": "AUTHOR_ATTESTATIONS_RECOMPUTED_FROM_RAW_OUTPUTS",
        "raw_output_set_digest": digest_object(
            {path.as_posix(): sha256_file(path) for path in raw_paths}
        ),
        "audit_digest": "",
    }
    require(not external_service_events, "E_EXTERNAL_PROVIDER_CALL")
    exit_audit["audit_digest"] = object_digest(exit_audit, "audit_digest")
    write_yaml(ROOT / EXTERNAL_EXIT_AUDIT, exit_audit)
    output_freeze = {
        "schema_version": "gate1-v1.1-positive-first-output-freeze-v1.0",
        "task_id": TASK_ID,
        "request_count": len(requests),
        "first_semantic_output_count": len(outputs),
        "second_candidate_count": 0,
        "replacement_count": 0,
        "author_requests_sha256": sha256_file(ROOT / AUTHOR_REQUESTS),
        "raw_output_set_digest": digest_object(
            {path.as_posix(): sha256_file(path) for path in raw_paths}
        ),
        "first_outputs_sha256": sha256_file(ROOT / FIRST_OUTPUTS),
        "production_basis_freeze_sha256": sha256_file(ROOT / PRODUCTION_FREEZE),
        "external_exit_audit_sha256": sha256_file(ROOT / EXTERNAL_EXIT_AUDIT),
        "counts_toward_300_before_review": 0,
        "publishable_count": 0,
        "runtime_consumable_count": 0,
    }
    output_freeze["freeze_digest"] = object_digest(output_freeze, "freeze_digest")
    write_yaml(ROOT / OUTPUT_FREEZE, output_freeze)


def _review_rows(pattern: str) -> list[dict[str, Any]]:
    relative = pattern.split("review/", 1)[1]
    paths = sorted((ROOT / TASK_ROOT / "review").glob(relative))
    require(paths, "E_PRODUCTION_REVIEW_FILES", pattern)
    return [row for path in paths for row in read_jsonl(path)]


def _validate_production_review_row(
    row: Mapping[str, Any],
    expected_track: str,
    output_by_request: Mapping[str, Mapping[str, Any]],
) -> None:
    require(
        row.get("schema_version") == "gate1-v1.1-production-review-item-v1.0"
        and row.get("task_id") == TASK_ID
        and row.get("review_track") == expected_track,
        "E_PRODUCTION_REVIEW_SCHEMA",
    )
    request_id = str(row.get("request_id"))
    require(request_id in output_by_request, "E_PRODUCTION_REVIEW_REQUEST", request_id)
    output = output_by_request[request_id]
    require(row.get("profile_id") == output["profile_id"], "E_PRODUCTION_REVIEW_PROFILE")
    require(row.get("output_digest") == output["output_digest"], "E_PRODUCTION_REVIEW_OUTPUT")
    require(row.get("model_capability_id") == MODEL_CAPABILITY, "E_PRODUCTION_REVIEW_MODEL")
    require(row.get("reasoning_effort") == REASONING_EFFORT, "E_PRODUCTION_REVIEW_REASONING")
    require(row.get("blank_context") is True, "E_PRODUCTION_REVIEW_CONTEXT")
    for key in (
        "reviewer_identity",
        "reviewer_session_logical_id",
        "reviewer_platform_agent_id",
        "rationale",
    ):
        require(isinstance(row.get(key), str) and bool(str(row[key]).strip()), "E_PRODUCTION_REVIEW_TEXT", key)
    require(
        row.get("blind_profile_choice") in PROFILE_IDS
        and isinstance(row.get("score"), int)
        and 0 <= int(row["score"]) <= 100
        and row.get("grade") in {"A", "B", "C", "D"},
        "E_PRODUCTION_REVIEW_VALUE",
    )
    require(
        isinstance(row.get("first_acceptable"), bool)
        and isinstance(row.get("approved_as_is"), bool)
        and isinstance(row.get("hard_error_codes"), list)
        and isinstance(row.get("formulaic_or_near_duplicate"), bool),
        "E_PRODUCTION_REVIEW_FLAGS",
    )
    require(
        isinstance(row.get("evidence"), list) and bool(row["evidence"]),
        "E_PRODUCTION_REVIEW_EVIDENCE",
    )
    if row["approved_as_is"]:
        require(
            row["grade"] == "A"
            and row["first_acceptable"] is True
            and not row["hard_error_codes"],
            "E_PRODUCTION_REVIEW_FALSE_APPROVAL",
        )
    require(row.get("review_digest") == object_digest(row, "review_digest"), "E_PRODUCTION_REVIEW_DIGEST")


def close_production_review() -> None:
    output_freeze = read_yaml(ROOT / OUTPUT_FREEZE)
    require(
        output_freeze.get("first_outputs_sha256") == sha256_file(ROOT / FIRST_OUTPUTS),
        "E_OUTPUT_DRIFT",
    )
    outputs = read_jsonl(ROOT / FIRST_OUTPUTS)
    output_by_request = {str(row["request_id"]): row for row in outputs}
    require(len(output_by_request) == len(outputs), "E_OUTPUT_REQUEST_DUPLICATE")
    content_rows = _review_rows(PRODUCTION_CONTENT_REVIEW_GLOB)
    fact_rows = _review_rows(PRODUCTION_FACT_REVIEW_GLOB)
    for row in content_rows:
        _validate_production_review_row(row, "CONTENT_VALUE", output_by_request)
    for row in fact_rows:
        _validate_production_review_row(row, "FACT_AUTHORIZATION", output_by_request)
    content_by_request = {str(row["request_id"]): row for row in content_rows}
    fact_by_request = {str(row["request_id"]): row for row in fact_rows}
    require(
        len(content_by_request) == len(content_rows) == len(outputs)
        and set(content_by_request) == set(output_by_request),
        "E_CONTENT_REVIEW_COVERAGE",
    )
    require(len(fact_by_request) == len(fact_rows) >= 48, "E_FACT_REVIEW_COVERAGE")
    fact_profile_counts = Counter(str(row["profile_id"]) for row in fact_rows)
    require(all(fact_profile_counts[profile_id] >= 2 for profile_id in PROFILE_IDS), "E_FACT_REVIEW_PROFILE_COVERAGE")
    role_manifest = read_json(ROOT / AUTHOR_ROLE_MANIFEST)
    authors = role_manifest.get("authors")
    require(isinstance(authors, list), "E_AUTHOR_ROLE_MANIFEST")
    author_values = {
        str(author[key])
        for author in authors
        for key in (
            "author_identity",
            "author_session_logical_id",
            "author_platform_agent_id",
        )
    }
    content_values = {
        str(row[key])
        for row in content_rows
        for key in (
            "reviewer_identity",
            "reviewer_session_logical_id",
            "reviewer_platform_agent_id",
        )
    }
    fact_values = {
        str(row[key])
        for row in fact_rows
        for key in (
            "reviewer_identity",
            "reviewer_session_logical_id",
            "reviewer_platform_agent_id",
        )
    }
    require(not author_values.intersection(content_values | fact_values), "E_AUTHOR_REVIEW_COLLISION")
    require(not content_values.intersection(fact_values), "E_REVIEW_TRACK_COLLISION")
    hard_or_unapproved = {
        request_id
        for request_id, row in content_by_request.items()
        if row["hard_error_codes"] or not row["approved_as_is"]
    }
    require(hard_or_unapproved.issubset(set(fact_by_request)), "E_HIGH_RISK_SECOND_REVIEW")
    approved_request_ids = sorted(
        request_id
        for request_id, row in content_by_request.items()
        if row["approved_as_is"]
        and (
            request_id not in fact_by_request
            or fact_by_request[request_id]["approved_as_is"]
        )
    )
    failures = []
    for request_id in sorted(output_by_request):
        if request_id in approved_request_ids:
            continue
        failures.append(
            {
                "request_id": request_id,
                "profile_id": output_by_request[request_id]["profile_id"],
                "output_digest": output_by_request[request_id]["output_digest"],
                "content_review_digest": content_by_request[request_id]["review_digest"],
                "fact_review_digest": fact_by_request.get(request_id, {}).get("review_digest"),
                "retained_in_first_acceptance_denominator": True,
                "replacement_allowed": False,
            }
        )
    write_jsonl(ROOT / PRODUCTION_FAILURES, failures)
    first_acceptable_count = sum(
        bool(row["first_acceptable"]) for row in content_by_request.values()
    )
    first_acceptance_rate = round(first_acceptable_count / len(outputs), 6)
    formulaic_ids = {
        request_id
        for request_id, row in content_by_request.items()
        if row["formulaic_or_near_duplicate"]
    }
    formulaic_rate = round(len(formulaic_ids) / len(outputs), 6)
    blind_correct_count = sum(
        row["blind_profile_choice"] == row["profile_id"] for row in content_rows
    )
    references = approved_reference_rows()
    p4_rows = approved_p4_rows()
    approved_new_rows = []
    for request_id in approved_request_ids:
        output = output_by_request[request_id]
        approved_new_rows.append(
            {
                "baseline_item_id": f"G1V11-P5-{request_id}",
                "request_id": request_id,
                "profile_id": output["profile_id"],
                "title": output["title"],
                "body": output["body"],
                "spoken_lines": output["spoken_lines"],
                "cta": output["cta"],
                "visual_execution": output["visual_execution"],
                "audio_execution": output["audio_execution"],
                "output_digest": output["output_digest"],
                "approval_source": "P5_INDEPENDENT_PRODUCTION_REVIEWS",
                "content_review_digest": content_by_request[request_id]["review_digest"],
                "fact_review_digest": fact_by_request.get(request_id, {}).get("review_digest"),
                "first_acceptable": bool(content_by_request[request_id]["first_acceptable"]),
                "original_first_output_unchanged": True,
                "publishable": False,
                "runtime_consumable": False,
            }
        )
    combined = [*references, *p4_rows, *approved_new_rows]
    profile_counts = Counter(str(row["profile_id"]) for row in combined)
    first_by_profile = Counter(
        str(row["profile_id"])
        for row in combined
        if row.get("first_acceptable") is True
    )
    lane_counts = Counter(
        str(output_by_request[request_id]["assigned_variant"])[0]
        for request_id in approved_request_ids
    )
    pass_gate = (
        len(combined) == 240
        and all(profile_counts[profile_id] == 12 for profile_id in PROFILE_IDS)
        and first_acceptance_rate >= 0.90
        and all(first_by_profile[profile_id] >= 11 for profile_id in PROFILE_IDS)
        and formulaic_rate <= 0.10
        and blind_correct_count / len(outputs) >= 0.85
        and not failures
        and lane_counts["A"] > 0
        and lane_counts["B"] > 0
    )
    result = {
        "schema_version": "gate1-v1.1-production-review-result-v1.0",
        "task_id": TASK_ID,
        "result_state": "PASS_TO_CANDIDATE_FREEZE" if pass_gate else "STOPPED_PRODUCTION_REPAIR_REQUIRED",
        "first_output_count": len(outputs),
        "first_acceptable_count": first_acceptable_count,
        "first_acceptance_rate": first_acceptance_rate,
        "approved_new_count": len(approved_new_rows),
        "failed_new_count": len(failures),
        "formulaic_or_near_duplicate_count": len(formulaic_ids),
        "formulaic_or_near_duplicate_rate": formulaic_rate,
        "blind_profile_correct_count": blind_correct_count,
        "blind_profile_total": len(outputs),
        "approved_reference_count": len(references),
        "approved_p4_count": len(p4_rows),
        "combined_positive_count": len(combined),
        "profile_counts": dict(sorted(profile_counts.items())),
        "first_acceptable_profile_counts": dict(sorted(first_by_profile.items())),
        "lane_counts": dict(sorted(lane_counts.items())),
        "hard_veto_count": sum(bool(row["hard_error_codes"]) for row in content_rows),
        "pass": pass_gate,
        "review_digest": "",
    }
    result["review_digest"] = object_digest(result, "review_digest")
    write_yaml(ROOT / PRODUCTION_REVIEW_RESULT, result)
    require(pass_gate, "E_PRODUCTION_REVIEW_GATE")
    write_jsonl(ROOT / APPROVED_POSITIVES, combined)
    manifest = {
        "schema_version": "gate1-v1.1-candidate-300-manifest-v1.0",
        "task_id": TASK_ID,
        "candidate_state": "FROZEN_PENDING_INDEPENDENT_FINAL_REVIEW",
        "positive_count": len(combined),
        "route_count": len(read_jsonl(ROOT / ROUTE_COMPARISONS)),
        "total_count": len(combined) + len(read_jsonl(ROOT / ROUTE_COMPARISONS)),
        "profile_positive_counts": dict(sorted(profile_counts.items())),
        "basis_freeze_sha256": sha256_file(ROOT / PRODUCTION_FREEZE),
        "output_freeze_sha256": sha256_file(ROOT / OUTPUT_FREEZE),
        "approved_positives_sha256": sha256_file(ROOT / APPROVED_POSITIVES),
        "route_comparisons_sha256": sha256_file(ROOT / ROUTE_COMPARISONS),
        "route_result_sha256": sha256_file(ROOT / ROUTE_RESULT),
        "production_review_result_sha256": sha256_file(ROOT / PRODUCTION_REVIEW_RESULT),
        "production_failures_sha256": sha256_file(ROOT / PRODUCTION_FAILURES),
        "content_review_set_digest": digest_object(
            {row["request_id"]: row["review_digest"] for row in content_rows}
        ),
        "fact_review_set_digest": digest_object(
            {row["request_id"]: row["review_digest"] for row in fact_rows}
        ),
        "production_role_may_modify_after_freeze": False,
        "readiness_changed": False,
        "manifest_digest": "",
    }
    require(manifest["positive_count"] == 240 and manifest["route_count"] == 60 and manifest["total_count"] == 300, "E_CANDIDATE_COUNTS")
    manifest["manifest_digest"] = object_digest(manifest, "manifest_digest")
    write_yaml(ROOT / CANDIDATE_MANIFEST, manifest)


def _validate_final_review(
    path: Path,
    expected_track: str,
    expected_ids: set[str],
) -> dict[str, Any]:
    review = read_json(ROOT / path)
    require(
        review.get("schema_version") == "gate1-v1.1-final-independent-review-v1.0"
        and review.get("task_id") == TASK_ID
        and review.get("review_track") == expected_track,
        "E_FINAL_REVIEW_SCHEMA",
    )
    require(review.get("blank_context") is True, "E_FINAL_REVIEW_CONTEXT")
    require(review.get("other_final_review_unavailable") is True, "E_FINAL_REVIEW_ISOLATION")
    require(
        review.get("model_capability_id") == MODEL_CAPABILITY
        and review.get("reasoning_effort") == REASONING_EFFORT,
        "E_FINAL_REVIEW_MODEL",
    )
    for key in (
        "reviewer_identity",
        "reviewer_session_logical_id",
        "reviewer_platform_agent_id",
    ):
        require(isinstance(review.get(key), str) and bool(str(review[key]).strip()), "E_FINAL_REVIEW_IDENTITY")
    require(
        review.get("candidate_manifest_sha256") == sha256_file(ROOT / CANDIDATE_MANIFEST),
        "E_FINAL_REVIEW_CANDIDATE_BINDING",
    )
    require(review.get("review_digest") == object_digest(review, "review_digest"), "E_FINAL_REVIEW_DIGEST")
    judgments = review.get("judgments")
    require(isinstance(judgments, list), "E_FINAL_REVIEW_JUDGMENTS")
    per_item: dict[str, dict[str, Any]] = {}
    for item in judgments:
        require(isinstance(item, dict), "E_FINAL_REVIEW_ITEM")
        item_id = str(item.get("baseline_item_id"))
        require(item_id in expected_ids and item_id not in per_item, "E_FINAL_REVIEW_ITEM_ID")
        require(
            isinstance(item.get("approved"), bool)
            and isinstance(item.get("hard_error_codes"), list)
            and isinstance(item.get("rationale"), str)
            and bool(str(item["rationale"]).strip())
            and isinstance(item.get("evidence"), list)
            and bool(item["evidence"]),
            "E_FINAL_REVIEW_ITEM_FIELDS",
        )
        if expected_track == "CONTENT_VALUE":
            require(
                item.get("blind_profile_choice") in PROFILE_IDS
                and isinstance(item.get("score"), int)
                and 0 <= int(item["score"]) <= 100
                and item.get("grade") in {"A", "B", "C", "D"}
                and isinstance(item.get("formulaic_or_near_duplicate"), bool),
                "E_FINAL_CONTENT_REVIEW_FIELDS",
            )
        else:
            require(
                item.get("item_type") in {"POSITIVE", "ROUTE"}
                and item.get("source_traceable") is True
                and item.get("authorization_valid") is True
                and item.get("freeze_intact") is True,
                "E_FINAL_FACT_REVIEW_FIELDS",
            )
        per_item[item_id] = item
    require(set(per_item) == expected_ids, "E_FINAL_REVIEW_COVERAGE", expected_track)
    return {"document": review, "per_item": per_item}


def prepare_final_decision_packet() -> None:
    candidate = read_yaml(ROOT / CANDIDATE_MANIFEST)
    require(candidate.get("manifest_digest") == object_digest(candidate, "manifest_digest"), "E_CANDIDATE_MANIFEST_DIGEST")
    positives = read_jsonl(ROOT / APPROVED_POSITIVES)
    positive_by_id = {str(row["baseline_item_id"]): row for row in positives}
    routes = read_jsonl(ROOT / ROUTE_COMPARISONS)
    route_by_id = {f"G1V11-ROUTE-{row['case_id']}": row for row in routes}
    require(len(positive_by_id) == 240 and len(route_by_id) == 60, "E_FINAL_INPUT_COUNTS")
    content = _validate_final_review(FINAL_CONTENT_REVIEW, "CONTENT_VALUE", set(positive_by_id))
    fact = _validate_final_review(
        FINAL_FACT_REVIEW,
        "FACT_AUTHORIZATION_FREEZE",
        set(positive_by_id) | set(route_by_id),
    )
    content_doc = content["document"]
    fact_doc = fact["document"]
    for field in (
        "reviewer_identity",
        "reviewer_session_logical_id",
        "reviewer_platform_agent_id",
    ):
        require(content_doc.get(field) != fact_doc.get(field), "E_FINAL_REVIEW_IDENTITY_COLLISION")
    prior_values: set[str] = set()
    role_manifest = read_json(ROOT / AUTHOR_ROLE_MANIFEST)
    for author in role_manifest.get("authors", []):
        if isinstance(author, dict):
            prior_values.update(
                str(author.get(key))
                for key in (
                    "author_identity",
                    "author_session_logical_id",
                    "author_platform_agent_id",
                )
            )
    for row in [
        *_review_rows(PRODUCTION_CONTENT_REVIEW_GLOB),
        *_review_rows(PRODUCTION_FACT_REVIEW_GLOB),
    ]:
        prior_values.update(
            str(row.get(key))
            for key in (
                "reviewer_identity",
                "reviewer_session_logical_id",
                "reviewer_platform_agent_id",
            )
        )
    final_values = {
        str(document.get(key))
        for document in (content_doc, fact_doc)
        for key in (
            "reviewer_identity",
            "reviewer_session_logical_id",
            "reviewer_platform_agent_id",
        )
    }
    require(not final_values.intersection(prior_values), "E_FINAL_REVIEW_PRIOR_ROLE_COLLISION")
    disagreements = sorted(
        item_id
        for item_id in positive_by_id
        if content["per_item"][item_id]["approved"]
        != fact["per_item"][item_id]["approved"]
    )
    adjudication_digest = None
    resolved_approved: dict[str, bool] = {}
    if disagreements:
        adjudication = read_json(ROOT / FINAL_ADJUDICATION)
        require(
            adjudication.get("schema_version") == "gate1-v1.1-final-targeted-adjudication-v1.0"
            and adjudication.get("task_id") == TASK_ID,
            "E_FINAL_ADJUDICATION_SCHEMA",
        )
        require(adjudication.get("review_digest") == object_digest(adjudication, "review_digest"), "E_FINAL_ADJUDICATION_DIGEST")
        items = adjudication.get("items")
        require(isinstance(items, list) and len(items) == len(disagreements), "E_FINAL_ADJUDICATION_COUNT")
        for item in items:
            item_id = str(item.get("baseline_item_id"))
            require(item_id in disagreements and item_id not in resolved_approved, "E_FINAL_ADJUDICATION_SCOPE")
            require(isinstance(item.get("approved"), bool), "E_FINAL_ADJUDICATION_VALUE")
            resolved_approved[item_id] = bool(item["approved"])
        require(set(resolved_approved) == set(disagreements), "E_FINAL_ADJUDICATION_COVERAGE")
        adjudication_digest = sha256_file(ROOT / FINAL_ADJUDICATION)
    else:
        require(not (ROOT / FINAL_ADJUDICATION).exists(), "E_FINAL_ADJUDICATION_UNNECESSARY")
    resolved_positive_approved = {
        item_id: (
            resolved_approved[item_id]
            if item_id in resolved_approved
            else bool(content["per_item"][item_id]["approved"])
            and bool(fact["per_item"][item_id]["approved"])
        )
        for item_id in positive_by_id
    }
    route_approved = {
        item_id: bool(fact["per_item"][item_id]["approved"])
        for item_id in route_by_id
    }
    blind_correct = sum(
        item.get("blind_profile_choice") == positive_by_id[item_id]["profile_id"]
        for item_id, item in content["per_item"].items()
    )
    formulaic_count = sum(
        item.get("formulaic_or_near_duplicate") is True
        for item in content["per_item"].values()
    )
    hard_codes = sorted(
        {
            str(code)
            for review in (content, fact)
            for item in review["per_item"].values()
            for code in item["hard_error_codes"]
        }
    )
    production = read_yaml(ROOT / PRODUCTION_REVIEW_RESULT)
    gate_pass = (
        all(resolved_positive_approved.values())
        and all(route_approved.values())
        and blind_correct / 240 >= 0.85
        and formulaic_count / 240 <= 0.10
        and not hard_codes
        and production.get("first_acceptance_rate", 0) >= 0.90
        and all(
            int(production["first_acceptable_profile_counts"].get(profile_id, 0)) >= 11
            for profile_id in PROFILE_IDS
        )
    )
    metrics = {
        "schema_version": "gate1-v1.1-final-review-metrics-v1.0",
        "task_id": TASK_ID,
        "candidate_manifest_sha256": sha256_file(ROOT / CANDIDATE_MANIFEST),
        "content_review_sha256": sha256_file(ROOT / FINAL_CONTENT_REVIEW),
        "fact_review_sha256": sha256_file(ROOT / FINAL_FACT_REVIEW),
        "targeted_adjudication_sha256": adjudication_digest,
        "positive_approved_count": sum(resolved_positive_approved.values()),
        "route_approved_count": sum(route_approved.values()),
        "blind_profile_correct_count": blind_correct,
        "blind_profile_total": 240,
        "formulaic_or_near_duplicate_count": formulaic_count,
        "hard_error_codes": hard_codes,
        "substantive_disagreement_ids": disagreements,
        "first_acceptance_rate": production["first_acceptance_rate"],
        "gate_pass": gate_pass,
        "metrics_digest": "",
    }
    metrics["metrics_digest"] = object_digest(metrics, "metrics_digest")
    write_yaml(ROOT / FINAL_REVIEW_METRICS, metrics)
    packet = {
        "schema_version": "gate1-v1.1-final-coordinator-decision-packet-v1.0",
        "task_id": TASK_ID,
        "decision_authority": "EXTERNAL_INDEPENDENT_FINAL_COORDINATOR",
        "review_metrics_digest": metrics["metrics_digest"],
        "review_metrics_sha256": sha256_file(ROOT / FINAL_REVIEW_METRICS),
        "candidate_manifest_sha256": sha256_file(ROOT / CANDIDATE_MANIFEST),
        "eligible_for_approval": gate_pass,
        "readiness_changed_before_decision": False,
        "packet_digest": "",
    }
    packet["packet_digest"] = object_digest(packet, "packet_digest")
    write_yaml(ROOT / FINAL_DECISION_PACKET, packet)
    require(gate_pass, "E_FINAL_REVIEW_GATE")


def apply_final_decision() -> None:
    metrics = read_yaml(ROOT / FINAL_REVIEW_METRICS)
    packet = read_yaml(ROOT / FINAL_DECISION_PACKET)
    decision = read_json(ROOT / FINAL_DECISION)
    require(metrics.get("metrics_digest") == object_digest(metrics, "metrics_digest"), "E_FINAL_METRICS_DIGEST")
    require(packet.get("packet_digest") == object_digest(packet, "packet_digest"), "E_FINAL_PACKET_DIGEST")
    require(
        decision.get("schema_version") == "gate1-v1.1-final-coordinator-decision-v1.0"
        and decision.get("task_id") == TASK_ID
        and decision.get("decision_authority") == "EXTERNAL_INDEPENDENT_FINAL_COORDINATOR",
        "E_FINAL_DECISION_SCHEMA",
    )
    require(decision.get("review_metrics_digest") == metrics["metrics_digest"], "E_FINAL_DECISION_METRICS")
    require(decision.get("decision_digest") == object_digest(decision, "decision_digest"), "E_FINAL_DECISION_DIGEST")
    score = decision.get("final_score")
    hard_veto = decision.get("hard_veto")
    verdict = decision.get("final_verdict")
    require(isinstance(score, int) and 0 <= score <= 100, "E_FINAL_DECISION_SCORE")
    require(isinstance(hard_veto, bool), "E_FINAL_DECISION_HARD_VETO")
    coordinator_values = {
        str(decision.get(key))
        for key in (
            "coordinator_identity",
            "coordinator_session_logical_id",
            "coordinator_platform_agent_id",
        )
    }
    final_review_values = {
        str(review.get(key))
        for review in (
            read_json(ROOT / FINAL_CONTENT_REVIEW),
            read_json(ROOT / FINAL_FACT_REVIEW),
        )
        for key in (
            "reviewer_identity",
            "reviewer_session_logical_id",
            "reviewer_platform_agent_id",
        )
    }
    require(
        len(coordinator_values) == 3
        and all(value and value != "None" for value in coordinator_values)
        and not coordinator_values.intersection(final_review_values),
        "E_FINAL_COORDINATOR_IDENTITY",
    )
    require(
        verdict == "APPROVE"
        and score >= 90
        and hard_veto is False
        and metrics.get("gate_pass") is True,
        "E_FINAL_DECISION_APPROVAL_GATE",
    )
    candidate = read_yaml(ROOT / CANDIDATE_MANIFEST)
    final_manifest = {
        "schema_version": "gate1-v1.1-final-300-quality-baseline-manifest-v1.0",
        "task_id": TASK_ID,
        "baseline_status": "APPROVED_NONBLOCKING_QUALITY_AND_REGRESSION_BASELINE",
        "positive_count": 240,
        "route_count": 60,
        "total_count": 300,
        "profile_positive_counts": candidate["profile_positive_counts"],
        "approved_positives_sha256": sha256_file(ROOT / APPROVED_POSITIVES),
        "route_comparisons_sha256": sha256_file(ROOT / ROUTE_COMPARISONS),
        "candidate_manifest_sha256": sha256_file(ROOT / CANDIDATE_MANIFEST),
        "final_review_metrics_sha256": sha256_file(ROOT / FINAL_REVIEW_METRICS),
        "final_decision_sha256": sha256_file(ROOT / FINAL_DECISION),
        "generator_core_sha256": read_yaml(ROOT / PRODUCTION_FREEZE)["basis_sha256"]["generator_core"],
        "production_basis_freeze_sha256": sha256_file(ROOT / PRODUCTION_FREEZE),
        "historical_failure_records_retained": True,
        "brand_fact_rag_orchestration_dify_mainline_blocked": False,
        "runtime_or_production_readiness_unlocked": False,
        "manifest_digest": "",
    }
    final_manifest["manifest_digest"] = object_digest(final_manifest, "manifest_digest")
    write_yaml(ROOT / FINAL_BASELINE_MANIFEST, final_manifest)
    result = {
        "schema_version": "gate1-v1.1-final-300-quality-baseline-result-v1.0",
        "task_id": TASK_ID,
        "result_state": "APPROVED_300_NONBLOCKING_BASELINE",
        "final_score": score,
        "hard_veto": hard_veto,
        "positive_count": 240,
        "route_count": 60,
        "total_count": 300,
        "frozen_reference_inventory_count": 120,
        "historical_component_inventory_count": 86,
        "active_component_count": 68,
        "readiness_true_keys": [],
        "nonblocking_for_brand_fact_rag_orchestration_dify": True,
        "final_manifest_sha256": sha256_file(ROOT / FINAL_BASELINE_MANIFEST),
        "result_digest": "",
    }
    result["result_digest"] = object_digest(result, "result_digest")
    write_yaml(ROOT / FINAL_RESULT, result)
    review_request = "\n".join(
        (
            "# Execution Review Request",
            "",
            f"- task_id: `{TASK_ID}`",
            "- requested_review: independent Guardian delivery review",
            "- claimed_state: `APPROVED_300_NONBLOCKING_BASELINE`",
            "- exact_baseline: 240 positive + 60 route = 300",
            "- frozen_reference_inventory: 120 (unchanged)",
            "- historical_component_inventory: 86 (unchanged; 68 active)",
            "- downstream_effect: nonblocking for brand fact, RAG, orchestration and Dify work",
            "- readiness_effect: none; all production/runtime readiness remains false",
            f"- final_manifest_sha256: `{sha256_file(ROOT / FINAL_BASELINE_MANIFEST)}`",
            f"- final_decision_sha256: `{sha256_file(ROOT / FINAL_DECISION)}`",
            "",
        )
    )
    (ROOT / EXECUTION_REVIEW_REQUEST).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / EXECUTION_REVIEW_REQUEST).write_text(review_request, encoding="utf-8")


def check() -> None:
    contract = read_yaml(ROOT / CONTRACT)
    require(contract.get("task_id") == TASK_ID, "E_CONTRACT_TASK")
    require(len(read_jsonl(ROOT / ACTIVE_COMPONENTS)) == 68, "E_COMPONENT_COUNT")
    require(len(read_jsonl(ROOT / ACTIVE_RULES)) == 8, "E_CONTROL_RULE_COUNT")
    require(len(read_jsonl(ROOT / ACTIVE_EDGES)) == 85, "E_EDGE_COUNT")
    if (ROOT / ROUTE_ACTUAL_FREEZE).exists():
        freeze = read_yaml(ROOT / ROUTE_ACTUAL_FREEZE)
        require(freeze.get("route_actuals_sha256") == sha256_file(ROOT / ROUTE_ACTUALS), "E_ROUTE_ACTUAL_DRIFT")
        require(freeze.get("gold_answer_loaded_by_actual_runner") is False, "E_ROUTE_GOLD_LEAK")
    if (ROOT / ROUTE_RESULT).exists():
        result = read_yaml(ROOT / ROUTE_RESULT)
        require(result.get("pass") is True, "E_ROUTE_RESULT")
        require(result.get("action_match_count") == 60, "E_ROUTE_ACTION_COUNT")
        require(result.get("reason_match_count") == 60, "E_ROUTE_REASON_COUNT")
        require(result.get("actuals_sha256") == sha256_file(ROOT / ROUTE_ACTUALS), "E_ROUTE_RESULT_ACTUAL_DRIFT")
        require(result.get("gold_sha256") == sha256_file(ROOT / ROUTE_GOLD), "E_ROUTE_GOLD_DRIFT")
        require(result.get("comparison_sha256") == sha256_file(ROOT / ROUTE_COMPARISONS), "E_ROUTE_COMPARISON_DRIFT")
    if (ROOT / P4_FINAL_RESULT).exists():
        p4_result = read_yaml(ROOT / P4_FINAL_RESULT)
        require(p4_result.get("result_digest") == object_digest(p4_result, "result_digest"), "E_P4_FINAL_RESULT_DIGEST")
        require(p4_result.get("H") == len(approved_p4_rows()), "E_P4_FINAL_H")
        require(p4_result.get("nonblocking_quality_baseline_authorized") is True, "E_P4_NONBLOCKING_AUTHORIZATION")
    if (ROOT / PRODUCTION_FREEZE).exists():
        freeze = read_yaml(ROOT / PRODUCTION_FREEZE)
        require(freeze.get("component_count") == 68, "E_COMPONENT_COUNT")
        require(freeze.get("control_rule_count") == 8, "E_CONTROL_RULE_COUNT")
        require(freeze.get("component_profile_edge_count") == 85, "E_EDGE_COUNT")
        require(freeze.get("author_requests_sha256") == sha256_file(ROOT / AUTHOR_REQUESTS), "E_AUTHOR_REQUEST_DRIFT")
        require(len(approved_reference_rows()) == 29, "E_REFERENCE_APPROVED_RECOMPUTE")
        basis_paths = {
            "active_components": ACTIVE_COMPONENTS,
            "active_control_rules": ACTIVE_RULES,
            "active_component_profile_edges": ACTIVE_EDGES,
            "active_ab_structural_paths": ACTIVE_AB_PATHS,
            "generator_core": GENERATOR_CORE,
            "generator_registry": GENERATOR_REGISTRY,
            "inherited_author_instruction": AUTHOR_INSTRUCTION,
            "production_author_instruction": PRODUCTION_AUTHOR_INSTRUCTION,
            "author_output_contract": AUTHOR_CONTRACT,
            "author_request_template": P4_REQUESTS,
            "route_input_compiler": ROUTE_MODULE_PATH,
            "baseline_contract": CONTRACT,
            "baseline_runner": TASK_ROOT / "p5_p6_baseline.py",
            "author_role_manifest": AUTHOR_ROLE_MANIFEST,
        }
        for name, path in basis_paths.items():
            require(
                freeze["basis_sha256"].get(name) == sha256_file(ROOT / path),
                "E_PRODUCTION_BASIS_DRIFT",
                name,
            )
        scenario_paths = sorted((ROOT / TASK_ROOT).glob(CURATION_GLOB.split("production/", 1)[1]))
        scenario_digest = (
            sha256_file(scenario_paths[0])
            if len(scenario_paths) == 1
            else digest_object({path.as_posix(): sha256_file(path) for path in scenario_paths})
        )
        require(
            freeze["basis_sha256"].get("curated_scenarios") == scenario_digest,
            "E_PRODUCTION_BASIS_DRIFT",
            "curated_scenarios",
        )
    if (ROOT / OUTPUT_FREEZE).exists():
        freeze = read_yaml(ROOT / OUTPUT_FREEZE)
        require(freeze.get("first_outputs_sha256") == sha256_file(ROOT / FIRST_OUTPUTS), "E_OUTPUT_DRIFT")
        require(freeze.get("second_candidate_count") == 0, "E_SECOND_CANDIDATE")
        require(freeze.get("replacement_count") == 0, "E_REPLACEMENT")
        audit = read_yaml(ROOT / EXTERNAL_EXIT_AUDIT)
        require(
            audit.get("audit_digest") == object_digest(audit, "audit_digest")
            and audit.get("external_content_provider_call_count") == 0
            and audit.get("external_content_provider_event_request_ids") == [],
            "E_EXTERNAL_PROVIDER_AUDIT",
        )
    if (ROOT / CANDIDATE_MANIFEST).exists():
        manifest = read_yaml(ROOT / CANDIDATE_MANIFEST)
        require(manifest.get("manifest_digest") == object_digest(manifest, "manifest_digest"), "E_CANDIDATE_MANIFEST_DIGEST")
        require(manifest.get("positive_count") == 240, "E_CANDIDATE_POSITIVE_COUNT")
        require(manifest.get("route_count") == 60, "E_CANDIDATE_ROUTE_COUNT")
        require(manifest.get("total_count") == 300, "E_CANDIDATE_TOTAL_COUNT")
        require(manifest.get("approved_positives_sha256") == sha256_file(ROOT / APPROVED_POSITIVES), "E_APPROVED_POSITIVE_DRIFT")
    if (ROOT / FINAL_RESULT).exists():
        result = read_yaml(ROOT / FINAL_RESULT)
        require(result.get("result_digest") == object_digest(result, "result_digest"), "E_FINAL_RESULT_DIGEST")
        require(result.get("result_state") == "APPROVED_300_NONBLOCKING_BASELINE", "E_FINAL_RESULT_STATE")
        require(result.get("readiness_true_keys") == [], "E_FINAL_READINESS")
        require(result.get("nonblocking_for_brand_fact_rag_orchestration_dify") is True, "E_FINAL_NONBLOCKING")
    print("GATE1_V11_300_BASELINE_CHECK: PASS")


def selftest() -> None:
    example = {
        "schema_version": "gate1-v1.1-curated-scenario-v1.0",
        "scenario_id": "P5-CUR-CP01-001",
        "profile_id": "CP01",
        "scenario_label": "example",
        "core_fact": "example core fact",
        "object_truth": "example object truth",
        "claim_boundary": "example boundary",
        "role_truth": "example role",
        "user_goal": "example goal",
        "assigned_variant": "A1",
        "lane_id": "A",
        "source_summary_a": "example source a",
        "source_summary_b": "example source b",
        "authorization_scope": "example authorization",
        "curator_identity": "CURATOR-TEST",
        "curator_session_logical_id": "CURATOR-TEST-SESSION",
        "curator_platform_agent_id": "CURATOR-TEST-AGENT",
        "synthetic_test_only": True,
    }
    example["scenario_digest"] = object_digest(example, "scenario_digest")
    _validate_scenario(example)
    changed = copy.deepcopy(example)
    changed["profile_id"] = "CP02"
    try:
        _validate_scenario(changed)
    except BaselineError as error:
        require(str(error).startswith("E_SCENARIO_ID_PROFILE"), "E_SELFTEST_WRONG_FAILURE")
    else:
        raise BaselineError("E_SELFTEST_TAMPER_ACCEPTED")
    require(240 + 60 == 300, "E_SELFTEST_CORE_TOTAL")
    print("GATE1_V11_300_BASELINE_SELFTEST: PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "prepare-routes",
            "compare-routes",
            "prepare-p4-decision",
            "apply-p4-decision",
            "prepare-production",
            "serialize-author",
            "close-production-review",
            "prepare-final-decision",
            "apply-final-decision",
            "check",
            "selftest",
        ),
    )
    args = parser.parse_args()
    if args.command == "prepare-routes":
        prepare_routes()
    elif args.command == "compare-routes":
        compare_routes()
    elif args.command == "prepare-p4-decision":
        prepare_p4_decision_packet()
    elif args.command == "apply-p4-decision":
        apply_p4_decision()
    elif args.command == "prepare-production":
        prepare_production()
    elif args.command == "serialize-author":
        serialize_author_outputs()
    elif args.command == "close-production-review":
        close_production_review()
    elif args.command == "prepare-final-decision":
        prepare_final_decision_packet()
    elif args.command == "apply-final-decision":
        apply_final_decision()
    elif args.command == "check":
        check()
    else:
        selftest()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BaselineError, OSError, ValueError, KeyError, TypeError) as error:
        sys.stderr.write(f"{error}\n")
        raise SystemExit(1)
