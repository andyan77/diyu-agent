#!/usr/bin/env bash
# Check milestone matrix [E2E] acceptance commands for text placeholders.
#
# Per governance-optimization-plan.md Section 8.3:
# - Before FW0-8 merges: SKIP (E2E placeholders allowed)
# - After FW0-8 merges: FAIL if any [E2E] command is plain text (not backtick-wrapped)
#
# Dual-channel detection (per review feedback):
#   1. FW08_MERGED=true env var (priority, stable in CI)
#   2. git log grep fallback (local dev convenience)
#
# Exit codes:
#   0 - PASS or SKIP
#   1 - FAIL (text placeholders found)

set -euo pipefail

MATRIX_FILES="docs/governance/milestone-matrix-backend.md
docs/governance/milestone-matrix-frontend.md
docs/governance/milestone-matrix-crosscutting.md"

# --- Detect FW0-8 merge status ---
fw08_merged=false

# Channel 1: explicit env var (CI-friendly, survives shallow clone)
if [ "${FW08_MERGED:-}" = "true" ]; then
  fw08_merged=true
fi

# Channel 2: git log fallback (may miss in shallow clone)
if [ "$fw08_merged" = "false" ] && command -v git >/dev/null 2>&1; then
  if git log --oneline --all --grep="FW0-8" 2>/dev/null | head -1 | grep -q .; then
    fw08_merged=true
  fi
fi

if [ "$fw08_merged" = "false" ]; then
  echo "SKIP: FW0-8 not yet merged, E2E placeholders allowed"
  exit 0
fi

# --- Check for text placeholders ---
# Match lines with [E2E] followed by non-backtick content (plain text description)
VIOLATIONS=""
for f in $MATRIX_FILES; do
  if [ -f "$f" ]; then
    result=$(grep -Pn '^\| .+ \| \[E2E\] [^`|]' "$f" 2>/dev/null || true)
    if [ -n "$result" ]; then
      VIOLATIONS="${VIOLATIONS}${f}:\n${result}\n\n"
    fi
  fi
done

if [ -n "$VIOLATIONS" ]; then
  echo "FAIL: E2E acceptance commands contain text placeholders:"
  echo ""
  echo -e "$VIOLATIONS"
  echo "ACTION: Replace text descriptions with executable Playwright commands"
  echo "  Example: [E2E] \`pnpm exec playwright test tests/e2e/login.spec.ts\`"
  exit 1
fi

echo "PASS: All [E2E] acceptance commands are machine-judgeable"
exit 0
