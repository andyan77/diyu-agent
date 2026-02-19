#!/usr/bin/env bash
# security_scan.sh - Unified security scanning entry point
#
# Single entry point for all security scanning across the project.
# Called by: Makefile, CI workflow, pre-commit hook, full_audit.sh, verify_phase.py
#
# Modes:
#   --quick   Scan staged files only (pre-commit). Tool missing = exit 2 (fail-closed).
#   --full    Full scan: semgrep + pip-audit. Tool missing = exit 2 (fail-closed).
#   --ci      Full scan + SARIF output + pnpm audit. Tool missing = exit 2.
#
# Exit codes:
#   0 = Pass (includes: no scannable files, or degraded with no findings)
#   1 = Blocking findings found
#   2 = Tool/config error (--full and --ci only)
#
# External service resilience:
#   pnpm audit and pip-audit depend on external registries (npmjs.org, pypi.org).
#   Infrastructure failures (HTTP 500, DNS, timeout) are distinguished from real
#   vulnerability findings. On infra failure: retry once, then WARN (not FAIL).
#   Emits GitHub Actions ::warning:: annotation when degraded.
#
# Severity: WARNING + ERROR block, INFO is informational only.
# Rule sets: p/default + p/python + p/docker-compose (no --config auto)
#
# gitleaks is NOT included here. In CI it runs as gitleaks-action@v2
# (Go binary with Git-native integration). Locally install separately.
#
# JSON summary (stdout): { reason, findings_count, tool_versions, ... }
# Diagnostic messages: stderr
#
# Usage:
#   bash scripts/security_scan.sh --quick          # pre-commit hook
#   bash scripts/security_scan.sh --full           # local deep scan / phase gate
#   bash scripts/security_scan.sh --ci             # CI with SARIF output

set -euo pipefail

MODE=""
EVIDENCE_DIR="evidence"
SARIF_FILE="${EVIDENCE_DIR}/security-scan.sarif"
SEMGREP_CONFIGS="--config p/default --config p/python --config p/docker-compose"
SCAN_TARGETS="src/ migrations/ scripts/ docker-compose.yml"

# Lockfiles and binary assets to exclude from --quick scanning
EXCLUDE_EXTENSIONS="md|png|jpg|jpeg|svg|gif|ico|lock|lockb|woff|woff2|ttf|eot"
EXCLUDE_FILES="pnpm-lock.yaml|package-lock.json|yarn.lock"

# --- Parse args ---
while [ $# -gt 0 ]; do
  case "$1" in
    --quick) MODE="quick" ;;
    --full)  MODE="full" ;;
    --ci)    MODE="ci" ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ -z "$MODE" ]; then
  echo "Usage: security_scan.sh --quick|--full|--ci" >&2
  exit 2
fi

# --- Helpers ---

json_summary() {
  local reason="$1"
  local findings="${2:-0}"
  local semgrep_ver="${3:-n/a}"
  local pip_audit_ver="${4:-n/a}"
  python3 -c "
import json, sys
print(json.dumps({
    'mode': sys.argv[1],
    'reason': sys.argv[2],
    'findings_count': int(sys.argv[3]),
    'tool_versions': {
        'semgrep': sys.argv[4],
        'pip_audit': sys.argv[5],
    },
}, ensure_ascii=False))
" "$MODE" "$reason" "$findings" "$semgrep_ver" "$pip_audit_ver"
}

minimal_sarif() {
  # Generate a minimal valid SARIF file (empty results)
  local reason="${1:-error}"
  mkdir -p "$EVIDENCE_DIR"
  python3 -c "
import json, sys
sarif = {
    '\$schema': 'https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json',
    'version': '2.1.0',
    'runs': [{
        'tool': {
            'driver': {
                'name': 'security_scan.sh',
                'version': '1.0.0',
                'informationUri': 'https://github.com/andyan77/diyu-agent',
            }
        },
        'results': [],
        'invocations': [{
            'executionSuccessful': sys.argv[1] == 'clean',
            'toolExecutionNotifications': [{
                'message': {'text': sys.argv[1]},
                'level': 'note',
            }],
        }],
    }],
}
with open(sys.argv[2], 'w') as f:
    json.dump(sarif, f, indent=2, ensure_ascii=False)
" "$reason" "$SARIF_FILE"
}

check_semgrep() {
  if command -v semgrep >/dev/null 2>&1; then
    semgrep --version 2>/dev/null | head -1
    return 0
  fi
  # Try uv-managed semgrep
  if command -v uv >/dev/null 2>&1 && uv run semgrep --version >/dev/null 2>&1; then
    uv run semgrep --version 2>/dev/null | head -1
    return 0
  fi
  return 1
}

run_semgrep() {
  # Use uv run if direct semgrep not available
  if command -v semgrep >/dev/null 2>&1; then
    semgrep "$@"
  else
    uv run semgrep "$@"
  fi
}

run_pip_audit() {
  if command -v uv >/dev/null 2>&1; then
    uv run pip-audit "$@"
  elif command -v pip-audit >/dev/null 2>&1; then
    pip-audit "$@"
  else
    return 1
  fi
}

# --- SARIF trap for --ci mode (ensure valid SARIF even on failure) ---
if [ "$MODE" = "ci" ]; then
  mkdir -p "$EVIDENCE_DIR"
  trap 'if [ ! -f "$SARIF_FILE" ]; then minimal_sarif "trap_fallback"; fi' EXIT
fi

# ============================================================
# MODE: --quick (staged files, pre-commit)
# ============================================================
if [ "$MODE" = "quick" ]; then
  # Check semgrep availability
  SEMGREP_VER=""
  SEMGREP_VER=$(check_semgrep 2>/dev/null) || true

  if [ -z "$SEMGREP_VER" ]; then
    echo "ERROR: semgrep not installed (install: uv tool install semgrep)" >&2
    json_summary "tool_missing" 0 "n/a"
    exit 2
  fi

  # Collect staged files safely (handles spaces/special chars)
  STAGED_FILES=()
  while IFS= read -r -d '' file; do
    STAGED_FILES+=("$file")
  done < <(git diff -z --cached --name-only --diff-filter=d 2>/dev/null || true)

  if [ ${#STAGED_FILES[@]} -eq 0 ]; then
    echo "No staged files to scan" >&2
    json_summary "no_scannable_files" 0 "$SEMGREP_VER"
    exit 0
  fi

  # Filter out non-code files
  SCANNABLE_FILES=()
  for f in "${STAGED_FILES[@]}"; do
    basename_f=$(basename "$f")
    # Skip by extension
    if echo "$basename_f" | grep -qiE "\.(${EXCLUDE_EXTENSIONS})$"; then
      continue
    fi
    # Skip known lockfiles
    if echo "$basename_f" | grep -qiE "^(${EXCLUDE_FILES})$"; then
      continue
    fi
    # Skip if file doesn't exist (shouldn't happen with --diff-filter=d, but safety)
    if [ -f "$f" ]; then
      SCANNABLE_FILES+=("$f")
    fi
  done

  if [ ${#SCANNABLE_FILES[@]} -eq 0 ]; then
    echo "No scannable code files in staged changes" >&2
    json_summary "no_scannable_files" 0 "$SEMGREP_VER"
    exit 0
  fi

  echo "Scanning ${#SCANNABLE_FILES[@]} staged file(s)..." >&2

  SCAN_EXIT=0
  run_semgrep scan \
    $SEMGREP_CONFIGS \
    --severity WARNING \
    --error \
    --quiet \
    --timeout 30 \
    "${SCANNABLE_FILES[@]}" 2>&2 || SCAN_EXIT=$?

  if [ "$SCAN_EXIT" -eq 0 ]; then
    json_summary "clean" 0 "$SEMGREP_VER"
    exit 0
  else
    # semgrep exit 1 = findings, other = error (treat as findings in quick mode)
    FINDING_COUNT=$(run_semgrep scan \
      $SEMGREP_CONFIGS \
      --severity WARNING \
      --json \
      --quiet \
      --timeout 30 \
      "${SCANNABLE_FILES[@]}" 2>/dev/null \
      | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('results',[])))" 2>/dev/null || echo "1")
    json_summary "findings" "$FINDING_COUNT" "$SEMGREP_VER"
    exit 1
  fi
fi

# ============================================================
# MODE: --full / --ci
# ============================================================

SEMGREP_VER=""
SEMGREP_VER=$(check_semgrep 2>/dev/null) || true

if [ -z "$SEMGREP_VER" ]; then
  echo "ERROR: semgrep not installed (required for --${MODE} mode)" >&2
  if [ "$MODE" = "ci" ]; then
    minimal_sarif "tool_error"
  fi
  json_summary "tool_error" 0 "n/a"
  exit 2
fi

TOTAL_FINDINGS=0
HAD_ERROR=false
PNPM_DEGRADED=false
PA_DEGRADED=false

# --- Semgrep ---
echo "=== SAST (semgrep ${SEMGREP_VER}) ===" >&2

SEMGREP_ARGS=(scan $SEMGREP_CONFIGS --severity WARNING --error --quiet)

if [ "$MODE" = "ci" ]; then
  mkdir -p "$EVIDENCE_DIR"
  # Run with SARIF output
  SCAN_EXIT=0
  run_semgrep scan \
    $SEMGREP_CONFIGS \
    --severity WARNING \
    --error \
    --sarif \
    --output "$SARIF_FILE" \
    $SCAN_TARGETS 2>&2 || SCAN_EXIT=$?

  # ALWAYS parse SARIF for findings count, regardless of exit code.
  # semgrep --sarif --output may return 0 even with blocking findings.
  # Exclude nosemgrep-suppressed results (they have suppressions: [{kind: "inSource"}]).
  if [ -f "$SARIF_FILE" ]; then
    FC=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    sarif = json.load(f)
total = 0
for run in sarif.get('runs', []):
    for r in run.get('results', []):
        if not r.get('suppressions'):
            total += 1
print(total)
" "$SARIF_FILE" 2>/dev/null || echo "0")
    TOTAL_FINDINGS=$((TOTAL_FINDINGS + FC))
  elif [ "$SCAN_EXIT" -ne 0 ]; then
    # No SARIF produced and semgrep failed: count as at least 1 finding
    TOTAL_FINDINGS=$((TOTAL_FINDINGS + 1))
  fi
else
  # --full mode: run with JSON to reliably count findings.
  # Do NOT rely on exit code alone (--error flag may not reflect all rules).
  FULL_JSON=$(mktemp /tmp/semgrep-full-XXXXXX.json)
  SCAN_EXIT=0
  run_semgrep scan \
    $SEMGREP_CONFIGS \
    --severity WARNING \
    --json \
    --output "$FULL_JSON" \
    $SCAN_TARGETS 2>&2 || SCAN_EXIT=$?

  FC=0
  if [ -f "$FULL_JSON" ]; then
    FC=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
print(len(data.get('results', [])))
" "$FULL_JSON" 2>/dev/null || echo "0")
  fi
  # If semgrep itself errored and produced no output, treat as error
  if [ "$SCAN_EXIT" -ne 0 ] && [ "$FC" -eq 0 ] && [ ! -s "$FULL_JSON" ]; then
    FC=1
  fi
  TOTAL_FINDINGS=$((TOTAL_FINDINGS + FC))

  # Display findings in human-readable format if any
  if [ "$FC" -gt 0 ] && [ -f "$FULL_JSON" ]; then
    run_semgrep scan \
      $SEMGREP_CONFIGS \
      --severity WARNING \
      $SCAN_TARGETS 2>&2 || true
  fi
  rm -f "$FULL_JSON"
fi
echo "  semgrep: ${TOTAL_FINDINGS} finding(s)" >&2

# --- pip-audit ---
echo "=== Dependency Audit (pip-audit) ===" >&2
PIP_AUDIT_VER=""
PIP_AUDIT_VER=$(uv run pip-audit --version 2>/dev/null | head -1 || echo "")

if [ -z "$PIP_AUDIT_VER" ]; then
  echo "ERROR: pip-audit not available" >&2
  HAD_ERROR=true
else
  PA_INFRA_ERROR_PATTERNS="ConnectionError|ReadTimeout|ECONNREFUSED|ETIMEDOUT|ENOTFOUND|ServiceUnavailable|HTTPError.*50[0-9]|Connection aborted"
  PA_OUTPUT_FILE=$(mktemp /tmp/pip-audit-XXXXXX.log)
  PA_EXIT=0
  run_pip_audit >"$PA_OUTPUT_FILE" 2>&1 || PA_EXIT=$?
  if [ "$PA_EXIT" -eq 0 ]; then
    cat "$PA_OUTPUT_FILE" >&2
    echo "  pip-audit: PASS" >&2
  elif grep -qiE "$PA_INFRA_ERROR_PATTERNS" "$PA_OUTPUT_FILE"; then
    echo "  pip-audit: WARN (PyPI unavailable, degraded)" >&2
    cat "$PA_OUTPUT_FILE" >&2
    PA_DEGRADED=true
  else
    cat "$PA_OUTPUT_FILE" >&2
    echo "  pip-audit: FAIL (vulnerable dependencies found)" >&2
    TOTAL_FINDINGS=$((TOTAL_FINDINGS + 1))
  fi
  rm -f "$PA_OUTPUT_FILE"
fi

# --- pnpm audit (--ci only) ---
# NOTE: pnpm audit depends on registry.npmjs.org which can have outages.
# We distinguish infrastructure failures (HTTP 500, DNS, timeout) from
# real vulnerability findings to avoid false CI blocks.
if [ "$MODE" = "ci" ]; then
  echo "=== Frontend Dependency Audit (pnpm audit) ===" >&2
  if command -v pnpm >/dev/null 2>&1 && [ -d "frontend" ]; then
    PNPM_INFRA_ERROR_PATTERNS="ERR_PNPM_AUDIT_BAD_RESPONSE|ECONNREFUSED|ETIMEDOUT|ENOTFOUND|EAI_AGAIN|Internal Server Error|fetch failed|socket hang up"
    PNPM_MAX_RETRIES=2
    PNPM_RETRY_DELAY=15
    PNPM_RESOLVED=false

    for attempt in $(seq 1 "$PNPM_MAX_RETRIES"); do
      PNPM_OUTPUT_FILE=$(mktemp /tmp/pnpm-audit-XXXXXX.log)
      PNPM_EXIT=0
      (cd frontend && pnpm audit --audit-level=high) \
        >"$PNPM_OUTPUT_FILE" 2>&1 || PNPM_EXIT=$?

      if [ "$PNPM_EXIT" -eq 0 ]; then
        echo "  pnpm audit: PASS" >&2
        PNPM_RESOLVED=true
        rm -f "$PNPM_OUTPUT_FILE"
        break
      fi

      # Check if failure is infrastructure (not a real finding)
      if grep -qiE "$PNPM_INFRA_ERROR_PATTERNS" "$PNPM_OUTPUT_FILE"; then
        if [ "$attempt" -lt "$PNPM_MAX_RETRIES" ]; then
          echo "  pnpm audit: registry error (attempt $attempt/$PNPM_MAX_RETRIES), retrying in ${PNPM_RETRY_DELAY}s..." >&2
          sleep "$PNPM_RETRY_DELAY"
          rm -f "$PNPM_OUTPUT_FILE"
          continue
        fi
        # All retries exhausted -- infrastructure failure, not a finding
        echo "  pnpm audit: WARN (registry unavailable after $PNPM_MAX_RETRIES attempts, degraded)" >&2
        cat "$PNPM_OUTPUT_FILE" >&2
        PNPM_DEGRADED=true
        PNPM_RESOLVED=true
        rm -f "$PNPM_OUTPUT_FILE"
        break
      else
        # Real vulnerability finding (not infra error)
        echo "  pnpm audit: FAIL (high+ vulnerabilities)" >&2
        cat "$PNPM_OUTPUT_FILE" >&2
        TOTAL_FINDINGS=$((TOTAL_FINDINGS + 1))
        PNPM_RESOLVED=true
        rm -f "$PNPM_OUTPUT_FILE"
        break
      fi
    done

    if [ "$PNPM_RESOLVED" != true ]; then
      echo "  pnpm audit: WARN (unresolved, treating as degraded)" >&2
    fi
  else
    echo "  pnpm audit: SKIP (pnpm or frontend/ not found)" >&2
  fi
fi

# --- Degradation report ---
if [ "$PNPM_DEGRADED" = true ] || [ "$PA_DEGRADED" = true ]; then
  DEGRADED_TOOLS=""
  [ "$PNPM_DEGRADED" = true ] && DEGRADED_TOOLS="pnpm-audit"
  [ "$PA_DEGRADED" = true ] && DEGRADED_TOOLS="${DEGRADED_TOOLS:+$DEGRADED_TOOLS,}pip-audit"
  echo "::warning::Security scan degraded (external registry unavailable): $DEGRADED_TOOLS" >&2
fi

# --- Summary ---
if [ "$HAD_ERROR" = true ]; then
  json_summary "tool_error" "$TOTAL_FINDINGS" "$SEMGREP_VER" "$PIP_AUDIT_VER"
  exit 2
elif [ "$TOTAL_FINDINGS" -gt 0 ]; then
  json_summary "findings" "$TOTAL_FINDINGS" "$SEMGREP_VER" "$PIP_AUDIT_VER"
  exit 1
else
  json_summary "clean" 0 "$SEMGREP_VER" "$PIP_AUDIT_VER"
  exit 0
fi
