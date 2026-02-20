"""Entity type registration mechanism.

Milestone: K3-6
Layer: Knowledge

Skills register new entity types at runtime without core code changes.
Core types are shipped with the system; skill-registered types are dynamic.

See: docs/architecture/02-Knowledge Section 4 (Entity types)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EntityTypeDefinition:
    """Schema definition for a knowledge entity type."""

    entity_type_id: str
    label: str  # Neo4j node label
    registered_by: str  # "core" | "skill:<skill_id>"
    status: str = "active"  # active | deprecated

    schema: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    vector_content_types: list[dict[str, Any]] = field(default_factory=list)
    visibility_rules: dict[str, Any] = field(default_factory=dict)
    org_scope: dict[str, Any] = field(default_factory=dict)


# Core entity types shipped with the system
CORE_TYPE_IDS: frozenset[str] = frozenset(
    {
        "Organization",
        "OrgMember",
        "RoleAdaptationRule",
        "BrandTone",
        "BrandKnowledge",
        "GlobalKnowledge",
        "StoreInsight",
        "EvolutionProposal",
    }
)

_CORE_TYPES: list[EntityTypeDefinition] = [
    EntityTypeDefinition(
        entity_type_id="Organization",
        label="Organization",
        registered_by="core",
        schema={"required_properties": ["name"], "type_constraints": {"name": "string"}},
    ),
    EntityTypeDefinition(
        entity_type_id="OrgMember",
        label="OrgMember",
        registered_by="core",
        schema={"required_properties": ["user_id", "role"]},
    ),
    EntityTypeDefinition(
        entity_type_id="RoleAdaptationRule",
        label="RoleAdaptationRule",
        registered_by="core",
        schema={"required_properties": ["role", "prompt_template"]},
        visibility_rules={"default_visibility": "global", "allowed_visibilities": ["global"]},
    ),
    EntityTypeDefinition(
        entity_type_id="BrandTone",
        label="BrandTone",
        registered_by="core",
        schema={"required_properties": ["tone_name", "description"]},
        visibility_rules={
            "default_visibility": "brand",
            "allowed_visibilities": ["global", "brand"],
        },
    ),
    EntityTypeDefinition(
        entity_type_id="BrandKnowledge",
        label="BrandKnowledge",
        registered_by="core",
        schema={"required_properties": ["content"]},
        vector_content_types=[
            {"content_type": "brand_knowledge", "embedding_field": "content", "is_primary": True}
        ],
        visibility_rules={
            "default_visibility": "brand",
            "allowed_visibilities": ["global", "brand", "region"],
        },
    ),
    EntityTypeDefinition(
        entity_type_id="GlobalKnowledge",
        label="GlobalKnowledge",
        registered_by="core",
        schema={"required_properties": ["content"]},
        vector_content_types=[
            {"content_type": "global_knowledge", "embedding_field": "content", "is_primary": True}
        ],
        visibility_rules={"default_visibility": "global", "allowed_visibilities": ["global"]},
    ),
    EntityTypeDefinition(
        entity_type_id="StoreInsight",
        label="StoreInsight",
        registered_by="core",
        schema={"required_properties": ["content"]},
        vector_content_types=[
            {"content_type": "store_insight", "embedding_field": "content", "is_primary": True}
        ],
        visibility_rules={
            "default_visibility": "store",
            "allowed_visibilities": ["store", "region"],
        },
    ),
    EntityTypeDefinition(
        entity_type_id="EvolutionProposal",
        label="EvolutionProposal",
        registered_by="core",
        schema={
            "required_properties": ["sanitized_content", "source_memory_id", "target_visibility"]
        },
    ),
]


class EntityTypeRegistry:
    """Registry for knowledge entity types.

    Core types are loaded at init. Skills can register additional
    types at runtime via register().
    """

    def __init__(self) -> None:
        self._types: dict[str, EntityTypeDefinition] = {}
        for t in _CORE_TYPES:
            self._types[t.entity_type_id] = t

    def get(self, entity_type_id: str) -> EntityTypeDefinition | None:
        """Look up an entity type by ID."""
        return self._types.get(entity_type_id)

    def list_all(self) -> list[EntityTypeDefinition]:
        """Return all registered entity types."""
        return list(self._types.values())

    def list_active(self) -> list[EntityTypeDefinition]:
        """Return only active entity types."""
        return [t for t in self._types.values() if t.status == "active"]

    def register(self, definition: EntityTypeDefinition) -> EntityTypeDefinition:
        """Register a new entity type (called by Skill lifecycle init).

        Args:
            definition: Entity type to register.

        Returns:
            The registered EntityTypeDefinition.

        Raises:
            ValueError: If collision with core type or invalid definition.
        """
        if not definition.entity_type_id or not definition.label:
            msg = "entity_type_id and label are required"
            raise ValueError(msg)

        if definition.entity_type_id in CORE_TYPE_IDS and definition.registered_by != "core":
            msg = f"Cannot override core type: {definition.entity_type_id}"
            raise ValueError(msg)

        existing = self._types.get(definition.entity_type_id)
        if existing is not None and existing.registered_by != definition.registered_by:
            msg = (
                f"Entity type '{definition.entity_type_id}' already registered "
                f"by {existing.registered_by}"
            )
            raise ValueError(msg)

        self._types[definition.entity_type_id] = definition
        logger.info(
            "Registered entity type: %s by %s",
            definition.entity_type_id,
            definition.registered_by,
        )
        return definition

    def deprecate(self, entity_type_id: str) -> EntityTypeDefinition | None:
        """Mark an entity type as deprecated.

        Data is retained but new writes are rejected.

        Args:
            entity_type_id: Type to deprecate.

        Returns:
            Updated definition, or None if not found.
        """
        existing = self._types.get(entity_type_id)
        if existing is None:
            return None

        if entity_type_id in CORE_TYPE_IDS:
            msg = f"Cannot deprecate core type: {entity_type_id}"
            raise ValueError(msg)

        deprecated = EntityTypeDefinition(
            entity_type_id=existing.entity_type_id,
            label=existing.label,
            registered_by=existing.registered_by,
            status="deprecated",
            schema=existing.schema,
            relationships=existing.relationships,
            vector_content_types=existing.vector_content_types,
            visibility_rules=existing.visibility_rules,
            org_scope=existing.org_scope,
        )
        self._types[entity_type_id] = deprecated
        logger.info("Deprecated entity type: %s", entity_type_id)
        return deprecated

    def is_writable(self, entity_type_id: str) -> bool:
        """Check if writes are allowed for this entity type."""
        t = self._types.get(entity_type_id)
        return t is not None and t.status == "active"
