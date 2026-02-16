#!/usr/bin/env bash
# Hook: PreToolUse (Bash) -- commit gate
# Purpose: Before git commit, verify lint + test-smoke + task card schema.
# Exit 0 = allow, exit 2 = block (stderr fed to Claude), other = non-blocking error.
#
# Only activates when the bash command contains "git commit".
# Runs: make lint && make test-smoke && schema check (if task cards staged).
# Per governance-optimization-plan.md Section C (line 526-527).

set -euo pipefail

AUDIT_DIR=".audit"
mkdir -p "$AUDIT_DIR"

# GAP-M1: Deterministic session ID
if [ -n "${CLAUDE_SESSION_ID:-}" ]; then
  SESSION_ID="$CLAUDE_SESSION_ID"
elif [ -n "${PPID:-}" ]; then
  SESSION_ID="$(date -u +%Y-%m-%d)-pid${PPID}"
else
  SESSION_ID="$(date -u +%Y-%m-%d)-ts$(date +%s)"
fi

DATE=$(date -u +%Y-%m-%d)
LOGFILE="${AUDIT_DIR}/session-${DATE}.jsonl"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Read tool input from stdin
INPUT=$(cat)

# Extract the command being executed (supports both nested tool_input.* and flat formats)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d)
    print(ti.get('command', ''))
except:
    print('')
" 2>/dev/null || echo "")

# Only gate on git commit commands
case "$COMMAND" in
    *"git commit"*)
        ;;
    *)
        # Not a commit, allow
        exit 0
        ;;
esac

echo "[gate] Commit detected -- running pre-commit gates..." >&2

# Gate 1: Lint check
echo "[gate] Running lint..." >&2
if ! make lint > /dev/null 2>&1; then
    python3 -c "import json; print(json.dumps({'timestamp':'$TIMESTAMP','tool':'Bash','cmd':'git commit','blocked':True,'reason':'make lint failed','session':'$SESSION_ID'}))" >> "$LOGFILE"
    echo "[gate] BLOCKED: make lint failed" >&2
    echo "[gate] Run: make lint" >&2
    exit 2
fi
echo "[gate] Lint: PASS" >&2

# Gate 2: Smoke tests
echo "[gate] Running test-smoke..." >&2
if ! make test-smoke > /dev/null 2>&1; then
    python3 -c "import json; print(json.dumps({'timestamp':'$TIMESTAMP','tool':'Bash','cmd':'git commit','blocked':True,'reason':'make test-smoke failed','session':'$SESSION_ID'}))" >> "$LOGFILE"
    echo "[gate] BLOCKED: make test-smoke failed" >&2
    echo "[gate] Run: make test-smoke" >&2
    exit 2
fi
echo "[gate] Smoke tests: PASS" >&2

# Gate 3: Task card / governance / delivery schema (if related files staged)
STAGED_CARDS=$(git diff --cached --name-only -- 'docs/task-cards/' 2>/dev/null || true)
STAGED_GOVERNANCE=$(git diff --cached --name-only -- 'docs/governance/' 2>/dev/null || true)
STAGED_DELIVERY=$(git diff --cached --name-only -- 'delivery/' 2>/dev/null || true)

if [ -n "$STAGED_CARDS" ] || [ -n "$STAGED_GOVERNANCE" ] || [ -n "$STAGED_DELIVERY" ]; then
    echo "[gate] Governance-related files staged -- running schema validation..." >&2

    RESULT=$(python3 scripts/check_task_schema.py --mode full --json 2>/dev/null)
    BLOCK_COUNT=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d['summary']['block'])
except:
    print(-1)
" 2>/dev/null || echo "-1")

    if [ "$BLOCK_COUNT" = "0" ]; then
        echo "[gate] Schema check: PASS (BLOCK=0)" >&2
    elif [ "$BLOCK_COUNT" = "-1" ]; then
        echo "[gate] BLOCKED: Schema check could not run (fail-closed)" >&2
        echo "[gate] Run: python3 scripts/check_task_schema.py --mode full" >&2
        exit 2
    else
        echo "[gate] BLOCKED: $BLOCK_COUNT schema violations found" >&2
        echo "[gate] Run: python3 scripts/check_task_schema.py --mode full" >&2
        exit 2
    fi
fi

# Gate 4: Migration safety (if migrations are staged) -- G1-security enforcement
STAGED_MIGRATIONS=$(git diff --cached --name-only -- 'migrations/' 2>/dev/null || true)

if [ -n "$STAGED_MIGRATIONS" ]; then
    echo "[gate] Migration files staged -- running migration check..." >&2
    if ! bash scripts/check_migration.sh > /dev/null 2>&1; then
        python3 -c "import json; print(json.dumps({'timestamp':'$TIMESTAMP','tool':'Bash','cmd':'git commit','blocked':True,'reason':'migration safety check failed','session':'$SESSION_ID'}))" >> "$LOGFILE"
        echo "[gate] BLOCKED: Migration safety check failed" >&2
        echo "[gate] Run: bash scripts/check_migration.sh" >&2
        exit 2
    fi
    echo "[gate] Migration check: PASS" >&2

    # Gate 4b: RLS policy check for migrations -- G1-security enforcement
    echo "[gate] Running RLS policy check on staged migrations..." >&2
    if ! bash scripts/check_rls.sh > /dev/null 2>&1; then
        python3 -c "import json; print(json.dumps({'timestamp':'$TIMESTAMP','tool':'Bash','cmd':'git commit','blocked':True,'reason':'RLS check failed','session':'$SESSION_ID'}))" >> "$LOGFILE"
        echo "[gate] BLOCKED: RLS policy check failed" >&2
        echo "[gate] Run: bash scripts/check_rls.sh" >&2
        exit 2
    fi
    echo "[gate] RLS check: PASS" >&2
fi

# Gate 5: Port interface changes (if src/ports/ is staged)
STAGED_PORTS=$(git diff --cached --name-only -- 'src/ports/' 2>/dev/null || true)

if [ -n "$STAGED_PORTS" ]; then
    echo "[gate] Port interface files staged -- running layer dependency check..." >&2
    if ! bash scripts/check_layer_deps.sh > /dev/null 2>&1; then
        echo "[gate] BLOCKED: Layer dependency violation detected in port changes" >&2
        echo "[gate] Run: bash scripts/check_layer_deps.sh" >&2
        exit 2
    fi
    echo "[gate] Layer deps: PASS" >&2
fi

# Gate 6: Coverage threshold (if src/ files are staged) -- G1-tdd enforcement
STAGED_SRC=$(git diff --cached --name-only -- 'src/' 2>/dev/null || true)

if [ -n "$STAGED_SRC" ]; then
    echo "[gate] Source files staged -- running coverage check..." >&2
    COV_OUTPUT=$(uv run pytest tests/unit/ --cov=src --cov-fail-under=80 -q 2>&1 || true)
    COV_EXIT=$?
    if echo "$COV_OUTPUT" | grep -q "FAIL Required test coverage"; then
        python3 -c "import json; print(json.dumps({'timestamp':'$TIMESTAMP','tool':'Bash','cmd':'git commit','blocked':True,'reason':'coverage below 80%','session':'$SESSION_ID'}))" >> "$LOGFILE"
        echo "[gate] BLOCKED: Test coverage below 80% threshold" >&2
        echo "[gate] Run: uv run pytest tests/unit/ --cov=src --cov-report=term-missing" >&2
        exit 2
    fi
    echo "[gate] Coverage: PASS (>=80%)" >&2
fi

# Gate 7: Security scan (staged files, quick mode -- tool missing = WARN not block)
echo "[gate] Running security scan..." >&2
SCAN_JSON=$(mktemp /tmp/security-scan-XXXXXX.json)
trap 'rm -f "$SCAN_JSON"' EXIT
SCAN_EXIT=0
bash scripts/security_scan.sh --quick > "$SCAN_JSON" 2>&2 || SCAN_EXIT=$?
if [ "$SCAN_EXIT" -eq 1 ]; then
    python3 -c "import json; print(json.dumps({'timestamp':'$TIMESTAMP','tool':'Bash','cmd':'git commit','blocked':True,'reason':'security scan found issues','session':'$SESSION_ID'}))" >> "$LOGFILE"
    echo "[gate] BLOCKED: security scan found issues" >&2
    echo "[gate] Run: bash scripts/security_scan.sh --quick" >&2
    exit 2
fi
echo "[gate] Security scan: PASS" >&2

# GAP-M1: structured audit entry for commit gate
python3 -c "
import json
entry = {
    'timestamp': '$TIMESTAMP',
    'tool': 'Bash',
    'cmd': 'git commit',
    'blocked': False,
    'reason': 'all gates passed',
    'session': '$SESSION_ID'
}
print(json.dumps(entry))
" >> "$LOGFILE"

echo "[gate] All pre-commit gates PASSED" >&2
exit 0
