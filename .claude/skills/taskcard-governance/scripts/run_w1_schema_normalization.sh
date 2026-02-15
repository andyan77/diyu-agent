#!/usr/bin/env bash
# W1: Schema Normalization - validate task cards against schema v1.0
# Produces session-level handoff artifacts in evidence/skills/taskcard-governance/
set -euo pipefail

SESSION_ID="${SESSION_ID:-$(date +%Y%m%dT%H%M%S)}"
WORKFLOW_ROLE="${WORKFLOW_ROLE:-W1}"
OUT_DIR="evidence/skills/taskcard-governance/${SESSION_ID}/W1"
mkdir -p "$OUT_DIR"

# Trap: ensure output.json exists even on unexpected failure
_w1_cleanup() {
  local exit_code=$?
  if [ ! -f "$OUT_DIR/output.json" ]; then
    cat > "$OUT_DIR/output.json" <<TRAPEOF
{"status": "FAIL", "error": "W1 script crashed before producing output", "session_id": "$SESSION_ID"}
TRAPEOF
  fi
  if [ ! -f "$OUT_DIR/failure.md" ] && [ $exit_code -ne 0 ]; then
    cat > "$OUT_DIR/failure.md" <<TRAPFAIL
# W1 Failure Report
- Session: $SESSION_ID
- Reason: Unexpected exit (code $exit_code)
TRAPFAIL
  fi
}
trap _w1_cleanup EXIT

# GAP-M2: Role enforcement via enforce_workflow_role.py (auditable, structured logging)
if ! python3 scripts/enforce_workflow_role.py \
    --expected W1 --actual "$WORKFLOW_ROLE" \
    --session "$SESSION_ID" --log-dir "$OUT_DIR"; then
  echo "FATAL: WORKFLOW_ROLE=$WORKFLOW_ROLE but this is W1. Aborting." >&2
  cat > "$OUT_DIR/failure.md" <<FEOF
# W1 Failure Report
- Session: $SESSION_ID
- Reason: Role mismatch (expected W1, got $WORKFLOW_ROLE)
FEOF
  exit 1
fi

# Record input
cat > "$OUT_DIR/input.json" <<INPUTEOF
{
  "workflow": "W1",
  "session_id": "$SESSION_ID",
  "scope": "docs/task-cards/**/*.md",
  "authority": "docs/governance/task-card-schema-v1.0.md",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
INPUTEOF

# Execute real validation
RESULT_FILE="$OUT_DIR/output.json"
if uv run python scripts/check_task_schema.py --mode full --json > "$RESULT_FILE" 2>"$OUT_DIR/stderr.log"; then
  STATUS="pass"
else
  STATUS="fail"
fi

# Extract summary
BLOCKS=$(uv run python -c "import json,sys; d=json.load(open('$RESULT_FILE')); print(d.get('summary',{}).get('block',0))" 2>/dev/null || echo "?")
TOTAL=$(uv run python -c "import json,sys; d=json.load(open('$RESULT_FILE')); print(d.get('total_cards',0))" 2>/dev/null || echo "?")

# Write next-step
cat > "$OUT_DIR/next-step.md" <<NSEOF
# W1 Next Steps

- Status: $STATUS
- BLOCK violations: $BLOCKS
- Total cards scanned: $TOTAL

## If BLOCK > 0
1. Fix each BLOCK violation listed in output.json
2. Re-run: \`bash .claude/skills/taskcard-governance/scripts/run_w1_schema_normalization.sh\`

## If BLOCK = 0
Proceed to W2: \`bash .claude/skills/taskcard-governance/scripts/run_w2_traceability_link.sh\`
NSEOF

# Write failure report only if failed
if [ "$STATUS" = "fail" ]; then
  cat > "$OUT_DIR/failure.md" <<FEOF
# W1 Failure Report

- Session: $SESSION_ID
- BLOCK violations: $BLOCKS
- Details: See output.json for full violation list
- Stderr: See stderr.log

## Required Actions
Fix all BLOCK violations before proceeding to W2.
FEOF
fi

echo "W1 complete: status=$STATUS blocks=$BLOCKS cards=$TOTAL"
echo "Artifacts: $OUT_DIR/"
exit $( [ "$STATUS" = "pass" ] && echo 0 || echo 1 )
