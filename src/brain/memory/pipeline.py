"""Memory write pipeline integration for Brain layer.

Task cards: B2-5 (write pipeline), B2-6 (receipts)
- Three-stage async pipeline: extract observation -> analyze -> write
- Non-blocking: failures don't interrupt conversation response
- Records injection/retrieval receipts

Architecture: Section 2.2 (Memory Write Pipeline)
             ADR-038 (Receipt structure)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.memory.evolution.pipeline import EvolutionPipeline
from src.memory.receipt import ReceiptStore, ReceiptStoreProtocol
from src.shared.types import Observation

if TYPE_CHECKING:
    from uuid import UUID

    from src.ports.memory_core_port import MemoryCorePort

logger = logging.getLogger(__name__)


class MemoryWritePipeline:
    """Brain-layer integration of the memory evolution pipeline.

    Wraps the MC-layer EvolutionPipeline and adds:
    - Conversation turn processing
    - Receipt recording for injections/retrievals
    - Non-blocking error handling (failures logged, never propagated)

    B2-5: Observer -> Analyzer -> Evolver chain
    B2-6: injection_receipt + retrieval_receipt recording
    """

    def __init__(
        self,
        memory_core: MemoryCorePort,
        receipt_store: ReceiptStoreProtocol | None = None,
        evolution_pipeline: EvolutionPipeline | None = None,
    ) -> None:
        self._memory_core = memory_core
        self._receipt_store: ReceiptStoreProtocol = receipt_store or ReceiptStore()
        self._evolution_pipeline = evolution_pipeline or EvolutionPipeline()

    async def process_turn(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
        user_message: str,
        assistant_response: str,
    ) -> list[dict[str, Any]]:
        """Process a conversation turn through the memory pipeline.

        1. Run evolution pipeline on the turn messages
        2. Write observations to MemoryCore
        3. Record receipts for each write

        Returns list of result dicts (for logging/debugging).
        """
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response},
        ]

        # Run evolution pipeline
        results = await self._evolution_pipeline.process_session(
            session_id=session_id,
            messages=messages,
        )

        write_results: list[dict[str, Any]] = []

        for result in results:
            if result.action == "skipped":
                write_results.append(
                    {
                        "observation_id": str(result.observation_id),
                        "action": "skipped",
                    }
                )
                continue

            # Write to MemoryCore
            try:
                receipt = await self._memory_core.write_observation(
                    user_id=user_id,
                    observation=Observation(
                        content=user_message,
                        memory_type="observation",
                        source_session_id=session_id,
                        confidence=0.6,
                    ),
                    org_id=org_id,
                )

                # Record injection receipt
                if self._receipt_store:
                    await self._receipt_store.record_injection(
                        memory_item_id=receipt.memory_id,
                        org_id=org_id,
                        candidate_score=0.6,
                        decision_reason="Auto-extracted from conversation",
                        policy_version="v1",
                    )

                write_results.append(
                    {
                        "observation_id": str(result.observation_id),
                        "action": result.action,
                        "memory_id": str(receipt.memory_id),
                        "version": receipt.version,
                    }
                )

            except Exception:
                logger.warning(
                    "Failed to write observation %s",
                    result.observation_id,
                    exc_info=True,
                )
                write_results.append(
                    {
                        "observation_id": str(result.observation_id),
                        "action": "error",
                    }
                )

        return write_results

    async def record_retrieval_receipt(
        self,
        *,
        memory_item_id: UUID,
        org_id: UUID,
        candidate_score: float,
        context_position: int,
    ) -> None:
        """Record a retrieval receipt when memories are injected into context.

        Called by ContextAssembler when memories are used in a prompt.
        """
        if self._receipt_store:
            await self._receipt_store.record_retrieval(
                memory_item_id=memory_item_id,
                org_id=org_id,
                candidate_score=candidate_score,
                decision_reason="Retrieved for context injection",
                policy_version="v1",
                context_position=context_position,
            )
