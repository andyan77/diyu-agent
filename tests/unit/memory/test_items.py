"""Unit tests for memory items CRUD versioned (MC2-3).

Complies with no-mock policy.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.memory.items import MemoryItemStore
from src.shared.types import MemoryItem

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store() -> MemoryItemStore:
    return MemoryItemStore()


@pytest.fixture()
def user_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMemoryItemStore:
    """MC2-3: memory_items CRUD with version chain."""

    def test_create_returns_version_1(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        item = store.create(
            user_id=user_id,
            memory_type="observation",
            content="User likes coffee",
        )
        assert isinstance(item, MemoryItem)
        assert item.version == 1
        assert item.superseded_by is None

    def test_get_by_id(self, store: MemoryItemStore, user_id) -> None:
        item = store.create(
            user_id=user_id,
            memory_type="observation",
            content="test",
        )
        found = store.get(item.memory_id)
        assert found is not None
        assert found.memory_id == item.memory_id

    def test_get_nonexistent_returns_none(
        self,
        store: MemoryItemStore,
    ) -> None:
        assert store.get(uuid4()) is None

    def test_update_creates_new_version(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        v1 = store.create(
            user_id=user_id,
            memory_type="observation",
            content="original",
        )
        v2 = store.update(v1.memory_id, content="updated")

        assert v2.version == 2
        assert v2.content == "updated"
        assert v2.superseded_by is None

        # Old version is superseded
        old = store.get(v1.memory_id)
        assert old is not None
        assert old.superseded_by == v2.memory_id
        assert old.invalid_at is not None

    def test_update_nonexistent_raises(
        self,
        store: MemoryItemStore,
    ) -> None:
        with pytest.raises(KeyError):
            store.update(uuid4(), content="x")

    def test_update_superseded_raises(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        v1 = store.create(
            user_id=user_id,
            memory_type="observation",
            content="v1",
        )
        store.update(v1.memory_id, content="v2")
        with pytest.raises(ValueError, match="superseded"):
            store.update(v1.memory_id, content="v3")

    def test_get_latest_follows_chain(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        v1 = store.create(
            user_id=user_id,
            memory_type="observation",
            content="v1",
        )
        v2 = store.update(v1.memory_id, content="v2")
        v3 = store.update(v2.memory_id, content="v3")

        latest = store.get_latest(v1.memory_id)
        assert latest is not None
        assert latest.memory_id == v3.memory_id
        assert latest.version == 3

    def test_version_history_complete(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        v1 = store.create(
            user_id=user_id,
            memory_type="observation",
            content="v1",
        )
        v2 = store.update(v1.memory_id, content="v2")
        store.update(v2.memory_id, content="v3")

        history = store.get_version_history(v1.memory_id)
        assert len(history) == 3
        assert history[0].version == 1
        assert history[1].version == 2
        assert history[2].version == 3

    def test_list_active_excludes_superseded(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        v1 = store.create(
            user_id=user_id,
            memory_type="observation",
            content="v1",
        )
        store.update(v1.memory_id, content="v2")
        store.create(
            user_id=user_id,
            memory_type="preference",
            content="likes tea",
        )

        active = store.list_active(user_id)
        assert len(active) == 2
        for item in active:
            assert item.superseded_by is None

    def test_update_preserves_user_id(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        v1 = store.create(
            user_id=user_id,
            memory_type="observation",
            content="v1",
        )
        v2 = store.update(v1.memory_id, content="v2")
        assert v2.user_id == user_id

    def test_update_confidence(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        v1 = store.create(
            user_id=user_id,
            memory_type="observation",
            content="test",
            confidence=0.5,
        )
        v2 = store.update(v1.memory_id, confidence=0.9)
        assert v2.confidence == 0.9
        assert v2.content == "test"  # content unchanged

    def test_create_with_epistemic_type(
        self,
        store: MemoryItemStore,
        user_id,
    ) -> None:
        item = store.create(
            user_id=user_id,
            memory_type="preference",
            content="likes tea",
            epistemic_type="preference",
        )
        assert item.epistemic_type == "preference"
