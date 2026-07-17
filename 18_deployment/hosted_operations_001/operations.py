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
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import Index, MetaData, Table, delete, func, inspect, select
from sqlalchemy.engine import Connection, Engine, URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
FOUNDATION_ROOT = REPOSITORY_ROOT / "11_product_foundation/public_foundation_001"
PACKAGE_2_ROOT = (
    REPOSITORY_ROOT / "12_expression_service/expression_runtime_adapter_001"
)
PACKAGE_5_ROOT = REPOSITORY_ROOT / "15_brand_retrieval/brand_fact_retrieval_001"
PACKAGE_6_ROOT = REPOSITORY_ROOT / "16_composition_runtime/fact_aware_plan_adapter_001"
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
    canonical_json,
    create_runtime_engine,
    create_session_factory,
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
APPLICATION_VERSION = "package8-v1.1"
SCHEMA_VERSION = 1
TASK_PREFIX = "diyu-pkg8-"
BRAND_REVISION_INDEX = "ix_hosted_brand_revision_tenant_digest"
SUPPORTED_RESTORE_SCHEMA_VERSIONS = {1, 2}
MATERIALIZATION_SCHEMA_VERSION = "v1.0"
RELEASE_PACKAGE_SCHEMA_VERSION = "v1.0"
MATERIALIZATION_FILE_NAME = "dify_narrative_documents.v1.jsonl"
MATERIALIZATION_MANIFEST_NAME = "dify_materialization_manifest.v1.json"
RELEASE_MANIFEST_NAME = "release_bundle_manifest.v1.json"
RELEASE_OBJECT_SPECS: tuple[tuple[str, str, Path], ...] = (
    ("implementation", APPLICATION_VERSION, PACKAGE_ROOT / "operations.py"),
    ("implementation", APPLICATION_VERSION, PACKAGE_ROOT / "hosted_operations.py"),
    ("implementation", APPLICATION_VERSION, PACKAGE_ROOT / "brand_bundle.py"),
    ("implementation", APPLICATION_VERSION, PACKAGE_ROOT / "hosted_models.py"),
    (
        "brand_import_template",
        "brand-import-v1.1",
        PACKAGE_ROOT / "brand_input_template.v1.yaml",
    ),
    (
        "retrieval_rebuild_contract",
        "runtime-materialization-v1",
        PACKAGE_ROOT / "dify_materialization_manifest.v1.json",
    ),
    ("dify_application", "dify-app-v1", PACKAGE_7_ROOT / "dify_app.v1.yaml"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "bridge_app.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "contracts.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "dify_chat.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "dify_knowledge.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "persistence.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "runtime_models.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "runtime_retrieval.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "runtime_service.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "security.py"),
    ("thin_bridge", "package7-bridge-v1", PACKAGE_7_ROOT / "seed_runtime.py"),
    ("brand_importer", "brand-import-v1.1", PACKAGE_7_ROOT / "brand_import.py"),
    (
        "brand_import_contract",
        "brand-import-v1.1",
        PACKAGE_7_ROOT / "brand_import_contract.v1.yaml",
    ),
    (
        "brand_runtime_profile",
        "package7-brand-profile-v1",
        PACKAGE_7_ROOT / "brand_runtime_profile.v1.yaml",
    ),
    (
        "dify_importer",
        "runtime-materialization-v1",
        PACKAGE_7_ROOT / "provision_dify.py",
    ),
    (
        "deployment_entrypoint",
        "runtime-materialization-v1",
        PACKAGE_7_ROOT / "deploy_remote.sh",
    ),
    ("portal", "package7-portal-v1", PACKAGE_7_ROOT / "portal.html"),
    ("portal", "package7-portal-v1", PACKAGE_7_ROOT / "portal.js"),
    ("portal", "package7-portal-v1", PACKAGE_7_ROOT / "portal.css"),
    (
        "expression_runtime_dependency",
        "package2-light-expression-v1",
        PACKAGE_2_ROOT / "light_expression_service.py",
    ),
    (
        "expression_runtime_dependency",
        "package2-light-expression-v1",
        PACKAGE_2_ROOT / "neutral_expression_profile.v1.yaml",
    ),
    (
        "expression_runtime_dependency",
        "package2-light-expression-v1",
        PACKAGE_2_ROOT / "service_manifest.v1.yaml",
    ),
    (
        "retrieval_runtime_dependency",
        "package5-brand-retrieval-v1",
        PACKAGE_5_ROOT / "brand_fact_retrieval.py",
    ),
    (
        "retrieval_runtime_dependency",
        "package5-brand-retrieval-v1",
        PACKAGE_5_ROOT / "retrieval_manifest.v1.json",
    ),
    (
        "retrieval_runtime_dependency",
        "package5-brand-retrieval-v1",
        PACKAGE_5_ROOT / "data/expression_candidates.v1.json",
    ),
    (
        "retrieval_runtime_dependency",
        "package5-brand-retrieval-v1",
        PACKAGE_5_ROOT / "data/retrieval_fragments.v1.jsonl",
    ),
    (
        "retrieval_runtime_dependency",
        "package5-brand-retrieval-v1",
        PACKAGE_5_ROOT / "data/source_dispositions.v1.jsonl",
    ),
    (
        "retrieval_runtime_dependency",
        "package5-brand-retrieval-v1",
        PACKAGE_5_ROOT / "data/verified_precise_facts.v1.jsonl",
    ),
    (
        "composition_runtime_dependency",
        "package6-fact-aware-plan-v1",
        PACKAGE_6_ROOT / "fact_aware_plan_adapter.py",
    ),
    (
        "public_contract_dependency",
        "public-foundation-v1",
        FOUNDATION_ROOT / "identity/simulation_tenant.v1.yaml",
    ),
    (
        "public_contract_dependency",
        "public-foundation-v1",
        FOUNDATION_ROOT / "taxonomy/topic_product_mapping.v1.yaml",
    ),
    (
        "dify_shell_dependency",
        "dify-shell-v1",
        REPOSITORY_ROOT
        / "14_dify_shell/dify_content_shell_001/state_action_mapping.v1.json",
    ),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("时间必须包含时区")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _tool_version(executable: str) -> str:
    path = shutil.which(executable)
    if path is None:
        raise ValueError(f"缺少 {executable} 工具")
    completed = subprocess.run(
        [path, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _health_digest(health: JsonObject) -> str:
    return digest_object(
        {
            "application_version": health["application_version"],
            "schema_version": health["schema_version"],
            "schema_features": health["schema_features"],
            "object_counts": health["object_counts"],
            "brand_revision_digest": health["brand_revision_digest"],
        }
    )


def _canonicalize_database_value(value: Any, namespace_aliases: set[str]) -> Any:
    """Normalize only the operational namespace while preserving all row content."""

    if isinstance(value, str):
        return "__DIYU_TASK_NAMESPACE__" if value in namespace_aliases else value
    if isinstance(value, dict):
        return {
            str(key): _canonicalize_database_value(item, namespace_aliases)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize_database_value(item, namespace_aliases) for item in value]
    return value


def _database_snapshot(engine: Engine, namespace_aliases: set[str]) -> JsonObject:
    """Digest every user table schema and row without exposing sensitive values."""

    inspector = inspect(engine)
    table_names = sorted(inspector.get_table_names(schema="public"))
    tables: JsonObject = {}
    with engine.connect() as connection:
        for table_name in table_names:
            metadata = MetaData()
            table = Table(
                table_name,
                metadata,
                schema="public",
                autoload_with=connection,
            )
            columns = [
                {
                    "name": column.name,
                    "type": str(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                }
                for column in table.columns
            ]
            row_digests = sorted(
                digest_object(
                    {
                        column.name: _canonicalize_database_value(
                            row[column.name], namespace_aliases
                        )
                        for column in table.columns
                    }
                )
                for row in connection.execute(select(table)).mappings()
            )
            indexes = sorted(
                (
                    {
                        "name": str(index.get("name")),
                        "columns": list(index.get("column_names") or []),
                        "unique": bool(index.get("unique")),
                    }
                    for index in inspector.get_indexes(table_name, schema="public")
                ),
                key=lambda item: (item["name"], item["columns"]),
            )
            tables[table_name] = {
                "columns": columns,
                "indexes": indexes,
                "row_count": len(row_digests),
                "row_content_digest": digest_object(row_digests),
            }
        sequence_rows = connection.exec_driver_sql(
            "SELECT sequencename, data_type, start_value, min_value, max_value, "
            "increment_by, cycle, cache_size, last_value "
            "FROM pg_catalog.pg_sequences WHERE schemaname = 'public' "
            "ORDER BY sequencename"
        ).mappings()
        sequences = [
            {
                "name": str(row["sequencename"]),
                "data_type": str(row["data_type"]),
                "start_value": int(row["start_value"]),
                "min_value": int(row["min_value"]),
                "max_value": int(row["max_value"]),
                "increment_by": int(row["increment_by"]),
                "cycle": bool(row["cycle"]),
                "cache_size": int(row["cache_size"]),
                "last_value": (
                    int(row["last_value"]) if row["last_value"] is not None else None
                ),
            }
            for row in sequence_rows
        ]
    snapshot = {
        "schema": "public",
        "table_names": table_names,
        "tables": tables,
        "sequences": sequences,
    }
    snapshot["snapshot_digest"] = digest_object(snapshot)
    return snapshot


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_canonical_json(path: Path, value: JsonObject) -> None:
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _safe_relative_path(value: object, *, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} 路径无效")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path == Path("."):
        raise ValueError(f"{label} 路径越界")
    return path


def _manifest_without_digest(manifest: JsonObject, field: str) -> JsonObject:
    payload = copy.deepcopy(manifest)
    payload.pop(field, None)
    return payload


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
                            "supported_data_modes": [
                                "SIMULATION",
                                "AUTHORIZED_REAL",
                            ],
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
                fragment = session.get(
                    RuntimeNarrativeFragment, object_id, with_for_update=True
                )
                if fragment is None or fragment.tenant_id != tenant_id:
                    raise KeyError(object_id)
                fragment.status = "REVOKED"
                fragment.authorization_state = "REVOKED"
                fragment.revocation_ref = reason_ref
                payload = copy.deepcopy(fragment.payload)
                payload.update(
                    {
                        "status": "REVOKED",
                        "authorization_state": "REVOKED",
                        "revocation_ref": reason_ref,
                    }
                )
                fragment.payload = payload
                fragment.updated_at = utc_now()
            elif object_kind == "fact":
                fact = session.get(RuntimePreciseFact, object_id, with_for_update=True)
                if fact is None or fact.tenant_id != tenant_id:
                    raise KeyError(object_id)
                fact.status = "REVOKED"
                fact.revocation_ref = reason_ref
                payload = copy.deepcopy(fact.payload)
                payload.update({"status": "REVOKED", "revocation_ref": reason_ref})
                fact.payload = payload
                fact.updated_at = utc_now()
            elif object_kind == "authorization":
                authorization = session.get(
                    RuntimeAuthorization, object_id, with_for_update=True
                )
                if authorization is None or authorization.tenant_id != tenant_id:
                    raise KeyError(object_id)
                authorization.status = "REVOKED"
                payload = copy.deepcopy(authorization.payload)
                payload["status"] = "REVOKED"
                payload["revocation_ref"] = reason_ref
                authorization.payload = payload
                authorization.updated_at = utc_now()
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

    @staticmethod
    def _revision_index_exists(bind: Engine | Connection) -> bool:
        return any(
            row.get("name") == BRAND_REVISION_INDEX
            for row in inspect(bind).get_indexes(HostedBrandRevision.__tablename__)
        )

    @staticmethod
    def _revision_index(bind: Connection) -> Index:
        metadata = MetaData()
        revisions = Table(
            HostedBrandRevision.__tablename__,
            metadata,
            autoload_with=bind,
        )
        return Index(
            BRAND_REVISION_INDEX,
            revisions.c.tenant_id,
            revisions.c.bundle_digest,
        )

    def upgrade(
        self, *, target_version: int, fail_after_write: bool = False
    ) -> JsonObject:
        self._require_installed()
        if target_version != 2:
            raise ValueError("只允许已声明的 v1 到 v2 升级")
        with self.engine.begin() as connection:
            with Session(bind=connection, expire_on_commit=False) as session:
                row = session.get(
                    HostedSchemaState,
                    self.namespace,
                    with_for_update=True,
                )
                if row is None:
                    raise RuntimeError("运维状态未安装")
                index_exists = self._revision_index_exists(connection)
                if row.schema_version == target_version:
                    if not index_exists:
                        raise RuntimeError("v2 结构索引缺失")
                    return {"state": "UNCHANGED", "schema_version": target_version}
                if row.schema_version != 1 or index_exists:
                    raise ValueError("升级来源版本不兼容或结构已漂移")
                self._revision_index(connection).create(connection)
                row.schema_version = target_version
                metadata = copy.deepcopy(row.metadata_payload)
                metadata["brand_import_transaction_version"] = 2
                metadata["upgrade_marker"] = "PKG8_SCHEMA_V2"
                metadata["revision_lookup_index"] = BRAND_REVISION_INDEX
                row.metadata_payload = metadata
                row.updated_at = utc_now()
                session.flush()
                if fail_after_write:
                    raise RuntimeError("intentional package8 upgrade failure")
                self._audit(
                    session,
                    "upgrade",
                    "APPLIED",
                    self.namespace,
                    {
                        "from": 1,
                        "to": 2,
                        "created_index": BRAND_REVISION_INDEX,
                    },
                )
                session.flush()
        return {
            "state": "UPGRADED",
            "schema_version": target_version,
            "created_index": BRAND_REVISION_INDEX,
        }

    def rollback_schema(self, *, target_version: int = 1) -> JsonObject:
        self._require_installed()
        if target_version != 1:
            raise ValueError("只能回滚到已知良好 v1")
        with self.engine.begin() as connection:
            with Session(bind=connection, expire_on_commit=False) as session:
                row = session.get(
                    HostedSchemaState,
                    self.namespace,
                    with_for_update=True,
                )
                if row is None:
                    raise RuntimeError("运维状态未安装")
                index_exists = self._revision_index_exists(connection)
                if row.schema_version == 1:
                    if index_exists:
                        raise RuntimeError("v1 结构意外包含 v2 索引")
                    return {"state": "UNCHANGED", "schema_version": 1}
                if row.schema_version != 2 or not index_exists:
                    raise ValueError("回滚来源版本不兼容或结构已漂移")
                self._revision_index(connection).drop(connection)
                row.schema_version = 1
                metadata = copy.deepcopy(row.metadata_payload)
                metadata["brand_import_transaction_version"] = 1
                metadata.pop("upgrade_marker", None)
                metadata.pop("revision_lookup_index", None)
                row.metadata_payload = metadata
                row.updated_at = utc_now()
                self._audit(
                    session,
                    "rollback-schema",
                    "APPLIED",
                    self.namespace,
                    {"to": 1, "dropped_index": BRAND_REVISION_INDEX},
                )
                session.flush()
        return {
            "state": "ROLLED_BACK",
            "schema_version": 1,
            "dropped_index": BRAND_REVISION_INDEX,
        }

    def materialize_dify(
        self,
        *,
        output_directory: Path,
        as_of: datetime,
    ) -> JsonObject:
        """Project current authorized narrative rows into one Dify import package."""

        self._require_installed()
        if as_of.tzinfo is None:
            raise ValueError("资料物化时间必须包含时区")
        as_of_utc = as_of.astimezone(timezone.utc)
        output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(output_directory, 0o700)
        document_path = output_directory / MATERIALIZATION_FILE_NAME
        manifest_path = output_directory / MATERIALIZATION_MANIFEST_NAME

        with self.sessions() as session:
            tenants = {
                row.tenant_id: row
                for row in session.scalars(select(RuntimeTenant)).all()
            }
            brands = {
                row.brand_id: row for row in session.scalars(select(RuntimeBrand)).all()
            }
            organizations = {
                row.organization_id: row
                for row in session.scalars(select(RuntimeOrganization)).all()
            }
            stores = {
                row.store_id: row for row in session.scalars(select(RuntimeStore)).all()
            }
            accounts = {
                row.account_id: row
                for row in session.scalars(select(RuntimeAccount)).all()
            }
            authorizations = {
                row.authorization_id: row
                for row in session.scalars(select(RuntimeAuthorization)).all()
            }
            sources = {
                row.source_id: row
                for row in session.scalars(select(RuntimeSource)).all()
            }
            fragments = list(
                session.scalars(
                    select(RuntimeNarrativeFragment).order_by(
                        RuntimeNarrativeFragment.fragment_id
                    )
                ).all()
            )

        excluded_counts: dict[str, int] = {}

        def exclude(reason: str) -> None:
            excluded_counts[reason] = excluded_counts.get(reason, 0) + 1

        documents: list[JsonObject] = []
        for fragment in fragments:
            payload = copy.deepcopy(fragment.payload)
            tenant = tenants.get(fragment.tenant_id)
            brand = brands.get(fragment.brand_id)
            if (
                tenant is None
                or tenant.status != "ACTIVE"
                or brand is None
                or brand.status != "ACTIVE"
                or brand.tenant_id != fragment.tenant_id
            ):
                exclude("TENANT_OR_BRAND_INACTIVE")
                continue
            if (
                fragment.status != "ACTIVE"
                or fragment.authorization_state != "GRANTED"
                or fragment.revocation_ref is not None
                or not fragment.valid_from <= as_of_utc < fragment.valid_until
            ):
                exclude("FRAGMENT_REVOKED_EXPIRED_OR_INACTIVE")
                continue
            authorization = authorizations.get(fragment.authorization_ref)
            if (
                authorization is None
                or authorization.tenant_id != fragment.tenant_id
                or authorization.status != "GRANTED"
                or not authorization.valid_from <= as_of_utc < authorization.valid_until
            ):
                exclude("AUTHORIZATION_MISSING_REVOKED_OR_EXPIRED")
                continue
            source_id = payload.get("source_id")
            source = sources.get(source_id) if isinstance(source_id, str) else None
            if (
                source is None
                or source.status != "ACTIVE"
                or not fragment.source_ref
                or source.source_digest != payload.get("source_sha256")
            ):
                exclude("SOURCE_MISSING_OR_INACTIVE")
                continue
            account_ids = payload.get("applicable_content_account_ids")
            organization_ids = payload.get("applicable_organization_ids")
            store_ids = payload.get("applicable_store_ids")
            if (
                not isinstance(account_ids, list)
                or not account_ids
                or not isinstance(organization_ids, list)
                or not organization_ids
                or not isinstance(store_ids, list)
            ):
                exclude("SCOPE_METADATA_INVALID")
                continue
            scoped_accounts = [accounts.get(value) for value in account_ids]
            if any(
                row is None
                or row.status != "ACTIVE"
                or row.tenant_id != fragment.tenant_id
                or row.brand_id != fragment.brand_id
                for row in scoped_accounts
            ):
                exclude("ACCOUNT_SCOPE_INACTIVE_OR_CROSS_BRAND")
                continue
            if any(
                not isinstance(value, str)
                or value not in organizations
                or organizations[value].status != "ACTIVE"
                or organizations[value].tenant_id != fragment.tenant_id
                for value in organization_ids
            ):
                exclude("ORGANIZATION_SCOPE_INACTIVE_OR_CROSS_TENANT")
                continue
            if any(
                value is not None
                and (
                    not isinstance(value, str)
                    or value not in stores
                    or stores[value].status != "ACTIVE"
                    or stores[value].organization_id not in organization_ids
                )
                for value in store_ids
            ):
                exclude("STORE_SCOPE_INACTIVE_OR_CROSS_ORGANIZATION")
                continue
            if payload.get("publish_allowed") is not False:
                exclude("PUBLISH_BOUNDARY_INVALID")
                continue
            text = normalize_knowledge_text(str(payload.get("text", "")))
            if not text or hashlib.sha256(text.encode("utf-8")).hexdigest() != (
                fragment.content_digest
            ):
                exclude("CONTENT_DIGEST_INVALID")
                continue
            simulation_only = payload.get("simulation_only") is True
            document = copy.deepcopy(payload)
            document.update(
                {
                    "materialization_id": f"dify-runtime://{fragment.fragment_id}",
                    "fragment_id": fragment.fragment_id,
                    "tenant_id": fragment.tenant_id,
                    "brand_id": fragment.brand_id,
                    "tenant_status": tenant.status,
                    "brand_status": brand.status,
                    "source_id": source.source_id,
                    "source_ref": source.source_ref,
                    "source_sha256": source.source_digest,
                    "fragment_sha256": fragment.content_digest,
                    "content_digest": fragment.content_digest,
                    "authorization_ref": fragment.authorization_ref,
                    "authorization_state": fragment.authorization_state,
                    "observed_at": _iso(fragment.valid_from),
                    "valid_until": _iso(fragment.valid_until),
                    "revocation_ref": fragment.revocation_ref,
                    "status": fragment.status,
                    "applicable_content_account_ids": sorted(map(str, account_ids)),
                    "applicable_organization_ids": sorted(map(str, organization_ids)),
                    "applicable_store_ids": sorted(
                        store_ids,
                        key=lambda value: "" if value is None else str(value),
                    ),
                    "data_mode": (
                        "SIMULATION" if simulation_only else "AUTHORIZED_REAL"
                    ),
                    "simulation_only": simulation_only,
                    "test_fixture_only": payload.get(
                        "test_fixture_only", simulation_only
                    ),
                    "publish_allowed": False,
                    "runtime_consumable": False,
                }
            )
            documents.append(document)

        documents.sort(key=lambda row: str(row["fragment_id"]))
        serialized = "".join(f"{canonical_json(row)}\n" for row in documents)
        document_path.write_text(serialized, encoding="utf-8")
        os.chmod(document_path, 0o600)
        document_digest = _sha256_file(document_path)
        source_state = {
            "tenants": [
                {
                    "tenant_id": row.tenant_id,
                    "status": row.status,
                    "payload": row.payload,
                }
                for row in sorted(tenants.values(), key=lambda item: item.tenant_id)
            ],
            "brands": [
                {
                    "brand_id": row.brand_id,
                    "tenant_id": row.tenant_id,
                    "status": row.status,
                    "payload": row.payload,
                }
                for row in sorted(brands.values(), key=lambda item: item.brand_id)
            ],
            "organizations": [
                {
                    "organization_id": row.organization_id,
                    "tenant_id": row.tenant_id,
                    "status": row.status,
                    "payload": row.payload,
                }
                for row in sorted(
                    organizations.values(), key=lambda item: item.organization_id
                )
            ],
            "stores": [
                {
                    "store_id": row.store_id,
                    "organization_id": row.organization_id,
                    "status": row.status,
                    "payload": row.payload,
                }
                for row in sorted(stores.values(), key=lambda item: item.store_id)
            ],
            "accounts": [
                {
                    "account_id": row.account_id,
                    "tenant_id": row.tenant_id,
                    "brand_id": row.brand_id,
                    "organization_id": row.organization_id,
                    "store_id": row.store_id,
                    "status": row.status,
                    "payload": row.payload,
                }
                for row in sorted(accounts.values(), key=lambda item: item.account_id)
            ],
            "authorizations": [
                {
                    "authorization_id": row.authorization_id,
                    "tenant_id": row.tenant_id,
                    "status": row.status,
                    "valid_from": row.valid_from,
                    "valid_until": row.valid_until,
                    "payload": row.payload,
                }
                for row in sorted(
                    authorizations.values(), key=lambda item: item.authorization_id
                )
            ],
            "sources": [
                {
                    "source_id": row.source_id,
                    "source_ref": row.source_ref,
                    "source_digest": row.source_digest,
                    "status": row.status,
                    "payload": row.payload,
                }
                for row in sorted(sources.values(), key=lambda item: item.source_id)
            ],
            "fragments": [
                {
                    "fragment_id": row.fragment_id,
                    "source_ref": row.source_ref,
                    "tenant_id": row.tenant_id,
                    "brand_id": row.brand_id,
                    "status": row.status,
                    "authorization_state": row.authorization_state,
                    "authorization_ref": row.authorization_ref,
                    "valid_from": row.valid_from,
                    "valid_until": row.valid_until,
                    "revocation_ref": row.revocation_ref,
                    "content_digest": row.content_digest,
                    "payload": row.payload,
                }
                for row in fragments
            ],
        }
        manifest: JsonObject = {
            "schema_version": MATERIALIZATION_SCHEMA_VERSION,
            "materialization_kind": "DIFY_NARRATIVE_IMPORT",
            "source_kind": "RUNTIME_POSTGRESQL_PROJECTION",
            "application_version": APPLICATION_VERSION,
            "database_schema_version": self.health()["schema_version"],
            "materialized_at": _iso(as_of_utc),
            "runtime_source_digest": digest_object(source_state),
            "document_file": document_path.name,
            "document_sha256": document_digest,
            "document_count": len(documents),
            "tenant_ids": sorted({str(row["tenant_id"]) for row in documents}),
            "brand_ids": sorted({str(row["brand_id"]) for row in documents}),
            "excluded_counts": dict(sorted(excluded_counts.items())),
            "scope_metadata_fields": [
                "tenant_id",
                "brand_id",
                "applicable_organization_ids",
                "applicable_store_ids",
                "applicable_content_account_ids",
                "authorization_ref",
                "authorization_state",
                "observed_at",
                "valid_until",
                "revocation_ref",
                "source_id",
                "source_ref",
                "simulation_only",
                "test_fixture_only",
            ],
            "filter_policy": (
                "ACTIVE_SCOPE_AND_SOURCE__GRANTED_CURRENT_AUTHORIZATION__"
                "ACTIVE_CURRENT_UNREVOKED_FRAGMENT"
            ),
            "second_retrieval_truth_created": False,
            "real_dify_import_performed": False,
            "contains_real_customer_data": False,
            "readiness": {
                "DIFY_ready": False,
                "production_servable": False,
                "release_ready": False,
                "production_ready": False,
            },
        }
        manifest["materialization_digest"] = digest_object(manifest)
        _write_canonical_json(manifest_path, manifest)
        os.chmod(manifest_path, 0o600)
        return {
            "state": "MATERIALIZED",
            "manifest_path": str(manifest_path),
            "document_path": str(document_path),
            "document_count": len(documents),
            "document_sha256": document_digest,
            "materialization_digest": manifest["materialization_digest"],
            "brand_ids": manifest["brand_ids"],
            "excluded_counts": manifest["excluded_counts"],
        }

    def _build_release_bundle(
        self,
        *,
        release_directory: Path,
        materialization: JsonObject,
    ) -> JsonObject:
        objects_directory = release_directory / "objects"
        objects_directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        records: list[JsonObject] = []
        for object_type, version, source_path in RELEASE_OBJECT_SPECS:
            if not source_path.is_file() or not source_path.is_relative_to(
                REPOSITORY_ROOT
            ):
                raise ValueError("发布对象缺失或越界")
            source_relative = source_path.relative_to(REPOSITORY_ROOT)
            release_relative = Path("objects") / source_relative
            target = release_directory / release_relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(source_path, target)
            os.chmod(target, 0o600)
            records.append(
                {
                    "object_type": object_type,
                    "version": version,
                    "source_path": source_relative.as_posix(),
                    "release_path": release_relative.as_posix(),
                    "sha256": _sha256_file(target),
                }
            )
        records.sort(key=lambda row: str(row["source_path"]))
        materialization_manifest = Path(str(materialization["manifest_path"]))
        materialization_document = Path(str(materialization["document_path"]))
        release_manifest: JsonObject = {
            "schema_version": RELEASE_PACKAGE_SCHEMA_VERSION,
            "application_version": APPLICATION_VERSION,
            "object_count": len(records),
            "objects": records,
            "object_inventory_digest": digest_object(records),
            "retrieval_rebuild_inputs": {
                "manifest_path": materialization_manifest.relative_to(
                    release_directory
                ).as_posix(),
                "manifest_sha256": _sha256_file(materialization_manifest),
                "materialization_digest": materialization["materialization_digest"],
                "document_path": materialization_document.relative_to(
                    release_directory
                ).as_posix(),
                "document_sha256": materialization["document_sha256"],
                "document_count": materialization["document_count"],
            },
            "contains_plaintext_secrets": False,
            "contains_real_customer_data": False,
            "real_dify_import_performed": False,
            "production_ready": False,
        }
        release_manifest["release_bundle_digest"] = digest_object(release_manifest)
        release_manifest_path = release_directory / RELEASE_MANIFEST_NAME
        _write_canonical_json(release_manifest_path, release_manifest)
        os.chmod(release_manifest_path, 0o600)
        return {
            "manifest_path": release_manifest_path,
            "manifest_sha256": _sha256_file(release_manifest_path),
            "release_bundle_digest": release_manifest["release_bundle_digest"],
            "object_count": len(records),
        }

    @staticmethod
    def _validate_release_bundle(
        *,
        backup_directory: Path,
        backup_manifest: JsonObject,
    ) -> tuple[JsonObject, JsonObject]:
        release_relative = _safe_relative_path(
            backup_manifest.get("release_bundle_manifest"),
            label="发布包清单",
        )
        release_manifest_path = backup_directory / release_relative
        if not release_manifest_path.is_file():
            raise ValueError("发布包清单缺失")
        if _sha256_file(release_manifest_path) != backup_manifest.get(
            "release_bundle_manifest_sha256"
        ):
            raise ValueError("发布包清单摘要不匹配")
        raw = json.loads(release_manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("发布包清单无效")
        release_manifest = dict(raw)
        recorded_digest = release_manifest.get("release_bundle_digest")
        if (
            release_manifest.get("schema_version") != RELEASE_PACKAGE_SCHEMA_VERSION
            or release_manifest.get("application_version") != APPLICATION_VERSION
            or release_manifest.get("contains_plaintext_secrets") is not False
            or release_manifest.get("contains_real_customer_data") is not False
            or release_manifest.get("real_dify_import_performed") is not False
            or release_manifest.get("production_ready") is not False
            or not isinstance(recorded_digest, str)
            or digest_object(
                _manifest_without_digest(release_manifest, "release_bundle_digest")
            )
            != recorded_digest
            or backup_manifest.get("release_bundle_digest") != recorded_digest
        ):
            raise ValueError("发布包版本或摘要无效")
        objects = release_manifest.get("objects")
        if not isinstance(objects, list):
            raise ValueError("发布对象清单无效")
        expected = {
            (
                object_type,
                version,
                source_path.relative_to(REPOSITORY_ROOT).as_posix(),
            )
            for object_type, version, source_path in RELEASE_OBJECT_SPECS
        }
        actual: set[tuple[str, str, str]] = set()
        for raw_item in objects:
            if not isinstance(raw_item, dict):
                raise ValueError("发布对象条目无效")
            item = dict(raw_item)
            key = (
                str(item.get("object_type", "")),
                str(item.get("version", "")),
                str(item.get("source_path", "")),
            )
            actual.add(key)
            release_path = _safe_relative_path(
                item.get("release_path"), label="发布对象"
            )
            target = release_manifest_path.parent / release_path
            source_path = REPOSITORY_ROOT / key[2]
            digest = item.get("sha256")
            if (
                not target.is_file()
                or not isinstance(digest, str)
                or _sha256_file(target) != digest
                or not source_path.is_file()
                or _sha256_file(source_path) != digest
            ):
                raise ValueError("发布对象缺失、损坏或与实现版本不匹配")
        if (
            actual != expected
            or len(actual) != len(objects)
            or release_manifest.get("object_count") != len(expected)
            or release_manifest.get("object_inventory_digest") != digest_object(objects)
        ):
            raise ValueError("发布对象清单不完整")
        rebuild = release_manifest.get("retrieval_rebuild_inputs")
        if not isinstance(rebuild, dict):
            raise ValueError("检索资料重建输入缺失")
        materialization_manifest_path = release_manifest_path.parent / (
            _safe_relative_path(rebuild.get("manifest_path"), label="资料清单")
        )
        materialization_document_path = release_manifest_path.parent / (
            _safe_relative_path(rebuild.get("document_path"), label="资料文件")
        )
        if (
            not materialization_manifest_path.is_file()
            or not materialization_document_path.is_file()
            or _sha256_file(materialization_manifest_path)
            != rebuild.get("manifest_sha256")
            or _sha256_file(materialization_document_path)
            != rebuild.get("document_sha256")
        ):
            raise ValueError("检索资料重建输入缺失或损坏")
        materialization_raw = json.loads(
            materialization_manifest_path.read_text(encoding="utf-8")
        )
        if not isinstance(materialization_raw, dict):
            raise ValueError("资料物化清单无效")
        materialization_manifest = dict(materialization_raw)
        materialization_digest = materialization_manifest.get("materialization_digest")
        if (
            materialization_manifest.get("schema_version")
            != MATERIALIZATION_SCHEMA_VERSION
            or materialization_manifest.get("application_version")
            != APPLICATION_VERSION
            or materialization_manifest.get("source_kind")
            != "RUNTIME_POSTGRESQL_PROJECTION"
            or materialization_manifest.get("document_file")
            != materialization_document_path.name
            or materialization_manifest.get("document_sha256")
            != rebuild.get("document_sha256")
            or materialization_manifest.get("document_count")
            != rebuild.get("document_count")
            or materialization_digest != rebuild.get("materialization_digest")
            or not isinstance(materialization_digest, str)
            or digest_object(
                _manifest_without_digest(
                    materialization_manifest, "materialization_digest"
                )
            )
            != materialization_digest
        ):
            raise ValueError("资料物化版本或摘要无效")
        return release_manifest, materialization_manifest

    def backup(self, *, database_url: str, output_directory: Path) -> JsonObject:
        self._require_installed()
        url = make_url(database_url)
        args, env = _database_args(url)
        if url.database != self.namespace:
            raise ValueError("备份数据库与当前命名空间不一致")
        output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(output_directory, 0o700)
        dump_path = output_directory / "runtime.pgdump"
        manifest_path = output_directory / "backup_manifest.v1.json"
        release_directory = output_directory / "release_bundle"
        if dump_path.exists() or manifest_path.exists() or release_directory.exists():
            raise ValueError("备份目标已包含第8包备份对象")
        backup_time = utc_now()
        snapshot_before = _database_snapshot(self.engine, {self.namespace})
        materialization = self.materialize_dify(
            output_directory=release_directory / "materialization",
            as_of=backup_time,
        )
        release = self._build_release_bundle(
            release_directory=release_directory,
            materialization=materialization,
        )
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
        snapshot_after = _database_snapshot(self.engine, {self.namespace})
        if snapshot_before != snapshot_after:
            raise RuntimeError("备份期间数据库发生变化，拒绝生成不一致清单")
        health = self.health()
        if health["database_snapshot_digest"] != snapshot_after["snapshot_digest"]:
            raise RuntimeError("备份健康状态与全库快照不一致")
        manifest = {
            "manifest_version": "v1.1",
            "namespace": self.namespace,
            "source_database": url.database,
            "application_version": APPLICATION_VERSION,
            "schema_version": health["schema_version"],
            "created_at": _iso(backup_time),
            "dump_file": dump_path.name,
            "dump_sha256": dump_digest,
            "object_counts": health["object_counts"],
            "brand_revision_digest": health["brand_revision_digest"],
            "schema_features": health["schema_features"],
            "health_digest": _health_digest(health),
            "database_snapshot": snapshot_after,
            "database_snapshot_digest": snapshot_after["snapshot_digest"],
            "release_bundle_manifest": Path(str(release["manifest_path"]))
            .relative_to(output_directory)
            .as_posix(),
            "release_bundle_manifest_sha256": release["manifest_sha256"],
            "release_bundle_digest": release["release_bundle_digest"],
            "release_object_count": release["object_count"],
            "materialization_digest": materialization["materialization_digest"],
            "materialization_document_sha256": materialization["document_sha256"],
            "materialization_document_count": materialization["document_count"],
            "materialization_as_of": _iso(backup_time),
            "contains_plaintext_secrets": False,
            "contains_credential_verifiers": True,
            "contains_sensitive_runtime_state": True,
            "requires_restricted_storage": True,
            "repository_commit_allowed": False,
            "contains_real_customer_data": False,
            "pg_dump_version": _tool_version("pg_dump"),
        }
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
            "health_digest": manifest["health_digest"],
            "database_snapshot_digest": manifest["database_snapshot_digest"],
            "release_bundle_digest": manifest["release_bundle_digest"],
            "release_object_count": manifest["release_object_count"],
            "materialization_digest": manifest["materialization_digest"],
            "materialization_document_sha256": manifest[
                "materialization_document_sha256"
            ],
            "materialization_document_count": manifest[
                "materialization_document_count"
            ],
        }

    @staticmethod
    def restore(*, target_database_url: str, manifest_path: Path) -> JsonObject:
        url = make_url(target_database_url)
        args, env = _database_args(url)
        target_database = str(url.database)
        manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest_raw, dict):
            raise ValueError("备份清单无效")
        manifest = dict(manifest_raw)
        if (
            manifest.get("manifest_version") != "v1.1"
            or not str(manifest.get("namespace", "")).startswith(TASK_PREFIX)
            or manifest.get("source_database") != manifest.get("namespace")
            or manifest.get("application_version") != APPLICATION_VERSION
            or manifest.get("schema_version") not in SUPPORTED_RESTORE_SCHEMA_VERSIONS
            or manifest.get("contains_plaintext_secrets") is not False
            or manifest.get("contains_credential_verifiers") is not True
            or manifest.get("contains_sensitive_runtime_state") is not True
            or manifest.get("requires_restricted_storage") is not True
            or manifest.get("repository_commit_allowed") is not False
            or manifest.get("contains_real_customer_data") is not False
            or not isinstance(manifest.get("release_bundle_manifest"), str)
            or not isinstance(manifest.get("release_bundle_manifest_sha256"), str)
            or not isinstance(manifest.get("release_bundle_digest"), str)
            or not isinstance(manifest.get("materialization_digest"), str)
            or not isinstance(manifest.get("materialization_document_sha256"), str)
            or not isinstance(manifest.get("materialization_as_of"), str)
        ):
            raise ValueError("备份归属或版本无效")
        if target_database == manifest.get("source_database"):
            raise ValueError("恢复必须使用新的隔离数据库")
        snapshot_raw = manifest.get("database_snapshot")
        if (
            not isinstance(manifest.get("object_counts"), dict)
            or not isinstance(manifest.get("health_digest"), str)
            or not isinstance(snapshot_raw, dict)
            or not isinstance(manifest.get("database_snapshot_digest"), str)
        ):
            raise ValueError("备份健康清单无效")
        expected_snapshot = dict(snapshot_raw)
        expected_snapshot_digest = expected_snapshot.pop("snapshot_digest", None)
        if (
            not isinstance(expected_snapshot_digest, str)
            or digest_object(expected_snapshot) != expected_snapshot_digest
            or manifest["database_snapshot_digest"] != expected_snapshot_digest
        ):
            raise ValueError("备份全库快照摘要无效")
        release_manifest, materialization_manifest = (
            HostedOperations._validate_release_bundle(
                backup_directory=manifest_path.parent,
                backup_manifest=manifest,
            )
        )
        if (
            manifest.get("release_object_count") != release_manifest.get("object_count")
            or manifest.get("materialization_digest")
            != materialization_manifest.get("materialization_digest")
            or manifest.get("materialization_document_sha256")
            != materialization_manifest.get("document_sha256")
            or manifest.get("materialization_document_count")
            != materialization_manifest.get("document_count")
            or manifest.get("materialization_as_of")
            != materialization_manifest.get("materialized_at")
        ):
            raise ValueError("备份与发布包绑定不一致")
        materialization_as_of = parse_time(str(manifest["materialization_as_of"]))
        dump_path = manifest_path.parent / str(manifest.get("dump_file"))
        if not dump_path.is_file():
            raise ValueError("备份文件缺失")
        digest = hashlib.sha256(dump_path.read_bytes()).hexdigest()
        if digest != manifest.get("dump_sha256"):
            raise ValueError("备份摘要不匹配")
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
        try:
            subprocess.run(
                [
                    "pg_restore",
                    *args,
                    "--single-transaction",
                    "--exit-on-error",
                    "--no-owner",
                    "--no-acl",
                    str(dump_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        except subprocess.CalledProcessError as exc:
            HostedOperations._clear_restored_database(target_database_url)
            raise ValueError("恢复执行失败且目标已清理") from exc

        target_engine = create_runtime_engine(target_database_url)
        try:
            target_sessions = create_session_factory(target_engine)
            source_namespace = str(manifest["namespace"])
            with target_sessions.begin() as session:
                state = session.get(HostedSchemaState, source_namespace)
                if state is None or state.application_version != APPLICATION_VERSION:
                    raise ValueError("恢复后的应用版本状态无效")
                if state.schema_version != manifest["schema_version"]:
                    raise ValueError("恢复后的结构版本不一致")
                state.namespace = target_database
                for audit in session.scalars(
                    select(HostedOperationAudit).where(
                        HostedOperationAudit.namespace == source_namespace
                    )
                ).all():
                    audit.namespace = target_database
            restored = HostedOperations(
                target_engine,
                target_sessions,
                target_database,
            )
            health = restored.health()
            restored_snapshot = _database_snapshot(
                target_engine,
                {source_namespace, target_database},
            )
            if (
                health["object_counts"] != manifest["object_counts"]
                or health["brand_revision_digest"] != manifest["brand_revision_digest"]
                or health["schema_features"] != manifest["schema_features"]
                or _health_digest(health) != manifest["health_digest"]
                or restored_snapshot != snapshot_raw
            ):
                raise ValueError("恢复后的对象健康状态不等价")
            with tempfile.TemporaryDirectory(prefix="diyu-pkg8-rematerialize-") as raw:
                regenerated = restored.materialize_dify(
                    output_directory=Path(raw),
                    as_of=materialization_as_of,
                )
                if (
                    regenerated["document_sha256"]
                    != manifest["materialization_document_sha256"]
                    or regenerated["materialization_digest"]
                    != manifest["materialization_digest"]
                    or regenerated["document_count"]
                    != manifest["materialization_document_count"]
                ):
                    raise ValueError("恢复后的 Dify 资料无法确定性重建")
        except Exception:
            target_engine.dispose()
            HostedOperations._clear_restored_database(target_database_url)
            raise
        finally:
            target_engine.dispose()
        return {
            "state": "RESTORED",
            "target_database": target_database,
            "dump_sha256": digest,
            "actual_object_counts": health["object_counts"],
            "actual_brand_revision_digest": health["brand_revision_digest"],
            "actual_health_digest": _health_digest(health),
            "actual_database_snapshot_digest": restored_snapshot["snapshot_digest"],
            "release_bundle_verified": True,
            "release_bundle_digest": release_manifest["release_bundle_digest"],
            "release_object_count": release_manifest["object_count"],
            "materialization_regenerated": True,
            "materialization_digest": manifest["materialization_digest"],
            "materialization_document_sha256": manifest[
                "materialization_document_sha256"
            ],
            "materialization_document_count": manifest[
                "materialization_document_count"
            ],
            "pg_restore_version": _tool_version("pg_restore"),
        }

    @staticmethod
    def _clear_restored_database(target_database_url: str) -> None:
        engine = create_runtime_engine(target_database_url)
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
                connection.exec_driver_sql("CREATE SCHEMA public")
            remaining = inspect(engine).get_table_names(schema="public")
            with engine.connect() as connection:
                remaining_objects = int(
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM pg_catalog.pg_class AS c "
                        "JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace "
                        "WHERE n.nspname = 'public' "
                        "AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')"
                    ).scalar_one()
                )
            if remaining or remaining_objects:
                raise RuntimeError("失败恢复的目标无法清空")
        finally:
            engine.dispose()

    def health(self) -> JsonObject:
        self._require_installed()
        database_snapshot = _database_snapshot(self.engine, {self.namespace})
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
            "schema_features": {
                "revision_lookup_index": self._revision_index_exists(self.engine),
            },
            "database_snapshot_digest": database_snapshot["snapshot_digest"],
            "database_table_count": len(database_snapshot["table_names"]),
            "plaintext_secrets_included": False,
            "credential_verifiers_included": True,
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

    @staticmethod
    def _delete_omitted_bundle_rows(
        session: Session,
        bundle: BrandImportBundle,
        tenant_id: str,
    ) -> int:
        """Apply full-bundle replacement semantics inside the import transaction."""

        identity = bundle.identity
        desired_organizations = {
            str(row["organization_id"]) for row in identity["organizations"]
        }
        desired_stores = {str(row["store_id"]) for row in identity["stores"]}
        desired_principals = {
            str(row["principal_id"]) for row in identity["login_principals"]
        }
        desired_accounts = {
            str(row["account_id"]) for row in identity["content_accounts"]
        }
        desired_authorizations = {
            str(row["authorization_id"]) for row in identity["authorization_grants"]
        }
        desired_confirmations = {
            str(row["subject_confirmation_id"])
            for row in identity["subject_confirmation_records"]
        }
        desired_fragments = {
            str(row["fragment_id"]) for row in bundle.narrative_fragments
        }
        desired_facts = {str(row["fact_id"]) for row in bundle.precise_facts}
        desired_sources = {
            str(row["source_id"])
            for row in (*bundle.narrative_fragments, *bundle.precise_facts)
        }

        current_organizations = set(
            session.scalars(
                select(RuntimeOrganization.organization_id).where(
                    RuntimeOrganization.tenant_id == tenant_id
                )
            ).all()
        )
        current_sources: set[str] = set()
        for material in session.scalars(
            select(RuntimeNarrativeFragment).where(
                RuntimeNarrativeFragment.tenant_id == tenant_id
            )
        ).all():
            source_id = material.payload.get("source_id")
            if isinstance(source_id, str):
                current_sources.add(source_id)
        for fact in session.scalars(
            select(RuntimePreciseFact).where(RuntimePreciseFact.tenant_id == tenant_id)
        ).all():
            source_id = fact.payload.get("source_id")
            if isinstance(source_id, str):
                current_sources.add(source_id)

        deleted_count = 0

        def delete_missing(
            model: type[Any],
            key_column: Any,
            current_ids: set[str],
            desired_ids: set[str],
        ) -> None:
            nonlocal deleted_count
            stale = current_ids - desired_ids
            if not stale:
                return
            result = session.execute(delete(model).where(key_column.in_(stale)))
            deleted_count += int(result.rowcount or 0)

        delete_missing(
            RuntimeStore,
            RuntimeStore.store_id,
            set(
                session.scalars(
                    select(RuntimeStore.store_id).where(
                        RuntimeStore.organization_id.in_(current_organizations)
                    )
                ).all()
            ),
            desired_stores,
        )
        scoped_models = (
            (
                RuntimePrincipal,
                RuntimePrincipal.principal_id,
                RuntimePrincipal.tenant_id,
                desired_principals,
            ),
            (
                RuntimeAccount,
                RuntimeAccount.account_id,
                RuntimeAccount.tenant_id,
                desired_accounts,
            ),
            (
                RuntimeAuthorization,
                RuntimeAuthorization.authorization_id,
                RuntimeAuthorization.tenant_id,
                desired_authorizations,
            ),
            (
                RuntimeSubjectConfirmation,
                RuntimeSubjectConfirmation.confirmation_id,
                RuntimeSubjectConfirmation.tenant_id,
                desired_confirmations,
            ),
            (
                RuntimeNarrativeFragment,
                RuntimeNarrativeFragment.fragment_id,
                RuntimeNarrativeFragment.tenant_id,
                desired_fragments,
            ),
            (
                RuntimePreciseFact,
                RuntimePreciseFact.fact_id,
                RuntimePreciseFact.tenant_id,
                desired_facts,
            ),
        )
        for model, key_column, tenant_column, desired_ids in scoped_models:
            delete_missing(
                model,
                key_column,
                set(
                    session.scalars(
                        select(key_column).where(tenant_column == tenant_id)
                    ).all()
                ),
                desired_ids,
            )
        delete_missing(
            RuntimeOrganization,
            RuntimeOrganization.organization_id,
            current_organizations,
            desired_organizations,
        )
        delete_missing(
            RuntimeSource,
            RuntimeSource.source_id,
            current_sources,
            desired_sources,
        )
        return deleted_count

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
        simulation_only = bundle.source_manifest.get("simulation_only") is True
        test_fixture_only = bundle.source_manifest.get("test_fixture_only") is True
        data_mode = str(bundle.source_manifest.get("data_mode"))
        now = utc_now()
        counts = {
            "created_or_updated": 0,
            "unchanged": 0,
            "deleted": self._delete_omitted_bundle_rows(
                session,
                bundle,
                tenant_id,
            ),
        }

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
                    "data_mode": data_mode,
                    "simulation_only": simulation_only,
                    "test_fixture_only": test_fixture_only,
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
                "data_mode": data_mode,
                "simulation_only": simulation_only,
                "test_fixture_only": test_fixture_only,
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
    if url.database != namespace:
        raise ValueError("目标命名空间与数据库名称不一致")
    free_bytes = shutil.disk_usage(PACKAGE_ROOT).free
    if free_bytes < minimum_free_bytes:
        raise ValueError("磁盘空间不足")
    if secret_file is not None:
        if not secret_file.is_file() or secret_file.is_symlink():
            raise ValueError("密钥文件必须是受限的普通文件")
        mode = secret_file.stat().st_mode & 0o777
        if mode & 0o077:
            raise ValueError("密钥文件权限过宽")
    required = {
        "package7_app": PACKAGE_7_ROOT / "dify_app.v1.yaml",
        "package7_bridge": PACKAGE_7_ROOT / "bridge_app.py",
        "package7_manifest": PACKAGE_7_ROOT / "dify_end_to_end_manifest.v1.json",
        "package8_manifest": PACKAGE_ROOT / "hosted_operations_manifest.v1.json",
        "materialization_manifest": PACKAGE_ROOT
        / "dify_materialization_manifest.v1.json",
    }
    missing = [label for label, path in required.items() if not path.is_file()]
    if missing:
        raise ValueError(f"前置对象缺失：{','.join(missing)}")
    hosted_manifest = json.loads(
        required["package8_manifest"].read_text(encoding="utf-8")
    )
    materialization = json.loads(
        required["materialization_manifest"].read_text(encoding="utf-8")
    )
    if (
        not isinstance(hosted_manifest, dict)
        or hosted_manifest.get("preconditions", {}).get("dify_community_version")
        != "1.15.0"
        or not isinstance(materialization, dict)
        or materialization.get("dify_platform_version") != "1.15.0"
    ):
        raise ValueError("Dify 前置版本未被清单精确锁定")
    for key in ("application_definition", "bridge", "package7_manifest"):
        item = materialization.get(key)
        if not isinstance(item, dict):
            raise ValueError("Dify 对象清单不完整")
        path = item.get("path")
        expected_digest = item.get("sha256")
        if not isinstance(path, str) or not isinstance(expected_digest, str):
            raise ValueError("Dify 对象清单字段无效")
        target = REPOSITORY_ROOT / path
        if (
            not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != expected_digest
        ):
            raise ValueError("Dify 前置对象摘要不匹配")
    pg_dump_version = _tool_version("pg_dump")
    pg_restore_version = _tool_version("pg_restore")
    engine = create_runtime_engine(database_url)
    try:
        with engine.connect() as connection:
            row = (
                connection.execute(
                    select(
                        func.current_database().label("database_name"),
                        func.current_setting("server_version_num").label(
                            "server_version_num"
                        ),
                        func.has_database_privilege(
                            func.current_database(), "CONNECT"
                        ).label("can_connect"),
                        func.has_database_privilege(
                            func.current_database(), "CREATE"
                        ).label("can_create"),
                    )
                )
                .mappings()
                .one()
            )
    except (OSError, SQLAlchemyError) as exc:
        raise ValueError("目标 PostgreSQL 不可连接或权限检查失败") from exc
    finally:
        engine.dispose()
    if (
        row["database_name"] != namespace
        or int(row["server_version_num"]) < 140000
        or row["can_connect"] is not True
        or row["can_create"] is not True
    ):
        raise ValueError("目标 PostgreSQL 版本、归属或权限不满足要求")
    return {
        "state": "CAN_PROCEED",
        "namespace": namespace,
        "database_name": url.database,
        "free_space_sufficient": True,
        "postgresql_server_version_num": int(row["server_version_num"]),
        "database_connect_privilege": True,
        "database_create_privilege": True,
        "pg_dump_version": pg_dump_version,
        "pg_restore_version": pg_restore_version,
        "dify_community_version": "1.15.0",
        "secret_file_checked": secret_file is not None,
        "required_object_digests": {
            label: hashlib.sha256(path.read_bytes()).hexdigest()
            for label, path in required.items()
        },
        "credentials_included": False,
    }
