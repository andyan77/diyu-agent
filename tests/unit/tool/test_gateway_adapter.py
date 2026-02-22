"""Tests for LiteLLM Gateway Adapter.

Task card: T2-1
Covers F-7 audit finding: test coverage for src/tool/llm/gateway_adapter.py

Uses DI adapter pattern (no unittest.mock, no monkeypatch).
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

from src.ports.llm_call_port import ContentBlock, LLMResponse
from src.tool.llm.gateway_adapter import LiteLLMGatewayAdapter

# ---------------------------------------------------------------------------
# DI fake: replaces litellm.acompletion via constructor injection
# ---------------------------------------------------------------------------


def _make_response(
    content: str | None = "Generated response",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    model: str = "gpt-4o",
    finish_reason: str = "stop",
    has_usage: bool = True,
) -> SimpleNamespace:
    """Build a fake LiteLLM response object using SimpleNamespace."""
    usage = (
        SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        if has_usage
        else None
    )
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=usage,
        model=model,
    )


class FakeACompletion:
    """Async callable that captures kwargs and returns a preset response.

    Implements the DI adapter pattern for testing LiteLLM acompletion calls.
    """

    def __init__(
        self,
        response: SimpleNamespace | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or _make_response()
        self.error = error
        self.call_kwargs: dict[str, Any] = {}
        self.call_count: int = 0

    async def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.call_kwargs = kwargs
        self.call_count += 1
        if self.error is not None:
            raise self.error
        return self.response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLiteLLMGatewayAdapter:
    """Test suite for LiteLLMGatewayAdapter."""

    def test_init_defaults(self) -> None:
        """Test initialization with default values."""
        adapter = LiteLLMGatewayAdapter()
        expected_model = os.environ.get("LLM_MODEL", "gpt-4o")
        assert adapter._default_model == expected_model
        assert adapter._timeout_s == 30
        assert adapter._max_retries == 2
        assert adapter._api_key is None
        assert adapter._base_url is None

    def test_init_custom_values(self) -> None:
        """Test initialization with custom values."""
        adapter = LiteLLMGatewayAdapter(
            default_model="gpt-4-turbo",
            timeout_s=60,
            max_retries=3,
            api_key="test-key",
            base_url="https://api.example.com",
        )
        assert adapter._default_model == "gpt-4-turbo"
        assert adapter._timeout_s == 60
        assert adapter._max_retries == 3
        assert adapter._api_key == "test-key"
        assert adapter._base_url == "https://api.example.com"

    # -- _build_messages tests (pure unit, no DI needed) --------------------

    def test_build_messages_text_only(self) -> None:
        """Test _build_messages with text-only prompt, no content_parts."""
        adapter = LiteLLMGatewayAdapter()
        messages = adapter._build_messages(prompt="Hello world", content_parts=None)

        assert messages == [{"role": "user", "content": "Hello world"}]

    def test_build_messages_prompt_with_text_blocks(self) -> None:
        """Test _build_messages with prompt + text content blocks."""
        adapter = LiteLLMGatewayAdapter()
        content_parts = [
            ContentBlock(type="text", text="Additional context"),
            ContentBlock(type="text", text="More information"),
        ]
        messages = adapter._build_messages(prompt="Main prompt", content_parts=content_parts)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert isinstance(content, list)
        assert len(content) == 3
        assert content[0] == {"type": "text", "text": "Main prompt"}
        assert content[1] == {"type": "text", "text": "Additional context"}
        assert content[2] == {"type": "text", "text": "More information"}

    def test_build_messages_image_block(self) -> None:
        """Test _build_messages with image content block."""
        adapter = LiteLLMGatewayAdapter()
        content_parts = [
            ContentBlock(
                type="image",
                media_id="https://example.com/image.jpg",
                text_fallback="An image",
            ),
        ]
        messages = adapter._build_messages(prompt="Analyze this", content_parts=content_parts)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0] == {"type": "text", "text": "Analyze this"}
        assert content[1] == {
            "type": "image_url",
            "image_url": {"url": "https://example.com/image.jpg"},
        }

    def test_build_messages_fallback_content_block(self) -> None:
        """Test _build_messages with fallback content block (no media_id)."""
        adapter = LiteLLMGatewayAdapter()
        content_parts = [
            ContentBlock(
                type="image",
                media_id=None,
                text="",
                text_fallback="Image fallback description",
            ),
            ContentBlock(
                type="audio",
                media_id=None,
                text="Some text",
                text_fallback="Audio fallback",
            ),
        ]
        messages = adapter._build_messages(prompt="Process this", content_parts=content_parts)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert isinstance(content, list)
        assert len(content) == 3
        assert content[0] == {"type": "text", "text": "Process this"}
        assert content[1] == {"type": "text", "text": "Image fallback description"}
        assert content[2] == {"type": "text", "text": "Audio fallback"}

    def test_build_messages_empty_prompt_with_blocks(self) -> None:
        """Test _build_messages with empty prompt but content blocks."""
        adapter = LiteLLMGatewayAdapter()
        content_parts = [
            ContentBlock(type="text", text="Only content block"),
        ]
        messages = adapter._build_messages(prompt="", content_parts=content_parts)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert isinstance(content, list)
        assert len(content) == 1
        assert content[0] == {"type": "text", "text": "Only content block"}

    # -- call() tests (DI adapter via acompletion_fn) -----------------------

    @pytest.mark.asyncio
    async def test_call_success(self) -> None:
        """Test call method success path."""
        fake = FakeACompletion()
        adapter = LiteLLMGatewayAdapter(default_model="gpt-4o", acompletion_fn=fake)

        result = await adapter.call(
            prompt="Test prompt",
            model_id="gpt-4o",
            content_parts=None,
            parameters={"temperature": 0.5, "max_tokens": 100},
        )

        assert isinstance(result, LLMResponse)
        assert result.text == "Generated response"
        assert result.tokens_used == {"input": 10, "output": 20}
        assert result.model_id == "gpt-4o"
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_call_with_custom_api_key_and_base_url(self) -> None:
        """Test call with custom api_key and base_url (verify openai/ prefix added)."""
        fake = FakeACompletion(
            response=_make_response(
                content="Response",
                prompt_tokens=5,
                completion_tokens=10,
                model="openai/gpt-3.5-turbo",
            ),
        )
        adapter = LiteLLMGatewayAdapter(
            api_key="custom-key",
            base_url="https://custom.example.com/v1",
            acompletion_fn=fake,
        )

        result = await adapter.call(
            prompt="Test",
            model_id="gpt-3.5-turbo",
        )

        assert fake.call_kwargs["model"] == "openai/gpt-3.5-turbo"
        assert fake.call_kwargs["api_key"] == "custom-key"
        assert fake.call_kwargs["api_base"] == "https://custom.example.com/v1"
        assert result.text == "Response"

    @pytest.mark.asyncio
    async def test_call_with_base_url_preserves_existing_prefix(self) -> None:
        """Test call with base_url preserves model prefix if already present."""
        fake = FakeACompletion(
            response=_make_response(
                content="Response",
                prompt_tokens=5,
                completion_tokens=10,
                model="anthropic/claude-3-opus",
            ),
        )
        adapter = LiteLLMGatewayAdapter(
            base_url="https://custom.example.com/v1",
            acompletion_fn=fake,
        )

        await adapter.call(
            prompt="Test",
            model_id="anthropic/claude-3-opus",
        )

        assert fake.call_kwargs["model"] == "anthropic/claude-3-opus"

    @pytest.mark.asyncio
    async def test_call_uses_default_model_when_empty(self) -> None:
        """Test call uses default model when model_id is empty."""
        fake = FakeACompletion(
            response=_make_response(
                content="Response",
                prompt_tokens=5,
                completion_tokens=10,
                model="gpt-4-turbo",
            ),
        )
        adapter = LiteLLMGatewayAdapter(
            default_model="gpt-4-turbo",
            acompletion_fn=fake,
        )

        await adapter.call(prompt="Test", model_id="")

        assert fake.call_kwargs["model"] == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_call_exception_reraise(self) -> None:
        """Test call re-raises exceptions from acompletion."""
        fake = FakeACompletion(error=ValueError("API Error"))
        adapter = LiteLLMGatewayAdapter(acompletion_fn=fake)

        with pytest.raises(ValueError, match="API Error"):
            await adapter.call(prompt="Test", model_id="gpt-4o")

    @pytest.mark.asyncio
    async def test_call_handles_missing_usage(self) -> None:
        """Test call handles missing usage data gracefully."""
        fake = FakeACompletion(
            response=_make_response(content="Response", has_usage=False),
        )
        adapter = LiteLLMGatewayAdapter(acompletion_fn=fake)

        result = await adapter.call(prompt="Test", model_id="gpt-4o")

        assert result.tokens_used == {"input": 0, "output": 0}

    @pytest.mark.asyncio
    async def test_call_handles_empty_content(self) -> None:
        """Test call handles empty message content."""
        fake = FakeACompletion(
            response=_make_response(
                content=None,
                prompt_tokens=5,
                completion_tokens=0,
            ),
        )
        adapter = LiteLLMGatewayAdapter(acompletion_fn=fake)

        result = await adapter.call(prompt="Test", model_id="gpt-4o")

        assert result.text == ""

    @pytest.mark.asyncio
    async def test_call_passes_parameters(self) -> None:
        """Test call passes parameters to acompletion."""
        fake = FakeACompletion(
            response=_make_response(
                content="Response",
                prompt_tokens=5,
                completion_tokens=10,
            ),
        )
        adapter = LiteLLMGatewayAdapter(
            timeout_s=45,
            max_retries=5,
            acompletion_fn=fake,
        )

        await adapter.call(
            prompt="Test",
            model_id="gpt-4o",
            parameters={"temperature": 0.9, "max_tokens": 200},
        )

        assert fake.call_kwargs["timeout"] == 45
        assert fake.call_kwargs["num_retries"] == 5
        assert fake.call_kwargs["temperature"] == 0.9
        assert fake.call_kwargs["max_tokens"] == 200

    @pytest.mark.asyncio
    async def test_call_default_temperature(self) -> None:
        """Test call uses default temperature when not specified."""
        fake = FakeACompletion(
            response=_make_response(
                content="Response",
                prompt_tokens=5,
                completion_tokens=10,
            ),
        )
        adapter = LiteLLMGatewayAdapter(acompletion_fn=fake)

        await adapter.call(prompt="Test", model_id="gpt-4o", parameters={})

        assert fake.call_kwargs["temperature"] == 0.7
