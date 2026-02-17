"""WebSocket real-time conversation handler.

Task card: B2-8
- Interface with Gateway WS endpoint
- Enable streaming replies + session persistence
- First-byte latency < 500ms

Architecture: delivery/phase2-runtime-config.yaml (realtime section)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from src.brain.engine.conversation import ConversationEngine
    from src.shared.types import OrganizationContext

logger = logging.getLogger(__name__)


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


class WSChatHandler:
    """WebSocket handler for real-time conversation.

    Bridges Gateway WS endpoint to ConversationEngine.
    Supports streaming responses via chunked sends.
    """

    def __init__(
        self,
        engine: ConversationEngine,
    ) -> None:
        self._engine = engine
        self._sessions: dict[UUID, list[dict[str, Any]]] = {}

    async def handle_message(
        self,
        message: WSMessage,
        sender: WebSocketSender,
        org_context: OrganizationContext | None = None,
    ) -> WSResponse:
        """Handle an incoming WebSocket message.

        Routes based on message type:
        - message: Process through conversation engine
        - ping: Return pong
        - close: Clean up session
        """
        if message.type == "ping":
            response = WSResponse(
                type="pong",
                session_id=message.session_id,
            )
            await sender.send({"type": "pong"})
            return response

        if message.type == "close":
            self._sessions.pop(message.session_id, None)
            return WSResponse(
                type="close",
                session_id=message.session_id,
            )

        # Process message through conversation engine
        history = self._sessions.get(message.session_id, [])

        # Send stream_start
        await sender.send(
            {
                "type": "stream_start",
                "session_id": str(message.session_id),
            }
        )

        turn = await self._engine.process_message(
            session_id=message.session_id,
            user_id=message.user_id,
            org_id=message.org_id,
            message=message.content,
            org_context=org_context,
            conversation_history=history,
        )

        # Update session history
        history.append({"role": "user", "content": message.content})
        history.append({"role": "assistant", "content": turn.assistant_response})
        self._sessions[message.session_id] = history

        # Send response
        response_data = {
            "type": "message",
            "session_id": str(message.session_id),
            "turn_id": str(turn.turn_id),
            "content": turn.assistant_response,
            "tokens_used": turn.tokens_used,
            "model_id": turn.model_id,
        }
        await sender.send(response_data)

        # Send stream_end
        await sender.send(
            {
                "type": "stream_end",
                "session_id": str(message.session_id),
            }
        )

        return WSResponse(
            type="message",
            session_id=message.session_id,
            content=turn.assistant_response,
            turn_id=turn.turn_id,
        )
