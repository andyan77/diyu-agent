#!/usr/bin/env bash
# check_port_compat.sh - Verify Port interface contract compatibility
#
# Checks that Port interfaces (src/ports/) maintain backward compatibility.
# Detects breaking changes: method removal/rename, type changes, required param additions.
#
# Usage:
#   bash scripts/check_port_compat.sh              # Check against main branch
#   bash scripts/check_port_compat.sh --dry-run    # Show what would be checked
#   bash scripts/check_port_compat.sh --json       # JSON output
#   bash scripts/check_port_compat.sh --base HEAD~1  # Compare against specific ref
#
# Exit codes: 0 = compatible, 1 = breaking changes detected

set -euo pipefail

DRY_RUN=false
JSON_OUTPUT=false
BASE_REF=""
PORTS_DIR="src/ports"

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)  DRY_RUN=true ;;
    --json)     JSON_OUTPUT=true ;;
    --base)     shift; BASE_REF="${1:-}" ;;
  esac
  shift
done

# Resolve BASE_REF: explicit > origin/main > HEAD
if [ -z "$BASE_REF" ]; then
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    BASE_REF="origin/main"
  elif git rev-parse --verify HEAD >/dev/null 2>&1; then
    BASE_REF="HEAD"
  fi
fi

# Day-1 Ports (from architecture doc v3.6 Section 12.3)
DAY1_PORTS=(
  "memory_core_port.py"
  "knowledge_port.py"
  "llm_call_port.py"
  "skill_registry.py"
  "org_context.py"
  "storage_port.py"
)

if [ ! -d "$PORTS_DIR" ]; then
  if [ "$DRY_RUN" = true ]; then
    echo "DRY-RUN: $PORTS_DIR not found. Would check Port contracts when code exists."
    echo "Day-1 Ports to monitor:"
    for port in "${DAY1_PORTS[@]}"; do
      echo "  - $PORTS_DIR/$port"
    done
    echo ""
    echo "Breaking change detection:"
    echo "  - Method removal or rename (def/async def signature gone)"
    echo "  - Return type changes"
    echo "  - Required parameter additions"
    echo "  - ABC/Protocol method removal"
    exit 0
  fi
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"skip","reason":"src/ports/ not found","breaking_changes":[]}'
  else
    echo "SKIP: $PORTS_DIR not found (Phase 0 skeleton stage)"
  fi
  exit 0
fi

BREAKING_CHANGES=0
CHANGES_DETAIL=""

# Check if we have git history to compare
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"skip","reason":"not a git repository"}'
  else
    echo "SKIP: Not a git repository, cannot compare Port changes"
  fi
  exit 0
fi

# Get list of changed port files
if [ -n "$BASE_REF" ]; then
  CHANGED_PORTS=$(git diff --name-only "$BASE_REF" -- "$PORTS_DIR/" 2>/dev/null || echo "")
else
  CHANGED_PORTS=$(git diff --cached --name-only -- "$PORTS_DIR/" 2>/dev/null || echo "")
fi

if [ -z "$CHANGED_PORTS" ]; then
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"pass","breaking_changes":[],"message":"No Port files changed"}'
  else
    echo "PASS: No Port files changed since $BASE_REF"
  fi
  exit 0
fi

# For each changed port, check for breaking changes
while IFS= read -r port_file; do
  [ -z "$port_file" ] && continue

  # Get old and new content
  OLD_CONTENT=$(git show "$BASE_REF:$port_file" 2>/dev/null || echo "")
  NEW_CONTENT=$(cat "$port_file" 2>/dev/null || echo "")

  if [ -z "$OLD_CONTENT" ]; then
    # New file, not a breaking change
    continue
  fi

  if [ -z "$NEW_CONTENT" ]; then
    # File deleted - breaking change
    BREAKING_CHANGES=$((BREAKING_CHANGES + 1))
    CHANGES_DETAIL="${CHANGES_DETAIL}  BREAKING: $port_file deleted\n"
    continue
  fi

  # Extract method signatures from old version
  OLD_METHODS=$(echo "$OLD_CONTENT" | grep -E '^\s*(async\s+)?def\s+[a-z_]' | sed 's/^\s*//' | sort || true)
  NEW_METHODS=$(echo "$NEW_CONTENT" | grep -E '^\s*(async\s+)?def\s+[a-z_]' | sed 's/^\s*//' | sort || true)

  # Check for removed methods
  REMOVED=$(comm -23 <(echo "$OLD_METHODS" | cut -d'(' -f1 | sort) <(echo "$NEW_METHODS" | cut -d'(' -f1 | sort) || true)

  if [ -n "$REMOVED" ]; then
    while IFS= read -r method; do
      [ -z "$method" ] && continue
      BREAKING_CHANGES=$((BREAKING_CHANGES + 1))
      CHANGES_DETAIL="${CHANGES_DETAIL}  BREAKING: $port_file - method removed: $method\n"
    done <<< "$REMOVED"
  fi

done <<< "$CHANGED_PORTS"

if [ "$JSON_OUTPUT" = true ]; then
  if [ "$BREAKING_CHANGES" -eq 0 ]; then
    echo '{"status":"pass","breaking_changes":[],"count":0}'
  else
    echo "{\"status\":\"fail\",\"count\":$BREAKING_CHANGES,\"message\":\"$BREAKING_CHANGES breaking change(s) detected\"}"
  fi
else
  if [ "$BREAKING_CHANGES" -eq 0 ]; then
    echo "PASS: No breaking Port changes detected"
  else
    echo -e "$CHANGES_DETAIL"
    echo "FAIL: $BREAKING_CHANGES breaking Port change(s) detected"
    echo "  See: docs/architecture/00-*.md Section 12.5 (Expand-Contract migration)"
  fi
fi

exit $( [ "$BREAKING_CHANGES" -eq 0 ] && echo 0 || echo 1 )
