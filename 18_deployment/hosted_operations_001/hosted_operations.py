#!/usr/bin/env python3
"""Single Package 8 operational entrypoint."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from brand_bundle import compile_brand_bundle, load_brand_input
from operations import HostedOperations, preflight_environment


def _database_url() -> str:
    value = os.environ.get("DIYU_PKG8_DATABASE_URL", "")
    if not value:
        raise ValueError("缺少 DIYU_PKG8_DATABASE_URL")
    return value


def _password() -> str:
    value = os.environ.get("DIYU_PKG8_PRINCIPAL_PASSWORD", "")
    if not value:
        raise ValueError("缺少 DIYU_PKG8_PRINCIPAL_PASSWORD")
    return value


def _operations(database_url: str, namespace: str) -> HostedOperations:
    from persistence import create_runtime_engine, create_session_factory

    engine = create_runtime_engine(database_url)
    return HostedOperations(engine, create_session_factory(engine), namespace)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="笛语第8包统一运维入口")
    parser.add_argument("--namespace", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--secret-file", type=Path)
    subparsers.add_parser("install")
    subparsers.add_parser("initialize")
    for name in ("import", "update"):
        command = subparsers.add_parser(name)
        command.add_argument("--brand-file", required=True, type=Path)
    revoke = subparsers.add_parser("revoke")
    revoke.add_argument("--tenant-id", required=True)
    revoke.add_argument(
        "--kind",
        required=True,
        choices=("fragment", "fact", "authorization"),
    )
    revoke.add_argument("--object-id", required=True)
    revoke.add_argument("--reason-ref", required=True)
    backup = subparsers.add_parser("backup")
    backup.add_argument("--output-directory", required=True, type=Path)
    materialize = subparsers.add_parser("materialize-dify")
    materialize.add_argument("--output-directory", required=True, type=Path)
    materialize.add_argument("--as-of", required=True)
    restore = subparsers.add_parser("restore")
    restore.add_argument("--manifest", required=True, type=Path)
    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("--tenant-id", required=True)
    rollback.add_argument("--revision", required=True, type=int)
    upgrade = subparsers.add_parser("upgrade")
    upgrade.add_argument("--target-version", required=True, type=int)
    rollback_schema = subparsers.add_parser("rollback-schema")
    rollback_schema.add_argument("--target-version", type=int, default=1)
    subparsers.add_parser("health")
    return parser


def execute(arguments: argparse.Namespace) -> dict[str, Any]:
    database_url = _database_url()
    if arguments.command == "preflight":
        return preflight_environment(
            database_url=database_url,
            namespace=arguments.namespace,
            secret_file=arguments.secret_file,
        )
    if arguments.command == "restore":
        return HostedOperations.restore(
            target_database_url=database_url,
            manifest_path=arguments.manifest,
        )
    operations = _operations(database_url, arguments.namespace)
    try:
        if arguments.command == "install":
            return operations.install()
        if arguments.command == "initialize":
            return operations.initialize_simulation(
                username=os.environ.get(
                    "DIYU_PKG8_PRINCIPAL_USERNAME", "pkg8-simulation-owner"
                ),
                password=_password(),
            )
        if arguments.command in {"import", "update"}:
            bundle = compile_brand_bundle(load_brand_input(arguments.brand_file))
            return operations.import_brand(
                bundle,
                principal_password=_password(),
                reason="IMPORT" if arguments.command == "import" else "UPDATE",
            )
        if arguments.command == "revoke":
            return operations.revoke(
                tenant_id=arguments.tenant_id,
                object_kind=arguments.kind,
                object_id=arguments.object_id,
                reason_ref=arguments.reason_ref,
            )
        if arguments.command == "backup":
            return operations.backup(
                database_url=database_url,
                output_directory=arguments.output_directory,
            )
        if arguments.command == "materialize-dify":
            normalized = (
                f"{arguments.as_of[:-1]}+00:00"
                if arguments.as_of.endswith("Z")
                else arguments.as_of
            )
            return operations.materialize_dify(
                output_directory=arguments.output_directory,
                as_of=datetime.fromisoformat(normalized),
            )
        if arguments.command == "rollback":
            return operations.rollback_brand(
                tenant_id=arguments.tenant_id,
                target_revision=arguments.revision,
                principal_password=_password(),
            )
        if arguments.command == "upgrade":
            return operations.upgrade(target_version=arguments.target_version)
        if arguments.command == "rollback-schema":
            return operations.rollback_schema(target_version=arguments.target_version)
        if arguments.command == "health":
            return operations.health()
        raise ValueError("未知运维命令")
    finally:
        operations.engine.dispose()


def main() -> int:
    try:
        result = execute(_parser().parse_args())
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"state": "FAILED_CLOSED", "message": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
