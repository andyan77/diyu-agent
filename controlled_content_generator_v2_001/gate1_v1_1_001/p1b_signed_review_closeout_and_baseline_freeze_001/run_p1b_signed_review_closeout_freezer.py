#!/usr/bin/env python3
"""Deterministically consume signed Gate 1 reviews without creating a fourth review."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml


if not __debug__:
    print("run_p1b_signed_review_closeout_freezer refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_SIGNED_REVIEW_CLOSEOUT_AND_BASELINE_FREEZE_001"
P1A_TASK_ID = "GATE1_V11_STANDARD_BASELINE_REVIEW_PACKET_AND_GOVERNANCE_PREFLIGHT_001"
P1B_FREEZER_IDENTITY = "P1B_DETERMINISTIC_SIGNED_REVIEW_FREEZER_V1"
P1A_BUILDER_IDENTITY = "P1A_DETERMINISTIC_PACKET_MATERIALIZER"
P1B_BASELINE_COMMIT = "01da326e4195b47e9b769b025bdf962936f10419"

P1A_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1a_standard_baseline_review_packet_and_governance_preflight_001"
)
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001"
)
CURRENT_OWNER_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml"
)
CURRENT_CHECKER_PATH = Path("ci/checkers/check_gate1_v1_1_current.py")
P1A_MATERIALIZER_PATH = P1A_ROOT / "run_p1a_standard_baseline_review_packet_freezer.py"

STANDARD_SNAPSHOT_PATH = P1A_ROOT / "standard/diyu_content_composition_standard.v1.1.md"
STANDARD_CONTRACT_PATH = P1A_ROOT / "standard/v1_1_standard_contract.v0.1.yaml"
REVIEW_CONTRACT_PATH = P1A_ROOT / "review/independent_review_contract.v0.1.yaml"
REVIEW_TEMPLATE_PATH = (
    P1A_ROOT / "review/unified_independent_review_record_template.v0.1.yaml"
)
REVIEW_PACKET_PATH = P1A_ROOT / "review/unified_gate1_review_packet.v0.1.jsonl"
BASELINE_MANIFEST_PATH = P1A_ROOT / "baseline/gate1_input_baseline_manifest.v0.1.yaml"

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

STANDARD_SHA256 = "022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542"
STANDARD_CONTRACT_SHA256 = (
    "cc5d447f86987c2df2cfb1ef801a48e925975e29b974b847de22ea8d0dea7e7d"
)
REVIEW_CONTRACT_SHA256 = (
    "dbe137cd7ed1af0a9001230ff6d40852b1b5ffeca97fc287d1efe844e9e04a0c"
)
REVIEW_TEMPLATE_SHA256 = (
    "509ae9700b062af30cd1803b93cebdc0b531918bfdd5ca5e4c4fbb7152d8669e"
)
REVIEW_PACKET_SHA256 = (
    "3790b629fb636ef33dbaad369896c1efb55709971c8a01ef2a60a99fa201d64f"
)
PROFILE_SHA256 = "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056"
CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
ROUTE_INPUT_SHA256 = "68bc65bff904652f1e565097117c7e8dfccdcc6ef00d2e3a0e93a082a4d72f12"
ROUTE_ACTUAL_SHA256 = "bb7d68686761b7be092f191a0f46cb7493a3947f98959703c3ccaa69a86de3ad"
COMPONENT_SOURCE_SHA256 = (
    "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601"
)
P1A_CURRENT_CHECKER_AS_BUILT_SHA256 = (
    "29a872dd08b13c02a776ca4b4074a419320667a97b6c16125ab03432626d3806"
)
P1B_CURRENT_CHECKER_AS_BUILT_SHA256 = (
    "6474966c8ea5d0fdb2c5d40cc5888969f5fc8ebb63f8006d61504a4aaae8e231"
)
P1B_CURRENT_OWNER_AS_BUILT_SHA256 = (
    "541443a9c5c34047fb5c9a4652412cc019218abd60d29528b57dbc1d771d637a"
)
P1A_MATERIALIZER_BEFORE_SHA256 = (
    "88468847d945db07eb00bad9cb70485af52ae10db5f08009920fa1a98ef5566d"
)

IMPORT_SOURCE_ROOT = Path(
    "/mnt/c/Users/Administrator/Documents/笛语agent/tasks/"
    "GATE1_V11_STANDARD_BASELINE_REVIEW_PACKET_AND_GOVERNANCE_PREFLIGHT_001"
)
IMPORT_ROOT = TASK_ROOT / "imports"
IMPORT_MANIFEST_PATH = IMPORT_ROOT / "signed_review_import_manifest.v0.1.yaml"
CONTRACT_PATH = TASK_ROOT / "contract/p1b_signed_review_closeout_contract.v0.1.yaml"
NORMALIZED_PATH = TASK_ROOT / "normalized/signed_review_records.v0.1.jsonl"
CONTENT_DISPOSITIONS_PATH = (
    TASK_ROOT / "content/reference_120_final_dispositions.v0.1.jsonl"
)
CONTENT_GAPS_PATH = (
    TASK_ROOT / "content/reference_120_content_product_gap_matrix.v0.1.yaml"
)
ROUTE_GOLD_PATH = TASK_ROOT / "route/route_60_gold_answers.v0.1.jsonl"
ROUTE_GOLD_FREEZE_PATH = TASK_ROOT / "route/route_60_gold_freeze_manifest.v0.1.yaml"
ROUTE_COMPARISON_PATH = (
    TASK_ROOT / "route/route_60_current_actual_comparison.v0.1.jsonl"
)
COMPONENT_DISPOSITIONS_PATH = (
    TASK_ROOT / "component/component_86_final_dispositions.v0.1.jsonl"
)
ACTIVE_COMPONENTS_PATH = (
    TASK_ROOT / "component/active_gate1_development_components.v0.1.jsonl"
)
ACTIVE_EDGES_PATH = TASK_ROOT / "component/active_gate1_development_edges.v0.1.jsonl"
COMPONENT_GAPS_PATH = TASK_ROOT / "component/component_supply_gap_matrix.v0.1.yaml"
TEST_INPUT_MANIFEST_PATH = (
    TASK_ROOT / "test_inputs/gate1_development_test_input_manifest.v0.1.yaml"
)
COMPAT_RECEIPT_PATH = (
    TASK_ROOT / "compatibility/p1b_historical_identity_repair_receipt.v0.1.yaml"
)
RESULT_PATH = TASK_ROOT / "result/p1b_signed_review_closeout_result.v0.1.yaml"

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

IMPORT_SPECS: tuple[tuple[Path, Path, str], ...] = (
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/review_job.v0.yaml",
        IMPORT_ROOT / "independent_reviews/review_job.v0.yaml",
        "511e203a464b7e57fdf2661abc7254f168c0da59c1631f618a861f3cf8f9192a",
    ),
    (
        IMPORT_SOURCE_ROOT
        / "independent_reviews/review_job_blindness_amendment.v0.yaml",
        IMPORT_ROOT / "independent_reviews/review_job_blindness_amendment.v0.yaml",
        "fa10da85ac4b380d426fc3ac896d56e832b2ff877001ff0d6767793f1f1861c1",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/review_session_invalidations.v0.yaml",
        IMPORT_ROOT / "independent_reviews/review_session_invalidations.v0.yaml",
        "5cb3c049ef8c99a4f89400a1c76b4383ae407f78d0d918603fff04d187583fcb",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/adjudication_assignment.v0.yaml",
        IMPORT_ROOT / "independent_reviews/adjudication_assignment.v0.yaml",
        "1cf4c1987af6a803baa741877bb51462e789b46341c9550040e8936e13a9a98b",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/primary/records.jsonl",
        IMPORT_ROOT / "independent_reviews/primary/records.jsonl",
        "fdaaff1355e3365fa51ecc26cac8d342f2c736b69cd2022ecf921ce339778a51",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/primary/report.md",
        IMPORT_ROOT / "independent_reviews/primary/report.md",
        "149bab88fdfca4203781ddb8aaee76897364bdca9ccd72ce2789f32ad3b7fe5c",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/primary/run_manifest.yaml",
        IMPORT_ROOT / "independent_reviews/primary/run_manifest.yaml",
        "801916ecf79b01023c2eec8b2d5e969565be6afe3f7c29e77dd61a7e5660a4c9",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/secondary/records.jsonl",
        IMPORT_ROOT / "independent_reviews/secondary/records.jsonl",
        "61586c7fce34baa59db1c179eeeae7214b6afebb3daa2282221e68e91f7e6b61",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/secondary/report.md",
        IMPORT_ROOT / "independent_reviews/secondary/report.md",
        "38ce8105b9e747eb0f26ceca15e8173da56143e99078a485414dcebd64f7a76c",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/secondary/run_manifest.yaml",
        IMPORT_ROOT / "independent_reviews/secondary/run_manifest.yaml",
        "07283675742cf0fd9900d6a5edc7b664071e4f4b603cb0a54786bd6ddf107bcb",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/adjudication/records.jsonl",
        IMPORT_ROOT / "independent_reviews/adjudication/records.jsonl",
        "47b88fd579f7fce70ed20f4a9ad43000f013019b5cbcf7e1338c04137e7c973c",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/adjudication/report.md",
        IMPORT_ROOT / "independent_reviews/adjudication/report.md",
        "940742b85805a8abe6cf495cb34a2095081507e863bd4bc8abe165b91084959a",
    ),
    (
        IMPORT_SOURCE_ROOT / "independent_reviews/adjudication/run_manifest.yaml",
        IMPORT_ROOT / "independent_reviews/adjudication/run_manifest.yaml",
        "c52eb752b9fd0ab38732e2504142c895da3e1c20b830d20f7650e1f8fb543d0b",
    ),
    (
        IMPORT_SOURCE_ROOT
        / "independent_reviews/coordinator_review_checkpoint_closeout.v0.md",
        IMPORT_ROOT
        / "independent_reviews/coordinator_review_checkpoint_closeout.v0.md",
        "5d68c5e2510e633bd25a6c076352727cdcd169bd2c1f452ae0acbd80454c72e2",
    ),
    (
        IMPORT_SOURCE_ROOT / "coordinator_expert_review.v1.md",
        IMPORT_ROOT / "coordinator_expert_review.v1.md",
        "6f1485cbbef84c52c546f171e7b1a49c5b87e2163d51a35e4a359e5b804bf6aa",
    ),
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
            raise ValueError(f"E_DUPLICATE_YAML_KEY:{key}")
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
    return sha256_bytes(
        canonical_json(
            {key: item for key, item in value.items() if key != digest_key}
        ).encode("utf-8")
    )


def yaml_bytes(value: dict[str, Any]) -> bytes:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120).encode(
        "utf-8"
    )


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"E_YAML_ROOT:{path}")
    return value


def read_jsonl(path: Path) -> list[tuple[dict[str, Any], str]]:
    rows: list[tuple[dict[str, Any], str]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line:
            continue
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            raise TypeError(f"E_JSONL_ROW:{path}:{line_number}")
        rows.append((value, raw_line))
    return rows


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise ValueError(f"{code}{suffix}")


def ensure_hash(path: Path, expected: str, code: str) -> None:
    require(path.exists(), code, path.as_posix())
    require(sha256_file(path) == expected, code, path.as_posix())


def deep_copy(value: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(value)


def set_nested(value: dict[str, Any], path: tuple[str, ...], replacement: Any) -> None:
    cursor: dict[str, Any] = value
    for key in path[:-1]:
        child = cursor.get(key)
        require(isinstance(child, dict), "E_SIGNED_RECORD_SCHEMA", ".".join(path))
        cursor = child
    cursor[path[-1]] = replacement


def record_digest(
    record: dict[str, Any], null_paths: tuple[tuple[str, ...], ...]
) -> str:
    copy_record = deep_copy(record)
    for path in null_paths:
        set_nested(copy_record, path, None)
    return sha256_bytes(canonical_json(copy_record).encode("utf-8"))


def record_digest_excluding(record: dict[str, Any], path: tuple[str, ...]) -> str:
    copy_record = deep_copy(record)
    cursor: dict[str, Any] = copy_record
    for key in path[:-1]:
        child = cursor.get(key)
        require(isinstance(child, dict), "E_SIGNED_RECORD_SCHEMA", ".".join(path))
        cursor = child
    cursor.pop(path[-1], None)
    return sha256_bytes(canonical_json(copy_record).encode("utf-8"))


def map_rows(
    rows: list[tuple[dict[str, Any], str]], key: str, code: str
) -> dict[str, tuple[dict[str, Any], str]]:
    result: dict[str, tuple[dict[str, Any], str]] = {}
    for row, raw_line in rows:
        value = row.get(key)
        require(
            isinstance(value, str) and value and value not in result, code, str(value)
        )
        result[value] = (row, raw_line)
    return result


def require_string(value: Any, code: str, detail: str) -> str:
    require(isinstance(value, str) and value, code, detail)
    return value


def recursively_find_true(value: Any) -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in READY_KEYS and child is True:
                matches.append(key)
            matches.extend(recursively_find_true(child))
    elif isinstance(value, list):
        for child in value:
            matches.extend(recursively_find_true(child))
    return matches


def source_state(root: Path) -> dict[str, Any]:
    frozen_hashes = {
        STANDARD_SNAPSHOT_PATH: STANDARD_SHA256,
        STANDARD_CONTRACT_PATH: STANDARD_CONTRACT_SHA256,
        REVIEW_CONTRACT_PATH: REVIEW_CONTRACT_SHA256,
        REVIEW_TEMPLATE_PATH: REVIEW_TEMPLATE_SHA256,
        REVIEW_PACKET_PATH: REVIEW_PACKET_SHA256,
        PROFILE_PATH: PROFILE_SHA256,
        CLEAN_120_PATH: CLEAN_120_SHA256,
        ROUTE_INPUT_PATH: ROUTE_INPUT_SHA256,
        ROUTE_ACTUAL_PATH: ROUTE_ACTUAL_SHA256,
        COMPONENT_SOURCE_PATH: COMPONENT_SOURCE_SHA256,
    }
    for path, digest in frozen_hashes.items():
        ensure_hash(root / path, digest, "E_FROZEN_INPUT_DRIFT")
    packet_rows = read_jsonl(root / REVIEW_PACKET_PATH)
    content_rows = read_jsonl(root / CLEAN_120_PATH)
    route_input_rows = read_jsonl(root / ROUTE_INPUT_PATH)
    component_rows = read_jsonl(root / COMPONENT_SOURCE_PATH)
    packet = map_rows(packet_rows, "packet_item_id", "E_PACKET_ID")
    content = map_rows(content_rows, "asset_id", "E_CONTENT_ID")
    route_inputs = map_rows(route_input_rows, "case_id", "E_ROUTE_INPUT_ID")
    components = map_rows(component_rows, "component_id", "E_COMPONENT_ID")
    require(len(packet) == 266, "E_PACKET_COUNT", str(len(packet)))
    require(len(content) == 120, "E_CONTENT_COUNT", str(len(content)))
    require(len(route_inputs) == 60, "E_ROUTE_INPUT_COUNT")
    require(len(components) == 86, "E_COMPONENT_COUNT", str(len(components)))
    profile_document = load_yaml(root / PROFILE_PATH).get(
        "content_product_profile_registry"
    )
    require(isinstance(profile_document, dict), "E_PROFILE_SCHEMA")
    profiles = profile_document.get("profiles")
    require(isinstance(profiles, list) and len(profiles) == 20, "E_PROFILE_COUNT")
    profile_by_id: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        require(isinstance(profile, dict), "E_PROFILE_SCHEMA")
        profile_id = require_string(
            profile.get("content_product_type_id"), "E_PROFILE_ID", "id"
        )
        require(profile_id not in profile_by_id, "E_PROFILE_ID", profile_id)
        profile_by_id[profile_id] = profile
    return {
        "packet": packet,
        "content": content,
        "route_inputs": route_inputs,
        "components": components,
        "profiles": profile_by_id,
    }


def route_actual_state(
    root: Path, state: dict[str, Any]
) -> dict[str, tuple[dict[str, Any], str]]:
    """Read current implementation only after the gold-answer bytes are frozen."""

    ensure_hash(root / ROUTE_ACTUAL_PATH, ROUTE_ACTUAL_SHA256, "E_FROZEN_INPUT_DRIFT")
    route_actual_rows = read_jsonl(root / ROUTE_ACTUAL_PATH)
    route_actuals = map_rows(route_actual_rows, "case_id", "E_ROUTE_ACTUAL_ID")
    require(len(route_actuals) == 60, "E_ROUTE_ACTUAL_COUNT")
    require(set(state["route_inputs"]) == set(route_actuals), "E_ROUTE_ID_PAIRING")
    return route_actuals


def import_manifest() -> dict[str, Any]:
    entries: list[dict[str, str]] = []
    for source, destination, digest in IMPORT_SPECS:
        entries.append(
            {
                "source_path": source.as_posix(),
                "import_path": destination.relative_to(TASK_ROOT).as_posix(),
                "sha256": digest,
            }
        )
    manifest: dict[str, Any] = {
        "signed_review_import_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "copy_mode": "BYTE_IDENTICAL_READ_ONLY_IMPORT",
            "entries": entries,
            "external_review_count": len(entries),
        }
    }
    document = manifest["signed_review_import_manifest"]
    document["manifest_digest"] = object_digest(document, "manifest_digest")
    return manifest


def import_signed_inputs(root: Path) -> None:
    for source, destination, expected in IMPORT_SPECS:
        ensure_hash(source, expected, "E_EXTERNAL_SIGNED_INPUT_DRIFT")
        target = root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        source_bytes = source.read_bytes()
        if not target.exists() or target.read_bytes() != source_bytes:
            target.write_bytes(source_bytes)


def verify_imports(root: Path) -> None:
    manifest_path = root / IMPORT_MANIFEST_PATH
    manifest = load_yaml(manifest_path).get("signed_review_import_manifest")
    require(isinstance(manifest, dict), "E_IMPORT_MANIFEST_SCHEMA")
    expected_manifest = import_manifest()["signed_review_import_manifest"]
    require(manifest == expected_manifest, "E_IMPORT_MANIFEST_DRIFT")
    for _, destination, expected in IMPORT_SPECS:
        ensure_hash(root / destination, expected, "E_IMPORT_HASH")


def primary_identity(record: dict[str, Any]) -> dict[str, Any]:
    identity = record.get("identity")
    require(isinstance(identity, dict), "E_PRIMARY_SCHEMA", "identity")
    return identity


def secondary_identity(record: dict[str, Any]) -> dict[str, Any]:
    identity = record.get("reviewer")
    require(isinstance(identity, dict), "E_SECONDARY_SCHEMA", "reviewer")
    return identity


def primary_evaluation(record: dict[str, Any]) -> dict[str, Any]:
    evaluation = record.get("evaluation")
    require(isinstance(evaluation, dict), "E_PRIMARY_SCHEMA", "evaluation")
    return evaluation


def secondary_evaluation(record: dict[str, Any]) -> dict[str, Any]:
    evaluation = record.get("evidence_and_evaluation")
    require(isinstance(evaluation, dict), "E_SECONDARY_SCHEMA", "evaluation")
    return evaluation


def record_object(record: dict[str, Any], code: str) -> dict[str, Any]:
    object_value = record.get("object")
    require(isinstance(object_value, dict), code, "object")
    for key in ("packet_item_id", "object_type", "object_id"):
        require_string(object_value.get(key), code, key)
    return object_value


def validate_packet_binding(
    record: dict[str, Any], state: dict[str, Any], code: str
) -> None:
    object_value = record_object(record, code)
    packet_id = object_value["packet_item_id"]
    packet_item = state["packet"].get(packet_id)
    require(packet_item is not None, code, packet_id)
    packet_row = packet_item[0]
    require(
        packet_row.get("object_type") == object_value.get("object_type")
        and packet_row.get("object_id") == object_value.get("object_id"),
        code,
        packet_id,
    )


def validate_channel_fields(record: dict[str, Any], code: str) -> None:
    object_value = record_object(record, code)
    lane = object_value.get("source_generation_lane_or_pair_ref")
    optional = object_value.get("optional_lane_applicability")
    source_refs = object_value.get("source_refs")
    if isinstance(source_refs, list):
        require(
            lane is None or not any("b_channel" in str(item) for item in source_refs),
            "E_CHANNEL_PATH_INFERENCE",
        )
    require(lane is None, "E_CHANNEL_PROVENANCE", str(lane))
    require(optional is None, "E_CHANNEL_PROVENANCE", str(optional))


def validate_primary_record(record: dict[str, Any], state: dict[str, Any]) -> None:
    identity = primary_identity(record)
    evaluation = primary_evaluation(record)
    integrity = record.get("integrity")
    require(isinstance(integrity, dict), "E_PRIMARY_SCHEMA", "integrity")
    for key in (
        "review_record_id",
        "reviewer_identity_id",
        "reviewer_instance_or_session_id",
        "review_run_id",
        "review_role",
        "instruction_sha256",
        "input_sha256",
        "model_or_instance_configuration_sha256",
    ):
        require_string(identity.get(key), "E_PRIMARY_SCHEMA", key)
    require(identity.get("review_role") == "PRIMARY_CONTENT_VALUE", "E_PRIMARY_ROLE")
    expected = record_digest_excluding(
        record, ("integrity", "append_only_record_sha256")
    )
    require(
        integrity.get("append_only_record_sha256") == expected,
        "E_PRIMARY_RECORD_DIGEST",
    )
    require_string(
        integrity.get("append_only_signature_or_attestation"),
        "E_PRIMARY_SCHEMA",
        "signature",
    )
    for key in (
        "disposition",
        "lifecycle_status",
        "conclusion",
        "veto",
        "hard_gate_results",
    ):
        require(key in evaluation, "E_PRIMARY_SCHEMA", key)
    validate_packet_binding(record, state, "E_PRIMARY_PACKET_BINDING")
    validate_channel_fields(record, "E_PRIMARY_CHANNEL")
    route = record_object(record, "E_PRIMARY_SCHEMA").get("object_type") == "ROUTE_CASE"
    route_determination = record.get("route_determination")
    if route:
        require(isinstance(route_determination, dict), "E_PRIMARY_ROUTE")
        require(
            route_determination.get("actual_result_seen_before_signature") is False,
            "E_ROUTE_BLINDNESS",
        )
        require_string(
            route_determination.get("primary_action"), "E_PRIMARY_ROUTE", "action"
        )
        require_string(
            route_determination.get("reason_code"), "E_PRIMARY_ROUTE", "reason"
        )


def validate_secondary_record(record: dict[str, Any], state: dict[str, Any]) -> None:
    identity = secondary_identity(record)
    evaluation = secondary_evaluation(record)
    integrity = record.get("integrity")
    signature = record.get("append_only_signature")
    require(
        isinstance(integrity, dict) and isinstance(signature, dict),
        "E_SECONDARY_SCHEMA",
        "integrity",
    )
    for key in (
        "reviewer_identity_id",
        "reviewer_instance_or_session_id",
        "review_run_id",
        "review_role",
        "instruction_sha256",
        "model_or_instance_configuration_sha256",
    ):
        require_string(identity.get(key), "E_SECONDARY_SCHEMA", key)
    object_value = record_object(record, "E_SECONDARY_SCHEMA")
    input_digest = object_value.get("input_digest", object_value.get("input_sha256"))
    require_string(input_digest, "E_SECONDARY_SCHEMA", "object.input_digest")
    require(
        identity.get("review_role") == "SECONDARY_FACT_AUTHORIZATION",
        "E_SECONDARY_ROLE",
    )
    expected = record_digest(
        record,
        (
            ("integrity", "append_only_record_sha256"),
            ("append_only_signature", "append_only_record_digest"),
        ),
    )
    require(
        integrity.get("append_only_record_sha256") == expected,
        "E_SECONDARY_RECORD_DIGEST",
    )
    require(
        signature.get("append_only_record_digest") == expected,
        "E_SECONDARY_RECORD_DIGEST",
    )
    require_string(
        signature.get("signature_or_attestation"), "E_SECONDARY_SCHEMA", "signature"
    )
    for key in (
        "disposition",
        "lifecycle_status",
        "conclusion",
        "veto",
        "hard_gate_results",
    ):
        require(key in evaluation, "E_SECONDARY_SCHEMA", key)
    validate_packet_binding(record, state, "E_SECONDARY_PACKET_BINDING")
    validate_channel_fields(record, "E_SECONDARY_CHANNEL")
    route = (
        record_object(record, "E_SECONDARY_SCHEMA").get("object_type") == "ROUTE_CASE"
    )
    route_determination = record.get("route_determination")
    if route:
        require(isinstance(route_determination, dict), "E_SECONDARY_ROUTE")
        require(
            route_determination.get("actual_result_seen_before_signature") is False,
            "E_ROUTE_BLINDNESS",
        )
        require_string(
            route_determination.get("primary_action"), "E_SECONDARY_ROUTE", "action"
        )
        require_string(
            route_determination.get("reason_code"), "E_SECONDARY_ROUTE", "reason"
        )


def validate_adjudication_record(
    record: dict[str, Any], state: dict[str, Any], assignment: dict[str, Any]
) -> None:
    for key in (
        "adjudication_record_id",
        "conflict_type",
        "packet_item_id",
        "primary_record_ref_and_digest",
        "secondary_record_ref_and_digest",
        "adjudicated_value",
        "final_disposition_for_p1b",
        "reviewer_identity_session_run_instruction_and_configuration_digests",
        "append_only_signature_and_record_digest",
    ):
        require(key in record, "E_ADJUDICATION_SCHEMA", key)
    packet_id = require_string(
        record.get("packet_item_id"), "E_ADJUDICATION_SCHEMA", "packet"
    )
    require(packet_id in state["packet"], "E_ADJUDICATION_PACKET", packet_id)
    signature = record.get("append_only_signature_and_record_digest")
    require(isinstance(signature, dict), "E_ADJUDICATION_SCHEMA", "signature")
    expected = record_digest(
        record, (("append_only_signature_and_record_digest", "record_sha256"),)
    )
    require(signature.get("record_sha256") == expected, "E_ADJUDICATION_RECORD_DIGEST")
    identity = record.get(
        "reviewer_identity_session_run_instruction_and_configuration_digests"
    )
    require(isinstance(identity, dict), "E_ADJUDICATION_SCHEMA", "identity")
    require(
        identity.get("review_role") == "INDEPENDENT_ADJUDICATION", "E_ADJUDICATION_ROLE"
    )
    conflict_type = require_string(
        record.get("conflict_type"), "E_ADJUDICATION_SCHEMA", "conflict"
    )
    conflicts = assignment.get("conflicts")
    require(isinstance(conflicts, dict), "E_ADJUDICATION_ASSIGNMENT")
    assigned = conflicts.get(conflict_type)
    require(
        isinstance(assigned, list) and packet_id in assigned,
        "E_ADJUDICATION_ASSIGNMENT",
        packet_id,
    )


def stage_identity(record: dict[str, Any], stage: str) -> tuple[str, str, str]:
    if stage == "PRIMARY":
        identity = primary_identity(record)
    elif stage == "SECONDARY":
        identity = secondary_identity(record)
    else:
        identity = record[
            "reviewer_identity_session_run_instruction_and_configuration_digests"
        ]
    return (
        require_string(
            identity.get("reviewer_identity_id"), "E_REVIEWER_IDENTITY", stage
        ),
        require_string(
            identity.get("reviewer_instance_or_session_id"),
            "E_REVIEWER_IDENTITY",
            stage,
        ),
        require_string(identity.get("review_run_id"), "E_REVIEWER_IDENTITY", stage),
    )


def validate_identity_isolation(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
    adjudication: list[dict[str, Any]],
    invalidations: dict[str, Any],
) -> None:
    identities = {
        "PRIMARY": stage_identity(primary[0], "PRIMARY"),
        "SECONDARY": stage_identity(secondary[0], "SECONDARY"),
        "ADJUDICATION": stage_identity(adjudication[0], "ADJUDICATION"),
    }
    for stage, records in (
        ("PRIMARY", primary),
        ("SECONDARY", secondary),
        ("ADJUDICATION", adjudication),
    ):
        require(
            all(
                stage_identity(record, stage) == identities[stage] for record in records
            ),
            "E_REVIEWER_IDENTITY",
            stage,
        )
    require(len(set(identities.values())) == 3, "E_REVIEWER_IDENTITY_COLLISION")
    forbidden = {P1A_BUILDER_IDENTITY, P1B_FREEZER_IDENTITY}
    sessions = invalidations.get("sessions")
    require(isinstance(sessions, list), "E_INVALIDATION_SCHEMA")
    for item in sessions:
        require(isinstance(item, dict), "E_INVALIDATION_SCHEMA")
        require(item.get("signed_records_created") is False, "E_INVALIDATED_SESSION")
        require(item.get("output_files_created") is False, "E_INVALIDATED_SESSION")
        require(item.get("judgments_may_be_reused") is False, "E_INVALIDATED_SESSION")
        identity = require_string(
            item.get("reviewer_identity"), "E_INVALIDATION_SCHEMA", "identity"
        )
        forbidden.add(identity)
    require(
        not any(identity[0] in forbidden for identity in identities.values()),
        "E_INVALIDATED_OR_FREEZER_IDENTITY",
    )


def imported_reviews(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    verify_imports(root)
    review_root = root / IMPORT_ROOT / "independent_reviews"
    primary = [row for row, _ in read_jsonl(review_root / "primary/records.jsonl")]
    secondary = [row for row, _ in read_jsonl(review_root / "secondary/records.jsonl")]
    adjudication = [
        row for row, _ in read_jsonl(review_root / "adjudication/records.jsonl")
    ]
    require(
        len(primary) == 266 and len(secondary) == 194 and len(adjudication) == 43,
        "E_REVIEW_RECORD_COUNT",
    )
    assignment = load_yaml(review_root / "adjudication_assignment.v0.yaml").get(
        "adjudication_assignment"
    )
    invalidations = load_yaml(review_root / "review_session_invalidations.v0.yaml").get(
        "review_session_invalidations"
    )
    require(
        isinstance(assignment, dict) and isinstance(invalidations, dict),
        "E_REVIEW_CONTROL_SCHEMA",
    )
    for record in primary:
        validate_primary_record(record, state)
    for record in secondary:
        validate_secondary_record(record, state)
    for record in adjudication:
        validate_adjudication_record(record, state, assignment)
    validate_identity_isolation(primary, secondary, adjudication, invalidations)
    checkpoint = (
        review_root / "coordinator_review_checkpoint_closeout.v0.md"
    ).read_text(encoding="utf-8")
    require(
        "checkpoint_verdict: PASS_FOR_P1B_INPUT" in checkpoint,
        "E_COORDINATOR_CHECKPOINT",
    )
    require("p1b_allowed: true" in checkpoint, "E_COORDINATOR_CHECKPOINT")
    return {
        "primary": primary,
        "secondary": secondary,
        "adjudication": adjudication,
        "assignment": assignment,
        "invalidations": invalidations,
    }


def normalized_records(reviews: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for stage, records in (
        ("PRIMARY", reviews["primary"]),
        ("SECONDARY", reviews["secondary"]),
    ):
        for record in records:
            object_value = record["object"]
            if stage == "PRIMARY":
                identity = record["identity"]
                evaluation = record["evaluation"]
                signature = record["integrity"]
                record_id = identity["review_record_id"]
                record_hash = signature["append_only_record_sha256"]
            else:
                identity = record["reviewer"]
                evaluation = record["evidence_and_evaluation"]
                signature = record["append_only_signature"]
                record_id = record["review_record_id"]
                record_hash = signature["append_only_record_digest"]
            normalized.append(
                {
                    "normalized_record_id": f"{stage}:{record_id}",
                    "review_stage": stage,
                    "review_record_id": record_id,
                    "signed_record_digest": record_hash,
                    "reviewer_identity_id": identity["reviewer_identity_id"],
                    "reviewer_instance_or_session_id": identity[
                        "reviewer_instance_or_session_id"
                    ],
                    "review_run_id": identity["review_run_id"],
                    "review_role": identity["review_role"],
                    "packet_item_id": object_value["packet_item_id"],
                    "object_type": object_value["object_type"],
                    "object_id": object_value["object_id"],
                    "primary_content_product_id": object_value.get(
                        "primary_content_product_id"
                    ),
                    "source_generation_lane_or_pair_ref": object_value.get(
                        "source_generation_lane_or_pair_ref"
                    ),
                    "optional_lane_applicability": object_value.get(
                        "optional_lane_applicability"
                    ),
                    "evaluation": evaluation,
                    "route_determination": record.get("route_determination"),
                    "component_determination": record.get("component_determination"),
                }
            )
    for record in reviews["adjudication"]:
        identity = record[
            "reviewer_identity_session_run_instruction_and_configuration_digests"
        ]
        signature = record["append_only_signature_and_record_digest"]
        normalized.append(
            {
                "normalized_record_id": f"ADJUDICATION:{record['adjudication_record_id']}",
                "review_stage": "ADJUDICATION",
                "review_record_id": record["adjudication_record_id"],
                "signed_record_digest": signature["record_sha256"],
                "reviewer_identity_id": identity["reviewer_identity_id"],
                "reviewer_instance_or_session_id": identity[
                    "reviewer_instance_or_session_id"
                ],
                "review_run_id": identity["review_run_id"],
                "review_role": identity["review_role"],
                "packet_item_id": record["packet_item_id"],
                "object_type": "ADJUDICATION_FIELD_ONLY",
                "object_id": record["packet_item_id"],
                "primary_content_product_id": None,
                "source_generation_lane_or_pair_ref": None,
                "optional_lane_applicability": None,
                "evaluation": None,
                "route_determination": None,
                "component_determination": None,
                "conflict_type": record["conflict_type"],
                "adjudicated_value": record["adjudicated_value"],
                "final_disposition_for_p1b": record["final_disposition_for_p1b"],
            }
        )
    return sorted(normalized, key=lambda row: row["normalized_record_id"])


def by_object(
    records: list[dict[str, Any]], object_type: str, code: str
) -> dict[str, dict[str, Any]]:
    selected = [
        record for record in records if record["object"]["object_type"] == object_type
    ]
    output: dict[str, dict[str, Any]] = {}
    for record in selected:
        object_id = record["object"]["object_id"]
        require(object_id not in output, code, object_id)
        output[object_id] = record
    return output


def adjudication_by_packet(
    records: list[dict[str, Any]], conflict_type: str, code: str
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for record in records:
        if record["conflict_type"] != conflict_type:
            continue
        packet_id = record["packet_item_id"]
        require(packet_id not in output, code, packet_id)
        output[packet_id] = record
    return output


def hard_gates_pass(evaluation: dict[str, Any]) -> bool:
    gates = evaluation.get("hard_gate_results")
    if isinstance(gates, dict):
        values = gates.values()
        return all(
            isinstance(value, str)
            and (value.startswith("PASS") or value == "NOT_APPLICABLE_FIRST_GATE")
            for value in values
        )
    if isinstance(gates, list):
        return all(
            isinstance(item, dict) and str(item.get("result", "")).startswith("PASS")
            for item in gates
        )
    return False


def derive_content(
    state: dict[str, Any], reviews: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    primary = by_object(
        reviews["primary"], "LEGACY_REFERENCE_CONTENT", "E_CONTENT_PRIMARY_DUPLICATE"
    )
    secondary = by_object(
        reviews["secondary"],
        "LEGACY_REFERENCE_CONTENT",
        "E_CONTENT_SECONDARY_DUPLICATE",
    )
    adjudication = adjudication_by_packet(
        reviews["adjudication"],
        "content_product_mapping",
        "E_CONTENT_ADJUDICATION_DUPLICATE",
    )
    require(len(primary) == 120 and len(secondary) >= 48, "E_CONTENT_REVIEW_COVERAGE")
    rows: list[dict[str, Any]] = []
    for asset_id, (_, raw_line) in state["content"].items():
        first = primary.get(asset_id)
        require(first is not None, "E_CONTENT_PRIMARY_MISSING", asset_id)
        second = secondary.get(asset_id)
        packet_id = first["object"]["packet_item_id"]
        adjudicated = adjudication.get(packet_id)
        evaluation = first["evaluation"]
        disposition = evaluation["disposition"]
        if disposition == "MERGE_WITH_CANONICAL_CLUSTER_CHAMPION":
            final = "MERGE_NOT_SEPARATELY_COUNTED"
        elif disposition == "MINOR_REVISION_AND_REVIEW":
            final = "HOLD_FOR_REPAIR"
        elif disposition == "APPROVE_AS_POSITIVE_BASELINE_CANDIDATE":
            second_evaluation = (
                second["evidence_and_evaluation"] if second is not None else None
            )
            second_blocks = isinstance(second_evaluation, dict) and (
                second_evaluation.get("disposition")
                == "REWORK_OR_REMAP_BEFORE_COUNTING"
                or second_evaluation.get("veto") is True
            )
            final = (
                "HOLD_FOR_REPAIR"
                if second_blocks
                else "COUNT_TOWARD_FINAL_300_POSITIVE"
            )
        else:
            raise ValueError(f"E_CONTENT_DISPOSITION:{asset_id}:{disposition}")
        primary_cp = first["object"].get("primary_content_product_id")
        require(isinstance(primary_cp, str), "E_CONTENT_PRIMARY_CP", asset_id)
        final_cp = primary_cp
        if adjudicated is not None:
            value = adjudicated.get("adjudicated_value")
            require(isinstance(value, dict), "E_CONTENT_ADJUDICATION_SCHEMA", asset_id)
            final_cp = require_string(
                value.get("primary_content_product_id"),
                "E_CONTENT_ADJUDICATION_SCHEMA",
                asset_id,
            )
        approval_conditions = {
            "primary_explicit_approval": disposition
            == "APPROVE_AS_POSITIVE_BASELINE_CANDIDATE",
            "primary_hard_gates_pass": hard_gates_pass(evaluation),
            "primary_veto_false": evaluation.get("veto") is False,
            "secondary_present": second is not None,
            "secondary_blocks": final == "HOLD_FOR_REPAIR" and second is not None,
            "third_adjudication_field_only": adjudicated is not None,
        }
        if final == "COUNT_TOWARD_FINAL_300_POSITIVE":
            require(
                all(
                    (
                        approval_conditions["primary_explicit_approval"],
                        approval_conditions["primary_hard_gates_pass"],
                        approval_conditions["primary_veto_false"],
                    )
                ),
                "E_CONTENT_APPROVAL_GATE",
                asset_id,
            )
        rows.append(
            {
                "asset_id": asset_id,
                "source_record_sha256": sha256_bytes(raw_line.encode("utf-8")),
                "packet_item_id": packet_id,
                "primary_review_record_id": first["identity"]["review_record_id"],
                "primary_signed_record_digest": first["integrity"][
                    "append_only_record_sha256"
                ],
                "secondary_review_record_id": second.get("review_record_id")
                if second is not None
                else None,
                "secondary_signed_record_digest": (
                    second["append_only_signature"]["append_only_record_digest"]
                    if second is not None
                    else None
                ),
                "adjudication_record_id": adjudicated.get("adjudication_record_id")
                if adjudicated is not None
                else None,
                "primary_content_product_id": primary_cp,
                "final_content_product_id": final_cp,
                "v1_1_scores": {
                    "primary_total_score_out_of_100": evaluation.get(
                        "total_score_out_of_100"
                    ),
                    "primary_key_item_minimum_results": evaluation.get(
                        "key_item_minimum_results"
                    ),
                    "primary_hard_gate_results": evaluation.get("hard_gate_results"),
                    "primary_veto": evaluation.get("veto"),
                },
                "duplicate_or_cluster_disposition": disposition,
                "fact_and_authorization_boundary": evaluation.get("hard_gate_results"),
                "final_disposition": final,
                "machine_derivation": approval_conditions,
            }
        )
    require(
        len(rows) == 120 and len({row["asset_id"] for row in rows}) == 120,
        "E_CONTENT_FINAL_COUNT",
    )
    counts = Counter(
        row["final_content_product_id"]
        for row in rows
        if row["final_disposition"] == "COUNT_TOWARD_FINAL_300_POSITIVE"
    )
    gaps: list[dict[str, Any]] = []
    for profile_id in sorted(state["profiles"]):
        count = counts[profile_id]
        gaps.append(
            {
                "content_product_id": profile_id,
                "final_positive_target": 12,
                "counted_legacy_reference_content": count,
                "gap_to_final_positive_target": 12 - count,
                "signed_evidence_status": "SIGNED_COUNTABLE_REFERENCE_PRESENT"
                if count
                else "NO_SIGNED_COUNTABLE_REFERENCE",
            }
        )
    matrix: dict[str, Any] = {
        "reference_120_content_product_gap_matrix": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "legacy_inventory_count": 120,
            "counted_positive_parent_count": sum(counts.values()),
            "final_positive_target": 240,
            "entries": gaps,
        }
    }
    document = matrix["reference_120_content_product_gap_matrix"]
    document["matrix_digest"] = object_digest(document, "matrix_digest")
    return rows, matrix


def derive_route_gold(
    reviews: dict[str, Any], state: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    primary = by_object(reviews["primary"], "ROUTE_CASE", "E_ROUTE_PRIMARY_DUPLICATE")
    secondary = by_object(
        reviews["secondary"], "ROUTE_CASE", "E_ROUTE_SECONDARY_DUPLICATE"
    )
    adjudication = adjudication_by_packet(
        reviews["adjudication"], "route_reason_code", "E_ROUTE_ADJUDICATION_DUPLICATE"
    )
    require(len(primary) == len(secondary) == 60, "E_ROUTE_REVIEW_COVERAGE")
    rows: list[dict[str, Any]] = []
    for case_id, (route_input, raw_line) in state["route_inputs"].items():
        first = primary.get(case_id)
        second = secondary.get(case_id)
        require(
            first is not None and second is not None, "E_ROUTE_REVIEW_MISSING", case_id
        )
        first_route = first.get("route_determination")
        second_route = second.get("route_determination")
        require(
            isinstance(first_route, dict) and isinstance(second_route, dict),
            "E_ROUTE_SCHEMA",
            case_id,
        )
        action = first_route.get("primary_action")
        require(
            action == second_route.get("primary_action"),
            "E_ROUTE_ACTION_CONFLICT",
            case_id,
        )
        packet_id = first["object"]["packet_item_id"]
        adjudicated = adjudication.get(packet_id)
        if adjudicated is None:
            reason = first_route.get("reason_code")
            require(
                reason == second_route.get("reason_code"),
                "E_ROUTE_REASON_CONFLICT",
                case_id,
            )
            basis = "PAIRWISE_SIGNED_MATCH"
            adjudication_record_id = None
        else:
            value = adjudicated.get("adjudicated_value")
            require(isinstance(value, dict), "E_ROUTE_ADJUDICATION_SCHEMA", case_id)
            require(
                value.get("primary_action") == action,
                "E_ROUTE_ADJUDICATION_ACTION",
                case_id,
            )
            reason = value.get("reason_code")
            basis = "ASSIGNED_INDEPENDENT_ADJUDICATION"
            adjudication_record_id = adjudicated.get("adjudication_record_id")
        reason = require_string(reason, "E_ROUTE_REASON", case_id)
        gold: dict[str, Any] = {
            "case_id": case_id,
            "profile_id": route_input.get("profile_id"),
            "route_input_record_sha256": sha256_bytes(raw_line.encode("utf-8")),
            "primary_review_record_id": first["identity"]["review_record_id"],
            "primary_signed_record_digest": first["integrity"][
                "append_only_record_sha256"
            ],
            "secondary_review_record_id": second["review_record_id"],
            "secondary_signed_record_digest": second["append_only_signature"][
                "append_only_record_digest"
            ],
            "adjudication_record_id": adjudication_record_id,
            "gold_primary_action": action,
            "gold_reason_code": reason,
            "gold_basis": basis,
            "evidence_refs": first_route.get("evidence_refs"),
        }
        gold["gold_answer_digest"] = object_digest(gold, "gold_answer_digest")
        rows.append(gold)
    require(len(rows) == 60, "E_ROUTE_GOLD_COUNT")
    gold_bytes = jsonl_bytes(rows)
    freeze: dict[str, Any] = {
        "route_60_gold_freeze_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "signed_review_inputs_only": True,
            "current_actual_source_included": False,
            "forbidden_current_actual_locator_or_digest": True,
            "gold_answer_count": 60,
            "gold_answers_sha256": sha256_bytes(gold_bytes),
        }
    }
    document = freeze["route_60_gold_freeze_manifest"]
    document["freeze_manifest_digest"] = object_digest(
        document, "freeze_manifest_digest"
    )
    return rows, freeze


def derive_route_comparison(
    route_actuals: dict[str, tuple[dict[str, Any], str]],
    gold_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gold_by_id = {row["case_id"]: row for row in gold_rows}
    comparison: list[dict[str, Any]] = []
    for case_id, (actual, raw_line) in route_actuals.items():
        gold = gold_by_id.get(case_id)
        require(gold is not None, "E_ROUTE_GOLD_MISSING", case_id)
        decision = actual.get("actual_decision")
        require(isinstance(decision, dict), "E_ROUTE_ACTUAL_SCHEMA", case_id)
        current_action = decision.get("actual_primary_action")
        current_reason = decision.get("actual_primary_reason_code")
        comparison.append(
            {
                "case_id": case_id,
                "gold_answer_digest": gold["gold_answer_digest"],
                "gold_primary_action": gold["gold_primary_action"],
                "gold_reason_code": gold["gold_reason_code"],
                "current_actual_record_sha256": sha256_bytes(raw_line.encode("utf-8")),
                "current_primary_action": current_action,
                "current_primary_reason_code": current_reason,
                "primary_action_matches_gold": current_action
                == gold["gold_primary_action"],
                "primary_reason_matches_gold": current_reason
                == gold["gold_reason_code"],
            }
        )
    require(len(comparison) == 60, "E_ROUTE_COMPARISON_COUNT")
    return comparison


def derive_components(
    state: dict[str, Any], reviews: dict[str, Any]
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    primary = by_object(
        reviews["primary"], "COMPONENT_CANDIDATE", "E_COMPONENT_PRIMARY_DUPLICATE"
    )
    secondary = by_object(
        reviews["secondary"], "COMPONENT_CANDIDATE", "E_COMPONENT_SECONDARY_DUPLICATE"
    )
    adjudication = adjudication_by_packet(
        reviews["adjudication"],
        "component_disposition",
        "E_COMPONENT_ADJUDICATION_DUPLICATE",
    )
    require(len(primary) == len(secondary) == 86, "E_COMPONENT_REVIEW_COVERAGE")
    final_rows: list[dict[str, Any]] = []
    active_components: list[dict[str, Any]] = []
    active_edges: list[dict[str, Any]] = []
    for component_id, (source, raw_line) in state["components"].items():
        first = primary.get(component_id)
        second = secondary.get(component_id)
        require(
            first is not None and second is not None,
            "E_COMPONENT_REVIEW_MISSING",
            component_id,
        )
        packet_id = first["object"]["packet_item_id"]
        adjudicated = adjudication.get(packet_id)
        first_eval = first["evaluation"]
        second_eval = second["evidence_and_evaluation"]
        adjudication_text = (
            adjudicated.get("final_disposition_for_p1b", "") if adjudicated else ""
        )
        if (
            "控制规则" in str(adjudication_text)
            or first_eval.get("disposition") == "RECLASSIFY_AS_CONTROL_RULE"
        ):
            final = "RECLASSIFY_AS_CONTROL_RULE"
            blocking_reason = "SIGNED_CONTROL_RULE_RECLASSIFICATION"
        elif (
            first_eval.get("disposition")
            not in {
                "KEEP_AS_APPROVED_COMPONENT_CANDIDATE",
                "KEEP_AS_APPROVED_DESIGN_COMPONENT_CANDIDATE",
            }
            or second_eval.get("disposition") != "KEEP_AS_DESIGN_CANDIDATE"
            or first_eval.get("lifecycle_status")
            != "PRIMARY_REVIEW_APPROVED_CANDIDATE_NOT_FROZEN"
            or second_eval.get("lifecycle_status") != "SECONDARY_REVIEWED_NOT_APPROVED"
            or first_eval.get("veto") is True
            or second_eval.get("veto") is True
        ):
            final = "KEEP_CANDIDATE_REPAIR_REQUIRED"
            blocking_reason = "SIGNED_REPAIR_OR_LIFECYCLE_NOT_APPROVED"
        else:
            # A secondary "NOT_APPROVED" lifecycle is explicitly not an active
            # lifecycle. This branch documents the conclusion rather than
            # promoting a candidate by implication.
            final = "KEEP_CANDIDATE_REPAIR_REQUIRED"
            blocking_reason = "SECONDARY_LIFECYCLE_NOT_APPROVED"
        role = source.get("component_role", source.get("source_component_role"))
        require(isinstance(role, str) and role, "E_COMPONENT_ROLE", component_id)
        row = {
            "component_id": component_id,
            "source_record_sha256": sha256_bytes(raw_line.encode("utf-8")),
            "packet_item_id": packet_id,
            "component_role": role,
            "composition_asset_class": source.get("composition_asset_class"),
            "primary_review_record_id": first["identity"]["review_record_id"],
            "primary_signed_record_digest": first["integrity"][
                "append_only_record_sha256"
            ],
            "secondary_review_record_id": second["review_record_id"],
            "secondary_signed_record_digest": second["append_only_signature"][
                "append_only_record_digest"
            ],
            "adjudication_record_id": adjudicated.get("adjudication_record_id")
            if adjudicated
            else None,
            "primary_disposition": first_eval.get("disposition"),
            "secondary_disposition": second_eval.get("disposition"),
            "primary_lifecycle_status": first_eval.get("lifecycle_status"),
            "secondary_lifecycle_status": second_eval.get("lifecycle_status"),
            "final_disposition": final,
            "blocking_reason": blocking_reason,
            "new_generator_consumable": False,
        }
        final_rows.append(row)
        if final == "KEEP_ACTIVE_FOR_GATE1_DEVELOPMENT_TEST":
            active_components.append(row)
    require(len(final_rows) == 86, "E_COMPONENT_FINAL_COUNT")
    active_by_id = {row["component_id"]: row for row in active_components}
    for component_id, final_row in active_by_id.items():
        primary_edges = primary[component_id]["component_determination"].get(
            "applicability_decisions", []
        )
        secondary_edges = secondary[component_id]["component_determination"].get(
            "applicability_decisions", []
        )
        primary_ids = {
            edge.get("content_product_id")
            for edge in primary_edges
            if isinstance(edge, dict)
        }
        secondary_ids = {
            edge.get("content_product_id")
            for edge in secondary_edges
            if isinstance(edge, dict)
        }
        for profile_id in sorted(primary_ids & secondary_ids):
            require(
                isinstance(profile_id, str) and profile_id in state["profiles"],
                "E_COMPONENT_EDGE_CP",
                component_id,
            )
            active_edges.append(
                {
                    "component_id": component_id,
                    "content_product_id": profile_id,
                    "component_role": final_row["component_role"],
                    "signed_edge_evidence": True,
                    "new_generator_consumable": False,
                }
            )
    edges_by_profile_role = Counter(
        (row["content_product_id"], row["component_role"]) for row in active_edges
    )
    entries: list[dict[str, Any]] = []
    for profile_id, profile in sorted(state["profiles"].items()):
        roles = profile.get("required_component_roles")
        require(isinstance(roles, list), "E_PROFILE_REQUIRED_ROLES", profile_id)
        gaps: list[dict[str, Any]] = []
        for requirement in roles:
            require(
                isinstance(requirement, dict), "E_PROFILE_REQUIRED_ROLES", profile_id
            )
            role = require_string(
                requirement.get("role"), "E_PROFILE_REQUIRED_ROLES", profile_id
            )
            minimum = requirement.get("min_count")
            require(
                isinstance(minimum, int) and minimum >= 1,
                "E_PROFILE_REQUIRED_ROLES",
                profile_id,
            )
            available = edges_by_profile_role[(profile_id, role)]
            if available < minimum:
                gaps.append({"role": role, "minimum": minimum, "available": available})
        entries.append(
            {
                "content_product_id": profile_id,
                "supply_complete": not gaps,
                "missing_required_roles": gaps,
            }
        )
    supply: dict[str, Any] = {
        "component_supply_gap_matrix": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "component_candidate_inventory": 86,
            "active_component_count": len(active_components),
            "active_edge_count": len(active_edges),
            "complete_profile_count": sum(
                1 for entry in entries if entry["supply_complete"]
            ),
            "incomplete_profile_count": sum(
                1 for entry in entries if not entry["supply_complete"]
            ),
            "entries": entries,
        }
    }
    supply_document = supply["component_supply_gap_matrix"]
    supply_document["matrix_digest"] = object_digest(supply_document, "matrix_digest")
    test_manifest: dict[str, Any] = {
        "gate1_development_test_input_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "source_status": "DERIVED_FROM_SIGNED_ACTIVE_COMPONENTS_ONLY",
            "component_count": len(active_components),
            "edge_count": len(active_edges),
            "p2_input_eligible": not any(
                not entry["supply_complete"] for entry in entries
            ),
            "runtime_consumable": False,
            "generation_allowed": False,
            "component_ids": [row["component_id"] for row in active_components],
        }
    }
    manifest_document = test_manifest["gate1_development_test_input_manifest"]
    manifest_document["manifest_digest"] = object_digest(
        manifest_document, "manifest_digest"
    )
    return final_rows, active_components, active_edges, supply, test_manifest


def closeout_contract() -> dict[str, Any]:
    contract: dict[str, Any] = {
        "p1b_signed_review_closeout_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "p1a_baseline_commit": P1B_BASELINE_COMMIT,
            "freezer_identity_id": P1B_FREEZER_IDENTITY,
            "input_model": "THREE_SIGNED_REVIEW_STRUCTURES_ONLY",
            "import_mode": "BYTE_IDENTICAL_READ_ONLY_IMPORT",
            "fourth_review_forbidden": True,
            "content_rules": {
                "approved_primary_plus_no_secondary_block": "COUNT_TOWARD_FINAL_300_POSITIVE",
                "merge": "MERGE_NOT_SEPARATELY_COUNTED",
                "minor_revision_or_secondary_rework": "HOLD_FOR_REPAIR",
                "veto": "REJECT",
            },
            "route_rules": {
                "gold_before_actual_comparison": True,
                "actual_may_not_define_or_modify_gold": True,
            },
            "component_rules": {
                "historical_edges_remain_non_active": True,
                "secondary_not_approved_lifecycle_blocks_activation": True,
                "control_rules_not_content_components": True,
            },
            "creative_channel_boundary": {
                "source_lane_or_pair_requires_source_evidence": True,
                "historical_b_channel_path_is_not_lane_evidence": True,
                "optional_lane_applicability_is_nonblocking": True,
            },
            "readiness": {
                "candidatepack_ready": False,
                "KE_ready": False,
                "RAG_ready": False,
                "DIFY_ready": False,
                "production_servable": False,
                "generation_eligible": False,
                "generation_allowed": False,
                "release_ready": False,
                "production_ready": False,
            },
        }
    }
    document = contract["p1b_signed_review_closeout_contract"]
    document["contract_digest"] = object_digest(document, "contract_digest")
    return contract


def owner_document(
    result_state: str,
    counted_positive: int,
    active_component_count: int,
) -> dict[str, Any]:
    owner: dict[str, Any] = {
        "current_gate1_owner": {
            "schema_version": "v0.1",
            "owner_id": "GATE1_V11_P1B_CURRENT_OWNER",
            "task_id": TASK_ID,
            "baseline_commit": P1B_BASELINE_COMMIT,
            "current_task_root": TASK_ROOT.as_posix(),
            "current_checker": CURRENT_CHECKER_PATH.as_posix(),
            "p1a_as_built_protection": {
                "p1a_task_id": P1A_TASK_ID,
                "p1a_materializer_path": P1A_MATERIALIZER_PATH.as_posix(),
                "p1a_current_checker_as_built_sha256": P1A_CURRENT_CHECKER_AS_BUILT_SHA256,
                "p1a_generated_outputs_must_remain_byte_identical": True,
            },
            "protected_inputs": {
                "standard_source": STANDARD_SNAPSHOT_PATH.as_posix(),
                "clean_120_source": CLEAN_120_PATH.as_posix(),
                "route_input_source": ROUTE_INPUT_PATH.as_posix(),
                "route_actual_source": ROUTE_ACTUAL_PATH.as_posix(),
                "component_source": COMPONENT_SOURCE_PATH.as_posix(),
                "profile_source": PROFILE_PATH.as_posix(),
            },
            "p1b_closeout": {
                "result_state": result_state,
                "counted_positive_parent_count": counted_positive,
                "active_component_count": active_component_count,
                "p2_allowed_by_p1b": result_state == "PASS_TO_P2",
            },
            "current_ledger_authority": {
                "checker_path": "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001/phase_0/check_current_ledger_owner.py",
                "shared_horizon_modified": False,
                "terminal_derivation": "delegated_to_existing_owner",
            },
            "readiness": {
                "changed": False,
                "generation_allowed": False,
                "generator_qualified": False,
                "runtime_ingest_ready": False,
                "production_ready": False,
            },
        }
    }
    return owner


def compatibility_receipt(root: Path) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "p1b_historical_identity_repair_receipt": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "p1a_materializer_reference_safe_change": {
                "path": P1A_MATERIALIZER_PATH.as_posix(),
                "sha256_before": P1A_MATERIALIZER_BEFORE_SHA256,
                "sha256_after": sha256_file(root / P1A_MATERIALIZER_PATH),
                "historical_current_checker_sha256": P1A_CURRENT_CHECKER_AS_BUILT_SHA256,
                "p1a_generated_output_bytes_changed": False,
            },
            "current_gate1_checker_successor": {
                "path": CURRENT_CHECKER_PATH.as_posix(),
                "sha256_before": P1A_CURRENT_CHECKER_AS_BUILT_SHA256,
                "sha256_after": P1B_CURRENT_CHECKER_AS_BUILT_SHA256,
                "must_reject": [
                    "filled_record_fake_lane_or_pair",
                    "historical_b_channel_path_inference",
                    "current_actual_changes_gold_answer",
                    "manual_count_or_readiness_flip",
                    "historical_edge_revival",
                ],
            },
            "modified_live_checker_count": 1,
            "historical_assets_rewritten": False,
        }
    }
    document = receipt["p1b_historical_identity_repair_receipt"]
    document["receipt_digest"] = object_digest(document, "receipt_digest")
    return receipt


def closeout_result(
    content_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    component_rows: list[dict[str, Any]],
    supply: dict[str, Any],
) -> dict[str, Any]:
    supply_document = supply["component_supply_gap_matrix"]
    incomplete = supply_document["incomplete_profile_count"]
    result_state = "STOPPED_COMPONENT_SUPPLY_GAP" if incomplete else "PASS_TO_P2"
    result: dict[str, Any] = {
        "p1b_signed_review_closeout_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "result_state": result_state,
            "p1b_evidence_closeout_complete": True,
            "p2_allowed": result_state == "PASS_TO_P2",
            "core_number_impact": {
                "target_total": 300,
                "legacy_reference_inventory": 120,
                "counted_positive_parent_count": sum(
                    row["final_disposition"] == "COUNT_TOWARD_FINAL_300_POSITIVE"
                    for row in content_rows
                ),
                "component_candidate_inventory": 86,
                "active_component_count": sum(
                    row["final_disposition"] == "KEEP_ACTIVE_FOR_GATE1_DEVELOPMENT_TEST"
                    for row in component_rows
                ),
                "route_case_count": len(gold_rows),
                "route_current_comparison_count": len(comparison_rows),
            },
            "content_closeout_complete": len(content_rows) == 120,
            "route_gold_frozen_before_actual_comparison": True,
            "component_supply_complete_profile_count": supply_document[
                "complete_profile_count"
            ],
            "component_supply_incomplete_profile_count": incomplete,
            "canonical_composition_plan_count": 0,
            "runtime_generation_eligible_profile_count": 0,
            "readiness": {
                "candidatepack_ready": False,
                "KE_ready": False,
                "RAG_ready": False,
                "DIFY_ready": False,
                "production_servable": False,
                "generation_eligible": False,
                "generation_allowed": False,
                "release_ready": False,
                "production_ready": False,
                "generator_qualified": False,
            },
        }
    }
    document = result["p1b_signed_review_closeout_result"]
    document["result_digest"] = object_digest(document, "result_digest")
    return result


def output_bytes(root: Path) -> dict[Path, bytes]:
    state = source_state(root)
    reviews = imported_reviews(root, state)
    normalized = normalized_records(reviews)
    content_rows, content_gaps = derive_content(state, reviews)
    gold_rows, gold_freeze = derive_route_gold(reviews, state)
    # The golden bytes exist before this function touches the current actuals.
    gold_bytes = jsonl_bytes(gold_rows)
    require(
        sha256_bytes(gold_bytes)
        == gold_freeze["route_60_gold_freeze_manifest"]["gold_answers_sha256"],
        "E_ROUTE_GOLD_FREEZE",
    )
    comparison_rows = derive_route_comparison(
        route_actual_state(root, state), gold_rows
    )
    component_rows, active_components, active_edges, supply, test_inputs = (
        derive_components(state, reviews)
    )
    result = closeout_result(
        content_rows, gold_rows, comparison_rows, component_rows, supply
    )
    return {
        IMPORT_MANIFEST_PATH: yaml_bytes(import_manifest()),
        CONTRACT_PATH: yaml_bytes(closeout_contract()),
        NORMALIZED_PATH: jsonl_bytes(normalized),
        CONTENT_DISPOSITIONS_PATH: jsonl_bytes(content_rows),
        CONTENT_GAPS_PATH: yaml_bytes(content_gaps),
        ROUTE_GOLD_PATH: gold_bytes,
        ROUTE_GOLD_FREEZE_PATH: yaml_bytes(gold_freeze),
        ROUTE_COMPARISON_PATH: jsonl_bytes(comparison_rows),
        COMPONENT_DISPOSITIONS_PATH: jsonl_bytes(component_rows),
        ACTIVE_COMPONENTS_PATH: jsonl_bytes(active_components),
        ACTIVE_EDGES_PATH: jsonl_bytes(active_edges),
        COMPONENT_GAPS_PATH: yaml_bytes(supply),
        TEST_INPUT_MANIFEST_PATH: yaml_bytes(test_inputs),
        COMPAT_RECEIPT_PATH: yaml_bytes(compatibility_receipt(root)),
        RESULT_PATH: yaml_bytes(result),
    }


def write_outputs(root: Path) -> list[str]:
    import_signed_inputs(root)
    manifest_target = root / IMPORT_MANIFEST_PATH
    manifest_target.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = yaml_bytes(import_manifest())
    if not manifest_target.exists() or manifest_target.read_bytes() != manifest_bytes:
        manifest_target.write_bytes(manifest_bytes)
    written: list[str] = []
    for relative_path, content in output_bytes(root).items():
        require(
            allowed_write_path(relative_path),
            "E_UNAUTHORIZED_PATH",
            relative_path.as_posix(),
        )
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
            written.append(relative_path.as_posix())
    return written


def check_outputs(root: Path) -> list[str]:
    mismatches: list[str] = []
    for relative_path, content in output_bytes(root).items():
        path = root / relative_path
        if not path.exists() or path.read_bytes() != content:
            mismatches.append(relative_path.as_posix())
    return mismatches


def allowed_write_path(path: Path) -> bool:
    return path.is_relative_to(TASK_ROOT)


def copy_fixture(root: Path, target: Path) -> None:
    paths = (
        P1A_ROOT,
        TASK_ROOT,
        CLEAN_120_PATH,
        ROUTE_INPUT_PATH,
        ROUTE_ACTUAL_PATH,
        COMPONENT_SOURCE_PATH,
        PROFILE_PATH,
        CURRENT_OWNER_PATH,
        CURRENT_CHECKER_PATH,
    )
    for relative_path in paths:
        source = root / relative_path
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def mutate_yaml(path: Path, mutate: Any) -> None:
    document = load_yaml(path)
    mutate(document)
    path.write_bytes(yaml_bytes(document))


def mutate_jsonl(path: Path, mutate: Any) -> None:
    rows = [row for row, _ in read_jsonl(path)]
    mutate(rows)
    path.write_bytes(jsonl_bytes(rows))


def expect_failure(root: Path, name: str, mutate: Any, expected: str) -> str | None:
    with tempfile.TemporaryDirectory(prefix=f"gate1-p1b-{name}-") as temporary:
        fixture = Path(temporary)
        copy_fixture(root, fixture)
        mutate(fixture)
        try:
            mismatches = check_outputs(fixture)
        except (
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            yaml.YAMLError,
        ) as exc:
            if expected in str(exc):
                return None
            return f"{name}: expected {expected}, got {exc}"
        if any(expected in mismatch for mismatch in mismatches):
            return None
        return f"{name}: expected {expected}, got {mismatches or 'success'}"


def expect_direct_failure(name: str, action: Any, expected: str) -> str | None:
    try:
        action()
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        if expected in str(exc):
            return None
        return f"{name}: expected {expected}, got {exc}"
    return f"{name}: expected {expected}, got success"


def selftest(root: Path) -> int:
    baseline_mismatches = check_outputs(root)
    if baseline_mismatches:
        print(
            json.dumps(
                {"status": "SELFTEST_BASE_INVALID", "mismatches": baseline_mismatches},
                ensure_ascii=False,
            )
        )
        return 1
    failures: list[str] = []
    tests: tuple[tuple[str, Any, str], ...] = (
        (
            "signed_import_byte_mutation",
            lambda temp: (
                temp / IMPORT_ROOT / "independent_reviews/primary/records.jsonl"
            ).write_bytes(
                (
                    temp / IMPORT_ROOT / "independent_reviews/primary/records.jsonl"
                ).read_bytes()
                + b"\n"
            ),
            "E_IMPORT_HASH",
        ),
        (
            "manual_positive_count",
            lambda temp: mutate_yaml(
                temp / RESULT_PATH,
                lambda value: value["p1b_signed_review_closeout_result"][
                    "core_number_impact"
                ].update({"counted_positive_parent_count": 999}),
            ),
            "result/p1b_signed_review_closeout_result.v0.1.yaml",
        ),
        (
            "readiness_flip",
            lambda temp: mutate_yaml(
                temp / RESULT_PATH,
                lambda value: value["p1b_signed_review_closeout_result"][
                    "readiness"
                ].update({"generation_allowed": True}),
            ),
            "result/p1b_signed_review_closeout_result.v0.1.yaml",
        ),
        (
            "gold_answer_mutation",
            lambda temp: mutate_jsonl(
                temp / ROUTE_GOLD_PATH,
                lambda rows: rows[0].update({"gold_reason_code": "伪造原因"}),
            ),
            "route/route_60_gold_answers.v0.1.jsonl",
        ),
        (
            "historical_edge_revival",
            lambda temp: mutate_jsonl(
                temp / ACTIVE_EDGES_PATH,
                lambda rows: rows.append(
                    {
                        "component_id": "RCV2-002-ACTION-01-KNIT-RECOVERY-CHECK",
                        "content_product_id": "CP01",
                        "component_role": "observable_action",
                        "signed_edge_evidence": True,
                        "new_generator_consumable": True,
                    }
                ),
            ),
            "component/active_gate1_development_edges.v0.1.jsonl",
        ),
    )
    for name, mutate, expected in tests:
        failure = expect_failure(root, name, mutate, expected)
        if failure is not None:
            failures.append(failure)
    state = source_state(root)
    reviews = imported_reviews(root, state)
    filled_primary = deep_copy(reviews["primary"][0])
    filled_primary["object"]["source_generation_lane_or_pair_ref"] = "B-LANE-FAKE"
    failure = expect_direct_failure(
        "filled_record_fake_lane",
        lambda: validate_channel_fields(filled_primary, "E_PRIMARY_CHANNEL"),
        "E_CHANNEL_PROVENANCE",
    )
    if failure is not None:
        failures.append(failure)
    filled_b_channel = deep_copy(reviews["primary"][0])
    filled_b_channel["object"]["source_generation_lane_or_pair_ref"] = "B-LANE-FAKE"
    filled_b_channel["object"]["source_refs"] = ["historical/b_channel/not-evidence"]
    failure = expect_direct_failure(
        "historical_b_channel_path_inference",
        lambda: validate_channel_fields(filled_b_channel, "E_PRIMARY_CHANNEL"),
        "E_CHANNEL_PATH_INFERENCE",
    )
    if failure is not None:
        failures.append(failure)
    invalidated_primary = deep_copy(reviews["primary"][0])
    invalidated_primary["identity"]["reviewer_identity_id"] = (
        "gate1_primary_independent_review_initial_session"
    )
    failure = expect_direct_failure(
        "invalidated_identity_cannot_contribute",
        lambda: validate_identity_isolation(
            [invalidated_primary],
            reviews["secondary"],
            reviews["adjudication"],
            reviews["invalidations"],
        ),
        "E_INVALIDATED_OR_FREEZER_IDENTITY",
    )
    if failure is not None:
        failures.append(failure)
    identity_collision_secondary = deep_copy(reviews["secondary"][0])
    primary_identity_record = reviews["primary"][0]["identity"]
    identity_collision_secondary["reviewer"].update(
        {
            "reviewer_identity_id": primary_identity_record["reviewer_identity_id"],
            "reviewer_instance_or_session_id": primary_identity_record[
                "reviewer_instance_or_session_id"
            ],
            "review_run_id": primary_identity_record["review_run_id"],
        }
    )
    failure = expect_direct_failure(
        "reviewer_identity_collision",
        lambda: validate_identity_isolation(
            [reviews["primary"][0]],
            [identity_collision_secondary],
            reviews["adjudication"],
            reviews["invalidations"],
        ),
        "E_REVIEWER_IDENTITY_COLLISION",
    )
    if failure is not None:
        failures.append(failure)
    missing_primary_field = deep_copy(reviews["primary"][0])
    missing_primary_field["identity"].pop("review_role")
    failure = expect_direct_failure(
        "missing_signed_review_field",
        lambda: validate_primary_record(missing_primary_field, state),
        "E_PRIMARY_SCHEMA",
    )
    if failure is not None:
        failures.append(failure)
    if allowed_write_path(Path("outside_p1b/unapproved.txt")):
        failures.append("unapproved_write_path_must_be_rejected")
    gold_rows, _ = derive_route_gold(reviews, state)
    changed_actuals = copy.deepcopy(route_actual_state(root, state))
    first_case = next(iter(changed_actuals))
    changed_row, raw_line = changed_actuals[first_case]
    changed_row["actual_decision"]["actual_primary_reason_code"] = (
        "MUTATED_CURRENT_IMPLEMENTATION"
    )
    changed_actuals[first_case] = (changed_row, raw_line)
    original_gold = jsonl_bytes(gold_rows)
    changed_gold = jsonl_bytes(derive_route_gold(reviews, state)[0])
    if original_gold != changed_gold:
        failures.append("actual_change_must_not_change_gold")
    if derive_route_comparison(
        route_actual_state(root, state), gold_rows
    ) == derive_route_comparison(changed_actuals, gold_rows):
        failures.append("actual_change_must_change_comparison")
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
                "negative_case_count": len(tests) + 8,
                "gold_is_independent_from_current_actuals": True,
                "readiness_flip_rejected": True,
                "filled_record_channel_forgery_rejected": True,
                "historical_b_channel_inference_rejected": True,
                "invalidated_identity_rejected": True,
                "reviewer_identity_collision_rejected": True,
                "missing_signed_review_field_rejected": True,
                "unapproved_write_path_rejected": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify existing deterministic outputs without writing",
    )
    parser.add_argument(
        "--selftest", action="store_true", help="run negative tamper tests"
    )
    args = parser.parse_args()
    try:
        if args.selftest:
            return selftest(ROOT)
        if args.check:
            mismatches = check_outputs(ROOT)
            if mismatches:
                print(
                    json.dumps(
                        {"status": "CHECK_FAIL", "mismatches": mismatches},
                        ensure_ascii=False,
                    )
                )
                return 1
            print(
                json.dumps(
                    {"status": "CHECK_PASS", "task_id": TASK_ID}, ensure_ascii=False
                )
            )
            return 0
        written = write_outputs(ROOT)
        print(
            json.dumps(
                {"status": "MATERIALIZED", "written": written}, ensure_ascii=False
            )
        )
        return 0
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        print(
            json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
