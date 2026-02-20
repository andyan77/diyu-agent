"""Qdrant vector collection initialization and seed vector loading.

Milestone: K3-2
Layer: Knowledge

Initializes Qdrant collections with proper payload indexes and loads
seed vectors (>= 50 vectors) with FK references to Neo4j nodes.

See: docs/architecture/02-Knowledge Section 4 (Qdrant schema)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeedVector:
    """A seed vector point for Qdrant bootstrap."""

    point_id: UUID
    vector: list[float]
    payload: dict[str, Any]
    graph_node_id: UUID | None = None


@dataclass
class VectorSeedData:
    """Collection of seed vectors."""

    vectors: list[SeedVector] = field(default_factory=list)


def _make_deterministic_vector(seed: int, dim: int = 1536) -> list[float]:
    """Generate a deterministic pseudo-embedding for seed data.

    Not a real embedding — used only for bootstrap/testing.
    Real vectors come from embedding model calls.

    Args:
        seed: Seed value for deterministic generation.
        dim: Vector dimension.

    Returns:
        Normalized float vector.
    """
    import math

    raw = [(math.sin(seed * 0.1 + i * 0.01) + 1.0) / 2.0 for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in raw))
    if norm == 0:
        return [0.0] * dim
    return [x / norm for x in raw]


def generate_seed_vectors(
    graph_node_ids: list[tuple[UUID, str, str]],
    *,
    org_id: UUID | None = None,
) -> VectorSeedData:
    """Generate seed vectors for knowledge graph nodes.

    Each graph node with semantic content gets a corresponding vector.

    Args:
        graph_node_ids: List of (node_id, entity_type, text_content).
        org_id: Organization scope.

    Returns:
        VectorSeedData with >= len(graph_node_ids) vectors.
    """
    vectors: list[SeedVector] = []

    for idx, (node_id, entity_type, text) in enumerate(graph_node_ids):
        point_id = uuid4()
        embedding = _make_deterministic_vector(idx)

        payload: dict[str, Any] = {
            "entity_type": entity_type,
            "text": text,
            "source_type": "enterprise",
            "content_type": f"{entity_type.lower()}_description",
        }
        if org_id is not None:
            payload["org_id"] = str(org_id)

        vectors.append(
            SeedVector(
                point_id=point_id,
                vector=embedding,
                payload=payload,
                graph_node_id=node_id,
            )
        )

    return VectorSeedData(vectors=vectors)


async def seed_vectors(adapter: Any, seed_data: VectorSeedData) -> int:
    """Load seed vectors into Qdrant.

    Args:
        adapter: Connected Qdrant adapter.
        seed_data: Vectors to load.

    Returns:
        Number of vectors inserted.
    """
    count = 0
    for sv in seed_data.vectors:
        await adapter.upsert_point(
            point_id=sv.point_id,
            vector=sv.vector,
            payload=sv.payload,
            graph_node_id=sv.graph_node_id,
        )
        count += 1

    logger.info("Seeded %d vectors", count)
    return count
