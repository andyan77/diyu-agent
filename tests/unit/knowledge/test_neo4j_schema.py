"""K3-1: Neo4j schema + seed data tests.

Tests: schema constraints, seed data generation, graph seeding.
Uses Fake adapter pattern (no unittest.mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.graph.neo4j_adapter import GraphNode, GraphRelationship
from src.knowledge.graph.schema import (
    SCHEMA_CONSTRAINTS,
    generate_seed_data,
    seed_graph,
)

# -- Fake adapter --


@dataclass
class FakeNeo4jAdapter:
    """In-memory fake for schema/seed tests."""

    _nodes: dict[str, GraphNode] = field(default_factory=dict)
    _relationships: list[GraphRelationship] = field(default_factory=list)

    async def create_node(
        self,
        entity_type: str,
        node_id: UUID,
        properties: dict[str, Any],
        *,
        org_id: UUID | None = None,
    ) -> GraphNode:
        node = GraphNode(
            node_id=node_id,
            entity_type=entity_type,
            properties=properties,
            org_id=org_id,
        )
        self._nodes[str(node_id)] = node
        return node

    async def create_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphRelationship:
        rel = GraphRelationship(
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            properties=properties or {},
        )
        self._relationships.append(rel)
        return rel

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def relationship_count(self) -> int:
        return len(self._relationships)


# -- Tests --


class TestSchemaConstraints:
    def test_constraints_not_empty(self) -> None:
        assert len(SCHEMA_CONSTRAINTS) > 0

    def test_all_constraints_have_label(self) -> None:
        for c in SCHEMA_CONSTRAINTS:
            assert c.label, f"Constraint missing label: {c}"
            assert c.property_name, f"Constraint missing property_name: {c}"

    def test_uniqueness_constraints_on_node_id(self) -> None:
        uniqueness = [c for c in SCHEMA_CONSTRAINTS if c.constraint_type == "uniqueness"]
        assert len(uniqueness) >= 5
        for c in uniqueness:
            assert c.property_name == "node_id"


class TestSeedDataGeneration:
    def test_generates_at_least_50_nodes(self) -> None:
        seed = generate_seed_data()
        assert len(seed.nodes) >= 50

    def test_generates_relationships(self) -> None:
        seed = generate_seed_data()
        assert len(seed.relationships) > 0

    def test_respects_org_id(self) -> None:
        org_id = uuid4()
        seed = generate_seed_data(org_id=org_id)
        for node in seed.nodes:
            assert node.org_id == org_id

    def test_contains_required_entity_types(self) -> None:
        seed = generate_seed_data()
        types = {n.entity_type for n in seed.nodes}
        assert "Product" in types
        assert "Category" in types

    def test_products_have_sku(self) -> None:
        seed = generate_seed_data()
        products = [n for n in seed.nodes if n.entity_type == "Product"]
        assert len(products) >= 20
        for p in products:
            assert "sku" in p.properties

    def test_relationships_are_typed(self) -> None:
        seed = generate_seed_data()
        rel_types = {r.rel_type for r in seed.relationships}
        assert "BELONGS_TO" in rel_types


class TestSeedGraph:
    @pytest.mark.asyncio
    async def test_seed_creates_nodes(self) -> None:
        adapter = FakeNeo4jAdapter()
        seed = generate_seed_data()
        count = await seed_graph(adapter, seed)  # type: ignore[arg-type]
        assert count >= 50
        assert adapter.node_count >= 50

    @pytest.mark.asyncio
    async def test_seed_creates_relationships(self) -> None:
        adapter = FakeNeo4jAdapter()
        seed = generate_seed_data()
        await seed_graph(adapter, seed)  # type: ignore[arg-type]
        assert adapter.relationship_count > 0

    @pytest.mark.asyncio
    async def test_seed_returns_correct_count(self) -> None:
        adapter = FakeNeo4jAdapter()
        seed = generate_seed_data()
        count = await seed_graph(adapter, seed)  # type: ignore[arg-type]
        assert count == len(seed.nodes)
