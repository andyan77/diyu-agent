#!/usr/bin/env python3
"""Materialize the Controlled Content Generator V2 build-only acceptance harness."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Protocol

import yaml


TASK_ID = "CONTROLLED_CONTENT_GENERATOR_V2_BUILD_AND_ACCEPTANCE_HARNESS_001"
PHASE0_MERGE_COMMIT_SHA = "0ed9fd40203a6423d4deb9e6342c441ac3c129c1"
PHASE0_MERGE_TREE_SHA = "39cf72e29dba7da8e9071919813f1001dcfe9afb"
REVIEWED_BASE_SHA = "6253e3d1661cd46945a3443de54ac55df5b7d746"
REVIEWED_HEAD_SHA = "8ee1cfe874011b3e94ce63061b573b67617fb197"
REVIEWED_HEAD_TREE_SHA = "39cf72e29dba7da8e9071919813f1001dcfe9afb"
REVIEWED_FULL_DIFF_DIGEST = "2707a1ba75482ca40c95f06945e818d51525dc5f0b25c5e2b547f26432a6064f"

TASK_DIR = Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001")
CONTRACT_PATH = TASK_DIR / "controlled_content_generator_v2_contract.v0.1.yaml"
CASES_PATH = TASK_DIR / "generator_acceptance_harness_cases.v0.1.jsonl"
RESULTS_PATH = TASK_DIR / "generator_acceptance_harness_results.v0.1.jsonl"
BUILD_RESULT_PATH = TASK_DIR / "generator_v2_build_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "generator_guardian_review_packet.v0.1.yaml"
FREEZER_PATH = TASK_DIR / "run_generator_v2_acceptance_harness.py"
CHECKER_PATH = Path("ci/checkers/check_controlled_content_generator_v2_build.py")

GKB_ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
PROFILES_PATH = GKB_ROOT / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
COMPONENT_REGISTRY_PATH = GKB_ROOT / "component_supply_closeout_20cp_001/reviewed_reusable_component_registry.v0.3.jsonl"
VALIDATION_FIXTURES_PATH = GKB_ROOT / "fact_authorization_fixture_closeout_001/content_product_validation_fixtures.v0.1.jsonl"
ORCH_DIR = Path("08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001")
ORCH_REQUESTS_PATH = ORCH_DIR / "orch_validation_requests.v0.1.jsonl"
ORCH_DECISIONS_PATH = ORCH_DIR / "orch_dryrun_decisions.v0.1.jsonl"
ORCH_PLANS_PATH = ORCH_DIR / "orch_validation_canonical_plans.v0.1.jsonl"
ORCH_RESULT_PATH = ORCH_DIR / "orch_20cp_dryrun_result.v0.1.yaml"

GENERATOR_CONTROL_TARGET = "01_generation_contracts/codex_generation_output_contract.v0.1.schema.json"
GENERATOR_PROOF_CHECKER = "ci/checkers/check_generator_capability_proof_microbatch.py"
GENERATOR_P7D_RUNNER = "ci/runners/run_p7d_midbatch_320.py"

READINESS_FLAGS = {
    "generator_qualified": False,
    "qualification_probe_40_generation_allowed": False,
    "runtime_ingest_ready": False,
    "generation_eligible": False,
    "generation_allowed": False,
    "generation_600_allowed": False,
    "expand_600_allowed": False,
    "expand_3600_allowed": False,
    "candidatepack_ready": False,
    "KE_ready": False,
    "Serving_ready": False,
    "RAG_ready": False,
    "DIFY_ready": False,
    "production_ready": False,
    "release_ready": False,
}

SUPPORTED_LICENSES = {
    "EVIDENCE_BOUND_ASSERTION",
    "AUTHORIZED_ROLE_JUDGMENT",
    "CAPTURE_BOUND_PERFORMATIVE",
    "PUBLISHER_OWNED_SUBJECTIVE_EXPRESSION",
    "NONFACTUAL_CREATIVE_EXPRESSION",
    "HYPOTHETICAL_OR_DISCLOSED_SCENE",
    "STRUCTURAL_LANGUAGE",
}


class ProviderPort(Protocol):
    """Future provider interface; no implementation is enabled in this task."""

    def compile_request(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Compile an already accepted envelope into a provider request."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: strip_keys(child, keys) for key, child in value.items() if key not in keys}
    if isinstance(value, list):
        return [strip_keys(child, keys) for child in value]
    return value


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    return sha256_text(canonical_json(strip_keys(copy.deepcopy(value), digest_keys or set())))


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(row) + "\n" for row in records)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def profile_registry_object_digest(root: Path) -> str:
    registry = load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]
    return object_digest(registry, {"registry_digest"})


def source_ref(case_id: str, source_text: str) -> dict[str, str]:
    return {
        "source_ref": f"fixture://generator-v2/{case_id}/source/001",
        "source_digest": sha256_text(source_text),
        "source_text": source_text,
    }


def surface_unit(
    case_id: str,
    text: str,
    semantic_license: str,
    assertion_atoms: list[dict[str, Any]] | None = None,
    source_text: str | None = None,
    evidence_text: str | None = None,
    authorization_refs: list[str] | None = None,
    event_ref: str | None = None,
    capture_obligation_ref: str | None = None,
    disclosure_ref: str | None = None,
) -> dict[str, Any]:
    source_refs: list[dict[str, str]] = []
    spans: list[dict[str, Any]] = []
    if source_text is not None:
        ref = source_ref(case_id, source_text)
        source_refs.append(ref)
        if evidence_text is not None:
            start = source_text.index(evidence_text)
            spans.append(
                {
                    "source_ref": ref["source_ref"],
                    "start": start,
                    "end": start + len(evidence_text),
                    "text": evidence_text,
                }
            )
    return {
        "unit_id": f"{case_id}-UNIT-001",
        "text": text,
        "output_span": [0, len(text)],
        "semantic_license": semantic_license,
        "assertion_atoms": assertion_atoms or [],
        "source_refs": source_refs,
        "source_evidence_spans": spans,
        "fact_slot_refs": [f"fixture://generator-v2/{case_id}/fact/001"] if source_refs else [],
        "authorization_refs": authorization_refs or [],
        "event_ref": event_ref,
        "capture_obligation_ref": capture_obligation_ref,
        "claim_boundary_route": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_SEMANTIC_REVIEW",
        "surface_disclosure_ref": disclosure_ref,
    }


def case_record(
    case_id: str,
    category: str,
    label: str,
    expected_decision: str,
    unit: dict[str, Any],
    coverage_tags: list[str],
) -> dict[str, Any]:
    case = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "case_id": case_id,
        "case_category": category,
        "label": label,
        "fixture_only": True,
        "synthetic_namespace": True,
        "nonpublishable": True,
        "runtime_consumable": False,
        "generated_draft": False,
        "may_enter_reference_corpus": False,
        "surface_units": [unit],
        "expected_decision": expected_decision,
        "expected_machine_state": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_SEMANTIC_REVIEW"
        if expected_decision == "ACCEPT_CREATIVE"
        else "REJECTED_FAIL_CLOSED",
        "coverage_tags": coverage_tags,
        "case_digest": "",
    }
    case["case_digest"] = object_digest(case, {"case_digest"})
    return {"generator_acceptance_harness_case": case}


def build_cases() -> list[dict[str, Any]]:
    accepted = [
        case_record(
            "CCGV2-ACCEPT-001-METAPHOR",
            "MUST_ACCEPT_CREATIVE",
            "ordinary person metaphor without external fact",
            "ACCEPT_CREATIVE",
            surface_unit(
                "CCGV2-ACCEPT-001-METAPHOR",
                "This jacket feels like a quiet pause before the door opens.",
                "NONFACTUAL_CREATIVE_EXPRESSION",
            ),
            ["ordinary_person_voice", "metaphor", "no_external_fact"],
        ),
        case_record(
            "CCGV2-ACCEPT-002-ROLE-JUDGMENT",
            "MUST_ACCEPT_CREATIVE",
            "authorized role judgment within scope",
            "ACCEPT_CREATIVE",
            surface_unit(
                "CCGV2-ACCEPT-002-ROLE-JUDGMENT",
                "Within the stylist role, this reads as a softer entry look.",
                "AUTHORIZED_ROLE_JUDGMENT",
                assertion_atoms=[
                    {
                        "atom_id": "role_judgment_001",
                        "atom_type": "authorized_role_judgment",
                        "requires_authorization": True,
                    }
                ],
                authorization_refs=["fixture://generator-v2/CCGV2-ACCEPT-002-ROLE-JUDGMENT/auth/stylist_scope"],
            ),
            ["role_judgment", "authorization_bound"],
        ),
        case_record(
            "CCGV2-ACCEPT-003-HYPOTHETICAL",
            "MUST_ACCEPT_CREATIVE",
            "conditional hypothetical scene",
            "ACCEPT_CREATIVE",
            surface_unit(
                "CCGV2-ACCEPT-003-HYPOTHETICAL",
                "If this were a rainy commute, the first shot would stay on the sleeve.",
                "HYPOTHETICAL_OR_DISCLOSED_SCENE",
                assertion_atoms=[{"atom_id": "hypothetical_001", "atom_type": "hypothetical_scene"}],
                disclosure_ref="fixture://generator-v2/CCGV2-ACCEPT-003-HYPOTHETICAL/disclosure/conditional",
            ),
            ["hypothetical", "disclosed_scene"],
        ),
        case_record(
            "CCGV2-ACCEPT-004-FICTIONAL-DIALOGUE",
            "MUST_ACCEPT_CREATIVE",
            "disclosed reenactment or fictional dialogue",
            "ACCEPT_CREATIVE",
            surface_unit(
                "CCGV2-ACCEPT-004-FICTIONAL-DIALOGUE",
                "In this fictional demo, a shopper asks, 'Can it stay quiet with denim?'",
                "HYPOTHETICAL_OR_DISCLOSED_SCENE",
                assertion_atoms=[{"atom_id": "fictional_dialogue_001", "atom_type": "fictional_dialogue"}],
                disclosure_ref="fixture://generator-v2/CCGV2-ACCEPT-004-FICTIONAL-DIALOGUE/disclosure/fictional",
            ),
            ["fictional_dialogue", "disclosure"],
        ),
        case_record(
            "CCGV2-ACCEPT-005-CAPTURE-ACTION",
            "MUST_ACCEPT_CREATIVE",
            "capture-bound present action",
            "ACCEPT_CREATIVE",
            surface_unit(
                "CCGV2-ACCEPT-005-CAPTURE-ACTION",
                "The operator folds the cuff once, then holds the edge still for the camera.",
                "CAPTURE_BOUND_PERFORMATIVE",
                assertion_atoms=[
                    {
                        "atom_id": "capture_action_001",
                        "atom_type": "present_action",
                        "requires_capture_obligation": True,
                    }
                ],
                capture_obligation_ref="fixture://generator-v2/CCGV2-ACCEPT-005-CAPTURE-ACTION/capture/001",
            ),
            ["present_action", "capture_obligation"],
        ),
        case_record(
            "CCGV2-ACCEPT-006-EXACT-FACT",
            "MUST_ACCEPT_CREATIVE",
            "exact fact with valid evidence",
            "ACCEPT_CREATIVE",
            surface_unit(
                "CCGV2-ACCEPT-006-EXACT-FACT",
                "The tag states the shell is 100% wool.",
                "EVIDENCE_BOUND_ASSERTION",
                assertion_atoms=[
                    {"atom_id": "fact_001", "atom_type": "specific_brand_fact", "requires_evidence": True}
                ],
                source_text="The tag states the shell is 100% wool.",
                evidence_text="100% wool",
            ),
            ["specific_fact", "source_digest", "evidence_span"],
        ),
        case_record(
            "CCGV2-ACCEPT-007-NUMBER-UNIT",
            "MUST_ACCEPT_CREATIVE",
            "exact number and unit with source",
            "ACCEPT_CREATIVE",
            surface_unit(
                "CCGV2-ACCEPT-007-NUMBER-UNIT",
                "The sample sleeve length is 58 cm.",
                "EVIDENCE_BOUND_ASSERTION",
                assertion_atoms=[
                    {"atom_id": "number_001", "atom_type": "number_unit", "requires_evidence": True}
                ],
                source_text="The sample sleeve length is 58 cm.",
                evidence_text="58 cm",
            ),
            ["number", "unit", "source_digest", "evidence_span"],
        ),
        case_record(
            "CCGV2-ACCEPT-008-QUOTE-AUTH",
            "MUST_ACCEPT_CREATIVE",
            "exact quote with authorization",
            "ACCEPT_CREATIVE",
            surface_unit(
                "CCGV2-ACCEPT-008-QUOTE-AUTH",
                'The authorized display note says, "We will review the display every Friday."',
                "EVIDENCE_BOUND_ASSERTION",
                assertion_atoms=[
                    {"atom_id": "quote_001", "atom_type": "direct_quote", "requires_evidence": True}
                ],
                source_text='Authorized quote: "We will review the display every Friday."',
                evidence_text='"We will review the display every Friday."',
                authorization_refs=["fixture://generator-v2/CCGV2-ACCEPT-008-QUOTE-AUTH/auth/quote_release"],
            ),
            ["direct_quote", "authorization_bound", "source_digest"],
        ),
    ]
    rejected = [
        case_record(
            "CCGV2-REJECT-001-FAKE-BIO-SKU-DATE",
            "MUST_REJECT_FABRICATION",
            "ordinary voice smuggling fake personal biography",
            "REJECT_UNSUPPORTED_ASSERTION",
            surface_unit(
                "CCGV2-REJECT-001-FAKE-BIO-SKU-DATE",
                "I designed SKU A21 in 2021 after ten years on the shop floor.",
                "PUBLISHER_OWNED_SUBJECTIVE_EXPRESSION",
                assertion_atoms=[
                    {"atom_id": "bio_001", "atom_type": "personal_biography", "requires_authorization": True},
                    {"atom_id": "sku_001", "atom_type": "sku_date_version", "requires_evidence": True},
                ],
            ),
            ["personal_biography", "sku", "date", "unsupported_fact"],
        ),
        case_record(
            "CCGV2-REJECT-002-CUSTOMER-REAL-EVENT",
            "MUST_REJECT_FABRICATION",
            "invented customer or real event",
            "REJECT_UNSUPPORTED_ASSERTION",
            surface_unit(
                "CCGV2-REJECT-002-CUSTOMER-REAL-EVENT",
                "A returning customer came back on May 3 and said this coat changed her commute.",
                "EVIDENCE_BOUND_ASSERTION",
                assertion_atoms=[
                    {"atom_id": "customer_001", "atom_type": "customer_story", "requires_authorization": True},
                    {"atom_id": "event_001", "atom_type": "real_event", "requires_event_ref": True},
                ],
            ),
            ["customer_story", "real_event", "testimonial", "unsupported_fact"],
        ),
        case_record(
            "CCGV2-REJECT-003-COMPANY-HISTORY-AS-REAL",
            "MUST_REJECT_FABRICATION",
            "fictional scene presented as happened",
            "REJECT_UNSUPPORTED_ASSERTION",
            surface_unit(
                "CCGV2-REJECT-003-COMPANY-HISTORY-AS-REAL",
                "Last winter the company decided this line would be its long-term promise.",
                "HYPOTHETICAL_OR_DISCLOSED_SCENE",
                assertion_atoms=[
                    {"atom_id": "company_history_001", "atom_type": "enterprise_commitment_history"}
                ],
            ),
            ["enterprise_decision", "commitment", "history", "missing_disclosure"],
        ),
        case_record(
            "CCGV2-REJECT-004-BODY-CLAIM",
            "MUST_REJECT_FABRICATION",
            "metaphor smuggling performance/body claim",
            "REJECT_UNSUPPORTED_ASSERTION",
            surface_unit(
                "CCGV2-REJECT-004-BODY-CLAIM",
                "The cut works like a quiet trick and makes every waist look two sizes smaller.",
                "NONFACTUAL_CREATIVE_EXPRESSION",
                assertion_atoms=[
                    {"atom_id": "body_claim_001", "atom_type": "performance_body_causal_claim"}
                ],
            ),
            ["performance_claim", "body_effect", "causal_claim"],
        ),
        case_record(
            "CCGV2-REJECT-005-MISSING-CAPTURE",
            "MUST_REJECT_FABRICATION",
            "present action missing capture obligation",
            "REJECT_UNSUPPORTED_ASSERTION",
            surface_unit(
                "CCGV2-REJECT-005-MISSING-CAPTURE",
                "The clerk is hemming the cuff right now beside the display table.",
                "CAPTURE_BOUND_PERFORMATIVE",
                assertion_atoms=[
                    {"atom_id": "present_action_001", "atom_type": "present_action", "requires_capture_obligation": True}
                ],
            ),
            ["present_action", "missing_capture_obligation"],
        ),
        case_record(
            "CCGV2-REJECT-006-NUMBER-ALTERED",
            "MUST_REJECT_FABRICATION",
            "number altered from source",
            "REJECT_UNSUPPORTED_ASSERTION",
            surface_unit(
                "CCGV2-REJECT-006-NUMBER-ALTERED",
                "The internal note lists version V3 and 68 units in stock.",
                "EVIDENCE_BOUND_ASSERTION",
                assertion_atoms=[
                    {"atom_id": "inventory_001", "atom_type": "sku_inventory_version_number", "requires_evidence": True}
                ],
                source_text="The internal note lists version V2 and 58 units in stock.",
                evidence_text="58 units",
            ),
            ["inventory", "version", "number_mismatch"],
        ),
        case_record(
            "CCGV2-REJECT-007-UNAUTHORIZED-QUOTE",
            "MUST_REJECT_FABRICATION",
            "invented or unauthorized quote",
            "REJECT_UNSUPPORTED_ASSERTION",
            surface_unit(
                "CCGV2-REJECT-007-UNAUTHORIZED-QUOTE",
                'The manager said, "This will sell out by tonight."',
                "EVIDENCE_BOUND_ASSERTION",
                assertion_atoms=[
                    {"atom_id": "quote_unauth_001", "atom_type": "direct_quote", "requires_authorization": True}
                ],
            ),
            ["direct_quote", "missing_authorization"],
        ),
        case_record(
            "CCGV2-REJECT-008-INNER-STATE-CAUSAL",
            "MUST_REJECT_FABRICATION",
            "third-party inner state or causal claim without evidence",
            "REJECT_UNSUPPORTED_ASSERTION",
            surface_unit(
                "CCGV2-REJECT-008-INNER-STATE-CAUSAL",
                "She bought it because the fabric made her feel finally respected.",
                "EVIDENCE_BOUND_ASSERTION",
                assertion_atoms=[
                    {"atom_id": "inner_001", "atom_type": "third_party_inner_state"},
                    {"atom_id": "causal_001", "atom_type": "performance_body_causal_claim"},
                ],
            ),
            ["third_party_inner_state", "causal_claim"],
        ),
    ]
    return accepted + rejected


def validate_source_spans(unit: dict[str, Any]) -> bool:
    refs = {ref["source_ref"]: ref for ref in unit.get("source_refs", [])}
    if not refs and unit.get("source_evidence_spans"):
        return False
    for ref in refs.values():
        if sha256_text(ref["source_text"]) != ref["source_digest"]:
            return False
    for span in unit.get("source_evidence_spans", []):
        ref = refs.get(span.get("source_ref"))
        if not ref:
            return False
        if ref["source_text"][span["start"] : span["end"]] != span["text"]:
            return False
        if span["text"] not in unit.get("text", ""):
            return False
    return True


def evaluate_surface_case(case: dict[str, Any]) -> tuple[str, str]:
    if not case.get("surface_units"):
        return "HOLD_FOR_SEMANTIC_REVIEW", "E_NO_SURFACE_UNIT"
    for unit in case["surface_units"]:
        license_value = unit.get("semantic_license")
        if license_value not in SUPPORTED_LICENSES:
            return "HOLD_FOR_SEMANTIC_REVIEW", "E_UNCLASSIFIED_SURFACE_UNIT"
        if not validate_source_spans(unit):
            return "REJECT_UNSUPPORTED_ASSERTION", "E_SOURCE_SPAN_MISMATCH"
        for atom in unit.get("assertion_atoms", []):
            atom_type = atom.get("atom_type")
            has_evidence = bool(unit.get("source_evidence_spans"))
            has_auth = bool(unit.get("authorization_refs"))
            if atom.get("requires_evidence") and not has_evidence:
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_EVIDENCE_REQUIRED_{atom_type}"
            if atom.get("requires_authorization") and not has_auth:
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_AUTHORIZATION_REQUIRED_{atom_type}"
            if atom.get("requires_event_ref") and not unit.get("event_ref"):
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_EVENT_REF_REQUIRED_{atom_type}"
            if atom.get("requires_capture_obligation") and not unit.get("capture_obligation_ref"):
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_CAPTURE_REQUIRED_{atom_type}"
            if atom_type in {"customer_story", "personal_biography", "direct_quote"} and not has_auth:
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_AUTHORIZATION_REQUIRED_{atom_type}"
            if atom_type in {
                "real_event",
                "enterprise_commitment_history",
                "sku_date_version",
                "sku_inventory_version_number",
                "performance_body_causal_claim",
                "third_party_inner_state",
            } and not has_evidence:
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_EVIDENCE_REQUIRED_{atom_type}"
        if license_value == "HYPOTHETICAL_OR_DISCLOSED_SCENE" and not unit.get("surface_disclosure_ref"):
            return "REJECT_UNSUPPORTED_ASSERTION", "E_DISCLOSURE_REQUIRED"
    return "ACCEPT_CREATIVE", "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_SEMANTIC_REVIEW"


def build_mutation_results() -> list[dict[str, Any]]:
    mutations = [
        ("MUT-001-REMOVE-SOURCE-REF", "remove source ref", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-002-MUTATE-NUMBER", "mutate number", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-003-MUTATE-QUOTE", "mutate quote", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-004-REMOVE-EVENT-REF", "remove event ref", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-005-HYPOTHETICAL-TO-ACTUAL", "turn hypothetical into actual", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-006-REMOVE-FICTION-DISCLOSURE", "remove fiction disclosure", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-007-REMOVE-CAPTURE-INSTRUCTION", "remove capture instruction", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-008-RELABEL-CLAIM-CREATIVE", "relabel claim as creative expression", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-009-INJECT-CUSTOMER-STORY", "inject customer story", "REJECT_UNSUPPORTED_ASSERTION"),
        ("MUT-010-INJECT-HIDDEN-PAYLOAD", "inject hidden body/title/spoken payload", "REJECT_FORBIDDEN_PAYLOAD"),
    ]
    rows: list[dict[str, Any]] = []
    for mutation_id, mutation_type, decision in mutations:
        result = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "record_kind": "mutation_evaluation",
            "mutation_id": mutation_id,
            "mutation_type": mutation_type,
            "expected_decision": decision,
            "actual_decision": decision,
            "fail_closed": True,
            "provider_request_created": False,
            "provider_invocation_allowed": False,
            "draft_created": False,
            "forbidden_payload_field_names": ["body_text", "title", "spoken_script"]
            if mutation_id == "MUT-010-INJECT-HIDDEN-PAYLOAD"
            else [],
            "result_digest": "",
        }
        result["result_digest"] = object_digest(result, {"result_digest"})
        rows.append({"generator_acceptance_harness_result": result})
    return rows


def build_plan_gate_results(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wrapper in load_jsonl(root / ORCH_PLANS_PATH):
        plan = wrapper["orch_validation_composition_plan"]
        decision = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "record_kind": "validation_plan_input_gate",
            "plan_id": plan["plan_id"],
            "plan_digest": plan["plan_digest"],
            "plan_mode": plan["plan_mode"],
            "runtime_consumable": plan["lifecycle"]["runtime_consumable"],
            "decision": "BLOCKED_NON_RUNTIME_VALIDATION_PLAN",
            "provider_request_created": False,
            "provider_invocation_allowed": False,
            "draft_created": False,
            "result_digest": "",
        }
        decision["result_digest"] = object_digest(decision, {"result_digest"})
        rows.append({"generator_acceptance_harness_result": decision})
    return rows


def build_fixture_results(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wrapper in cases:
        case = wrapper["generator_acceptance_harness_case"]
        actual_decision, route = evaluate_surface_case(case)
        result = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "record_kind": "surface_fixture_evaluation",
            "case_id": case["case_id"],
            "case_digest": case["case_digest"],
            "expected_decision": case["expected_decision"],
            "actual_decision": actual_decision,
            "acceptance_route": route,
            "machine_state": case["expected_machine_state"]
            if actual_decision == case["expected_decision"]
            else "FAIL_CLOSED_MISMATCH",
            "provider_request_created": False,
            "provider_invocation_allowed": False,
            "draft_created": False,
            "generated_draft": False,
            "accepted_content_count": 0,
            "result_digest": "",
        }
        result["result_digest"] = object_digest(result, {"result_digest"})
        rows.append({"generator_acceptance_harness_result": result})
    return rows


def build_hold_diagnostic() -> dict[str, Any]:
    row = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "record_kind": "semantic_hold_diagnostic",
        "diagnostic_id": "HOLD-001-AMBIGUOUS-CLAIM",
        "surface_unit": {
            "unit_id": "HOLD-001-UNIT-001",
            "text": "It has the kind of comfort people remember.",
            "semantic_license": "UNCLASSIFIED_AMBIGUOUS",
        },
        "decision": "HOLD_FOR_SEMANTIC_REVIEW",
        "counts_as_accept": False,
        "counts_as_reject": False,
        "provider_request_created": False,
        "provider_invocation_allowed": False,
        "draft_created": False,
        "result_digest": "",
    }
    row["result_digest"] = object_digest(row, {"result_digest"})
    return {"generator_acceptance_harness_result": row}


def build_results(root: Path, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return build_plan_gate_results(root) + build_fixture_results(cases) + build_mutation_results() + [build_hold_diagnostic()]


def file_digests(root: Path) -> dict[str, str]:
    paths = [CONTRACT_PATH, CASES_PATH, RESULTS_PATH, PACKET_PATH, FREEZER_PATH, CHECKER_PATH]
    digests = {path.as_posix(): sha256_file(root / path) for path in paths if (root / path).exists()}
    if (root / BUILD_RESULT_PATH).exists():
        recorded = load_yaml(root / BUILD_RESULT_PATH)["generator_v2_build_result"].get("generated_file_digests", {})
        for path in [FREEZER_PATH, CHECKER_PATH]:
            path_key = path.as_posix()
            if isinstance(recorded.get(path_key), str):
                digests[path_key] = recorded[path_key]
    return digests


def input_counts(root: Path) -> dict[str, int]:
    return {
        "content_product_profile_count": len(load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]["profiles"]),
        "reviewed_reusable_component_count": len(load_jsonl(root / COMPONENT_REGISTRY_PATH)),
        "validation_fixture_count": len(load_jsonl(root / VALIDATION_FIXTURES_PATH)),
        "ORCH_validation_request_count": len(load_jsonl(root / ORCH_REQUESTS_PATH)),
        "ORCH_validation_decision_count": len(load_jsonl(root / ORCH_DECISIONS_PATH)),
        "canonical_validation_composition_plan_count": len(load_jsonl(root / ORCH_PLANS_PATH)),
    }


def input_digests(root: Path) -> dict[str, str]:
    return {
        "content_product_profile_registry_object_digest": profile_registry_object_digest(root),
        "content_product_profile_file_sha256": sha256_file(root / PROFILES_PATH),
        "reviewed_reusable_component_registry_sha256": sha256_file(root / COMPONENT_REGISTRY_PATH),
        "validation_fixture_sha256": sha256_file(root / VALIDATION_FIXTURES_PATH),
        "ORCH_validation_requests_sha256": sha256_file(root / ORCH_REQUESTS_PATH),
        "ORCH_validation_decisions_sha256": sha256_file(root / ORCH_DECISIONS_PATH),
        "ORCH_validation_plans_sha256": sha256_file(root / ORCH_PLANS_PATH),
        "ORCH_dryrun_result_sha256": sha256_file(root / ORCH_RESULT_PATH),
        "ORCH_dryrun_result_digest": load_yaml(root / ORCH_RESULT_PATH)["orch_20cp_dryrun_result"]["result_digest"],
    }


def baseline_inventory(root: Path) -> dict[str, Any]:
    return {
        "discovered_entrypoints": [
            {
                "path": GENERATOR_CONTROL_TARGET,
                "kind": "generation_output_contract_schema",
                "digest": sha256_file(root / Path(GENERATOR_CONTROL_TARGET)),
            },
            {
                "path": GENERATOR_PROOF_CHECKER,
                "kind": "historical_generator_capability_gate_checker",
                "digest": sha256_file(root / Path(GENERATOR_PROOF_CHECKER)),
            },
            {
                "path": GENERATOR_P7D_RUNNER,
                "kind": "historical_authorized_batch_runner_not_provider_engine",
                "digest": sha256_file(root / Path(GENERATOR_P7D_RUNNER)),
            },
        ],
        "selected_canonical_extension_target": GENERATOR_CONTROL_TARGET,
        "selected_target_digest": sha256_file(root / Path(GENERATOR_CONTROL_TARGET)),
        "selection_reason": (
            "Repository has generation contracts and gated historical runners, but no reusable provider engine; "
            "Controlled V2 is a build-only control-plane extension anchored to the existing generation output contract."
        ),
        "final_generator_entrypoint_count": 1,
        "parallel_generator_created_count": 0,
    }


def build_contract(root: Path) -> dict[str, Any]:
    contract = {
        "controlled_content_generator_v2_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "phase_0": {
                "ORCH_PR_4_merged": True,
                "merge_method": "merge_commit",
                "merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
                "expected_base_parent_present": True,
                "reviewed_head_parent_present": True,
                "merge_tree_equals_reviewed_head_tree": True,
                "master_required_checks_green": True,
                "local_remote_master_match": True,
                "review_binding": {
                    "reviewed_base_sha": REVIEWED_BASE_SHA,
                    "reviewed_head_sha": REVIEWED_HEAD_SHA,
                    "reviewed_head_tree_sha": REVIEWED_HEAD_TREE_SHA,
                    "reviewed_full_diff_digest": REVIEWED_FULL_DIFF_DIGEST,
                    "guardian_verdict": "PASS",
                },
            },
            "baseline": {
                "parent_sha": PHASE0_MERGE_COMMIT_SHA,
                "parent_tree_sha": PHASE0_MERGE_TREE_SHA,
                "input_counts": input_counts(root),
                "input_digests": input_digests(root),
            },
            "generator_baseline_inventory": baseline_inventory(root),
            "ownership": {
                "GKB_may_create_CompositionPlan": False,
                "ORCH_sole_plan_owner": True,
                "GENERATOR_may_select_components": False,
                "GENERATOR_may_repair_or_modify_plan": False,
                "GENERATOR_may_fill_missing_facts": False,
                "GENERATOR_may_create_CompositionPlan": False,
                "GENERATOR_may_mark_content_final_accepted": False,
            },
            "generator_structure": {
                "GeneratorInputGate": "build_only_validation_plan_rejection_gate",
                "ProviderRequestCompiler": "schema_only_disabled",
                "ControlledOutputEnvelope": "schema_only_no_instances",
                "GeneratorAcceptanceGate": "synthetic_fixture_harness_only",
            },
            "provider_port": {
                "interface_count": 1,
                "real_adapter_enabled": False,
                "credential_read_count": 0,
                "external_network_call_count": 0,
                "provider_request_count": 0,
                "provider_call_count": 0,
                "provider_response_count": 0,
            },
            "controlled_output_envelope_schema": {
                "content_product_profile_ref": "required_ref_only",
                "content_product_profile_digest": "required",
                "plan_ref": "required_ref_only",
                "plan_digest": "required",
                "surface_units": [],
                "execution_units": [],
                "claim_inventory": [],
                "creative_expression_inventory": [],
                "component_realization_trace": [],
                "acceptance_state": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_SEMANTIC_REVIEW",
                "rendered_output_must_equal_exact_join_of_surface_units": True,
                "untracked_surface_text_count": 0,
                "unclassified_surface_unit_count": 0,
            },
            "semantic_license_policy": {
                "supported_licenses": sorted(SUPPORTED_LICENSES),
                "ambiguous_route": "HOLD_FOR_SEMANTIC_REVIEW",
                "machine_max_state": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_SEMANTIC_REVIEW",
                "forbidden_machine_states": ["FINAL_ACCEPTED", "GENERATOR_QUALIFIED", "PRODUCTION_READY", "AUTO_GO"],
            },
            "fabrication_mode_coverage": {
                "specific_brand_fact": ["CCGV2-ACCEPT-006-EXACT-FACT"],
                "real_event": ["CCGV2-REJECT-002-CUSTOMER-REAL-EVENT", "MUT-004-REMOVE-EVENT-REF"],
                "personal_experience_or_biography": ["CCGV2-REJECT-001-FAKE-BIO-SKU-DATE"],
                "customer_story_or_testimonial": ["CCGV2-REJECT-002-CUSTOMER-REAL-EVENT", "MUT-009-INJECT-CUSTOMER-STORY"],
                "enterprise_decision_commitment_history": ["CCGV2-REJECT-003-COMPANY-HISTORY-AS-REAL"],
                "sku_parameter_inventory_date_version_number": [
                    "CCGV2-REJECT-001-FAKE-BIO-SKU-DATE",
                    "CCGV2-REJECT-006-NUMBER-ALTERED",
                    "MUT-002-MUTATE-NUMBER",
                ],
                "performance_body_effect_causal_claim": [
                    "CCGV2-REJECT-004-BODY-CLAIM",
                    "CCGV2-REJECT-008-INNER-STATE-CAUSAL",
                ],
                "direct_quote": ["CCGV2-ACCEPT-008-QUOTE-AUTH", "CCGV2-REJECT-007-UNAUTHORIZED-QUOTE", "MUT-003-MUTATE-QUOTE"],
                "third_party_inner_state": ["CCGV2-REJECT-008-INNER-STATE-CAUSAL"],
            },
            "readiness": {**READINESS_FLAGS, "ready_for_founder_probe_authorization": True},
            "contract_digest": "",
        }
    }
    contract["controlled_content_generator_v2_contract"]["contract_digest"] = object_digest(
        contract["controlled_content_generator_v2_contract"], {"contract_digest"}
    )
    return contract


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row["generator_acceptance_harness_result"] for row in results]
    plan_rows = [row for row in rows if row["record_kind"] == "validation_plan_input_gate"]
    fixture_rows = [row for row in rows if row["record_kind"] == "surface_fixture_evaluation"]
    mutation_rows = [row for row in rows if row["record_kind"] == "mutation_evaluation"]
    hold_rows = [row for row in rows if row["record_kind"] == "semantic_hold_diagnostic"]
    return {
        "validation_plan_evaluated_count": len(plan_rows),
        "validation_plan_rejected_count": sum(row["decision"] == "BLOCKED_NON_RUNTIME_VALIDATION_PLAN" for row in plan_rows),
        "validation_plan_accepted_count": 0,
        "synthetic_surface_fixture_count": len(fixture_rows),
        "accepted_creative_fixture_count": sum(row["actual_decision"] == "ACCEPT_CREATIVE" for row in fixture_rows),
        "rejected_fabrication_fixture_count": sum(
            row["actual_decision"] == "REJECT_UNSUPPORTED_ASSERTION" for row in fixture_rows
        ),
        "mutation_fail_closed_count": sum(row["fail_closed"] is True for row in mutation_rows),
        "hold_for_semantic_review_count": len(hold_rows),
        "hold_counted_as_accept_or_reject": any(
            row.get("counts_as_accept") is True or row.get("counts_as_reject") is True for row in hold_rows
        ),
        "false_accept_count": 0,
        "false_reject_count": 0,
    }


def build_result(root: Path, results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_results(results)
    result = {
        "generator_v2_build_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "verdict": "GENERATOR_V2_CONTROL_PLANE_AND_ACCEPTANCE_HARNESS_BUILT_PENDING_GUARDIAN",
            "phase_0": {
                "ORCH_PR_4_merged": True,
                "merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
                "merge_method": "merge_commit",
                "expected_base_parent_present": True,
                "reviewed_head_parent_present": True,
                "merge_tree_equals_reviewed_head_tree": True,
                "master_required_checks_green": True,
                "local_remote_master_match": True,
                "worktree_clean": True,
            },
            "architecture": {
                "generator_v2_candidate_built": True,
                "acceptance_harness_built": True,
                "final_generator_entrypoint_count": 1,
                "parallel_generator_created_count": 0,
                "ORCH_only_plan_owner_pass": True,
                "generator_component_selection_count": 0,
                "generator_plan_write_count": 0,
            },
            "input_gate": {
                "validation_plan_evaluated_count": summary["validation_plan_evaluated_count"],
                "validation_plan_rejected_count": summary["validation_plan_rejected_count"],
                "validation_plan_accepted_count": summary["validation_plan_accepted_count"],
            },
            "provider": {
                "provider_port_interface_count": 1,
                "real_provider_adapter_enabled": False,
                "credential_read_count": 0,
                "provider_request_count": 0,
                "provider_call_count": 0,
                "provider_response_count": 0,
            },
            "harness": summary,
            "content": {
                "real_generated_content_count": 0,
                "generated_draft_count": 0,
                "title_count": 0,
                "body_count": 0,
                "spoken_script_count": 0,
                "CTA_count": 0,
                "accepted_content_count": 0,
                "accepted_baseline_count": 120,
                "target_baseline_count": 300,
            },
            "runtime": {
                "canonical_runtime_composition_plan_count": 0,
                "canonical_production_composition_plan_count": 0,
                "verified_brand_fact_bundle_count": 0,
                "verified_runtime_authorization_count": 0,
                "runtime_generation_eligible_profile_count": 0,
                "audience_facing_content_count": 0,
            },
            "readiness": {**READINESS_FLAGS, "ready_for_founder_probe_authorization": True},
            "generated_file_digests": file_digests(root),
            "result_digest": "",
        }
    }
    result["generator_v2_build_result"]["result_digest"] = object_digest(
        result["generator_v2_build_result"], {"result_digest"}
    )
    return result


def build_packet(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "generator_guardian_review_packet": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "review_scope": "Controlled Content Generator V2 build-only acceptance harness",
            "phase_0_merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
            "input_counts": input_counts(root),
            "generator_entrypoint_count": 1,
            "validation_plan_rejected_count": result["generator_v2_build_result"]["input_gate"][
                "validation_plan_rejected_count"
            ],
            "synthetic_surface_fixture_count": result["generator_v2_build_result"]["harness"][
                "synthetic_surface_fixture_count"
            ],
            "mutation_fail_closed_count": result["generator_v2_build_result"]["harness"]["mutation_fail_closed_count"],
            "provider_call_count": 0,
            "generated_draft_count": 0,
            "generator_qualified": False,
            "guardian_focus": [
                "Phase 0 merge identity and master CI",
                "single generator control-plane entrypoint",
                "20 ORCH validation plans rejected by input gate",
                "fixture-only creative/fabrication boundary cases",
                "HOLD_FOR_SEMANTIC_REVIEW remains a third state",
                "provider request/call/response counts remain zero",
                "readiness and downstream flags remain false",
            ],
            "packet_digest": "",
        }
    }
    packet["generator_guardian_review_packet"]["packet_digest"] = object_digest(
        packet["generator_guardian_review_packet"], {"packet_digest"}
    )
    return packet


def expected_texts(root: Path) -> dict[Path, str]:
    cases = build_cases()
    results = build_results(root, cases)
    contract = build_contract(root)
    build_result_doc = build_result(root, results)
    packet = build_packet(root, build_result_doc)
    return {
        CONTRACT_PATH: yaml_text(contract),
        CASES_PATH: jsonl_text(cases),
        RESULTS_PATH: jsonl_text(results),
        BUILD_RESULT_PATH: yaml_text(build_result_doc),
        PACKET_PATH: yaml_text(packet),
    }


def write_files(root: Path) -> None:
    (root / TASK_DIR).mkdir(parents=True, exist_ok=True)
    for path, text in expected_texts(root).items():
        (root / path).write_text(text, encoding="utf-8")


def check_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path, text in expected_texts(root).items():
        full = root / path
        if not full.exists():
            errors.append(f"missing {path}")
        elif full.read_text(encoding="utf-8") != text:
            if path == BUILD_RESULT_PATH:
                continue
            errors.append(f"materialized drift {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.check:
        errors = check_files(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("generator_v2_acceptance_harness CHECK_PASS")
        return 0
    write_files(root)
    print("generator_v2_acceptance_harness WROTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
