#!/usr/bin/env python3
"""Materialize Package 5 retrieval data from the frozen Package 3 handoff."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import tempfile
from collections import Counter
from datetime import timezone
from pathlib import Path
from typing import Any, Iterable, cast

import yaml  # type: ignore[import-untyped]

from brand_fact_retrieval import digest_object, parse_timestamp


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
TASK_ID = "DIYU_BRAND_FACT_RETRIEVAL_001"
BASELINE_MASTER_COMMIT = "8475fdf1043e820f37c763b45ee680ea1a98b1e0"
BUILD_AT = "2026-07-15T00:00:00Z"
POLICY_VERSION = "pkg5-evidence-closed-filter-first-v1"

PUBLIC_CONTRACT = Path(
    "11_product_foundation/public_foundation_001/contract/public_foundation_contract.v1.yaml"
)
IDENTITY = Path(
    "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml"
)
PACKAGE_2_MANIFEST = Path(
    "12_expression_service/expression_runtime_adapter_001/service_manifest.v1.yaml"
)
PACKAGE_3_ROOT = Path("13_brand_data/brand_data_import_001")
PACKAGE_3_MANIFEST = PACKAGE_3_ROOT / "materialization_manifest.v1.json"
NARRATIVE_INPUT = PACKAGE_3_ROOT / "data/narrative_units.v1.jsonl"
FACT_INPUT = PACKAGE_3_ROOT / "data/precise_facts.v1.jsonl"
EXPRESSION_INPUT = PACKAGE_3_ROOT / "data/expression_import_candidates.v1.json"
EXAMPLE_INPUT = PACKAGE_3_ROOT / "data/example_references.v1.jsonl"
FIXTURE_PATH = Path("fixtures/retrieval_cases.v1.jsonl")

INPUT_SHA256 = {
    PUBLIC_CONTRACT: "a3aec92fdcc22635bb07bc5d2595ebaa5cfa1f1c9d5fad42cc39481808bbc1af",
    IDENTITY: "65b8242b9b760e64f8e441c4334c68fa76f6dc3a11e2fe2f8f62ad6a887c3cbc",
    PACKAGE_2_MANIFEST: "ca354c12a30990ac84e2267bc22b427450804c18ff44b6cb50a71a79ff56c172",
    PACKAGE_3_MANIFEST: "9f2d86c153e0dbbf2f184a3552b7a58bedf0f10b552ac62603f040da6e96d848",
    NARRATIVE_INPUT: "668700fd0bb7c41ccc1e3d2e9727132f407abb35b5b4c53717a62e18b4f656c9",
    FACT_INPUT: "85a77bd70e07d99d31579028306e50aa312d9a94856f0875178aa16dfabe1bf6",
    EXPRESSION_INPUT: "f5dade80ab3d3ffab8cc7aa1cedab3ddf53a239a9efef8f8375ab547859c9189",
    EXAMPLE_INPUT: "744ea4c5df6630e36f077980f53bd95a78d055fb81821257d376534ff034bb1c",
}

GENERATED_PATHS = (
    Path("data/retrieval_fragments.v1.jsonl"),
    Path("data/verified_precise_facts.v1.jsonl"),
    Path("data/source_dispositions.v1.jsonl"),
    Path("data/expression_candidates.v1.json"),
    Path("retrieval_manifest.v1.json"),
)

NARRATIVE_SEMANTIC_APPROVALS = frozenset(
    {
        "BD-NARR-02-006",
        "BD-NARR-03-002",
        "BD-NARR-03-012",
        "BD-NARR-03-014",
        "BD-NARR-03-015",
        "BD-NARR-03-018",
        "BD-NARR-04-013",
        "BD-NARR-04-019",
        "BD-NARR-05-002",
        "BD-NARR-05-003",
        "BD-NARR-05-011",
        "BD-NARR-05-013",
        "BD-NARR-05-015",
        "BD-NARR-05-016",
        "BD-NARR-05-017",
        "BD-NARR-05-023",
        "BD-NARR-06-002",
        "BD-NARR-06-017",
        "BD-NARR-06-018",
        "BD-NARR-06-021",
        "BD-NARR-06-024",
        "BD-NARR-06-027",
    }
)
NARRATIVE_SEMANTIC_HOLDS = {
    "BD-NARR-05-004": "PACKAGE5_MIXED_RESTRICTED_ASSET_BOUNDARIES",
}
PRODUCT_SUBSECTION_SPLIT_IDS = frozenset({"BD-NARR-04-013"})


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def canonical_jsonl(rows: Iterable[JsonObject]) -> bytes:
    lines = [
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        for row in rows
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def load_json(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def load_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected object: {path}:{line_number}")
        rows.append(value)
    return rows


def load_identity(path: Path) -> JsonObject:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("simulation_tenant"), dict):
        raise ValueError("invalid public simulation identity")
    return cast(JsonObject, document["simulation_tenant"])


def map_rows(rows: object, key: str) -> dict[str, JsonObject]:
    if not isinstance(rows, list):
        raise ValueError(f"invalid identity list: {key}")
    result: dict[str, JsonObject] = {}
    for raw in rows:
        if not isinstance(raw, dict) or not isinstance(raw.get(key), str):
            raise ValueError(f"invalid identity row: {key}")
        identifier = raw[key]
        if identifier in result:
            raise ValueError(f"duplicate identity: {identifier}")
        result[identifier] = raw
    return result


def normalize_source_time(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("source time is missing")
    parsed = parse_timestamp(value)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def earlier_expiry(record_value: object, grant_value: object) -> str:
    grant_time = parse_timestamp(grant_value)
    if record_value in (None, ""):
        return grant_time.isoformat().replace("+00:00", "Z")
    record_time = parse_timestamp(record_value)
    return min(record_time, grant_time).isoformat().replace("+00:00", "Z")


def validate_inputs(repo_root: Path) -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative_path, expected in INPUT_SHA256.items():
        path = repo_root / relative_path
        if not path.is_file():
            raise ValueError(f"input missing: {relative_path}")
        digest = sha256_file(path)
        if digest != expected:
            raise ValueError(f"input drift: {relative_path}")
        actual[relative_path.as_posix()] = digest
    return actual


def validate_source_slice(row: JsonObject, source_manifest: JsonObject, repo_root: Path) -> None:
    sources = source_manifest.get("sources")
    if not isinstance(sources, list):
        raise ValueError("Package 3 source manifest is invalid")
    source_id = row.get("source_id")
    matching = [item for item in sources if isinstance(item, dict) and item.get("source_id") == source_id]
    if len(matching) != 1:
        raise ValueError(f"source not found: {source_id}")
    source = matching[0]
    snapshot_path = source.get("snapshot_path")
    if not isinstance(snapshot_path, str):
        raise ValueError(f"snapshot path missing: {source_id}")
    snapshot = repo_root / PACKAGE_3_ROOT / snapshot_path
    if sha256_file(snapshot) != row.get("source_sha256"):
        raise ValueError(f"source digest mismatch: {source_id}")
    locator = row.get("locator")
    body = row.get("body")
    if not isinstance(locator, dict) or not isinstance(body, str):
        return
    start = locator.get("byte_start")
    end = locator.get("byte_end_exclusive")
    if not isinstance(start, int) or not isinstance(end, int):
        raise ValueError(f"source locator invalid: {row.get('unit_id')}")
    if snapshot.read_bytes()[start:end] != body.encode("utf-8"):
        raise ValueError(f"source body mismatch: {row.get('unit_id')}")


def grant_closes_record(
    row: JsonObject,
    grants: dict[str, JsonObject],
    organizations: dict[str, JsonObject],
    stores: dict[str, JsonObject],
    accounts: dict[str, JsonObject],
    *,
    record_type: str,
) -> tuple[bool, str, JsonObject | None]:
    grant_ref = row.get("authorization_ref")
    if not isinstance(grant_ref, str) or row.get("authorization_state") != "GRANTED":
        return False, "PACKAGE5_AUTHORIZATION_MISSING", None
    grant = grants.get(grant_ref)
    if grant is None or grant.get("status") != "GRANTED":
        return False, "PACKAGE5_AUTHORIZATION_INVALID", grant
    now = parse_timestamp(BUILD_AT)
    if not (
        parse_timestamp(grant.get("valid_from"))
        <= now
        <= parse_timestamp(grant.get("valid_until"))
    ):
        return False, "PACKAGE5_AUTHORIZATION_OUTSIDE_TIME", grant
    source_org_key = "source_organization_id" if record_type == "NARRATIVE" else "organization_id"
    source_store_key = "source_store_id" if record_type == "NARRATIVE" else "store_id"
    source_org = row.get(source_org_key)
    source_store = row.get(source_store_key)
    if not isinstance(source_org, str) or source_org not in organizations:
        return False, "PACKAGE5_SOURCE_ORGANIZATION_UNREGISTERED", grant
    if source_store is not None:
        if not isinstance(source_store, str) or source_store not in stores:
            return False, "PACKAGE5_SOURCE_STORE_UNREGISTERED", grant
        if stores[source_store].get("organization_id") != source_org:
            return False, "PACKAGE5_SOURCE_STORE_SCOPE_MISMATCH", grant
    if (
        grant.get("source_organization_id") != source_org
        or grant.get("source_store_id") != source_store
        or grant.get("tenant_id") != row.get("tenant_id")
        or grant.get("brand_id") != row.get("brand_id")
        or grant.get("disclosure_scope") != row.get("disclosure_scope")
    ):
        return False, "PACKAGE5_AUTHORIZATION_SCOPE_MISMATCH", grant
    target_accounts = row.get("applicable_content_account_ids")
    if not isinstance(target_accounts, list) or not target_accounts:
        return False, "PACKAGE5_TARGET_ACCOUNT_MISSING", grant
    permitted_accounts = grant.get("permitted_content_account_ids")
    if not isinstance(permitted_accounts, list) or any(
        account not in accounts or account not in permitted_accounts for account in target_accounts
    ):
        return False, "PACKAGE5_TARGET_ACCOUNT_NOT_GRANTED", grant
    if record_type == "NARRATIVE":
        target_orgs = row.get("applicable_organization_ids")
        target_stores = row.get("applicable_store_ids")
        if not isinstance(target_orgs, list) or not target_orgs:
            return False, "PACKAGE5_TARGET_ORGANIZATION_MISSING", grant
        if not isinstance(target_stores, list) or not target_stores:
            return False, "PACKAGE5_TARGET_STORE_MISSING", grant
        permitted_orgs = grant.get("permitted_organization_ids")
        permitted_stores = grant.get("permitted_store_ids")
        if not isinstance(permitted_orgs, list) or any(
            org not in organizations or org not in permitted_orgs for org in target_orgs
        ):
            return False, "PACKAGE5_TARGET_ORGANIZATION_NOT_GRANTED", grant
        if not isinstance(permitted_stores, list) or any(
            store not in permitted_stores or (store is not None and store not in stores)
            for store in target_stores
        ):
            return False, "PACKAGE5_TARGET_STORE_NOT_GRANTED", grant
    return True, "PACKAGE5_EVIDENCE_CLOSED", grant


def narrative_disposition(
    row: JsonObject,
    grants: dict[str, JsonObject],
    organizations: dict[str, JsonObject],
    stores: dict[str, JsonObject],
    accounts: dict[str, JsonObject],
) -> tuple[str, str, JsonObject | None]:
    if row.get("import_review_state") != "READY_FOR_PACKAGE_5_REVIEW":
        return "HOLD", str(row.get("hold_reason") or row.get("import_review_state")), None
    if row.get("source_status") != "SOURCE_ASSERTED" or not row.get("observed_at"):
        return "HOLD", "PACKAGE5_MISSING_OBSERVATION_TIME", None
    unit_id = str(row.get("unit_id"))
    if row.get("semantic_review_required") is True:
        if unit_id in NARRATIVE_SEMANTIC_HOLDS:
            return "HOLD", NARRATIVE_SEMANTIC_HOLDS[unit_id], None
        if unit_id not in NARRATIVE_SEMANTIC_APPROVALS:
            return "HOLD", "PACKAGE5_SEMANTIC_REVIEW_NOT_COMPLETED", None
    if row.get("revocation_ref") not in (None, ""):
        return "HOLD", "PACKAGE5_REVOKED", None
    closes, reason, grant = grant_closes_record(
        row,
        grants,
        organizations,
        stores,
        accounts,
        record_type="NARRATIVE",
    )
    if not closes:
        return "HOLD", reason, grant
    return "ACTIVE_FOR_SIMULATION_RETRIEVAL", reason, grant


def reviewed_narrative_segments(row: JsonObject) -> list[JsonObject]:
    body = row.get("body")
    locator = row.get("locator")
    unit_id = str(row.get("unit_id"))
    if not isinstance(body, str) or not isinstance(locator, dict):
        raise ValueError(f"narrative body or locator missing: {unit_id}")
    if unit_id not in PRODUCT_SUBSECTION_SPLIT_IDS:
        return [{"suffix": "", "text": body, "locator": copy.deepcopy(locator)}]

    starts = [match.start() for match in re.finditer(r"(?m)^##\s+\d+\.", body)]
    if len(starts) != 8:
        raise ValueError(f"expected eight product subsections: {unit_id}")
    parent_byte_start = locator.get("byte_start")
    parent_line_start = locator.get("line_start")
    if not isinstance(parent_byte_start, int) or not isinstance(parent_line_start, int):
        raise ValueError(f"narrative locator invalid: {unit_id}")
    segments: list[JsonObject] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(body)
        text = body[start:end]
        leading_text = body[:start]
        byte_start = parent_byte_start + len(leading_text.encode("utf-8"))
        byte_end = byte_start + len(text.encode("utf-8"))
        line_start = parent_line_start + leading_text.count("\n")
        line_end = line_start + max(0, len(text.splitlines()) - 1)
        segments.append(
            {
                "suffix": f"-S{index + 1:02d}",
                "text": text,
                "locator": {
                    "byte_start": byte_start,
                    "byte_end_exclusive": byte_end,
                    "line_start": line_start,
                    "line_end": line_end,
                },
            }
        )
    return segments


def fact_disposition(
    row: JsonObject,
    grants: dict[str, JsonObject],
    organizations: dict[str, JsonObject],
    stores: dict[str, JsonObject],
    accounts: dict[str, JsonObject],
) -> tuple[str, str, JsonObject | None]:
    if row.get("import_review_state") != "READY_FOR_PACKAGE_5_REVIEW":
        return "HOLD", str(row.get("hold_reason") or row.get("import_review_state")), None
    if row.get("status") == "RECONFIRMATION_REQUIRED":
        return "HOLD", "PACKAGE5_RECONFIRMATION_REQUIRED", None
    if row.get("status") != "SOURCE_ASSERTED":
        return "HOLD", f"PACKAGE5_STATUS_{row.get('status')}", None
    if row.get("revocation_ref") not in (None, ""):
        return "HOLD", "PACKAGE5_REVOKED", None
    closes, reason, grant = grant_closes_record(
        row,
        grants,
        organizations,
        stores,
        accounts,
        record_type="PRECISE_FACT",
    )
    if not closes:
        return "HOLD", reason, grant
    return "ACTIVE_VERIFIED_PRECISE_FACT", reason, grant


def derive_bundle(repo_root: Path) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject], JsonObject]:
    source_manifest = load_json(repo_root / PACKAGE_3_MANIFEST)
    narrative_rows = load_jsonl(repo_root / NARRATIVE_INPUT)
    fact_rows = load_jsonl(repo_root / FACT_INPUT)
    expression_input = load_json(repo_root / EXPRESSION_INPUT)
    examples = load_jsonl(repo_root / EXAMPLE_INPUT)
    identity = load_identity(repo_root / IDENTITY)
    tenant = identity.get("tenant")
    if not isinstance(tenant, dict):
        raise ValueError("identity tenant missing")
    grants = map_rows(identity.get("authorization_grants"), "authorization_id")
    organizations = map_rows(identity.get("organizations"), "organization_id")
    stores = map_rows(identity.get("stores"), "store_id")
    accounts = map_rows(identity.get("content_accounts"), "account_id")
    input_hashes = {path.as_posix(): sha256_file(repo_root / path) for path in INPUT_SHA256}
    data_version_digest = digest_object(
        {"input_sha256": input_hashes, "policy_version": POLICY_VERSION}
    )

    fragments: list[JsonObject] = []
    facts: list[JsonObject] = []
    dispositions: list[JsonObject] = []
    for row in narrative_rows:
        validate_source_slice(row, source_manifest, repo_root)
        disposition, reason, grant = narrative_disposition(
            row, grants, organizations, stores, accounts
        )
        output_ids: list[str] = []
        if disposition == "ACTIVE_FOR_SIMULATION_RETRIEVAL":
            if grant is None:
                raise ValueError("active narrative has no grant")
            for segment in reviewed_narrative_segments(row):
                suffix = str(segment["suffix"])
                output_id = f"PKG5-FRAGMENT-{row['unit_id']}{suffix}"
                output_ids.append(output_id)
                locator = copy.deepcopy(segment["locator"])
                text = str(segment["text"])
                fragments.append(
                    {
                    "fragment_id": output_id,
                    "unit_id": row["unit_id"],
                    "tenant_id": row["tenant_id"],
                    "brand_id": row["brand_id"],
                    "source_id": row["source_id"],
                    "source_organization_id": row["source_organization_id"],
                    "source_store_id": row["source_store_id"],
                    "source_ref": (
                        f"snapshot://{row['source_id']}/"
                        f"L{locator['line_start']}-L{locator['line_end']}"
                    ),
                    "source_position": locator,
                    "source_sha256": row["source_sha256"],
                    "fragment_sha256": sha256_bytes(text.encode("utf-8")),
                    "applicable_organization_ids": copy.deepcopy(
                        row["applicable_organization_ids"]
                    ),
                    "applicable_store_ids": copy.deepcopy(row["applicable_store_ids"]),
                    "applicable_content_account_ids": copy.deepcopy(
                        row["applicable_content_account_ids"]
                    ),
                    "observed_at": normalize_source_time(row["observed_at"]),
                    "source_time_precision": "DATE_ONLY_NO_TIMEZONE_NORMALIZED_TO_UTC_DAY_START",
                    "valid_until": earlier_expiry(row.get("valid_until"), grant["valid_until"]),
                    "authorization_ref": row["authorization_ref"],
                    "authorization_state": "GRANTED",
                    "disclosure_scope": row["disclosure_scope"],
                    "revocation_ref": row.get("revocation_ref"),
                    "status": "ACTIVE",
                    "text": text,
                    "data_version_digest": data_version_digest,
                    "derivation_review_state": "PACKAGE5_EVIDENCE_CLOSED",
                    "package6_adapter_eligible": True,
                    "simulation_only": True,
                    "publish_allowed": False,
                    "runtime_consumable": False,
                    }
                )
        dispositions.append(
            {
                "record_type": "NARRATIVE",
                "source_record_id": row["unit_id"],
                "source_id": row["source_id"],
                "source_record_sha256": digest_object(row),
                "package3_review_state": row["import_review_state"],
                "package5_disposition": disposition,
                "reason_code": reason,
                "derived_record_id": output_ids[0] if len(output_ids) == 1 else None,
                "derived_record_ids": output_ids,
                "fact_kind": None,
                "selector_projection": {},
                "tenant_id": row.get("tenant_id"),
                "brand_id": row.get("brand_id"),
                "source_organization_id": row.get("source_organization_id"),
                "source_store_id": row.get("source_store_id"),
                "applicable_content_account_ids": copy.deepcopy(
                    row.get("applicable_content_account_ids", [])
                ),
                "authorization_ref": row.get("authorization_ref"),
                "disclosure_scope": row.get("disclosure_scope"),
            }
        )

    for row in fact_rows:
        validate_source_slice(row, source_manifest, repo_root)
        disposition, reason, grant = fact_disposition(
            row, grants, organizations, stores, accounts
        )
        fact_output_id: str | None = None
        value = copy.deepcopy(row.get("value"))
        selector_projection: JsonObject = {"fact_id": row["fact_id"]}
        if disposition == "ACTIVE_VERIFIED_PRECISE_FACT":
            if grant is None:
                raise ValueError("active precise fact has no grant")
            fact_output_id = f"PKG5-{row['fact_id']}"
            facts.append(
                {
                    "fact_id": fact_output_id,
                    "source_fact_id": row["fact_id"],
                    "tenant_id": row["tenant_id"],
                    "brand_id": row["brand_id"],
                    "organization_id": row["organization_id"],
                    "store_id": row["store_id"],
                    "applicable_content_account_ids": copy.deepcopy(
                        row["applicable_content_account_ids"]
                    ),
                    "fact_kind": row["fact_kind"],
                    "value": value,
                    "source_id": row["source_id"],
                    "source_ref": row["source_ref"],
                    "source_position": copy.deepcopy(row["locator"]),
                    "source_sha256": row["source_sha256"],
                    "source_excerpt_sha256": row["source_excerpt_sha256"],
                    "effective_at": normalize_source_time(row["effective_at"]),
                    "source_time_precision": "DATE_ONLY_NO_TIMEZONE_NORMALIZED_TO_UTC_DAY_START",
                    "valid_until": earlier_expiry(row.get("valid_until"), grant["valid_until"]),
                    "authorization_ref": row["authorization_ref"],
                    "disclosure_scope": row["disclosure_scope"],
                    "revocation_ref": row.get("revocation_ref"),
                    "status": "ACTIVE",
                    "data_version_digest": data_version_digest,
                    "derivation_review_state": "PACKAGE5_EVIDENCE_CLOSED",
                    "package6_adapter_eligible": True,
                    "simulation_only": True,
                    "publish_allowed": False,
                    "runtime_consumable": False,
                }
            )
        dispositions.append(
            {
                "record_type": "PRECISE_FACT",
                "source_record_id": row["fact_id"],
                "source_id": row["source_id"],
                "source_record_sha256": digest_object(row),
                "package3_review_state": row["import_review_state"],
                "package5_disposition": disposition,
                "reason_code": reason,
                "derived_record_id": fact_output_id,
                "derived_record_ids": [fact_output_id] if fact_output_id else [],
                "fact_kind": row["fact_kind"],
                "selector_projection": selector_projection,
                "tenant_id": row.get("tenant_id"),
                "brand_id": row.get("brand_id"),
                "source_organization_id": row.get("organization_id"),
                "source_store_id": row.get("store_id"),
                "applicable_content_account_ids": copy.deepcopy(
                    row.get("applicable_content_account_ids", [])
                ),
                "authorization_ref": row.get("authorization_ref"),
                "disclosure_scope": row.get("disclosure_scope"),
            }
        )

    example_lineage = [
        {
            "example_ref": row["example_id"],
            "source_id": row["source_id"],
            "source_sha256": row["source_sha256"],
            "text_sha256": row["text_sha256"],
            "candidate_status": row["example_status"],
            "may_grant_fact": False,
            "may_grant_authorization": False,
            "may_grant_scope": False,
            "runtime_authoritative": False,
            "publish_allowed": False,
        }
        for row in examples
    ]
    expression = {
        "schema_version": "v1.0",
        "tenant_id": tenant["tenant_id"],
        "brand_id": tenant["brand_id"],
        "brand_expression_profile_candidate_ref": (
            "expression-profile-candidate://pkg5/diyu-sim/v1"
        ),
        "source_profile_ref": expression_input["brand_guidance_candidate"][
            "default_profile_ref"
        ],
        "available_high_level_mode_refs": copy.deepcopy(
            expression_input["available_high_level_mode_refs"]
        ),
        "available_approved_example_refs": [row["example_ref"] for row in example_lineage],
        "example_lineage": example_lineage,
        "candidate_only": True,
        "runtime_authoritative": False,
        "may_grant_fact_authorization_or_scope": False,
        "publish_allowed": False,
    }
    fragments.sort(key=lambda row: str(row["fragment_id"]))
    facts.sort(key=lambda row: str(row["fact_id"]))
    dispositions.sort(key=lambda row: (str(row["record_type"]), str(row["source_record_id"])))
    return fragments, facts, dispositions, expression


def write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def materialize(repo_root: Path, output_root: Path) -> JsonObject:
    input_hashes = validate_inputs(repo_root)
    fragments, facts, dispositions, expression = derive_bundle(repo_root)
    data_version_digest = digest_object(
        {"input_sha256": input_hashes, "policy_version": POLICY_VERSION}
    )
    outputs = {
        Path("data/retrieval_fragments.v1.jsonl"): canonical_jsonl(fragments),
        Path("data/verified_precise_facts.v1.jsonl"): canonical_jsonl(facts),
        Path("data/source_dispositions.v1.jsonl"): canonical_jsonl(dispositions),
        Path("data/expression_candidates.v1.json"): canonical_json(expression),
    }
    for relative_path, value in outputs.items():
        write_bytes(output_root / relative_path, value)

    public_document = yaml.safe_load((repo_root / PUBLIC_CONTRACT).read_text(encoding="utf-8"))
    public_root = public_document["public_foundation_contract"]
    channels = public_root["brand_fact_contract"]["channels"]
    narrative_contract = next(
        row for row in channels if row["channel_id"] == "SCOPED_NARRATIVE_RETRIEVAL"
    )
    fact_contract = next(row for row in channels if row["channel_id"] == "VERIFIED_PRECISE_FACT")
    fixture_digest = sha256_file(output_root / FIXTURE_PATH)
    disposition_counts = Counter(str(row["package5_disposition"]) for row in dispositions)
    hold_reason_counts = Counter(
        str(row["reason_code"])
        for row in dispositions
        if row["package5_disposition"] == "HOLD"
    )
    manifest: JsonObject = {
        "schema_version": "v1.0",
        "task_id": TASK_ID,
        "baseline_master_commit": BASELINE_MASTER_COMMIT,
        "policy_version": POLICY_VERSION,
        "materialized_at_fixed_evaluation_time": BUILD_AT,
        "data_version_digest": data_version_digest,
        "input_anchors": [
            {"path": path, "sha256": digest} for path, digest in sorted(input_hashes.items())
        ],
        "materialization": {
            "narrative_segmentation": (
                "REUSE_PACKAGE3_NATURAL_SECTIONS_WITH_ONE_"
                "EIGHT_PRODUCT_SUBSECTION_SPLIT"
            ),
            "activation_rule": (
                "READY_PLUS_PACKAGE5_SEMANTIC_DECISION_PLUS_"
                "SOURCE_TIME_SCOPE_AUTHORIZATION_EVIDENCE_CLOSED"
            ),
            "date_normalization": "DATE_ONLY_NO_TIMEZONE_TO_UTC_DAY_START_WITH_PRECISION_LABEL",
            "rebuild_mode": "DELETE_AND_REBUILD_TRANSPARENT_JSON",
            "idempotent": True,
            "binary_index_created": False,
            "production_semantic_quality_claimed": False,
        },
        "output_contract": {
            "scoped_retrieval_fragments_field": "scoped_retrieval_fragments",
            "verified_precise_facts_field": "verified_precise_facts",
            "fragment_required_fields": narrative_contract["required_metadata"],
            "fact_required_fields": fact_contract["required_metadata"],
            "parallel_context_bundle_created": False,
            "plan_or_generator_created": False,
        },
        "counts": {
            "package3_narrative_input": 197,
            "package3_precise_fact_input": 9,
            "active_retrieval_fragments": len(fragments),
            "active_verified_precise_facts": len(facts),
            "source_dispositions": len(dispositions),
            "hold_records": disposition_counts["HOLD"],
            "hold_reason_counts": dict(sorted(hold_reason_counts.items())),
            "expression_example_candidates": len(expression["example_lineage"]),
        },
        "artifacts": [
            {
                "path": path.as_posix(),
                "sha256": sha256_bytes(value),
                "byte_size": len(value),
                "record_count": (
                    len(value.decode("utf-8").splitlines())
                    if path.suffix == ".jsonl"
                    else 1
                ),
            }
            for path, value in sorted(outputs.items(), key=lambda item: item[0].as_posix())
        ],
        "fixture": {
            "path": FIXTURE_PATH.as_posix(),
            "sha256": fixture_digest,
            "case_count": len(load_jsonl(output_root / FIXTURE_PATH)),
        },
        "external_calls": {
            "network": 0,
            "database": 0,
            "dify": 0,
            "model": 0,
            "production": 0,
        },
        "simulation_boundary": {
            "simulation_only": True,
            "publish_allowed": False,
            "runtime_consumable": False,
            "package6_adapter_eligible": True,
            "package2_prepare_called": False,
        },
        "readiness": {
            "candidatepack_ready": False,
            "KE_ready": False,
            "RAG_ready": False,
            "DIFY_ready": False,
            "retrieval_ready": False,
            "database_imported": False,
            "production_servable": False,
            "generation_eligible": False,
            "generation_allowed": False,
            "release_ready": False,
            "production_ready": False,
        },
        "core_numbers": {"target_300": 300, "reference_120": 120, "historical_86": 86},
    }
    write_bytes(output_root / "retrieval_manifest.v1.json", canonical_json(manifest))
    return manifest


def check_materialization(repo_root: Path, package_root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="pkg5-materialize-check-") as temporary:
        output = Path(temporary)
        (output / FIXTURE_PATH).parent.mkdir(parents=True, exist_ok=True)
        (output / FIXTURE_PATH).write_bytes((package_root / FIXTURE_PATH).read_bytes())
        materialize(repo_root, output)
        for relative_path in GENERATED_PATHS:
            if (output / relative_path).read_bytes() != (package_root / relative_path).read_bytes():
                raise ValueError(f"materialization drift: {relative_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        check_materialization(REPO_ROOT, PACKAGE_ROOT)
        print("PASS: Package 5 materialization is deterministic")
        return 0
    output_root = args.output_root.resolve() if args.output_root else PACKAGE_ROOT
    if output_root != PACKAGE_ROOT:
        (output_root / FIXTURE_PATH).parent.mkdir(parents=True, exist_ok=True)
        (output_root / FIXTURE_PATH).write_bytes((PACKAGE_ROOT / FIXTURE_PATH).read_bytes())
    manifest = materialize(REPO_ROOT, output_root)
    print(
        "PASS: materialized "
        f"{manifest['counts']['active_retrieval_fragments']} fragments and "
        f"{manifest['counts']['active_verified_precise_facts']} precise facts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
