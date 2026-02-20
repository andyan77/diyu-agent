"""Skill API -- list and trigger skills via REST.

Task card: G3-2
- GET /api/v1/skills -> list available skills
- POST /api/v1/skills/{id}/execute -> trigger skill execution
- GET /api/v1/skills/{id} -> skill detail

Architecture: docs/architecture/05-Gateway Section 1
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID  # noqa: TC003 - needed at runtime by FastAPI

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.ports.skill_registry import SkillRegistry, SkillStatus

logger = logging.getLogger(__name__)


class SkillSummaryResponse(BaseModel):
    skill_id: str
    name: str
    description: str
    status: str
    version: str
    intent_types: list[str]


class SkillListResponse(BaseModel):
    skills: list[SkillSummaryResponse]
    total: int


class ExecuteSkillRequest(BaseModel):
    params: dict[str, Any] = {}


class SkillExecutionResponse(BaseModel):
    skill_id: str
    success: bool
    output: Any | None = None
    error: str | None = None


def create_skill_router(*, registry: SkillRegistry) -> APIRouter:
    """Create skill API router."""
    router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

    @router.get("/", response_model=SkillListResponse)
    async def list_skills(
        request: Request,
        status: str | None = None,
    ) -> SkillListResponse:
        """List all registered skills."""
        filter_status = None
        if status:
            try:
                filter_status = SkillStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}",
                ) from None

        if hasattr(registry, "list_skills"):
            skills = registry.list_skills(status=filter_status)
        else:
            skills = []

        return SkillListResponse(
            skills=[
                SkillSummaryResponse(
                    skill_id=s.skill_id,
                    name=s.name,
                    description=s.description,
                    status=s.status.value,
                    version=s.version,
                    intent_types=s.intent_types,
                )
                for s in skills
            ],
            total=len(skills),
        )

    @router.get("/{skill_id}", response_model=SkillSummaryResponse)
    async def get_skill(
        skill_id: str,
        request: Request,
    ) -> SkillSummaryResponse:
        """Get skill details."""
        defn = registry.get_definition(skill_id) if hasattr(registry, "get_definition") else None

        if defn is None:
            raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

        return SkillSummaryResponse(
            skill_id=defn.skill_id,
            name=defn.name,
            description=defn.description,
            status=defn.status.value,
            version=defn.version,
            intent_types=defn.intent_types,
        )

    @router.post("/{skill_id}/execute", response_model=SkillExecutionResponse)
    async def execute_skill(
        skill_id: str,
        body: ExecuteSkillRequest,
        request: Request,
    ) -> SkillExecutionResponse:
        """Trigger skill execution."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id

        from src.shared.types import KnowledgeBundle

        context: dict[str, Any] = {
            "params": body.params,
            "org_id": str(org_id),
            "user_id": str(user_id),
        }
        empty_knowledge = KnowledgeBundle()

        result = await registry.execute(skill_id, empty_knowledge, context)

        return SkillExecutionResponse(
            skill_id=result.skill_id,
            success=result.success,
            output=result.output,
            error=result.error,
        )

    return router
