# DIYU Agent Production Container
# Multi-stage build: builder (uv + deps) -> runtime (slim, non-root)
# Usage: docker build -t diyu-agent:latest .
# Scan:  trivy image --exit-code 1 --severity HIGH,CRITICAL diyu-agent:latest

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy dependency files first (cache layer)
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev)
# Use /app/.venv so shebangs match the runtime stage path
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini ./

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd --gid 1000 diyu && \
    useradd --uid 1000 --gid diyu --shell /bin/false --create-home diyu

WORKDIR /app

# Copy virtual environment from builder (built at /app/.venv via UV_PROJECT_ENVIRONMENT)
COPY --from=builder --chown=diyu:diyu /app/.venv /app/.venv

# Copy application source
COPY --from=builder --chown=diyu:diyu /build/src /app/src
COPY --from=builder --chown=diyu:diyu /build/migrations /app/migrations
COPY --from=builder --chown=diyu:diyu /build/alembic.ini /app/alembic.ini

# Ensure venv binaries are on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import httpx; httpx.get('http://localhost:8000/healthz').raise_for_status()"]

# Drop to non-root
USER diyu

EXPOSE 8000

# Default entrypoint: uvicorn with production settings
CMD ["uvicorn", "src.gateway.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
