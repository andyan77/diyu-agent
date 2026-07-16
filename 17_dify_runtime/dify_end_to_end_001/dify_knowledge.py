#!/usr/bin/env python3
"""Trusted Dify Knowledge retrieval client with server-owned metadata filters."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


JsonObject = dict[str, Any]


class KnowledgeRetrievalError(RuntimeError):
    """Raised when the isolated Dify knowledge endpoint cannot be trusted."""


class KnowledgeClient(Protocol):
    def retrieve(self, *, query: str, scope: JsonObject, query_at: str, limit: int) -> JsonObject: ...


def _scope_token(value: str | None) -> str:
    return f"|{value if value is not None else 'NONE'}|"


@dataclass(frozen=True)
class DifyKnowledgeClient:
    base_url: str
    dataset_api_token: str
    dataset_id: str
    timeout_seconds: float = 20.0

    def _conditions(self, scope: JsonObject, query_at: str) -> list[JsonObject]:
        normalized = query_at[:-1] + "+00:00" if query_at.endswith("Z") else query_at
        query_timestamp = datetime.fromisoformat(normalized).timestamp()
        return [
            {"name": "tenant_id", "comparison_operator": "is", "value": scope["tenant_id"]},
            {"name": "brand_id", "comparison_operator": "is", "value": scope["brand_id"]},
            {"name": "status", "comparison_operator": "is", "value": "ACTIVE"},
            {
                "name": "authorization_state",
                "comparison_operator": "is",
                "value": "GRANTED",
            },
            {
                "name": "account_scope",
                "comparison_operator": "contains",
                "value": _scope_token(str(scope["content_account_id"])),
            },
            {
                "name": "organization_scope",
                "comparison_operator": "contains",
                "value": _scope_token(str(scope["organization_id"])),
            },
            {
                "name": "store_scope",
                "comparison_operator": "contains",
                "value": _scope_token(scope.get("store_id")),
            },
            {"name": "valid_from", "comparison_operator": "before", "value": query_timestamp},
            {"name": "valid_until", "comparison_operator": "after", "value": query_timestamp},
            {"name": "revocation_state", "comparison_operator": "is", "value": "CLEAR"},
        ]

    def retrieve(self, *, query: str, scope: JsonObject, query_at: str, limit: int) -> JsonObject:
        if not query.strip():
            return {"results": [], "usage": {}, "prefilter_applied": True}
        payload = {
            "query": query.strip(),
            "retrieval_model": {
                "search_method": "keyword_search",
                "top_k": limit,
                "reranking_enable": False,
                "reranking_model": None,
                "score_threshold_enabled": False,
                "score_threshold": None,
                "metadata_filtering_conditions": {
                    "logical_operator": "and",
                    "conditions": self._conditions(scope, query_at),
                },
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/datasets/{self.dataset_id}/retrieve",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.dataset_api_token}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise KnowledgeRetrievalError("Dify knowledge retrieval failed") from exc
        if not isinstance(parsed, dict) or not isinstance(parsed.get("records"), list):
            raise KnowledgeRetrievalError("Dify knowledge response is invalid")
        results: list[JsonObject] = []
        for raw in parsed["records"]:
            if not isinstance(raw, dict) or not isinstance(raw.get("segment"), dict):
                raise KnowledgeRetrievalError("Dify knowledge record is invalid")
            segment = raw["segment"]
            document = segment.get("document")
            metadata = document.get("doc_metadata") if isinstance(document, dict) else None
            if not isinstance(metadata, dict):
                raise KnowledgeRetrievalError("Dify knowledge metadata is invalid")
            results.append(
                {
                    "metadata": {
                        **metadata,
                        "document_id": segment.get("document_id"),
                        "score": raw.get("score"),
                    },
                    "content": segment.get("content"),
                    "title": document.get("name"),
                }
            )
        return {"results": results, "usage": {}, "prefilter_applied": True}
