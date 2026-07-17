#!/usr/bin/env python3
"""Single Package 9 migration, verification, and rollback entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from database_security import (
    apply_database_security,
    render_rollback_sql,
    render_security_sql,
    rollback_database_security,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
TASK_ID = "DIYU_ECS_CUTOVER_001"
ROLLBACK_ACTIONS = (
    "RESTORE_PRE_CUTOVER_NGINX",
    "ROLLBACK_DATABASE_SECURITY",
    "START_LEGACY_BRIDGE_FROM_BACKUP_IDENTITY",
    "VERIFY_LEGACY_BRIDGE_HEALTH",
    "VERIFY_DIFY_ROOT_HEALTH",
)
FORWARD_ACTIONS = (
    "APPLY_DATABASE_SECURITY",
    "DEPLOY_FROZEN_RELEASE",
    "START_CURRENT_BRIDGE",
    "INSTALL_APPS_NGINX_ROUTE",
    "VERIFY_ROOT_AND_APPS_HEALTH",
    "VERIFY_FORCED_RLS_AND_RUNTIME_ROLE",
)
SECRET_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|"
    r"postgresql(?:\+\w+)?://[^\s'\"]+:[^@\s'\"]+@|Bearer [A-Za-z0-9._-]{20,})"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected one JSON object: {path}")
    return value


def verify_encrypted_backup_manifest(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    artifacts = value.get("artifacts")
    if (
        value.get("task_id") != TASK_ID
        or value.get("location_class")
        != "SERVER_EXTERNAL_RESTRICTED_LOCAL_STORAGE"
        or value.get("key_location_class")
        != "SEPARATE_SERVER_EXTERNAL_RESTRICTED_KEY_STORE"
        or value.get("encryption") != "GPG_SYMMETRIC_AES256"
        or value.get("plaintext_artifacts_persisted") is not False
        or not isinstance(artifacts, list)
        or len(artifacts) != value.get("artifact_count")
        or any(
            not isinstance(row, dict)
            or row.get("decryption_verified") is not True
            or not isinstance(row.get("encrypted_sha256"), str)
            or len(str(row.get("encrypted_sha256"))) != 64
            or int(row.get("encrypted_size_bytes", 0)) <= 0
            for row in artifacts
        )
    ):
        raise ValueError("The external encrypted backup manifest is incomplete")
    verified_artifacts: list[dict[str, Any]] = []
    for row in artifacts:
        artifact_name = row.get("artifact")
        if not isinstance(artifact_name, str):
            raise ValueError("The external encrypted backup manifest is incomplete")
        relative = Path(artifact_name)
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
            raise ValueError("The external backup artifact path is unsafe")
        artifact = path.parent / relative
        if (
            not artifact.is_file()
            or artifact.is_symlink()
            or artifact.stat().st_size != int(row["encrypted_size_bytes"])
            or _sha256(artifact) != row["encrypted_sha256"]
        ):
            raise ValueError("The external encrypted backup artifact is missing or corrupt")
        verified_artifacts.append(
            {
                "artifact": artifact_name,
                "encrypted_sha256": row["encrypted_sha256"],
                "encrypted_size_bytes": row["encrypted_size_bytes"],
            }
        )
    return {
        "state": "BACKUP_MANIFEST_VERIFIED",
        "artifact_count": len(artifacts),
        "manifest_sha256": _sha256(path),
        "artifacts": verified_artifacts,
    }


def verify_transition_record(path: Path) -> dict[str, Any]:
    """Verify the sanitized record emitted by the actual rollback/forward run."""

    value = _read_json(path)
    record = value.get("transition_record")
    if not isinstance(record, dict):
        raise ValueError("The cutover transition record is missing")
    if (
        record.get("task_id") != TASK_ID
        or record.get("actual_execution") is not True
        or record.get("final_state") != "PACKAGE9_CANDIDATE"
        or record.get("rollback_and_forward_pass") is not True
    ):
        raise ValueError("The cutover transition identity is invalid")
    bindings = record.get("bindings")
    if not isinstance(bindings, dict) or any(
        not isinstance(bindings.get(name), str)
        or re.fullmatch(r"[0-9a-f]{64}", str(bindings.get(name))) is None
        for name in (
            "release_archive_sha256",
            "pre_cutover_backup_manifest_sha256",
            "post_cutover_backup_manifest_sha256",
            "rollback_checkpoint_sha256",
            "forward_result_sha256",
        )
    ):
        raise ValueError("The cutover transition bindings are incomplete")
    for phase_name, expected_actions in (
        ("rollback_phase", ROLLBACK_ACTIONS),
        ("forward_phase", FORWARD_ACTIONS),
    ):
        phase = record.get(phase_name)
        if not isinstance(phase, dict):
            raise ValueError("The cutover transition phase is missing")
        actions = phase.get("actions")
        if (
            not isinstance(actions, list)
            or tuple(row.get("action") for row in actions if isinstance(row, dict))
            != expected_actions
            or any(
                not isinstance(row, dict)
                or row.get("status") != "PASS"
                or not isinstance(row.get("evidence_ref"), str)
                for row in actions
            )
        ):
            raise ValueError("The cutover transition actions are incomplete")
    return {
        "state": "CUTOVER_TRANSITION_RECORD_VERIFIED",
        "transition_record_sha256": hashlib.sha256(
            json.dumps(
                record,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
    }


def verify_repository_has_no_secret_surface() -> dict[str, Any]:
    offending: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            offending.append(path.relative_to(REPOSITORY_ROOT).as_posix())
            continue
        if SECRET_PATTERN.search(text):
            offending.append(path.relative_to(REPOSITORY_ROOT).as_posix())
    if offending:
        raise ValueError(f"Package 9 contains a secret-like surface: {offending}")
    return {"state": "SECRET_SURFACE_CLEAR", "checked_root": str(PACKAGE_ROOT)}


def render_nginx(template: Path) -> dict[str, Any]:
    text = template.read_text(encoding="utf-8")
    required = (
        "location = /apps",
        "location ^~ /apps/",
        "proxy_pass http://127.0.0.1:18471/",
        "proxy_hide_header Server",
    )
    if any(item not in text for item in required):
        raise ValueError("The /apps reverse-proxy template is incomplete")
    sys.stdout.write(text)
    return {"state": "NGINX_TEMPLATE_RENDERED"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="笛语第9包统一切换与回滚入口")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("render-database-security")
    subparsers.add_parser("render-database-rollback")
    subparsers.add_parser("apply-database-security")
    subparsers.add_parser("rollback-database-security")
    backup = subparsers.add_parser("verify-backup-manifest")
    backup.add_argument("--manifest", type=Path, required=True)
    transition = subparsers.add_parser("verify-transition-record")
    transition.add_argument("--record", type=Path, required=True)
    nginx = subparsers.add_parser("render-nginx")
    nginx.add_argument(
        "--template",
        type=Path,
        default=PACKAGE_ROOT / "nginx_apps.conf.template",
    )
    subparsers.add_parser("verify-secret-surface")
    return parser


def execute(arguments: argparse.Namespace) -> dict[str, Any]:
    if arguments.command == "render-database-security":
        sys.stdout.write(render_security_sql())
        return {"state": "DATABASE_SECURITY_RENDERED"}
    if arguments.command == "render-database-rollback":
        sys.stdout.write(render_rollback_sql())
        return {"state": "DATABASE_ROLLBACK_RENDERED"}
    if arguments.command == "apply-database-security":
        return apply_database_security(
            admin_database_url=os.environ["DIYU_PKG9_ADMIN_DATABASE_URL"],
            migration_password=os.environ["DIYU_PKG9_MIGRATION_ROLE_PASSWORD"],
            runtime_password=os.environ["DIYU_PKG9_RUNTIME_ROLE_PASSWORD"],
        )
    if arguments.command == "rollback-database-security":
        return rollback_database_security(
            admin_database_url=os.environ["DIYU_PKG9_ADMIN_DATABASE_URL"]
        )
    if arguments.command == "verify-backup-manifest":
        return verify_encrypted_backup_manifest(arguments.manifest)
    if arguments.command == "verify-transition-record":
        return verify_transition_record(arguments.record)
    if arguments.command == "render-nginx":
        return render_nginx(arguments.template)
    if arguments.command == "verify-secret-surface":
        return verify_repository_has_no_secret_surface()
    raise ValueError("Unknown Package 9 operation")


def main() -> int:
    try:
        result = execute(_parser().parse_args())
    except (KeyError, OSError, ValueError) as exc:
        sys.stderr.write(f"Package 9 failed closed: {type(exc).__name__}\n")
        return 1
    if result.get("state") not in {
        "DATABASE_SECURITY_RENDERED",
        "DATABASE_ROLLBACK_RENDERED",
        "NGINX_TEMPLATE_RENDERED",
    }:
        sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
