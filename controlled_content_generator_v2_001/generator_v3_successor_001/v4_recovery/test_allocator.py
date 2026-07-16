"""Stable family-aware Gate1 test allocation.

The resulting object is a qualification test assignment. It must never be
interpreted as a formal content-composition plan. Runtime batch identifiers are
deliberately absent from all allocation inputs and digests.
"""

from __future__ import annotations

import itertools
import json
import re
import copy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import contract, material_policy

CONFIG_PATH = Path(__file__).resolve().parent / "config/family_strategies.v1.json"
PROFILE_IDS = tuple(f"CP{index:02d}" for index in range(1, 21))
FROZEN_LINEAR_PROFILES = frozenset({"CP01", "CP02", "CP03"})
AXES = ("entry_lens", "evidence_route", "boundary_carrier", "closing_function")
TEST_DNA_FIELDS = (*AXES, "strategy_id", "strategy_source", "strategy_frozen")
PROFILE_CAPACITY_MINIMUM = 12
PROFILE_CAPACITY_BUFFER_TARGET = 15


def _validate_axes(axes: Mapping[str, Any], code: str) -> None:
    contract.exact_fields(axes, AXES, f"{code}_FIELDS")
    for axis in AXES:
        values = contract.unique_text_list(axes[axis], f"{code}:{axis}")
        contract.require(len(values) >= 2, f"{code}_CAPACITY:{axis}")


def validate_family_strategies(config: Mapping[str, Any]) -> None:
    contract.exact_fields(config, {"schema_version", "strategy_version", "families"},
                          "E_V4_STRATEGY_FIELDS")
    contract.require(config["schema_version"] == "gate1-v4-family-strategies-v1",
                     "E_V4_STRATEGY_SCHEMA")
    contract.as_text(config["strategy_version"], "E_V4_STRATEGY_VERSION")
    contract.require(isinstance(config["families"], list) and config["families"],
                     "E_V4_STRATEGY_FAMILIES")
    seen_profiles: set[str] = set()
    seen_families: set[str] = set()
    override_profiles: set[str] = set()
    for family in config["families"]:
        family = contract.as_mapping(family, "E_V4_STRATEGY_FAMILY")
        contract.exact_fields(
            family,
            {"family_id", "profiles", "assignment_axes", "profile_strategy_overrides"},
            "E_V4_STRATEGY_FAMILY_FIELDS",
        )
        family_id = contract.as_text(family["family_id"], "E_V4_STRATEGY_FAMILY_ID")
        contract.require(family_id not in seen_families, "E_V4_STRATEGY_FAMILY_DUP",
                         family_id)
        seen_families.add(family_id)
        profiles = contract.unique_text_list(family["profiles"], "E_V4_STRATEGY_PROFILES")
        for profile_id in profiles:
            contract.require(profile_id in PROFILE_IDS, "E_V4_STRATEGY_PROFILE", profile_id)
            contract.require(profile_id not in seen_profiles,
                             "E_V4_STRATEGY_PROFILE_DUP", profile_id)
            seen_profiles.add(profile_id)
        axes = contract.as_mapping(family["assignment_axes"], "E_V4_STRATEGY_AXES")
        _validate_axes(axes, "E_V4_STRATEGY_AXIS")
        overrides = contract.as_mapping(
            family["profile_strategy_overrides"], "E_V4_STRATEGY_OVERRIDES")
        for profile_id, raw_override in overrides.items():
            contract.require(profile_id in profiles, "E_V4_STRATEGY_OVERRIDE_PROFILE",
                             str(profile_id))
            contract.require(profile_id not in override_profiles,
                             "E_V4_STRATEGY_OVERRIDE_DUP", str(profile_id))
            override_profiles.add(str(profile_id))
            override = contract.as_mapping(raw_override, "E_V4_STRATEGY_OVERRIDE")
            contract.exact_fields(
                override, {"strategy_id", "frozen", "reason_code", "assignment_axes"},
                "E_V4_STRATEGY_OVERRIDE_FIELDS")
            contract.as_text(override["strategy_id"], "E_V4_STRATEGY_OVERRIDE_ID")
            contract.as_text(override["reason_code"], "E_V4_STRATEGY_OVERRIDE_REASON")
            contract.require(override["frozen"] is True,
                             "E_V4_STRATEGY_OVERRIDE_NOT_FROZEN", str(profile_id))
            _validate_axes(contract.as_mapping(
                override["assignment_axes"], "E_V4_STRATEGY_OVERRIDE_AXES"),
                "E_V4_STRATEGY_OVERRIDE_AXIS")
    contract.require(seen_profiles == set(PROFILE_IDS), "E_V4_STRATEGY_PROFILE_COVERAGE",
                     ",".join(sorted(set(PROFILE_IDS) ^ seen_profiles)))
    contract.require(override_profiles == set(FROZEN_LINEAR_PROFILES),
                     "E_V4_STRATEGY_FROZEN_OVERRIDE_COVERAGE",
                     ",".join(sorted(override_profiles ^ set(FROZEN_LINEAR_PROFILES))))


def load_family_strategies(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_family_strategies(config)
    return config


def _profile_strategy(config: Mapping[str, Any], profile_id: str) -> dict[str, Any]:
    for family in config["families"]:
        if profile_id in family["profiles"]:
            override = family["profile_strategy_overrides"].get(profile_id)
            if override is not None:
                return {
                    "family_id": family["family_id"],
                    "assignment_axes": override["assignment_axes"],
                    "strategy_id": override["strategy_id"],
                    "strategy_source": "PROFILE_OVERRIDE",
                    "strategy_frozen": True,
                }
            return {
                "family_id": family["family_id"],
                "assignment_axes": family["assignment_axes"],
                "strategy_id": f"{family['family_id']}_FAMILY_DEFAULT_V1",
                "strategy_source": "FAMILY_DEFAULT",
                "strategy_frozen": False,
            }
    raise contract.ContractError(f"E_V4_STRATEGY_PROFILE_MISSING:{profile_id}")


def scenario_digest_for_case(case: Mapping[str, Any]) -> str:
    stable = {key: value for key, value in case.items()
              if key not in {"batch_id", "runtime", "scenario_digest",
                             "material_packet_digest", "evidence_surface_policy",
                             "paired_assignment_id"}}
    expected = contract.sha256_text(contract.canonical_json(stable))
    supplied = case.get("scenario_digest")
    if supplied is not None:
        contract.as_text(supplied, "E_V4_SCENARIO_DIGEST")
        contract.require(supplied == expected, "E_V4_SCENARIO_DIGEST",
                         "digest_mismatch")
    return expected


def _combinations(strategy: Mapping[str, Any]) -> list[dict[str, str]]:
    axes = strategy["assignment_axes"]
    values = [list(axes[axis]) for axis in AXES]
    return [dict(zip(AXES, row, strict=True)) for row in itertools.product(*values)]


def allocate_test_assignments(
    cases: Sequence[Mapping[str, Any]],
    assignment_set_id: str,
    *,
    config: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Allocate one stable test assignment per scenario.

    No ``batch_id`` argument exists by design. Within each profile, test DNA is
    unique while available Cartesian strategy capacity remains.
    """
    contract.as_text(assignment_set_id, "E_V4_ASSIGNMENT_SET_ID")
    strategy_config = dict(config) if config is not None else load_family_strategies()
    # Validate caller-supplied config through the same path without writing it.
    if config is not None:
        temporary = contract.canonical_json(strategy_config)
        strategy_config = json.loads(temporary)
        validate_family_strategies(strategy_config)
    strategy_digest = contract.sha256_text(contract.canonical_json(strategy_config))
    strategy_version = contract.as_text(strategy_config.get("strategy_version"),
                                        "E_V4_STRATEGY_VERSION")
    seen_scenarios: set[str] = set()
    by_profile: dict[str, list[Mapping[str, Any]]] = {}
    for raw_case in cases:
        case = contract.as_mapping(raw_case, "E_V4_CASE")
        scenario_id = contract.as_text(case.get("scenario_id"), "E_V4_CASE_SCENARIO")
        profile_id = contract.as_text(case.get("profile_id"), "E_V4_CASE_PROFILE")
        contract.require(profile_id in PROFILE_IDS, "E_V4_CASE_PROFILE", profile_id)
        contract.require(scenario_id not in seen_scenarios, "E_V4_CASE_DUP", scenario_id)
        seen_scenarios.add(scenario_id)
        by_profile.setdefault(profile_id, []).append(case)

    assignments: list[dict[str, Any]] = []
    for profile_id in sorted(by_profile):
        strategy = _profile_strategy(strategy_config, profile_id)
        combinations = _combinations(strategy)
        contract.require(len(by_profile[profile_id]) <= len(combinations),
                         "E_V4_ASSIGNMENT_CAPACITY", profile_id)
        used: set[int] = set()
        for case in sorted(by_profile[profile_id], key=lambda item: str(item["scenario_id"])):
            scenario_id = str(case["scenario_id"])
            seed = contract.sha256_text(
                f"{assignment_set_id}|{strategy_version}|{strategy_digest}|"
                f"{profile_id}|{scenario_id}"
            )
            index = int(seed[:16], 16) % len(combinations)
            while index in used:
                index = (index + 1) % len(combinations)
            used.add(index)
            material_packet_digest = contract.as_text(
                case.get("material_packet_digest"), "E_V4_ASSIGNMENT_MATERIAL_DIGEST")
            contract.require(len(material_packet_digest) == 64,
                             "E_V4_ASSIGNMENT_MATERIAL_DIGEST")
            evidence_policy = case.get("evidence_surface_policy")
            contract.require(isinstance(evidence_policy, list) and evidence_policy,
                             "E_V4_ASSIGNMENT_EVIDENCE_POLICY")
            for row in evidence_policy:
                row = contract.as_mapping(row, "E_V4_ASSIGNMENT_EVIDENCE_POLICY_ROW")
                contract.exact_fields(row, {"reference_assertion_id", "policy", "reason_code"},
                                      "E_V4_ASSIGNMENT_EVIDENCE_POLICY_FIELDS")
                contract.as_text(row["reference_assertion_id"],
                                 "E_V4_ASSIGNMENT_REFERENCE_ASSERTION")
                contract.require(row["policy"] in contract.SURFACE_POLICIES,
                                 "E_V4_ASSIGNMENT_EVIDENCE_POLICY_VALUE")
                contract.as_text(row["reason_code"],
                                 "E_V4_ASSIGNMENT_EVIDENCE_POLICY_REASON")
            forbidden_inferences = contract.unique_text_list(
                case.get("forbidden_inferences", []),
                "E_V4_ASSIGNMENT_FORBIDDEN_INFERENCES",
                allow_empty=True,
            )
            test_dna = {
                **combinations[index],
                "strategy_id": strategy["strategy_id"],
                "strategy_source": strategy["strategy_source"],
                "strategy_frozen": strategy["strategy_frozen"],
            }
            assignment: dict[str, Any] = {
                "schema_version": contract.TEST_ASSIGNMENT_SCHEMA,
                "object_type": "gate1_test_assignment",
                "assignment_id": f"G1TA-{contract.sha256_text(assignment_set_id + '|' + scenario_id)[:16]}",
                "assignment_set_id": assignment_set_id,
                "case_id": scenario_id,
                "scenario_id": scenario_id,
                "scenario_digest": scenario_digest_for_case(case),
                "profile_id": profile_id,
                "family_id": str(strategy["family_id"]),
                "material_packet_digest": material_packet_digest,
                "allocation_version": strategy_version,
                "strategy_version": strategy_version,
                "strategy_digest": strategy_digest,
                "argument_spine": [combinations[index]["entry_lens"],
                                   combinations[index]["evidence_route"]],
                "evidence_surface_policy": copy.deepcopy(evidence_policy),
                "perspective_anchor": combinations[index]["entry_lens"],
                "limitation_carrier": combinations[index]["boundary_carrier"],
                "closing_function": combinations[index]["closing_function"],
                "paired_assignment_id": case.get("paired_assignment_id"),
                "forbidden_inferences": forbidden_inferences,
                "stage_scope": "GATE1_QUALIFICATION_ONLY",
                "not_formal_content_composition_plan": True,
                "runtime_consumable": False,
                "publishable": False,
                "binds_enterprise_runtime_input": False,
                "counts_toward_300": False,
                "test_dna": test_dna,
                "assignment_digest": "",
            }
            contract.close_digest(assignment, "assignment_digest")
            validate_assignment(assignment)
            assignments.append(assignment)
    return sorted(assignments, key=lambda row: str(row["scenario_id"]))


def validate_assignment(assignment: Mapping[str, Any]) -> None:
    expected = {
        "schema_version", "object_type", "assignment_id", "assignment_set_id", "case_id",
        "scenario_id", "scenario_digest", "profile_id", "family_id",
        "material_packet_digest", "allocation_version", "strategy_version",
        "strategy_digest", "argument_spine", "evidence_surface_policy",
        "perspective_anchor", "limitation_carrier", "closing_function",
        "paired_assignment_id", "forbidden_inferences", "stage_scope",
        "not_formal_content_composition_plan", "runtime_consumable", "publishable",
        "binds_enterprise_runtime_input", "counts_toward_300", "test_dna",
        "assignment_digest",
    }
    contract.exact_fields(assignment, expected, "E_V4_ASSIGNMENT_FIELDS")
    contract.require(assignment["schema_version"] == contract.TEST_ASSIGNMENT_SCHEMA,
                     "E_V4_ASSIGNMENT_SCHEMA")
    for field in ("assignment_id", "assignment_set_id", "case_id", "scenario_id",
                  "profile_id", "family_id", "allocation_version", "strategy_version",
                  "perspective_anchor", "limitation_carrier", "closing_function"):
        contract.as_text(assignment[field], f"E_V4_ASSIGNMENT_TEXT:{field}")
    contract.require(assignment["case_id"] == assignment["scenario_id"],
                     "E_V4_ASSIGNMENT_CASE_JOIN")
    fixed = {
        "object_type": "gate1_test_assignment",
        "stage_scope": "GATE1_QUALIFICATION_ONLY",
        "not_formal_content_composition_plan": True,
        "runtime_consumable": False,
        "publishable": False,
        "binds_enterprise_runtime_input": False,
        "counts_toward_300": False,
    }
    for field, expected_value in fixed.items():
        contract.require(assignment[field] == expected_value,
                         f"E_V4_ASSIGNMENT_FIXED:{field}")
    contract.require(not ({"content_composition_plan", "expression_plan", "runtime_plan"}
                          & set(assignment)), "E_V4_ASSIGNMENT_PLAN_MASQUERADE")
    for field in ("scenario_digest", "strategy_digest", "material_packet_digest"):
        value = contract.as_text(assignment[field], f"E_V4_ASSIGNMENT_DIGEST:{field}")
        contract.require(len(value) == 64, f"E_V4_ASSIGNMENT_DIGEST:{field}")
    contract.text_list(assignment["argument_spine"], "E_V4_ASSIGNMENT_ARGUMENT_SPINE")
    evidence_policy = assignment["evidence_surface_policy"]
    contract.require(isinstance(evidence_policy, list) and evidence_policy,
                     "E_V4_ASSIGNMENT_EVIDENCE_POLICY")
    reference_ids: set[str] = set()
    for row in evidence_policy:
        contract.exact_fields(row, {"reference_assertion_id", "policy", "reason_code"},
                              "E_V4_ASSIGNMENT_EVIDENCE_POLICY_FIELDS")
        reference_id = contract.as_text(row["reference_assertion_id"],
                                        "E_V4_ASSIGNMENT_REFERENCE_ASSERTION")
        contract.require(reference_id not in reference_ids,
                         "E_V4_ASSIGNMENT_REFERENCE_ASSERTION_DUP", reference_id)
        reference_ids.add(reference_id)
        contract.require(row["policy"] in contract.SURFACE_POLICIES,
                         "E_V4_ASSIGNMENT_EVIDENCE_POLICY_VALUE")
        contract.as_text(row["reason_code"], "E_V4_ASSIGNMENT_EVIDENCE_POLICY_REASON")
    paired = assignment["paired_assignment_id"]
    contract.require(paired is None or (isinstance(paired, str) and bool(paired.strip())),
                     "E_V4_ASSIGNMENT_PAIRED_ID")
    contract.unique_text_list(
        assignment["forbidden_inferences"],
        "E_V4_ASSIGNMENT_FORBIDDEN_INFERENCES",
        allow_empty=True,
    )
    dna = contract.as_mapping(assignment["test_dna"], "E_V4_ASSIGNMENT_DNA")
    contract.exact_fields(dna, TEST_DNA_FIELDS, "E_V4_ASSIGNMENT_DNA_FIELDS")
    for axis in AXES:
        contract.as_text(dna[axis], f"E_V4_ASSIGNMENT_DNA:{axis}")
    contract.as_text(dna["strategy_id"], "E_V4_ASSIGNMENT_DNA:strategy_id")
    contract.require(dna["strategy_source"] in {"PROFILE_OVERRIDE", "FAMILY_DEFAULT"},
                     "E_V4_ASSIGNMENT_DNA:strategy_source")
    contract.require(isinstance(dna["strategy_frozen"], bool),
                     "E_V4_ASSIGNMENT_DNA:strategy_frozen")
    if assignment["profile_id"] in FROZEN_LINEAR_PROFILES:
        contract.require(dna["strategy_source"] == "PROFILE_OVERRIDE" and
                         dna["strategy_frozen"] is True,
                         "E_V4_ASSIGNMENT_FROZEN_PROFILE_STRATEGY")
    else:
        contract.require(dna["strategy_source"] == "FAMILY_DEFAULT" and
                         dna["strategy_frozen"] is False,
                         "E_V4_ASSIGNMENT_FAMILY_PROFILE_STRATEGY")
    contract.validate_digest(assignment, "assignment_digest", "E_V4_ASSIGNMENT_DIGEST")


def _constraint_digest(assignment: Mapping[str, Any]) -> str:
    value = {
        "argument_spine": assignment["argument_spine"],
        "evidence_surface_policy": assignment["evidence_surface_policy"],
        "perspective_anchor": assignment["perspective_anchor"],
        "limitation_carrier": assignment["limitation_carrier"],
        "closing_function": assignment["closing_function"],
        "forbidden_inferences": assignment["forbidden_inferences"],
        "test_dna": assignment["test_dna"],
    }
    return contract.sha256_text(contract.canonical_json(value))


def _semantic_material_fingerprint(material: Mapping[str, Any]) -> str:
    """Ignore record IDs so cloned materials cannot manufacture capacity."""
    value = {
        "profile_id": material["profile_id"],
        "source_texts": sorted(source["source_text"] for source in material["sources"]),
        "authorization_scopes": sorted(
            authorization["scope"] for authorization in material["authorizations"]),
        "facts": sorted(
            ({"slot_id": fact["slot_id"], "fact_value": fact["fact_value"],
              "surface_policy": fact["surface_policy"],
              "conditions": sorted(fact["conditions"]),
              "prohibited_surface_terms": sorted(fact["prohibited_surface_terms"])}
             for fact in material["facts"]),
            key=contract.canonical_json,
        ),
    }
    return contract.sha256_text(contract.canonical_json(value))


def _assignment_dna_fingerprint(assignment: Mapping[str, Any]) -> str:
    dna = assignment["test_dna"]
    value = {
        "argument_spine": assignment["argument_spine"],
        "perspective_anchor": assignment["perspective_anchor"],
        "limitation_carrier": assignment["limitation_carrier"],
        "closing_function": assignment["closing_function"],
        "forbidden_inferences": assignment["forbidden_inferences"],
        "test_dna_axes": {axis: dna[axis] for axis in AXES},
    }
    return contract.sha256_text(contract.canonical_json(value))


def make_capacity_legality_record(
    assignment: Mapping[str, Any],
    material: Mapping[str, Any],
    *,
    assessor_identity: str,
    assessment_evidence_ref: str,
    material_and_constraints_support_assignment: bool,
) -> dict[str, Any]:
    """Seal an independent material/constraint feasibility decision."""
    validate_assignment(assignment)
    material_policy.validate_material(material)
    contract.require(assignment["scenario_id"] == material["scenario_id"] and
                     assignment["profile_id"] == material["profile_id"] and
                     assignment["material_packet_digest"] == material["material_digest"],
                     "E_V4_CAPACITY_LEGALITY_MATERIAL_JOIN")
    record: dict[str, Any] = {
        "schema_version": "gate1-v4-assignment-legality-v1",
        "assignment_id": assignment["assignment_id"],
        "assignment_digest": assignment["assignment_digest"],
        "material_digest": material["material_digest"],
        "constraint_digest": _constraint_digest(assignment),
        "assessor_identity": contract.as_text(
            assessor_identity, "E_V4_CAPACITY_LEGALITY_ASSESSOR"),
        "assessment_evidence_ref": contract.as_text(
            assessment_evidence_ref, "E_V4_CAPACITY_LEGALITY_EVIDENCE"),
        "independent_assessment": True,
        "material_and_constraints_support_assignment": contract.as_bool(
            material_and_constraints_support_assignment,
            "E_V4_CAPACITY_LEGALITY_DECISION"),
        "record_digest": "",
    }
    contract.close_digest(record, "record_digest")
    validate_capacity_legality_record(record)
    return record


def validate_capacity_legality_record(record: Mapping[str, Any]) -> None:
    contract.exact_fields(
        record,
        {"schema_version", "assignment_id", "assignment_digest", "material_digest",
         "constraint_digest", "assessor_identity", "assessment_evidence_ref",
         "independent_assessment", "material_and_constraints_support_assignment",
         "record_digest"},
        "E_V4_CAPACITY_LEGALITY_FIELDS",
    )
    contract.require(record["schema_version"] ==
                     "gate1-v4-assignment-legality-v1",
                     "E_V4_CAPACITY_LEGALITY_SCHEMA")
    for field in ("assignment_id", "assessor_identity", "assessment_evidence_ref"):
        contract.as_text(record[field], f"E_V4_CAPACITY_LEGALITY_TEXT:{field}")
    for field in ("assignment_digest", "material_digest", "constraint_digest"):
        value = contract.as_text(record[field], f"E_V4_CAPACITY_LEGALITY_DIGEST:{field}")
        contract.require(len(value) == 64, f"E_V4_CAPACITY_LEGALITY_DIGEST:{field}")
    contract.require(record["independent_assessment"] is True,
                     "E_V4_CAPACITY_LEGALITY_INDEPENDENCE")
    contract.require(isinstance(record["material_and_constraints_support_assignment"],
                                bool), "E_V4_CAPACITY_LEGALITY_DECISION")
    contract.validate_digest(record, "record_digest", "E_V4_CAPACITY_LEGALITY_DIGEST")


def audit_profile_capacity(
    assignments: Sequence[Mapping[str, Any]],
    materials: Sequence[Mapping[str, Any]],
    *,
    legality_records: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Audit observed, material-bound capacity without theoretical inflation.

    An assignment counts only after its complete contract, material digest, profile,
    scenario, and three-way evidence policy all join to a supplied normalized material,
    and an independent legality record confirms that the material supports the assigned
    constraints. Semantic material and assignment-DNA capacity are counted separately,
    so ID-renamed material clones cannot manufacture capacity.
    Configuration Cartesian capacity is deliberately never consulted. Missing material
    coverage for any of the 20 profiles yields ``NOT_EVALUATED``; once all profiles are
    represented, fewer than 12 unique legal assignments yields ``REQUEST_CURATION``.
    Fifteen is reported only as a non-gating buffer target.
    """
    material_by_scenario: dict[str, Mapping[str, Any]] = {}
    material_profiles: set[str] = set()
    for material in materials:
        material_policy.validate_material(material)
        scenario_id = str(material["scenario_id"])
        contract.require(material["profile_id"] in PROFILE_IDS,
                         "E_V4_CAPACITY_MATERIAL_PROFILE", str(material["profile_id"]))
        contract.require(scenario_id not in material_by_scenario,
                         "E_V4_CAPACITY_MATERIAL_DUP", scenario_id)
        material_by_scenario[scenario_id] = material
        material_profiles.add(str(material["profile_id"]))

    legality_by_assignment: dict[str, Mapping[str, Any]] = {}
    for record in legality_records:
        validate_capacity_legality_record(record)
        assignment_digest = str(record["assignment_digest"])
        contract.require(assignment_digest not in legality_by_assignment,
                         "E_V4_CAPACITY_LEGALITY_DUP", assignment_digest)
        legality_by_assignment[assignment_digest] = record

    combined_fingerprints = {profile_id: set() for profile_id in PROFILE_IDS}
    semantic_material_fingerprints = {profile_id: set() for profile_id in PROFILE_IDS}
    assignment_dna_fingerprints = {profile_id: set() for profile_id in PROFILE_IDS}
    observed_valid_counts = {profile_id: 0 for profile_id in PROFILE_IDS}
    seen_scenarios: set[str] = set()
    invalid_assignments: list[dict[str, str]] = []
    for index, assignment in enumerate(assignments, 1):
        assignment_id = (str(assignment.get("assignment_id", f"ROW-{index:04d}"))
                         if isinstance(assignment, Mapping) else f"ROW-{index:04d}")
        try:
            assignment = contract.as_mapping(assignment, "E_V4_CAPACITY_ASSIGNMENT")
            validate_assignment(assignment)
            scenario_id = str(assignment["scenario_id"])
            contract.require(scenario_id not in seen_scenarios,
                             "E_V4_CAPACITY_MULTIPLE_ASSIGNMENTS", scenario_id)
            seen_scenarios.add(scenario_id)
            contract.require(scenario_id in material_by_scenario,
                             "E_V4_CAPACITY_MATERIAL_MISSING", scenario_id)
            material = material_by_scenario[scenario_id]
            contract.require(assignment["profile_id"] == material["profile_id"],
                             "E_V4_CAPACITY_PROFILE_JOIN", scenario_id)
            contract.require(assignment["material_packet_digest"] ==
                             material["material_digest"],
                             "E_V4_CAPACITY_MATERIAL_DIGEST", scenario_id)
            assignment_policy = {
                row["reference_assertion_id"]: row["policy"]
                for row in assignment["evidence_surface_policy"]
            }
            expected_policy = {fact["fact_id"]: fact["surface_policy"]
                               for fact in material["facts"]}
            contract.require(assignment_policy == expected_policy,
                             "E_V4_CAPACITY_POLICY_JOIN", scenario_id)
            record = legality_by_assignment.get(str(assignment["assignment_digest"]))
            contract.require(record is not None,
                             "E_V4_CAPACITY_LEGALITY_RECORD_MISSING", assignment_id)
            contract.require(record["assignment_id"] == assignment["assignment_id"] and
                             record["material_digest"] == material["material_digest"] and
                             record["constraint_digest"] == _constraint_digest(assignment),
                             "E_V4_CAPACITY_LEGALITY_JOIN", assignment_id)
            contract.require(record["material_and_constraints_support_assignment"] is True,
                             "E_V4_CAPACITY_ASSIGNMENT_UNSUPPORTED", assignment_id)
            profile_id = str(assignment["profile_id"])
            observed_valid_counts[profile_id] += 1
            material_fingerprint = _semantic_material_fingerprint(material)
            dna_fingerprint = _assignment_dna_fingerprint(assignment)
            semantic_material_fingerprints[profile_id].add(material_fingerprint)
            assignment_dna_fingerprints[profile_id].add(dna_fingerprint)
            combined_fingerprints[profile_id].add(
                contract.sha256_text(f"{material_fingerprint}|{dna_fingerprint}"))
        except (contract.ContractError, KeyError, TypeError) as error:
            invalid_assignments.append({
                "assignment_id": assignment_id,
                "reason": str(error) or error.__class__.__name__,
            })

    missing_material_profiles = sorted(set(PROFILE_IDS) - material_profiles)
    full_material_coverage = not missing_material_profiles
    profile_rows: dict[str, dict[str, Any]] = {}
    for profile_id in PROFILE_IDS:
        semantic_material_count = len(semantic_material_fingerprints[profile_id])
        assignment_dna_count = len(assignment_dna_fingerprints[profile_id])
        combined_count = len(combined_fingerprints[profile_id])
        effective_count = min(semantic_material_count, assignment_dna_count,
                              combined_count)
        if not full_material_coverage:
            status = "NOT_EVALUATED"
        elif effective_count < PROFILE_CAPACITY_MINIMUM:
            status = "REQUEST_CURATION"
        else:
            status = "MINIMUM_MET"
        profile_rows[profile_id] = {
            "observed_valid_assignment_count": observed_valid_counts[profile_id],
            "unique_semantic_material_count": semantic_material_count,
            "unique_assignment_dna_count": assignment_dna_count,
            "unique_material_dna_binding_count": combined_count,
            "effective_capacity_count": effective_count,
            "deduplicated_or_capacity_limited_count":
                observed_valid_counts[profile_id] - effective_count,
            "minimum_required": PROFILE_CAPACITY_MINIMUM,
            "minimum_met": full_material_coverage and
                           effective_count >= PROFILE_CAPACITY_MINIMUM,
            "buffer_target": PROFILE_CAPACITY_BUFFER_TARGET,
            "buffer_target_met": full_material_coverage and
                                 effective_count >= PROFILE_CAPACITY_BUFFER_TARGET,
            "status": status,
        }
    if not full_material_coverage:
        overall_status = "NOT_EVALUATED"
    elif invalid_assignments or any(
            min(len(semantic_material_fingerprints[profile_id]),
                len(assignment_dna_fingerprints[profile_id]),
                len(combined_fingerprints[profile_id])) < PROFILE_CAPACITY_MINIMUM
            for profile_id in PROFILE_IDS):
        overall_status = "REQUEST_CURATION"
    else:
        overall_status = "CAPACITY_MINIMUM_MET"
    report: dict[str, Any] = {
        "schema_version": "gate1-v4-profile-capacity-audit-v1",
        "counting_basis": "OBSERVED_MATERIAL_BOUND_LEGAL_ASSIGNMENTS_ONLY",
        "theoretical_cartesian_capacity_used": False,
        "minimum_per_profile": PROFILE_CAPACITY_MINIMUM,
        "buffer_target_per_profile": PROFILE_CAPACITY_BUFFER_TARGET,
        "buffer_target_is_gate": False,
        "material_count": len(material_by_scenario),
        "assignment_candidate_count": len(assignments),
        "legality_record_count": len(legality_by_assignment),
        "material_profile_coverage_complete": full_material_coverage,
        "missing_material_profile_ids": missing_material_profiles,
        "invalid_assignments": sorted(
            invalid_assignments, key=lambda row: row["assignment_id"]),
        "profiles": profile_rows,
        "overall_status": overall_status,
        "report_digest": "",
    }
    contract.close_digest(report, "report_digest")
    return report


_LEGACY_STYLE_RE = re.compile(r"风格=(?P<style>BS_[A-Z_]+)")


def diagnose_legacy_r5_plan_mismatch(
    scenarios_path: Path,
    requests_path: Path,
) -> dict[str, Any]:
    """Read-only diagnosis of the historical R5 dual-planning mismatch."""
    scenarios = contract.load_jsonl(scenarios_path)
    requests = contract.load_jsonl(requests_path)
    curated_style: dict[str, str] = {}
    missing_curated_style: list[str] = []
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id", ""))
        provenance = scenario.get("provenance", {})
        note = str(provenance.get("boundary_recuration", "")) if isinstance(provenance, Mapping) else ""
        match = _LEGACY_STYLE_RE.search(note)
        if match:
            curated_style[scenario_id] = match.group("style")
        else:
            missing_curated_style.append(scenario_id)
    mismatches: list[dict[str, str]] = []
    matches = 0
    missing_request_style: list[str] = []
    for request in requests:
        scenario_id = str(request.get("scenario_id", ""))
        request_id = str(request.get("request_id", ""))
        plan = request.get("expression_plan", {})
        planned = str(plan.get("boundary_style", "")) if isinstance(plan, Mapping) else ""
        curated = curated_style.get(scenario_id, "")
        if not planned:
            missing_request_style.append(request_id)
        elif curated and planned == curated:
            matches += 1
        elif curated:
            mismatches.append({"request_id": request_id, "scenario_id": scenario_id,
                               "curated_style": curated, "request_style": planned})
    report: dict[str, Any] = {
        "schema_version": "gate1-v4-legacy-r5-plan-mismatch-diagnostic-v1",
        "read_only": True,
        "scenario_count": len(scenarios),
        "request_count": len(requests),
        "match_count": matches,
        "mismatch_count": len(mismatches),
        "missing_curated_style_ids": sorted(missing_curated_style),
        "missing_request_style_ids": sorted(missing_request_style),
        "mismatches": sorted(mismatches, key=lambda row: row["request_id"]),
        "scenarios_sha256": contract.sha256_bytes(scenarios_path.read_bytes()),
        "requests_sha256": contract.sha256_bytes(requests_path.read_bytes()),
        "report_digest": "",
    }
    contract.close_digest(report, "report_digest")
    return report


__all__ = [
    "AXES", "FROZEN_LINEAR_PROFILES", "PROFILE_CAPACITY_BUFFER_TARGET",
    "PROFILE_CAPACITY_MINIMUM", "PROFILE_IDS", "allocate_test_assignments",
    "audit_profile_capacity", "make_capacity_legality_record",
    "diagnose_legacy_r5_plan_mismatch", "load_family_strategies",
    "scenario_digest_for_case", "validate_assignment",
    "validate_capacity_legality_record", "validate_family_strategies",
]
