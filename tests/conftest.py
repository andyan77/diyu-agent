"""Root conftest - shared fixtures for all test layers.

Markers:
    @pytest.mark.unit       - No external deps
    @pytest.mark.isolation  - Needs DB (RLS tests)
    @pytest.mark.smoke      - Fast subset
    @pytest.mark.integration - Needs running services
    @pytest.mark.e2e        - End-to-end tests
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.shared.types import ModelAccess, OrganizationContext


@pytest.fixture
def sample_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def sample_org_id() -> UUID:
    return uuid4()


@pytest.fixture
def sample_org_context(sample_user_id: UUID, sample_org_id: UUID) -> OrganizationContext:
    """Default single-tenant org context for testing."""
    return OrganizationContext(
        user_id=sample_user_id,
        org_id=sample_org_id,
        org_tier="brand_hq",
        org_path="platform.brand_hq_001",
        org_chain=[sample_org_id],
        brand_id=sample_org_id,
        role="admin",
        permissions=frozenset({"read", "write", "manage"}),
        org_settings={},
        model_access=ModelAccess(
            allowed_models=["gpt-4o"],
            default_model="gpt-4o",
            budget_monthly_tokens=1_000_000,
        ),
    )
