"""Tests for structured error logging.

Task card: OS2-4
Verifies: error_code, stack_trace, context in structured logs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.shared.errors import DiyuError, PortUnavailableError
from src.shared.logging.error_handler import (
    StructuredError,
    _redact_sensitive,
    create_structured_error,
    log_structured_error,
)

if TYPE_CHECKING:
    import pytest

_REDACTED = "[REDACTED]"


class TestRedactSensitive:
    def test_redacts_password(self) -> None:
        result = _redact_sensitive({"password": "secret123", "user": "alice"})
        assert result["password"] == _REDACTED
        assert result["user"] == "alice"

    def test_redacts_token(self) -> None:
        result = _redact_sensitive({"token": "abc", "api_key": "xyz"})
        assert result["token"] == _REDACTED
        assert result["api_key"] == _REDACTED

    def test_redacts_nested(self) -> None:
        result = _redact_sensitive({"outer": {"password": "secret"}})
        assert result["outer"]["password"] == _REDACTED

    def test_preserves_non_sensitive(self) -> None:
        result = _redact_sensitive({"name": "test", "count": 42})
        assert result == {"name": "test", "count": 42}


class TestCreateStructuredError:
    def test_from_generic_exception(self) -> None:
        exc = ValueError("bad value")
        try:
            raise exc
        except ValueError:
            result = create_structured_error(exc)
        assert result.error_code == "ValueError"
        assert result.message == "bad value"
        assert "ValueError" in result.stack_trace
        assert "bad value" in result.stack_trace

    def test_from_diyu_error(self) -> None:
        exc = PortUnavailableError("MemoryCore")
        try:
            raise exc
        except DiyuError:
            result = create_structured_error(exc)
        assert result.error_code == "PORT_UNAVAILABLE"
        assert "MemoryCore" in result.message

    def test_custom_error_code_overrides(self) -> None:
        exc = ValueError("x")
        try:
            raise exc
        except ValueError:
            result = create_structured_error(exc, error_code="CUSTOM_CODE")
        assert result.error_code == "CUSTOM_CODE"

    def test_context_and_ids(self) -> None:
        exc = RuntimeError("fail")
        try:
            raise exc
        except RuntimeError:
            result = create_structured_error(
                exc,
                trace_id="t-123",
                org_id="org-456",
                request_id="req-789",
                context={"action": "test"},
            )
        assert result.trace_id == "t-123"
        assert result.org_id == "org-456"
        assert result.request_id == "req-789"
        assert result.context == {"action": "test"}


class TestStructuredErrorToDict:
    def test_to_dict_redacts_sensitive(self) -> None:
        se = StructuredError(
            error_code="TEST",
            message="test",
            stack_trace="...",
            context={"password": "secret", "action": "login"},
        )
        d = se.to_dict()
        assert d["context"]["password"] == _REDACTED
        assert d["context"]["action"] == "login"

    def test_to_dict_fields(self) -> None:
        se = StructuredError(
            error_code="E001",
            message="msg",
            stack_trace="trace",
            trace_id="t1",
            org_id="o1",
            request_id="r1",
        )
        d = se.to_dict()
        assert d["error_code"] == "E001"
        assert d["message"] == "msg"
        assert d["stack_trace"] == "trace"
        assert d["trace_id"] == "t1"


class TestLogStructuredError:
    def test_logs_at_error_level(self, caplog: pytest.LogCaptureFixture) -> None:
        test_logger = logging.getLogger("test.structured")
        exc = ValueError("test error")
        try:
            raise exc
        except ValueError:
            with caplog.at_level(logging.ERROR, logger="test.structured"):
                result = log_structured_error(test_logger, exc, trace_id="t-abc")
        assert result.error_code == "ValueError"
        assert result.trace_id == "t-abc"
        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.ERROR
