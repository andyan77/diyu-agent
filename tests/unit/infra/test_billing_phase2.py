"""Unit tests for token billing (I2-3) -- phase2.

Tests zero-error billing with in-memory TokenBudgetManager.
Complies with no-mock policy.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.infra.billing.budget import (
    Budget,
    BudgetStatus,
    DeductionReceipt,
    TokenBudgetManager,
    UsageSummary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def manager() -> TokenBudgetManager:
    return TokenBudgetManager()


@pytest.fixture()
def org_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBillingPhase2:
    """Token billing unit tests (phase2, zero-error)."""

    def test_create_budget(self, manager: TokenBudgetManager, org_id) -> None:
        budget = manager.create_budget(org_id, total_tokens=10000)
        assert isinstance(budget, Budget)
        assert budget.org_id == org_id
        assert budget.total_tokens == 10000
        assert budget.used_tokens == 0
        assert budget.remaining_tokens == 10000
        assert budget.status == BudgetStatus.ACTIVE

    def test_create_budget_invalid_tokens(
        self,
        manager: TokenBudgetManager,
        org_id,
    ) -> None:
        with pytest.raises(ValueError, match="positive"):
            manager.create_budget(org_id, total_tokens=0)
        with pytest.raises(ValueError, match="positive"):
            manager.create_budget(org_id, total_tokens=-100)

    def test_deduct_tokens(self, manager: TokenBudgetManager, org_id) -> None:
        budget = manager.create_budget(org_id, total_tokens=1000)
        receipt = manager.deduct(budget.id, tokens=250)

        assert isinstance(receipt, DeductionReceipt)
        assert receipt.budget_id == budget.id
        assert receipt.tokens_deducted == 250
        assert receipt.tokens_remaining == 750
        assert budget.used_tokens == 250
        assert budget.remaining_tokens == 750

    def test_deduct_invalid_tokens(
        self,
        manager: TokenBudgetManager,
        org_id,
    ) -> None:
        budget = manager.create_budget(org_id, total_tokens=1000)
        with pytest.raises(ValueError, match="positive"):
            manager.deduct(budget.id, tokens=0)

    def test_deduct_unknown_budget(self, manager: TokenBudgetManager) -> None:
        with pytest.raises(KeyError):
            manager.deduct(uuid4(), tokens=100)

    def test_deduct_exhausts_budget(
        self,
        manager: TokenBudgetManager,
        org_id,
    ) -> None:
        budget = manager.create_budget(org_id, total_tokens=500)
        receipt = manager.deduct(budget.id, tokens=500)

        assert receipt.tokens_remaining == 0
        assert budget.status == BudgetStatus.EXHAUSTED

    def test_deduct_rejects_when_exhausted(
        self,
        manager: TokenBudgetManager,
        org_id,
    ) -> None:
        budget = manager.create_budget(org_id, total_tokens=100)
        manager.deduct(budget.id, tokens=100)

        with pytest.raises(PermissionError, match="exhausted"):
            manager.deduct(budget.id, tokens=1)

    def test_deduct_rejects_insufficient_tokens(
        self,
        manager: TokenBudgetManager,
        org_id,
    ) -> None:
        budget = manager.create_budget(org_id, total_tokens=100)
        with pytest.raises(PermissionError, match="Insufficient"):
            manager.deduct(budget.id, tokens=101)
        assert budget.status == BudgetStatus.EXHAUSTED

    def test_zero_error_precision(
        self,
        manager: TokenBudgetManager,
        org_id,
    ) -> None:
        """Billing error = 0: multiple deductions sum exactly to total."""
        budget = manager.create_budget(org_id, total_tokens=10000)

        deductions = [1500, 2500, 3000, 1000, 2000]
        for d in deductions:
            manager.deduct(budget.id, tokens=d)

        assert budget.used_tokens == sum(deductions)
        assert budget.remaining_tokens == 10000 - sum(deductions)
        assert budget.used_tokens + budget.remaining_tokens == budget.total_tokens

    def test_check_budget(self, manager: TokenBudgetManager, org_id) -> None:
        budget = manager.create_budget(org_id, total_tokens=5000)
        manager.deduct(budget.id, tokens=1000)

        checked = manager.check_budget(budget.id)
        assert checked.used_tokens == 1000
        assert checked.remaining_tokens == 4000

    def test_check_budget_unknown(self, manager: TokenBudgetManager) -> None:
        with pytest.raises(KeyError):
            manager.check_budget(uuid4())

    def test_usage_summary(self, manager: TokenBudgetManager, org_id) -> None:
        budget = manager.create_budget(org_id, total_tokens=3000)
        manager.deduct(budget.id, tokens=500)
        manager.deduct(budget.id, tokens=700)

        summary = manager.get_usage_summary(budget.id)
        assert isinstance(summary, UsageSummary)
        assert summary.org_id == org_id
        assert summary.total_tokens == 3000
        assert summary.used_tokens == 1200
        assert summary.remaining_tokens == 1800
        assert summary.deduction_count == 2
        assert summary.status == BudgetStatus.ACTIVE

    def test_usage_summary_after_exhaustion(
        self,
        manager: TokenBudgetManager,
        org_id,
    ) -> None:
        budget = manager.create_budget(org_id, total_tokens=100)
        manager.deduct(budget.id, tokens=100)

        summary = manager.get_usage_summary(budget.id)
        assert summary.status == BudgetStatus.EXHAUSTED
        assert summary.remaining_tokens == 0
        assert summary.deduction_count == 1
