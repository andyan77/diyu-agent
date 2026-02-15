#!/bin/bash
# post_tool_failure_log.sh - PostToolUseFailure hook
# Logs tool execution failures for debugging and observability.
#
# Input (stdin): JSON with tool_name, tool_input, error details
# Always exit 0 (non-blocking, logging only)

set -e

AUDIT_DIR=".audit"
FAILURE_LOG="${AUDIT_DIR}/tool-failures.jsonl"

# Ensure audit directory exists
mkdir -p "$AUDIT_DIR"

# GAP-M1: Deterministic session ID
if [ -n "${CLAUDE_SESSION_ID:-}" ]; then
  SESSION_ID="$CLAUDE_SESSION_ID"
elif [ -n "${PPID:-}" ]; then
  SESSION_ID="$(date -u +%Y-%m-%d)-pid${PPID}"
else
  SESSION_ID="$(date -u +%Y-%m-%d)-ts$(date +%s)"
fi

# Read input from stdin
INPUT=$(cat)

# Extract failure details using Python for reliable JSON parsing
python3 -c "
import sys, json
from datetime import datetime, timezone

d = json.load(sys.stdin)
ti = d.get('tool_input', d)

tool_name = d.get('tool_name', 'unknown')
error = d.get('tool_error', d.get('error', ''))

# Truncate error to prevent log bloat
if len(str(error)) > 500:
    error = str(error)[:500] + '...[truncated]'

entry = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'tool': tool_name,
    'error': error,
    'session': '${SESSION_ID}',
}

# Append to failure log
with open('${FAILURE_LOG}', 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')

# Also output to stderr for terminal visibility
print(f'[PostToolUseFailure] {tool_name} failed: {str(error)[:100]}', file=sys.stderr)
" <<< "$INPUT" || true

# Pass through input (non-blocking)
echo "$INPUT"
exit 0
