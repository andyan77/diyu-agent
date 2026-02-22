"""Composition root integration test (M6).

Verifies that build_app() wires all layers correctly:
  - All expected P2 + P3 routes are mounted
  - Authenticated requests reach real handlers (not 404)
  - Unauthenticated requests get 401 (not 404)

No external services required — engine is created lazily and never
actually connects during these tests.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.gateway.middleware.auth import encode_token

_JWT_SECRET = "composition-root-test-secret-key-32b"  # noqa: S105


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required env vars for build_app().

    Uses a real postgresql+asyncpg URL — the engine is created but never
    actually connects during these tests since knowledge admin uses the
    in-memory KnowledgeWriteAdapter and auth endpoints are exempt.
    """
    monkeypatch.setenv("JWT_SECRET_KEY", _JWT_SECRET)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    # asyncpg engine creation succeeds without a live DB (lazy connect)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test:test@localhost:25432/test_composition",
    )


@pytest.fixture()
def app():
    """Build app fresh for each test."""
    from src.main import build_app

    return build_app()


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    user_id = uuid4()
    org_id = uuid4()
    token = encode_token(
        user_id=user_id,
        org_id=org_id,
        secret=_JWT_SECRET,
        role="admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestCompositionRoot:
    """Verify build_app() assembles all layers correctly."""

    @pytest.mark.asyncio
    async def test_all_routes_mounted(self, app) -> None:
        """All expected route patterns exist in the app."""
        route_paths = set()
        for route in app.routes:
            if hasattr(route, "path"):
                route_paths.add(route.path)
            # Include sub-routes from routers
            if hasattr(route, "routes"):
                for sub in route.routes:
                    if hasattr(sub, "path"):
                        route_paths.add(sub.path)

        # Spot-check critical routes
        critical = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/admin/auth/login",
            "/api/v1/conversations/",
            "/api/v1/skills/",
            "/api/v1/admin/knowledge/",
        ]
        for path in critical:
            assert path in route_paths, f"Route {path} not mounted"

    @pytest.mark.asyncio
    async def test_unauthenticated_protected_routes_return_401(self, client: AsyncClient) -> None:
        """Protected routes return 401 without JWT (not 404)."""
        protected = [
            ("GET", "/api/v1/conversations/"),
            ("GET", "/api/v1/skills/"),
            ("GET", "/api/v1/admin/knowledge/"),
        ]
        for method, path in protected:
            resp = await client.request(method, path)
            assert resp.status_code == 401, (
                f"{method} {path} returned {resp.status_code}, expected 401"
            )

    @pytest.mark.asyncio
    async def test_auth_routes_exempt_from_jwt(self, client: AsyncClient) -> None:
        """Auth routes are accessible without JWT (return 422 for missing body, not 401)."""
        resp = await client.post("/api/v1/auth/login")
        assert resp.status_code == 422, f"Login returned {resp.status_code}, expected 422"

    @pytest.mark.asyncio
    async def test_admin_auth_login_exempt_from_jwt(self, client: AsyncClient) -> None:
        """Admin auth login route is exempt from JWT (return 422 for missing body, not 401)."""
        resp = await client.post("/api/v1/admin/auth/login")
        assert resp.status_code == 422, f"Admin login returned {resp.status_code}, expected 422"

    @pytest.mark.asyncio
    async def test_authenticated_knowledge_admin_crud(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Knowledge admin CRUD endpoints work with valid JWT."""
        # GET list
        resp = await client.get("/api/v1/admin/knowledge/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "total" in data

        # POST create
        resp = await client.post(
            "/api/v1/admin/knowledge/",
            headers=auth_headers,
            json={
                "entity_type": "product",
                "properties": {"name": "Test Product"},
            },
        )
        assert resp.status_code == 201
        created = resp.json()
        assert created["entity_type"] == "product"
        entry_id = created["entry_id"]

        # GET single
        resp = await client.get(
            f"/api/v1/admin/knowledge/{entry_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # PUT update
        resp = await client.put(
            f"/api/v1/admin/knowledge/{entry_id}",
            headers=auth_headers,
            json={"properties": {"name": "Updated Product"}},
        )
        assert resp.status_code == 200

        # DELETE
        resp = await client.delete(
            f"/api/v1/admin/knowledge/{entry_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_knowledge_status_change(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """PATCH /status endpoint changes entry status."""
        # Create entry first
        resp = await client.post(
            "/api/v1/admin/knowledge/",
            headers=auth_headers,
            json={"entity_type": "product", "properties": {"name": "Status Test"}},
        )
        assert resp.status_code == 201
        entry_id = resp.json()["entry_id"]

        # Change status to published
        resp = await client.patch(
            f"/api/v1/admin/knowledge/{entry_id}/status",
            headers=auth_headers,
            json={"status": "published"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

        # Verify status persisted
        resp = await client.get(
            f"/api/v1/admin/knowledge/{entry_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["properties"].get("status") == "published"

    @pytest.mark.asyncio
    async def test_knowledge_review_action(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """POST /review endpoint performs review action."""
        # Create entry first
        resp = await client.post(
            "/api/v1/admin/knowledge/",
            headers=auth_headers,
            json={"entity_type": "article", "properties": {"title": "Review Test"}},
        )
        assert resp.status_code == 201
        entry_id = resp.json()["entry_id"]

        # Approve the entry
        resp = await client.post(
            f"/api/v1/admin/knowledge/{entry_id}/review",
            headers=auth_headers,
            json={"action": "approve", "comment": "Looks good"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "approve"
        assert data["new_status"] == "published"

    @pytest.mark.asyncio
    async def test_knowledge_status_invalid_value(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Invalid status value returns 422."""
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = await client.patch(
            f"/api/v1/admin/knowledge/{fake_id}/status",
            headers=auth_headers,
            json={"status": "invalid_status"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_knowledge_review_invalid_action(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Invalid review action returns 422."""
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = await client.post(
            f"/api/v1/admin/knowledge/{fake_id}/review",
            headers=auth_headers,
            json={"action": "invalid_action"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_skill_list_returns_registered_skills(
        self, client: AsyncClient, auth_headers: dict[str, str], app
    ) -> None:
        """After startup bootstrap, skill list endpoint returns registered skills."""
        # Bootstrap skills directly (lifespan handles this in production,
        # but also tries Neo4j/Qdrant connect which isn't available in tests)
        from src.main import _bootstrap_skill_registry

        await _bootstrap_skill_registry(app.state.skill_registry)

        resp = await client.get("/api/v1/skills/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        skills = data["skills"]
        # Should have at least content_writer and merchandising
        assert len(skills) >= 2
        skill_ids = [s["skill_id"] for s in skills]
        assert "content_writer" in skill_ids
        assert "merchandising" in skill_ids

    @pytest.mark.asyncio
    async def test_healthz_exempt(self, client: AsyncClient) -> None:
        """Health check endpoint is exempt from auth."""
        resp = await client.get("/healthz")
        assert resp.status_code == 200
