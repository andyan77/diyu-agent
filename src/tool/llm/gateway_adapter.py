"""LLMCallPort real implementation via LiteLLM.

Task card: T2-1
- Replace Stub with real LLM provider calls via LiteLLM
- Supports OpenAI, Anthropic, DeepSeek via unified interface
- Token metering write to records

Architecture: Section 12.3 (LLMCallPort)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import litellm

from src.ports.llm_call_port import ContentBlock, LLMCallPort, LLMResponse

logger = logging.getLogger(__name__)


class LiteLLMGatewayAdapter(LLMCallPort):
    """LiteLLM-backed implementation of LLMCallPort.

    Routes LLM calls through LiteLLM for unified multi-provider access.
    Supports OpenAI, Anthropic, and other providers configured in
    delivery/phase2-runtime-config.yaml.
    """

    def __init__(
        self,
        *,
        default_model: str = "",
        timeout_s: int = 30,
        max_retries: int = 2,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._default_model = default_model or os.environ.get("LLM_MODEL", "gpt-4o")
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._api_key = api_key
        self._base_url = base_url

        litellm.drop_params = True

    async def call(
        self,
        prompt: str,
        model_id: str,
        content_parts: list[ContentBlock] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Invoke LLM via LiteLLM.

        Constructs messages from prompt and optional content_parts,
        then calls the specified model through LiteLLM's unified API.
        """
        model = model_id or self._default_model
        params = parameters or {}

        messages = self._build_messages(prompt, content_parts)

        optional_params: dict[str, Any] = {}
        if self._api_key:
            optional_params["api_key"] = self._api_key
        if self._base_url:
            optional_params["api_base"] = self._base_url

        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                timeout=self._timeout_s,
                num_retries=self._max_retries,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens"),
                **optional_params,
            )

            text = response.choices[0].message.content or ""
            usage = response.usage
            tokens_used = {
                "input": usage.prompt_tokens if usage else 0,
                "output": usage.completion_tokens if usage else 0,
            }
            finish_reason = response.choices[0].finish_reason or "stop"

            return LLMResponse(
                text=text,
                tokens_used=tokens_used,
                model_id=response.model or model,
                finish_reason=finish_reason,
            )

        except Exception:
            logger.exception("LLM call failed for model=%s", model)
            raise

    def _build_messages(
        self,
        prompt: str,
        content_parts: list[ContentBlock] | None,
    ) -> list[dict[str, Any]]:
        """Build LiteLLM messages from prompt and optional content_parts."""
        if not content_parts:
            return [{"role": "user", "content": prompt}]

        parts: list[dict[str, Any]] = []
        if prompt:
            parts.append({"type": "text", "text": prompt})

        for block in content_parts:
            if block.type == "text":
                parts.append({"type": "text", "text": block.text})
            elif block.type == "image" and block.media_id:
                parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": block.media_id},
                    }
                )
            else:
                parts.append({"type": "text", "text": block.text_fallback or block.text})

        return [{"role": "user", "content": parts}]
