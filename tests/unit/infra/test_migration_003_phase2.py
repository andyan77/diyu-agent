"""Unit tests for migration 003_create_conversation_events -- phase2.

Tests migration module attributes and structure WITHOUT mocks.
Complies with no-mock policy.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
class TestMigration003Phase2:
    """Verify migration 003 structure and attributes (phase2)."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = importlib.import_module("migrations.versions.003_create_conversation_events")

    def test_revision_id(self) -> None:
        assert self.mod.revision == "003_conversation_events"

    def test_down_revision_chain(self) -> None:
        assert self.mod.down_revision == "002_audit_events"

    def test_upgrade_function_exists(self) -> None:
        assert callable(getattr(self.mod, "upgrade", None))

    def test_downgrade_function_exists(self) -> None:
        assert callable(getattr(self.mod, "downgrade", None))

    def test_upgrade_source_contains_table_name(self) -> None:
        """The upgrade function source must reference conversation_events."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "conversation_events" in source

    def test_upgrade_source_contains_content_schema_version(self) -> None:
        """I2-4 requirement: content_schema_version column must exist."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "content_schema_version" in source

    def test_upgrade_source_contains_session_id(self) -> None:
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "session_id" in source

    def test_upgrade_source_contains_rls_policy(self) -> None:
        """RLS isolation is mandatory for tenant-scoped tables."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "ROW LEVEL SECURITY" in source
        assert "conversation_events_isolation" in source
        assert "app.current_org_id" in source

    def test_downgrade_drops_policy_and_table(self) -> None:
        import inspect

        source = inspect.getsource(self.mod.downgrade)
        assert "conversation_events_isolation" in source
        assert "conversation_events" in source

    def test_upgrade_contains_sequence_number(self) -> None:
        """Ordering within session requires sequence_number."""
        import inspect

        source = inspect.getsource(self.mod.upgrade)
        assert "sequence_number" in source
