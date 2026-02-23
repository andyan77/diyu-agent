"""Skill execution timeout wrapper.

Task card: S4-2
- Wraps async skill execution with asyncio.wait_for
- Default timeout: 30 seconds
- Raises SkillTimeoutError on timeout

Architecture: Section 3 (Skill Layer Resilience)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Coroutine

T = TypeVar("T")

_DEFAULT_TIMEOUT = 30.0


class SkillTimeoutError(Exception):
    """Raised when a skill execution exceeds the timeout."""


async def execute_with_timeout(  # noqa: UP047
    coro: Coroutine[Any, Any, T],
    timeout_seconds: float = _DEFAULT_TIMEOUT,
) -> T:
    """Execute a coroutine with a timeout.

    Raises SkillTimeoutError if the coroutine doesn't complete
    within timeout_seconds.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except TimeoutError:
        raise SkillTimeoutError(f"Skill execution timed out after {timeout_seconds}s") from None
