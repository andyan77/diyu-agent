"""T3-1: WebSearch Tool tests.

Tests: input validation, output schema, backend integration, error handling.
"""

from __future__ import annotations

import pytest

from src.tool.implementations.web_search import WebSearchTool


class TestWebSearchInputValidation:
    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self) -> None:
        tool = WebSearchTool()
        result = await tool.execute({"query": ""})
        assert result.status == "error"
        assert "required" in (result.error or "")

    @pytest.mark.asyncio
    async def test_missing_query_returns_error(self) -> None:
        tool = WebSearchTool()
        result = await tool.execute({})
        assert result.status == "error"


class TestWebSearchOutputSchema:
    @pytest.mark.asyncio
    async def test_success_output_has_results(self) -> None:
        tool = WebSearchTool()
        result = await tool.execute({"query": "test search"})
        assert result.status == "success"
        assert result.data is not None
        assert "results" in result.data
        assert "total_results" in result.data

    @pytest.mark.asyncio
    async def test_results_is_list(self) -> None:
        tool = WebSearchTool()
        result = await tool.execute({"query": "test"})
        assert result.data is not None
        assert isinstance(result.data["results"], list)

    @pytest.mark.asyncio
    async def test_metadata_contains_query(self) -> None:
        tool = WebSearchTool()
        result = await tool.execute({"query": "hello world"})
        assert result.metadata.get("query") == "hello world"


class TestWebSearchWithBackend:
    @pytest.mark.asyncio
    async def test_backend_results_returned(self) -> None:

        class FakeBackend:
            async def search(self, query: str, top_k: int, safe_search: bool) -> list:
                return [
                    {"url": "https://example.com", "title": "Example", "snippet": "A site"},
                    {"url": "https://test.com", "title": "Test", "snippet": "Test site"},
                ]

        tool = WebSearchTool(search_backend=FakeBackend())
        result = await tool.execute({"query": "test", "top_k": 5})
        assert result.status == "success"
        assert result.data is not None
        assert len(result.data["results"]) == 2
        assert result.data["results"][0]["position"] == 1
        assert result.data["results"][1]["position"] == 2

    @pytest.mark.asyncio
    async def test_backend_error_handled(self) -> None:

        class FailingBackend:
            async def search(self, **kwargs) -> list:
                msg = "API error"
                raise RuntimeError(msg)

        tool = WebSearchTool(search_backend=FailingBackend())
        result = await tool.execute({"query": "test"})
        assert result.status == "error"
        assert "API error" in (result.error or "")
