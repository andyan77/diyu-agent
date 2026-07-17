#!/usr/bin/env python3
"""Compile a human-facing fictional brand document into the Package 7 bundle."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_7_ROOT = REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001"
if str(PACKAGE_7_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_7_ROOT))

from brand_import import BrandImportBundle  # noqa: E402
from persistence import canonical_json, digest_object  # noqa: E402


JsonObject = dict[str, Any]


def _canonical_code(value: str) -> str:
    if "--" in value or value.endswith("-"):
        raise ValueError("code must already be in canonical form")
    return value


Code = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9-]{1,31}$", strip_whitespace=True),
    AfterValidator(_canonical_code),
]
NonEmpty = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnterpriseInput(StrictModel):
    enterprise_code: Code
    brand_code: Code
    enterprise_name: NonEmpty
    brand_name: NonEmpty


class OrganizationInput(StrictModel):
    code: Code
    name: NonEmpty
    level: Literal["HEADQUARTERS", "REGION"]


class StoreInput(StrictModel):
    code: Code
    name: NonEmpty
    organization_code: Code


class AccountInput(StrictModel):
    code: Code
    display_name: NonEmpty
    organization_code: Code
    store_code: Code | None = None
    level: Literal["HEADQUARTERS", "REGION", "STORE"]
    role_code: Code
    allowed_source_organization_codes: list[Code]


class RoleInput(StrictModel):
    code: Code
    name: NonEmpty
    boundary: NonEmpty


class UserInput(StrictModel):
    code: Code
    username: Code
    display_name: NonEmpty
    allowed_account_codes: list[Code] = Field(min_length=1)


class AuthorizationInput(StrictModel):
    code: Code
    status: Literal["GRANTED", "REVOKED", "EXPIRED"]
    valid_from: datetime
    valid_until: datetime
    organization_codes: list[Code] = Field(min_length=1)
    store_codes: list[Code | None]
    account_codes: list[Code] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_window(self) -> AuthorizationInput:
        if self.valid_from.tzinfo is None or self.valid_until.tzinfo is None:
            raise ValueError("authorization times require a timezone")
        if self.valid_from >= self.valid_until:
            raise ValueError("authorization validity window is empty")
        return self


class RealBrandAuthorizationInput(StrictModel):
    authorization_ref: NonEmpty
    source_refs: list[NonEmpty] = Field(min_length=1)
    status: Literal["GRANTED", "REVOKED", "EXPIRED"]
    valid_from: datetime
    valid_until: datetime
    revocation_state: Literal["CLEAR", "REVOKED"]
    revocation_ref: NonEmpty | None = None
    operator_ref: NonEmpty
    operator_confirmed: bool
    operator_confirmed_at: datetime

    @model_validator(mode="after")
    def validate_authorization(self) -> RealBrandAuthorizationInput:
        values = (self.valid_from, self.valid_until, self.operator_confirmed_at)
        if any(value.tzinfo is None for value in values):
            raise ValueError("real brand authorization times require a timezone")
        if self.valid_from >= self.valid_until:
            raise ValueError("real brand authorization window is empty")
        if self.status != "GRANTED":
            raise ValueError("real brand import requires granted authorization")
        if self.revocation_state != "CLEAR" or self.revocation_ref is not None:
            raise ValueError("revoked real brand authorization cannot be imported")
        if not self.operator_confirmed:
            raise ValueError("real brand import requires operator confirmation")
        if not self.valid_from <= self.operator_confirmed_at < self.valid_until:
            raise ValueError("operator confirmation is outside authorization window")
        if len(set(self.source_refs)) != len(self.source_refs):
            raise ValueError("real brand authorization source refs must be unique")
        return self


class MaterialInput(StrictModel):
    code: Code
    title: NonEmpty
    text: NonEmpty
    source_label: NonEmpty
    source_ref: NonEmpty
    authorization_code: Code
    account_codes: list[Code] = Field(min_length=1)
    observed_at: datetime
    valid_until: datetime
    status: Literal["ACTIVE", "REVOKED"] = "ACTIVE"

    @model_validator(mode="after")
    def validate_window(self) -> MaterialInput:
        if self.observed_at.tzinfo is None or self.valid_until.tzinfo is None:
            raise ValueError("material times require a timezone")
        if self.observed_at >= self.valid_until:
            raise ValueError("material validity window is empty")
        return self


class FactInput(StrictModel):
    code: Code
    kind: Literal[
        "SKU",
        "SPECIFICATION",
        "PRICE",
        "STOCK",
        "TIME_POINT",
        "AUTHORIZATION",
        "REVOCATION",
    ]
    label: NonEmpty
    value: JsonObject
    source_label: NonEmpty
    source_ref: NonEmpty
    authorization_code: Code
    account_codes: list[Code] = Field(min_length=1)
    effective_at: datetime
    valid_until: datetime
    status: Literal["ACTIVE", "REVOKED", "EXPIRED"] = "ACTIVE"

    @model_validator(mode="after")
    def validate_window(self) -> FactInput:
        if self.effective_at.tzinfo is None or self.valid_until.tzinfo is None:
            raise ValueError("fact times require a timezone")
        if self.effective_at >= self.valid_until:
            raise ValueError("fact validity window is empty")
        return self


class StorylineInput(StrictModel):
    code: Code
    name: NonEmpty
    purpose: NonEmpty


class ColumnInput(StrictModel):
    code: Code
    name: NonEmpty
    storyline_code: Code


class ExpressionInput(StrictModel):
    why_exist: NonEmpty
    audience: NonEmpty
    tone_tendencies: list[NonEmpty] = Field(min_length=1)
    preferred_phrasing: list[NonEmpty] = Field(min_length=1)
    prohibited_categories: list[NonEmpty] = Field(min_length=1)
    storylines: list[StorylineInput] = Field(min_length=1)
    columns: list[ColumnInput] = Field(min_length=1)


class BrandInputDocument(StrictModel):
    schema_version: Literal["v1.0"]
    data_mode: Literal["SIMULATION", "AUTHORIZED_REAL"]
    fictional_test_data: bool
    safe_fixture_data: bool
    real_brand_authorization: RealBrandAuthorizationInput | None = None
    enterprise: EnterpriseInput
    organizations: list[OrganizationInput] = Field(min_length=1)
    stores: list[StoreInput]
    roles: list[RoleInput] = Field(min_length=1)
    users: list[UserInput] = Field(min_length=1)
    accounts: list[AccountInput] = Field(min_length=1)
    authorizations: list[AuthorizationInput] = Field(min_length=1)
    materials: list[MaterialInput] = Field(min_length=1)
    facts: list[FactInput] = Field(min_length=1)
    expression: ExpressionInput

    @model_validator(mode="after")
    def validate_references(self) -> BrandInputDocument:
        if self.data_mode == "SIMULATION":
            if not self.fictional_test_data or not self.safe_fixture_data:
                raise ValueError("simulation mode requires safe fictional fixture data")
            if self.real_brand_authorization is not None:
                raise ValueError(
                    "simulation mode cannot carry real brand authorization"
                )
        else:
            real_authorization = self.real_brand_authorization
            if real_authorization is None:
                raise ValueError(
                    "authorized real mode requires real brand authorization"
                )
            if self.fictional_test_data != self.safe_fixture_data:
                raise ValueError(
                    "authorized real test fixtures must disclose both fixture flags"
                )
            supplied_source_refs = {
                *(row.source_ref for row in self.materials),
                *(row.source_ref for row in self.facts),
            }
            if not supplied_source_refs <= set(real_authorization.source_refs):
                raise ValueError("real brand source is outside operator authorization")
            if any(
                row.observed_at < real_authorization.valid_from
                or row.valid_until > real_authorization.valid_until
                for row in self.materials
            ) or any(
                row.effective_at < real_authorization.valid_from
                or row.valid_until > real_authorization.valid_until
                for row in self.facts
            ):
                raise ValueError(
                    "real brand input is outside operator authorization window"
                )

        def unique(values: list[str], label: str) -> set[str]:
            result = set(values)
            if len(result) != len(values):
                raise ValueError(f"duplicate {label} code")
            return result

        organizations = unique([row.code for row in self.organizations], "organization")
        stores = unique([row.code for row in self.stores], "store")
        roles = unique([row.code for row in self.roles], "role")
        accounts = unique([row.code for row in self.accounts], "account")
        authorizations = unique(
            [row.code for row in self.authorizations], "authorization"
        )
        unique([row.code for row in self.users], "user")
        unique([row.code for row in self.materials], "material")
        unique([row.code for row in self.facts], "fact")
        storylines = unique(
            [row.code for row in self.expression.storylines], "storyline"
        )
        unique([row.code for row in self.expression.columns], "column")
        stores_by_code = {row.code: row for row in self.stores}
        accounts_by_code = {row.code: row for row in self.accounts}
        authorizations_by_code = {row.code: row for row in self.authorizations}
        for store in self.stores:
            if store.organization_code not in organizations:
                raise ValueError("store organization is unknown")
        for account in self.accounts:
            if account.organization_code not in organizations:
                raise ValueError("account organization is unknown")
            if account.store_code is not None and account.store_code not in stores:
                raise ValueError("account store is unknown")
            if (
                account.store_code is not None
                and stores_by_code[account.store_code].organization_code
                != account.organization_code
            ):
                raise ValueError("account store is outside its organization")
            if account.role_code not in roles:
                raise ValueError("account role is unknown")
            if not set(account.allowed_source_organization_codes) <= organizations:
                raise ValueError("account source organization is unknown")
        for user in self.users:
            if not set(user.allowed_account_codes) <= accounts:
                raise ValueError("user account is unknown")
        for authorization_input in self.authorizations:
            if not set(authorization_input.organization_codes) <= organizations:
                raise ValueError("authorization organization is unknown")
            if not set(filter(None, authorization_input.store_codes)) <= stores:
                raise ValueError("authorization store is unknown")
            if not set(authorization_input.account_codes) <= accounts:
                raise ValueError("authorization account is unknown")
            for store_code in filter(None, authorization_input.store_codes):
                if (
                    stores_by_code[store_code].organization_code
                    not in authorization_input.organization_codes
                ):
                    raise ValueError("authorization store is outside its organization")
            for account_code in authorization_input.account_codes:
                account = accounts_by_code[account_code]
                if (
                    account.organization_code
                    not in authorization_input.organization_codes
                ):
                    raise ValueError(
                        "authorization does not cover account organization"
                    )
                if account.store_code not in authorization_input.store_codes:
                    raise ValueError("authorization does not cover account store")
        for material in self.materials:
            if material.authorization_code not in authorizations:
                raise ValueError("content authorization is unknown")
            if not set(material.account_codes) <= accounts:
                raise ValueError("content account is unknown")
            material_authorization = authorizations_by_code[material.authorization_code]
            if not set(material.account_codes) <= set(
                material_authorization.account_codes
            ):
                raise ValueError("content account is outside authorization scope")
            if (
                material.status == "ACTIVE"
                and material_authorization.status != "GRANTED"
            ):
                raise ValueError("active content requires a granted authorization")
            if (
                material.observed_at < material_authorization.valid_from
                or material.valid_until > material_authorization.valid_until
            ):
                raise ValueError("content validity is outside authorization window")
        for fact in self.facts:
            if fact.authorization_code not in authorizations:
                raise ValueError("content authorization is unknown")
            if not set(fact.account_codes) <= accounts:
                raise ValueError("content account is unknown")
            fact_authorization = authorizations_by_code[fact.authorization_code]
            if not set(fact.account_codes) <= set(fact_authorization.account_codes):
                raise ValueError("content account is outside authorization scope")
            if fact.status == "ACTIVE" and fact_authorization.status != "GRANTED":
                raise ValueError("active fact requires a granted authorization")
            if (
                fact.effective_at < fact_authorization.valid_from
                or fact.valid_until > fact_authorization.valid_until
            ):
                raise ValueError("fact validity is outside authorization window")
        for column in self.expression.columns:
            if column.storyline_code not in storylines:
                raise ValueError("column storyline is unknown")
        return self


def _identifier(prefix: str, *parts: str) -> str:
    normalized_parts = []
    for part in parts:
        normalized = re.sub(r"[^A-Z0-9-]", "-", part.upper())
        normalized = re.sub(r"-+", "-", normalized).strip("-")
        if not normalized:
            raise ValueError("identifier part is empty")
        normalized_parts.append(normalized)
    return f"{prefix}-{'--'.join(normalized_parts)}"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_brand_input(path: Path) -> BrandInputDocument:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("brand input must be a YAML object")
    return BrandInputDocument.model_validate(raw)


def compile_brand_bundle(document: BrandInputDocument) -> BrandImportBundle:
    enterprise = document.enterprise
    simulation_only = document.data_mode == "SIMULATION"
    test_fixture_only = document.safe_fixture_data
    tenant_id = _identifier("TENANT", enterprise.enterprise_code)
    brand_id = _identifier("BRAND", enterprise.enterprise_code, enterprise.brand_code)
    input_digest = hashlib.sha256(
        canonical_json(document.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()
    organization_ids = {
        row.code: _identifier("ORG", enterprise.enterprise_code, row.code)
        for row in document.organizations
    }
    store_ids = {
        row.code: _identifier("STORE", enterprise.enterprise_code, row.code)
        for row in document.stores
    }
    role_ids = {
        row.code: _identifier("ROLE", enterprise.enterprise_code, row.code)
        for row in document.roles
    }
    account_ids = {
        row.code: _identifier("ACCOUNT", enterprise.enterprise_code, row.code)
        for row in document.accounts
    }
    authorization_ids = {
        row.code: _identifier("AUTH", enterprise.enterprise_code, row.code)
        for row in document.authorizations
    }
    organizations = [
        {
            "organization_id": organization_ids[row.code],
            "tenant_id": tenant_id,
            "display_name": row.name,
            "organization_level": row.level,
            "status": "ACTIVE",
            "simulation_only": simulation_only,
            "test_fixture_only": test_fixture_only,
        }
        for row in document.organizations
    ]
    stores = [
        {
            "store_id": store_ids[row.code],
            "organization_id": organization_ids[row.organization_code],
            "display_name": row.name,
            "status": "ACTIVE",
            "simulation_only": simulation_only,
            "test_fixture_only": test_fixture_only,
        }
        for row in document.stores
    ]
    roles = [
        {
            "role_id": role_ids[row.code],
            "display_name": row.name,
            "boundary": row.boundary,
            "simulation_only": simulation_only,
            "test_fixture_only": test_fixture_only,
        }
        for row in document.roles
    ]
    accounts: list[JsonObject] = []
    for account_input in document.accounts:
        account_id = account_ids[account_input.code]
        accounts.append(
            {
                "account_id": account_id,
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "organization_id": organization_ids[account_input.organization_code],
                "store_id": None
                if account_input.store_code is None
                else store_ids[account_input.store_code],
                "display_name": account_input.display_name,
                "account_kind": "BRAND_OFFICIAL"
                if account_input.level == "HEADQUARTERS"
                else "STORE_ACCOUNT",
                "represented_scope": account_input.level,
                "maker_role_ids": [role_ids[account_input.role_code]],
                "confirmation_routes": [
                    {
                        "scope": "brand_formal_conclusion",
                        "confirmer_role_ids": [role_ids[account_input.role_code]],
                        "approval_mode": "ANY_OF",
                        "subject_confirmation_required": False,
                        "simulation_only": simulation_only,
                        "test_fixture_only": test_fixture_only,
                        "publish_allowed": False,
                    }
                ],
                "allowed_source_organization_ids": [
                    organization_ids[code]
                    for code in account_input.allowed_source_organization_codes
                ],
                "runtime_confirmation_authorization_ref": _identifier(
                    "AUTH", enterprise.enterprise_code, account_input.code, "confirm"
                ),
                "status": "ACTIVE",
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
                "publish_allowed": False,
            }
        )
    principals = []
    for user_input in document.users:
        allowed_ids = [account_ids[code] for code in user_input.allowed_account_codes]
        principals.append(
            {
                "principal_id": _identifier(
                    "PRINCIPAL", enterprise.enterprise_code, user_input.code
                ),
                "tenant_id": tenant_id,
                "username": user_input.username,
                "display_name": user_input.display_name,
                "trusted_identity_source": "SERVER_MANAGED_ONLY",
                "allowed_content_account_ids": allowed_ids,
                "account_role_grants": [
                    {
                        "account_id": account_ids[code],
                        "maker_role_ids": next(
                            account["maker_role_ids"]
                            for account in accounts
                            if account["account_id"] == account_ids[code]
                        ),
                        "confirmer_role_ids": next(
                            account["maker_role_ids"]
                            for account in accounts
                            if account["account_id"] == account_ids[code]
                        ),
                        "simulation_only": simulation_only,
                        "test_fixture_only": test_fixture_only,
                        "publish_allowed": False,
                    }
                    for code in user_input.allowed_account_codes
                ],
                "status": "ACTIVE",
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
            }
        )
    authorizations: list[JsonObject] = []
    for authorization_input in document.authorizations:
        authorizations.append(
            {
                "authorization_id": authorization_ids[authorization_input.code],
                "authorization_kind": "MATERIAL_AND_FACT_DISCLOSURE",
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "source_organization_id": organization_ids[
                    authorization_input.organization_codes[0]
                ],
                "source_store_id": (
                    None
                    if not authorization_input.store_codes
                    else (
                        None
                        if authorization_input.store_codes[0] is None
                        else store_ids[authorization_input.store_codes[0]]
                    )
                ),
                "permitted_organization_ids": [
                    organization_ids[code]
                    for code in authorization_input.organization_codes
                ],
                "permitted_store_ids": [
                    None if code is None else store_ids[code]
                    for code in authorization_input.store_codes
                ],
                "permitted_content_account_ids": [
                    account_ids[code] for code in authorization_input.account_codes
                ],
                "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
                "valid_from": _iso(authorization_input.valid_from),
                "valid_until": _iso(authorization_input.valid_until),
                "status": authorization_input.status,
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
                "publish_allowed": False,
            }
        )
    valid_grants = [row for row in document.authorizations if row.status == "GRANTED"]
    if not valid_grants:
        raise ValueError("at least one granted authorization is required")
    confirmation_start = min(row.valid_from for row in valid_grants)
    confirmation_end = max(row.valid_until for row in valid_grants)
    for account_input in document.accounts:
        account_id = account_ids[account_input.code]
        authorizations.append(
            {
                "authorization_id": _identifier(
                    "AUTH", enterprise.enterprise_code, account_input.code, "confirm"
                ),
                "authorization_kind": "REQUIREMENT_CONFIRMATION",
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "source_organization_id": organization_ids[
                    account_input.organization_code
                ],
                "source_store_id": (
                    None
                    if account_input.store_code is None
                    else store_ids[account_input.store_code]
                ),
                "permitted_organization_ids": [
                    organization_ids[account_input.organization_code]
                ],
                "permitted_store_ids": [
                    None
                    if account_input.store_code is None
                    else store_ids[account_input.store_code]
                ],
                "permitted_content_account_ids": [account_id],
                "disclosure_scope": "REQUIREMENT_CONFIRMATION_ONLY",
                "valid_from": _iso(confirmation_start),
                "valid_until": _iso(confirmation_end),
                "status": "GRANTED",
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
                "publish_allowed": False,
            }
        )
        authorizations.append(
            {
                "authorization_id": _identifier(
                    "AUTH", enterprise.enterprise_code, account_input.code, "disclose"
                ),
                "authorization_kind": "FACT_DISCLOSURE",
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "source_organization_id": organization_ids[
                    account_input.organization_code
                ],
                "source_store_id": (
                    None
                    if account_input.store_code is None
                    else store_ids[account_input.store_code]
                ),
                "permitted_organization_ids": [
                    organization_ids[account_input.organization_code]
                ],
                "permitted_store_ids": [
                    None
                    if account_input.store_code is None
                    else store_ids[account_input.store_code]
                ],
                "permitted_content_account_ids": [account_id],
                "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
                "valid_from": _iso(confirmation_start),
                "valid_until": _iso(confirmation_end),
                "status": "GRANTED",
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
                "publish_allowed": False,
            }
        )

    account_inputs = {row.code: row for row in document.accounts}

    def scopes(codes: list[str]) -> tuple[list[str], list[str | None]]:
        organization_scope = sorted(
            {organization_ids[account_inputs[code].organization_code] for code in codes}
        )
        store_scope = sorted(
            {
                None
                if account_inputs[code].store_code is None
                else store_ids[str(account_inputs[code].store_code)]
                for code in codes
            },
            key=lambda value: "" if value is None else value,
        )
        return organization_scope, store_scope

    fragments: list[JsonObject] = []
    for material_input in document.materials:
        organizations_scope, stores_scope = scopes(material_input.account_codes)
        source_account = account_inputs[material_input.account_codes[0]]
        source_organization_id = organization_ids[source_account.organization_code]
        source_store_id = (
            None
            if source_account.store_code is None
            else store_ids[source_account.store_code]
        )
        text = material_input.text.replace("\r\n", "\n").replace("\r", "\n").strip()
        source_id = _identifier(
            "SOURCE", enterprise.enterprise_code, "material", material_input.code
        )
        source_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        fragments.append(
            {
                "fragment_id": _identifier(
                    "FRAGMENT", enterprise.enterprise_code, material_input.code
                ),
                "unit_id": material_input.code,
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "text": text,
                "title": material_input.title,
                "source_id": source_id,
                "source_ref": material_input.source_ref,
                "source_sha256": source_digest,
                "fragment_sha256": source_digest,
                "source_organization_id": source_organization_id,
                "source_store_id": source_store_id,
                "applicable_organization_ids": organizations_scope,
                "applicable_store_ids": stores_scope,
                "applicable_content_account_ids": [
                    account_ids[code] for code in material_input.account_codes
                ],
                "authorization_ref": authorization_ids[
                    material_input.authorization_code
                ],
                "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
                "authorization_state": (
                    "GRANTED" if material_input.status == "ACTIVE" else "REVOKED"
                ),
                "observed_at": _iso(material_input.observed_at),
                "valid_until": _iso(material_input.valid_until),
                "status": material_input.status,
                "revocation_ref": (
                    None
                    if material_input.status == "ACTIVE"
                    else _identifier(
                        "REVOKE", enterprise.enterprise_code, material_input.code
                    )
                ),
                "data_version_digest": input_digest,
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
                "publish_allowed": False,
                "runtime_consumable": False,
                "source_label": material_input.source_label,
            }
        )
    facts: list[JsonObject] = []
    for fact_input in document.facts:
        organizations_scope, stores_scope = scopes(fact_input.account_codes)
        source_account = account_inputs[fact_input.account_codes[0]]
        source_organization_id = organization_ids[source_account.organization_code]
        source_store_id = (
            None
            if source_account.store_code is None
            else store_ids[source_account.store_code]
        )
        json_value = json.loads(fact_input.model_dump_json())["value"]
        value_digest = digest_object(json_value)
        source_id = _identifier(
            "SOURCE", enterprise.enterprise_code, "fact", fact_input.code
        )
        facts.append(
            {
                "fact_id": _identifier(
                    "FACT", enterprise.enterprise_code, fact_input.code
                ),
                "fact_kind": fact_input.kind,
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "organization_id": source_organization_id,
                "store_id": source_store_id,
                "applicable_content_account_ids": [
                    account_ids[code] for code in fact_input.account_codes
                ],
                "authorization_ref": authorization_ids[fact_input.authorization_code],
                "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
                "effective_at": _iso(fact_input.effective_at),
                "valid_until": _iso(fact_input.valid_until),
                "status": fact_input.status,
                "revocation_ref": (
                    None
                    if fact_input.status == "ACTIVE"
                    else _identifier(
                        "REVOKE", enterprise.enterprise_code, fact_input.code
                    )
                ),
                "source_id": source_id,
                "source_ref": fact_input.source_ref,
                "source_sha256": value_digest,
                "source_excerpt_sha256": value_digest,
                "data_version_digest": input_digest,
                "value": json_value,
                "label": fact_input.label,
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
                "publish_allowed": False,
                "runtime_consumable": False,
                "source_label": fact_input.source_label,
            }
        )
    for account_input in document.accounts:
        account_id = account_ids[account_input.code]
        organization_id = organization_ids[account_input.organization_code]
        store_id = (
            None
            if account_input.store_code is None
            else store_ids[account_input.store_code]
        )
        value = {
            "account_id": account_id,
            "display_name": account_input.display_name,
            "represented_scope": account_input.level,
            "organization_id": organization_id,
            "store_id": store_id,
        }
        value_digest = digest_object(value)
        source_id = _identifier(
            "SOURCE", enterprise.enterprise_code, account_input.code, "scope"
        )
        facts.append(
            {
                "fact_id": _identifier(
                    "FACT", enterprise.enterprise_code, account_input.code, "scope"
                ),
                "fact_kind": "AUTHORIZATION",
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "organization_id": organization_id,
                "store_id": store_id,
                "applicable_content_account_ids": [account_id],
                "authorization_ref": _identifier(
                    "AUTH", enterprise.enterprise_code, account_input.code, "disclose"
                ),
                "disclosure_scope": "CONTENT_ACCOUNT_ONLY",
                "effective_at": _iso(confirmation_start),
                "valid_until": _iso(confirmation_end),
                "status": "ACTIVE",
                "revocation_ref": None,
                "source_id": source_id,
                "source_ref": (
                    f"brand-import-contract://{input_digest}/account/{account_id}"
                ),
                "source_sha256": value_digest,
                "source_excerpt_sha256": value_digest,
                "data_version_digest": input_digest,
                "value": value,
                "label": "内容账号范围",
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
                "publish_allowed": False,
                "runtime_consumable": False,
                "source_label": "第8包服务端身份范围",
            }
        )
    profile = {
        "schema_version": "v1.0",
        "profile_ref": f"expression-profile://{brand_id.lower()}/v1",
        "profile_version": 1,
        "resolution_mode": (
            "REVIEWED_SIMULATION_BRAND"
            if simulation_only
            else "AUTHORIZED_REAL_BRAND_INPUT"
        ),
        "tenant_specific": True,
        "tenant_id": tenant_id,
        "brand_id": brand_id,
        "simulation_only": simulation_only,
        "test_fixture_only": test_fixture_only,
        "publish_allowed": False,
        "operating_proposition": {
            "why_exist": document.expression.why_exist,
            "serves": document.expression.audience,
        },
        "hard_protections": {
            "protected_core": [
                "不把建议或创意写成已经发生的品牌事实。",
                "不跨企业、品牌、门店或内容账号借用资料。",
                "撤回或过期资料立即停止使用。",
            ],
            "source_refs": [],
        },
        "tone_tendencies": list(document.expression.tone_tendencies),
        "preferred_phrasing": list(document.expression.preferred_phrasing),
        "prohibited_expression_categories": list(
            document.expression.prohibited_categories
        ),
        "literal_prohibited_phrases": ["百分百适合", "永远有效"],
        "expression_intensity": "MEDIUM",
        "perspective": "ACCOUNT_AND_TASK_APPROPRIATE",
        "may_grant_fact_authorization_or_scope": False,
        "cross_tenant_borrowing_allowed": False,
        "runtime_publishable": False,
        "principal_roles": [
            {
                "role_id": role_ids[row.code],
                "display_name": row.name,
                "kind": "PROFESSIONAL",
                "source_role_refs": [role_ids[row.code]],
                "boundary": row.boundary,
            }
            for row in document.roles
        ],
        "storylines": [
            {
                "storyline_id": _identifier(
                    "STORYLINE", enterprise.enterprise_code, row.code
                ),
                "display_name": row.name,
                "purpose": row.purpose,
                "source_refs": [],
            }
            for row in document.expression.storylines
        ],
        "columns": [
            {
                "column_id": _identifier(
                    "COLUMN", enterprise.enterprise_code, row.code
                ),
                "display_name": row.name,
                "storyline_id": _identifier(
                    "STORYLINE", enterprise.enterprise_code, row.storyline_code
                ),
            }
            for row in document.expression.columns
        ],
        "account_role_cards": [
            {
                "account_id": account_ids[row.code],
                "level": row.level,
                "display_role": next(
                    role.name for role in document.roles if role.code == row.role_code
                ),
                "default_role_id": role_ids[row.role_code],
            }
            for row in document.accounts
        ],
    }
    identity = {
        "tenant": {
            "tenant_id": tenant_id,
            "brand_id": brand_id,
            "display_name": enterprise.enterprise_name,
            "brand_display_name": enterprise.brand_name,
            "tenant_kind": (
                "SIMULATED_ACCEPTANCE_ENTERPRISE"
                if simulation_only
                else "AUTHORIZED_REAL_BRAND_ENTERPRISE"
            ),
            "simulation_only": simulation_only,
            "test_fixture_only": test_fixture_only,
            "publish_allowed": False,
        },
        "organizations": organizations,
        "stores": stores,
        "work_roles": roles,
        "login_principals": principals,
        "content_accounts": accounts,
        "authorization_grants": authorizations,
        "subject_confirmation_records": [],
        "source": {
            "source_ref": (
                "fixture://package8-brand-input"
                if simulation_only
                else f"brand-import-contract://{input_digest}"
            ),
            "sha256": input_digest,
        },
    }
    return BrandImportBundle(
        identity=identity,
        narrative_fragments=tuple(fragments),
        precise_facts=tuple(facts),
        expression_profile=profile,
        source_manifest={
            "schema_version": document.schema_version,
            "input_digest": input_digest,
            "data_mode": document.data_mode,
            "simulation_only": simulation_only,
            "test_fixture_only": test_fixture_only,
            "publish_allowed": False,
            "compiler": "DIYU_HOSTED_OPERATIONS_001",
            "real_brand_authorization": (
                None
                if document.real_brand_authorization is None
                else document.real_brand_authorization.model_dump(mode="json")
            ),
            "derived_source_refs": [
                f"brand-import-contract://{input_digest}/account/{account_ids[row.code]}"
                for row in document.accounts
            ],
        },
    )


def bundle_to_payload(bundle: BrandImportBundle) -> JsonObject:
    return {
        "identity": copy.deepcopy(bundle.identity),
        "narrative_fragments": copy.deepcopy(list(bundle.narrative_fragments)),
        "precise_facts": copy.deepcopy(list(bundle.precise_facts)),
        "expression_profile": copy.deepcopy(bundle.expression_profile),
        "source_manifest": copy.deepcopy(bundle.source_manifest),
    }


def bundle_from_payload(payload: JsonObject) -> BrandImportBundle:
    return BrandImportBundle(
        identity=copy.deepcopy(dict(payload["identity"])),
        narrative_fragments=tuple(copy.deepcopy(list(payload["narrative_fragments"]))),
        precise_facts=tuple(copy.deepcopy(list(payload["precise_facts"]))),
        expression_profile=copy.deepcopy(dict(payload["expression_profile"])),
        source_manifest=copy.deepcopy(dict(payload["source_manifest"])),
    )


def bundle_digest(bundle: BrandImportBundle) -> str:
    return hashlib.sha256(
        canonical_json(bundle_to_payload(bundle)).encode("utf-8")
    ).hexdigest()
