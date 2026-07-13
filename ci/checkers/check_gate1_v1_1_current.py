#!/usr/bin/env python3
"""Fail-closed current checker for the Gate 1 v1.1 P1A review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml


if not __debug__:
    print("check_gate1_v1_1_current refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "GATE1_V11_STANDARD_BASELINE_REVIEW_PACKET_AND_GOVERNANCE_PREFLIGHT_001"
P1B_TASK_ID = "GATE1_V11_SIGNED_REVIEW_CLOSEOUT_AND_BASELINE_FREEZE_001"
BASELINE_COMMIT = "473a8664bdab37246db1b75785f765e62c80ed86"
V1_REPAIR_BASELINE_COMMIT = "69235a23d62d6c92683fadf572f7b8c291771dd6"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1a_standard_baseline_review_packet_and_governance_preflight_001"
)
P1B_TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001"
)
CURRENT_OWNER_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml"
)
REPORT_PATH = Path(
    "docs/reports/gate1_v1_1_generator_gkb_retrospective_and_recovery_plan_20260713.md"
)
STANDARD_SNAPSHOT_PATH = (
    TASK_ROOT / "standard/diyu_content_composition_standard.v1.1.md"
)
STANDARD_CONTRACT_PATH = TASK_ROOT / "standard/v1_1_standard_contract.v0.1.yaml"
BASELINE_MANIFEST_PATH = TASK_ROOT / "baseline/gate1_input_baseline_manifest.v0.1.yaml"
REVIEW_PACKET_PATH = TASK_ROOT / "review/unified_gate1_review_packet.v0.1.jsonl"
REVIEW_CONTRACT_PATH = TASK_ROOT / "review/independent_review_contract.v0.1.yaml"
REVIEW_RECORD_TEMPLATE_PATH = (
    TASK_ROOT / "review/unified_independent_review_record_template.v0.1.yaml"
)
LEGACY_EDGE_MANIFEST_PATH = (
    TASK_ROOT
    / "component/legacy_component_applicability_historical_manifest.v0.1.jsonl"
)
COMPAT_RECEIPT_PATH = (
    TASK_ROOT / "compatibility/governance_compatibility_repair_receipt.v0.1.yaml"
)
RESULT_PATH = TASK_ROOT / "result/p1a_standard_baseline_preflight_result.v0.1.yaml"
MATERIALIZER_PATH = TASK_ROOT / "run_p1a_standard_baseline_review_packet_freezer.py"
P1B_MATERIALIZER_PATH = P1B_TASK_ROOT / "run_p1b_signed_review_closeout_freezer.py"
P1B_IMPORT_MANIFEST_PATH = (
    P1B_TASK_ROOT / "imports/signed_review_import_manifest.v0.1.yaml"
)
P1B_CONTRACT_PATH = (
    P1B_TASK_ROOT / "contract/p1b_signed_review_closeout_contract.v0.1.yaml"
)
P1B_NORMALIZED_PATH = P1B_TASK_ROOT / "normalized/signed_review_records.v0.1.jsonl"
P1B_CONTENT_PATH = P1B_TASK_ROOT / "content/reference_120_final_dispositions.v0.1.jsonl"
P1B_CONTENT_GAPS_PATH = (
    P1B_TASK_ROOT / "content/reference_120_content_product_gap_matrix.v0.1.yaml"
)
P1B_ROUTE_GOLD_PATH = P1B_TASK_ROOT / "route/route_60_gold_answers.v0.1.jsonl"
P1B_ROUTE_FREEZE_PATH = P1B_TASK_ROOT / "route/route_60_gold_freeze_manifest.v0.1.yaml"
P1B_ROUTE_COMPARISON_PATH = (
    P1B_TASK_ROOT / "route/route_60_current_actual_comparison.v0.1.jsonl"
)
P1B_COMPONENT_PATH = (
    P1B_TASK_ROOT / "component/component_86_final_dispositions.v0.1.jsonl"
)
P1B_ACTIVE_COMPONENTS_PATH = (
    P1B_TASK_ROOT / "component/active_gate1_development_components.v0.1.jsonl"
)
P1B_ACTIVE_EDGES_PATH = (
    P1B_TASK_ROOT / "component/active_gate1_development_edges.v0.1.jsonl"
)
P1B_COMPONENT_GAPS_PATH = (
    P1B_TASK_ROOT / "component/component_supply_gap_matrix.v0.1.yaml"
)
P1B_TEST_INPUTS_PATH = (
    P1B_TASK_ROOT / "test_inputs/gate1_development_test_input_manifest.v0.1.yaml"
)
P1B_COMPAT_RECEIPT_PATH = (
    P1B_TASK_ROOT / "compatibility/p1b_historical_identity_repair_receipt.v0.1.yaml"
)
P1B_RESULT_PATH = P1B_TASK_ROOT / "result/p1b_signed_review_closeout_result.v0.1.yaml"

CLEAN_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
ROUTE_INPUT_PATH = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/"
    "route/route_inputs.v0.1.jsonl"
)
ROUTE_ACTUAL_PATH = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001/"
    "route/route_regression_actuals.v0.1.jsonl"
)
COMPONENT_SOURCE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
    "reviewed_reusable_component_registry.v0.4.jsonl"
)
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
B24_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_b_channel_24_component_review.py")
SUCCESSOR_CHECKER_PATH = Path(
    "ci/checkers/check_orch_generator_v2_b_channel_component_consumption_dev_gate.py"
)
CI_WORKFLOW_PATH = Path(".github/workflows/ci.yml")

STANDARD_SHA256 = "022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542"
CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
ROUTE_INPUT_SHA256 = "68bc65bff904652f1e565097117c7e8dfccdcc6ef00d2e3a0e93a082a4d72f12"
ROUTE_ACTUAL_SHA256 = "bb7d68686761b7be092f191a0f46cb7493a3947f98959703c3ccaa69a86de3ad"
COMPONENT_SOURCE_SHA256 = (
    "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601"
)
REPORT_AFTER_POLICY_SHA256 = (
    "b89dd9f29bc084c9df69595efc6e3145372ade05210c0ecfe7df76f5aba6f02d"
)
B24_CHECKER_BEFORE_SHA256 = (
    "ff4060e02f387e92b9ec1613df31b5b855cbd04a1155d92f5ca03dacf3191394"
)
SUCCESSOR_CHECKER_BEFORE_SHA256 = (
    "95fcf3e6716e86f01a210c64dbe4685705962583ff9b2c560182389ba66df71c"
)
CURRENT_GATE1_CHECKER_V1_BEFORE_SHA256 = (
    "679343b9187ad12c3af077ab4041a3c706bcef56b915c6ef0234af54319ee716"
)
P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256 = (
    "29a872dd08b13c02a776ca4b4074a419320667a97b6c16125ab03432626d3806"
)
P1B_BASELINE_COMMIT = "01da326e4195b47e9b769b025bdf962936f10419"
P1B_IMPORT_HASHES = {
    "independent_reviews/review_job.v0.yaml": "511e203a464b7e57fdf2661abc7254f168c0da59c1631f618a861f3cf8f9192a",
    "independent_reviews/review_job_blindness_amendment.v0.yaml": "fa10da85ac4b380d426fc3ac896d56e832b2ff877001ff0d6767793f1f1861c1",
    "independent_reviews/review_session_invalidations.v0.yaml": "5cb3c049ef8c99a4f89400a1c76b4383ae407f78d0d918603fff04d187583fcb",
    "independent_reviews/adjudication_assignment.v0.yaml": "1cf4c1987af6a803baa741877bb51462e789b46341c9550040e8936e13a9a98b",
    "independent_reviews/primary/records.jsonl": "fdaaff1355e3365fa51ecc26cac8d342f2c736b69cd2022ecf921ce339778a51",
    "independent_reviews/primary/report.md": "149bab88fdfca4203781ddb8aaee76897364bdca9ccd72ce2789f32ad3b7fe5c",
    "independent_reviews/primary/run_manifest.yaml": "801916ecf79b01023c2eec8b2d5e969565be6afe3f7c29e77dd61a7e5660a4c9",
    "independent_reviews/secondary/records.jsonl": "61586c7fce34baa59db1c179eeeae7214b6afebb3daa2282221e68e91f7e6b61",
    "independent_reviews/secondary/report.md": "38ce8105b9e747eb0f26ceca15e8173da56143e99078a485414dcebd64f7a76c",
    "independent_reviews/secondary/run_manifest.yaml": "07283675742cf0fd9900d6a5edc7b664071e4f4b603cb0a54786bd6ddf107bcb",
    "independent_reviews/adjudication/records.jsonl": "47b88fd579f7fce70ed20f4a9ad43000f013019b5cbcf7e1338c04137e7c973c",
    "independent_reviews/adjudication/report.md": "940742b85805a8abe6cf495cb34a2095081507e863bd4bc8abe165b91084959a",
    "independent_reviews/adjudication/run_manifest.yaml": "c52eb752b9fd0ab38732e2504142c895da3e1c20b830d20f7650e1f8fb543d0b",
    "independent_reviews/coordinator_review_checkpoint_closeout.v0.md": "5d68c5e2510e633bd25a6c076352727cdcd169bd2c1f452ae0acbd80454c72e2",
    "coordinator_expert_review.v1.md": "6f1485cbbef84c52c546f171e7b1a49c5b87e2163d51a35e4a359e5b804bf6aa",
}

ALLOWED_EXACT_PATHS = frozenset(
    {
        CURRENT_OWNER_PATH,
        REPORT_PATH,
        Path("ci/checkers/check_gate1_v1_1_current.py"),
    }
)
TASK_MANAGED_PATHS = frozenset(
    {
        STANDARD_SNAPSHOT_PATH,
        STANDARD_CONTRACT_PATH,
        BASELINE_MANIFEST_PATH,
        REVIEW_PACKET_PATH,
        REVIEW_CONTRACT_PATH,
        REVIEW_RECORD_TEMPLATE_PATH,
        LEGACY_EDGE_MANIFEST_PATH,
        COMPAT_RECEIPT_PATH,
        RESULT_PATH,
        MATERIALIZER_PATH,
    }
)
READY_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "Serving_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "release_ready",
        "production_ready",
        "generator_qualified",
        "runtime_ingest_ready",
        "runtime_provider_adapter_qualified",
    }
)


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: dict[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def add_error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return value


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[tuple[dict[str, Any], str]]:
    rows: list[tuple[dict[str, Any], str]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line:
            continue
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            raise TypeError(f"{path}:{line_number} is not a JSON object")
        rows.append((value, raw_line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(canonical_json(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def recursively_find_true(value: Any, keys: frozenset[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and child is True:
                found.append(key)
            found.extend(recursively_find_true(child, keys))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursively_find_true(child, keys))
    return found


def recursively_find_strings(value: Any) -> list[str]:
    """Return all mapping keys and scalar strings for narrow leakage checks."""

    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.append(str(key))
            found.extend(recursively_find_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursively_find_strings(child))
    elif isinstance(value, str):
        found.append(value)
    return found


def git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def unexpected_write_paths(paths: set[Path]) -> list[str]:
    unexpected: list[str] = []
    for path in paths:
        if path.is_relative_to(P1B_TASK_ROOT):
            continue
        if path.is_relative_to(TASK_ROOT):
            if path not in TASK_MANAGED_PATHS:
                unexpected.append(path.as_posix())
        elif path not in ALLOWED_EXACT_PATHS:
            unexpected.append(path.as_posix())
    return sorted(unexpected)


def validate_write_surface(root: Path, errors: list[dict[str, str]]) -> None:
    if not (root / ".git").exists():
        return
    ancestor = git(
        root, ["merge-base", "--is-ancestor", V1_REPAIR_BASELINE_COMMIT, "HEAD"]
    )
    if ancestor.returncode != 0:
        add_error(errors, "E_BASELINE", "baseline commit is not an ancestor of HEAD")
        return
    changed = git(root, ["diff", "--name-only", f"{V1_REPAIR_BASELINE_COMMIT}..HEAD"])
    unstaged = git(root, ["diff", "--name-only", "HEAD"])
    untracked = git(root, ["ls-files", "--others", "--exclude-standard"])
    if any(result.returncode != 0 for result in (changed, unstaged, untracked)):
        add_error(errors, "E_WRITE_SURFACE", "unable to inspect git paths")
        return
    paths = {
        Path(line)
        for result in (changed, unstaged, untracked)
        for line in result.stdout.splitlines()
        if line
    }
    unexpected = unexpected_write_paths(paths)
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", str(unexpected))


def source_maps(root: Path, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    expected_hashes = {
        CLEAN_120_PATH: CLEAN_120_SHA256,
        ROUTE_INPUT_PATH: ROUTE_INPUT_SHA256,
        ROUTE_ACTUAL_PATH: ROUTE_ACTUAL_SHA256,
        COMPONENT_SOURCE_PATH: COMPONENT_SOURCE_SHA256,
    }
    for relative_path, expected_hash in expected_hashes.items():
        path = root / relative_path
        if not path.exists() or sha256_file(path) != expected_hash:
            add_error(errors, "E_SOURCE_DRIFT", relative_path.as_posix())
    if errors:
        return None
    try:
        clean_rows = read_jsonl(root / CLEAN_120_PATH)
        route_input_rows = read_jsonl(root / ROUTE_INPUT_PATH)
        route_actual_rows = read_jsonl(root / ROUTE_ACTUAL_PATH)
        component_rows = read_jsonl(root / COMPONENT_SOURCE_PATH)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_SOURCE_PARSE", str(exc))
        return None
    if (
        len(clean_rows) != 120
        or len(route_input_rows) != 60
        or len(route_actual_rows) != 60
    ):
        add_error(errors, "E_SOURCE_COUNT", "expected 120/60/60")
    if len(component_rows) != 86:
        add_error(errors, "E_SOURCE_COUNT", "expected 86 components")

    def as_map(
        rows: list[tuple[dict[str, Any], str]], key: str, label: str
    ) -> dict[str, str]:
        output: dict[str, str] = {}
        for row, raw_line in rows:
            value = row.get(key)
            if not isinstance(value, str) or not value or value in output:
                add_error(errors, "E_SOURCE_IDS", label)
                continue
            output[value] = sha256_bytes(raw_line.encode("utf-8"))
        return output

    clean_by_id = as_map(clean_rows, "asset_id", "clean_120")
    route_input_by_id = as_map(route_input_rows, "case_id", "route_input")
    route_actual_by_id = as_map(route_actual_rows, "case_id", "route_actual")
    component_by_id = as_map(component_rows, "component_id", "components")
    if set(route_input_by_id) != set(route_actual_by_id):
        add_error(errors, "E_SOURCE_ROUTE_PAIRING", "route input/actual ids differ")
    edge_set: set[tuple[str, str]] = set()
    for row, _ in component_rows:
        component_id = row.get("component_id")
        cp_ids = row.get("applicable_content_product_type_ids")
        if not isinstance(component_id, str) or not isinstance(cp_ids, list):
            add_error(errors, "E_SOURCE_COMPONENT_SCHEMA", str(component_id))
            continue
        for cp_id in cp_ids:
            if not isinstance(cp_id, str) or (component_id, cp_id) in edge_set:
                add_error(errors, "E_SOURCE_COMPONENT_EDGE", str(component_id))
                continue
            edge_set.add((component_id, cp_id))
    if len(edge_set) != 543:
        add_error(errors, "E_SOURCE_EDGE_COUNT", str(len(edge_set)))
    return {
        "clean_by_id": clean_by_id,
        "route_input_by_id": route_input_by_id,
        "route_actual_by_id": route_actual_by_id,
        "component_by_id": component_by_id,
        "edge_set": edge_set,
    }


def validate_standard(root: Path, errors: list[dict[str, str]]) -> None:
    snapshot = root / STANDARD_SNAPSHOT_PATH
    contract_path = root / STANDARD_CONTRACT_PATH
    if not snapshot.exists() or sha256_file(snapshot) != STANDARD_SHA256:
        add_error(errors, "E_STANDARD_SNAPSHOT", STANDARD_SNAPSHOT_PATH.as_posix())
    try:
        contract = load_yaml(contract_path).get("gate1_v1_1_standard_contract")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_STANDARD_CONTRACT", str(exc))
        return
    if not isinstance(contract, dict):
        add_error(errors, "E_STANDARD_CONTRACT", "root missing")
        return
    expected = {
        "standard_version": "v1.1",
        "source_sha256": STANDARD_SHA256,
        "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            add_error(errors, "E_STANDARD_CONTRACT", f"{key}={contract.get(key)}")
    targets = contract.get("first_gate_targets")
    if targets != {
        "positive_parent_content_target": 240,
        "route_case_target": 60,
        "total_case_target": 300,
        "content_product_count": 20,
    }:
        add_error(errors, "E_STANDARD_TARGETS", str(targets))
    if contract.get("contract_digest") != object_digest(contract, "contract_digest"):
        add_error(errors, "E_STANDARD_CONTRACT_DIGEST", "mismatch")


def validate_baseline_manifest(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        manifest = load_yaml(root / BASELINE_MANIFEST_PATH).get(
            "gate1_input_baseline_manifest"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_BASELINE_MANIFEST", str(exc))
        return
    if not isinstance(manifest, dict):
        add_error(errors, "E_BASELINE_MANIFEST", "root missing")
        return
    if (
        manifest.get("task_id") != TASK_ID
        or manifest.get("baseline_commit") != BASELINE_COMMIT
    ):
        add_error(errors, "E_BASELINE_MANIFEST", "task or commit mismatch")
    anchor = manifest.get("anchor_report")
    if (
        not isinstance(anchor, dict)
        or anchor.get("after_p1a_policy_correction_sha256")
        != REPORT_AFTER_POLICY_SHA256
    ):
        add_error(errors, "E_BASELINE_REPORT", str(anchor))
    inputs = manifest.get("review_inputs")
    expected = {
        "legacy_reference_content": (CLEAN_120_PATH.as_posix(), CLEAN_120_SHA256, 120),
        "route_input_cases": (ROUTE_INPUT_PATH.as_posix(), ROUTE_INPUT_SHA256, 60),
        "route_actual_records": (ROUTE_ACTUAL_PATH.as_posix(), ROUTE_ACTUAL_SHA256, 60),
        "component_candidates": (
            COMPONENT_SOURCE_PATH.as_posix(),
            COMPONENT_SOURCE_SHA256,
            86,
        ),
    }
    if not isinstance(inputs, dict):
        add_error(errors, "E_BASELINE_INPUTS", "missing")
    else:
        for key, (path, digest, count) in expected.items():
            item = inputs.get(key)
            if not isinstance(item, dict) or (
                item.get("path"),
                item.get("sha256"),
                item.get("count"),
            ) != (path, digest, count):
                add_error(errors, "E_BASELINE_INPUTS", key)
        route_actual = inputs.get("route_actual_records")
        if (
            not isinstance(route_actual, dict)
            or route_actual.get("excluded_from_blind_review_packet") is not True
            or route_actual.get(
                "comparison_allowed_only_after_signed_independent_determination"
            )
            is not True
        ):
            add_error(
                errors, "E_ROUTE_BLINDNESS", "baseline route actual release policy"
            )
    boundary = manifest.get("p1a_boundary")
    if not isinstance(boundary, dict) or any(
        boundary.get(key) not in (False, "NOT_FROZEN")
        for key in (
            "review_decisions_created",
            "counted_positive_parent_count",
            "component_dispositions_created",
            "route_gold_answers_created",
        )
    ):
        add_error(errors, "E_REVIEW_DECISION", "baseline manifest boundary")
    if manifest.get("manifest_digest") != object_digest(manifest, "manifest_digest"):
        add_error(errors, "E_BASELINE_MANIFEST_DIGEST", "mismatch")


def validate_review_packet(
    root: Path, source: dict[str, Any], errors: list[dict[str, str]]
) -> None:
    try:
        rows = [row for row, _ in read_jsonl(root / REVIEW_PACKET_PATH)]
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_REVIEW_PACKET", str(exc))
        return
    if len(rows) != 266:
        add_error(errors, "E_REVIEW_PACKET_COUNT", str(len(rows)))
        return
    packet_ids = [row.get("packet_item_id") for row in rows]
    if len(set(packet_ids)) != 266 or any(
        not isinstance(item, str) for item in packet_ids
    ):
        add_error(errors, "E_REVIEW_PACKET_IDS", "duplicate or missing")
    by_type = Counter(row.get("object_type") for row in rows)
    if by_type != Counter(
        {
            "LEGACY_REFERENCE_CONTENT": 120,
            "ROUTE_CASE": 60,
            "COMPONENT_CANDIDATE": 86,
        }
    ):
        add_error(errors, "E_REVIEW_PACKET_TYPES", str(dict(by_type)))
    clean_seen: set[str] = set()
    route_seen: set[str] = set()
    component_seen: set[str] = set()
    for row in rows:
        packet_strings = recursively_find_strings(row)
        forbidden_route_leakage = {
            "observed_implementation_record",
            "current_implementation_record",
            "actual_decision",
            "implementation_result",
            ROUTE_ACTUAL_PATH.as_posix(),
            ROUTE_ACTUAL_SHA256,
        }
        if forbidden_route_leakage.intersection(packet_strings):
            add_error(errors, "E_ROUTE_BLINDNESS", str(row.get("packet_item_id")))
        review_state = row.get("review_state")
        if review_state != "PENDING_INDEPENDENT_REVIEW":
            add_error(errors, "E_REVIEW_DECISION", str(row.get("packet_item_id")))
        object_type = row.get("object_type")
        object_id = row.get("object_id")
        if not isinstance(object_id, str):
            add_error(errors, "E_REVIEW_PACKET_SCHEMA", str(row.get("packet_item_id")))
            continue
        if object_type == "LEGACY_REFERENCE_CONTENT":
            record = row.get("source")
            expected = source["clean_by_id"].get(object_id)
            if (
                not isinstance(record, dict)
                or record.get("path") != CLEAN_120_PATH.as_posix()
                or record.get("locator") != f"{CLEAN_120_PATH}#{object_id}"
                or record.get("record_sha256") != expected
                or row.get("may_count_toward_positive_240_before_p1b") is not False
            ):
                add_error(errors, "E_REVIEW_PACKET_SOURCE", object_id)
            clean_seen.add(object_id)
        elif object_type == "ROUTE_CASE":
            input_record = row.get("input_source")
            if (
                not isinstance(input_record, dict)
                or input_record.get("path") != ROUTE_INPUT_PATH.as_posix()
                or input_record.get("locator") != f"{ROUTE_INPUT_PATH}#{object_id}"
                or input_record.get("record_sha256")
                != source["route_input_by_id"].get(object_id)
            ):
                add_error(errors, "E_REVIEW_PACKET_ROUTE", object_id)
            route_seen.add(object_id)
        elif object_type == "COMPONENT_CANDIDATE":
            record = row.get("source")
            if (
                not isinstance(record, dict)
                or record.get("path") != COMPONENT_SOURCE_PATH.as_posix()
                or record.get("locator") != f"{COMPONENT_SOURCE_PATH}#{object_id}"
                or record.get("record_sha256")
                != source["component_by_id"].get(object_id)
                or row.get("may_be_consumed_by_new_generator") is not False
            ):
                add_error(errors, "E_REVIEW_PACKET_SOURCE", object_id)
            component_seen.add(object_id)
    if clean_seen != set(source["clean_by_id"]):
        add_error(errors, "E_REVIEW_PACKET_COVERAGE", "legacy content")
    if route_seen != set(source["route_input_by_id"]):
        add_error(errors, "E_REVIEW_PACKET_COVERAGE", "route cases")
    if component_seen != set(source["component_by_id"]):
        add_error(errors, "E_REVIEW_PACKET_COVERAGE", "components")


def validate_review_identity_set(
    reviewer_records: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    """Validate the identity separation P1B must apply to a review record set."""

    primary = reviewer_records.get("PRIMARY_CONTENT_VALUE")
    secondary = reviewer_records.get("SECONDARY_FACT_AUTHORIZATION")
    if not isinstance(primary, dict) or not isinstance(secondary, dict):
        add_error(
            errors, "E_REVIEWER_IDENTITY_COLLISION", "primary or secondary missing"
        )
        return
    distinct_fields = (
        "reviewer_identity_id",
        "reviewer_instance_or_session_id",
        "review_run_id",
        "append_only_signature_or_attestation",
    )
    for field in distinct_fields:
        primary_value = primary.get(field)
        secondary_value = secondary.get(field)
        if (
            not isinstance(primary_value, str)
            or not isinstance(secondary_value, str)
            or primary_value == secondary_value
        ):
            add_error(
                errors, "E_REVIEWER_IDENTITY_COLLISION", f"primary/secondary:{field}"
            )
    adjudicator = reviewer_records.get("INDEPENDENT_ADJUDICATION")
    if adjudicator is not None:
        if not isinstance(adjudicator, dict):
            add_error(errors, "E_REVIEWER_IDENTITY_COLLISION", "adjudicator schema")
            return
        for field in distinct_fields:
            adjudicator_value = adjudicator.get(field)
            if not isinstance(adjudicator_value, str) or adjudicator_value in {
                primary.get(field),
                secondary.get(field),
            }:
                add_error(
                    errors, "E_REVIEWER_IDENTITY_COLLISION", f"adjudicator:{field}"
                )


def validate_scoring_contract_binding(value: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, dict):
        add_error(errors, "E_SCORING_CONTRACT", "missing")
        return
    expected = {
        "positive_content": ("formula", "70_PLUS_30_EQUALS_100"),
        "component_candidate": ("formula", "80_PLUS_20_EQUALS_100"),
        "route_case": ("formula", "HARD_PRIMARY_ACTION_AND_REASON_CODE"),
    }
    for key, (field, expected_value) in expected.items():
        item = value.get(key)
        if not isinstance(item, dict) or item.get(field) != expected_value:
            add_error(errors, "E_SCORING_CONTRACT", key)
    route = value.get("route_case")
    summary = value.get("review_delivery_summary")
    if (
        not isinstance(route, dict)
        or route.get("per_record_percentage_forbidden") is not True
        or not isinstance(summary, dict)
        or summary.get("independent_coordinator_score_out_of") != 100
        or summary.get("is_not_a_substitute_for_object_level_decision") is not True
        or value.get("high_score_may_not_override_hard_veto") is not True
        or not isinstance(value.get("separation_required"), list)
        or set(value["separation_required"])
        != {
            "total_score",
            "hard_gate",
            "veto",
            "grade",
            "disposition",
            "lifecycle_status",
        }
    ):
        add_error(errors, "E_SCORING_CONTRACT", "decision separation")


def validate_review_contract(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        contract = load_yaml(root / REVIEW_CONTRACT_PATH).get(
            "independent_review_contract"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_REVIEW_CONTRACT", str(exc))
        return
    if not isinstance(contract, dict):
        add_error(errors, "E_REVIEW_CONTRACT", "root missing")
        return
    policy = contract.get("reviewer_identity_policy")
    required_policy = {
        "reviewer_may_be_ai_or_human": True,
        "distinct_reviewer_identity_id_required": True,
        "isolated_instance_or_session_required": True,
        "independent_run_and_signature_record_required": True,
        "blind_to_other_review_before_own_conclusion": True,
        "primary_and_secondary_pairwise_distinct_required": True,
        "adjudicator_pairwise_distinct_from_primary_and_secondary_when_triggered": True,
        "may_not_equal_content_author": True,
        "may_not_equal_p1a_packet_builder": True,
        "may_not_equal_p1b_freezer": True,
    }
    if not isinstance(policy, dict) or any(
        policy.get(key) != value for key, value in required_policy.items()
    ):
        add_error(errors, "E_REVIEW_IDENTITY_POLICY", str(policy))
    if not isinstance(policy, dict) or policy.get(
        "pairwise_distinct_record_fields"
    ) != [
        "reviewer_identity_id",
        "reviewer_instance_or_session_id",
        "review_run_id",
        "append_only_signature_or_attestation",
    ]:
        add_error(errors, "E_REVIEW_IDENTITY_POLICY", "pairwise record fields")
    roles = contract.get("roles")
    if not isinstance(roles, dict):
        add_error(errors, "E_REVIEW_ROLES", "missing")
    else:
        primary = roles.get("PRIMARY_CONTENT_VALUE")
        if (
            not isinstance(primary, dict)
            or primary.get("coverage")
            != "APPLICABLE_POSITIVE_FIRST_OUTPUTS_100_PERCENT"
        ):
            add_error(errors, "E_REVIEW_COVERAGE", str(primary))
        secondary = roles.get("SECONDARY_FACT_AUTHORIZATION")
        if (
            not isinstance(secondary, dict)
            or secondary.get("minimum_review_count") != 48
            or secondary.get("minimum_per_content_product") != 2
        ):
            add_error(errors, "E_REVIEW_COVERAGE", str(secondary))
        adjudicator = roles.get("INDEPENDENT_ADJUDICATION")
        if (
            not isinstance(adjudicator, dict)
            or adjudicator.get("required_when")
            != "PRIMARY_AND_SECONDARY_CONCLUSIONS_CONFLICT"
            or adjudicator.get("may_not_be_p1a_builder_or_p1b_freezer") is not True
        ):
            add_error(errors, "E_REVIEW_ROLES", str(adjudicator))
    standard_binding = contract.get("repository_standard_binding")
    if not isinstance(standard_binding, dict) or standard_binding != {
        "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
        "snapshot_sha256": STANDARD_SHA256,
        "positive_content_scoring": "70_PLUS_30_EQUALS_100",
        "component_scoring": "80_PLUS_20_EQUALS_100",
        "route_scoring": "HARD_PRIMARY_ACTION_AND_REASON_CODE_NO_PER_RECORD_PERCENTAGE",
    }:
        add_error(errors, "E_SCORING_CONTRACT", "repository standard binding")
    validate_scoring_contract_binding(
        contract.get("scoring_and_decision_contract"), errors
    )
    route_sequence = contract.get("route_blind_review_sequence")
    expected_route_actual = {
        "path": ROUTE_ACTUAL_PATH.as_posix(),
        "sha256": ROUTE_ACTUAL_SHA256,
        "p1b_only_after_signed_determination": True,
    }
    if (
        not isinstance(route_sequence, dict)
        or route_sequence.get(
            "blind_packet_may_not_contain_current_implementation_locator_or_digest"
        )
        is not True
        or route_sequence.get("first_submission_required_before_actual_comparison")
        is not True
        or route_sequence.get("current_actual_source") != expected_route_actual
        or route_sequence.get("required_signed_determination_fields")
        != [
            "primary_action",
            "reason_code",
            "evidence_refs",
            "append_only_record_digest",
        ]
    ):
        add_error(errors, "E_ROUTE_BLINDNESS", str(route_sequence))
    disagreement = contract.get("disagreement_policy")
    expected_disagreement = {
        "original_conclusions_and_evidence_append_only": True,
        "independent_adjudication_required_on_conflict": True,
        "silent_intersection_forbidden": True,
        "average_forbidden": True,
        "overwrite_forbidden": True,
    }
    if disagreement != expected_disagreement:
        add_error(errors, "E_DISAGREEMENT_POLICY", str(disagreement))
    channel_boundary = contract.get("creative_channel_boundary")
    expected_channel_boundary = {
        "review_roles": [
            "PRIMARY_CONTENT_VALUE",
            "SECONDARY_FACT_AUTHORIZATION",
            "INDEPENDENT_ADJUDICATION",
        ],
        "review_role_may_not_be_mapped_to_generation_lane": True,
        "historical_b_channel_is_not_generation_lane_evidence": True,
        "source_generation_lane_or_pair_ref_only_if_source_carries_it": True,
        "source_generation_lane_or_pair_ref_fabrication_forbidden": True,
        "optional_lane_applicability_nonblocking": True,
        "optional_lane_applicability_not_approval_evidence": True,
        "default_lane_applicability_without_source_evidence": "NOT_APPLICABLE",
        "p1a_may_not_assert_dual_channel_qualified": True,
        "p2_to_p6_must_preserve_dual_channel_requirement": True,
    }
    if channel_boundary != expected_channel_boundary:
        add_error(errors, "E_LANE_BOUNDARY", str(channel_boundary))
    prohibitions = contract.get("p1a_prohibitions")
    if not isinstance(prohibitions, dict) or any(
        value is not False for value in prohibitions.values()
    ):
        add_error(errors, "E_REVIEW_DECISION", "contract p1a boundary")
    if contract.get("contract_digest") != object_digest(contract, "contract_digest"):
        add_error(errors, "E_REVIEW_CONTRACT_DIGEST", "mismatch")


def validate_review_record_template(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        template = load_yaml(root / REVIEW_RECORD_TEMPLATE_PATH).get(
            "unified_independent_review_record_template"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_REVIEW_TEMPLATE", str(exc))
        return
    if not isinstance(template, dict):
        add_error(errors, "E_REVIEW_TEMPLATE", "root missing")
        return
    standard = template.get("standard_binding")
    if not isinstance(standard, dict) or standard != {
        "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
        "snapshot_sha256": STANDARD_SHA256,
        "content_formula": "70_PLUS_30_EQUALS_100",
        "component_formula": "80_PLUS_20_EQUALS_100",
        "route_formula": "HARD_PRIMARY_ACTION_AND_REASON_CODE_NO_PER_RECORD_PERCENTAGE",
    }:
        add_error(errors, "E_SCORING_CONTRACT", "template standard binding")
    object_record = template.get("object")
    reviewer = template.get("reviewer")
    evaluation = template.get("evidence_and_evaluation")
    disagreement = template.get("disagreement")
    required_top_level = {
        "schema_version": "v0.1",
        "template_status": "BLANK_TEMPLATE_NO_REVIEW_DECISION",
        "task_id": TASK_ID,
        "contract_path": REVIEW_CONTRACT_PATH.as_posix(),
    }
    if any(template.get(key) != value for key, value in required_top_level.items()):
        add_error(errors, "E_REVIEW_TEMPLATE", "top level")
    if (
        not isinstance(object_record, dict)
        or object_record.get("source_generation_lane_or_pair_ref") is not None
        or object_record.get("optional_lane_applicability") is not None
        or not isinstance(reviewer, dict)
        or any(value is not None for value in reviewer.values())
        or not isinstance(evaluation, dict)
        or evaluation.get("conclusion") is not None
        or evaluation.get("disposition") is not None
        or not isinstance(disagreement, dict)
        or disagreement.get("adjudication_conclusion") is not None
        or disagreement.get("final_disposition") is not None
    ):
        add_error(errors, "E_REVIEW_TEMPLATE", "must remain blank")
    if template.get("template_digest") != object_digest(template, "template_digest"):
        add_error(errors, "E_REVIEW_TEMPLATE_DIGEST", "mismatch")


def validate_legacy_edges(
    root: Path, source: dict[str, Any], errors: list[dict[str, str]]
) -> None:
    try:
        rows = [row for row, _ in read_jsonl(root / LEGACY_EDGE_MANIFEST_PATH)]
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_LEGACY_EDGE_MANIFEST", str(exc))
        return
    if len(rows) != 543:
        add_error(errors, "E_LEGACY_EDGE_COUNT", str(len(rows)))
        return
    seen: set[tuple[str, str]] = set()
    for row in rows:
        component_id = row.get("component_id")
        cp_id = row.get("content_product_type_id")
        edge = (component_id, cp_id)
        if (
            not isinstance(component_id, str)
            or not isinstance(cp_id, str)
            or edge in seen
        ):
            add_error(errors, "E_LEGACY_EDGE_SCHEMA", str(edge))
            continue
        seen.add(edge)
        if (
            row.get("relationship_lifecycle") != "HISTORICAL_UNREVIEWED_NON_ACTIVE"
            or row.get("review_state") != "PENDING_INDEPENDENT_REVIEW"
            or row.get("new_generator_consumable") is not False
            or row.get("active_edge_claimed") is not False
        ):
            add_error(errors, "E_LEGACY_EDGE_ACTIVE", str(edge))
        record = row.get("source")
        if (
            not isinstance(record, dict)
            or record.get("path") != COMPONENT_SOURCE_PATH.as_posix()
            or record.get("locator") != f"{COMPONENT_SOURCE_PATH}#{component_id}"
            or record.get("record_sha256")
            != source["component_by_id"].get(component_id)
        ):
            add_error(errors, "E_LEGACY_EDGE_SOURCE", str(edge))
    if seen != source["edge_set"]:
        add_error(errors, "E_LEGACY_EDGE_COVERAGE", str(len(seen)))


def validate_result(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        result = load_yaml(root / RESULT_PATH).get(
            "p1a_standard_baseline_preflight_result"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_RESULT", str(exc))
        return
    if not isinstance(result, dict):
        add_error(errors, "E_RESULT", "root missing")
        return
    if result.get("execution_status") != "PASS_PENDING_INDEPENDENT_REVIEWS":
        add_error(errors, "E_RESULT", str(result.get("execution_status")))
    boundary = result.get("review_decision_boundary")
    if (
        not isinstance(boundary, dict)
        or boundary.get("review_decisions_created") is not False
        or boundary.get("counted_positive_parent_count") != "NOT_FROZEN"
    ):
        add_error(errors, "E_REVIEW_DECISION", "result boundary")
    readiness = result.get("readiness")
    if not isinstance(readiness, dict) or recursively_find_true(readiness, READY_KEYS):
        add_error(errors, "E_READINESS", str(readiness))
    impact = result.get("core_number_impact")
    if impact != {
        "target_total": 300,
        "legacy_reference_content": 120,
        "component_candidates": 86,
        "all_unchanged": True,
    }:
        add_error(errors, "E_CORE_NUMBERS", str(impact))
    if result.get("result_digest") != object_digest(result, "result_digest"):
        add_error(errors, "E_RESULT_DIGEST", "mismatch")


def validate_owner(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        owner = load_yaml(root / CURRENT_OWNER_PATH).get("current_gate1_owner")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_OWNER_POLICY", str(exc))
        return
    if not isinstance(owner, dict):
        add_error(errors, "E_OWNER_POLICY", "root missing")
        return
    p1b_owner = owner.get("task_id") == P1B_TASK_ID
    expected = (
        {
            "task_id": P1B_TASK_ID,
            "baseline_commit": P1B_BASELINE_COMMIT,
            "current_task_root": P1B_TASK_ROOT.as_posix(),
            "current_checker": "ci/checkers/check_gate1_v1_1_current.py",
        }
        if p1b_owner
        else {
            "task_id": TASK_ID,
            "baseline_commit": BASELINE_COMMIT,
            "current_task_root": TASK_ROOT.as_posix(),
            "current_checker": "ci/checkers/check_gate1_v1_1_current.py",
        }
    )
    if any(owner.get(key) != value for key, value in expected.items()):
        add_error(errors, "E_OWNER_POLICY", "task binding")
    protected_inputs = owner.get("protected_inputs")
    expected_inputs = {
        "clean_120_source": CLEAN_120_PATH.as_posix(),
        "route_input_source": ROUTE_INPUT_PATH.as_posix(),
        "route_actual_source": ROUTE_ACTUAL_PATH.as_posix(),
        "component_source": COMPONENT_SOURCE_PATH.as_posix(),
    }
    if not isinstance(protected_inputs, dict) or any(
        protected_inputs.get(key) != value for key, value in expected_inputs.items()
    ):
        add_error(errors, "E_OWNER_POLICY", "protected inputs")
    if p1b_owner:
        p1a_protection = owner.get("p1a_as_built_protection")
        closeout = owner.get("p1b_closeout")
        if (
            not isinstance(p1a_protection, dict)
            or p1a_protection.get("p1a_current_checker_as_built_sha256")
            != P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
            or p1a_protection.get("p1a_generated_outputs_must_remain_byte_identical")
            is not True
            or not isinstance(closeout, dict)
            or closeout.get("result_state") != "STOPPED_COMPONENT_SUPPLY_GAP"
            or closeout.get("counted_positive_parent_count") != 29
            or closeout.get("active_component_count") != 0
            or closeout.get("p2_allowed_by_p1b") is not False
        ):
            add_error(errors, "E_OWNER_POLICY", "p1b closeout binding")
    authority = owner.get("current_ledger_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("shared_horizon_modified") is not False
        or authority.get("terminal_derivation") != "delegated_to_existing_owner"
    ):
        add_error(errors, "E_OWNER_POLICY", "ledger authority")
    if recursively_find_true(owner.get("readiness"), READY_KEYS):
        add_error(errors, "E_READINESS", "owner")


def validate_compatibility_receipt(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        receipt = load_yaml(root / COMPAT_RECEIPT_PATH).get(
            "governance_compatibility_repair_receipt"
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_COMPAT_RECEIPT", str(exc))
        return
    if not isinstance(receipt, dict):
        add_error(errors, "E_COMPAT_RECEIPT", "root missing")
        return
    checkers = receipt.get("modified_live_checkers")
    expected_before = {
        B24_CHECKER_PATH.as_posix(): B24_CHECKER_BEFORE_SHA256,
        SUCCESSOR_CHECKER_PATH.as_posix(): SUCCESSOR_CHECKER_BEFORE_SHA256,
    }
    if (
        receipt.get("modified_live_checker_count") != 2
        or not isinstance(checkers, list)
        or len(checkers) != 2
    ):
        add_error(errors, "E_COMPAT_RECEIPT", "modified checker count")
    else:
        seen: set[str] = set()
        for item in checkers:
            if not isinstance(item, dict):
                add_error(errors, "E_COMPAT_RECEIPT", "checker item")
                continue
            path_value = item.get("path")
            if not isinstance(path_value, str):
                add_error(errors, "E_COMPAT_RECEIPT", "checker path")
                continue
            seen.add(path_value)
            relative = Path(path_value)
            if (
                item.get("sha256_before") != expected_before.get(path_value)
                or not (root / relative).exists()
                or item.get("sha256_after") != sha256_file(root / relative)
                or not isinstance(item.get("negative_injection_proof"), dict)
            ):
                add_error(errors, "E_COMPAT_RECEIPT", path_value)
        if seen != set(expected_before):
            add_error(errors, "E_COMPAT_RECEIPT", "modified checker paths")
    current = receipt.get("new_current_checker")
    if (
        not isinstance(current, dict)
        or current.get("path") != "ci/checkers/check_gate1_v1_1_current.py"
        or current.get("sha256") != P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
    ):
        add_error(errors, "E_COMPAT_RECEIPT", "new checker")
    v1_repair = receipt.get("v1_current_checker_repair")
    expected_v1_repair_proof = {
        "command": "python3 ci/checkers/check_gate1_v1_1_current.py --selftest",
        "must_reject": [
            "route actual leakage into blind packet",
            "same reviewer identity or session/run/signature",
            "missing scoring contract",
            "review role mapped to generation lane",
        ],
    }
    if (
        not isinstance(v1_repair, dict)
        or v1_repair.get("path") != "ci/checkers/check_gate1_v1_1_current.py"
        or v1_repair.get("sha256_before") != CURRENT_GATE1_CHECKER_V1_BEFORE_SHA256
        or v1_repair.get("sha256_after") != P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
        or v1_repair.get("negative_injection_proof") != expected_v1_repair_proof
    ):
        add_error(errors, "E_COMPAT_RECEIPT", "v1 current checker repair")
    if (
        receipt.get("shared_ledger_or_horizon_modified") is not False
        or receipt.get("historical_allowlist_expanded") is not False
    ):
        add_error(errors, "E_COMPAT_RECEIPT", "shared authority boundary")
    if receipt.get("receipt_digest") != object_digest(receipt, "receipt_digest"):
        add_error(errors, "E_COMPAT_RECEIPT_DIGEST", "mismatch")


def validate_repair_shape(root: Path, errors: list[dict[str, str]]) -> None:
    b24_text = (root / B24_CHECKER_PATH).read_text(encoding="utf-8")
    successor_text = (root / SUCCESSOR_CHECKER_PATH).read_text(encoding="utf-8")
    if (
        "validate_current_write_surface" in b24_text
        or "CURRENT_ALLOWED_EXACT_PATHS" in b24_text
    ):
        add_error(errors, "E_REPAIR_SCOPE", "B24 still owns current write surface")
    if (
        "CURRENT_LEDGER_OWNER_CHECKER" not in successor_text
        or "CURRENT_B_CHANNEL_CHECKER" in successor_text
    ):
        add_error(errors, "E_REPAIR_SCOPE", "successor has not delegated current owner")
    if (
        "HISTORICAL_ROUTE_DIGESTS_19_33" not in successor_text
        or '"E_ROUTE34"' in successor_text
    ):
        add_error(errors, "E_REPAIR_SCOPE", "successor historical scope missing")


def validate_report(root: Path, errors: list[dict[str, str]]) -> None:
    path = root / REPORT_PATH
    if not path.exists() or sha256_file(path) != REPORT_AFTER_POLICY_SHA256:
        add_error(errors, "E_REPORT_ANCHOR", REPORT_PATH.as_posix())
        return
    report = path.read_text(encoding="utf-8")
    required_phrases = (
        "AI 审查可以计入正式审查",
        "身份隔离审查",
        "第二专家至少 48 条且每个 CP 至少 2 条",
        "八份实际执行指令",
        "全部旧关系标 historical/non-active",
        "甲／乙是后续创作与资格测试的质量要求，不是两份审查职责",
        "P2 至 P6 必须继续承接",
    )
    if any(phrase not in report for phrase in required_phrases):
        add_error(errors, "E_REPORT_POLICY", "required policy phrase missing")
    forbidden_phrases = (
        "543 条",
        "654 个槽位",
        "68 个 authorization-like",
        "887 个案例",
        "七份执行 Prompt",
        "3_to_6",
        "3 至 6",
        "预计3..6",
    )
    if any(phrase in report for phrase in forbidden_phrases):
        add_error(errors, "E_REPORT_POLICY", "obsolete process metric retained")


def p1b_document(
    root: Path, relative_path: Path, key: str, errors: list[dict[str, str]]
) -> dict[str, Any] | None:
    try:
        value = load_yaml(root / relative_path).get(key)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_P1B_SCHEMA", f"{relative_path}:{exc}")
        return None
    if not isinstance(value, dict):
        add_error(errors, "E_P1B_SCHEMA", relative_path.as_posix())
        return None
    return value


def validate_p1b(
    root: Path, source: dict[str, Any] | None, errors: list[dict[str, str]]
) -> None:
    """Independently verify P1B's externally signed inputs and mechanical closeout."""

    required = (
        P1B_MATERIALIZER_PATH,
        P1B_IMPORT_MANIFEST_PATH,
        P1B_CONTRACT_PATH,
        P1B_NORMALIZED_PATH,
        P1B_CONTENT_PATH,
        P1B_CONTENT_GAPS_PATH,
        P1B_ROUTE_GOLD_PATH,
        P1B_ROUTE_FREEZE_PATH,
        P1B_ROUTE_COMPARISON_PATH,
        P1B_COMPONENT_PATH,
        P1B_ACTIVE_COMPONENTS_PATH,
        P1B_ACTIVE_EDGES_PATH,
        P1B_COMPONENT_GAPS_PATH,
        P1B_TEST_INPUTS_PATH,
        P1B_COMPAT_RECEIPT_PATH,
        P1B_RESULT_PATH,
    )
    for relative_path in required:
        if not (root / relative_path).exists():
            add_error(errors, "E_P1B_REQUIRED_FILE", relative_path.as_posix())
    if any(error["code"] == "E_P1B_REQUIRED_FILE" for error in errors):
        return

    for import_path, expected_hash in P1B_IMPORT_HASHES.items():
        path = root / P1B_TASK_ROOT / "imports" / import_path
        if not path.exists() or sha256_file(path) != expected_hash:
            add_error(errors, "E_P1B_IMPORT_HASH", import_path)

    import_manifest = p1b_document(
        root, P1B_IMPORT_MANIFEST_PATH, "signed_review_import_manifest", errors
    )
    contract = p1b_document(
        root, P1B_CONTRACT_PATH, "p1b_signed_review_closeout_contract", errors
    )
    content_gaps = p1b_document(
        root, P1B_CONTENT_GAPS_PATH, "reference_120_content_product_gap_matrix", errors
    )
    route_freeze = p1b_document(
        root, P1B_ROUTE_FREEZE_PATH, "route_60_gold_freeze_manifest", errors
    )
    component_gaps = p1b_document(
        root, P1B_COMPONENT_GAPS_PATH, "component_supply_gap_matrix", errors
    )
    test_inputs = p1b_document(
        root, P1B_TEST_INPUTS_PATH, "gate1_development_test_input_manifest", errors
    )
    compatibility = p1b_document(
        root, P1B_COMPAT_RECEIPT_PATH, "p1b_historical_identity_repair_receipt", errors
    )
    result = p1b_document(
        root, P1B_RESULT_PATH, "p1b_signed_review_closeout_result", errors
    )
    documents = (
        (import_manifest, "manifest_digest"),
        (contract, "contract_digest"),
        (content_gaps, "matrix_digest"),
        (route_freeze, "freeze_manifest_digest"),
        (component_gaps, "matrix_digest"),
        (test_inputs, "manifest_digest"),
        (compatibility, "receipt_digest"),
        (result, "result_digest"),
    )
    for document, digest_key in documents:
        if document is not None and document.get(digest_key) != object_digest(
            document, digest_key
        ):
            add_error(errors, "E_P1B_DOCUMENT_DIGEST", digest_key)
    if any(value is None for value, _ in documents):
        return
    if any(
        value is None
        for value in (
            import_manifest,
            contract,
            content_gaps,
            route_freeze,
            component_gaps,
            test_inputs,
            compatibility,
            result,
        )
    ):
        return

    entries = import_manifest.get("entries")
    if (
        import_manifest.get("task_id") != P1B_TASK_ID
        or import_manifest.get("external_review_count") != len(P1B_IMPORT_HASHES)
        or not isinstance(entries, list)
        or {
            entry.get("import_path"): entry.get("sha256")
            for entry in entries
            if isinstance(entry, dict)
        }
        != {f"imports/{path}": digest for path, digest in P1B_IMPORT_HASHES.items()}
    ):
        add_error(errors, "E_P1B_IMPORT_MANIFEST", "signed input set")
    if (
        contract.get("task_id") != P1B_TASK_ID
        or contract.get("fourth_review_forbidden") is not True
        or contract.get("input_model") != "THREE_SIGNED_REVIEW_STRUCTURES_ONLY"
        or recursively_find_true(contract.get("readiness"), READY_KEYS)
    ):
        add_error(errors, "E_P1B_CONTRACT", "closeout boundary")

    try:
        normalized_rows = read_jsonl(root / P1B_NORMALIZED_PATH)
        content_rows = read_jsonl(root / P1B_CONTENT_PATH)
        gold_rows = read_jsonl(root / P1B_ROUTE_GOLD_PATH)
        comparison_rows = read_jsonl(root / P1B_ROUTE_COMPARISON_PATH)
        component_rows = read_jsonl(root / P1B_COMPONENT_PATH)
        active_components = read_jsonl(root / P1B_ACTIVE_COMPONENTS_PATH)
        active_edges = read_jsonl(root / P1B_ACTIVE_EDGES_PATH)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "E_P1B_PARSE", str(exc))
        return
    normalized = [row for row, _ in normalized_rows]
    content = [row for row, _ in content_rows]
    gold = [row for row, _ in gold_rows]
    comparison = [row for row, _ in comparison_rows]
    components = [row for row, _ in component_rows]
    if (
        len(normalized) != 503
        or len({row.get("normalized_record_id") for row in normalized}) != 503
        or any(
            row.get("source_generation_lane_or_pair_ref") is not None
            or row.get("optional_lane_applicability") is not None
            for row in normalized
        )
    ):
        add_error(
            errors, "E_P1B_REVIEW_NORMALIZATION", "count, identity, or lane evidence"
        )
    if source is not None:
        content_ids = {row.get("asset_id") for row in content}
        counted_content = [
            row
            for row in content
            if row.get("final_disposition") == "COUNT_TOWARD_FINAL_300_POSITIVE"
        ]
        if (
            len(content) != 120
            or content_ids != set(source["clean_by_id"])
            or any(
                row.get("source_record_sha256")
                != source["clean_by_id"].get(row.get("asset_id"))
                for row in content
            )
            or len(counted_content) != 29
        ):
            add_error(errors, "E_P1B_CONTENT_CLOSEOUT", "120 disposition derivation")
        actual_rows = {
            row.get("case_id"): row
            for row, _ in read_jsonl(root / ROUTE_ACTUAL_PATH)
            if isinstance(row.get("case_id"), str)
        }
        if (
            len(gold) != 60
            or len({row.get("case_id") for row in gold}) != 60
            or len(comparison) != 60
            or len({row.get("case_id") for row in comparison}) != 60
            or set(row.get("case_id") for row in gold)
            != set(source["route_input_by_id"])
            or any(
                row.get("current_actual_record_sha256")
                != source["route_actual_by_id"].get(row.get("case_id"))
                for row in comparison
            )
            or any(
                not isinstance(actual_rows.get(row.get("case_id")), dict)
                or row.get("current_primary_action")
                != actual_rows[row["case_id"]]
                .get("actual_decision", {})
                .get("actual_primary_action")
                or row.get("current_primary_reason_code")
                != actual_rows[row["case_id"]]
                .get("actual_decision", {})
                .get("actual_primary_reason_code")
                or row.get("primary_action_matches_gold")
                != (row.get("gold_primary_action") == row.get("current_primary_action"))
                or row.get("primary_reason_matches_gold")
                != (
                    row.get("gold_reason_code")
                    == row.get("current_primary_reason_code")
                )
                for row in comparison
            )
        ):
            add_error(errors, "E_P1B_ROUTE_COMPARISON", "60 signed gold answers")
        if (
            len(components) != 86
            or {row.get("component_id") for row in components}
            != set(source["component_by_id"])
            or any(
                row.get("source_record_sha256")
                != source["component_by_id"].get(row.get("component_id"))
                for row in components
            )
            or any(
                row.get("final_disposition") == "KEEP_ACTIVE_FOR_GATE1_DEVELOPMENT_TEST"
                for row in components
            )
            or active_components
            or active_edges
        ):
            add_error(errors, "E_P1B_COMPONENT_CLOSEOUT", "86 candidate disposition")
    golden_text = (root / P1B_ROUTE_GOLD_PATH).read_text(encoding="utf-8")
    freeze_text = (root / P1B_ROUTE_FREEZE_PATH).read_text(encoding="utf-8")
    if (
        ROUTE_ACTUAL_PATH.as_posix() in golden_text
        or ROUTE_ACTUAL_SHA256 in golden_text
        or ROUTE_ACTUAL_PATH.as_posix() in freeze_text
        or ROUTE_ACTUAL_SHA256 in freeze_text
        or route_freeze.get("gold_answers_sha256")
        != sha256_file(root / P1B_ROUTE_GOLD_PATH)
    ):
        add_error(
            errors, "E_P1B_ROUTE_BLINDNESS", "actual implementation leaked into gold"
        )
    if (
        content_gaps.get("counted_positive_parent_count") != 29
        or content_gaps.get("legacy_inventory_count") != 120
        or not isinstance(content_gaps.get("entries"), list)
        or len(content_gaps["entries"]) != 20
        or component_gaps.get("active_component_count") != 0
        or component_gaps.get("active_edge_count") != 0
        or component_gaps.get("complete_profile_count") != 0
        or component_gaps.get("incomplete_profile_count") != 20
        or not isinstance(component_gaps.get("entries"), list)
        or len(component_gaps["entries"]) != 20
    ):
        add_error(errors, "E_P1B_GAP_MATRIX", "content or component gap")
    if (
        test_inputs.get("component_count") != 0
        or test_inputs.get("edge_count") != 0
        or test_inputs.get("p2_input_eligible") is not False
        or recursively_find_true(test_inputs, READY_KEYS)
    ):
        add_error(errors, "E_P1B_TEST_INPUTS", "supply must remain unavailable")
    current_successor = compatibility.get("current_gate1_checker_successor")
    p1a_protection = compatibility.get("p1a_materializer_reference_safe_change")
    if (
        compatibility.get("modified_live_checker_count") != 1
        or compatibility.get("historical_assets_rewritten") is not False
        or not isinstance(current_successor, dict)
        or current_successor.get("sha256_after")
        != sha256_file(root / Path("ci/checkers/check_gate1_v1_1_current.py"))
        or not isinstance(p1a_protection, dict)
        or p1a_protection.get("historical_current_checker_sha256")
        != P1A_CURRENT_GATE1_CHECKER_AS_BUILT_SHA256
        or p1a_protection.get("p1a_generated_output_bytes_changed") is not False
    ):
        add_error(errors, "E_P1B_COMPATIBILITY", "historical identity protection")
    impact = result.get("core_number_impact")
    if (
        result.get("task_id") != P1B_TASK_ID
        or result.get("result_state") != "STOPPED_COMPONENT_SUPPLY_GAP"
        or result.get("p2_allowed") is not False
        or not isinstance(impact, dict)
        or impact.get("target_total") != 300
        or impact.get("legacy_reference_inventory") != 120
        or impact.get("counted_positive_parent_count") != 29
        or impact.get("component_candidate_inventory") != 86
        or impact.get("active_component_count") != 0
        or result.get("component_supply_incomplete_profile_count") != 20
        or recursively_find_true(result.get("readiness"), READY_KEYS)
    ):
        add_error(errors, "E_P1B_RESULT", "honest stop state")

    if root == ROOT:
        materializer = subprocess.run(
            [sys.executable, str(root / P1B_MATERIALIZER_PATH), "--check"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if materializer.returncode != 0:
            add_error(
                errors, "E_P1B_MATERIALIZER", materializer.stderr or materializer.stdout
            )


def validate(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = (
        CURRENT_OWNER_PATH,
        REPORT_PATH,
        STANDARD_SNAPSHOT_PATH,
        STANDARD_CONTRACT_PATH,
        BASELINE_MANIFEST_PATH,
        REVIEW_PACKET_PATH,
        REVIEW_CONTRACT_PATH,
        REVIEW_RECORD_TEMPLATE_PATH,
        LEGACY_EDGE_MANIFEST_PATH,
        COMPAT_RECEIPT_PATH,
        RESULT_PATH,
        B24_CHECKER_PATH,
        SUCCESSOR_CHECKER_PATH,
    )
    for relative_path in required:
        if not (root / relative_path).exists():
            add_error(errors, "E_REQUIRED_FILE", relative_path.as_posix())
    if errors:
        return errors
    validate_write_surface(root, errors)
    validate_report(root, errors)
    source = source_maps(root, errors)
    validate_standard(root, errors)
    validate_baseline_manifest(root, errors)
    if source is not None:
        validate_review_packet(root, source, errors)
        validate_legacy_edges(root, source, errors)
    validate_review_contract(root, errors)
    validate_review_record_template(root, errors)
    validate_result(root, errors)
    validate_owner(root, errors)
    validate_compatibility_receipt(root, errors)
    validate_repair_shape(root, errors)
    if (root / P1B_TASK_ROOT).exists():
        validate_p1b(root, source, errors)
    return errors


def copy_fixture(root: Path, target: Path) -> None:
    relative_paths = (
        CURRENT_OWNER_PATH,
        REPORT_PATH,
        CLEAN_120_PATH,
        ROUTE_INPUT_PATH,
        ROUTE_ACTUAL_PATH,
        COMPONENT_SOURCE_PATH,
        PROFILE_PATH,
        B24_CHECKER_PATH,
        SUCCESSOR_CHECKER_PATH,
        Path("ci/checkers/check_gate1_v1_1_current.py"),
    )
    for relative_path in relative_paths:
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative_path, destination)
    shutil.copytree(root / TASK_ROOT, target / TASK_ROOT)
    if (root / P1B_TASK_ROOT).exists():
        shutil.copytree(root / P1B_TASK_ROOT, target / P1B_TASK_ROOT)


def mutate_yaml(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    value = load_yaml(path)
    mutate(value)
    write_yaml(path, value)


def mutate_jsonl(path: Path, mutate: Callable[[list[dict[str, Any]]], None]) -> None:
    rows = [row for row, _ in read_jsonl(path)]
    mutate(rows)
    write_jsonl(path, rows)


def selftest(root: Path) -> int:
    tests: list[tuple[str, str, Callable[[Path], None]]] = [
        (
            "standard_snapshot_mutation",
            "E_STANDARD_SNAPSHOT",
            lambda temp: (temp / STANDARD_SNAPSHOT_PATH).write_bytes(
                (temp / STANDARD_SNAPSHOT_PATH).read_bytes() + b"\nmutation\n"
            ),
        ),
        (
            "active_legacy_edge",
            "E_LEGACY_EDGE_ACTIVE",
            lambda temp: mutate_jsonl(
                temp / LEGACY_EDGE_MANIFEST_PATH,
                lambda rows: rows[0].update({"new_generator_consumable": True}),
            ),
        ),
        (
            "review_decision_created",
            "E_REVIEW_DECISION",
            lambda temp: mutate_jsonl(
                temp / REVIEW_PACKET_PATH,
                lambda rows: rows[0].update({"review_state": "APPROVED"}),
            ),
        ),
        (
            "route_actual_leakage",
            "E_ROUTE_BLINDNESS",
            lambda temp: mutate_jsonl(
                temp / REVIEW_PACKET_PATH,
                lambda rows: rows[120].update(
                    {
                        "observed_implementation_record": {
                            "path": ROUTE_ACTUAL_PATH.as_posix(),
                            "record_sha256": ROUTE_ACTUAL_SHA256,
                        }
                    }
                ),
            ),
        ),
        (
            "missing_scoring_contract",
            "E_SCORING_CONTRACT",
            lambda temp: mutate_yaml(
                temp / REVIEW_CONTRACT_PATH,
                lambda value: value["independent_review_contract"].pop(
                    "scoring_and_decision_contract"
                ),
            ),
        ),
        (
            "review_role_mapped_to_lane",
            "E_LANE_BOUNDARY",
            lambda temp: mutate_yaml(
                temp / REVIEW_CONTRACT_PATH,
                lambda value: value["independent_review_contract"][
                    "creative_channel_boundary"
                ].update({"review_role_may_not_be_mapped_to_generation_lane": False}),
            ),
        ),
        (
            "historical_b_channel_auto_inference",
            "E_LANE_BOUNDARY",
            lambda temp: mutate_yaml(
                temp / REVIEW_CONTRACT_PATH,
                lambda value: value["independent_review_contract"][
                    "creative_channel_boundary"
                ].update(
                    {"historical_b_channel_is_not_generation_lane_evidence": False}
                ),
            ),
        ),
        (
            "readiness_flip",
            "E_READINESS",
            lambda temp: mutate_yaml(
                temp / RESULT_PATH,
                lambda value: value["p1a_standard_baseline_preflight_result"][
                    "readiness"
                ].update({"generation_allowed": True}),
            ),
        ),
        (
            "owner_shared_horizon_flip",
            "E_OWNER_POLICY",
            lambda temp: mutate_yaml(
                temp / CURRENT_OWNER_PATH,
                lambda value: value["current_gate1_owner"][
                    "current_ledger_authority"
                ].update({"shared_horizon_modified": True}),
            ),
        ),
        (
            "compatibility_receipt_prior_hash",
            "E_COMPAT_RECEIPT",
            lambda temp: mutate_yaml(
                temp / COMPAT_RECEIPT_PATH,
                lambda value: value["governance_compatibility_repair_receipt"][
                    "modified_live_checkers"
                ][0].update({"sha256_before": "0" * 64}),
            ),
        ),
    ]
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="gate1-p1a-checker-selftest-") as temporary:
        base = Path(temporary)
        for name, expected_code, mutate in tests:
            case_root = base / name
            copy_fixture(root, case_root)
            mutate(case_root)
            codes = {error["code"] for error in validate(case_root)}
            if expected_code not in codes:
                failures.append(
                    {"case": name, "expected": expected_code, "actual": sorted(codes)}
                )
    identity_errors: list[dict[str, str]] = []
    validate_review_identity_set(
        {
            "PRIMARY_CONTENT_VALUE": {
                "reviewer_identity_id": "same-agent",
                "reviewer_instance_or_session_id": "same-session",
                "review_run_id": "same-run",
                "append_only_signature_or_attestation": "same-signature",
            },
            "SECONDARY_FACT_AUTHORIZATION": {
                "reviewer_identity_id": "same-agent",
                "reviewer_instance_or_session_id": "same-session",
                "review_run_id": "same-run",
                "append_only_signature_or_attestation": "same-signature",
            },
        },
        identity_errors,
    )
    if "E_REVIEWER_IDENTITY_COLLISION" not in {
        error["code"] for error in identity_errors
    }:
        failures.append(
            {
                "case": "same_reviewer_identity",
                "expected": "E_REVIEWER_IDENTITY_COLLISION",
                "actual": sorted({error["code"] for error in identity_errors}),
            }
        )
    if not unexpected_write_paths({Path("outside_p1a/unapproved.txt")}):
        failures.append(
            {"case": "unauthorized_path", "expected": "E_WRITE_SURFACE", "actual": []}
        )
    if (root / P1B_MATERIALIZER_PATH).exists():
        p1b_selftest = subprocess.run(
            [sys.executable, str(root / P1B_MATERIALIZER_PATH), "--selftest"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if p1b_selftest.returncode != 0:
            failures.append(
                {
                    "case": "p1b_negative_tamper_suite",
                    "expected": "exit 0",
                    "actual": p1b_selftest.stderr or p1b_selftest.stdout,
                }
            )
    if failures:
        print(
            json.dumps(
                {"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "SELFTEST_PASS",
                "negative_case_count": len(tests) + 1,
                "unauthorized_write_surface_rejected": True,
                "review_decision_creation_rejected": True,
                "readiness_flip_rejected": True,
                "route_actual_leakage_rejected": True,
                "same_reviewer_identity_rejected": True,
                "missing_scoring_contract_rejected": True,
                "p1b_negative_tamper_suite_passed": (
                    root / P1B_MATERIALIZER_PATH
                ).exists(),
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest(ROOT)
    errors = validate(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "task_id": (
                    P1B_TASK_ID
                    if load_yaml(ROOT / CURRENT_OWNER_PATH)
                    .get("current_gate1_owner", {})
                    .get("task_id")
                    == P1B_TASK_ID
                    else TASK_ID
                ),
                "review_decisions_created": False,
                "shared_horizon_modified": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
