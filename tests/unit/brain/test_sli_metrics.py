"""Tests for Brain 7 SLI instrumentation.

Task card: B4-4
- 7 SLI metrics exposed via prometheus_client
- context_assembly_duration_seconds (Histogram)
- llm_call_duration_seconds (Histogram)
- memory_write_duration_seconds (Histogram)
- skill_execution_duration_seconds (Histogram)
- conversation_turn_duration_seconds (Histogram)
- knowledge_resolution_duration_seconds (Histogram)
- memory_retrieval_count (Counter, labels: status=hit|miss)

Architecture: ADR-038
"""

from __future__ import annotations

import time

import pytest
from prometheus_client import CollectorRegistry

from src.brain.metrics.sli import BrainSLI


@pytest.fixture
def registry() -> CollectorRegistry:
    """Isolated Prometheus registry per test."""
    return CollectorRegistry()


@pytest.fixture
def sli(registry: CollectorRegistry) -> BrainSLI:
    """BrainSLI instance with isolated registry."""
    return BrainSLI(registry=registry)


class TestBrainSLICreation:
    """BrainSLI is constructable and registers all 7 metrics."""

    def test_creates_all_histograms(self, sli: BrainSLI) -> None:
        assert sli.context_assembly_duration is not None
        assert sli.llm_call_duration is not None
        assert sli.memory_write_duration is not None
        assert sli.skill_execution_duration is not None
        assert sli.conversation_turn_duration is not None
        assert sli.knowledge_resolution_duration is not None

    def test_creates_counter(self, sli: BrainSLI) -> None:
        assert sli.memory_retrieval_count is not None


class TestHistogramObserve:
    """Each histogram can record observations."""

    def test_context_assembly_observe(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        sli.context_assembly_duration.observe(0.15)
        # Verify sample exists
        samples = _get_samples(registry, "brain_context_assembly_duration_seconds")
        assert any(s.value > 0 for s in samples)

    def test_llm_call_observe(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        sli.llm_call_duration.observe(1.2)
        samples = _get_samples(registry, "brain_llm_call_duration_seconds")
        assert any(s.value > 0 for s in samples)

    def test_memory_write_observe(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        sli.memory_write_duration.observe(0.05)
        samples = _get_samples(registry, "brain_memory_write_duration_seconds")
        assert any(s.value > 0 for s in samples)

    def test_skill_execution_observe(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        sli.skill_execution_duration.observe(2.0)
        samples = _get_samples(registry, "brain_skill_execution_duration_seconds")
        assert any(s.value > 0 for s in samples)

    def test_conversation_turn_observe(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        sli.conversation_turn_duration.observe(3.5)
        samples = _get_samples(registry, "brain_conversation_turn_duration_seconds")
        assert any(s.value > 0 for s in samples)

    def test_knowledge_resolution_observe(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        sli.knowledge_resolution_duration.observe(0.08)
        samples = _get_samples(registry, "brain_knowledge_resolution_duration_seconds")
        assert any(s.value > 0 for s in samples)


class TestCounterIncrement:
    """memory_retrieval_count has hit/miss labels."""

    def test_hit_increment(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        sli.memory_retrieval_count.labels(status="hit").inc()
        samples = _get_samples(registry, "brain_memory_retrieval_total")
        hit_samples = [
            s for s in samples if s.labels.get("status") == "hit" and s.name.endswith("_total")
        ]
        assert any(s.value == 1.0 for s in hit_samples)

    def test_miss_increment(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        sli.memory_retrieval_count.labels(status="miss").inc(3)
        samples = _get_samples(registry, "brain_memory_retrieval_total")
        miss_samples = [
            s for s in samples if s.labels.get("status") == "miss" and s.name.endswith("_total")
        ]
        assert any(s.value == 3.0 for s in miss_samples)


class TestTimerContextManager:
    """BrainSLI.timer() context manager for auto-observing duration."""

    def test_timer_records_duration(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        with sli.timer(sli.context_assembly_duration):
            time.sleep(0.01)

        samples = _get_samples(registry, "brain_context_assembly_duration_seconds")
        sum_samples = [s for s in samples if s.name.endswith("_sum")]
        assert any(s.value >= 0.01 for s in sum_samples)

    def test_timer_records_on_exception(self, sli: BrainSLI, registry: CollectorRegistry) -> None:
        with pytest.raises(ValueError), sli.timer(sli.llm_call_duration):
            raise ValueError("boom")

        samples = _get_samples(registry, "brain_llm_call_duration_seconds")
        count_samples = [s for s in samples if s.name.endswith("_count")]
        assert any(s.value == 1.0 for s in count_samples)


def _get_samples(
    registry: CollectorRegistry,
    metric_name: str,
) -> list:
    """Collect all samples matching a metric name prefix."""
    result = []
    for metric in registry.collect():
        for sample in metric.samples:
            if sample.name.startswith(metric_name):
                result.append(sample)
    return result
