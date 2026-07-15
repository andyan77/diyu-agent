#!/usr/bin/env python3
"""Fail-closed checker for the Package 5 brand-fact retrieval slice."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml  # type: ignore[import-untyped]

import materialize_retrieval as materialize
from brand_fact_retrieval import (
    BrandFactRetrievalService,
    IdentityAuthority,
    RetrievalContractError,
    RetrievalIndex,
    canonical_json_bytes,
    digest_object,
)


if not __debug__:
    sys.stderr.write("check_brand_fact_retrieval refuses python -O\n")
    raise SystemExit(2)


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_RELATIVE_ROOT = Path("15_brand_retrieval/brand_fact_retrieval_001")
RESULT_PATH = PACKAGE_ROOT / "result/brand_fact_retrieval_result.v1.json"
REVIEW_PATHS = (
    PACKAGE_ROOT / "review/architecture_consumability_review.v1.yaml",
    PACKAGE_ROOT / "review/fact_authorization_isolation_review.v1.yaml",
)
IMMUTABLE_SNAPSHOT_PATHS = (
    PACKAGE_RELATIVE_ROOT / "brand_fact_retrieval.py",
    PACKAGE_RELATIVE_ROOT / "materialize_retrieval.py",
    PACKAGE_RELATIVE_ROOT / "check_brand_fact_retrieval.py",
    PACKAGE_RELATIVE_ROOT / "retrieval_manifest.v1.json",
    PACKAGE_RELATIVE_ROOT / "data/retrieval_fragments.v1.jsonl",
    PACKAGE_RELATIVE_ROOT / "data/verified_precise_facts.v1.jsonl",
    PACKAGE_RELATIVE_ROOT / "data/source_dispositions.v1.jsonl",
    PACKAGE_RELATIVE_ROOT / "data/expression_candidates.v1.json",
    PACKAGE_RELATIVE_ROOT / "fixtures/retrieval_cases.v1.jsonl",
    Path("ci/checkers/check_product_foundation.py"),
    Path("ci/checkers/check_gate1_v1_1_current.py"),
    Path(".github/workflows/ci.yml"),
)
BASE_PACKAGE_FILES = frozenset(
    {
        Path("brand_fact_retrieval.py"),
        Path("materialize_retrieval.py"),
        Path("check_brand_fact_retrieval.py"),
        Path("retrieval_manifest.v1.json"),
        Path("data/retrieval_fragments.v1.jsonl"),
        Path("data/verified_precise_facts.v1.jsonl"),
        Path("data/source_dispositions.v1.jsonl"),
        Path("data/expression_candidates.v1.json"),
        Path("fixtures/retrieval_cases.v1.jsonl"),
        Path("result/brand_fact_retrieval_result.v1.json"),
    }
)
REVIEW_PACKAGE_FILES = frozenset(
    {
        Path("review/architecture_consumability_review.v1.yaml"),
        Path("review/fact_authorization_isolation_review.v1.yaml"),
    }
)
REQUIRED_FALSE_FLAGS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "database_imported",
        "generation_eligible",
        "generation_allowed",
        "production_ready",
        "production_servable",
        "release_ready",
        "retrieval_ready",
    }
)
EXPECTED_REVIEW_TYPES = frozenset(
    {"ARCHITECTURE_AND_DOWNSTREAM_CONSUMABILITY", "FACT_AUTHORIZATION_PRIVACY_ISOLATION"}
)
BANNED_RUNTIME_IMPORTS = frozenset(
    {"requests", "httpx", "urllib", "socket", "psycopg", "psycopg2", "openai"}
)


@dataclass(frozen=True)
class Bundle:
    manifest: JsonObject
    fragments: tuple[JsonObject, ...]
    facts: tuple[JsonObject, ...]
    dispositions: tuple[JsonObject, ...]
    expression: JsonObject
    fixtures: tuple[JsonObject, ...]
    result: JsonObject


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> tuple[JsonObject, ...]:
    values: list[JsonObject] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected object: {path}:{line_number}")
        values.append(value)
    return tuple(values)


def load_bundle(package_root: Path) -> Bundle:
    return Bundle(
        manifest=load_json(package_root / "retrieval_manifest.v1.json"),
        fragments=load_jsonl(package_root / "data/retrieval_fragments.v1.jsonl"),
        facts=load_jsonl(package_root / "data/verified_precise_facts.v1.jsonl"),
        dispositions=load_jsonl(package_root / "data/source_dispositions.v1.jsonl"),
        expression=load_json(package_root / "data/expression_candidates.v1.json"),
        fixtures=load_jsonl(package_root / "fixtures/retrieval_cases.v1.jsonl"),
        result=load_json(package_root / "result/brand_fact_retrieval_result.v1.json"),
    )


def require_fields(
    value: Mapping[str, Any], fields: Iterable[str], label: str, errors: list[str]
) -> None:
    missing = sorted(set(fields) - set(value))
    if missing:
        errors.append(f"{label}: missing fields {missing}")


def candidate_snapshot_digest(repo_root: Path = REPO_ROOT) -> str:
    entries: list[JsonObject] = []
    for relative_path in IMMUTABLE_SNAPSHOT_PATHS:
        path = repo_root / relative_path
        if not path.is_file():
            raise ValueError(f"candidate snapshot file missing: {relative_path}")
        entries.append({"path": relative_path.as_posix(), "sha256": sha256_file(path)})
    return digest_object(entries)


def validate_file_set(package_root: Path, require_reviews: bool, errors: list[str]) -> None:
    actual = {
        path.relative_to(package_root)
        for path in package_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    expected = BASE_PACKAGE_FILES | (REVIEW_PACKAGE_FILES if require_reviews else frozenset())
    if actual != expected:
        errors.append(
            f"package file set mismatch: missing={sorted(map(str, expected - actual))}, "
            f"extra={sorted(map(str, actual - expected))}"
        )


def validate_manifest(bundle: Bundle, repo_root: Path, errors: list[str]) -> None:
    manifest = bundle.manifest
    require_fields(
        manifest,
        {
            "schema_version",
            "task_id",
            "data_version_digest",
            "input_anchors",
            "artifacts",
            "counts",
            "output_contract",
            "readiness",
            "external_calls",
            "simulation_boundary",
        },
        "manifest",
        errors,
    )
    if manifest.get("task_id") != materialize.TASK_ID:
        errors.append("manifest task_id mismatch")
    anchors = manifest.get("input_anchors")
    expected_anchors = {
        path.as_posix(): digest for path, digest in materialize.INPUT_SHA256.items()
    }
    actual_anchors: dict[str, str] = {}
    if not isinstance(anchors, list):
        errors.append("manifest input_anchors must be a list")
    else:
        for item in anchors:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                errors.append("invalid manifest input anchor")
                continue
            actual_anchors[str(item["path"])] = str(item.get("sha256"))
    if actual_anchors != expected_anchors:
        errors.append("manifest input anchor set differs from the pinned Package 5 inputs")
    for relative, expected in expected_anchors.items():
        path = repo_root / relative
        if not path.is_file() or sha256_file(path) != expected:
            errors.append(f"upstream input drift: {relative}")
    expected_version = digest_object(
        {"input_sha256": expected_anchors, "policy_version": materialize.POLICY_VERSION}
    )
    if manifest.get("data_version_digest") != expected_version:
        errors.append("data_version_digest is not derived from pinned inputs and policy")

    artifact_rows = manifest.get("artifacts")
    artifacts: dict[str, JsonObject] = {}
    if isinstance(artifact_rows, list):
        for row in artifact_rows:
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                artifacts[str(row["path"])] = row
    expected_artifacts = {
        "data/retrieval_fragments.v1.jsonl": len(bundle.fragments),
        "data/verified_precise_facts.v1.jsonl": len(bundle.facts),
        "data/source_dispositions.v1.jsonl": len(bundle.dispositions),
        "data/expression_candidates.v1.json": 1,
    }
    if set(artifacts) != set(expected_artifacts):
        errors.append("manifest artifact set mismatch")
    package_root = repo_root / PACKAGE_RELATIVE_ROOT
    for relative, count in expected_artifacts.items():
        row = artifacts.get(relative, {})
        path = package_root / relative
        if row.get("record_count") != count:
            errors.append(f"artifact record count mismatch: {relative}")
        if not path.is_file() or row.get("sha256") != sha256_file(path):
            errors.append(f"artifact digest mismatch: {relative}")
        if path.is_file() and row.get("byte_size") != path.stat().st_size:
            errors.append(f"artifact byte size mismatch: {relative}")

    counts = manifest.get("counts")
    expected_counts = {
        "active_retrieval_fragments": 29,
        "active_verified_precise_facts": 5,
        "hold_records": 179,
        "source_dispositions": 206,
        "package3_narrative_input": 197,
        "package3_precise_fact_input": 9,
    }
    if not isinstance(counts, dict):
        errors.append("manifest counts missing")
    else:
        for key, expected_count in expected_counts.items():
            if counts.get(key) != expected_count:
                errors.append(f"manifest count mismatch: {key}")
    external = manifest.get("external_calls")
    if not isinstance(external, dict) or any(value != 0 for value in external.values()):
        errors.append("external call counts must all be measured as zero")
    readiness = manifest.get("readiness")
    if not isinstance(readiness, dict):
        errors.append("manifest readiness missing")
    else:
        for flag in REQUIRED_FALSE_FLAGS:
            if readiness.get(flag) is not False:
                errors.append(f"readiness must remain false: {flag}")
    boundary = manifest.get("simulation_boundary")
    if not isinstance(boundary, dict) or not (
        boundary.get("simulation_only") is True
        and boundary.get("publish_allowed") is False
        and boundary.get("runtime_consumable") is False
        and boundary.get("package2_prepare_called") is False
    ):
        errors.append("simulation boundary is not closed")


def ast_literal_frozenset(path: Path, variable: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == variable for target in node.targets):
            continue
        call = node.value
        if not isinstance(call, ast.Call) or not call.args:
            break
        literal = ast.literal_eval(call.args[0])
        if not isinstance(literal, set):
            break
        return {str(item) for item in literal}
    raise ValueError(f"unable to read {variable} from {path}")


def validate_records(bundle: Bundle, repo_root: Path, errors: list[str]) -> None:
    consumer = repo_root / "12_expression_service/expression_runtime_adapter_001/light_expression_service.py"
    try:
        fragment_required = ast_literal_frozenset(consumer, "REQUIRED_FRAGMENT_FIELDS")
        fact_required = ast_literal_frozenset(consumer, "REQUIRED_FACT_FIELDS")
    except (SyntaxError, ValueError) as exc:
        errors.append(f"cannot derive Package 2 consumer shape: {exc}")
        return
    contract = bundle.manifest.get("output_contract", {})
    if set(contract.get("fragment_required_fields", [])) != fragment_required:
        errors.append("manifest fragment shape differs from Package 2 live consumer")
    if set(contract.get("fact_required_fields", [])) != fact_required:
        errors.append("manifest fact shape differs from Package 2 live consumer")
    if contract.get("parallel_context_bundle_created") is not False:
        errors.append("parallel context bundle must not be created")
    if contract.get("plan_or_generator_created") is not False:
        errors.append("plan or generator must not be created")

    version = bundle.manifest.get("data_version_digest")
    source_manifest = materialize.load_json(repo_root / materialize.PACKAGE_3_MANIFEST)
    source_rows = source_manifest.get("sources")
    source_snapshots: dict[str, Path] = {}
    if not isinstance(source_rows, list):
        errors.append("Package 3 source manifest has no sources")
    else:
        for source_row in source_rows:
            if not isinstance(source_row, dict):
                continue
            source_id = source_row.get("source_id")
            snapshot_path = source_row.get("snapshot_path")
            if isinstance(source_id, str) and isinstance(snapshot_path, str):
                source_snapshots[source_id] = (
                    repo_root / materialize.PACKAGE_3_ROOT / snapshot_path
                )

    def source_slice(row: JsonObject, label: str) -> bytes | None:
        source_id = row.get("source_id")
        snapshot = source_snapshots.get(str(source_id))
        locator = row.get("source_position")
        if snapshot is None or not isinstance(locator, dict):
            errors.append(f"source locator missing: {label}")
            return None
        if row.get("source_sha256") != sha256_file(snapshot):
            errors.append(f"source snapshot digest mismatch: {label}")
            return None
        start = locator.get("byte_start")
        end = locator.get("byte_end_exclusive")
        if not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"source byte locator invalid: {label}")
            return None
        return snapshot.read_bytes()[start:end]

    fragment_ids: set[str] = set()
    for row in bundle.fragments:
        identifier = row.get("fragment_id")
        if not isinstance(identifier, str) or identifier in fragment_ids:
            errors.append(f"invalid or duplicate fragment_id: {identifier}")
            continue
        fragment_ids.add(identifier)
        require_fields(row, fragment_required, identifier, errors)
        if row.get("status") != "ACTIVE" or row.get("authorization_state") != "GRANTED":
            errors.append(f"active fragment state invalid: {identifier}")
        if row.get("data_version_digest") != version:
            errors.append(f"fragment data version mismatch: {identifier}")
        if row.get("fragment_sha256") != sha256_bytes(str(row.get("text", "")).encode("utf-8")):
            errors.append(f"fragment body digest mismatch: {identifier}")
        source_bytes = source_slice(row, identifier)
        if source_bytes is not None and source_bytes != str(row.get("text", "")).encode("utf-8"):
            errors.append(f"fragment source slice mismatch: {identifier}")
        if row.get("simulation_only") is not True or row.get("publish_allowed") is not False:
            errors.append(f"fragment simulation boundary invalid: {identifier}")
        if row.get("runtime_consumable") is not False:
            errors.append(f"fragment marked runtime consumable: {identifier}")

    fact_ids: set[str] = set()
    for row in bundle.facts:
        identifier = row.get("fact_id")
        if not isinstance(identifier, str) or identifier in fact_ids:
            errors.append(f"invalid or duplicate fact_id: {identifier}")
            continue
        fact_ids.add(identifier)
        require_fields(row, fact_required, identifier, errors)
        if row.get("status") != "ACTIVE" or row.get("data_version_digest") != version:
            errors.append(f"active fact state invalid: {identifier}")
        if row.get("fact_kind") not in {
            "SKU", "SPECIFICATION", "PRICE", "STOCK", "TIME_POINT", "AUTHORIZATION", "REVOCATION"
        }:
            errors.append(f"unsupported precise fact kind: {identifier}")
        if row.get("simulation_only") is not True or row.get("publish_allowed") is not False:
            errors.append(f"fact simulation boundary invalid: {identifier}")
        if row.get("runtime_consumable") is not False:
            errors.append(f"fact marked runtime consumable: {identifier}")
        source_bytes = source_slice(row, identifier)
        if source_bytes is not None and row.get("source_excerpt_sha256") != sha256_bytes(source_bytes):
            errors.append(f"fact source excerpt digest mismatch: {identifier}")

    source_narratives = {
        str(row["unit_id"]): row
        for row in materialize.load_jsonl(repo_root / materialize.NARRATIVE_INPUT)
    }
    source_facts = {
        str(row["fact_id"]): row
        for row in materialize.load_jsonl(repo_root / materialize.FACT_INPUT)
    }
    if len(source_narratives) != 197 or len(source_facts) != 9:
        errors.append("Package 3 source count drift")
    seen_sources: set[tuple[str, str]] = set()
    active_disposition_ids: set[str] = set()
    disposition_by_source: dict[str, JsonObject] = {}
    hold_count = 0
    for row in bundle.dispositions:
        record_type = row.get("record_type")
        source_id = row.get("source_record_id")
        key = (str(record_type), str(source_id))
        if key in seen_sources:
            errors.append(f"duplicate source disposition: {key}")
            continue
        seen_sources.add(key)
        disposition_by_source[str(source_id)] = row
        source = (
            source_narratives.get(str(source_id))
            if record_type == "NARRATIVE"
            else source_facts.get(str(source_id))
        )
        if source is None:
            errors.append(f"disposition source missing: {key}")
            continue
        if row.get("source_record_sha256") != digest_object(source):
            errors.append(f"source disposition digest mismatch: {key}")
        disposition = row.get("package5_disposition")
        derived = row.get("derived_record_id")
        derived_ids = row.get("derived_record_ids")
        if not isinstance(derived_ids, list) or any(
            not isinstance(identifier, str) for identifier in derived_ids
        ):
            errors.append(f"derived_record_ids invalid: {key}")
            derived_ids = []
        require_fields(
            row,
            {
                "tenant_id", "brand_id", "source_organization_id",
                "source_store_id", "applicable_content_account_ids",
                "authorization_ref", "disclosure_scope",
            },
            f"disposition {key}",
            errors,
        )
        projection = row.get("selector_projection")
        if record_type == "PRECISE_FACT" and (
            not isinstance(projection, dict) or set(projection) != {"fact_id"}
        ):
            errors.append(f"precise fact HOLD projection exposes value selectors: {key}")
        if disposition == "HOLD":
            hold_count += 1
            if derived is not None or derived_ids:
                errors.append(f"HOLD disposition has derived record: {key}")
        elif disposition in {"ACTIVE_FOR_SIMULATION_RETRIEVAL", "ACTIVE_VERIFIED_PRECISE_FACT"}:
            if not derived_ids:
                errors.append(f"active disposition lacks derived records: {key}")
            active_disposition_ids.update(str(identifier) for identifier in derived_ids)
            if len(derived_ids) == 1 and derived != derived_ids[0]:
                errors.append(f"single derived record pointer mismatch: {key}")
            if len(derived_ids) > 1 and derived is not None:
                errors.append(f"multi-fragment source must not claim one primary record: {key}")
        else:
            errors.append(f"unknown disposition: {key}")
    expected_source_keys = {
        *[("NARRATIVE", key) for key in source_narratives],
        *[("PRECISE_FACT", key) for key in source_facts],
    }
    if seen_sources != expected_source_keys:
        errors.append("source disposition coverage is not exactly 197 narratives plus 9 facts")
    if active_disposition_ids != fragment_ids | fact_ids:
        errors.append("active dispositions do not exactly close over derived records")
    if hold_count != 179:
        errors.append(f"expected 179 HOLD dispositions, found {hold_count}")
    restricted = disposition_by_source.get("BD-NARR-05-004", {})
    if not (
        restricted.get("package5_disposition") == "HOLD"
        and restricted.get("reason_code")
        == "PACKAGE5_MIXED_RESTRICTED_ASSET_BOUNDARIES"
    ):
        errors.append("mixed restricted asset section must remain HOLD")
    split = disposition_by_source.get("BD-NARR-04-013", {})
    split_ids = split.get("derived_record_ids")
    if not isinstance(split_ids, list) or len(split_ids) != 8:
        errors.append("multi-product R&D section must produce eight traceable fragments")


def validate_expression(bundle: Bundle, errors: list[str]) -> None:
    expression = bundle.expression
    if expression.get("candidate_only") is not True:
        errors.append("expression partition must remain candidate-only")
    for key in ("runtime_authoritative", "may_grant_fact_authorization_or_scope", "publish_allowed"):
        if expression.get(key) is not False:
            errors.append(f"expression partition authority leak: {key}")
    lineage = expression.get("example_lineage")
    if not isinstance(lineage, list) or len(lineage) != 3:
        errors.append("expression example lineage must contain three candidates")
        return
    for row in lineage:
        if not isinstance(row, dict):
            errors.append("invalid expression lineage row")
            continue
        for key in ("may_grant_fact", "may_grant_authorization", "may_grant_scope", "runtime_authoritative", "publish_allowed"):
            if row.get(key) is not False:
                errors.append(f"expression lineage authority leak: {row.get('example_ref')}:{key}")


def apply_mutation(index: RetrievalIndex, mutation: object) -> RetrievalIndex:
    if not isinstance(mutation, dict):
        return index
    record_type = mutation.get("record_type")
    rows = index.fragments if record_type == "FRAGMENT" else index.facts
    id_key = "fragment_id" if record_type == "FRAGMENT" else "fact_id"
    base_id = mutation.get("base_id")
    matching = [row for row in rows if row.get(id_key) == base_id]
    if len(matching) != 1:
        raise ValueError(f"fixture mutation base missing: {base_id}")
    clone = copy.deepcopy(matching[0])
    clone[id_key] = mutation.get("new_id")
    updates = mutation.get("updates")
    if not isinstance(updates, dict):
        raise ValueError("fixture mutation updates must be an object")
    clone.update(copy.deepcopy(updates))
    if record_type == "FRAGMENT":
        return index.with_records(fragments=[clone])
    if record_type == "FACT":
        return index.with_records(facts=[clone])
    raise ValueError(f"unsupported fixture record type: {record_type}")


def assert_expected(result: JsonObject, expected: Mapping[str, Any], case_id: str) -> None:
    fragment_ids = {str(row["fragment_id"]) for row in result["scoped_retrieval_fragments"]}
    fact_ids = {str(row["fact_id"]) for row in result["verified_precise_facts"]}
    gap_codes = {str(row["code"]) for row in result["gaps"]}
    checks = {
        "fragment_count": len(fragment_ids),
        "fact_count": len(fact_ids),
        "resolved_account": result["resolved_scope"]["content_account_id"],
        "client_claims_ignored": result["retrieval_audit"]["client_claims_ignored"],
        "claim_precedence": result["claim_precedence"]["policy"],
        "narrative_may_create_precise_fact": result["claim_precedence"]["narrative_may_create_precise_fact"],
    }
    for key, actual in checks.items():
        if key in expected and expected[key] != actual:
            raise ValueError(f"{case_id}: {key} expected {expected[key]!r}, got {actual!r}")
    for identifier in expected.get("fragment_contains", []):
        if identifier not in fragment_ids:
            raise ValueError(f"{case_id}: missing fragment {identifier}")
    for identifier in expected.get("fragment_excludes", []):
        if identifier in fragment_ids or identifier in result["retrieval_audit"]["ranker_input_fragment_ids"]:
            raise ValueError(f"{case_id}: excluded fragment reached ranker {identifier}")
    for identifier in expected.get("fact_contains", []):
        if identifier not in fact_ids:
            raise ValueError(f"{case_id}: missing fact {identifier}")
    if "gap_codes" in expected and set(expected["gap_codes"]) != gap_codes:
        raise ValueError(f"{case_id}: gap codes expected {expected['gap_codes']!r}, got {sorted(gap_codes)!r}")
    reason = expected.get("excluded_reason")
    if reason is not None and result["retrieval_audit"]["fragment_excluded_counts"].get(reason, 0) < 1:
        raise ValueError(f"{case_id}: exclusion reason not observed: {reason}")
    if expected.get("expression_non_authoritative") is True:
        partition = result["expression_candidate_partition"]
        if partition.get("runtime_authoritative") is not False or partition.get("may_grant_fact_authorization_or_scope") is not False:
            raise ValueError(f"{case_id}: expression partition gained authority")


def copy_derivation_inputs(destination: Path) -> None:
    for relative in materialize.INPUT_SHA256:
        source = REPO_ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    source_snapshots = REPO_ROOT / materialize.PACKAGE_3_ROOT / "source_snapshots"
    target_snapshots = destination / materialize.PACKAGE_3_ROOT / "source_snapshots"
    shutil.copytree(source_snapshots, target_snapshots)


def validate_rebuild_withdrawal(source_record_id: str) -> None:
    base_fragments, _, _, _ = materialize.derive_bundle(REPO_ROOT)
    with tempfile.TemporaryDirectory(prefix="pkg5-withdraw-") as directory:
        temp_root = Path(directory)
        copy_derivation_inputs(temp_root)
        narrative_path = temp_root / materialize.NARRATIVE_INPUT
        rows = materialize.load_jsonl(narrative_path)
        target = [row for row in rows if row.get("unit_id") == source_record_id]
        if len(target) != 1:
            raise ValueError("withdrawal fixture source record missing")
        target[0]["revocation_ref"] = "REVOCATION-PKG5-REBUILD-TEST"
        narrative_path.write_bytes(materialize.canonical_jsonl(rows))
        rebuilt, _, _, _ = materialize.derive_bundle(temp_root)
    target_id = f"PKG5-FRAGMENT-{source_record_id}"
    if any(row.get("fragment_id") == target_id for row in rebuilt):
        raise ValueError("withdrawn source remained in rebuilt fragments")
    def strip_version(row: JsonObject) -> JsonObject:
        return {
            key: value
            for key, value in row.items()
            if key != "data_version_digest"
        }

    before = {
        str(row["fragment_id"]): strip_version(row)
        for row in base_fragments
        if row.get("fragment_id") != target_id
    }
    after = {str(row["fragment_id"]): strip_version(row) for row in rebuilt}
    if before != after:
        raise ValueError("withdrawal rebuild changed unrelated fragment content")


def validate_source_version_change() -> None:
    base_fragments, _, _, _ = materialize.derive_bundle(REPO_ROOT)
    with tempfile.TemporaryDirectory(prefix="pkg5-version-") as directory:
        temp_root = Path(directory)
        copy_derivation_inputs(temp_root)
        narrative_path = temp_root / materialize.NARRATIVE_INPUT
        rows = materialize.load_jsonl(narrative_path)
        rows[0]["package5_version_probe"] = "changed-source-metadata"
        narrative_path.write_bytes(materialize.canonical_jsonl(rows))
        changed_fragments, _, _, _ = materialize.derive_bundle(temp_root)
    if not base_fragments or not changed_fragments:
        raise ValueError("source version test has no active fragments")
    if base_fragments[0]["data_version_digest"] == changed_fragments[0]["data_version_digest"]:
        raise ValueError("source version change did not change data version digest")


def validate_structural(bundle: Bundle, errors: list[str]) -> None:
    if not bundle.fragments or not bundle.facts:
        errors.append("structural fixture needs both output channels")
    if any(row.get("runtime_consumable") is not False for row in (*bundle.fragments, *bundle.facts)):
        errors.append("structural fixture found runtime-consumable records")
    if bundle.expression.get("may_grant_fact_authorization_or_scope") is not False:
        errors.append("expression candidates may grant authority")


def run_fixture_cases(bundle: Bundle, errors: list[str]) -> None:
    authority = IdentityAuthority.from_path()
    base_index = RetrievalIndex.from_package(PACKAGE_ROOT)
    case_ids: set[str] = set()
    for case in bundle.fixtures:
        case_id = str(case.get("case_id"))
        if case_id in case_ids:
            errors.append(f"duplicate fixture case_id: {case_id}")
            continue
        case_ids.add(case_id)
        operation = case.get("operation")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{case_id}: expected must be an object")
            continue
        try:
            if operation in {"RETRIEVE", "ERROR", "DETERMINISM"}:
                index = apply_mutation(base_index, case.get("mutation"))
                service = BrandFactRetrievalService(authority, index)
                arguments = {
                    "request": case.get("request", {}),
                    "principal_id": str(case.get("principal_id")),
                    "content_account_id": str(case.get("content_account_id")),
                    "query_at": str(case.get("query_at")),
                }
                if operation == "ERROR":
                    try:
                        service.retrieve(**arguments)
                    except RetrievalContractError as exc:
                        if exc.code != expected.get("error_code"):
                            raise ValueError(f"expected error {expected.get('error_code')}, got {exc.code}") from exc
                    else:
                        raise ValueError("expected request rejection")
                elif operation == "DETERMINISM":
                    count = expected.get("identical_replays")
                    if not isinstance(count, int) or count < 2:
                        raise ValueError("invalid replay count")
                    outputs = [canonical_json_bytes(service.retrieve(**arguments)) for _ in range(count)]
                    if len(set(outputs)) != 1:
                        raise ValueError("identical requests produced different bytes")
                else:
                    assert_expected(service.retrieve(**arguments), expected, case_id)
            elif operation == "STRUCTURAL":
                validate_structural(bundle, errors)
            elif operation == "REBUILD_WITHDRAWAL":
                validate_rebuild_withdrawal(str(case.get("source_record_id")))
            elif operation == "SOURCE_VERSION_CHANGE":
                validate_source_version_change()
            else:
                raise ValueError(f"unknown operation {operation}")
        except (KeyError, TypeError, ValueError, RetrievalContractError) as exc:
            errors.append(f"{case_id}: {exc}")
    if len(case_ids) != 32:
        errors.append(f"expected 32 fixture cases, found {len(case_ids)}")


def validate_materialization(package_root: Path, errors: list[str]) -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="pkg5-materialize-") as directory:
            temp_root = Path(directory)
            fixture_target = temp_root / materialize.FIXTURE_PATH
            fixture_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package_root / materialize.FIXTURE_PATH, fixture_target)
            materialize.materialize(REPO_ROOT, temp_root)
            for relative in materialize.GENERATED_PATHS:
                if (temp_root / relative).read_bytes() != (package_root / relative).read_bytes():
                    errors.append(f"non-deterministic materialization: {relative}")
    except (OSError, ValueError) as exc:
        errors.append(f"materialization replay failed: {exc}")


def validate_runtime_import_boundary(errors: list[str]) -> None:
    for relative in ("brand_fact_retrieval.py", "materialize_retrieval.py"):
        path = PACKAGE_ROOT / relative
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errors.append(f"syntax error: {relative}:{exc}")
            continue
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = imported & BANNED_RUNTIME_IMPORTS
        if forbidden:
            errors.append(f"external runtime imports found in {relative}: {sorted(forbidden)}")


def load_reviews(errors: list[str]) -> list[JsonObject]:
    reviews: list[JsonObject] = []
    for path in REVIEW_PATHS:
        if not path.is_file():
            errors.append(f"review missing: {path.relative_to(PACKAGE_ROOT)}")
            continue
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or not isinstance(document.get("review"), dict):
            errors.append(f"review root invalid: {path.name}")
            continue
        reviews.append(document["review"])
    return reviews


def validate_reviews(bundle: Bundle, errors: list[str]) -> None:
    reviews = load_reviews(errors)
    if len(reviews) != 2:
        return
    snapshot = candidate_snapshot_digest()
    identities: set[str] = set()
    sessions: set[str] = set()
    runs: set[str] = set()
    review_types: set[str] = set()
    commits: set[str] = set()
    for review in reviews:
        require_fields(
            review,
            {
                "schema_version", "review_id", "task_id", "review_type", "reviewer_identity",
                "reviewer_session_id", "reviewer_run_id", "candidate_commit",
                "candidate_snapshot_digest", "score", "verdict", "hard_blockers",
                "acceptance_ids", "signed_at",
            },
            "review",
            errors,
        )
        identities.add(str(review.get("reviewer_identity")))
        sessions.add(str(review.get("reviewer_session_id")))
        runs.add(str(review.get("reviewer_run_id")))
        review_types.add(str(review.get("review_type")))
        commits.add(str(review.get("candidate_commit")))
        if review.get("task_id") != materialize.TASK_ID:
            errors.append("review task mismatch")
        if review.get("candidate_snapshot_digest") != snapshot:
            errors.append("review does not bind the live candidate snapshot")
        score = review.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or score < 90 or score > 100:
            errors.append("review score must be an integer from 90 through 100")
        if review.get("verdict") != "PASS" or review.get("hard_blockers") != []:
            errors.append("review must explicitly PASS without hard blockers")
        acceptance_ids = review.get("acceptance_ids")
        if not isinstance(acceptance_ids, list) or not acceptance_ids:
            errors.append("review acceptance_ids must be non-empty")
    if len(identities) != 2 or len(sessions) != 2 or len(runs) != 2:
        errors.append("the two reviews must have distinct identity, session, and run records")
    if review_types != EXPECTED_REVIEW_TYPES:
        errors.append("review type set mismatch")
    if len(commits) != 1 or "None" in commits or "" in commits:
        errors.append("reviews must bind one non-empty candidate commit")
    else:
        candidate = next(iter(commits))
        process = subprocess.run(
            ["git", "merge-base", "--is-ancestor", candidate, "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        if process.returncode != 0:
            errors.append("reviewed candidate commit is not an ancestor of HEAD")

    result = bundle.result
    if result.get("status") != "PASS_BRAND_FACT_RETRIEVAL_PENDING_PACKAGE_6":
        errors.append("final result status mismatch")
    if result.get("candidate_snapshot_digest") != snapshot:
        errors.append("result candidate snapshot digest mismatch")
    if len(commits) == 1 and result.get("candidate_commit") != next(iter(commits)):
        errors.append("result candidate commit differs from reviews")
    result_reviews = result.get("independent_reviews")
    if not isinstance(result_reviews, list) or len(result_reviews) != 2:
        errors.append("result must summarize exactly two independent reviews")


def validate_result(bundle: Bundle, require_reviews: bool, errors: list[str]) -> None:
    result = bundle.result
    require_fields(
        result,
        {
            "schema_version", "task_id", "status", "counts", "checks", "readiness",
            "external_calls", "core_numbers", "candidate_snapshot_digest",
            "candidate_commit", "independent_reviews",
        },
        "result",
        errors,
    )
    if result.get("task_id") != materialize.TASK_ID:
        errors.append("result task_id mismatch")
    counts = result.get("counts")
    expected = {
        "active_retrieval_fragments": 29,
        "active_verified_precise_facts": 5,
        "hold_records": 179,
        "fixture_cases": 32,
    }
    if not isinstance(counts, dict) or any(counts.get(key) != value for key, value in expected.items()):
        errors.append("result counts mismatch")
    readiness = result.get("readiness")
    if not isinstance(readiness, dict) or any(readiness.get(flag) is not False for flag in REQUIRED_FALSE_FLAGS):
        errors.append("result readiness flags must all remain false")
    calls = result.get("external_calls")
    if not isinstance(calls, dict) or any(value != 0 for value in calls.values()):
        errors.append("result external calls must remain zero")
    numbers = result.get("core_numbers")
    if numbers != {"target_300": 300, "reference_120": 120, "historical_86": 86, "changed": False}:
        errors.append("result core numbers changed")
    if not require_reviews:
        if result.get("status") != "CANDIDATE_PENDING_INDEPENDENT_REVIEWS":
            errors.append("pre-review result status mismatch")
        if result.get("independent_reviews") != []:
            errors.append("pre-review result must not self-assert review outcomes")


def validate_package(
    package_root: Path = PACKAGE_ROOT,
    *,
    require_reviews: bool,
    replay_materialization: bool = True,
    run_cases: bool = True,
) -> list[str]:
    errors: list[str] = []
    try:
        bundle = load_bundle(package_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"load failure: {exc}"]
    validate_file_set(package_root, require_reviews, errors)
    validate_manifest(bundle, REPO_ROOT, errors)
    validate_records(bundle, REPO_ROOT, errors)
    validate_expression(bundle, errors)
    validate_runtime_import_boundary(errors)
    validate_result(bundle, require_reviews, errors)
    if replay_materialization:
        validate_materialization(package_root, errors)
    if run_cases:
        run_fixture_cases(bundle, errors)
    if require_reviews:
        validate_reviews(bundle, errors)
    return errors


def selftest(require_reviews: bool) -> list[str]:
    failures: list[str] = []
    mutations: Sequence[tuple[str, Path, Any]] = (
        (
            "fragment body tamper",
            Path("data/retrieval_fragments.v1.jsonl"),
            lambda path: path.write_text(path.read_text(encoding="utf-8").replace("尺码", "伪改", 1), encoding="utf-8"),
        ),
        (
            "fact state tamper",
            Path("data/verified_precise_facts.v1.jsonl"),
            lambda path: path.write_text(path.read_text(encoding="utf-8").replace('"status":"ACTIVE"', '"status":"HOLD"', 1), encoding="utf-8"),
        ),
        (
            "disposition tamper",
            Path("data/source_dispositions.v1.jsonl"),
            lambda path: path.write_text(path.read_text(encoding="utf-8").replace('"package5_disposition":"HOLD"', '"package5_disposition":"ACTIVE_FOR_SIMULATION_RETRIEVAL"', 1), encoding="utf-8"),
        ),
        (
            "expression authority tamper",
            Path("data/expression_candidates.v1.json"),
            lambda path: path.write_text(path.read_text(encoding="utf-8").replace('"may_grant_fact_authorization_or_scope": false', '"may_grant_fact_authorization_or_scope": true', 1), encoding="utf-8"),
        ),
        (
            "readiness tamper",
            Path("retrieval_manifest.v1.json"),
            lambda path: path.write_text(path.read_text(encoding="utf-8").replace('"retrieval_ready": false', '"retrieval_ready": true', 1), encoding="utf-8"),
        ),
        (
            "upstream anchor tamper",
            Path("retrieval_manifest.v1.json"),
            lambda path: path.write_text(path.read_text(encoding="utf-8").replace(materialize.INPUT_SHA256[materialize.NARRATIVE_INPUT], "0" * 64, 1), encoding="utf-8"),
        ),
    )
    for label, relative, mutate in mutations:
        with tempfile.TemporaryDirectory(prefix="pkg5-selftest-") as directory:
            temp_package = Path(directory) / "package"
            shutil.copytree(PACKAGE_ROOT, temp_package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            mutate(temp_package / relative)
            errors = validate_package(
                temp_package,
                require_reviews=require_reviews,
                replay_materialization=False,
                run_cases=False,
            )
            if not errors:
                failures.append(f"selftest mutation was not rejected: {label}")
    if require_reviews:
        with tempfile.TemporaryDirectory(prefix="pkg5-review-selftest-") as directory:
            temp_package = Path(directory) / "package"
            shutil.copytree(PACKAGE_ROOT, temp_package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            review_path = temp_package / "review/architecture_consumability_review.v1.yaml"
            review_path.write_text(review_path.read_text(encoding="utf-8").replace("score: 9", "score: 8", 1), encoding="utf-8")
            errors = validate_package(
                temp_package,
                require_reviews=True,
                replay_materialization=False,
                run_cases=False,
            )
            if not errors:
                failures.append("selftest mutation was not rejected: review score")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-review", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_reviews = not args.pre_review
    errors = validate_package(require_reviews=require_reviews)
    if args.selftest:
        errors.extend(selftest(require_reviews))
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    mode = "final" if require_reviews else "pre-review"
    print(f"PASS: Package 5 brand fact retrieval ({mode}, 32 cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
