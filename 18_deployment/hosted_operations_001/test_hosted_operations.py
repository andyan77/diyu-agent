#!/usr/bin/env python3
"""Compact unit and real-PostgreSQL acceptance tests for Package 8."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from sqlalchemy import inspect, select
from sqlalchemy.engine import make_url


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_7_ROOT = REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001"
if str(PACKAGE_7_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_7_ROOT))

from contracts import BridgePrepareRequest  # type: ignore[import-not-found]  # noqa: E402
from persistence import (  # type: ignore[import-not-found]  # noqa: E402
    RuntimeRepository,
    SqlAlchemyPlanStore,
    create_runtime_engine,
    create_session_factory,
    digest_object,
)
from runtime_models import (  # type: ignore[import-not-found]  # noqa: E402
    RuntimeAccount,
    RuntimeAuthorization,
    RuntimeCandidate,
    RuntimeFeedback,
    RuntimeNarrativeFragment,
    RuntimeOrganization,
    RuntimePreciseFact,
    RuntimeSource,
)
from runtime_retrieval import (  # type: ignore[import-not-found]  # noqa: E402
    RuntimeBrandFactRetrievalService,
)
from runtime_service import Package7Runtime  # type: ignore[import-not-found]  # noqa: E402
from test_dify_end_to_end import (  # type: ignore[import-not-found]  # noqa: E402
    Package7Tests as _Package7Tests,
)

from brand_bundle import (  # noqa: E402
    BrandInputDocument,
    bundle_from_payload,
    bundle_to_payload,
    compile_brand_bundle,
    load_brand_input,
)
from hosted_models import HostedBrandRevision  # noqa: E402
from operations import HostedOperations, preflight_environment  # noqa: E402


JsonObject = dict[str, Any]
FIXTURE_PATH = PACKAGE_ROOT / "fixtures/second_brand_fixture.v1.yaml"
PASSWORD = "package8-local-acceptance-password"
PACKAGE7_CANDIDATE_FACTORY = _Package7Tests._candidate
del _Package7Tests


class LocalKnowledgeClient:
    """Deterministic local Dify materialization double over real runtime rows."""

    def __init__(self, sessions: Any) -> None:
        self.sessions = sessions
        self.requests: list[JsonObject] = []

    def retrieve(
        self,
        *,
        query: str,
        scope: JsonObject,
        query_at: str,
        limit: int,
    ) -> JsonObject:
        self.requests.append(
            {
                "query_digest": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "scope": copy.deepcopy(scope),
                "query_at": query_at,
                "limit": limit,
            }
        )
        with self.sessions() as session:
            rows = session.scalars(
                select(RuntimeNarrativeFragment).where(
                    RuntimeNarrativeFragment.tenant_id == scope["tenant_id"],
                    RuntimeNarrativeFragment.brand_id == scope["brand_id"],
                )
            ).all()
        results = []
        for row in rows:
            payload = row.payload
            if scope["content_account_id"] not in payload.get(
                "applicable_content_account_ids", []
            ):
                continue
            results.append(
                {
                    "metadata": {
                        "document_id": row.dify_document_id,
                        "score": 1.0,
                    },
                    "content": str(payload["text"])
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .strip(),
                    "title": "package8-local-material",
                }
            )
        return {
            "results": results[:limit],
            "usage": {},
            "prefilter_applied": True,
        }


def _request(message: str, display_name: str = "笛语童装") -> BridgePrepareRequest:
    return BridgePrepareRequest(
        session_token="x" * 64,
        account_display_name=display_name,
        operation="确认制作",
        topic_label="用户问题与理性选择",
        selected_content_product_id="CP06",
        primary_audience="内部测试用户",
        message=message,
        target_platform="内部图文测试",
    )


def _candidate_envelope(material_refs: list[str]) -> JsonObject:
    return {
        "kind": "CANDIDATE_SET",
        "reply": None,
        "candidates": [
            PACKAGE7_CANDIDATE_FACTORY(
                "物件路径",
                "先从眼前物件说明当前选择。",
                material_refs,
                ["核心创意", "画面组织方法"],
            ),
            PACKAGE7_CANDIDATE_FACTORY(
                "问题路径",
                "先问哪些条件值得继续核对。",
                material_refs,
                ["切入问题或场景", "叙事视角"],
            ),
        ],
    }


def _encoded_envelope(material_refs: list[str]) -> str:
    return base64.b64encode(
        json.dumps(
            _candidate_envelope(material_refs),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).decode("ascii")


class Package8UnitTests(unittest.TestCase):
    def test_brand_fixture_compiles_without_internal_user_inputs(self) -> None:
        document = load_brand_input(FIXTURE_PATH)
        bundle = compile_brand_bundle(document)
        from brand_import import preflight_brand_bundle

        preflight = preflight_brand_bundle(bundle)
        self.assertEqual(preflight["state"], "CAN_IMPORT")
        self.assertEqual(preflight["account_count"], 2)
        self.assertTrue(document.fictional_test_data)
        self.assertEqual(bundle.identity["tenant"]["tenant_id"], "TENANT-QINGHE-LAB")
        self.assertEqual(
            bundle.identity["tenant"]["brand_id"],
            "BRAND-QINGHE-LAB--QINGHE-HOME",
        )
        self.assertEqual(
            bundle.identity["content_accounts"][0]["display_name"], "笛语童装"
        )
        self.assertNotIn("route_migration", FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("component_id", FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_preflight_rejects_wrong_namespace_database_and_secret_mode(self) -> None:
        valid_url = "postgresql://test@127.0.0.1:1/diyu-pkg8-unit?connect_timeout=1"
        with self.assertRaisesRegex(ValueError, "目标命名空间"):
            preflight_environment(database_url=valid_url, namespace="shared")
        with self.assertRaisesRegex(ValueError, "数据库不属于"):
            preflight_environment(
                database_url="postgresql://test@localhost/shared",
                namespace="diyu-pkg8-unit",
            )
        with tempfile.TemporaryDirectory(prefix="diyu-pkg8-") as temporary:
            secret = Path(temporary) / "secret.env"
            secret.write_text("PLACEHOLDER_ONLY\n", encoding="utf-8")
            secret.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "权限过宽"):
                preflight_environment(
                    database_url=valid_url,
                    namespace="diyu-pkg8-unit",
                    secret_file=secret,
                )
        with self.assertRaisesRegex(ValueError, "不一致"):
            preflight_environment(
                database_url=valid_url,
                namespace="diyu-pkg8-other",
            )
        with self.assertRaisesRegex(ValueError, "不可连接"):
            preflight_environment(
                database_url=valid_url,
                namespace="diyu-pkg8-unit",
            )

    def test_codes_and_authorization_scope_are_closed_before_compile(self) -> None:
        document = load_brand_input(FIXTURE_PATH)
        payload = document.model_dump(mode="json")
        invalid_code = copy.deepcopy(payload)
        invalid_code["enterprise"]["enterprise_code"] = "alpha--corp"
        with self.assertRaisesRegex(ValueError, "canonical"):
            BrandInputDocument.model_validate(invalid_code)

        invalid_scope = copy.deepcopy(payload)
        invalid_scope["authorizations"][0]["account_codes"] = ["brand-account"]
        with self.assertRaisesRegex(ValueError, "outside authorization scope"):
            BrandInputDocument.model_validate(invalid_scope)

        ambiguous_first = copy.deepcopy(payload)
        ambiguous_first["enterprise"]["enterprise_code"] = "alpha-b"
        ambiguous_first["enterprise"]["brand_code"] = "cc"
        ambiguous_second = copy.deepcopy(payload)
        ambiguous_second["enterprise"]["enterprise_code"] = "alpha"
        ambiguous_second["enterprise"]["brand_code"] = "b-cc"
        first = compile_brand_bundle(BrandInputDocument.model_validate(ambiguous_first))
        second = compile_brand_bundle(
            BrandInputDocument.model_validate(ambiguous_second)
        )
        self.assertNotEqual(
            first.identity["tenant"]["brand_id"],
            second.identity["tenant"]["brand_id"],
        )


@unittest.skipUnless(
    os.environ.get("DIYU_PKG8_ADMIN_DATABASE_URL"),
    "real PostgreSQL acceptance needs DIYU_PKG8_ADMIN_DATABASE_URL",
)
class Package8PostgresAcceptance(unittest.TestCase):
    def test_full_hosted_operations_lifecycle(self) -> None:
        admin_url_text = os.environ["DIYU_PKG8_ADMIN_DATABASE_URL"]
        admin_url = make_url(admin_url_text)
        suffix = hashlib.sha256(
            f"{os.getpid()}:{threading.get_ident()}".encode("utf-8")
        ).hexdigest()[:8]
        source_name = f"diyu-pkg8-acceptance-{suffix}"
        restore_name = f"diyu-pkg8-restore-{suffix}"
        corrupt_name = f"diyu-pkg8-corrupt-{suffix}"
        names = (source_name, restore_name, corrupt_name)
        self._recreate_databases(admin_url, names)
        source_url = str(admin_url.set(database=source_name))
        restore_url = str(admin_url.set(database=restore_name))
        corrupt_url = str(admin_url.set(database=corrupt_name))
        report: JsonObject = {
            "database_kind": "POSTGRESQL",
            "database_names": list(names),
            "external_model_calls": 0,
            "real_cloud_mutations": 0,
        }
        temporary = tempfile.mkdtemp(prefix="diyu-pkg8-acceptance-")
        source_engine = create_runtime_engine(source_url)
        try:
            sessions = create_session_factory(source_engine)
            operations = HostedOperations(source_engine, sessions, source_name)
            report["preflight"] = preflight_environment(
                database_url=source_url,
                namespace=source_name,
            )
            first_install = operations.install()
            second_install = operations.install()
            self.assertEqual(first_install["state"], "INSTALLED")
            self.assertEqual(second_install["state"], "UNCHANGED")
            first_init = operations.initialize_simulation(
                username=f"pkg8-first-{suffix}",
                password=PASSWORD,
            )
            second_init = operations.initialize_simulation(
                username=f"pkg8-first-{suffix}",
                password=PASSWORD,
            )
            self.assertEqual(second_init["seed"]["created_or_updated"], 0)
            bundle = compile_brand_bundle(load_brand_input(FIXTURE_PATH))
            imported = operations.import_brand(bundle, principal_password=PASSWORD)
            repeated = operations.import_brand(bundle, principal_password=PASSWORD)
            self.assertEqual(imported["state"], "APPLIED")
            self.assertEqual(repeated["state"], "UNCHANGED")
            self._assert_same_label_is_scoped(sessions)
            first_brand_fact_digest = self._first_brand_fact_digest(sessions)
            updated_payload = bundle_to_payload(bundle)
            updated_payload["precise_facts"][0]["value"]["product_name"] = (
                "青禾实验收纳篮修订版"
            )
            updated_value_digest = digest_object(
                updated_payload["precise_facts"][0]["value"]
            )
            updated_payload["precise_facts"][0]["source_sha256"] = updated_value_digest
            updated_payload["precise_facts"][0]["source_excerpt_sha256"] = (
                updated_value_digest
            )
            transient_material = copy.deepcopy(
                updated_payload["narrative_fragments"][0]
            )
            transient_material.update(
                {
                    "fragment_id": "FRAGMENT-QINGHE-LAB--TRANSIENT",
                    "unit_id": "transient",
                    "source_id": "SOURCE-QINGHE-LAB--MATERIAL--TRANSIENT",
                    "source_ref": "fixture://SOURCE-QINGHE-LAB--MATERIAL--TRANSIENT",
                    "title": "稍后应被完整替换移除的资料",
                    "text": "这是一条只用于验证完整替换语义的虚构临时资料。",
                }
            )
            transient_digest = hashlib.sha256(
                transient_material["text"].encode("utf-8")
            ).hexdigest()
            transient_material["source_sha256"] = transient_digest
            transient_material["fragment_sha256"] = transient_digest
            updated_payload["narrative_fragments"].append(transient_material)
            later_only_fact = copy.deepcopy(updated_payload["precise_facts"][0])
            later_only_fact.update(
                {
                    "fact_id": "FACT-QINGHE-LAB--LATER-ONLY",
                    "source_id": "SOURCE-QINGHE-LAB--FACT--LATER-ONLY",
                    "source_ref": "fixture://SOURCE-QINGHE-LAB--FACT--LATER-ONLY",
                    "label": "稍后应由整包回滚移除的字段",
                    "value": {"test_marker": "later-only"},
                }
            )
            later_only_digest = digest_object(later_only_fact["value"])
            later_only_fact["source_sha256"] = later_only_digest
            later_only_fact["source_excerpt_sha256"] = later_only_digest
            updated_payload["precise_facts"].append(later_only_fact)
            updated = bundle_from_payload(updated_payload)
            concurrent_results: list[JsonObject] = []
            concurrent_errors: list[str] = []

            def concurrent_import() -> None:
                engine = create_runtime_engine(source_url)
                try:
                    worker = HostedOperations(
                        engine,
                        create_session_factory(engine),
                        source_name,
                    )
                    concurrent_results.append(
                        worker.import_brand(
                            updated,
                            principal_password=PASSWORD,
                            reason="UPDATE",
                        )
                    )
                except Exception as exc:  # pragma: no cover - asserted below
                    concurrent_errors.append(type(exc).__name__)
                finally:
                    engine.dispose()

            workers = [threading.Thread(target=concurrent_import) for _ in range(2)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=30)
            self.assertFalse(concurrent_errors)
            self.assertEqual(
                sorted(result["state"] for result in concurrent_results),
                ["APPLIED", "UNCHANGED"],
            )
            self.assertEqual(
                first_brand_fact_digest,
                self._first_brand_fact_digest(sessions),
            )
            contracted_payload = bundle_to_payload(updated)
            contracted_payload["narrative_fragments"] = [
                row
                for row in contracted_payload["narrative_fragments"]
                if row["fragment_id"] != "FRAGMENT-QINGHE-LAB--TRANSIENT"
            ]
            contracted = bundle_from_payload(contracted_payload)
            contracted_result = operations.import_brand(
                contracted,
                principal_password=PASSWORD,
                reason="UPDATE",
            )
            self.assertEqual(contracted_result["state"], "APPLIED")
            self.assertGreaterEqual(contracted_result["deleted"], 2)
            with sessions() as session:
                self.assertIsNone(
                    session.get(
                        RuntimeNarrativeFragment,
                        "FRAGMENT-QINGHE-LAB--TRANSIENT",
                    )
                )
                self.assertIsNone(
                    session.get(
                        RuntimeSource,
                        "SOURCE-QINGHE-LAB--MATERIAL--TRANSIENT",
                    )
                )
            revisions_before_failure = self._revision_count(sessions)
            organization_before = self._organization_name(
                sessions, "ORG-QINGHE-LAB--HQ"
            )
            failure_payload = bundle_to_payload(updated)
            failure_payload["identity"]["organizations"][0]["display_name"] = (
                "不应提交的半套资料"
            )
            with self.assertRaisesRegex(RuntimeError, "intentional"):
                operations.import_brand(
                    bundle_from_payload(failure_payload),
                    principal_password=PASSWORD,
                    reason="UPDATE",
                    fail_after_stage="identity",
                )
            self.assertEqual(revisions_before_failure, self._revision_count(sessions))
            self.assertEqual(
                organization_before,
                self._organization_name(sessions, "ORG-QINGHE-LAB--HQ"),
            )
            runtime_report = self._exercise_both_brands(sessions)
            report["runtime"] = runtime_report
            second_principal = "PRINCIPAL-QINGHE-LAB--ACCEPTANCE-OWNER"
            second_account = "ACCOUNT-QINGHE-LAB--BRAND-ACCOUNT"
            runtime, knowledge = self._runtime(sessions)
            prepared_before_revoke = runtime.prepare(
                _request("整理物品时先保留日常会反复使用的部分"),
                second_principal,
            )
            self.assertEqual(prepared_before_revoke["response_kind"], "MODEL_REQUIRED")
            material_refs = prepared_before_revoke["author_prompt"]["author_materials"][
                "retrieval_fragment_refs"
            ][:1]
            operations.revoke(
                tenant_id="TENANT-QINGHE-LAB",
                object_kind="authorization",
                object_id="AUTH-QINGHE-LAB--CURRENT-MATERIAL",
                reason_ref="revoke://package8-acceptance",
            )
            for operation_name in ("审核", "导出", "查看来源"):
                stale_operation = runtime.prepare(
                    _request("当前候选必须重新核对").model_copy(
                        update={"operation": operation_name}
                    ),
                    second_principal,
                )
                self.assertTrue(stale_operation.get("action_card"))
                self.assertNotIn("当前范围可用", stale_operation["user_visible_text"])
            rejected = runtime.finalize_model_output(
                prepared_before_revoke["run_id"],
                _encoded_envelope(material_refs),
            )
            self.assertEqual(rejected["response_kind"], "DIRECT")
            self.assertIn("暂时停止", rejected["user_visible_text"])
            with sessions() as session:
                stale_candidates = session.scalars(
                    select(RuntimeCandidate).where(
                        RuntimeCandidate.run_id == prepared_before_revoke["run_id"]
                    )
                ).all()
            self.assertFalse(stale_candidates)
            after_revoke = runtime.prepare(
                _request("整理物品时先保留日常会反复使用的部分"),
                second_principal,
            )
            self.assertEqual(after_revoke["response_kind"], "DIRECT")
            self.assertFalse(
                any(
                    request["scope"]["tenant_id"] == "TENANT-DIYU-SIM-001"
                    for request in knowledge.requests[-1:]
                )
            )
            rolled_back = operations.rollback_brand(
                tenant_id="TENANT-QINGHE-LAB",
                target_revision=1,
                principal_password=PASSWORD,
            )
            self.assertEqual(rolled_back["state"], "APPLIED")
            with sessions() as session:
                self.assertIsNone(
                    session.get(RuntimePreciseFact, "FACT-QINGHE-LAB--LATER-ONLY")
                )
                self.assertIsNone(
                    session.get(
                        RuntimeSource,
                        "SOURCE-QINGHE-LAB--FACT--LATER-ONLY",
                    )
                )
            restored_prepare = runtime.prepare(
                _request("整理物品时先保留日常会反复使用的部分"),
                second_principal,
            )
            self.assertEqual(restored_prepare["response_kind"], "MODEL_REQUIRED")
            self.assertEqual(
                runtime.repository.model_run(restored_prepare["run_id"]).account_id,
                second_account,
            )
            with self.assertRaisesRegex(RuntimeError, "intentional"):
                operations.upgrade(target_version=2, fail_after_write=True)
            self.assertEqual(operations.health()["schema_version"], 1)
            self.assertFalse(self._has_revision_index(source_engine))
            self.assertEqual(operations.upgrade(target_version=2)["schema_version"], 2)
            self.assertTrue(self._has_revision_index(source_engine))
            self.assertEqual(operations.rollback_schema()["schema_version"], 1)
            self.assertFalse(self._has_revision_index(source_engine))
            before_backup = operations.health()
            state_before_backup = self._runtime_state(sessions)
            backup = operations.backup(
                database_url=source_url,
                output_directory=Path(temporary) / "backup",
            )
            manifest_path = Path(backup["manifest_path"])
            restore = HostedOperations.restore(
                target_database_url=restore_url,
                manifest_path=manifest_path,
            )
            self.assertEqual(restore["state"], "RESTORED")
            restore_engine = create_runtime_engine(restore_url)
            try:
                restore_sessions = create_session_factory(restore_engine)
                restored_operations = HostedOperations(
                    restore_engine,
                    restore_sessions,
                    restore_name,
                )
                after_restore = restored_operations.health()
                self.assertEqual(
                    before_backup["object_counts"], after_restore["object_counts"]
                )
                self.assertEqual(
                    before_backup["brand_revision_digest"],
                    after_restore["brand_revision_digest"],
                )
                self.assertEqual(
                    state_before_backup,
                    self._runtime_state(restore_sessions),
                )
                self._assert_same_label_is_scoped(restore_sessions)
            finally:
                restore_engine.dispose()
            incompatible_manifest = Path(temporary) / "backup" / "incompatible.json"
            incompatible_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            incompatible_payload["application_version"] = "package8-incompatible"
            incompatible_manifest.write_text(
                json.dumps(incompatible_payload, sort_keys=True),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "归属或版本"):
                HostedOperations.restore(
                    target_database_url=corrupt_url,
                    manifest_path=incompatible_manifest,
                )
            corrupt_directory = Path(temporary) / "corrupt"
            shutil.copytree(manifest_path.parent, corrupt_directory)
            corrupt_dump = corrupt_directory / "runtime.pgdump"
            corrupt_dump.write_bytes(b"not-a-postgresql-custom-archive")
            with self.assertRaisesRegex(ValueError, "摘要不匹配"):
                HostedOperations.restore(
                    target_database_url=corrupt_url,
                    manifest_path=corrupt_directory / "backup_manifest.v1.json",
                )
            corrupt_manifest = json.loads(
                (corrupt_directory / "backup_manifest.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            corrupt_manifest["dump_sha256"] = hashlib.sha256(
                corrupt_dump.read_bytes()
            ).hexdigest()
            (corrupt_directory / "backup_manifest.v1.json").write_text(
                json.dumps(corrupt_manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "恢复执行失败"):
                HostedOperations.restore(
                    target_database_url=corrupt_url,
                    manifest_path=corrupt_directory / "backup_manifest.v1.json",
                )
            corrupt_engine = create_runtime_engine(corrupt_url)
            try:
                self.assertEqual(inspect(corrupt_engine).get_table_names(), [])
            finally:
                corrupt_engine.dispose()
            report.update(
                {
                    "install_idempotent": True,
                    "brand_import_idempotent": True,
                    "concurrent_import_serialized": True,
                    "failed_import_rolled_back": True,
                    "same_display_name_scope_safe": True,
                    "bidirectional_brand_isolation": True,
                    "revocation_immediate": True,
                    "stale_candidate_rejected": True,
                    "bundle_rollback_restored": True,
                    "bundle_omission_removed": True,
                    "failed_upgrade_rolled_back": True,
                    "schema_upgrade_changed_structure": True,
                    "successful_upgrade_and_rollback": True,
                    "fresh_namespace_restore_equal": True,
                    "corrupt_backup_rejected": True,
                    "incompatible_backup_rejected": True,
                    "failed_restore_left_target_empty": True,
                    "selected_candidate_rechecked_after_revocation": True,
                    "source_health": before_backup,
                    "backup_dump_sha256": backup["dump_sha256"],
                    "first_initialization_state": first_init["state"],
                }
            )
            report["acceptance_digest"] = digest_object(report)
            report_path = os.environ.get("DIYU_PKG8_ACCEPTANCE_REPORT")
            if report_path:
                Path(report_path).write_text(
                    json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n",
                    encoding="utf-8",
                )
        finally:
            source_engine.dispose()
            shutil.rmtree(temporary, ignore_errors=True)
            self._drop_databases(admin_url, names)

    @staticmethod
    def _connection_string(url: Any) -> str:
        return url.set(drivername="postgresql").render_as_string(hide_password=False)

    @classmethod
    def _recreate_databases(cls, admin_url: Any, names: tuple[str, ...]) -> None:
        cls._drop_databases(admin_url, names)
        with psycopg.connect(
            cls._connection_string(admin_url), autocommit=True
        ) as connection:
            for name in names:
                if not name.startswith("diyu-pkg8-"):
                    raise ValueError("test database ownership is invalid")
                connection.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name))
                )

    @classmethod
    def _drop_databases(cls, admin_url: Any, names: tuple[str, ...]) -> None:
        with psycopg.connect(
            cls._connection_string(admin_url), autocommit=True
        ) as connection:
            for name in names:
                if not name.startswith("diyu-pkg8-"):
                    raise ValueError("test database ownership is invalid")
                connection.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (name,),
                )
                connection.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name))
                )

    @staticmethod
    def _assert_same_label_is_scoped(sessions: Any) -> None:
        with sessions() as session:
            rows = session.scalars(
                select(RuntimeAccount).where(RuntimeAccount.display_name == "笛语童装")
            ).all()
        if len(rows) != 2 or len({row.tenant_id for row in rows}) != 2:
            raise AssertionError("same-label account scope was not isolated")

    @staticmethod
    def _first_brand_fact_digest(sessions: Any) -> str:
        with sessions() as session:
            rows = session.scalars(
                select(RuntimePreciseFact).where(
                    RuntimePreciseFact.tenant_id == "TENANT-DIYU-SIM-001"
                )
            ).all()
        return digest_object(sorted((row.fact_id, row.payload) for row in rows))

    @staticmethod
    def _revision_count(sessions: Any) -> int:
        with sessions() as session:
            return len(session.scalars(select(HostedBrandRevision)).all())

    @staticmethod
    def _organization_name(sessions: Any, organization_id: str) -> str:
        with sessions() as session:
            row = session.get(RuntimeOrganization, organization_id)
            if row is None:
                raise AssertionError(organization_id)
            return row.display_name

    @staticmethod
    def _has_revision_index(engine: Any) -> bool:
        return any(
            row.get("name") == "ix_hosted_brand_revision_tenant_digest"
            for row in inspect(engine).get_indexes("hosted_brand_revisions")
        )

    @staticmethod
    def _runtime(sessions: Any) -> tuple[Package7Runtime, LocalKnowledgeClient]:
        repository = RuntimeRepository(sessions)
        knowledge = LocalKnowledgeClient(sessions)
        retrieval = RuntimeBrandFactRetrievalService(repository, knowledge)
        return (
            Package7Runtime(repository, SqlAlchemyPlanStore(sessions), retrieval),
            knowledge,
        )

    def _exercise_both_brands(self, sessions: Any) -> JsonObject:
        runtime, knowledge = self._runtime(sessions)
        cases = (
            (
                "SIM-LOGIN-DIYU-ACCEPTANCE-001",
                "尺码不能只看身高",
                "ACCOUNT-DIYU-HQ-OFFICIAL",
                "TENANT-DIYU-SIM-001",
            ),
            (
                "PRINCIPAL-QINGHE-LAB--ACCEPTANCE-OWNER",
                "整理物品时先保留日常会反复使用的部分",
                "ACCOUNT-QINGHE-LAB--BRAND-ACCOUNT",
                "TENANT-QINGHE-LAB",
            ),
        )
        run_accounts: list[str] = []
        for principal, message, account_id, tenant_id in cases:
            prepared = runtime.prepare(_request(message), principal)
            self.assertEqual(prepared["response_kind"], "MODEL_REQUIRED")
            run = runtime.repository.model_run(prepared["run_id"])
            self.assertIsNotNone(run)
            self.assertEqual(run.account_id if run else None, account_id)
            refs = prepared["author_prompt"]["author_materials"][
                "retrieval_fragment_refs"
            ][:1]
            self.assertTrue(refs)
            runtime.finalize_model_output(
                prepared["run_id"],
                _encoded_envelope(refs),
            )
            runtime.prepare(
                _request(message).model_copy(
                    update={"operation": "选择候选", "candidate_number": 1}
                ),
                principal,
            )
            feedback = runtime.prepare(
                _request(message).model_copy(
                    update={
                        "operation": "提交反馈",
                        "topic_label": None,
                        "selected_content_product_id": None,
                        "primary_audience": None,
                        "message": "当前切入可继续内部核对。",
                    }
                ),
                principal,
            )
            self.assertIn("反馈已记录", feedback["user_visible_text"])
            self.assertEqual(knowledge.requests[-1]["scope"]["tenant_id"], tenant_id)
            run_accounts.append(account_id)
        denied_left = runtime.prepare(
            _request("不能跨企业", "青禾门店记录"),
            "SIM-LOGIN-DIYU-ACCEPTANCE-001",
        )
        denied_right = runtime.prepare(
            _request("不能跨企业", "林知远｜笛语"),
            "PRINCIPAL-QINGHE-LAB--ACCEPTANCE-OWNER",
        )
        self.assertEqual(denied_left["response_kind"], "DIRECT")
        self.assertEqual(denied_right["response_kind"], "DIRECT")
        return {
            "prepared_and_validated_brand_count": 2,
            "feedback_brand_count": 2,
            "run_account_ids": run_accounts,
            "cross_tenant_attacks_rejected": 2,
            "retrieval_request_count": len(knowledge.requests),
        }

    @staticmethod
    def _runtime_state(sessions: Any) -> JsonObject:
        with sessions() as session:
            candidates = session.scalars(
                select(RuntimeCandidate).order_by(RuntimeCandidate.candidate_id)
            ).all()
            feedback = session.scalars(
                select(RuntimeFeedback).order_by(RuntimeFeedback.feedback_id)
            ).all()
            authorizations = session.scalars(
                select(RuntimeAuthorization).order_by(
                    RuntimeAuthorization.authorization_id
                )
            ).all()
        return {
            "candidates": [
                [row.candidate_id, row.account_id, row.selected] for row in candidates
            ],
            "feedback": [
                [row.feedback_id, row.account_id, row.review_state] for row in feedback
            ],
            "authorizations": [
                [row.authorization_id, row.tenant_id, row.status]
                for row in authorizations
            ],
        }


if __name__ == "__main__":
    unittest.main()
