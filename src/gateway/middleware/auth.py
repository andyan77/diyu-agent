"""JWT authentication middleware.

Task card: G1-1
- No token -> 401
- Invalid/expired token -> 401
- Valid token -> extract user_id + org_id
- healthz exempt

Uses PyJWT (HS256). Secret must come from environment, never hardcoded.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID

import jwt

from src.shared.errors import AuthenticationError

_ALGORITHM = "HS256"


@dataclass(frozen=True)
class TokenPayload:
    """Decoded JWT payload."""

    user_id: UUID
    org_id: UUID
    role: str = "member"


def encode_token(
    *,
    user_id: UUID,
    org_id: UUID,
    secret: str,
    role: str = "member",
    ttl_seconds: int = 3600,
) -> str:
    """Create a signed JWT containing user_id, org_id, and role."""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "org": str(org_id),
        "role": role,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_token(token: str, *, secret: str) -> TokenPayload:
    """Decode and validate a JWT. Raises AuthenticationError on failure."""
    try:
        data = jwt.decode(token, secret, algorithms=[_ALGORITHM])
        return TokenPayload(
            user_id=UUID(data["sub"]),
            org_id=UUID(data["org"]),
            role=data.get("role", "member"),
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token expired") from exc
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc


class JWTAuthMiddleware:
    """Synchronous JWT auth check for gateway requests.

    Exempt paths (healthz, docs) skip authentication entirely.
    """

    def __init__(
        self,
        *,
        secret: str,
        exempt_paths: list[str] | None = None,
    ) -> None:
        self._secret = secret
        self._exempt_paths = set(exempt_paths or [])

    def authenticate(self, *, token: str | None, path: str) -> TokenPayload | None:
        """Authenticate request. Returns None for exempt paths.

        Raises AuthenticationError for missing/invalid tokens on
        non-exempt paths.
        """
        if path in self._exempt_paths:
            return None

        if not token:
            raise AuthenticationError("Missing authentication token")

        return decode_token(token, secret=self._secret)
