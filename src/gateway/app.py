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
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from src.gateway.middleware.auth import JWTAuthMiddleware, TokenPayload, decode_token
from src.gateway.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from src.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    DiyuError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

_EXEMPT_PATHS = frozenset(
    {
        "/healthz",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/admin/auth/login",
    }
)

# Type alias for post-auth middleware callables
PostAuthMiddleware = Callable[
    [Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]
]


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
    post_auth_middlewares: list[PostAuthMiddleware] | None = None,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        jwt_secret: JWT signing secret. Falls back to JWT_SECRET_KEY env var.
        cors_origins: Allowed CORS origins. Falls back to CORS_ORIGINS env var.
        post_auth_middlewares: Middleware callables that run after JWT auth.
            Each has signature (request, call_next) -> Response.
            They can intercept (return 402/429) or add headers to responses.
        lifespan: Async context manager factory for startup/shutdown lifecycle.

    Returns:
        Configured FastAPI application with partitioned routers.
    """
    secret = jwt_secret or os.environ.get("JWT_SECRET_KEY", "")
    if not secret:
        msg = "JWT_SECRET_KEY must be provided via argument or environment variable"
        raise ValueError(msg)

    origins = cors_origins or [
        o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
    ]
    _post_auth = post_auth_middlewares or []

    app = FastAPI(
        title="Diyu Agent API",
        description="AI-powered intelligent work assistant",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
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

    @app.exception_handler(ServiceUnavailableError)
    async def _service_unavailable(_: Request, exc: ServiceUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": exc.code, "message": str(exc)},
        )

    @app.exception_handler(DiyuError)
    async def _diyu_error(_: Request, exc: DiyuError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": exc.code, "message": str(exc)},
        )

    # -- Override Starlette default HTTP errors for uniform {error, message} schema (F-10) --
    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": code_map.get(exc.status_code, "HTTP_ERROR"),
                "message": exc.detail or f"HTTP {exc.status_code}",
            },
        )

    # -- Auth middleware (ASGI) --

    @app.middleware("http")
    async def jwt_auth_middleware(request: Request, call_next: Any) -> Response:
        path = request.url.path

        # Security headers applied to ALL responses
        def _add_security_headers(response: Response) -> Response:
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

        # F-1: Check if path matches a registered route before requiring auth.
        # Unknown paths should return 404, not 401 (information leak).
        route_matched = any(route.matches(request.scope)[0] != Match.NONE for route in app.routes)
        if not route_matched:
            response = await call_next(request)
            return _add_security_headers(response)

        auth_header = request.headers.get("authorization", "")

        # F-3: SSE/WebSocket query-token fallback for EventSource clients
        # that cannot set Authorization headers.
        token: str | None = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif request.query_params.get("token"):
            token = request.query_params["token"]

        if not token:
            return _add_security_headers(
                JSONResponse(
                    status_code=401,
                    content={
                        "error": "AUTH_FAILED",
                        "message": "Missing or malformed Authorization header",
                    },
                )
            )
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
        request.state.role = payload.role

        # Chain post-auth middlewares (budget check, rate limit, etc.)
        # Build a call chain: mw_n(... mw_1(call_next) ...)
        # Each middleware can intercept (return 402/429) or modify response
        chained = call_next
        for mw in reversed(_post_auth):
            outer = chained

            async def _make_chained(
                req: Request,
                *,
                _mw: PostAuthMiddleware = mw,
                _next: Any = outer,
            ) -> Response:
                return await _mw(req, _next)

            chained = _make_chained

        response = await chained(request)
        return _add_security_headers(response)

    # -- Exempt routes --

    @app.get("/healthz", tags=["system"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # F-12: Prometheus metrics endpoint (exempt from auth)
    @app.get("/metrics", tags=["system"], include_in_schema=False)
    async def metrics() -> Response:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    # -- User API: /api/v1/* --

    @app.get("/api/v1/me", tags=["user"])
    async def get_me(request: Request) -> dict[str, str]:
        """Return current authenticated user info."""
        return {
            "user_id": str(request.state.user_id),
            "org_id": str(request.state.org_id),
        }

    # -- Admin API: /api/v1/admin/* --

    @app.get("/api/v1/admin/status", tags=["admin"])
    async def admin_status(request: Request) -> dict[str, object]:
        """Admin-only system status endpoint."""
        return {
            "status": "ok",
            "admin": True,
            "org_id": str(request.state.org_id),
        }

    return app
