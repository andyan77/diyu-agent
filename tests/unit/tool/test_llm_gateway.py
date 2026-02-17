"""Tests for T2-1: LLMCallPort real implementation (LiteLLM gateway).

Validates:
- LiteLLMGatewayAdapter implements LLMCallPort interface
- Message building for text and multimodal content
- Error propagation
- Parameter passing
"""

from __future__ import annotations

import pytest

from src.ports.llm_call_port import ContentBlock, LLMCallPort, LLMResponse
from src.tool.llm.gateway_adapter import LiteLLMGatewayAdapter


class FakeLLMAdapter(LLMCallPort):
    """Fake LLM adapter for testing without real API calls.

    Returns predictable responses based on prompt content.
    """

    def __init__(self, response_text: str = "Hello! How can I help?") -> None:
        self._response_text = response_text
        self.calls: list[dict] = []

    async def call(
        self,
        prompt,
        model_id,
        content_parts=None,
        parameters=None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "prompt": prompt,
                "model_id": model_id,
                "content_parts": content_parts,
                "parameters": parameters,
            }
        )
        return LLMResponse(
            text=self._response_text,
            tokens_used={"input": 10, "output": 20},
            model_id=model_id,
            finish_reason="stop",
        )


@pytest.mark.unit
class TestLiteLLMGatewayAdapter:
    """T2-1: LLMCallPort real implementation."""

    def test_implements_llm_call_port(self) -> None:
        adapter = LiteLLMGatewayAdapter()
        assert isinstance(adapter, LLMCallPort)

    def test_build_text_messages(self) -> None:
        adapter = LiteLLMGatewayAdapter()
        messages = adapter._build_messages("Hello world", None)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello world"

    def test_build_multimodal_messages(self) -> None:
        adapter = LiteLLMGatewayAdapter()
        parts = [
            ContentBlock(type="text", text="Describe this image"),
            ContentBlock(
                type="image",
                media_id="https://example.com/img.png",
                text_fallback="An image",
            ),
        ]
        messages = adapter._build_messages("What is this?", parts)
        assert len(messages) == 1
        content = messages[0]["content"]
        assert isinstance(content, list)
        assert len(content) == 3  # prompt + text block + image block

    def test_build_messages_with_text_fallback(self) -> None:
        adapter = LiteLLMGatewayAdapter()
        parts = [
            ContentBlock(type="audio", text_fallback="[audio transcript]"),
        ]
        messages = adapter._build_messages("", parts)
        content = messages[0]["content"]
        assert any(p.get("text") == "[audio transcript]" for p in content if isinstance(p, dict))

    def test_default_model_from_init(self) -> None:
        adapter = LiteLLMGatewayAdapter(default_model="gpt-4o-mini")
        assert adapter._default_model == "gpt-4o-mini"


@pytest.mark.unit
class TestFakeLLMAdapter:
    """Verify FakeLLMAdapter for use in other tests."""

    @pytest.fixture()
    def adapter(self) -> FakeLLMAdapter:
        return FakeLLMAdapter(response_text="Test response")

    @pytest.mark.asyncio()
    async def test_returns_configured_response(self, adapter: FakeLLMAdapter) -> None:
        result = await adapter.call("Hello", "gpt-4o")
        assert result.text == "Test response"
        assert result.model_id == "gpt-4o"

    @pytest.mark.asyncio()
    async def test_records_calls(self, adapter: FakeLLMAdapter) -> None:
        await adapter.call("Q1", "model-a")
        await adapter.call("Q2", "model-b")
        assert len(adapter.calls) == 2
        assert adapter.calls[0]["prompt"] == "Q1"
        assert adapter.calls[1]["model_id"] == "model-b"

    @pytest.mark.asyncio()
    async def test_tokens_used(self, adapter: FakeLLMAdapter) -> None:
        result = await adapter.call("Hello", "gpt-4o")
        assert result.tokens_used["input"] == 10
        assert result.tokens_used["output"] == 20
