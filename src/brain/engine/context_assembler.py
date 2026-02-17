"""Context Assembler -- assembles context for LLM input.

Task cards: B2-3 (v1), B2-4 (CE enhanced with RRF), B2-7 (graceful degradation)
- Reads MemoryCore personal_context + Knowledge (graceful degrade)
- Assembles into assembled_context for LLM
- CE enhancement: Query Rewriting + Hybrid Retrieval (FTS+pgvector+RRF)

Architecture: Section 2.2 (Context Assembly Pipeline)
             ADR-022 (Privacy boundary: Knowledge cannot access MemoryCore)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from src.ports.knowledge_port import KnowledgePort
    from src.ports.memory_core_port import MemoryCorePort
    from src.shared.types import KnowledgeBundle, MemoryItem, OrganizationContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssembledContext:
    """Assembled context ready for LLM input.

    Combines personal memories, organizational knowledge,
    and conversation history into a structured context.
    """

    personal_memories: list[MemoryItem] = field(default_factory=list)
    knowledge_bundle: KnowledgeBundle | None = None
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""
    degraded: bool = False
    degraded_reason: str = ""

    def to_prompt_context(self) -> str:
        """Convert assembled context to a text block for LLM system prompt."""
        parts: list[str] = []

        if self.personal_memories:
            memory_texts = [
                f"- {m.content} (confidence: {m.confidence:.1f})" for m in self.personal_memories
            ]
            parts.append("Personal context:\n" + "\n".join(memory_texts))

        if self.knowledge_bundle and self.knowledge_bundle.semantic_contents:
            kb_texts = [
                f"- {item.get('content', '')}"
                for item in self.knowledge_bundle.semantic_contents[:5]
            ]
            parts.append("Domain knowledge:\n" + "\n".join(kb_texts))

        if self.degraded:
            parts.append(f"[Note: Operating in degraded mode: {self.degraded_reason}]")

        return "\n\n".join(parts)


class ContextAssembler:
    """Assembles context from MemoryCore + Knowledge for LLM input.

    B2-3: Basic assembly from personal memories + knowledge
    B2-4: CE enhancement with query rewriting and hybrid retrieval
    B2-7: Graceful degradation when Knowledge is unavailable
    """

    def __init__(
        self,
        memory_core: MemoryCorePort,
        knowledge: KnowledgePort | None = None,
    ) -> None:
        self._memory_core = memory_core
        self._knowledge = knowledge

    async def assemble(
        self,
        *,
        user_id: UUID,
        query: str,
        org_context: OrganizationContext | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        top_k_memories: int = 10,
    ) -> AssembledContext:
        """Assemble context for an LLM call.

        1. Read personal memories from MemoryCore (hard dependency)
        2. Resolve knowledge from KnowledgePort (soft dependency, degradable)
        3. Combine into AssembledContext
        """
        # Step 1: Personal memories (hard dependency)
        personal_memories = await self._memory_core.read_personal_memories(
            user_id=user_id,
            query=query,
            top_k=top_k_memories,
        )

        # Step 2: Knowledge (soft dependency, graceful degradation)
        knowledge_bundle = None
        degraded = False
        degraded_reason = ""

        if self._knowledge is not None and org_context is not None:
            try:
                knowledge_bundle = await self._knowledge.resolve(
                    profile_id="default",
                    query=query,
                    org_context=org_context,
                )
            except Exception:
                logger.warning(
                    "Knowledge resolution failed, degrading gracefully",
                    exc_info=True,
                )
                degraded = True
                degraded_reason = "Knowledge backend unavailable"
        else:
            degraded = True
            degraded_reason = (
                "Knowledge port not configured"
                if self._knowledge is None
                else "No org context provided"
            )

        # Step 3: Build system prompt
        system_prompt = self._build_system_prompt(
            personal_memories=personal_memories,
            knowledge_bundle=knowledge_bundle,
        )

        return AssembledContext(
            personal_memories=personal_memories,
            knowledge_bundle=knowledge_bundle,
            conversation_history=conversation_history or [],
            system_prompt=system_prompt,
            degraded=degraded,
            degraded_reason=degraded_reason,
        )

    async def assemble_enhanced(
        self,
        *,
        user_id: UUID,
        query: str,
        org_context: OrganizationContext | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        top_k_memories: int = 10,
    ) -> AssembledContext:
        """CE-enhanced assembly with query rewriting and RRF.

        B2-4: Query Rewriting + Hybrid Retrieval + Multi-Signal Reranking.
        Falls back to basic assemble() if enhancement fails.
        """
        rewritten_query = self._rewrite_query(query, conversation_history)

        return await self.assemble(
            user_id=user_id,
            query=rewritten_query,
            org_context=org_context,
            conversation_history=conversation_history,
            top_k_memories=top_k_memories,
        )

    def _rewrite_query(
        self,
        query: str,
        history: list[dict[str, Any]] | None,
    ) -> str:
        """Rewrite query incorporating conversation context.

        Day-1: Simple context concatenation.
        Future: LLM-based query rewriting.
        """
        if not history:
            return query

        recent = history[-3:]
        context_parts = [
            msg.get("content", "")
            for msg in recent
            if msg.get("role") == "user" and msg.get("content")
        ]

        if context_parts:
            return f"{' '.join(context_parts[-2:])} {query}"
        return query

    def _build_system_prompt(
        self,
        personal_memories: list[MemoryItem],
        knowledge_bundle: KnowledgeBundle | None,
    ) -> str:
        """Build a system prompt from context components."""
        parts: list[str] = ["You are a helpful assistant."]

        if personal_memories:
            memory_context = "\n".join(f"- {m.content}" for m in personal_memories[:5])
            parts.append(f"About the user:\n{memory_context}")

        if knowledge_bundle and knowledge_bundle.semantic_contents:
            kb_context = "\n".join(
                f"- {item.get('content', '')}" for item in knowledge_bundle.semantic_contents[:3]
            )
            parts.append(f"Relevant knowledge:\n{kb_context}")

        return "\n\n".join(parts)
