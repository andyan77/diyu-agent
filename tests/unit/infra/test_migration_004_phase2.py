"""Unit tests for migration 004_create_memory_items -- phase2.

Tests migration module attributes and structure WITHOUT mocks.
Complies with no-mock policy.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
class TestMigration004Phase2:
    """Verify migration 004 structure and attributes (phase2)."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = importlib.import_module("migrations.versions.004_create_memory_items")

    def test_revision_id(self) -> None:
        assert self.mod.revision == "004_memory_items"

    def test_down_revision_chain(self) -> None:
        assert self.mod.down_revision == "003_conversation_events"

    def test_upgrade_function_exists(self) -> None:
        assert callable(getattr(self.mod, "upgrade", None))

    def test_downgrade_function_exists(self) -> None:
        assert callable(getattr(self.mod, "downgrade", None))

    def test_upgrade_source_contains_memory_items(self) -> None:
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "memory_items" in source

    def test_upgrade_source_contains_pgvector_extension(self) -> None:
        """I2-5 requirement: pgvector extension must be enabled."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "CREATE EXTENSION" in source
        assert "vector" in source

    def test_upgrade_source_contains_embedding_column(self) -> None:
        """I2-5 requirement: embedding column for vector storage."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "embedding" in source
        assert "vector(1536)" in source

    def test_upgrade_source_contains_hnsw_index(self) -> None:
        """HNSW index for efficient vector similarity search."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "hnsw" in source
        assert "vector_cosine_ops" in source

    def test_upgrade_source_contains_last_validated_at(self) -> None:
        """I2-5 requirement: last_validated_at column."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "last_validated_at" in source

    def test_upgrade_source_contains_memory_receipts(self) -> None:
        """memory_receipts table for MC2-6 support."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "memory_receipts" in source

    def test_upgrade_source_contains_rls_policies(self) -> None:
        """RLS isolation mandatory for both tables."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "memory_items_isolation" in source
        assert "memory_receipts_isolation" in source
        assert "app.current_org_id" in source

    def test_downgrade_drops_tables_in_order(self) -> None:
        """Downgrade must drop memory_receipts first (FK dependency)."""
        import inspect

        source = inspect.getsource(self.mod.downgrade)
        receipts_pos = source.index("memory_receipts")
        items_pos = source.index("memory_items")
        assert receipts_pos < items_pos, "memory_receipts must be dropped before memory_items"

    def test_upgrade_source_contains_versioning(self) -> None:
        """Version column for MC2-3 versioned CRUD."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert '"version"' in source or "'version'" in source or "version" in source
