#!/usr/bin/env bash
# W3: Acceptance Normalizer - ensure acceptance commands are executable or tagged
# Produces session-level handoff artifacts in evidence/skills/taskcard-governance/
set -euo pipefail

SESSION_ID="${SESSION_ID:-$(date +%Y%m%dT%H%M%S)}"
WORKFLOW_ROLE="${WORKFLOW_ROLE:-W3}"
OUT_DIR="evidence/skills/taskcard-governance/${SESSION_ID}/W3"
mkdir -p "$OUT_DIR"

# Trap: ensure output.json exists even on unexpected failure
_w3_cleanup() {
  local exit_code=$?
  if [ ! -f "$OUT_DIR/output.json" ]; then
    cat > "$OUT_DIR/output.json" <<TRAPEOF
{"status": "FAIL", "error": "W3 script crashed before producing output", "session_id": "$SESSION_ID"}
TRAPEOF
  fi
  if [ ! -f "$OUT_DIR/failure.md" ] && [ $exit_code -ne 0 ]; then
    cat > "$OUT_DIR/failure.md" <<TRAPFAIL
# W3 Failure Report
- Session: $SESSION_ID
- Reason: Unexpected exit (code $exit_code)
TRAPFAIL
  fi
}
trap _w3_cleanup EXIT

# GAP-M2: Role enforcement via enforce_workflow_role.py (auditable, structured logging)
if ! python3 scripts/enforce_workflow_role.py \
    --expected W3 --actual "$WORKFLOW_ROLE" \
    --session "$SESSION_ID" --log-dir "$OUT_DIR"; then
  echo "FATAL: WORKFLOW_ROLE=$WORKFLOW_ROLE but this is W3. Aborting." >&2
  cat > "$OUT_DIR/failure.md" <<FEOF
# W3 Failure Report
- Session: $SESSION_ID
- Reason: Role mismatch (expected W3, got $WORKFLOW_ROLE)
FEOF
  exit 1
fi

# Record input
cat > "$OUT_DIR/input.json" <<INPUTEOF
{
  "workflow": "W3",
  "session_id": "$SESSION_ID",
  "scope": "docs/task-cards/**/*.md (acceptance commands only)",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
INPUTEOF

# Execute: run both schema validation and acceptance gate
RESULT_FILE="$OUT_DIR/output.json"
FULL_RESULT_FILE="$OUT_DIR/full_schema_result.json"
GATE_RESULT_FILE="$OUT_DIR/acceptance_gate_result.json"

uv run python scripts/check_task_schema.py --mode full --json > "$FULL_RESULT_FILE" 2>/dev/null || echo '{"violations":[]}' > "$FULL_RESULT_FILE"
uv run python scripts/check_acceptance_gate.py --json > "$GATE_RESULT_FILE" 2>/dev/null || echo '{"violations":[]}' > "$GATE_RESULT_FILE"

# Merge violations from both checkers (schema + acceptance gate)
uv run python -c "
import json, sys
with open('$FULL_RESULT_FILE') as f:
    schema_data = json.load(f)
with open('$GATE_RESULT_FILE') as f:
    gate_data = json.load(f)
schema_rules = ['acceptance-not-executable', 'acceptance-empty', 'manual-verify-no-alt']
schema_violations = [v for v in schema_data.get('violations', []) if v.get('rule') in schema_rules]
gate_violations = gate_data.get('violations', [])
# Deduplicate: gate violations for env-dep-no-mapping take precedence
seen = set()
merged = []
for v in gate_violations:
    key = (v.get('card_id',''), v.get('rule',''))
    if key not in seen:
        seen.add(key)
        merged.append(v)
for v in schema_violations:
    key = (v.get('card_id',''), v.get('rule',''))
    if key not in seen:
        seen.add(key)
        merged.append(v)
result = {
    'total_violations': len(merged),
    'violations': merged,
    'sources': {'schema_check': len(schema_violations), 'acceptance_gate': len(gate_violations)},
    'status': 'pass' if len(merged) == 0 else 'fail'
}
json.dump(result, open('$RESULT_FILE', 'w'), indent=2, ensure_ascii=False)
print(json.dumps({'status': result['status'], 'count': len(merged)}))
" 2>"$OUT_DIR/stderr.log"

STATUS=$(uv run python -c "import json; print(json.load(open('$RESULT_FILE'))['status'])" 2>/dev/null || echo "fail")
COUNT=$(uv run python -c "import json; print(json.load(open('$RESULT_FILE'))['total_violations'])" 2>/dev/null || echo "?")

# Write next-step
cat > "$OUT_DIR/next-step.md" <<NSEOF
# W3 Next Steps

- Status: $STATUS
- Acceptance violations: $COUNT

## If violations > 0
1. For each violation in output.json:
   - Can be command-ized: rewrite as executable shell command in backticks
   - Needs external env: add [ENV-DEP] tag
   - Needs browser/E2E: add [E2E] tag
   - Cannot automate: add [MANUAL-VERIFY] with alternative description
2. Re-run: \`bash .claude/skills/taskcard-governance/scripts/run_w3_acceptance_normalizer.sh\`

## If violations = 0
Proceed to W4: \`bash .claude/skills/taskcard-governance/scripts/run_w4_evidence_gate.sh\`
NSEOF

if [ "$STATUS" = "fail" ]; then
  cat > "$OUT_DIR/failure.md" <<FEOF
# W3 Failure Report

- Session: $SESSION_ID
- Acceptance violations: $COUNT
- Details: See output.json

## Required Actions
Normalize all acceptance commands before proceeding to W4.
FEOF
fi

echo "W3 complete: status=$STATUS violations=$COUNT"
echo "Artifacts: $OUT_DIR/"
exit $( [ "$STATUS" = "pass" ] && echo 0 || echo 1 )
