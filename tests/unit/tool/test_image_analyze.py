"""T3-2: ImageAnalyze Tool tests.

Tests: input validation, output schema, URL validation, size check.
"""

from __future__ import annotations

import pytest

from src.tool.implementations.image_analyze import ImageAnalyzeTool


class TestImageAnalyzeInputValidation:
    @pytest.mark.asyncio
    async def test_empty_url_returns_error(self) -> None:
        tool = ImageAnalyzeTool()
        result = await tool.execute({"image_url": ""})
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_missing_url_returns_error(self) -> None:
        tool = ImageAnalyzeTool()
        result = await tool.execute({})
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_invalid_source_rejected(self) -> None:
        tool = ImageAnalyzeTool()
        result = await tool.execute({"image_url": "ftp://evil.com/image.jpg"})
        assert result.status == "error"
        assert "Invalid" in (result.error or "")


class TestImageAnalyzeOutputSchema:
    @pytest.mark.asyncio
    async def test_success_has_description(self) -> None:
        tool = ImageAnalyzeTool()
        result = await tool.execute({"image_url": "https://example.com/img.jpg"})
        assert result.status == "success"
        assert result.data is not None
        assert "description" in result.data

    @pytest.mark.asyncio
    async def test_output_has_objects_and_colors(self) -> None:
        tool = ImageAnalyzeTool()
        result = await tool.execute({"image_url": "https://example.com/img.jpg"})
        assert result.data is not None
        assert "objects" in result.data
        assert "colors" in result.data

    @pytest.mark.asyncio
    async def test_analysis_type_in_output(self) -> None:
        tool = ImageAnalyzeTool()
        result = await tool.execute(
            {
                "image_url": "https://example.com/img.jpg",
                "analysis_type": "product",
            }
        )
        assert result.data is not None
        assert result.data.get("analysis_type") == "product"


class TestImageAnalyzeWithBackend:
    @pytest.mark.asyncio
    async def test_vision_backend_called(self) -> None:

        class FakeVision:
            async def analyze(self, image_url: str, analysis_type: str, detail_level: str) -> dict:
                return {
                    "description": "A red dress",
                    "objects": [{"name": "dress", "confidence": 0.95}],
                    "colors": ["red", "white"],
                    "text_found": "",
                    "analysis_type": analysis_type,
                }

        tool = ImageAnalyzeTool(vision_backend=FakeVision())
        result = await tool.execute({"image_url": "https://cdn.example.com/img.jpg"})
        assert result.status == "success"
        assert result.data is not None
        assert result.data["description"] == "A red dress"
        assert len(result.data["objects"]) == 1
