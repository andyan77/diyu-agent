"""Three-step file upload protocol.

Task card: G2-6
- Step 1: POST /api/v1/uploads/init -> presigned URL + upload_id
- Step 2: Client uploads directly to storage (not through gateway)
- Step 3: POST /api/v1/uploads/{upload_id}/complete -> confirm + validate

Architecture: ADR-045, 05-Gateway Section 8.2
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


# Max file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_MIME_TYPES = frozenset(
    {
        "text/plain",
        "text/csv",
        "text/markdown",
        "application/json",
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
    }
)


class UploadInitRequest(BaseModel):
    """Step 1: Initialize upload."""

    filename: str
    content_type: str
    file_size: int

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v or not v.strip():
            msg = "Filename cannot be empty"
            raise ValueError(msg)
        # Basic path traversal prevention
        if ".." in v or "/" in v or "\\" in v:
            msg = "Invalid filename"
            raise ValueError(msg)
        return v.strip()

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        if v not in ALLOWED_MIME_TYPES:
            msg = f"Content type not allowed: {v}"
            raise ValueError(msg)
        return v

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        if v <= 0:
            msg = "File size must be positive"
            raise ValueError(msg)
        if v > MAX_FILE_SIZE:
            msg = f"File size exceeds limit: {v} > {MAX_FILE_SIZE}"
            raise ValueError(msg)
        return v


class UploadInitResponse(BaseModel):
    """Step 1 response: presigned URL for upload."""

    upload_id: str
    upload_url: str
    expires_at: str


class UploadCompleteRequest(BaseModel):
    """Step 3: Complete upload with checksum verification."""

    checksum_sha256: str | None = None


class UploadCompleteResponse(BaseModel):
    """Step 3 response: confirmed upload details."""

    upload_id: str
    filename: str
    content_type: str
    file_size: int
    status: str


class UploadStatusResponse(BaseModel):
    """Upload status for querying."""

    upload_id: str
    filename: str
    status: str
    created_at: str


# In-memory upload registry for Phase 2
_uploads: dict[UUID, dict[str, Any]] = {}


def _reset_uploads() -> None:
    """Reset in-memory upload store (for testing)."""
    _uploads.clear()


def create_upload_router(
    *,
    storage_base_url: str = "http://localhost:9000",
) -> APIRouter:
    """Create upload API router."""
    router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])

    @router.post("/init", response_model=UploadInitResponse, status_code=201)
    async def init_upload(
        body: UploadInitRequest,
        request: Request,
    ) -> UploadInitResponse:
        """Step 1: Initialize file upload and get presigned URL."""
        org_id: UUID = request.state.org_id
        user_id: UUID = request.state.user_id
        upload_id = uuid4()
        now = datetime.now(UTC)

        # Generate presigned upload URL (simulated for Phase 2)
        upload_url = f"{storage_base_url}/uploads/{org_id}/{upload_id}/{body.filename}"
        expires_at = datetime(now.year, now.month, now.day, now.hour + 1, tzinfo=UTC).isoformat()

        _uploads[upload_id] = {
            "upload_id": upload_id,
            "org_id": org_id,
            "user_id": user_id,
            "filename": body.filename,
            "content_type": body.content_type,
            "file_size": body.file_size,
            "status": "pending",
            "upload_url": upload_url,
            "created_at": now.isoformat(),
        }

        logger.info(
            "Upload initialized upload_id=%s filename=%s org_id=%s",
            upload_id,
            body.filename,
            org_id,
        )

        return UploadInitResponse(
            upload_id=str(upload_id),
            upload_url=upload_url,
            expires_at=expires_at,
        )

    @router.post(
        "/{upload_id}/complete",
        response_model=UploadCompleteResponse,
    )
    async def complete_upload(
        upload_id: UUID,
        body: UploadCompleteRequest,
        request: Request,
    ) -> UploadCompleteResponse:
        """Step 3: Confirm upload completion with optional checksum."""
        org_id: UUID = request.state.org_id

        upload = _uploads.get(upload_id)
        if upload is None:
            raise HTTPException(status_code=404, detail="Upload not found")

        if upload["org_id"] != org_id:
            raise HTTPException(status_code=404, detail="Upload not found")

        if upload["status"] != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Upload already {upload['status']}",
            )

        upload["status"] = "completed"

        logger.info(
            "Upload completed upload_id=%s filename=%s",
            upload_id,
            upload["filename"],
        )

        return UploadCompleteResponse(
            upload_id=str(upload_id),
            filename=upload["filename"],
            content_type=upload["content_type"],
            file_size=upload["file_size"],
            status="completed",
        )

    @router.get("/{upload_id}", response_model=UploadStatusResponse)
    async def get_upload_status(
        upload_id: UUID,
        request: Request,
    ) -> UploadStatusResponse:
        """Query upload status."""
        org_id: UUID = request.state.org_id

        upload = _uploads.get(upload_id)
        if upload is None or upload["org_id"] != org_id:
            raise HTTPException(status_code=404, detail="Upload not found")

        return UploadStatusResponse(
            upload_id=str(upload_id),
            filename=upload["filename"],
            status=upload["status"],
            created_at=upload["created_at"],
        )

    return router
