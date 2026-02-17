"""Token budget pre-check middleware.

Task card: G2-4
- Budget exhausted -> 402 + X-Budget-Remaining header
- 402 vs 429 semantic distinction (budget vs rate limit)

Architecture: 05-Gateway Section 6, ADR-047
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from uuid import UUID

    from fastapi import Request, Response

    from src.infra.billing.budget import TokenBudgetManager

logger = logging.getLogger(__name__)

_EXEMPT_PATHS = frozenset({"/healthz", "/docs", "/openapi.json", "/redoc"})


class BudgetResolver:
    """Resolves org_id to budget_id.

    In-memory mapping for Phase 2; production uses DB lookup.
    """

    def __init__(self) -> None:
        self._org_budgets: dict[UUID, UUID] = {}

    def register(self, org_id: UUID, budget_id: UUID) -> None:
        """Register a budget for an organization."""
        self._org_budgets[org_id] = budget_id

    def resolve(self, org_id: UUID) -> UUID | None:
        """Resolve org_id to budget_id."""
        return self._org_budgets.get(org_id)


class BudgetPreCheckMiddleware:
    """Callable middleware that checks token budget before request processing.

    Returns 402 Payment Required when budget is exhausted.
    Adds X-Budget-Remaining header to all responses.

    Usage with FastAPI:
        middleware = BudgetPreCheckMiddleware(budget_manager=mgr, budget_resolver=resolver)
        app.middleware("http")(middleware)
    """

    def __init__(
        self,
        *,
        budget_manager: TokenBudgetManager,
        budget_resolver: BudgetResolver | None = None,
        exempt_paths: frozenset[str] | None = None,
    ) -> None:
        self._budget_manager = budget_manager
        self._budget_resolver = budget_resolver
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

        # Resolve budget for org
        budget = None
        if self._budget_resolver:
            budget_id = self._budget_resolver.resolve(org_id)
            if budget_id:
                try:
                    budget = self._budget_manager.check_budget(budget_id)
                except KeyError:
                    budget = None

        if budget is not None and budget.status.value == "exhausted":
            return JSONResponse(
                status_code=402,
                content={"error": "QUOTA_EXCEEDED", "message": "Token budget exhausted"},
                headers={"X-Budget-Remaining": "0"},
            )

        response = await call_next(request)

        # Add budget header to response
        remaining = str(budget.remaining_tokens) if budget else "unknown"
        response.headers["X-Budget-Remaining"] = remaining

        return response
