"""K3-5: Resolver audit and profile management tests.

Tests: profile registration, resolution metadata, audit trail, error handling.
Gate criterion: p3-resolver-audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from src.knowledge.resolver.resolver import (
    BUILTIN_PROFILES,
    DiyuResolver,
    ResolverProfile,
)
from src.shared.types import OrganizationContext

# -- Fake adapters --


@dataclass
class FakeGraphSession:
    """Fake session that returns pre-configured nodes."""

    _results: list[dict[str, Any]] = field(default_factory=list)
    _index: int = 0

    async def run(self, query: str, **params: Any) -> FakeGraphSession:
        self._index = 0
        return self

    def __aiter__(self) -> FakeGraphSession:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._index >= len(self._results):
            raise StopAsyncIteration
        item = self._results[self._index]
        self._index += 1
        return item

    async def __aenter__(self) -> FakeGraphSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class FakeNeo4jDriver:
    """Fake driver that produces fake sessions."""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self._results = results or []

    def session(self) -> FakeGraphSession:
        return FakeGraphSession(_results=self._results)


@dataclass
class FakeNeo4j:
    """Fake Neo4j adapter with controllable results."""

    driver: Any = None

    def __post_init__(self) -> None:
        if self.driver is None:
            self.driver = FakeNeo4jDriver()


@dataclass
class FakeQdrant:
    """Fake Qdrant adapter (unused for graph-only tests)."""

    pass


def _make_org_context() -> OrganizationContext:
    org_id = uuid4()
    return OrganizationContext(
        user_id=uuid4(),
        org_id=org_id,
        org_tier="brand_hq",
        org_path=f"root.{org_id}",
        org_chain=[org_id],
    )


def _make_resolver(
    results: list[dict[str, Any]] | None = None,
) -> DiyuResolver:
    neo4j = FakeNeo4j(driver=FakeNeo4jDriver(results=results or []))
    qdrant = FakeQdrant()
    return DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]


class TestBuiltinProfiles:
    def test_has_minimum_profiles(self) -> None:
        assert len(BUILTIN_PROFILES) >= 2

    def test_role_adaptation_profile(self) -> None:
        profile = BUILTIN_PROFILES.get("core:role_adaptation")
        assert profile is not None
        assert profile.fk_strategy == "none"
        assert profile.graph_query_template is not None

    def test_brand_context_profile(self) -> None:
        profile = BUILTIN_PROFILES.get("core:brand_context")
        assert profile is not None
        assert profile.fk_strategy == "graph_first"
        assert profile.vector_search is True


class TestProfileRegistration:
    def test_register_custom_profile(self) -> None:
        resolver = _make_resolver()
        custom = ResolverProfile(
            profile_id="custom:product_lookup",
            fk_strategy="none",
            graph_query_template="MATCH (n:Product) RETURN n, labels(n) as labels LIMIT $limit",
            description="Custom product lookup",
        )
        resolver.register_profile(custom)
        assert resolver.get_profile("custom:product_lookup") is not None

    def test_builtin_profiles_available(self) -> None:
        resolver = _make_resolver()
        assert resolver.get_profile("core:role_adaptation") is not None
        assert resolver.get_profile("core:brand_context") is not None

    def test_unknown_profile_returns_none(self) -> None:
        resolver = _make_resolver()
        assert resolver.get_profile("nonexistent:profile") is None


class TestResolutionMetadata:
    @pytest.mark.asyncio
    async def test_graph_only_metadata(self) -> None:
        node_id = uuid4()
        results = [
            {
                "n": {
                    "node_id": str(node_id),
                    "org_id": str(uuid4()),
                    "role": "advisor",
                    "prompt_template": "You are...",
                },
                "labels": ["RoleAdaptationRule"],
            }
        ]
        resolver = _make_resolver(results=results)
        org = _make_org_context()

        bundle = await resolver.resolve("core:role_adaptation", "role rules", org)
        assert bundle.metadata is not None
        assert bundle.metadata.profile_id == "core:role_adaptation"
        assert bundle.metadata.graph_hits == 1
        assert bundle.metadata.vector_hits == 0
        assert bundle.metadata.fk_enrichments == 0
        assert bundle.metadata.completeness_score == 1.0

    @pytest.mark.asyncio
    async def test_empty_result_metadata(self) -> None:
        resolver = _make_resolver(results=[])
        org = _make_org_context()

        bundle = await resolver.resolve("core:role_adaptation", "nothing", org)
        assert bundle.metadata is not None
        assert bundle.metadata.graph_hits == 0
        assert bundle.metadata.completeness_score == 0.0


class TestResolutionErrors:
    @pytest.mark.asyncio
    async def test_unknown_profile_raises(self) -> None:
        resolver = _make_resolver()
        org = _make_org_context()
        with pytest.raises(ValueError, match="Profile not found"):
            await resolver.resolve("nonexistent:profile", "test", org)

    @pytest.mark.asyncio
    async def test_unknown_strategy_raises(self) -> None:
        resolver = _make_resolver()
        bad_profile = ResolverProfile(
            profile_id="bad:strategy",
            fk_strategy="invalid_strategy",
        )
        resolver.register_profile(bad_profile)
        org = _make_org_context()
        with pytest.raises(ValueError, match="Unknown FK strategy"):
            await resolver.resolve("bad:strategy", "test", org)


class TestGraphResolution:
    @pytest.mark.asyncio
    async def test_entities_grouped_by_type(self) -> None:
        node1 = uuid4()
        node2 = uuid4()
        results = [
            {
                "n": {
                    "node_id": str(node1),
                    "org_id": str(uuid4()),
                    "role": "advisor",
                    "prompt_template": "You are an advisor",
                },
                "labels": ["RoleAdaptationRule"],
            },
            {
                "n": {
                    "node_id": str(node2),
                    "org_id": str(uuid4()),
                    "role": "sales",
                    "prompt_template": "You are a sales rep",
                },
                "labels": ["RoleAdaptationRule"],
            },
        ]
        resolver = _make_resolver(results=results)
        org = _make_org_context()

        bundle = await resolver.resolve("core:role_adaptation", "roles", org)
        assert "RoleAdaptationRule" in bundle.entities
        assert len(bundle.entities["RoleAdaptationRule"]) == 2

    @pytest.mark.asyncio
    async def test_org_context_in_bundle(self) -> None:
        resolver = _make_resolver(results=[])
        org = _make_org_context()

        bundle = await resolver.resolve("core:role_adaptation", "test", org)
        assert bundle.org_context is not None
        assert bundle.org_context["org_id"] == str(org.org_id)
        assert bundle.org_context["org_tier"] == "brand_hq"
