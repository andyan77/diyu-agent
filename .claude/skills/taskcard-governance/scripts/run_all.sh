#!/usr/bin/env bash
# Run all taskcard-governance workflows in sequence: W1 -> W2 -> W3 -> W4
# Each step produces handoff artifacts; stops on first failure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SESSION_ID="${SESSION_ID:-$(date +%Y%m%dT%H%M%S)}"

echo "=== Task Card Governance: Full Run ==="
echo "Session: $SESSION_ID"
echo ""

STEPS=("run_w1_schema_normalization.sh" "run_w2_traceability_link.sh" "run_w3_acceptance_normalizer.sh" "run_w4_evidence_gate.sh")
LABELS=("W1: Schema Normalization" "W2: Traceability Link" "W3: Acceptance Normalizer" "W4: Evidence Gate")
STEP_IDS=("W1" "W2" "W3" "W4")
LOGGER="uv run python scripts/skills/skill_session_logger.py"

PASSED=0
for i in "${!STEPS[@]}"; do
  echo "--- ${LABELS[$i]} ---"
  ARTIFACTS="evidence/skills/taskcard-governance/$SESSION_ID/${STEP_IDS[$i]}"
  # GAP-M2: pass WORKFLOW_ROLE per step to enforce role isolation
  if WORKFLOW_ROLE="${STEP_IDS[$i]}" bash "$SCRIPT_DIR/${STEPS[$i]}"; then
    PASSED=$((PASSED + 1))
    $LOGGER --skill taskcard-governance --step "${STEP_IDS[$i]}" --status pass --artifacts "$ARTIFACTS"
    echo "  -> PASS"
  else
    $LOGGER --skill taskcard-governance --step "${STEP_IDS[$i]}" --status fail --artifacts "$ARTIFACTS"
    echo "  -> FAIL (stopping)"
    echo ""
    echo "Session artifacts: evidence/skills/taskcard-governance/$SESSION_ID/"
    echo "Passed: $PASSED / ${#STEPS[@]}"
    exit 1
  fi
  echo ""
done

echo "=== All workflows passed ==="
echo "Session artifacts: evidence/skills/taskcard-governance/$SESSION_ID/"
echo "Session log: .audit/skill-session-$SESSION_ID.jsonl"
echo "Passed: $PASSED / ${#STEPS[@]}"
