"""ORM model schema assertion tests.

Verifies SQLAlchemy ORM models match migration DDL exactly.
These tests catch drift between models.py and migration files.

Phase 1 (I1-1): organizations, users, org_members, org_settings
Phase 1 (I1-5): audit_events
"""

from __future__ import annotations

import pytest

from src.infra.models import (
    AuditEvent,
    Base,
    Organization,
    OrgMember,
    OrgSettings,
    User,
)


def _col_names(model) -> set[str]:
    """Extract column names from a SQLAlchemy model."""
    return {c.name for c in model.__table__.columns}


@pytest.mark.unit
class TestOrganizationModel:
    """Verify Organization ORM matches 001 migration."""

    def test_tablename(self) -> None:
        assert Organization.__tablename__ == "organizations"

    def test_required_columns(self) -> None:
        cols = _col_names(Organization)
        expected = {
            "id",
            "name",
            "slug",
            "tier",
            "org_path",
            "parent_id",
            "is_active",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(cols), f"Missing: {expected - cols}"

    def test_primary_key_is_id(self) -> None:
        pk_cols = [c.name for c in Organization.__table__.primary_key.columns]
        assert pk_cols == ["id"]

    def test_slug_is_unique(self) -> None:
        col = Organization.__table__.c.slug
        assert col.unique is True

    def test_parent_id_is_nullable(self) -> None:
        col = Organization.__table__.c.parent_id
        assert col.nullable is True

    def test_parent_id_has_fk(self) -> None:
        col = Organization.__table__.c.parent_id
        fks = {str(fk.target_fullname) for fk in col.foreign_keys}
        assert "organizations.id" in fks


@pytest.mark.unit
class TestUserModel:
    """Verify User ORM matches 001 migration."""

    def test_tablename(self) -> None:
        assert User.__tablename__ == "users"

    def test_required_columns(self) -> None:
        cols = _col_names(User)
        expected = {"id", "email", "display_name", "is_active", "created_at", "updated_at"}
        assert expected.issubset(cols), f"Missing: {expected - cols}"

    def test_email_is_unique(self) -> None:
        col = User.__table__.c.email
        assert col.unique is True


@pytest.mark.unit
class TestOrgMemberModel:
    """Verify OrgMember ORM matches 001 migration."""

    def test_tablename(self) -> None:
        assert OrgMember.__tablename__ == "org_members"

    def test_required_columns(self) -> None:
        cols = _col_names(OrgMember)
        expected = {
            "id",
            "org_id",
            "user_id",
            "role",
            "permissions",
            "is_active",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(cols), f"Missing: {expected - cols}"

    def test_org_id_not_nullable(self) -> None:
        col = OrgMember.__table__.c.org_id
        assert col.nullable is False

    def test_user_id_not_nullable(self) -> None:
        col = OrgMember.__table__.c.user_id
        assert col.nullable is False

    def test_org_id_has_fk_to_organizations(self) -> None:
        col = OrgMember.__table__.c.org_id
        fks = {str(fk.target_fullname) for fk in col.foreign_keys}
        assert "organizations.id" in fks

    def test_user_id_has_fk_to_users(self) -> None:
        col = OrgMember.__table__.c.user_id
        fks = {str(fk.target_fullname) for fk in col.foreign_keys}
        assert "users.id" in fks

    def test_unique_constraint_org_user(self) -> None:
        constraints = {
            c.name
            for c in OrgMember.__table__.constraints
            if hasattr(c, "columns") and len(c.columns) > 1
        }
        assert "uq_org_members_org_user" in constraints


@pytest.mark.unit
class TestOrgSettingsModel:
    """Verify OrgSettings ORM matches 001 migration."""

    def test_tablename(self) -> None:
        assert OrgSettings.__tablename__ == "org_settings"

    def test_required_columns(self) -> None:
        cols = _col_names(OrgSettings)
        expected = {
            "id",
            "org_id",
            "settings",
            "model_access",
            "inherit_parent",
            "updated_at",
        }
        assert expected.issubset(cols), f"Missing: {expected - cols}"

    def test_org_id_is_unique(self) -> None:
        col = OrgSettings.__table__.c.org_id
        assert col.unique is True


@pytest.mark.unit
class TestAuditEventModel:
    """Verify AuditEvent ORM matches 002 migration."""

    def test_tablename(self) -> None:
        assert AuditEvent.__tablename__ == "audit_events"

    def test_required_columns(self) -> None:
        cols = _col_names(AuditEvent)
        expected = {
            "id",
            "org_id",
            "user_id",
            "action",
            "resource_type",
            "resource_id",
            "detail",
            "ip_address",
            "user_agent",
            "created_at",
        }
        assert expected.issubset(cols), f"Missing: {expected - cols}"

    def test_org_id_not_nullable(self) -> None:
        col = AuditEvent.__table__.c.org_id
        assert col.nullable is False

    def test_user_id_is_nullable(self) -> None:
        col = AuditEvent.__table__.c.user_id
        assert col.nullable is True

    def test_org_id_has_fk_to_organizations(self) -> None:
        col = AuditEvent.__table__.c.org_id
        fks = {str(fk.target_fullname) for fk in col.foreign_keys}
        assert "organizations.id" in fks

    def test_no_updated_at_column(self) -> None:
        """audit_events is append-only, no updated_at."""
        cols = _col_names(AuditEvent)
        assert "updated_at" not in cols


@pytest.mark.unit
class TestBaseMetadata:
    """Verify Base.metadata includes all Phase 1 tables."""

    def test_all_phase1_tables_registered(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        expected = {"organizations", "users", "org_members", "org_settings", "audit_events"}
        assert expected.issubset(table_names), f"Missing: {expected - table_names}"
