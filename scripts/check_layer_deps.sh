#!/usr/bin/env bash
# check_layer_deps.sh - Verify layer dependency rules are not violated
#
# Architecture constraint: Layers may only depend downward or on Port interfaces.
# Brain -> Ports only (never Infrastructure directly)
# Knowledge -> Ports only
# Skill -> Ports only
# Tool -> external libs only
# Gateway -> Ports + auth
# Infrastructure -> implements Ports
#
# Usage:
#   bash scripts/check_layer_deps.sh              # Check all
#   bash scripts/check_layer_deps.sh --dry-run    # Show what would be checked
#   bash scripts/check_layer_deps.sh --json       # JSON output
#
# Exit codes: 0 = clean, 1 = violations found

set -euo pipefail

DRY_RUN=false
JSON_OUTPUT=false
VIOLATIONS=0
VIOLATION_LIST=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --json)    JSON_OUTPUT=true ;;
  esac
done

SRC_DIR="src"

if [ ! -d "$SRC_DIR" ]; then
  if [ "$DRY_RUN" = true ]; then
    echo "DRY-RUN: src/ directory not found. Would check layer imports when code exists."
    echo "Rules:"
    echo "  brain/    -> may import from: ports/"
    echo "  knowledge/-> may import from: ports/"
    echo "  skill/    -> may import from: ports/, shared/"
    echo "  tool/     -> may import from: shared/ (external libs only)"
    echo "  gateway/  -> may import from: ports/, shared/"
    echo "  infra/    -> may import from: ports/ (implements), shared/"
    exit 0
  fi
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"skip","reason":"src/ directory not found","violations":[]}'
  else
    echo "SKIP: src/ directory not found (Phase 0 skeleton stage)"
  fi
  exit 0
fi

# Layer dependency rules: layer -> forbidden import patterns
declare -A FORBIDDEN_IMPORTS
FORBIDDEN_IMPORTS[brain]="from src.infra|from src.gateway|from src.tool|import src.infra|import src.gateway"
FORBIDDEN_IMPORTS[knowledge]="from src.infra|from src.gateway|from src.brain|import src.infra|import src.gateway"
FORBIDDEN_IMPORTS[skill]="from src.infra|from src.gateway|import src.infra|import src.gateway"
FORBIDDEN_IMPORTS[gateway]="from src.brain|from src.knowledge|from src.skill|import src.brain"
FORBIDDEN_IMPORTS[tool]="from src.infra|from src.brain|from src.knowledge|import src.infra|import src.brain"

check_layer() {
  local layer="$1"
  local pattern="${FORBIDDEN_IMPORTS[$layer]:-}"
  local layer_dir="$SRC_DIR/$layer"

  if [ ! -d "$layer_dir" ]; then
    return 0
  fi
  if [ -z "$pattern" ]; then
    return 0
  fi

  local matches
  matches=$(grep -rn --include="*.py" -E "$pattern" "$layer_dir" 2>/dev/null || true)

  if [ -n "$matches" ]; then
    while IFS= read -r line; do
      VIOLATIONS=$((VIOLATIONS + 1))
      VIOLATION_LIST="${VIOLATION_LIST}${line}\n"
      if [ "$JSON_OUTPUT" = false ] && [ "$DRY_RUN" = false ]; then
        echo "  VIOLATION: $line"
      fi
    done <<< "$matches"
  fi
}

if [ "$DRY_RUN" = true ]; then
  echo "DRY-RUN: Would check the following layer dependency rules:"
  for layer in brain knowledge skill gateway tool; do
    echo "  $layer/ -> forbidden: ${FORBIDDEN_IMPORTS[$layer]:-none}"
  done
  exit 0
fi

for layer in brain knowledge skill gateway tool; do
  check_layer "$layer"
done

if [ "$JSON_OUTPUT" = true ]; then
  if [ "$VIOLATIONS" -eq 0 ]; then
    echo '{"status":"pass","violations":[],"count":0}'
  else
    echo "{\"status\":\"fail\",\"count\":$VIOLATIONS,\"message\":\"$VIOLATIONS layer dependency violation(s) found\"}"
  fi
else
  if [ "$VIOLATIONS" -eq 0 ]; then
    echo "PASS: No layer dependency violations found"
  else
    echo ""
    echo "FAIL: $VIOLATIONS layer dependency violation(s) found"
  fi
fi

exit $( [ "$VIOLATIONS" -eq 0 ] && echo 0 || echo 1 )
