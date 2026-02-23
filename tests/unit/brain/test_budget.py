"""Tests for B4-2: Dynamic budget allocator.

Task card: B4-2
- Token budget allocated across context components
- Budget utilization >= 90%
- Components: system_prompt, memories, knowledge, history, response_reserve
"""

from __future__ import annotations

import pytest

from src.brain.budget.allocator import BudgetAllocator, TokenBudget


class TestTokenBudget:
    """TokenBudget data container."""

    def test_total_equals_sum_of_parts(self) -> None:
        budget = TokenBudget(
            total=4096,
            system_prompt=256,
            memories=1024,
            knowledge=1024,
            history=1024,
            response_reserve=768,
        )
        allocated = (
            budget.system_prompt
            + budget.memories
            + budget.knowledge
            + budget.history
            + budget.response_reserve
        )
        assert allocated == budget.total

    def test_utilization_ratio(self) -> None:
        budget = TokenBudget(
            total=4096,
            system_prompt=256,
            memories=1024,
            knowledge=1024,
            history=1024,
            response_reserve=768,
        )
        assert budget.utilization == 1.0

    def test_zero_total_utilization(self) -> None:
        budget = TokenBudget(
            total=0, system_prompt=0, memories=0, knowledge=0, history=0, response_reserve=0
        )
        assert budget.utilization == 0.0


class TestBudgetAllocator:
    """Dynamic allocation based on context availability."""

    @pytest.fixture
    def allocator(self) -> BudgetAllocator:
        return BudgetAllocator(max_tokens=4096, response_reserve_ratio=0.25)

    def test_default_allocation(self, allocator: BudgetAllocator) -> None:
        budget = allocator.allocate()
        assert budget.total == 4096
        assert budget.response_reserve == 1024  # 25%
        assert budget.utilization >= 0.9

    def test_with_short_history(self, allocator: BudgetAllocator) -> None:
        budget = allocator.allocate(history_token_count=100)
        # History gets only what it needs; surplus redistributed
        assert budget.history == 100
        assert budget.utilization >= 0.9

    def test_with_no_knowledge(self, allocator: BudgetAllocator) -> None:
        budget = allocator.allocate(knowledge_available=False)
        # Knowledge budget = 0, redistributed to memories/history
        assert budget.knowledge == 0
        assert budget.utilization >= 0.9

    def test_with_no_memories(self, allocator: BudgetAllocator) -> None:
        budget = allocator.allocate(memory_token_count=0)
        assert budget.memories == 0
        assert budget.utilization >= 0.9

    def test_all_components_non_negative(self, allocator: BudgetAllocator) -> None:
        budget = allocator.allocate(
            history_token_count=5000,  # exceeds available
            knowledge_available=False,
        )
        assert budget.system_prompt >= 0
        assert budget.memories >= 0
        assert budget.knowledge >= 0
        assert budget.history >= 0
        assert budget.response_reserve >= 0

    def test_system_prompt_always_reserved(self, allocator: BudgetAllocator) -> None:
        budget = allocator.allocate()
        assert budget.system_prompt >= 128  # minimum system prompt

    def test_custom_max_tokens(self) -> None:
        allocator = BudgetAllocator(max_tokens=8192, response_reserve_ratio=0.20)
        budget = allocator.allocate()
        assert budget.total == 8192
        assert budget.response_reserve == 1638  # floor(8192 * 0.20)

    def test_utilization_at_least_90_percent(self, allocator: BudgetAllocator) -> None:
        """B4-2 acceptance: utilization >= 90%."""
        scenarios = [
            {},
            {"history_token_count": 50},
            {"knowledge_available": False},
            {"memory_token_count": 0},
            {"history_token_count": 200, "knowledge_available": False, "memory_token_count": 0},
        ]
        for kwargs in scenarios:
            budget = allocator.allocate(**kwargs)
            assert budget.utilization >= 0.9, (
                f"Utilization {budget.utilization:.2f} < 0.9 for {kwargs}"
            )
