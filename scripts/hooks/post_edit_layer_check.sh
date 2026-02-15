#!/usr/bin/env bash
# Hook: PostToolUse (Edit|Write)
# Purpose: Check cross-layer import violations after file edits.
# Calls check_layer_deps.sh on the edited file's layer.
# Phase 0: exit 0 only (log, no block).
#
# Exit codes: 0 = allow (always, Phase 0 is observability only)

set -euo pipefail

# Read tool input from stdin
INPUT=$(cat)

# Extract file path
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d)
    print(ti.get('file_path', ti.get('path', '')))
except:
    print('')
" 2>/dev/null || echo "")

# Only check Python source files in src/
case "$FILE_PATH" in
    src/*.py)
        ;;
    *)
        exit 0
        ;;
esac

# Run layer dependency check (non-blocking in Phase 0)
RESULT=$(bash scripts/check_layer_deps.sh --json 2>/dev/null || true)

if [ -n "$RESULT" ]; then
    STATUS=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('status', 'unknown'))
except:
    print('unknown')
" 2>/dev/null || echo "unknown")

    if [ "$STATUS" = "fail" ]; then
        COUNT=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('count', 0))
except:
    print('?')
" 2>/dev/null || echo "?")
        echo "[PostToolUse:LayerCheck] WARNING: $COUNT cross-layer violation(s) detected after editing $FILE_PATH" >&2
        # Log to audit
        mkdir -p .audit 2>/dev/null || true
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] LAYER_VIOLATION file=$FILE_PATH count=$COUNT" >> .audit/layer-check.log 2>/dev/null || true
    fi
fi

# Phase 0: always exit 0 (observability only, never blocks)
exit 0
