#!/usr/bin/env bash
# change_impact_router.sh - Route change impact to CI gates + reviewers
#
# Dual routing: determines which CI checks to trigger AND which reviewers to assign
# based on changed file paths. Respects phase-based gate activation.
#
# Design source: governance-optimization-plan.md Section 2 (Gap B)
#
# Usage:
#   bash scripts/change_impact_router.sh              # Analyze current changes vs main
#   bash scripts/change_impact_router.sh --dry-run    # Show routing rules
#   bash scripts/change_impact_router.sh --json       # JSON output
#   bash scripts/change_impact_router.sh --base HEAD~1  # Compare against specific ref
#
# Exit codes: 0 = routing computed, 1 = error

set -euo pipefail

DRY_RUN=false
JSON_OUTPUT=false
BASE_REF=""

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true ;;
    --json)    JSON_OUTPUT=true ;;
    --base)    shift; BASE_REF="${1:-}" ;;
  esac
  shift
done

# Resolve BASE_REF: explicit > origin/main > HEAD > staged
if [ -z "$BASE_REF" ]; then
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    BASE_REF="origin/main"
  elif git rev-parse --verify HEAD >/dev/null 2>&1; then
    BASE_REF="HEAD"
  fi
fi

if [ "$DRY_RUN" = true ]; then
  cat <<'RULES'
Change Impact Routing Rules (priority high to low):

  Path Pattern              -> Gates                         -> Reviewers
  -------------------------------------------------------------------------
  docs/task-cards/** | docs/governance/** -> [governance]     -> [docs-owner]
  docs/** | *.md            -> []                            -> [docs-owner]
  src/ports/**              -> [check_port_compat]           -> [architect]
  migrations/**             -> [check_migration]             -> [architect, data-safety]
  src/infra/org/**          -> [isolation_smoke]             -> [security-lead]
  src/**                    -> [check_layer_deps]            -> [same-layer-dev]
  frontend/packages/api-client/** -> [fe_lint, fe_test, contract_test] -> [fe-lead, api-owner]
  frontend/**               -> [fe_lint, fe_test]            -> [fe-lead]
  openapi.yaml | openapi/** -> [openapi_sync]                -> [fe-lead, api-owner]
  delivery/**               -> []                            -> [devops]
  .github/**                -> []                            -> [devops]

Phase-based activation:
  Gates only trigger if their activation_phase <= current_phase
RULES
  exit 0
fi

# Get current phase from milestone matrix
CURRENT_PHASE=0
if [ -f "delivery/milestone-matrix.yaml" ]; then
  CURRENT_PHASE=$(python3 -c "
import yaml
with open('delivery/milestone-matrix.yaml') as f:
    m = yaml.safe_load(f)
phase = m.get('current_phase', 'phase_0')
print(phase.replace('phase_', ''))
" 2>/dev/null || echo "0")
fi

# Get changed files
CHANGED_FILES=""
if git rev-parse --git-dir >/dev/null 2>&1; then
  if [ -n "$BASE_REF" ]; then
    CHANGED_FILES=$(git diff --name-only "$BASE_REF" 2>/dev/null || echo "")
  fi
  # Fallback: include staged (uncommitted) files
  if [ -z "$CHANGED_FILES" ]; then
    CHANGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")
  fi
  # Fallback: untracked + staged for fresh repos with no commits
  if [ -z "$CHANGED_FILES" ] && ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    CHANGED_FILES=$(git status --porcelain 2>/dev/null | awk '{print $2}' || echo "")
  fi
fi

if [ -z "$CHANGED_FILES" ]; then
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"changed_paths":[],"triggered_gates":[],"skipped_gates":[],"required_reviewers":[],"risk_score":0}'
  else
    echo "No changed files detected"
  fi
  exit 0
fi

# Initialize arrays
declare -A GATES
declare -A REVIEWERS
SKIPPED_GATES=""

add_gate() {
  local gate="$1"
  local activation_phase="${2:-0}"
  if [ "$CURRENT_PHASE" -ge "$activation_phase" ]; then
    GATES["$gate"]=1
  else
    SKIPPED_GATES="${SKIPPED_GATES}{\"gate\":\"$gate\",\"reason\":\"phase $CURRENT_PHASE < activation phase $activation_phase\"},"
  fi
}

add_reviewer() {
  local reviewer="$1"
  REVIEWERS["$reviewer"]=1
}

# Route each changed file
while IFS= read -r filepath; do
  [ -z "$filepath" ] && continue

  case "$filepath" in
    src/ports/*)
      add_gate "check_port_compat" 0
      add_reviewer "architect"
      ;;
    migrations/*)
      add_gate "check_migration" 0
      add_reviewer "architect"
      add_reviewer "data-safety"
      ;;
    src/infra/org/*)
      add_gate "isolation_smoke" 1
      add_reviewer "security-lead"
      ;;
    src/*)
      add_gate "check_layer_deps" 0
      add_reviewer "same-layer-dev"
      ;;
    frontend/packages/api-client/*)
      add_gate "fe_lint" 1
      add_gate "fe_test" 1
      add_gate "contract_test" 2
      add_reviewer "fe-lead"
      add_reviewer "api-owner"
      ;;
    frontend/*)
      add_gate "fe_lint" 1
      add_gate "fe_test" 1
      add_reviewer "fe-lead"
      ;;
    openapi.yaml|openapi/*)
      add_gate "openapi_sync" 2
      add_reviewer "fe-lead"
      add_reviewer "api-owner"
      ;;
    delivery/*)
      add_reviewer "devops"
      ;;
    .github/*)
      add_reviewer "devops"
      ;;
    docs/task-cards/*|docs/governance/*)
      add_gate "governance" 0
      add_reviewer "docs-owner"
      ;;
    docs/*|*.md)
      add_reviewer "docs-owner"
      ;;
  esac
done <<< "$CHANGED_FILES"

# Get risk score
RISK_SCORE=0
if [ -x "scripts/risk_scorer.sh" ]; then
  RISK_SCORE=$(bash scripts/risk_scorer.sh --score-only 2>/dev/null || echo "0")
fi

# Build output
GATE_LIST=$(printf '%s\n' "${!GATES[@]}" | sort | tr '\n' ',' | sed 's/,$//')
REVIEWER_LIST=$(printf '%s\n' "${!REVIEWERS[@]}" | sort | tr '\n' ',' | sed 's/,$//')
FILE_COUNT=$(echo "$CHANGED_FILES" | wc -l)

if [ "$JSON_OUTPUT" = true ]; then
  # Build JSON arrays
  GATES_JSON=$(echo "$GATE_LIST" | tr ',' '\n' | sed 's/^/"/;s/$/"/' | tr '\n' ',' | sed 's/,$//')
  REVIEWERS_JSON=$(echo "$REVIEWER_LIST" | tr ',' '\n' | sed 's/^/"/;s/$/"/' | tr '\n' ',' | sed 's/,$//')
  SKIPPED_JSON=$(echo "$SKIPPED_GATES" | sed 's/,$//')

  cat <<EOF
{
  "changed_paths_count": $FILE_COUNT,
  "triggered_gates": [${GATES_JSON:-}],
  "skipped_gates": [${SKIPPED_JSON:-}],
  "required_reviewers": [${REVIEWERS_JSON:-}],
  "risk_score": $RISK_SCORE,
  "current_phase": $CURRENT_PHASE
}
EOF
else
  echo "Change Impact Analysis:"
  echo "  Files changed: $FILE_COUNT"
  echo "  Current phase: $CURRENT_PHASE"
  echo "  Triggered gates: ${GATE_LIST:-none}"
  echo "  Required reviewers: ${REVIEWER_LIST:-none}"
  echo "  Risk score: $RISK_SCORE"
fi

exit 0
