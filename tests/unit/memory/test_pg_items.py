"""Unit tests for PgMemoryItemStore (MC2-3).

Tests PgMemoryItemStore using Fake adapters instead of unittest.mock.
Verifies: add_item, get_item, get_items_for_user, update_item, supersede_item.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.memory.items import PgMemoryItemStore
from src.shared.types import MemoryItem
from tests.fakes import FakeAsyncSession, FakeOrmRow, FakeSessionFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orm_row(
    *,
    user_id=None,
    org_id=None,
    memory_type="observation",
    content="test content",
    confidence=1.0,
    version=1,
    superseded_by=None,
    epistemic_type="fact",
) -> FakeOrmRow:
    """Create a FakeOrmRow representing a MemoryItemModel row."""
    return FakeOrmRow(
        id=uuid4(),
        user_id=user_id or uuid4(),
        org_id=org_id or uuid4(),
        memory_type=memory_type,
        content=content,
        confidence=confidence,
        version=version,
        superseded_by=superseded_by,
        epistemic_type=epistemic_type,
        source_sessions=[],
        provenance=None,
        valid_at=datetime.now(UTC),
        invalid_at=None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def user_id():
    return uuid4()


@pytest.fixture()
def org_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPgMemoryItemStore:
    """MC2-3: PG-backed memory item store."""

    async def test_add_item_creates_row_and_commits(
        self,
        user_id,
        org_id,
    ) -> None:
        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        item = await store.add_item(
            user_id=user_id,
            org_id=org_id,
            memory_type="observation",
            content="User prefers Python",
        )

        assert isinstance(item, MemoryItem)
        assert item.user_id == user_id
        assert item.memory_type == "observation"
        assert item.content == "User prefers Python"
        assert item.version == 1
        assert item.superseded_by is None
        assert len(session.added) == 1
        assert session.committed is True

    async def test_add_item_with_optional_fields(
        self,
        user_id,
        org_id,
    ) -> None:
        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        source_session = uuid4()
        item = await store.add_item(
            user_id=user_id,
            org_id=org_id,
            memory_type="preference",
            content="likes coffee",
            confidence=0.8,
            epistemic_type="preference",
            source_session_id=source_session,
        )

        assert item.confidence == 0.8
        assert item.epistemic_type == "preference"
        assert source_session in item.source_sessions

    async def test_get_item_returns_item(
        self,
        user_id,
    ) -> None:
        row = _make_orm_row(user_id=user_id)
        session = FakeAsyncSession()
        session.set_execute_result(scalar_one_or_none_value=row)
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        result = await store.get_item(row.id)

        assert result is not None
        assert isinstance(result, MemoryItem)
        assert result.memory_id == row.id
        assert result.user_id == row.user_id

    async def test_get_item_nonexistent_returns_none(self) -> None:
        session = FakeAsyncSession()
        session.set_execute_result(scalar_one_or_none_value=None)
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        result = await store.get_item(uuid4())

        assert result is None

    async def test_get_items_for_user_returns_list(
        self,
        user_id,
        org_id,
    ) -> None:
        rows = [
            _make_orm_row(user_id=user_id, org_id=org_id, content=f"item {i}") for i in range(3)
        ]
        session = FakeAsyncSession()
        session.set_scalars_result(rows)
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        items = await store.get_items_for_user(user_id)

        assert len(items) == 3
        for item in items:
            assert isinstance(item, MemoryItem)
            assert item.user_id == user_id

    async def test_get_items_for_user_empty(self) -> None:
        session = FakeAsyncSession()
        session.set_scalars_result([])
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        items = await store.get_items_for_user(uuid4())

        assert items == []

    async def test_update_item_creates_new_version(
        self,
        user_id,
        org_id,
    ) -> None:
        original = _make_orm_row(
            user_id=user_id,
            org_id=org_id,
            content="original content",
            version=1,
        )
        session = FakeAsyncSession()
        session.set_execute_result(scalar_one_or_none_value=original)
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        updated = await store.update_item(
            original.id,
            content="updated content",
        )

        assert isinstance(updated, MemoryItem)
        assert updated.content == "updated content"
        assert updated.version == 2
        assert updated.user_id == user_id
        assert len(session.added) == 1
        assert session.committed is True

    async def test_update_item_not_found_raises(self) -> None:
        session = FakeAsyncSession()
        session.set_execute_result(scalar_one_or_none_value=None)
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        with pytest.raises(KeyError):
            await store.update_item(uuid4(), content="new")

    async def test_supersede_item_sets_superseded_by(
        self,
        user_id,
        org_id,
    ) -> None:
        original = _make_orm_row(
            user_id=user_id,
            org_id=org_id,
            content="v1",
            version=1,
        )
        session = FakeAsyncSession()
        session.set_execute_result(scalar_one_or_none_value=original)
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        new_id = uuid4()
        await store.supersede_item(original.id, new_memory_id=new_id)

        assert session.committed is True
        assert original.superseded_by == new_id

    async def test_get_items_for_user_only_active_by_default(
        self,
        user_id,
    ) -> None:
        rows = [
            _make_orm_row(user_id=user_id, superseded_by=None),
        ]
        session = FakeAsyncSession()
        session.set_scalars_result(rows)
        factory = FakeSessionFactory(session)
        store = PgMemoryItemStore(session_factory=factory)

        items = await store.get_items_for_user(user_id, active_only=True)

        assert len(items) == 1
        assert items[0].superseded_by is None
