"""Tests for S4-1: Skill circuit breaker.

Task card: S4-1
- States: CLOSED → OPEN → HALF_OPEN → CLOSED
- 5 consecutive failures → OPEN (reject all calls)
- After cooldown period → HALF_OPEN (allow one probe)
- Probe succeeds → CLOSED; probe fails → OPEN again
"""

from __future__ import annotations

import pytest

from src.skill.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


@pytest.fixture
def cb() -> CircuitBreaker:
    """Circuit breaker with threshold=5, cooldown=0.01s for fast tests."""
    return CircuitBreaker(failure_threshold=5, cooldown_seconds=0.01)


class TestCircuitState:
    """Three states exist."""

    def test_states(self) -> None:
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestInitialState:
    def test_starts_closed(self, cb: CircuitBreaker) -> None:
        assert cb.state == CircuitState.CLOSED

    def test_failure_count_zero(self, cb: CircuitBreaker) -> None:
        assert cb.failure_count == 0


class TestClosedState:
    """In CLOSED state, calls pass through."""

    def test_record_success_stays_closed(self, cb: CircuitBreaker) -> None:
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_record_failure_increments(self, cb: CircuitBreaker) -> None:
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED

    def test_threshold_failures_opens(self, cb: CircuitBreaker) -> None:
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self, cb: CircuitBreaker) -> None:
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0


class TestOpenState:
    """In OPEN state, calls are rejected."""

    def test_allow_request_false(self, cb: CircuitBreaker) -> None:
        for _ in range(5):
            cb.record_failure()
        assert not cb.allow_request()

    def test_raises_on_check(self, cb: CircuitBreaker) -> None:
        for _ in range(5):
            cb.record_failure()
        with pytest.raises(CircuitOpenError):
            cb.check()


class TestHalfOpenState:
    """After cooldown, transitions to HALF_OPEN."""

    @pytest.mark.asyncio
    async def test_transitions_to_half_open(self) -> None:
        import asyncio

        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=0.01)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.02)
        assert cb.allow_request()  # transitions to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_success_in_half_open_closes(self) -> None:
        import asyncio

        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=0.01)
        for _ in range(5):
            cb.record_failure()
        await asyncio.sleep(0.02)
        cb.allow_request()  # → HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failure_in_half_open_opens(self) -> None:
        import asyncio

        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=0.01)
        for _ in range(5):
            cb.record_failure()
        await asyncio.sleep(0.02)
        cb.allow_request()  # → HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
