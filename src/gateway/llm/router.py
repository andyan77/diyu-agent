"""LLM Gateway router -- unified routing to LLM providers.

Task card: G2-3
- Route to different LLM providers via LiteLLM
- Billing audit trail
- Model validation against org's allowed models

Architecture: 05-Gateway Section 5
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    from uuid import UUID

    from src.ports.llm_call_port import LLMCallPort
    from src.tool.llm.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


class LLMCallRequest(BaseModel):
    """Request model for LLM call."""

    prompt: str
    model_id: str = ""
    parameters: dict[str, Any] | None = None


class LLMCallResponse(BaseModel):
    """Response model for LLM call."""

    text: str
    tokens_used: dict[str, int]
    model_id: str
    finish_reason: str


class ModelListResponse(BaseModel):
    """Response listing available models."""

    models: list[dict[str, str]]


# Default model registry (will be loaded from config in production)
_DEFAULT_MODELS: list[dict[str, str]] = [
    {"id": "gpt-4o", "provider": "openai", "name": "GPT-4o"},
    {"id": "gpt-4o-mini", "provider": "openai", "name": "GPT-4o Mini"},
    {"id": "claude-sonnet-4-20250514", "provider": "anthropic", "name": "Claude Sonnet 4"},
]


def create_llm_router(
    *,
    llm_adapter: LLMCallPort,
    usage_tracker: UsageTracker | None = None,
) -> APIRouter:
    """Create LLM gateway router with dependency injection."""
    router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

    @router.get("/models", response_model=ModelListResponse)
    async def list_models(request: Request) -> ModelListResponse:
        """List available LLM models."""
        return ModelListResponse(models=_DEFAULT_MODELS)

    @router.post("/call", response_model=LLMCallResponse)
    async def call_llm(
        body: LLMCallRequest,
        request: Request,
    ) -> LLMCallResponse:
        """Direct LLM call via gateway (admin/debug use)."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id

        model_id = body.model_id or "gpt-4o"

        try:
            response = await llm_adapter.call(
                prompt=body.prompt,
                model_id=model_id,
                parameters=body.parameters,
            )
        except Exception:
            logger.exception("LLM call failed model=%s org=%s", model_id, org_id)
            raise HTTPException(status_code=502, detail="LLM provider unavailable") from None

        # Record usage for billing
        if usage_tracker:
            usage_tracker.record_usage(
                org_id=org_id,
                user_id=user_id,
                model_id=response.model_id or model_id,
                input_tokens=response.tokens_used.get("input", 0),
                output_tokens=response.tokens_used.get("output", 0),
            )

        return LLMCallResponse(
            text=response.text,
            tokens_used=response.tokens_used,
            model_id=response.model_id or model_id,
            finish_reason=response.finish_reason,
        )

    return router
