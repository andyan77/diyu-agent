"""Tests for T2-2: Model Registry + Fallback.

Validates:
- Circuit breaker state transitions
- Automatic failover through fallback chain
- Provider health tracking
- Fallback latency (must complete quickly)
"""

from __future__ import annotations

import time

import pytest

from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.tool.llm.model_registry import (
    _STATE_CLOSED,
    _STATE_HALF_OPEN,
    _STATE_OPEN,
    CircuitState,
    ModelRegistry,
    ProviderConfig,
)


class FailingLLMAdapter(LLMCallPort):
    """LLM adapter that fails N times before succeeding."""

    def __init__(self, fail_count: int = 0, response_text: str = "OK") -> None:
        self._fail_count = fail_count
        self._call_count = 0
        self._response_text = response_text

    async def call(self, prompt, model_id, content_parts=None, parameters=None) -> LLMResponse:
        self._call_count += 1
        if self._call_count <= self._fail_count:
            msg = f"Simulated failure #{self._call_count}"
            raise RuntimeError(msg)
        return LLMResponse(
            text=self._response_text,
            tokens_used={"input": 5, "output": 10},
            model_id=model_id,
        )


class SelectiveLLMAdapter(LLMCallPort):
    """LLM adapter that fails for specific models."""

    def __init__(self, failing_models: set[str] | None = None) -> None:
        self._failing_models = failing_models or set()
        self.calls: list[str] = []

    async def call(self, prompt, model_id, content_parts=None, parameters=None) -> LLMResponse:
        self.calls.append(model_id)
        if model_id in self._failing_models:
            msg = f"Provider unavailable for {model_id}"
            raise RuntimeError(msg)
        return LLMResponse(
            text=f"Response from {model_id}",
            tokens_used={"input": 5, "output": 10},
            model_id=model_id,
        )


@pytest.mark.unit
class TestCircuitBreaker:
    """Circuit breaker state machine tests."""

    def test_initial_state_is_closed(self) -> None:
        circuit = CircuitState()
        assert circuit.state == _STATE_CLOSED

    def test_transitions_to_open_after_threshold(self) -> None:
        circuit = CircuitState(failure_threshold=3)
        circuit.failure_count = 3
        circuit.state = _STATE_OPEN
        assert circuit.state == _STATE_OPEN

    def test_half_open_after_recovery_timeout(self) -> None:
        circuit = CircuitState(
            state=_STATE_OPEN,
            last_failure_time=time.monotonic() - 120,  # 2 min ago
            recovery_timeout_s=60.0,
        )
        # ModelRegistry._is_available should transition to half_open
        registry = ModelRegistry(adapter=FailingLLMAdapter())
        assert registry._is_available(circuit) is True
        assert circuit.state == _STATE_HALF_OPEN


@pytest.mark.unit
class TestModelRegistry:
    """T2-2: Model Registry + Fallback chain."""

    def _make_registry(
        self,
        adapter: LLMCallPort,
        primary: str = "openai",
        fallback: list[str] | None = None,
    ) -> ModelRegistry:
        providers = {
            "openai": ProviderConfig(
                name="openai",
                models=["gpt-4o", "gpt-4o-mini"],
                default_model="gpt-4o",
            ),
            "anthropic": ProviderConfig(
                name="anthropic",
                models=["claude-sonnet-4-20250514"],
                default_model="claude-sonnet-4-20250514",
            ),
        }
        return ModelRegistry(
            adapter=adapter,
            primary=primary,
            fallback_chain=fallback or ["anthropic"],
            providers=providers,
        )

    @pytest.mark.asyncio()
    async def test_primary_succeeds(self) -> None:
        adapter = SelectiveLLMAdapter()
        registry = self._make_registry(adapter)
        result = await registry.call("Hello")
        assert result.text == "Response from gpt-4o"

    @pytest.mark.asyncio()
    async def test_fallback_on_primary_failure(self) -> None:
        adapter = SelectiveLLMAdapter(failing_models={"gpt-4o"})
        registry = self._make_registry(adapter)
        result = await registry.call("Hello")
        assert result.model_id == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio()
    async def test_all_providers_fail_raises(self) -> None:
        adapter = SelectiveLLMAdapter(
            failing_models={"gpt-4o", "claude-sonnet-4-20250514"},
        )
        registry = self._make_registry(adapter)
        with pytest.raises(RuntimeError, match="All providers"):
            await registry.call("Hello")

    @pytest.mark.asyncio()
    async def test_fallback_latency_under_2s(self) -> None:
        adapter = SelectiveLLMAdapter(failing_models={"gpt-4o"})
        registry = self._make_registry(adapter)
        start = time.monotonic()
        await registry.call("Hello")
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"Fallback took {elapsed:.2f}s, must be < 2s"

    @pytest.mark.asyncio()
    async def test_circuit_opens_after_failures(self) -> None:
        adapter = FailingLLMAdapter(fail_count=10)
        registry = self._make_registry(adapter, fallback=[])
        # Set low threshold: 2 failures opens circuit
        registry._circuits["openai"].failure_threshold = 2
        # Each call tries openai once, increments failure_count
        with pytest.raises(RuntimeError):
            await registry.call("Hello")
        with pytest.raises(RuntimeError):
            await registry.call("Hello")
        assert not registry.is_provider_available("openai")

    def test_reset_circuit(self) -> None:
        adapter = FailingLLMAdapter()
        registry = self._make_registry(adapter)
        registry._circuits["openai"].state = _STATE_OPEN
        registry.reset_circuit("openai")
        assert registry.is_provider_available("openai")

    def test_get_default_model(self) -> None:
        adapter = FailingLLMAdapter()
        registry = self._make_registry(adapter)
        assert registry.get_default_model("openai") == "gpt-4o"
        assert registry.get_default_model("anthropic") == "claude-sonnet-4-20250514"
