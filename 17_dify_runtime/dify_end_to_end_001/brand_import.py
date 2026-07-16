#!/usr/bin/env python3
"""Brand-neutral import bundle and fail-closed preflight for Package 7."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
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


def load_simulation_bundle(repository_root: Path = REPOSITORY_ROOT) -> BrandImportBundle:
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
    identity = identity_document.get("simulation_tenant") if isinstance(identity_document, dict) else None
    profile = profile_document.get("brand_runtime_profile") if isinstance(profile_document, dict) else None
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
            "simulation_only": True,
        },
    )


def preflight_brand_bundle(bundle: BrandImportBundle) -> JsonObject:
    """Classify a bundle without guessing or mutating it."""

    fatal: list[str] = []
    missing: list[str] = []
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
            row_id = row.get("fragment_id") if label == "fragment" else row.get("fact_id")
            if row.get("tenant_id") != tenant_id or row.get("brand_id") != brand_id:
                fatal.append(f"{label}_cross_brand_scope:{row_id}")
            if row.get("authorization_ref") not in grants:
                fatal.append(f"{label}_authorization_unknown:{row_id}")
            applicable = row.get("applicable_content_account_ids")
            if not isinstance(applicable, list) or any(value not in accounts for value in applicable):
                fatal.append(f"{label}_account_scope_invalid:{row_id}")
            if not isinstance(row.get("source_ref"), str) or not row["source_ref"]:
                fatal.append(f"{label}_source_missing:{row_id}")

    profile = bundle.expression_profile
    if profile.get("tenant_specific") is True and (
        profile.get("tenant_id") != tenant_id or profile.get("brand_id") != brand_id
    ):
        fatal.append("expression_profile_cross_brand_scope")
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
        "account_count": len(accounts),
        "fragment_count": len(bundle.narrative_fragments),
        "precise_fact_count": len(bundle.precise_facts),
        "mutated": False,
    }
