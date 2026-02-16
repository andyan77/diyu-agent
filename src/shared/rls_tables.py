"""RLS table registry -- single source of truth.

All tenant-scoped tables that MUST have Row-Level Security policies
are declared here, organized by the phase that introduces them.

Consumers:
  - scripts/check_rls.sh (via `uv run python -c "from src.shared.rls_tables import ..."`)
  - tests/isolation/smoke/test_rls_isolation.py
  - Any future RLS verification tooling

Adding a new tenant-scoped table:
  1. Add it to the appropriate PHASE_N_RLS_TABLES list below
  2. Ensure the migration enables RLS + creates isolation policy
  3. Run: make check-rls
"""

from __future__ import annotations

# Phase 1: Security & Tenant Foundation
PHASE_1_RLS_TABLES: list[str] = [
    "organizations",
    "org_members",
    "org_settings",
    "audit_events",
]

# Phase 2+: Add tables here as they are introduced
PHASE_2_RLS_TABLES: list[str] = [
    # "conversations",
    # "messages",
    # "memory_items",
    # "knowledge_items",
    # "knowledge_bundles",
    # "skill_instances",
    # "media_objects",
    # "user_preferences",
]


def get_rls_tables(phase: int | str = "all") -> list[str]:
    """Return RLS tables for a given phase or all phases.

    Args:
        phase: Phase number (1, 2, ...) or "all" for cumulative list.

    Returns:
        List of table names requiring RLS.
    """
    if phase == "all" or phase == 0:
        tables = PHASE_1_RLS_TABLES + PHASE_2_RLS_TABLES
        return [t for t in tables if not t.startswith("#")]
    if phase == 1:
        return list(PHASE_1_RLS_TABLES)
    if phase == 2:
        return PHASE_1_RLS_TABLES + PHASE_2_RLS_TABLES
    return PHASE_1_RLS_TABLES + PHASE_2_RLS_TABLES


__all__ = [
    "PHASE_1_RLS_TABLES",
    "PHASE_2_RLS_TABLES",
    "get_rls_tables",
]
