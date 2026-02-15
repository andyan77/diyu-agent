#!/usr/bin/env bash
# Hook: PostToolUse (Edit|Write)
# Purpose: Post-edit schema check for task card files.
# Runs a quick schema check on the edited file to provide immediate feedback.
# GAP-M11: renamed from post_edit_format.sh to match actual behavior.
#
# Exit code is always 0 (informational only, does not block).

set -euo pipefail

# Read tool input from stdin
INPUT=$(cat)

# Extract file path (supports both nested tool_input.* and flat formats)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d)
    print(ti.get('file_path', ti.get('path', '')))
except:
    print('')
" 2>/dev/null || echo "")

# Only process task card files
case "$FILE_PATH" in
    docs/task-cards/*.md)
        ;;
    *)
        exit 0
        ;;
esac

# Quick schema check on the specific file
RESULT=$(python3 scripts/check_task_schema.py --mode full --filter-file "$FILE_PATH" --json 2>/dev/null || true)

if [ -n "$RESULT" ]; then
    BLOCK=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d['summary']['block'])
except:
    print('?')
" 2>/dev/null || echo "?")

    WARNING=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d['summary']['warning'])
except:
    print('?')
" 2>/dev/null || echo "?")

    CARDS=$(echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d['total_cards'])
except:
    print('?')
" 2>/dev/null || echo "?")

    echo "[PostToolUse] $FILE_PATH: ${CARDS} cards, BLOCK=${BLOCK}, WARNING=${WARNING}"
fi

exit 0
