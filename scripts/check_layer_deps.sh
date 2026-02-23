#!/usr/bin/env bash
# check_layer_deps.sh - Verify layer dependency rules are not violated
#
# Architecture constraint: Layers may only depend downward or on Port interfaces.
# Brain    -> Ports, shared only (never Infrastructure/Gateway/Tool directly)
# Knowledge-> Ports, shared only (never Infrastructure/Gateway/Brain/Memory)
# Skill    -> Ports, shared only (never Infrastructure/Gateway)
# Tool     -> shared only (external libs; never Infrastructure/Brain/Knowledge)
# Gateway  -> Ports, shared only (never Brain/Knowledge/Skill directly)
# Memory   -> Ports, shared only (never Infrastructure/Gateway/Tool/Skill)
# Infra    -> Ports, shared only (implements Ports; never Brain/Knowledge/Skill/Tool)
# Shared   -> stdlib + external only (never business layers)
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
NEW_VIOLATIONS=0
KNOWN_VIOLATIONS=0
VIOLATION_LIST=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --json)    JSON_OUTPUT=true ;;
  esac
done

SRC_DIR="src"

# Known pre-existing violations (tech debt tracked in guardian-system-completion-plan-v1.0.md)
# These are reported but do not cause exit code 1.
# Format: "file_path:pattern" — matched as substring against violation lines.
KNOWN_ALLOWLIST=(
  "src/memory/pg_adapter.py:from src.infra.models"
  "src/memory/events.py:from src.infra.models"
  "src/memory/items.py:from src.infra.models"
  "src/memory/receipt.py:from src.infra.models"
)

if [ ! -d "$SRC_DIR" ]; then
  if [ "$DRY_RUN" = true ]; then
    echo "DRY-RUN: src/ directory not found. Would check layer imports when code exists."
    echo "Rules:"
    echo "  brain/    -> may import from: ports/, shared/"
    echo "  knowledge/-> may import from: ports/, shared/"
    echo "  skill/    -> may import from: ports/, shared/"
    echo "  tool/     -> may import from: shared/ (external libs only)"
    echo "  gateway/  -> may import from: ports/, shared/"
    echo "  memory/   -> may import from: ports/, shared/"
    echo "  infra/    -> may import from: ports/ (implements), shared/"
    echo "  shared/   -> may import from: stdlib, external libs only"
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
FORBIDDEN_IMPORTS[brain]="from src.infra|from src.gateway|from src.tool|import src.infra|import src.gateway|import src.tool"
FORBIDDEN_IMPORTS[knowledge]="from src.infra|from src.gateway|from src.brain|from src.memory|import src.infra|import src.gateway|import src.brain|import src.memory"
FORBIDDEN_IMPORTS[skill]="from src.infra|from src.gateway|import src.infra|import src.gateway"
FORBIDDEN_IMPORTS[gateway]="from src.brain|from src.knowledge|from src.skill|import src.brain|import src.knowledge|import src.skill"
FORBIDDEN_IMPORTS[tool]="from src.infra|from src.brain|from src.knowledge|import src.infra|import src.brain|import src.knowledge"
FORBIDDEN_IMPORTS[memory]="from src.infra|from src.gateway|from src.tool|from src.skill|import src.infra|import src.gateway|import src.tool|import src.skill"
FORBIDDEN_IMPORTS[infra]="from src.brain|from src.knowledge|from src.skill|from src.tool|import src.brain|import src.knowledge|import src.skill|import src.tool"
FORBIDDEN_IMPORTS[shared]="from src.brain|from src.gateway|from src.knowledge|from src.memory|from src.skill|from src.tool|from src.infra|import src.brain|import src.gateway|import src.knowledge|import src.memory|import src.skill|import src.tool|import src.infra"

is_known_violation() {
  local line="$1"
  for entry in "${KNOWN_ALLOWLIST[@]}"; do
    local file_part="${entry%%:*}"
    local pattern_part="${entry#*:}"
    if [[ "$line" == *"$file_part"* ]] && [[ "$line" == *"$pattern_part"* ]]; then
      return 0
    fi
  done
  return 1
}

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
      if is_known_violation "$line"; then
        KNOWN_VIOLATIONS=$((KNOWN_VIOLATIONS + 1))
        if [ "$JSON_OUTPUT" = false ] && [ "$DRY_RUN" = false ]; then
          echo "  KNOWN: $line"
        fi
      else
        NEW_VIOLATIONS=$((NEW_VIOLATIONS + 1))
        VIOLATION_LIST="${VIOLATION_LIST}${line}\n"
        if [ "$JSON_OUTPUT" = false ] && [ "$DRY_RUN" = false ]; then
          echo "  VIOLATION: $line"
        fi
      fi
    done <<< "$matches"
  fi
}

if [ "$DRY_RUN" = true ]; then
  echo "DRY-RUN: Would check the following layer dependency rules:"
  for layer in brain knowledge skill gateway tool memory infra shared; do
    echo "  $layer/ -> forbidden: ${FORBIDDEN_IMPORTS[$layer]:-none}"
  done
  exit 0
fi

for layer in brain knowledge skill gateway tool memory infra shared; do
  check_layer "$layer"
done

if [ "$JSON_OUTPUT" = true ]; then
  # "count" kept for backward compatibility (consumed by hooks/post_edit_layer_check.sh)
  if [ "$NEW_VIOLATIONS" -eq 0 ]; then
    echo "{\"status\":\"pass\",\"violations\":[],\"count\":0,\"new_count\":0,\"known_count\":$KNOWN_VIOLATIONS,\"total_count\":$VIOLATIONS}"
  else
    echo "{\"status\":\"fail\",\"count\":$NEW_VIOLATIONS,\"new_count\":$NEW_VIOLATIONS,\"known_count\":$KNOWN_VIOLATIONS,\"total_count\":$VIOLATIONS,\"message\":\"$NEW_VIOLATIONS new layer dependency violation(s) found\"}"
  fi
else
  if [ "$NEW_VIOLATIONS" -eq 0 ] && [ "$KNOWN_VIOLATIONS" -eq 0 ]; then
    echo "PASS: No layer dependency violations found"
  elif [ "$NEW_VIOLATIONS" -eq 0 ]; then
    echo ""
    echo "PASS: $KNOWN_VIOLATIONS known violation(s) in allowlist (tech debt), 0 new violations"
  else
    echo ""
    echo "FAIL: $NEW_VIOLATIONS new layer dependency violation(s) found ($KNOWN_VIOLATIONS known in allowlist)"
  fi
fi

# Exit code based on NEW violations only — known allowlisted tech debt does not block CI
exit $( [ "$NEW_VIOLATIONS" -eq 0 ] && echo 0 || echo 1 )
