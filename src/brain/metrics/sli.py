"""Brain layer 7 SLI metrics for Prometheus.

Task card: B4-4 / ADR-038
7 SLI metrics:
1. context_assembly_duration_seconds  — Context assembly latency
2. llm_call_duration_seconds          — LLM call latency
3. memory_write_duration_seconds      — Memory write pipeline latency
4. skill_execution_duration_seconds   — Skill execution latency
5. conversation_turn_duration_seconds — Full turn latency (gateway → response)
6. knowledge_resolution_duration_seconds — Knowledge resolution latency
7. memory_retrieval_count (hit/miss)  — Memory retrieval hit/miss counter

Architecture: Section 7 (Observability)
"""

from __future__ import annotations

import time
from collections.abc import Generator  # noqa: TC003 -- used at runtime by contextmanager
from contextlib import contextmanager
from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram

if TYPE_CHECKING:
    from prometheus_client import CollectorRegistry

# Latency buckets: 10ms to 10s (tuned for Brain layer operations)
_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0)


class BrainSLI:
    """Central registry for Brain layer SLI metrics.

    Pass a custom CollectorRegistry for testing isolation.
    In production, use the default global registry (registry=None).
    """

    def __init__(self, *, registry: CollectorRegistry | None = None) -> None:
        kw: dict = {}
        if registry is not None:
            kw["registry"] = registry

        self.context_assembly_duration = Histogram(
            "brain_context_assembly_duration_seconds",
            "Time spent assembling context (Memory + Knowledge)",
            buckets=_LATENCY_BUCKETS,
            **kw,
        )

        self.llm_call_duration = Histogram(
            "brain_llm_call_duration_seconds",
            "Time spent in LLM call (prompt → response)",
            buckets=_LATENCY_BUCKETS,
            **kw,
        )

        self.memory_write_duration = Histogram(
            "brain_memory_write_duration_seconds",
            "Time spent writing to memory pipeline",
            buckets=_LATENCY_BUCKETS,
            **kw,
        )

        self.skill_execution_duration = Histogram(
            "brain_skill_execution_duration_seconds",
            "Time spent executing a skill",
            buckets=_LATENCY_BUCKETS,
            **kw,
        )

        self.conversation_turn_duration = Histogram(
            "brain_conversation_turn_duration_seconds",
            "Total time for a full conversation turn",
            buckets=_LATENCY_BUCKETS,
            **kw,
        )

        self.knowledge_resolution_duration = Histogram(
            "brain_knowledge_resolution_duration_seconds",
            "Time spent resolving knowledge from KnowledgePort",
            buckets=_LATENCY_BUCKETS,
            **kw,
        )

        self.memory_retrieval_count = Counter(
            "brain_memory_retrieval_total",
            "Memory retrieval attempts",
            ["status"],
            **kw,
        )

    @contextmanager
    def timer(self, histogram: Histogram) -> Generator[None, None, None]:
        """Context manager that observes elapsed time on a histogram.

        Duration is always recorded, even if the block raises an exception.
        """
        start = time.monotonic()
        try:
            yield
        finally:
            histogram.observe(time.monotonic() - start)
