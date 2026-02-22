"""Conversation engine -- core loop for user interaction.

Task card: B2-1
- Receive user message -> assemble context -> call LLM -> return reply
- Complete first-turn conversation closure
- Ports: MemoryCorePort, LLMCallPort

Architecture: Section 2.1 (Conversation Engine Core Loop)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID, uuid4

from src.brain.engine.context_assembler import AssembledContext, ContextAssembler
from src.shared.types import OrganizationContext

if TYPE_CHECKING:
    from src.brain.intent.classifier import IntentClassifier
    from src.brain.memory.pipeline import MemoryWritePipeline
    from src.brain.skill.orchestrator import SkillOrchestrator
    from src.memory.receipt import ReceiptStoreProtocol
    from src.ports.knowledge_port import KnowledgePort
    from src.ports.llm_call_port import ContentBlock, LLMResponse
    from src.ports.memory_core_port import MemoryCorePort


class LLMCallProtocol(Protocol):
    """Protocol for LLM invocation (structural typing).

    Both LLMCallPort implementations and ModelRegistry satisfy this protocol.
    Brain depends on the protocol, never concrete classes.
    """

    async def call(
        self,
        prompt: str,
        model_id: str = ...,
        content_parts: list[ContentBlock] | None = ...,
        parameters: dict[str, Any] | None = ...,
    ) -> LLMResponse: ...


class UsageRecorder(Protocol):
    """Protocol for recording LLM usage (structural typing).

    Brain layer depends on this protocol, not the concrete UsageTracker
    in the Tool layer, to respect layer boundaries.
    """

    def record_usage(
        self,
        *,
        org_id: UUID,
        user_id: UUID,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Any: ...


class EventStoreProtocol(Protocol):
    """Protocol for conversation event persistence (structural typing).

    Both ConversationEventStore (in-memory) and PgConversationEventStore
    satisfy this protocol. Brain depends on the protocol, never concrete classes.
    """

    async def append_event(
        self,
        *,
        org_id: UUID,
        session_id: UUID,
        user_id: UUID | None = None,
        event_type: str,
        role: str = "user",
        content: dict[str, Any] | None = None,
        parent_event_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any: ...

    async def get_session_events(
        self,
        session_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[Any]: ...


logger = logging.getLogger(__name__)


def _default_org_context(org_id: UUID, user_id: UUID) -> OrganizationContext:
    """Build a minimal OrganizationContext when the caller doesn't supply one."""
    return OrganizationContext(
        user_id=user_id,
        org_id=org_id,
        org_tier="platform",
        org_path=str(org_id),
    )


@dataclass(frozen=True)
class ConversationTurn:
    """A single conversation turn (request + response)."""

    turn_id: UUID
    session_id: UUID
    user_message: str
    assistant_response: str
    context: AssembledContext
    tokens_used: dict[str, int] = field(default_factory=dict)
    model_id: str = ""
    intent_type: str = "chat"


class ConversationEngine:
    """Core conversation engine implementing the Brain's main loop.

    Flow:
    1. User message arrives
    2. Intent classification (B2-2)
    3. Context assembly (B2-3/B2-4)
    4. LLM call via LLMCallPort
    5. Memory write pipeline (B2-5) -- async, non-blocking
    6. Return response

    Ports used (all via dependency injection):
    - MemoryCorePort (hard dependency)
    - LLMCallPort (hard dependency)
    - KnowledgePort (soft dependency, degradable)
    """

    def __init__(
        self,
        *,
        llm: LLMCallProtocol,
        memory_core: MemoryCorePort,
        knowledge: KnowledgePort | None = None,
        intent_classifier: IntentClassifier | None = None,
        memory_pipeline: MemoryWritePipeline | None = None,
        usage_tracker: UsageRecorder | None = None,
        event_store: EventStoreProtocol | None = None,
        receipt_store: ReceiptStoreProtocol | None = None,
        skill_orchestrator: SkillOrchestrator | None = None,
        default_model: str = "gpt-4o",
    ) -> None:
        self._llm = llm
        self._memory_core = memory_core
        self._knowledge = knowledge
        self._intent_classifier = intent_classifier
        self._memory_pipeline = memory_pipeline
        self._usage_tracker = usage_tracker
        self._event_store = event_store
        self._skill_orchestrator = skill_orchestrator
        self._default_model = default_model
        self._context_assembler = ContextAssembler(
            memory_core=memory_core,
            knowledge=knowledge,
            receipt_store=receipt_store,
        )

    async def process_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
        message: str,
        org_context: OrganizationContext | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        model_id: str | None = None,
    ) -> ConversationTurn:
        """Process a user message and return assistant response.

        This is the main entry point for the conversation loop.
        """
        turn_id = uuid4()

        # Step 1: Intent classification (use detailed result for skill hint)
        intent_type = "chat"
        matched_skill_hint: str | None = None
        if self._intent_classifier:
            intent_result = await self._intent_classifier.classify_detailed(message)
            intent_type = intent_result.intent_type
            matched_skill_hint = intent_result.matched_skill

        # Step 2: Skill orchestration (if intent != chat and orchestrator available)
        skill_response_text: str | None = None
        resolved_model = model_id or self._default_model

        if intent_type != "chat" and self._skill_orchestrator:
            try:
                orch_result = await self._skill_orchestrator.orchestrate(
                    intent_type=intent_type,
                    org_context=org_context or _default_org_context(org_id, user_id),
                    user_message=message,
                    matched_skill_hint=matched_skill_hint,
                )
                if orch_result.executed and orch_result.skill_result:
                    if orch_result.skill_result.success:
                        skill_response_text = str(orch_result.skill_result.output or "")
                    else:
                        logger.warning(
                            "Skill '%s' failed: %s, falling back to LLM",
                            orch_result.skill_id,
                            orch_result.skill_result.error,
                        )
            except Exception:
                logger.warning(
                    "Skill orchestration failed, falling back to LLM",
                    exc_info=True,
                )

        # Step 3: Context assembly
        context = await self._context_assembler.assemble(
            user_id=user_id,
            query=message,
            org_context=org_context,
            conversation_history=conversation_history,
        )

        if skill_response_text is not None:
            # Skill produced a response -- skip LLM call
            response_text = skill_response_text
            tokens_used: dict[str, int] = {}
            response_model_id = f"skill:{intent_type}"
        else:
            # Step 4: Build messages for LLM
            messages = self._build_llm_messages(
                message=message,
                context=context,
                conversation_history=conversation_history,
            )

            # Step 5: Call LLM
            llm_response = await self._llm.call(
                prompt=messages,
                model_id=resolved_model,
            )
            response_text = llm_response.text
            tokens_used = llm_response.tokens_used
            response_model_id = llm_response.model_id

        # Step 6: Record usage (zero metering loss)
        if self._usage_tracker and tokens_used:
            self._usage_tracker.record_usage(
                org_id=org_id,
                user_id=user_id,
                model_id=response_model_id or resolved_model,
                input_tokens=tokens_used.get("input", 0),
                output_tokens=tokens_used.get("output", 0),
            )

        # Step 7: Persist conversation events (non-blocking)
        if self._event_store:
            try:
                await self._event_store.append_event(
                    org_id=org_id,
                    session_id=session_id,
                    user_id=user_id,
                    event_type="user_message",
                    role="user",
                    content={"text": message},
                )
                await self._event_store.append_event(
                    org_id=org_id,
                    session_id=session_id,
                    user_id=user_id,
                    event_type="assistant_message",
                    role="assistant",
                    content={"text": response_text},
                )
            except Exception:
                logger.warning(
                    "Event store write failed (non-blocking)",
                    exc_info=True,
                )

        # Step 8: Memory write pipeline (async, non-blocking)
        if self._memory_pipeline:
            try:
                await self._memory_pipeline.process_turn(
                    session_id=session_id,
                    user_id=user_id,
                    org_id=org_id,
                    user_message=message,
                    assistant_response=response_text,
                )
            except Exception:
                logger.warning(
                    "Memory pipeline failed (non-blocking)",
                    exc_info=True,
                )

        return ConversationTurn(
            turn_id=turn_id,
            session_id=session_id,
            user_message=message,
            assistant_response=response_text,
            context=context,
            tokens_used=tokens_used,
            model_id=response_model_id,
            intent_type=intent_type,
        )

    async def get_session_history(
        self,
        session_id: UUID,
    ) -> list[dict[str, Any]]:
        """Load conversation history from the event store.

        Returns list of {"role": ..., "content": ...} dicts suitable for
        passing as conversation_history to process_message().
        Returns [] if no event_store is configured or the session is empty.
        """
        if not self._event_store:
            return []

        events = await self._event_store.get_session_events(session_id)
        history: list[dict[str, Any]] = []
        for event in events:
            role = getattr(event, "role", None) or event.get("role", "user")
            content_obj = getattr(event, "content", None) or event.get("content", {})
            if isinstance(content_obj, dict):
                text = content_obj.get("text", "")
            else:
                text = str(content_obj)
            history.append({"role": role, "content": text})
        return history

    def _build_llm_messages(
        self,
        message: str,
        context: AssembledContext,
        conversation_history: list[dict[str, Any]] | None,
    ) -> str:
        """Build the prompt string for LLM call.

        Combines system prompt, conversation history, and user message.
        """
        parts: list[str] = []

        if context.system_prompt:
            parts.append(f"System: {context.system_prompt}")

        if conversation_history:
            for msg in conversation_history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role.capitalize()}: {content}")

        parts.append(f"User: {message}")

        return "\n\n".join(parts)
