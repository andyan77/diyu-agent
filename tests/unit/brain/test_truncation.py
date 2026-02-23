"""Tests for B4-3: TruncationPolicy.

Task card: B4-3
- Truncate context when it exceeds token budget
- Priority order: system > memory > knowledge > history
- Higher-priority components are never truncated before lower-priority ones
"""

from __future__ import annotations

import pytest

from src.brain.context.truncation import ContextBlock, FixedPriorityPolicy, Priority


class TestContextBlock:
    """ContextBlock data container."""

    def test_creation(self) -> None:
        block = ContextBlock(
            name="memories",
            content="some text",
            token_count=10,
            priority=Priority.MEMORY,
        )
        assert block.name == "memories"
        assert block.token_count == 10
        assert block.priority == Priority.MEMORY

    def test_priority_ordering(self) -> None:
        assert Priority.SYSTEM > Priority.MEMORY
        assert Priority.MEMORY > Priority.KNOWLEDGE
        assert Priority.KNOWLEDGE > Priority.HISTORY


class TestFixedPriorityPolicy:
    """B4-3: FixedPriorityPolicy truncation."""

    @pytest.fixture
    def policy(self) -> FixedPriorityPolicy:
        return FixedPriorityPolicy()

    def test_no_truncation_within_budget(self, policy: FixedPriorityPolicy) -> None:
        blocks = [
            ContextBlock("system", "sys prompt", 50, Priority.SYSTEM),
            ContextBlock("memory", "mem data", 100, Priority.MEMORY),
            ContextBlock("knowledge", "kb data", 100, Priority.KNOWLEDGE),
            ContextBlock("history", "hist data", 100, Priority.HISTORY),
        ]
        result = policy.truncate(blocks, max_tokens=400)
        assert sum(b.token_count for b in result) == 350
        assert len(result) == 4

    def test_history_truncated_first(self, policy: FixedPriorityPolicy) -> None:
        blocks = [
            ContextBlock("system", "sys", 50, Priority.SYSTEM),
            ContextBlock("memory", "mem", 100, Priority.MEMORY),
            ContextBlock("knowledge", "kb", 100, Priority.KNOWLEDGE),
            ContextBlock("history", "hist" * 100, 400, Priority.HISTORY),
        ]
        result = policy.truncate(blocks, max_tokens=300)
        # System(50) + Memory(100) + Knowledge(100) = 250 -> history gets 50
        names = {b.name for b in result}
        assert "system" in names
        assert "memory" in names
        assert "knowledge" in names
        history_block = next((b for b in result if b.name == "history"), None)
        assert history_block is not None
        assert history_block.token_count <= 50

    def test_knowledge_truncated_after_history(self, policy: FixedPriorityPolicy) -> None:
        blocks = [
            ContextBlock("system", "sys", 50, Priority.SYSTEM),
            ContextBlock("memory", "mem", 100, Priority.MEMORY),
            ContextBlock("knowledge", "kb" * 200, 400, Priority.KNOWLEDGE),
            ContextBlock("history", "hist" * 200, 400, Priority.HISTORY),
        ]
        result = policy.truncate(blocks, max_tokens=200)
        # System(50) + Memory(100) = 150 -> knowledge gets 50, history dropped
        history_block = next((b for b in result if b.name == "history"), None)
        if history_block:
            assert history_block.token_count == 0
        knowledge_block = next((b for b in result if b.name == "knowledge"), None)
        assert knowledge_block is not None
        assert knowledge_block.token_count <= 50

    def test_system_never_truncated(self, policy: FixedPriorityPolicy) -> None:
        blocks = [
            ContextBlock("system", "sys", 150, Priority.SYSTEM),
            ContextBlock("memory", "mem", 100, Priority.MEMORY),
        ]
        result = policy.truncate(blocks, max_tokens=200)
        sys_block = next(b for b in result if b.name == "system")
        assert sys_block.token_count == 150

    def test_empty_blocks(self, policy: FixedPriorityPolicy) -> None:
        result = policy.truncate([], max_tokens=100)
        assert result == []

    def test_all_zero_budget(self, policy: FixedPriorityPolicy) -> None:
        blocks = [
            ContextBlock("system", "sys", 100, Priority.SYSTEM),
            ContextBlock("memory", "mem", 100, Priority.MEMORY),
        ]
        result = policy.truncate(blocks, max_tokens=0)
        # All truncated to 0
        assert all(b.token_count == 0 for b in result)

    def test_preserves_block_order(self, policy: FixedPriorityPolicy) -> None:
        blocks = [
            ContextBlock("history", "h", 100, Priority.HISTORY),
            ContextBlock("system", "s", 50, Priority.SYSTEM),
            ContextBlock("memory", "m", 100, Priority.MEMORY),
        ]
        result = policy.truncate(blocks, max_tokens=300)
        assert [b.name for b in result] == ["history", "system", "memory"]
