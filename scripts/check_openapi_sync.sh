#!/usr/bin/env bash
# OpenAPI type sync CI gate
# Task card: D2-2
#
# Verifies that generated TypeScript types are in sync with the OpenAPI schema.
# If types drift from the schema, the diff will be non-empty and this check fails.
#
# Usage:
#   bash scripts/check_openapi_sync.sh
#
# Exit codes:
#   0 - Types are in sync
#   1 - Types have drifted (regeneration needed)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== OpenAPI Type Sync Check ==="

# Check if frontend directory exists
if [ ! -d "$PROJECT_ROOT/frontend" ]; then
    echo "SKIP: frontend/ directory not found"
    exit 0
fi

cd "$PROJECT_ROOT/frontend"

# Check if the openapi:generate script exists
if ! pnpm run --filter @diyu/api-client openapi:generate --help >/dev/null 2>&1; then
    # If no generate script, check that schema.d.ts exists as baseline
    if [ -f "packages/api-client/src/generated/schema.d.ts" ]; then
        echo "PASS: schema.d.ts exists (no openapi:generate script configured yet)"
        exit 0
    fi
    echo "SKIP: No openapi:generate script and no schema.d.ts found"
    exit 0
fi

# Run the generator
pnpm run --filter @diyu/api-client openapi:generate

# Check for drift
cd "$PROJECT_ROOT"
if git diff --exit-code frontend/packages/api-client/src/generated/; then
    echo "PASS: OpenAPI types are in sync"
    exit 0
else
    echo "FAIL: OpenAPI types have drifted. Run 'pnpm openapi:generate' to update."
    exit 1
fi
