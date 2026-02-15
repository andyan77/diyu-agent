#!/usr/bin/env bash
# Hook: PreToolUse (Edit|Write)
# Purpose: Append audit log entry for every file edit/write operation.
# Output: .audit/session-{date}.jsonl
#
# Fields: timestamp, tool, file, governance, layer, tier, guard_triggered, session
# Layer/Tier mapping per governance-optimization-plan.md Section C.
#
# Called by Claude Code hooks with tool input on stdin.
# Exit 0 = allow, non-zero = block.

set -euo pipefail

AUDIT_DIR=".audit"
mkdir -p "$AUDIT_DIR"

DATE=$(date -u +%Y-%m-%d)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# GAP-M1: Deterministic session ID -- never "unknown"
# Priority: CLAUDE_SESSION_ID > input JSON session_id > timestamp+PID
if [ -n "${CLAUDE_SESSION_ID:-}" ]; then
  SESSION_ID="$CLAUDE_SESSION_ID"
elif [ -n "${PPID:-}" ]; then
  SESSION_ID="${DATE}-pid${PPID}"
else
  SESSION_ID="${DATE}-ts$(date +%s)"
fi

LOGFILE="${AUDIT_DIR}/session-${DATE}.jsonl"

# Read tool input from stdin (JSON with file_path, etc.)
INPUT=$(cat)

# Extract file path from the tool input (supports both nested tool_input.* and flat formats)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d)
    print(ti.get('file_path', ti.get('path', 'unknown')))
except:
    print('unknown')
" 2>/dev/null || echo "unknown")

# Determine layer and tier from file path
LAYER="unknown"
TIER=0
IS_GOVERNANCE="false"

case "$FILE_PATH" in
    src/infra/org/*)
        LAYER="infra"; TIER=4 ;;
    src/brain/*)
        LAYER="brain"; TIER=2 ;;
    src/ports/*)
        LAYER="ports"; TIER=4 ;;
    src/knowledge/*)
        LAYER="knowledge"; TIER=2 ;;
    src/skill/*)
        LAYER="skill"; TIER=2 ;;
    src/tool/*)
        LAYER="tool"; TIER=2 ;;
    src/gateway/*)
        LAYER="gateway"; TIER=2 ;;
    src/infra/*)
        LAYER="infra"; TIER=3 ;;
    src/shared/*)
        LAYER="shared"; TIER=2 ;;
    migrations/*)
        LAYER="migrations"; TIER=3 ;;
    frontend/*)
        LAYER="frontend"; TIER=2 ;;
    tests/*)
        LAYER="tests"; TIER=1 ;;
    docs/task-cards/*|docs/governance/*|delivery/*)
        LAYER="governance"; TIER=3; IS_GOVERNANCE="true" ;;
    docs/*)
        LAYER="docs"; TIER=1 ;;
    .github/*)
        LAYER="ci"; TIER=3 ;;
    *)
        LAYER="other"; TIER=1 ;;
esac

# ---------------------------------------------------------------------------
# Layer boundary enforcement (phased enablement per H7 audit fix)
# Read current_phase from milestone-matrix.yaml to decide enforcement level:
#   src/ports/        -> Phase 0-1: WARN only, Phase 2+: BLOCK
#   src/infra/org/    -> Phase 1+: BLOCK (RLS critical)
#   delivery/manifest -> Phase 3+: BLOCK
# ---------------------------------------------------------------------------
CURRENT_PHASE=$(python3 -c "
import yaml
with open('delivery/milestone-matrix.yaml') as f:
    d = yaml.safe_load(f)
phase_str = d.get('current_phase', 'phase_0')
print(int(phase_str.replace('phase_', '')))
" 2>/dev/null || echo "0")

GUARD_ACTION=""

case "$FILE_PATH" in
    src/infra/org/*)
        # RLS-critical layer: block at Phase 1+, warn at Phase 0
        if [ "$CURRENT_PHASE" -ge 1 ]; then
            GUARD_ACTION="BLOCK"
        else
            GUARD_ACTION="WARN"
        fi
        echo "[PreToolUse] WARNING: Editing RLS-critical path: $FILE_PATH (phase=$CURRENT_PHASE, tier=$TIER)" >&2
        ;;
    src/ports/*)
        # Port interfaces: warn at Phase 0-1, block at Phase 2+
        if [ "$CURRENT_PHASE" -ge 2 ]; then
            GUARD_ACTION="BLOCK"
        else
            GUARD_ACTION="WARN"
        fi
        echo "[PreToolUse] WARNING: Editing port interface: $FILE_PATH (phase=$CURRENT_PHASE, boundary change)" >&2
        ;;
    delivery/manifest*)
        # Delivery manifest: block at Phase 3+, warn before
        if [ "$CURRENT_PHASE" -ge 3 ]; then
            GUARD_ACTION="BLOCK"
        else
            GUARD_ACTION="WARN"
        fi
        echo "[PreToolUse] WARNING: Editing delivery manifest: $FILE_PATH (phase=$CURRENT_PHASE)" >&2
        ;;
esac

# Write audit entry
python3 -c "
import json, sys
entry = {
    'timestamp': '$TIMESTAMP',
    'tool': '${TOOL_NAME:-edit}',
    'file': '$FILE_PATH',
    'governance': '$IS_GOVERNANCE' == 'true',
    'layer': '$LAYER',
    'tier': $TIER,
    'guard_triggered': '${GUARD_ACTION:-None}',
    'session': '$SESSION_ID'
}
print(json.dumps(entry))
" >> "$LOGFILE"

# Enforce boundary based on guard action
if [ "$GUARD_ACTION" = "BLOCK" ]; then
    echo "[PreToolUse] BLOCKED: $FILE_PATH requires elevated review (RLS boundary)" >&2
    exit 2
fi

# Allow the operation (includes WARN and no-action cases)
exit 0
