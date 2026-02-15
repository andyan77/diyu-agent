"""OrgContext gateway tests.

Phase 1 gate check: p1-orgcontext
Tests the OrgContextPort contract and its stub implementation.

Validates:
- OrgContextPort interface compliance
- Default stub returns valid OrganizationContext
- org_id isolation is enforced
- Tier hierarchy is respected
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest

from src.ports.org_context import OrgContextPort
from src.shared.errors import AuthenticationError
from src.shared.types import ModelAccess, OrganizationContext


class StubOrgContext(OrgContextPort):
    """Day-1 stub: returns default single-tenant context.

    Validates tokens are non-empty. Returns fixed context per org_id.
    """

    def __init__(self) -> None:
        self._org_registry: dict[UUID, dict] = {}

    def register_org(self, org_id: UUID, tier: str = "brand_hq", role: str = "admin") -> None:
        self._org_registry[org_id] = {"tier": tier, "role": role}

    async def get_org_context(
        self,
        user_id: UUID,
        org_id: UUID,
        token: str,
    ) -> OrganizationContext:
        if not token or not token.strip():
            raise AuthenticationError("Token is required")

        org_info = self._org_registry.get(org_id, {"tier": "brand_hq", "role": "member"})

        return OrganizationContext(
            user_id=user_id,
            org_id=org_id,
            org_tier=org_info["tier"],
            org_path=f"platform.{org_id}",
            org_chain=[org_id],
            brand_id=org_id,
            role=org_info["role"],
            permissions=frozenset({"read"}),
            org_settings={},
            model_access=ModelAccess(
                allowed_models=["gpt-4o"],
                default_model="gpt-4o",
                budget_monthly_tokens=100_000,
            ),
        )


def _run(coro):
    """Run async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.mark.unit
class TestOrgContextPortContract:
    """Verify OrgContextPort interface and stub behavior."""

    @pytest.fixture
    def stub(self) -> StubOrgContext:
        return StubOrgContext()

    @pytest.fixture
    def user_id(self) -> UUID:
        return uuid4()

    @pytest.fixture
    def org_id(self) -> UUID:
        return uuid4()

    @pytest.mark.smoke
    def test_get_org_context_returns_valid_context(
        self, stub: StubOrgContext, user_id: UUID, org_id: UUID
    ) -> None:
        ctx = _run(stub.get_org_context(user_id, org_id, "valid-token"))
        assert isinstance(ctx, OrganizationContext)
        assert ctx.user_id == user_id
        assert ctx.org_id == org_id

    def test_context_has_required_fields(
        self, stub: StubOrgContext, user_id: UUID, org_id: UUID
    ) -> None:
        ctx = _run(stub.get_org_context(user_id, org_id, "valid-token"))
        valid_tiers = (
            "platform",
            "brand_hq",
            "brand_dept",
            "regional_agent",
            "franchise_store",
        )
        assert ctx.org_tier in valid_tiers
        assert len(ctx.org_path) > 0
        assert len(ctx.org_chain) > 0
        assert ctx.role != ""
        assert isinstance(ctx.permissions, frozenset)

    def test_context_has_model_access(
        self, stub: StubOrgContext, user_id: UUID, org_id: UUID
    ) -> None:
        ctx = _run(stub.get_org_context(user_id, org_id, "valid-token"))
        assert ctx.model_access is not None
        assert len(ctx.model_access.allowed_models) > 0
        assert ctx.model_access.default_model != ""
        assert ctx.model_access.budget_monthly_tokens > 0

    @pytest.mark.smoke
    def test_empty_token_raises_auth_error(
        self, stub: StubOrgContext, user_id: UUID, org_id: UUID
    ) -> None:
        with pytest.raises(AuthenticationError):
            _run(stub.get_org_context(user_id, org_id, ""))

    def test_whitespace_token_raises_auth_error(
        self, stub: StubOrgContext, user_id: UUID, org_id: UUID
    ) -> None:
        with pytest.raises(AuthenticationError):
            _run(stub.get_org_context(user_id, org_id, "   "))

    def test_different_orgs_return_different_contexts(
        self, stub: StubOrgContext, user_id: UUID
    ) -> None:
        org_a = uuid4()
        org_b = uuid4()
        ctx_a = _run(stub.get_org_context(user_id, org_a, "token-a"))
        ctx_b = _run(stub.get_org_context(user_id, org_b, "token-b"))
        assert ctx_a.org_id != ctx_b.org_id
        assert ctx_a.org_path != ctx_b.org_path

    def test_registered_org_uses_custom_tier(self, stub: StubOrgContext, user_id: UUID) -> None:
        org_id = uuid4()
        stub.register_org(org_id, tier="franchise_store", role="viewer")
        ctx = _run(stub.get_org_context(user_id, org_id, "token"))
        assert ctx.org_tier == "franchise_store"
        assert ctx.role == "viewer"

    def test_stub_is_instance_of_port(self, stub: StubOrgContext) -> None:
        assert isinstance(stub, OrgContextPort)

    def test_port_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            OrgContextPort()  # type: ignore[abstract]
