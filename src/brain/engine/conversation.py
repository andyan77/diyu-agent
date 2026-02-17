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

if TYPE_CHECKING:
    from src.brain.intent.classifier import IntentClassifier
    from src.brain.memory.pipeline import MemoryWritePipeline
    from src.ports.knowledge_port import KnowledgePort
    from src.ports.llm_call_port import LLMCallPort
    from src.ports.memory_core_port import MemoryCorePort
    from src.shared.types import OrganizationContext


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


logger = logging.getLogger(__name__)


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
        llm: LLMCallPort,
        memory_core: MemoryCorePort,
        knowledge: KnowledgePort | None = None,
        intent_classifier: IntentClassifier | None = None,
        memory_pipeline: MemoryWritePipeline | None = None,
        usage_tracker: UsageRecorder | None = None,
        default_model: str = "gpt-4o",
    ) -> None:
        self._llm = llm
        self._memory_core = memory_core
        self._knowledge = knowledge
        self._intent_classifier = intent_classifier
        self._memory_pipeline = memory_pipeline
        self._usage_tracker = usage_tracker
        self._default_model = default_model
        self._context_assembler = ContextAssembler(
            memory_core=memory_core,
            knowledge=knowledge,
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

        # Step 1: Intent classification
        intent_type = "chat"
        if self._intent_classifier:
            intent_type = await self._intent_classifier.classify(message)

        # Step 2: Context assembly
        context = await self._context_assembler.assemble(
            user_id=user_id,
            query=message,
            org_context=org_context,
            conversation_history=conversation_history,
        )

        # Step 3: Build messages for LLM
        messages = self._build_llm_messages(
            message=message,
            context=context,
            conversation_history=conversation_history,
        )

        # Step 4: Call LLM
        resolved_model = model_id or self._default_model
        llm_response = await self._llm.call(
            prompt=messages,
            model_id=resolved_model,
        )

        # Step 5: Record usage (zero metering loss)
        if self._usage_tracker:
            self._usage_tracker.record_usage(
                org_id=org_id,
                user_id=user_id,
                model_id=llm_response.model_id or resolved_model,
                input_tokens=llm_response.tokens_used.get("input", 0),
                output_tokens=llm_response.tokens_used.get("output", 0),
            )

        # Step 6: Memory write pipeline (async, non-blocking)
        if self._memory_pipeline:
            try:
                await self._memory_pipeline.process_turn(
                    session_id=session_id,
                    user_id=user_id,
                    org_id=org_id,
                    user_message=message,
                    assistant_response=llm_response.text,
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
            assistant_response=llm_response.text,
            context=context,
            tokens_used=llm_response.tokens_used,
            model_id=llm_response.model_id,
            intent_type=intent_type,
        )

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
