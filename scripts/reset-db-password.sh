#!/usr/bin/env bash
# Reset PostgreSQL password to match docker-compose.yml / .env settings.
# Use when pgdata volume was created with a different password.
#
# Usage: bash scripts/reset-db-password.sh

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PG_USER="${PG_USER:-diyu}"
PG_PASSWORD="${PG_PASSWORD:-diyu_dev}"

echo "[1/3] Resetting password for PostgreSQL user '${PG_USER}'..."
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  psql -U postgres -c "ALTER USER ${PG_USER} WITH PASSWORD '${PG_PASSWORD}';"

echo "[2/3] Verifying connection from host..."
if docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  psql -U "${PG_USER}" -d diyu -c "SELECT 1;" > /dev/null 2>&1; then
  echo "  OK: password authentication successful"
else
  echo "  WARN: verification via psql failed (may need pg_hba.conf update)"
fi

echo "[3/3] Done. Backend should now connect with DATABASE_URL password '${PG_PASSWORD}'."
echo "  Restart backend if needed: docker compose restart backend"
