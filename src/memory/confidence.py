"""Confidence effective decay calculation.

Task card: MC2-7
- Old memories' effective confidence decays over time
- 30 days after last validation -> observable decay
- Decay is read-only (computed at retrieval, not stored)

Architecture: ADR-042.2, Section 2.3.2.4
"""

from __future__ import annotations

import math
from datetime import UTC, datetime


def confidence_effective(
    base_confidence: float,
    valid_at: datetime,
    last_validated_at: datetime | None = None,
    now: datetime | None = None,
    half_life_days: float = 90.0,
) -> float:
    """Compute effective confidence with time-based decay.

    Uses exponential decay from the most recent validation point:
        effective = base * 2^(-days_since / half_life)

    Args:
        base_confidence: Stored confidence value [0, 1].
        valid_at: When the memory was created/last updated.
        last_validated_at: When the memory was last validated.
            If None, uses valid_at as baseline.
        now: Current time (for testing). Defaults to UTC now.
        half_life_days: Half-life in days (default 90).

    Returns:
        Effective confidence after decay [0, 1].
    """
    if now is None:
        now = datetime.now(UTC)

    # Use the most recent validation as decay baseline
    baseline = last_validated_at if last_validated_at is not None else valid_at

    # Ensure timezone-aware comparison
    if baseline.tzinfo is None:
        baseline = baseline.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    days_elapsed = (now - baseline).total_seconds() / 86400.0

    if days_elapsed <= 0:
        return base_confidence

    decay_factor = math.pow(2.0, -days_elapsed / half_life_days)
    return base_confidence * decay_factor


def is_stale(
    base_confidence: float,
    valid_at: datetime,
    last_validated_at: datetime | None = None,
    threshold: float = 0.3,
    now: datetime | None = None,
    half_life_days: float = 90.0,
) -> bool:
    """Check if a memory's effective confidence has decayed below threshold.

    Args:
        base_confidence: Stored confidence.
        valid_at: Creation time.
        last_validated_at: Last validation time.
        threshold: Staleness threshold (default 0.3).
        now: Current time (for testing).
        half_life_days: Decay half-life.

    Returns:
        True if effective confidence < threshold.
    """
    effective = confidence_effective(
        base_confidence,
        valid_at,
        last_validated_at=last_validated_at,
        now=now,
        half_life_days=half_life_days,
    )
    return effective < threshold
