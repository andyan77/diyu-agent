"""K3-5: Diyu Resolver tests.

Tests: profile resolution, graph-only and graph-first strategies,
entity grouping, error handling.
Uses Fake adapter pattern (no unittest.mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from src.knowledge.resolver.resolver import BUILTIN_PROFILES, DiyuResolver, ResolverProfile
from src.shared.types import OrganizationContext

# -- Fake adapters --


class FakeSession:
    """Fake Neo4j session that returns pre-configured results."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    async def run(self, query: str, **kwargs: Any) -> FakeResult:
        return FakeResult(self._records)

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class FakeResult:
    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records
        self._idx = 0

    def __aiter__(self) -> FakeResult:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._idx >= len(self._records):
            raise StopAsyncIteration
        record = self._records[self._idx]
        self._idx += 1
        return record


@dataclass
class FakeDriver:
    _records: list[dict[str, Any]] = field(default_factory=list)

    def session(self) -> FakeSession:
        return FakeSession(self._records)


@dataclass
class FakeNeo4jAdapter:
    _driver: FakeDriver = field(default_factory=FakeDriver)

    @property
    def driver(self) -> FakeDriver:
        return self._driver


@dataclass
class FakeQdrantAdapter:
    _collection_name: str = "knowledge_vectors"
    _vector_size: int = 1536


# -- Tests --


class TestBuiltinProfiles:
    def test_role_adaptation_exists(self) -> None:
        assert "core:role_adaptation" in BUILTIN_PROFILES

    def test_brand_context_exists(self) -> None:
        assert "core:brand_context" in BUILTIN_PROFILES

    def test_role_adaptation_is_graph_only(self) -> None:
        p = BUILTIN_PROFILES["core:role_adaptation"]
        assert p.fk_strategy == "none"
        assert p.vector_search is False

    def test_brand_context_has_fk_enrichment(self) -> None:
        p = BUILTIN_PROFILES["core:brand_context"]
        assert p.fk_strategy == "graph_first"
        assert p.vector_search is True


class TestResolverGraphOnly:
    @pytest.mark.asyncio
    async def test_resolve_empty_graph(self) -> None:
        neo4j = FakeNeo4jAdapter()
        qdrant = FakeQdrantAdapter()
        resolver = DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]
        org = OrganizationContext(
            user_id=uuid4(), org_id=uuid4(), org_tier="brand_hq", org_path="root"
        )

        bundle = await resolver.resolve("core:role_adaptation", "test query", org)
        assert bundle.metadata is not None
        assert bundle.metadata.profile_id == "core:role_adaptation"
        assert bundle.metadata.graph_hits == 0

    @pytest.mark.asyncio
    async def test_resolve_with_nodes(self) -> None:
        nid = uuid4()
        records = [
            {
                "n": {
                    "node_id": str(nid),
                    "org_id": str(uuid4()),
                    "sync_status": "synced",
                    "role": "admin",
                    "prompt_template": "You are an admin",
                },
                "labels": ["RoleAdaptationRule"],
            }
        ]
        neo4j = FakeNeo4jAdapter(_driver=FakeDriver(_records=records))
        qdrant = FakeQdrantAdapter()
        resolver = DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]
        org = OrganizationContext(
            user_id=uuid4(), org_id=uuid4(), org_tier="brand_hq", org_path="root"
        )

        bundle = await resolver.resolve("core:role_adaptation", "test query", org)
        assert bundle.metadata is not None
        assert bundle.metadata.graph_hits == 1
        assert "RoleAdaptationRule" in bundle.entities


class TestResolverProfileRegistration:
    @pytest.mark.asyncio
    async def test_unknown_profile_raises(self) -> None:
        neo4j = FakeNeo4jAdapter()
        qdrant = FakeQdrantAdapter()
        resolver = DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]
        org = OrganizationContext(
            user_id=uuid4(), org_id=uuid4(), org_tier="brand_hq", org_path="root"
        )

        with pytest.raises(ValueError, match="Profile not found"):
            await resolver.resolve("nonexistent", "query", org)

    def test_register_custom_profile(self) -> None:
        neo4j = FakeNeo4jAdapter()
        qdrant = FakeQdrantAdapter()
        resolver = DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]

        profile = ResolverProfile(
            profile_id="custom:test",
            fk_strategy="none",
            description="Test profile",
        )
        resolver.register_profile(profile)
        assert resolver.get_profile("custom:test") is not None
