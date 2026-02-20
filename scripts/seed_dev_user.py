#!/usr/bin/env python3
"""Seed a development user for local testing.

Usage:
    uv run python scripts/seed_dev_user.py

Creates:
    - User:  dev@diyu.ai / devpass123
    - Org:   Dev Organization
    - Membership: user -> org (role=admin)
"""

from __future__ import annotations

import asyncio
import os
import uuid

import bcrypt
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://diyu:diyu_dev@localhost:5432/diyu",
)

DEV_EMAIL = os.environ.get("DEV_EMAIL", "dev@diyu.ai")
DEV_PASSWORD = os.environ.get("DEV_PASSWORD", "devpass123")
DEV_DISPLAY_NAME = "Dev User"
DEV_ORG_NAME = "Dev Organization"
DEV_ORG_SLUG = "dev-org"


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]

    async with async_session() as session:
        # Check if user already exists
        result = await session.execute(
            sa.text("SELECT id FROM users WHERE email = :email"),
            {"email": DEV_EMAIL},
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Dev user already exists: {DEV_EMAIL} (id={existing})")
            await engine.dispose()
            return

        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        member_id = uuid.uuid4()

        password_hash = bcrypt.hashpw(DEV_PASSWORD.encode(), bcrypt.gensalt()).decode()

        # Set RLS context (superuser can bypass, but explicit is safer)
        await session.execute(
            sa.text(f"SET LOCAL app.current_org_id = '{org_id}'"),
        )

        # Create org (include org_path which is NOT NULL)
        await session.execute(
            sa.text(
                "INSERT INTO organizations (id, name, slug, tier, org_path) "
                "VALUES (:id, :name, :slug, :tier, :org_path)"
            ),
            {
                "id": str(org_id),
                "name": DEV_ORG_NAME,
                "slug": DEV_ORG_SLUG,
                "tier": "free",
                "org_path": str(org_id),
            },
        )

        # Create user
        await session.execute(
            sa.text(
                "INSERT INTO users (id, email, password_hash, display_name) "
                "VALUES (:id, :email, :pw, :name)"
            ),
            {
                "id": str(user_id),
                "email": DEV_EMAIL,
                "pw": password_hash,
                "name": DEV_DISPLAY_NAME,
            },
        )

        # Create membership
        await session.execute(
            sa.text(
                "INSERT INTO org_members (id, org_id, user_id, role, permissions) "
                "VALUES (:id, :org_id, :user_id, :role, :perms)"
            ),
            {
                "id": str(member_id),
                "org_id": str(org_id),
                "user_id": str(user_id),
                "role": "admin",
                "perms": "[]",
            },
        )

        await session.commit()
        print(f"Created dev user: {DEV_EMAIL} / {DEV_PASSWORD}")
        print(f"  user_id: {user_id}")
        print(f"  org_id:  {org_id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
