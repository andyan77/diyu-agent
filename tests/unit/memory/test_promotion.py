"""MC3-1: Promotion pipeline tests.

Tests: eligibility, sanitization, PII detection, proposal creation, approval flow.
Uses Fake adapter pattern (no unittest.mock).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.memory.promotion.pipeline import (
    PromotionPipeline,
    PromotionThresholds,
    sanitize_content,
)
from src.shared.types import MemoryItem


def _make_memory(
    *,
    confidence: float = 0.9,
    content: str = "Customer prefers cotton fabrics",
) -> MemoryItem:
    return MemoryItem(
        memory_id=uuid4(),
        user_id=uuid4(),
        memory_type="preference",
        content=content,
        valid_at=datetime.now(tz=UTC) - timedelta(days=30),
        confidence=confidence,
    )


class TestEligibility:
    def test_eligible_memory(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory(confidence=0.9)
        assert pipeline.is_eligible(memory, frequency_30d=5) is True

    def test_low_confidence_ineligible(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory(confidence=0.5)
        assert pipeline.is_eligible(memory, frequency_30d=5) is False

    def test_low_frequency_ineligible(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory(confidence=0.9)
        assert pipeline.is_eligible(memory, frequency_30d=1) is False

    def test_custom_thresholds(self) -> None:
        thresholds = PromotionThresholds(confidence_min=0.5, frequency_min_30d=1)
        pipeline = PromotionPipeline(thresholds=thresholds)
        memory = _make_memory(confidence=0.6)
        assert pipeline.is_eligible(memory, frequency_30d=2) is True


class TestSanitization:
    def test_clean_content(self) -> None:
        result = sanitize_content("Customer prefers cotton fabrics")
        assert result.is_clean is True
        assert result.sanitized_content == "Customer prefers cotton fabrics"
        assert result.violations == []

    def test_email_detected(self) -> None:
        result = sanitize_content("Contact john@example.com for details")
        assert result.is_clean is False
        assert "email_detected" in result.violations
        assert "[REDACTED_EMAIL]" in result.sanitized_content

    def test_phone_detected(self) -> None:
        result = sanitize_content("Call 555-123-4567 for info")
        assert result.is_clean is False
        assert "phone_detected" in result.violations
        assert "[REDACTED_PHONE]" in result.sanitized_content

    def test_credit_card_detected(self) -> None:
        result = sanitize_content("Card 4111-1111-1111-1111 on file")
        assert result.is_clean is False
        assert "credit_card_detected" in result.violations
        assert "[REDACTED_CC]" in result.sanitized_content

    def test_multiple_violations(self) -> None:
        result = sanitize_content("Email john@test.com phone 555-123-4567")
        assert result.is_clean is False
        assert len(result.violations) >= 2


class TestProposalCreation:
    @pytest.mark.asyncio
    async def test_clean_proposal_created(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory()
        receipt = await pipeline.create_proposal(
            memory,
            target_org_id=uuid4(),
            target_visibility="store",
        )
        assert receipt.status == "promoted"
        assert receipt.source_memory_id == memory.memory_id
        assert receipt.proposal_id is not None

    @pytest.mark.asyncio
    async def test_pii_proposal_fails(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory(content="Contact john@example.com")
        receipt = await pipeline.create_proposal(
            memory,
            target_org_id=uuid4(),
        )
        assert receipt.status == "sanitize_failed"
        assert "PII detected" in (receipt.rejection_reason or "")

    @pytest.mark.asyncio
    async def test_proposal_stored(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory()
        receipt = await pipeline.create_proposal(
            memory,
            target_org_id=uuid4(),
        )
        proposal = pipeline.get_proposal(receipt.proposal_id)
        assert proposal is not None
        assert proposal.status == "pending_approval"


class TestApprovalFlow:
    @pytest.mark.asyncio
    async def test_approve_proposal(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory()
        receipt = await pipeline.create_proposal(
            memory,
            target_org_id=uuid4(),
        )
        approval = await pipeline.approve_proposal(
            receipt.proposal_id,
            approver_id=uuid4(),
        )
        assert approval.status == "promoted"

    @pytest.mark.asyncio
    async def test_approve_nonexistent_raises(self) -> None:
        pipeline = PromotionPipeline()
        with pytest.raises(ValueError, match="Proposal not found"):
            await pipeline.approve_proposal(uuid4(), approver_id=uuid4())

    @pytest.mark.asyncio
    async def test_expired_proposal_rejected(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory()
        receipt = await pipeline.create_proposal(
            memory,
            target_org_id=uuid4(),
        )
        # Force expire
        proposal = pipeline.get_proposal(receipt.proposal_id)
        assert proposal is not None
        proposal.expires_at = datetime.now(tz=UTC) - timedelta(hours=1)

        result = await pipeline.approve_proposal(
            receipt.proposal_id,
            approver_id=uuid4(),
        )
        assert result.status == "expired"

    @pytest.mark.asyncio
    async def test_receipts_tracked(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory()
        await pipeline.create_proposal(memory, target_org_id=uuid4())
        receipts = pipeline.get_receipts()
        assert len(receipts) >= 1
