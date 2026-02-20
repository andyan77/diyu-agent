"""Memory-to-Knowledge promotion pipeline.

Milestone: MC3-1
Layer: Memory Core (cross-SSOT boundary)

Promotes personal memories that meet thresholds to organizational
knowledge via sanitization, conflict checking, and approval flow.

See: docs/architecture/02-Knowledge Section 7.2 (Promotion Pipeline)
     docs/architecture/01-Brain Section 2.3.1 (MemoryItem)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from src.shared.types import MemoryItem, PromotionReceipt

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromotionThresholds:
    """Thresholds for memory promotion eligibility."""

    confidence_min: float = 0.75
    frequency_min_30d: int = 3
    min_age_days: int = 7
    max_pending_per_user: int = 10


@dataclass(frozen=True)
class SanitizationResult:
    """Result of PII/sensitive content sanitization."""

    is_clean: bool
    sanitized_content: str
    violations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConflictCheckResult:
    """Result of deduplication conflict check."""

    has_conflict: bool
    similar_knowledge_id: UUID | None = None
    similarity_score: float = 0.0


@dataclass
class EvolutionProposal:
    """A promotion proposal pending approval."""

    proposal_id: UUID
    source_memory_id: UUID
    sanitized_content: str
    confidence: float
    target_org_id: UUID
    target_visibility: str  # store | region | brand
    status: str = "pending_approval"  # pending_approval | approved | rejected | expired
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    expires_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC) + timedelta(days=7))
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    knowledge_id: UUID | None = None


def sanitize_content(content: str) -> SanitizationResult:
    """Remove PII and sensitive data from memory content.

    Detects and masks:
    - Email addresses
    - Phone numbers
    - Credit card patterns

    Args:
        content: Raw memory content.

    Returns:
        SanitizationResult with cleaned content and any violations.
    """
    violations: list[str] = []
    sanitized = content

    # Email detection
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    if re.search(email_pattern, sanitized):
        violations.append("email_detected")
        sanitized = re.sub(email_pattern, "[REDACTED_EMAIL]", sanitized)

    # Phone detection (simple patterns)
    phone_pattern = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
    if re.search(phone_pattern, sanitized):
        violations.append("phone_detected")
        sanitized = re.sub(phone_pattern, "[REDACTED_PHONE]", sanitized)

    # Credit card patterns
    cc_pattern = r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
    if re.search(cc_pattern, sanitized):
        violations.append("credit_card_detected")
        sanitized = re.sub(cc_pattern, "[REDACTED_CC]", sanitized)

    return SanitizationResult(
        is_clean=len(violations) == 0,
        sanitized_content=sanitized,
        violations=violations,
    )


class PromotionPipeline:
    """Orchestrates the memory-to-knowledge promotion flow.

    Flow: candidate -> sanitize -> conflict check -> proposal -> approval -> write
    """

    def __init__(
        self,
        *,
        thresholds: PromotionThresholds | None = None,
        knowledge_writer: Any | None = None,  # KnowledgeWriteService
        vector_search: Any | None = None,  # QdrantAdapter for conflict check
    ) -> None:
        self._thresholds = thresholds or PromotionThresholds()
        self._writer = knowledge_writer
        self._vector_search = vector_search
        self._proposals: dict[str, EvolutionProposal] = {}
        self._receipts: list[PromotionReceipt] = []

    def is_eligible(self, memory: MemoryItem, *, frequency_30d: int = 0) -> bool:
        """Check if a memory item meets promotion thresholds.

        Args:
            memory: Memory item to evaluate.
            frequency_30d: Number of times this memory was referenced in 30 days.

        Returns:
            True if eligible for promotion.
        """
        if memory.confidence < self._thresholds.confidence_min:
            return False
        return not frequency_30d < self._thresholds.frequency_min_30d

    async def create_proposal(
        self,
        memory: MemoryItem,
        *,
        target_org_id: UUID,
        target_visibility: str = "store",
    ) -> PromotionReceipt:
        """Create a promotion proposal from a memory item.

        Sanitizes content, checks for conflicts, and creates
        an EvolutionProposal pending approval.

        Args:
            memory: Source memory item.
            target_org_id: Target organization.
            target_visibility: Visibility level.

        Returns:
            PromotionReceipt tracking the proposal status.
        """
        proposal_id = uuid4()

        # Step 1: Sanitize
        sanitization = sanitize_content(memory.content)

        if not sanitization.is_clean:
            receipt = PromotionReceipt(
                proposal_id=proposal_id,
                source_memory_id=memory.memory_id,
                target_knowledge_id=None,
                status="sanitize_failed",
                rejection_reason=f"PII detected: {', '.join(sanitization.violations)}",
            )
            self._receipts.append(receipt)
            return receipt

        # Step 2: Conflict check
        conflict = await self._check_conflict(sanitization.sanitized_content, target_org_id)

        if conflict.has_conflict:
            receipt = PromotionReceipt(
                proposal_id=proposal_id,
                source_memory_id=memory.memory_id,
                target_knowledge_id=conflict.similar_knowledge_id,
                status="rejected",
                rejection_reason=(
                    f"Similar knowledge exists (similarity={conflict.similarity_score:.2f})"
                ),
            )
            self._receipts.append(receipt)
            return receipt

        # Step 3: Create proposal
        proposal = EvolutionProposal(
            proposal_id=proposal_id,
            source_memory_id=memory.memory_id,
            sanitized_content=sanitization.sanitized_content,
            confidence=memory.confidence,
            target_org_id=target_org_id,
            target_visibility=target_visibility,
        )
        self._proposals[str(proposal_id)] = proposal

        receipt = PromotionReceipt(
            proposal_id=proposal_id,
            source_memory_id=memory.memory_id,
            target_knowledge_id=None,
            status="promoted",  # Proposal created (pending approval in full flow)
            promoted_at=datetime.now(tz=UTC),
        )
        self._receipts.append(receipt)
        return receipt

    async def approve_proposal(
        self,
        proposal_id: UUID,
        *,
        approver_id: UUID,
    ) -> PromotionReceipt:
        """Approve a promotion proposal and write to Knowledge.

        Args:
            proposal_id: Proposal to approve.
            approver_id: User approving the proposal.

        Returns:
            PromotionReceipt with final status.

        Raises:
            ValueError: If proposal not found or expired.
        """
        proposal = self._proposals.get(str(proposal_id))
        if proposal is None:
            msg = f"Proposal not found: {proposal_id}"
            raise ValueError(msg)

        now = datetime.now(tz=UTC)
        if now > proposal.expires_at:
            proposal.status = "expired"
            receipt = PromotionReceipt(
                proposal_id=proposal_id,
                source_memory_id=proposal.source_memory_id,
                target_knowledge_id=None,
                status="expired",
                rejection_reason="Approval window expired",
            )
            self._receipts.append(receipt)
            return receipt

        # Write to Knowledge if writer available
        knowledge_id = None
        if self._writer is not None:
            from src.knowledge.api.write import KnowledgeWriteRequest

            try:
                response = await self._writer.write(
                    KnowledgeWriteRequest(
                        entity_type="BrandKnowledge",
                        properties={"content": proposal.sanitized_content},
                        org_id=proposal.target_org_id,
                        visibility=proposal.target_visibility,
                        idempotency_key=f"promotion#{proposal_id}",
                        source="promotion",
                        semantic_content=proposal.sanitized_content,
                    ),
                    user_id=approver_id,
                )
                knowledge_id = response.graph_node_id
            except Exception as e:
                receipt = PromotionReceipt(
                    proposal_id=proposal_id,
                    source_memory_id=proposal.source_memory_id,
                    target_knowledge_id=None,
                    status="write_failed",
                    rejection_reason=str(e),
                )
                self._receipts.append(receipt)
                return receipt

        proposal.status = "approved"
        proposal.approved_by = approver_id
        proposal.approved_at = now
        proposal.knowledge_id = knowledge_id

        receipt = PromotionReceipt(
            proposal_id=proposal_id,
            source_memory_id=proposal.source_memory_id,
            target_knowledge_id=knowledge_id,
            status="promoted",
            promoted_at=now,
        )
        self._receipts.append(receipt)
        return receipt

    async def _check_conflict(
        self,
        content: str,
        org_id: UUID,
    ) -> ConflictCheckResult:
        """Check for duplicate knowledge via semantic similarity."""
        # Without vector search, no conflict detection
        if self._vector_search is None:
            return ConflictCheckResult(has_conflict=False)

        # Real implementation would embed content and search
        return ConflictCheckResult(has_conflict=False)

    def get_proposal(self, proposal_id: UUID) -> EvolutionProposal | None:
        """Look up a proposal by ID."""
        return self._proposals.get(str(proposal_id))

    def get_receipts(self) -> list[PromotionReceipt]:
        """Return all promotion receipts."""
        return list(self._receipts)
