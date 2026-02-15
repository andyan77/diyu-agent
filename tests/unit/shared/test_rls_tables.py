"""Tests for src/shared/rls_tables.py (RLS table SSOT).

WF-P0.3: Validates the single source of truth for RLS table lists.
Ensures consistency between the SSOT and consumers.
"""

from __future__ import annotations

import pytest

from src.shared.rls_tables import (
    PHASE_1_RLS_TABLES,
    PHASE_2_RLS_TABLES,
    get_rls_tables,
)


@pytest.mark.unit
class TestPhase1RLSTables:
    """Phase 1 RLS table list correctness."""

    def test_phase1_contains_organizations(self) -> None:
        assert "organizations" in PHASE_1_RLS_TABLES

    def test_phase1_contains_org_members(self) -> None:
        assert "org_members" in PHASE_1_RLS_TABLES

    def test_phase1_contains_org_settings(self) -> None:
        assert "org_settings" in PHASE_1_RLS_TABLES

    def test_phase1_contains_audit_events(self) -> None:
        assert "audit_events" in PHASE_1_RLS_TABLES

    def test_phase1_has_exactly_4_tables(self) -> None:
        assert len(PHASE_1_RLS_TABLES) == 4

    def test_no_duplicates_in_phase1(self) -> None:
        assert len(PHASE_1_RLS_TABLES) == len(set(PHASE_1_RLS_TABLES))


@pytest.mark.unit
class TestGetRLSTables:
    """get_rls_tables() function behavior."""

    def test_phase_1_returns_phase1_tables(self) -> None:
        result = get_rls_tables(1)
        assert set(result) == set(PHASE_1_RLS_TABLES)

    def test_phase_all_includes_phase1(self) -> None:
        result = get_rls_tables("all")
        for table in PHASE_1_RLS_TABLES:
            assert table in result

    def test_default_is_all(self) -> None:
        result_default = get_rls_tables()
        result_all = get_rls_tables("all")
        assert result_default == result_all

    def test_phase_0_same_as_all(self) -> None:
        result_0 = get_rls_tables(0)
        result_all = get_rls_tables("all")
        assert result_0 == result_all

    def test_returns_list_type(self) -> None:
        result = get_rls_tables(1)
        assert isinstance(result, list)

    def test_phase1_result_is_independent_copy(self) -> None:
        """Mutating result does not affect the source."""
        result = get_rls_tables(1)
        result.append("fake_table")
        assert "fake_table" not in PHASE_1_RLS_TABLES


@pytest.mark.unit
class TestRLSTablesConsistency:
    """Cross-check SSOT against known consumers."""

    def test_phase1_tables_match_model_tablenames(self) -> None:
        """Phase 1 RLS tables should correspond to ORM models with org_id."""
        from src.infra.models import AuditEvent, Organization, OrgMember, OrgSettings

        orm_tables = {
            Organization.__tablename__,
            OrgMember.__tablename__,
            OrgSettings.__tablename__,
            AuditEvent.__tablename__,
        }
        assert set(PHASE_1_RLS_TABLES) == orm_tables

    def test_no_overlap_between_phases(self) -> None:
        """Tables should not appear in multiple phase lists."""
        active_phase2 = [t for t in PHASE_2_RLS_TABLES if not t.startswith("#")]
        overlap = set(PHASE_1_RLS_TABLES) & set(active_phase2)
        assert len(overlap) == 0, f"Duplicate tables across phases: {overlap}"
