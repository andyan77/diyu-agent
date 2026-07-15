#!/usr/bin/env python3
"""Direct deterministic checks for the lightweight Dify conversation shell."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence, cast


Doc = dict[str, object]
BASELINE: Final = "95b8b1700b7e96b1d2383465713bef8c36e7f6cb"
ALLOWED_ROOT: Final = "14_dify_shell/dify_content_shell_001/"
FLOW_FILE: Final = "conversation_flow.version_neutral.v1.json"
MAPPING_FILE: Final = "state_action_mapping.v1.json"
JOURNEYS_FILE: Final = "journeys.simulated.v1.json"
RESULT_FILE: Final = "result_and_review_request.v1.json"
CORE_PACKAGE_FILES: Final = {FLOW_FILE, MAPPING_FILE, JOURNEYS_FILE, RESULT_FILE, "check_dify_content_shell.py"}
ACCEPTANCE_IDS: Final = tuple(f"PKG4-A{number:02d}" for number in range(1, 13)) + tuple(
    f"PKG4-S{number:02d}" for number in range(1, 9)
)
SUMMARY_FIELDS: Final = tuple("为哪个内容账号 讲什么 给谁看 发到哪里 现有真实材料 还缺什么 采用什么大方向".split())
FEEDBACK_FIELDS: Final = ("selected_candidate_ref", "necessary_modification", "short_reason")
READINESS_FLAGS: Final = tuple(
    "candidatepack_ready KE_ready RAG_ready DIFY_ready production_servable generation_eligible generation_allowed "
    "generator_qualified retrieval_ready runtime_ready release_ready production_ready".split()
)
EXPECTED_STAGE_IDS: Final = tuple(
    "CHAT INSPIRATION_OR_CLARIFICATION REQUIREMENT_SUMMARY_AND_CONFIRMATION CONTENT_PREPARATION_PLACEHOLDER "
    "CANDIDATES_AND_LOCAL_REVISION ACTION_CARD".split()
)
EXPECTED_RESPONSIBILITIES: Final = frozenset(
    "ORDINARY_CHAT INSPIRATION_CLARIFICATION_AND_SUMMARY CONFIRMED_PREPARATION_PLACEHOLDER "
    "CANDIDATE_AUTHORING_AND_REVISION_PLACEHOLDER CANDIDATE_DISPLAY_SELECTION_AND_MINIMAL_FEEDBACK "
    "PLAIN_LANGUAGE_ACTION_CARD".split()
)
EXPECTED_CASE_IDS: Final = frozenset(
    "CHAT-TWO-TURNS ENTRY-INSPIRATION ENTRY-VAGUE ENTRY-CLEAR UNCONFIRMED-BLOCKS-PREPARE "
    "SERVER-CONFIRMED-ACCOUNT EDIT-REQUIRES-RECONFIRM CANCEL-RETURNS-TO-CHAT "
    "UNTRUSTED-IDENTITY-SOURCES-REJECTED TWO-CANDIDATES-SELECT-REVISE-RETURN "
    "THREE-CANDIDATES-SELECT-ACCEPT CHANGE-REQUIREMENT-RECONFIRM MISSING-FACT MISSING-MATERIAL "
    "MISSING-AUTHORIZATION OUT-OF-SCOPE DEGRADE-SAFELY BLOCK-UNSAFE-REQUEST".split()
)
DIRECT_CASE_ASSERTIONS: Final[tuple[tuple[str, str, str, object], ...]] = (
    ("CHAT-TWO-TURNS", "input", "turn_count", 2),
    ("CHAT-TWO-TURNS", "expected", "prepare_placeholder_requested", False),
    ("CHAT-TWO-TURNS", "expected", "author_placeholder_requested", False),
    ("ENTRY-INSPIRATION", "expected", "direction_count", 3),
    ("ENTRY-CLEAR", "expected", "experience", "REQUIREMENT_SUMMARY"),
    ("ENTRY-CLEAR", "expected", "prepare_placeholder_requested", False),
    ("UNCONFIRMED-BLOCKS-PREPARE", "input", "requirement_confirmation", "DRAFT"),
    ("UNCONFIRMED-BLOCKS-PREPARE", "input", "scope_authority", "SERVER_CONFIRMED"),
    ("UNCONFIRMED-BLOCKS-PREPARE", "expected", "prepare_placeholder_requested", False),
    ("UNCONFIRMED-BLOCKS-PREPARE", "expected", "confirmation_required", True),
    ("SERVER-CONFIRMED-ACCOUNT", "input", "requirement_confirmation", "CONFIRMED"),
    ("SERVER-CONFIRMED-ACCOUNT", "input", "scope_authority", "SERVER_CONFIRMED"),
    ("SERVER-CONFIRMED-ACCOUNT", "expected", "prepare_placeholder_requested", True),
    ("SERVER-CONFIRMED-ACCOUNT", "expected", "external_service_called", False),
    ("EDIT-REQUIRES-RECONFIRM", "expected", "requirement_confirmation", "DRAFT"),
    ("EDIT-REQUIRES-RECONFIRM", "expected", "selected_candidate_ref", "UNBOUND"),
    ("EDIT-REQUIRES-RECONFIRM", "expected", "prepare_placeholder_requested", False),
    ("CANCEL-RETURNS-TO-CHAT", "expected", "mode", "CHAT"),
    ("CANCEL-RETURNS-TO-CHAT", "expected", "returns_to_chat", True),
    ("UNTRUSTED-IDENTITY-SOURCES-REJECTED", "expected", "prepare_placeholder_requested", False),
    ("UNTRUSTED-IDENTITY-SOURCES-REJECTED", "expected", "action_card", "REQUEST_AUTHORIZATION"),
    ("TWO-CANDIDATES-SELECT-REVISE-RETURN", "input", "candidate_set_ref", "two_candidates"),
    ("TWO-CANDIDATES-SELECT-REVISE-RETURN", "expected", "candidate_count", 2),
    ("TWO-CANDIDATES-SELECT-REVISE-RETURN", "expected", "selection_is_displayed_candidate", True),
    ("TWO-CANDIDATES-SELECT-REVISE-RETURN", "expected", "local_revision_bound_to_selection", True),
    ("TWO-CANDIDATES-SELECT-REVISE-RETURN", "expected", "local_revision_bound_to_confirmed_requirement", True),
    ("THREE-CANDIDATES-SELECT-ACCEPT", "input", "candidate_set_ref", "three_candidates"),
    ("THREE-CANDIDATES-SELECT-ACCEPT", "expected", "candidate_count", 3),
    ("THREE-CANDIDATES-SELECT-ACCEPT", "expected", "selection_is_displayed_candidate", True),
    ("THREE-CANDIDATES-SELECT-ACCEPT", "expected", "publish_allowed", False),
    ("CHANGE-REQUIREMENT-RECONFIRM", "expected", "requirement_confirmation", "DRAFT"),
    ("CHANGE-REQUIREMENT-RECONFIRM", "expected", "selected_candidate_ref", "UNBOUND"),
    ("CHANGE-REQUIREMENT-RECONFIRM", "expected", "prepare_placeholder_requested", False),
)
FORBIDDEN_ENGINE_KEYS: Final = frozenset("states routes transitions from event to requires effects guards".split())
VISIBLE_LEAK_PATTERNS: Final = (
    re.compile(r"\bCP[0-9]{2}\b"),
    re.compile(r"\b(?:BNO|BRV|VGA|BCL|FC)-[0-9]{2}\b"),
    re.compile(r"\b(?:G1V11|RCV2)-[A-Z0-9-]+\b"),
    re.compile(
        r"\b(?:all_required_inputs_present|required_source_missing|required_fact_missing|"
        r"required_authorization_missing)\b"
    ),
    re.compile(r"\bE_[A-Z0-9_]+\b"),
    re.compile(r"\b(?:component_id|content_product_id|route_code|raw_error_code|internal_route_id)\b"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]+|api[_-]?key|password|secret)\b", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
)
PINNED_CORE_FILES: Final = {
    (
        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
        "clean_120_reference_corpus_freeze_001/founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
    ): "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91",
    (
        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/controlled_composition_v2_001/"
        "b_channel_component_review_and_handoff_001/reviewed_reusable_component_registry.v0.4.jsonl"
    ): "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601",
}
PINNED_HISTORICAL_REVIEW_FILES: Final = {
    "reviews/novice_experience/review-output-2026-07-15-025016.md": (
        "69c2e45ece23d21e83777dc0c7f99c34e378d21741dae5b582a6c2399b0e06d4"
    ),
    "reviews/architecture_trust/review-output-2026-07-15-025016.md": (
        "a55b0ebfd7a9bb75efe2011b89166d7efab8c52039698d91eb0dc1dca889ba71"
    ),
    "reviews/findings-ledger.json": "6700586afd47055864c72197eac26d28013ba5405cdee720f94590b3290d0747",
}


@dataclass(frozen=True)
class Summary:
    errors: tuple[str, ...]
    journey_cases: int
    visible_strings: int


def to_doc(value: object, label: str) -> Doc:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return cast(Doc, value)


def to_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return cast(list[object], value)


def to_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def to_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def to_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    return value


def doc(parent: Doc, key: str, label: str = "document") -> Doc:
    return to_doc(parent.get(key), f"{label}.{key}")


def items(parent: Doc, key: str, label: str = "document") -> list[object]:
    return to_list(parent.get(key), f"{label}.{key}")


def text(parent: Doc, key: str, label: str = "document") -> str:
    return to_str(parent.get(key), f"{label}.{key}")


def flag(parent: Doc, key: str, label: str = "document") -> bool:
    return to_bool(parent.get(key), f"{label}.{key}")


def load(path: Path) -> Doc:
    try:
        with path.open(encoding="utf-8") as handle:
            value: object = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {path}: {exc}") from exc
    return to_doc(value, str(path))


def visible_strings(value: object, visible: bool = False) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in cast(Doc, value).items():
            found.extend(visible_strings(child, visible or key.startswith("user_visible")))
    elif isinstance(value, list):
        for child in cast(list[object], value):
            found.extend(visible_strings(child, visible))
    elif visible and isinstance(value, str):
        found.append(value)
    return found


def structural_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in cast(Doc, value).items():
            found.add(key)
            found.update(structural_keys(child))
    elif isinstance(value, list):
        for child in cast(list[object], value):
            found.update(structural_keys(child))
    return found


def git(repo: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *arguments], cwd=repo, check=False, capture_output=True, text=True, encoding="utf-8")


class PackageChecker:
    def __init__(self, flow: Doc, mapping: Doc, journeys: Doc, result: Doc, repo: Path, root: Path) -> None:
        self.flow = flow
        self.mapping = mapping
        self.journeys = journeys
        self.result = result
        self.repo = repo
        self.root = root
        self.app = doc(flow, "application", "flow")
        self.errors: list[str] = []
        self.cases: dict[str, Doc] = {}
        self.candidate_refs: dict[str, frozenset[str]] = {}

    def error(self, code: str, message: str) -> None:
        self.errors.append(f"{code}: {message}")

    def expect(self, case_id: str, section: Doc, key: str, expected: object, code: str) -> None:
        if section.get(key) != expected:
            self.error(code, f"{case_id} must declare {key}={expected!r}")

    def case(self, case_id: str) -> tuple[Doc, Doc]:
        case = self.cases.get(case_id)
        if case is None:
            raise ValueError(f"missing journey case {case_id}")
        return doc(case, "simulated_inputs", case_id), doc(case, "expected", case_id)

    def check_lightweight_shape(self) -> None:
        forbidden = set()
        for candidate in (self.flow, self.mapping, self.journeys):
            forbidden.update(structural_keys(candidate) & FORBIDDEN_ENGINE_KEYS)
        if forbidden:
            self.error("S01_FORBIDDEN_RUNTIME_MODEL", f"generic workflow keys remain: {sorted(forbidden)}")

        constraints = doc(self.app, "lightweight_constraints", "application")
        for key in (
            "generic_route_language_implemented",
            "graph_traversal_implemented",
            "guard_evaluator_implemented",
            "effect_interpreter_implemented",
            "state_transition_runtime_implemented",
        ):
            if flag(constraints, key, "lightweight constraints"):
                self.error("S01_RUNTIME_ENGINE_PRESENT", f"{key} must remain false")
        if not flag(constraints, "interaction_stages_are_human_readable_guidance_only", "lightweight constraints"):
            self.error("S01_STAGE_SEMANTICS", "interaction stages must be guidance only")

        stage_ids: list[str] = []
        for raw_stage in items(self.app, "interaction_stages", "application"):
            stage = to_doc(raw_stage, "interaction stage")
            stage_ids.append(text(stage, "stage_id", "interaction stage"))
            if not flag(stage, "allows_return_to_chat", "interaction stage"):
                self.error("A03_RETURN_TO_CHAT", "every human-readable stage must allow return to chat")
            if flag(stage, "creates_plan", "interaction stage"):
                self.error("A06_PLAN_OWNERSHIP", "interaction guidance cannot create a plan")
            if flag(stage, "writes_brand_fact", "interaction stage"):
                self.error("A02_FACT_WRITE", "interaction guidance cannot write brand facts")
        if tuple(stage_ids) != EXPECTED_STAGE_IDS:
            self.error("S01_STAGE_SET", "only the six allowed human-readable stages may remain")

    def check_candidate_and_experience(self) -> None:
        candidate = doc(self.flow, "candidate", "flow")
        expected_values: tuple[tuple[str, object, str], ...] = (
            ("kind", "VERSION_NEUTRAL_FLOW_CANDIDATE", "A01_CANDIDATE_KIND"),
            ("target_dify_version", "UNKNOWN_NOT_VERIFIED", "A12_DIFY_VERSION"),
            ("native_dify_export", False, "A12_NATIVE_EXPORT"),
            ("importable_claimed", False, "A12_IMPORTABLE_CLAIM"),
            ("application_count", 1, "A01_APPLICATION_COUNT"),
            ("current_stage", "PENDING_SHARED_CHECKER_MERGE_AND_FINAL_FREEZE", "S07_CANDIDATE_STAGE"),
        )
        for key, expected, code in expected_values:
            if candidate.get(key) != expected:
                self.error(code, f"candidate {key} must be {expected!r}")
        if self.result.get("candidate_state") != "PENDING_SHARED_CHECKER_MERGE_AND_FINAL_FREEZE":
            self.error("S07_PREMATURE_SUCCESS", "r2 candidate must wait for the shared fix and final freeze")

        entry = doc(self.app, "entry_experience", "application")
        if entry.get("kind") != "NATURAL_CHAT" or flag(entry, "parameter_form_required", "entry experience"):
            self.error("A03_NATURAL_ENTRY", "entry must be natural chat without a parameter form")
        intent = doc(self.app, "intent_resolution", "application")
        for key in (
            "natural_language_parser_implemented",
            "keyword_classifier_implemented",
            "regex_intent_engine_implemented",
        ):
            if flag(intent, key, "intent resolution"):
                self.error("A03_FORBIDDEN_INTENT_ENGINE", f"{key} must remain false")
        if intent.get("local_journeys") != "EXPLICIT_SIMULATED_INTENT_RESULT_INJECTION":
            self.error("A03_SIMULATED_INTENT", "local journeys must inject explicit simulated results")

        if set(doc(self.app, "minimal_session_markers", "application")) != {
            "mode",
            "requirement_confirmation",
            "selected_candidate_ref",
        }:
            self.error("A10_SESSION_MARKERS", "only the three minimal session markers may remain")
        experience = doc(self.app, "user_experience", "application")
        direction_count = len(items(experience, "user_visible_inspiration_directions", "user experience"))
        if not 2 <= direction_count <= 3:
            self.error("A03_DIRECTION_COUNT", "inspiration must offer two or three directions")
        clarification = doc(experience, "clarification_policy", "user experience")
        minimum = to_int(clarification.get("questions_per_turn_minimum"), "question minimum")
        maximum = to_int(clarification.get("questions_per_turn_maximum"), "question maximum")
        if minimum < 1 or maximum > 3 or minimum > maximum:
            self.error("A03_QUESTION_COUNT", "clarification must ask one to three questions")
        if flag(clarification, "parameters_are_entry_requirement", "clarification policy"):
            self.error("A03_PARAMETER_GATE", "parameters cannot gate content creation")
        fields = tuple(
            to_str(value, "summary field")
            for value in items(experience, "user_visible_requirement_summary_fields", "user experience")
        )
        if fields != SUMMARY_FIELDS:
            self.error("A03_SUMMARY_FIELDS", "plain-language summary fields are incomplete")
        if len(items(experience, "user_visible_topic_categories", "user experience")) != 8:
            self.error("A09_TOPIC_COUNT", "the user surface must expose eight public categories")

        confirmation = doc(self.app, "confirmation_policy", "application")
        if confirmation.get("prepare_placeholder_requires_requirement_confirmation") != "CONFIRMED":
            self.error("A04_CONFIRMATION_BOUNDARY", "preparation requires confirmed requirements")
        if confirmation.get("prepare_placeholder_requires_scope_authority") != "SERVER_CONFIRMED":
            self.error("A04_SCOPE_BOUNDARY", "preparation requires server-confirmed scope")
        for key in ("requirement_edit_invalidates_confirmation", "requirement_edit_clears_selected_candidate"):
            if not flag(confirmation, key, "confirmation policy"):
                self.error("A04_RECONFIRMATION", f"{key} must remain true")
        if flag(confirmation, "untrusted_sources_may_unlock_prepare", "confirmation policy"):
            self.error("A05_UNTRUSTED_UNLOCK", "untrusted sources cannot unlock preparation")

        policy = doc(self.app, "candidate_policy", "application")
        if policy.get("minimum_count") != 2 or policy.get("maximum_count") != 3:
            self.error("A07_CANDIDATE_RANGE", "candidate range must remain two to three")
        for key in (
            "selection_must_reference_displayed_candidate",
            "local_revision_requires_confirmed_requirement",
            "local_revision_requires_selected_candidate",
            "requirement_change_requires_reconfirmation",
            "human_experience_review_required",
        ):
            if not flag(policy, key, "candidate policy"):
                self.error("A07_CANDIDATE_BINDING", f"{key} must remain true")
        for key in ("machine_claims_semantic_difference", "near_synonym_rewording_accepted_as_difference"):
            if flag(policy, key, "candidate policy"):
                self.error("A07_FALSE_DIFFERENCE", f"{key} must remain false")

        feedback = doc(self.app, "feedback_policy", "application")
        stored = tuple(to_str(value, "feedback field") for value in items(feedback, "stored_fields", "feedback"))
        if stored != FEEDBACK_FIELDS:
            self.error("A10_FEEDBACK_FIELDS", "feedback must contain only the three minimal fields")
        for key in ("persistent_memory_implemented", "user_profile_implemented", "preference_system_implemented"):
            if flag(feedback, key, "feedback"):
                self.error("A10_HEAVY_MEMORY", f"{key} must remain false")

    def check_boundaries(self) -> None:
        identity = doc(self.app, "identity_policy", "application")
        for key in ("dify_user_field", "self_reported_company_store_or_account", "conversation_variables"):
            if identity.get(key) != "UNTRUSTED_HINT":
                self.error("A05_UNTRUSTED_IDENTITY", f"{key} must remain an untrusted hint")
        if identity.get("server_confirmed_scope") != "TRUSTED_REFERENCE":
            self.error("A05_SERVER_AUTHORITY", "server-confirmed scope must remain a trusted reference")
        if flag(identity, "trusted_scope_model_copied", "identity policy"):
            self.error("A06_MODEL_COPY", "trusted scope model cannot be copied")
        if flag(identity, "hint_may_grant_identity_scope_or_permission", "identity policy"):
            self.error("A05_HINT_GRANT", "a hint cannot grant identity, scope, or permission")

        for key, value in doc(self.app, "ownership_boundaries", "application").items():
            if to_bool(value, f"ownership boundary {key}"):
                code = "A02_FACT_WRITE" if key == "writes_brand_fact" else "A06_OWNERSHIP_DRIFT"
                self.error(code, f"{key} must remain false")
        bindings = doc(self.app, "external_bindings", "application")
        for key, value in bindings.items():
            if key == "external_call_count":
                if to_int(value, "external call count") != 0:
                    self.error("A12_EXTERNAL_CALL", "external call count must be zero")
            elif to_bool(value, f"external binding {key}"):
                self.error("A12_EXTERNAL_BINDING", f"{key} must remain false")
        readiness = doc(self.app, "readiness", "application")
        if tuple(readiness) != READINESS_FLAGS:
            self.error("A12_READINESS_SET", "readiness flags do not match the public contract")
        for key in READINESS_FLAGS:
            if flag(readiness, key, "readiness"):
                self.error("A12_FALSE_READY", f"{key} must remain false")

    def check_mapping(self) -> None:
        if self.mapping.get("mapping_kind") != "THIN_ACTION_OWNERSHIP_REFERENCE_ONLY":
            self.error("A06_MAPPING_KIND", "mapping must remain a thin action-ownership reference")
        if flag(self.mapping, "copies_public_models", "mapping") or flag(
            self.mapping, "is_flow_source_of_truth", "mapping"
        ):
            self.error("A06_MODEL_COPY", "mapping cannot copy public models or become a flow source")
        if "state_mappings" in self.mapping:
            self.error("S01_STATE_MAPPING", "per-state mapping must not return")

        areas: list[str] = []
        for raw in items(self.mapping, "interaction_responsibilities", "mapping"):
            responsibility = to_doc(raw, "interaction responsibility")
            areas.append(text(responsibility, "experience_area", "interaction responsibility"))
            for key, code in (
                ("creates_light_content_plan", "A06_PLAN_OWNERSHIP"),
                ("writes_brand_fact", "A02_FACT_WRITE"),
                ("external_call_implemented", "A12_EXTERNAL_CALL"),
            ):
                if flag(responsibility, key, "interaction responsibility"):
                    self.error(code, f"interaction responsibility {key} must remain false")
        if len(areas) != len(set(areas)) or set(areas) != EXPECTED_RESPONSIBILITIES:
            self.error("A06_ACTION_OWNERSHIP", "thin action responsibilities are incomplete or duplicated")

        authorities: dict[str, Doc] = {}
        for raw in items(self.mapping, "authority_sources", "mapping"):
            authority = to_doc(raw, "authority source")
            authorities[text(authority, "input_source", "authority source")] = authority
        for source in ("DIFY_USER_FIELD", "SELF_REPORTED_COMPANY_STORE_OR_ACCOUNT", "CONVERSATION_VARIABLE"):
            mapped_authority = authorities.get(source)
            if mapped_authority is None or mapped_authority.get("classification") != "UNTRUSTED_HINT":
                self.error("A05_AUTHORITY_MAPPING", f"{source} must remain an untrusted hint")
            elif mapped_authority.get("may_unlock_confirmed_prepare_placeholder") is not False:
                self.error("A05_AUTHORITY_UNLOCK", f"{source} cannot unlock preparation")
        server = authorities.get("SERVER_CONFIRMED_SCOPE")
        if server is None or server.get("classification") != "TRUSTED_REFERENCE":
            self.error("A05_SERVER_AUTHORITY", "server-confirmed scope mapping is missing")
        elif server.get("may_unlock_confirmed_prepare_placeholder") is not True:
            self.error("A05_SERVER_AUTHORITY", "server-confirmed scope must be the only trusted unlock reference")

        for key, value in doc(self.mapping, "non_ownership_assertions", "mapping").items():
            if to_bool(value, f"non-ownership {key}"):
                self.error("A06_OWNERSHIP_DRIFT", f"{key} must remain false")
        action_types: set[str] = set()
        for raw in items(self.mapping, "action_cards", "mapping"):
            card = to_doc(raw, "action card")
            action_types.add(text(card, "action_type", "action card"))
            if flag(card, "contains_publishable_candidate", "action card"):
                self.error("A08_FAKE_PUBLISHABLE", "action cards cannot contain publishable candidates")
        if action_types != {"COLLECT_FACT", "COLLECT_MATERIAL", "REQUEST_AUTHORIZATION", "DEGRADE", "BLOCK"}:
            self.error("A08_ACTION_CARDS", "action card set is incomplete")

    def load_candidate_sets(self) -> None:
        sets = doc(self.journeys, "candidate_sets", "journeys")
        if set(sets) != {"two_candidates", "three_candidates"}:
            self.error("A07_CANDIDATE_SETS", "exactly the two- and three-candidate fixtures are required")
        for set_name, raw_set in sets.items():
            candidate_set = to_doc(raw_set, f"candidate set {set_name}")
            candidates = items(candidate_set, "candidates", f"candidate set {set_name}")
            expected_count = 2 if set_name == "two_candidates" else 3
            if len(candidates) != expected_count:
                self.error("A07_CANDIDATE_COUNT", f"{set_name} must contain {expected_count} candidates")
            if candidate_set.get("machine_difference_score") is not None:
                self.error("A07_FALSE_SCORE", f"{set_name} cannot contain a machine difference score")
            if candidate_set.get("human_difference_review_required") is not True:
                self.error("A07_HUMAN_REVIEW", f"{set_name} must require human experience review")
            refs: list[str] = []
            for raw_candidate in candidates:
                candidate = to_doc(raw_candidate, f"candidate in {set_name}")
                refs.append(text(candidate, "candidate_ref", "candidate"))
                if not flag(candidate, "simulation_only", "candidate"):
                    self.error("A11_SIMULATION_LABEL", f"{set_name} candidate must be simulation-only")
                if flag(candidate, "publish_allowed", "candidate"):
                    self.error("A08_PUBLISHABLE_CANDIDATE", f"{set_name} candidate cannot be publishable")
            if len(refs) != len(set(refs)):
                self.error("A07_CANDIDATE_REFS", f"{set_name} candidate references must be unique")
            self.candidate_refs[set_name] = frozenset(refs)

    def load_cases(self) -> None:
        for raw_case in items(self.journeys, "journey_cases", "journeys"):
            case = to_doc(raw_case, "journey case")
            case_id = text(case, "case_id", "journey case")
            if case_id in self.cases:
                self.error("A11_DUPLICATE_CASE", f"duplicate case {case_id}")
            self.cases[case_id] = case
            text(case, "user_visible_case_label", case_id)
            doc(case, "simulated_inputs", case_id)
            doc(case, "expected", case_id)
        if set(self.cases) != EXPECTED_CASE_IDS:
            self.error("A11_CASE_COVERAGE", f"journey cases differ: {sorted(set(self.cases) ^ EXPECTED_CASE_IDS)}")

    def check_direct_cases(self) -> None:
        for case_id, section_name, key, expected_value in DIRECT_CASE_ASSERTIONS:
            inputs, expected = self.case(case_id)
            section = inputs if section_name == "input" else expected
            self.expect(case_id, section, key, expected_value, "A11_DIRECT_ASSERTION")

        vague_expected = self.case("ENTRY-VAGUE")[1]
        if not 1 <= to_int(vague_expected.get("question_count"), "ENTRY-VAGUE question count") <= 3:
            self.error("A03_QUESTION_COUNT", "ENTRY-VAGUE must ask one to three questions")
        untrusted_inputs = self.case("UNTRUSTED-IDENTITY-SOURCES-REJECTED")[0]
        claimed_sources = {
            to_str(value, "claimed authority source")
            for value in items(untrusted_inputs, "claimed_authority_sources", "untrusted identity case")
        }
        if claimed_sources != {
            "DIFY_USER_FIELD",
            "SELF_REPORTED_COMPANY_STORE_OR_ACCOUNT",
            "CONVERSATION_VARIABLE",
        }:
            self.error("A05_UNTRUSTED_CASE_COVERAGE", "all three untrusted identity sources must be covered")

        for case_id, set_name in (
            ("TWO-CANDIDATES-SELECT-REVISE-RETURN", "two_candidates"),
            ("THREE-CANDIDATES-SELECT-ACCEPT", "three_candidates"),
        ):
            inputs, _ = self.case(case_id)
            if text(inputs, "selected_candidate_ref", case_id) not in self.candidate_refs.get(set_name, frozenset()):
                self.error("A07_UNKNOWN_SELECTION", f"{case_id} must select a displayed candidate")
            if items(inputs, "optional_expression_asset_refs", case_id):
                self.error("A06_OPTIONAL_ASSETS", f"{case_id} must work without atomic components, relations, or paths")
        feedback = tuple(
            to_str(value, "minimal feedback field")
            for value in items(self.case("TWO-CANDIDATES-SELECT-REVISE-RETURN")[1], "minimal_feedback_fields")
        )
        if feedback != FEEDBACK_FIELDS:
            self.error("A10_FEEDBACK_FIELDS", "two-candidate case must retain only minimal feedback")

        expected_cards = {
            "MISSING-FACT": "COLLECT_FACT",
            "MISSING-MATERIAL": "COLLECT_MATERIAL",
            "MISSING-AUTHORIZATION": "REQUEST_AUTHORIZATION",
            "OUT-OF-SCOPE": "BLOCK",
            "DEGRADE-SAFELY": "DEGRADE",
            "BLOCK-UNSAFE-REQUEST": "BLOCK",
        }
        for case_id, action_card in expected_cards.items():
            _, expected = self.case(case_id)
            if (
                expected.get("action_card") != action_card
                or expected.get("action_card_contains_publishable_candidate") is not False
            ):
                self.error("A08_ACTION_CARD", f"{case_id} must return a non-publishable {action_card} card")

    def check_journeys(self) -> None:
        boundary = doc(self.journeys, "simulation_boundary", "journeys")
        for key in ("simulation_only", "intent_results_are_injected"):
            if not flag(boundary, key, "simulation boundary"):
                self.error("A11_SIMULATION_BOUNDARY", f"{key} must be true")
        for key in (
            "natural_language_understanding_claimed",
            "chat_quality_claimed",
            "content_quality_claimed",
            "dify_import_or_runtime_claimed",
            "publish_allowed",
        ):
            if flag(boundary, key, "simulation boundary"):
                self.error("A11_FALSE_RUNTIME_CLAIM", f"{key} must be false")
        if boundary.get("external_call_count") != 0:
            self.error("A12_EXTERNAL_CALL", "journey external call count must be zero")
        coverage = tuple(to_str(value, "acceptance id") for value in items(self.journeys, "acceptance_coverage"))
        if coverage != ACCEPTANCE_IDS:
            self.error("A11_ACCEPTANCE_COVERAGE", "coverage must list PKG4-A01-A12 and PKG4-S01-S08")
        common = doc(self.journeys, "common_expected_boundaries", "journeys")
        expected_common: Doc = {
            "plan_created": False,
            "brand_fact_written": False,
            "external_call_count": 0,
            "publish_allowed": False,
            "publishable_candidate_created": False,
        }
        if common != expected_common:
            self.error("A12_COMMON_BOUNDARIES", "all fixed journeys must share the five fail-closed boundaries")
        self.load_candidate_sets()
        self.load_cases()
        if set(self.cases) == EXPECTED_CASE_IDS:
            self.check_direct_cases()

    def check_visible_output(self) -> int:
        strings = [
            *visible_strings(self.flow),
            *visible_strings(self.mapping),
            *visible_strings(self.journeys),
        ]
        for value in strings:
            for pattern in VISIBLE_LEAK_PATTERNS:
                if pattern.search(value):
                    self.error("A09_USER_VISIBLE_LEAK", f"user-visible text matched {pattern.pattern!r}")
        return len(strings)

    def check_repository(self) -> None:
        if {path.name for path in self.root.iterdir() if path.is_file()} != CORE_PACKAGE_FILES:
            self.error("S06_CORE_FILE_SET", "r2 must reuse exactly the five existing core package files")
        if [path.name for path in sorted(self.root.glob("conversation_flow*.json"))] != [FLOW_FILE]:
            self.error("A01_FLOW_FILE_COUNT", "exactly one version-neutral flow candidate is allowed")
        if [path.name for path in sorted(self.root.glob("check_*.py"))] != ["check_dify_content_shell.py"]:
            self.error("A11_CHECKER_COUNT", "exactly one package checker is allowed")

        base_ref = "refs/remotes/origin/master"
        if git(self.repo, ("rev-parse", "--verify", base_ref)).returncode != 0:
            base_ref = BASELINE
        changed: set[str] = set()
        for arguments in (
            ("diff", "--name-only", f"{base_ref}...HEAD", "--"),
            ("diff", "--name-only", "--"),
            ("diff", "--cached", "--name-only", "--"),
            ("ls-files", "--others", "--exclude-standard"),
        ):
            result = git(self.repo, arguments)
            if result.returncode != 0:
                self.error("A12_GIT_SCOPE", result.stderr.strip() or "git scope check failed")
            changed.update(line for line in result.stdout.splitlines() if line)
        for changed_path in changed:
            if not changed_path.startswith(ALLOWED_ROOT):
                self.error("A12_WRITE_SCOPE", f"changed path is outside the exclusive root: {changed_path}")
        if git(self.repo, ("merge-base", "--is-ancestor", BASELINE, "HEAD")).returncode != 0:
            self.error("A12_BASELINE", "the exact r1 baseline must remain an ancestor of HEAD")
        for relative, expected_hash in PINNED_CORE_FILES.items():
            path = self.repo / relative
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                self.error("A12_CORE_NUMBER_GUARD", f"pinned 120/86 evidence changed: {relative}")
        for relative, expected_hash in PINNED_HISTORICAL_REVIEW_FILES.items():
            path = self.root / relative
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                self.error("S07_HISTORICAL_REVIEW_CHANGED", f"historical review evidence changed: {relative}")

    def run(self, *, check_repository: bool) -> Summary:
        self.check_lightweight_shape()
        self.check_candidate_and_experience()
        self.check_boundaries()
        self.check_mapping()
        self.check_journeys()
        visible_count = self.check_visible_output()
        if check_repository:
            self.check_repository()
        return Summary(tuple(self.errors), len(self.cases), visible_count)


def validate(
    flow: Doc,
    mapping: Doc,
    journeys: Doc,
    result: Doc,
    repo: Path,
    root: Path,
    *,
    check_repository: bool,
) -> Summary:
    try:
        return PackageChecker(flow, mapping, journeys, result, repo, root).run(check_repository=check_repository)
    except ValueError as exc:
        return Summary((f"A11_DATA_SHAPE: {exc}",), 0, 0)


def selftest(flow: Doc, mapping: Doc, journeys: Doc, result: Doc, repo: Path, root: Path) -> tuple[str, ...]:
    failures: list[str] = []

    def expect(
        name: str,
        changed_flow: Doc,
        changed_mapping: Doc,
        changed_journeys: Doc,
        changed_result: Doc,
        code: str,
    ) -> None:
        summary = validate(
            changed_flow,
            changed_mapping,
            changed_journeys,
            changed_result,
            repo,
            root,
            check_repository=False,
        )
        if not any(error.startswith(f"{code}:") for error in summary.errors):
            failures.append(f"SELFTEST_{name}: expected {code}")

    changed_flow = copy.deepcopy(flow)
    doc(changed_flow, "application", "flow")["routes"] = []
    expect("GENERIC_ROUTE_LANGUAGE", changed_flow, mapping, journeys, result, "S01_FORBIDDEN_RUNTIME_MODEL")
    changed_flow = copy.deepcopy(flow)
    constraints = doc(doc(changed_flow, "application", "flow"), "lightweight_constraints", "application")
    constraints["graph_traversal_implemented"] = True
    expect("GRAPH_RUNTIME", changed_flow, mapping, journeys, result, "S01_RUNTIME_ENGINE_PRESENT")
    changed_flow = copy.deepcopy(flow)
    identity = doc(doc(changed_flow, "application", "flow"), "identity_policy", "application")
    identity["hint_may_grant_identity_scope_or_permission"] = True
    expect("HINT_GRANT", changed_flow, mapping, journeys, result, "A05_HINT_GRANT")
    changed_flow = copy.deepcopy(flow)
    confirmation = doc(doc(changed_flow, "application", "flow"), "confirmation_policy", "application")
    confirmation["prepare_placeholder_requires_requirement_confirmation"] = "DRAFT"
    expect("CONFIRM_BOUNDARY", changed_flow, mapping, journeys, result, "A04_CONFIRMATION_BOUNDARY")
    changed_mapping = copy.deepcopy(mapping)
    changed_mapping["state_mappings"] = []
    expect("STATE_MAPPING", flow, changed_mapping, journeys, result, "S01_STATE_MAPPING")
    changed_mapping = copy.deepcopy(mapping)
    first_card = to_doc(items(changed_mapping, "action_cards", "mapping")[0], "action card")
    first_card["contains_publishable_candidate"] = True
    expect("ACTION_CARD_BODY", flow, changed_mapping, journeys, result, "A08_FAKE_PUBLISHABLE")
    changed_journeys = copy.deepcopy(journeys)
    two_set = doc(doc(changed_journeys, "candidate_sets", "journeys"), "two_candidates", "candidate sets")
    first_candidate = to_doc(items(two_set, "candidates", "two-candidate set")[0], "candidate")
    doc(first_candidate, "user_visible_surfaces", "candidate")["title"] = "CP02"
    expect("VISIBLE_LEAK", flow, mapping, changed_journeys, result, "A09_USER_VISIBLE_LEAK")
    changed_flow = copy.deepcopy(flow)
    bindings = doc(doc(changed_flow, "application", "flow"), "external_bindings", "application")
    bindings["author_model_connected"] = True
    expect("EXTERNAL_BINDING", changed_flow, mapping, journeys, result, "A12_EXTERNAL_BINDING")
    changed_journeys = copy.deepcopy(journeys)
    for raw_case in items(changed_journeys, "journey_cases", "journeys"):
        case = to_doc(raw_case, "journey case")
        if case.get("case_id") == "UNCONFIRMED-BLOCKS-PREPARE":
            doc(case, "expected", "unconfirmed case")["prepare_placeholder_requested"] = True
    expect("UNCONFIRMED_PREPARE", flow, mapping, changed_journeys, result, "A11_DIRECT_ASSERTION")
    changed_result = copy.deepcopy(result)
    changed_result["candidate_state"] = "PASS_DIFY_CONVERSATION_SHELL_PENDING_PACKAGE_7"
    expect("PREMATURE_SUCCESS", flow, mapping, journeys, changed_result, "S07_PREMATURE_SUCCESS")
    return tuple(failures)


def parse_arguments(arguments: Sequence[str]) -> bool:
    if not arguments:
        return False
    if list(arguments) == ["--selftest"]:
        return True
    raise ValueError("usage: check_dify_content_shell.py [--selftest]")


def main(arguments: Sequence[str]) -> int:
    if not __debug__:
        sys.stderr.write("REFUSED: optimized mode disables assertions; deterministic checker will not run.\n")
        return 2
    try:
        run_selftest = parse_arguments(arguments)
        root = Path(__file__).resolve().parent
        repo = root.parents[1]
        flow = load(root / FLOW_FILE)
        mapping = load(root / MAPPING_FILE)
        journeys = load(root / JOURNEYS_FILE)
        result = load(root / RESULT_FILE)
        summary = validate(flow, mapping, journeys, result, repo, root, check_repository=True)
        if summary.errors:
            sys.stderr.write("FAIL_DIFY_CONTENT_SHELL\n" + "\n".join(summary.errors) + "\n")
            return 1
        if run_selftest:
            failures = selftest(flow, mapping, journeys, result, repo, root)
            if failures:
                sys.stderr.write("FAIL_DIFY_CONTENT_SHELL_SELFTEST\n" + "\n".join(failures) + "\n")
                return 1
        mode = "SELFTEST" if run_selftest else "PACKAGE"
        sys.stdout.write(
            f"PASS_DIFY_CONTENT_SHELL_{mode} cases={summary.journey_cases} "
            f"visible_strings={summary.visible_strings} external_calls=0 readiness=false lightweight=true\n"
        )
        return 0
    except ValueError as exc:
        sys.stderr.write(f"FAIL_DIFY_CONTENT_SHELL_INPUT: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
