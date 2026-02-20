"""K3-6: Entity type registration tests.

Tests: core types, skill registration, deprecation, collision prevention.
"""

from __future__ import annotations

import pytest

from src.knowledge.registry.entity_type import (
    CORE_TYPE_IDS,
    EntityTypeDefinition,
    EntityTypeRegistry,
)


class TestCoreTypes:
    def test_core_types_loaded_at_init(self) -> None:
        registry = EntityTypeRegistry()
        for core_id in CORE_TYPE_IDS:
            assert registry.get(core_id) is not None

    def test_core_types_are_active(self) -> None:
        registry = EntityTypeRegistry()
        for core_id in CORE_TYPE_IDS:
            t = registry.get(core_id)
            assert t is not None
            assert t.status == "active"

    def test_core_type_count(self) -> None:
        EntityTypeRegistry()
        assert len(CORE_TYPE_IDS) == 8


class TestSkillRegistration:
    def test_register_new_type(self) -> None:
        registry = EntityTypeRegistry()
        defn = EntityTypeDefinition(
            entity_type_id="Product",
            label="Product",
            registered_by="skill:merchandising",
            schema={"required_properties": ["name", "sku"]},
        )
        result = registry.register(defn)
        assert result.entity_type_id == "Product"
        assert registry.get("Product") is not None

    def test_cannot_override_core_type(self) -> None:
        registry = EntityTypeRegistry()
        defn = EntityTypeDefinition(
            entity_type_id="Organization",
            label="Organization",
            registered_by="skill:rogue",
        )
        with pytest.raises(ValueError, match="Cannot override core type"):
            registry.register(defn)

    def test_collision_between_skills(self) -> None:
        registry = EntityTypeRegistry()
        defn1 = EntityTypeDefinition(
            entity_type_id="Persona",
            label="Persona",
            registered_by="skill:content_writer",
        )
        defn2 = EntityTypeDefinition(
            entity_type_id="Persona",
            label="Persona",
            registered_by="skill:other",
        )
        registry.register(defn1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(defn2)

    def test_same_skill_can_re_register(self) -> None:
        registry = EntityTypeRegistry()
        defn = EntityTypeDefinition(
            entity_type_id="Persona",
            label="Persona",
            registered_by="skill:content_writer",
        )
        registry.register(defn)
        registry.register(defn)  # Should not raise
        assert registry.get("Persona") is not None

    def test_register_requires_id_and_label(self) -> None:
        registry = EntityTypeRegistry()
        with pytest.raises(ValueError, match="required"):
            registry.register(
                EntityTypeDefinition(entity_type_id="", label="", registered_by="skill:x")
            )


class TestDeprecation:
    def test_deprecate_skill_type(self) -> None:
        registry = EntityTypeRegistry()
        registry.register(
            EntityTypeDefinition(
                entity_type_id="Persona",
                label="Persona",
                registered_by="skill:content_writer",
            )
        )
        result = registry.deprecate("Persona")
        assert result is not None
        assert result.status == "deprecated"
        assert not registry.is_writable("Persona")

    def test_cannot_deprecate_core_type(self) -> None:
        registry = EntityTypeRegistry()
        with pytest.raises(ValueError, match="Cannot deprecate core"):
            registry.deprecate("Organization")

    def test_deprecate_nonexistent_returns_none(self) -> None:
        registry = EntityTypeRegistry()
        assert registry.deprecate("NonExistent") is None


class TestIsWritable:
    def test_active_type_is_writable(self) -> None:
        registry = EntityTypeRegistry()
        assert registry.is_writable("BrandKnowledge")

    def test_deprecated_type_not_writable(self) -> None:
        registry = EntityTypeRegistry()
        registry.register(
            EntityTypeDefinition(
                entity_type_id="Old",
                label="Old",
                registered_by="skill:x",
                status="deprecated",
            )
        )
        assert not registry.is_writable("Old")

    def test_unknown_type_not_writable(self) -> None:
        registry = EntityTypeRegistry()
        assert not registry.is_writable("DoesNotExist")


class TestListOperations:
    def test_list_all_includes_core(self) -> None:
        registry = EntityTypeRegistry()
        all_types = registry.list_all()
        ids = {t.entity_type_id for t in all_types}
        assert "Organization" in ids

    def test_list_active_excludes_deprecated(self) -> None:
        registry = EntityTypeRegistry()
        registry.register(
            EntityTypeDefinition(
                entity_type_id="Old",
                label="Old",
                registered_by="skill:x",
                status="deprecated",
            )
        )
        active = registry.list_active()
        ids = {t.entity_type_id for t in active}
        assert "Old" not in ids
