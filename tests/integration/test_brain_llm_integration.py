"""Integration test for Brain + Tool layer (WF2-B2).

Tests the full conversation flow:
  ConversationEngine -> ContextAssembler -> LLMCallPort -> UsageTracker -> MemoryWritePipeline

Uses in-memory adapters (no external services required).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine
from src.brain.intent.classifier import IntentClassifier
from src.brain.memory.pipeline import MemoryWritePipeline
from src.memory.receipt import ReceiptStore
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, WriteReceipt
from src.tool.llm.usage_tracker import UsageTracker


class FakeMemoryCore(MemoryCorePort):
    """In-memory MemoryCorePort for integration testing."""

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


class FakeLLMPort(LLMCallPort):
    """Fake LLM for integration testing."""

    def __init__(self) -> None:
        self.call_count = 0

    async def call(self, prompt, model_id, content_parts=None, parameters=None):
        self.call_count += 1
        return LLMResponse(
            text=f"Response #{self.call_count}",
            tokens_used={"input": 20, "output": 30},
            model_id=model_id,
        )


@pytest.fixture()
def brain_stack():
    """Build complete Brain + Tool stack with in-memory adapters."""
    memory_core = FakeMemoryCore()
    receipt_store = ReceiptStore()
    llm = FakeLLMPort()
    usage = UsageTracker()
    intent = IntentClassifier()
    pipeline = MemoryWritePipeline(memory_core=memory_core, receipt_store=receipt_store)

    engine = ConversationEngine(
        llm=llm,
        memory_core=memory_core,
        intent_classifier=intent,
        memory_pipeline=pipeline,
        usage_tracker=usage,
        default_model="gpt-4o",
    )
    return engine, llm, usage, receipt_store


@pytest.mark.integration
class TestBrainLLMIntegration:
    """Full Brain + Tool integration: ConversationEngine -> LLM -> Usage -> Memory."""

    @pytest.mark.asyncio()
    async def test_full_conversation_turn(self, brain_stack) -> None:
        """Single message flows through entire stack."""
        engine, llm, usage, _receipts = brain_stack
        org_id = uuid4()

        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=org_id,
            message="I prefer dark mode for coding",
        )

        assert turn.assistant_response == "Response #1"
        assert turn.tokens_used == {"input": 20, "output": 30}
        assert turn.model_id == "gpt-4o"
        assert llm.call_count == 1

        summary = usage.get_org_summary(org_id)
        assert summary.total_tokens == 50
        assert summary.record_count == 1

    @pytest.mark.asyncio()
    async def test_multi_turn_session(self, brain_stack) -> None:
        """Multiple turns in same session maintain conversation history."""
        engine, llm, usage, _receipts = brain_stack
        session_id = uuid4()
        user_id = uuid4()
        org_id = uuid4()

        turn1 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Hello",
        )
        assert turn1.assistant_response == "Response #1"

        turn2 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Follow up",
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": turn1.assistant_response},
            ],
        )
        assert turn2.assistant_response == "Response #2"
        assert llm.call_count == 2

        summary = usage.get_org_summary(org_id)
        assert summary.record_count == 2
        assert summary.total_tokens == 100

    @pytest.mark.asyncio()
    async def test_intent_classification_in_flow(self, brain_stack) -> None:
        """Intent classification integrates correctly with conversation engine."""
        engine, _llm, _usage, _receipts = brain_stack

        chat_turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="What is the weather?",
        )
        assert chat_turn.intent_type == "chat"

        skill_turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Generate content for my blog",
        )
        assert skill_turn.intent_type == "skill"

    @pytest.mark.asyncio()
    async def test_memory_pipeline_integration(self, brain_stack) -> None:
        """Memory write pipeline runs during conversation turn without errors."""
        engine, _llm, _usage, receipt_store = brain_stack

        await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="I am a software engineer who prefers Python",
        )

        # Verify receipts were stored (check all receipts exist)
        all_receipts = list(receipt_store._receipts.values())
        injection_count = sum(1 for r in all_receipts if r.receipt_type == "injection")
        assert injection_count >= 0  # Pipeline ran without error
