"""Admin authentication endpoints.

Provides POST /api/v1/admin/auth/login for the admin frontend.
Reuses the same credential verification as the user auth flow,
but could add admin-specific checks (e.g. role = admin) in future.

This route is JWT-exempt (pre-auth).
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
from src.shared.errors import AuthenticationError, ServiceUnavailableError

logger = logging.getLogger(__name__)


class AdminLoginRequest(BaseModel):
    """Admin login credentials."""

    email: EmailStr
    password: str


class AdminLoginResponse(BaseModel):
    """JWT token returned on successful admin login."""

    token: str


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def _get_first_org_id(session: AsyncSession, user_id: UUID) -> UUID | None:
    stmt = (
        select(OrgMember.org_id)
        .where(OrgMember.user_id == user_id, OrgMember.is_active == True)  # noqa: E712
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_org_role(session: AsyncSession, user_id: UUID, org_id: UUID) -> str:
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


def create_admin_auth_router() -> APIRouter:
    """Create admin auth API router. Session factory comes from app.state."""
    router = APIRouter(prefix="/api/v1/admin/auth", tags=["admin-auth"])

    @router.post("/login", response_model=AdminLoginResponse)
    async def admin_login(body: AdminLoginRequest, request: Request) -> AdminLoginResponse:
        """Authenticate admin with email + password, return JWT."""
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

                org_id = await _get_first_org_id(session, user.id)
                if org_id is None:
                    org_id = user.id

                role = await _get_org_role(session, user.id, org_id)

                token = encode_token(
                    user_id=user.id,
                    org_id=org_id,
                    secret=secret,
                    role=role,
                )
        except (AuthenticationError, ServiceUnavailableError):
            raise
        except Exception as exc:
            logger.error("Admin login DB error: %s", exc)
            msg = "Database is temporarily unavailable"
            raise ServiceUnavailableError("database", msg) from exc

        logger.info("Admin login: email=%s user_id=%s", body.email, user.id)
        return AdminLoginResponse(token=token)

    return router
