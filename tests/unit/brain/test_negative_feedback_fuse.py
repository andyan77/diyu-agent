"""B3-4: Negative feedback fuse tests.

Tests: 3 negations -> fuse, fused memory not injected (confidence=0),
reset, configurable threshold.
"""

from __future__ import annotations

from uuid import uuid4

from src.brain.memory.feedback import NegativeFeedbackFuse


class TestFuseAfterThreshold:
    def test_not_fused_before_threshold(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        mid = uuid4()
        fuse.record_negative(mid)
        fuse.record_negative(mid)
        assert fuse.is_fused(mid) is False

    def test_fused_at_threshold(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        mid = uuid4()
        for _ in range(3):
            result = fuse.record_negative(mid)
        assert result.fused is True
        assert result.confidence == 0.0
        assert fuse.is_fused(mid) is True

    def test_fused_beyond_threshold(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        mid = uuid4()
        for _ in range(5):
            fuse.record_negative(mid)
        assert fuse.is_fused(mid) is True

    def test_configurable_threshold(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=1)
        mid = uuid4()
        result = fuse.record_negative(mid)
        assert result.fused is True


class TestConfidenceZeroAfterFuse:
    def test_effective_confidence_zero_when_fused(self) -> None:
        """Task card: fused memory injection rate = 0%."""
        fuse = NegativeFeedbackFuse(threshold=3)
        mid = uuid4()
        for _ in range(3):
            fuse.record_negative(mid)

        effective = fuse.get_effective_confidence(mid, original_confidence=0.95)
        assert effective == 0.0

    def test_effective_confidence_preserved_when_not_fused(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        mid = uuid4()
        fuse.record_negative(mid)
        effective = fuse.get_effective_confidence(mid, original_confidence=0.8)
        assert effective == 0.8

    def test_unknown_memory_preserves_confidence(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        mid = uuid4()
        effective = fuse.get_effective_confidence(mid, original_confidence=0.9)
        assert effective == 0.9


class TestMultipleMemories:
    def test_independent_tracking(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        m1, m2 = uuid4(), uuid4()
        for _ in range(3):
            fuse.record_negative(m1)
        fuse.record_negative(m2)

        assert fuse.is_fused(m1) is True
        assert fuse.is_fused(m2) is False

    def test_fused_memories_set(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=2)
        m1, m2, m3 = uuid4(), uuid4(), uuid4()
        for _ in range(2):
            fuse.record_negative(m1)
            fuse.record_negative(m2)
        fuse.record_negative(m3)

        fused = fuse.fused_memories
        assert m1 in fused
        assert m2 in fused
        assert m3 not in fused


class TestReset:
    def test_reset_clears_fuse(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        mid = uuid4()
        for _ in range(3):
            fuse.record_negative(mid)
        assert fuse.is_fused(mid) is True

        fuse.reset(mid)
        assert fuse.is_fused(mid) is False
        assert fuse.get_effective_confidence(mid, 0.9) == 0.9

    def test_reset_unknown_memory_no_error(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        fuse.reset(uuid4())  # Should not raise


class TestDegradingConfidence:
    def test_confidence_degrades_before_fuse(self) -> None:
        fuse = NegativeFeedbackFuse(threshold=3)
        mid = uuid4()
        r1 = fuse.record_negative(mid)
        r2 = fuse.record_negative(mid)
        # Before threshold, confidence degrades but stays > 0
        assert r1.confidence > 0
        assert r2.confidence > 0
        assert r2.confidence < r1.confidence
