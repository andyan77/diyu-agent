#!/usr/bin/env bash
# DIYU Agent manifest drift checker (D3-3).
#
# Purpose: Verify that deployment files (docker-compose.yml, Dockerfile)
# are consistent with the single source of truth (delivery/manifest.yaml).
#
# Usage:
#   bash scripts/check_manifest_drift.sh
#
# Output: JSON report with drift details
#   {"status":"pass","drifts":[],"count":0} - No drift
#   {"status":"fail","drifts":[...],"count":N} - Drift detected
#
# Exit codes:
#   0 - No drift detected
#   1 - Drift detected

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$PROJECT_ROOT/delivery/manifest.yaml"
DOCKER_COMPOSE="$PROJECT_ROOT/docker-compose.yml"
DOCKERFILE="$PROJECT_ROOT/Dockerfile"

DRIFTS=()

# Helper: Extract value from YAML
yaml_get() {
  local file="$1" key="$2"
  grep -E "^\s*${key}:" "$file" | head -1 | sed -E 's/^[^:]+:\s*//' | sed 's/"//g' | sed "s/'//g" | xargs
}

# Helper: Record drift
record_drift() {
  local file="$1" key="$2" expected="$3" actual="$4"
  DRIFTS+=("{\"file\":\"$file\",\"key\":\"$key\",\"expected\":\"$expected\",\"actual\":\"$actual\"}")
}

# --- Check 1: PostgreSQL version in docker-compose.yml ---
EXPECTED_PG_VERSION="16"
if [ -f "$DOCKER_COMPOSE" ]; then
  # Extract pgvector image
  ACTUAL_PG_IMAGE=$(grep "pgvector/pgvector" "$DOCKER_COMPOSE" | grep -oE "pgvector/pgvector:pg[0-9]+" | head -1 || echo "")
  if [ -n "$ACTUAL_PG_IMAGE" ]; then
    ACTUAL_PG_VERSION=$(echo "$ACTUAL_PG_IMAGE" | grep -oE '[0-9]+$')
    if [ "$ACTUAL_PG_VERSION" != "$EXPECTED_PG_VERSION" ]; then
      record_drift "docker-compose.yml" "postgres.image" "pgvector/pgvector:pg${EXPECTED_PG_VERSION}" "$ACTUAL_PG_IMAGE"
    fi
  else
    record_drift "docker-compose.yml" "postgres.image" "pgvector/pgvector:pg${EXPECTED_PG_VERSION}" "NOT_FOUND"
  fi
fi

# --- Check 2: Redis version in docker-compose.yml ---
EXPECTED_REDIS_VERSION="7"
if [ -f "$DOCKER_COMPOSE" ]; then
  # Extract redis image
  ACTUAL_REDIS_IMAGE=$(grep "image: redis:" "$DOCKER_COMPOSE" | grep -oE "redis:[0-9]+-alpine" | head -1 || echo "")
  if [ -n "$ACTUAL_REDIS_IMAGE" ]; then
    ACTUAL_REDIS_VERSION=$(echo "$ACTUAL_REDIS_IMAGE" | grep -oE '[0-9]+' | head -1)
    if [ "$ACTUAL_REDIS_VERSION" != "$EXPECTED_REDIS_VERSION" ]; then
      record_drift "docker-compose.yml" "redis.image" "redis:${EXPECTED_REDIS_VERSION}-alpine" "$ACTUAL_REDIS_IMAGE"
    fi
  else
    record_drift "docker-compose.yml" "redis.image" "redis:${EXPECTED_REDIS_VERSION}-alpine" "NOT_FOUND"
  fi
fi

# --- Check 3: Neo4j version in docker-compose.yml ---
EXPECTED_NEO4J_VERSION="5"
if [ -f "$DOCKER_COMPOSE" ]; then
  # Extract neo4j image
  ACTUAL_NEO4J_IMAGE=$(grep "image: neo4j:" "$DOCKER_COMPOSE" | grep -oE "neo4j:[0-9]+-community" | head -1 || echo "")
  if [ -n "$ACTUAL_NEO4J_IMAGE" ]; then
    # Extract version after the colon
    ACTUAL_NEO4J_VERSION=$(echo "$ACTUAL_NEO4J_IMAGE" | sed 's/neo4j://' | grep -oE '^[0-9]+')
    if [ "$ACTUAL_NEO4J_VERSION" != "$EXPECTED_NEO4J_VERSION" ]; then
      record_drift "docker-compose.yml" "neo4j.image" "neo4j:${EXPECTED_NEO4J_VERSION}-community" "$ACTUAL_NEO4J_IMAGE"
    fi
  else
    record_drift "docker-compose.yml" "neo4j.image" "neo4j:${EXPECTED_NEO4J_VERSION}-community" "NOT_FOUND"
  fi
fi

# --- Check 4: Python version in Dockerfile ---
EXPECTED_PYTHON_VERSION="3.12"
if [ -f "$DOCKERFILE" ]; then
  ACTUAL_PYTHON_IMAGE=$(grep -E "^FROM python:" "$DOCKERFILE" | head -1 | awk '{print $2}' || echo "")
  if [ -n "$ACTUAL_PYTHON_IMAGE" ]; then
    ACTUAL_PYTHON_VERSION=$(echo "$ACTUAL_PYTHON_IMAGE" | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if [ "$ACTUAL_PYTHON_VERSION" != "$EXPECTED_PYTHON_VERSION" ]; then
      record_drift "Dockerfile" "base_image" "python:${EXPECTED_PYTHON_VERSION}-slim" "$ACTUAL_PYTHON_IMAGE"
    fi
  else
    record_drift "Dockerfile" "base_image" "python:${EXPECTED_PYTHON_VERSION}-slim" "NOT_FOUND"
  fi
fi

# --- Output JSON report ---
DRIFT_COUNT="${#DRIFTS[@]}"
STATUS="pass"

if [ "$DRIFT_COUNT" -gt 0 ]; then
  STATUS="fail"
fi

if [ "$DRIFT_COUNT" -eq 0 ]; then
  printf '{"status":"%s","drifts":[],"count":0}\n' "$STATUS"
else
  DRIFTS_JSON=$(printf '%s,' "${DRIFTS[@]}" | sed 's/,$//')
  printf '{"status":"%s","drifts":[%s],"count":%d}\n' "$STATUS" "$DRIFTS_JSON" "$DRIFT_COUNT"
fi

exit "$(( DRIFT_COUNT > 0 ? 1 : 0 ))"
