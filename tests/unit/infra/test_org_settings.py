"""Tests for I1-2: org_settings inheritance with is_locked BRIDGE mechanism.

Acceptance: pytest tests/unit/infra/test_org_settings.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.infra.org.settings import (
    OrgSettingsNode,
    SettingEntry,
    merge_settings,
    resolve_settings,
)


@pytest.fixture()
def root_org_id():
    return uuid4()


@pytest.fixture()
def child_org_id():
    return uuid4()


@pytest.fixture()
def grandchild_org_id():
    return uuid4()


class TestResolveSettings:
    """resolve_settings walks the org hierarchy correctly."""

    def test_empty_chain_returns_empty(self):
        assert resolve_settings([]) == {}

    def test_single_node_returns_its_settings(self, root_org_id):
        node = OrgSettingsNode(
            org_id=root_org_id,
            settings={"max_tokens": 1000, "theme": "dark"},
        )
        result = resolve_settings([node])
        assert result["max_tokens"].value == 1000
        assert result["theme"].value == "dark"
        assert result["max_tokens"].source_org_id == root_org_id

    def test_child_overrides_parent(self, root_org_id, child_org_id):
        parent = OrgSettingsNode(
            org_id=root_org_id,
            settings={"max_tokens": 1000, "theme": "dark"},
        )
        child = OrgSettingsNode(
            org_id=child_org_id,
            settings={"max_tokens": 500},
        )
        result = resolve_settings([parent, child])
        assert result["max_tokens"].value == 500
        assert result["max_tokens"].source_org_id == child_org_id
        # theme inherited from parent
        assert result["theme"].value == "dark"
        assert result["theme"].source_org_id == root_org_id

    def test_locked_key_cannot_be_overridden(self, root_org_id, child_org_id):
        parent = OrgSettingsNode(
            org_id=root_org_id,
            settings={"max_tokens": 1000},
            locked_keys=frozenset({"max_tokens"}),
        )
        child = OrgSettingsNode(
            org_id=child_org_id,
            settings={"max_tokens": 9999},  # should be ignored
        )
        result = resolve_settings([parent, child])
        assert result["max_tokens"].value == 1000  # parent value preserved
        assert result["max_tokens"].is_locked is True
        assert result["max_tokens"].source_org_id == root_org_id

    def test_locked_propagates_through_hierarchy(
        self, root_org_id, child_org_id, grandchild_org_id
    ):
        root = OrgSettingsNode(
            org_id=root_org_id,
            settings={"security_mode": "strict"},
            locked_keys=frozenset({"security_mode"}),
        )
        child = OrgSettingsNode(
            org_id=child_org_id,
            settings={"security_mode": "relaxed"},  # ignored
        )
        grandchild = OrgSettingsNode(
            org_id=grandchild_org_id,
            settings={"security_mode": "off"},  # also ignored
        )
        result = resolve_settings([root, child, grandchild])
        assert result["security_mode"].value == "strict"
        assert result["security_mode"].source_org_id == root_org_id

    def test_child_can_lock_its_own_key(self, root_org_id, child_org_id, grandchild_org_id):
        root = OrgSettingsNode(
            org_id=root_org_id,
            settings={"theme": "light"},
        )
        child = OrgSettingsNode(
            org_id=child_org_id,
            settings={"theme": "dark"},
            locked_keys=frozenset({"theme"}),
        )
        grandchild = OrgSettingsNode(
            org_id=grandchild_org_id,
            settings={"theme": "blue"},  # ignored because child locked it
        )
        result = resolve_settings([root, child, grandchild])
        assert result["theme"].value == "dark"
        assert result["theme"].source_org_id == child_org_id
        assert result["theme"].is_locked is True

    def test_unlocked_keys_can_be_freely_overridden(
        self, root_org_id, child_org_id, grandchild_org_id
    ):
        chain = [
            OrgSettingsNode(org_id=root_org_id, settings={"lang": "en"}),
            OrgSettingsNode(org_id=child_org_id, settings={"lang": "zh"}),
            OrgSettingsNode(org_id=grandchild_org_id, settings={"lang": "ja"}),
        ]
        result = resolve_settings(chain)
        assert result["lang"].value == "ja"
        assert result["lang"].source_org_id == grandchild_org_id

    def test_multiple_locked_keys(self, root_org_id, child_org_id):
        parent = OrgSettingsNode(
            org_id=root_org_id,
            settings={"a": 1, "b": 2, "c": 3},
            locked_keys=frozenset({"a", "b"}),
        )
        child = OrgSettingsNode(
            org_id=child_org_id,
            settings={"a": 10, "b": 20, "c": 30},
        )
        result = resolve_settings([parent, child])
        assert result["a"].value == 1  # locked
        assert result["b"].value == 2  # locked
        assert result["c"].value == 30  # overridden


class TestMergeSettings:
    """merge_settings is a two-level convenience wrapper."""

    def test_merge_respects_parent_lock(self, root_org_id, child_org_id):
        parent_resolved = {
            "max_tokens": SettingEntry(
                key="max_tokens",
                value=1000,
                is_locked=True,
                source_org_id=root_org_id,
            ),
        }
        child_node = OrgSettingsNode(
            org_id=child_org_id,
            settings={"max_tokens": 9999, "theme": "dark"},
        )
        result = merge_settings(parent_resolved, child_node)
        assert result["max_tokens"].value == 1000  # locked, not overridden
        assert result["theme"].value == "dark"  # new key from child

    def test_merge_child_adds_new_keys(self, root_org_id, child_org_id):
        parent_resolved: dict[str, SettingEntry] = {}
        child_node = OrgSettingsNode(
            org_id=child_org_id,
            settings={"new_feature": True},
        )
        result = merge_settings(parent_resolved, child_node)
        assert result["new_feature"].value is True
        assert result["new_feature"].source_org_id == child_org_id


class TestSettingEntry:
    """SettingEntry is frozen/immutable."""

    def test_frozen(self, root_org_id):
        entry = SettingEntry(key="k", value="v", source_org_id=root_org_id)
        with pytest.raises(AttributeError):
            entry.value = "new"  # type: ignore[misc]
