"""ConversationPort - Gateway-facing conversation interface.

Defines Protocol types for the conversation engine and WebSocket handler.
Gateway depends on these protocols, not Brain concrete classes.

Data classes (WSMessage, WSResponse) are defined here so both Gateway and
Brain can import them without cross-layer violations.

See: docs/architecture/00-*.md Section 12.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from src.shared.types import OrganizationContext


class ConversationPort(Protocol):
    """Port: Conversation processing interface (structural typing).

    Brain's ConversationEngine satisfies this protocol automatically.
    """

    async def process_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
        message: str,
        org_context: OrganizationContext | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        model_id: str | None = None,
    ) -> Any:
        """Process a user message and return a conversation turn."""
        ...


class WebSocketSender(Protocol):
    """Protocol for sending messages over WebSocket."""

    async def send(self, data: dict[str, Any]) -> None:
        """Send a message to the connected client."""
        ...


@dataclass(frozen=True)
class WSMessage:
    """A WebSocket message from client."""

    type: str  # "message" | "ping" | "close"
    session_id: UUID
    user_id: UUID
    org_id: UUID
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WSResponse:
    """A WebSocket response to client."""

    type: str  # "message" | "pong" | "error" | "stream_start" | "stream_end"
    session_id: UUID
    content: str = ""
    turn_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class WSChatPort(Protocol):
    """Port: WebSocket chat handler interface (structural typing).

    Brain's WSChatHandler satisfies this protocol automatically.
    """

    async def handle_message(
        self,
        message: WSMessage,
        sender: WebSocketSender,
        org_context: OrganizationContext | None = None,
    ) -> WSResponse:
        """Handle an incoming WebSocket message."""
        ...
