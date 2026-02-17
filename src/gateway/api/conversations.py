"""Conversation REST API endpoints.

Task card: G2-1
- POST /api/v1/conversations/{id}/messages -> Brain processing -> return reply
- GET /api/v1/conversations/{id}/messages -> conversation history
- POST /api/v1/conversations -> create new conversation
- GET /api/v1/conversations -> list conversations

Architecture: 05-Gateway Section 1, ADR-029
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

if TYPE_CHECKING:
    from src.ports.conversation_port import ConversationPort

logger = logging.getLogger(__name__)


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""

    message: str
    model_id: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            msg = "Message cannot be empty"
            raise ValueError(msg)
        return v.strip()


class SendMessageResponse(BaseModel):
    """Response model for a processed message."""

    turn_id: str
    session_id: str
    assistant_response: str
    tokens_used: dict[str, int]
    model_id: str
    intent_type: str


class CreateConversationResponse(BaseModel):
    """Response for conversation creation."""

    session_id: str
    created_at: str


class ConversationSummary(BaseModel):
    """Summary of a conversation."""

    session_id: str
    created_at: str
    message_count: int = 0


class MessageItem(BaseModel):
    """Single message in conversation history."""

    role: str
    content: str
    timestamp: str | None = None


# In-memory stores for Phase 2 (Redis/PG adapter in production)
_conversations: dict[tuple[UUID, UUID], dict[str, Any]] = {}
_messages: dict[tuple[UUID, UUID], list[dict[str, str]]] = {}


def _reset_stores() -> None:
    """Reset in-memory stores (for testing)."""
    _conversations.clear()
    _messages.clear()


def create_conversation_router(*, engine: ConversationPort) -> APIRouter:
    """Create conversation API router with injected engine dependency."""
    router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

    @router.post("/", response_model=CreateConversationResponse, status_code=201)
    async def create_conversation(request: Request) -> CreateConversationResponse:
        """Create a new conversation session."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id
        session_id = uuid4()
        now = datetime.now(UTC).isoformat()

        _conversations[(org_id, session_id)] = {
            "session_id": session_id,
            "org_id": org_id,
            "user_id": user_id,
            "created_at": now,
            "message_count": 0,
        }
        _messages[(org_id, session_id)] = []

        logger.info(
            "Created conversation session_id=%s org_id=%s",
            session_id,
            org_id,
        )
        return CreateConversationResponse(session_id=str(session_id), created_at=now)

    @router.get("/", response_model=list[ConversationSummary])
    async def list_conversations(request: Request) -> list[ConversationSummary]:
        """List conversations for the authenticated user."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id

        result: list[ConversationSummary] = []
        for (stored_org, sid), data in _conversations.items():
            if stored_org == org_id and data.get("user_id") == user_id:
                result.append(
                    ConversationSummary(
                        session_id=str(sid),
                        created_at=data["created_at"],
                        message_count=data.get("message_count", 0),
                    )
                )
        result.sort(key=lambda c: c.created_at, reverse=True)
        return result

    @router.post("/{session_id}/messages", response_model=SendMessageResponse)
    async def send_message(
        session_id: UUID,
        body: SendMessageRequest,
        request: Request,
    ) -> SendMessageResponse:
        """Send a message and receive assistant response."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id
        key = (org_id, session_id)

        # Auto-create conversation if not exists
        if key not in _conversations:
            now = datetime.now(UTC).isoformat()
            _conversations[key] = {
                "session_id": session_id,
                "org_id": org_id,
                "user_id": user_id,
                "created_at": now,
                "message_count": 0,
            }
            _messages[key] = []

        history = [{"role": m["role"], "content": m["content"]} for m in _messages.get(key, [])]

        try:
            turn = await engine.process_message(
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                message=body.message,
                conversation_history=history,
                model_id=body.model_id,
            )
        except Exception:
            logger.exception("Error processing message session_id=%s", session_id)
            raise HTTPException(status_code=500, detail="Failed to process message") from None

        now = datetime.now(UTC).isoformat()
        _messages[key].append({"role": "user", "content": body.message, "ts": now})
        _messages[key].append({"role": "assistant", "content": turn.assistant_response, "ts": now})
        _conversations[key]["message_count"] = len(_messages[key])

        return SendMessageResponse(
            turn_id=str(turn.turn_id),
            session_id=str(turn.session_id),
            assistant_response=turn.assistant_response,
            tokens_used=turn.tokens_used,
            model_id=turn.model_id,
            intent_type=turn.intent_type,
        )

    @router.get("/{session_id}/messages", response_model=list[MessageItem])
    async def get_messages(
        session_id: UUID,
        request: Request,
    ) -> list[MessageItem]:
        """Get conversation message history."""
        org_id: UUID = request.state.org_id
        msgs = _messages.get((org_id, session_id), [])
        return [
            MessageItem(role=m["role"], content=m["content"], timestamp=m.get("ts")) for m in msgs
        ]

    return router
