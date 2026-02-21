#!/usr/bin/env bash
# DIYU Agent product installer script.
#
# Purpose: Install DIYU Agent on a customer/staging environment.
# This is the main entry point for product deployment (D3-2).
#
# Usage:
#   bash delivery/install.sh
#
# Prerequisites:
#   - Docker 24+ and Docker Compose 2+
#   - Python 3.12+
#   - Node.js 22+ and pnpm 9+ (for frontend)
#   - uv (Python package manager)
#
# Exit codes:
#   0 - Installation successful
#   1 - Installation failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== DIYU Agent Installer ==="
echo ""

# --- Step 1: Check prerequisites ---
echo "[1/7] Checking prerequisites..."

check_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "  ERROR: $cmd not found. Please install $cmd first."
    exit 1
  fi
  echo "  ✓ $cmd found"
}

check_command docker
check_command docker
check_command uv
check_command pnpm
check_command node

echo ""

# --- Step 2: Run preflight check ---
echo "[2/7] Running preflight check..."
if [ -f "$SCRIPT_DIR/preflight.sh" ]; then
  if bash "$SCRIPT_DIR/preflight.sh"; then
    echo "  ✓ Preflight check passed"
  else
    echo "  ERROR: Preflight check failed. Please fix issues above and retry."
    exit 1
  fi
else
  echo "  WARNING: preflight.sh not found, skipping..."
fi

echo ""

# --- Step 3: Copy .env.example to .env if needed ---
echo "[3/7] Setting up environment configuration..."
cd "$PROJECT_ROOT"

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "  ✓ Created .env from .env.example"
    echo "  NOTE: Please review and update .env with your actual configuration."
  else
    echo "  WARNING: .env.example not found, skipping .env creation..."
  fi
else
  echo "  ✓ .env already exists"
fi

echo ""

# --- Step 4: Start Docker services ---
echo "[4/7] Starting Docker services..."
if docker compose up -d; then
  echo "  ✓ Docker services started"
else
  echo "  ERROR: Failed to start Docker services"
  exit 1
fi

echo ""

# --- Step 5: Install Python dependencies ---
echo "[5/7] Installing Python dependencies..."
if uv sync --dev; then
  echo "  ✓ Python dependencies installed"
else
  echo "  ERROR: Failed to install Python dependencies"
  exit 1
fi

echo ""

# --- Step 6: Install frontend dependencies ---
echo "[6/7] Installing frontend dependencies..."
cd "$PROJECT_ROOT/frontend"
if pnpm install; then
  echo "  ✓ Frontend dependencies installed"
else
  echo "  ERROR: Failed to install frontend dependencies"
  exit 1
fi

cd "$PROJECT_ROOT"
echo ""

# --- Step 7: Final health check ---
echo "[7/7] Running final health check..."
if make doctor; then
  echo "  ✓ Health check passed"
else
  echo "  WARNING: Health check reported issues. Please review above."
  echo "  Installation completed but may require manual intervention."
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "  1. Review and update .env with your configuration"
echo "  2. Run database migrations: make migrate"
echo "  3. Start the backend: make dev"
echo "  4. Start the frontend: cd frontend && pnpm dev"
echo ""

exit 0
