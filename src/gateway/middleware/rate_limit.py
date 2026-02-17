"""Rate limiting middleware using sliding window counter.

Task card: G2-5
- Exceeding threshold -> 429 Too Many Requests
- Three tiers: tenant / user / API granularity
- Uses StoragePort (Redis in production) for counters

Architecture: 05-Gateway Section 6
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from uuid import UUID

    from fastapi import Request, Response

logger = logging.getLogger(__name__)

_EXEMPT_PATHS = frozenset({"/healthz", "/docs", "/openapi.json", "/redoc"})


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10


DEFAULT_LIMITS = RateLimitConfig(requests_per_minute=60, requests_per_hour=1000, burst_size=10)


class InMemoryRateLimiter:
    """In-memory sliding window rate limiter.

    Phase 2: in-memory counters. Production: Redis-backed via StoragePort.
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or DEFAULT_LIMITS
        self._windows: dict[str, list[float]] = {}

    def check(self, key: str) -> tuple[bool, int, int]:
        """Check if request is within rate limits.

        Args:
            key: Rate limit key (e.g., "org:{org_id}" or "user:{user_id}").

        Returns:
            Tuple of (allowed, remaining, retry_after_seconds).
        """
        now = time.monotonic()
        window_start = now - 60.0

        if key not in self._windows:
            self._windows[key] = []

        # Clean expired entries
        self._windows[key] = [t for t in self._windows[key] if t > window_start]

        count = len(self._windows[key])
        limit = self._config.requests_per_minute
        remaining = max(0, limit - count)

        if count >= limit:
            oldest = self._windows[key][0] if self._windows[key] else now
            retry_after = max(1, int(oldest + 60.0 - now))
            return False, 0, retry_after

        self._windows[key].append(now)
        return True, remaining - 1, 0

    def reset(self, key: str) -> None:
        """Reset rate limit counters for a key."""
        self._windows.pop(key, None)


class RateLimitMiddleware:
    """Callable middleware for request rate limiting.

    Returns 429 Too Many Requests when limit is exceeded.
    Adds standard rate limit headers to all responses.

    Usage with FastAPI:
        middleware = RateLimitMiddleware(limiter=limiter, config=config)
        app.middleware("http")(middleware)
    """

    def __init__(
        self,
        *,
        limiter: InMemoryRateLimiter | None = None,
        config: RateLimitConfig | None = None,
        exempt_paths: frozenset[str] | None = None,
    ) -> None:
        self._config = config or DEFAULT_LIMITS
        self._limiter = limiter or InMemoryRateLimiter(self._config)
        self._exempt_paths = exempt_paths or _EXEMPT_PATHS

    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if path in self._exempt_paths:
            return await call_next(request)

        # org_id is set by JWT middleware in request.state
        org_id: UUID | None = getattr(request.state, "org_id", None)
        if org_id is None:
            return await call_next(request)

        key = f"rl:org:{org_id}"
        allowed, remaining, retry_after = self._limiter.check(key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "RATE_LIMITED", "message": "Too many requests"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self._config.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
