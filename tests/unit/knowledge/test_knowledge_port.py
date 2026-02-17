"""Knowledge port contract tests (knowledge-layer perspective).

Phase 2 exit criteria: p2-knowledge-port
Validates KnowledgePort ABC, KnowledgeBundle schema, and stub behavior.
"""

from __future__ import annotations

import inspect
from uuid import UUID

import pytest

from src.ports.knowledge_port import KnowledgePort
from src.shared.types import KnowledgeBundle, OrganizationContext

_TEST_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
_TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000002")


class _StubKnowledgePort(KnowledgePort):
    """Minimal stub implementing KnowledgePort for test purposes."""

    async def resolve(
        self,
        profile_id: str,
        query: str,
        org_context: OrganizationContext,
    ) -> KnowledgeBundle:
        return KnowledgeBundle()

    async def capabilities(self) -> set[str]:
        return {"entity_lookup", "semantic_search"}


@pytest.mark.unit
class TestKnowledgePortABC:
    """KnowledgePort abstract base class contract."""

    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            KnowledgePort()  # type: ignore[abstract]

    def test_resolve_signature(self) -> None:
        sig = inspect.signature(KnowledgePort.resolve)
        params = list(sig.parameters.keys())
        assert "profile_id" in params
        assert "query" in params
        assert "org_context" in params

    def test_capabilities_signature(self) -> None:
        sig = inspect.signature(KnowledgePort.capabilities)
        params = list(sig.parameters.keys())
        assert "self" in params


@pytest.mark.unit
class TestKnowledgeBundleSchema:
    """KnowledgeBundle data structure contract."""

    def test_empty_bundle(self) -> None:
        bundle = KnowledgeBundle()
        assert bundle.entities == {}
        assert bundle.relationships == []
        assert bundle.semantic_contents == []

    def test_bundle_has_required_fields(self) -> None:
        fields = {f.name for f in KnowledgeBundle.__dataclass_fields__.values()}
        assert "entities" in fields
        assert "relationships" in fields
        assert "semantic_contents" in fields


@pytest.mark.unit
class TestStubKnowledgePort:
    """Stub implementation satisfies port contract."""

    @pytest.mark.asyncio
    async def test_resolve_returns_bundle(self) -> None:
        stub = _StubKnowledgePort()
        ctx = OrganizationContext(
            org_id=_TEST_ORG_ID,
            user_id=_TEST_USER_ID,
            org_tier="platform",
            org_path="root",
            role="member",
        )
        result = await stub.resolve("default", "test query", ctx)
        assert isinstance(result, KnowledgeBundle)

    @pytest.mark.asyncio
    async def test_capabilities_returns_set(self) -> None:
        stub = _StubKnowledgePort()
        caps = await stub.capabilities()
        assert isinstance(caps, set)
        assert len(caps) > 0

    def test_stub_is_instance_of_port(self) -> None:
        stub = _StubKnowledgePort()
        assert isinstance(stub, KnowledgePort)
