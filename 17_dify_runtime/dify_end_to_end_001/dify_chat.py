#!/usr/bin/env python3
"""Server-side Dify chat client with a conservative Package 7 budget."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from persistence import RuntimeRepository, digest_object


JsonObject = dict[str, Any]
MAXIMUM_CUMULATIVE_MODEL_CALLS = 1096


class DifyChatError(RuntimeError):
    """Fail-closed external chat transport error."""


class DifyChatClient:
    def __init__(
        self,
        *,
        base_url: str,
        app_api_token: str,
        repository: RuntimeRepository,
        timeout_seconds: int = 95,
        maximum_model_calls: int = 40,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("A valid Dify service API URL is required")
        if len(app_api_token) < 20:
            raise ValueError("A valid server-side Dify app token is required")
        if (
            maximum_model_calls < 1
            or maximum_model_calls > MAXIMUM_CUMULATIVE_MODEL_CALLS
        ):
            raise ValueError(
                "The Package 7 cumulative model-call limit must be between "
                f"1 and {MAXIMUM_CUMULATIVE_MODEL_CALLS}"
            )
        self.base_url = base_url.rstrip("/")
        self.app_api_token = app_api_token
        self.repository = repository
        self.timeout_seconds = timeout_seconds
        self.maximum_model_calls = maximum_model_calls

    def invoke(
        self,
        *,
        invocation_id: str,
        principal_id: str,
        conversation_scope: str,
        user_key: str,
        query: str,
        inputs: JsonObject,
        reuse_conversation: bool = True,
        recovery_run_id: str | None = None,
    ) -> JsonObject:
        self.repository.reserve_dify_invocation(
            invocation_id=invocation_id,
            principal_id=principal_id,
            model_call_upper_bound=1,
            maximum_model_calls=self.maximum_model_calls,
        )
        binding = (
            self.repository.dify_conversation(principal_id, conversation_scope)
            if reuse_conversation
            else None
        )
        effective_user_key = user_key if binding is None else binding[0]
        conversation_id = "" if binding is None else binding[1]
        payload = {
            "inputs": inputs,
            "query": query,
            "response_mode": "blocking",
            "conversation_id": conversation_id,
            "user": effective_user_key,
            "files": [],
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat-messages",
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.app_api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise DifyChatError("Dify response exceeded the accepted size")
                value = json.loads(body.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.repository.fail_dify_invocation(
                invocation_id,
                failure_class=type(exc).__name__,
            )
            raise DifyChatError("Dify chat transport failed") from exc
        response_conversation_id = value.get("conversation_id") if isinstance(value, dict) else None
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("answer"), str)
            or not isinstance(response_conversation_id, str)
            or not response_conversation_id
            or (conversation_id and response_conversation_id != conversation_id)
        ):
            self.repository.fail_dify_invocation(
                invocation_id,
                failure_class="INVALID_RESPONSE_CONTRACT",
            )
            raise DifyChatError("Dify chat response contract failed")
        metadata = value.get("metadata")
        usage = metadata.get("usage", {}) if isinstance(metadata, dict) else {}
        if not isinstance(usage, dict):
            usage = {}
        public_result = {"answer": value["answer"], "usage": usage}
        response_digest = digest_object(public_result)
        if recovery_run_id is not None:
            self.repository.stage_dify_response(
                invocation_id,
                run_id=recovery_run_id,
                account_id=conversation_scope,
                response_payload=public_result,
                response_digest=response_digest,
                dify_user_key=effective_user_key,
                conversation_id=response_conversation_id,
                persist_conversation=reuse_conversation,
            )
        self.repository.complete_dify_invocation(
            invocation_id,
            account_id=conversation_scope,
            usage=usage,
            response_digest=response_digest,
            dify_user_key=effective_user_key,
            conversation_id=response_conversation_id,
            persist_conversation=reuse_conversation,
        )
        return public_result

    def adopt_latest_conversation(
        self,
        *,
        principal_id: str,
        conversation_scope: str,
        user_key: str,
    ) -> JsonObject:
        """Adopt the latest conversation from this app without invoking a model."""

        query = urllib.parse.urlencode(
            {"user": user_key, "limit": 20, "sort_by": "-updated_at"}
        )
        request = urllib.request.Request(
            f"{self.base_url}/conversations?{query}",
            headers={
                "Authorization": f"Bearer {self.app_api_token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                value = json.loads(response.read(1_000_001).decode("utf-8"))
        except (
            urllib.error.URLError,
            TimeoutError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise DifyChatError("Dify conversation lookup failed") from exc
        rows = value.get("data") if isinstance(value, dict) else None
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            raise DifyChatError("No current-app Dify conversation is available")
        conversation_id = rows[0].get("id")
        if not isinstance(conversation_id, str) or not conversation_id:
            raise DifyChatError("Dify conversation lookup contract failed")
        self.repository.adopt_dify_conversation(
            principal_id=principal_id,
            account_id=conversation_scope,
            dify_user_key=user_key,
            conversation_id=conversation_id,
        )
        return {"adopted": True, "conversation_count_seen": len(rows)}
