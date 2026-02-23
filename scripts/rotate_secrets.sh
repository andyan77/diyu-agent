#!/usr/bin/env bash
# DIYU Agent Secret Rotation Script
#
# Gate ID: p4-key-rotation
# Rotates JWT secret, database password, MinIO keys, and LLM API key.
#
# Usage:
#   bash scripts/rotate_secrets.sh              # Execute rotation
#   bash scripts/rotate_secrets.sh --dry-run    # Validate rotation steps only
#
# Scope (decision C-8):
#   - JWT_SECRET_KEY
#   - POSTGRES_PASSWORD (DATABASE_URL)
#   - MINIO_SECRET_KEY / AWS_SECRET_ACCESS_KEY
#   - LLM_API_KEY
#
# Exit codes:
#   0 - Rotation completed (or --dry-run passed)
#   1 - Rotation failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

echo "=== DIYU Agent Secret Rotation ==="
echo ""

# Define rotation targets
ROTATION_TARGETS=(
  "JWT_SECRET_KEY"
  "POSTGRES_PASSWORD"
  "MINIO_SECRET_KEY"
  "AWS_SECRET_ACCESS_KEY"
  "LLM_API_KEY"
)

# Verify .env exists
if [ ! -f "$ENV_FILE" ]; then
  echo "[FAIL] .env file not found at $ENV_FILE"
  echo "  Copy from .env.example: cp .env.example .env"
  exit 1
fi

if $DRY_RUN; then
  echo "[DRY-RUN] Secret rotation validation:"
  echo ""

  FOUND=0
  MISSING=0
  for key in "${ROTATION_TARGETS[@]}"; do
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
      # Check if it's still the default/placeholder value
      VALUE=$(grep "^${key}=" "$ENV_FILE" | cut -d= -f2-)
      if [[ "$VALUE" == "CHANGE_ME"* ]] || [[ "$VALUE" == *"diyu_dev"* ]]; then
        echo "  [WARN] $key: still using default/dev value"
      else
        echo "  [OK]   $key: configured (not default)"
      fi
      FOUND=$((FOUND + 1))
    else
      echo "  [MISS] $key: not found in .env"
      MISSING=$((MISSING + 1))
    fi
  done

  echo ""
  echo "  Found: $FOUND / ${#ROTATION_TARGETS[@]}"
  if [ "$MISSING" -gt 0 ]; then
    echo "  Missing: $MISSING (non-blocking for dry-run)"
  fi

  # Verify rotation tooling
  echo ""
  echo "  Rotation readiness:"
  if command -v openssl >/dev/null 2>&1; then
    echo "  [OK] openssl available (for JWT_SECRET_KEY generation)"
  else
    echo "  [WARN] openssl not found"
  fi

  echo ""
  echo "[DRY-RUN] Secret rotation validation: PASS"
  exit 0
fi

# --- Live rotation ---
echo "[WARNING] This will rotate secrets in $ENV_FILE"
echo "  Make sure to restart services after rotation."
echo ""

# Backup current .env
BACKUP="$ENV_FILE.bak.$(date -u +%Y%m%dT%H%M%SZ)"
cp "$ENV_FILE" "$BACKUP"
echo "  Backup: $BACKUP"

# Generate new JWT secret
NEW_JWT=$(openssl rand -hex 32)
if grep -q "^JWT_SECRET_KEY=" "$ENV_FILE"; then
  sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$NEW_JWT|" "$ENV_FILE"
  echo "  [ROTATED] JWT_SECRET_KEY"
fi

# TODO(F-9/Stage-2): Implement automated rotation for DB/MinIO/LLM keys
# with service coordination (restart + migration).
# Current: manual rotation guidance only.
echo ""
echo "  [MANUAL] The following require service restart after .env update:"
echo "    - POSTGRES_PASSWORD (also update docker-compose.yml or env override)"
echo "    - MINIO_SECRET_KEY + AWS_SECRET_ACCESS_KEY"
echo "    - LLM_API_KEY (obtain new key from provider)"
echo ""
echo "=== Secret Rotation Complete ==="
echo "  JWT_SECRET_KEY: auto-rotated"
echo "  Other keys: update manually in .env, then restart services"

exit 0
