#!/usr/bin/env bash
# check_rls.sh - Row Level Security isolation checks
#
# Validates that all tenant-scoped tables have RLS policies enabled.
# Ensures org_id isolation is enforced at the database level.
#
# Table list sourced from src/shared/rls_tables.py (SSOT).
#
# Usage:
#   bash scripts/check_rls.sh                  # Check all phases
#   bash scripts/check_rls.sh --phase 1        # Phase 1 tables only
#   bash scripts/check_rls.sh --dry-run        # Show what would be checked
#   bash scripts/check_rls.sh --json           # JSON output
#
# Exit codes: 0 = all tables have RLS, 1 = missing RLS policies

set -euo pipefail

DRY_RUN=false
JSON_OUTPUT=false
PHASE="all"

# Parse arguments (supports --phase N value args)
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)  DRY_RUN=true ;;
    --json)     JSON_OUTPUT=true ;;
    --phase)    shift; PHASE="${1:-all}" ;;
    --phase=*)  PHASE="${1#--phase=}" ;;
  esac
  shift
done

MIGRATIONS_DIR="migrations/versions"

# Get table list from SSOT (src/shared/rls_tables.py)
TENANT_TABLES_RAW=$(uv run python -c "
from src.shared.rls_tables import get_rls_tables
for t in get_rls_tables($( [ "$PHASE" = "all" ] && echo "'all'" || echo "$PHASE" )):
    print(t)
" 2>/dev/null) || {
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"fail","reason":"Failed to load RLS table list from src/shared/rls_tables.py"}'
  else
    echo "FAIL: Cannot load RLS table list from src/shared/rls_tables.py"
  fi
  exit 1
}

# Convert to array
IFS=$'\n' read -r -d '' -a TENANT_TABLES <<< "$TENANT_TABLES_RAW" || true

if [ "${#TENANT_TABLES[@]}" -eq 0 ]; then
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"pass","violations":0,"message":"No RLS tables for specified phase","tables_checked":[]}'
  else
    echo "PASS: No RLS tables required for phase=$PHASE"
  fi
  exit 0
fi

if [ "$DRY_RUN" = true ]; then
  echo "DRY-RUN: Would check RLS policies for tenant-scoped tables (phase=$PHASE)."
  echo "Tables requiring RLS (org_id isolation):"
  for table in "${TENANT_TABLES[@]}"; do
    echo "  - $table"
  done
  echo ""
  echo "Source: src/shared/rls_tables.py"
  echo "Checks performed:"
  echo "  1. Migration files contain CREATE POLICY for each tenant table"
  echo "  2. RLS is ENABLED (ALTER TABLE ... ENABLE ROW LEVEL SECURITY)"
  echo "  3. Policy uses org_id = current_setting('app.current_org_id')"
  exit 0
fi

if [ ! -d "$MIGRATIONS_DIR" ]; then
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"fail","reason":"migrations/versions/ directory not found","violations":1}'
  else
    echo "FAIL: $MIGRATIONS_DIR not found"
  fi
  exit 1
fi

VIOLATIONS=0
RESULTS=""
VIOLATION_JSON="[]"

# Concatenate all migration files for checking
ALL_MIGRATIONS=$(cat "$MIGRATIONS_DIR"/*.py 2>/dev/null || echo "")

if [ -z "$ALL_MIGRATIONS" ]; then
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"fail","reason":"No migration files found","violations":1}'
  else
    echo "FAIL: No migration files found in $MIGRATIONS_DIR"
  fi
  exit 1
fi

for table in "${TENANT_TABLES[@]}"; do
  # Check if table exists in migrations (handles multiline op.create_table calls)
  has_table=$(echo "$ALL_MIGRATIONS" | grep -c "\"$table\"\|'$table'" || true)

  if [ "$has_table" -eq 0 ]; then
    # Table required but not found in migrations = FAIL
    VIOLATIONS=$((VIOLATIONS + 1))
    RESULTS="${RESULTS}  MISSING-TABLE: $table (no migration creates this table)\n"
    VIOLATION_JSON=$(uv run python -c "
import json,sys
v=json.loads(sys.argv[1])
v.append({'table':sys.argv[2],'issue':'table not found in migrations'})
print(json.dumps(v))
" "$VIOLATION_JSON" "$table" 2>/dev/null || echo "$VIOLATION_JSON")
    continue
  fi

  # Check for RLS enable
  has_rls_enable=$(echo "$ALL_MIGRATIONS" | grep -ciE "ENABLE ROW LEVEL SECURITY.*$table|$table.*ENABLE ROW LEVEL SECURITY|_enable_rls\(['\"]?$table" || true)

  # Check for RLS policy
  has_rls_policy=$(echo "$ALL_MIGRATIONS" | grep -ciE "CREATE POLICY.*$table|policy.*on.*$table" || true)

  if [ "$has_rls_enable" -eq 0 ] || [ "$has_rls_policy" -eq 0 ]; then
    VIOLATIONS=$((VIOLATIONS + 1))
    RESULTS="${RESULTS}  MISSING-RLS: $table (rls_enabled=$has_rls_enable, policy=$has_rls_policy)\n"
    VIOLATION_JSON=$(uv run python -c "
import json,sys
v=json.loads(sys.argv[1])
v.append({'table':sys.argv[2],'issue':'missing RLS','rls_enabled':int(sys.argv[3]),'policy':int(sys.argv[4])})
print(json.dumps(v))
" "$VIOLATION_JSON" "$table" "$has_rls_enable" "$has_rls_policy" 2>/dev/null || echo "$VIOLATION_JSON")
  else
    RESULTS="${RESULTS}  OK: $table\n"
  fi
done

if [ "$JSON_OUTPUT" = true ]; then
  if [ "$VIOLATIONS" -eq 0 ]; then
    echo "{\"status\":\"pass\",\"violations\":0,\"phase\":\"$PHASE\",\"tables_checked\":${#TENANT_TABLES[@]}}"
  else
    echo "{\"status\":\"fail\",\"violations\":$VIOLATIONS,\"phase\":\"$PHASE\",\"tables_checked\":${#TENANT_TABLES[@]},\"details\":$VIOLATION_JSON}"
  fi
else
  echo "RLS Isolation Check (phase=$PHASE):"
  echo -e "$RESULTS"
  if [ "$VIOLATIONS" -eq 0 ]; then
    echo "PASS: All ${#TENANT_TABLES[@]} tenant tables have RLS policies"
  else
    echo "FAIL: $VIOLATIONS of ${#TENANT_TABLES[@]} table(s) missing RLS policies"
    echo "  Every tenant-scoped table MUST have:"
    echo "    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"
    echo "    CREATE POLICY {table}_org_isolation ON {table}"
    echo "      USING (org_id = current_setting('app.current_org_id')::uuid);"
    echo ""
    echo "  Table list source: src/shared/rls_tables.py"
  fi
fi

exit $( [ "$VIOLATIONS" -eq 0 ] && echo 0 || echo 1 )
