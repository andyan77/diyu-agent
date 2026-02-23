#!/usr/bin/env bash
# DIYU Agent HA Validation Check
#
# Gate ID: p4-ha-validation
# Validates High Availability configuration and failover capability.
#
# Topology (decision R-4):
#   - 2 app instances behind nginx upstream
#   - PostgreSQL primary/standby (pg_basebackup + manual promote)
#   - Failover target: <30s recovery
#
# Usage:
#   bash scripts/check_ha_validation.sh              # Run HA validation
#   bash scripts/check_ha_validation.sh --dry-run    # Check HA config only
#
# Exit codes:
#   0 - HA validation passed
#   1 - HA validation failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

echo "=== DIYU Agent HA Validation ==="
echo ""

PASS_COUNT=0
FAIL_COUNT=0

check_pass() {
  echo "  [OK]   $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

check_fail() {
  echo "  [FAIL] $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

# Check 1: HA docker-compose config exists
HA_COMPOSE="$PROJECT_ROOT/deploy/ha/docker-compose.ha.yml"
if [ -f "$HA_COMPOSE" ]; then
  check_pass "HA docker-compose config exists ($HA_COMPOSE)"
else
  check_fail "HA docker-compose config not found ($HA_COMPOSE)"
fi

# Check 2: nginx upstream config exists
NGINX_CONF="$PROJECT_ROOT/deploy/ha/nginx.conf"
if [ -f "$NGINX_CONF" ]; then
  # Verify it contains upstream block
  if grep -q "upstream" "$NGINX_CONF" 2>/dev/null; then
    check_pass "nginx upstream config valid ($NGINX_CONF)"
  else
    check_fail "nginx config missing upstream block"
  fi
else
  check_fail "nginx config not found ($NGINX_CONF)"
fi

# Check 3: PG standby promote script exists
PG_PROMOTE="$PROJECT_ROOT/deploy/ha/pg_promote.sh"
if [ -f "$PG_PROMOTE" ]; then
  check_pass "PG promote script exists ($PG_PROMOTE)"
else
  check_fail "PG promote script not found ($PG_PROMOTE)"
fi

# Check 4: HA test script or E2E
HA_TEST="$PROJECT_ROOT/tests/e2e/cross/test_ha_failover.py"
if [ -f "$HA_TEST" ]; then
  check_pass "HA failover test exists ($HA_TEST)"
else
  check_fail "HA failover test not found ($HA_TEST)"
fi

if $DRY_RUN; then
  echo ""
  echo "  [DRY-RUN] HA config validation only (no live failover test)"
  echo ""
  echo "  Passed: $PASS_COUNT  Failed: $FAIL_COUNT"
  echo ""
  if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "HA validation (dry-run): PASS"
    exit 0
  else
    echo "HA validation (dry-run): FAIL"
    exit 1
  fi
fi

# Live HA validation: start HA stack and test failover
echo ""
echo "[Live] Starting HA stack for failover test..."

# Check docker compose availability
if ! command -v docker >/dev/null 2>&1; then
  check_fail "docker not available for live HA test"
  echo ""
  echo "HA validation: FAIL ($FAIL_COUNT failures)"
  exit 1
fi

if [ ! -f "$HA_COMPOSE" ]; then
  echo "  Cannot run live test without HA compose file"
  echo ""
  echo "HA validation: FAIL"
  exit 1
fi

echo "  Starting HA services..."
cd "$PROJECT_ROOT" && docker compose -f "$HA_COMPOSE" up -d 2>/dev/null || {
  check_fail "Failed to start HA stack"
  echo "HA validation: FAIL"
  exit 1
}

# Wait for services
sleep 10

echo "  Simulating app instance failure..."
docker compose -f "$HA_COMPOSE" stop app-1 2>/dev/null || true

# Measure recovery time
START=$(date +%s%N)
RECOVERED=false
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    END=$(date +%s%N)
    RECOVERY_MS=$(( (END - START) / 1000000 ))
    RECOVERED=true
    break
  fi
  sleep 1
done

if $RECOVERED; then
  if [ "$RECOVERY_MS" -le 30000 ]; then
    check_pass "Failover recovery: ${RECOVERY_MS}ms (<30s target)"
  else
    check_fail "Failover recovery: ${RECOVERY_MS}ms (>30s target)"
  fi
else
  check_fail "Failover recovery: did not recover within 30s"
fi

# Cleanup
echo "  Cleaning up HA stack..."
cd "$PROJECT_ROOT" && docker compose -f "$HA_COMPOSE" down 2>/dev/null || true

echo ""
echo "  Passed: $PASS_COUNT  Failed: $FAIL_COUNT"
echo ""
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "HA validation: PASS"
  exit 0
else
  echo "HA validation: FAIL"
  exit 1
fi
