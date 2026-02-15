"""LLMCallPort - LLM invocation interface.

Encapsulates all LLM API calls. v3.6 expanded with content_parts
for multimodal support.
Day-1 implementation: Stub returning fixed text.
Real implementation: LLM Gateway + Model Registry (LiteLLM).

See: docs/architecture/00-*.md Section 12.3
     ADR-046 (content_parts Expand)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContentBlock:
    """Content block for multimodal input (v3.6 Schema v1.1)."""

    type: str  # "text" | "image" | "audio" | "document"
    text: str = ""
    media_id: str | None = None
    text_fallback: str = ""  # LAW: mandatory for non-text blocks
    mime_type: str | None = None


@dataclass(frozen=True)
class LLMResponse:
    """Response from LLM invocation."""

    text: str
    tokens_used: dict[str, int] = field(default_factory=dict)  # {input, output}
    model_id: str = ""
    finish_reason: str = "stop"  # "stop" | "length" | "error"


class LLMCallPort(ABC):
    """Port: LLM invocation operations."""

    @abstractmethod
    async def call(
        self,
        prompt: str,
        model_id: str,
        content_parts: list[ContentBlock] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Invoke an LLM with prompt and optional multimodal content.

        Args:
            prompt: Text prompt.
            model_id: Target model identifier.
            content_parts: Optional multimodal content blocks (v3.6).
            parameters: Optional model parameters (temperature, etc.).

        Returns:
            LLMResponse with generated text and metadata.
        """
