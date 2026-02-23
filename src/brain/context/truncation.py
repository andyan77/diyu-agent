"""Fixed-priority truncation policy for context blocks.

Task card: B4-3
- When assembled context exceeds the token budget, truncate by priority
- Priority order: SYSTEM > MEMORY > KNOWLEDGE > HISTORY
- Higher-priority blocks are fully preserved before lower ones are trimmed

Architecture: Section 2.2 (Context Assembly Pipeline)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Priority(enum.IntEnum):
    """Truncation priority (higher value = higher priority, preserved first)."""

    HISTORY = 10
    KNOWLEDGE = 20
    MEMORY = 30
    SYSTEM = 40


@dataclass
class ContextBlock:
    """A named block of context with token count and priority."""

    name: str
    content: str
    token_count: int
    priority: Priority


class FixedPriorityPolicy:
    """Truncate context blocks by fixed priority order.

    Strategy: sort blocks by priority descending, greedily allocate budget.
    Blocks that don't fit get their token_count reduced (content is logically
    truncated to fit). Original input order is preserved in the output.
    """

    def truncate(
        self,
        blocks: list[ContextBlock],
        max_tokens: int,
    ) -> list[ContextBlock]:
        """Return blocks with token_count adjusted to fit within max_tokens.

        Blocks are allocated in priority order (highest first).
        The output preserves the original order of blocks.
        """
        if not blocks:
            return []

        # Build allocation map: name -> allowed tokens
        allocation: dict[str, int] = {}
        remaining = max(0, max_tokens)

        # Sort by priority descending for greedy allocation
        sorted_blocks = sorted(blocks, key=lambda b: b.priority, reverse=True)

        for block in sorted_blocks:
            give = min(block.token_count, remaining)
            allocation[block.name] = give
            remaining -= give

        # Return in original order with adjusted token_count
        return [
            ContextBlock(
                name=b.name,
                content=b.content,
                token_count=allocation[b.name],
                priority=b.priority,
            )
            for b in blocks
        ]
