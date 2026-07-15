#!/usr/bin/env python3
"""Deterministic, simulation-only brand fact retrieval vertical slice."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml  # type: ignore[import-untyped]


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
IDENTITY_PATH = (
    REPO_ROOT
    / "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml"
)
MANIFEST_PATH = PACKAGE_ROOT / "retrieval_manifest.v1.json"
FRAGMENT_PATH = PACKAGE_ROOT / "data/retrieval_fragments.v1.jsonl"
FACT_PATH = PACKAGE_ROOT / "data/verified_precise_facts.v1.jsonl"
DISPOSITION_PATH = PACKAGE_ROOT / "data/source_dispositions.v1.jsonl"
EXPRESSION_PATH = PACKAGE_ROOT / "data/expression_candidates.v1.json"

ALLOWED_FACT_KINDS = frozenset(
    {"SKU", "SPECIFICATION", "PRICE", "STOCK", "TIME_POINT", "AUTHORIZATION", "REVOCATION"}
)
ALLOWED_REQUEST_FIELDS = frozenset(
    {
        "query_text",
        "max_fragments",
        "precise_fact_queries",
        "client_claims",
        "requested_high_level_mode_refs",
        "approved_example_refs",
    }
)
ALLOWED_FACT_QUERY_FIELDS = frozenset({"fact_kind", "selectors", "required"})


class RetrievalContractError(ValueError):
    """Raised when a request attempts to cross the local trust contract."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable UTF-8 JSON bytes for hashing and generated artifacts."""

    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def parse_timestamp(value: object) -> datetime:
    """Parse an ISO timestamp; source date-only values map to UTC day start."""

    if not isinstance(value, str) or not value.strip():
        raise RetrievalContractError("INVALID_TIME", "expected a non-empty ISO timestamp")
    normalized = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        normalized = f"{normalized}T00:00:00Z"
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RetrievalContractError("INVALID_TIME", value) from exc
    if parsed.tzinfo is None:
        raise RetrievalContractError("INVALID_TIME", "timezone is required")
    return parsed.astimezone(timezone.utc)


def iso_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read_jsonl(path: Path) -> tuple[JsonObject, ...]:
    rows: list[JsonObject] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RetrievalContractError("INVALID_DATA", f"{path}:{line_number}")
        rows.append(value)
    return tuple(rows)


def require_mapping(value: object, label: str) -> JsonObject:
    if not isinstance(value, dict):
        raise RetrievalContractError("INVALID_REQUEST", f"{label} must be an object")
    return value


def require_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RetrievalContractError("INVALID_REQUEST", f"{label} must be a string list")
    return list(value)


@dataclass(frozen=True)
class TrustedScope:
    tenant_id: str
    brand_id: str
    principal_id: str
    content_account_id: str
    organization_id: str
    store_id: str | None
    allowed_source_organization_ids: tuple[str, ...]
    role_ids: tuple[str, ...]

    @property
    def scope_ref(self) -> str:
        return (
            f"scope://{self.tenant_id}/{self.principal_id}/{self.content_account_id}"
        )


@dataclass(frozen=True)
class IdentityAuthority:
    tenant_id: str
    brand_id: str
    principals: Mapping[str, JsonObject]
    organizations: Mapping[str, JsonObject]
    stores: Mapping[str, JsonObject]
    accounts: Mapping[str, JsonObject]
    grants: Mapping[str, JsonObject]

    @classmethod
    def from_path(cls, path: Path = IDENTITY_PATH) -> IdentityAuthority:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise RetrievalContractError("IDENTITY_INVALID", str(path))
        root = document.get("simulation_tenant")
        if not isinstance(root, dict) or not isinstance(root.get("tenant"), dict):
            raise RetrievalContractError("IDENTITY_INVALID", "simulation_tenant")
        tenant = root["tenant"]

        def by_id(rows: object, key: str) -> dict[str, JsonObject]:
            if not isinstance(rows, list):
                raise RetrievalContractError("IDENTITY_INVALID", key)
            result: dict[str, JsonObject] = {}
            for row in rows:
                item = require_mapping(row, key)
                identifier = item.get(key)
                if not isinstance(identifier, str) or identifier in result:
                    raise RetrievalContractError("IDENTITY_INVALID", key)
                result[identifier] = item
            return result

        return cls(
            tenant_id=str(tenant["tenant_id"]),
            brand_id=str(tenant["brand_id"]),
            principals=by_id(root.get("login_principals"), "principal_id"),
            organizations=by_id(root.get("organizations"), "organization_id"),
            stores=by_id(root.get("stores"), "store_id"),
            accounts=by_id(root.get("content_accounts"), "account_id"),
            grants=by_id(root.get("authorization_grants"), "authorization_id"),
        )

    def resolve_scope(self, principal_id: str, account_id: str) -> TrustedScope:
        principal = self.principals.get(principal_id)
        account = self.accounts.get(account_id)
        if principal is None:
            raise RetrievalContractError("UNTRUSTED_PRINCIPAL", principal_id)
        if account is None:
            raise RetrievalContractError("UNKNOWN_CONTENT_ACCOUNT", account_id)
        if principal.get("trusted_identity_source") != "SERVER_MANAGED_ONLY":
            raise RetrievalContractError("UNTRUSTED_PRINCIPAL", principal_id)
        if principal.get("tenant_id") != self.tenant_id:
            raise RetrievalContractError("CROSS_TENANT_SCOPE", principal_id)
        allowed_accounts = principal.get("allowed_content_account_ids")
        if not isinstance(allowed_accounts, list) or account_id not in allowed_accounts:
            raise RetrievalContractError("CONTENT_ACCOUNT_NOT_GRANTED", account_id)
        role_grants = principal.get("account_role_grants")
        if not isinstance(role_grants, list):
            raise RetrievalContractError("ROLE_GRANT_MISSING", account_id)
        matching = [
            row
            for row in role_grants
            if isinstance(row, dict) and row.get("account_id") == account_id
        ]
        if len(matching) != 1:
            raise RetrievalContractError("ROLE_GRANT_MISSING", account_id)
        roles = matching[0].get("maker_role_ids")
        if not isinstance(roles, list) or not roles or any(not isinstance(role, str) for role in roles):
            raise RetrievalContractError("ROLE_GRANT_MISSING", account_id)
        organization_id = account.get("organization_id")
        store_id = account.get("store_id")
        if not isinstance(organization_id, str) or organization_id not in self.organizations:
            raise RetrievalContractError("ORGANIZATION_UNREGISTERED", account_id)
        if store_id is not None:
            if not isinstance(store_id, str) or store_id not in self.stores:
                raise RetrievalContractError("STORE_UNREGISTERED", account_id)
            if self.stores[store_id].get("organization_id") != organization_id:
                raise RetrievalContractError("STORE_SCOPE_MISMATCH", account_id)
        source_organizations = account.get("allowed_source_organization_ids")
        if not isinstance(source_organizations, list) or any(
            not isinstance(item, str) for item in source_organizations
        ):
            raise RetrievalContractError("SOURCE_SCOPE_MISSING", account_id)
        return TrustedScope(
            tenant_id=self.tenant_id,
            brand_id=self.brand_id,
            principal_id=principal_id,
            content_account_id=account_id,
            organization_id=organization_id,
            store_id=store_id,
            allowed_source_organization_ids=tuple(source_organizations),
            role_ids=tuple(roles),
        )


@dataclass(frozen=True)
class RetrievalIndex:
    fragments: tuple[JsonObject, ...]
    facts: tuple[JsonObject, ...]
    dispositions: tuple[JsonObject, ...]
    expression_candidates: JsonObject
    data_version_digest: str

    @classmethod
    def from_package(cls, package_root: Path = PACKAGE_ROOT) -> RetrievalIndex:
        manifest = json.loads(
            (package_root / "retrieval_manifest.v1.json").read_text(encoding="utf-8")
        )
        if not isinstance(manifest, dict) or not isinstance(
            manifest.get("data_version_digest"), str
        ):
            raise RetrievalContractError("MANIFEST_INVALID", str(package_root))
        expression = json.loads(
            (package_root / "data/expression_candidates.v1.json").read_text(
                encoding="utf-8"
            )
        )
        if not isinstance(expression, dict):
            raise RetrievalContractError("EXPRESSION_PARTITION_INVALID", str(package_root))
        return cls(
            fragments=read_jsonl(package_root / "data/retrieval_fragments.v1.jsonl"),
            facts=read_jsonl(package_root / "data/verified_precise_facts.v1.jsonl"),
            dispositions=read_jsonl(package_root / "data/source_dispositions.v1.jsonl"),
            expression_candidates=expression,
            data_version_digest=manifest["data_version_digest"],
        )

    def with_records(
        self,
        *,
        fragments: Iterable[JsonObject] = (),
        facts: Iterable[JsonObject] = (),
    ) -> RetrievalIndex:
        return replace(
            self,
            fragments=(*self.fragments, *(copy.deepcopy(row) for row in fragments)),
            facts=(*self.facts, *(copy.deepcopy(row) for row in facts)),
        )


class BrandFactRetrievalService:
    """Resolve trusted scope, prefilter records, then rank or query facts."""

    def __init__(self, authority: IdentityAuthority, index: RetrievalIndex) -> None:
        self.authority = authority
        self.index = index

    @classmethod
    def from_package(cls, package_root: Path = PACKAGE_ROOT) -> BrandFactRetrievalService:
        return cls(IdentityAuthority.from_path(), RetrievalIndex.from_package(package_root))

    def retrieve(
        self,
        request: Mapping[str, Any],
        *,
        principal_id: str,
        content_account_id: str,
        query_at: str,
    ) -> JsonObject:
        unknown = set(request) - ALLOWED_REQUEST_FIELDS
        if unknown:
            raise RetrievalContractError("UNKNOWN_REQUEST_FIELDS", ",".join(sorted(unknown)))
        scope = self.authority.resolve_scope(principal_id, content_account_id)
        now = parse_timestamp(query_at)
        query_text = request.get("query_text", "")
        if not isinstance(query_text, str):
            raise RetrievalContractError("INVALID_REQUEST", "query_text")
        max_fragments = request.get("max_fragments", 5)
        if not isinstance(max_fragments, int) or isinstance(max_fragments, bool):
            raise RetrievalContractError("INVALID_REQUEST", "max_fragments")
        if not 1 <= max_fragments <= 20:
            raise RetrievalContractError("INVALID_REQUEST", "max_fragments must be 1..20")
        client_claims = request.get("client_claims", {})
        if not isinstance(client_claims, dict):
            raise RetrievalContractError("INVALID_REQUEST", "client_claims")

        filtered_fragments, fragment_exclusions = self._prefilter_fragments(scope, now)
        ranked = self._rank_fragments(query_text, filtered_fragments, max_fragments)
        gaps: list[JsonObject] = []
        if query_text.strip() and not ranked:
            gaps.append(
                self._gap(
                    "MATERIAL_MISSING_FOR_SCOPE",
                    "COLLECT_MATERIAL",
                    "No relevant authorized narrative material exists for the resolved account scope.",
                )
            )
        if not query_text.strip() and not request.get("precise_fact_queries"):
            gaps.append(
                self._gap(
                    "QUERY_OR_FACT_REQUEST_REQUIRED",
                    "REQUEST_CLARIFICATION",
                    "Provide a narrative query or at least one precise fact request.",
                )
            )

        facts, fact_gaps, fact_audit = self._resolve_fact_queries(
            request.get("precise_fact_queries", []), scope, now
        )
        gaps.extend(fact_gaps)
        expression = self._resolve_expression_candidates(request)
        fragments = [copy.deepcopy(row) for _, row in ranked]
        return {
            "schema_version": "v1.0",
            "result_type": "BRAND_FACT_RETRIEVAL_RESULT",
            "trusted_scope_ref": scope.scope_ref,
            "resolved_scope": {
                "tenant_id": scope.tenant_id,
                "brand_id": scope.brand_id,
                "organization_id": scope.organization_id,
                "store_id": scope.store_id,
                "login_principal_id": scope.principal_id,
                "content_account_id": scope.content_account_id,
            },
            "query_at": iso_timestamp(now),
            "data_version_digest": self.index.data_version_digest,
            "scoped_retrieval_fragments": fragments,
            "verified_precise_facts": facts,
            "gaps": gaps,
            "expression_candidate_partition": expression,
            "claim_precedence": {
                "policy": "VERIFIED_PRECISE_FACT_OVER_RETRIEVED_NARRATIVE",
                "narrative_may_create_precise_fact": False,
                "revocation_over_prior_authorization": True,
            },
            "retrieval_audit": {
                "prefilter_before_ranking": True,
                "fragment_input_count": len(self.index.fragments),
                "fragment_excluded_counts": dict(sorted(fragment_exclusions.items())),
                "ranker_input_fragment_ids": [
                    str(row["fragment_id"]) for row in filtered_fragments
                ],
                "ranked_fragment_count": len(fragments),
                "fact_audit": fact_audit,
                "client_claims_ignored": bool(client_claims),
                "external_call_count": 0,
            },
            "simulation_only": True,
            "publish_allowed": False,
            "runtime_consumable": False,
        }

    def _prefilter_fragments(
        self, scope: TrustedScope, now: datetime
    ) -> tuple[list[JsonObject], Counter[str]]:
        accepted: list[JsonObject] = []
        excluded: Counter[str] = Counter()
        for row in self.index.fragments:
            reason = self._record_filter_reason(row, scope, now, record_type="FRAGMENT")
            if reason is None:
                accepted.append(row)
            else:
                excluded[reason] += 1
        return accepted, excluded

    def _prefilter_facts(
        self, scope: TrustedScope, now: datetime
    ) -> tuple[list[JsonObject], Counter[str]]:
        accepted: list[JsonObject] = []
        excluded: Counter[str] = Counter()
        for row in self.index.facts:
            reason = self._record_filter_reason(row, scope, now, record_type="FACT")
            if reason is None:
                accepted.append(row)
            else:
                excluded[reason] += 1
        return accepted, excluded

    def _record_filter_reason(
        self,
        row: JsonObject,
        scope: TrustedScope,
        now: datetime,
        *,
        record_type: str,
    ) -> str | None:
        if row.get("status") != "ACTIVE":
            return "NOT_ACTIVE"
        if row.get("revocation_ref") not in (None, ""):
            return "REVOKED"
        if not isinstance(row.get("source_ref"), str) or not row["source_ref"].strip():
            return "SOURCE_MISSING"
        if row.get("tenant_id") != scope.tenant_id:
            return "TENANT_MISMATCH"
        if row.get("brand_id") != scope.brand_id:
            return "BRAND_MISMATCH"

        source_organization = row.get(
            "source_organization_id" if record_type == "FRAGMENT" else "organization_id"
        )
        source_store = row.get("source_store_id" if record_type == "FRAGMENT" else "store_id")
        if (
            not isinstance(source_organization, str)
            or source_organization not in self.authority.organizations
            or source_organization not in scope.allowed_source_organization_ids
        ):
            return "SOURCE_SCOPE_UNREGISTERED"
        if source_store is not None:
            if not isinstance(source_store, str) or source_store not in self.authority.stores:
                return "SOURCE_SCOPE_UNREGISTERED"
            if self.authority.stores[source_store].get("organization_id") != source_organization:
                return "SOURCE_SCOPE_UNREGISTERED"

        if record_type == "FRAGMENT":
            if row.get("authorization_state") != "GRANTED":
                return "AUTHORIZATION_INVALID"
            if scope.organization_id not in row.get("applicable_organization_ids", []):
                return "TARGET_ORGANIZATION_MISMATCH"
            if scope.store_id not in row.get("applicable_store_ids", []):
                return "TARGET_STORE_MISMATCH"
        if scope.content_account_id not in row.get("applicable_content_account_ids", []):
            return "TARGET_ACCOUNT_MISMATCH"

        observed_key = "observed_at" if record_type == "FRAGMENT" else "effective_at"
        try:
            if parse_timestamp(row.get(observed_key)) > now:
                return "FUTURE"
            if parse_timestamp(row.get("valid_until")) < now:
                return "EXPIRED"
        except RetrievalContractError:
            return "TIME_INVALID"

        grant_id = row.get("authorization_ref")
        grant = self.authority.grants.get(grant_id) if isinstance(grant_id, str) else None
        if grant is None or not self._grant_covers_record(
            grant, row, scope, now, record_type=record_type
        ):
            return "AUTHORIZATION_INVALID"
        return None

    def _grant_covers_record(
        self,
        grant: JsonObject,
        row: JsonObject,
        scope: TrustedScope,
        now: datetime,
        *,
        record_type: str,
    ) -> bool:
        allowed_kinds = (
            {"MATERIAL_AND_FACT_DISCLOSURE"}
            if record_type == "FRAGMENT"
            else {"MATERIAL_AND_FACT_DISCLOSURE", "FACT_DISCLOSURE"}
        )
        try:
            within_time = (
                parse_timestamp(grant.get("valid_from"))
                <= now
                <= parse_timestamp(grant.get("valid_until"))
            )
        except RetrievalContractError:
            return False
        source_org_key = (
            "source_organization_id" if record_type == "FRAGMENT" else "organization_id"
        )
        source_store_key = "source_store_id" if record_type == "FRAGMENT" else "store_id"
        return bool(
            grant.get("status") == "GRANTED"
            and grant.get("authorization_kind") in allowed_kinds
            and within_time
            and grant.get("tenant_id") == scope.tenant_id
            and grant.get("brand_id") == scope.brand_id
            and grant.get("source_organization_id") == row.get(source_org_key)
            and grant.get("source_store_id") == row.get(source_store_key)
            and scope.organization_id in grant.get("permitted_organization_ids", [])
            and scope.store_id in grant.get("permitted_store_ids", [])
            and scope.content_account_id in grant.get("permitted_content_account_ids", [])
            and grant.get("disclosure_scope") == row.get("disclosure_scope")
        )

    def _rank_fragments(
        self, query_text: str, fragments: Sequence[JsonObject], limit: int
    ) -> list[tuple[float, JsonObject]]:
        query_terms = self._lexical_terms(query_text)
        if not query_terms:
            return []
        normalized_query = self._normalize_text(query_text)
        ranked: list[tuple[float, JsonObject]] = []
        for row in fragments:
            text = str(row.get("text", ""))
            document_terms = self._lexical_terms(text)
            overlap = len(query_terms & document_terms)
            score = overlap / len(query_terms)
            if normalized_query and normalized_query in self._normalize_text(text):
                score += 2.0
            if score > 0:
                ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], str(item[1].get("fragment_id"))))
        return ranked[:limit]

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", "", value).casefold()

    @staticmethod
    def _lexical_terms(value: str) -> set[str]:
        lowered = value.casefold()
        terms = set(re.findall(r"[a-z0-9]+", lowered))
        for sequence in re.findall(r"[\u4e00-\u9fff]+", lowered):
            terms.update(sequence)
            terms.update(sequence[index : index + 2] for index in range(len(sequence) - 1))
        return terms

    def _resolve_fact_queries(
        self, raw_queries: object, scope: TrustedScope, now: datetime
    ) -> tuple[list[JsonObject], list[JsonObject], JsonObject]:
        if not isinstance(raw_queries, list):
            raise RetrievalContractError("INVALID_REQUEST", "precise_fact_queries")
        filtered, excluded = self._prefilter_facts(scope, now)
        selected: dict[str, JsonObject] = {}
        gaps: list[JsonObject] = []
        for position, raw_query in enumerate(raw_queries):
            query = require_mapping(raw_query, f"precise_fact_queries[{position}]")
            unknown = set(query) - ALLOWED_FACT_QUERY_FIELDS
            if unknown:
                raise RetrievalContractError(
                    "UNKNOWN_FACT_QUERY_FIELDS", ",".join(sorted(unknown))
                )
            fact_kind = query.get("fact_kind")
            if not isinstance(fact_kind, str) or fact_kind not in ALLOWED_FACT_KINDS:
                raise RetrievalContractError("INVALID_FACT_KIND", str(fact_kind))
            selectors = query.get("selectors", {})
            if not isinstance(selectors, dict) or any(
                not isinstance(key, str) for key in selectors
            ):
                raise RetrievalContractError("INVALID_FACT_SELECTORS", fact_kind)
            required = query.get("required", True)
            if not isinstance(required, bool):
                raise RetrievalContractError("INVALID_REQUEST", "required")
            kind_matches = [row for row in filtered if row.get("fact_kind") == fact_kind]
            matches = [row for row in kind_matches if self._selectors_match(row, selectors)]
            if not selectors and len(matches) > 1:
                if required:
                    gaps.append(
                        self._gap(
                            "PRECISE_FACT_SELECTOR_REQUIRED",
                            "COLLECT_FACT",
                            f"{fact_kind} identifies multiple objects; an exact selector is required.",
                            fact_kind=fact_kind,
                        )
                    )
                continue
            if not matches:
                if required:
                    gaps.append(self._missing_fact_gap(fact_kind, selectors))
                continue
            chosen = self._choose_fact(matches)
            if chosen is None:
                gaps.append(
                    self._gap(
                        "PRECISE_FACT_CONFLICT",
                        "RECONFIRM_FACT",
                        f"Conflicting {fact_kind} values share the latest effective time.",
                        fact_kind=fact_kind,
                    )
                )
                continue
            selected[str(chosen["fact_id"])] = copy.deepcopy(chosen)
        ordered = [selected[key] for key in sorted(selected)]
        return (
            ordered,
            gaps,
            {
                "prefilter_before_exact_match": True,
                "input_count": len(self.index.facts),
                "excluded_counts": dict(sorted(excluded.items())),
                "eligible_fact_ids": [str(row["fact_id"]) for row in filtered],
                "selected_fact_ids": [str(row["fact_id"]) for row in ordered],
            },
        )

    @staticmethod
    def _selectors_match(row: JsonObject, selectors: Mapping[str, Any]) -> bool:
        value = row.get("value")
        value_map = value if isinstance(value, dict) else {}
        for key, expected in selectors.items():
            actual = row.get("fact_id") if key == "fact_id" else value_map.get(key)
            if actual != expected:
                return False
        return True

    @staticmethod
    def _choose_fact(matches: Sequence[JsonObject]) -> JsonObject | None:
        if len(matches) == 1:
            return matches[0]
        latest_time = max(parse_timestamp(row.get("effective_at")) for row in matches)
        latest = [
            row for row in matches if parse_timestamp(row.get("effective_at")) == latest_time
        ]
        value_digests = {digest_object(row.get("value")) for row in latest}
        if len(value_digests) != 1:
            return None
        return min(latest, key=lambda row: str(row.get("fact_id")))

    def _missing_fact_gap(
        self, fact_kind: str, selectors: Mapping[str, Any]
    ) -> JsonObject:
        held = [
            row
            for row in self.index.dispositions
            if row.get("record_type") == "PRECISE_FACT"
            and row.get("fact_kind") == fact_kind
            and self._disposition_selectors_match(row, selectors)
        ]
        reasons = {str(row.get("reason_code")) for row in held}
        if any(
            "RECONFIRM" in reason or "EXPIRED" in reason or "FUTURE" in reason
            for reason in reasons
        ):
            return self._gap(
                "PRECISE_FACT_RECONFIRMATION_REQUIRED",
                "RECONFIRM_FACT",
                f"{fact_kind} exists only as stale, future, or reconfirmation-required evidence.",
                fact_kind=fact_kind,
            )
        return self._gap(
            "PRECISE_FACT_MISSING",
            "COLLECT_FACT",
            f"No verified {fact_kind} exists for the exact requested scope and selector.",
            fact_kind=fact_kind,
        )

    @staticmethod
    def _disposition_selectors_match(
        row: JsonObject, selectors: Mapping[str, Any]
    ) -> bool:
        if not selectors:
            return True
        projection = row.get("selector_projection")
        if not isinstance(projection, dict):
            return False
        return all(projection.get(key) == expected for key, expected in selectors.items())

    def _resolve_expression_candidates(self, request: Mapping[str, Any]) -> JsonObject:
        partition = self.index.expression_candidates
        modes = require_string_list(
            partition.get("available_high_level_mode_refs", []),
            "available_high_level_mode_refs",
        )
        examples = require_string_list(
            partition.get("available_approved_example_refs", []),
            "available_approved_example_refs",
        )
        requested_modes = require_string_list(
            request.get("requested_high_level_mode_refs", []),
            "requested_high_level_mode_refs",
        )
        requested_examples = require_string_list(
            request.get("approved_example_refs", []), "approved_example_refs"
        )
        unknown_modes = set(requested_modes) - set(modes)
        unknown_examples = set(requested_examples) - set(examples)
        if unknown_modes:
            raise RetrievalContractError(
                "UNKNOWN_EXPRESSION_MODE", ",".join(sorted(unknown_modes))
            )
        if unknown_examples:
            raise RetrievalContractError(
                "UNKNOWN_EXAMPLE_REF", ",".join(sorted(unknown_examples))
            )
        return {
            "brand_expression_profile_candidate_ref": partition.get(
                "brand_expression_profile_candidate_ref"
            ),
            "available_high_level_mode_refs": modes,
            "available_approved_example_refs": examples,
            "requested_high_level_mode_refs": requested_modes,
            "approved_example_refs": requested_examples,
            "runtime_authoritative": False,
            "may_grant_fact_authorization_or_scope": False,
        }

    @staticmethod
    def _gap(
        code: str,
        next_action: str,
        reason: str,
        *,
        fact_kind: str | None = None,
    ) -> JsonObject:
        gap: JsonObject = {
            "code": code,
            "next_action": next_action,
            "plain_language_reason": reason,
        }
        if fact_kind is not None:
            gap["fact_kind"] = fact_kind
        return gap


__all__ = [
    "BrandFactRetrievalService",
    "IdentityAuthority",
    "RetrievalContractError",
    "RetrievalIndex",
    "TrustedScope",
    "canonical_json_bytes",
    "digest_object",
    "parse_timestamp",
]
