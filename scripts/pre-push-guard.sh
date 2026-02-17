#!/usr/bin/env bash
# Pre-push guard -- compensating control for missing GitHub branch protection.
#
# Install: cp scripts/pre-push-guard.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
# Or:      ln -sf ../../scripts/pre-push-guard.sh .git/hooks/pre-push
#
# Blocks direct push to main unless all checks pass.
set -euo pipefail

PROTECTED_BRANCH="main"

while read -r _local_ref _local_sha remote_ref _remote_sha; do
  branch_name="${remote_ref##refs/heads/}"
  if [ "$branch_name" = "$PROTECTED_BRANCH" ]; then
    echo "[pre-push-guard] Push to '$PROTECTED_BRANCH' detected. Running checks..."

    echo "  [1/4] ruff check..."
    uv run ruff check src/ scripts/ tests/ --quiet || {
      echo "BLOCKED: ruff check failed. Fix lint errors before pushing to $PROTECTED_BRANCH."
      exit 1
    }

    echo "  [2/4] ruff format --check..."
    uv run ruff format --check src/ scripts/ tests/ --quiet || {
      echo "BLOCKED: ruff format failed. Run 'uv run ruff format' before pushing to $PROTECTED_BRANCH."
      exit 1
    }

    echo "  [3/4] pytest (unit)..."
    uv run pytest tests/unit/ -q --tb=line -x || {
      echo "BLOCKED: unit tests failed. Fix tests before pushing to $PROTECTED_BRANCH."
      exit 1
    }

    echo "  [4/4] layer boundary check..."
    bash scripts/check_layer_deps.sh --quiet 2>/dev/null || {
      echo "BLOCKED: layer boundary violations. Fix imports before pushing to $PROTECTED_BRANCH."
      exit 1
    }

    echo "[pre-push-guard] All checks passed. Push to '$PROTECTED_BRANCH' allowed."
  fi
done

exit 0
