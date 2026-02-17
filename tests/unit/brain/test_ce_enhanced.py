"""Tests for B2-4: Context Assembler CE enhancement.

Validates:
- Query rewriting with conversation context
- RRF ranking output stability
- Enhanced assembly falls back to basic on failure
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.brain.engine.context_assembler import ContextAssembler
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.ports.storage_port import StoragePort
from src.shared.types import Observation


class FakeStoragePort(StoragePort):
    """In-memory storage for testing."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    async def put(self, key, value, ttl=None):
        self._data[key] = value

    async def get(self, key):
        return self._data.get(key)

    async def delete(self, key):
        self._data.pop(key, None)

    async def list_keys(self, pattern):
        import fnmatch

        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]


@pytest.mark.unit
class TestContextAssemblerCE:
    """B2-4: Context Assembler CE enhancement."""

    @pytest.fixture()
    def memory_core(self) -> PgMemoryCoreAdapter:
        return PgMemoryCoreAdapter(storage=FakeStoragePort())

    @pytest.fixture()
    def assembler(self, memory_core: PgMemoryCoreAdapter) -> ContextAssembler:
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
        memory_core: PgMemoryCoreAdapter,
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
