#!/usr/bin/env python3
"""Password and short-lived simulated-session primitives."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390_000


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("The simulated-login password must contain at least 12 characters")
    actual_salt = salt or os.urandom(18)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        actual_salt,
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        (
            PASSWORD_SCHEME,
            str(PASSWORD_ITERATIONS),
            _b64encode(actual_salt),
            _b64encode(digest),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, raw_iterations, raw_salt, raw_digest = encoded.split("$", 3)
        if scheme != PASSWORD_SCHEME or int(raw_iterations) != PASSWORD_ITERATIONS:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64decode(raw_salt),
            PASSWORD_ITERATIONS,
        )
        return hmac.compare_digest(candidate, _b64decode(raw_digest))
    except (ValueError, TypeError):
        return False


def issue_session(
    *,
    principal_id: str,
    allowed_account_ids: list[str],
    signing_key: str,
    browser_session_id: str | None = None,
    lifetime_seconds: int = 3_600,
    now: int | None = None,
) -> str:
    if len(signing_key) < 32:
        raise ValueError("A session signing key of at least 32 characters is required")
    issued_at = int(time.time() if now is None else now)
    effective_browser_session_id = (
        browser_session_id or f"BRS-{secrets.token_urlsafe(18)}"
    )
    if (
        not effective_browser_session_id.startswith("BRS-")
        or len(effective_browser_session_id) > 160
    ):
        raise ValueError("A valid server-generated browser session id is required")
    payload = {
        "principal_id": principal_id,
        "browser_session_id": effective_browser_session_id,
        "allowed_account_ids": sorted(set(allowed_account_ids)),
        "iat": issued_at,
        "exp": issued_at + lifetime_seconds,
        "simulation_only": True,
    }
    body = _b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(signing_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def verify_session(token: str, signing_key: str, *, now: int | None = None) -> dict[str, Any]:
    try:
        body, raw_signature = token.split(".", 1)
        expected = hmac.new(
            signing_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _b64decode(raw_signature)):
            raise ValueError("invalid session")
        payload = json.loads(_b64decode(body))
        current = int(time.time() if now is None else now)
        if not isinstance(payload, dict) or payload.get("simulation_only") is not True:
            raise ValueError("invalid session")
        if not isinstance(payload.get("principal_id"), str):
            raise ValueError("invalid session")
        browser_session_id = payload.get("browser_session_id")
        if (
            not isinstance(browser_session_id, str)
            or not browser_session_id.startswith("BRS-")
            or len(browser_session_id) > 160
        ):
            raise ValueError("invalid session")
        account_ids = payload.get("allowed_account_ids")
        if not isinstance(account_ids, list) or any(not isinstance(item, str) for item in account_ids):
            raise ValueError("invalid session")
        if not isinstance(payload.get("exp"), int) or payload["exp"] < current:
            raise ValueError("expired session")
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or expired simulated session") from exc


def verify_bridge_secret(provided: str | None, configured: str) -> bool:
    return bool(
        provided
        and len(configured) >= 32
        and hmac.compare_digest(provided.encode("utf-8"), configured.encode("utf-8"))
    )
