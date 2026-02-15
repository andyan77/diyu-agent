"""Tests for audit artifact JSON schemas (R9 requirement).

Covers:
  - Schema files exist and are valid JSON
  - Required fields are declared in each schema
  - fix-verification schema enforces: id, criterion, scope, evidence, verdict
  - Validator script rejects invalid artifacts
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "scripts" / "schemas"

SCHEMAS = [
    "review-report.schema.json",
    "cross-audit-report.schema.json",
    "fix-verification-report.schema.json",
]


class TestSchemaFilesExist:
    """All three schema files must exist and be valid JSON."""

    @pytest.mark.parametrize("schema_name", SCHEMAS)
    def test_schema_file_exists(self, schema_name: str) -> None:
        path = SCHEMA_DIR / schema_name
        assert path.exists(), f"Schema file missing: {path}"

    @pytest.mark.parametrize("schema_name", SCHEMAS)
    def test_schema_is_valid_json(self, schema_name: str) -> None:
        path = SCHEMA_DIR / schema_name
        data = json.loads(path.read_text())
        assert isinstance(data, dict)
        assert "$schema" in data or "type" in data


class TestSchemaRequiredFields:
    """Each schema must declare required fields."""

    @pytest.mark.parametrize("schema_name", SCHEMAS)
    def test_has_required_array(self, schema_name: str) -> None:
        schema = json.loads((SCHEMA_DIR / schema_name).read_text())
        assert "required" in schema, f"{schema_name} has no top-level 'required'"
        assert len(schema["required"]) > 0, f"{schema_name} 'required' is empty"


class TestFixVerificationSchema:
    """fix-verification-report.schema.json must enforce per-finding fields."""

    @pytest.fixture()
    def schema(self) -> dict:
        return json.loads((SCHEMA_DIR / "fix-verification-report.schema.json").read_text())

    def test_finding_requires_id(self, schema: dict) -> None:
        finding_schema = schema["properties"]["findings"]["items"]
        assert "id" in finding_schema["required"]

    def test_finding_requires_criterion(self, schema: dict) -> None:
        finding_schema = schema["properties"]["findings"]["items"]
        assert "criterion" in finding_schema["required"]

    def test_finding_requires_scope(self, schema: dict) -> None:
        finding_schema = schema["properties"]["findings"]["items"]
        assert "scope" in finding_schema["required"]

    def test_finding_requires_evidence(self, schema: dict) -> None:
        finding_schema = schema["properties"]["findings"]["items"]
        assert "evidence" in finding_schema["required"]

    def test_finding_requires_verdict(self, schema: dict) -> None:
        finding_schema = schema["properties"]["findings"]["items"]
        assert "verdict" in finding_schema["required"]

    def test_verdict_enum_values(self, schema: dict) -> None:
        finding_schema = schema["properties"]["findings"]["items"]
        verdict_enum = finding_schema["properties"]["verdict"]["enum"]
        assert set(verdict_enum) == {"CLOSED", "OPEN", "PRE_RESOLVED"}

    def test_evidence_requires_command_and_output(self, schema: dict) -> None:
        finding_schema = schema["properties"]["findings"]["items"]
        evidence_schema = finding_schema["properties"]["evidence"]
        assert "command" in evidence_schema["required"]
        assert "output_summary" in evidence_schema["required"]


class TestSchemaValidation:
    """Schema must reject invalid data."""

    def test_review_rejects_missing_findings(self) -> None:
        schema = json.loads((SCHEMA_DIR / "review-report.schema.json").read_text())
        invalid = {"version": "1.0", "timestamp": "2026-01-01T00:00:00Z"}
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(invalid))
        assert len(errors) > 0, "Schema should reject data missing 'findings'"

    def test_fix_verification_rejects_missing_verdict(self) -> None:
        schema = json.loads((SCHEMA_DIR / "fix-verification-report.schema.json").read_text())
        invalid = {
            "version": "1.0",
            "timestamp": "2026-01-01T00:00:00Z",
            "source_review": "evidence/review-report.json",
            "findings": [
                {
                    "id": "H1",
                    "criterion": "test",
                    "scope": ["file.py"],
                    "evidence": {"command": "test", "output_summary": "ok"},
                    # verdict missing
                }
            ],
            "summary": {"total": 1, "closed": 0, "open": 1, "pre_resolved": 0},
        }
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(invalid))
        assert len(errors) > 0, "Schema should reject finding missing 'verdict'"

    def test_cross_audit_rejects_missing_summary(self) -> None:
        schema = json.loads((SCHEMA_DIR / "cross-audit-report.schema.json").read_text())
        invalid = {
            "version": "1.0",
            "timestamp": "2026-01-01T00:00:00Z",
            "pairs_checked": [],
            "mismatches": [],
            # summary missing
        }
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(invalid))
        assert len(errors) > 0, "Schema should reject data missing 'summary'"
