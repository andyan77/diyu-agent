#!/usr/bin/env bash
# DIYU Agent pre-deployment environment preflight check.
#
# Purpose: Validate customer/staging environment before installation.
# Differs from scripts/doctor.py (dev-oriented) by focusing on
# runtime dependencies and minimum production requirements.
#
# Usage:
#   bash delivery/preflight.sh          # Human-readable
#   bash delivery/preflight.sh --json   # JSON output
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

set -euo pipefail

PASS=0
FAIL=0
WARN=0
RESULTS=()

check() {
  local name="$1" cmd="$2" min_major="$3" severity="${4:-required}"
  local version=""

  if ! command -v "$cmd" >/dev/null 2>&1; then
    if [ "$severity" = "required" ]; then
      FAIL=$((FAIL + 1))
      RESULTS+=("{\"name\":\"$name\",\"status\":\"FAIL\",\"detail\":\"$cmd not found\"}")
      [ -z "${JSON:-}" ] && printf "  [FAIL]   %s: %s not found\n" "$name" "$cmd" || true
    else
      WARN=$((WARN + 1))
      RESULTS+=("{\"name\":\"$name\",\"status\":\"WARN\",\"detail\":\"$cmd not found (optional)\"}")
      [ -z "${JSON:-}" ] && printf "  [WARN]   %s: %s not found (optional)\n" "$name" "$cmd" || true
    fi
    return
  fi

  version=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "0.0")
  local major="${version%%.*}"

  if [ "${major:-0}" -ge "$min_major" ]; then
    PASS=$((PASS + 1))
    RESULTS+=("{\"name\":\"$name\",\"status\":\"PASS\",\"detail\":\"$version\"}")
    [ -z "${JSON:-}" ] && printf "  [PASS]   %s: %s\n" "$name" "$version" || true
  else
    if [ "$severity" = "required" ]; then
      FAIL=$((FAIL + 1))
      RESULTS+=("{\"name\":\"$name\",\"status\":\"FAIL\",\"detail\":\"$version (need >= $min_major)\"}")
      [ -z "${JSON:-}" ] && printf "  [FAIL]   %s: %s (need >= %s)\n" "$name" "$version" "$min_major" || true
    else
      WARN=$((WARN + 1))
      RESULTS+=("{\"name\":\"$name\",\"status\":\"WARN\",\"detail\":\"$version (want >= $min_major)\"}")
      [ -z "${JSON:-}" ] && printf "  [WARN]   %s: %s (want >= %s)\n" "$name" "$version" "$min_major" || true
    fi
  fi
}

check_port() {
  local name="$1" host="$2" port="$3" severity="${4:-required}"

  if (echo >/dev/tcp/"$host"/"$port") 2>/dev/null; then
    PASS=$((PASS + 1))
    RESULTS+=("{\"name\":\"$name\",\"status\":\"PASS\",\"detail\":\"$host:$port reachable\"}")
    [ -z "${JSON:-}" ] && printf "  [PASS]   %s: %s:%s reachable\n" "$name" "$host" "$port" || true
  else
    if [ "$severity" = "required" ]; then
      FAIL=$((FAIL + 1))
      RESULTS+=("{\"name\":\"$name\",\"status\":\"FAIL\",\"detail\":\"$host:$port unreachable\"}")
      [ -z "${JSON:-}" ] && printf "  [FAIL]   %s: %s:%s unreachable\n" "$name" "$host" "$port" || true
    else
      WARN=$((WARN + 1))
      RESULTS+=("{\"name\":\"$name\",\"status\":\"WARN\",\"detail\":\"$host:$port unreachable\"}")
      [ -z "${JSON:-}" ] && printf "  [WARN]   %s: %s:%s unreachable\n" "$name" "$host" "$port" || true
    fi
  fi
}

check_disk() {
  local path="$1" min_gb="$2"
  local avail_kb
  avail_kb=$(df -k "$path" 2>/dev/null | awk 'NR==2{print $4}')
  local avail_gb=$(( ${avail_kb:-0} / 1048576 ))

  if [ "$avail_gb" -ge "$min_gb" ]; then
    PASS=$((PASS + 1))
    RESULTS+=("{\"name\":\"Disk ($path)\",\"status\":\"PASS\",\"detail\":\"${avail_gb}GB free\"}")
    [ -z "${JSON:-}" ] && printf "  [PASS]   Disk (%s): %sGB free\n" "$path" "$avail_gb" || true
  else
    FAIL=$((FAIL + 1))
    RESULTS+=("{\"name\":\"Disk ($path)\",\"status\":\"FAIL\",\"detail\":\"${avail_gb}GB free (need >= ${min_gb}GB)\"}")
    [ -z "${JSON:-}" ] && printf "  [FAIL]   Disk (%s): %sGB free (need >= %sGB)\n" "$path" "$avail_gb" "$min_gb" || true
  fi
}

# --- Parse args ---
JSON=""
if [[ "${1:-}" == "--json" ]]; then
  JSON=1
fi

[ -z "$JSON" ] && echo "=== DIYU Agent Preflight Check ===" || true

# --- Runtime dependencies ---
check "Python"          python3   3   required
check "Docker"          docker   24   required
check "Docker Compose"  docker   2    required

# --- Services ---
check_port "PostgreSQL" localhost 5432 required
check_port "Redis"      localhost 6379 required

# --- Optional tooling ---
check "Node.js"  node  22  optional
check "pnpm"     pnpm   9  optional
check "uv"       uv     0  optional

# --- Disk space ---
check_disk "/" 5

# --- Output ---
if [ -n "$JSON" ]; then
  printf '{"pass":%d,"fail":%d,"warn":%d,"items":[%s]}\n' \
    "$PASS" "$FAIL" "$WARN" "$(IFS=,; echo "${RESULTS[*]}")"
else
  echo ""
  printf "  Summary: %d PASS, %d FAIL, %d WARN\n" "$PASS" "$FAIL" "$WARN"
fi

exit "$(( FAIL > 0 ? 1 : 0 ))"
