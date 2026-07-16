#!/usr/bin/env python3
"""Package 5-compatible retrieval backed by one Dify Knowledge truth."""

from __future__ import annotations

import copy
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy import select

from dify_knowledge import KnowledgeClient, KnowledgeRetrievalError
from persistence import RuntimeRepository
from runtime_models import RuntimeAuthorization, RuntimeNarrativeFragment


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_5_ROOT = REPOSITORY_ROOT / "15_brand_retrieval/brand_fact_retrieval_001"
if str(PACKAGE_5_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_5_ROOT))

from brand_fact_retrieval import (  # type: ignore[import-not-found]  # noqa: E402
    BrandFactRetrievalService,
    IdentityAuthority,
    RetrievalContractError,
    RetrievalIndex,
    parse_timestamp,
)


class RuntimeBrandFactRetrievalService(BrandFactRetrievalService):
    """Keep Package 5 result semantics while replacing narrative ranking only."""

    def __init__(
        self,
        repository: RuntimeRepository,
        knowledge_client: KnowledgeClient,
    ) -> None:
        self.repository = repository
        self.knowledge_client = knowledge_client
        active = repository.setting("active_runtime_brand")
        identity = self._identity_authority(
            repository.setting(str(active["identity_setting_key"]))
        )
        package_index = RetrievalIndex.from_package(PACKAGE_5_ROOT)
        runtime_index = RetrievalIndex(
            fragments=(),
            facts=repository.precise_facts(),
            dispositions=package_index.dispositions,
            expression_candidates=package_index.expression_candidates,
            data_version_digest=package_index.data_version_digest,
        )
        self._dispositions = package_index.dispositions
        self._expression_candidates = package_index.expression_candidates
        self._data_version_digest = package_index.data_version_digest
        super().__init__(identity, runtime_index)

    @staticmethod
    def _identity_authority(root: JsonObject) -> IdentityAuthority:
        def keyed(rows: object, key: str) -> dict[str, JsonObject]:
            if not isinstance(rows, list):
                raise RetrievalContractError("IDENTITY_INVALID", key)
            return {str(row[key]): copy.deepcopy(row) for row in rows if isinstance(row, dict)}

        tenant = root.get("tenant")
        if not isinstance(tenant, dict):
            raise RetrievalContractError("IDENTITY_INVALID", "tenant")
        return IdentityAuthority(
            tenant_id=str(tenant["tenant_id"]),
            brand_id=str(tenant["brand_id"]),
            principals=keyed(root.get("login_principals"), "principal_id"),
            organizations=keyed(root.get("organizations"), "organization_id"),
            stores=keyed(root.get("stores"), "store_id"),
            accounts=keyed(root.get("content_accounts"), "account_id"),
            grants=keyed(root.get("authorization_grants"), "authorization_id"),
        )

    def retrieve(
        self,
        request: Mapping[str, Any],
        *,
        principal_id: str,
        content_account_id: str,
        query_at: str,
    ) -> JsonObject:
        request_copy = copy.deepcopy(dict(request))
        query = request_copy.get("query_text", "")
        if not isinstance(query, str):
            raise RetrievalContractError("INVALID_REQUEST", "query_text")
        limit = request_copy.get("max_fragments", 5)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise RetrievalContractError("INVALID_REQUEST", "max_fragments")
        scope = self.authority.resolve_scope(principal_id, content_account_id)
        scope_payload = {
            "tenant_id": scope.tenant_id,
            "brand_id": scope.brand_id,
            "principal_id": scope.principal_id,
            "content_account_id": scope.content_account_id,
            "organization_id": scope.organization_id,
            "store_id": scope.store_id,
        }
        knowledge = self.knowledge_client.retrieve(
            query=query,
            scope=scope_payload,
            query_at=query_at,
            limit=limit,
        )
        fragments, postcheck = self._postcheck_results(knowledge["results"], scope_payload, query_at)

        self.index = RetrievalIndex(
            fragments=(),
            facts=self.repository.precise_facts(),
            dispositions=self._dispositions,
            expression_candidates=self._expression_candidates,
            data_version_digest=self._data_version_digest,
        )
        request_copy["query_text"] = ""
        request_copy["max_fragments"] = limit
        base = super().retrieve(
            request_copy,
            principal_id=principal_id,
            content_account_id=content_account_id,
            query_at=query_at,
        )
        base["scoped_retrieval_fragments"] = fragments
        base["gaps"] = [
            gap for gap in base["gaps"] if gap.get("code") != "QUERY_OR_FACT_REQUEST_REQUIRED"
        ]
        if query.strip() and not fragments:
            base["gaps"].append(
                {
                    "code": "MATERIAL_MISSING_FOR_SCOPE",
                    "action_type": "COLLECT_MATERIAL",
                    "detail": "No relevant authorized narrative material exists for the resolved account scope.",
                }
            )
        base["retrieval_audit"] = {
            "formal_narrative_truth": "DIFY_KNOWLEDGE_BASE",
            "trusted_metadata_prefilter_before_ranking": bool(knowledge.get("prefilter_applied")),
            "ranked_result_count": len(knowledge["results"]),
            "postcheck": postcheck,
            "exact_fact_resolution": base.get("retrieval_audit", {}).get("fact_audit", {}),
            "exact_fact_authoritative_metadata_refreshed": True,
        }
        return base

    def _postcheck_results(
        self,
        raw_results: object,
        scope: JsonObject,
        query_at: str,
    ) -> tuple[list[JsonObject], JsonObject]:
        if not isinstance(raw_results, list):
            raise KnowledgeRetrievalError("Dify knowledge results are invalid")
        accepted: list[JsonObject] = []
        rejected: list[str] = []
        now = parse_timestamp(query_at)
        with self.repository.sessions() as session:
            for raw in raw_results:
                metadata = raw.get("metadata") if isinstance(raw, dict) else None
                document_id = metadata.get("document_id") if isinstance(metadata, dict) else None
                if not isinstance(document_id, str):
                    rejected.append("MISSING_DOCUMENT_ID")
                    continue
                row = session.scalar(
                    select(RuntimeNarrativeFragment).where(
                        RuntimeNarrativeFragment.dify_document_id == document_id
                    )
                )
                reason = self._postcheck_row(session, row, scope, now, raw)
                if reason is not None:
                    rejected.append(reason)
                    continue
                if row is None:
                    raise RuntimeError("unreachable")
                accepted.append(copy.deepcopy(row.payload))
        return accepted, {
            "authoritative_metadata_recheck": True,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "rejected_reasons": sorted(rejected),
            "ranking_order_preserved": True,
        }

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _postcheck_row(
        session: Any,
        row: RuntimeNarrativeFragment | None,
        scope: JsonObject,
        now: datetime,
        raw: JsonObject,
    ) -> str | None:
        if row is None:
            return "UNKNOWN_DOCUMENT"
        payload = row.payload
        raw_content = raw.get("content")
        if not isinstance(raw_content, str):
            return "MISSING_CONTENT"
        normalized_content = raw_content.replace("\r\n", "\n").replace("\r", "\n").strip()
        if hashlib.sha256(normalized_content.encode("utf-8")).hexdigest() != row.content_digest:
            return "INDEX_CONTENT_DRIFT"
        if (
            row.tenant_id != scope["tenant_id"]
            or row.brand_id != scope["brand_id"]
            or row.status != "ACTIVE"
            or row.authorization_state != "GRANTED"
            or row.revocation_ref is not None
            or RuntimeBrandFactRetrievalService._aware(row.valid_from) > now
            or RuntimeBrandFactRetrievalService._aware(row.valid_until) < now
        ):
            return "RECORD_SCOPE_OR_STATE_INVALID"
        if (
            scope["content_account_id"] not in payload.get("applicable_content_account_ids", [])
            or scope["organization_id"] not in payload.get("applicable_organization_ids", [])
            or scope.get("store_id") not in payload.get("applicable_store_ids", [])
        ):
            return "TARGET_SCOPE_INVALID"
        grant = session.get(RuntimeAuthorization, row.authorization_ref)
        if (
            grant is None
            or grant.status != "GRANTED"
            or RuntimeBrandFactRetrievalService._aware(grant.valid_from) > now
            or RuntimeBrandFactRetrievalService._aware(grant.valid_until) < now
        ):
            return "AUTHORIZATION_INVALID"
        grant_payload = grant.payload
        if (
            scope["organization_id"] not in grant_payload.get("permitted_organization_ids", [])
            or scope.get("store_id") not in grant_payload.get("permitted_store_ids", [])
            or scope["content_account_id"]
            not in grant_payload.get("permitted_content_account_ids", [])
        ):
            return "GRANT_SCOPE_INVALID"
        return None
