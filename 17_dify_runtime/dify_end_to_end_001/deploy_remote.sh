#!/usr/bin/env bash
set -euo pipefail

: "${PACKAGE7_SOURCE_ROOT:?set PACKAGE7_SOURCE_ROOT}"
: "${PACKAGE7_STATE_ROOT:?set PACKAGE7_STATE_ROOT}"
: "${PACKAGE7_BRIDGE_PORT:?set PACKAGE7_BRIDGE_PORT}"
: "${PACKAGE7_DIFY_API_CONTAINER:?set PACKAGE7_DIFY_API_CONTAINER}"
: "${PACKAGE7_DIFY_IMAGE:?set PACKAGE7_DIFY_IMAGE}"
: "${PACKAGE7_DIFY_NETWORK:?set PACKAGE7_DIFY_NETWORK}"
: "${PACKAGE7_DB_NETWORK:?set PACKAGE7_DB_NETWORK}"
: "${PACKAGE7_DB_CONTAINER:?set PACKAGE7_DB_CONTAINER}"
: "${PACKAGE7_DIFY_INTERNAL_URL:?set PACKAGE7_DIFY_INTERNAL_URL}"

PACKAGE_DIR="${PACKAGE7_SOURCE_ROOT}/17_dify_runtime/dify_end_to_end_001"
SECRETS_FILE="${PACKAGE7_STATE_ROOT}/package7-secrets.env"
DIFY_ENV_FILE="${PACKAGE7_STATE_ROOT}/dify-api.env"
DIFY_STATE_FILE="${PACKAGE7_STATE_ROOT}/dify-state.json"
RENDERED_DSL="${PACKAGE7_STATE_ROOT}/dify-app.rendered.yaml"
BRIDGE_ENV_FILE="${PACKAGE7_STATE_ROOT}/bridge.env"
BRIDGE_NAME="diyu-package7-bridge"
DB_ROLE="diyu_pkg7_runtime"
DB_NAME="diyu_pkg7_runtime"
DATABASE_IS_MANAGED="false"
PRESERVED_DATABASE_URL=""

umask 077
mkdir -p "${PACKAGE7_STATE_ROOT}"
chmod 700 "${PACKAGE7_STATE_ROOT}"

if [[ -f "${BRIDGE_ENV_FILE}" ]] \
  && grep -qx 'DIYU_PKG9_MANAGED_DATABASE=true' "${BRIDGE_ENV_FILE}"; then
  DATABASE_IS_MANAGED="true"
  PRESERVED_DATABASE_URL="$(
    grep '^DIYU_PKG7_DATABASE_URL=' "${BRIDGE_ENV_FILE}" | cut -d= -f2-
  )"
  case "${PRESERVED_DATABASE_URL}" in
    postgresql+psycopg://diyu_pkg9_runtime:*@postgres/diyu_pkg7_runtime) ;;
    postgresql+psycopg://diyu_pkg9_runtime:*@postgres:5432/diyu_pkg7_runtime) ;;
    *) printf 'Managed Package 9 database URL is missing or invalid.\n' >&2; exit 1 ;;
  esac
fi
export PACKAGE7_DATABASE_IS_MANAGED="${DATABASE_IS_MANAGED}"
export PACKAGE7_PRESERVED_DATABASE_URL="${PRESERVED_DATABASE_URL}"

if [[ ! -f "${DIFY_STATE_FILE}" ]]; then
  : "${PACKAGE7_APPROVED_DIFY_TENANT_ID:?set explicit Package 7 Dify workspace for first provision}"
  : "${PACKAGE7_APPROVED_DIFY_OWNER_ACCOUNT_ID:?set explicit Package 7 Dify owner for first provision}"
fi

if [[ ! -f "${SECRETS_FILE}" ]]; then
  {
    printf 'DIYU_PKG7_DB_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'DIYU_SIM_USERNAME=%s\n' "package7-sim-owner"
    printf 'DIYU_SIM_PASSWORD=%s\n' "$(openssl rand -base64 30 | tr -d '\n')"
    printf 'DIYU_SESSION_SIGNING_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'DIYU_BRIDGE_SECRET=%s\n' "$(openssl rand -hex 32)"
  } >"${SECRETS_FILE}"
  chmod 600 "${SECRETS_FILE}"
fi

set -a
source "${SECRETS_FILE}"
set +a

if ! docker network inspect "${PACKAGE7_DB_NETWORK}" >/dev/null 2>&1; then
  docker network create \
    --label diyu.package=7 \
    --label diyu.lifecycle=non-production \
    "${PACKAGE7_DB_NETWORK}" >/dev/null
fi

if ! docker inspect "${PACKAGE7_DB_CONTAINER}" \
  --format '{{json .NetworkSettings.Networks}}' \
  | python3 -c 'import json, sys; raise SystemExit(0 if sys.argv[1] in json.load(sys.stdin) else 1)' \
    "${PACKAGE7_DB_NETWORK}"; then
  docker network connect \
    --alias postgres \
    "${PACKAGE7_DB_NETWORK}" \
    "${PACKAGE7_DB_CONTAINER}"
fi

if [[ "${DATABASE_IS_MANAGED}" == "true" ]]; then
  docker exec -i \
    -e PKG7_DB_NAME="${DB_NAME}" \
    "${PACKAGE7_DB_CONTAINER}" sh -ceu '
      psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$PKG7_DB_NAME" <<SQL
BEGIN;
SELECT pg_advisory_xact_lock(744970072);
CREATE TABLE IF NOT EXISTS runtime_browser_sessions (
  browser_session_id VARCHAR(160) PRIMARY KEY,
  principal_id VARCHAR(128) NOT NULL,
  state VARCHAR(32) NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_runtime_browser_sessions_principal_id
  ON runtime_browser_sessions (principal_id);
CREATE INDEX IF NOT EXISTS ix_runtime_browser_sessions_state
  ON runtime_browser_sessions (state);
ALTER TABLE runtime_requirements ADD COLUMN IF NOT EXISTS browser_session_id
  VARCHAR(160) NOT NULL DEFAULT '\''BRS-HISTORICAL'\'';
ALTER TABLE runtime_candidates ADD COLUMN IF NOT EXISTS principal_id
  VARCHAR(128) NOT NULL DEFAULT '\''PRINCIPAL-HISTORICAL'\'';
ALTER TABLE runtime_candidates ADD COLUMN IF NOT EXISTS browser_session_id
  VARCHAR(160) NOT NULL DEFAULT '\''BRS-HISTORICAL'\'';
ALTER TABLE runtime_feedback ADD COLUMN IF NOT EXISTS browser_session_id
  VARCHAR(160) NOT NULL DEFAULT '\''BRS-HISTORICAL'\'';
ALTER TABLE runtime_model_runs ADD COLUMN IF NOT EXISTS browser_session_id
  VARCHAR(160) NOT NULL DEFAULT '\''BRS-HISTORICAL'\'';
ALTER TABLE runtime_dify_conversations ADD COLUMN IF NOT EXISTS browser_session_id
  VARCHAR(160) NOT NULL DEFAULT '\''BRS-HISTORICAL'\'';
ALTER TABLE runtime_dify_conversations
  DROP CONSTRAINT IF EXISTS uq_runtime_dify_conversation_scope;
ALTER TABLE runtime_dify_conversations
  ADD CONSTRAINT uq_runtime_dify_conversation_scope
  UNIQUE (principal_id, account_id, browser_session_id);
ALTER TABLE runtime_browser_sessions OWNER TO diyu_pkg9_migrator;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE runtime_browser_sessions
  TO diyu_pkg9_runtime;
ALTER TABLE runtime_browser_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE runtime_browser_sessions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS diyu_scope_policy ON runtime_browser_sessions;
CREATE POLICY diyu_scope_policy ON runtime_browser_sessions
  FOR ALL TO diyu_pkg9_runtime
  USING (EXISTS (
    SELECT 1 FROM runtime_principals AS scope_principal
    WHERE scope_principal.principal_id = runtime_browser_sessions.principal_id
      AND scope_principal.tenant_id =
        NULLIF(current_setting('\''app.tenant_id'\'', true), '\'''\'')
      AND (
        NULLIF(current_setting('\''app.principal_id'\'', true), '\'''\'') IS NULL
        OR scope_principal.principal_id =
          NULLIF(current_setting('\''app.principal_id'\'', true), '\'''\'')
      )
  ) AND browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''))
  WITH CHECK (EXISTS (
    SELECT 1 FROM runtime_principals AS scope_principal
    WHERE scope_principal.principal_id = runtime_browser_sessions.principal_id
      AND scope_principal.tenant_id =
        NULLIF(current_setting('\''app.tenant_id'\'', true), '\'''\'')
      AND (
        NULLIF(current_setting('\''app.principal_id'\'', true), '\'''\'') IS NULL
        OR scope_principal.principal_id =
          NULLIF(current_setting('\''app.principal_id'\'', true), '\'''\'')
      )
  ) AND browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''));
DROP POLICY IF EXISTS diyu_pkg7_browser_scope ON runtime_requirements;
CREATE POLICY diyu_pkg7_browser_scope ON runtime_requirements
  AS RESTRICTIVE FOR ALL TO diyu_pkg9_runtime
  USING (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''))
  WITH CHECK (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''));
DROP POLICY IF EXISTS diyu_pkg7_browser_scope ON runtime_model_runs;
CREATE POLICY diyu_pkg7_browser_scope ON runtime_model_runs
  AS RESTRICTIVE FOR ALL TO diyu_pkg9_runtime
  USING (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''))
  WITH CHECK (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''));
DROP POLICY IF EXISTS diyu_pkg7_browser_scope ON runtime_candidates;
CREATE POLICY diyu_pkg7_browser_scope ON runtime_candidates
  AS RESTRICTIVE FOR ALL TO diyu_pkg9_runtime
  USING (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''))
  WITH CHECK (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''));
DROP POLICY IF EXISTS diyu_pkg7_browser_scope ON runtime_feedback;
CREATE POLICY diyu_pkg7_browser_scope ON runtime_feedback
  AS RESTRICTIVE FOR ALL TO diyu_pkg9_runtime
  USING (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''))
  WITH CHECK (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''));
DROP POLICY IF EXISTS diyu_pkg7_browser_scope ON runtime_dify_conversations;
CREATE POLICY diyu_pkg7_browser_scope ON runtime_dify_conversations
  AS RESTRICTIVE FOR ALL TO diyu_pkg9_runtime
  USING (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''))
  WITH CHECK (browser_session_id =
    NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\''));
DROP POLICY IF EXISTS diyu_pkg7_browser_scope ON runtime_validations;
CREATE POLICY diyu_pkg7_browser_scope ON runtime_validations
  AS RESTRICTIVE FOR ALL TO diyu_pkg9_runtime
  USING (EXISTS (
    SELECT 1 FROM runtime_candidates AS browser_candidate
    WHERE browser_candidate.candidate_id = runtime_validations.candidate_id
      AND browser_candidate.browser_session_id =
        NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\'')
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM runtime_candidates AS browser_candidate
    WHERE browser_candidate.candidate_id = runtime_validations.candidate_id
      AND browser_candidate.browser_session_id =
        NULLIF(current_setting('\''app.browser_session_id'\'', true), '\'''\'')
  ));
COMMIT;

BEGIN;
CREATE TABLE package7_migration_rollback_probe (probe_id INTEGER PRIMARY KEY);
ALTER TABLE package7_migration_rollback_probe ADD COLUMN should_rollback TEXT;
ROLLBACK;
DO \$\$
BEGIN
  IF to_regclass('\''public.package7_migration_rollback_probe'\'') IS NOT NULL THEN
    RAISE EXCEPTION '\''Package 7 migration rollback probe was not rolled back'\'';
  END IF;
END
\$\$;
SQL
    '
else
  docker exec -i \
    -e PKG7_DB_ROLE="${DB_ROLE}" \
    -e PKG7_DB_NAME="${DB_NAME}" \
    -e PKG7_DB_PASSWORD="${DIYU_PKG7_DB_PASSWORD}" \
    "${PACKAGE7_DB_CONTAINER}" sh -ceu '
      psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres <<SQL
SELECT format('\''CREATE ROLE %I LOGIN PASSWORD %L'\'', '\''${PKG7_DB_ROLE}'\'', '\''${PKG7_DB_PASSWORD}'\'')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '\''${PKG7_DB_ROLE}'\'')\gexec
SELECT format('\''ALTER ROLE %I LOGIN PASSWORD %L'\'', '\''${PKG7_DB_ROLE}'\'', '\''${PKG7_DB_PASSWORD}'\'')\gexec
SELECT format('\''CREATE DATABASE %I OWNER %I'\'', '\''${PKG7_DB_NAME}'\'', '\''${PKG7_DB_ROLE}'\'')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '\''${PKG7_DB_NAME}'\'')\gexec
SQL
    '
fi

docker inspect "${PACKAGE7_DIFY_API_CONTAINER}" \
  --format '{{range .Config.Env}}{{println .}}{{end}}' >"${DIFY_ENV_FILE}"
chmod 600 "${DIFY_ENV_FILE}"
cleanup_dify_env() {
  rm -f "${DIFY_ENV_FILE}"
}
trap cleanup_dify_env EXIT

python3 - "${PACKAGE_DIR}/dify_app.v1.yaml" "${RENDERED_DSL}" <<'PY'
import os
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8")
if "__PACKAGE7_" in source:
    raise SystemExit("unresolved Package 7 Dify placeholder")
Path(sys.argv[2]).write_text(source, encoding="utf-8")
PY
chmod 600 "${RENDERED_DSL}"

DIFY_STORAGE_SOURCE="$(docker inspect "${PACKAGE7_DIFY_API_CONTAINER}" --format '{{range .Mounts}}{{if eq .Destination "/app/api/storage"}}{{.Source}}{{end}}{{end}}')"
docker run --rm \
  --entrypoint python \
  --user root \
  --env-file "${DIFY_ENV_FILE}" \
  --network "${PACKAGE7_DIFY_NETWORK}" \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/app/api \
  -e PACKAGE7_DSL_PATH=/state/dify-app.rendered.yaml \
  -e PACKAGE8_DIFY_MATERIALIZATION_MANIFEST_PATH=/state/package8-materialization/dify_materialization_manifest.v1.json \
  -e PACKAGE7_STATE_PATH=/state/dify-state.json \
  -e PACKAGE7_APPROVED_DIFY_TENANT_ID="${PACKAGE7_APPROVED_DIFY_TENANT_ID:-}" \
  -e PACKAGE7_APPROVED_DIFY_OWNER_ACCOUNT_ID="${PACKAGE7_APPROVED_DIFY_OWNER_ACCOUNT_ID:-}" \
  -v "${PACKAGE7_SOURCE_ROOT}:/repo:ro" \
  -v "${PACKAGE7_STATE_ROOT}:/state" \
  -v "${DIFY_STORAGE_SOURCE}:/app/api/storage" \
  -w /app/api \
  "${PACKAGE7_DIFY_IMAGE}" \
  /repo/17_dify_runtime/dify_end_to_end_001/provision_dify.py
cleanup_dify_env
trap - EXIT

python3 - "${DIFY_STATE_FILE}" "${BRIDGE_ENV_FILE}" <<'PY'
import json
import os
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
managed_database = os.environ["PACKAGE7_DATABASE_IS_MANAGED"] == "true"
database_url = (
    os.environ["PACKAGE7_PRESERVED_DATABASE_URL"]
    if managed_database
    else (
        "postgresql+psycopg://diyu_pkg7_runtime:"
        f"{os.environ['DIYU_PKG7_DB_PASSWORD']}@postgres/diyu_pkg7_runtime"
    )
)
values = {
    "DIYU_PKG7_DATABASE_URL": database_url,
    "DIYU_SIM_USERNAME": os.environ["DIYU_SIM_USERNAME"],
    "DIYU_SIM_PASSWORD": os.environ["DIYU_SIM_PASSWORD"],
    "DIYU_SESSION_SIGNING_KEY": os.environ["DIYU_SESSION_SIGNING_KEY"],
    "DIYU_BRIDGE_SECRET": os.environ["DIYU_BRIDGE_SECRET"],
    "DIYU_BRIDGE_PORT": os.environ["PACKAGE7_BRIDGE_PORT"],
    "DIYU_DIFY_INTERNAL_URL": os.environ["PACKAGE7_DIFY_INTERNAL_URL"],
    "DIYU_DIFY_SERVICE_API_URL": os.environ["PACKAGE7_DIFY_INTERNAL_URL"].rstrip("/") + "/v1",
    "DIYU_DIFY_TENANT_ID": state["tenant_id"],
    "DIYU_DIFY_APP_ID": state["app_id"],
    "DIYU_DIFY_DATASET_ID": state["dataset_id"],
    "DIYU_DIFY_STATE_PATH": "/state/dify-state.json",
    "DIYU_PKG7_MAX_MODEL_CALLS": os.environ.get("PACKAGE7_MAX_MODEL_CALLS", "1096"),
    "DIYU_COOKIE_SECURE": "true",
    "PYTHONDONTWRITEBYTECODE": "1",
}
if managed_database:
    values["DIYU_PKG9_MANAGED_DATABASE"] = "true"
Path(sys.argv[2]).write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
PY
chmod 600 "${BRIDGE_ENV_FILE}"
chown -R 1001:1001 "${PACKAGE7_SOURCE_ROOT}" "${PACKAGE7_STATE_ROOT}"
find "${PACKAGE7_SOURCE_ROOT}" "${PACKAGE7_STATE_ROOT}" -type d -exec chmod 500 {} +
find "${PACKAGE7_SOURCE_ROOT}" "${PACKAGE7_STATE_ROOT}" -type f -exec chmod 400 {} +

if docker container inspect "${BRIDGE_NAME}" >/dev/null 2>&1; then
  docker rm -f "${BRIDGE_NAME}" >/dev/null
fi
docker create \
  --name "${BRIDGE_NAME}" \
  --entrypoint python \
  --restart unless-stopped \
  --user 1001:1001 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --env-file "${BRIDGE_ENV_FILE}" \
  --network "${PACKAGE7_DIFY_NETWORK}" \
  -p "127.0.0.1:${PACKAGE7_BRIDGE_PORT}:${PACKAGE7_BRIDGE_PORT}" \
  -v "${PACKAGE7_SOURCE_ROOT}:/repo:ro" \
  -v "${PACKAGE7_STATE_ROOT}:/state:ro" \
  -w /repo/17_dify_runtime/dify_end_to_end_001 \
  "${PACKAGE7_DIFY_IMAGE}" \
  bridge_app.py >/dev/null
docker network connect "${PACKAGE7_DB_NETWORK}" "${BRIDGE_NAME}"
docker start "${BRIDGE_NAME}" >/dev/null

printf 'Package 7 isolated objects provisioned; secrets remain in root-only state files.\n'
