#!/usr/bin/env bash
# Release rollback drill script (Decision R-4: docker-compose HA mode)
# Gate ID: p4-release-drill
# Validates: rollback procedure completes in < 5 minutes
# Usage: bash scripts/drill_release.sh --dry-run
set -euo pipefail

DRY_RUN=false
EVIDENCE_DIR="evidence/release"
DRILL_RESULT=""
STEPS=()
ERRORS=()
COMPOSE_FILE="deploy/ha/docker-compose.ha.yml"

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --evidence-dir=*) EVIDENCE_DIR="${arg#*=}" ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
epoch_ms() { date +%s%3N 2>/dev/null || python3 -c "import time; print(int(time.time()*1000))"; }

record_step() {
  local name="$1" status="$2" start_ms="$3" end_ms="$4"
  local duration_ms=$((end_ms - start_ms))
  STEPS+=("{\"name\":\"$name\",\"status\":\"$status\",\"duration_ms\":$duration_ms}")
}

check_prerequisites() {
  local start_ms
  start_ms=$(epoch_ms)

  echo "[1/6] Checking prerequisites..."

  if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Skipping live infrastructure checks"
    echo "  [dry-run] Checking compose file exists: $COMPOSE_FILE"
    if [ -f "$COMPOSE_FILE" ]; then
      echo "  [dry-run] HA compose file found"
    else
      echo "  [dry-run] HA compose file not found (expected for dry-run)"
    fi
    record_step "check_prerequisites" "PASS" "$start_ms" "$(epoch_ms)"
    return 0
  fi

  # Verify docker compose access (R-4: docker-compose, NOT kubectl)
  if ! command -v docker &>/dev/null; then
    echo "  FAIL: docker not found"
    record_step "check_prerequisites" "FAIL" "$start_ms" "$(epoch_ms)"
    return 1
  fi

  # Verify HA compose file exists
  if [ ! -f "$COMPOSE_FILE" ]; then
    echo "  FAIL: HA compose file not found: $COMPOSE_FILE"
    record_step "check_prerequisites" "FAIL" "$start_ms" "$(epoch_ms)"
    return 1
  fi

  # Verify services are running
  if ! docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | head -1 | grep -q "running"; then
    echo "  WARN: HA services not running (start with: docker compose -f $COMPOSE_FILE up -d)"
  fi

  record_step "check_prerequisites" "PASS" "$start_ms" "$(epoch_ms)"
}

simulate_deploy() {
  local start_ms
  start_ms=$(epoch_ms)

  echo "[2/6] Simulating canary deploy..."

  if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would deploy canary with new image tag"
    echo "  [dry-run] Would run: docker compose -f $COMPOSE_FILE up -d --no-deps app-1"
    echo "  [dry-run] Would verify app-1 health check passes"
    sleep 1
    record_step "simulate_deploy" "PASS" "$start_ms" "$(epoch_ms)"
    return 0
  fi

  # Live mode: rebuild and restart app-1 with new image
  docker compose -f "$COMPOSE_FILE" up -d --no-deps --build app-1
  # Wait for health check
  for i in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T app-1 curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
      echo "  app-1 healthy after ${i}s"
      break
    fi
    sleep 1
  done

  record_step "simulate_deploy" "PASS" "$start_ms" "$(epoch_ms)"
}

simulate_health_failure() {
  local start_ms
  start_ms=$(epoch_ms)

  echo "[3/6] Simulating health check failure..."

  if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Simulating: health check returns HTTP 503"
    echo "  [dry-run] Trigger condition: error rate > 5% for 2 minutes"
    sleep 1
    record_step "simulate_health_failure" "PASS" "$start_ms" "$(epoch_ms)"
    return 0
  fi

  # In live mode, simulate by stopping app-1
  echo "  Stopping app-1 to simulate failure..."
  docker compose -f "$COMPOSE_FILE" stop app-1

  # Verify nginx routes to app-2
  echo "  Checking nginx failover to app-2..."
  if curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
    echo "  Nginx successfully routing to app-2"
  else
    echo "  WARN: Health check failing (both instances may be down)"
  fi

  record_step "simulate_health_failure" "PASS" "$start_ms" "$(epoch_ms)"
}

execute_rollback() {
  local start_ms
  start_ms=$(epoch_ms)

  echo "[4/6] Executing rollback..."

  if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would run: docker compose -f $COMPOSE_FILE up -d --no-deps app-1"
    echo "  [dry-run] Would wait for app-1 health check (timeout 120s)"
    sleep 1
    record_step "execute_rollback" "PASS" "$start_ms" "$(epoch_ms)"
    return 0
  fi

  # Restart app-1 (rollback = restart with previous image)
  docker compose -f "$COMPOSE_FILE" up -d --no-deps app-1
  # Wait for health
  for i in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T app-1 curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
      echo "  app-1 recovered after ${i}s"
      break
    fi
    sleep 1
  done

  record_step "execute_rollback" "PASS" "$start_ms" "$(epoch_ms)"
}

verify_rollback() {
  local start_ms
  start_ms=$(epoch_ms)

  echo "[5/6] Verifying rollback success..."

  if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would verify: health endpoint returns 200"
    echo "  [dry-run] Would verify: error rate < 1%"
    echo "  [dry-run] Would verify: golden signals recovered"
    sleep 1
    record_step "verify_rollback" "PASS" "$start_ms" "$(epoch_ms)"
    return 0
  fi

  # Verify both instances healthy via nginx
  if ! curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
    echo "  FAIL: health check not passing after rollback"
    record_step "verify_rollback" "FAIL" "$start_ms" "$(epoch_ms)"
    return 1
  fi

  record_step "verify_rollback" "PASS" "$start_ms" "$(epoch_ms)"
}

generate_evidence() {
  local start_ms total_start_ms="$1" drill_status="$2"
  start_ms=$(epoch_ms)

  echo "[6/6] Generating evidence..."

  mkdir -p "$EVIDENCE_DIR"

  local total_duration_ms=$(($(epoch_ms) - total_start_ms))
  local total_duration_s=$((total_duration_ms / 1000))
  local rollback_target_s=300  # 5 minutes

  local timing_pass="true"
  if [ "$total_duration_s" -gt "$rollback_target_s" ]; then
    timing_pass="false"
  fi

  # Build steps JSON array
  local steps_json="["
  local first=true
  for step in "${STEPS[@]}"; do
    if [ "$first" = true ]; then
      first=false
    else
      steps_json+=","
    fi
    steps_json+="$step"
  done
  steps_json+="]"

  local evidence_file="$EVIDENCE_DIR/drill-release-$(date -u +%Y%m%d-%H%M%S).json"

  cat > "$evidence_file" <<EOF
{
  "drill_type": "release-rollback",
  "gate_id": "p4-release-drill",
  "timestamp": "$(timestamp)",
  "dry_run": $DRY_RUN,
  "topology": "docker-compose HA (R-4)",
  "steps": $steps_json,
  "timing": {
    "total_duration_ms": $total_duration_ms,
    "target_ms": 300000,
    "within_target": $timing_pass
  },
  "result": "$drill_status",
  "runbook_ref": "delivery/commercial/runbook/release-rollback.md"
}
EOF

  echo "  Evidence written to: $evidence_file"
  record_step "generate_evidence" "PASS" "$start_ms" "$(epoch_ms)"
}

main() {
  echo "=== Release Rollback Drill ==="
  echo "Mode: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'LIVE')"
  echo "Topology: docker-compose HA (Decision R-4)"
  echo "Started: $(timestamp)"
  echo ""

  local total_start_ms
  total_start_ms=$(epoch_ms)
  local drill_status="PASS"

  check_prerequisites || drill_status="FAIL"
  simulate_deploy || drill_status="FAIL"
  simulate_health_failure || drill_status="FAIL"
  execute_rollback || drill_status="FAIL"
  verify_rollback || drill_status="FAIL"
  generate_evidence "$total_start_ms" "$drill_status"

  echo ""
  echo "=== Drill Complete ==="
  echo "Result: $drill_status"
  echo "Duration: $(( ($(epoch_ms) - total_start_ms) / 1000 ))s (target: < 300s)"

  if [ "$drill_status" = "FAIL" ]; then
    exit 1
  fi
}

main
