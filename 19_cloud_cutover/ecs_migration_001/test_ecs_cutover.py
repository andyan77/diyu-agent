#!/usr/bin/env python3
"""Compact deterministic tests for the Package 9 cutover boundary."""

from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_7_ROOT = REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001"
for path in (PACKAGE_ROOT, PACKAGE_7_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from database_security import (  # noqa: E402
    DATABASE_NAME,
    LEGACY_ROLE,
    MIGRATION_ONLY_TABLES,
    MIGRATION_ROLE,
    RUNTIME_ROLE,
    TABLE_POLICIES,
    render_rollback_sql,
    render_security_sql,
)
from ecs_cutover import (  # noqa: E402
    render_nginx,
    verify_encrypted_backup_manifest,
    verify_repository_has_no_secret_surface,
    verify_transition_record,
)
from persistence import TrustedDatabaseScope, trusted_database_scope  # noqa: E402


class Package9Tests(unittest.TestCase):
    def test_rls_migration_is_forced_and_runtime_cannot_bypass(self) -> None:
        migration = render_security_sql()
        self.assertEqual(
            migration.count("ENABLE ROW LEVEL SECURITY"),
            len(TABLE_POLICIES),
        )
        self.assertEqual(
            migration.count("FORCE ROW LEVEL SECURITY"),
            len(TABLE_POLICIES),
        )
        self.assertIn(f"ALTER DATABASE {DATABASE_NAME} OWNER TO {MIGRATION_ROLE}", migration)
        self.assertIn(f"ALTER ROLE {RUNTIME_ROLE} NOSUPERUSER", migration)
        self.assertIn("NOBYPASSRLS", migration)
        self.assertIn(f"ALTER ROLE {MIGRATION_ROLE} NOSUPERUSER", migration)
        self.assertIn("BYPASSRLS", migration)
        self.assertIn(f"ALTER ROLE {LEGACY_ROLE} NOLOGIN", migration)
        for table in TABLE_POLICIES:
            self.assertIn(f"CREATE POLICY diyu_pkg9_scope ON {table}", migration)
        for table in MIGRATION_ONLY_TABLES:
            self.assertIn(table, migration)
        self.assertIn("hosted_operation_audit", MIGRATION_ONLY_TABLES)
        self.assertNotIn("hosted_operation_audits", migration)

    def test_rls_policy_dimensions_and_rollback_are_closed(self) -> None:
        combined = "\n".join(TABLE_POLICIES.values())
        for dimension in (
            "app.tenant_id",
            "app.brand_id",
            "app.organization_id",
            "app.store_id",
            "app.account_id",
            "app.principal_id",
        ):
            self.assertIn(dimension, combined)
        self.assertIn("setting_principal.allowed_account_ids", combined)
        self.assertIn("brand_expression_profile:", combined)
        rollback = render_rollback_sql()
        self.assertEqual(
            rollback.count("DISABLE ROW LEVEL SECURITY"),
            len(TABLE_POLICIES),
        )
        self.assertIn(f"ALTER ROLE {RUNTIME_ROLE} NOLOGIN", rollback)

    def test_invalid_postgresql_identifier_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "identifier"):
            render_security_sql(runtime_role="runtime; DROP DATABASE unsafe")

    def test_trusted_database_scope_is_server_constructed_and_nested(self) -> None:
        outer = TrustedDatabaseScope(
            tenant_id="TENANT-DIYU-SIM-001",
            principal_id="SIM-LOGIN-DIYU-ACCEPTANCE-001",
        )
        inner = TrustedDatabaseScope(
            tenant_id=outer.tenant_id,
            brand_id="BRAND-DIYU-SIM-001",
            account_id="ACCOUNT-DIYU-FOUNDER",
            principal_id=outer.principal_id,
        )
        with trusted_database_scope(outer):
            with trusted_database_scope(inner):
                self.assertEqual(inner.account_id, "ACCOUNT-DIYU-FOUNDER")
        with self.assertRaisesRegex(ValueError, "tenant"):
            with trusted_database_scope(TrustedDatabaseScope(tenant_id="")):
                pass

    def test_nginx_apps_route_is_single_loopback_proxy(self) -> None:
        template = PACKAGE_ROOT / "nginx_apps.conf.template"
        text = template.read_text(encoding="utf-8")
        self.assertEqual(text.count("location = /apps"), 1)
        self.assertEqual(text.count("location ^~ /apps/"), 1)
        self.assertEqual(text.count("proxy_pass http://127.0.0.1:18471/"), 1)
        self.assertNotIn("0.0.0.0:18471", text)
        with tempfile.TemporaryFile(mode="w+") as output:
            original = sys.stdout
            try:
                sys.stdout = output
                result = render_nginx(template)
            finally:
                sys.stdout = original
        self.assertEqual(result["state"], "NGINX_TEMPLATE_RENDERED")

    def test_portal_uses_apps_aware_relative_assets_and_endpoints(self) -> None:
        html = (PACKAGE_7_ROOT / "portal.html").read_text(encoding="utf-8")
        javascript = (PACKAGE_7_ROOT / "portal.js").read_text(encoding="utf-8")
        self.assertIn('href="portal.css"', html)
        self.assertIn('src="portal.js"', html)
        self.assertIn('startsWith("/apps")', javascript)
        for route in ("/login", "/logout", "/v1/portal/chat"):
            self.assertIn(f'endpoint("{route}")', javascript)

    def test_external_backup_manifest_requires_encryption_and_verification(self) -> None:
        artifact_bytes = b"encrypted-test-artifact"
        document = {
            "task_id": "DIYU_ECS_CUTOVER_001",
            "location_class": "SERVER_EXTERNAL_RESTRICTED_LOCAL_STORAGE",
            "key_location_class": "SEPARATE_SERVER_EXTERNAL_RESTRICTED_KEY_STORE",
            "encryption": "GPG_SYMMETRIC_AES256",
            "plaintext_artifacts_persisted": False,
            "artifact_count": 1,
            "artifacts": [
                {
                    "artifact": "database.pgdump.gpg",
                    "encrypted_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
                    "encrypted_size_bytes": len(artifact_bytes),
                    "decryption_verified": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "manifest.json"
            artifact = Path(raw) / "database.pgdump.gpg"
            artifact.write_bytes(artifact_bytes)
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assertEqual(
                verify_encrypted_backup_manifest(path)["state"],
                "BACKUP_MANIFEST_VERIFIED",
            )
            document["artifacts"][0]["decryption_verified"] = False
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                verify_encrypted_backup_manifest(path)
            document["artifacts"][0]["decryption_verified"] = True
            path.write_text(json.dumps(document), encoding="utf-8")
            artifact.unlink()
            with self.assertRaisesRegex(ValueError, "missing or corrupt"):
                verify_encrypted_backup_manifest(path)

    def test_package_files_contain_no_secret_like_surface(self) -> None:
        result = verify_repository_has_no_secret_surface()
        self.assertEqual(result["state"], "SECRET_SURFACE_CLEAR")

    def test_actual_rollback_and_forward_record_is_action_closed(self) -> None:
        source = PACKAGE_ROOT / "evidence/remote_cutover_evidence.v1.json"
        result = verify_transition_record(source)
        self.assertEqual(result["state"], "CUTOVER_TRANSITION_RECORD_VERIFIED")
        document = json.loads(source.read_text(encoding="utf-8"))
        document["transition_record"]["forward_phase"]["actions"][1]["status"] = "SKIPPED"
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "transition.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "actions are incomplete"):
                verify_transition_record(path)


if __name__ == "__main__":
    unittest.main()
