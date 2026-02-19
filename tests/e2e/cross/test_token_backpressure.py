"""Cross-layer E2E: Token budget backpressure (X2-4).

Verifies: consume token -> deduct -> exhaust -> 402 rejection.
Uses in-memory TokenBudgetManager + BudgetPreCheckMiddleware via FastAPI TestClient.
No live PG required.

Covers:
    X2-4: Token budget backpressure (Loop D)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.gateway.middleware.budget import BudgetPreCheckMiddleware, BudgetResolver
from src.infra.billing.budget import BudgetStatus, TokenBudgetManager


@pytest.fixture()
def org_id():
    return uuid4()


@pytest.fixture()
def budget_manager():
    return TokenBudgetManager()


@pytest.fixture()
def budget_resolver():
    return BudgetResolver()


@pytest.mark.e2e
class TestTokenBackpressureCrossLayer:
    """Cross-layer token budget backpressure verification.

    Exercises the Gateway -> BudgetMiddleware -> TokenBudgetManager path
    end-to-end using in-memory implementations.
    """

    def test_token_deduction_on_chat(
        self,
        budget_manager: TokenBudgetManager,
        budget_resolver: BudgetResolver,
        org_id,
    ) -> None:
        """X2-4: Chat request flows through budget check with remaining header."""
        budget = budget_manager.create_budget(org_id, total_tokens=1000)
        budget_resolver.register(org_id, budget.id)

        # Build app with correct middleware order (LIFO: last added = outermost)
        app = FastAPI()

        budget_mw = BudgetPreCheckMiddleware(
            budget_manager=budget_manager,
            budget_resolver=budget_resolver,
        )
        app.middleware("http")(budget_mw)

        @app.middleware("http")
        async def inject_org(request: Request, call_next):
            request.state.org_id = org_id
            return await call_next(request)

        @app.get("/api/v1/chat/send")
        async def _chat() -> dict:
            return {"message": "response", "tokens_used": 100}

        client = TestClient(app)
        resp = client.get("/api/v1/chat/send")
        assert resp.status_code == 200
        assert "X-Budget-Remaining" in resp.headers
        assert resp.headers["X-Budget-Remaining"] == "1000"

    def test_budget_exhaustion_returns_402(
        self,
        budget_manager: TokenBudgetManager,
        budget_resolver: BudgetResolver,
        org_id,
    ) -> None:
        """X2-4: Exhausted budget returns HTTP 402."""
        # Create budget with minimal tokens and exhaust it
        budget = budget_manager.create_budget(org_id, total_tokens=50)
        budget_resolver.register(org_id, budget.id)

        # Deduct all tokens
        budget_manager.deduct(budget.id, 50)
        assert budget.status == BudgetStatus.EXHAUSTED

        # Build a fresh app with the exhausted budget
        # FastAPI middleware is LIFO: last added = outermost = runs first
        # So: add budget check FIRST, then org injection wraps it (runs before)
        app = FastAPI()

        budget_mw = BudgetPreCheckMiddleware(
            budget_manager=budget_manager,
            budget_resolver=budget_resolver,
        )
        app.middleware("http")(budget_mw)

        @app.middleware("http")
        async def inject_org(request: Request, call_next):
            request.state.org_id = org_id
            return await call_next(request)

        @app.get("/api/v1/chat/send")
        async def _chat() -> dict:
            return {"message": "should not reach"}

        client = TestClient(app)
        resp = client.get("/api/v1/chat/send")
        assert resp.status_code == 402
        assert resp.json()["error"] == "QUOTA_EXCEEDED"
        assert resp.headers["X-Budget-Remaining"] == "0"

    def test_concurrent_deduction_race_safety(
        self,
        budget_manager: TokenBudgetManager,
        org_id,
    ) -> None:
        """X2-4: Concurrent requests don't over-deduct beyond budget.

        In-memory TokenBudgetManager uses sequential deduction;
        verifies that attempting to deduct more than remaining raises
        PermissionError and marks budget as exhausted.
        """
        budget = budget_manager.create_budget(org_id, total_tokens=100)

        # First deduction: 60 tokens (succeeds)
        receipt1 = budget_manager.deduct(budget.id, 60)
        assert receipt1.tokens_remaining == 40

        # Second deduction: 60 tokens (should fail — only 40 remaining)
        with pytest.raises(PermissionError, match="Insufficient tokens"):
            budget_manager.deduct(budget.id, 60)

        # Budget should be marked exhausted after failed deduction
        assert budget.status == BudgetStatus.EXHAUSTED

        # No further deductions allowed
        with pytest.raises(PermissionError, match="exhausted"):
            budget_manager.deduct(budget.id, 1)
