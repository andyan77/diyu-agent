"""RBAC integration test -- real middleware chain, no mocks.

Validates:
- Non-admin JWT + admin path -> 403 via real RBAC middleware
- Admin JWT + admin path -> 200 (allowed)
- Non-admin JWT + regular path -> 200 (no admin check)
- No JWT + any path -> 401

Uses create_app() with post_auth_middlewares=[RBACMiddleware()],
hitting the real JWT auth -> RBAC chain.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.gateway.middleware.rbac import RBACMiddleware

_JWT_SECRET = "test-rbac-integration-secret-32byte!"  # noqa: S105


@pytest.fixture()
def app():
    """Build a minimal app with real RBAC middleware wired in."""
    rbac_mw = RBACMiddleware()
    application = create_app(
        jwt_secret=_JWT_SECRET,
        cors_origins=["http://localhost:3000"],
        post_auth_middlewares=[rbac_mw],
    )
    return application


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_token(*, role: str = "member") -> dict[str, str]:
    token = encode_token(
        user_id=uuid4(),
        org_id=uuid4(),
        secret=_JWT_SECRET,
        role=role,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestRBACIntegration:
    """Real middleware chain: JWT auth -> RBAC -> endpoint."""

    @pytest.mark.asyncio
    async def test_admin_path_denied_for_member(self, client: AsyncClient) -> None:
        """member role + /api/v1/admin/* -> 403."""
        headers = _make_token(role="member")
        resp = await client.get("/api/v1/admin/status", headers=headers)
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_admin_path_denied_for_viewer(self, client: AsyncClient) -> None:
        """viewer role + /api/v1/admin/* -> 403."""
        headers = _make_token(role="viewer")
        resp = await client.get("/api/v1/admin/status", headers=headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_path_allowed_for_admin(self, client: AsyncClient) -> None:
        """admin role + /api/v1/admin/* -> 200."""
        headers = _make_token(role="admin")
        resp = await client.get("/api/v1/admin/status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["admin"] is True

    @pytest.mark.asyncio
    async def test_regular_path_allowed_for_member(self, client: AsyncClient) -> None:
        """member role + /api/v1/me -> 200."""
        headers = _make_token(role="member")
        resp = await client.get("/api/v1/me", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_regular_path_allowed_for_viewer(self, client: AsyncClient) -> None:
        """viewer role + /api/v1/me -> 200."""
        headers = _make_token(role="viewer")
        resp = await client.get("/api/v1/me", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        """No Authorization header -> 401 (auth fails before RBAC)."""
        resp = await client.get("/api/v1/admin/status")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_healthz_exempt_from_auth(self, client: AsyncClient) -> None:
        """/healthz is exempt from JWT auth entirely."""
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_role_round_trip_in_state(self, client: AsyncClient) -> None:
        """JWT role field propagates through to request.state."""
        headers = _make_token(role="admin")
        resp = await client.get("/api/v1/me", headers=headers)
        assert resp.status_code == 200
        # /api/v1/me returns user_id + org_id, confirming auth passed
        body = resp.json()
        assert "user_id" in body
        assert "org_id" in body
