#!/usr/bin/env python3
"""Materialize the P2 component-review checkpoint without activating supply."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("P2 materializer refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
BASELINE_COMMIT = "81ddfe975a11b3dc9533d6828ac6418328b0f254"
CURRENT_OWNER_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml"
)
CURRENT_CHECKER_PATH = Path("ci/checkers/check_gate1_v1_1_current.py")
P1B_MATERIALIZER_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001/"
    "run_p1b_signed_review_closeout_freezer.py"
)
P1B_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001"
)
STANDARD_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1a_standard_baseline_review_packet_and_governance_preflight_001/"
    "standard/diyu_content_composition_standard.v1.1.md"
)
P1B_RESULT_PATH = P1B_ROOT / "result/p1b_signed_review_closeout_result.v0.1.yaml"
P1B_CONTENT_PATH = P1B_ROOT / "content/reference_120_final_dispositions.v0.1.jsonl"
P1B_ROUTE_GOLD_PATH = P1B_ROOT / "route/route_60_gold_answers.v0.1.jsonl"
P1B_ROUTE_FREEZE_PATH = P1B_ROOT / "route/route_60_gold_freeze_manifest.v0.1.yaml"
P1B_DISPOSITIONS_PATH = (
    P1B_ROOT / "component/component_86_final_dispositions.v0.1.jsonl"
)
P1B_SUPPLY_PATH = P1B_ROOT / "component/component_supply_gap_matrix.v0.1.yaml"
COMPONENT_SOURCE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
    "reviewed_reusable_component_registry.v0.4.jsonl"
)
CANDIDATE_SOURCE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/component_candidate_manifest.v0.1.jsonl"
)
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
AB_CONTRACT_PATH = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001/"
    "contracts/orch_ab_divergence_contract.v0.1.json"
)

SUCCESSOR_PATH = TASK_ROOT / "component/historical_86_successor_dispositions.v0.1.jsonl"
COMPONENT_CANDIDATES_PATH = (
    TASK_ROOT / "component/successor_component_candidates.v0.1.jsonl"
)
CONTROL_RULES_PATH = TASK_ROOT / "component/control_rule_candidates.v0.1.jsonl"
EDGE_PATH = TASK_ROOT / "component/proposed_component_cp_edges.v0.1.jsonl"
SUPPLY_PATH = TASK_ROOT / "component/candidate_supply_matrix.v0.1.yaml"
ADDITION_PATH = TASK_ROOT / "component/necessary_addition_assessment.v0.1.yaml"
AB_PATH = TASK_ROOT / "ab/ab_structural_path_candidates.v0.1.jsonl"
REVIEW_PACKET_PATH = TASK_ROOT / "review/independent_component_review_packet.v0.1.jsonl"
REVIEW_JOB_PATH = TASK_ROOT / "review/independent_component_review_job.v0.1.yaml"
COMPAT_PATH = TASK_ROOT / "compatibility/p1b_successor_compatibility_receipt.v0.1.yaml"
RESULT_PATH = TASK_ROOT / "result/p2_component_review_checkpoint_result.v0.1.yaml"

PINNED_HASHES = {
    STANDARD_PATH: "022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542",
    P1B_RESULT_PATH: "d4738a12b846d4c7fa5ca231de6d9e884e32733c01b9add6e81fad8d56601f72",
    P1B_CONTENT_PATH: "d4798e9847f9e4800676f002c46bb431e03d2e4763b07c91685f7962f7525ed0",
    P1B_ROUTE_GOLD_PATH: "f87d984d1780423e7ace0d78c54ba40e97ab5b48c39950f691c7ffca6652e054",
    P1B_ROUTE_FREEZE_PATH: "59490dc0260d9b05e28891136906744a2f383a15dc6f90d1e4754f353f769f3e",
    P1B_DISPOSITIONS_PATH: "554f97ff23c913bc85722305f6002a91876bbd3848cc399e1fb6dd46001fc4e0",
    P1B_SUPPLY_PATH: "a5cf34ec23b95649bc23f8e400268c432cb8f2e017fc56d2ea3120a5730f666e",
    COMPONENT_SOURCE_PATH: "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601",
    CANDIDATE_SOURCE_PATH: "70ce2f7ebae3699fba6be0a0fff5d4a0a8e1023bbd32ae5a4f7340b3c4f43f7d",
    PROFILE_PATH: "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056",
    AB_CONTRACT_PATH: "6862166cffb84dfb45ad8d98c82d5ae1faed18739df5e502d43a5d21d384a221",
}
P1B_MATERIALIZER_BEFORE_SHA256 = (
    "b82cfcedd747f8ac43748f57405c5760f5637e604403a8f5ed8893e504fba11f"
)
P1B_OWNER_AS_BUILT_SHA256 = (
    "541443a9c5c34047fb5c9a4652412cc019218abd60d29528b57dbc1d771d637a"
)
P1B_CHECKER_AS_BUILT_SHA256 = (
    "6474966c8ea5d0fdb2c5d40cc5888969f5fc8ebb63f8006d61504a4aaae8e231"
)
# Filled once the two authorized live files are finalized. These values are
# historical receipt data, not inputs used to decide component supply.
P1B_MATERIALIZER_AFTER_SHA256 = (
    "d7ab6454bdf31ecba7020109ba51cca8b5527e5aa07ad9afad690221aee9c2c8"
)
CURRENT_CHECKER_AFTER_SHA256 = (
    "2aec6f38dd6d64118506ad998c504e950eeaae34fc97b718ab285e49edc035bd"
)

READY_KEYS = frozenset(
    {
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
)

CONTROL_RULE_SPECS = {
    "RCV2-002-JUDGE-04-CLAIM-EVIDENCE-LIMIT": (
        "unsupported_claim_or_source_scope_mismatch",
        "HOLD_OR_DEGRADE_TO_EVIDENCE_BOUND_CLAIM",
        "Allow a faithful paraphrase when every assertion remains inside its cited source scope.",
    ),
    "RCV2-002-JUDGE-05-ONLY-SITE-DOABLE-ACTIONS": (
        "action_exceeds_actor_or_site_authority",
        "REQUEST_AUTHORIZED_ACTION_OR_STOP",
        "Allow actions explicitly assigned to the actor and feasible under supplied site conditions.",
    ),
    "RCV2-002-JUDGE-06-ANONYMIZE-CLOTHING-STORY": (
        "person_or_customer_story_lacks_identity_authorization",
        "ANONYMIZE_IF_SUPPORTED_ELSE_HOLD",
        "Do not anonymize away facts that still identify a person or invent an anonymous customer.",
    ),
    "RCV2-002-JUDGE-07-WORKMANSHIP-VS-LIFESPAN": (
        "visible_workmanship_is_used_as_lifespan_proof",
        "REMOVE_LONG_TERM_INFERENCE_OR_REQUEST_RECORDS",
        "Allow visible workmanship observations without treating them as durability proof.",
    ),
    "RCV2-002-JUDGE-08-LIGHT-BEFORE-COLOR-CLAIM": (
        "color_claim_lacks_observed_light_context",
        "REQUEST_LIGHT_CONTEXT_OR_DEGRADE",
        "Allow color wording when the supplied observation already includes its lighting condition.",
    ),
    "RCV2-002-JUDGE-09-OBSERVABLE-VS-RECORD-CLAIM": (
        "observation_is_presented_as_formal_record_or_result",
        "SEPARATE_OBSERVATION_FROM_RECORD_OR_HOLD",
        "Allow an observation to remain an observation when no formal record is claimed.",
    ),
    "RCV2-002-JUDGE-10-DEMO-NOT-BODY-PROMISE": (
        "styling_demo_is_used_as_body_effect_promise",
        "REMOVE_BODY_EFFECT_PROMISE_OR_STOP",
        "Allow a bounded demonstration that does not promise a body outcome.",
    ),
    "RCV2-002-JUDGE-11-OUTFIT-ROLE-NOT-BODY-JUDGE": (
        "outfit_role_is_rewritten_as_body_judgment",
        "REWRITE_TO_GARMENT_ROLE_OR_STOP",
        "Allow garment-role comparison without judging a person's body.",
    ),
}

B_MECHANISMS = {
    "CP01": "parallel_status_map",
    "CP02": "fixed_anchor_time_slice",
    "CP03": "same_object_state_evidence_path",
    "CP04": "result_first_multi_role_readback",
    "CP05": "document_field_evidence_path",
    "CP06": "single_variable_evidence_experiment",
    "CP07": "condition_exclusion_alternative",
    "CP08": "same_object_state_evidence_path",
    "CP09": "single_variable_evidence_experiment",
    "CP10": "result_to_authorized_trace",
    "CP11": "document_field_evidence_path",
    "CP12": "result_to_authorized_trace",
    "CP13": "condition_exclusion_alternative",
    "CP14": "single_variable_evidence_experiment",
    "CP15": "parallel_status_map",
    "CP16": "result_first_multi_role_readback",
    "CP17": "same_object_state_evidence_path",
    "CP18": "fixed_anchor_time_slice",
    "CP19": "result_to_authorized_trace",
    "CP20": "commitment_evidence_review_path",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


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


def object_digest(value: dict[str, Any], key: str) -> str:
    payload = {name: child for name, child in value.items() if name != key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"JSONL row is not an object: {path}:{line_number}")
        rows.append(value)
    return rows


def yaml_bytes(value: dict[str, Any]) -> bytes:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    ).encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return ("".join(canonical_json(row) + "\n" for row in rows)).encode("utf-8")


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ValueError(f"{code}: {detail}")


def role_of(component: dict[str, Any]) -> str:
    role = component.get("component_role") or component.get("source_component_role")
    require(isinstance(role, str) and bool(role), "E_COMPONENT_ROLE")
    return role


def verify_pins(root: Path) -> None:
    for path, expected in PINNED_HASHES.items():
        require((root / path).is_file(), "E_PIN_MISSING", path.as_posix())
        require(sha256_file(root / path) == expected, "E_PIN_DRIFT", path.as_posix())


def source_state(root: Path) -> dict[str, Any]:
    verify_pins(root)
    components = load_jsonl(root / COMPONENT_SOURCE_PATH)
    dispositions = load_jsonl(root / P1B_DISPOSITIONS_PATH)
    candidates = load_jsonl(root / CANDIDATE_SOURCE_PATH)
    profile_root = load_yaml(root / PROFILE_PATH).get(
        "content_product_profile_registry"
    )
    require(isinstance(profile_root, dict), "E_PROFILE_ROOT")
    profiles = profile_root.get("profiles")
    require(isinstance(profiles, list) and len(profiles) == 20, "E_PROFILE_COUNT")
    require(len(components) == 86 and len(dispositions) == 86, "E_COMPONENT_COUNT")
    component_ids = [row.get("component_id") for row in components]
    disposition_ids = [row.get("component_id") for row in dispositions]
    require(len(set(component_ids)) == 86, "E_COMPONENT_DUPLICATE")
    require(set(component_ids) == set(disposition_ids), "E_DISPOSITION_COVERAGE")
    return {
        "components": components,
        "component_by_id": {row["component_id"]: row for row in components},
        "disposition_by_id": {row["component_id"]: row for row in dispositions},
        "candidate_by_id": {row["component_id"]: row for row in candidates},
        "profiles": profiles,
        "profile_by_id": {row["content_product_type_id"]: row for row in profiles},
    }


def provenance_for(
    source: dict[str, Any],
    candidate_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    component_id = str(source["component_id"])
    if component_id.startswith("RCV2-004-"):
        provenance = source.get("provenance")
        require(isinstance(provenance, dict), "E_DESIGN_PROVENANCE", component_id)
        return {
            "source_type": "FOUNDER_AUTHORIZED_DESIGN_COMPONENT",
            "design_basis": provenance,
            "source_text_span_required": False,
            "evidence_boundary": "DESIGN_MECHANISM_ONLY_NO_FACT_AUTHORITY",
        }
    if component_id.startswith("RCV2-003-"):
        spans = source.get("evidence_spans")
        parent_ids = source.get("parent_asset_ids")
        parent_digests = source.get("parent_digests")
        require(isinstance(spans, list) and spans, "E_SOURCE_SPANS", component_id)
        require(
            isinstance(parent_ids, list) and parent_ids, "E_PARENT_IDS", component_id
        )
        require(isinstance(parent_digests, dict), "E_PARENT_DIGESTS", component_id)
        return {
            "source_type": "SOURCE_DERIVED",
            "parent_assets": [
                {
                    "parent_asset_id": parent_id,
                    "parent_digest": parent_digests[parent_id],
                }
                for parent_id in parent_ids
            ],
            "evidence_spans": spans,
            "evidence_boundary": "ABSTRACTED_MECHANISM_NOT_PARENT_SURFACE",
        }
    lineage = source.get("lineage")
    require(isinstance(lineage, dict), "E_SOURCE_LINEAGE", component_id)
    source_refs = lineage.get("source_candidate_refs")
    require(
        isinstance(source_refs, list) and source_refs,
        "E_SOURCE_CANDIDATES",
        component_id,
    )
    parent_assets: list[dict[str, Any]] = []
    for source_ref in source_refs:
        require(isinstance(source_ref, dict), "E_SOURCE_REF", component_id)
        candidate_id = source_ref.get("candidate_id")
        candidate = candidate_by_id.get(candidate_id)
        require(candidate is not None, "E_CANDIDATE_NOT_FOUND", str(candidate_id))
        parent_refs = candidate.get("parent_refs")
        require(
            isinstance(parent_refs, list) and parent_refs,
            "E_PARENT_REFS",
            str(candidate_id),
        )
        for parent_ref in parent_refs:
            require(isinstance(parent_ref, dict), "E_PARENT_REF", str(candidate_id))
            parent_assets.append({"source_candidate_id": candidate_id, **parent_ref})
    return {
        "source_type": "SOURCE_DERIVED",
        "parent_assets": parent_assets,
        "evidence_boundary": "ABSTRACTED_MECHANISM_NOT_PARENT_SURFACE",
    }


def mechanism_for(source: dict[str, Any]) -> dict[str, Any]:
    abstract = source.get("abstract_payload")
    if isinstance(abstract, dict):
        return abstract
    return {
        "function": source.get("function"),
        "reusable_mechanism": source.get("reusable_mechanism"),
        "abstraction_invariants": source.get("abstraction_invariants", []),
        "surface_policy": {
            "generate_new_surface": True,
            "parent_verbatim_allowed": False,
            "source_sentence_template_allowed": False,
        },
    }


def build_component_candidates(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in sorted(state["components"], key=lambda row: row["component_id"]):
        component_id = str(source["component_id"])
        disposition = state["disposition_by_id"][component_id]
        if disposition["final_disposition"] == "RECLASSIFY_AS_CONTROL_RULE":
            continue
        row: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "component_id": component_id,
            "component_version": "v1.1-p2-candidate",
            "supersedes_component_digest": source["component_digest"],
            "historical_source_sha256": disposition["source_record_sha256"],
            "component_role": role_of(source),
            "composition_asset_class": source["composition_asset_class"],
            "mechanism": mechanism_for(source),
            "required_input_slots": source.get("required_input_slots")
            or source.get("input_slot_contract", {}).get("required", []),
            "required_fact_slots": source.get("required_fact_slots", []),
            "required_authorization_slots": source.get(
                "required_authorization_slots", []
            ),
            "claim_boundary": source.get("claim_boundary")
            or source.get("abstract_payload", {}).get("claim_boundary"),
            "role_authority_boundary": source.get("role_authority_boundary")
            or "runtime must bind an authorized role before realization",
            "compatibility_rules": source.get("compatibility_rules", []),
            "forbidden_combinations": source.get("forbidden_combinations")
            or source.get("forbidden_combination_rule_refs", []),
            "missing_input_behavior": "DEGRADE_OR_STOP_USING_TARGET_PROFILE_ROUTE",
            "truth_boundary": source.get("truth_boundary", {}),
            "provenance": provenance_for(source, state["candidate_by_id"]),
            "historical_applicability_only": source.get(
                "applicable_content_product_type_ids", []
            ),
            "activation_proposal": "PENDING_NEED_SELECTION",
            "new_generator_consumable": False,
            "independent_review_state": "PENDING_TWO_REVIEWS",
            "readiness": {
                "generation_eligible": False,
                "runtime_ingest_ready": False,
                "production_ready": False,
            },
        }
        row["component_digest"] = object_digest(row, "component_digest")
        rows.append(row)
    require(len(rows) == 78, "E_CONTENT_COMPONENT_COUNT", str(len(rows)))
    return rows


def build_control_rules(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_id, spec in sorted(CONTROL_RULE_SPECS.items()):
        source = state["component_by_id"][source_id]
        trigger, action, false_positive = spec
        row: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "control_rule_id": source_id.replace("RCV2-002-JUDGE", "G1V11-CR"),
            "supersedes_misclassified_component_id": source_id,
            "supersedes_component_digest": source["component_digest"],
            "trigger_condition": trigger,
            "blocking_or_repair_action": action,
            "false_positive_handling": false_positive,
            "applicability_boundary": source.get(
                "applicable_content_product_type_ids", []
            ),
            "source_mechanism": mechanism_for(source),
            "contributes_component_supply": False,
            "may_write_audience_surface": False,
            "independent_review_state": "PENDING_TWO_REVIEWS",
            "active": False,
        }
        row["control_rule_digest"] = object_digest(row, "control_rule_digest")
        rows.append(row)
    require(len(rows) == 8, "E_CONTROL_RULE_COUNT")
    return rows


def rank_component(row: dict[str, Any]) -> tuple[int, int, str]:
    component_id = str(row["component_id"])
    generation_rank = 0 if component_id.startswith("RCV2-004-") else 1
    if component_id.startswith("RCV2-002-"):
        generation_rank = 2
    return (
        generation_rank,
        len(row["historical_applicability_only"]),
        component_id,
    )


def profile_requirements(profile: dict[str, Any]) -> dict[str, list[str]]:
    requirements = profile.get("input_requirements", {})
    return {
        "source": list(requirements.get("required_source_slots", [])),
        "fact": list(requirements.get("required_fact_slots", [])),
        "authorization": list(requirements.get("required_authorization_slots", [])),
    }


def build_edges(
    components: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], list[str]]]:
    selected: dict[tuple[str, str], list[str]] = {}
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        cp_id = str(profile["content_product_type_id"])
        for requirement in profile["required_component_roles"]:
            role = str(requirement["role"])
            candidates = [
                row
                for row in components
                if row["component_role"] == role
                and cp_id in row["historical_applicability_only"]
            ]
            candidates.sort(key=rank_component)
            require(candidates, "E_CANDIDATE_SUPPLY_GAP", f"{cp_id}:{role}")
            chosen = candidates[:2]
            selected[(cp_id, role)] = [str(row["component_id"]) for row in chosen]
            hard_guards = profile.get("founder_hard_guards", [])
            for selection_rank, component in enumerate(chosen, 1):
                mechanism = component["mechanism"]
                function = mechanism.get("function") or mechanism.get(
                    "reusable_mechanism"
                )
                edge: dict[str, Any] = {
                    "schema_version": "v0.1",
                    "task_id": TASK_ID,
                    "edge_id": f"P2-EDGE-{cp_id}-{role}-{selection_rank:02d}",
                    "content_product_type_id": cp_id,
                    "component_id": component["component_id"],
                    "component_digest": component["component_digest"],
                    "required_component_role": role,
                    "selection_purpose": (
                        "MINIMUM_SUPPLY"
                        if selection_rank == 1
                        else "AB_STRUCTURAL_ALTERNATIVE"
                    ),
                    "fit_basis": {
                        "profile_requires_exact_role": role,
                        "component_mechanism": function,
                        "business_purpose": profile.get("business_purpose"),
                        "profile_specific_hard_guards": hard_guards,
                        "fact_set_must_be_runtime_supplied": True,
                    },
                    "required_bindings": {
                        "profile": profile_requirements(profile),
                        "component_input_slots": component["required_input_slots"],
                        "component_fact_slots": component["required_fact_slots"],
                        "component_authorization_slots": component[
                            "required_authorization_slots"
                        ],
                    },
                    "forbidden_combinations": component["forbidden_combinations"],
                    "missing_input_behavior": component["missing_input_behavior"],
                    "historical_edge_reactivated": False,
                    "proposed_new_edge": True,
                    "active": False,
                    "independent_review_state": "PENDING_TWO_REVIEWS",
                }
                edge["edge_digest"] = object_digest(edge, "edge_digest")
                rows.append(edge)
    require(len(selected) >= 80, "E_DEMAND_CELL_COUNT", str(len(selected)))
    return rows, selected


def apply_activation_proposals(
    components: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    selected_ids = {str(row["component_id"]) for row in edges}
    for component in components:
        component["activation_proposal"] = (
            "PROPOSED_FOR_ACTIVATION_PENDING_TWO_REVIEWS"
            if component["component_id"] in selected_ids
            else "DEFERRED_NOT_REQUIRED_FOR_P2_MINIMUM_OR_AB_ALTERNATIVE"
        )
        component["component_digest"] = object_digest(component, "component_digest")
    digest_by_id = {row["component_id"]: row["component_digest"] for row in components}
    for edge in edges:
        edge["component_digest"] = digest_by_id[edge["component_id"]]
        edge["edge_digest"] = object_digest(edge, "edge_digest")


def build_successor_dispositions(
    state: dict[str, Any],
    components: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    component_by_id = {row["component_id"]: row for row in components}
    rule_by_source = {
        row["supersedes_misclassified_component_id"]: row for row in rules
    }
    rows: list[dict[str, Any]] = []
    for source in sorted(state["components"], key=lambda row: row["component_id"]):
        component_id = str(source["component_id"])
        if component_id in rule_by_source:
            rule = rule_by_source[component_id]
            successor_id = rule["control_rule_id"]
            successor_digest = rule["control_rule_digest"]
            disposition = "RECLASSIFIED_AS_CONTROL_RULE_CANDIDATE"
        else:
            successor = component_by_id[component_id]
            successor_id = component_id
            successor_digest = successor["component_digest"]
            disposition = (
                "REVISED_COMPONENT_PROPOSED_FOR_ACTIVATION"
                if successor["activation_proposal"].startswith("PROPOSED")
                else "REVISED_COMPONENT_DEFERRED_NOT_REQUIRED_FOR_P2"
            )
        row: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "historical_component_id": component_id,
            "historical_component_digest": source["component_digest"],
            "p1b_final_disposition": state["disposition_by_id"][component_id][
                "final_disposition"
            ],
            "p2_successor_disposition": disposition,
            "successor_id": successor_id,
            "successor_digest": successor_digest,
            "historical_inventory_counted_once": True,
            "historical_source_unchanged": True,
            "active": False,
            "independent_review_state": "PENDING_TWO_REVIEWS",
        }
        row["mapping_digest"] = object_digest(row, "mapping_digest")
        rows.append(row)
    require(len(rows) == 86, "E_SUCCESSOR_COVERAGE")
    return rows


def build_supply(
    profiles: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        cp_id = str(profile["content_product_type_id"])
        role_rows: list[dict[str, Any]] = []
        for requirement in profile["required_component_roles"]:
            role = str(requirement["role"])
            matching = [
                row
                for row in edges
                if row["content_product_type_id"] == cp_id
                and row["required_component_role"] == role
            ]
            role_rows.append(
                {
                    "role": role,
                    "minimum": requirement["min_count"],
                    "candidate_count": len(matching),
                    "candidate_component_ids": [
                        row["component_id"] for row in matching
                    ],
                    "candidate_coverage": "COMPLETE_PENDING_INDEPENDENT_REVIEW",
                    "approved_count": 0,
                }
            )
        rows.append(
            {
                "content_product_type_id": cp_id,
                "candidate_supply_complete": all(
                    row["candidate_count"] >= row["minimum"] for row in role_rows
                ),
                "approved_supply_complete": False,
                "required_roles": role_rows,
            }
        )
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "candidate_complete_profile_count": sum(
            row["candidate_supply_complete"] for row in rows
        ),
        "approved_complete_profile_count": 0,
        "components_active": False,
        "entries": rows,
    }
    document["matrix_digest"] = object_digest(document, "matrix_digest")
    return {"candidate_supply_matrix": document}


def build_ab_paths(
    profiles: list[dict[str, Any]],
    selected: dict[tuple[str, str], list[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        cp_id = str(profile["content_product_type_id"])
        roles = [str(row["role"]) for row in profile["required_component_roles"]]
        lane_a = [selected[(cp_id, role)][0] for role in roles]
        lane_b = [
            selected[(cp_id, role)][1]
            if len(selected[(cp_id, role)]) > 1
            else selected[(cp_id, role)][0]
            for role in roles
        ]
        row: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "content_product_type_id": cp_id,
            "same_fact_source_authorization_and_boundary_required": True,
            "lane_a": {
                "session_policy": "INDEPENDENT_SESSION_A",
                "component_ids": lane_a,
                "narrative_mechanism": "chronological_problem_judgment_action",
                "information_order": "context_then_action_then_boundary",
                "visual_subject": "actor_and_observable_action",
                "sound_subject": "ambient_and_evidence_bound_spoken_line",
                "rhythm": "steady_observation",
                "ending": "current_evidence_boundary",
            },
            "lane_b": {
                "session_policy": "INDEPENDENT_SESSION_B",
                "component_ids": lane_b,
                "narrative_mechanism": B_MECHANISMS[cp_id],
                "information_order": "result_or_state_then_trace_then_open_question",
                "visual_subject": "object_document_or_state_map",
                "sound_subject": "source_sound_or_time_anchor",
                "rhythm": "time_slice_or_evidence_pulse",
                "ending": "next_verification_without_promise",
            },
            "observable_difference_axes": [
                "narrative_mechanism",
                "information_order",
                "visual_subject",
                "sound_subject",
                "rhythm",
                "ending",
            ],
            "observable_difference_axis_count": 6,
            "structural_candidate_only": True,
            "content_quality_proven": False,
            "active": False,
            "independent_review_state": "PENDING_TWO_REVIEWS",
        }
        row["path_digest"] = object_digest(row, "path_digest")
        rows.append(row)
    require(len(rows) == 20, "E_AB_PATH_COUNT")
    return rows
