#!/usr/bin/env bash
# W2: Traceability Link Check - verify L1->L2->L3 bidirectional links
# Produces session-level handoff artifacts in evidence/skills/taskcard-governance/
#
# GAP-H2 fix: default to task_card_traceability_check.py --threshold 98 --json.
# grep-fallback is forbidden in default mode; if json-parser fails, status=fail.
set -euo pipefail

SESSION_ID="${SESSION_ID:-$(date +%Y%m%dT%H%M%S)}"
WORKFLOW_ROLE="${WORKFLOW_ROLE:-W2}"
OUT_DIR="evidence/skills/taskcard-governance/${SESSION_ID}/W2"
mkdir -p "$OUT_DIR"

# Trap: ensure output.json exists even on unexpected failure
_w2_cleanup() {
  local exit_code=$?
  if [ ! -f "$OUT_DIR/output.json" ]; then
    cat > "$OUT_DIR/output.json" <<TRAPEOF
{"status": "FAIL", "error": "W2 script crashed before producing output", "session_id": "$SESSION_ID"}
TRAPEOF
  fi
  if [ ! -f "$OUT_DIR/failure.md" ] && [ $exit_code -ne 0 ]; then
    cat > "$OUT_DIR/failure.md" <<TRAPFAIL
# W2 Failure Report
- Session: $SESSION_ID
- Reason: Unexpected exit (code $exit_code)
TRAPFAIL
  fi
}
trap _w2_cleanup EXIT

# Role enforcement (GAP-M2) via enforce_workflow_role.py (auditable, structured logging)
if ! python3 scripts/enforce_workflow_role.py \
    --expected W2 --actual "$WORKFLOW_ROLE" \
    --session "$SESSION_ID" --log-dir "$OUT_DIR"; then
  echo "FATAL: WORKFLOW_ROLE=$WORKFLOW_ROLE but this is W2. Aborting." >&2
  cat > "$OUT_DIR/failure.md" <<FEOF
# W2 Failure Report
- Session: $SESSION_ID
- Reason: Role mismatch (expected W2, got $WORKFLOW_ROLE)
FEOF
  exit 1
fi

# Record input
cat > "$OUT_DIR/input.json" <<INPUTEOF
{
  "workflow": "W2",
  "session_id": "$SESSION_ID",
  "role": "$WORKFLOW_ROLE",
  "scope": "docs/task-cards/ + docs/governance/milestone-matrix*.md",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
INPUTEOF

RESULT_FILE="$OUT_DIR/output.json"
STATUS="pass"
METHOD="json-parser"

# Execute real traceability check -- json-parser is the ONLY valid method
TRACE_OUTPUT=$(uv run python scripts/task_card_traceability_check.py --threshold 98 --json 2>"$OUT_DIR/stderr.log") || true

# Validate output is parseable JSON
if echo "$TRACE_OUTPUT" | uv run python -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
  # Valid JSON -- write result with method tag
  uv run python -c "
import json, sys
data = json.loads(sys.stdin.read())
data['method'] = 'json-parser'
json.dump(data, open('$RESULT_FILE', 'w'), indent=2, ensure_ascii=False)
trace_status = data.get('status', 'FAIL')
print(f'Traceability: {trace_status}', file=sys.stderr)
sys.exit(0 if trace_status == 'PASS' else 1)
" <<< "$TRACE_OUTPUT" 2>"$OUT_DIR/trace_status.log" || STATUS="fail"
else
  # JSON parse failed -- this is a HARD FAIL, no grep fallback
  STATUS="fail"
  METHOD="fallback-failed"
  cat > "$RESULT_FILE" <<ERREOF
{
  "status": "FAIL",
  "method": "fallback-failed",
  "error": "task_card_traceability_check.py did not produce valid JSON",
  "stderr": $(uv run python -c "import json; print(json.dumps(open('$OUT_DIR/stderr.log').read()[:500]))" 2>/dev/null || echo '"unknown"')
}
ERREOF

  # Write mandatory failure.md for fallback-failed
  cat > "$OUT_DIR/failure.md" <<FEOF
# W2 Failure Report

- Session: $SESSION_ID
- Method: fallback-failed
- Reason: task_card_traceability_check.py did not produce valid JSON output
- Stderr: See stderr.log

## Required Actions
1. Fix scripts/task_card_traceability_check.py to produce valid JSON
2. Re-run: \`bash .claude/skills/taskcard-governance/scripts/run_w2_traceability_link.sh\`

## Note
grep-based fallback is FORBIDDEN per GAP-H2. The json-parser is the only valid method.
FEOF
fi

# Write next-step (always)
cat > "$OUT_DIR/next-step.md" <<NSEOF
# W2 Next Steps

- Status: $STATUS
- Method: $METHOD

## If fail
1. Check stderr.log for error details
2. Check output.json for traceability gaps
3. If method=fallback-failed: fix the traceability script first
4. Re-run: \`bash .claude/skills/taskcard-governance/scripts/run_w2_traceability_link.sh\`

## If pass
Proceed to W3: \`bash .claude/skills/taskcard-governance/scripts/run_w3_acceptance_normalizer.sh\`
NSEOF

# Write failure.md for non-fallback failures
if [ "$STATUS" = "fail" ] && [ "$METHOD" = "json-parser" ]; then
  cat > "$OUT_DIR/failure.md" <<FEOF
# W2 Failure Report

- Session: $SESSION_ID
- Method: json-parser
- Details: See output.json for traceability gaps

## Required Actions
1. Add missing \`> 矩阵条目:\` references to orphan cards
2. Add task cards for uncovered matrix entries
3. Re-run: \`bash .claude/skills/taskcard-governance/scripts/run_w2_traceability_link.sh\`
FEOF
fi

echo "W2 complete: status=$STATUS method=$METHOD"
echo "Artifacts: $OUT_DIR/"
exit $( [ "$STATUS" = "pass" ] && echo 0 || echo 1 )
