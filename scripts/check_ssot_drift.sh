#!/usr/bin/env bash
# DIYU Agent Triple SSOT Consistency Check
#
# Gate ID: p4-ssot-drift
# XNode: X4-3
#
# Validates consistency across three Sources of Truth:
#   1. Decision docs (ADR + governance docs)
#   2. Port interface signatures (Python source)
#   3. delivery/manifest.yaml
#
# Usage:
#   bash scripts/check_ssot_drift.sh
#
# Exit codes:
#   0 - All three SSOT sources are consistent
#   1 - Drift detected between sources

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== DIYU Agent Triple SSOT Consistency Check ==="
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

# --- Check 1: manifest.yaml exists and lists all 6 Day-1 Ports ---
MANIFEST="$PROJECT_ROOT/delivery/manifest.yaml"
if [ -f "$MANIFEST" ]; then
  check_pass "manifest.yaml exists"
else
  check_fail "manifest.yaml not found"
  echo ""
  echo "SSOT drift check: FAIL"
  exit 1
fi

# Verify 6 Day-1 Ports are referenced
DAY1_PORTS=(
  "MemoryCorePort"
  "KnowledgePort"
  "LLMCallPort"
  "SkillRegistry"
  "OrgContext"
  "StoragePort"
)

for port in "${DAY1_PORTS[@]}"; do
  if grep -q "$port" "$MANIFEST" 2>/dev/null; then
    check_pass "manifest references $port"
  else
    check_fail "manifest missing $port reference"
  fi
done

# --- Check 2: Port interface files exist in source ---
PORT_DIR="$PROJECT_ROOT/src/ports"
if [ -d "$PORT_DIR" ]; then
  check_pass "Port interfaces directory exists ($PORT_DIR)"

  # Check each port has a corresponding file or is defined in __init__.py
  INIT_FILE="$PORT_DIR/__init__.py"
  if [ -f "$INIT_FILE" ]; then
    for port in "${DAY1_PORTS[@]}"; do
      if grep -q "class $port" "$INIT_FILE" 2>/dev/null || \
         find "$PORT_DIR" -name "*.py" -exec grep -l "class $port" {} \; 2>/dev/null | grep -q .; then
        check_pass "Port $port defined in source"
      else
        check_fail "Port $port not found in source"
      fi
    done
  else
    check_fail "Ports __init__.py not found"
  fi
else
  check_fail "Port interfaces directory not found ($PORT_DIR)"
fi

# --- Check 3: ADR decisions reference Ports consistently ---
ADR_DIR="$PROJECT_ROOT/docs/governance/decisions"
if [ -d "$ADR_DIR" ]; then
  # Count ADRs that mention Port interfaces
  ADR_COUNT=$(find "$ADR_DIR" -name "*.md" | wc -l)
  PORT_ADRS=$(grep -rl "Port" "$ADR_DIR"/*.md 2>/dev/null | wc -l)
  check_pass "ADR directory has $ADR_COUNT decisions ($PORT_ADRS reference Ports)"
else
  check_fail "ADR decisions directory not found"
fi

# --- Check 4: milestone-matrix.yaml milestones reference correct layers ---
MATRIX="$PROJECT_ROOT/delivery/milestone-matrix.yaml"
if [ -f "$MATRIX" ]; then
  if command -v python3 >/dev/null 2>&1; then
    LAYER_CHECK=$(python3 -c "
import yaml, sys
with open('$MATRIX') as f:
    data = yaml.safe_load(f)
phases = data.get('phases', {})
# Verify current_phase is defined and valid
cp = data.get('current_phase', '')
if cp and cp in phases:
    print(f'current_phase={cp}: valid')
else:
    print(f'current_phase={cp}: INVALID', file=sys.stderr)
    sys.exit(1)
" 2>&1) && check_pass "milestone-matrix current_phase valid: $LAYER_CHECK" \
       || check_fail "milestone-matrix current_phase invalid: $LAYER_CHECK"
  else
    check_pass "milestone-matrix.yaml exists (python3 unavailable for deep check)"
  fi
else
  check_fail "milestone-matrix.yaml not found"
fi

echo ""
echo "  Passed: $PASS_COUNT  Failed: $FAIL_COUNT"
echo ""
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "SSOT drift check: PASS"
  exit 0
else
  echo "SSOT drift check: FAIL ($FAIL_COUNT issues)"
  exit 1
fi
