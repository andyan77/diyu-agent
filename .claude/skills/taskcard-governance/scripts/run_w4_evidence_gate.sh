#!/usr/bin/env bash
# W4: Evidence and Gate Report - generate phase gate review with evidence assessment
# Produces session-level handoff artifacts in evidence/skills/taskcard-governance/
set -euo pipefail

SESSION_ID="${SESSION_ID:-$(date +%Y%m%dT%H%M%S)}"
WORKFLOW_ROLE="${WORKFLOW_ROLE:-W4}"
OUT_DIR="evidence/skills/taskcard-governance/${SESSION_ID}/W4"
mkdir -p "$OUT_DIR"

# GAP-M2: Role enforcement via enforce_workflow_role.py (auditable, structured logging)
if ! python3 scripts/enforce_workflow_role.py \
    --expected W4 --actual "$WORKFLOW_ROLE" \
    --session "$SESSION_ID" --log-dir "$OUT_DIR"; then
  echo "FATAL: WORKFLOW_ROLE=$WORKFLOW_ROLE but this is W4. Aborting." >&2
  cat > "$OUT_DIR/failure.md" <<FEOF
# W4 Failure Report
- Session: $SESSION_ID
- Reason: Role mismatch (expected W4, got $WORKFLOW_ROLE)
FEOF
  exit 1
fi

# Record input
cat > "$OUT_DIR/input.json" <<INPUTEOF
{
  "workflow": "W4",
  "session_id": "$SESSION_ID",
  "scope": "Full phase gate: schema + traceability + acceptance + evidence",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
INPUTEOF

RESULT_FILE="$OUT_DIR/output.json"
STATUS="pass"

# GAP-M5: trap ensures artifacts are written even on failure
_w4_cleanup() {
  local exit_code=$?
  if [ ! -f "$RESULT_FILE" ]; then
    cat > "$RESULT_FILE" <<TRAPEOF
{"status": "FAIL", "error": "W4 script crashed before producing output", "session_id": "$SESSION_ID"}
TRAPEOF
  fi
  if [ ! -f "$OUT_DIR/next-step.md" ]; then
    cat > "$OUT_DIR/next-step.md" <<TRAPNS
# W4 Next Steps
- Gate Status: FAIL (script crashed)
- Check stderr.log and output.json for details
TRAPNS
  fi
  if [ ! -f "$OUT_DIR/failure.md" ] && [ $exit_code -ne 0 ]; then
    cat > "$OUT_DIR/failure.md" <<TRAPFAIL
# W4 Failure Report
- Session: $SESSION_ID
- Gate Status: FAIL (unexpected exit code: $exit_code)
- Details: See stderr.log
TRAPFAIL
  fi
}
trap _w4_cleanup EXIT

# Run all guard scripts and collect results
uv run python -c "
import json
import subprocess
import sys

results = {}

# 1. Schema validation (full)
try:
    r = subprocess.run(
        ['uv', 'run', 'python', 'scripts/check_task_schema.py', '--mode', 'full', '--json'],
        capture_output=True, text=True, timeout=60
    )
    results['schema'] = json.loads(r.stdout) if r.stdout.strip() else {'error': 'empty output'}
    results['schema']['exit_code'] = r.returncode
except Exception as e:
    results['schema'] = {'error': str(e)}

# 2. Card inventory
try:
    r = subprocess.run(
        ['uv', 'run', 'python', 'scripts/count_task_cards.py', '--json'],
        capture_output=True, text=True, timeout=60
    )
    results['inventory'] = json.loads(r.stdout) if r.stdout.strip() else {'error': 'empty output'}
except Exception as e:
    results['inventory'] = {'error': str(e)}

# 3. Layer boundary check
try:
    r = subprocess.run(
        ['bash', 'scripts/check_layer_deps.sh', '--json'],
        capture_output=True, text=True, timeout=60
    )
    results['layer_boundary'] = json.loads(r.stdout) if r.stdout.strip() else {'error': 'empty output'}
except Exception as e:
    results['layer_boundary'] = {'error': str(e)}

# 4. Port compatibility check
try:
    r = subprocess.run(
        ['bash', 'scripts/check_port_compat.sh', '--json'],
        capture_output=True, text=True, timeout=60
    )
    results['port_compat'] = json.loads(r.stdout) if r.stdout.strip() else {'error': 'empty output'}
except Exception as e:
    results['port_compat'] = {'error': str(e)}

# 5. Migration safety check
try:
    r = subprocess.run(
        ['bash', 'scripts/check_migration.sh', '--json'],
        capture_output=True, text=True, timeout=60
    )
    results['migration_safety'] = json.loads(r.stdout) if r.stdout.strip() else {'error': 'empty output'}
except Exception as e:
    results['migration_safety'] = {'error': str(e)}

# Determine overall status
blocks = results.get('schema', {}).get('summary', {}).get('block', 0)
layer_fails = results.get('layer_boundary', {}).get('count', 0)
port_fails = results.get('port_compat', {}).get('count', 0)
migration_fails = results.get('migration_safety', {}).get('count', 0)

overall = 'pass' if (blocks == 0 and layer_fails == 0 and port_fails == 0 and migration_fails == 0) else 'fail'

gate_report = {
    'session_id': '$SESSION_ID',
    'status': overall,
    'checks': results,
    'summary': {
        'schema_blocks': blocks,
        'layer_violations': layer_fails,
        'port_breaking_changes': port_fails,
        'migration_violations': migration_fails
    }
}

with open('$RESULT_FILE', 'w') as f:
    json.dump(gate_report, f, indent=2, ensure_ascii=False)

print(json.dumps({'status': overall, 'blocks': blocks, 'layer': layer_fails, 'port': port_fails, 'migration': migration_fails}))
sys.exit(0 if overall == 'pass' else 1)
" 2>"$OUT_DIR/stderr.log"

EXIT_CODE=$?
STATUS=$(uv run python -c "import json; print(json.load(open('$RESULT_FILE'))['status'])" 2>/dev/null || echo "fail")

# Write next-step
cat > "$OUT_DIR/next-step.md" <<NSEOF
# W4 Next Steps

- Gate Status: $STATUS

## If FAIL
1. Review output.json for failing checks
2. Fix each failing guard individually
3. Re-run: \`bash .claude/skills/taskcard-governance/scripts/run_w4_evidence_gate.sh\`

## If PASS
Gate review complete. All governance checks passed.
NSEOF

if [ "$STATUS" = "fail" ]; then
  cat > "$OUT_DIR/failure.md" <<FEOF
# W4 Failure Report

- Session: $SESSION_ID
- Gate Status: FAIL
- Details: See output.json for per-check results

## Required Actions
Fix all failing checks before declaring gate pass.
FEOF
fi

echo "W4 complete: status=$STATUS"
echo "Artifacts: $OUT_DIR/"
exit $EXIT_CODE
