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
    ) -> dict[str, Any]: ...

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


class KnowledgeEntryResponse(BaseModel):
    entry_id: str
    entity_type: str
    properties: dict[str, Any]
    org_id: str


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

    return router
