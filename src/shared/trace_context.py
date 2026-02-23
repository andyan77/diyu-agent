"""Trace-id propagation via contextvars.

Task card: OS4-4
- Gateway sets trace_id on request entry
- All layers read it via get_trace_id() for structured logging & metrics
- Uses Python contextvars: zero dependency, async-safe

Architecture: Section 7 (Observability)
"""

from __future__ import annotations

from collections.abc import Generator  # noqa: TC003 -- used at runtime by contextmanager
from contextlib import contextmanager
from contextvars import ContextVar, Token
from uuid import uuid4

# The single ContextVar holding the current trace_id string.
current_trace_id: ContextVar[str] = ContextVar("current_trace_id", default="")


def get_trace_id() -> str:
    """Return the current trace_id (empty string if not set)."""
    return current_trace_id.get()


def set_trace_id(trace_id: str) -> Token[str]:
    """Set the trace_id for the current context. Returns a reset token."""
    return current_trace_id.set(trace_id)


@contextmanager
def trace_context(trace_id: str | None = None) -> Generator[str, None, None]:
    """Scoped trace_id context manager.

    Sets trace_id for the duration of the `with` block, then restores
    the previous value on exit. If trace_id is None or empty, a new
    UUID4 is auto-generated.

    Usage::

        with trace_context("req-abc") as tid:
            # get_trace_id() == "req-abc"
            ...
        # previous trace_id is restored
    """
    effective_id = trace_id if trace_id else str(uuid4())
    token = current_trace_id.set(effective_id)
    try:
        yield effective_id
    finally:
        current_trace_id.reset(token)
