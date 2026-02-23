"""Circuit breaker for Skill execution.

Task card: S4-1
States: CLOSED → OPEN → HALF_OPEN → CLOSED
- failure_threshold consecutive failures → OPEN
- After cooldown_seconds → HALF_OPEN (probe one request)
- Probe success → CLOSED; probe failure → OPEN again

Architecture: Section 3 (Skill Layer Resilience)
"""

from __future__ import annotations

import enum
import time


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a call is attempted on an OPEN circuit."""


class CircuitBreaker:
    """Three-state circuit breaker."""

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float = 0.0

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def allow_request(self) -> bool:
        """Check if a request should be allowed.

        Returns True if allowed, False if circuit is OPEN.
        Transitions OPEN → HALF_OPEN after cooldown.
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.HALF_OPEN:
            return True

        # OPEN: check if cooldown has elapsed
        if time.monotonic() - self._opened_at >= self._cooldown_seconds:
            self._state = CircuitState.HALF_OPEN
            return True

        return False

    def check(self) -> None:
        """Raise CircuitOpenError if circuit is OPEN."""
        if not self.allow_request():
            raise CircuitOpenError(f"Circuit is OPEN (failures={self._failure_count})")

    def record_success(self) -> None:
        """Record a successful call. Resets failure count, closes circuit."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call. May open circuit."""
        self._failure_count += 1

        if self._state == CircuitState.HALF_OPEN:
            # Probe failed — back to OPEN
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            return

        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
