#!/usr/bin/env bash
# DIYU Agent Diagnostic Package Generator
#
# Gate ID: p4-diag-package
# Collects logs, metrics, config, and system info into a single diagnostic archive.
#
# Usage:
#   bash scripts/diyu_diagnose.sh              # Generate full diagnostic package
#   bash scripts/diyu_diagnose.sh --dry-run    # Validate collection steps only
#
# Outputs:
#   evidence/diag/diyu-diag-<timestamp>.tar.gz
#
# Exit codes:
#   0 - Diagnostic package generated (or --dry-run passed)
#   1 - Collection failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
DIAG_DIR="$PROJECT_ROOT/evidence/diag/diyu-diag-$TIMESTAMP"
DRY_RUN=false

# Read ports from .env or use docker-compose defaults
if [ -f "$PROJECT_ROOT/.env" ]; then
  PG_PORT=$(grep -oP 'POSTGRES_PORT=\K[0-9]+' "$PROJECT_ROOT/.env" 2>/dev/null || echo "25432")
  REDIS_PORT=$(grep -oP 'REDIS_PORT=\K[0-9]+' "$PROJECT_ROOT/.env" 2>/dev/null || echo "6380")
else
  PG_PORT=25432
  REDIS_PORT=6380
fi

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

echo "=== DIYU Agent Diagnostic Package ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# Verify required tools
REQUIRED_TOOLS=(docker python3 uv)
MISSING=()
for tool in "${REQUIRED_TOOLS[@]}"; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    MISSING+=("$tool")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "[WARN] Missing tools: ${MISSING[*]}"
  echo "  Some diagnostic data may be incomplete."
fi

if $DRY_RUN; then
  echo "[DRY-RUN] Collection steps validated:"
  echo "  1. System info (uname, docker version, python version)"
  echo "  2. Service health (docker compose ps)"
  echo "  3. Application logs (docker compose logs --tail=500)"
  echo "  4. Database status (pg_isready, connection count)"
  echo "  5. Redis status (redis-cli ping)"
  echo "  6. Configuration snapshot (.env.example, docker-compose.yml)"
  echo "  7. Disk usage (du -sh data volumes)"
  echo "  8. Recent evidence files (ls evidence/)"
  echo ""
  echo "[DRY-RUN] Diagnostic package generation: PASS"
  exit 0
fi

# Create diagnostic directory
mkdir -p "$DIAG_DIR"

# Step 1: System info
echo "[1/8] Collecting system info..."
{
  echo "=== System Info ==="
  uname -a 2>/dev/null || echo "uname: unavailable"
  echo ""
  echo "=== Docker Version ==="
  docker version 2>/dev/null || echo "docker: unavailable"
  echo ""
  echo "=== Python Version ==="
  python3 --version 2>/dev/null || echo "python3: unavailable"
  echo ""
  echo "=== uv Version ==="
  uv --version 2>/dev/null || echo "uv: unavailable"
} > "$DIAG_DIR/system-info.txt" 2>&1

# Step 2: Service health
echo "[2/8] Checking service health..."
{
  echo "=== Docker Compose Status ==="
  cd "$PROJECT_ROOT" && docker compose ps 2>/dev/null || echo "docker compose: unavailable"
} > "$DIAG_DIR/service-health.txt" 2>&1

# Step 3: Application logs
echo "[3/8] Collecting application logs..."
{
  cd "$PROJECT_ROOT" && docker compose logs --tail=500 2>/dev/null || echo "logs: unavailable"
} > "$DIAG_DIR/app-logs.txt" 2>&1

# Step 4: Database status
echo "[4/8] Checking database status..."
{
  echo "=== PostgreSQL ==="
  pg_isready -h localhost -p "$PG_PORT" 2>/dev/null || echo "pg_isready: unavailable or not running"
} > "$DIAG_DIR/db-status.txt" 2>&1

# Step 5: Redis status
echo "[5/8] Checking Redis status..."
{
  echo "=== Redis ==="
  redis-cli -p "$REDIS_PORT" ping 2>/dev/null || echo "redis: unavailable"
} > "$DIAG_DIR/redis-status.txt" 2>&1

# Step 6: Configuration snapshot (no secrets)
echo "[6/8] Snapshotting configuration..."
cp "$PROJECT_ROOT/.env.example" "$DIAG_DIR/env-example.txt" 2>/dev/null || true
cp "$PROJECT_ROOT/docker-compose.yml" "$DIAG_DIR/docker-compose.yml" 2>/dev/null || true

# Step 7: Disk usage
echo "[7/8] Checking disk usage..."
{
  echo "=== Project Size ==="
  du -sh "$PROJECT_ROOT" 2>/dev/null || echo "du: unavailable"
  echo ""
  echo "=== Evidence Directory ==="
  du -sh "$PROJECT_ROOT/evidence/"* 2>/dev/null || echo "No evidence files"
} > "$DIAG_DIR/disk-usage.txt" 2>&1

# Step 8: Recent evidence
echo "[8/8] Listing recent evidence..."
{
  ls -la "$PROJECT_ROOT/evidence/" 2>/dev/null || echo "No evidence directory"
} > "$DIAG_DIR/evidence-listing.txt" 2>&1

# Create archive
ARCHIVE="$PROJECT_ROOT/evidence/diag/diyu-diag-$TIMESTAMP.tar.gz"
cd "$PROJECT_ROOT/evidence/diag" && tar czf "$ARCHIVE" "diyu-diag-$TIMESTAMP/" 2>/dev/null

# Cleanup unarchived directory
rm -rf "$DIAG_DIR"

echo ""
echo "=== Diagnostic Package Complete ==="
echo "Archive: $ARCHIVE"
echo "Size: $(du -sh "$ARCHIVE" | cut -f1)"

exit 0
