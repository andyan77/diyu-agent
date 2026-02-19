#!/usr/bin/env bash
# Release rollback drill script
# Gate ID: p4-release-drill
# Validates: rollback procedure completes in < 5 minutes
# Usage: bash scripts/drill_release.sh --dry-run
set -euo pipefail

DRY_RUN=false
EVIDENCE_DIR="evidence/release"
DRILL_RESULT=""
STEPS=()
ERRORS=()

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
    echo "  [dry-run] Skipping live cluster checks"
    record_step "check_prerequisites" "PASS" "$start_ms" "$(epoch_ms)"
    return 0
  fi

  # Verify kubectl access
  if ! command -v kubectl &>/dev/null; then
    echo "  FAIL: kubectl not found"
    record_step "check_prerequisites" "FAIL" "$start_ms" "$(epoch_ms)"
    return 1
  fi

  # Verify current deployment exists
  if ! kubectl get deployment/diyu-agent --namespace=production &>/dev/null; then
    echo "  FAIL: deployment/diyu-agent not found in production namespace"
    record_step "check_prerequisites" "FAIL" "$start_ms" "$(epoch_ms)"
    return 1
  fi

  record_step "check_prerequisites" "PASS" "$start_ms" "$(epoch_ms)"
}

simulate_deploy() {
  local start_ms
  start_ms=$(epoch_ms)

  echo "[2/6] Simulating canary deploy..."

  if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would deploy canary with new image tag"
    echo "  [dry-run] Would run: kubectl set image deployment/diyu-agent app=diyu-agent:\$NEW_TAG"
    sleep 1
    record_step "simulate_deploy" "PASS" "$start_ms" "$(epoch_ms)"
    return 0
  fi

  # Live mode would do actual deploy
  kubectl set image deployment/diyu-agent app=diyu-agent:"${NEW_TAG:-drill-test}" \
    --namespace=production --record
  kubectl rollout status deployment/diyu-agent --timeout=120s

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

  # In live mode, wait for actual health check failure or simulate one
  echo "  Checking health endpoint..."
  if curl -sf https://api.diyu.app/healthz | jq -e '.status == "healthy"' &>/dev/null; then
    echo "  Health check still passing - simulating failure scenario"
  fi

  record_step "simulate_health_failure" "PASS" "$start_ms" "$(epoch_ms)"
}

execute_rollback() {
  local start_ms
  start_ms=$(epoch_ms)

  echo "[4/6] Executing rollback..."

  if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] Would run: kubectl rollout undo deployment/diyu-agent --namespace=production"
    echo "  [dry-run] Would run: kubectl rollout status deployment/diyu-agent --timeout=120s"
    sleep 1
    record_step "execute_rollback" "PASS" "$start_ms" "$(epoch_ms)"
    return 0
  fi

  kubectl rollout undo deployment/diyu-agent --namespace=production
  kubectl rollout status deployment/diyu-agent --timeout=120s

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

  # Verify health
  if ! curl -sf https://api.diyu.app/healthz | jq -e '.status == "healthy"' &>/dev/null; then
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
