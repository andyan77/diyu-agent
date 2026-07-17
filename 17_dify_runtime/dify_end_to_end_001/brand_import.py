#!/usr/bin/env python3
"""Brand-neutral import bundle and fail-closed preflight for Package 7."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


@dataclass(frozen=True)
class BrandImportBundle:
    """One immutable import projection; persistence remains one transaction."""

    identity: JsonObject
    narrative_fragments: tuple[JsonObject, ...]
    precise_facts: tuple[JsonObject, ...]
    expression_profile: JsonObject
    source_manifest: JsonObject


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _read_jsonl(path: Path) -> tuple[JsonObject, ...]:
    rows: list[JsonObject] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Expected an object in {path}")
        rows.append(value)
    return tuple(rows)


def load_simulation_bundle(
    repository_root: Path = REPOSITORY_ROOT,
) -> BrandImportBundle:
    """Adapt frozen repository owners into the same generic bundle used by any brand."""

    identity_path = repository_root / (
        "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml"
    )
    fragment_path = repository_root / (
        "15_brand_retrieval/brand_fact_retrieval_001/data/retrieval_fragments.v1.jsonl"
    )
    fact_path = repository_root / (
        "15_brand_retrieval/brand_fact_retrieval_001/data/verified_precise_facts.v1.jsonl"
    )
    profile_path = PACKAGE_ROOT / "brand_runtime_profile.v1.yaml"
    identity_document = yaml.safe_load(identity_path.read_text(encoding="utf-8"))
    profile_document = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    identity = (
        identity_document.get("simulation_tenant")
        if isinstance(identity_document, dict)
        else None
    )
    profile = (
        profile_document.get("brand_runtime_profile")
        if isinstance(profile_document, dict)
        else None
    )
    if not isinstance(identity, dict) or not isinstance(profile, dict):
        raise ValueError("The simulation brand inputs are invalid")
    return BrandImportBundle(
        identity=copy.deepcopy(identity),
        narrative_fragments=_read_jsonl(fragment_path),
        precise_facts=_read_jsonl(fact_path),
        expression_profile=copy.deepcopy(profile),
        source_manifest={
            "identity_path": identity_path.relative_to(repository_root).as_posix(),
            "fragment_path": fragment_path.relative_to(repository_root).as_posix(),
            "fact_path": fact_path.relative_to(repository_root).as_posix(),
            "profile_path": profile_path.relative_to(repository_root).as_posix(),
            "data_mode": "SIMULATION",
            "simulation_only": True,
            "test_fixture_only": True,
            "publish_allowed": False,
            "real_brand_authorization": None,
            "derived_source_refs": [],
        },
    )


def preflight_brand_bundle(bundle: BrandImportBundle) -> JsonObject:
    """Classify a bundle without guessing or mutating it."""

    fatal: list[str] = []
    missing: list[str] = []
    manifest = bundle.source_manifest
    data_mode = manifest.get("data_mode")
    simulation_only = manifest.get("simulation_only")
    test_fixture_only = manifest.get("test_fixture_only")
    if data_mode not in {"SIMULATION", "AUTHORIZED_REAL"}:
        fatal.append("data_mode_invalid")
    if manifest.get("publish_allowed") is not False:
        fatal.append("publish_boundary_invalid")
    authorized_source_refs: set[str] = set()
    real_valid_from: datetime | None = None
    real_valid_until: datetime | None = None
    derived_source_refs = manifest.get("derived_source_refs", [])
    if not isinstance(derived_source_refs, list) or any(
        not isinstance(value, str) or not value for value in derived_source_refs
    ):
        fatal.append("derived_source_refs_invalid")
        derived_source_refs = []
    if data_mode == "SIMULATION":
        if simulation_only is not True or test_fixture_only is not True:
            fatal.append("simulation_disclosure_invalid")
        if manifest.get("real_brand_authorization") is not None:
            fatal.append("simulation_real_authorization_forbidden")
    elif data_mode == "AUTHORIZED_REAL":
        if simulation_only is not False or not isinstance(test_fixture_only, bool):
            fatal.append("real_brand_mode_disclosure_invalid")
        authorization = manifest.get("real_brand_authorization")
        if not isinstance(authorization, dict):
            fatal.append("real_brand_authorization_missing")
        else:
            source_refs = authorization.get("source_refs")
            valid_from = _parse_time(authorization.get("valid_from"))
            valid_until = _parse_time(authorization.get("valid_until"))
            confirmed_at = _parse_time(authorization.get("operator_confirmed_at"))
            if (
                not isinstance(authorization.get("authorization_ref"), str)
                or not authorization.get("authorization_ref")
                or authorization.get("status") != "GRANTED"
                or authorization.get("revocation_state") != "CLEAR"
                or authorization.get("revocation_ref") is not None
                or not isinstance(authorization.get("operator_ref"), str)
                or not authorization.get("operator_ref")
                or authorization.get("operator_confirmed") is not True
                or not isinstance(source_refs, list)
                or not source_refs
                or any(not isinstance(value, str) or not value for value in source_refs)
                or valid_from is None
                or valid_until is None
                or confirmed_at is None
                or not valid_from <= confirmed_at < valid_until
            ):
                fatal.append("real_brand_authorization_invalid")
            else:
                authorized_source_refs = set(source_refs)
                real_valid_from = valid_from
                real_valid_until = valid_until
    identity = bundle.identity
    tenant = identity.get("tenant")
    if not isinstance(tenant, dict):
        fatal.append("tenant_structure_invalid")
        tenant = {}
    tenant_id = tenant.get("tenant_id")
    brand_id = tenant.get("brand_id")
    if not isinstance(tenant_id, str) or not tenant_id:
        fatal.append("tenant_id_missing")
    if not isinstance(brand_id, str) or not brand_id:
        fatal.append("brand_id_missing")
    if tenant.get("simulation_only") is not simulation_only:
        fatal.append("tenant_mode_mismatch")
    if tenant.get("publish_allowed") is not False:
        fatal.append("tenant_publish_boundary_invalid")

    required_collections = (
        "organizations",
        "stores",
        "work_roles",
        "login_principals",
        "content_accounts",
        "authorization_grants",
        "subject_confirmation_records",
    )
    for key in required_collections:
        value = identity.get(key)
        if not isinstance(value, list):
            fatal.append(f"{key}_structure_invalid")
        elif not value and key not in {"stores", "subject_confirmation_records"}:
            missing.append(f"{key}_empty")

    organizations = {
        row.get("organization_id")
        for row in identity.get("organizations", [])
        if isinstance(row, dict) and isinstance(row.get("organization_id"), str)
    }
    stores = {
        row.get("store_id"): row.get("organization_id")
        for row in identity.get("stores", [])
        if isinstance(row, dict) and isinstance(row.get("store_id"), str)
    }
    accounts = {
        row.get("account_id"): row
        for row in identity.get("content_accounts", [])
        if isinstance(row, dict) and isinstance(row.get("account_id"), str)
    }
    grants = {
        row.get("authorization_id")
        for row in identity.get("authorization_grants", [])
        if isinstance(row, dict) and isinstance(row.get("authorization_id"), str)
    }
    for account_id, row in accounts.items():
        if row.get("organization_id") not in organizations:
            fatal.append(f"account_organization_unknown:{account_id}")
        store_id = row.get("store_id")
        if store_id is not None and stores.get(store_id) != row.get("organization_id"):
            fatal.append(f"account_store_scope_invalid:{account_id}")

    for label, rows in (
        ("fragment", bundle.narrative_fragments),
        ("fact", bundle.precise_facts),
    ):
        for row in rows:
            row_id = (
                row.get("fragment_id") if label == "fragment" else row.get("fact_id")
            )
            if row.get("tenant_id") != tenant_id or row.get("brand_id") != brand_id:
                fatal.append(f"{label}_cross_brand_scope:{row_id}")
            if row.get("authorization_ref") not in grants:
                fatal.append(f"{label}_authorization_unknown:{row_id}")
            applicable = row.get("applicable_content_account_ids")
            if not isinstance(applicable, list) or any(
                value not in accounts for value in applicable
            ):
                fatal.append(f"{label}_account_scope_invalid:{row_id}")
            if not isinstance(row.get("source_ref"), str) or not row["source_ref"]:
                fatal.append(f"{label}_source_missing:{row_id}")
            if row.get("simulation_only") is not simulation_only:
                fatal.append(f"{label}_mode_mismatch:{row_id}")
            if row.get("publish_allowed") is not False:
                fatal.append(f"{label}_publish_boundary_invalid:{row_id}")
            if data_mode == "AUTHORIZED_REAL" and row.get("source_ref") not in (
                authorized_source_refs | set(derived_source_refs)
            ):
                fatal.append(f"{label}_source_not_authorized:{row_id}")
            if data_mode == "AUTHORIZED_REAL":
                starts_at = _parse_time(
                    row.get("observed_at")
                    if label == "fragment"
                    else row.get("effective_at")
                )
                valid_until = _parse_time(row.get("valid_until"))
                if (
                    real_valid_from is None
                    or real_valid_until is None
                    or starts_at is None
                    or valid_until is None
                    or starts_at < real_valid_from
                    or valid_until > real_valid_until
                ):
                    fatal.append(f"{label}_outside_real_authorization_window:{row_id}")

    profile = bundle.expression_profile
    if profile.get("tenant_specific") is True and (
        profile.get("tenant_id") != tenant_id or profile.get("brand_id") != brand_id
    ):
        fatal.append("expression_profile_cross_brand_scope")
    if profile.get("simulation_only") is not simulation_only:
        fatal.append("expression_profile_mode_mismatch")
    if profile.get("publish_allowed") is not False:
        fatal.append("expression_profile_publish_boundary_invalid")
    if not isinstance(profile.get("profile_ref"), str):
        missing.append("expression_profile_missing")
    profile_accounts = {
        row.get("account_id")
        for row in profile.get("account_role_cards", [])
        if isinstance(row, dict)
    }
    if profile_accounts and profile_accounts != set(accounts):
        fatal.append("expression_profile_account_mapping_mismatch")

    state = "CANNOT_IMPORT" if fatal else ("NEEDS_INPUT" if missing else "CAN_IMPORT")
    return {
        "state": state,
        "fatal_reasons": sorted(set(fatal)),
        "missing_inputs": sorted(set(missing)),
        "tenant_id": tenant_id,
        "brand_id": brand_id,
        "data_mode": data_mode,
        "simulation_only": simulation_only,
        "test_fixture_only": test_fixture_only,
        "account_count": len(accounts),
        "fragment_count": len(bundle.narrative_fragments),
        "precise_fact_count": len(bundle.precise_facts),
        "mutated": False,
    }
