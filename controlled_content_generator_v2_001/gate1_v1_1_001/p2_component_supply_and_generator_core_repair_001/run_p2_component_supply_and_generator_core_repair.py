#!/usr/bin/env python3
"""Run or verify the deterministic P2 component-review checkpoint."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from p2_checkpoint_documents import build_documents, validate_documents
from p2_component_model import (
    AB_PATH,
    ADDITION_PATH,
    COMPONENT_CANDIDATES_PATH,
    CONTROL_RULES_PATH,
    CURRENT_OWNER_PATH,
    EDGE_PATH,
    RESULT_PATH,
    REVIEW_PACKET_PATH,
    ROOT,
    SUCCESSOR_PATH,
    TASK_ROOT,
    canonical_json,
    load_jsonl,
    object_digest,
    require,
    source_state,
)
from p2_final_documents import build_generator_evidence
from p2_final_documents_r4 import build_generator_evidence_r4
from p2_generator_core import Gate1ValidationError, realize_request
from p2_final_materializer import (
    FINAL_IMPORT_SENTINEL,
    FINAL_RESULT_PATH,
    build_final_documents,
    validate_final_documents,
)
from p2_targeted_repair import (
    TARGETED_RESULT_PATH,
    build_targeted_repair_documents,
    validate_targeted_repair_documents,
)
from p2_targeted_repair_r2 import (
    FINAL_EDGE_CANDIDATES_R2_PATH,
    REVISED_AB_R2_PATH,
    TARGETED_RESULT_R2_PATH,
    build_targeted_repair_r2_documents,
    validate_targeted_repair_r2_documents,
)
from p2_targeted_repair_r3 import (
    ADDITION_CANDIDATES_R3_PATH,
    REVISED_AB_R3_PATH,
    REVISED_COMPONENTS_R3_PATH,
    REVISED_RULES_R3_PATH,
    TARGETED_RESULT_R3_PATH,
    build_targeted_repair_r3_documents,
    validate_targeted_repair_r3_documents,
)
from p2_targeted_repair_r4 import (
    ADDITION_CANDIDATES_R4_PATH,
    REVISED_AB_R4_PATH,
    REVISED_COMPONENTS_R4_PATH,
    REVISED_RULES_R4_PATH,
    TARGETED_RESULT_R4_PATH,
    build_targeted_repair_r4_documents,
    validate_targeted_repair_r4_documents,
)
from p2_generator_core_r4 import (
    Gate1ValidationError as Gate1ValidationErrorR4,
    realize_request as realize_request_r4,
)


if not __debug__:
    sys.stderr.write("P2 materializer refuses python -O\n")
    raise SystemExit(2)


def selected_documents(root: Path, phase: str) -> dict[Path, bytes]:
    if phase == "final":
        documents = build_final_documents(root)
        validate_final_documents(documents)
        return documents
    if phase == "targeted-repair":
        documents = build_targeted_repair_documents(root)
        validate_targeted_repair_documents(documents)
        return documents
    if phase == "targeted-repair-r2":
        documents = build_targeted_repair_r2_documents(root)
        validate_targeted_repair_r2_documents(documents)
        return documents
    if phase == "targeted-repair-r3":
        documents = build_targeted_repair_r3_documents(root)
        validate_targeted_repair_r3_documents(documents)
        return documents
    if phase == "targeted-repair-r4":
        documents = build_targeted_repair_r4_documents(root)
        validate_targeted_repair_r4_documents(documents)
        return documents
    documents = build_documents(root)
    validate_documents(documents)
    return documents


def write_outputs(root: Path, phase: str) -> list[str]:
    documents = selected_documents(root, phase)
    written: list[str] = []
    for relative_path, content in documents.items():
        require(
            relative_path == CURRENT_OWNER_PATH
            or relative_path.is_relative_to(TASK_ROOT),
            "E_WRITE_SURFACE",
            relative_path.as_posix(),
        )
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
            written.append(relative_path.as_posix())
    return written


def check_outputs(root: Path, phase: str) -> list[str]:
    documents = selected_documents(root, phase)
    return [
        path.as_posix()
        for path, content in documents.items()
        if not (root / path).is_file() or (root / path).read_bytes() != content
    ]


def checkpoint_selftest(root: Path) -> int:
    first = build_documents(root)
    second = build_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        ("component_activation", SUCCESSOR_PATH, '"active":false', '"active":true'),
        (
            "control_rule_supply",
            CONTROL_RULES_PATH,
            '"contributes_component_supply":false',
            '"contributes_component_supply":true',
        ),
        (
            "ab_shared_session",
            AB_PATH,
            '"INDEPENDENT_SESSION_B"',
            '"INDEPENDENT_SESSION_A"',
        ),
        ("p3_unlock", RESULT_PATH, "p3_allowed: false", "p3_allowed: true"),
        (
            "core_number_change",
            RESULT_PATH,
            "historical_component_inventory: 86",
            "historical_component_inventory: 87",
        ),
        (
            "source_provenance_removed",
            COMPONENT_CANDIDATES_PATH,
            '"parent_assets":[',
            '"parent_assets_missing":[',
        ),
        (
            "edge_component_unknown",
            EDGE_PATH,
            '"component_id":"',
            '"component_id":"UNKNOWN-',
        ),
        (
            "review_prefilled",
            REVIEW_PACKET_PATH,
            '"prefilled_decision":null',
            '"prefilled_decision":"APPROVE"',
        ),
        (
            "unsupported_addition",
            ADDITION_PATH,
            "necessary_addition_count: 0",
            "necessary_addition_count: 1",
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        text = mutated[path].decode("utf-8")
        require(before in text, "E_SELFTEST_PATTERN", name)
        mutated[path] = text.replace(before, after, 1).encode("utf-8")
        try:
            validate_documents(mutated)
        except (ValueError, KeyError, TypeError):
            continue
        failures.append(name)
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "negative_case_count": len(mutations),
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def final_selftest(root: Path) -> int:
    first = build_final_documents(root)
    second = build_final_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_final_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        (
            "result_readiness",
            FINAL_RESULT_PATH,
            "generator_qualified: false",
            "generator_qualified: true",
        ),
        (
            "result_p3_without_completion",
            FINAL_RESULT_PATH,
            "p2_complete: true",
            "p2_complete: false",
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        content = mutated[path].decode("utf-8")
        require(before in content, "E_FINAL_SELFTEST_PATTERN", name)
        mutated[path] = content.replace(before, after, 1).encode("utf-8")
        try:
            validate_final_documents(mutated)
        except (ValueError, KeyError, TypeError):
            continue
        failures.append(name)
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "phase": "final",
                "negative_case_count": len(mutations),
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def targeted_repair_selftest(root: Path) -> int:
    first = build_targeted_repair_documents(root)
    second = build_targeted_repair_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_targeted_repair_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        (
            "early_p3",
            TARGETED_RESULT_PATH,
            "p3_allowed: false",
            "p3_allowed: true",
        ),
        (
            "number_target",
            TARGETED_RESULT_PATH,
            "historical_component_inventory: 86",
            "historical_component_inventory: 87",
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        content = mutated[path].decode("utf-8")
        require(before in content, "E_REPAIR_SELFTEST_PATTERN", name)
        mutated[path] = content.replace(before, after, 1).encode("utf-8")
        try:
            validate_targeted_repair_documents(mutated)
        except (ValueError, KeyError, TypeError):
            continue
        failures.append(name)
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "phase": "targeted-repair",
                "negative_case_count": len(mutations),
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def targeted_repair_r2_selftest(root: Path) -> int:
    first = build_targeted_repair_r2_documents(root)
    second = build_targeted_repair_r2_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_targeted_repair_r2_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        (
            "early_p3",
            TARGETED_RESULT_R2_PATH,
            "p3_allowed: false",
            "p3_allowed: true",
        ),
        (
            "number_target",
            TARGETED_RESULT_R2_PATH,
            "historical_component_inventory: 86",
            "historical_component_inventory: 87",
        ),
        (
            "typed_object_binding",
            FINAL_EDGE_CANDIDATES_R2_PATH,
            '"object_id":"LOCAL-',
            '"object_id":"TAMPERED-',
        ),
        (
            "axis_operator",
            REVISED_AB_R2_PATH,
            '"operator_component_id":"G1V11-P2-AXIS-',
            '"operator_component_id":"UNKNOWN-AXIS-',
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        content = mutated[path].decode("utf-8")
        require(before in content, "E_REPAIR_R2_SELFTEST_PATTERN", name)
        mutated[path] = content.replace(before, after, 1).encode("utf-8")
        try:
            validate_targeted_repair_r2_documents(mutated)
        except (ValueError, KeyError, StopIteration, TypeError):
            continue
        failures.append(name)
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "phase": "targeted-repair-r2",
                "negative_case_count": len(mutations),
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def targeted_repair_r3_selftest(root: Path) -> int:
    first = build_targeted_repair_r3_documents(root)
    second = build_targeted_repair_r3_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_targeted_repair_r3_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        (
            "early_p3",
            TARGETED_RESULT_R3_PATH,
            "p3_allowed: false",
            "p3_allowed: true",
        ),
        (
            "unreviewed_axis_value",
            ADDITION_CANDIDATES_R3_PATH,
            '"unknown_value_behavior":"REJECT"',
            '"unknown_value_behavior":"ALLOW"',
        ),
        (
            "unresolved_axis_pointer",
            REVISED_AB_R3_PATH,
            '"/structural_realization/lane_{lane_id}/axes/',
            '"/lane/{lane_id}/axes/',
        ),
        (
            "label_only_structural_output",
            REVISED_AB_R3_PATH,
            '"structural_effect_digest":"',
            '"removed_structural_effect_digest":"',
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        content = mutated[path].decode("utf-8")
        require(before in content, "E_REPAIR_R3_SELFTEST_PATTERN", name)
        mutated[path] = content.replace(before, after, 1).encode("utf-8")
        try:
            validate_targeted_repair_r3_documents(mutated)
        except (KeyError, TypeError, ValueError):
            continue
        failures.append(name)

    def document_rows(path: Path) -> list[dict[str, object]]:
        return [
            json.loads(line)
            for line in first[path].decode("utf-8").splitlines()
            if line
        ]

    try:
        state = source_state(root)
        component_by_id = {
            str(row["component_id"]): row
            for row in load_jsonl(root / COMPONENT_CANDIDATES_PATH)
        }
        for row in document_rows(REVISED_COMPONENTS_R3_PATH) + document_rows(
            ADDITION_CANDIDATES_R3_PATH
        ):
            component_by_id[str(row["component_id"])] = row
        components = list(component_by_id.values())
        evidence = build_generator_evidence(
            state["profiles"],
            components,
            document_rows(REVISED_RULES_R3_PATH),
            document_rows(REVISED_AB_R3_PATH),
        )
        if (
            len(evidence["requests"]) != 40
            or len(evidence["realizations"]) != 40
            or len(evidence["pair_results"]) != 20
            or not all(
                row["implementation_changed"] for row in evidence["ablations"]
            )
            or not all(row["tamper_rejected"] for row in evidence["digest_tampers"])
        ):
            failures.append("generator_evidence_counts_or_tamper")

        realization_by_request = {
            str(row["request_id"]): row for row in evidence["realizations"]
        }
        for request in evidence["requests"]:
            realization = realization_by_request[str(request["request_id"])]
            for axis_row in realization["lane_axis_realizations"]:
                pointer = str(axis_row["implementation_pointer"])
                node: object = realization
                for token in pointer.removeprefix("/").split("/"):
                    if not isinstance(node, dict) or token not in node:
                        failures.append("axis_pointer_not_resolvable")
                        break
                    node = node[token]
                else:
                    if not isinstance(node, dict) or node.get(
                        "structural_output_digest"
                    ) != axis_row["structural_output_digest"]:
                        failures.append("axis_pointer_wrong_output")

        base_request = copy.deepcopy(evidence["requests"][0])
        axis = sorted(base_request["lane"]["axes"])[0]
        unknown_axis = copy.deepcopy(base_request)
        unknown_axis["lane"]["axes"][axis] = "UNREVIEWED_AXIS_VALUE"
        unknown_axis["lane"]["axis_operator_parameters"][axis][
            "parameter_value"
        ] = "UNREVIEWED_AXIS_VALUE"
        unknown_axis["request_digest"] = object_digest(
            unknown_axis, "request_digest"
        )
        try:
            realize_request(unknown_axis, component_by_id)
        except Gate1ValidationError:
            pass
        else:
            failures.append("unknown_axis_value_accepted")

        truth_tamper = copy.deepcopy(base_request)
        truth_tamper["typed_material"]["facts"][0]["fact_value_digest"] = "f" * 64
        truth_tamper["typed_material"]["material_digest"] = object_digest(
            truth_tamper["typed_material"], "material_digest"
        )
        truth_tamper["request_digest"] = object_digest(
            truth_tamper, "request_digest"
        )
        try:
            realize_request(truth_tamper, component_by_id)
        except Gate1ValidationError:
            pass
        else:
            failures.append("truth_tampered_material_accepted")

        stripped_binding = copy.deepcopy(base_request)
        non_axis_binding = next(
            row
            for row in stripped_binding["component_bindings"]
            if row["component_role"]
            not in {
                "narrative_mechanism_operator",
                "information_order_operator",
                "visual_subject_operator",
                "sound_subject_operator",
                "rhythm_operator",
                "ending_operator",
            }
            and (row["required_fact_slots"] or row["required_authorization_slots"])
        )
        non_axis_binding["required_fact_slots"] = []
        non_axis_binding["fact_object_ids"] = []
        non_axis_binding["required_authorization_slots"] = []
        non_axis_binding["authorization_object_ids"] = []
        stripped_binding["request_digest"] = object_digest(
            stripped_binding, "request_digest"
        )
        try:
            realize_request(stripped_binding, component_by_id)
        except Gate1ValidationError:
            pass
        else:
            failures.append("stripped_nonaxis_binding_accepted")
    except (KeyError, StopIteration, TypeError, ValueError) as exc:
        failures.append(f"generator_evidence_fixture:{exc}")
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "phase": "targeted-repair-r3",
                "negative_case_count": len(mutations) + 3,
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def targeted_repair_r4_selftest(root: Path) -> int:
    first = build_targeted_repair_r4_documents(root)
    second = build_targeted_repair_r4_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_targeted_repair_r4_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        (
            "early_p3",
            TARGETED_RESULT_R4_PATH,
            "p3_allowed: false",
            "p3_allowed: true",
        ),
        (
            "wrong_lane_allowed",
            ADDITION_CANDIDATES_R4_PATH,
            '"known_but_wrong_lane_value_behavior":"REJECT"',
            '"known_but_wrong_lane_value_behavior":"ALLOW"',
        ),
        (
            "token_inference_enabled",
            ADDITION_CANDIDATES_R4_PATH,
            '"selection_by_hash_or_token_inference_allowed":false',
            '"selection_by_hash_or_token_inference_allowed":true',
        ),
        (
            "body_effect_source_changed",
            REVISED_AB_R4_PATH,
            '"structural_bodies_must_differ":true',
            '"structural_bodies_must_differ":false',
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        content = mutated[path].decode("utf-8")
        require(before in content, "E_REPAIR_R4_SELFTEST_PATTERN", name)
        mutated[path] = content.replace(before, after, 1).encode("utf-8")
        try:
            validate_targeted_repair_r4_documents(mutated)
        except (KeyError, TypeError, ValueError):
            continue
        failures.append(name)

    def document_rows(path: Path) -> list[dict[str, object]]:
        return [
            json.loads(line)
            for line in first[path].decode("utf-8").splitlines()
            if line
        ]

    try:
        state = source_state(root)
        component_by_id = {
            str(row["component_id"]): row
            for row in load_jsonl(root / COMPONENT_CANDIDATES_PATH)
        }
        for row in document_rows(REVISED_COMPONENTS_R4_PATH) + document_rows(
            ADDITION_CANDIDATES_R4_PATH
        ):
            component_by_id[str(row["component_id"])] = row
        components = list(component_by_id.values())
        paths = document_rows(REVISED_AB_R4_PATH)
        path_by_cp = {str(row["content_product_type_id"]): row for row in paths}
        evidence = build_generator_evidence_r4(
            state["profiles"],
            components,
            document_rows(REVISED_RULES_R4_PATH),
            paths,
        )
        if (
            len(evidence["requests"]) != 40
            or len(evidence["realizations"]) != 40
            or len(evidence["pair_results"]) != 20
            or len(evidence["axis_body_pairs"]) != 120
            or len(evidence["lane_binding_tampers"]) != 120
            or len(evidence["contract_tampers"]) != 240
            or not all(row["body_level_difference"] for row in evidence["axis_body_pairs"])
            or not all(
                row["substitution_rejected"]
                for row in evidence["lane_binding_tampers"]
            )
            or not all(
                row["tamper_rejected"] for row in evidence["contract_tampers"]
            )
            or not all(row["implementation_changed"] for row in evidence["ablations"])
            or not all(row["tamper_rejected"] for row in evidence["digest_tampers"])
        ):
            failures.append("generator_evidence_counts_or_semantics")
        base_request = copy.deepcopy(evidence["requests"][0])
        axis = sorted(base_request["lane"]["axes"])[0]
        contract = next(
            row
            for row in base_request["lane"]["axis_realization_contracts"]
            if row["axis"] == axis
        )
        base_request["lane"]["axes"][axis] = contract["lane_b_value"]
        base_request["lane"]["axis_operator_parameters"][axis][
            "parameter_value"
        ] = contract["lane_b_value"]
        base_request["request_digest"] = object_digest(
            base_request, "request_digest"
        )
        try:
            realize_request_r4(base_request, component_by_id, path_by_cp)
        except Gate1ValidationErrorR4:
            pass
        else:
            failures.append("known_enum_lane_substitution_accepted")
    except (KeyError, StopIteration, TypeError, ValueError) as exc:
        failures.append(f"generator_evidence_fixture:{exc}")
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "phase": "targeted-repair-r4",
                "negative_case_count": len(mutations) + 1,
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument(
        "--phase",
        choices=(
            "auto",
            "checkpoint",
            "targeted-repair",
            "targeted-repair-r2",
            "targeted-repair-r3",
            "targeted-repair-r4",
            "final",
        ),
        default="auto",
    )
    args = parser.parse_args()
    phase = args.phase
    if phase == "auto":
        if (ROOT / FINAL_IMPORT_SENTINEL).is_file():
            phase = "final"
        elif (ROOT / TARGETED_RESULT_R2_PATH).is_file():
            if (ROOT / TARGETED_RESULT_R4_PATH).is_file():
                phase = "targeted-repair-r4"
            elif (ROOT / TARGETED_RESULT_R3_PATH).is_file():
                phase = "targeted-repair-r3"
            else:
                phase = "targeted-repair-r2"
        else:
            phase = "checkpoint"
    if args.selftest:
        if phase == "final":
            return final_selftest(ROOT)
        if phase == "targeted-repair":
            return targeted_repair_selftest(ROOT)
        if phase == "targeted-repair-r2":
            return targeted_repair_r2_selftest(ROOT)
        if phase == "targeted-repair-r3":
            return targeted_repair_r3_selftest(ROOT)
        if phase == "targeted-repair-r4":
            return targeted_repair_r4_selftest(ROOT)
        return checkpoint_selftest(ROOT)
    if args.check:
        mismatches = check_outputs(ROOT, phase)
        sys.stdout.write(
            canonical_json(
                {
                    "status": "PASS" if not mismatches else "FAIL",
                    "phase": phase,
                    "mismatches": mismatches,
                }
            )
            + "\n"
        )
        return 0 if not mismatches else 1
    written = write_outputs(ROOT, phase)
    sys.stdout.write(
        canonical_json(
            {
                "status": "MATERIALIZED",
                "phase": phase,
                "written": written,
            }
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
