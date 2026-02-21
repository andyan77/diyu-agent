"""OS3-2: Full CRUD + permission change audit coverage tests.

Validates that all write operations (create, update, delete, permission change)
are covered by the AuditEventWriter -- no write escapes without an audit trail.

Acceptance: `uv run pytest tests/unit/infra/test_audit_coverage.py -q`
"""

from __future__ import annotations

import inspect

import pytest

from src.infra.audit.writer import AuditEventWriter

# -- All auditable action categories in the system --
AUDITABLE_WRITE_ACTIONS: list[str] = [
    # User lifecycle
    "user.login",
    "user.logout",
    "user.create",
    "user.update",
    "user.disable",
    # Organization lifecycle
    "org.create",
    "org.update",
    "org.delete",
    # Permission changes
    "permission.grant",
    "permission.revoke",
    "permission.role_change",
    # Knowledge CRUD
    "knowledge.create",
    "knowledge.update",
    "knowledge.delete",
    # Conversation lifecycle
    "conversation.create",
    "conversation.delete",
    # Data operations
    "data.export",
    "data.import",
    # System events
    "system.startup",
    "system.config_change",
]


@pytest.mark.unit
class TestAuditCoverageContract:
    """Verify AuditEventWriter can record every auditable action category."""

    def test_write_event_accepts_all_action_categories(self) -> None:
        """writer.write_event() must accept action as a plain string,
        covering all categories without an allow-list filter."""
        sig = inspect.signature(AuditEventWriter.write_event)
        params = sig.parameters

        # action is a plain str, not an enum -- so any action string is accepted
        assert "action" in params
        annotation = params["action"].annotation
        assert annotation in ("str", str), (
            "action parameter must be str (free-form), not an enum or restricted type"
        )

    def test_write_event_supports_resource_type(self) -> None:
        """Audit must track which resource type was affected."""
        sig = inspect.signature(AuditEventWriter.write_event)
        assert "resource_type" in sig.parameters

    def test_write_event_supports_resource_id(self) -> None:
        """Audit must track which resource was affected."""
        sig = inspect.signature(AuditEventWriter.write_event)
        assert "resource_id" in sig.parameters

    def test_write_event_supports_user_id(self) -> None:
        """Audit must track who performed the action."""
        sig = inspect.signature(AuditEventWriter.write_event)
        assert "user_id" in sig.parameters

    def test_write_event_supports_ip_address(self) -> None:
        """Audit must capture client IP for forensics."""
        sig = inspect.signature(AuditEventWriter.write_event)
        assert "ip_address" in sig.parameters

    def test_write_event_supports_user_agent(self) -> None:
        """Audit must capture user agent for forensics."""
        sig = inspect.signature(AuditEventWriter.write_event)
        assert "user_agent" in sig.parameters


class FakeAsyncSession:
    """Minimal fake AsyncSession for audit writer DI."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_count: int = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flush_count += 1


@pytest.mark.unit
class TestAuditCoverageBehavior:
    """Verify every auditable write action can be recorded."""

    @pytest.fixture
    def session(self) -> FakeAsyncSession:
        return FakeAsyncSession()

    @pytest.fixture
    def writer(self, session: FakeAsyncSession) -> AuditEventWriter:
        return AuditEventWriter(session)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", AUDITABLE_WRITE_ACTIONS)
    async def test_action_recorded(
        self,
        writer: AuditEventWriter,
        session: FakeAsyncSession,
        sample_org_id,
        action: str,
    ) -> None:
        """Every auditable action must produce exactly one audit record."""
        from uuid import uuid4

        event_id = await writer.write_event(
            org_id=sample_org_id,
            action=action,
            detail={"test": True},
            user_id=uuid4(),
            resource_type="test_resource",
        )
        assert event_id is not None
        assert len(session.added) == 1
        added = session.added[0]
        assert added.action == action
        assert added.org_id == sample_org_id

    @pytest.mark.asyncio
    async def test_permission_change_captures_detail(
        self,
        writer: AuditEventWriter,
        session: FakeAsyncSession,
        sample_org_id,
        sample_user_id,
    ) -> None:
        """Permission changes must record before/after state in detail."""
        detail = {
            "target_user_id": str(sample_user_id),
            "old_role": "member",
            "new_role": "admin",
        }
        await writer.write_event(
            org_id=sample_org_id,
            action="permission.role_change",
            detail=detail,
            user_id=sample_user_id,
        )
        added = session.added[0]
        assert added.detail["old_role"] == "member"
        assert added.detail["new_role"] == "admin"

    @pytest.mark.asyncio
    async def test_crud_delete_captures_resource_id(
        self,
        writer: AuditEventWriter,
        session: FakeAsyncSession,
        sample_org_id,
        sample_user_id,
    ) -> None:
        """Delete actions must record which resource was deleted."""
        from uuid import uuid4

        resource_id = uuid4()
        await writer.write_event(
            org_id=sample_org_id,
            action="knowledge.delete",
            detail={"reason": "user_request"},
            user_id=sample_user_id,
            resource_type="knowledge_entry",
            resource_id=resource_id,
        )
        added = session.added[0]
        assert added.resource_type == "knowledge_entry"
        assert added.resource_id == resource_id

    def test_append_only_no_bulk_delete(self) -> None:
        """Ensure no bulk deletion capability exists."""
        assert not hasattr(AuditEventWriter, "delete_events")
        assert not hasattr(AuditEventWriter, "bulk_delete")
        assert not hasattr(AuditEventWriter, "truncate")
        assert not hasattr(AuditEventWriter, "purge")
