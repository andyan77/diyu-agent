"""JWT authentication middleware tests.

Phase 1 gate check: p1-gateway-auth
Task card: G1-1

Validates:
- Missing token returns 401 (AuthenticationError)
- Invalid/expired token returns 401
- Valid token extracts user_id + org_id
- healthz endpoint is exempt from auth
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.gateway.middleware.auth import (
    JWTAuthMiddleware,
    TokenPayload,
    decode_token,
    encode_token,
)
from src.shared.errors import AuthenticationError


@pytest.mark.unit
class TestTokenEncoding:
    """Token encode/decode round-trip."""

    def test_encode_returns_string(self) -> None:
        token = encode_token(user_id=uuid4(), org_id=uuid4(), secret="test-secret-key")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_round_trip(self) -> None:
        uid = uuid4()
        oid = uuid4()
        token = encode_token(user_id=uid, org_id=oid, secret="test-secret-key")
        payload = decode_token(token, secret="test-secret-key")
        assert payload.user_id == uid
        assert payload.org_id == oid

    def test_decode_invalid_token_raises(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_token("not-a-valid-jwt", secret="test-secret-key")

    def test_decode_wrong_secret_raises(self) -> None:
        token = encode_token(user_id=uuid4(), org_id=uuid4(), secret="secret-a")
        with pytest.raises(AuthenticationError):
            decode_token(token, secret="secret-b")

    def test_decode_expired_token_raises(self) -> None:
        token = encode_token(
            user_id=uuid4(), org_id=uuid4(), secret="test-secret-key", ttl_seconds=-1
        )
        with pytest.raises(AuthenticationError):
            decode_token(token, secret="test-secret-key")


@pytest.mark.unit
class TestTokenPayload:
    """TokenPayload dataclass."""

    def test_payload_has_user_id(self) -> None:
        uid = uuid4()
        p = TokenPayload(user_id=uid, org_id=uuid4())
        assert isinstance(p.user_id, UUID)

    def test_payload_has_org_id(self) -> None:
        oid = uuid4()
        p = TokenPayload(user_id=uuid4(), org_id=oid)
        assert isinstance(p.org_id, UUID)


@pytest.mark.unit
class TestJWTAuthMiddleware:
    """Middleware: reject / accept / exempt."""

    @pytest.fixture
    def secret(self) -> str:
        return "unit-test-secret-key-minimum-len"

    @pytest.fixture
    def mw(self, secret: str) -> JWTAuthMiddleware:
        return JWTAuthMiddleware(
            secret=secret,
            exempt_paths=["/healthz", "/docs", "/openapi.json"],
        )

    @pytest.mark.smoke
    def test_no_token_returns_401(self, mw: JWTAuthMiddleware) -> None:
        with pytest.raises(AuthenticationError):
            mw.authenticate(token=None, path="/api/v1/resource")

    def test_empty_token_returns_401(self, mw: JWTAuthMiddleware) -> None:
        with pytest.raises(AuthenticationError):
            mw.authenticate(token="", path="/api/v1/resource")

    @pytest.mark.smoke
    def test_valid_token_extracts_ids(self, mw: JWTAuthMiddleware, secret: str) -> None:
        uid, oid = uuid4(), uuid4()
        token = encode_token(user_id=uid, org_id=oid, secret=secret)
        payload = mw.authenticate(token=token, path="/api/v1/resource")
        assert payload is not None
        assert payload.user_id == uid
        assert payload.org_id == oid

    def test_invalid_token_returns_401(self, mw: JWTAuthMiddleware) -> None:
        with pytest.raises(AuthenticationError):
            mw.authenticate(token="bad.jwt.value", path="/api/v1/resource")

    @pytest.mark.smoke
    def test_healthz_exempt(self, mw: JWTAuthMiddleware) -> None:
        result = mw.authenticate(token=None, path="/healthz")
        assert result is None

    def test_docs_exempt(self, mw: JWTAuthMiddleware) -> None:
        result = mw.authenticate(token=None, path="/docs")
        assert result is None

    def test_expired_token_returns_401(self, mw: JWTAuthMiddleware, secret: str) -> None:
        token = encode_token(
            user_id=uuid4(), org_id=uuid4(), secret=secret, ttl_seconds=-1
        )
        with pytest.raises(AuthenticationError):
            mw.authenticate(token=token, path="/api/v1/resource")
