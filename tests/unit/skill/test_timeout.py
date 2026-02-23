"""Tests for S4-2: Skill execution timeout.

Task card: S4-2
- Skill execution > 30s → timeout (asyncio.wait_for)
- SkillTimeoutError raised on timeout
"""

from __future__ import annotations

import asyncio

import pytest

from src.skill.resilience.timeout import SkillTimeoutError, execute_with_timeout


class TestExecuteWithTimeout:
    """execute_with_timeout wraps async callables."""

    @pytest.mark.asyncio
    async def test_completes_within_timeout(self) -> None:
        async def fast_skill() -> str:
            return "ok"

        result = await execute_with_timeout(fast_skill(), timeout_seconds=1.0)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self) -> None:
        async def slow_skill() -> str:
            await asyncio.sleep(10)
            return "never"

        with pytest.raises(SkillTimeoutError):
            await execute_with_timeout(slow_skill(), timeout_seconds=0.01)

    @pytest.mark.asyncio
    async def test_propagates_exceptions(self) -> None:
        async def failing_skill() -> str:
            msg = "skill error"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="skill error"):
            await execute_with_timeout(failing_skill(), timeout_seconds=1.0)

    @pytest.mark.asyncio
    async def test_default_timeout(self) -> None:
        """Default timeout is 30s (doesn't actually wait that long)."""

        async def quick() -> str:
            return "fast"

        result = await execute_with_timeout(quick())
        assert result == "fast"
