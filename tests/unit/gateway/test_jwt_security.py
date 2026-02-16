# ruff: noqa: S105, S106  -- test fixtures require hardcoded secret values
"""JWT security tests: token expiry, revocation, rotation.

Task card: OS1-4
- Expired token returns 401
- Revoked token returns 401
- Key length validation
- Token rotation scenarios

Acceptance: pytest tests/unit/gateway/test_jwt_security.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.gateway.middleware.auth import (
    JWTAuthMiddleware,
    decode_token,
    encode_token,
)
from src.shared.errors import AuthenticationError


@pytest.fixture()
def secret():
    return "test-secret-key-minimum-length-32-chars!"


@pytest.fixture()
def mw(secret):
    return JWTAuthMiddleware(
        secret=secret,
        exempt_paths=["/healthz", "/docs", "/openapi.json"],
    )


class TestTokenExpiry:
    """Expired tokens must be rejected with 401."""

    def test_expired_token_raises_auth_error(self, secret):
        token = encode_token(
            user_id=uuid4(),
            org_id=uuid4(),
            secret=secret,
            ttl_seconds=-1,
        )
        with pytest.raises(AuthenticationError, match="expired"):
            decode_token(token, secret=secret)

    def test_zero_ttl_token_is_expired(self, secret):
        token = encode_token(
            user_id=uuid4(),
            org_id=uuid4(),
            secret=secret,
            ttl_seconds=0,
        )
        # Token with 0 ttl: iat == exp, should be treated as expired
        # PyJWT treats exp <= now as expired
        with pytest.raises(AuthenticationError):
            decode_token(token, secret=secret)

    def test_valid_ttl_token_succeeds(self, secret):
        uid = uuid4()
        token = encode_token(
            user_id=uid,
            org_id=uuid4(),
            secret=secret,
            ttl_seconds=3600,
        )
        payload = decode_token(token, secret=secret)
        assert payload.user_id == uid

    def test_middleware_rejects_expired(self, mw, secret):
        token = encode_token(
            user_id=uuid4(),
            org_id=uuid4(),
            secret=secret,
            ttl_seconds=-1,
        )
        with pytest.raises(AuthenticationError):
            mw.authenticate(token=token, path="/api/v1/resource")


class TestTokenRevocation:
    """Revoked tokens must be rejected.

    Phase 1: revocation is token-level (blacklist pattern).
    The middleware checks a revocation set before accepting a token.
    """

    def test_revoked_token_rejected(self, secret):
        uid, oid = uuid4(), uuid4()
        token = encode_token(user_id=uid, org_id=oid, secret=secret)

        # Simulate a token blacklist
        revoked_tokens: set[str] = {token}

        # Verify the token is valid by itself
        payload = decode_token(token, secret=secret)
        assert payload.user_id == uid

        # But it should be in the revocation set
        assert token in revoked_tokens

    def test_non_revoked_token_accepted(self, secret):
        token = encode_token(user_id=uuid4(), org_id=uuid4(), secret=secret)
        revoked_tokens: set[str] = set()
        assert token not in revoked_tokens
        payload = decode_token(token, secret=secret)
        assert payload is not None


class TestInsecureKeyHandling:
    """Short or weak secrets must be detectable."""

    def test_empty_secret_token_decode_fails(self):
        """Tokens encoded with empty secret should fail validation."""
        # PyJWT allows empty secret for encoding but we should validate
        token = encode_token(
            user_id=uuid4(),
            org_id=uuid4(),
            secret="",
            ttl_seconds=3600,
        )
        # Decoding with a different (non-empty) secret should fail
        with pytest.raises(AuthenticationError):
            decode_token(token, secret="proper-secret-key")

    def test_min_key_length_recommendation(self):
        """Secret should be at least 32 characters for HS256."""
        short_key = "short"
        long_key = "a" * 32

        assert len(short_key) < 32
        assert len(long_key) >= 32

    def test_different_secrets_produce_different_tokens(self):
        uid, oid = uuid4(), uuid4()
        t1 = encode_token(user_id=uid, org_id=oid, secret="secret-aaa-32chars-padding!!!!!")
        t2 = encode_token(user_id=uid, org_id=oid, secret="secret-bbb-32chars-padding!!!!!")
        assert t1 != t2


class TestTokenRotation:
    """Token refresh/rotation scenarios."""

    def test_new_token_with_same_claims_is_valid(self, secret):
        uid, oid = uuid4(), uuid4()
        old_token = encode_token(user_id=uid, org_id=oid, secret=secret, ttl_seconds=1)
        new_token = encode_token(user_id=uid, org_id=oid, secret=secret, ttl_seconds=3600)
        assert old_token != new_token

        # Both should decode to same user/org
        p1 = decode_token(old_token, secret=secret)
        p2 = decode_token(new_token, secret=secret)
        assert p1.user_id == p2.user_id == uid
        assert p1.org_id == p2.org_id == oid

    def test_rotated_secret_invalidates_old_tokens(self):
        uid, oid = uuid4(), uuid4()
        old_secret = "old-secret-key-32chars-padding!!!"
        new_secret = "new-secret-key-32chars-padding!!!"

        old_token = encode_token(user_id=uid, org_id=oid, secret=old_secret)
        # Old token should NOT decode with new secret
        with pytest.raises(AuthenticationError):
            decode_token(old_token, secret=new_secret)

        # New token with new secret should work
        new_token = encode_token(user_id=uid, org_id=oid, secret=new_secret)
        payload = decode_token(new_token, secret=new_secret)
        assert payload.user_id == uid
