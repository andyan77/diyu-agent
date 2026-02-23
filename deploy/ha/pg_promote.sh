#!/usr/bin/env bash
# PostgreSQL Standby Promote Script (Decision R-4)
#
# Promotes pg-standby to primary when pg-primary fails.
# No Patroni — manual promote via pg_ctl or pg_promote().
#
# Usage:
#   bash deploy/ha/pg_promote.sh                  # Live promote
#   bash deploy/ha/pg_promote.sh --dry-run        # Validate only
#
# Prerequisites:
#   - docker compose with deploy/ha/docker-compose.ha.yml running
#   - pg-standby is in streaming replication mode
#
# Exit codes:
#   0 - Promote succeeded (or dry-run validation passed)
#   1 - Promote failed

set -euo pipefail

COMPOSE_FILE="deploy/ha/docker-compose.ha.yml"
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

echo "=== PostgreSQL Standby Promote ==="
echo "Mode: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'LIVE')"
echo ""

# Check compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "[FAIL] Compose file not found: $COMPOSE_FILE"
  exit 1
fi
echo "[OK] Compose file exists"

if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "[dry-run] Would execute:"
  echo "  1. Verify pg-standby is in recovery mode"
  echo "  2. docker compose exec pg-standby pg_ctl promote -D \$PGDATA"
  echo "  3. Verify pg-standby is accepting writes"
  echo "  4. Update app-1/app-2 DATABASE_URL to point to pg-standby"
  echo ""
  echo "Promote dry-run: PASS"
  exit 0
fi

# Live promote
echo "[1/4] Checking pg-standby recovery status..."
IS_RECOVERY=$(docker compose -f "$COMPOSE_FILE" exec -T pg-standby \
  psql -U diyu -d diyu -tAc "SELECT pg_is_in_recovery();" 2>/dev/null || echo "error")

if [ "$IS_RECOVERY" != "t" ]; then
  echo "[FAIL] pg-standby is not in recovery mode (got: $IS_RECOVERY)"
  exit 1
fi
echo "  pg-standby is in recovery mode"

echo "[2/4] Promoting pg-standby..."
docker compose -f "$COMPOSE_FILE" exec -T pg-standby \
  pg_ctl promote -D /var/lib/postgresql/data

echo "[3/4] Waiting for promotion to complete..."
for i in $(seq 1 30); do
  IS_RECOVERY=$(docker compose -f "$COMPOSE_FILE" exec -T pg-standby \
    psql -U diyu -d diyu -tAc "SELECT pg_is_in_recovery();" 2>/dev/null || echo "error")
  if [ "$IS_RECOVERY" = "f" ]; then
    echo "  pg-standby promoted to primary after ${i}s"
    break
  fi
  sleep 1
done

if [ "$IS_RECOVERY" != "f" ]; then
  echo "[FAIL] pg-standby did not complete promotion within 30s"
  exit 1
fi

echo "[4/4] Verifying write access..."
docker compose -f "$COMPOSE_FILE" exec -T pg-standby \
  psql -U diyu -d diyu -c "CREATE TABLE IF NOT EXISTS _promote_test (id int); DROP TABLE _promote_test;" \
  2>/dev/null

echo ""
echo "=== Promote Complete ==="
echo "pg-standby is now the primary. Update app DATABASE_URL to point to pg-standby:5432."
