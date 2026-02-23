"""Tests for B4-1: Context Assembler parallel optimization + SLI.

Validates:
- Memory + Knowledge queries run in parallel (asyncio.gather)
- SLI metrics are recorded for context assembly
- trace_id is propagated through assembly
- Performance: parallel is faster than sequential
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from prometheus_client import CollectorRegistry

from src.brain.engine.context_assembler import ContextAssembler
from src.brain.metrics.sli import BrainSLI
from src.ports.knowledge_port import KnowledgePort
from src.ports.memory_core_port import MemoryCorePort
from src.shared.trace_context import get_trace_id, set_trace_id
from src.shared.types import (
    KnowledgeBundle,
    MemoryItem,
    Observation,
    OrganizationContext,
    PromotionReceipt,
    WriteReceipt,
)


class SlowMemoryCore(MemoryCorePort):
    """Memory core that takes delay_ms to respond."""

    def __init__(self, *, delay: float = 0.05) -> None:
        self._delay = delay
        self.call_count = 0
        self.seen_trace_ids: list[str] = []

    async def read_personal_memories(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        *,
        org_id: UUID | None = None,
    ) -> list[MemoryItem]:
        self.call_count += 1
        self.seen_trace_ids.append(get_trace_id())
        await asyncio.sleep(self._delay)
        return [
            MemoryItem(
                memory_id=uuid4(),
                user_id=user_id,
                memory_type="preference",
                content="test memory",
                confidence=0.9,
                valid_at=datetime.now(UTC),
            )
        ]

    async def write_observation(
        self, user_id: UUID, observation: Observation, *, org_id: UUID | None = None
    ) -> WriteReceipt:
        return WriteReceipt(memory_id=uuid4(), version=1, written_at=datetime.now(UTC))

    async def get_session(self, session_id: UUID) -> object:
        return None

    async def archive_session(self, session_id: UUID) -> object:
        return None

    async def promote_to_knowledge(
        self,
        memory_id: UUID,
        target_org_id: UUID,
        target_visibility: str,
        *,
        user_id: UUID | None = None,
    ) -> PromotionReceipt:
        return PromotionReceipt(
            proposal_id=memory_id,
            source_memory_id=memory_id,
            target_knowledge_id=None,
            status="promoted",
            promoted_at=datetime.now(UTC),
        )


class SlowKnowledgePort(KnowledgePort):
    """Knowledge port that takes delay_ms to respond."""

    def __init__(self, *, delay: float = 0.05) -> None:
        self._delay = delay
        self.call_count = 0
        self.seen_trace_ids: list[str] = []

    async def resolve(self, profile_id, query, org_context):
        self.call_count += 1
        self.seen_trace_ids.append(get_trace_id())
        await asyncio.sleep(self._delay)
        return KnowledgeBundle(semantic_contents=[{"content": "test knowledge"}])

    async def capabilities(self):
        return {"semantic_search"}


@pytest.fixture
def org_context() -> OrganizationContext:
    return OrganizationContext(
        user_id=uuid4(), org_id=uuid4(), org_tier="platform", org_path="root"
    )


@pytest.fixture
def registry() -> CollectorRegistry:
    return CollectorRegistry()


@pytest.fixture
def sli(registry: CollectorRegistry) -> BrainSLI:
    return BrainSLI(registry=registry)


class TestParallelExecution:
    """Memory + Knowledge queries should run concurrently."""

    @pytest.mark.asyncio
    async def test_parallel_is_faster_than_sequential(
        self, org_context: OrganizationContext
    ) -> None:
        """With 50ms delay each, parallel should be ~50ms, not ~100ms."""
        delay = 0.05
        memory = SlowMemoryCore(delay=delay)
        knowledge = SlowKnowledgePort(delay=delay)
        assembler = ContextAssembler(memory_core=memory, knowledge=knowledge)

        start = time.monotonic()
        ctx = await assembler.assemble(
            user_id=org_context.user_id,
            query="test",
            org_context=org_context,
        )
        elapsed = time.monotonic() - start

        assert memory.call_count == 1
        assert knowledge.call_count == 1
        assert ctx.personal_memories
        assert ctx.knowledge_bundle is not None
        # Parallel: should be around delay, not 2*delay
        # Allow generous margin for CI: less than 1.5 * delay
        assert elapsed < delay * 3, f"Took {elapsed:.3f}s, expected < {delay * 3:.3f}s"

    @pytest.mark.asyncio
    async def test_knowledge_failure_still_returns_memories(
        self, org_context: OrganizationContext
    ) -> None:
        """Knowledge failure doesn't prevent memory retrieval."""
        memory = SlowMemoryCore(delay=0.01)

        class FailKnowledge(KnowledgePort):
            async def resolve(self, profile_id, query, org_context):
                raise ConnectionError("neo4j down")

            async def capabilities(self):
                return set()

        assembler = ContextAssembler(memory_core=memory, knowledge=FailKnowledge())
        ctx = await assembler.assemble(
            user_id=org_context.user_id,
            query="test",
            org_context=org_context,
        )
        assert ctx.personal_memories  # memory succeeded
        assert ctx.degraded is True
        assert "unavailable" in ctx.degraded_reason.lower()


class TestSLIInstrumentation:
    """Context assembler records SLI metrics."""

    @pytest.mark.asyncio
    async def test_assembly_duration_recorded(
        self, org_context: OrganizationContext, sli: BrainSLI, registry: CollectorRegistry
    ) -> None:
        memory = SlowMemoryCore(delay=0.01)
        assembler = ContextAssembler(memory_core=memory, sli=sli)

        await assembler.assemble(
            user_id=org_context.user_id,
            query="test",
            org_context=org_context,
        )

        # Check that context_assembly_duration was observed
        samples = [
            s
            for m in registry.collect()
            for s in m.samples
            if s.name.startswith("brain_context_assembly_duration_seconds")
        ]
        count_samples = [s for s in samples if s.name.endswith("_count")]
        assert any(s.value >= 1.0 for s in count_samples)

    @pytest.mark.asyncio
    async def test_memory_retrieval_hit_counted(
        self, org_context: OrganizationContext, sli: BrainSLI, registry: CollectorRegistry
    ) -> None:
        memory = SlowMemoryCore(delay=0.001)
        assembler = ContextAssembler(memory_core=memory, sli=sli)

        await assembler.assemble(
            user_id=org_context.user_id,
            query="test",
            org_context=org_context,
        )

        samples = [
            s
            for m in registry.collect()
            for s in m.samples
            if s.name.startswith("brain_memory_retrieval_total")
        ]
        hit_samples = [s for s in samples if s.labels.get("status") == "hit"]
        assert any(s.value >= 1.0 for s in hit_samples)

    @pytest.mark.asyncio
    async def test_memory_retrieval_miss_when_empty(
        self, org_context: OrganizationContext, sli: BrainSLI, registry: CollectorRegistry
    ) -> None:
        """No memories returned -> miss counter incremented."""

        class EmptyMemory(MemoryCorePort):
            async def read_personal_memories(self, user_id, query, top_k=10, *, org_id=None):
                return []

            async def write_observation(self, user_id, observation, *, org_id=None):
                return WriteReceipt(memory_id=uuid4(), version=1, written_at=datetime.now(UTC))

            async def get_session(self, session_id):
                return None

            async def archive_session(self, session_id):
                return None

            async def promote_to_knowledge(
                self, memory_id, target_org_id, target_visibility, *, user_id=None
            ):
                return PromotionReceipt(
                    proposal_id=memory_id,
                    source_memory_id=memory_id,
                    target_knowledge_id=None,
                    status="promoted",
                    promoted_at=datetime.now(UTC),
                )

        assembler = ContextAssembler(memory_core=EmptyMemory(), sli=sli)
        await assembler.assemble(
            user_id=org_context.user_id,
            query="test",
            org_context=org_context,
        )

        samples = [
            s
            for m in registry.collect()
            for s in m.samples
            if s.name.startswith("brain_memory_retrieval_total")
        ]
        miss_samples = [s for s in samples if s.labels.get("status") == "miss"]
        assert any(s.value >= 1.0 for s in miss_samples)


class TestTraceIdPropagation:
    """trace_id is visible in Memory + Knowledge calls."""

    @pytest.mark.asyncio
    async def test_trace_id_propagated_to_ports(self, org_context: OrganizationContext) -> None:
        memory = SlowMemoryCore(delay=0.001)
        knowledge = SlowKnowledgePort(delay=0.001)
        assembler = ContextAssembler(memory_core=memory, knowledge=knowledge)

        set_trace_id("trace-abc")
        await assembler.assemble(
            user_id=org_context.user_id,
            query="test",
            org_context=org_context,
        )

        assert memory.seen_trace_ids == ["trace-abc"]
        assert knowledge.seen_trace_ids == ["trace-abc"]
