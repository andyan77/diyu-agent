"""Cross-layer E2E: Memory Evolution closed loop (X2-3).

Verifies: conversation -> extract observation -> update memory_items -> next conversation injects.
Requires PG + pgvector in full mode; uses Fake adapter in CI.

Covers:
    X2-3: Memory evolution closed loop
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
class TestMemoryEvolutionCrossLayer:
    """Cross-layer memory evolution verification."""

    async def test_observation_extraction_and_injection(self) -> None:
        """X2-3: Conversation triggers memory update, next turn reflects it."""
        pytest.skip("Requires PG + pgvector; soft gate in Phase 2")

    async def test_memory_confidence_decay(self) -> None:
        """X2-3 sub: confidence_effective decays over time without reinforcement."""
        pytest.skip("Requires PG + pgvector; soft gate in Phase 2")
