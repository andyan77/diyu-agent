"""Port interfaces - Layer boundary contracts.

Day-1 Ports (6):
    MemoryCorePort  - Memory Core read/write (Brain hard dep)
    KnowledgePort   - Knowledge Stores read (soft dep, degradable)
    LLMCallPort     - LLM invocations
    SkillRegistry   - Skill discovery and dispatch
    OrgContext      - Organization context assembly
    StoragePort     - Generic persistence

Extension Ports:
    ConversationPort - Gateway-facing conversation interface
    WSChatPort       - Gateway-facing WebSocket handler interface
    ObjectStoragePort - Object storage (v3.6, not Day-1)

See: docs/architecture/00-*.md Section 12.3
"""

from src.ports.conversation_port import (
    ConversationPort,
    WebSocketSender,
    WSChatPort,
    WSMessage,
    WSResponse,
)
from src.ports.knowledge_port import KnowledgePort
from src.ports.llm_call_port import LLMCallPort
from src.ports.memory_core_port import MemoryCorePort
from src.ports.object_storage_port import ObjectStoragePort
from src.ports.org_context import OrgContextPort
from src.ports.skill_registry import SkillRegistry
from src.ports.storage_port import StoragePort

__all__ = [
    "ConversationPort",
    "KnowledgePort",
    "LLMCallPort",
    "MemoryCorePort",
    "ObjectStoragePort",
    "OrgContextPort",
    "SkillRegistry",
    "StoragePort",
    "WSChatPort",
    "WSMessage",
    "WSResponse",
    "WebSocketSender",
]
