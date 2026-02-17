"""Structured error logging handler.

Task card: OS2-4
- Error logs contain: error_code, stack_trace, context
- JSON structured output for log aggregation
- Sensitive fields are redacted

Architecture: 07-Deployment-Security Section 2
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class StructuredError:
    """Structured representation of an error for logging."""

    error_code: str
    message: str
    stack_trace: str
    context: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    org_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict suitable for JSON logging."""
        d = asdict(self)
        # Redact sensitive context keys
        if "context" in d:
            d["context"] = _redact_sensitive(d["context"])
        return d


_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "authorization",
        "cookie",
        "jwt",
        "credential",
    }
)


def _redact_sensitive(data: dict[str, Any]) -> dict[str, Any]:
    """Redact values of sensitive keys."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_KEYS:
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = _redact_sensitive(value)
        else:
            result[key] = value
    return result


def create_structured_error(
    exc: Exception,
    *,
    error_code: str = "",
    trace_id: str = "",
    org_id: str = "",
    request_id: str = "",
    context: dict[str, Any] | None = None,
) -> StructuredError:
    """Create a StructuredError from an exception.

    If the exception has a `.code` attribute (e.g. DiyuError subclass),
    it is used as the error_code unless overridden.
    """
    code = error_code or getattr(exc, "code", type(exc).__name__)
    stack = traceback.format_exception(type(exc), exc, exc.__traceback__)
    return StructuredError(
        error_code=code,
        message=str(exc),
        stack_trace="".join(stack),
        context=context or {},
        trace_id=trace_id,
        org_id=org_id,
        request_id=request_id,
    )


def log_structured_error(
    logger: logging.Logger,
    exc: Exception,
    *,
    error_code: str = "",
    trace_id: str = "",
    org_id: str = "",
    request_id: str = "",
    context: dict[str, Any] | None = None,
    level: int = logging.ERROR,
) -> StructuredError:
    """Log an exception as a structured error.

    Returns the StructuredError for further processing (e.g. metrics).
    """
    structured = create_structured_error(
        exc,
        error_code=error_code,
        trace_id=trace_id,
        org_id=org_id,
        request_id=request_id,
        context=context,
    )
    logger.log(level, "structured_error", extra={"structured_error": structured.to_dict()})
    return structured
