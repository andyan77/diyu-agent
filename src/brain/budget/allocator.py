"""Dynamic token budget allocator for context assembly.

Task card: B4-2
- Allocates token budget across context components
- Redistributes unused budget to maximize utilization (>= 90%)
- Components: system_prompt, memories, knowledge, history, response_reserve

Architecture: Section 2.2 (Context Assembly Pipeline)
"""

from __future__ import annotations

from dataclasses import dataclass

# Minimum tokens reserved for the system prompt (always guaranteed).
_MIN_SYSTEM_PROMPT = 128

# Default ratio splits for the *available* budget (after system_prompt + response_reserve).
# memories : knowledge : history = 40% : 30% : 30%
_DEFAULT_MEMORY_RATIO = 0.40
_DEFAULT_KNOWLEDGE_RATIO = 0.30
_DEFAULT_HISTORY_RATIO = 0.30


@dataclass(frozen=True)
class TokenBudget:
    """Allocated token budget for a single context assembly."""

    total: int
    system_prompt: int
    memories: int
    knowledge: int
    history: int
    response_reserve: int

    @property
    def utilization(self) -> float:
        """Ratio of allocated tokens to total budget."""
        if self.total == 0:
            return 0.0
        allocated = (
            self.system_prompt
            + self.memories
            + self.knowledge
            + self.history
            + self.response_reserve
        )
        return allocated / self.total


class BudgetAllocator:
    """Allocates token budget dynamically based on context availability.

    Strategy:
    1. Reserve response tokens (fixed ratio).
    2. Reserve system prompt tokens (minimum guaranteed).
    3. Split remaining budget across memories, knowledge, history.
    4. If a component needs fewer tokens, redistribute surplus.
    """

    def __init__(
        self,
        *,
        max_tokens: int = 4096,
        response_reserve_ratio: float = 0.25,
    ) -> None:
        self._max_tokens = max_tokens
        self._response_reserve_ratio = response_reserve_ratio

    def allocate(
        self,
        *,
        history_token_count: int | None = None,
        memory_token_count: int | None = None,
        knowledge_available: bool = True,
    ) -> TokenBudget:
        """Allocate token budget for a context assembly.

        Args:
            history_token_count: Actual tokens in conversation history.
                If None, full history allocation is used.
            memory_token_count: Actual tokens in retrieved memories.
                If None, full memory allocation is used.
            knowledge_available: Whether KnowledgePort is available.
        """
        total = self._max_tokens
        response_reserve = int(total * self._response_reserve_ratio)
        system_prompt = _MIN_SYSTEM_PROMPT

        # Available budget for context components
        available = max(0, total - response_reserve - system_prompt)

        # Initial split
        if knowledge_available:
            mem_alloc = int(available * _DEFAULT_MEMORY_RATIO)
            know_alloc = int(available * _DEFAULT_KNOWLEDGE_RATIO)
            hist_alloc = int(available * _DEFAULT_HISTORY_RATIO)
        else:
            # Redistribute knowledge budget
            know_alloc = 0
            mem_alloc = int(available * 0.55)
            hist_alloc = int(available * 0.45)

        # Cap to actual needs and collect surplus
        surplus = 0

        if memory_token_count is not None and memory_token_count < mem_alloc:
            surplus += mem_alloc - memory_token_count
            mem_alloc = memory_token_count

        if history_token_count is not None and history_token_count < hist_alloc:
            surplus += hist_alloc - history_token_count
            hist_alloc = history_token_count

        # Redistribute surplus: prefer knowledge > memories > history
        if surplus > 0:
            if knowledge_available and know_alloc > 0:
                know_alloc += surplus
                surplus = 0
            elif memory_token_count is None:
                mem_alloc += surplus
                surplus = 0
            elif history_token_count is None:
                hist_alloc += surplus
                surplus = 0
            else:
                # All capped — give to response_reserve
                response_reserve += surplus
                surplus = 0

        return TokenBudget(
            total=total,
            system_prompt=system_prompt,
            memories=mem_alloc,
            knowledge=know_alloc,
            history=hist_alloc,
            response_reserve=response_reserve,
        )
