"""Performance baseline: Context Assembler P95 latency (B4-1).

Gate: p4-perf-baseline
Verifies: ContextAssembler.assemble() completes within P95 < 200ms
    at 10 concurrent calls (R-5 CI regression baseline).

Uses FakeMemoryCore (in-memory) — measures assembler overhead,
not network/database latency. Real-infra perf tests are separate
capacity-planning exercises (R-5 档位 2).

Design: Assembler calls memory_core + knowledge in parallel.
With in-memory fakes, P95 should be well under 200ms.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from uuid import uuid4

import pytest

from src.brain.engine.context_assembler import ContextAssembler
from tests.e2e.test_conversation_loop import FakeMemoryCore


@pytest.fixture()
def user_id():
    return uuid4()


@pytest.fixture()
def assembler():
    """Create assembler with FakeMemoryCore, no knowledge (degraded)."""
    memory_core = FakeMemoryCore()
    return ContextAssembler(memory_core=memory_core, knowledge=None)


@pytest.mark.perf
class TestAssemblerLatency:
    """Assembler latency benchmark (B4-1, R-5 CI baseline).

    P95 < 200ms at 10 concurrent calls with FakeMemoryCore.
    """

    @pytest.mark.asyncio
    async def test_single_call_under_200ms(
        self,
        assembler: ContextAssembler,
        user_id,
    ) -> None:
        """Single assemble() call completes under 200ms."""
        start = time.perf_counter()
        ctx = await assembler.assemble(
            user_id=user_id,
            query="test latency",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert ctx is not None
        assert elapsed_ms < 200, f"Single call took {elapsed_ms:.1f}ms (target: <200ms)"

    @pytest.mark.asyncio
    async def test_p95_under_200ms_10_concurrent(
        self,
        assembler: ContextAssembler,
        user_id,
    ) -> None:
        """P95 latency < 200ms across 10 concurrent assemble() calls."""
        latencies: list[float] = []

        async def timed_call() -> float:
            start = time.perf_counter()
            await assembler.assemble(
                user_id=user_id,
                query="concurrent latency test",
            )
            return (time.perf_counter() - start) * 1000

        # Run 10 concurrent calls
        tasks = [timed_call() for _ in range(10)]
        latencies = await asyncio.gather(*tasks)

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p50 = statistics.median(latencies)

        assert p95 < 200, (
            f"Assembler P95={p95:.1f}ms exceeds 200ms target "
            f"(P50={p50:.1f}ms, min={min(latencies):.1f}ms, max={max(latencies):.1f}ms)"
        )

    @pytest.mark.asyncio
    async def test_p95_under_200ms_50_sequential(
        self,
        assembler: ContextAssembler,
        user_id,
    ) -> None:
        """P95 latency < 200ms across 50 sequential assemble() calls.

        Sequential test to detect any memory leaks or accumulation issues.
        """
        latencies: list[float] = []

        for _ in range(50):
            start = time.perf_counter()
            await assembler.assemble(
                user_id=user_id,
                query="sequential latency test",
            )
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p50 = statistics.median(latencies)
        mean = statistics.mean(latencies)

        assert p95 < 200, (
            f"Sequential P95={p95:.1f}ms exceeds 200ms (mean={mean:.1f}ms, P50={p50:.1f}ms)"
        )

    @pytest.mark.asyncio
    async def test_enhanced_assembly_under_200ms(
        self,
        assembler: ContextAssembler,
        user_id,
    ) -> None:
        """CE-enhanced assemble_enhanced() also under 200ms."""
        start = time.perf_counter()
        ctx = await assembler.assemble_enhanced(
            user_id=user_id,
            query="enhanced assembly test",
            conversation_history=[
                {"role": "user", "content": "previous message"},
                {"role": "assistant", "content": "previous response"},
            ],
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert ctx is not None
        assert elapsed_ms < 200, f"Enhanced assembly took {elapsed_ms:.1f}ms (target: <200ms)"
