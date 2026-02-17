"""Tests for Rate limiting middleware (G2-5).

Acceptance: pytest tests/unit/gateway/test_rate_limit.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.gateway.middleware.rate_limit import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitMiddleware,
)

_JWT_SECRET = "test-secret-for-g2-5-rate-limit"  # noqa: S105


@pytest.fixture()
def test_user():
    return {"user_id": uuid4(), "org_id": uuid4()}


@pytest.fixture()
def auth_headers(test_user):
    token = encode_token(
        user_id=test_user["user_id"],
        org_id=test_user["org_id"],
        secret=_JWT_SECRET,
    )
    return {"Authorization": f"Bearer {token}"}


class TestInMemoryRateLimiter:
    """Unit tests for the limiter logic."""

    def test_allows_within_limit(self):
        limiter = InMemoryRateLimiter(RateLimitConfig(requests_per_minute=5))
        for _ in range(5):
            allowed, _remaining, retry_after = limiter.check("key1")
            assert allowed is True
            assert retry_after == 0

    def test_blocks_over_limit(self):
        limiter = InMemoryRateLimiter(RateLimitConfig(requests_per_minute=3))
        for _ in range(3):
            limiter.check("key1")

        allowed, remaining, retry_after = limiter.check("key1")
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_different_keys_independent(self):
        limiter = InMemoryRateLimiter(RateLimitConfig(requests_per_minute=2))
        limiter.check("org:a")
        limiter.check("org:a")

        allowed_a, _, _ = limiter.check("org:a")
        allowed_b, _, _ = limiter.check("org:b")

        assert allowed_a is False
        assert allowed_b is True

    def test_reset_clears_counter(self):
        limiter = InMemoryRateLimiter(RateLimitConfig(requests_per_minute=1))
        limiter.check("key1")
        allowed, _, _ = limiter.check("key1")
        assert allowed is False

        limiter.reset("key1")
        allowed, _, _ = limiter.check("key1")
        assert allowed is True

    def test_remaining_decrements(self):
        limiter = InMemoryRateLimiter(RateLimitConfig(requests_per_minute=5))
        _, remaining, _ = limiter.check("key1")
        assert remaining == 4
        _, remaining, _ = limiter.check("key1")
        assert remaining == 3


class TestRateLimitMiddleware:
    """Integration tests for the middleware."""

    @pytest.fixture()
    async def client_with_limit(self):
        config = RateLimitConfig(requests_per_minute=5)
        limiter = InMemoryRateLimiter(config)
        middleware = RateLimitMiddleware(limiter=limiter, config=config)
        app = create_app(
            jwt_secret=_JWT_SECRET,
            post_auth_middlewares=[middleware],
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_within_limit(self, client_with_limit: AsyncClient, auth_headers):
        resp = await client_with_limit.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        assert "x-ratelimit-limit" in resp.headers
        assert "x-ratelimit-remaining" in resp.headers

    @pytest.mark.asyncio
    async def test_exceeds_limit_returns_429(self, client_with_limit: AsyncClient, auth_headers):
        for _ in range(5):
            await client_with_limit.get("/api/v1/me", headers=auth_headers)

        resp = await client_with_limit.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 429
        data = resp.json()
        assert data["error"] == "RATE_LIMITED"
        assert "retry-after" in resp.headers

    @pytest.mark.asyncio
    async def test_exempt_paths_not_limited(self, client_with_limit: AsyncClient):
        for _ in range(10):
            resp = await client_with_limit.get("/healthz")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client_with_limit: AsyncClient, auth_headers):
        resp = await client_with_limit.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["x-ratelimit-limit"] == "5"
        remaining = int(resp.headers["x-ratelimit-remaining"])
        assert remaining >= 0
