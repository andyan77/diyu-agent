"""Organization settings inheritance with is_locked BRIDGE mechanism.

Task card: I1-2
- Parent locked settings cannot be overridden by children
- is_locked=True on parent acts as RULE for current org, LAW for children
- Settings resolve by walking the org tree upward

Architecture: 06 Section 1.5-1.6 (BRIDGE mechanism)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID  # noqa: TC003 -- used at runtime in dataclass fields


@dataclass(frozen=True)
class SettingEntry:
    """A single setting key-value with lock status."""

    key: str
    value: Any
    is_locked: bool = False
    source_org_id: UUID | None = None


@dataclass(frozen=True)
class OrgSettingsNode:
    """Represents one organization's settings in the hierarchy."""

    org_id: UUID
    settings: dict[str, Any] = field(default_factory=dict)
    locked_keys: frozenset[str] = field(default_factory=frozenset)


def resolve_settings(
    chain: list[OrgSettingsNode],
) -> dict[str, SettingEntry]:
    """Resolve effective settings by walking the org hierarchy.

    Args:
        chain: List of OrgSettingsNode from root (index 0) to leaf (last).
              The last element is the target organization.

    Returns:
        Dict of key -> SettingEntry with the effective value and lock status.

    Rules:
        1. Walk from root to leaf.
        2. Each node's settings are applied on top of the accumulated result.
        3. If a key was locked by an ancestor, the child's value is ignored.
        4. The source_org_id records which org provided the effective value.
    """
    if not chain:
        return {}

    effective: dict[str, SettingEntry] = {}
    locked_keys: set[str] = set()

    for node in chain:
        # Apply this node's settings
        for key, value in node.settings.items():
            if key in locked_keys:
                # Ancestor locked this key; child value is silently ignored
                continue

            is_locked = key in node.locked_keys
            effective[key] = SettingEntry(
                key=key,
                value=value,
                is_locked=is_locked,
                source_org_id=node.org_id,
            )

            if is_locked:
                locked_keys.add(key)

    return effective


def merge_settings(
    parent_settings: dict[str, SettingEntry],
    child_node: OrgSettingsNode,
) -> dict[str, SettingEntry]:
    """Merge a child's settings into resolved parent settings.

    This is a convenience wrapper around resolve_settings for
    two-level merge scenarios.

    Args:
        parent_settings: Already-resolved parent settings.
        child_node: The child organization's settings node.

    Returns:
        Merged settings dict.
    """
    result = dict(parent_settings)

    for key, value in child_node.settings.items():
        existing = result.get(key)
        if existing and existing.is_locked:
            # Parent locked this key; child cannot override
            continue

        is_locked = key in child_node.locked_keys
        result[key] = SettingEntry(
            key=key,
            value=value,
            is_locked=is_locked,
            source_org_id=child_node.org_id,
        )

    return result
