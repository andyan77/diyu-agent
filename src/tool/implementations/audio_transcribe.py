"""AudioTranscribe Tool — transcribe audio file to structured text.

Milestone: T3-3
Layer: Tool

Atomic, stateless tool for speech-to-text transcription.
All calls metered to tool_usage_records.

See: docs/architecture/04-Tool Section 3 (ToolProtocol)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, ClassVar

logger = logging.getLogger(__name__)

_MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB


@dataclass(frozen=True)
class TranscriptSegment:
    """A segment of transcribed audio."""

    start: float
    end: float
    text: str
    confidence: float = 1.0


@dataclass(frozen=True)
class ToolResult:
    """Generic tool execution result."""

    status: str  # success | error | rate_limited
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AudioTranscribeTool:
    """Audio transcription tool using speech-to-text backend.

    Accepts a presigned audio URL and returns structured transcript
    with segments and timestamps.
    """

    name: str = "audio_transcribe"
    version: str = "1.0"
    description: str = "Transcribe audio to text"

    INPUT_SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "audio_url": {"type": "string", "description": "Presigned URL to audio file"},
            "language": {
                "type": "string",
                "enum": ["en", "zh", "ja", "ko", "auto"],
                "default": "auto",
            },
            "format": {
                "type": "string",
                "enum": ["json", "vtt", "srt"],
                "default": "json",
            },
        },
        "required": ["audio_url"],
    }

    OUTPUT_SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "language": {"type": "string"},
            "duration_seconds": {"type": "number"},
            "segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "number"},
                        "end": {"type": "number"},
                        "text": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                },
            },
        },
    }

    def __init__(
        self,
        *,
        transcription_backend: Any | None = None,
        storage_backend: Any | None = None,
    ) -> None:
        self._transcription = transcription_backend
        self._storage = storage_backend

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute audio transcription.

        Args:
            params: Must contain "audio_url", optionally language and format.

        Returns:
            ToolResult with transcription data.
        """
        audio_url = params.get("audio_url", "")
        if not audio_url:
            return ToolResult(status="error", error="audio_url is required")

        language = params.get("language", "auto")
        output_format = params.get("format", "json")

        # Validate URL
        if not self._is_valid_source(audio_url):
            return ToolResult(status="error", error="Invalid audio source URL")

        # Check file size if storage backend available
        if self._storage is not None:
            try:
                metadata = await self._storage.head_object(audio_url)
                if metadata.size_bytes > _MAX_AUDIO_SIZE:
                    return ToolResult(status="error", error="Audio file too large (max 25MB)")
            except Exception as e:
                return ToolResult(status="error", error=f"Audio validation failed: {e}")

        try:
            if self._transcription is not None:
                result = await self._transcription.transcribe(
                    audio_url=audio_url,
                    language=language,
                    output_format=output_format,
                )
            else:
                # Stub response when no backend configured
                result = {
                    "text": f"Transcription placeholder ({language})",
                    "language": language if language != "auto" else "en",
                    "duration_seconds": 0.0,
                    "segments": [],
                }

            return ToolResult(
                status="success",
                data=result,
                metadata={"audio_url": audio_url, "language": language},
            )
        except Exception as e:
            logger.exception("AudioTranscribe failed")
            return ToolResult(status="error", error=str(e))

    @staticmethod
    def _is_valid_source(url: str) -> bool:
        """Validate that URL comes from an allowed source."""
        allowed_prefixes = ("https://", "http://localhost", "http://minio")
        return url.startswith(allowed_prefixes)
