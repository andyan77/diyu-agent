#!/usr/bin/env bash
# full_audit.sh - Unified audit entry point (Section 12.6)
#
# Runs all 14 audit categories:
#   1. Guards: check_layer_deps, check_port_compat, check_rls
#   2. Skill audits: run_systematic_review, run_cross_audit, run_fix_verify
#   3. Agent tests: test_agent_permissions
#   4. Hook tests: test_hook_behavior
#   5. Workflow tests: test_workflow_completeness
#   6. Governance: test_governance_consistency
#   7. Security: security_scan --full
#   8. Phase gate: verify_phase --current
#   9. Cross-validation: check_cross_validation (8-category diagnostic)
#  10. Promise Registry: check_promise_registry
#  11. ADR Consistency: check_adr_consistency
#  12. Contract Alignment: check_contract_alignment (6-type)
#  13. Evidence Grading: check_evidence_grade (A-F)
#  14. Temporal Integrity: check_temporal_integrity (migration chain)
#
# Exit codes: 0 = all pass, 1 = failures found, 2 = critical error
#
# Usage:
#   bash scripts/full_audit.sh              # Run full audit
#   bash scripts/full_audit.sh --json       # JSON report only
#   bash scripts/full_audit.sh --phase N    # Set phase context

set -euo pipefail

PHASE="${PHASE:-0}"
JSON_OUTPUT=false
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EVIDENCE_DIR="evidence"
REPORT_FILE="${EVIDENCE_DIR}/full-audit-${TIMESTAMP//[:.]/-}.json"

while [ $# -gt 0 ]; do
  case "$1" in
    --json)      JSON_OUTPUT=true ;;
    --phase)     shift; PHASE="${1:-0}" ;;
    --phase=*)   PHASE="${1#--phase=}" ;;
  esac
  shift
done

mkdir -p "$EVIDENCE_DIR"

TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0
RESULTS="{}"

run_check() {
  local name="$1"
  local category="$2"
  local cmd="$3"
  TOTAL=$((TOTAL + 1))

  if [ "$JSON_OUTPUT" = false ]; then
    echo "--- [$category] $name ---"
  fi

  local output=""
  local status="pass"
  if output=$(eval "$cmd" 2>&1); then
    PASSED=$((PASSED + 1))
    status="pass"
  else
    local exit_code=$?
    if [ $exit_code -eq 5 ]; then
      SKIPPED=$((SKIPPED + 1))
      status="skip"
    else
      FAILED=$((FAILED + 1))
      status="fail"
    fi
  fi

  if [ "$JSON_OUTPUT" = false ]; then
    echo "  Result: $status"
  fi

  # Append to results JSON
  RESULTS=$(python3 -c "
import json, sys
r = json.loads(sys.argv[1])
cat = r.get(sys.argv[2], {})
cat[sys.argv[3]] = {'status': sys.argv[4]}
r[sys.argv[2]] = cat
print(json.dumps(r))
" "$RESULTS" "$category" "$name" "$status" 2>/dev/null || echo "$RESULTS")
}

# ============================================================
# 1. Guard scripts
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo "=== Phase 1: Guard Scripts ==="
fi
run_check "check_layer_deps" "guards" "bash scripts/check_layer_deps.sh --json"
run_check "check_port_compat" "guards" "bash scripts/check_port_compat.sh --json"
run_check "check_rls" "guards" "bash scripts/check_rls.sh --json"

# ============================================================
# 2. Skill audit scripts
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 2: Skill Audits ==="
fi
run_check "run_systematic_review" "skills" "bash scripts/run_systematic_review.sh 2>&1"
run_check "run_cross_audit" "skills" "bash scripts/run_cross_audit.sh 2>&1"
run_check "run_fix_verify" "skills" "bash scripts/run_fix_verify.sh 2>&1"

# ============================================================
# 3. Agent tests
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 3: Agent Tests ==="
fi
run_check "test_agent_permissions" "agents" "uv run pytest tests/unit/scripts/ -k 'agent' --tb=short -q 2>&1"

# ============================================================
# 4. Hook tests
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 4: Hook Tests ==="
fi
run_check "test_hook_behavior" "hooks" "uv run pytest tests/unit/scripts/test_hook_behavior.py --tb=short -q"

# ============================================================
# 5. Workflow tests
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 5: Workflow Tests ==="
fi
run_check "test_workflow_completeness" "workflows" "uv run pytest tests/unit/scripts/test_workflow_completeness.py --tb=short -q"

# ============================================================
# 6. Governance consistency
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 6: Governance ==="
fi
run_check "test_governance_consistency" "governance" "uv run pytest tests/unit/scripts/test_governance_consistency.py --tb=short -q"

# ============================================================
# 7. Security scanning
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 7: Security ==="
fi
run_check "security_scan" "security" "bash scripts/security_scan.sh --full"

# ============================================================
# 8. Phase gate status
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 8: Phase Gate Status ==="
fi
run_check "verify_phase_gate" "phase_gate" "uv run python scripts/verify_phase.py --phase $PHASE --json 2>&1"

# ============================================================
# 9. Cross-validation diagnostic
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 9: Cross-Validation ==="
fi
run_check "cross_validation" "cross_validation" "uv run python scripts/check_cross_validation.py --skip-execution --json 2>&1"

# ============================================================
# 10. Promise Registry
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 10: Promise Registry ==="
fi
run_check "promise_registry" "promise_registry" "uv run python scripts/check_promise_registry.py --json 2>&1"

# ============================================================
# 11. ADR Consistency
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 11: ADR Consistency ==="
fi
run_check "adr_consistency" "adr_consistency" "uv run python scripts/check_adr_consistency.py --json 2>&1"

# ============================================================
# 12. Contract Alignment
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 12: Contract Alignment ==="
fi
run_check "contract_alignment" "contract_alignment" "uv run python scripts/check_contract_alignment.py --json 2>&1"

# ============================================================
# 13. Evidence Grading
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 13: Evidence Grading ==="
fi
run_check "evidence_grade" "evidence_grade" "uv run python scripts/check_evidence_grade.py --json 2>&1"

# ============================================================
# 14. Temporal Integrity
# ============================================================
if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Phase 14: Temporal Integrity ==="
fi
run_check "temporal_integrity" "temporal_integrity" "uv run python scripts/check_temporal_integrity.py --json 2>&1"

# ============================================================
# Report aggregation
# ============================================================
OVERALL="pass"
if [ "$FAILED" -gt 0 ]; then
  OVERALL="fail"
elif [ "$SKIPPED" -gt 0 ]; then
  OVERALL="partial"
fi

python3 -c "
import json, sys
report = {
    'timestamp': sys.argv[1],
    'phase': int(sys.argv[2]),
    'results': json.loads(sys.argv[3]),
    'summary': {
        'total_categories': 14,
        'total_sub_checks': int(sys.argv[4]),
        'passed': int(sys.argv[5]),
        'failed': int(sys.argv[6]),
        'skipped': int(sys.argv[7])
    },
    'status': sys.argv[8]
}
with open(sys.argv[9], 'w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
if sys.argv[10] == 'true':
    print(json.dumps(report, indent=2, ensure_ascii=False))
else:
    print(f'Report written to: {sys.argv[9]}')
" "$TIMESTAMP" "$PHASE" "$RESULTS" "$TOTAL" "$PASSED" "$FAILED" "$SKIPPED" "$OVERALL" "$REPORT_FILE" "$JSON_OUTPUT"

if [ "$JSON_OUTPUT" = false ]; then
  echo ""
  echo "=== Summary ==="
  echo "  Total: $TOTAL | Passed: $PASSED | Failed: $FAILED | Skipped: $SKIPPED"
  echo "  Status: $OVERALL"
  echo "  Report: $REPORT_FILE"
fi

exit $( [ "$FAILED" -eq 0 ] && echo 0 || echo 1 )
