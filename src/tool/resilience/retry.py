"""Retry with exponential backoff for Tool execution.

Task card: T4-2
- Max 3 retries with exponential backoff: 100ms → 500ms → 2000ms
- Only retry on retriable exceptions (ConnectionError, TimeoutError, OSError)
- Non-retriable exceptions propagate immediately

Architecture: Section 4 (Tool Layer Resilience)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")

# Default retriable exception types
_DEFAULT_RETRIABLE = (ConnectionError, TimeoutError, OSError)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_error: Exception) -> None:
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_error}")
        self.attempts = attempts
        self.last_error = last_error


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 0.1  # 100ms
    multiplier: float = 5.0  # 100ms → 500ms → 2500ms
    max_delay: float = 2.0  # Cap at 2s

    def delay_for_attempt(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt (0-indexed)."""
        delay = self.base_delay * (self.multiplier**attempt)
        return min(delay, self.max_delay)


async def retry_with_backoff(  # noqa: UP047
    fn: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy | None = None,
    retriable_exceptions: tuple[type[Exception], ...] = _DEFAULT_RETRIABLE,
) -> T:
    """Execute an async callable with retry and exponential backoff.

    Args:
        fn: Async callable (no arguments) to execute.
        policy: Retry policy configuration.
        retriable_exceptions: Exception types that trigger a retry.

    Returns:
        Result of fn().

    Raises:
        RetryExhaustedError: If all retries are exhausted.
        Exception: Non-retriable exceptions propagate immediately.
    """
    p = policy or RetryPolicy()
    last_error: Exception | None = None

    for attempt in range(1 + p.max_retries):
        try:
            return await fn()
        except retriable_exceptions as exc:
            last_error = exc
            if attempt < p.max_retries:
                delay = p.delay_for_attempt(attempt)
                await asyncio.sleep(delay)
        except Exception:
            raise

    assert last_error is not None
    raise RetryExhaustedError(attempts=1 + p.max_retries, last_error=last_error)
