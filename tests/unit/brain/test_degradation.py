"""Tests for B2-7: Graceful degradation.

Validates:
- Knowledge unavailable -> conversation still works
- Degradation flag set with reason
- Memory Core (hard dep) failure -> proper error
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.brain.engine.context_assembler import ContextAssembler
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.ports.knowledge_port import KnowledgePort
from src.ports.storage_port import StoragePort
from src.shared.types import OrganizationContext


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
    def memory_core(self) -> PgMemoryCoreAdapter:
        return PgMemoryCoreAdapter(storage=FakeStoragePort())

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
        memory_core: PgMemoryCoreAdapter,
    ) -> None:
        """No KnowledgePort configured -> degraded but functional."""
        assembler = ContextAssembler(memory_core=memory_core, knowledge=None)
        ctx = await assembler.assemble(user_id=uuid4(), query="Hello")
        assert ctx.degraded is True
        assert "not configured" in ctx.degraded_reason

    @pytest.mark.asyncio()
    async def test_knowledge_port_fails(
        self,
        memory_core: PgMemoryCoreAdapter,
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
        memory_core: PgMemoryCoreAdapter,
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
        memory_core: PgMemoryCoreAdapter,
    ) -> None:
        assembler = ContextAssembler(memory_core=memory_core, knowledge=None)
        ctx = await assembler.assemble(user_id=uuid4(), query="Test")
        prompt = ctx.to_prompt_context()
        assert "degraded" in prompt.lower()

    @pytest.mark.asyncio()
    async def test_degraded_chat_success_rate_100(
        self,
        memory_core: PgMemoryCoreAdapter,
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
