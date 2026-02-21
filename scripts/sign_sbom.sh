#!/usr/bin/env bash
# DIYU Agent SBOM signing script (D3-5, soft gate).
#
# Purpose: Generate Software Bill of Materials (SBOM) and sign it using cosign.
# This is a soft gate: if cosign is unavailable, SBOM is still generated but unsigned.
#
# Usage:
#   bash scripts/sign_sbom.sh
#
# Outputs:
#   - evidence/sbom.json (combined Python + frontend SBOM)
#   - evidence/sbom.json.bundle (cosign signature, if cosign available)
#
# Exit codes:
#   0 - SBOM generated (and signed if cosign available)
#   1 - SBOM generation failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EVIDENCE_DIR="$PROJECT_ROOT/evidence"
SBOM_FILE="$EVIDENCE_DIR/sbom.json"

echo "=== DIYU Agent SBOM Generator ==="
echo ""

# --- Step 1: Create evidence directory if needed ---
mkdir -p "$EVIDENCE_DIR"

# --- Step 2: Generate Python SBOM ---
echo "[1/3] Generating Python SBOM..."
cd "$PROJECT_ROOT"

PYTHON_SBOM=$(uv pip list --format json 2>/dev/null || echo "[]")
if [ "$PYTHON_SBOM" = "[]" ]; then
  echo "  WARNING: No Python packages found or uv pip list failed"
fi

# --- Step 3: Generate frontend SBOM ---
echo "[2/3] Generating frontend SBOM..."
cd "$PROJECT_ROOT/frontend"

FRONTEND_SBOM="[]"
if [ -f "package.json" ]; then
  # Use pnpm list --json and extract the dependencies
  if PNPM_OUTPUT=$(pnpm list --json 2>/dev/null); then
    # pnpm list --json returns an array, take the first element
    FRONTEND_SBOM=$(echo "$PNPM_OUTPUT" | jq '.[0].dependencies // {}' 2>/dev/null || echo "{}")

    # Convert pnpm format to simple array format
    if [ "$FRONTEND_SBOM" != "{}" ]; then
      FRONTEND_SBOM=$(echo "$FRONTEND_SBOM" | jq '[to_entries | .[] | {name: .key, version: .value.version}]' 2>/dev/null || echo "[]")
    else
      FRONTEND_SBOM="[]"
    fi
  else
    echo "  WARNING: pnpm list failed, frontend SBOM may be incomplete"
  fi
fi

cd "$PROJECT_ROOT"

# --- Step 4: Combine SBOMs ---
echo "[3/3] Combining SBOMs..."

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Create combined SBOM JSON
cat > "$SBOM_FILE" <<EOF
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "version": 1,
  "metadata": {
    "timestamp": "$TIMESTAMP",
    "component": {
      "type": "application",
      "name": "diyu-agent",
      "version": "0.1.0"
    }
  },
  "components": {
    "python": $PYTHON_SBOM,
    "frontend": $FRONTEND_SBOM
  }
}
EOF

echo "  ✓ SBOM written to $SBOM_FILE"

# --- Step 5: Sign SBOM with cosign (soft gate) ---
if command -v cosign >/dev/null 2>&1; then
  echo ""
  echo "[Bonus] Signing SBOM with cosign..."

  if cosign sign-blob --bundle "${SBOM_FILE}.bundle" "$SBOM_FILE" 2>/dev/null; then
    echo "  ✓ SBOM signed successfully"
    echo "  ✓ Signature bundle: ${SBOM_FILE}.bundle"
  else
    echo "  WARNING: cosign signing failed (requires keyless mode or key setup)"
    echo "  SBOM generated but unsigned"
  fi
else
  echo ""
  echo "[Info] cosign not found - SBOM generated but unsigned"
  echo "  This is a soft gate. Install cosign for signed SBOMs in production."
fi

echo ""
echo "=== SBOM Generation Complete ==="

exit 0
