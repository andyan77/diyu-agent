"""Knowledge Admin API -- CRUD knowledge entries via admin endpoint.

Task card: G3-1
- POST/GET/PUT/DELETE /api/v1/admin/knowledge/*
- Dual-write to Neo4j + Qdrant via Knowledge Write API (K3-4)
- RBAC protected (admin role required)

Architecture: docs/architecture/05-Gateway Section 1
"""

from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID  # noqa: TC003 - needed at runtime by FastAPI path params

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


class KnowledgeWritePort(Protocol):
    """Protocol for knowledge write operations (structural typing).

    Satisfied by Knowledge Write API (K3-4).
    Gateway depends on protocol, not concrete implementation.
    """

    async def create_entry(
        self,
        *,
        org_id: UUID,
        entity_type: str,
        properties: dict[str, Any],
        user_id: UUID,
    ) -> dict[str, Any]: ...

    async def get_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
    ) -> dict[str, Any] | None: ...

    async def update_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
        properties: dict[str, Any],
        user_id: UUID,
    ) -> dict[str, Any] | None: ...

    async def delete_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
        user_id: UUID,
    ) -> bool: ...

    async def list_entries(
        self,
        *,
        org_id: UUID,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...


# -- Request/Response models --


class CreateKnowledgeRequest(BaseModel):
    entity_type: str
    properties: dict[str, Any]

    @field_validator("entity_type")
    @classmethod
    def entity_type_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            msg = "entity_type cannot be empty"
            raise ValueError(msg)
        return v.strip()


class UpdateKnowledgeRequest(BaseModel):
    properties: dict[str, Any]


class StatusChangeRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        allowed = {"draft", "published", "archived"}
        if v not in allowed:
            msg = f"status must be one of {allowed}"
            raise ValueError(msg)
        return v


class ReviewActionRequest(BaseModel):
    action: str
    comment: str = ""

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        allowed = {"approve", "reject", "escalate"}
        if v not in allowed:
            msg = f"action must be one of {allowed}"
            raise ValueError(msg)
        return v


class KnowledgeEntryResponse(BaseModel):
    entry_id: str
    entity_type: str
    properties: dict[str, Any]
    org_id: str
    status: str = "draft"


class ReviewActionResponse(BaseModel):
    entry_id: str
    action: str
    new_status: str
    reviewed_by: str


class KnowledgeListResponse(BaseModel):
    entries: list[KnowledgeEntryResponse]
    total: int


def create_knowledge_admin_router(*, knowledge_writer: KnowledgeWritePort) -> APIRouter:
    """Create knowledge admin API router."""
    router = APIRouter(prefix="/api/v1/admin/knowledge", tags=["knowledge-admin"])

    @router.post("/", response_model=KnowledgeEntryResponse, status_code=201)
    async def create_entry(
        body: CreateKnowledgeRequest,
        request: Request,
    ) -> KnowledgeEntryResponse:
        """Create a new knowledge entry (dual-write to Neo4j + Qdrant)."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id

        result = await knowledge_writer.create_entry(
            org_id=org_id,
            entity_type=body.entity_type,
            properties=body.properties,
            user_id=user_id,
        )

        return KnowledgeEntryResponse(
            entry_id=str(result.get("entry_id", result.get("node_id", ""))),
            entity_type=body.entity_type,
            properties=result.get("properties", body.properties),
            org_id=str(org_id),
        )

    @router.get("/", response_model=KnowledgeListResponse)
    async def list_entries(
        request: Request,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> KnowledgeListResponse:
        """List knowledge entries for the organization."""
        org_id: UUID = request.state.org_id

        entries = await knowledge_writer.list_entries(
            org_id=org_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
        )

        return KnowledgeListResponse(
            entries=[
                KnowledgeEntryResponse(
                    entry_id=str(e.get("entry_id", e.get("node_id", ""))),
                    entity_type=e.get("entity_type", ""),
                    properties=e.get("properties", {}),
                    org_id=str(org_id),
                    status=e.get("properties", {}).get("status", "draft"),
                )
                for e in entries
            ],
            total=len(entries),
        )

    @router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
    async def get_entry(
        entry_id: UUID,
        request: Request,
    ) -> KnowledgeEntryResponse:
        """Get a specific knowledge entry."""
        org_id: UUID = request.state.org_id

        result = await knowledge_writer.get_entry(org_id=org_id, entry_id=entry_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")

        return KnowledgeEntryResponse(
            entry_id=str(result.get("entry_id", result.get("node_id", ""))),
            entity_type=result.get("entity_type", ""),
            properties=result.get("properties", {}),
            org_id=str(org_id),
        )

    @router.put("/{entry_id}", response_model=KnowledgeEntryResponse)
    async def update_entry(
        entry_id: UUID,
        body: UpdateKnowledgeRequest,
        request: Request,
    ) -> KnowledgeEntryResponse:
        """Update a knowledge entry."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id

        result = await knowledge_writer.update_entry(
            org_id=org_id,
            entry_id=entry_id,
            properties=body.properties,
            user_id=user_id,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")

        return KnowledgeEntryResponse(
            entry_id=str(result.get("entry_id", result.get("node_id", ""))),
            entity_type=result.get("entity_type", ""),
            properties=result.get("properties", body.properties),
            org_id=str(org_id),
        )

    @router.delete("/{entry_id}", status_code=204)
    async def delete_entry(
        entry_id: UUID,
        request: Request,
    ) -> None:
        """Delete a knowledge entry."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id

        deleted = await knowledge_writer.delete_entry(
            org_id=org_id,
            entry_id=entry_id,
            user_id=user_id,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")

    @router.patch("/{entry_id}/status", response_model=KnowledgeEntryResponse)
    async def change_status(
        entry_id: UUID,
        body: StatusChangeRequest,
        request: Request,
    ) -> KnowledgeEntryResponse:
        """Change the status of a knowledge entry (publish/archive/draft)."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id

        result = await knowledge_writer.update_entry(
            org_id=org_id,
            entry_id=entry_id,
            properties={"status": body.status},
            user_id=user_id,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")

        return KnowledgeEntryResponse(
            entry_id=str(result.get("entry_id", result.get("node_id", ""))),
            entity_type=result.get("entity_type", ""),
            properties=result.get("properties", {}),
            org_id=str(org_id),
            status=body.status,
        )

    @router.post("/{entry_id}/review", response_model=ReviewActionResponse)
    async def review_action(
        entry_id: UUID,
        body: ReviewActionRequest,
        request: Request,
    ) -> ReviewActionResponse:
        """Perform a review action on a knowledge entry (approve/reject/escalate)."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id

        # Map review action to status
        action_status_map = {
            "approve": "published",
            "reject": "rejected",
            "escalate": "escalated",
        }
        new_status = action_status_map[body.action]

        props: dict[str, Any] = {
            "status": new_status,
            "review_action": body.action,
            "reviewed_by": str(user_id),
        }
        if body.comment:
            props["review_comment"] = body.comment

        result = await knowledge_writer.update_entry(
            org_id=org_id,
            entry_id=entry_id,
            properties=props,
            user_id=user_id,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")

        return ReviewActionResponse(
            entry_id=str(result.get("entry_id", result.get("node_id", ""))),
            action=body.action,
            new_status=new_status,
            reviewed_by=str(user_id),
        )

    return router
