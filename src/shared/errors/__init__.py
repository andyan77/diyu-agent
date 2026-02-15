"""Unified error hierarchy for DIYU Agent.

All domain errors inherit from DiyuError. Each layer may define
sublayer-specific errors, but cross-layer errors must use these base types.
"""

from __future__ import annotations


class DiyuError(Exception):
    """Base error for all DIYU Agent exceptions."""

    def __init__(self, message: str, code: str = "DIYU_ERROR") -> None:
        self.code = code
        super().__init__(message)


# -- Port errors (raised by Port implementations) --


class PortUnavailableError(DiyuError):
    """A Port dependency is temporarily unavailable."""

    def __init__(self, port_name: str, message: str = "") -> None:
        self.port_name = port_name
        super().__init__(
            message or f"Port {port_name} is unavailable",
            code="PORT_UNAVAILABLE",
        )


class PortTimeoutError(DiyuError):
    """A Port operation timed out."""

    def __init__(self, port_name: str, timeout_ms: int) -> None:
        self.port_name = port_name
        self.timeout_ms = timeout_ms
        super().__init__(
            f"Port {port_name} timed out after {timeout_ms}ms",
            code="PORT_TIMEOUT",
        )


# -- Auth / Org errors --


class AuthenticationError(DiyuError):
    """Authentication failed (invalid token, expired, etc.)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTH_FAILED")


class AuthorizationError(DiyuError):
    """Authorization denied (insufficient permissions)."""

    def __init__(self, required_permission: str = "") -> None:
        msg = (
            f"Permission denied: {required_permission}"
            if required_permission
            else "Permission denied"
        )
        self.required_permission = required_permission
        super().__init__(msg, code="AUTH_DENIED")


class OrgIsolationError(DiyuError):
    """Cross-org data access attempted (RLS violation)."""

    def __init__(self, message: str = "Organization isolation violation") -> None:
        super().__init__(message, code="ORG_ISOLATION")


# -- Domain errors --


class NotFoundError(DiyuError):
    """Requested resource not found."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            code="NOT_FOUND",
        )


class ConflictError(DiyuError):
    """Resource state conflict (concurrent modification, duplicate, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFLICT")


class ValidationError(DiyuError):
    """Input validation failed."""

    def __init__(self, message: str, field: str = "") -> None:
        self.field = field
        super().__init__(message, code="VALIDATION")


class QuotaExceededError(DiyuError):
    """Usage quota exceeded (tokens, storage, API calls)."""

    def __init__(self, resource: str, limit: int, current: int) -> None:
        self.resource = resource
        self.limit = limit
        self.current = current
        super().__init__(
            f"Quota exceeded for {resource}: {current}/{limit}",
            code="QUOTA_EXCEEDED",
        )


__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "DiyuError",
    "NotFoundError",
    "OrgIsolationError",
    "PortTimeoutError",
    "PortUnavailableError",
    "QuotaExceededError",
    "ValidationError",
]
