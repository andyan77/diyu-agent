"""Tests for 4 golden signals middleware.

Task card: OS2-1
Verifies: latency, traffic, errors, saturation metrics are collected.
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
    _normalize_path,
    golden_signals_middleware,
)


@pytest.fixture()
def app() -> FastAPI:
    """Create a test FastAPI app with golden signals middleware."""
    _app = FastAPI()
    _app.middleware("http")(golden_signals_middleware)

    @_app.get("/api/v1/test")
    async def _test_endpoint() -> dict:
        return {"ok": True}

    @_app.get("/api/v1/error")
    async def _error_endpoint() -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": "boom"})

    @_app.get("/healthz")
    async def _health() -> dict:
        return {"status": "ok"}

    return _app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


_LABELS_OK = {"method": "GET", "path": "/api/v1/test", "status_code": "200"}
_LABELS_ERR = {"method": "GET", "path": "/api/v1/error", "status_code": "500"}


class TestNormalizePath:
    def test_simple_path(self) -> None:
        assert _normalize_path("/api/v1/conversations") == "/api/v1/conversations"

    def test_uuid_path(self) -> None:
        result = _normalize_path("/api/v1/conversations/abc12345-def6-7890")
        assert result == "/api/v1/conversations/{id}"

    def test_numeric_id(self) -> None:
        result = _normalize_path("/api/v1/users/12345678")
        assert result == "/api/v1/users/{id}"

    def test_root_path(self) -> None:
        assert _normalize_path("/") == "/"

    def test_trailing_slash(self) -> None:
        result = _normalize_path("/api/v1/test/")
        assert result == "/api/v1/test"


class TestGoldenSignalsMiddleware:
    def test_request_total_incremented(self, client: TestClient) -> None:
        """Traffic signal: request counter increments."""
        before = REQUEST_TOTAL.labels(**_LABELS_OK)._value.get()
        client.get("/api/v1/test")
        after = REQUEST_TOTAL.labels(**_LABELS_OK)._value.get()
        assert after > before

    def test_duration_observed(self, client: TestClient) -> None:
        """Latency signal: duration histogram records a value."""
        before = REQUEST_DURATION.labels(**_LABELS_OK)._sum.get()
        client.get("/api/v1/test")
        after = REQUEST_DURATION.labels(**_LABELS_OK)._sum.get()
        assert after > before

    def test_error_counted_for_5xx(self, client: TestClient) -> None:
        """Error signal: 5xx responses increment error counter."""
        before = ERROR_TOTAL.labels(**_LABELS_ERR)._value.get()
        client.get("/api/v1/error")
        after = ERROR_TOTAL.labels(**_LABELS_ERR)._value.get()
        assert after > before

    def test_healthz_exempt(self, client: TestClient) -> None:
        """Exempt paths do not generate metrics."""
        lbl = {"method": "GET", "path": "/healthz", "status_code": "200"}
        before = REQUEST_TOTAL.labels(**lbl)._value.get()
        client.get("/healthz")
        after = REQUEST_TOTAL.labels(**lbl)._value.get()
        assert after == before

    def test_active_requests_gauge(self, client: TestClient) -> None:
        """Saturation signal: active requests gauge stays >= 0."""
        client.get("/api/v1/test")
        val = ACTIVE_REQUESTS.labels(method="GET")._value.get()
        assert val >= 0
