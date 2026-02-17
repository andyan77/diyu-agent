"""4 Golden Signals middleware for FastAPI.

Task card: OS2-1
- Latency: request duration histogram (seconds)
- Traffic: request counter
- Errors: error counter (HTTP 5xx)
- Saturation: active request gauge

Architecture: 07-Deployment-Security Section 2
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request, Response

# -- Latency --
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status_code"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# -- Traffic --
REQUEST_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

# -- Errors --
ERROR_TOTAL = Counter(
    "http_errors_total",
    "Total HTTP error responses (5xx)",
    ["method", "path", "status_code"],
)

# -- Saturation --
ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Number of active HTTP requests",
    ["method"],
)

_EXEMPT_PATHS = frozenset({"/metrics", "/healthz"})


def _normalize_path(path: str) -> str:
    """Collapse path parameters to reduce cardinality.

    /api/v1/conversations/abc123 -> /api/v1/conversations/{id}
    """
    parts = path.rstrip("/").split("/")
    normalized: list[str] = []
    for part in parts:
        if not part:
            normalized.append(part)
            continue
        # Heuristic: if part looks like a UUID or numeric ID, replace
        if len(part) >= 8 and any(c.isdigit() for c in part):
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized) or "/"


async def golden_signals_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Collect 4 golden signals for each request."""
    path = request.url.path

    if path in _EXEMPT_PATHS:
        return await call_next(request)

    method = request.method
    normalized = _normalize_path(path)

    ACTIVE_REQUESTS.labels(method=method).inc()
    start = time.monotonic()

    try:
        response = await call_next(request)
    except Exception:
        duration = time.monotonic() - start
        status = "500"
        labels = {"method": method, "path": normalized, "status_code": status}
        REQUEST_DURATION.labels(**labels).observe(duration)
        REQUEST_TOTAL.labels(**labels).inc()
        ERROR_TOTAL.labels(**labels).inc()
        raise
    finally:
        ACTIVE_REQUESTS.labels(method=method).dec()

    duration = time.monotonic() - start
    status = str(response.status_code)

    REQUEST_DURATION.labels(method=method, path=normalized, status_code=status).observe(duration)
    REQUEST_TOTAL.labels(method=method, path=normalized, status_code=status).inc()

    if response.status_code >= 500:
        ERROR_TOTAL.labels(method=method, path=normalized, status_code=status).inc()

    return response
