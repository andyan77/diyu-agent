"""Unit tests for confidence_effective decay (MC2-7).

Complies with no-mock policy.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.memory.confidence import confidence_effective, is_stale

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfidenceDecay:
    """MC2-7: confidence_effective decay formula."""

    def test_no_decay_at_creation(self) -> None:
        now = datetime.now(UTC)
        result = confidence_effective(1.0, valid_at=now, now=now)
        assert abs(result - 1.0) < 1e-9

    def test_half_life_decay(self) -> None:
        """After exactly half_life_days, confidence should be ~0.5 of base."""
        base = datetime.now(UTC)
        half_life = 90.0
        future = base + timedelta(days=half_life)

        result = confidence_effective(
            1.0,
            valid_at=base,
            now=future,
            half_life_days=half_life,
        )
        assert abs(result - 0.5) < 0.01

    def test_30_day_decay_observable(self) -> None:
        """After 30 days, decay must be measurably observable."""
        base = datetime.now(UTC)
        after_30d = base + timedelta(days=30)

        original = 1.0
        decayed = confidence_effective(
            original,
            valid_at=base,
            now=after_30d,
        )
        assert decayed < original
        assert decayed > 0.5  # Shouldn't decay too much in 30 days

    def test_long_term_approaches_zero(self) -> None:
        """After very long time, confidence approaches zero."""
        base = datetime.now(UTC)
        far_future = base + timedelta(days=365 * 5)

        result = confidence_effective(1.0, valid_at=base, now=far_future)
        assert result < 0.01

    def test_last_validated_at_resets_decay(self) -> None:
        """Validating a memory resets the decay baseline."""
        base = datetime.now(UTC)
        validated = base + timedelta(days=60)
        check = base + timedelta(days=90)

        # Without validation: 90 days of decay
        without = confidence_effective(1.0, valid_at=base, now=check)

        # With validation at day 60: only 30 days of decay
        with_val = confidence_effective(
            1.0,
            valid_at=base,
            last_validated_at=validated,
            now=check,
        )

        assert with_val > without

    def test_zero_base_stays_zero(self) -> None:
        base = datetime.now(UTC)
        future = base + timedelta(days=30)
        result = confidence_effective(0.0, valid_at=base, now=future)
        assert result == 0.0

    def test_decay_with_different_half_lives(self) -> None:
        """Shorter half-life decays faster."""
        base = datetime.now(UTC)
        future = base + timedelta(days=30)

        fast = confidence_effective(
            1.0,
            valid_at=base,
            now=future,
            half_life_days=30,
        )
        slow = confidence_effective(
            1.0,
            valid_at=base,
            now=future,
            half_life_days=180,
        )
        assert fast < slow


@pytest.mark.unit
class TestIsStale:
    """MC2-7: staleness detection."""

    def test_fresh_memory_not_stale(self) -> None:
        now = datetime.now(UTC)
        assert is_stale(1.0, valid_at=now, now=now) is False

    def test_old_memory_is_stale(self) -> None:
        base = datetime.now(UTC)
        far_future = base + timedelta(days=365)
        assert is_stale(1.0, valid_at=base, now=far_future) is True

    def test_custom_threshold(self) -> None:
        base = datetime.now(UTC)
        future = base + timedelta(days=90)  # half-life point
        # At half-life, confidence ~= 0.5
        assert is_stale(1.0, valid_at=base, now=future, threshold=0.6) is True
        assert is_stale(1.0, valid_at=base, now=future, threshold=0.4) is False

    def test_validated_memory_not_stale(self) -> None:
        base = datetime.now(UTC)
        validated = base + timedelta(days=300)
        check = base + timedelta(days=310)
        # Only 10 days since validation
        assert (
            is_stale(
                1.0,
                valid_at=base,
                last_validated_at=validated,
                now=check,
            )
            is False
        )
