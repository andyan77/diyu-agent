"""AuditEventWriter unit tests.

Phase 1 (I1-5): audit_events table + audit writer
Acceptance: pytest tests/unit/infra/test_audit.py -v

Validates:
- Append-only write behavior
- org_id is always required (RLS compliance)
- action field validation
- No update/delete methods exist (immutable)
- Correct AuditEvent ORM construction
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.infra.audit.writer import AuditEventWriter
from src.infra.models import AuditEvent
from src.shared.errors import ValidationError


def _make_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.unit
class TestAuditEventWriterContract:
    """Verify AuditEventWriter interface and append-only constraint."""

    def test_has_write_event_method(self) -> None:
        assert hasattr(AuditEventWriter, "write_event")
        assert callable(AuditEventWriter.write_event)

    def test_no_update_method(self) -> None:
        """Append-only: update is forbidden."""
        assert not hasattr(AuditEventWriter, "update_event")
        assert not hasattr(AuditEventWriter, "update")

    def test_no_delete_method(self) -> None:
        """Append-only: delete is forbidden."""
        assert not hasattr(AuditEventWriter, "delete_event")
        assert not hasattr(AuditEventWriter, "delete")

    def test_no_modify_method(self) -> None:
        """Append-only: modify/edit is forbidden."""
        assert not hasattr(AuditEventWriter, "modify")
        assert not hasattr(AuditEventWriter, "edit")


@pytest.mark.unit
class TestAuditEventWriterBehavior:
    """Verify write_event creates correct AuditEvent records."""

    @pytest.fixture
    def session(self) -> AsyncMock:
        return _make_session()

    @pytest.fixture
    def writer(self, session: AsyncMock) -> AuditEventWriter:
        return AuditEventWriter(session)

    @pytest.fixture
    def org_id(self):
        return uuid4()

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_write_event_returns_uuid(self, writer, org_id) -> None:
        event_id = await writer.write_event(
            org_id=org_id,
            action="user.login",
            detail={"method": "password"},
        )
        assert event_id is not None

    @pytest.mark.asyncio
    async def test_write_event_adds_to_session(self, writer, session, org_id) -> None:
        await writer.write_event(
            org_id=org_id,
            action="user.login",
            detail={},
        )
        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, AuditEvent)

    @pytest.mark.asyncio
    async def test_write_event_flushes_session(self, writer, session, org_id) -> None:
        await writer.write_event(
            org_id=org_id,
            action="user.login",
            detail={},
        )
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_write_event_sets_org_id(self, writer, session, org_id) -> None:
        await writer.write_event(
            org_id=org_id,
            action="org.update",
            detail={"field": "name"},
        )
        added_obj = session.add.call_args[0][0]
        assert added_obj.org_id == org_id

    @pytest.mark.asyncio
    async def test_write_event_sets_action(self, writer, session, org_id) -> None:
        await writer.write_event(
            org_id=org_id,
            action="data.export",
            detail={},
        )
        added_obj = session.add.call_args[0][0]
        assert added_obj.action == "data.export"

    @pytest.mark.asyncio
    async def test_write_event_sets_detail(self, writer, session, org_id) -> None:
        detail = {"key": "value", "count": 42}
        await writer.write_event(
            org_id=org_id,
            action="data.export",
            detail=detail,
        )
        added_obj = session.add.call_args[0][0]
        assert added_obj.detail == detail

    @pytest.mark.asyncio
    async def test_write_event_with_user_id(self, writer, session, org_id, user_id) -> None:
        await writer.write_event(
            org_id=org_id,
            action="user.login",
            detail={},
            user_id=user_id,
        )
        added_obj = session.add.call_args[0][0]
        assert added_obj.user_id == user_id

    @pytest.mark.asyncio
    async def test_write_event_user_id_defaults_none(
        self,
        writer,
        session,
        org_id,
    ) -> None:
        await writer.write_event(
            org_id=org_id,
            action="system.startup",
            detail={},
        )
        added_obj = session.add.call_args[0][0]
        assert added_obj.user_id is None

    @pytest.mark.asyncio
    async def test_write_event_with_optional_fields(
        self,
        writer,
        session,
        org_id,
        user_id,
    ) -> None:
        resource_id = uuid4()
        await writer.write_event(
            org_id=org_id,
            action="conversation.create",
            detail={"title": "test"},
            user_id=user_id,
            resource_type="conversation",
            resource_id=resource_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        added_obj = session.add.call_args[0][0]
        assert added_obj.resource_type == "conversation"
        assert added_obj.resource_id == resource_id
        assert added_obj.ip_address == "192.168.1.1"
        assert added_obj.user_agent == "Mozilla/5.0"


@pytest.mark.unit
class TestAuditEventWriterValidation:
    """Verify input validation enforces RLS compliance."""

    @pytest.fixture
    def session(self) -> AsyncMock:
        return _make_session()

    @pytest.fixture
    def writer(self, session: AsyncMock) -> AuditEventWriter:
        return AuditEventWriter(session)

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_empty_action_raises_validation_error(self, writer) -> None:
        with pytest.raises(ValidationError):
            await writer.write_event(
                org_id=uuid4(),
                action="",
                detail={},
            )

    @pytest.mark.asyncio
    async def test_whitespace_action_raises_validation_error(self, writer) -> None:
        with pytest.raises(ValidationError):
            await writer.write_event(
                org_id=uuid4(),
                action="   ",
                detail={},
            )

    @pytest.mark.asyncio
    async def test_none_org_id_raises_validation_error(self, writer) -> None:
        with pytest.raises(ValidationError):
            await writer.write_event(
                org_id=None,  # type: ignore[arg-type]
                action="user.login",
                detail={},
            )
