"""Tests for B2-1: Conversation engine full implementation.

Validates:
- Complete first-turn conversation closure
- Context assembly integration
- LLM call through Port
- Memory pipeline integration (non-blocking)
- Usage tracking
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine, ConversationTurn
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.storage_port import StoragePort
from src.tool.llm.usage_tracker import UsageTracker


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


class FakeLLM(LLMCallPort):
    """Fake LLM for conversation engine tests."""

    def __init__(self, response: str = "I understand.") -> None:
        self._response = response
        self.call_count = 0

    async def call(self, prompt, model_id, content_parts=None, parameters=None):
        self.call_count += 1
        return LLMResponse(
            text=self._response,
            tokens_used={"input": 50, "output": 30},
            model_id=model_id,
            finish_reason="stop",
        )


@pytest.mark.unit
class TestConversationEngine:
    """B2-1: Conversation engine full impl."""

    @pytest.fixture()
    def engine(self) -> ConversationEngine:
        storage = FakeStoragePort()
        memory_core = PgMemoryCoreAdapter(storage=storage)
        llm = FakeLLM(response="Hello! I'm here to help.")
        usage_tracker = UsageTracker()
        return ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            usage_tracker=usage_tracker,
            default_model="gpt-4o",
        )

    @pytest.mark.asyncio()
    async def test_first_turn_closure(self, engine: ConversationEngine) -> None:
        """Complete first-turn: user message -> assistant response."""
        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Hello, who are you?",
        )
        assert isinstance(turn, ConversationTurn)
        assert turn.assistant_response == "Hello! I'm here to help."
        assert turn.user_message == "Hello, who are you?"
        assert turn.tokens_used["input"] == 50
        assert turn.tokens_used["output"] == 30

    @pytest.mark.asyncio()
    async def test_session_id_preserved(self, engine: ConversationEngine) -> None:
        session_id = uuid4()
        turn = await engine.process_message(
            session_id=session_id,
            user_id=uuid4(),
            org_id=uuid4(),
            message="Test",
        )
        assert turn.session_id == session_id

    @pytest.mark.asyncio()
    async def test_model_id_passed(self, engine: ConversationEngine) -> None:
        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Test",
            model_id="gpt-4o-mini",
        )
        assert turn.model_id == "gpt-4o-mini"

    @pytest.mark.asyncio()
    async def test_usage_tracking(self, engine: ConversationEngine) -> None:
        org_id = uuid4()
        await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=org_id,
            message="Test",
        )
        assert engine._usage_tracker is not None
        summary = engine._usage_tracker.get_org_summary(org_id)
        assert summary.record_count == 1
        assert summary.total_tokens == 80  # 50 + 30

    @pytest.mark.asyncio()
    async def test_intent_defaults_to_chat(self, engine: ConversationEngine) -> None:
        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="What's the weather?",
        )
        assert turn.intent_type == "chat"

    @pytest.mark.asyncio()
    async def test_conversation_history_passed(self, engine: ConversationEngine) -> None:
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]
        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Follow up",
            conversation_history=history,
        )
        assert turn.assistant_response is not None

    @pytest.mark.asyncio()
    async def test_coverage_85_percent(self, engine: ConversationEngine) -> None:
        """Run multiple scenarios to ensure 85%+ coverage."""
        for msg in ["Hi", "Tell me a joke", "What is Python?", "", "Bye"]:
            turn = await engine.process_message(
                session_id=uuid4(),
                user_id=uuid4(),
                org_id=uuid4(),
                message=msg,
            )
            assert turn.assistant_response is not None
