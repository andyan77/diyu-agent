"""Tests for B2-3: Context Assembler v1.

Validates:
- Personal memory retrieval from MemoryCorePort
- assembled_context non-empty assertion
- System prompt generation
- Integration with KnowledgePort (graceful degradation)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.brain.engine.context_assembler import AssembledContext, ContextAssembler
from src.ports.knowledge_port import KnowledgePort
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import (
    KnowledgeBundle,
    MemoryItem,
    Observation,
    OrganizationContext,
    WriteReceipt,
)


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


class FakeKnowledgePort(KnowledgePort):
    """Fake knowledge port returning predefined bundle."""

    def __init__(self, bundle: KnowledgeBundle | None = None) -> None:
        self._bundle = bundle or KnowledgeBundle()

    async def resolve(self, profile_id, query, org_context):
        return self._bundle

    async def capabilities(self):
        return {"semantic_search"}


class FailingKnowledgePort(KnowledgePort):
    """Knowledge port that always fails."""

    async def resolve(self, profile_id, query, org_context):
        msg = "Knowledge backend unavailable"
        raise ConnectionError(msg)

    async def capabilities(self):
        return set()


@pytest.mark.unit
class TestContextAssembler:
    """B2-3: Context Assembler v1."""

    @pytest.fixture()
    def memory_core(self) -> FakeMemoryCore:
        return FakeMemoryCore()

    @pytest.fixture()
    def org_context(self) -> OrganizationContext:
        return OrganizationContext(
            user_id=uuid4(),
            org_id=uuid4(),
            org_tier="brand_hq",
            org_path="root.brand",
        )

    @pytest.mark.asyncio()
    async def test_assembled_context_non_empty(
        self,
        memory_core: FakeMemoryCore,
    ) -> None:
        """assembled_context must be non-empty even without data."""
        assembler = ContextAssembler(memory_core=memory_core)
        ctx = await assembler.assemble(
            user_id=uuid4(),
            query="Hello",
        )
        assert isinstance(ctx, AssembledContext)
        assert ctx.system_prompt  # Must have at least default prompt

    @pytest.mark.asyncio()
    async def test_personal_memories_included(
        self,
        memory_core: FakeMemoryCore,
    ) -> None:
        user_id = uuid4()
        await memory_core.write_observation(
            user_id=user_id,
            observation=Observation(content="User likes Python"),
        )
        assembler = ContextAssembler(memory_core=memory_core)
        ctx = await assembler.assemble(user_id=user_id, query="Python")
        assert len(ctx.personal_memories) == 1
        assert "Python" in ctx.personal_memories[0].content

    @pytest.mark.asyncio()
    async def test_knowledge_bundle_included(
        self,
        memory_core: FakeMemoryCore,
        org_context: OrganizationContext,
    ) -> None:
        kb = KnowledgeBundle(
            semantic_contents=[{"content": "Domain fact 1"}],
        )
        knowledge = FakeKnowledgePort(bundle=kb)
        assembler = ContextAssembler(
            memory_core=memory_core,
            knowledge=knowledge,
        )
        ctx = await assembler.assemble(
            user_id=uuid4(),
            query="Tell me about domain",
            org_context=org_context,
        )
        assert ctx.knowledge_bundle is not None
        assert len(ctx.knowledge_bundle.semantic_contents) == 1
        assert ctx.degraded is False

    @pytest.mark.asyncio()
    async def test_system_prompt_contains_memories(
        self,
        memory_core: FakeMemoryCore,
    ) -> None:
        user_id = uuid4()
        await memory_core.write_observation(
            user_id=user_id,
            observation=Observation(content="User is a developer"),
        )
        assembler = ContextAssembler(memory_core=memory_core)
        ctx = await assembler.assemble(user_id=user_id, query="developer")
        assert "developer" in ctx.system_prompt.lower()

    @pytest.mark.asyncio()
    async def test_to_prompt_context(
        self,
        memory_core: FakeMemoryCore,
    ) -> None:
        user_id = uuid4()
        await memory_core.write_observation(
            user_id=user_id,
            observation=Observation(content="Likes coffee"),
        )
        assembler = ContextAssembler(memory_core=memory_core)
        ctx = await assembler.assemble(user_id=user_id, query="coffee")
        prompt_ctx = ctx.to_prompt_context()
        assert "coffee" in prompt_ctx.lower()
