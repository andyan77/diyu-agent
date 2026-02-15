"""Layer 1: Port Schema assertion tests.

Verifies Port interfaces maintain expected method signatures.
These tests catch accidental breaking changes to Port contracts.

See: docs/architecture/00-*.md Section 12.6 (Contract testing strategy)
"""

from __future__ import annotations

import inspect

import pytest

from src.ports.knowledge_port import KnowledgePort
from src.ports.llm_call_port import LLMCallPort
from src.ports.memory_core_port import MemoryCorePort
from src.ports.org_context import OrgContextPort
from src.ports.skill_registry import SkillRegistry
from src.ports.storage_port import StoragePort


@pytest.mark.unit
class TestMemoryCorePortContract:
    """MemoryCorePort must expose required methods."""

    def test_has_read_personal_memories(self) -> None:
        assert hasattr(MemoryCorePort, "read_personal_memories")
        sig = inspect.signature(MemoryCorePort.read_personal_memories)
        params = list(sig.parameters.keys())
        assert "user_id" in params
        assert "query" in params
        assert "top_k" in params

    def test_has_write_observation(self) -> None:
        assert hasattr(MemoryCorePort, "write_observation")
        sig = inspect.signature(MemoryCorePort.write_observation)
        params = list(sig.parameters.keys())
        assert "user_id" in params
        assert "observation" in params

    def test_has_get_session(self) -> None:
        assert hasattr(MemoryCorePort, "get_session")

    def test_has_archive_session(self) -> None:
        assert hasattr(MemoryCorePort, "archive_session")


@pytest.mark.unit
class TestKnowledgePortContract:
    """KnowledgePort must expose required methods."""

    def test_has_resolve(self) -> None:
        assert hasattr(KnowledgePort, "resolve")
        sig = inspect.signature(KnowledgePort.resolve)
        params = list(sig.parameters.keys())
        assert "profile_id" in params
        assert "query" in params
        assert "org_context" in params

    def test_has_capabilities(self) -> None:
        assert hasattr(KnowledgePort, "capabilities")


@pytest.mark.unit
class TestLLMCallPortContract:
    """LLMCallPort must expose required methods."""

    def test_has_call(self) -> None:
        assert hasattr(LLMCallPort, "call")
        sig = inspect.signature(LLMCallPort.call)
        params = list(sig.parameters.keys())
        assert "prompt" in params
        assert "model_id" in params
        assert "content_parts" in params
        assert "parameters" in params


@pytest.mark.unit
class TestSkillRegistryContract:
    """SkillRegistry must expose required methods."""

    def test_has_find_skill(self) -> None:
        assert hasattr(SkillRegistry, "find_skill")
        sig = inspect.signature(SkillRegistry.find_skill)
        params = list(sig.parameters.keys())
        assert "intent_type" in params
        assert "org_context" in params

    def test_has_can_handle(self) -> None:
        assert hasattr(SkillRegistry, "can_handle")

    def test_has_execute(self) -> None:
        assert hasattr(SkillRegistry, "execute")
        sig = inspect.signature(SkillRegistry.execute)
        params = list(sig.parameters.keys())
        assert "skill_id" in params
        assert "knowledge" in params


@pytest.mark.unit
class TestOrgContextPortContract:
    """OrgContextPort must expose required methods."""

    def test_has_get_org_context(self) -> None:
        assert hasattr(OrgContextPort, "get_org_context")
        sig = inspect.signature(OrgContextPort.get_org_context)
        params = list(sig.parameters.keys())
        assert "user_id" in params
        assert "org_id" in params
        assert "token" in params


@pytest.mark.unit
class TestStoragePortContract:
    """StoragePort must expose required methods."""

    def test_has_put(self) -> None:
        assert hasattr(StoragePort, "put")
        sig = inspect.signature(StoragePort.put)
        params = list(sig.parameters.keys())
        assert "key" in params
        assert "value" in params
        assert "ttl" in params

    def test_has_get(self) -> None:
        assert hasattr(StoragePort, "get")

    def test_has_delete(self) -> None:
        assert hasattr(StoragePort, "delete")

    def test_has_list_keys(self) -> None:
        assert hasattr(StoragePort, "list_keys")
