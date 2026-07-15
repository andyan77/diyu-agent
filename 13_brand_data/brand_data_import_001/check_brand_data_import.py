#!/usr/bin/env python3
"""Fail-closed checker for the brand-data import-ready package."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

import materialize_brand_data as materialize


if not __debug__:
    sys.stderr.write("check_brand_data_import refuses python -O\n")
    raise SystemExit(2)


LOGGER = logging.getLogger("brand_data_import_checker")
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_RELATIVE_ROOT = Path("13_brand_data/brand_data_import_001")
BASELINE_COMMIT = "95b8b1700b7e96b1d2383465713bef8c36e7f6cb"
MANIFEST_PATH = PACKAGE_ROOT / "materialization_manifest.v1.json"
NARRATIVE_PATH = PACKAGE_ROOT / "data/narrative_units.v1.jsonl"
FACT_PATH = PACKAGE_ROOT / "data/precise_facts.v1.jsonl"
EXPRESSION_PATH = PACKAGE_ROOT / "data/expression_import_candidates.v1.json"
EXAMPLE_PATH = PACKAGE_ROOT / "data/example_references.v1.jsonl"
CASE_PATH = PACKAGE_ROOT / "fixtures/check_cases.v1.jsonl"
RESULT_PATH = PACKAGE_ROOT / "result/brand_data_import_result.v1.json"
IDENTITY_PATH = REPO_ROOT / "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml"
CONTRACT_PATH = REPO_ROOT / "11_product_foundation/public_foundation_001/contract/public_foundation_contract.v1.yaml"
TRUST_REVIEW_PATH = PACKAGE_ROOT / "review/source_fact_authorization_review.v1.yaml"
EXPRESSION_REVIEW_PATH = PACKAGE_ROOT / "review/brand_expression_consumability_review.v1.yaml"
REVIEW_REQUEST_PATH = PACKAGE_ROOT / "review/execution_review_request.v1.md"

READY_STATE = "READY_FOR_PACKAGE_5_REVIEW"
NON_CONSUMABLE_STATES = frozenset(
    {
        "EXPIRED",
        "REVOKED",
        "CONFLICT",
        "PAUSED",
        "RECONFIRMATION_REQUIRED",
        "HOLD_UNREGISTERED_SCOPE",
    }
)
REQUIRED_FALSE_READINESS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "database_imported",
        "generation_eligible",
        "generation_allowed",
        "generator_qualified",
        "retrieval_available",
        "retrieval_ready",
        "runtime_ready",
        "release_ready",
        "production_servable",
        "production_ready",
        "publish_allowed",
    }
)
EXPECTED_PACKAGE_FILES = frozenset(
    {
        Path(".gitattributes"),
        Path("README.md"),
        Path("check_brand_data_import.py"),
        Path("materialize_brand_data.py"),
        Path("materialization_manifest.v1.json"),
        Path("data/example_references.v1.jsonl"),
        Path("data/expression_import_candidates.v1.json"),
        Path("data/narrative_units.v1.jsonl"),
        Path("data/precise_facts.v1.jsonl"),
        Path("fixtures/check_cases.v1.jsonl"),
        Path("result/brand_data_import_result.v1.json"),
        Path("review/execution_review_request.v1.md"),
        Path("review/source_fact_authorization_review.v1.yaml"),
        Path("review/brand_expression_consumability_review.v1.yaml"),
        *(Path("source_snapshots") / source.snapshot_filename for source in materialize.SOURCES),
    }
)


@dataclass
class Bundle:
    manifest: dict[str, Any]
    narratives: list[dict[str, Any]]
    facts: list[dict[str, Any]]
    expression: dict[str, Any]
    examples: list[dict[str, Any]]
    cases: list[dict[str, Any]]
    result: dict[str, Any]
    identity: dict[str, Any]
    contract: dict[str, Any]
    source_bytes: dict[str, bytes]
    reviews: list[dict[str, Any]]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected object: {path}:{line_number}")
        values.append(value)
    return values


def load_yaml_object(path: Path, root_key: str) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get(root_key), dict):
        raise ValueError(f"missing YAML root {root_key}: {path}")
    return cast(dict[str, Any], value[root_key])


def load_bundle() -> Bundle:
    source_bytes = {
        source.source_id: (PACKAGE_ROOT / "source_snapshots" / source.snapshot_filename).read_bytes()
        for source in materialize.SOURCES
    }
    reviews = [
        load_yaml_object(TRUST_REVIEW_PATH, "review"),
        load_yaml_object(EXPRESSION_REVIEW_PATH, "review"),
    ]
    return Bundle(
        manifest=load_json(MANIFEST_PATH),
        narratives=load_jsonl(NARRATIVE_PATH),
        facts=load_jsonl(FACT_PATH),
        expression=load_json(EXPRESSION_PATH),
        examples=load_jsonl(EXAMPLE_PATH),
        cases=load_jsonl(CASE_PATH),
        result=load_json(RESULT_PATH),
        identity=load_yaml_object(IDENTITY_PATH, "simulation_tenant"),
        contract=load_yaml_object(CONTRACT_PATH, "public_foundation_contract"),
        source_bytes=source_bytes,
        reviews=reviews,
    )


def require_fields(record: dict[str, Any], fields: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(fields - record.keys())
    if missing:
        errors.append(f"{label}: missing fields {missing}")


def registered_identifiers(bundle: Bundle) -> tuple[set[str], set[str], set[str]]:
    organizations = {item["organization_id"] for item in bundle.identity["organizations"]}
    stores = {item["store_id"] for item in bundle.identity["stores"]}
    accounts = {item["account_id"] for item in bundle.identity["content_accounts"]}
    return organizations, stores, accounts


def authorization_grants(bundle: Bundle) -> dict[str, dict[str, Any]]:
    return {item["authorization_id"]: item for item in bundle.identity["authorization_grants"]}


def account_organizations(bundle: Bundle) -> dict[str, str]:
    return {item["account_id"]: item["organization_id"] for item in bundle.identity["content_accounts"]}


def allowed_fact_kinds(bundle: Bundle) -> set[str]:
    channels = bundle.contract["brand_fact_contract"]["channels"]
    precise_channel = next(channel for channel in channels if channel["channel_id"] == "VERIFIED_PRECISE_FACT")
    return {str(value) for value in precise_channel["fact_kinds"]}


def parse_temporal(value: Any, *, end_of_day: bool = False) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            boundary = time.max if end_of_day else time.min
            return datetime.combine(date.fromisoformat(value), boundary, tzinfo=timezone.utc)
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def grant_is_current(grant: dict[str, Any]) -> bool:
    evaluated_at = parse_temporal(materialize.PACKAGE_EVALUATED_AT)
    valid_from = parse_temporal(grant.get("valid_from"))
    valid_until = parse_temporal(grant.get("valid_until"), end_of_day=True)
    return (
        evaluated_at is not None
        and valid_from is not None
        and valid_until is not None
        and valid_from <= evaluated_at <= valid_until
    )


def record_is_current(record: dict[str, Any]) -> bool:
    value = record.get("valid_until")
    if value is None:
        return True
    evaluated_at = parse_temporal(materialize.PACKAGE_EVALUATED_AT)
    valid_until = parse_temporal(value, end_of_day=True)
    return evaluated_at is not None and valid_until is not None and evaluated_at <= valid_until


def locator_bytes(source: bytes, locator: dict[str, Any], label: str, errors: list[str]) -> bytes:
    required = {"byte_start", "byte_end_exclusive", "line_start", "line_end"}
    if not required.issubset(locator):
        errors.append(f"{label}: incomplete locator")
        return b""
    byte_start = locator["byte_start"]
    byte_end = locator["byte_end_exclusive"]
    line_start = locator["line_start"]
    line_end = locator["line_end"]
    if not all(isinstance(value, int) for value in (byte_start, byte_end, line_start, line_end)):
        errors.append(f"{label}: locator values must be integers")
        return b""
    lines = source.splitlines(keepends=True)
    if byte_start < 0 or byte_end < byte_start or byte_end > len(source):
        errors.append(f"{label}: byte locator is out of bounds")
        return b""
    if line_start < 1 or line_end < line_start or line_end > len(lines):
        errors.append(f"{label}: line locator is out of bounds")
        return b""
    expected_start = sum(len(line) for line in lines[: line_start - 1])
    expected_end = sum(len(line) for line in lines[:line_end])
    if (byte_start, byte_end) != (expected_start, expected_end):
        errors.append(f"{label}: byte and line locators disagree")
    return source[byte_start:byte_end]


def validate_manifest(bundle: Bundle, errors: list[str]) -> None:
    require_fields(
        bundle.manifest,
        {"task_id", "baseline_commit", "sources", "artifacts", "readiness", "external_calls", "materialization"},
        "manifest",
        errors,
    )
    if bundle.manifest.get("task_id") != materialize.TASK_ID:
        errors.append("manifest: task_id mismatch")
    if bundle.manifest.get("baseline_commit") != BASELINE_COMMIT:
        errors.append("manifest: baseline commit mismatch")

    source_by_id = {item.get("source_id"): item for item in bundle.manifest.get("sources", [])}
    if set(source_by_id) != {source.source_id for source in materialize.SOURCES}:
        errors.append("manifest: source inventory mismatch")
    for source in materialize.SOURCES:
        entry = source_by_id.get(source.source_id, {})
        value = bundle.source_bytes.get(source.source_id, b"")
        if len(value) != source.byte_size or sha256_bytes(value) != source.sha256:
            errors.append(f"{source.source_id}: snapshot byte identity mismatch")
        if entry.get("sha256") != source.sha256 or entry.get("byte_size") != source.byte_size:
            errors.append(f"{source.source_id}: manifest digest or size mismatch")
        if entry.get("snapshot_path") != f"source_snapshots/{source.snapshot_filename}":
            errors.append(f"{source.source_id}: snapshot path mismatch")

    artifacts = {item.get("path"): item for item in bundle.manifest.get("artifacts", [])}
    expected_outputs = {
        "data/example_references.v1.jsonl": materialize.canonical_jsonl(materialize.materialize_examples()),
        "data/expression_import_candidates.v1.json": materialize.canonical_json(
            materialize.materialize_expression_candidates()
        ),
        "data/narrative_units.v1.jsonl": materialize.canonical_jsonl(materialize.materialize_narrative_units()),
        "data/precise_facts.v1.jsonl": materialize.canonical_jsonl(materialize.materialize_precise_facts()),
        "fixtures/check_cases.v1.jsonl": materialize.canonical_jsonl(materialize.materialize_cases()),
    }
    if set(artifacts) != set(expected_outputs):
        errors.append("manifest: derived artifact inventory mismatch")
    for relative_path, expected in expected_outputs.items():
        actual = (PACKAGE_ROOT / relative_path).read_bytes()
        if actual != expected:
            errors.append(f"{relative_path}: materialization is not deterministic")
        entry = artifacts.get(relative_path, {})
        if entry.get("sha256") != sha256_bytes(actual) or entry.get("byte_size") != len(actual):
            errors.append(f"{relative_path}: manifest artifact digest or size mismatch")

    for key in REQUIRED_FALSE_READINESS:
        if bundle.manifest.get("readiness", {}).get(key) is not False:
            errors.append(f"manifest: readiness {key} must remain false")
    if any(value != 0 for value in bundle.manifest.get("external_calls", {}).values()):
        errors.append("manifest: all external call counts must remain zero")
    if bundle.manifest.get("materialization", {}).get("semantic_quality_machine_claimed") is not False:
        errors.append("manifest: checker may not claim semantic quality")


def grant_matches_narrative(record: dict[str, Any], grant: dict[str, Any]) -> bool:
    return (
        grant.get("status") == "GRANTED"
        and grant.get("authorization_kind") == "MATERIAL_AND_FACT_DISCLOSURE"
        and grant.get("disclosure_scope") == "CONTENT_ACCOUNT_ONLY"
        and record.get("disclosure_scope") == grant.get("disclosure_scope")
        and grant_is_current(grant)
        and grant.get("simulation_only") is True
        and grant.get("publish_allowed") is False
        and grant.get("tenant_id") == record.get("tenant_id")
        and grant.get("brand_id") == record.get("brand_id")
        and grant.get("source_organization_id") == record.get("source_organization_id")
        and grant.get("source_store_id") == record.get("source_store_id")
        and set(record.get("applicable_organization_ids", [])) <= set(grant.get("permitted_organization_ids", []))
        and set(record.get("applicable_store_ids", [])) <= set(grant.get("permitted_store_ids", []))
        and set(record.get("applicable_content_account_ids", []))
        <= set(grant.get("permitted_content_account_ids", []))
    )


def validate_narratives(bundle: Bundle, errors: list[str]) -> None:
    required = {
        "unit_id",
        "source_id",
        "source_sha256",
        "heading",
        "locator",
        "body",
        "body_sha256",
        "tenant_id",
        "brand_id",
        "source_organization_id",
        "source_store_id",
        "applicable_organization_ids",
        "applicable_store_ids",
        "applicable_content_account_ids",
        "observed_at",
        "valid_until",
        "authorization_ref",
        "authorization_state",
        "revocation_ref",
        "source_status",
        "import_review_state",
        "runtime_consumable",
        "publish_allowed",
        "semantic_review_required",
    }
    organizations, stores, accounts = registered_identifiers(bundle)
    grants = authorization_grants(bundle)
    seen_ids: set[str] = set()
    for record in bundle.narratives:
        label = str(record.get("unit_id", "unknown narrative"))
        require_fields(record, required, label, errors)
        if label in seen_ids:
            errors.append(f"{label}: duplicate unit_id")
        seen_ids.add(label)
        source_id_value = record.get("source_id")
        if not isinstance(source_id_value, str):
            errors.append(f"{label}: source_id must be a string")
            continue
        source_id = source_id_value
        source = bundle.source_bytes.get(source_id)
        if source is None:
            errors.append(f"{label}: unknown source_id")
            continue
        excerpt = locator_bytes(source, record.get("locator", {}), label, errors)
        if excerpt.decode("utf-8") != record.get("body"):
            errors.append(f"{label}: body does not match snapshot locator")
        if sha256_bytes(excerpt) != record.get("body_sha256"):
            errors.append(f"{label}: body digest mismatch")
        source_spec = next(item for item in materialize.SOURCES if item.source_id == source_id)
        if record.get("source_sha256") != source_spec.sha256:
            errors.append(f"{label}: source digest mismatch")
        if record.get("tenant_id") != materialize.TENANT_ID or record.get("brand_id") != materialize.BRAND_ID:
            errors.append(f"{label}: tenant or brand mismatch")
        if record.get("runtime_consumable") is not False or record.get("publish_allowed") is not False:
            errors.append(f"{label}: package records may not be runtime-consumable or publishable")
        if record.get("semantic_review_required") is not True:
            errors.append(f"{label}: semantic review must remain required")

        state = record.get("import_review_state")
        if state == READY_STATE:
            organization_id = record.get("source_organization_id")
            store_id = record.get("source_store_id")
            applicable_accounts = set(record.get("applicable_content_account_ids", []))
            if organization_id not in organizations or (store_id is not None and store_id not in stores):
                errors.append(f"{label}: ready narrative uses an unregistered source scope")
            if not applicable_accounts or not applicable_accounts <= accounts:
                errors.append(f"{label}: ready narrative uses an unknown or empty account scope")
            authorization_ref = record.get("authorization_ref")
            grant = grants.get(authorization_ref) if isinstance(authorization_ref, str) else None
            if grant is None or not grant_matches_narrative(record, grant):
                errors.append(f"{label}: ready narrative authorization does not close")
            if record.get("authorization_state") != "GRANTED":
                errors.append(f"{label}: ready narrative authorization state is not GRANTED")
            if not record_is_current(record):
                errors.append(f"{label}: ready narrative validity has expired or is invalid")
            if any(
                marker in str(record.get("body", "")) for marker in materialize.UNREGISTERED_SCOPE_MARKERS
            ):
                errors.append(f"{label}: ready narrative body contains an unregistered source scope")
        elif state == "HOLD_UNREGISTERED_SCOPE":
            if any(
                (
                    record.get("source_organization_id") is not None,
                    record.get("source_store_id") is not None,
                    bool(record.get("applicable_organization_ids")),
                    bool(record.get("applicable_store_ids")),
                    bool(record.get("applicable_content_account_ids")),
                    record.get("authorization_ref") is not None,
                )
            ):
                errors.append(f"{label}: unregistered scope leaked into registered mappings")


def grant_matches_fact(record: dict[str, Any], grant: dict[str, Any], account_orgs: dict[str, str]) -> bool:
    account_ids = set(record.get("applicable_content_account_ids", []))
    target_organizations = {account_orgs[account_id] for account_id in account_ids if account_id in account_orgs}
    return (
        grant.get("status") == "GRANTED"
        and grant.get("authorization_kind") in {"FACT_DISCLOSURE", "MATERIAL_AND_FACT_DISCLOSURE"}
        and grant.get("disclosure_scope") == "CONTENT_ACCOUNT_ONLY"
        and record.get("disclosure_scope") == grant.get("disclosure_scope")
        and grant_is_current(grant)
        and grant.get("simulation_only") is True
        and grant.get("publish_allowed") is False
        and grant.get("tenant_id") == record.get("tenant_id")
        and grant.get("brand_id") == record.get("brand_id")
        and grant.get("source_organization_id") == record.get("organization_id")
        and grant.get("source_store_id") == record.get("store_id")
        and account_ids <= set(grant.get("permitted_content_account_ids", []))
        and target_organizations <= set(grant.get("permitted_organization_ids", []))
    )


def validate_facts(bundle: Bundle, errors: list[str]) -> None:
    required = {
        "fact_id",
        "tenant_id",
        "brand_id",
        "organization_id",
        "store_id",
        "applicable_content_account_ids",
        "fact_kind",
        "value",
        "source_ref",
        "source_id",
        "source_sha256",
        "locator",
        "source_excerpt",
        "source_excerpt_sha256",
        "effective_at",
        "valid_until",
        "authorization_ref",
        "authorization_state",
        "revocation_ref",
        "disclosure_scope",
        "status",
        "conflict_group_id",
        "import_review_state",
        "runtime_consumable",
        "publish_allowed",
        "semantic_review_required",
    }
    organizations, stores, accounts = registered_identifiers(bundle)
    account_orgs = account_organizations(bundle)
    contract_fact_kinds = allowed_fact_kinds(bundle)
    grants = authorization_grants(bundle)
    seen_ids: set[str] = set()
    for record in bundle.facts:
        label = str(record.get("fact_id", "unknown fact"))
        require_fields(record, required, label, errors)
        if label in seen_ids:
            errors.append(f"{label}: duplicate fact_id")
        seen_ids.add(label)
        source_id_value = record.get("source_id")
        if not isinstance(source_id_value, str):
            errors.append(f"{label}: source_id must be a string")
            continue
        source_id = source_id_value
        source = bundle.source_bytes.get(source_id)
        if source is None:
            errors.append(f"{label}: unknown source_id")
            continue
        excerpt = locator_bytes(source, record.get("locator", {}), label, errors)
        if excerpt.decode("utf-8") != record.get("source_excerpt"):
            errors.append(f"{label}: source excerpt does not match locator")
        if sha256_bytes(excerpt) != record.get("source_excerpt_sha256"):
            errors.append(f"{label}: source excerpt digest mismatch")
        source_spec = next(item for item in materialize.SOURCES if item.source_id == source_id)
        if record.get("source_sha256") != source_spec.sha256:
            errors.append(f"{label}: source digest mismatch")
        if record.get("fact_kind") not in contract_fact_kinds:
            errors.append(f"{label}: unsupported precise fact kind")
        if record.get("value") is None or record.get("effective_at") is None:
            errors.append(f"{label}: precise fact lacks value or effective time")
        if record.get("runtime_consumable") is not False or record.get("publish_allowed") is not False:
            errors.append(f"{label}: package facts may not be runtime-consumable or publishable")
        if record.get("semantic_review_required") is not True:
            errors.append(f"{label}: semantic review must remain required")

        state = record.get("import_review_state")
        if state == READY_STATE:
            organization_id = record.get("organization_id")
            store_id = record.get("store_id")
            account_ids = set(record.get("applicable_content_account_ids", []))
            if organization_id not in organizations or (store_id is not None and store_id not in stores):
                errors.append(f"{label}: ready fact uses an unregistered source scope")
            if not account_ids or not account_ids <= accounts:
                errors.append(f"{label}: ready fact uses an unknown or empty account scope")
            authorization_ref = record.get("authorization_ref")
            grant = grants.get(authorization_ref) if isinstance(authorization_ref, str) else None
            if grant is None or not grant_matches_fact(record, grant, account_orgs):
                errors.append(f"{label}: ready fact authorization does not close")
            if record.get("authorization_state") != "GRANTED":
                errors.append(f"{label}: ready fact authorization state is not GRANTED")
            if not record_is_current(record):
                errors.append(f"{label}: ready fact validity has expired or is invalid")
        elif state == "HOLD_UNREGISTERED_SCOPE":
            if record.get("organization_id") is not None or record.get("store_id") is not None:
                errors.append(f"{label}: unregistered fact leaked into a registered source scope")
            if record.get("applicable_content_account_ids") or record.get("authorization_ref") is not None:
                errors.append(f"{label}: unregistered fact leaked into account or authorization scope")
        if record.get("status") in NON_CONSUMABLE_STATES and record.get("runtime_consumable") is not False:
            errors.append(f"{label}: non-consumable fact was marked runtime-consumable")
        if record.get("revocation_ref") is not None and record.get("runtime_consumable") is not False:
            errors.append(f"{label}: revoked fact was marked runtime-consumable")
        if record.get("conflict_group_id") is not None and record.get("runtime_consumable") is not False:
            errors.append(f"{label}: conflicted fact was marked runtime-consumable")


def validate_expression(bundle: Bundle, errors: list[str]) -> None:
    expression = bundle.expression
    if expression.get("runtime_authoritative") is not False:
        errors.append("expression: runtime_authoritative must remain false")
    if expression.get("fact_or_authorization_authority") is not False:
        errors.append("expression: may not claim fact or authorization authority")
    if expression.get("light_content_plan_created") is not False:
        errors.append("expression: package may not create a light content plan")
    if expression.get("publish_allowed") is not False:
        errors.append("expression: publish_allowed must remain false")
    guidance = expression.get("brand_guidance_candidate", {})
    if guidance.get("candidate_only") is not True or guidance.get("runtime_profile_ref") is not None:
        errors.append("expression: brand guidance must remain a non-runtime candidate")
    if guidance.get("hard_prohibitions_may_be_weakened") is not False:
        errors.append("expression: brand guidance may not weaken hard prohibitions")

    _, _, accounts = registered_identifiers(bundle)
    mappings = expression.get("account_mappings", [])
    mapped_ids = {item.get("account_id") for item in mappings}
    if len(mappings) != 11 or mapped_ids != accounts:
        errors.append("expression: account mapping must cover exactly the 11 registered accounts")
    for mapping in mappings:
        account_id = mapping.get("account_id", "unknown account")
        if mapping.get("default_profile_ref") != materialize.NEUTRAL_PROFILE_REF:
            errors.append(f"{account_id}: default profile must be the public neutral profile")
        if mapping.get("account_specific_persona_created") is not False:
            errors.append(f"{account_id}: account-specific persona must not be invented")
        if mapping.get("runtime_profile_resolution_claimed") is not False:
            errors.append(f"{account_id}: runtime profile resolution may not be claimed")
        if mapping.get("publish_allowed") is not False:
            errors.append(f"{account_id}: expression mapping may not grant publishing")

    contract_modes = {
        item["mode_ref"] for item in bundle.contract["light_expression_contract"]["high_level_modes"]
    }
    if set(expression.get("available_high_level_mode_refs", [])) != contract_modes:
        errors.append("expression: high-level mode refs drift from the public contract")

    source_ids = set(bundle.source_bytes)
    example_ids: set[str] = set()
    for example in bundle.examples:
        label = str(example.get("example_id", "unknown example"))
        if label in example_ids:
            errors.append(f"{label}: duplicate example_id")
        example_ids.add(label)
        source_id = example.get("source_id")
        if source_id not in source_ids:
            errors.append(f"{label}: unknown example source")
            continue
        excerpt = locator_bytes(bundle.source_bytes[source_id], example.get("locator", {}), label, errors)
        if excerpt.decode("utf-8") != example.get("text") or sha256_bytes(excerpt) != example.get("text_sha256"):
            errors.append(f"{label}: example citation does not close")
        for key in ("may_grant_authorization", "may_grant_fact", "may_grant_scope", "publish_allowed", "runtime_authoritative"):
            if example.get(key) is not False:
                errors.append(f"{label}: {key} must remain false")
    if set(guidance.get("source_example_refs", [])) != example_ids:
        errors.append("expression: brand guidance example references do not close")


def validate_reviews_and_result(bundle: Bundle, errors: list[str]) -> None:
    result = bundle.result
    counts = result.get("counts", {})
    narrative_ready = sum(item.get("import_review_state") == READY_STATE for item in bundle.narratives)
    fact_ready = sum(item.get("import_review_state") == READY_STATE for item in bundle.facts)
    expected_counts = {
        "source_documents": len(materialize.SOURCES),
        "narrative_units": len(bundle.narratives),
        "narrative_review_candidates": narrative_ready,
        "narrative_isolated": len(bundle.narratives) - narrative_ready,
        "precise_facts": len(bundle.facts),
        "precise_fact_review_candidates": fact_ready,
        "precise_fact_isolated": len(bundle.facts) - fact_ready,
        "expression_examples": len(bundle.examples),
        "content_account_mappings": len(bundle.expression.get("account_mappings", [])),
    }
    if counts != expected_counts:
        errors.append("result: counts do not match materialized data")
    if result.get("terminal_state") != "PASS_BRAND_DATA_IMPORT_READY_PENDING_PACKAGE_5":
        errors.append("result: terminal state mismatch")
    for key in REQUIRED_FALSE_READINESS:
        if result.get("readiness", {}).get(key) is not False:
            errors.append(f"result: readiness {key} must remain false")
    if result.get("core_numbers_affected") != {"target_300": False, "frozen_reference_120": False, "historical_components_86": False}:
        errors.append("result: core-number impact must remain false")

    candidate_commit = result.get("candidate_commit")
    if not isinstance(candidate_commit, str) or len(candidate_commit) != 40:
        errors.append("result: candidate_commit must be a full commit hash")
    review_ids: set[str] = set()
    reviewer_ids: set[str] = set()
    session_ids: set[str] = set()
    run_ids: set[str] = set()
    for review in bundle.reviews:
        review_ids.add(str(review.get("review_id")))
        reviewer_ids.add(str(review.get("reviewer_identity_id")))
        session_ids.add(str(review.get("session_id")))
        run_ids.add(str(review.get("run_record_id")))
        if review.get("candidate_commit") != candidate_commit:
            errors.append("review: both reviews must target the fixed candidate commit")
        if review.get("verdict") != "PASS" or not isinstance(review.get("score"), int) or review["score"] < 90:
            errors.append("review: verdict must be PASS with score at least 90")
        if review.get("hard_blockers") != []:
            errors.append("review: hard blockers must be empty")
        if set(review.get("acceptance_coverage", [])) != {f"PKG3-A{index:02d}" for index in range(1, 13)}:
            errors.append("review: acceptance coverage must include PKG3-A01 through PKG3-A12")
    if review_ids != {"SOURCE_FACT_AUTHORIZATION_REVIEW", "BRAND_EXPRESSION_CONSUMABILITY_REVIEW"}:
        errors.append("review: required independent review ids are missing")
    if len(reviewer_ids) != 2 or len(session_ids) != 2 or len(run_ids) != 2:
        errors.append("review: reviewer identity, session, and run record must be distinct")


def validate_bundle(bundle: Bundle) -> list[str]:
    errors: list[str] = []
    validate_manifest(bundle, errors)
    validate_narratives(bundle, errors)
    validate_facts(bundle, errors)
    validate_expression(bundle, errors)
    validate_reviews_and_result(bundle, errors)
    return errors


def git_paths(args: list[str]) -> set[Path]:
    process = subprocess.run(
        ["git", *args, "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return {Path(value.decode("utf-8")) for value in process.stdout.split(b"\0") if value}


def validate_file_scope(errors: list[str]) -> None:
    actual_files = {
        path.relative_to(PACKAGE_ROOT)
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    if actual_files != EXPECTED_PACKAGE_FILES:
        missing = sorted(str(path) for path in EXPECTED_PACKAGE_FILES - actual_files)
        extra = sorted(str(path) for path in actual_files - EXPECTED_PACKAGE_FILES)
        errors.append(f"package file inventory mismatch; missing={missing}, extra={extra}")
    if any(path.is_symlink() for path in PACKAGE_ROOT.rglob("*")):
        errors.append("package may not contain symbolic links")
    attributes_path = PACKAGE_ROOT / ".gitattributes"
    if attributes_path.read_text(encoding="utf-8") != "source_snapshots/** -text -diff\n":
        errors.append("package .gitattributes must preserve snapshot bytes")
    checkers = [path for path in PACKAGE_ROOT.rglob("check*.py") if "__pycache__" not in path.parts]
    if checkers != [Path(__file__).resolve()]:
        errors.append("package must contain exactly one checker entry")

    changed = set()
    changed |= git_paths(["diff", "--name-only", BASELINE_COMMIT])
    changed |= git_paths(["diff", "--cached", "--name-only", BASELINE_COMMIT])
    changed |= git_paths(["ls-files", "--others", "--exclude-standard"])
    outside = sorted(str(path) for path in changed if not path.is_relative_to(PACKAGE_RELATIVE_ROOT))
    if outside:
        errors.append(f"write scope escaped exclusive root: {outside}")

    for source in materialize.SOURCES:
        snapshot_path = PACKAGE_RELATIVE_ROOT / "source_snapshots" / source.snapshot_filename
        process = subprocess.run(
            ["git", "show", f":{snapshot_path}"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
        )
        if process.returncode != 0 or sha256_bytes(process.stdout) != source.sha256:
            errors.append(f"{source.source_id}: Git index does not preserve snapshot bytes")


def mutate_case(bundle: Bundle, mutation: str) -> None:
    ready_fact = next(item for item in bundle.facts if item["import_review_state"] == READY_STATE)
    if mutation in {"NONE", "ASSERT_HOLD_PRESENT", "ASSERT_RECONFIRMATION_PRESENT"}:
        return
    if mutation == "CHANGE_SOURCE_DIGEST":
        bundle.manifest["sources"][0]["sha256"] = "0" * 64
    elif mutation == "SET_UNKNOWN_ORGANIZATION":
        ready_fact["organization_id"] = "ORG-UNKNOWN"
    elif mutation == "MAKE_UNREGISTERED_FACT_READY":
        fact = next(item for item in bundle.facts if item["import_review_state"] == "HOLD_UNREGISTERED_SCOPE")
        fact["import_review_state"] = READY_STATE
        fact["applicable_content_account_ids"] = ["ACCOUNT-DIYU-HQ-OFFICIAL"]
        fact["authorization_ref"] = "AUTH-SIM-001"
    elif mutation == "MAKE_UNREGISTERED_NARRATIVE_READY":
        narrative = next(
            item for item in bundle.narratives if item["import_review_state"] == "HOLD_UNREGISTERED_SCOPE"
        )
        narrative.update(
            {
                "applicable_content_account_ids": ["ACCOUNT-DIYU-HQ-OFFICIAL"],
                "applicable_organization_ids": ["ORG-DIYU-HQ"],
                "applicable_store_ids": [],
                "authorization_ref": "AUTH-SIM-001",
                "authorization_state": "GRANTED",
                "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
                "hold_reason": None,
                "import_review_state": READY_STATE,
                "source_organization_id": "ORG-DIYU-HQ",
                "source_scope_label": "笛语童装总部",
                "source_store_id": None,
            }
        )
    elif mutation == "REMOVE_READY_AUTHORIZATION":
        ready_fact["authorization_ref"] = None
    elif mutation == "USE_REQUIREMENT_CONFIRMATION_GRANT":
        ready_fact["authorization_ref"] = "AUTH-SIM-CONFIRM-001"
    elif mutation == "EXPIRE_READY_GRANT":
        next(
            grant
            for grant in bundle.identity["authorization_grants"]
            if grant["authorization_id"] == ready_fact["authorization_ref"]
        )["valid_until"] = "2026-07-14T23:59:59Z"
    elif mutation == "DEFER_READY_GRANT":
        next(
            grant
            for grant in bundle.identity["authorization_grants"]
            if grant["authorization_id"] == ready_fact["authorization_ref"]
        )["valid_from"] = "2026-07-16T00:00:00Z"
    elif mutation == "REVOKE_READY_FACT_AUTHORIZATION_STATE":
        ready_fact["authorization_state"] = "REVOKED"
    elif mutation == "EXPIRE_READY_FACT_VALIDITY":
        ready_fact["valid_until"] = "2026-07-14"
    elif mutation == "SET_UNSUPPORTED_FACT_KIND":
        ready_fact["fact_kind"] = "STATUS"
    elif mutation == "MAKE_REVOKED_RUNTIME_CONSUMABLE":
        ready_fact["status"] = "REVOKED"
        ready_fact["revocation_ref"] = "REVOCATION-TEST"
        ready_fact["runtime_consumable"] = True
    elif mutation == "MAKE_EXPIRED_RUNTIME_CONSUMABLE":
        ready_fact["status"] = "EXPIRED"
        ready_fact["runtime_consumable"] = True
    elif mutation == "MAKE_CONFLICT_RUNTIME_CONSUMABLE":
        ready_fact["status"] = "CONFLICT"
        ready_fact["conflict_group_id"] = "CONFLICT-TEST"
        ready_fact["runtime_consumable"] = True
    elif mutation == "MAKE_EXPRESSION_AUTHORITATIVE":
        bundle.expression["runtime_authoritative"] = True
        bundle.expression["fact_or_authorization_authority"] = True
    elif mutation == "SET_DATABASE_IMPORTED_TRUE":
        bundle.manifest["readiness"]["database_imported"] = True
    else:
        raise ValueError(f"unknown selftest mutation: {mutation}")


def run_selftests(bundle: Bundle) -> list[str]:
    failures: list[str] = []
    for case in bundle.cases:
        candidate = copy.deepcopy(bundle)
        mutation = str(case["mutation"])
        mutate_case(candidate, mutation)
        if mutation == "ASSERT_HOLD_PRESENT" and not any(
            item["import_review_state"].startswith("HOLD_") for item in candidate.narratives
        ):
            failures.append(f"{case['case_id']}: expected held narrative evidence")
            continue
        if mutation == "ASSERT_RECONFIRMATION_PRESENT" and not any(
            item["status"] == "RECONFIRMATION_REQUIRED" for item in candidate.facts
        ):
            failures.append(f"{case['case_id']}: expected degraded fact evidence")
            continue
        passed = not validate_bundle(candidate)
        if passed is not case["expected_pass"]:
            failures.append(
                f"{case['case_id']}: expected_pass={case['expected_pass']} actual_pass={passed}"
            )
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run compact parameterized positive and negative cases")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bundle = load_bundle()
        errors = validate_bundle(bundle)
        validate_file_scope(errors)
        if args.selftest:
            errors.extend(run_selftests(bundle))
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        LOGGER.error("checker input failure: %s", exc)
        return 1
    if errors:
        for error in errors:
            LOGGER.error("FAIL: %s", error)
        LOGGER.error("brand-data import checker failed with %d issue(s)", len(errors))
        return 1
    LOGGER.info(
        "PASS: sources=%d narratives=%d facts=%d accounts=%d selftest=%s",
        len(materialize.SOURCES),
        len(bundle.narratives),
        len(bundle.facts),
        len(bundle.expression["account_mappings"]),
        args.selftest,
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
