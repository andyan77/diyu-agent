"""WebSearch Tool — keyword search returning structured results.

Milestone: T3-1
Layer: Tool

Atomic, stateless tool for web search. All calls metered to
tool_usage_records.

See: docs/architecture/04-Tool Section 3 (ToolProtocol)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebSearchResult:
    """A single search result."""

    url: str
    title: str
    snippet: str
    position: int


@dataclass(frozen=True)
class WebSearchOutput:
    """Output of a web search execution."""

    results: list[WebSearchResult] = field(default_factory=list)
    total_results: int = 0


@dataclass(frozen=True)
class ToolResult:
    """Generic tool execution result."""

    status: str  # success | error | rate_limited
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class WebSearchTool:
    """Web search tool implementation.

    Accepts a query string and returns structured search results.
    Uses a configurable backend (Bing, Google, etc.) via adapter.
    """

    name: str = "web_search"
    version: str = "1.0"
    description: str = "Search the web for information"

    INPUT_SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1, "maxLength": 500},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
            "safe_search": {"type": "boolean", "default": True},
        },
        "required": ["query"],
    }

    OUTPUT_SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                        "snippet": {"type": "string"},
                        "position": {"type": "integer"},
                    },
                },
            },
            "total_results": {"type": "integer"},
        },
    }

    def __init__(self, *, search_backend: Any | None = None) -> None:
        self._backend = search_backend

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute a web search.

        Args:
            params: Must contain "query", optionally "top_k" and "safe_search".

        Returns:
            ToolResult with search results.
        """
        query = params.get("query", "")
        if not query:
            return ToolResult(status="error", error="query is required")

        top_k = params.get("top_k", 10)
        safe_search = params.get("safe_search", True)

        try:
            if self._backend is not None:
                raw_results = await self._backend.search(
                    query=query,
                    top_k=top_k,
                    safe_search=safe_search,
                )
            else:
                # Stub: return empty results when no backend configured
                raw_results = []

            results = [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "position": idx + 1,
                }
                for idx, r in enumerate(raw_results[:top_k])
            ]

            return ToolResult(
                status="success",
                data={"results": results, "total_results": len(results)},
                metadata={"query": query, "safe_search": safe_search},
            )
        except Exception as e:
            logger.exception("WebSearch failed")
            return ToolResult(status="error", error=str(e))
