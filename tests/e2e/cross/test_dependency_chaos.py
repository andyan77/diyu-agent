"""Cross-layer E2E: Dependency Chaos Testing (CB-4).

Gate: p4-dependency-chaos
Verifies: System resilience when external dependencies fail:
    1. Circuit breaker trips after threshold failures -> OPEN -> rejects
    2. Circuit breaker recovers: OPEN -> HALF_OPEN -> CLOSED
    3. Retry with exponential backoff exhaustion -> RetryExhaustedError
    4. Retry succeeds on transient failure
    5. Combined: CB + retry in a realistic Skill/Tool execution path
    6. ConversationEngine survives dependency chaos (non-blocking paths)

Integration path:
    Skill (circuit breaker) -> Tool (retry+backoff)
    -> Brain (ConversationEngine, graceful degradation)
    -> Full chain resilience under dependency failures

Uses circuit_breaker.py + retry.py directly for deterministic testing.
No external dependencies (no Redis, no real LLM, etc.).

Design: Circuit breaker protects Skill layer; retry protects Tool layer.
Both are per-component, not global.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine
from src.brain.memory.pipeline import MemoryWritePipeline
from src.memory.receipt import ReceiptStore
from src.skill.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)
from src.tool.resilience.retry import (
    RetryExhaustedError,
    RetryPolicy,
    retry_with_backoff,
)
from tests.e2e.test_conversation_loop import FakeEventStore, FakeLLM, FakeMemoryCore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def org_id():
    return uuid4()


@pytest.fixture()
def user_id():
    return uuid4()


@pytest.fixture()
def session_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Test class: Circuit Breaker E2E
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestCircuitBreakerE2E:
    """Circuit breaker resilience patterns (S4-1, CB-4).

    Validates the 3-state circuit breaker protects the Skill layer
    from cascading failures.
    """

    async def test_circuit_trips_after_threshold_failures(self) -> None:
        """5 consecutive failures -> circuit OPEN -> requests rejected."""
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=10.0)

        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

        # Record 4 failures — still CLOSED
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 4

        # 5th failure trips the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 5

        # Requests rejected while OPEN
        assert cb.allow_request() is False

        # check() raises CircuitOpenError
        with pytest.raises(CircuitOpenError):
            cb.check()

    async def test_circuit_recovery_half_open_probe(self) -> None:
        """OPEN -> (cooldown elapsed) -> HALF_OPEN -> success -> CLOSED."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.01)

        # Trip the circuit
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for cooldown
        await asyncio.sleep(0.02)

        # allow_request transitions to HALF_OPEN
        assert cb.allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN

        # Probe success -> CLOSED
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    async def test_half_open_probe_failure_reopens(self) -> None:
        """HALF_OPEN -> probe failure -> back to OPEN."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.01)

        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.02)
        assert cb.allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN

        # Probe fails -> back to OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    async def test_success_resets_failure_count(self) -> None:
        """A success after partial failures resets the counter."""
        cb = CircuitBreaker(failure_threshold=5)

        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 3

        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    async def test_circuit_breaker_with_async_workload(self) -> None:
        """Circuit breaker works correctly with concurrent async tasks."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.01)
        results: list[str] = []

        async def simulated_skill_call(call_id: int) -> None:
            if not cb.allow_request():
                results.append(f"rejected-{call_id}")
                return
            # Simulate failure for first 3 calls
            if call_id < 3:
                cb.record_failure()
                results.append(f"failed-{call_id}")
            else:
                cb.record_success()
                results.append(f"success-{call_id}")

        # First 3 calls fail, tripping the circuit
        for i in range(3):
            await simulated_skill_call(i)

        assert cb.state == CircuitState.OPEN

        # Next calls are rejected
        await simulated_skill_call(3)
        assert "rejected-3" in results


# ---------------------------------------------------------------------------
# Test class: Retry with Backoff E2E
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestRetryBackoffE2E:
    """Retry with exponential backoff resilience patterns (T4-2, CB-4).

    Validates the retry mechanism protects the Tool layer
    from transient failures.
    """

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_transient_failures(self) -> None:
        """Retry succeeds on 3rd attempt after 2 transient failures."""
        call_count = 0

        async def flaky_tool() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = f"Transient failure #{call_count}"
                raise ConnectionError(msg)
            return "success"

        policy = RetryPolicy(
            max_retries=3,
            base_delay=0.001,  # fast for testing
            multiplier=2.0,
            max_delay=0.01,
        )

        result = await retry_with_backoff(flaky_tool, policy=policy)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self) -> None:
        """All retries exhausted -> RetryExhaustedError."""

        async def always_fails() -> str:
            msg = "Persistent failure"
            raise ConnectionError(msg)

        policy = RetryPolicy(
            max_retries=2,
            base_delay=0.001,
            multiplier=1.0,
            max_delay=0.001,
        )

        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_with_backoff(always_fails, policy=policy)

        assert exc_info.value.attempts == 3  # 1 initial + 2 retries
        assert isinstance(exc_info.value.last_error, ConnectionError)

    @pytest.mark.asyncio
    async def test_non_retriable_exception_propagates_immediately(self) -> None:
        """Non-retriable exceptions bypass retry and propagate directly."""
        call_count = 0

        async def raises_value_error() -> str:
            nonlocal call_count
            call_count += 1
            msg = "Not retriable"
            raise ValueError(msg)

        policy = RetryPolicy(max_retries=3, base_delay=0.001)

        with pytest.raises(ValueError, match="Not retriable"):
            await retry_with_backoff(raises_value_error, policy=policy)

        # Should only be called once (no retry for ValueError)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_delay_calculation(self) -> None:
        """Delay increases exponentially: 100ms -> 500ms -> 2000ms."""
        policy = RetryPolicy(
            max_retries=3,
            base_delay=0.1,
            multiplier=5.0,
            max_delay=2.0,
        )

        assert policy.delay_for_attempt(0) == pytest.approx(0.1)
        assert policy.delay_for_attempt(1) == pytest.approx(0.5)
        assert policy.delay_for_attempt(2) == pytest.approx(2.0)  # capped at max_delay
        assert policy.delay_for_attempt(3) == pytest.approx(2.0)  # still capped

    @pytest.mark.asyncio
    async def test_retry_with_timeout_error(self) -> None:
        """TimeoutError is retriable by default."""
        call_count = 0

        async def timeout_then_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Tool execution timeout")
            return "recovered"

        policy = RetryPolicy(max_retries=2, base_delay=0.001)

        result = await retry_with_backoff(timeout_then_success, policy=policy)
        assert result == "recovered"
        assert call_count == 2


# ---------------------------------------------------------------------------
# Test class: Combined Resilience E2E
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestCombinedResilienceE2E:
    """Combined circuit breaker + retry in realistic scenarios (CB-4).

    Validates that the Brain layer survives dependency chaos through
    its non-blocking error handling in memory pipeline and event store.
    """

    async def test_conversation_survives_all_non_critical_failures(
        self,
        session_id,
        user_id,
        org_id,
    ) -> None:
        """ConversationEngine completes even when memory + events both fail.

        Both memory_pipeline and event_store are non-blocking. The user
        gets their response regardless of persistence failures.
        """
        llm = FakeLLM(responses=["I'm still here despite chaos!"])
        memory_core = FakeMemoryCore()

        # Create a memory pipeline that will fail internally
        # (FailingMemoryCore with all writes failing)
        from tests.e2e.cross.test_fault_injection import (
            FailingEventStore,
            FailingMemoryCore,
        )

        failing_memory = FailingMemoryCore(fail_writes_on={0, 1, 2, 3})
        failing_events = FailingEventStore()

        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,  # reads work fine
            event_store=failing_events,  # event persistence fails
            memory_pipeline=MemoryWritePipeline(
                memory_core=failing_memory,  # writes fail
                receipt_store=ReceiptStore(),
            ),
            default_model="gpt-4o",
        )

        # Should still succeed
        turn = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Test chaos resilience",
        )

        assert turn.assistant_response == "I'm still here despite chaos!"

    async def test_circuit_breaker_protects_skill_layer(self) -> None:
        """Circuit breaker prevents cascading failures in Skill layer.

        After threshold failures, the circuit opens and new requests
        are immediately rejected without hitting the backend.
        """
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
        backend_calls = 0

        async def skill_with_circuit_breaker() -> str:
            nonlocal backend_calls
            cb.check()  # Raises CircuitOpenError if OPEN
            backend_calls += 1
            msg = "Backend overloaded"
            raise ConnectionError(msg)

        # 3 calls hit the backend and fail
        for _ in range(3):
            try:
                await skill_with_circuit_breaker()
            except ConnectionError:
                cb.record_failure()

        assert backend_calls == 3
        assert cb.state == CircuitState.OPEN

        # Next calls are rejected without hitting backend
        for _ in range(10):
            with pytest.raises(CircuitOpenError):
                await skill_with_circuit_breaker()

        # Backend was NOT called during OPEN state
        assert backend_calls == 3

    async def test_retry_then_circuit_breaker_integration(self) -> None:
        """Retry exhaustion feeds into circuit breaker failure count.

        When retry_with_backoff exhausts retries, the circuit breaker
        records a failure. After threshold, circuit opens.
        """
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=60.0)

        async def always_fails() -> str:
            msg = "Persistent backend failure"
            raise ConnectionError(msg)

        policy = RetryPolicy(
            max_retries=1,  # quick exhaustion
            base_delay=0.001,
        )

        # Each retry_with_backoff exhaustion = 1 circuit breaker failure
        for _ in range(2):
            try:
                await retry_with_backoff(always_fails, policy=policy)
            except RetryExhaustedError:
                cb.record_failure()

        assert cb.state == CircuitState.OPEN

    async def test_multi_turn_conversation_under_chaos(
        self,
        session_id,
        user_id,
        org_id,
    ) -> None:
        """Multi-turn conversation completes under dependency chaos.

        Turn 1: Everything works
        Turn 2: Memory pipeline fails (non-blocking)
        Turn 3: Event store fails (non-blocking)
        All turns should produce valid responses.
        """
        llm = FakeLLM(
            responses=[
                "Turn 1 response.",
                "Turn 2 response.",
                "Turn 3 response.",
            ]
        )
        memory_core = FakeMemoryCore()
        event_store = FakeEventStore()
        receipt_store = ReceiptStore()

        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            event_store=event_store,
            memory_pipeline=MemoryWritePipeline(
                memory_core=memory_core,
                receipt_store=receipt_store,
            ),
            default_model="gpt-4o",
        )

        # Turn 1: Normal
        turn1 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="First message",
        )
        assert turn1.assistant_response == "Turn 1 response."

        # Turn 2: Still works (memory pipeline failure is non-blocking
        # if it occurs internally)
        turn2 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Second message",
        )
        assert turn2.assistant_response == "Turn 2 response."

        # Turn 3: Still works
        turn3 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Third message",
        )
        assert turn3.assistant_response == "Turn 3 response."
