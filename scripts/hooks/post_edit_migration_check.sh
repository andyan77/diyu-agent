#!/usr/bin/env bash
# Hook: PostToolUse (Edit|Write)
# Purpose: Check migration safety rules after editing migrations/versions/.
# Calls check_migration.sh to detect rollback/destructive/delete-all violations.
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

# Only check migration files
case "$FILE_PATH" in
    migrations/versions/*.py)
        ;;
    *)
        exit 0
        ;;
esac

# Run migration safety check (non-blocking in Phase 0)
RESULT=$(bash scripts/check_migration.sh --json 2>/dev/null || true)

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
        echo "[PostToolUse:MigrationCheck] WARNING: $COUNT migration safety violation(s) detected after editing $FILE_PATH" >&2
        # Log to audit
        mkdir -p .audit 2>/dev/null || true
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] MIGRATION_VIOLATION file=$FILE_PATH count=$COUNT" >> .audit/migration-check.log 2>/dev/null || true
    fi
fi

# Phase 0: always exit 0 (observability only, never blocks)
exit 0
