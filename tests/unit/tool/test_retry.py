"""Tests for T4-2: Tool retry + exponential backoff.

Task card: T4-2
- Max 3 retries with exponential backoff: 100ms, 500ms, 2000ms
- Retries only on retriable exceptions
- Non-retriable exceptions propagate immediately
"""

from __future__ import annotations

import time

import pytest

from src.tool.resilience.retry import RetryExhaustedError, RetryPolicy, retry_with_backoff


class TestRetryPolicy:
    """RetryPolicy configuration."""

    def test_default_policy(self) -> None:
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.base_delay == 0.1
        assert policy.multiplier == 5.0
        assert policy.max_delay == 2.0

    def test_custom_policy(self) -> None:
        policy = RetryPolicy(max_retries=5, base_delay=0.5, multiplier=2.0, max_delay=10.0)
        assert policy.max_retries == 5

    def test_delay_schedule(self) -> None:
        policy = RetryPolicy(base_delay=0.1, multiplier=5.0, max_delay=2.0)
        assert policy.delay_for_attempt(0) == 0.1
        assert policy.delay_for_attempt(1) == 0.5
        assert policy.delay_for_attempt(2) == 2.0  # capped at max_delay
        assert policy.delay_for_attempt(3) == 2.0  # still capped


class TestRetryWithBackoff:
    """retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_succeeds_first_try(self) -> None:
        call_count = 0

        async def good() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_with_backoff(good)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self) -> None:
        call_count = 0

        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "recovered"

        policy = RetryPolicy(base_delay=0.001, multiplier=1.0, max_delay=0.01)
        result = await retry_with_backoff(flaky, policy=policy)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_after_max_retries(self) -> None:
        async def always_fail() -> str:
            raise ConnectionError("permanent")

        policy = RetryPolicy(max_retries=2, base_delay=0.001, multiplier=1.0, max_delay=0.01)
        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_with_backoff(always_fail, policy=policy)
        assert exc_info.value.attempts == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_non_retriable_not_retried(self) -> None:
        call_count = 0

        async def bad_input() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        policy = RetryPolicy(base_delay=0.001, multiplier=1.0, max_delay=0.01)
        with pytest.raises(ValueError, match="bad input"):
            await retry_with_backoff(
                bad_input,
                policy=policy,
                retriable_exceptions=(ConnectionError, TimeoutError),
            )
        assert call_count == 1  # no retries

    @pytest.mark.asyncio
    async def test_backoff_delays(self) -> None:
        """Verify that actual delays match the policy schedule."""
        call_count = 0
        timestamps: list[float] = []

        async def slow_recover() -> str:
            nonlocal call_count
            call_count += 1
            timestamps.append(time.monotonic())
            if call_count < 3:
                raise ConnectionError("retry me")
            return "done"

        policy = RetryPolicy(base_delay=0.05, multiplier=2.0, max_delay=1.0)
        await retry_with_backoff(slow_recover, policy=policy)
        assert call_count == 3
        # Check that delay between calls is roughly correct
        # First retry: ~50ms delay
        assert timestamps[1] - timestamps[0] >= 0.04
        # Second retry: ~100ms delay
        assert timestamps[2] - timestamps[1] >= 0.08
