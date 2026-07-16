#!/usr/bin/env python3
"""Transactional hosted operations over the existing Package 7 runtime model."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_7_ROOT = REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001"
if str(PACKAGE_7_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_7_ROOT))

from brand_import import (  # noqa: E402
    BrandImportBundle,
    load_simulation_bundle,
    preflight_brand_bundle,
)
from persistence import (  # noqa: E402
    RuntimeRepository,
    digest_object,
)
from runtime_models import (  # noqa: E402
    RuntimeAccount,
    RuntimeAuthorization,
    RuntimeBrand,
    RuntimeCandidate,
    RuntimeFeedback,
    RuntimeNarrativeFragment,
    RuntimeOrganization,
    RuntimePreciseFact,
    RuntimePrincipal,
    RuntimeSetting,
    RuntimeSource,
    RuntimeStore,
    RuntimeSubjectConfirmation,
    RuntimeTenant,
)
from security import hash_password, verify_password  # noqa: E402
from seed_runtime import (  # noqa: E402
    normalize_knowledge_text,
    parse_time,
    seed_database,
)

from brand_bundle import (  # noqa: E402
    bundle_digest,
    bundle_from_payload,
    bundle_to_payload,
)
from hosted_models import (  # noqa: E402
    HostedBase,
    HostedBrandRevision,
    HostedOperationAudit,
    HostedSchemaState,
)


JsonObject = dict[str, Any]
ModelType = TypeVar("ModelType")
APPLICATION_VERSION = "package8-v1"
SCHEMA_VERSION = 1
TASK_PREFIX = "diyu-pkg8-"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_namespace(value: str) -> str:
    if not value.startswith(TASK_PREFIX):
        raise ValueError("目标命名空间不属于第8包")
    if not value.replace("-", "").isalnum():
        raise ValueError("目标命名空间格式无效")
    return value


def _upsert(
    session: Session,
    model: type[ModelType],
    key: str,
    value: ModelType,
) -> bool:
    current = session.get(model, key)
    if current is None:
        session.add(value)
        return True
    ignored = {"_sa_instance_state", "updated_at"}
    before = digest_object(
        {key: val for key, val in vars(current).items() if key not in ignored}
    )
    after = digest_object(
        {key: val for key, val in vars(value).items() if key not in ignored}
    )
    if before == after:
        return False
    for field, field_value in vars(value).items():
        if field not in ignored:
            setattr(current, field, copy.deepcopy(field_value))
    if hasattr(current, "updated_at"):
        setattr(current, "updated_at", utc_now())
    return True


def _advisory_key(value: str) -> int:
    raw = int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "big")
    return raw & ((1 << 63) - 1)


def _database_args(url: URL) -> tuple[list[str], dict[str, str]]:
    if not url.drivername.startswith("postgresql"):
        raise ValueError("真实验收只允许独立 PostgreSQL")
    database = url.database
    if not isinstance(database, str) or not database.startswith(TASK_PREFIX):
        raise ValueError("数据库不属于第8包")
    args: list[str] = []
    host = url.host or url.query.get("host")
    port = url.port or url.query.get("port")
    if host:
        args.extend(["--host", str(host)])
    if port:
        args.extend(["--port", str(port)])
    if url.username:
        args.extend(["--username", str(url.username)])
    args.extend(["--dbname", database])
    env = dict(os.environ)
    if url.password:
        env["PGPASSWORD"] = str(url.password)
    return args, env


class HostedOperations:
    """One operational boundary for install, import, recovery, and health."""

    def __init__(
        self,
        engine: Engine,
        sessions: sessionmaker[Session],
        namespace: str,
    ) -> None:
        self.engine = engine
        self.sessions = sessions
        self.namespace = _safe_namespace(namespace)
        self.repository = RuntimeRepository(sessions)

    def install(self) -> JsonObject:
        self.repository.initialize_schema(self.engine)
        HostedBase.metadata.create_all(self.engine)
        with self.sessions.begin() as session:
            row = session.get(HostedSchemaState, self.namespace)
            if row is None:
                session.add(
                    HostedSchemaState(
                        namespace=self.namespace,
                        schema_version=SCHEMA_VERSION,
                        application_version=APPLICATION_VERSION,
                        state="KNOWN_GOOD",
                        metadata_payload={
                            "brand_import_transaction_version": 1,
                            "simulation_only": True,
                            "production_ready": False,
                        },
                        updated_at=utc_now(),
                    )
                )
                state = "INSTALLED"
            else:
                state = "UNCHANGED"
            self._audit(
                session,
                "install",
                state,
                self.namespace,
                {"schema_version": row.schema_version if row else SCHEMA_VERSION},
            )
        return {"state": state, "namespace": self.namespace}

    def initialize_simulation(
        self,
        *,
        username: str,
        password: str,
    ) -> JsonObject:
        self._require_installed()
        seed = seed_database(
            self.engine,
            self.sessions,
            username=username,
            password=password,
        )
        bundle = load_simulation_bundle(REPOSITORY_ROOT)
        self._bind_local_documents(bundle)
        revision = self._record_existing_revision(bundle, "INITIAL_SIMULATION")
        return {"state": "INITIALIZED", "seed": seed, "revision": revision}

    def import_brand(
        self,
        bundle: BrandImportBundle,
        *,
        principal_password: str,
        reason: str = "IMPORT",
        fail_after_stage: str | None = None,
    ) -> JsonObject:
        self._require_installed()
        preflight = preflight_brand_bundle(bundle)
        if preflight["state"] != "CAN_IMPORT":
            raise ValueError(
                "品牌资料不能导入："
                + ",".join(
                    [
                        *map(str, preflight["fatal_reasons"]),
                        *map(str, preflight["missing_inputs"]),
                    ]
                )
            )
        identity = bundle.identity
        tenant = dict(identity["tenant"])
        tenant_id = str(tenant["tenant_id"])
        brand_id = str(tenant["brand_id"])
        digest = bundle_digest(bundle)
        with self.sessions.begin() as session:
            if self.engine.dialect.name == "postgresql":
                session.execute(
                    select(func.pg_advisory_xact_lock(_advisory_key(tenant_id)))
                )
            current = session.scalar(
                select(HostedBrandRevision)
                .where(
                    HostedBrandRevision.tenant_id == tenant_id,
                    HostedBrandRevision.state == "ACTIVE",
                )
                .with_for_update()
            )
            if current is not None and current.bundle_digest == digest:
                self._audit(
                    session,
                    "import",
                    "UNCHANGED",
                    tenant_id,
                    {"bundle_digest": digest},
                )
                return {
                    "state": "UNCHANGED",
                    "tenant_id": tenant_id,
                    "brand_id": brand_id,
                    "revision_number": current.revision_number,
                    "bundle_digest": digest,
                }
            self._assert_ownership(session, tenant_id, brand_id)
            counts = self._apply_bundle_rows(
                session,
                bundle,
                principal_password=principal_password,
                fail_after_stage=fail_after_stage,
            )
            if current is not None:
                current.state = "SUPERSEDED"
            revision_number = (
                1
                if current is None
                else max(
                    session.scalars(
                        select(HostedBrandRevision.revision_number).where(
                            HostedBrandRevision.tenant_id == tenant_id
                        )
                    ).all()
                )
                + 1
            )
            revision_id = f"{tenant_id}:r{revision_number}"
            session.add(
                HostedBrandRevision(
                    revision_id=revision_id,
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    revision_number=revision_number,
                    bundle_digest=digest,
                    bundle_payload=bundle_to_payload(bundle),
                    state="ACTIVE",
                    reason=reason,
                    created_at=utc_now(),
                )
            )
            self._audit(
                session,
                "import" if reason == "IMPORT" else "update",
                "APPLIED",
                revision_id,
                {"bundle_digest": digest, **counts},
            )
        return {
            "state": "APPLIED",
            "tenant_id": tenant_id,
            "brand_id": brand_id,
            "revision_number": revision_number,
            "bundle_digest": digest,
            **counts,
        }

    def revoke(
        self,
        *,
        tenant_id: str,
        object_kind: str,
        object_id: str,
        reason_ref: str,
    ) -> JsonObject:
        self._require_installed()
        with self.sessions.begin() as session:
            if object_kind == "fragment":
                row = session.get(
                    RuntimeNarrativeFragment, object_id, with_for_update=True
                )
                if row is None or row.tenant_id != tenant_id:
                    raise KeyError(object_id)
                row.status = "REVOKED"
                row.authorization_state = "REVOKED"
                row.revocation_ref = reason_ref
                payload = copy.deepcopy(row.payload)
                payload.update(
                    {
                        "status": "REVOKED",
                        "authorization_state": "REVOKED",
                        "revocation_ref": reason_ref,
                    }
                )
                row.payload = payload
                row.updated_at = utc_now()
            elif object_kind == "fact":
                row = session.get(RuntimePreciseFact, object_id, with_for_update=True)
                if row is None or row.tenant_id != tenant_id:
                    raise KeyError(object_id)
                row.status = "REVOKED"
                row.revocation_ref = reason_ref
                payload = copy.deepcopy(row.payload)
                payload.update({"status": "REVOKED", "revocation_ref": reason_ref})
                row.payload = payload
                row.updated_at = utc_now()
            elif object_kind == "authorization":
                row = session.get(RuntimeAuthorization, object_id, with_for_update=True)
                if row is None or row.tenant_id != tenant_id:
                    raise KeyError(object_id)
                row.status = "REVOKED"
                payload = copy.deepcopy(row.payload)
                payload["status"] = "REVOKED"
                payload["revocation_ref"] = reason_ref
                row.payload = payload
                row.updated_at = utc_now()
                self._sync_identity_authorization(
                    session, tenant_id, object_id, reason_ref
                )
            else:
                raise ValueError("撤回对象类型无效")
            self._audit(
                session,
                "revoke",
                "APPLIED",
                object_id,
                {"object_kind": object_kind, "reason_ref": reason_ref},
            )
        return {"state": "REVOKED", "object_kind": object_kind, "object_id": object_id}

    def rollback_brand(
        self,
        *,
        tenant_id: str,
        target_revision: int,
        principal_password: str,
    ) -> JsonObject:
        self._require_installed()
        with self.sessions() as session:
            target = session.scalar(
                select(HostedBrandRevision).where(
                    HostedBrandRevision.tenant_id == tenant_id,
                    HostedBrandRevision.revision_number == target_revision,
                )
            )
            if target is None:
                raise KeyError(f"unknown revision {target_revision}")
            bundle = bundle_from_payload(copy.deepcopy(target.bundle_payload))
        result = self.import_brand(
            bundle,
            principal_password=principal_password,
            reason=f"ROLLBACK_TO_R{target_revision}",
        )
        result["rolled_back_to_revision"] = target_revision
        return result

    def upgrade(
        self, *, target_version: int, fail_after_write: bool = False
    ) -> JsonObject:
        self._require_installed()
        if target_version != 2:
            raise ValueError("只允许已声明的 v1 到 v2 升级")
        with self.sessions.begin() as session:
            row = session.get(HostedSchemaState, self.namespace, with_for_update=True)
            if row is None:
                raise RuntimeError("运维状态未安装")
            if row.schema_version == target_version:
                return {"state": "UNCHANGED", "schema_version": target_version}
            if row.schema_version != 1:
                raise ValueError("升级来源版本不兼容")
            row.schema_version = target_version
            metadata = copy.deepcopy(row.metadata_payload)
            metadata["brand_import_transaction_version"] = 2
            metadata["upgrade_marker"] = "PKG8_SCHEMA_V2"
            row.metadata_payload = metadata
            row.updated_at = utc_now()
            if fail_after_write:
                raise RuntimeError("intentional package8 upgrade failure")
            self._audit(
                session,
                "upgrade",
                "APPLIED",
                self.namespace,
                {"from": 1, "to": 2},
            )
        return {"state": "UPGRADED", "schema_version": target_version}

    def rollback_schema(self, *, target_version: int = 1) -> JsonObject:
        self._require_installed()
        if target_version != 1:
            raise ValueError("只能回滚到已知良好 v1")
        with self.sessions.begin() as session:
            row = session.get(HostedSchemaState, self.namespace, with_for_update=True)
            if row is None:
                raise RuntimeError("运维状态未安装")
            row.schema_version = 1
            metadata = copy.deepcopy(row.metadata_payload)
            metadata["brand_import_transaction_version"] = 1
            metadata.pop("upgrade_marker", None)
            row.metadata_payload = metadata
            row.updated_at = utc_now()
            self._audit(
                session,
                "rollback-schema",
                "APPLIED",
                self.namespace,
                {"to": 1},
            )
        return {"state": "ROLLED_BACK", "schema_version": 1}

    def backup(self, *, database_url: str, output_directory: Path) -> JsonObject:
        self._require_installed()
        url = make_url(database_url)
        args, env = _database_args(url)
        output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(output_directory, 0o700)
        dump_path = output_directory / "runtime.pgdump"
        subprocess.run(
            [
                "pg_dump",
                *args,
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--file",
                str(dump_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        dump_digest = hashlib.sha256(dump_path.read_bytes()).hexdigest()
        health = self.health()
        manifest = {
            "manifest_version": "v1.0",
            "namespace": self.namespace,
            "source_database": url.database,
            "application_version": APPLICATION_VERSION,
            "schema_version": health["schema_version"],
            "created_at": utc_now().isoformat(),
            "dump_file": dump_path.name,
            "dump_sha256": dump_digest,
            "object_counts": health["object_counts"],
            "brand_revision_digest": health["brand_revision_digest"],
            "contains_secrets": False,
            "contains_real_customer_data": False,
        }
        manifest_path = output_directory / "backup_manifest.v1.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(dump_path, 0o600)
        os.chmod(manifest_path, 0o600)
        return {
            "state": "BACKED_UP",
            "manifest_path": str(manifest_path),
            "dump_sha256": dump_digest,
            "object_counts": health["object_counts"],
        }

    @staticmethod
    def restore(*, target_database_url: str, manifest_path: Path) -> JsonObject:
        url = make_url(target_database_url)
        args, env = _database_args(url)
        manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest_raw, dict):
            raise ValueError("备份清单无效")
        manifest = dict(manifest_raw)
        if (
            manifest.get("manifest_version") != "v1.0"
            or not str(manifest.get("namespace", "")).startswith(TASK_PREFIX)
            or manifest.get("contains_secrets") is not False
            or manifest.get("contains_real_customer_data") is not False
        ):
            raise ValueError("备份归属或版本无效")
        dump_path = manifest_path.parent / str(manifest.get("dump_file"))
        if not dump_path.is_file():
            raise ValueError("备份文件缺失")
        digest = hashlib.sha256(dump_path.read_bytes()).hexdigest()
        if digest != manifest.get("dump_sha256"):
            raise ValueError("备份摘要不匹配")
        from persistence import create_runtime_engine

        target_engine = create_runtime_engine(target_database_url)
        try:
            existing = [
                name
                for name in inspect(target_engine).get_table_names()
                if not name.startswith("pg_")
            ]
        finally:
            target_engine.dispose()
        if existing:
            raise ValueError("恢复目标不是空命名空间")
        subprocess.run(
            ["pg_restore", *args, "--no-owner", "--no-acl", str(dump_path)],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return {
            "state": "RESTORED",
            "target_database": url.database,
            "dump_sha256": digest,
            "expected_object_counts": manifest["object_counts"],
            "expected_brand_revision_digest": manifest["brand_revision_digest"],
        }

    def health(self) -> JsonObject:
        self._require_installed()
        models = {
            "tenants": RuntimeTenant,
            "brands": RuntimeBrand,
            "organizations": RuntimeOrganization,
            "stores": RuntimeStore,
            "principals": RuntimePrincipal,
            "accounts": RuntimeAccount,
            "authorizations": RuntimeAuthorization,
            "sources": RuntimeSource,
            "narrative_fragments": RuntimeNarrativeFragment,
            "precise_facts": RuntimePreciseFact,
            "candidates": RuntimeCandidate,
            "feedback": RuntimeFeedback,
        }
        with self.sessions() as session:
            state = session.get(HostedSchemaState, self.namespace)
            if state is None:
                raise RuntimeError("运维状态未安装")
            counts = {
                label: int(session.scalar(select(func.count()).select_from(model)) or 0)
                for label, model in models.items()
            }
            revisions = [
                {
                    "tenant_id": row.tenant_id,
                    "brand_id": row.brand_id,
                    "revision_number": row.revision_number,
                    "bundle_digest": row.bundle_digest,
                    "state": row.state,
                }
                for row in session.scalars(
                    select(HostedBrandRevision).order_by(
                        HostedBrandRevision.tenant_id,
                        HostedBrandRevision.revision_number,
                    )
                ).all()
            ]
        return {
            "state": "HEALTHY" if state.state == "KNOWN_GOOD" else state.state,
            "namespace": self.namespace,
            "schema_version": state.schema_version,
            "application_version": state.application_version,
            "object_counts": counts,
            "brand_revision_digest": digest_object(revisions),
            "secrets_included": False,
            "private_content_included": False,
            "production_ready": False,
        }

    def _require_installed(self) -> None:
        if "hosted_schema_state" not in inspect(self.engine).get_table_names():
            raise RuntimeError("请先执行安装")

    def _record_existing_revision(
        self, bundle: BrandImportBundle, reason: str
    ) -> JsonObject:
        identity = bundle.identity
        tenant = dict(identity["tenant"])
        tenant_id = str(tenant["tenant_id"])
        brand_id = str(tenant["brand_id"])
        digest = bundle_digest(bundle)
        with self.sessions.begin() as session:
            current = session.scalar(
                select(HostedBrandRevision).where(
                    HostedBrandRevision.tenant_id == tenant_id,
                    HostedBrandRevision.state == "ACTIVE",
                )
            )
            if current is not None:
                if current.bundle_digest != digest:
                    raise ValueError("初始化品牌版本与已登记版本冲突")
                return {
                    "state": "UNCHANGED",
                    "revision_number": current.revision_number,
                    "bundle_digest": digest,
                }
            session.add(
                HostedBrandRevision(
                    revision_id=f"{tenant_id}:r1",
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    revision_number=1,
                    bundle_digest=digest,
                    bundle_payload=bundle_to_payload(bundle),
                    state="ACTIVE",
                    reason=reason,
                    created_at=utc_now(),
                )
            )
            self._audit(
                session,
                "initialize",
                "APPLIED",
                tenant_id,
                {"bundle_digest": digest},
            )
        return {"state": "APPLIED", "revision_number": 1, "bundle_digest": digest}

    @staticmethod
    def _assert_ownership(session: Session, tenant_id: str, brand_id: str) -> None:
        tenant = session.get(RuntimeTenant, tenant_id)
        brand = session.get(RuntimeBrand, brand_id)
        if tenant is not None and tenant.payload.get("brand_id") != brand_id:
            raise ValueError("企业标识已经属于另一个品牌")
        if brand is not None and brand.tenant_id != tenant_id:
            raise ValueError("品牌标识已经属于另一个企业")

    def _apply_bundle_rows(
        self,
        session: Session,
        bundle: BrandImportBundle,
        *,
        principal_password: str,
        fail_after_stage: str | None,
    ) -> JsonObject:
        identity = copy.deepcopy(bundle.identity)
        tenant = dict(identity["tenant"])
        tenant_id = str(tenant["tenant_id"])
        brand_id = str(tenant["brand_id"])
        now = utc_now()
        counts = {"created_or_updated": 0, "unchanged": 0}

        def apply(model: type[ModelType], key: str, row: ModelType) -> None:
            changed = _upsert(session, model, key, row)
            counts["created_or_updated" if changed else "unchanged"] += 1

        apply(
            RuntimeTenant,
            tenant_id,
            RuntimeTenant(
                tenant_id=tenant_id,
                display_name=str(tenant["display_name"]),
                status="ACTIVE",
                payload=copy.deepcopy(tenant),
                updated_at=now,
            ),
        )
        apply(
            RuntimeBrand,
            brand_id,
            RuntimeBrand(
                brand_id=brand_id,
                tenant_id=tenant_id,
                display_name=str(
                    tenant.get("brand_display_name", tenant["display_name"])
                ),
                status="ACTIVE",
                payload={
                    "brand_id": brand_id,
                    "tenant_id": tenant_id,
                    "display_name": tenant.get(
                        "brand_display_name", tenant["display_name"]
                    ),
                    "simulation_only": True,
                    "publish_allowed": False,
                },
                updated_at=now,
            ),
        )
        for raw in identity["organizations"]:
            row = dict(raw)
            key = str(row["organization_id"])
            apply(
                RuntimeOrganization,
                key,
                RuntimeOrganization(
                    organization_id=key,
                    tenant_id=tenant_id,
                    display_name=str(row["display_name"]),
                    status=str(row.get("status", "ACTIVE")),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for raw in identity["stores"]:
            row = dict(raw)
            key = str(row["store_id"])
            apply(
                RuntimeStore,
                key,
                RuntimeStore(
                    store_id=key,
                    organization_id=str(row["organization_id"]),
                    status=str(row.get("status", "ACTIVE")),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        if fail_after_stage == "identity":
            raise RuntimeError("intentional package8 import failure")
        for raw in identity["login_principals"]:
            row = dict(raw)
            key = str(row["principal_id"])
            existing = session.get(RuntimePrincipal, key)
            password_hash = (
                existing.password_hash
                if existing is not None
                and verify_password(principal_password, existing.password_hash)
                else hash_password(principal_password)
            )
            apply(
                RuntimePrincipal,
                key,
                RuntimePrincipal(
                    principal_id=key,
                    tenant_id=tenant_id,
                    username=str(row["username"]),
                    password_hash=password_hash,
                    status=str(row.get("status", "ACTIVE")),
                    allowed_account_ids=list(row["allowed_content_account_ids"]),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for raw in identity["content_accounts"]:
            row = dict(raw)
            key = str(row["account_id"])
            apply(
                RuntimeAccount,
                key,
                RuntimeAccount(
                    account_id=key,
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    organization_id=str(row["organization_id"]),
                    store_id=row.get("store_id"),
                    display_name=str(row["display_name"]),
                    status=str(row.get("status", "ACTIVE")),
                    maker_role_ids=list(row["maker_role_ids"]),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for raw in identity["authorization_grants"]:
            row = dict(raw)
            key = str(row["authorization_id"])
            apply(
                RuntimeAuthorization,
                key,
                RuntimeAuthorization(
                    authorization_id=key,
                    tenant_id=tenant_id,
                    status=str(row["status"]),
                    valid_from=parse_time(str(row["valid_from"])),
                    valid_until=parse_time(str(row["valid_until"])),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for raw in identity["subject_confirmation_records"]:
            row = dict(raw)
            key = str(row["subject_confirmation_id"])
            apply(
                RuntimeSubjectConfirmation,
                key,
                RuntimeSubjectConfirmation(
                    confirmation_id=key,
                    tenant_id=tenant_id,
                    status=str(row["status"]),
                    valid_until=parse_time(str(row["valid_until"])),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        source_rows: dict[str, JsonObject] = {}
        for raw in (*bundle.narrative_fragments, *bundle.precise_facts):
            row = dict(raw)
            source_rows[str(row["source_id"])] = {
                "source_id": str(row["source_id"]),
                "source_ref": str(row["source_ref"]),
                "source_sha256": str(row["source_sha256"]),
                "simulation_only": True,
                "publish_allowed": False,
            }
        for source_id, row in source_rows.items():
            apply(
                RuntimeSource,
                source_id,
                RuntimeSource(
                    source_id=source_id,
                    source_ref=str(row["source_ref"]),
                    source_digest=str(row["source_sha256"]),
                    status="ACTIVE",
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for raw in bundle.narrative_fragments:
            row = dict(raw)
            key = str(row["fragment_id"])
            text = normalize_knowledge_text(str(row["text"]))
            content_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            apply(
                RuntimeNarrativeFragment,
                key,
                RuntimeNarrativeFragment(
                    fragment_id=key,
                    source_ref=str(row["source_ref"]),
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    status=str(row["status"]),
                    authorization_state=str(row["authorization_state"]),
                    authorization_ref=str(row["authorization_ref"]),
                    valid_from=parse_time(str(row["observed_at"])),
                    valid_until=parse_time(str(row["valid_until"])),
                    revocation_ref=row.get("revocation_ref"),
                    content_digest=content_digest,
                    dify_document_id=f"PKG8-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:40]}",
                    index_content_digest=content_digest,
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        for raw in bundle.precise_facts:
            row = dict(raw)
            key = str(row["fact_id"])
            apply(
                RuntimePreciseFact,
                key,
                RuntimePreciseFact(
                    fact_id=key,
                    source_ref=str(row["source_ref"]),
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    fact_kind=str(row["fact_kind"]),
                    status=str(row["status"]),
                    authorization_ref=str(row["authorization_ref"]),
                    valid_from=parse_time(str(row["effective_at"])),
                    valid_until=parse_time(str(row["valid_until"])),
                    revocation_ref=row.get("revocation_ref"),
                    payload=copy.deepcopy(row),
                    updated_at=now,
                ),
            )
        if fail_after_stage == "content":
            raise RuntimeError("intentional package8 import failure")
        settings = {
            f"identity_authority:{tenant_id}": identity,
            f"brand_expression_profile:{brand_id}": bundle.expression_profile,
            f"active_runtime_brand:{tenant_id}": {
                "tenant_id": tenant_id,
                "brand_id": brand_id,
                "identity_setting_key": f"identity_authority:{tenant_id}",
                "profile_setting_key": f"brand_expression_profile:{brand_id}",
                "source_manifest": bundle.source_manifest,
            },
        }
        for key, payload in settings.items():
            apply(
                RuntimeSetting,
                key,
                RuntimeSetting(
                    setting_key=key,
                    setting_version="v1",
                    payload=copy.deepcopy(payload),
                    source_digest=digest_object(payload),
                    updated_at=now,
                ),
            )
        return counts

    def _bind_local_documents(self, bundle: BrandImportBundle) -> None:
        mapping: dict[str, JsonObject] = {}
        for row in bundle.narrative_fragments:
            text = normalize_knowledge_text(str(row["text"]))
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            key = str(row["fragment_id"])
            mapping[key] = {
                "document_id": f"PKG8-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:40]}",
                "source_content_sha256": digest,
                "index_content_sha256": digest,
            }
        self.repository.bind_dify_documents(mapping)

    @staticmethod
    def _sync_identity_authorization(
        session: Session,
        tenant_id: str,
        authorization_id: str,
        reason_ref: str,
    ) -> None:
        setting = session.get(RuntimeSetting, f"identity_authority:{tenant_id}")
        if setting is None:
            raise KeyError(f"identity_authority:{tenant_id}")
        payload = copy.deepcopy(setting.payload)
        matches = [
            row
            for row in payload.get("authorization_grants", [])
            if isinstance(row, dict) and row.get("authorization_id") == authorization_id
        ]
        if len(matches) != 1:
            raise ValueError("授权真源无法闭合")
        matches[0]["status"] = "REVOKED"
        matches[0]["revocation_ref"] = reason_ref
        setting.payload = payload
        setting.source_digest = digest_object(payload)
        setting.updated_at = utc_now()

    def _audit(
        self,
        session: Session,
        command: str,
        status: str,
        object_ref: str,
        details: JsonObject,
    ) -> None:
        payload = {
            "namespace": self.namespace,
            "command": command,
            "status": status,
            "object_ref": object_ref,
            "details": details,
        }
        digest = digest_object(payload)
        operation_id = f"PKG8-{command.upper()}-{digest[:24]}"
        if session.get(HostedOperationAudit, operation_id) is None:
            session.add(
                HostedOperationAudit(
                    operation_id=operation_id,
                    namespace=self.namespace,
                    command=command,
                    status=status,
                    object_ref=object_ref,
                    object_digest=digest,
                    details=copy.deepcopy(details),
                    created_at=utc_now(),
                )
            )


def preflight_environment(
    *,
    database_url: str,
    namespace: str,
    secret_file: Path | None = None,
    minimum_free_bytes: int = 64 * 1024 * 1024,
) -> JsonObject:
    _safe_namespace(namespace)
    url = make_url(database_url)
    _database_args(url)
    free_bytes = shutil.disk_usage(PACKAGE_ROOT).free
    if free_bytes < minimum_free_bytes:
        raise ValueError("磁盘空间不足")
    if secret_file is not None:
        mode = secret_file.stat().st_mode & 0o777
        if mode & 0o077:
            raise ValueError("密钥文件权限过宽")
    required = {
        "package7_app": PACKAGE_7_ROOT / "dify_app.v1.yaml",
        "package7_bridge": PACKAGE_7_ROOT / "bridge_app.py",
        "package7_manifest": PACKAGE_7_ROOT / "dify_end_to_end_manifest.v1.json",
    }
    missing = [label for label, path in required.items() if not path.is_file()]
    if missing:
        raise ValueError(f"前置对象缺失：{','.join(missing)}")
    return {
        "state": "CAN_PROCEED",
        "namespace": namespace,
        "database_name": url.database,
        "free_space_sufficient": True,
        "secret_file_checked": secret_file is not None,
        "required_object_digests": {
            label: hashlib.sha256(path.read_bytes()).hexdigest()
            for label, path in required.items()
        },
        "credentials_included": False,
    }
