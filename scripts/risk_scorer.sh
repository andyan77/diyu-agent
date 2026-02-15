#!/usr/bin/env bash
# risk_scorer.sh - Quantitative risk scoring for changes
#
# 4-dimension scoring model:
#   D1: Blast Radius (0-3) - How many layers/services affected
#   D2: Data Safety (0-3)  - Migration/RLS/deletion risk
#   D3: Contract Impact (0-3) - Port/API/schema changes
#   D4: Security Surface (0-3) - Auth/crypto/permission changes
#
# Total score: 0-12 (Low: 0-3, Medium: 4-6, High: 7-9, Critical: 10-12)
#
# Usage:
#   bash scripts/risk_scorer.sh              # Full report
#   bash scripts/risk_scorer.sh --json       # JSON output
#   bash scripts/risk_scorer.sh --score-only # Just the numeric score
#   bash scripts/risk_scorer.sh --dry-run    # Show scoring rules
#   bash scripts/risk_scorer.sh --base HEAD~1  # Compare against specific ref
#
# Exit codes: 0 = scored, 1 = error

set -euo pipefail

DRY_RUN=false
JSON_OUTPUT=false
SCORE_ONLY=false
BASE_REF=""

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)    DRY_RUN=true ;;
    --json)       JSON_OUTPUT=true ;;
    --score-only) SCORE_ONLY=true ;;
    --base)       shift; BASE_REF="${1:-}" ;;
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
Risk Scoring Model (4 dimensions, 0-3 each, total 0-12):

D1 Blast Radius:
  0 = docs/tests only
  1 = single layer
  2 = 2-3 layers
  3 = 4+ layers or cross-cutting

D2 Data Safety:
  0 = no data changes
  1 = additive migration only
  2 = migration with schema alteration
  3 = destructive DDL / data deletion / RLS change

D3 Contract Impact:
  0 = no contract changes
  1 = additive Port/API changes
  2 = Port signature change (backward compatible)
  3 = breaking Port/API change

D4 Security Surface:
  0 = no security impact
  1 = auth-adjacent code
  2 = permission/RBAC changes
  3 = crypto/JWT/RLS policy changes

Risk Levels: Low(0-3) Medium(4-6) High(7-9) Critical(10-12)
RULES
  exit 0
fi

# Get changed files
CHANGED_FILES=""
DIFF_STAT=""
if git rev-parse --git-dir >/dev/null 2>&1; then
  if [ -n "$BASE_REF" ]; then
    CHANGED_FILES=$(git diff --name-only "$BASE_REF" 2>/dev/null || echo "")
    DIFF_STAT=$(git diff --stat "$BASE_REF" 2>/dev/null || echo "")
  fi
  # Fallback: include staged (uncommitted) files
  if [ -z "$CHANGED_FILES" ]; then
    CHANGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")
    DIFF_STAT=$(git diff --cached --stat 2>/dev/null || echo "")
  fi
  # Fallback: untracked + staged for fresh repos with no commits
  if [ -z "$CHANGED_FILES" ] && ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    CHANGED_FILES=$(git status --porcelain 2>/dev/null | awk '{print $2}' || echo "")
  fi
fi

if [ -z "$CHANGED_FILES" ]; then
  if [ "$SCORE_ONLY" = true ]; then
    echo "0"
  elif [ "$JSON_OUTPUT" = true ]; then
    echo '{"total":0,"level":"low","d1_blast_radius":0,"d2_data_safety":0,"d3_contract_impact":0,"d4_security_surface":0}'
  else
    echo "Risk Score: 0 (Low) - No changes detected"
  fi
  exit 0
fi

# D1: Blast Radius
LAYERS_TOUCHED=0
echo "$CHANGED_FILES" | grep -q '^src/brain/'      && LAYERS_TOUCHED=$((LAYERS_TOUCHED + 1))
echo "$CHANGED_FILES" | grep -q '^src/knowledge/'   && LAYERS_TOUCHED=$((LAYERS_TOUCHED + 1))
echo "$CHANGED_FILES" | grep -q '^src/skill/'       && LAYERS_TOUCHED=$((LAYERS_TOUCHED + 1))
echo "$CHANGED_FILES" | grep -q '^src/tool/'        && LAYERS_TOUCHED=$((LAYERS_TOUCHED + 1))
echo "$CHANGED_FILES" | grep -q '^src/gateway/'     && LAYERS_TOUCHED=$((LAYERS_TOUCHED + 1))
echo "$CHANGED_FILES" | grep -q '^src/infra/'       && LAYERS_TOUCHED=$((LAYERS_TOUCHED + 1))
echo "$CHANGED_FILES" | grep -q '^frontend/'        && LAYERS_TOUCHED=$((LAYERS_TOUCHED + 1))
echo "$CHANGED_FILES" | grep -q '^src/ports/'       && LAYERS_TOUCHED=$((LAYERS_TOUCHED + 1))

D1=0
ONLY_DOCS=$(echo "$CHANGED_FILES" | grep -cvE '^(docs/|.*\.md$|tests/)' || true)
if [ "$ONLY_DOCS" -eq 0 ]; then
  D1=0
elif [ "$LAYERS_TOUCHED" -le 1 ]; then
  D1=1
elif [ "$LAYERS_TOUCHED" -le 3 ]; then
  D1=2
else
  D1=3
fi

# D2: Data Safety
D2=0
if echo "$CHANGED_FILES" | grep -q '^migrations/'; then
  D2=1
  # Check for schema alterations
  if [ -n "$BASE_REF" ]; then
    MIGRATION_DIFF=$(git diff "$BASE_REF" -- migrations/ 2>/dev/null || echo "")
  else
    MIGRATION_DIFF=$(git diff --cached -- migrations/ 2>/dev/null || echo "")
  fi
  if echo "$MIGRATION_DIFF" | grep -qiE 'alter_column|drop_column'; then
    D2=2
  fi
  if echo "$MIGRATION_DIFF" | grep -qiE 'drop_table|truncate|delete.*from'; then
    D2=3
  fi
fi
# RLS changes
if echo "$CHANGED_FILES" | grep -q 'rls\|row.level.security'; then
  D2=3
fi

# D3: Contract Impact
D3=0
if echo "$CHANGED_FILES" | grep -q '^src/ports/'; then
  D3=1
  if [ -n "$BASE_REF" ]; then
    PORT_DIFF=$(git diff "$BASE_REF" -- src/ports/ 2>/dev/null || echo "")
  else
    PORT_DIFF=$(git diff --cached -- src/ports/ 2>/dev/null || echo "")
  fi
  if echo "$PORT_DIFF" | grep -qE '^\-.*def '; then
    D3=3  # Method removed = breaking
  elif echo "$PORT_DIFF" | grep -qE '^\-.*->|^\+.*->'; then
    D3=2  # Return type changed
  fi
fi
if echo "$CHANGED_FILES" | grep -q 'openapi'; then
  [ "$D3" -lt 2 ] && D3=2
fi

# D4: Security Surface
D4=0
if echo "$CHANGED_FILES" | grep -qE 'auth|jwt|token|crypto|password|secret'; then
  D4=1
fi
if echo "$CHANGED_FILES" | grep -qE 'rbac|permission|role|policy'; then
  D4=2
fi
if echo "$CHANGED_FILES" | grep -qE 'src/infra/org/|rls|jwt.*secret|crypto'; then
  D4=3
fi

TOTAL=$((D1 + D2 + D3 + D4))

# Determine level
LEVEL="low"
if [ "$TOTAL" -ge 10 ]; then
  LEVEL="critical"
elif [ "$TOTAL" -ge 7 ]; then
  LEVEL="high"
elif [ "$TOTAL" -ge 4 ]; then
  LEVEL="medium"
fi

if [ "$SCORE_ONLY" = true ]; then
  echo "$TOTAL"
elif [ "$JSON_OUTPUT" = true ]; then
  cat <<EOF
{
  "total": $TOTAL,
  "level": "$LEVEL",
  "d1_blast_radius": $D1,
  "d2_data_safety": $D2,
  "d3_contract_impact": $D3,
  "d4_security_surface": $D4,
  "layers_touched": $LAYERS_TOUCHED,
  "files_changed": $(echo "$CHANGED_FILES" | wc -l)
}
EOF
else
  echo "Risk Score: $TOTAL/12 ($LEVEL)"
  echo "  D1 Blast Radius:    $D1/3 ($LAYERS_TOUCHED layers touched)"
  echo "  D2 Data Safety:     $D2/3"
  echo "  D3 Contract Impact: $D3/3"
  echo "  D4 Security Surface: $D4/3"
fi

exit 0
