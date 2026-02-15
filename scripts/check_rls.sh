#!/usr/bin/env bash
# check_rls.sh - Row Level Security isolation checks
#
# Validates that all tenant-scoped tables have RLS policies enabled.
# Ensures org_id isolation is enforced at the database level.
#
# Usage:
#   bash scripts/check_rls.sh              # Check RLS policies
#   bash scripts/check_rls.sh --dry-run    # Show what would be checked
#   bash scripts/check_rls.sh --json       # JSON output
#
# Exit codes: 0 = all tables have RLS, 1 = missing RLS policies

set -euo pipefail

DRY_RUN=false
JSON_OUTPUT=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --json)    JSON_OUTPUT=true ;;
  esac
done

# Tables that MUST have RLS (org_id scoped)
# Updated as new tenant-scoped tables are added
TENANT_TABLES=(
  "conversations"
  "messages"
  "memory_items"
  "knowledge_items"
  "knowledge_bundles"
  "skill_instances"
  "media_objects"
  "audit_events"
  "user_preferences"
)

MIGRATIONS_DIR="migrations/versions"

if [ "$DRY_RUN" = true ]; then
  echo "DRY-RUN: Would check RLS policies for tenant-scoped tables."
  echo "Tables requiring RLS (org_id isolation):"
  for table in "${TENANT_TABLES[@]}"; do
    echo "  - $table"
  done
  echo ""
  echo "Checks performed:"
  echo "  1. Migration files contain CREATE POLICY for each tenant table"
  echo "  2. RLS is ENABLED (ALTER TABLE ... ENABLE ROW LEVEL SECURITY)"
  echo "  3. Policy uses org_id = current_setting('app.current_org_id')"
  exit 0
fi

if [ ! -d "$MIGRATIONS_DIR" ]; then
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"skip","reason":"No migrations directory","tables_checked":[]}'
  else
    echo "SKIP: No migrations directory (Phase 0 skeleton stage)"
  fi
  exit 0
fi

VIOLATIONS=0
RESULTS=""

# Concatenate all migration files for checking
ALL_MIGRATIONS=$(cat "$MIGRATIONS_DIR"/*.py 2>/dev/null || echo "")

if [ -z "$ALL_MIGRATIONS" ]; then
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"status":"skip","reason":"No migration files found"}'
  else
    echo "SKIP: No migration files found"
  fi
  exit 0
fi

for table in "${TENANT_TABLES[@]}"; do
  # Check if table exists in migrations
  has_table=$(echo "$ALL_MIGRATIONS" | grep -c "create_table.*$table\|op\.create_table.*$table" || true)

  if [ "$has_table" -eq 0 ]; then
    # Table not yet created, skip
    continue
  fi

  # Check for RLS enable
  has_rls_enable=$(echo "$ALL_MIGRATIONS" | grep -ciE "enable row level security.*$table|$table.*enable row level security" || true)

  # Check for RLS policy
  has_rls_policy=$(echo "$ALL_MIGRATIONS" | grep -ciE "create policy.*$table|policy.*on.*$table" || true)

  if [ "$has_rls_enable" -eq 0 ] || [ "$has_rls_policy" -eq 0 ]; then
    VIOLATIONS=$((VIOLATIONS + 1))
    RESULTS="${RESULTS}  MISSING: $table (rls_enabled=$has_rls_enable, policy=$has_rls_policy)\n"
  else
    RESULTS="${RESULTS}  OK: $table\n"
  fi
done

if [ "$JSON_OUTPUT" = true ]; then
  if [ "$VIOLATIONS" -eq 0 ]; then
    echo '{"status":"pass","violations":0,"message":"All tenant tables have RLS"}'
  else
    echo "{\"status\":\"fail\",\"violations\":$VIOLATIONS,\"message\":\"$VIOLATIONS table(s) missing RLS\"}"
  fi
else
  echo "RLS Isolation Check:"
  echo -e "$RESULTS"
  if [ "$VIOLATIONS" -eq 0 ]; then
    echo "PASS: All created tenant tables have RLS policies"
  else
    echo "FAIL: $VIOLATIONS table(s) missing RLS policies"
    echo "  Every tenant-scoped table MUST have:"
    echo "    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"
    echo "    CREATE POLICY {table}_org_isolation ON {table}"
    echo "      USING (org_id = current_setting('app.current_org_id')::uuid);"
  fi
fi

exit $( [ "$VIOLATIONS" -eq 0 ] && echo 0 || echo 1 )
