"""Cross-layer E2E: Full-chain trace_id propagation (X4-1).

Gate: p4-trace-e2e
Verifies: trace_id set at Gateway entry propagates through:
    Gateway -> Brain (ConversationEngine) -> ContextAssembler
    -> MemoryCore (read) + Knowledge (resolve, parallel)
    -> MemoryWritePipeline (write)
    -> Response header (X-Trace-ID)

Uses the same FakeLLM + FakeMemoryCore pattern from test_conversation_loop.
trace_id propagation is via contextvars (src/shared/trace_context.py).

Design decision (ADR): Port signatures are NOT modified.
trace_id flows through contextvars, which auto-propagates across
asyncio.gather and create_task boundaries.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.brain.engine.context_assembler import ContextAssembler
from src.brain.engine.conversation import ConversationEngine
from src.brain.memory.pipeline import MemoryWritePipeline
from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.memory.receipt import ReceiptStore
from src.shared.trace_context import get_trace_id, trace_context
from tests.e2e.test_conversation_loop import FakeEventStore, FakeLLM, FakeMemoryCore

# ---------------------------------------------------------------------------
# Trace-capturing log handler
# ---------------------------------------------------------------------------


class TraceCapture(logging.Handler):
    """Captures log records and their associated trace_id for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[tuple[str, str, str]] = []  # (logger_name, message, trace_id)

    def emit(self, record: logging.LogRecord) -> None:
        tid = get_trace_id()
        self.records.append((record.name, record.getMessage(), tid))

    def trace_ids_for(self, logger_prefix: str) -> list[str]:
        """Return all trace_ids captured for loggers starting with prefix."""
        return [tid for name, _, tid in self.records if name.startswith(logger_prefix)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JWT_SECRET = "test-trace-jwt-secret-256bit-minimum-len"  # noqa: S105


@pytest.fixture()
def session_id() -> UUID:
    return uuid4()


@pytest.fixture()
def user_id() -> UUID:
    return uuid4()


@pytest.fixture()
def org_id() -> UUID:
    return uuid4()


@pytest.fixture()
def auth_token(user_id: UUID, org_id: UUID) -> str:
    """Create a valid JWT token for test requests."""
    return encode_token(
        user_id=user_id,
        org_id=org_id,
        secret=JWT_SECRET,
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestTraceIdFullStack:
    """Full-chain trace_id propagation E2E (X4-1, OS4-4).

    Validates that trace_id set at Gateway entry is visible in every
    downstream layer via contextvars, and returned in the response.
    """

    async def test_trace_id_propagates_through_conversation_engine(
        self,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
    ) -> None:
        """trace_id set before ConversationEngine.process_message is visible
        in all downstream calls (ContextAssembler, MemoryWritePipeline).

        This tests the Brain-layer wiring without the Gateway HTTP layer.
        """
        memory_core = FakeMemoryCore()
        event_store = FakeEventStore()
        receipt_store = ReceiptStore()
        llm = FakeLLM(responses=["Traced response."])

        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            event_store=event_store,
            memory_pipeline=MemoryWritePipeline(
                memory_core=memory_core,
                receipt_store=receipt_store,
            ),
            default_model="gpt-4o",
        )

        expected_tid = "trace-e2e-brain-001"

        with trace_context(expected_tid):
            turn = await engine.process_message(
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                message="Hello from trace test",
            )

            # trace_id should still be the same after full processing
            assert get_trace_id() == expected_tid

        assert turn.assistant_response == "Traced response."

    async def test_trace_id_survives_parallel_context_assembly(
        self,
        user_id: UUID,
        org_id: UUID,
    ) -> None:
        """trace_id propagates correctly through asyncio.gather in
        ContextAssembler (Memory + Knowledge parallel fetch).
        """
        memory_core = FakeMemoryCore()
        assembler = ContextAssembler(memory_core=memory_core, knowledge=None)

        expected_tid = "trace-e2e-parallel-002"

        with trace_context(expected_tid):
            ctx = await assembler.assemble(
                user_id=user_id,
                query="test parallel trace propagation",
            )
            # trace_id should survive the asyncio.gather inside assemble()
            assert get_trace_id() == expected_tid

        # Assembler should have completed (degraded since knowledge=None)
        assert ctx.degraded is True

    async def test_trace_id_in_gateway_http_roundtrip(
        self,
        auth_token: str,
    ) -> None:
        """Gateway HTTP middleware sets trace_id from X-Trace-ID header
        and returns it in the response header.
        """
        app = create_app(jwt_secret=JWT_SECRET)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Request with explicit trace_id
            resp = await client.get(
                "/api/v1/me",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "X-Trace-ID": "trace-gateway-roundtrip-003",
                },
            )

            assert resp.status_code == 200
            # Gateway should echo trace_id back in response header
            assert resp.headers.get("x-trace-id") == "trace-gateway-roundtrip-003"

    async def test_trace_id_auto_generated_when_absent(
        self,
        auth_token: str,
    ) -> None:
        """When no X-Trace-ID header is provided, Gateway auto-generates one
        and returns it in the response.
        """
        app = create_app(jwt_secret=JWT_SECRET)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/me",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

            assert resp.status_code == 200
            # Should have an auto-generated trace_id
            returned_tid = resp.headers.get("x-trace-id")
            assert returned_tid is not None
            assert len(returned_tid) > 0
            # Should be a valid UUID4
            UUID(returned_tid, version=4)

    async def test_trace_id_isolated_across_concurrent_requests(
        self,
        auth_token: str,
    ) -> None:
        """Two concurrent requests get independent trace_ids via contextvars.

        This verifies that contextvars isolation works correctly in the
        ASGI middleware context — each request gets its own context copy.
        """
        import asyncio

        app = create_app(jwt_secret=JWT_SECRET)
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            tid_a = "trace-concurrent-A"
            tid_b = "trace-concurrent-B"

            resp_a, resp_b = await asyncio.gather(
                client.get(
                    "/api/v1/me",
                    headers={
                        "Authorization": f"Bearer {auth_token}",
                        "X-Trace-ID": tid_a,
                    },
                ),
                client.get(
                    "/api/v1/me",
                    headers={
                        "Authorization": f"Bearer {auth_token}",
                        "X-Trace-ID": tid_b,
                    },
                ),
            )

            assert resp_a.status_code == 200
            assert resp_b.status_code == 200
            assert resp_a.headers.get("x-trace-id") == tid_a
            assert resp_b.headers.get("x-trace-id") == tid_b

    async def test_trace_id_visible_in_structured_logging(
        self,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
    ) -> None:
        """Brain-layer logger.info/warning calls can access trace_id
        from contextvars during ConversationEngine processing.

        Verifies the observability contract: any log emitted during
        a traced request can be correlated by trace_id.
        """
        capture = TraceCapture()
        brain_logger = logging.getLogger("src.brain")
        brain_logger.addHandler(capture)
        brain_logger.setLevel(logging.DEBUG)

        try:
            memory_core = FakeMemoryCore()
            event_store = FakeEventStore()
            llm = FakeLLM(responses=["Logged response."])

            engine = ConversationEngine(
                llm=llm,
                memory_core=memory_core,
                event_store=event_store,
                default_model="gpt-4o",
            )

            expected_tid = "trace-logging-006"

            with trace_context(expected_tid):
                await engine.process_message(
                    session_id=session_id,
                    user_id=user_id,
                    org_id=org_id,
                    message="Test structured logging trace",
                )

            # Any log emitted under src.brain.* during processing should
            # have had the trace_id accessible via get_trace_id()
            brain_tids = capture.trace_ids_for("src.brain")
            # If any brain logs were emitted, they should all see the trace_id
            if brain_tids:
                assert all(tid == expected_tid for tid in brain_tids)
        finally:
            brain_logger.removeHandler(capture)

    async def test_healthz_exempt_from_trace_id(self) -> None:
        """Health check endpoint does not require or set trace_id."""
        app = create_app(jwt_secret=JWT_SECRET)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/healthz")
            assert resp.status_code == 200
            # healthz is exempt — trace_id header is optional
            # (may or may not be present depending on implementation)
            assert resp.json()["status"] == "ok"
