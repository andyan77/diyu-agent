"""Model Registry with circuit breaker and fallback chain.

Task card: T2-2
- Circuit breaker pattern for LLM provider resilience
- Automatic failover to backup model on primary failure
- Fallback latency < 2s

Architecture: delivery/phase2-runtime-config.yaml (llm section)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.ports.llm_call_port import ContentBlock, LLMCallPort, LLMResponse

logger = logging.getLogger(__name__)

# Circuit breaker states
_STATE_CLOSED = "closed"  # Normal operation
_STATE_OPEN = "open"  # Failing, reject calls
_STATE_HALF_OPEN = "half_open"  # Trying recovery


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""

    name: str
    models: list[str]
    default_model: str
    timeout_s: int = 30
    max_retries: int = 2


@dataclass
class CircuitState:
    """Circuit breaker state for a provider."""

    state: str = _STATE_CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    failure_threshold: int = 3
    recovery_timeout_s: float = 60.0


@dataclass
class ModelRegistry:
    """Registry of LLM providers with circuit breaker and fallback.

    Wraps an LLMCallPort and adds:
    - Per-provider circuit breaker
    - Automatic failover through fallback chain
    - Provider health tracking
    """

    adapter: LLMCallPort
    primary: str = "openai"
    fallback_chain: list[str] = field(default_factory=list)
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    _circuits: dict[str, CircuitState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in [self.primary, *self.fallback_chain]:
            if name not in self._circuits:
                self._circuits[name] = CircuitState()

    async def call(
        self,
        prompt: str,
        model_id: str = "",
        content_parts: list[ContentBlock] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Call LLM with automatic fallback on failure.

        Tries primary provider first, then each fallback in order.
        Uses circuit breaker to skip known-failed providers.

        Args:
            model_id: Target model. Empty string uses provider default.
        """
        chain = [self.primary, *self.fallback_chain]
        last_error: Exception | None = None

        for provider_name in chain:
            circuit = self._circuits.get(provider_name)
            if circuit is None:
                circuit = CircuitState()
                self._circuits[provider_name] = circuit

            if not self._is_available(circuit):
                logger.info("Skipping provider=%s (circuit open)", provider_name)
                continue

            config = self.providers.get(provider_name)
            resolved_model = model_id or (config.default_model if config else provider_name)

            try:
                response = await self.adapter.call(
                    prompt=prompt,
                    model_id=resolved_model,
                    content_parts=content_parts,
                    parameters=parameters,
                )
                self._record_success(circuit)
                return response

            except Exception as e:
                logger.warning(
                    "Provider %s failed: %s, trying next",
                    provider_name,
                    str(e)[:200],
                )
                self._record_failure(circuit)
                last_error = e

        msg = f"All providers in chain {chain} failed"
        raise RuntimeError(msg) from last_error

    def get_default_model(self, provider: str | None = None) -> str:
        """Get the default model for a provider."""
        name = provider or self.primary
        config = self.providers.get(name)
        return config.default_model if config else name

    def is_provider_available(self, provider: str) -> bool:
        """Check if a provider's circuit breaker allows calls."""
        circuit = self._circuits.get(provider)
        if circuit is None:
            return True
        return self._is_available(circuit)

    def reset_circuit(self, provider: str) -> None:
        """Manually reset a provider's circuit breaker."""
        self._circuits[provider] = CircuitState()

    def _is_available(self, circuit: CircuitState) -> bool:
        if circuit.state == _STATE_CLOSED:
            return True
        if circuit.state == _STATE_OPEN:
            elapsed = time.monotonic() - circuit.last_failure_time
            if elapsed >= circuit.recovery_timeout_s:
                circuit.state = _STATE_HALF_OPEN
                return True
            return False
        # half_open: allow one probe call
        return True

    def _record_success(self, circuit: CircuitState) -> None:
        circuit.state = _STATE_CLOSED
        circuit.failure_count = 0

    def _record_failure(self, circuit: CircuitState) -> None:
        circuit.failure_count += 1
        circuit.last_failure_time = time.monotonic()
        if circuit.failure_count >= circuit.failure_threshold:
            circuit.state = _STATE_OPEN
