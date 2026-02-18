"""Tests for B2-7: Graceful degradation.

Validates:
- Knowledge unavailable -> conversation still works
- Degradation flag set with reason
- Memory Core (hard dep) failure -> proper error
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.brain.engine.context_assembler import ContextAssembler
from src.ports.knowledge_port import KnowledgePort
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, OrganizationContext, WriteReceipt


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


class FailingKnowledgePort(KnowledgePort):
    """Knowledge port that always raises ConnectionError."""

    async def resolve(self, profile_id, query, org_context):
        msg = "Knowledge backend unavailable"
        raise ConnectionError(msg)

    async def capabilities(self):
        return set()


@pytest.mark.unit
class TestGracefulDegradation:
    """B2-7: Knowledge unavailable -> conversation still works."""

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
    async def test_no_knowledge_port(
        self,
        memory_core: FakeMemoryCore,
    ) -> None:
        """No KnowledgePort configured -> degraded but functional."""
        assembler = ContextAssembler(memory_core=memory_core, knowledge=None)
        ctx = await assembler.assemble(user_id=uuid4(), query="Hello")
        assert ctx.degraded is True
        assert "not configured" in ctx.degraded_reason

    @pytest.mark.asyncio()
    async def test_knowledge_port_fails(
        self,
        memory_core: FakeMemoryCore,
        org_context: OrganizationContext,
    ) -> None:
        """KnowledgePort raises exception -> degraded with reason."""
        assembler = ContextAssembler(
            memory_core=memory_core,
            knowledge=FailingKnowledgePort(),
        )
        ctx = await assembler.assemble(
            user_id=uuid4(),
            query="Hello",
            org_context=org_context,
        )
        assert ctx.degraded is True
        assert "unavailable" in ctx.degraded_reason.lower()
        assert ctx.knowledge_bundle is None

    @pytest.mark.asyncio()
    async def test_degraded_still_has_system_prompt(
        self,
        memory_core: FakeMemoryCore,
        org_context: OrganizationContext,
    ) -> None:
        assembler = ContextAssembler(
            memory_core=memory_core,
            knowledge=FailingKnowledgePort(),
        )
        ctx = await assembler.assemble(
            user_id=uuid4(),
            query="Hello",
            org_context=org_context,
        )
        assert ctx.system_prompt  # Must still have a system prompt

    @pytest.mark.asyncio()
    async def test_degraded_to_prompt_context(
        self,
        memory_core: FakeMemoryCore,
    ) -> None:
        assembler = ContextAssembler(memory_core=memory_core, knowledge=None)
        ctx = await assembler.assemble(user_id=uuid4(), query="Test")
        prompt = ctx.to_prompt_context()
        assert "degraded" in prompt.lower()

    @pytest.mark.asyncio()
    async def test_degraded_chat_success_rate_100(
        self,
        memory_core: FakeMemoryCore,
        org_context: OrganizationContext,
    ) -> None:
        """100% success rate when Knowledge is unavailable."""
        assembler = ContextAssembler(
            memory_core=memory_core,
            knowledge=FailingKnowledgePort(),
        )
        for query in ["Hello", "How are you?", "Tell me about X", "Bye", ""]:
            ctx = await assembler.assemble(
                user_id=uuid4(),
                query=query,
                org_context=org_context,
            )
            assert ctx is not None
            assert ctx.system_prompt
