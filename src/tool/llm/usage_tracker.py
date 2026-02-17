"""Token metering -- tracks LLM usage per org/user.

Task card: T2-3
- Write prompt/completion tokens after each LLM call
- Zero metering loss: every call recorded
- Supports pre-check (budget) and post-settle

Architecture: delivery/phase2-runtime-config.yaml (billing section)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UsageRecord:
    """A single LLM usage record."""

    id: UUID
    org_id: UUID
    user_id: UUID
    model_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    created_at: datetime


@dataclass
class UsageSummary:
    """Aggregated usage summary for an org."""

    org_id: UUID
    total_input: int = 0
    total_output: int = 0
    total_tokens: int = 0
    record_count: int = 0


class UsageTracker:
    """In-memory usage tracker for unit testing.

    Production implementation uses llm_usage_records table via SQLAlchemy.
    """

    def __init__(self) -> None:
        self._records: dict[UUID, UsageRecord] = {}
        self._by_org: dict[UUID, list[UUID]] = {}
        self._by_user: dict[UUID, list[UUID]] = {}
        self._budgets: dict[UUID, int] = {}

    def record_usage(
        self,
        *,
        org_id: UUID,
        user_id: UUID,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> UsageRecord:
        """Record token usage from an LLM call.

        Must be called after every successful LLM call.
        Zero metering loss: failures are logged, never silently dropped.
        """
        record = UsageRecord(
            id=uuid4(),
            org_id=org_id,
            user_id=user_id,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            created_at=datetime.now(UTC),
        )

        self._records[record.id] = record
        self._by_org.setdefault(org_id, []).append(record.id)
        self._by_user.setdefault(user_id, []).append(record.id)

        logger.debug(
            "Recorded usage: org=%s user=%s model=%s tokens=%d",
            org_id,
            user_id,
            model_id,
            record.total_tokens,
        )
        return record

    def get_org_summary(self, org_id: UUID) -> UsageSummary:
        """Get aggregated usage summary for an organization."""
        record_ids = self._by_org.get(org_id, [])
        summary = UsageSummary(org_id=org_id)

        for rid in record_ids:
            record = self._records.get(rid)
            if record:
                summary.total_input += record.input_tokens
                summary.total_output += record.output_tokens
                summary.total_tokens += record.total_tokens
                summary.record_count += 1

        return summary

    def set_budget(self, org_id: UUID, monthly_tokens: int) -> None:
        """Set a monthly token budget for an organization."""
        self._budgets[org_id] = monthly_tokens

    def check_budget(self, org_id: UUID, estimated_tokens: int) -> bool:
        """Pre-check: verify org has sufficient budget for estimated usage.

        Returns True if call should proceed, False if budget exceeded.
        """
        budget = self._budgets.get(org_id)
        if budget is None:
            return True  # No budget set = unlimited

        summary = self.get_org_summary(org_id)
        return (summary.total_tokens + estimated_tokens) <= budget

    def get_records_for_org(
        self,
        org_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[UsageRecord]:
        """Get usage records for an org, newest first."""
        record_ids = self._by_org.get(org_id, [])
        records = [self._records[rid] for rid in reversed(record_ids) if rid in self._records]
        if limit is not None:
            records = records[:limit]
        return records


@dataclass
class MeteringLossTracker:
    """Tracks metering failures to ensure zero loss.

    Any failure to record usage is logged and counted.
    The count must remain 0 for the metering guarantee.
    """

    lost_count: int = 0
    _failures: list[dict[str, str]] = field(default_factory=list)

    def record_failure(
        self,
        *,
        org_id: UUID,
        user_id: UUID,
        model_id: str,
        reason: str,
    ) -> None:
        """Record a metering failure."""
        self.lost_count += 1
        self._failures.append(
            {
                "org_id": str(org_id),
                "user_id": str(user_id),
                "model_id": model_id,
                "reason": reason,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        logger.error(
            "METERING LOSS: org=%s model=%s reason=%s (total_lost=%d)",
            org_id,
            model_id,
            reason,
            self.lost_count,
        )
