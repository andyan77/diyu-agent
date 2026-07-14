#!/usr/bin/env python3
"""Independent current-gate validation for the complete P3 evidence set."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import yaml


TASK_ID = "GATE1_V11_OPEN_PROBE40_001"
TASK_ROOT = Path("controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001")
P2_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
CURRENT_OWNER_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml"
)
ATTEMPT0_INTEGRITY = TASK_ROOT / "repair/attempt_1/attempt_0_integrity_manifest.v0.1.jsonl"
REPAIR_FREEZE = TASK_ROOT / "freeze/attempt_1/p3_open_repair_freeze.v0.2.yaml"
STRUCTURES = TASK_ROOT / "structure/attempt_1/structure_80.v0.2.jsonl"
DIFFERENCES = TASK_ROOT / "structure/attempt_1/difference_80.v0.2.jsonl"
REMOVALS = TASK_ROOT / "structure/attempt_1/axis_removal_480.v0.2.jsonl"
REQUESTS = TASK_ROOT / "freeze/attempt_1/positive_author_requests_20.v0.2.jsonl"
ROUTE_INPUTS = TASK_ROOT / "freeze/attempt_1/route_inputs_20.v0.2.jsonl"
OUTPUTS = TASK_ROOT / "open_probe/attempt_1/positive_20_first_outputs.v0.2.jsonl"
ROUTE_ACTUALS = TASK_ROOT / "open_probe/attempt_1/route_20_actuals.v0.2.jsonl"
ROUTE_COMPARISONS = TASK_ROOT / "open_probe/attempt_1/route_20_comparisons.v0.2.jsonl"
EXIT_EVENTS = TASK_ROOT / "open_probe/attempt_1/execution_exit_events.v0.2.jsonl"
MACHINE_REPORT = TASK_ROOT / "open_probe/attempt_1/machine_acceptance_report.v0.2.yaml"
REVIEW_ROOT = TASK_ROOT / "review/attempt_1"
REVIEW_PACKET = REVIEW_ROOT / "p3_review_packet.v0.2.yaml"
BLIND_PACKET = REVIEW_ROOT / "blind_positive_20.v0.2.jsonl"
BLIND_LABELS = REVIEW_ROOT / "blind_label_mapping.v0.2.jsonl"
CHOICE_CATALOG = REVIEW_ROOT / "content_product_choice_catalog.v0.2.jsonl"
REVIEW_ONE = REVIEW_ROOT / "signed_content_value_review.v0.2.json"
REVIEW_TWO = REVIEW_ROOT / "signed_fact_authorization_review.v0.2.json"
ADJUDICATION = REVIEW_ROOT / "targeted_adjudication.v0.2.json"
RESULT = TASK_ROOT / "result/p3_open_probe40_result.v0.2.yaml"
HANDOFF = TASK_ROOT / "result/p4_sealed_probe_handoff.v0.2.yaml"
DELIVERY = TASK_ROOT / "result/p3_delivery_receipt.v0.2.yaml"
P2_COMPONENTS = P2_ROOT / "component/active_gate1_components.v0.1.jsonl"
P2_RULES = P2_ROOT / "component/active_control_rules.v0.1.jsonl"
P2_EDGES = P2_ROOT / "component/active_gate1_edges.v0.1.jsonl"
P2_PATHS = P2_ROOT / "ab/active_ab_structural_paths.v0.1.jsonl"
AUTHOR_IDENTITY = "P3-CONTROLLED-AUTHOR-GPT56SOL-001"
AUTHOR_AGENT = "019f5f1b-eca1-7be3-9038-5464fb0ed0f6"
AUTHOR_SESSION = "P3-AUTHOR-SESSION-GPT56SOL-001"
VALID_PROFILES = {f"CP{index:02d}" for index in range(1, 21)}
VARIANTS = {"A1", "A2", "B1", "B2"}
AXES = {
    "narrative_mechanism",
    "information_order",
    "visual_subject",
    "sound_subject",
    "rhythm",
    "ending",
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
    "generator_qualified",
    "runtime_ingest_ready",
}
PUBLIC_MAX = {
    "truth_evidence_traceability": 20,
    "apparel_business_specificity": 10,
    "role_brand_viewpoint_consistency": 10,
    "user_value_information_gain": 10,
    "platform_native_executability": 10,
    "anti_formula_ethics_restraint": 10,
}
PRODUCT_MAX = {
    "core_product_value": 15,
    "product_specific_narrative_av": 10,
    "continuity_composability_accumulation": 5,
}
MINIMUMS = {
    "A": {
        "truth_evidence_traceability": 18,
        "core_product_value": 13,
        "role_brand_viewpoint_consistency": 8,
        "platform_native_executability": 8,
        "anti_formula_ethics_restraint": 8,
    },
    "B": {
        "truth_evidence_traceability": 17,
        "core_product_value": 12,
        "role_brand_viewpoint_consistency": 7,
        "platform_native_executability": 7,
        "anti_formula_ethics_restraint": 7,
    },
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _object_digest(value: Mapping[str, Any], field: str) -> str:
    return _sha_bytes(_canonical({key: child for key, child in value.items() if key != field}).encode("utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"not a mapping: {path}")
    return value


def _error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def _true_readiness(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in READY_KEYS and child is True:
                found.append(key)
            found.extend(_true_readiness(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_true_readiness(child))
    return found


def _grade(total: int) -> str:
    if total >= 90:
        return "A"
    if total >= 80:
        return "B"
    if total >= 70:
        return "C"
    return "D"


def _validate_attempt0(root: Path, errors: list[dict[str, str]]) -> None:
    rows = _jsonl(root / ATTEMPT0_INTEGRITY)
    if len(rows) != 45:
        _error(errors, "E_P3_ATTEMPT0_INTEGRITY", f"count={len(rows)}")
        return
    for row in rows:
        path = root / row["path"]
        if not path.is_file() or _sha_file(path) != row["sha256_at_attempt_0_failure_commit"]:
            _error(errors, "E_P3_ATTEMPT0_INTEGRITY", str(row["path"]))


def _validate_freeze(root: Path, errors: list[dict[str, str]]) -> None:
    freeze = _yaml(root / REPAIR_FREEZE).get("p3_open_repair_freeze", {})
    if freeze.get("freeze_state") != "FROZEN_BEFORE_ATTEMPT_1_AUTHORING":
        _error(errors, "E_P3_FREEZE", "state")
    if freeze.get("open_core_repair_window_used") is not True or freeze.get("open_core_repair_window_remaining") != 0:
        _error(errors, "E_P3_REPAIR_WINDOW", "must be used exactly once")
    if freeze.get("component_addition_count") != 0 or freeze.get("counts_toward_300") != 0:
        _error(errors, "E_P3_CORE_NUMBERS", "freeze")
    if freeze.get("freeze_manifest_digest") != _object_digest(freeze, "freeze_manifest_digest"):
        _error(errors, "E_P3_FREEZE", "digest")
    for key in (
        "repair_basis",
        "attempt_0_integrity_manifest",
        "scenario_set",
        "typed_material",
        "structure",
        "differences",
        "axis_removals",
        "author_instruction",
        "author_model",
        "positive_assignments",
        "author_requests",
        "route_selections",
        "route_inputs",
    ):
        record = freeze.get(key, {})
        path = root / str(record.get("path", ""))
        if not path.is_file() or record.get("sha256") != _sha_file(path):
            _error(errors, "E_P3_FREEZE", key)
    expected_p2 = {
        P2_COMPONENTS: "83dd1a8d35149785ac8bb172700b79d6221e5a7331b210018699fabaa49bc8ae",
        P2_RULES: "5d0ded265a6be6d0f39d35d2f739239225211081db6d6c4e4df0c8dcc2f09386",
        P2_EDGES: "de366eb50afe8a5a9362d3faa2a6a845af9c334683bdb9a8489cbfad2b2566f0",
        P2_PATHS: "4756971ef58ed472d0447f61f00bac7b7ef594117c43ecfb9fe3d7106c9631f3",
    }
    for path, expected in expected_p2.items():
        if _sha_file(root / path) != expected:
            _error(errors, "E_P3_P2_FROZEN", path.as_posix())


def _validate_structures(root: Path, errors: list[dict[str, str]]) -> None:
    structures = _jsonl(root / STRUCTURES)
    differences = _jsonl(root / DIFFERENCES)
    removals = _jsonl(root / REMOVALS)
    if len(structures) != 80 or len(differences) != 80 or len(removals) != 480:
        _error(errors, "E_P3_STRUCTURE_COUNTS", f"{len(structures)}/{len(differences)}/{len(removals)}")
        return
    pairs = Counter((row.get("profile_id"), row.get("variant")) for row in structures)
    if set(pairs) != {(profile, variant) for profile in VALID_PROFILES for variant in VARIANTS} or set(pairs.values()) != {1}:
        _error(errors, "E_P3_STRUCTURE_COVERAGE", "20x4")
    active_components = {row["component_id"] for row in _jsonl(root / P2_COMPONENTS)}
    for row in structures:
        if row.get("record_digest") != _object_digest(row, "record_digest"):
            _error(errors, "E_P3_STRUCTURE_DIGEST", str(row.get("record_id")))
        if set(row.get("addressable_outputs", {}).get("axes", {})) != AXES:
            _error(errors, "E_P3_STRUCTURE_AXES", str(row.get("record_id")))
        if not set(row.get("selected_component_ids", [])).issubset(active_components):
            _error(errors, "E_P3_STRUCTURE_COMPONENT", str(row.get("record_id")))
        if any(
            (
                row.get("audience_content") is not False,
                row.get("audience_title") not in (None, "", []),
                row.get("audience_body") not in (None, "", []),
                row.get("spoken_script") not in (None, "", []),
                row.get("cta") not in (None, "", []),
                row.get("composition_plan_created") is not False,
                row.get("external_provider_called") is not False,
                row.get("counts_toward_300") is not False,
            )
        ):
            _error(errors, "E_P3_STRUCTURE_BOUNDARY", str(row.get("record_id")))
    by_profile: dict[str, dict[str, dict[str, Any]]] = {}
    for row in structures:
        by_profile.setdefault(str(row.get("profile_id")), {})[str(row.get("variant"))] = row
    for profile, variants in by_profile.items():
        if set(variants) != VARIANTS:
            continue
        signatures = {_canonical(row.get("addressable_outputs")) for row in variants.values()}
        if len(signatures) != 4:
            _error(errors, "E_P3_STRUCTURE_CLONE", profile)
        for left, right, minimum in (("A1", "B1", 4), ("A2", "B2", 4), ("A1", "A2", 2), ("B1", "B2", 2)):
            left_axes = variants[left].get("axis_values", {})
            right_axes = variants[right].get("axis_values", {})
            actual = sum(left_axes.get(axis) != right_axes.get(axis) for axis in AXES)
            if actual < minimum:
                _error(errors, "E_P3_STRUCTURE_CLONE", f"{profile}:{left}:{right}:{actual}")
    if any(
        row.get("comparison_digest") != _object_digest(row, "comparison_digest")
        or row.get("pass") is not True
        or row.get("same_fact_source_authorization_boundary") is not True
        or int(row.get("differing_axis_count", 0)) < int(row.get("required_minimum", 99))
        for row in differences
    ):
        _error(errors, "E_P3_STRUCTURE_DIFFERENCE", "difference evidence")
    removal_counts = Counter(row.get("record_id") for row in removals)
    if set(removal_counts.values()) != {6} or any(
        row.get("test_digest") != _object_digest(row, "test_digest")
        or row.get("rejected") is not True
        or row.get("removed_axis") not in AXES
        for row in removals
    ):
        _error(errors, "E_P3_STRUCTURE_REMOVAL", "axis removal evidence")


def _surface_sequence(output: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows = [("synthetic_disclosure", output["synthetic_disclosure"]), ("title", output["title"])]
    rows.extend(("body", text) for text in output["body"])
    rows.extend(("spoken_line", text) for text in output["spoken_lines"])
    if output["cta"]:
        rows.append(("cta", output["cta"]))
    rows.extend(("visual_execution", text) for text in output["visual_execution"])
    rows.extend(("audio_execution", text) for text in output["audio_execution"])
    return rows


def _validate_outputs(root: Path, errors: list[dict[str, str]]) -> None:
    requests = {row["request_id"]: row for row in _jsonl(root / REQUESTS)}
    outputs = _jsonl(root / OUTPUTS)
    if len(requests) != 20 or len(outputs) != 20 or {row.get("profile_id") for row in outputs} != VALID_PROFILES:
        _error(errors, "E_P3_OUTPUT_COUNT", "20 profiles")
        return
    seen_runs: set[str] = set()
    for output in outputs:
        request = requests.get(output.get("request_id"))
        if not request or output.get("request_digest") != request.get("request_digest"):
            _error(errors, "E_P3_OUTPUT_REQUEST", str(output.get("request_id")))
            continue
        if output.get("output_digest") != _object_digest(output, "output_digest"):
            _error(errors, "E_P3_OUTPUT_DIGEST", str(output.get("request_id")))
        if (
            output.get("author_identity") != AUTHOR_IDENTITY
            or output.get("author_platform_agent_id") != AUTHOR_AGENT
            or output.get("author_session_logical_id") != AUTHOR_SESSION
            or output.get("model_capability_id") != "gpt-5.6-sol"
        ):
            _error(errors, "E_P3_AUTHOR_IDENTITY", str(output.get("request_id")))
        seen_runs.add(str(output.get("run_id")))
        if any(output.get(key) is not False for key in ("publishable", "runtime_consumable", "counts_toward_300")):
            _error(errors, "E_P3_OUTPUT_BOUNDARY", str(output.get("request_id")))
        if any(output.get("author_attestation", {}).values()):
            _error(errors, "E_P3_AUTHOR_ATTESTATION", str(output.get("request_id")))
        sequence = _surface_sequence(output)
        units = output.get("surface_units", [])
        if len(sequence) != len(units):
            _error(errors, "E_P3_SURFACE_JOIN", str(output.get("request_id")))
            continue
        material = request["typed_material"]
        fact_ids = {row["fact_id"] for row in material["facts"]}
        source_ids = {row["source_id"] for row in material["sources"]}
        authorization_ids = {row["authorization_id"] for row in material["authorizations"]}
        surface_ids: set[str] = set()
        for unit, expected in zip(units, sequence, strict=True):
            surface_ids.add(str(unit.get("surface_unit_id")))
            if (unit.get("surface_kind"), unit.get("text")) != expected:
                _error(errors, "E_P3_SURFACE_JOIN", str(output.get("request_id")))
            if not set(unit.get("fact_ids", [])).issubset(fact_ids):
                _error(errors, "E_P3_UNBOUND_FACT", str(unit.get("surface_unit_id")))
            if not set(unit.get("source_ids", [])).issubset(source_ids):
                _error(errors, "E_P3_UNBOUND_SOURCE", str(unit.get("surface_unit_id")))
            if not set(unit.get("authorization_ids", [])).issubset(authorization_ids):
                _error(errors, "E_P3_UNBOUND_AUTHORIZATION", str(unit.get("surface_unit_id")))
        approved = {
            row["component_id"]
            for row in request.get("approved_components", [])
            if isinstance(row, dict) and isinstance(row.get("component_id"), str)
        }
        for usage in output.get("component_usage", []):
            if usage.get("component_id") not in approved or not set(usage.get("implementation_surface_unit_ids", [])).issubset(surface_ids):
                _error(errors, "E_P3_COMPONENT_USE", str(output.get("request_id")))
        for claim in output.get("claims", []):
            if claim.get("claim_text") not in {unit[1] for unit in sequence}:
                _error(errors, "E_P3_CLAIM_SURFACE", str(claim.get("claim_id")))
            if not set(claim.get("fact_ids", [])).issubset(fact_ids):
                _error(errors, "E_P3_UNBOUND_FACT", str(claim.get("claim_id")))
    if len(seen_runs) != 20:
        _error(errors, "E_P3_REROLL_OR_RUN_ID", f"run_ids={len(seen_runs)}")


def _validate_routes_and_exit(root: Path, errors: list[dict[str, str]]) -> None:
    route_inputs = _jsonl(root / ROUTE_INPUTS)
    actuals = _jsonl(root / ROUTE_ACTUALS)
    comparisons = _jsonl(root / ROUTE_COMPARISONS)
    if len(actuals) != 20 or len(comparisons) != 20:
        _error(errors, "E_P3_ROUTE_COUNT", f"{len(actuals)}/{len(comparisons)}")
        return
    forbidden_gold_keys = {
        "gold_primary_action",
        "gold_reason_code",
        "expected_primary_action",
        "expected_primary_reason",
        "expected_route",
    }

    def keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(child) for child in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(child) for child in value)) if value else set()
        return set()

    if len(route_inputs) != 20 or any(keys(row).intersection(forbidden_gold_keys) for row in route_inputs):
        _error(errors, "E_P3_ROUTE_GOLD_LEAK", "route inputs")
    actions = Counter(row.get("actual_primary_action") for row in actuals)
    if actions != Counter({"BLOCK": 7, "DEGRADE": 7, "REQUEST_INPUT": 6}):
        _error(errors, "E_P3_ROUTE_DISTRIBUTION", str(dict(actions)))
    if any(
        row.get("route_result_digest") != _object_digest(row, "route_result_digest")
        or row.get("audience_title_created") is not False
        or row.get("audience_body_created") is not False
        or row.get("spoken_script_created") is not False
        or row.get("runtime_plan_created") is not False
        for row in actuals
    ):
        _error(errors, "E_P3_ROUTE_ACTUAL", "route boundary or digest")
    if any(
        row.get("comparison_digest") != _object_digest(row, "comparison_digest")
        or row.get("primary_action_matches_gold") is not True
        or row.get("primary_reason_matches_gold") is not True
        or row.get("audience_content_created") is not False
        for row in comparisons
    ):
        _error(errors, "E_P3_ROUTE_COMPARISON", "gold mismatch")
    events = _jsonl(root / EXIT_EVENTS)
    if len(events) != 2 or any(
        row.get("event_digest") != _object_digest(row, "event_digest")
        or row.get("external_provider") is not False
        or row.get("api_request") is not False
        or row.get("credential_read") is not False
        or row.get("network_dispatch") is not False
        for row in events
    ):
        _error(errors, "E_P3_EXIT_AUDIT", "event evidence")
    report = _yaml(root / MACHINE_REPORT).get("machine_acceptance_report", {})
    if report.get("machine_report_digest") != _object_digest(report, "machine_report_digest"):
        _error(errors, "E_P3_MACHINE_REPORT", "digest")
    audit = report.get("exit_audit", {})
    expected_audit = {
        "event_count": len(events),
        "controlled_execution_agent_run_count": sum(row.get("exit_class") == "CONTROLLED_EXECUTION_AGENT" for row in events),
        "external_provider_request_count": sum(int(row.get("request_count", 0)) for row in events if row.get("external_provider")),
        "external_api_call_count": sum(int(row.get("request_count", 0)) for row in events if row.get("api_request")),
        "credential_read_count": sum(int(bool(row.get("credential_read"))) for row in events),
        "network_dispatch_count": sum(int(bool(row.get("network_dispatch"))) for row in events),
    }
    if audit != expected_audit:
        _error(errors, "E_P3_EXIT_AUDIT", "not derived from events")


def _validate_review_report(report: Mapping[str, Any], labels: Mapping[str, str], errors: list[dict[str, str]]) -> None:
    if report.get("signed_record_digest") != _object_digest(report, "signed_record_digest"):
        _error(errors, "E_P3_REVIEW_DIGEST", str(report.get("review_id")))
    blind = report.get("blind_stage", {})
    if blind.get("blind_stage_digest") != _object_digest(blind, "blind_stage_digest"):
        _error(errors, "E_P3_BLIND_DIGEST", str(report.get("review_id")))
    predictions = blind.get("predictions", [])
    correct = sum(labels.get(row.get("blind_id")) == row.get("predicted_profile_id") for row in predictions)
    if len(predictions) != 20 or report.get("blind_top1_correct_count") != correct or report.get("blind_top1_accuracy") != round(correct / 20, 4):
        _error(errors, "E_P3_BLIND_RESULT", str(report.get("review_id")))
    scores = report.get("positive_scores", [])
    accepted = 0
    for score in scores:
        public = score.get("public_quality", {})
        product = score.get("product_quality", {})
        if set(public) != set(PUBLIC_MAX) or set(product) != set(PRODUCT_MAX):
            _error(errors, "E_P3_REVIEW_SCORE", str(score.get("profile_id")))
            continue
        total = sum(public.values()) + sum(product.values())
        grade = _grade(total)
        merged = {**public, **product}
        minimum = grade in MINIMUMS and all(merged[key] >= value for key, value in MINIMUMS.get(grade, {}).items())
        expected = grade in {"A", "B"} and minimum and not score.get("hard_vetoes")
        if score.get("total_score") != total or score.get("grade") != grade or score.get("critical_minimum_pass") is not minimum or score.get("first_acceptable") is not expected:
            _error(errors, "E_P3_REVIEW_SCORE", str(score.get("profile_id")))
        accepted += int(expected)
    if len(scores) != 20 or {row.get("profile_id") for row in scores} != VALID_PROFILES:
        _error(errors, "E_P3_REVIEW_COVERAGE", str(report.get("review_id")))
    average = round(sum(row.get("total_score", 0) for row in scores) / 20, 2) if len(scores) == 20 else -1
    if report.get("p3_score") != average or report.get("first_acceptable_count") != accepted or report.get("first_acceptance_rate") != round(accepted / 20, 4):
        _error(errors, "E_P3_REVIEW_SUMMARY", str(report.get("review_id")))
    formula = set(report.get("human_confirmed_formula_or_near_duplicate_profile_ids", []))
    hard = set(report.get("hard_error_profile_ids", []))
    expected_pass = accepted >= 18 and correct >= 17 and len(formula) <= 2 and not hard and report.get("structure_hard_gate_pass") is True and report.get("route_hard_gate_pass") is True
    if report.get("overall_verdict") != ("PASS" if expected_pass else "FAIL"):
        _error(errors, "E_P3_REVIEW_VERDICT", str(report.get("review_id")))


def _validate_reviews_and_result(root: Path, errors: list[dict[str, str]]) -> None:
    packet = _yaml(root / REVIEW_PACKET).get("p3_review_packet", {})
    if packet.get("packet_digest") != _object_digest(packet, "packet_digest"):
        _error(errors, "E_P3_REVIEW_PACKET", "digest")
    for record in packet.get("artifacts", {}).values():
        path = root / str(record.get("path", ""))
        if not path.is_file() or record.get("sha256") != _sha_file(path):
            _error(errors, "E_P3_REVIEW_PACKET", str(record.get("path")))
    labels = {row["blind_id"]: row["profile_id"] for row in _jsonl(root / BLIND_LABELS)}
    one = json.loads((root / REVIEW_ONE).read_text(encoding="utf-8"))
    two = json.loads((root / REVIEW_TWO).read_text(encoding="utf-8"))
    _validate_review_report(one, labels, errors)
    _validate_review_report(two, labels, errors)
    identities = {
        one.get("reviewer_identity"),
        two.get("reviewer_identity"),
        one.get("reviewer_platform_agent_id"),
        two.get("reviewer_platform_agent_id"),
        one.get("reviewer_session_id"),
        two.get("reviewer_session_id"),
        one.get("review_run_id"),
        two.get("review_run_id"),
    }
    if len(identities) != 8 or AUTHOR_IDENTITY in identities or AUTHOR_AGENT in identities or AUTHOR_SESSION in identities:
        _error(errors, "E_P3_REVIEW_IDENTITY", "reviewers must be isolated")
    first = {row["profile_id"]: row for row in one["positive_scores"]}
    second = {row["profile_id"]: row for row in two["positive_scores"]}
    disagreements = []
    for profile in sorted(VALID_PROFILES):
        reasons = []
        if first[profile]["first_acceptable"] != second[profile]["first_acceptable"]:
            reasons.append("FIRST_ACCEPTANCE_DISAGREEMENT")
        if set(first[profile]["hard_vetoes"]) != set(second[profile]["hard_vetoes"]):
            reasons.append("HARD_VETO_DISAGREEMENT")
        if reasons:
            disagreements.append({"profile_id": profile, "reasons": reasons})
    if disagreements:
        if not (root / ADJUDICATION).is_file():
            _error(errors, "E_P3_ADJUDICATION", "missing")
        else:
            adjudication = json.loads((root / ADJUDICATION).read_text(encoding="utf-8"))
            if adjudication.get("targeted_items") != disagreements or adjudication.get("all_substantive_disagreements_closed") is not True or adjudication.get("adjudication_digest") != _object_digest(adjudication, "adjudication_digest"):
                _error(errors, "E_P3_ADJUDICATION", "scope or digest")
    result = _yaml(root / RESULT).get("p3_open_probe40_result", {})
    handoff = _yaml(root / HANDOFF).get("p4_sealed_probe_handoff", {})
    delivery = _yaml(root / DELIVERY).get("p3_delivery_receipt", {})
    for value, field, code in ((result, "result_digest", "E_P3_RESULT"), (handoff, "handoff_digest", "E_P3_HANDOFF"), (delivery, "receipt_digest", "E_P3_DELIVERY")):
        if value.get(field) != _object_digest(value, field):
            _error(errors, code, "digest")
    pass_state = one.get("overall_verdict") == two.get("overall_verdict") == "PASS" and (not disagreements or (root / ADJUDICATION).is_file())
    expected_state = "PASS_TO_P4_SEALED_HIDDEN_PROBE" if pass_state else "STOPPED_OPEN_QUALIFICATION_FAILED"
    if result.get("result_state") != expected_state or result.get("p4_allowed") is not pass_state or result.get("p3_complete") is not pass_state:
        _error(errors, "E_P3_RESULT", "review/result mismatch")
    if handoff.get("p4_allowed") is not pass_state or handoff.get("p4_execution_authorized") is not False:
        _error(errors, "E_P3_HANDOFF", "boundary")
    if result.get("counts_toward_300") != 0 or result.get("open_core_repair_window_remaining") != 0 or result.get("component_addition_count") != 0:
        _error(errors, "E_P3_CORE_NUMBERS", "result")
    if _true_readiness(result) or _true_readiness(handoff) or _true_readiness(delivery):
        _error(errors, "E_P3_READINESS", "true readiness")
    owner = _yaml(root / CURRENT_OWNER_PATH).get("current_gate1_owner", {})
    expected_owner = "GATE1_V11_P3_OPEN_PROBE_FINAL_OWNER" if pass_state else "GATE1_V11_P2_FINAL_OWNER"
    if owner.get("owner_id") != expected_owner:
        _error(errors, "E_P3_OWNER", str(owner.get("owner_id")))


def validate_p3_current(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = (
        ATTEMPT0_INTEGRITY,
        REPAIR_FREEZE,
        STRUCTURES,
        DIFFERENCES,
        REMOVALS,
        REQUESTS,
        ROUTE_INPUTS,
        OUTPUTS,
        ROUTE_ACTUALS,
        ROUTE_COMPARISONS,
        EXIT_EVENTS,
        MACHINE_REPORT,
        REVIEW_PACKET,
        BLIND_PACKET,
        BLIND_LABELS,
        CHOICE_CATALOG,
        REVIEW_ONE,
        REVIEW_TWO,
        RESULT,
        HANDOFF,
        DELIVERY,
    )
    missing = [path.as_posix() for path in required if not (root / path).is_file()]
    if missing:
        _error(errors, "E_P3_REQUIRED_FILE", str(missing))
        return errors
    try:
        _validate_attempt0(root, errors)
        _validate_freeze(root, errors)
        _validate_structures(root, errors)
        _validate_outputs(root, errors)
        _validate_routes_and_exit(root, errors)
        _validate_reviews_and_result(root, errors)
        hidden_paths = [
            path.relative_to(root).as_posix()
            for path in (root / TASK_ROOT).rglob("*")
            if path.is_file() and any(part.lower() == "hidden" for part in path.parts)
        ]
        if hidden_paths:
            _error(errors, "E_P3_HIDDEN_MATERIAL", str(hidden_paths))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        _error(errors, "E_P3_PARSE", str(exc))
    return errors


__all__ = ["TASK_ROOT", "validate_p3_current"]
