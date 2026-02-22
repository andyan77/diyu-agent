"""Authentication endpoints (login / register).

E2E chain fix: provides POST /api/v1/auth/login so the frontend can
obtain a JWT without prior authentication.

Architecture: Gateway layer, exempt from JWT middleware.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import bcrypt
from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from src.gateway.middleware.auth import encode_token

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.infra.models import OrgMember, User
from src.shared.errors import AuthenticationError, ConflictError, ServiceUnavailableError

logger = logging.getLogger(__name__)


# -- Request / Response models --


class LoginRequest(BaseModel):
    """Login credentials."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """JWT token returned on successful login."""

    token: str


class RegisterRequest(BaseModel):
    """New user registration (dev/private only)."""

    email: EmailStr
    password: str
    display_name: str | None = None


class RegisterResponse(BaseModel):
    """Registration result."""

    token: str
    user_id: str


# -- Helpers --


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def _get_first_org_id(session: AsyncSession, user_id: UUID) -> UUID | None:
    """Return the first org_id for a user, or None if not a member of any org."""
    stmt = (
        select(OrgMember.org_id)
        .where(OrgMember.user_id == user_id, OrgMember.is_active == True)  # noqa: E712
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row


async def _get_first_org_role(session: AsyncSession, user_id: UUID, org_id: UUID) -> str:
    """Return the user's role within the given org, defaulting to 'member'."""
    stmt = (
        select(OrgMember.role)
        .where(
            OrgMember.user_id == user_id,
            OrgMember.org_id == org_id,
            OrgMember.is_active == True,  # noqa: E712
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()
    return role or "member"


# -- Router factory --


def create_auth_router() -> APIRouter:
    """Create auth API router. Session factory comes from app.state."""
    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

    @router.post("/login", response_model=LoginResponse)
    async def login(body: LoginRequest, request: Request) -> LoginResponse:
        """Authenticate with email + password, return JWT."""
        sf: async_sessionmaker[AsyncSession] = request.app.state.session_factory
        secret: str = request.app.state.jwt_secret

        try:
            async with sf() as session:
                stmt = select(User).where(User.email == body.email)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user is None or user.password_hash is None:
                    raise AuthenticationError("Invalid email or password")

                if not _verify_password(body.password, user.password_hash):
                    raise AuthenticationError("Invalid email or password")

                if not user.is_active:
                    raise AuthenticationError("Account is disabled")

                # Resolve org membership
                org_id = await _get_first_org_id(session, user.id)
                if org_id is None:
                    # Allow login without org for dev; use user_id as fallback
                    org_id = user.id

                # Resolve org role for RBAC
                role = await _get_first_org_role(session, user.id, org_id)

                token = encode_token(
                    user_id=user.id,
                    org_id=org_id,
                    secret=secret,
                    role=role,
                )
        except (AuthenticationError, ServiceUnavailableError):
            raise
        except Exception as exc:
            logger.error("Login DB error: %s", exc)
            msg = "Database is temporarily unavailable"
            raise ServiceUnavailableError("database", msg) from exc

        logger.info("User login: email=%s user_id=%s", body.email, user.id)
        return LoginResponse(token=token)

    @router.post("/register", response_model=RegisterResponse, status_code=201)
    async def register(body: RegisterRequest, request: Request) -> RegisterResponse:
        """Register a new user (dev / private deployment)."""
        sf: async_sessionmaker[AsyncSession] = request.app.state.session_factory
        secret: str = request.app.state.jwt_secret

        try:
            async with sf() as session:
                # Check duplicate
                dup = await session.execute(select(User.id).where(User.email == body.email))
                if dup.scalar_one_or_none() is not None:
                    raise ConflictError(f"Email already registered: {body.email}")

                user = User(
                    email=body.email,
                    password_hash=_hash_password(body.password),
                    display_name=body.display_name,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)

                token = encode_token(
                    user_id=user.id,
                    org_id=user.id,  # No org yet; use user_id as placeholder
                    secret=secret,
                )
        except (ConflictError, ServiceUnavailableError):
            raise
        except Exception as exc:
            logger.error("Register DB error: %s", exc)
            msg = "Database is temporarily unavailable"
            raise ServiceUnavailableError("database", msg) from exc

        logger.info("User registered: email=%s user_id=%s", body.email, user.id)
        return RegisterResponse(token=token, user_id=str(user.id))

    return router
