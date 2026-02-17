"""Tests for B2-3: Context Assembler v1.

Validates:
- Personal memory retrieval from MemoryCorePort
- assembled_context non-empty assertion
- System prompt generation
- Integration with KnowledgePort (graceful degradation)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.brain.engine.context_assembler import AssembledContext, ContextAssembler
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.ports.knowledge_port import KnowledgePort
from src.ports.storage_port import StoragePort
from src.shared.types import KnowledgeBundle, Observation, OrganizationContext


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
    def storage(self) -> FakeStoragePort:
        return FakeStoragePort()

    @pytest.fixture()
    def memory_core(self, storage: FakeStoragePort) -> PgMemoryCoreAdapter:
        return PgMemoryCoreAdapter(storage=storage)

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
        memory_core: PgMemoryCoreAdapter,
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
        memory_core: PgMemoryCoreAdapter,
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
        memory_core: PgMemoryCoreAdapter,
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
        memory_core: PgMemoryCoreAdapter,
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
        memory_core: PgMemoryCoreAdapter,
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
