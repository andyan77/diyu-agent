"""T3-3: AudioTranscribe Tool tests.

Tests: input validation, output schema, URL validation, backend integration.
"""

from __future__ import annotations

import pytest

from src.tool.implementations.audio_transcribe import AudioTranscribeTool


class TestAudioTranscribeInputValidation:
    @pytest.mark.asyncio
    async def test_empty_url_returns_error(self) -> None:
        tool = AudioTranscribeTool()
        result = await tool.execute({"audio_url": ""})
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_missing_url_returns_error(self) -> None:
        tool = AudioTranscribeTool()
        result = await tool.execute({})
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_invalid_source_rejected(self) -> None:
        tool = AudioTranscribeTool()
        result = await tool.execute({"audio_url": "ftp://evil.com/audio.mp3"})
        assert result.status == "error"


class TestAudioTranscribeOutputSchema:
    @pytest.mark.asyncio
    async def test_success_has_text(self) -> None:
        tool = AudioTranscribeTool()
        result = await tool.execute({"audio_url": "https://example.com/audio.mp3"})
        assert result.status == "success"
        assert result.data is not None
        assert "text" in result.data

    @pytest.mark.asyncio
    async def test_output_has_language(self) -> None:
        tool = AudioTranscribeTool()
        result = await tool.execute({"audio_url": "https://example.com/audio.mp3"})
        assert result.data is not None
        assert "language" in result.data

    @pytest.mark.asyncio
    async def test_output_has_segments(self) -> None:
        tool = AudioTranscribeTool()
        result = await tool.execute({"audio_url": "https://example.com/audio.mp3"})
        assert result.data is not None
        assert "segments" in result.data
        assert isinstance(result.data["segments"], list)


class TestAudioTranscribeWithBackend:
    @pytest.mark.asyncio
    async def test_transcription_backend_called(self) -> None:

        class FakeTranscription:
            async def transcribe(self, audio_url: str, language: str, output_format: str) -> dict:
                return {
                    "text": "Hello world",
                    "language": "en",
                    "duration_seconds": 3.5,
                    "segments": [
                        {"start": 0.0, "end": 1.5, "text": "Hello", "confidence": 0.98},
                        {"start": 1.5, "end": 3.5, "text": "world", "confidence": 0.95},
                    ],
                }

        tool = AudioTranscribeTool(transcription_backend=FakeTranscription())
        result = await tool.execute({"audio_url": "https://cdn.example.com/audio.wav"})
        assert result.status == "success"
        assert result.data is not None
        assert result.data["text"] == "Hello world"
        assert len(result.data["segments"]) == 2
        assert result.data["duration_seconds"] == 3.5
