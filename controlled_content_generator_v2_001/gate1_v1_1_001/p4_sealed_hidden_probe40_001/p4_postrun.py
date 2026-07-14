#!/usr/bin/env python3
"""Deterministically materialize and close P4 stages six and seven."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from p4_common import (
    ADJUDICATION,
    BLIND_CATALOG,
    BLIND_MAPPING,
    BLIND_PACKET,
    CHECKPOINT_RESULT,
    CURATOR_RECEIPT,
    DECISION_PACKET,
    DELIVERY_RECEIPT,
    EXPECTED_PROFILES,
    LIFECYCLE,
    MACHINE_REPORT,
    POSITIVE_OUTPUTS,
    PROFILES,
    PROMPT_REVISION,
    READY_KEYS,
    REVIEW_CONTRACT,
    REVIEW_ONE,
    REVIEW_ONE_STAGE,
    REVIEW_PACKET,
    REVIEW_TWO,
    REVIEW_TWO_STAGE,
    ROOT,
    ROUTE_ACTUAL_FREEZE,
    ROUTE_ACTUALS,
    ROUTE_COMPARISONS,
    ROUTE_GOLD,
    ROUTE_INPUTS,
    TASK_ID,
    bind_digest,
    canonical_json,
    load_json,
    load_yaml,
    object_digest,
    read_jsonl,
    recursively_true,
    sha256_bytes,
    sha256_file,
    write_jsonl,
)


REVIEW_ROLES = (
    "CONTENT_VALUE",
    "FACT_AUTHORIZATION",
)
PUBLIC_DIMENSIONS = {
    "truth_and_boundary": 20,
    "apparel_specificity": 10,
    "role_and_brand_consistency": 10,
    "user_value": 10,
    "platform_execution": 10,
    "anti_formula": 10,
}
PRODUCT_DIMENSIONS = {
    "product_core_fidelity": 15,
    "product_specific_narrative_av": 10,
    "continuity": 5,
}
HARD_VETOES = frozenset(
    {
        "FABRICATED_OR_REALITY_WASHED_FACT",
        "UNBOUND_OR_OUT_OF_SCOPE_CLAIM",
        "AUTHORIZATION_OR_PRIVACY_VIOLATION",
        "CROSS_SUBJECT_OR_TENANT_MISUSE",
        "PRODUCT_MANDATORY_INPUT_OR_GUARD_VIOLATION",
        "UNSAFE_OR_DISCRIMINATORY_PROMISE",
        "SUBSTANTIAL_SOURCE_OR_LEGACY_COPY",
        "SELF_APPROVAL_OR_READINESS_ESCALATION",
    }
)
EXPECTED_PROFILE_SET = frozenset(EXPECTED_PROFILES)


class P4PostrunError(ValueError):
    """Fail-closed P4 post-run validation error."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise P4PostrunError(f"{code}{suffix}")


def _unwrap(document: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    if isinstance(value, dict):
        return value
    require(len(document) == 1, "E_P4_WRAPPER", key)
    only = next(iter(document.values()))
    require(isinstance(only, dict), "E_P4_WRAPPER", key)
    return dict(only)


def _json_mapping(path: Path) -> dict[str, Any]:
    value = load_json(path)
    require(
        not recursively_true(value), "E_P4_REVIEW_READINESS_ESCALATION", path.as_posix()
    )
    return value


def _digest_matches(value: Mapping[str, Any], key: str) -> bool:
    return value.get(key) == object_digest(value, key)


def _readiness_false() -> dict[str, bool]:
    values = {key: False for key in sorted(READY_KEYS)}
    values["generator_qualified"] = False
    return values


def _profile_rows(root: Path) -> list[dict[str, Any]]:
    registry = _unwrap(load_yaml(root / PROFILES), "content_product_profile_registry")
    rows = registry.get("profiles")
    require(isinstance(rows, list) and len(rows) == 20, "E_P4_PROFILE_COUNT")
    profiles = [dict(row) for row in rows if isinstance(row, dict)]
    require(len(profiles) == 20, "E_P4_PROFILE_OBJECTS")
    require(
        {row.get("content_product_type_id") for row in profiles}
        == EXPECTED_PROFILE_SET,
        "E_P4_PROFILE_COVERAGE",
    )
    return profiles


def _validate_route_actual_freeze(root: Path) -> list[dict[str, Any]]:
    """Validate the sealed actual receipt before any caller may read route gold."""
    require((root / ROUTE_ACTUAL_FREEZE).is_file(), "E_P4_ROUTE_FREEZE_MISSING")
    freeze = _unwrap(
        load_yaml(root / ROUTE_ACTUAL_FREEZE), "route_actual_freeze_receipt"
    )
    require(freeze.get("task_id") == TASK_ID, "E_P4_ROUTE_FREEZE_TASK")
    require(
        str(freeze.get("schema_version", "")).startswith(
            "gate1-p4-route-actual-freeze"
        ),
        "E_P4_ROUTE_FREEZE_SCHEMA",
    )
    require(_digest_matches(freeze, "actual_freeze_digest"), "E_P4_ROUTE_FREEZE_DIGEST")
    require(
        freeze.get("actual_result_path") == ROUTE_ACTUALS.as_posix(),
        "E_P4_ROUTE_FREEZE_PATH",
    )
    require(
        freeze.get("actual_engine_inputs") == ROUTE_INPUTS.as_posix(),
        "E_P4_ROUTE_INPUT_PATH",
    )
    require(freeze.get("actual_result_count") == 20, "E_P4_ROUTE_FREEZE_COUNT")
    require(
        freeze.get("actual_result_frozen_before_independent_comparison") is True,
        "E_P4_ROUTE_GOLD_ORDER",
    )
    require(
        freeze.get("freeze_path") == ROUTE_ACTUAL_FREEZE.as_posix(),
        "E_P4_ROUTE_FREEZE_SELF_PATH",
    )
    actual_path = root / ROUTE_ACTUALS
    input_path = root / ROUTE_INPUTS
    require(actual_path.is_file() and input_path.is_file(), "E_P4_ROUTE_FROZEN_FILE")
    require(
        freeze.get("actual_result_sha256") == sha256_file(actual_path),
        "E_P4_ROUTE_ACTUAL_SHA",
    )
    require(
        freeze.get("actual_engine_input_sha256") == sha256_file(input_path),
        "E_P4_ROUTE_INPUT_SHA",
    )
    actuals = read_jsonl(actual_path)
    require(len(actuals) == 20, "E_P4_ROUTE_ACTUAL_COUNT")
    case_ids = [row.get("case_id") for row in actuals]
    require(
        all(isinstance(case_id, str) and case_id for case_id in case_ids),
        "E_P4_ROUTE_CASE_ID",
    )
    require(len(set(case_ids)) == 20, "E_P4_ROUTE_CASE_UNIQUE")
    for row in actuals:
        require(row.get("profile_id") in EXPECTED_PROFILE_SET, "E_P4_ROUTE_PROFILE")
        require(
            row.get("actual_primary_action") in {"BLOCK", "DEGRADE", "REQUEST_INPUT"},
            "E_P4_ROUTE_ACTION",
        )
        require(
            row.get("actual_primary_reason_category")
            in {"事实缺失", "授权缺失", "输入冲突"},
            "E_P4_ROUTE_REASON",
        )
        if "route_result_digest" in row:
            require(
                _digest_matches(row, "route_result_digest"), "E_P4_ROUTE_RESULT_DIGEST"
            )
    return actuals


def build_route_comparisons(root: Path = ROOT) -> list[dict[str, Any]]:
    actuals = _validate_route_actual_freeze(root)
    # This is deliberately the first ROUTE_GOLD access in the call graph.
    gold_rows = read_jsonl(root / ROUTE_GOLD)
    require(len(gold_rows) == 20, "E_P4_ROUTE_GOLD_COUNT")
    gold_by_case = {str(row.get("case_id")): row for row in gold_rows}
    require(len(gold_by_case) == 20, "E_P4_ROUTE_GOLD_UNIQUE")
    require(
        set(gold_by_case) == {str(row["case_id"]) for row in actuals},
        "E_P4_ROUTE_GOLD_COVERAGE",
    )
    comparisons: list[dict[str, Any]] = []
    for actual in actuals:
        gold = gold_by_case[str(actual["case_id"])]
        require(
            gold.get("profile_id") == actual.get("profile_id"),
            "E_P4_ROUTE_GOLD_PROFILE",
        )
        require(_digest_matches(gold, "gold_digest"), "E_P4_ROUTE_GOLD_DIGEST")
        audience_created = any(
            bool(actual.get(field))
            for field in (
                "audience_title_created",
                "audience_body_created",
                "spoken_script_created",
            )
        )
        comparison: dict[str, Any] = {
            "schema_version": "gate1-p4-route-comparison-v0.1",
            "task_id": TASK_ID,
            "case_id": actual["case_id"],
            "profile_id": actual["profile_id"],
            "actual_route_result_digest": actual.get("route_result_digest"),
            "gold_digest": gold["gold_digest"],
            "actual_primary_action": actual["actual_primary_action"],
            "gold_primary_action": gold.get("gold_primary_action"),
            "primary_action_matches_gold": actual["actual_primary_action"]
            == gold.get("gold_primary_action"),
            "actual_primary_reason_category": actual["actual_primary_reason_category"],
            "gold_primary_reason_category": gold.get("gold_primary_reason_category"),
            "primary_reason_matches_gold": actual["actual_primary_reason_category"]
            == gold.get("gold_primary_reason_category"),
            "audience_content_created": audience_created,
        }
        comparisons.append(bind_digest(comparison, "comparison_digest"))
    return comparisons


def materialize_route_comparisons(root: Path = ROOT) -> Path:
    rows = build_route_comparisons(root)
    write_jsonl(root / ROUTE_COMPARISONS, rows)
    return root / ROUTE_COMPARISONS


def _validated_positive_outputs(root: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(root / POSITIVE_OUTPUTS)
    require(len(rows) == 20, "E_P4_POSITIVE_COUNT")
    require(
        {row.get("profile_id") for row in rows} == EXPECTED_PROFILE_SET,
        "E_P4_POSITIVE_PROFILES",
    )
    require(
        len({row.get("request_id") for row in rows}) == 20, "E_P4_POSITIVE_REQUESTS"
    )
    require(
        len({row.get("output_digest") for row in rows}) == 20, "E_P4_POSITIVE_DIGESTS"
    )
    for row in rows:
        require(_digest_matches(row, "output_digest"), "E_P4_POSITIVE_DIGEST")
        require(row.get("counts_toward_300") is False, "E_P4_POSITIVE_PREMATURE_COUNT")
        for surface_field in (
            "title",
            "body",
            "spoken_lines",
            "cta",
            "visual_execution",
            "audio_execution",
        ):
            require(
                surface_field in row,
                "E_P4_POSITIVE_SURFACE",
                surface_field,
            )
    return rows


def _forbidden_review_identities(root: Path) -> set[str]:
    outputs = _validated_positive_outputs(root)
    fields = (
        "author_identity",
        "author_platform_agent_id",
        "author_session_logical_id",
        "run_id",
    )
    forbidden = {
        str(row[field])
        for row in outputs
        for field in fields
        if isinstance(row.get(field), str) and row[field]
    }
    receipt = _unwrap(load_yaml(root / CURATOR_RECEIPT), "p4_curator_run_receipt")
    for field in (
        "curator_identity_id",
        "curator_platform_agent_id",
        "curator_session_id",
        "curator_run_id",
    ):
        value = receipt.get(field)
        require(isinstance(value, str) and bool(value), "E_P4_CURATOR_IDENTITY", field)
        forbidden.add(value)
    return forbidden


def _blind_documents(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    outputs = sorted(
        _validated_positive_outputs(root),
        key=lambda row: sha256_bytes(str(row["output_digest"]).encode("utf-8")),
    )
    profiles = _profile_rows(root)
    forbidden_labels = {
        str(value)
        for profile in profiles
        for value in (profile["content_product_type_id"], profile["chinese_label"])
    }
    blind_rows: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []
    for index, output in enumerate(outputs, 1):
        blind_id = f"P4-BLIND-{index:02d}"
        blind: dict[str, Any] = {
            "schema_version": "gate1-p4-blind-positive-v0.1",
            "blind_id": blind_id,
            "synthetic_disclosure": output.get("synthetic_disclosure"),
            "title": output["title"],
            "body": output["body"],
            "spoken_lines": output["spoken_lines"],
            "cta": output["cta"],
            "visual_execution": output["visual_execution"],
            "audio_execution": output["audio_execution"],
            "output_digest": output["output_digest"],
            "content_product_identity_hidden": True,
            "request_identity_hidden": True,
        }
        serialized = canonical_json(blind)
        require(
            not any(label in serialized for label in forbidden_labels),
            "E_P4_BLIND_LABEL_LEAK",
            blind_id,
        )
        require(
            re.search(r"\bCP(?:0[1-9]|1\d|20)\b", serialized) is None,
            "E_P4_BLIND_CP_LEAK",
            blind_id,
        )
        blind_rows.append(blind)
        mapping: dict[str, Any] = {
            "schema_version": "gate1-p4-blind-label-mapping-v0.1",
            "blind_id": blind_id,
            "profile_id": output["profile_id"],
            "request_id": output["request_id"],
            "output_digest": output["output_digest"],
        }
        mappings.append(bind_digest(mapping, "mapping_digest"))
    catalog: list[dict[str, Any]] = []
    for profile in sorted(
        profiles, key=lambda row: str(row["content_product_type_id"])
    ):
        row: dict[str, Any] = {
            "schema_version": "gate1-p4-choice-catalog-row-v0.1",
            "profile_id": profile["content_product_type_id"],
            "chinese_label": profile["chinese_label"],
            "business_purpose": profile["business_purpose"],
            "founder_core_inputs": profile["founder_core_inputs"],
            "target_account_roles": profile["target_account_roles"],
            "target_platforms": profile["target_platforms"],
            "catalog_fixed_before_blind_review": True,
        }
        catalog.append(bind_digest(row, "catalog_row_digest"))
    return blind_rows, catalog, mappings


def _jsonl_payload(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def _yaml_payload(value: Mapping[str, Any]) -> bytes:
    import yaml

    return yaml.safe_dump(
        dict(value), allow_unicode=True, sort_keys=False, width=120
    ).encode("utf-8")


def build_review_documents(root: Path = ROOT) -> dict[Path, bytes]:
    require((root / REVIEW_CONTRACT).is_file(), "E_P4_REVIEW_CONTRACT_MISSING")
    require((root / MACHINE_REPORT).is_file(), "E_P4_MACHINE_REPORT_MISSING")
    comparisons = build_route_comparisons(root)
    blind, catalog, mappings = _blind_documents(root)
    payloads = {
        BLIND_PACKET: _jsonl_payload(blind),
        BLIND_CATALOG: _jsonl_payload(catalog),
        BLIND_MAPPING: _jsonl_payload(mappings),
        ROUTE_COMPARISONS: _jsonl_payload(comparisons),
    }
    contract = _unwrap(load_yaml(root / REVIEW_CONTRACT), "independent_review_contract")
    require(contract.get("task_id") == TASK_ID, "E_P4_REVIEW_CONTRACT_TASK")
    require(_digest_matches(contract, "contract_digest"), "E_P4_REVIEW_CONTRACT_DIGEST")
    artifacts = {
        "blind_positive_visible_stage_1": BLIND_PACKET,
        "fixed_choice_catalog_visible_stage_1": BLIND_CATALOG,
        "label_mapping_reveal_after_both_stage_1_signatures": BLIND_MAPPING,
        "positive_first_outputs": POSITIVE_OUTPUTS,
        "route_comparisons": ROUTE_COMPARISONS,
        "machine_report": MACHINE_REPORT,
        "route_actual_freeze": ROUTE_ACTUAL_FREEZE,
        "review_contract": REVIEW_CONTRACT,
    }
    packet: dict[str, Any] = {
        "schema_version": "gate1-p4-review-packet-v0.1",
        "task_id": TASK_ID,
        "review_contract_path": REVIEW_CONTRACT.as_posix(),
        "review_contract_digest": contract["contract_digest"],
        "stage_order": [
            "EACH_REVIEWER_READS_ONLY_FIXED_CHOICE_CATALOG_AND_BLIND_PACKET",
            "EACH_REVIEWER_WRITES_AND_SIGNS_OWN_TWENTY_PREDICTION_STAGE",
            "REVEAL_SEPARATE_LABEL_MAPPING_ONLY_AFTER_BOTH_STAGE_FILES_VALIDATE",
            "EACH_REVIEWER_READS_FULL_POSITIVE_ROUTE_AND_MACHINE_EVIDENCE",
            "EACH_REVIEWER_WRITES_OWN_SIGNED_FINAL_REPORT",
            "TARGETED_ADJUDICATION_ONLY_IF_RAW_REPORTS_SUBSTANTIVELY_DISAGREE",
        ],
        "artifacts": {
            name: {
                "path": path.as_posix(),
                "sha256": sha256_bytes(payloads[path])
                if path in payloads
                else sha256_file(root / path),
            }
            for name, path in artifacts.items()
        },
        "positive_count": 20,
        "route_count": 20,
        "counts_toward_300": 0,
        "founder_qualification_decision_requested": False,
    }
    bind_digest(packet, "packet_digest")
    payloads[REVIEW_PACKET] = _yaml_payload({"p4_review_packet": packet})
    return payloads


def materialize_review_packet(root: Path = ROOT) -> list[Path]:
    documents = build_review_documents(root)
    changed: list[Path] = []
    for relative, payload in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
            changed.append(path)
    return changed


def _review_contract(root: Path) -> dict[str, Any]:
    contract = _unwrap(load_yaml(root / REVIEW_CONTRACT), "independent_review_contract")
    require(contract.get("task_id") == TASK_ID, "E_P4_REVIEW_CONTRACT_TASK")
    require(_digest_matches(contract, "contract_digest"), "E_P4_REVIEW_CONTRACT_DIGEST")
    return contract


def _contract_dimensions(
    contract: Mapping[str, Any], key: str, fallback: Mapping[str, int]
) -> dict[str, int]:
    value = contract.get(key, fallback)
    require(isinstance(value, dict) and value, "E_P4_REVIEW_DIMENSIONS", key)
    dimensions = {str(name): int(maximum) for name, maximum in value.items()}
    require(
        all(maximum > 0 for maximum in dimensions.values()),
        "E_P4_REVIEW_DIMENSION_MAX",
        key,
    )
    return dimensions


def _grade(total: int) -> str:
    if total >= 90:
        return "A"
    if total >= 80:
        return "B"
    if total >= 70:
        return "C"
    return "D"


def validate_blind_stage(
    stage: Mapping[str, Any], expected_role: str, root: Path = ROOT
) -> None:
    require(
        str(stage.get("schema_version", "")).startswith("gate1-p4-blind-stage"),
        "E_P4_BLIND_STAGE_SCHEMA",
    )
    require(stage.get("task_id") == TASK_ID, "E_P4_BLIND_STAGE_TASK")
    require(
        stage.get("review_role", stage.get("reviewer_role")) == expected_role,
        "E_P4_BLIND_STAGE_ROLE",
    )
    require(stage.get("recorded_before_label_reveal") is True, "E_P4_BLIND_STAGE_ORDER")
    require(
        stage.get("label_mapping_accessed") is False, "E_P4_BLIND_STAGE_MAPPING_ACCESS"
    )
    require(
        stage.get("blind_packet_sha256") == sha256_file(root / BLIND_PACKET),
        "E_P4_BLIND_STAGE_PACKET_SHA",
    )
    require(
        stage.get("choice_catalog_sha256") == sha256_file(root / BLIND_CATALOG),
        "E_P4_BLIND_STAGE_CATALOG_SHA",
    )
    require(_digest_matches(stage, "blind_stage_digest"), "E_P4_BLIND_STAGE_DIGEST")
    for field in (
        "review_id",
        "reviewer_identity",
        "reviewer_platform_agent_id",
        "reviewer_session_id",
        "review_run_id",
        "reviewer_model_capability_id",
        "reviewer_reasoning_effort",
    ):
        require(
            isinstance(stage.get(field), str) and bool(str(stage[field]).strip()),
            "E_P4_BLIND_STAGE_IDENTITY",
            field,
        )
    predictions = stage.get("predictions")
    require(
        isinstance(predictions, list) and len(predictions) == 20,
        "E_P4_BLIND_PREDICTION_COUNT",
    )
    blind_ids = {row["blind_id"] for row in read_jsonl(root / BLIND_PACKET)}
    require(
        {row.get("blind_id") for row in predictions if isinstance(row, dict)}
        == blind_ids,
        "E_P4_BLIND_PREDICTION_COVERAGE",
    )
    for prediction in predictions:
        require(isinstance(prediction, dict), "E_P4_BLIND_PREDICTION_OBJECT")
        require(
            set(prediction) == {"blind_id", "predicted_profile_id", "reason"},
            "E_P4_BLIND_PREDICTION_FIELDS",
        )
        require(
            prediction["predicted_profile_id"] in EXPECTED_PROFILE_SET,
            "E_P4_BLIND_PREDICTION_PROFILE",
        )
        require(
            isinstance(prediction["reason"], str)
            and bool(prediction["reason"].strip()),
            "E_P4_BLIND_PREDICTION_REASON",
        )


def _validate_score(
    score: Mapping[str, Any],
    output: Mapping[str, Any],
    public_dimensions: Mapping[str, int],
    product_dimensions: Mapping[str, int],
    allowed_vetoes: frozenset[str],
) -> bool:
    require(
        score.get("request_id") == output.get("request_id"), "E_P4_REVIEW_SCORE_REQUEST"
    )
    public = score.get("public_quality")
    product = score.get("product_quality")
    require(
        isinstance(public, dict) and set(public) == set(public_dimensions),
        "E_P4_REVIEW_PUBLIC_FIELDS",
    )
    require(
        isinstance(product, dict) and set(product) == set(product_dimensions),
        "E_P4_REVIEW_PRODUCT_FIELDS",
    )
    for key, maximum in public_dimensions.items():
        require(
            isinstance(public[key], int) and 0 <= public[key] <= maximum,
            "E_P4_REVIEW_PUBLIC_SCORE",
            key,
        )
    for key, maximum in product_dimensions.items():
        require(
            isinstance(product[key], int) and 0 <= product[key] <= maximum,
            "E_P4_REVIEW_PRODUCT_SCORE",
            key,
        )
    total = sum(public.values()) + sum(product.values())
    grade = _grade(total)
    require(
        score.get("total_score") == total and score.get("grade") == grade,
        "E_P4_REVIEW_SCORE_TOTAL",
    )
    vetoes = score.get("hard_vetoes")
    require(
        isinstance(vetoes, list) and len(vetoes) == len(set(vetoes)),
        "E_P4_REVIEW_HARD_VETOES",
    )
    require(set(vetoes).issubset(allowed_vetoes), "E_P4_REVIEW_HARD_VETO_CODE")
    acceptable = grade in {"A", "B"} and not vetoes
    require(score.get("first_acceptable") is acceptable, "E_P4_REVIEW_ACCEPTABLE")
    require(
        isinstance(score.get("evidence"), list) and bool(score["evidence"]),
        "E_P4_REVIEW_EVIDENCE",
    )
    require(isinstance(score.get("defects"), list), "E_P4_REVIEW_DEFECTS")
    return acceptable


def _normalized_positive_reviews(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_rows = report.get("positive_reviews", report.get("positive_scores"))
    require(
        isinstance(raw_rows, list) and len(raw_rows) == 20, "E_P4_REVIEW_SCORE_COUNT"
    )
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        require(isinstance(raw, dict), "E_P4_REVIEW_SCORE_OBJECT")
        row = dict(raw)
        row["public_quality"] = row.get("public_quality", row.get("public_scores"))
        row["product_quality"] = row.get("product_quality", row.get("product_scores"))
        row["hard_vetoes"] = row.get("hard_vetoes", row.get("hard_errors", []))
        rows.append(row)
    return rows


def validate_review_report(
    report: Mapping[str, Any],
    stage: Mapping[str, Any],
    expected_role: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    require(
        str(report.get("schema_version", "")).startswith("gate1-p4-independent-review"),
        "E_P4_REVIEW_SCHEMA",
    )
    report_role = report.get("review_role", report.get("reviewer_role"))
    require(
        report.get("task_id") == TASK_ID and report_role == expected_role,
        "E_P4_REVIEW_ROLE",
    )
    embedded = report.get("blind_stage")
    if embedded is None:
        require(
            report.get("blind_stage_digest") == stage.get("blind_stage_digest"),
            "E_P4_REVIEW_BLIND_STAGE_BINDING",
        )
    else:
        require(
            isinstance(embedded, dict) and embedded == stage,
            "E_P4_REVIEW_BLIND_STAGE_BINDING",
        )
    for field in (
        "review_id",
        "reviewer_identity",
        "reviewer_platform_agent_id",
        "reviewer_session_id",
        "review_run_id",
        "reviewer_model_capability_id",
        "reviewer_reasoning_effort",
    ):
        require(
            report.get(field) == stage.get(field),
            "E_P4_REVIEW_STAGE_IDENTITY_BINDING",
            field,
        )
    require(_digest_matches(report, "signed_record_digest"), "E_P4_REVIEW_SIGNATURE")
    contract = _review_contract(root)
    scoring = contract.get("positive_scoring")
    require(isinstance(scoring, dict), "E_P4_REVIEW_SCORING_CONTRACT")
    public_dimensions = _contract_dimensions(
        scoring, "public_dimensions", PUBLIC_DIMENSIONS
    )
    product_dimensions = _contract_dimensions(
        scoring, "product_dimensions", PRODUCT_DIMENSIONS
    )
    allowed_vetoes = HARD_VETOES
    scores = _normalized_positive_reviews(report)
    require(
        {row.get("profile_id") for row in scores} == EXPECTED_PROFILE_SET,
        "E_P4_REVIEW_SCORE_PROFILES",
    )
    outputs = {row["profile_id"]: row for row in _validated_positive_outputs(root)}
    accepted = 0
    for score in scores:
        require(isinstance(score, dict), "E_P4_REVIEW_SCORE_OBJECT")
        accepted += int(
            _validate_score(
                score,
                outputs[str(score["profile_id"])],
                public_dimensions,
                product_dimensions,
                allowed_vetoes,
            )
        )
    average = round(sum(int(row["total_score"]) for row in scores) / 20, 2)
    for field in ("p4_score", "review_score"):
        if field in report:
            require(report[field] == average, "E_P4_REVIEW_AVERAGE")
    if "first_acceptable_count" in report:
        require(
            report["first_acceptable_count"] == accepted, "E_P4_REVIEW_ACCEPTED_COUNT"
        )
    if "first_acceptance_rate" in report:
        require(
            report["first_acceptance_rate"] == round(accepted / 20, 4),
            "E_P4_REVIEW_ACCEPTED_RATE",
        )
    labels = {row["blind_id"]: row for row in read_jsonl(root / BLIND_MAPPING)}
    predictions = {row["blind_id"]: row for row in stage["predictions"]}
    expected_correct = {
        blind_id: predictions[blind_id]["predicted_profile_id"] == mapping["profile_id"]
        for blind_id, mapping in labels.items()
    }
    correct = sum(expected_correct.values())
    native_rows = report.get("positive_reviews")
    if isinstance(native_rows, list):
        by_blind = {
            row.get("blind_id"): row for row in native_rows if isinstance(row, dict)
        }
        require(set(by_blind) == set(labels), "E_P4_REVIEW_BLIND_ROW_COVERAGE")
        for blind_id, row in by_blind.items():
            require(
                row.get("profile_id") == labels[blind_id]["profile_id"],
                "E_P4_REVIEW_BLIND_PROFILE_BINDING",
            )
            require(
                row.get("blind_top1_correct") is expected_correct[blind_id],
                "E_P4_REVIEW_BLIND_CORRECT",
            )
    if "blind_top1_correct_count" in report:
        require(
            report["blind_top1_correct_count"] == correct, "E_P4_REVIEW_BLIND_CORRECT"
        )
    if "blind_top1_accuracy" in report:
        require(
            report["blind_top1_accuracy"] == round(correct / 20, 4),
            "E_P4_REVIEW_BLIND_RATE",
        )
    formula_ids = report.get("human_confirmed_formula_or_near_duplicate_profile_ids")
    if formula_ids is None:
        formula_ids = [
            row["profile_id"]
            for row in scores
            if row.get("formula_or_near_duplicate") is True
        ]
    hard_ids = report.get("hard_error_profile_ids")
    if hard_ids is None:
        hard_ids = [row["profile_id"] for row in scores if row["hard_vetoes"]]
    require(
        isinstance(formula_ids, list) and len(formula_ids) == len(set(formula_ids)),
        "E_P4_REVIEW_FORMULA_IDS",
    )
    require(
        isinstance(hard_ids, list) and len(hard_ids) == len(set(hard_ids)),
        "E_P4_REVIEW_HARD_IDS",
    )
    require(
        set(formula_ids).issubset(EXPECTED_PROFILE_SET), "E_P4_REVIEW_FORMULA_PROFILE"
    )
    require(set(hard_ids).issubset(EXPECTED_PROFILE_SET), "E_P4_REVIEW_HARD_PROFILE")
    derived_hard_ids = sorted(row["profile_id"] for row in scores if row["hard_vetoes"])
    require(sorted(hard_ids) == derived_hard_ids, "E_P4_REVIEW_HARD_AGGREGATE")
    if "human_confirmed_formula_or_near_duplicate_rate" in report:
        require(
            report["human_confirmed_formula_or_near_duplicate_rate"]
            == round(len(formula_ids) / 20, 4),
            "E_P4_REVIEW_FORMULA_RATE",
        )
    route_pass = _route_metrics(root)["route_gate_pass"]
    route_reviews = report.get("route_reviews")
    require(
        isinstance(route_reviews, list) and len(route_reviews) == 20,
        "E_P4_REVIEW_ROUTE_ROWS",
    )
    expected_routes = {
        row["case_id"]: row for row in read_jsonl(root / ROUTE_COMPARISONS)
    }
    require(
        {row.get("case_id") for row in route_reviews if isinstance(row, dict)}
        == set(expected_routes),
        "E_P4_REVIEW_ROUTE_ROW_COVERAGE",
    )
    for row in route_reviews:
        expected = expected_routes[row["case_id"]]
        require(
            row.get("primary_action_matches_gold")
            is expected["primary_action_matches_gold"],
            "E_P4_REVIEW_ROUTE_ACTION",
        )
        require(
            row.get("primary_reason_matches_gold")
            is expected["primary_reason_matches_gold"],
            "E_P4_REVIEW_ROUTE_REASON",
        )
    if "route_hard_gate_pass" in report:
        require(report["route_hard_gate_pass"] is route_pass, "E_P4_REVIEW_ROUTE_GATE")
    report_pass = (
        accepted >= 18
        and correct >= 17
        and len(formula_ids) <= 2
        and not hard_ids
        and route_pass
    )
    require(
        report.get("overall_verdict") == ("PASS" if report_pass else "FAIL"),
        "E_P4_REVIEW_VERDICT",
    )
    return {
        "score": average,
        "accepted_count": accepted,
        "blind_correct_count": correct,
        "formula_ids": sorted(formula_ids),
        "hard_ids": sorted(hard_ids),
        "pass": report_pass,
    }


def load_and_validate_reviews(
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    stage_one = _json_mapping(root / REVIEW_ONE_STAGE)
    stage_two = _json_mapping(root / REVIEW_TWO_STAGE)
    validate_blind_stage(stage_one, REVIEW_ROLES[0], root)
    validate_blind_stage(stage_two, REVIEW_ROLES[1], root)
    report_one = _json_mapping(root / REVIEW_ONE)
    report_two = _json_mapping(root / REVIEW_TWO)
    identity_fields = (
        "reviewer_identity",
        "reviewer_platform_agent_id",
        "reviewer_session_id",
        "review_run_id",
    )
    identities = [
        stage[field] for stage in (stage_one, stage_two) for field in identity_fields
    ]
    require(len(set(identities)) == 8, "E_P4_REVIEW_IDENTITY_COLLISION")
    require(
        not set(identities).intersection(_forbidden_review_identities(root)),
        "E_P4_REVIEW_UPSTREAM_IDENTITY_COLLISION",
    )
    metrics_one = validate_review_report(report_one, stage_one, REVIEW_ROLES[0], root)
    metrics_two = validate_review_report(report_two, stage_two, REVIEW_ROLES[1], root)
    return report_one, report_two, metrics_one, metrics_two


def substantive_disagreements(
    one: Mapping[str, Any], two: Mapping[str, Any]
) -> list[dict[str, Any]]:
    first = {row["profile_id"]: row for row in _normalized_positive_reviews(one)}
    second = {row["profile_id"]: row for row in _normalized_positive_reviews(two)}
    disagreements: list[dict[str, Any]] = []
    for profile_id in EXPECTED_PROFILES:
        reasons: list[str] = []
        if (
            first[profile_id]["first_acceptable"]
            != second[profile_id]["first_acceptable"]
        ):
            reasons.append("FIRST_ACCEPTANCE_DISAGREEMENT")
        if set(first[profile_id]["hard_vetoes"]) != set(
            second[profile_id]["hard_vetoes"]
        ):
            reasons.append("HARD_VETO_DISAGREEMENT")
        if reasons:
            disagreements.append({"profile_id": profile_id, "reasons": reasons})
    route_one = all(
        row.get("primary_action_matches_gold") is True
        and row.get("primary_reason_matches_gold") is True
        for row in one["route_reviews"]
    )
    route_two = all(
        row.get("primary_action_matches_gold") is True
        and row.get("primary_reason_matches_gold") is True
        for row in two["route_reviews"]
    )
    if route_one != route_two:
        disagreements.append(
            {"profile_id": "ROUTE_GATE", "reasons": ["ROUTE_GATE_DISAGREEMENT"]}
        )
    return disagreements


def _validate_adjudication(
    disagreements: list[dict[str, Any]],
    one: Mapping[str, Any],
    two: Mapping[str, Any],
    root: Path,
) -> dict[str, Any] | None:
    path = root / ADJUDICATION
    if not disagreements:
        require(not path.exists(), "E_P4_ADJUDICATION_WITHOUT_DISAGREEMENT")
        return None
    require(path.is_file(), "E_P4_ADJUDICATION_REQUIRED")
    adjudication = _json_mapping(path)
    require(
        str(adjudication.get("schema_version", "")).startswith(
            "gate1-p4-targeted-adjudication"
        ),
        "E_P4_ADJUDICATION_SCHEMA",
    )
    require(adjudication.get("task_id") == TASK_ID, "E_P4_ADJUDICATION_TASK")
    require(
        adjudication.get("targeted_items") == disagreements, "E_P4_ADJUDICATION_SCOPE"
    )
    require(
        adjudication.get("full_batch_rereviewed") is False,
        "E_P4_ADJUDICATION_FULL_BATCH",
    )
    require(
        adjudication.get("source_reports_preserved") is True,
        "E_P4_ADJUDICATION_SOURCE_REPORTS",
    )
    require(
        adjudication.get("all_substantive_disagreements_closed") is True,
        "E_P4_ADJUDICATION_OPEN",
    )
    require(
        _digest_matches(adjudication, "adjudication_digest"), "E_P4_ADJUDICATION_DIGEST"
    )
    excluded = {
        one["reviewer_identity"],
        two["reviewer_identity"],
        one["reviewer_platform_agent_id"],
        two["reviewer_platform_agent_id"],
    }
    require(
        adjudication.get("adjudicator_identity") not in excluded,
        "E_P4_ADJUDICATOR_COLLISION",
    )
    require(
        adjudication.get("adjudicator_platform_agent_id") not in excluded,
        "E_P4_ADJUDICATOR_COLLISION",
    )
    expected_profiles = sorted(
        row["profile_id"]
        for row in disagreements
        if row["profile_id"] in EXPECTED_PROFILE_SET
    )
    require(
        sorted(adjudication.get("reviewed_profile_ids", [])) == expected_profiles,
        "E_P4_ADJUDICATION_PROFILE_SCOPE",
    )
    return adjudication


def _route_metrics(root: Path) -> dict[str, Any]:
    expected = build_route_comparisons(root)
    require((root / ROUTE_COMPARISONS).is_file(), "E_P4_ROUTE_COMPARISON_MISSING")
    stored = read_jsonl(root / ROUTE_COMPARISONS)
    require(stored == expected, "E_P4_ROUTE_COMPARISON_DRIFT")
    action_count = sum(bool(row["primary_action_matches_gold"]) for row in stored)
    reason_count = sum(bool(row["primary_reason_matches_gold"]) for row in stored)
    audience_count = sum(bool(row["audience_content_created"]) for row in stored)
    return {
        "route_case_count": len(stored),
        "route_action_match_count": action_count,
        "route_reason_match_count": reason_count,
        "route_audience_content_count": audience_count,
        "route_gate_pass": len(stored) == action_count == reason_count == 20
        and audience_count == 0,
    }


def recompute_checkpoint_metrics(root: Path = ROOT) -> dict[str, Any]:
    one, two, metrics_one, metrics_two = load_and_validate_reviews(root)
    disagreements = substantive_disagreements(one, two)
    adjudication = _validate_adjudication(disagreements, one, two, root)
    route = _route_metrics(root)
    formula_union = sorted(
        set(metrics_one["formula_ids"]).union(metrics_two["formula_ids"])
    )
    hard_union = sorted(set(metrics_one["hard_ids"]).union(metrics_two["hard_ids"]))
    thresholds = {
        "review_one_first_acceptable_18_of_20": metrics_one["accepted_count"] >= 18,
        "review_two_first_acceptable_18_of_20": metrics_two["accepted_count"] >= 18,
        "review_one_blind_top1_17_of_20": metrics_one["blind_correct_count"] >= 17,
        "review_two_blind_top1_17_of_20": metrics_two["blind_correct_count"] >= 17,
        "formula_union_at_most_2": len(formula_union) <= 2,
        "hard_error_union_zero": not hard_union,
        "route_action_20_of_20": route["route_action_match_count"] == 20,
        "route_reason_20_of_20": route["route_reason_match_count"] == 20,
        "route_audience_content_zero": route["route_audience_content_count"] == 0,
        "raw_report_verdicts_both_pass": metrics_one["pass"] and metrics_two["pass"],
        "all_true_disagreements_closed": not disagreements or adjudication is not None,
    }
    return {
        "review_one": metrics_one,
        "review_two": metrics_two,
        "formula_profile_ids_union": formula_union,
        "hard_error_profile_ids_union": hard_union,
        "substantive_disagreements": disagreements,
        "adjudication_used": adjudication is not None,
        "route": route,
        "thresholds": thresholds,
        "all_thresholds_met": all(thresholds.values()),
    }


def _artifact_record(root: Path, path: Path) -> dict[str, Any]:
    return {"path": path.as_posix(), "sha256": sha256_file(root / path)}


def build_final_documents(root: Path = ROOT) -> dict[Path, bytes]:
    metrics = recompute_checkpoint_metrics(root)
    pass_pending = bool(metrics["all_thresholds_met"])
    state = (
        "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION"
        if pass_pending
        else "STOPPED_RETURN_TO_P3"
    )
    h_candidate: dict[str, Any] = {
        "status": "CANDIDATE_PENDING_FOUNDER_QUALIFICATION_DECISION"
        if pass_pending
        else "NOT_ADMITTED",
        "candidate_positive_count": 20 if pass_pending else 0,
        "candidate_source": _artifact_record(root, POSITIVE_OUTPUTS),
        "founder_admitted_to_H": False,
        "H_admitted_count": 0,
        "counts_toward_300": 0,
    }
    checkpoint: dict[str, Any] = {
        "schema_version": "gate1-p4-checkpoint-result-v0.1",
        "task_id": TASK_ID,
        "prompt_revision": PROMPT_REVISION,
        "result_state": state,
        "p4_execution_complete": True,
        "contract_thresholds_met": pass_pending,
        "founder_qualification_decision_required": pass_pending,
        "founder_qualification_decision_recorded": False,
        "generator_qualified": False,
        "qualification_eligibility": False,
        "p5_allowed": False,
        "metrics_recomputed_from_raw_signed_reports": metrics,
        "evidence": {
            "route_actual_freeze": _artifact_record(root, ROUTE_ACTUAL_FREEZE),
            "route_comparisons": _artifact_record(root, ROUTE_COMPARISONS),
            "review_one_stage": _artifact_record(root, REVIEW_ONE_STAGE),
            "review_two_stage": _artifact_record(root, REVIEW_TWO_STAGE),
            "review_one_signed_report": _artifact_record(root, REVIEW_ONE),
            "review_two_signed_report": _artifact_record(root, REVIEW_TWO),
            "adjudication": _artifact_record(root, ADJUDICATION)
            if metrics["adjudication_used"]
            else None,
        },
        "H_candidate": h_candidate,
        "H": [],
        "readiness": _readiness_false(),
    }
    bind_digest(checkpoint, "result_digest")
    decision: dict[str, Any] = {
        "schema_version": "gate1-p4-founder-qualification-decision-packet-v0.1",
        "task_id": TASK_ID,
        "decision_state": "PENDING_EXTERNAL_COORDINATOR_DECISION"
        if pass_pending
        else "NOT_ELIGIBLE_FOR_DECISION",
        "decision_received": False,
        "approved_hidden_positive_ids": [],
        "checkpoint_result_path": CHECKPOINT_RESULT.as_posix(),
        "checkpoint_result_digest": checkpoint["result_digest"],
        "contract_thresholds_met": pass_pending,
        "machine_or_executor_qualification_decision": None,
        "founder_decision": None,
        "founder_decision_recorded": False,
        "generator_qualified": False,
        "qualification_eligibility": False,
        "H_candidate": h_candidate,
        "decision_boundary": {
            "only_founder_may_decide_generator_qualification": True,
            "packet_does_not_self_qualify_generator": True,
            "no_production_or_generation_authority_granted": True,
        },
        "readiness": _readiness_false(),
    }
    bind_digest(decision, "packet_digest")
    receipt: dict[str, Any] = {
        "schema_version": "gate1-p4-delivery-receipt-v0.1",
        "task_id": TASK_ID,
        "result_state": state,
        "checkpoint_result_path": CHECKPOINT_RESULT.as_posix(),
        "checkpoint_result_digest": checkpoint["result_digest"],
        "decision_packet_path": DECISION_PACKET.as_posix(),
        "decision_packet_digest": decision["packet_digest"],
        "review_reports_preserved_unmodified": True,
        "qualification_decision_created_by_executor": False,
        "generator_qualified": False,
        "H_only_candidate": True,
        "H_admitted_count": 0,
        "counts_toward_300": 0,
        "readiness_all_false": True,
    }
    bind_digest(receipt, "receipt_digest")
    lifecycle = _unwrap(load_yaml(root / LIFECYCLE), "p4_lifecycle")
    require(lifecycle.get("task_id") == TASK_ID, "E_P4_LIFECYCLE_TASK")
    require(_digest_matches(lifecycle, "lifecycle_digest"), "E_P4_LIFECYCLE_DIGEST")
    require(
        lifecycle.get("state") in {"RUN_FROZEN", "REVIEW_CLOSED", state},
        "E_P4_LIFECYCLE_STAGE",
    )
    lifecycle.update(
        {"state": state, "generator_qualified": False, "p5_allowed": False}
    )
    bind_digest(lifecycle, "lifecycle_digest")
    return {
        CHECKPOINT_RESULT: _yaml_payload({"p4_checkpoint_result": checkpoint}),
        DECISION_PACKET: _yaml_payload(
            {"founder_qualification_decision_packet": decision}
        ),
        DELIVERY_RECEIPT: _yaml_payload({"p4_delivery_receipt": receipt}),
        LIFECYCLE: _yaml_payload({"p4_lifecycle": lifecycle}),
    }


def materialize_final(root: Path = ROOT) -> list[Path]:
    documents = build_final_documents(root)
    changed: list[Path] = []
    for relative, payload in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
            changed.append(path)
    return changed


def check_stage_six(root: Path = ROOT) -> None:
    expected = build_review_documents(root)
    for relative, payload in expected.items():
        require(
            (root / relative).read_bytes() == payload,
            "E_P4_STAGE6_DRIFT",
            relative.as_posix(),
        )


def check_stage_seven(root: Path = ROOT) -> None:
    expected = build_final_documents(root)
    for relative, payload in expected.items():
        require(
            (root / relative).read_bytes() == payload,
            "E_P4_STAGE7_DRIFT",
            relative.as_posix(),
        )


def _emit(status: str, paths: Sequence[Path] = ()) -> None:
    sys.stdout.write(
        canonical_json({"status": status, "paths": [path.as_posix() for path in paths]})
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--stage-six", action="store_true")
    actions.add_argument("--validate-reviews", action="store_true")
    actions.add_argument("--stage-seven", action="store_true")
    actions.add_argument("--check-stage-six", action="store_true")
    actions.add_argument("--check-stage-seven", action="store_true")
    args = parser.parse_args()
    if args.stage_six:
        _emit("P4_STAGE_SIX_REVIEW_PACKET_READY", materialize_review_packet())
    elif args.validate_reviews:
        recompute_checkpoint_metrics()
        _emit("P4_INDEPENDENT_REVIEWS_VALID")
    elif args.stage_seven:
        _emit("P4_STAGE_SEVEN_CHECKPOINT_READY", materialize_final())
    elif args.check_stage_six:
        check_stage_six()
        _emit("P4_STAGE_SIX_CHECK_PASS")
    else:
        check_stage_seven()
        _emit("P4_STAGE_SEVEN_CHECK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
