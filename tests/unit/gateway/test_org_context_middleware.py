"""OrgContext middleware tests.

Task card: G1-2
- Extract org_id from JWT payload
- Set OrgContext for downstream handlers
- Reject missing user_id / org_id on non-exempt paths
- Exempt paths skip context extraction

Acceptance: pytest tests/unit/gateway/test_org_context_middleware.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.gateway.middleware.org_context import OrgContext, OrgContextMiddleware
from src.shared.errors import AuthenticationError, OrgIsolationError


@pytest.fixture()
def mw():
    return OrgContextMiddleware(exempt_paths=["/healthz", "/docs", "/openapi.json"])


class TestOrgContextDataclass:
    """OrgContext is a frozen dataclass with required fields."""

    def test_create_org_context(self):
        uid, oid = uuid4(), uuid4()
        ctx = OrgContext(user_id=uid, org_id=oid, role="admin")
        assert ctx.user_id == uid
        assert ctx.org_id == oid
        assert ctx.role == "admin"

    def test_default_role_is_member(self):
        ctx = OrgContext(user_id=uuid4(), org_id=uuid4())
        assert ctx.role == "member"

    def test_frozen_immutable(self):
        ctx = OrgContext(user_id=uuid4(), org_id=uuid4())
        with pytest.raises(AttributeError):
            ctx.role = "admin"  # type: ignore[misc]


class TestExemptPaths:
    """Exempt paths skip context extraction entirely."""

    def test_healthz_returns_none(self, mw):
        result = mw.extract_context(user_id=None, org_id=None, path="/healthz")
        assert result is None

    def test_docs_returns_none(self, mw):
        result = mw.extract_context(user_id=None, org_id=None, path="/docs")
        assert result is None

    def test_openapi_returns_none(self, mw):
        result = mw.extract_context(user_id=None, org_id=None, path="/openapi.json")
        assert result is None

    def test_exempt_path_ignores_valid_credentials(self, mw):
        """Even with valid user/org, exempt paths return None."""
        result = mw.extract_context(user_id=uuid4(), org_id=uuid4(), path="/healthz")
        assert result is None


class TestMissingCredentials:
    """Non-exempt paths must have valid user_id and org_id."""

    def test_missing_user_id_raises_auth_error(self, mw):
        with pytest.raises(AuthenticationError, match="User ID"):
            mw.extract_context(user_id=None, org_id=uuid4(), path="/api/v1/resource")

    def test_missing_org_id_raises_isolation_error(self, mw):
        with pytest.raises(OrgIsolationError, match="Organization ID"):
            mw.extract_context(user_id=uuid4(), org_id=None, path="/api/v1/resource")

    def test_both_missing_raises_auth_error_first(self, mw):
        """user_id is checked before org_id."""
        with pytest.raises(AuthenticationError):
            mw.extract_context(user_id=None, org_id=None, path="/api/v1/resource")


class TestSuccessfulExtraction:
    """Valid credentials on non-exempt paths produce OrgContext."""

    def test_returns_org_context(self, mw):
        uid, oid = uuid4(), uuid4()
        ctx = mw.extract_context(user_id=uid, org_id=oid, path="/api/v1/resource")
        assert isinstance(ctx, OrgContext)
        assert ctx.user_id == uid
        assert ctx.org_id == oid
        assert ctx.role == "member"

    def test_custom_role_preserved(self, mw):
        ctx = mw.extract_context(
            user_id=uuid4(),
            org_id=uuid4(),
            path="/api/v1/resource",
            role="org_admin",
        )
        assert ctx.role == "org_admin"

    def test_admin_path_requires_context(self, mw):
        uid, oid = uuid4(), uuid4()
        ctx = mw.extract_context(user_id=uid, org_id=oid, path="/api/v1/admin/status")
        assert ctx is not None
        assert ctx.org_id == oid


class TestMiddlewareConfiguration:
    """Middleware configuration edge cases."""

    def test_no_exempt_paths(self):
        mw = OrgContextMiddleware()
        uid, oid = uuid4(), uuid4()
        ctx = mw.extract_context(user_id=uid, org_id=oid, path="/healthz")
        # Without exempt paths, even /healthz requires context
        assert ctx is not None

    def test_custom_exempt_paths(self):
        mw = OrgContextMiddleware(exempt_paths=["/custom", "/ping"])
        result = mw.extract_context(user_id=None, org_id=None, path="/custom")
        assert result is None

    def test_non_exempt_unknown_path(self, mw):
        with pytest.raises(AuthenticationError):
            mw.extract_context(user_id=None, org_id=None, path="/unknown")
