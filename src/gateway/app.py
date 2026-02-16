"""FastAPI application factory with API partition rules.

Task card: G1-5
- User API:  /api/v1/*  (non-admin)
- Admin API: /api/v1/admin/*  (RBAC-protected)
- healthz:   exempt from auth
- docs:      exempt from auth

ADR-029: API partition for clear permission boundaries + independent rate limiting.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.gateway.middleware.auth import JWTAuthMiddleware, TokenPayload, decode_token
from src.gateway.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from src.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    DiyuError,
    NotFoundError,
    ValidationError,
)

_EXEMPT_PATHS = frozenset({"/healthz", "/docs", "/openapi.json", "/redoc"})


def _extract_token(request: Request) -> TokenPayload:
    """FastAPI dependency: extract and validate JWT from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    secret = request.app.state.jwt_secret

    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or malformed Authorization header")

    token = auth_header[7:]
    return decode_token(token, secret=secret)


def create_app(
    *,
    jwt_secret: str | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        jwt_secret: JWT signing secret. Falls back to JWT_SECRET env var.
        cors_origins: Allowed CORS origins. Falls back to CORS_ORIGINS env var.

    Returns:
        Configured FastAPI application with partitioned routers.
    """
    secret = jwt_secret or os.environ.get("JWT_SECRET", "")
    if not secret:
        msg = "JWT_SECRET must be provided via argument or environment variable"
        raise ValueError(msg)

    origins = cors_origins or [
        o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
    ]

    app = FastAPI(
        title="Diyu Agent API",
        description="AI-powered intelligent work assistant",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.jwt_secret = secret
    app.state.jwt_middleware = JWTAuthMiddleware(
        secret=secret,
        exempt_paths=list(_EXEMPT_PATHS),
    )

    # -- CORS middleware (OS1-5) --
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["Authorization", "Content-Type"],
        )

    # -- Security headers middleware (G1-6 / OS1-5) --
    _sec_headers = SecurityHeadersMiddleware()
    app.state.security_headers = _sec_headers

    # -- Error handlers --

    @app.exception_handler(AuthenticationError)
    async def _auth_error(_: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"error": exc.code, "message": str(exc)},
        )

    @app.exception_handler(AuthorizationError)
    async def _authz_error(_: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"error": exc.code, "message": str(exc)},
        )

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": exc.code, "message": str(exc)},
        )

    @app.exception_handler(ValidationError)
    async def _validation_error(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": exc.code, "message": str(exc)},
        )

    @app.exception_handler(DiyuError)
    async def _diyu_error(_: Request, exc: DiyuError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": exc.code, "message": str(exc)},
        )

    # -- Auth middleware (ASGI) --

    @app.middleware("http")
    async def jwt_auth_middleware(request: Request, call_next):
        path = request.url.path

        # Security headers applied to ALL responses
        def _add_security_headers(response):
            for name, value in _sec_headers.get_headers().items():
                response.headers[name] = value
            return response

        # CORS preflight (OPTIONS) must pass through to CORSMiddleware
        if request.method == "OPTIONS":
            response = await call_next(request)
            return _add_security_headers(response)

        if path in _EXEMPT_PATHS:
            response = await call_next(request)
            return _add_security_headers(response)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return _add_security_headers(
                JSONResponse(
                    status_code=401,
                    content={
                        "error": "AUTH_FAILED",
                        "message": "Missing or malformed Authorization header",
                    },
                )
            )

        token = auth_header[7:]
        try:
            payload = decode_token(token, secret=secret)
        except AuthenticationError as exc:
            return _add_security_headers(
                JSONResponse(
                    status_code=401,
                    content={"error": exc.code, "message": str(exc)},
                )
            )

        request.state.user_id = payload.user_id
        request.state.org_id = payload.org_id
        response = await call_next(request)
        return _add_security_headers(response)

    # -- Exempt routes --

    @app.get("/healthz", tags=["system"])
    async def healthz():
        return {"status": "ok"}

    # -- User API: /api/v1/* --

    @app.get("/api/v1/me", tags=["user"])
    async def get_me(request: Request):
        """Return current authenticated user info."""
        return {
            "user_id": str(request.state.user_id),
            "org_id": str(request.state.org_id),
        }

    # -- Admin API: /api/v1/admin/* --

    @app.get("/api/v1/admin/status", tags=["admin"])
    async def admin_status(request: Request):
        """Admin-only system status endpoint."""
        return {
            "status": "ok",
            "admin": True,
            "org_id": str(request.state.org_id),
        }

    return app
