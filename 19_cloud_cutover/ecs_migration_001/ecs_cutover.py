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
    return {
        "state": "BACKUP_MANIFEST_VERIFIED",
        "artifact_count": len(artifacts),
        "manifest_sha256": _sha256(path),
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

