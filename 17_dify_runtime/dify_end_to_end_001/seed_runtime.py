#!/usr/bin/env python3
"""Idempotently materialize approved Package 3/5 data into Package 7."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, TypeVar

import yaml  # type: ignore[import-untyped]
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from brand_import import load_simulation_bundle, preflight_brand_bundle
from persistence import digest_object
from runtime_models import (
    RuntimeAccount,
    RuntimeAuthorization,
    RuntimeBrand,
    RuntimeNarrativeFragment,
    RuntimeOrganization,
    RuntimePreciseFact,
    RuntimePrincipal,
    RuntimeSetting,
    RuntimeSource,
    RuntimeStore,
    RuntimeSubjectConfirmation,
    RuntimeTenant,
)
from security import hash_password, verify_password


JsonObject = dict[str, Any]
ModelType = TypeVar("ModelType")
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
NEUTRAL_PROFILE_PATH = (
    REPOSITORY_ROOT
    / "12_expression_service/expression_runtime_adapter_001/neutral_expression_profile.v1.yaml"
)


def parse_time(value: str) -> datetime:
    normalized = value.strip()
    if len(normalized) == 10:
        normalized = f"{normalized}T00:00:00Z"
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("Timezone is required")
    return parsed.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_knowledge_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _replace_payload(target: object, source: object) -> None:
    for key, value in vars(source).items():
        if key.startswith("_" ):
            continue
        setattr(target, key, copy.deepcopy(value))


def _upsert(session: Session, model: type[ModelType], key: str, value: object) -> bool:
    current = session.get(model, key)
    if current is None:
        session.add(value)
        return True
    before = digest_object(
        {
            field: val
            for field, val in vars(current).items()
            if not field.startswith("_") and field != "updated_at"
        }
    )
    after = digest_object(
        {
            field: val
            for field, val in vars(value).items()
            if not field.startswith("_") and field != "updated_at"
        }
    )
    if before == after:
        return False
    _replace_payload(current, value)
    return True


def seed_database(
    engine: Engine,
    sessions: sessionmaker[Session],
    *,
    username: str,
    password: str,
) -> JsonObject:
    """Load only approved rows; reruns update in place and never duplicate."""

    bundle = load_simulation_bundle(REPOSITORY_ROOT)
    preflight = preflight_brand_bundle(bundle)
    if preflight["state"] != "CAN_IMPORT":
        raise ValueError(f"Brand import preflight failed: {preflight['state']}")
    identity = copy.deepcopy(bundle.identity)
    tenant = dict(identity["tenant"])
    tenant_id = str(tenant["tenant_id"])
    brand_id = str(tenant["brand_id"])
    now = utc_now()
    fragments = bundle.narrative_fragments
    grants = [copy.deepcopy(row) for row in identity["authorization_grants"]]
    grant_window_start = min(str(row["valid_from"]) for row in grants)
    grant_window_end = max(str(row["valid_until"]) for row in grants)
    identity_digest = digest_object(identity)
    derived_confirmation_refs: dict[str, str] = {}
    derived_facts: list[JsonObject] = []
    for raw_account in identity["content_accounts"]:
        account = copy.deepcopy(raw_account)
        account_id = str(account["account_id"])
        suffix = hashlib.sha256(account_id.encode("utf-8")).hexdigest()[:16].upper()
        disclosure_ref = f"PKG7-AUTH-ACCOUNT-SELF-{suffix}"
        confirmation_ref = f"PKG7-AUTH-TASK-CONFIRM-{suffix}"
        organization_id = str(account["organization_id"])
        store_id = account.get("store_id")
        grants.extend(
            [
                {
                    "authorization_id": disclosure_ref,
                    "authorization_kind": "FACT_DISCLOSURE",
                    "tenant_id": tenant_id,
                    "brand_id": brand_id,
                    "source_organization_id": organization_id,
                    "source_store_id": store_id,
                    "permitted_organization_ids": [organization_id],
                    "permitted_store_ids": [store_id],
                    "permitted_content_account_ids": [account_id],
                    "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
                    "valid_from": grant_window_start,
                    "valid_until": grant_window_end,
                    "status": "GRANTED",
                    "derived_from_account_self_scope": True,
                    "simulation_only": True,
                    "publish_allowed": False,
                },
                {
                    "authorization_id": confirmation_ref,
                    "authorization_kind": "REQUIREMENT_CONFIRMATION",
                    "tenant_id": tenant_id,
                    "brand_id": brand_id,
                    "source_organization_id": organization_id,
                    "source_store_id": store_id,
                    "permitted_organization_ids": [organization_id],
                    "permitted_store_ids": [store_id],
                    "permitted_content_account_ids": [account_id],
                    "disclosure_scope": "REQUIREMENT_CONFIRMATION_ONLY",
                    "valid_from": grant_window_start,
                    "valid_until": grant_window_end,
                    "status": "GRANTED",
                    "derived_from_confirmed_account_role_grant": True,
                    "simulation_only": True,
                    "publish_allowed": False,
                },
            ]
        )
        derived_confirmation_refs[account_id] = confirmation_ref
        derived_facts.append(
            {
                "fact_id": f"PKG7-ACCOUNT-SCOPE-{suffix}",
                "fact_kind": "AUTHORIZATION",
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "organization_id": organization_id,
                "store_id": store_id,
                "applicable_content_account_ids": [account_id],
                "authorization_ref": disclosure_ref,
                "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
                "effective_at": grant_window_start,
                "valid_until": grant_window_end,
                "status": "ACTIVE",
                "revocation_ref": None,
                "source_id": "PUBLIC-IDENTITY",
                "source_ref": "snapshot://public-foundation/simulation-identity",
                "source_sha256": str(identity.get("source", {}).get("sha256", identity_digest)),
                "source_excerpt_sha256": digest_object(account),
                "data_version_digest": identity_digest,
                "package6_adapter_eligible": True,
                "simulation_only": True,
                "publish_allowed": False,
                "runtime_consumable": False,
                "value": {
                    "account_id": account_id,
                    "display_name": account["display_name"],
                    "represented_scope": account["represented_scope"],
                    "organization_id": organization_id,
                    "store_id": store_id,
                },
            }
        )
    identity["authorization_grants"] = grants
    facts = (*bundle.precise_facts, *derived_facts)
    profile = copy.deepcopy(bundle.expression_profile)
    neutral_document = yaml.safe_load(NEUTRAL_PROFILE_PATH.read_text(encoding="utf-8"))
    neutral_profile = dict(neutral_document["neutral_expression_profile"])
    counts = {"created_or_updated": 0, "unchanged": 0}

    def apply(model: type[ModelType], key: str, row: object) -> None:
        changed = _upsert(session, model, key, row)
        counts["created_or_updated" if changed else "unchanged"] += 1

    with sessions.begin() as session:
        apply(
            RuntimeTenant,
            tenant_id,
            RuntimeTenant(
                tenant_id=tenant_id,
                display_name=str(tenant["display_name"]),
                status="ACTIVE",
                payload=copy.deepcopy(tenant),
                updated_at=now,
            ),
        )
        apply(
            RuntimeBrand,
            brand_id,
            RuntimeBrand(
                brand_id=brand_id,
                tenant_id=tenant_id,
                display_name=str(tenant["display_name"]),
                status="ACTIVE",
                payload={
                    "brand_id": brand_id,
                    "tenant_id": tenant_id,
                    "display_name": tenant["display_name"],
                    "simulation_only": True,
                    "publish_allowed": False,
                },
                updated_at=now,
            ),
        )
        for organization in identity["organizations"]:
            row = dict(organization)
            key = str(row["organization_id"])
            apply(
                RuntimeOrganization,
                key,
                RuntimeOrganization(
                    organization_id=key,
                    tenant_id=str(row["tenant_id"]),
                    display_name=str(row["display_name"]),
                    status="ACTIVE",
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for store in identity["stores"]:
            row = dict(store)
            key = str(row["store_id"])
            apply(
                RuntimeStore,
                key,
                RuntimeStore(
                    store_id=key,
                    organization_id=str(row["organization_id"]),
                    status="ACTIVE",
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        principal = dict(identity["login_principals"][0])
        principal_id = str(principal["principal_id"])
        existing_principal = session.get(RuntimePrincipal, principal_id)
        password_hash = (
            existing_principal.password_hash
            if existing_principal is not None and verify_password(password, existing_principal.password_hash)
            else hash_password(password)
        )
        apply(
            RuntimePrincipal,
            principal_id,
            RuntimePrincipal(
                principal_id=principal_id,
                tenant_id=tenant_id,
                username=username,
                password_hash=password_hash,
                status="ACTIVE",
                allowed_account_ids=list(principal["allowed_content_account_ids"]),
                payload=copy.deepcopy(principal),
                updated_at=now,
            ),
        )
        for account in identity["content_accounts"]:
            row = dict(account)
            key = str(row["account_id"])
            row["runtime_confirmation_authorization_ref"] = derived_confirmation_refs[key]
            apply(
                RuntimeAccount,
                key,
                RuntimeAccount(
                    account_id=key,
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    organization_id=str(row["organization_id"]),
                    store_id=row.get("store_id"),
                    display_name=str(row["display_name"]),
                    status="ACTIVE",
                    maker_role_ids=list(row["maker_role_ids"]),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for authorization in grants:
            row = dict(authorization)
            key = str(row["authorization_id"])
            apply(
                RuntimeAuthorization,
                key,
                RuntimeAuthorization(
                    authorization_id=key,
                    tenant_id=tenant_id,
                    status=str(row["status"]),
                    valid_from=parse_time(str(row["valid_from"])),
                    valid_until=parse_time(str(row["valid_until"])),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for confirmation in identity["subject_confirmation_records"]:
            row = dict(confirmation)
            key = str(row["subject_confirmation_id"])
            apply(
                RuntimeSubjectConfirmation,
                key,
                RuntimeSubjectConfirmation(
                    confirmation_id=key,
                    tenant_id=tenant_id,
                    status=str(row["status"]),
                    valid_until=parse_time(str(row["valid_until"])),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        source_rows: dict[str, JsonObject] = {}
        for row in (*fragments, *facts):
            source_id = str(row["source_id"])
            source_rows.setdefault(
                source_id,
                {
                    "source_id": source_id,
                    "source_ref": f"snapshot://{source_id}",
                    "source_sha256": row["source_sha256"],
                    "simulation_only": True,
                    "publish_allowed": False,
                },
            )
        for source_id, row in source_rows.items():
            apply(
                RuntimeSource,
                source_id,
                RuntimeSource(
                    source_id=source_id,
                    source_ref=str(row["source_ref"]),
                    source_digest=str(row["source_sha256"]),
                    status="ACTIVE",
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for fragment in fragments:
            row = dict(fragment)
            key = str(row["fragment_id"])
            existing_fragment = session.get(RuntimeNarrativeFragment, key)
            apply(
                RuntimeNarrativeFragment,
                key,
                RuntimeNarrativeFragment(
                    fragment_id=key,
                    source_ref=str(row["source_ref"]),
                    tenant_id=str(row["tenant_id"]),
                    brand_id=str(row["brand_id"]),
                    status=str(row["status"]),
                    authorization_state=str(row["authorization_state"]),
                    authorization_ref=str(row["authorization_ref"]),
                    valid_from=parse_time(str(row["observed_at"])),
                    valid_until=parse_time(str(row["valid_until"])),
                    revocation_ref=row.get("revocation_ref"),
                    content_digest=hashlib.sha256(
                        normalize_knowledge_text(str(row["text"])).encode("utf-8")
                    ).hexdigest(),
                    dify_document_id=(
                        None if existing_fragment is None else existing_fragment.dify_document_id
                    ),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for fact in facts:
            row = dict(fact)
            key = str(row["fact_id"])
            apply(
                RuntimePreciseFact,
                key,
                RuntimePreciseFact(
                    fact_id=key,
                    source_ref=str(row["source_ref"]),
                    tenant_id=str(row["tenant_id"]),
                    brand_id=str(row["brand_id"]),
                    fact_kind=str(row["fact_kind"]),
                    status=str(row["status"]),
                    authorization_ref=str(row["authorization_ref"]),
                    valid_from=parse_time(str(row["effective_at"])),
                    valid_until=parse_time(str(row["valid_until"])),
                    revocation_ref=row.get("revocation_ref"),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        settings = {
            "active_runtime_brand": {
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "identity_setting_key": f"identity_authority:{tenant_id}",
                "profile_setting_key": f"brand_expression_profile:{brand_id}",
                "source_manifest": copy.deepcopy(bundle.source_manifest),
            },
            f"identity_authority:{tenant_id}": identity,
            f"brand_expression_profile:{brand_id}": profile,
            "neutral_expression_profile": neutral_profile,
            "runtime_boundary": {
                "simulation_only": True,
                "non_production": True,
                "publish_allowed": False,
                "runtime_consumable": False,
                "readiness_flags_changed": False,
            },
        }
        for key, payload in settings.items():
            apply(
                RuntimeSetting,
                key,
                RuntimeSetting(
                    setting_key=key,
                    setting_version="v1",
                    payload=copy.deepcopy(payload),
                    source_digest=digest_object(payload),
                    updated_at=now,
                ),
            )

    with sessions() as session:
        summary = {
            "tenant_count": session.query(RuntimeTenant).count(),
            "brand_count": session.query(RuntimeBrand).count(),
            "organization_count": session.query(RuntimeOrganization).count(),
            "store_count": session.query(RuntimeStore).count(),
            "principal_count": session.query(RuntimePrincipal).count(),
            "content_account_count": session.query(RuntimeAccount).count(),
            "authorization_count": session.query(RuntimeAuthorization).count(),
            "source_count": session.query(RuntimeSource).count(),
            "narrative_fragment_count": session.query(RuntimeNarrativeFragment).count(),
            "precise_fact_count": session.query(RuntimePreciseFact).count(),
            "import_preflight_state": preflight["state"],
            **counts,
        }
    summary["seed_digest"] = digest_object(summary)
    return summary


def eligible_fragment_ids(sessions: sessionmaker[Session]) -> list[str]:
    with sessions() as session:
        rows: Iterable[RuntimeNarrativeFragment] = session.scalars(
            select(RuntimeNarrativeFragment).where(
                RuntimeNarrativeFragment.status == "ACTIVE",
                RuntimeNarrativeFragment.authorization_state == "GRANTED",
                RuntimeNarrativeFragment.revocation_ref.is_(None),
            )
        )
        return sorted(row.fragment_id for row in rows)
