"""WebSocket streaming endpoint for real-time conversation.

Task card: G2-2
- WS /ws/conversations/{id} -> streaming ai_response_chunk
- First-byte latency < 500ms
- JWT auth on WS handshake

Architecture: 05-Gateway Section 7
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID  # noqa: TC003 - required at runtime for FastAPI path param

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.gateway.middleware.auth import decode_token
from src.ports.conversation_port import WSMessage
from src.shared.errors import AuthenticationError
from src.shared.types import OrganizationContext

if TYPE_CHECKING:
    from src.ports.conversation_port import WSChatPort

logger = logging.getLogger(__name__)


class _FastAPIWebSocketSender:
    """Adapter from FastAPI WebSocket to Brain's WebSocketSender protocol."""

    def __init__(self, ws: WebSocket) -> None:
        self._ws = ws

    async def send(self, data: dict[str, Any]) -> None:
        await self._ws.send_json(data)


def create_ws_router(*, handler: WSChatPort, jwt_secret: str) -> APIRouter:
    """Create WebSocket router with injected dependencies."""
    router = APIRouter(tags=["websocket"])

    @router.websocket("/ws/conversations/{session_id}")
    async def websocket_conversation(
        websocket: WebSocket,
        session_id: UUID,
    ) -> None:
        """WebSocket endpoint for real-time conversation streaming."""
        # Authenticate via query param or first message
        token = websocket.query_params.get("token")
        if not token:
            # Try Sec-WebSocket-Protocol header
            protocols = websocket.headers.get("sec-websocket-protocol", "")
            for proto in protocols.split(","):
                proto = proto.strip()
                if proto.startswith("auth."):
                    token = proto[5:]
                    break

        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            return

        try:
            payload = decode_token(token, secret=jwt_secret)
        except AuthenticationError:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return

        await websocket.accept()
        sender = _FastAPIWebSocketSender(websocket)

        # Build org_context from JWT payload for the session
        org_context = OrganizationContext(
            user_id=payload.user_id,
            org_id=payload.org_id,
            org_tier="platform",
            org_path=str(payload.org_id),
            role=payload.role,
        )

        logger.info(
            "WS connected session_id=%s user_id=%s org_id=%s",
            session_id,
            payload.user_id,
            payload.org_id,
        )

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "message")

                msg = WSMessage(
                    type=msg_type,
                    session_id=session_id,
                    user_id=payload.user_id,
                    org_id=payload.org_id,
                    content=data.get("content", ""),
                    metadata=data.get("metadata", {}),
                )

                response = await handler.handle_message(msg, sender, org_context=org_context)

                if response.type == "close":
                    break
        except WebSocketDisconnect:
            logger.info("WS disconnected session_id=%s", session_id)
        except Exception:
            logger.exception("WS error session_id=%s", session_id)
            await websocket.close(code=1011, reason="Internal server error")

    return router
