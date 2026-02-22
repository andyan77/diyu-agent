"""Tests for unified error hierarchy.

Covers F-8 audit finding: test coverage for src/shared/errors/__init__.py
"""

from __future__ import annotations

from src.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DiyuError,
    NotFoundError,
    OrgIsolationError,
    PortTimeoutError,
    PortUnavailableError,
    QuotaExceededError,
    ServiceUnavailableError,
    ValidationError,
)


class TestDiyuError:
    """Test suite for DiyuError base class."""

    def test_instantiation(self) -> None:
        """Test DiyuError instantiation."""
        error = DiyuError("Test error")
        assert str(error) == "Test error"
        assert error.code == "DIYU_ERROR"

    def test_custom_code(self) -> None:
        """Test DiyuError with custom code."""
        error = DiyuError("Custom error", code="CUSTOM_CODE")
        assert str(error) == "Custom error"
        assert error.code == "CUSTOM_CODE"

    def test_is_exception(self) -> None:
        """Test DiyuError is an Exception."""
        error = DiyuError("Test")
        assert isinstance(error, Exception)


class TestPortUnavailableError:
    """Test suite for PortUnavailableError."""

    def test_instantiation_with_default_message(self) -> None:
        """Test PortUnavailableError with default message."""
        error = PortUnavailableError(port_name="TestPort")
        assert str(error) == "Port TestPort is unavailable"
        assert error.code == "PORT_UNAVAILABLE"
        assert error.port_name == "TestPort"

    def test_instantiation_with_custom_message(self) -> None:
        """Test PortUnavailableError with custom message."""
        error = PortUnavailableError(port_name="TestPort", message="Custom unavailable message")
        assert str(error) == "Custom unavailable message"
        assert error.code == "PORT_UNAVAILABLE"
        assert error.port_name == "TestPort"

    def test_is_diyu_error(self) -> None:
        """Test PortUnavailableError is a DiyuError."""
        error = PortUnavailableError(port_name="TestPort")
        assert isinstance(error, DiyuError)


class TestPortTimeoutError:
    """Test suite for PortTimeoutError."""

    def test_instantiation(self) -> None:
        """Test PortTimeoutError instantiation."""
        error = PortTimeoutError(port_name="TestPort", timeout_ms=5000)
        assert str(error) == "Port TestPort timed out after 5000ms"
        assert error.code == "PORT_TIMEOUT"
        assert error.port_name == "TestPort"
        assert error.timeout_ms == 5000

    def test_is_diyu_error(self) -> None:
        """Test PortTimeoutError is a DiyuError."""
        error = PortTimeoutError(port_name="TestPort", timeout_ms=1000)
        assert isinstance(error, DiyuError)


class TestAuthenticationError:
    """Test suite for AuthenticationError."""

    def test_instantiation_with_default_message(self) -> None:
        """Test AuthenticationError with default message."""
        error = AuthenticationError()
        assert str(error) == "Authentication failed"
        assert error.code == "AUTH_FAILED"

    def test_instantiation_with_custom_message(self) -> None:
        """Test AuthenticationError with custom message."""
        error = AuthenticationError(message="Invalid token")
        assert str(error) == "Invalid token"
        assert error.code == "AUTH_FAILED"

    def test_is_diyu_error(self) -> None:
        """Test AuthenticationError is a DiyuError."""
        error = AuthenticationError()
        assert isinstance(error, DiyuError)


class TestAuthorizationError:
    """Test suite for AuthorizationError."""

    def test_instantiation_without_permission(self) -> None:
        """Test AuthorizationError without permission."""
        error = AuthorizationError()
        assert str(error) == "Permission denied"
        assert error.code == "AUTH_DENIED"
        assert error.required_permission == ""

    def test_instantiation_with_permission(self) -> None:
        """Test AuthorizationError with required permission."""
        error = AuthorizationError(required_permission="admin:write")
        assert str(error) == "Permission denied: admin:write"
        assert error.code == "AUTH_DENIED"
        assert error.required_permission == "admin:write"

    def test_is_diyu_error(self) -> None:
        """Test AuthorizationError is a DiyuError."""
        error = AuthorizationError()
        assert isinstance(error, DiyuError)


class TestOrgIsolationError:
    """Test suite for OrgIsolationError."""

    def test_instantiation_with_default_message(self) -> None:
        """Test OrgIsolationError with default message."""
        error = OrgIsolationError()
        assert str(error) == "Organization isolation violation"
        assert error.code == "ORG_ISOLATION"

    def test_instantiation_with_custom_message(self) -> None:
        """Test OrgIsolationError with custom message."""
        error = OrgIsolationError(message="Cross-org access detected")
        assert str(error) == "Cross-org access detected"
        assert error.code == "ORG_ISOLATION"

    def test_is_diyu_error(self) -> None:
        """Test OrgIsolationError is a DiyuError."""
        error = OrgIsolationError()
        assert isinstance(error, DiyuError)


class TestNotFoundError:
    """Test suite for NotFoundError."""

    def test_instantiation(self) -> None:
        """Test NotFoundError instantiation."""
        error = NotFoundError(resource_type="User", resource_id="user-123")
        assert str(error) == "User not found: user-123"
        assert error.code == "NOT_FOUND"
        assert error.resource_type == "User"
        assert error.resource_id == "user-123"

    def test_is_diyu_error(self) -> None:
        """Test NotFoundError is a DiyuError."""
        error = NotFoundError(resource_type="Document", resource_id="doc-456")
        assert isinstance(error, DiyuError)


class TestConflictError:
    """Test suite for ConflictError."""

    def test_instantiation(self) -> None:
        """Test ConflictError instantiation."""
        error = ConflictError(message="Resource already exists")
        assert str(error) == "Resource already exists"
        assert error.code == "CONFLICT"

    def test_is_diyu_error(self) -> None:
        """Test ConflictError is a DiyuError."""
        error = ConflictError(message="Concurrent modification")
        assert isinstance(error, DiyuError)


class TestValidationError:
    """Test suite for ValidationError."""

    def test_instantiation_without_field(self) -> None:
        """Test ValidationError without field."""
        error = ValidationError(message="Invalid input")
        assert str(error) == "Invalid input"
        assert error.code == "VALIDATION"
        assert error.field == ""

    def test_instantiation_with_field(self) -> None:
        """Test ValidationError with field."""
        error = ValidationError(message="Email is required", field="email")
        assert str(error) == "Email is required"
        assert error.code == "VALIDATION"
        assert error.field == "email"

    def test_is_diyu_error(self) -> None:
        """Test ValidationError is a DiyuError."""
        error = ValidationError(message="Invalid format")
        assert isinstance(error, DiyuError)


class TestQuotaExceededError:
    """Test suite for QuotaExceededError."""

    def test_instantiation(self) -> None:
        """Test QuotaExceededError instantiation."""
        error = QuotaExceededError(resource="tokens", limit=1000, current=1500)
        assert str(error) == "Quota exceeded for tokens: 1500/1000"
        assert error.code == "QUOTA_EXCEEDED"
        assert error.resource == "tokens"
        assert error.limit == 1000
        assert error.current == 1500

    def test_is_diyu_error(self) -> None:
        """Test QuotaExceededError is a DiyuError."""
        error = QuotaExceededError(resource="storage", limit=100, current=150)
        assert isinstance(error, DiyuError)


class TestServiceUnavailableError:
    """Test suite for ServiceUnavailableError."""

    def test_instantiation_with_default_message(self) -> None:
        """Test ServiceUnavailableError with default message."""
        error = ServiceUnavailableError(service="PostgreSQL")
        assert str(error) == "Service temporarily unavailable: PostgreSQL"
        assert error.code == "SERVICE_UNAVAILABLE"
        assert error.service == "PostgreSQL"

    def test_instantiation_with_custom_message(self) -> None:
        """Test ServiceUnavailableError with custom message."""
        error = ServiceUnavailableError(service="Redis", message="Connection pool exhausted")
        assert str(error) == "Connection pool exhausted"
        assert error.code == "SERVICE_UNAVAILABLE"
        assert error.service == "Redis"

    def test_is_diyu_error(self) -> None:
        """Test ServiceUnavailableError is a DiyuError."""
        error = ServiceUnavailableError(service="Database")
        assert isinstance(error, DiyuError)


class TestExports:
    """Test __all__ exports."""

    def test_all_exports(self) -> None:
        """Test __all__ contains all error classes."""
        from src.shared import errors

        expected_exports = {
            "AuthenticationError",
            "AuthorizationError",
            "ConflictError",
            "DiyuError",
            "NotFoundError",
            "OrgIsolationError",
            "PortTimeoutError",
            "PortUnavailableError",
            "QuotaExceededError",
            "ServiceUnavailableError",
            "ValidationError",
        }

        assert set(errors.__all__) == expected_exports

    def test_all_classes_exported(self) -> None:
        """Test all classes in __all__ are importable."""
        from src.shared import errors

        for name in errors.__all__:
            assert hasattr(errors, name), f"{name} not found in module"
            cls = getattr(errors, name)
            assert issubclass(cls, DiyuError), f"{name} is not a DiyuError subclass"


class TestErrorInheritance:
    """Test error inheritance hierarchy."""

    def test_all_errors_inherit_from_diyu_error(self) -> None:
        """Test all error classes inherit from DiyuError."""
        error_classes = [
            PortUnavailableError,
            PortTimeoutError,
            AuthenticationError,
            AuthorizationError,
            OrgIsolationError,
            NotFoundError,
            ConflictError,
            ValidationError,
            QuotaExceededError,
            ServiceUnavailableError,
        ]

        for error_cls in error_classes:
            assert issubclass(error_cls, DiyuError), (
                f"{error_cls.__name__} does not inherit from DiyuError"
            )

    def test_diyu_error_inherits_from_exception(self) -> None:
        """Test DiyuError inherits from Exception."""
        assert issubclass(DiyuError, Exception)

    def test_errors_can_be_caught_as_diyu_error(self) -> None:
        """Test all errors can be caught as DiyuError."""
        errors_to_test = [
            PortUnavailableError(port_name="Test"),
            PortTimeoutError(port_name="Test", timeout_ms=1000),
            AuthenticationError(),
            AuthorizationError(),
            OrgIsolationError(),
            NotFoundError(resource_type="Test", resource_id="123"),
            ConflictError(message="Test"),
            ValidationError(message="Test"),
            QuotaExceededError(resource="test", limit=10, current=20),
            ServiceUnavailableError(service="Test"),
        ]

        for error in errors_to_test:
            try:
                raise error
            except DiyuError as e:
                assert e is error, f"Failed to catch {type(error).__name__} as DiyuError"
