"""Token budget management for LLM usage billing.

Task card: I2-3
- LLM call -> token metering -> usage_budgets deduction -> reject on exhaustion
- Billing error = 0 (hard requirement)

Architecture: ADR-047, 06 Section 1.5
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


class BudgetStatus(enum.Enum):
    """Budget lifecycle states."""

    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    SUSPENDED = "suspended"


@dataclass
class Budget:
    """Token budget for an organization."""

    id: UUID
    org_id: UUID
    total_tokens: int
    used_tokens: int = 0
    status: BudgetStatus = BudgetStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def remaining_tokens(self) -> int:
        return self.total_tokens - self.used_tokens


@dataclass(frozen=True)
class DeductionReceipt:
    """Receipt for a token deduction."""

    receipt_id: UUID
    budget_id: UUID
    tokens_deducted: int
    tokens_remaining: int
    timestamp: datetime


@dataclass(frozen=True)
class UsageSummary:
    """Aggregated usage summary for a budget."""

    budget_id: UUID
    org_id: UUID
    total_tokens: int
    used_tokens: int
    remaining_tokens: int
    deduction_count: int
    status: BudgetStatus


class TokenBudgetManager:
    """Manages token budgets with zero-error billing.

    In-memory implementation for unit testing.
    Production adapter will use PostgreSQL usage_budgets table.
    """

    def __init__(self) -> None:
        self._budgets: dict[UUID, Budget] = {}
        self._receipts: dict[UUID, list[DeductionReceipt]] = {}

    def create_budget(self, org_id: UUID, total_tokens: int) -> Budget:
        """Create a new token budget for an organization.

        Args:
            org_id: Organization ID.
            total_tokens: Total token allocation.

        Returns:
            Created Budget.

        Raises:
            ValueError: If total_tokens <= 0.
        """
        if total_tokens <= 0:
            msg = f"total_tokens must be positive, got {total_tokens}"
            raise ValueError(msg)

        budget = Budget(
            id=uuid4(),
            org_id=org_id,
            total_tokens=total_tokens,
        )
        self._budgets[budget.id] = budget
        self._receipts[budget.id] = []
        return budget

    def deduct(self, budget_id: UUID, tokens: int) -> DeductionReceipt:
        """Deduct tokens from a budget.

        Args:
            budget_id: Budget to deduct from.
            tokens: Number of tokens to deduct (must be > 0).

        Returns:
            DeductionReceipt confirming the deduction.

        Raises:
            ValueError: If tokens <= 0.
            KeyError: If budget not found.
            PermissionError: If budget is exhausted or suspended.
        """
        if tokens <= 0:
            msg = f"tokens must be positive, got {tokens}"
            raise ValueError(msg)

        budget = self._budgets.get(budget_id)
        if budget is None:
            msg = f"Budget {budget_id} not found"
            raise KeyError(msg)

        if budget.status != BudgetStatus.ACTIVE:
            msg = f"Budget {budget_id} is {budget.status.value}, cannot deduct"
            raise PermissionError(msg)

        if budget.remaining_tokens < tokens:
            budget.status = BudgetStatus.EXHAUSTED
            msg = f"Insufficient tokens: requested {tokens}, remaining {budget.remaining_tokens}"
            raise PermissionError(msg)

        budget.used_tokens += tokens

        receipt = DeductionReceipt(
            receipt_id=uuid4(),
            budget_id=budget_id,
            tokens_deducted=tokens,
            tokens_remaining=budget.remaining_tokens,
            timestamp=datetime.now(UTC),
        )
        self._receipts[budget_id].append(receipt)

        if budget.remaining_tokens == 0:
            budget.status = BudgetStatus.EXHAUSTED

        return receipt

    def check_budget(self, budget_id: UUID) -> Budget:
        """Check current budget status.

        Raises:
            KeyError: If budget not found.
        """
        budget = self._budgets.get(budget_id)
        if budget is None:
            msg = f"Budget {budget_id} not found"
            raise KeyError(msg)
        return budget

    def get_usage_summary(self, budget_id: UUID) -> UsageSummary:
        """Get aggregated usage summary for a budget.

        Raises:
            KeyError: If budget not found.
        """
        budget = self._budgets.get(budget_id)
        if budget is None:
            msg = f"Budget {budget_id} not found"
            raise KeyError(msg)

        return UsageSummary(
            budget_id=budget.id,
            org_id=budget.org_id,
            total_tokens=budget.total_tokens,
            used_tokens=budget.used_tokens,
            remaining_tokens=budget.remaining_tokens,
            deduction_count=len(self._receipts.get(budget_id, [])),
            status=budget.status,
        )
