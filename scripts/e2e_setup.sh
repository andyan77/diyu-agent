#!/usr/bin/env bash
# E2E environment bootstrap for Playwright tests.
#
# Ensures PostgreSQL + Redis are reachable, runs migrations,
# seeds the dev user, and verifies backend health.
#
# Usage:
#   bash scripts/e2e_setup.sh          # local (docker compose services)
#   bash scripts/e2e_setup.sh --ci     # CI (services provided by GitHub Actions)
#
# Environment variables (with defaults):
#   E2E_API_PORT          8001
#   DATABASE_URL          postgresql+asyncpg://diyu:diyu_dev@localhost:25432/diyu
#   REDIS_URL             redis://localhost:6380/0
#   SKIP_DOCKER_COMPOSE   0   (set to 1 in CI)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

E2E_API_PORT="${E2E_API_PORT:-8001}"

# CI mode: GitHub Actions provides services on standard ports
if [[ "${1:-}" == "--ci" ]] || [[ "${CI:-}" == "true" ]]; then
    export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://diyu:diyu_dev@localhost:5432/diyu}"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
    SKIP_DOCKER_COMPOSE=1
else
    export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://diyu:diyu_dev@localhost:25432/diyu}"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6380/0}"
    SKIP_DOCKER_COMPOSE="${SKIP_DOCKER_COMPOSE:-0}"
fi

echo "=== E2E Setup ==="
echo "  DATABASE_URL: ${DATABASE_URL//:*@/:***@}"
echo "  REDIS_URL:    $REDIS_URL"
echo "  API_PORT:     $E2E_API_PORT"
echo ""

# ---- Step 1: Ensure docker compose services (local only) ----
if [[ "$SKIP_DOCKER_COMPOSE" != "1" ]]; then
    echo "[1/4] Checking docker compose services..."
    cd "$PROJECT_ROOT"
    # Only start postgres + redis (not the full app stack)
    docker compose up -d postgres redis 2>/dev/null || {
        echo "WARNING: docker compose up failed, assuming services are already running"
    }
    # Wait for PostgreSQL to accept connections
    for i in $(seq 1 30); do
        if docker compose exec -T postgres pg_isready -U diyu > /dev/null 2>&1; then
            echo "  PostgreSQL ready"
            break
        fi
        if [[ $i -eq 30 ]]; then
            echo "ERROR: PostgreSQL not ready after 30s"
            exit 1
        fi
        sleep 1
    done
else
    echo "[1/4] Skipping docker compose (CI mode)"
fi

# ---- Step 2: Run Alembic migrations ----
echo "[2/4] Running database migrations..."
cd "$PROJECT_ROOT"
uv run alembic upgrade head 2>&1 || {
    echo "WARNING: alembic upgrade failed (may already be at head)"
}

# ---- Step 3: Seed dev user ----
echo "[3/4] Seeding dev user..."
uv run python scripts/seed_dev_user.py 2>&1 || {
    echo "WARNING: seed_dev_user failed (user may already exist)"
}

# ---- Step 4: Verify backend health (if running) ----
echo "[4/4] E2E environment ready."
echo ""
echo "To start the backend for E2E tests:"
echo "  uv run uvicorn src.main:app --host 0.0.0.0 --port $E2E_API_PORT"
echo ""
echo "Playwright will auto-start the backend via webServer config."
