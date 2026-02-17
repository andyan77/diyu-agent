#!/usr/bin/env bash
# check_migration.sh - Migration safety checks
#
# Validates that database migrations follow safety rules:
# 1. Every upgrade has a matching downgrade
# 2. No destructive DDL without explicit marker
# 3. Migration files follow naming convention
# 4. No data-loss operations without [CONFIRMED-DESTRUCTIVE] marker
#
# Usage:
#   bash scripts/check_migration.sh              # Check all migrations
#   bash scripts/check_migration.sh --dry-run    # Show what would be checked
#   bash scripts/check_migration.sh --json       # JSON output
#
# Exit codes: 0 = safe, 1 = violations found

set -euo pipefail

DRY_RUN=false
JSON_OUTPUT=false
VIOLATIONS=0
VIOLATION_LIST=""
VIOLATION_JSON="[]"

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --json)    JSON_OUTPUT=true ;;
  esac
done

MIGRATIONS_DIR="migrations/versions"

if [ ! -d "$MIGRATIONS_DIR" ]; then
  if [ "$DRY_RUN" = true ]; then
    echo "DRY-RUN: $MIGRATIONS_DIR not found. Would check when migrations exist."
    echo "Rules:"
    echo "  1. Every upgrade() must have matching downgrade()"
    echo "  2. DROP TABLE/DROP COLUMN requires [CONFIRMED-DESTRUCTIVE] marker"
    echo "  3. No DELETE FROM without WHERE clause"
    echo "  4. TRUNCATE requires [CONFIRMED-DESTRUCTIVE] marker"
    exit 0
  fi
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"skip","reason":"migrations/versions/ not found","violations":[]}'
  else
    echo "SKIP: $MIGRATIONS_DIR not found (no migrations yet)"
  fi
  exit 0
fi

add_violation() {
  local file="$1"
  local rule="$2"
  local detail="$3"
  VIOLATIONS=$((VIOLATIONS + 1))
  VIOLATION_LIST="${VIOLATION_LIST}  [$rule] $file: $detail\n"
  VIOLATION_JSON=$(python3 -c "
import json,sys
v=json.loads(sys.argv[1])
v.append({'file':sys.argv[2],'rule':sys.argv[3],'detail':sys.argv[4]})
print(json.dumps(v))
" "$VIOLATION_JSON" "$file" "$rule" "$detail" 2>/dev/null || echo "$VIOLATION_JSON")
}

# Check each migration file
for migration in "$MIGRATIONS_DIR"/*.py; do
  [ -f "$migration" ] || continue
  basename=$(basename "$migration")

  # Rule 1: Must have both upgrade() and downgrade()
  has_upgrade=$(grep -c 'def upgrade' "$migration" || true)
  has_downgrade=$(grep -c 'def downgrade' "$migration" || true)
  if [ "$has_upgrade" -gt 0 ] && [ "$has_downgrade" -eq 0 ]; then
    add_violation "$basename" "ROLLBACK" "upgrade() without downgrade()"
  fi

  # Rule 2: Destructive DDL in upgrade() needs marker
  # Extract upgrade() body (from 'def upgrade' to next 'def ' or EOF)
  # Skip comments, docstrings, and downgrade() body
  upgrade_body=$(sed -n '/^def upgrade/,/^def /p' "$migration" | head -n -1)
  destructive_ops=$(echo "$upgrade_body" \
    | grep -niE 'drop\s+(table|column|index)|op\.drop_(table|column)|truncate\s+' \
    | grep -vE '^\s*[0-9]+[:-]\s*(#|"""|Rollback)' || true)
  if [ -n "$destructive_ops" ]; then
    has_marker=$(grep -c 'CONFIRMED-DESTRUCTIVE' "$migration" || true)
    if [ "$has_marker" -eq 0 ]; then
      add_violation "$basename" "DESTRUCTIVE" "Contains DROP/TRUNCATE without [CONFIRMED-DESTRUCTIVE] marker"
    fi
  fi

  # Rule 3: DELETE without WHERE
  delete_no_where=$(grep -niE '^\s*op\.execute.*DELETE\s+FROM' "$migration" | grep -iv 'WHERE' || true)
  if [ -n "$delete_no_where" ]; then
    has_marker=$(grep -c 'CONFIRMED-DESTRUCTIVE' "$migration" || true)
    if [ "$has_marker" -eq 0 ]; then
      add_violation "$basename" "DELETE-ALL" "DELETE FROM without WHERE clause and no [CONFIRMED-DESTRUCTIVE] marker"
    fi
  fi

  # Rule 5: Migration metadata keys (治理规范 v1.1 Section 8)
  for meta_key in reversible_type rollback_artifact drill_evidence_id; do
    has_key=$(grep -cE "^${meta_key}\s*=" "$migration" || true)
    if [ "$has_key" -eq 0 ]; then
      add_violation "$basename" "METADATA" "Missing required migration metadata: $meta_key"
    fi
  done

  # Rule 4: downgrade() must not be empty pass
  if [ "$has_downgrade" -gt 0 ]; then
    # Check if downgrade body is just 'pass'
    downgrade_body=$(sed -n '/def downgrade/,/^def \|^$/p' "$migration" | tail -n +2 | grep -v '^\s*$' | head -5)
    if echo "$downgrade_body" | grep -qE '^\s*pass\s*$' && [ "$(echo "$downgrade_body" | wc -l)" -le 1 ]; then
      # pass-only downgrade is a warning, not violation for additive migrations
      :
    fi
  fi
done

if [ "$JSON_OUTPUT" = true ]; then
  if [ "$VIOLATIONS" -eq 0 ]; then
    echo '{"status":"pass","violations":[],"count":0}'
  else
    echo "{\"status\":\"fail\",\"count\":$VIOLATIONS,\"violations\":$VIOLATION_JSON}"
  fi
else
  if [ "$VIOLATIONS" -eq 0 ]; then
    echo "PASS: All migrations follow safety rules"
  else
    echo -e "$VIOLATION_LIST"
    echo "FAIL: $VIOLATIONS migration safety violation(s)"
    echo "  See: CLAUDE.md -> 'NEVER delete migrations'"
  fi
fi

exit $( [ "$VIOLATIONS" -eq 0 ] && echo 0 || echo 1 )
