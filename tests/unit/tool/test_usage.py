"""Tests for T2-3: Token metering.

Validates:
- Every LLM call recorded (zero metering loss)
- Usage aggregation per org
- Budget pre-check enforcement
- Record retrieval
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.tool.llm.usage_tracker import MeteringLossTracker, UsageTracker


@pytest.mark.unit
class TestUsageTracker:
    """T2-3: Token metering writes."""

    @pytest.fixture()
    def tracker(self) -> UsageTracker:
        return UsageTracker()

    def test_record_usage(self, tracker: UsageTracker) -> None:
        org_id = uuid4()
        user_id = uuid4()
        record = tracker.record_usage(
            org_id=org_id,
            user_id=user_id,
            model_id="gpt-4o",
            input_tokens=100,
            output_tokens=50,
        )
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150
        assert record.model_id == "gpt-4o"

    def test_org_summary(self, tracker: UsageTracker) -> None:
        org_id = uuid4()
        user_id = uuid4()
        tracker.record_usage(
            org_id=org_id,
            user_id=user_id,
            model_id="gpt-4o",
            input_tokens=100,
            output_tokens=50,
        )
        tracker.record_usage(
            org_id=org_id,
            user_id=user_id,
            model_id="gpt-4o",
            input_tokens=200,
            output_tokens=100,
        )
        summary = tracker.get_org_summary(org_id)
        assert summary.total_input == 300
        assert summary.total_output == 150
        assert summary.total_tokens == 450
        assert summary.record_count == 2

    def test_empty_org_summary(self, tracker: UsageTracker) -> None:
        summary = tracker.get_org_summary(uuid4())
        assert summary.total_tokens == 0
        assert summary.record_count == 0

    def test_budget_pre_check_passes(self, tracker: UsageTracker) -> None:
        org_id = uuid4()
        tracker.set_budget(org_id, 1000)
        assert tracker.check_budget(org_id, 500) is True

    def test_budget_pre_check_fails(self, tracker: UsageTracker) -> None:
        org_id = uuid4()
        user_id = uuid4()
        tracker.set_budget(org_id, 1000)
        tracker.record_usage(
            org_id=org_id,
            user_id=user_id,
            model_id="gpt-4o",
            input_tokens=800,
            output_tokens=100,
        )
        # Already used 900, trying to use 200 more = 1100 > 1000
        assert tracker.check_budget(org_id, 200) is False

    def test_no_budget_returns_true(self, tracker: UsageTracker) -> None:
        assert tracker.check_budget(uuid4(), 999999) is True

    def test_get_records_for_org(self, tracker: UsageTracker) -> None:
        org_id = uuid4()
        user_id = uuid4()
        tracker.record_usage(
            org_id=org_id,
            user_id=user_id,
            model_id="gpt-4o",
            input_tokens=10,
            output_tokens=5,
        )
        tracker.record_usage(
            org_id=org_id,
            user_id=user_id,
            model_id="gpt-4o-mini",
            input_tokens=20,
            output_tokens=10,
        )
        records = tracker.get_records_for_org(org_id)
        assert len(records) == 2
        # Newest first
        assert records[0].model_id == "gpt-4o-mini"

    def test_get_records_with_limit(self, tracker: UsageTracker) -> None:
        org_id = uuid4()
        user_id = uuid4()
        for i in range(5):
            tracker.record_usage(
                org_id=org_id,
                user_id=user_id,
                model_id=f"model-{i}",
                input_tokens=10,
                output_tokens=5,
            )
        records = tracker.get_records_for_org(org_id, limit=2)
        assert len(records) == 2

    def test_zero_metering_loss(self, tracker: UsageTracker) -> None:
        """Every call must be recorded -- no silent drops."""
        org_id = uuid4()
        user_id = uuid4()
        for _ in range(100):
            tracker.record_usage(
                org_id=org_id,
                user_id=user_id,
                model_id="gpt-4o",
                input_tokens=1,
                output_tokens=1,
            )
        summary = tracker.get_org_summary(org_id)
        assert summary.record_count == 100


@pytest.mark.unit
class TestMeteringLossTracker:
    """Metering loss monitoring."""

    def test_initial_zero_loss(self) -> None:
        tracker = MeteringLossTracker()
        assert tracker.lost_count == 0

    def test_record_failure_increments(self) -> None:
        tracker = MeteringLossTracker()
        tracker.record_failure(
            org_id=uuid4(),
            user_id=uuid4(),
            model_id="gpt-4o",
            reason="DB write failed",
        )
        assert tracker.lost_count == 1
