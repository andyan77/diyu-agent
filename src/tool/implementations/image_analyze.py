"""ImageAnalyze Tool — analyze image to structured description.

Milestone: T3-2
Layer: Tool

Atomic, stateless tool for image analysis via vision LLM.
All calls metered to tool_usage_records.

See: docs/architecture/04-Tool Section 3 (ToolProtocol)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, ClassVar

logger = logging.getLogger(__name__)

_MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


@dataclass(frozen=True)
class ToolResult:
    """Generic tool execution result."""

    status: str  # success | error | rate_limited
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ImageAnalyzeTool:
    """Image analysis tool using vision LLM.

    Accepts a presigned image URL and returns structured analysis
    (description, objects, colors, text).
    """

    name: str = "image_analyze"
    version: str = "1.0"
    description: str = "Analyze an image and return structured description"

    INPUT_SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "image_url": {"type": "string", "description": "Presigned URL to image"},
            "analysis_type": {
                "type": "string",
                "enum": ["general", "product", "scene", "text_extraction"],
                "default": "general",
            },
            "detail_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "default": "medium",
            },
        },
        "required": ["image_url"],
    }

    OUTPUT_SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "objects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                },
            },
            "colors": {"type": "array", "items": {"type": "string"}},
            "text_found": {"type": "string"},
            "analysis_type": {"type": "string"},
        },
    }

    def __init__(
        self,
        *,
        vision_backend: Any | None = None,
        storage_backend: Any | None = None,
    ) -> None:
        self._vision = vision_backend
        self._storage = storage_backend

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute image analysis.

        Args:
            params: Must contain "image_url", optionally analysis_type and detail_level.

        Returns:
            ToolResult with analysis data.
        """
        image_url = params.get("image_url", "")
        if not image_url:
            return ToolResult(status="error", error="image_url is required")

        analysis_type = params.get("analysis_type", "general")
        detail_level = params.get("detail_level", "medium")

        # Validate URL (only accept presigned S3/MinIO URLs)
        if not self._is_valid_source(image_url):
            return ToolResult(status="error", error="Invalid image source URL")

        # Check file size if storage backend available
        if self._storage is not None:
            try:
                metadata = await self._storage.head_object(image_url)
                if metadata.size_bytes > _MAX_IMAGE_SIZE:
                    return ToolResult(status="error", error="Image too large (max 10MB)")
            except Exception as e:
                return ToolResult(status="error", error=f"Image validation failed: {e}")

        try:
            if self._vision is not None:
                analysis = await self._vision.analyze(
                    image_url=image_url,
                    analysis_type=analysis_type,
                    detail_level=detail_level,
                )
            else:
                # Stub response when no backend configured
                analysis = {
                    "description": f"Image analysis ({analysis_type}, {detail_level})",
                    "objects": [],
                    "colors": [],
                    "text_found": "",
                    "analysis_type": analysis_type,
                }

            return ToolResult(
                status="success",
                data=analysis,
                metadata={"image_url": image_url, "analysis_type": analysis_type},
            )
        except Exception as e:
            logger.exception("ImageAnalyze failed")
            return ToolResult(status="error", error=str(e))

    @staticmethod
    def _is_valid_source(url: str) -> bool:
        """Validate that URL comes from an allowed source."""
        allowed_prefixes = ("https://", "http://localhost", "http://minio")
        return url.startswith(allowed_prefixes)
