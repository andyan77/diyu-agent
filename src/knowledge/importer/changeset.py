"""ERP/PIM ChangeSet batch import with idempotency and audit.

Milestone: K3-7
Layer: Knowledge

Batch import from ERP/PIM systems with idempotency key deduplication,
audit trail, and rollback support.

See: docs/architecture/02-Knowledge Section 5.4.3 (Batch import)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from src.knowledge.api.write import KnowledgeWriteRequest, KnowledgeWriteService

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChangeSetEntry:
    """A single entry in a changeset."""

    operation: str  # create | update | delete
    entity_type: str
    properties: dict[str, Any]
    idempotency_key: str
    graph_node_id: UUID | None = None  # Required for update/delete
    semantic_content: str | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True)
class ChangeSet:
    """A batch of changes from an ERP/PIM source."""

    changeset_id: UUID
    source_system: str  # erp | pim | admin_import
    org_id: UUID
    entries: list[ChangeSetEntry]
    batch_timestamp: datetime | None = None
    source_user_id: UUID | None = None
    source_request_id: str = ""


@dataclass
class ChangeSetAudit:
    """Audit record for changeset processing."""

    changeset_id: UUID
    source_system: str
    org_id: UUID
    entries_total: int = 0
    entries_processed: int = 0
    entries_failed: int = 0
    entries_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_node_ids: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class ChangeSetResult:
    """Result of processing a changeset."""

    changeset_id: UUID
    processed: int
    failed: int
    skipped: int
    audit: ChangeSetAudit


class ChangeSetProcessor:
    """Processes ERP/PIM batch imports with idempotency.

    Deduplicates via idempotency keys, writes through the
    KnowledgeWriteService, and generates audit records.
    """

    def __init__(self, write_service: KnowledgeWriteService) -> None:
        self._write_service = write_service
        self._processed_keys: dict[str, UUID] = {}  # idempotency_key -> graph_node_id
        self._audits: dict[str, ChangeSetAudit] = {}

    async def process(self, changeset: ChangeSet) -> ChangeSetResult:
        """Process a complete changeset.

        Args:
            changeset: Batch of changes to process.

        Returns:
            ChangeSetResult with processing summary.
        """
        audit = ChangeSetAudit(
            changeset_id=changeset.changeset_id,
            source_system=changeset.source_system,
            org_id=changeset.org_id,
            entries_total=len(changeset.entries),
            started_at=datetime.now(tz=UTC),
        )

        creates = [e for e in changeset.entries if e.operation == "create"]
        updates = [e for e in changeset.entries if e.operation == "update"]
        deletes = [e for e in changeset.entries if e.operation == "delete"]

        # Process creates
        for entry in creates:
            await self._process_create(entry, changeset, audit)

        # Process updates
        for entry in updates:
            await self._process_update(entry, changeset, audit)

        # Process deletes
        for entry in deletes:
            await self._process_delete(entry, changeset, audit)

        audit.completed_at = datetime.now(tz=UTC)
        self._audits[str(changeset.changeset_id)] = audit

        return ChangeSetResult(
            changeset_id=changeset.changeset_id,
            processed=audit.entries_processed,
            failed=audit.entries_failed,
            skipped=audit.entries_skipped,
            audit=audit,
        )

    async def _process_create(
        self,
        entry: ChangeSetEntry,
        changeset: ChangeSet,
        audit: ChangeSetAudit,
    ) -> None:
        """Process a create entry with idempotency."""
        # Idempotency check
        if entry.idempotency_key in self._processed_keys:
            audit.entries_skipped += 1
            return

        try:
            request = KnowledgeWriteRequest(
                entity_type=entry.entity_type,
                properties=entry.properties,
                org_id=changeset.org_id,
                visibility="brand",  # Default for ERP imports
                idempotency_key=entry.idempotency_key,
                source=changeset.source_system,
                semantic_content=entry.semantic_content,
            )

            response = await self._write_service.write(
                request,
                user_id=changeset.source_user_id,
            )

            self._processed_keys[entry.idempotency_key] = response.graph_node_id
            audit.entries_processed += 1
            audit.created_node_ids.append(response.graph_node_id)

        except ValueError as e:
            if "Idempotency key conflict" in str(e):
                audit.entries_skipped += 1
            else:
                audit.entries_failed += 1
                audit.errors.append(f"create {entry.entity_type}: {e}")
        except Exception as e:
            audit.entries_failed += 1
            audit.errors.append(f"create {entry.entity_type}: {e}")

    async def _process_update(
        self,
        entry: ChangeSetEntry,
        changeset: ChangeSet,
        audit: ChangeSetAudit,
    ) -> None:
        """Process an update entry."""
        if entry.graph_node_id is None:
            audit.entries_failed += 1
            audit.errors.append(f"update {entry.entity_type}: graph_node_id required")
            return

        try:
            # Use FK registry to update (via write service's underlying infra)
            fk_registry = self._write_service._fk_registry
            result = await fk_registry._neo4j.update_node(
                entry.graph_node_id,
                entry.properties,
            )
            if result is None:
                audit.entries_failed += 1
                audit.errors.append(
                    f"update {entry.entity_type}: node {entry.graph_node_id} not found"
                )
            else:
                audit.entries_processed += 1
        except Exception as e:
            audit.entries_failed += 1
            audit.errors.append(f"update {entry.entity_type}: {e}")

    async def _process_delete(
        self,
        entry: ChangeSetEntry,
        changeset: ChangeSet,
        audit: ChangeSetAudit,
    ) -> None:
        """Process a delete entry."""
        if entry.graph_node_id is None:
            audit.entries_failed += 1
            audit.errors.append(f"delete {entry.entity_type}: graph_node_id required")
            return

        try:
            fk_registry = self._write_service._fk_registry
            deleted = await fk_registry.delete_with_fk(entry.graph_node_id)
            if deleted:
                audit.entries_processed += 1
            else:
                audit.entries_failed += 1
                audit.errors.append(
                    f"delete {entry.entity_type}: node {entry.graph_node_id} not found"
                )
        except Exception as e:
            audit.entries_failed += 1
            audit.errors.append(f"delete {entry.entity_type}: {e}")

    def get_audit(self, changeset_id: UUID) -> ChangeSetAudit | None:
        """Retrieve audit record for a changeset."""
        return self._audits.get(str(changeset_id))
