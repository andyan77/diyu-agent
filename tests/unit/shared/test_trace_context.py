"""Tests for trace_id propagation via contextvars.

Task card: OS4-4 (foundation)
- trace_id set at Gateway entry, propagated through Brain -> Memory -> Knowledge
- Uses contextvars for zero-dependency propagation
- Auto-generates UUID4 trace_id if not provided
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest

from src.shared.trace_context import (
    current_trace_id,
    get_trace_id,
    set_trace_id,
    trace_context,
)


class TestGetSetTraceId:
    """Basic get/set operations on the trace_id context var."""

    def test_get_returns_empty_string_by_default(self) -> None:
        """Default trace_id is empty string when not set."""
        # Reset for test isolation
        set_trace_id("")
        assert get_trace_id() == ""

    def test_set_and_get(self) -> None:
        tid = "abc-123"
        set_trace_id(tid)
        assert get_trace_id() == tid

    def test_set_overwrites_previous(self) -> None:
        set_trace_id("first")
        set_trace_id("second")
        assert get_trace_id() == "second"


class TestTraceContextManager:
    """The trace_context() context manager for scoped trace_id."""

    def test_sets_trace_id_within_scope(self) -> None:
        with trace_context("scope-1"):
            assert get_trace_id() == "scope-1"

    def test_restores_previous_on_exit(self) -> None:
        set_trace_id("outer")
        with trace_context("inner"):
            assert get_trace_id() == "inner"
        assert get_trace_id() == "outer"

    def test_auto_generates_uuid_when_none(self) -> None:
        with trace_context() as tid:
            assert tid != ""
            # Should be valid UUID4
            UUID(tid, version=4)
            assert get_trace_id() == tid

    def test_auto_generates_uuid_when_empty_string(self) -> None:
        with trace_context("") as tid:
            assert tid != ""
            UUID(tid, version=4)

    def test_nested_contexts(self) -> None:
        with trace_context("level-1"):
            assert get_trace_id() == "level-1"
            with trace_context("level-2"):
                assert get_trace_id() == "level-2"
            assert get_trace_id() == "level-1"


class TestCurrentTraceId:
    """current_trace_id is a convenience alias for the ContextVar."""

    def test_is_the_same_context_var(self) -> None:
        set_trace_id("via-setter")
        assert current_trace_id.get() == "via-setter"


class TestAsyncPropagation:
    """trace_id propagates correctly across async tasks."""

    @pytest.mark.asyncio
    async def test_propagates_in_same_coroutine(self) -> None:
        set_trace_id("async-1")
        await asyncio.sleep(0)
        assert get_trace_id() == "async-1"

    @pytest.mark.asyncio
    async def test_isolated_across_tasks(self) -> None:
        """Each asyncio.Task gets a copy of the context."""
        set_trace_id("parent")

        async def child() -> str:
            set_trace_id("child")
            return get_trace_id()

        # Run child task — it should see its own copy
        result = await asyncio.create_task(child())
        assert result == "child"
        # Parent should still see "parent"
        assert get_trace_id() == "parent"
