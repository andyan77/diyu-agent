#!/usr/bin/env python3
"""Current successor guard for legal P4 failure and author-interface recovery."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from author_contract import ROOT, TASK_ID, object_digest, read_jsonl, serialize_all, sha256_file
from run_open_recovery import (
    OLD_P4_ROOT,
    OWNER,
    RESEALED_ROOT,
    TASK_ROOT,
    _strict_reject_second_p4,
    _strict_validate_first_p4,
)


if not __debug__:
    sys.stderr.write("recovery_guard refuses python -O\n")
    raise SystemExit(2)


OLD_P4_TREE = "404a77ec7f59e0ce639daddbcd3c8d658d9bed5b"
RESEALED_P4_TREE = "0d51df3fbd122173f3848d8e87ccc3a7253e963f"
RECOVERY_BASELINE = "f42c1978e5adda2c475071723c5f44b14741691a"
P3_RECOVERY_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p3_route_input_compiler_recovery_001"
)
P3_RECOVERY_TREE = "9bdbbe6864c8afd5942b8dfe827bab2f0522907a"
THIRD_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_third_sealed_hidden_probe40_001"
)
PINNED_FILES = {
    OLD_P4_ROOT.relative_to(ROOT) / "freeze/positive_author_requests_20.v0.1.jsonl": "82ecdbdaebd90b6cdfe24a0bf9e3b882244dfdab2a1d72941a20ea4c8d4f4749",
    OLD_P4_ROOT.relative_to(ROOT) / "run/positive_20_first_outputs.v0.1.jsonl": "17c7da686a52252897e57313707b6947283585b26595d6df00be21b6bc611a65",
    RESEALED_ROOT.relative_to(ROOT) / "freeze/positive_author_requests_20.v1.0.jsonl": "744d8f3d53452a92269bee29e4eb43228e8685389de7cd80fa0227bb9bbe6037",
    RESEALED_ROOT.relative_to(ROOT) / "run/positive_20_first_outputs.v1.0.jsonl": "b1a9a608d7cce325fe886ff88cdf23d5769a441439f58e3ced8a69c16ebff25b",
    RESEALED_ROOT.relative_to(ROOT) / "audit/author_output_contract_failure.v1.0.yaml": "75f020461684299d3a1ecc3507a01684a1ca33fd61d242a032d8a2a2de0b9f1e",
    RESEALED_ROOT.relative_to(ROOT) / "result/p4_resealed_lifecycle.v1.0.yaml": "d00c6f18876c448cd818ba96cc37a269d5a58e8fdba0c8ff3f0b0973c915617e",
}
READY_KEYS = {
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
    "runtime_ingest_ready",
}


def _add(errors: list[dict[str, str]], code: str, detail: str = "") -> None:
    errors.append({"code": code, "detail": detail})


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path.as_posix())
    return value


def _git_tree(root: Path, relative: Path) -> str:
    if not (root / ".git").exists():
        return ""
    result = subprocess.run(
        ["git", "rev-parse", f"HEAD:{relative.as_posix()}"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _recursive_true(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in READY_KEYS and child is True:
                found.append(key)
            found.extend(_recursive_true(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_recursive_true(child))
    return found


def validate_legacy_failure(root: Path, errors: list[dict[str, str]]) -> None:
    for relative, expected in PINNED_FILES.items():
        candidate = root / relative
        if not candidate.is_file() or sha256_file(candidate) != expected:
            _add(errors, "E_RECOVERY_PRIOR_FILE_DRIFT", relative.as_posix())
    if (root / ".git").exists():
        if _git(root, "merge-base", "--is-ancestor", RECOVERY_BASELINE, "HEAD").returncode != 0:
            _add(errors, "E_RECOVERY_BASELINE_ANCESTRY")
        old_tree = _git_tree(root, OLD_P4_ROOT.relative_to(ROOT))
        resealed_tree = _git_tree(root, RESEALED_ROOT.relative_to(ROOT))
        p3_recovery_tree = _git_tree(root, P3_RECOVERY_ROOT)
        if old_tree != OLD_P4_TREE:
            _add(errors, "E_RECOVERY_OLD_P4_TREE", old_tree)
        if resealed_tree != RESEALED_P4_TREE:
            _add(errors, "E_RECOVERY_RESEALED_P4_TREE", resealed_tree)
        if p3_recovery_tree != P3_RECOVERY_TREE:
            _add(errors, "E_RECOVERY_P3_RECOVERY_TREE", p3_recovery_tree)
        prior_owner = _git(
            root,
            "show",
            f"{RECOVERY_BASELINE}:{OWNER.relative_to(ROOT).as_posix()}",
        )
        if prior_owner.returncode != 0:
            _add(errors, "E_RECOVERY_PRIOR_OWNER_MISSING")
        else:
            prior = yaml.safe_load(prior_owner.stdout).get("current_gate1_owner", {})
            if (
                prior.get("owner_id") != "GATE1_V11_P4_RESEALED_STOPPED_OWNER"
                or prior.get("result_state") != "STOPPED_RETURN_TO_P3"
                or prior.get("same_hidden_batch_may_be_reused") is not False
                or prior.get("H_admitted_count", 0) != 0
                or prior.get("generator_qualified", False) is not False
                or prior.get("p5_allowed", False) is not False
                or _recursive_true(prior)
            ):
                _add(errors, "E_RECOVERY_PRIOR_OWNER_BOUNDARY")
    try:
        failure = _load_yaml(
            root
            / RESEALED_ROOT.relative_to(ROOT)
            / "audit/author_output_contract_failure.v1.0.yaml"
        ).get("p4_resealed_author_output_contract_failure")
        lifecycle = _load_yaml(
            root
            / RESEALED_ROOT.relative_to(ROOT)
            / "result/p4_resealed_lifecycle.v1.0.yaml"
        ).get("p4_resealed_lifecycle")
        if not isinstance(failure, dict) or not isinstance(lifecycle, dict):
            raise TypeError("prior failure structures")
        if (
            failure.get("first_failure_code") != "E_P4_SURFACE_FIELDS"
            or failure.get("captured_first_output_count") != 20
            or failure.get("human_review_started") is not False
            or failure.get("hidden_exposed") is not True
            or failure.get("recovery_requires_third_fresh_hidden_set") is not True
        ):
            _add(errors, "E_RECOVERY_PRIOR_FAILURE_RECORD")
        if (
            lifecycle.get("state") != "STOPPED_RETURN_TO_P3"
            or lifecycle.get("first_failure_code") != "E_P4_SURFACE_FIELDS"
            or lifecycle.get("hidden_exposed") is not True
            or lifecycle.get("same_hidden_batch_may_be_reused") is True
            or lifecycle.get("human_review_started") is not False
            or lifecycle.get("H_admitted_count") != 0
            or lifecycle.get("generator_qualified") is not False
            or lifecycle.get("p5_allowed") is not False
            or lifecycle.get("readiness_true_keys") != []
        ):
            _add(errors, "E_RECOVERY_PRIOR_LIFECYCLE")
        review_files = list(
            (root / RESEALED_ROOT.relative_to(ROOT) / "review").glob("signed_*")
        )
        if review_files:
            _add(errors, "E_RECOVERY_PRIOR_FAKE_REVIEW")
        if not errors and root == ROOT:
            code = _strict_reject_second_p4()
            if code != "E_P4_SURFACE_FIELDS":
                _add(errors, "E_RECOVERY_PRIOR_FAILURE_REPLAY", code)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        _add(errors, "E_RECOVERY_PRIOR_FAILURE_PARSE", str(exc))


def validate_open_recovery(
    root: Path,
    errors: list[dict[str, str]],
    *,
    validate_owner: bool = True,
) -> None:
    required = (
        TASK_ROOT / "author_contract.py",
        TASK_ROOT / "build_public_requests.py",
        TASK_ROOT / "run_open_recovery.py",
        TASK_ROOT / "recovery_guard.py",
        TASK_ROOT / "contract/author_semantic_output_contract.v1.0.json",
        TASK_ROOT / "contract/controlled_author_instruction.v1.0.md",
        TASK_ROOT / "public/public_author_requests_20.v1.0.jsonl",
        TASK_ROOT / "public/public_author_raw_outputs_20.v1.0.jsonl",
        TASK_ROOT / "public/public_author_outputs_20.v1.0.jsonl",
        TASK_ROOT / "result/open_recovery_result.v1.0.yaml",
        TASK_ROOT / "audit/external_exit_audit.v1.0.yaml",
    )
    for relative in required:
        if not (root / relative).is_file():
            _add(errors, "E_RECOVERY_REQUIRED", relative.as_posix())
    if errors:
        return
    try:
        requests = read_jsonl(root / TASK_ROOT / "public/public_author_requests_20.v1.0.jsonl")
        raws = read_jsonl(root / TASK_ROOT / "public/public_author_raw_outputs_20.v1.0.jsonl")
        expected_outputs = serialize_all(raws, requests)
        actual_outputs = read_jsonl(root / TASK_ROOT / "public/public_author_outputs_20.v1.0.jsonl")
        if expected_outputs != actual_outputs:
            _add(errors, "E_RECOVERY_PUBLIC_REBUILD")
        result = _load_yaml(root / TASK_ROOT / "result/open_recovery_result.v1.0.yaml").get("open_recovery_result")
        audit = _load_yaml(root / TASK_ROOT / "audit/external_exit_audit.v1.0.yaml").get("external_exit_audit")
        if not isinstance(result, dict) or result.get("result_digest") != object_digest(result, "result_digest"):
            _add(errors, "E_RECOVERY_RESULT_DIGEST")
        elif (
            result.get("result_state") != "OPEN_RECOVERY_COMPLETE"
            or result.get("public_probe_strict_pass_count") != 20
            or result.get("first_p4_legal_regression_pass_count") != 20
            or result.get("second_p4_malformed_rejected_count") != 20
            or result.get("second_p4_first_failure_code") != "E_P4_SURFACE_FIELDS"
            or result.get("third_hidden_created") is not False
            or result.get("H_admitted_count") != 0
            or result.get("generator_qualified") is not False
            or result.get("p5_allowed") is not False
            or result.get("core_number_impact") != {"300": 0, "120": 0, "86": 0}
            or result.get("readiness_true_keys") != []
        ):
            _add(errors, "E_RECOVERY_RESULT_BOUNDARY")
        if not isinstance(audit, dict) or audit.get("audit_digest") != object_digest(audit, "audit_digest"):
            _add(errors, "E_RECOVERY_AUDIT_DIGEST")
        elif (
            audit.get("external_api_call_count") != len(audit.get("observed_content_exit_events", []))
            or audit.get("external_api_call_count") != 0
            or audit.get("credential_read_count") != 0
            or audit.get("network_dispatch_count") != 0
        ):
            _add(errors, "E_RECOVERY_EXTERNAL_EXIT")
        if validate_owner:
            owner = _load_yaml(root / OWNER.relative_to(ROOT)).get("current_gate1_owner")
            if not isinstance(owner, dict) or owner.get("owner_digest") != object_digest(owner, "owner_digest"):
                _add(errors, "E_OWNER_POLICY", "successor owner digest")
            elif (
                owner.get("owner_id") != "GATE1_V11_P4_AUTHOR_OUTPUT_RECOVERY_OPEN_OWNER"
                or owner.get("task_id") != TASK_ID
                or owner.get("result_state") != "OPEN_RECOVERY_COMPLETE"
                or owner.get("third_hidden_created") is not False
                or owner.get("H_admitted_count") != 0
                or owner.get("generator_qualified") is not False
                or owner.get("p5_allowed") is not False
                or owner.get("core_numbers")
                != {
                    "target_total": 300,
                    "reference_inventory": 120,
                    "historical_component_inventory": 86,
                    "all_unchanged": True,
                }
                or _recursive_true(owner)
            ):
                _add(errors, "E_OWNER_POLICY", "successor owner boundary")
        if root == ROOT:
            _strict_validate_first_p4()
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        _add(errors, "E_RECOVERY_OPEN_PARSE", str(exc))


def _load_third_guard(root: Path) -> Any:
    third_dir = root / THIRD_ROOT
    path = third_dir / "third_p4_guard.py"
    sys.path.insert(0, str(third_dir))
    sys.modules.pop("third_p4", None)
    sys.modules.pop("gate1_third_p4_guard_current", None)
    spec = importlib.util.spec_from_file_location("gate1_third_p4_guard_current", path)
    if spec is None or spec.loader is None:
        raise ImportError(path.as_posix())
    module = importlib.util.module_from_spec(spec)
    sys.modules["gate1_third_p4_guard_current"] = module
    spec.loader.exec_module(module)
    return module


def validate_recovery(root: Path = ROOT) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    validate_legacy_failure(root, errors)
    third_exists = (root / THIRD_ROOT / "third_p4_guard.py").is_file()
    validate_open_recovery(root, errors, validate_owner=not third_exists)
    if third_exists:
        try:
            errors.extend(_load_third_guard(root).validate_third_p4(root))
        except (ImportError, OSError, TypeError, ValueError) as exc:
            _add(errors, "E_RECOVERY_THIRD_GUARD", str(exc))
    return errors


def selftest(root: Path = ROOT) -> int:
    baseline = validate_recovery(root)
    if baseline:
        print(json.dumps({"status": "SELFTEST_SETUP_FAIL", "errors": baseline}, ensure_ascii=False))
        return 1
    failures: list[dict[str, str]] = []
    third_exists = (root / THIRD_ROOT / "third_p4_guard.py").is_file()

    def validate_historical_and_open(target: Path) -> list[dict[str, str]]:
        local_errors: list[dict[str, str]] = []
        validate_legacy_failure(target, local_errors)
        validate_open_recovery(target, local_errors, validate_owner=False)
        return local_errors
    def copy_case() -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        target = Path(directory.name)
        for source_relative in (
            OLD_P4_ROOT.relative_to(ROOT),
            RESEALED_ROOT.relative_to(ROOT),
            P3_RECOVERY_ROOT,
            TASK_ROOT,
        ):
            shutil.copytree(root / source_relative, target / source_relative)
        owner_target = target / OWNER.relative_to(ROOT)
        owner_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / OWNER.relative_to(ROOT), owner_target)
        return directory, target

    def write_bound_yaml(path: Path, root_key: str, digest_key: str, mutate: Any) -> None:
        document = _load_yaml(path)
        value = document[root_key]
        mutate(value)
        value[digest_key] = object_digest(value, digest_key)
        path.write_text(
            yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=110),
            encoding="utf-8",
        )

    byte_mutations = (
        (RESEALED_ROOT.relative_to(ROOT) / "audit/author_output_contract_failure.v1.0.yaml", b"\n# tamper failure code\n", "failure_audit_tamper"),
        (RESEALED_ROOT.relative_to(ROOT) / "run/positive_20_first_outputs.v1.0.jsonl", b"\n", "output_digest_tamper"),
        (TASK_ROOT / "public/public_author_raw_outputs_20.v1.0.jsonl", b"\n{}\n", "public_raw_tamper"),
    )
    for relative, suffix, name in byte_mutations:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for source_relative in (
                OLD_P4_ROOT.relative_to(ROOT),
                RESEALED_ROOT.relative_to(ROOT),
                P3_RECOVERY_ROOT,
                TASK_ROOT,
            ):
                shutil.copytree(root / source_relative, target / source_relative)
            owner_target = target / OWNER.relative_to(ROOT)
            owner_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / OWNER.relative_to(ROOT), owner_target)
            candidate = target / relative
            candidate.write_bytes(candidate.read_bytes() + suffix)
            if not validate_historical_and_open(target):
                failures.append({"case": name, "error": "false negative"})

    directory, target = copy_case()
    try:
        fake_review = target / RESEALED_ROOT.relative_to(ROOT) / "review/signed_fake.json"
        fake_review.parent.mkdir(parents=True, exist_ok=True)
        fake_review.write_text("{}\n", encoding="utf-8")
        if not validate_historical_and_open(target):
            failures.append({"case": "fake_review", "error": "false negative"})
    finally:
        directory.cleanup()
    if third_exists and _load_third_guard(root).selftest(root) != 0:
        failures.append({"case": "third_guard_selftest", "error": "failed"})
    if failures:
        print(json.dumps({"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "SELFTEST_PASS",
                "negative_case_count": len(byte_mutations)
                + 1,
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
    errors = validate_recovery(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False))
        return 1
    owner = _load_yaml(ROOT / OWNER.relative_to(ROOT)).get("current_gate1_owner", {})
    print(
        json.dumps(
            {
                "status": "PASS",
                "task_id": owner.get("task_id", TASK_ID),
                "state": owner.get("result_state", "OPEN_RECOVERY_COMPLETE"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
