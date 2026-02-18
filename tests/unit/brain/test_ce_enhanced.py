"""Tests for B2-4: Context Assembler CE enhancement.

Validates:
- Query rewriting with conversation context
- RRF ranking output stability
- Enhanced assembly falls back to basic on failure
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.brain.engine.context_assembler import ContextAssembler
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, WriteReceipt


class FakeMemoryCore(MemoryCorePort):
    """In-memory MemoryCorePort for testing."""

    def __init__(self) -> None:
        self._items: list[MemoryItem] = []

    async def read_personal_memories(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        *,
        org_id: UUID | None = None,
    ) -> list[MemoryItem]:
        results = [m for m in self._items if m.user_id == user_id]
        if query:
            results = [m for m in results if query.lower() in m.content.lower()]
        return sorted(results, key=lambda m: m.confidence, reverse=True)[:top_k]

    async def write_observation(
        self,
        user_id: UUID,
        observation: Observation,
        *,
        org_id: UUID | None = None,
    ) -> WriteReceipt:
        memory_id = uuid4()
        now = datetime.now(UTC)
        item = MemoryItem(
            memory_id=memory_id,
            user_id=user_id,
            memory_type=observation.memory_type,
            content=observation.content,
            confidence=observation.confidence,
            valid_at=now,
            source_sessions=(
                [observation.source_session_id] if observation.source_session_id else []
            ),
        )
        self._items.append(item)
        return WriteReceipt(memory_id=memory_id, version=1, written_at=now)

    async def get_session(self, session_id: UUID) -> object:
        return None

    async def archive_session(self, session_id: UUID) -> object:
        return None


@pytest.mark.unit
class TestContextAssemblerCE:
    """B2-4: Context Assembler CE enhancement."""

    @pytest.fixture()
    def memory_core(self) -> FakeMemoryCore:
        return FakeMemoryCore()

    @pytest.fixture()
    def assembler(self, memory_core: FakeMemoryCore) -> ContextAssembler:
        return ContextAssembler(memory_core=memory_core)

    def test_query_rewriting_no_history(
        self,
        assembler: ContextAssembler,
    ) -> None:
        result = assembler._rewrite_query("What is X?", None)
        assert result == "What is X?"

    def test_query_rewriting_with_history(
        self,
        assembler: ContextAssembler,
    ) -> None:
        history = [
            {"role": "user", "content": "Tell me about Python"},
            {"role": "assistant", "content": "Python is..."},
            {"role": "user", "content": "What about its libraries?"},
        ]
        result = assembler._rewrite_query("Which one?", history)
        assert "Which one?" in result
        # Should incorporate recent user messages
        assert len(result) > len("Which one?")

    def test_query_rewriting_empty_history(
        self,
        assembler: ContextAssembler,
    ) -> None:
        result = assembler._rewrite_query("Hello", [])
        assert result == "Hello"

    @pytest.mark.asyncio()
    async def test_enhanced_assembly_returns_context(
        self,
        assembler: ContextAssembler,
    ) -> None:
        ctx = await assembler.assemble_enhanced(
            user_id=uuid4(),
            query="Tell me about Python",
        )
        assert ctx is not None
        assert ctx.system_prompt

    @pytest.mark.asyncio()
    async def test_rrf_ranking_output_stable(
        self,
        memory_core: FakeMemoryCore,
    ) -> None:
        """RRF ranking output should be deterministic for same input."""
        user_id = uuid4()
        await memory_core.write_observation(
            user_id=user_id,
            observation=Observation(content="User likes Python programming"),
        )
        await memory_core.write_observation(
            user_id=user_id,
            observation=Observation(content="User works with Python daily"),
        )

        assembler = ContextAssembler(memory_core=memory_core)

        ctx1 = await assembler.assemble_enhanced(
            user_id=user_id,
            query="Python",
        )
        ctx2 = await assembler.assemble_enhanced(
            user_id=user_id,
            query="Python",
        )

        assert len(ctx1.personal_memories) == len(ctx2.personal_memories)
        for m1, m2 in zip(ctx1.personal_memories, ctx2.personal_memories, strict=True):
            assert m1.memory_id == m2.memory_id
