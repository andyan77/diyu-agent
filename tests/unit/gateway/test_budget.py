"""Tests for Token budget pre-check middleware (G2-4).

Acceptance: pytest tests/unit/gateway/test_budget.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.gateway.middleware.budget import BudgetPreCheckMiddleware, BudgetResolver
from src.infra.billing.budget import BudgetStatus, TokenBudgetManager

_JWT_SECRET = "test-secret-for-g2-4-budget-check"  # noqa: S105


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


@pytest.fixture()
def budget_manager():
    return TokenBudgetManager()


@pytest.fixture()
def budget_resolver():
    return BudgetResolver()


@pytest.fixture()
async def client_with_budget(budget_manager, budget_resolver):
    middleware = BudgetPreCheckMiddleware(
        budget_manager=budget_manager,
        budget_resolver=budget_resolver,
    )
    app = create_app(
        jwt_secret=_JWT_SECRET,
        post_auth_middlewares=[middleware],
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestBudgetPreCheck:
    """Budget middleware tests."""

    @pytest.mark.asyncio
    async def test_active_budget_passes(
        self,
        client_with_budget: AsyncClient,
        auth_headers,
        budget_manager,
        budget_resolver,
        test_user,
    ):
        budget = budget_manager.create_budget(test_user["org_id"], 100_000)
        budget_resolver.register(test_user["org_id"], budget.id)

        resp = await client_with_budget.get("/healthz")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_exhausted_budget_returns_402(
        self,
        client_with_budget: AsyncClient,
        auth_headers,
        budget_manager,
        budget_resolver,
        test_user,
    ):
        budget = budget_manager.create_budget(test_user["org_id"], 100)
        budget_resolver.register(test_user["org_id"], budget.id)

        # Exhaust the budget
        budget_manager.deduct(budget.id, 100)
        assert budget.status == BudgetStatus.EXHAUSTED

        resp = await client_with_budget.get(
            "/api/v1/me",
            headers=auth_headers,
        )
        assert resp.status_code == 402
        assert resp.json()["error"] == "QUOTA_EXCEEDED"
        assert resp.headers.get("x-budget-remaining") == "0"

    @pytest.mark.asyncio
    async def test_budget_remaining_header(
        self,
        client_with_budget: AsyncClient,
        auth_headers,
        budget_manager,
        budget_resolver,
        test_user,
    ):
        budget = budget_manager.create_budget(test_user["org_id"], 50_000)
        budget_resolver.register(test_user["org_id"], budget.id)

        resp = await client_with_budget.get(
            "/api/v1/me",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers.get("x-budget-remaining") == "50000"

    @pytest.mark.asyncio
    async def test_exempt_paths_skip_budget_check(
        self,
        client_with_budget: AsyncClient,
    ):
        resp = await client_with_budget.get("/healthz")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_budget_configured_passes(
        self,
        client_with_budget: AsyncClient,
        auth_headers,
    ):
        # No budget registered for this org
        resp = await client_with_budget.get(
            "/api/v1/me",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestBudgetResolver:
    """BudgetResolver unit tests."""

    def test_register_and_resolve(self):
        resolver = BudgetResolver()
        org_id = uuid4()
        budget_id = uuid4()
        resolver.register(org_id, budget_id)
        assert resolver.resolve(org_id) == budget_id

    def test_resolve_unknown_org(self):
        resolver = BudgetResolver()
        assert resolver.resolve(uuid4()) is None
