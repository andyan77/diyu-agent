"""WebSocket real-time conversation handler.

Task card: B2-8
- Interface with Gateway WS endpoint
- Enable streaming replies + session persistence
- First-byte latency < 500ms

Architecture: delivery/phase2-runtime-config.yaml (realtime section)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.ports.conversation_port import WebSocketSender, WSMessage, WSResponse

if TYPE_CHECKING:
    from src.brain.engine.conversation import ConversationEngine
    from src.shared.types import OrganizationContext

logger = logging.getLogger(__name__)


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
            return WSResponse(
                type="close",
                session_id=message.session_id,
            )

        # Load history from event store (PG-backed persistence)
        history = await self._engine.get_session_history(message.session_id)

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

        # Send response (event_store already persisted in process_message)
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
