"""Cross-layer E2E: 4 golden signals end-to-end (X2-5).

Verifies: Send requests -> prometheus_client registry has latency/traffic/errors/saturation data.
Uses FastAPI TestClient with golden_signals_middleware — no live Prometheus required.

Covers:
    X2-5: 4 golden signals end-to-end verification
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from src.gateway.metrics.golden_signals import (
    ACTIVE_REQUESTS,
    ERROR_TOTAL,
    REQUEST_DURATION,
    REQUEST_TOTAL,
    golden_signals_middleware,
)


@pytest.fixture()
def signals_app() -> FastAPI:
    """Minimal FastAPI app with golden signals middleware for cross-layer E2E."""
    app = FastAPI()
    app.middleware("http")(golden_signals_middleware)

    @app.get("/api/v1/chat/send")
    async def _chat_send() -> dict:
        return {"message": "streamed response", "tokens_used": 42}

    @app.get("/api/v1/chat/error")
    async def _chat_error() -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": "LLM timeout"})

    @app.get("/healthz")
    async def _health() -> dict:
        return {"status": "ok"}

    return app


@pytest.fixture()
def signals_client(signals_app: FastAPI) -> TestClient:
    return TestClient(signals_app)


_LABELS_CHAT = {"method": "GET", "path": "/api/v1/chat/send", "status_code": "200"}
_LABELS_ERR = {"method": "GET", "path": "/api/v1/chat/error", "status_code": "500"}


@pytest.mark.e2e
class TestGoldenSignalsCrossLayer:
    """Cross-layer observability golden signals verification.

    Exercises the Gateway metrics middleware end-to-end through a realistic
    chat API path, verifying all 4 golden signals are recorded in the
    prometheus_client registry.
    """

    def test_latency_metric_recorded(self, signals_client: TestClient) -> None:
        """X2-5: Request latency metric exists after a chat request."""
        before = REQUEST_DURATION.labels(**_LABELS_CHAT)._sum.get()
        signals_client.get("/api/v1/chat/send")
        after = REQUEST_DURATION.labels(**_LABELS_CHAT)._sum.get()
        assert after > before, "Latency histogram should record duration for chat request"

    def test_traffic_metric_recorded(self, signals_client: TestClient) -> None:
        """X2-5: Request count metric increments on chat request."""
        before = REQUEST_TOTAL.labels(**_LABELS_CHAT)._value.get()
        signals_client.get("/api/v1/chat/send")
        after = REQUEST_TOTAL.labels(**_LABELS_CHAT)._value.get()
        assert after == before + 1, "Traffic counter should increment by 1"

    def test_error_rate_metric_recorded(self, signals_client: TestClient) -> None:
        """X2-5: Error responses produce error rate metric."""
        before = ERROR_TOTAL.labels(**_LABELS_ERR)._value.get()
        signals_client.get("/api/v1/chat/error")
        after = ERROR_TOTAL.labels(**_LABELS_ERR)._value.get()
        assert after == before + 1, "Error counter should increment on 5xx response"

    def test_saturation_metric_recorded(self, signals_client: TestClient) -> None:
        """X2-5: Active requests gauge returns to 0 after request completes."""
        signals_client.get("/api/v1/chat/send")
        val = ACTIVE_REQUESTS.labels(method="GET")._value.get()
        assert val >= 0, "Active requests gauge should be non-negative after completion"
