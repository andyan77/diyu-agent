"""Neo4j knowledge graph schema and seed data management.

Milestone: K3-1
Layer: Knowledge

Defines the graph schema (constraints, indexes) and provides seed data
loading for knowledge graph bootstrap (>= 50 nodes).

See: docs/architecture/02-Knowledge Section 4 (Neo4j schema)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds"


@dataclass
class SchemaConstraint:
    """A Neo4j schema constraint or index."""

    label: str
    property_name: str
    constraint_type: str = "uniqueness"  # uniqueness | index


# Required schema constraints for Knowledge Graph
SCHEMA_CONSTRAINTS: list[SchemaConstraint] = [
    SchemaConstraint(label="Product", property_name="node_id"),
    SchemaConstraint(label="Category", property_name="node_id"),
    SchemaConstraint(label="StylingRule", property_name="node_id"),
    SchemaConstraint(label="BrandKnowledge", property_name="node_id"),
    SchemaConstraint(label="GlobalKnowledge", property_name="node_id"),
    SchemaConstraint(label="Organization", property_name="node_id"),
    SchemaConstraint(label="StoreInsight", property_name="node_id"),
    SchemaConstraint(label="EvolutionProposal", property_name="node_id"),
    SchemaConstraint(label="RoleAdaptationRule", property_name="node_id"),
    SchemaConstraint(label="BrandTone", property_name="node_id"),
    # Indexes for org scoping
    SchemaConstraint(label="Product", property_name="org_id", constraint_type="index"),
    SchemaConstraint(label="Category", property_name="org_id", constraint_type="index"),
    SchemaConstraint(label="BrandKnowledge", property_name="org_id", constraint_type="index"),
]


@dataclass
class SeedNode:
    """A seed data node for graph bootstrap."""

    entity_type: str
    node_id: UUID
    properties: dict[str, Any]
    org_id: UUID | None = None


@dataclass
class SeedRelationship:
    """A seed data relationship."""

    source_id: UUID
    target_id: UUID
    rel_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class SeedData:
    """Complete seed data set for knowledge graph bootstrap."""

    nodes: list[SeedNode] = field(default_factory=list)
    relationships: list[SeedRelationship] = field(default_factory=list)


async def apply_schema(adapter: Any) -> int:
    """Apply schema constraints and indexes to Neo4j.

    Args:
        adapter: Connected Neo4j adapter.

    Returns:
        Number of constraints/indexes created.
    """
    count = 0
    for constraint in SCHEMA_CONSTRAINTS:
        try:
            if constraint.constraint_type == "uniqueness":
                query = (
                    f"CREATE CONSTRAINT IF NOT EXISTS "
                    f"FOR (n:{constraint.label}) "
                    f"REQUIRE n.{constraint.property_name} IS UNIQUE"
                )
            else:
                query = (
                    f"CREATE INDEX IF NOT EXISTS "
                    f"FOR (n:{constraint.label}) "
                    f"ON (n.{constraint.property_name})"
                )
            async with adapter.driver.session() as session:
                await session.run(query)
            count += 1
        except Exception:
            logger.exception(
                "Failed to create constraint: %s.%s",
                constraint.label,
                constraint.property_name,
            )
    logger.info("Applied %d schema constraints/indexes", count)
    return count


def generate_seed_data(org_id: UUID | None = None) -> SeedData:
    """Generate in-memory seed data (>= 50 nodes).

    If data/seeds/ JSON files exist, loads from disk.
    Otherwise generates deterministic demo data.

    Args:
        org_id: Organization to scope seed data to.

    Returns:
        SeedData with nodes and relationships.
    """
    products_file = DATA_DIR / "products.json"
    if products_file.exists():
        return _load_seed_from_disk(org_id)
    return _generate_demo_seed(org_id)


def _load_seed_from_disk(org_id: UUID | None) -> SeedData:
    """Load seed data from JSON files."""
    nodes: list[SeedNode] = []
    relationships: list[SeedRelationship] = []

    for filename, entity_type in [
        ("products.json", "Product"),
        ("categories.json", "Category"),
        ("styling_rules.json", "StylingRule"),
    ]:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            continue
        with filepath.open() as f:
            items = json.load(f)
        for item in items:
            nid = UUID(item["node_id"]) if "node_id" in item else uuid4()
            props = {k: v for k, v in item.items() if k not in ("node_id", "org_id")}
            nodes.append(
                SeedNode(entity_type=entity_type, node_id=nid, properties=props, org_id=org_id)
            )

    rels_file = DATA_DIR / "relationships.json"
    if rels_file.exists():
        with rels_file.open() as f:
            rels = json.load(f)
        for rel in rels:
            relationships.append(
                SeedRelationship(
                    source_id=UUID(rel["source_id"]),
                    target_id=UUID(rel["target_id"]),
                    rel_type=rel["rel_type"],
                    properties=rel.get("properties", {}),
                )
            )

    return SeedData(nodes=nodes, relationships=relationships)


def _generate_demo_seed(org_id: UUID | None) -> SeedData:
    """Generate deterministic demo seed data (>= 50 nodes)."""
    nodes: list[SeedNode] = []
    relationships: list[SeedRelationship] = []

    # 5 categories
    cat_ids: list[UUID] = []
    categories = [
        "Tops",
        "Bottoms",
        "Dresses",
        "Accessories",
        "Footwear",
    ]
    for name in categories:
        nid = uuid4()
        cat_ids.append(nid)
        nodes.append(
            SeedNode(
                entity_type="Category",
                node_id=nid,
                properties={"name": name, "description": f"{name} category"},
                org_id=org_id,
            )
        )

    # 25 products (5 per category)
    product_ids: list[UUID] = []
    for cat_idx, cat_name in enumerate(categories):
        for i in range(5):
            pid = uuid4()
            product_ids.append(pid)
            nodes.append(
                SeedNode(
                    entity_type="Product",
                    node_id=pid,
                    properties={
                        "name": f"{cat_name} Item {i + 1}",
                        "description": f"A {cat_name.lower()} product, style variant {i + 1}",
                        "sku": f"SKU-{cat_name[:3].upper()}-{i + 1:03d}",
                        "price": round(29.99 + i * 10, 2),
                    },
                    org_id=org_id,
                )
            )
            # BELONGS_TO category
            relationships.append(
                SeedRelationship(
                    source_id=pid,
                    target_id=cat_ids[cat_idx],
                    rel_type="BELONGS_TO",
                )
            )

    # 10 styling rules
    for i in range(10):
        sid = uuid4()
        nodes.append(
            SeedNode(
                entity_type="StylingRule",
                node_id=sid,
                properties={
                    "name": f"Style Rule {i + 1}",
                    "description": f"Combine items for look #{i + 1}",
                    "rule_type": "outfit_combination",
                },
                org_id=org_id,
            )
        )
        # Link to 2 random products
        if len(product_ids) >= 2:
            idx_a = i % len(product_ids)
            idx_b = (i + 5) % len(product_ids)
            relationships.append(
                SeedRelationship(
                    source_id=sid,
                    target_id=product_ids[idx_a],
                    rel_type="RECOMMENDS",
                )
            )
            relationships.append(
                SeedRelationship(
                    source_id=sid,
                    target_id=product_ids[idx_b],
                    rel_type="RECOMMENDS",
                )
            )

    # 5 brand knowledge entries
    for i in range(5):
        nodes.append(
            SeedNode(
                entity_type="BrandKnowledge",
                node_id=uuid4(),
                properties={
                    "content": f"Brand guideline #{i + 1}: maintain consistent tone and style",
                    "knowledge_type": "guideline",
                },
                org_id=org_id,
            )
        )

    # 5 global knowledge entries
    for i in range(5):
        nodes.append(
            SeedNode(
                entity_type="GlobalKnowledge",
                node_id=uuid4(),
                properties={
                    "content": f"Fashion trend #{i + 1}: seasonal color palette guidance",
                    "knowledge_type": "trend",
                },
                org_id=org_id,
            )
        )

    # 5 role adaptation rules
    roles = ["brand_hq", "regional_agent", "franchise_store", "brand_dept", "platform"]
    for role in roles:
        nodes.append(
            SeedNode(
                entity_type="RoleAdaptationRule",
                node_id=uuid4(),
                properties={
                    "role": role,
                    "prompt_template": f"You are assisting a {role} user. Adjust tone accordingly.",
                },
                org_id=org_id,
            )
        )

    # Total: 5 + 25 + 10 + 5 + 5 + 5 = 55 nodes
    return SeedData(nodes=nodes, relationships=relationships)


async def seed_graph(adapter: Any, seed_data: SeedData) -> int:
    """Load seed data into Neo4j.

    Args:
        adapter: Connected Neo4j adapter.
        seed_data: Nodes and relationships to load.

    Returns:
        Number of nodes created.
    """
    count = 0
    for node in seed_data.nodes:
        await adapter.create_node(
            entity_type=node.entity_type,
            node_id=node.node_id,
            properties=node.properties,
            org_id=node.org_id,
        )
        count += 1

    for rel in seed_data.relationships:
        await adapter.create_relationship(
            source_id=rel.source_id,
            target_id=rel.target_id,
            rel_type=rel.rel_type,
            properties=rel.properties,
        )

    logger.info("Seeded %d nodes, %d relationships", count, len(seed_data.relationships))
    return count
