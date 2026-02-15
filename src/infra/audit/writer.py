"""AuditEventWriter - Append-only audit event recording.

Infrastructure layer component. Writes audit events to the audit_events
table via SQLAlchemy AsyncSession. Enforces:
  - org_id is always required (RLS compliance)
  - action field is non-empty
  - Append-only: no update/delete operations

Usage (Gateway/Infra only -- Brain/Knowledge/Skill MUST NOT import):
    writer = AuditEventWriter(session)
    event_id = await writer.write_event(
        org_id=ctx.org_id,
        action="user.login",
        detail={"method": "password"},
        user_id=ctx.user_id,
    )

See: docs/architecture/06-Infrastructure Section 1 (audit_events)
     TASK-I1-5
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from src.infra.models import AuditEvent
from src.shared.errors import ValidationError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AuditEventWriter:
    """Append-only writer for audit events.

    This class intentionally has NO update/delete methods.
    Audit records are immutable once written.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write_event(
        self,
        *,
        org_id: UUID,
        action: str,
        detail: dict[str, Any],
        user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UUID:
        """Write a single audit event.

        Args:
            org_id: Organization ID (required, RLS scoping).
            action: Action identifier (e.g. "user.login", "org.update").
            detail: Arbitrary JSON-serializable detail payload.
            user_id: Acting user ID (None for system events).
            resource_type: Type of affected resource (e.g. "conversation").
            resource_id: ID of affected resource.
            ip_address: Client IP address.
            user_agent: Client user-agent string.

        Returns:
            UUID of the created audit event.

        Raises:
            ValidationError: If org_id is None or action is empty.
        """
        if org_id is None:
            raise ValidationError("org_id is required for audit events", field="org_id")

        if not action or not action.strip():
            raise ValidationError("action must be non-empty", field="action")

        event_id = uuid4()
        event = AuditEvent(
            id=event_id,
            org_id=org_id,
            user_id=user_id,
            action=action.strip(),
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self._session.add(event)
        await self._session.flush()

        return event_id
