#!/usr/bin/env python3
"""Deterministic checker for the version-neutral Dify conversation shell."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence, cast


Doc = dict[str, object]
BASELINE: Final = "95b8b1700b7e96b1d2383465713bef8c36e7f6cb"
ALLOWED_ROOT: Final = "14_dify_shell/dify_content_shell_001/"
FLOW_FILE: Final = "conversation_flow.version_neutral.v1.json"
MAPPING_FILE: Final = "state_action_mapping.v1.json"
JOURNEYS_FILE: Final = "journeys.simulated.v1.json"
ACCEPTANCE_IDS: Final = tuple(f"PKG4-A{number:02d}" for number in range(1, 13))
SUMMARY_FIELDS: Final = (
    "为哪个内容账号",
    "讲什么",
    "给谁看",
    "发到哪里",
    "现有真实材料",
    "还缺什么",
    "采用什么大方向",
)
FEEDBACK_FIELDS: Final = ("selected_candidate_ref", "necessary_modification", "short_reason")
READINESS_FLAGS: Final = (
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "generator_qualified",
    "retrieval_ready",
    "runtime_ready",
    "release_ready",
    "production_ready",
)
EXPECTED_CASE_IDS: Final = {
    "CHAT-TWO-TURNS",
    "ENTRY-INSPIRATION",
    "ENTRY-VAGUE",
    "ENTRY-CLEAR",
    "UNCONFIRMED-BLOCKS-PREPARE",
    "EDIT-REQUIRES-RECONFIRM",
    "CANCEL-AFTER-CONFIRM",
    "SERVER-CONFIRMED-ACCOUNT",
    "SELF-REPORTED-ACCOUNT-REJECTED",
    "DIFY-USER-REJECTED",
    "TWO-CANDIDATES-SELECT-REVISE-RETURN",
    "THREE-CANDIDATES-SELECT-ACCEPT",
    "CHANGE-REQUIREMENT-RECONFIRM",
    "MISSING-FACT",
    "MISSING-MATERIAL",
    "MISSING-AUTHORIZATION",
    "OUT-OF-SCOPE",
    "DEGRADE-SAFELY",
    "BLOCK-UNSAFE-REQUEST",
}
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


class DataError(ValueError):
    """Raised when a package document has an unsafe or unexpected shape."""


@dataclass(frozen=True)
class Summary:
    """Stable package validation result."""

    errors: tuple[str, ...]
    journeys: int
    transitions: int
    visible_strings: int


@dataclass
class Runtime:
    """Only the three allowed session markers plus journey-local observations."""

    state: str
    markers: dict[str, str]
    selected_ref: str | None = None
    active_refs: frozenset[str] = frozenset()
    candidate_count: int = 0
    prepare_requested: bool = False
    author_requested: bool = False
    feedback_recorded: bool = False
    external_calls: int = 0


def to_doc(value: object, label: str) -> Doc:
    if not isinstance(value, dict):
        raise DataError(f"{label} must be an object")
    return cast(Doc, value)


def to_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise DataError(f"{label} must be a list")
    return cast(list[object], value)


def to_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise DataError(f"{label} must be a string")
    return value


def to_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise DataError(f"{label} must be a boolean")
    return value


def to_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError(f"{label} must be an integer")
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
        raise DataError(f"cannot load {path}: {exc}") from exc
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


def git(repo: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *arguments], cwd=repo, check=False, capture_output=True, text=True, encoding="utf-8")


class PackageChecker:
    """Package-specific checks; this is not a general workflow engine."""

    def __init__(self, flow: Doc, mapping: Doc, journeys: Doc, repo: Path, root: Path) -> None:
        self.flow = flow
        self.mapping = mapping
        self.journeys_doc = journeys
        self.repo = repo
        self.root = root
        self.app = doc(flow, "application", "flow")
        self.errors: list[str] = []
        self.routes: dict[tuple[str, str], Doc] = {}
        self.state_ids: set[str] = set()
        self.candidate_sets: dict[str, frozenset[str]] = {}
        self.journey_count = 0

    def error(self, code: str, message: str) -> None:
        self.errors.append(f"{code}: {message}")

    def check_candidate_ui(self) -> None:
        candidate = doc(self.flow, "candidate", "flow")
        expected_values: tuple[tuple[str, object, str], ...] = (
            ("kind", "VERSION_NEUTRAL_FLOW_CANDIDATE", "A01_CANDIDATE_KIND"),
            ("target_dify_version", "UNKNOWN_NOT_VERIFIED", "A12_DIFY_VERSION"),
            ("native_dify_export", False, "A12_NATIVE_EXPORT"),
            ("importable_claimed", False, "A12_IMPORTABLE_CLAIM"),
            ("application_count", 1, "A01_APPLICATION_COUNT"),
        )
        for key, expected, code in expected_values:
            if candidate.get(key) != expected:
                self.error(code, f"candidate {key} must be {expected!r}")

        intent = doc(self.app, "intent_resolution", "application")
        for key in (
            "natural_language_parser_implemented",
            "keyword_classifier_implemented",
            "regex_intent_engine_implemented",
        ):
            if flag(intent, key, "intent_resolution"):
                self.error("A03_FORBIDDEN_INTENT_ENGINE", f"{key} must remain false")
        if intent.get("local_journeys") != "EXPLICIT_SIMULATED_INTENT_RESULT_INJECTION":
            self.error("A03_SIMULATED_INTENT", "journeys must inject explicit simulated intent results")

        marker_names = set(doc(self.app, "minimal_session_markers", "application"))
        if marker_names != {"mode", "requirement_confirmation", "selected_candidate_ref"}:
            self.error("A10_SESSION_MARKERS", "only mode, confirmation, and selected reference may persist")
        experience = doc(self.app, "user_experience", "application")
        if not 2 <= len(items(experience, "user_visible_inspiration_directions", "user_experience")) <= 3:
            self.error("A03_DIRECTION_COUNT", "inspiration must offer two or three directions")
        clarification = doc(experience, "clarification_policy", "user_experience")
        minimum = to_int(clarification.get("questions_per_turn_minimum"), "question minimum")
        maximum = to_int(clarification.get("questions_per_turn_maximum"), "question maximum")
        if minimum < 1 or maximum > 3 or minimum > maximum:
            self.error("A03_QUESTION_COUNT", "clarification must ask one to three questions")
        if flag(clarification, "parameters_are_entry_requirement", "clarification"):
            self.error("A03_PARAMETER_GATE", "parameters cannot gate content creation")
        summary_fields = tuple(
            to_str(value, "summary field")
            for value in items(experience, "user_visible_requirement_summary_fields", "user_experience")
        )
        if summary_fields != SUMMARY_FIELDS:
            self.error("A03_SUMMARY_FIELDS", "plain-language summary fields are incomplete")
        if len(items(experience, "user_visible_topic_categories", "user_experience")) != 8:
            self.error("A09_TOPIC_COUNT", "the user surface must expose exactly eight topic categories")

        policy = doc(self.app, "candidate_policy", "application")
        if policy.get("minimum_count") != 2 or policy.get("maximum_count") != 3:
            self.error("A07_CANDIDATE_RANGE", "candidate range must be two to three")
        if flag(policy, "machine_claims_semantic_difference", "candidate_policy"):
            self.error("A07_FALSE_DIFFERENCE", "machine cannot claim semantic difference")
        if flag(policy, "near_synonym_rewording_accepted_as_difference", "candidate_policy"):
            self.error("A07_NEAR_SYNONYM", "near-synonym rewrites cannot count as difference")
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
        if flag(identity, "trusted_scope_model_copied", "identity_policy"):
            self.error("A06_MODEL_COPY", "trusted scope model cannot be copied")
        if flag(identity, "hint_may_grant_identity_scope_or_permission", "identity_policy"):
            self.error("A05_HINT_GRANT", "a hint cannot grant identity, scope, or permission")
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

    def build_routes(self) -> None:
        adjacency: dict[str, set[str]] = {}
        creation_states: set[str] = set()
        raw_states = items(self.app, "states", "application")
        for index, raw_state in enumerate(raw_states):
            state = to_doc(raw_state, f"states[{index}]")
            state_id = text(state, "id", "state")
            if state_id in self.state_ids:
                self.error("A11_DUPLICATE_STATE", f"duplicate state {state_id}")
            self.state_ids.add(state_id)
            adjacency[state_id] = set()
            if state.get("mode") == "CREATION":
                creation_states.add(state_id)
            if flag(state, "creates_plan", "state"):
                self.error("A06_PLAN_OWNERSHIP", f"state {state_id} cannot create a plan")
            if flag(state, "writes_brand_fact", "state"):
                self.error("A02_FACT_WRITE", f"state {state_id} cannot write brand facts")
        exit_states: set[str] = set()
        for index, raw_route in enumerate(items(self.app, "routes", "application")):
            route = to_doc(raw_route, f"routes[{index}]")
            source, event, target = (text(route, key, "route") for key in ("from", "event", "to"))
            key = (source, event)
            if key in self.routes:
                self.error("A11_AMBIGUOUS_ROUTE", f"duplicate route {source}/{event}")
            self.routes[key] = route
            if source not in adjacency or target not in adjacency:
                self.error("A11_UNKNOWN_STATE", f"route {source}/{event} references an unknown state")
            else:
                adjacency[source].add(target)
            if event == "EXIT_CREATION" and target == "chat":
                exit_states.add(source)
        missing_exits = creation_states - exit_states
        if missing_exits:
            self.error("A03_EXIT_ROUTE", f"states missing chat exit: {', '.join(sorted(missing_exits))}")
        entry = text(self.app, "entry_state", "application")
        reached: set[str] = set()
        queue: deque[str] = deque([entry])
        while queue:
            current = queue.popleft()
            if current not in reached:
                reached.add(current)
                queue.extend(adjacency.get(current, set()) - reached)
        if self.state_ids - reached:
            self.error("A11_UNREACHABLE_STATE", f"unreachable states: {sorted(self.state_ids - reached)}")

    def require_guard(self, source: str, event: str, required: dict[str, str], code: str) -> None:
        route = self.routes.get((source, event))
        if route is None:
            self.error(code, f"missing route {source}/{event}")
            return
        guards = doc(route, "requires", "route")
        if any(guards.get(key) != value for key, value in required.items()):
            self.error(code, f"route {source}/{event} is missing required guards")

    def check_route_guards(self) -> None:
        self.require_guard(
            "awaiting_confirmation",
            "CONFIRM_REQUIREMENT",
            {"requirement_confirmation": "DRAFT", "scope_authority": "SERVER_CONFIRMED"},
            "A04_CONFIRM_GUARD",
        )
        confirm = self.routes.get(("awaiting_confirmation", "CONFIRM_REQUIREMENT"))
        if confirm is not None:
            markers = doc(doc(confirm, "effects", "confirm route"), "set_markers", "confirm effects")
            if markers.get("requirement_confirmation") != "CONFIRMED":
                self.error("A04_CONFIRM_EFFECT", "confirmation must set the confirmed marker")
        self.require_guard(
            "prepare_placeholder",
            "PREPARE_READY",
            {"requirement_confirmation": "CONFIRMED", "scope_authority": "SERVER_CONFIRMED"},
            "A04_PREPARE_GUARD",
        )
        self.require_guard(
            "candidate_selected",
            "REVISE_SELECTED",
            {"requirement_confirmation": "CONFIRMED", "selected_candidate_ref": "BOUND"},
            "A07_REVISION_BINDING",
        )
        for source in ("candidate_display", "candidate_selected", "result_status"):
            route = self.routes.get((source, "CHANGE_REQUIREMENT"))
            if route is None:
                self.error("A04_RECONFIRM_ROUTE", f"{source} cannot return to requirement editing")
                continue
            markers = doc(doc(route, "effects", "change route"), "set_markers", "change effects")
            if markers.get("requirement_confirmation") != "DRAFT":
                self.error("A04_RECONFIRM_RESET", f"{source} does not reset confirmation")
            if markers.get("selected_candidate_ref") != "UNBOUND":
                self.error("A07_SELECTION_RESET", f"{source} does not clear candidate selection")

    def check_mapping(self) -> None:
        if self.mapping.get("mapping_kind") != "THIN_REFERENCE_ONLY" or flag(
            self.mapping, "copies_public_models", "mapping"
        ):
            self.error("A06_MODEL_COPY", "mapping must be a thin reference without copied public models")
        mapped: list[str] = []
        for index, raw in enumerate(items(self.mapping, "state_mappings", "mapping")):
            mapping = to_doc(raw, f"state_mappings[{index}]")
            mapped.extend(to_str(value, "mapped state") for value in items(mapping, "states", "mapping"))
            for key, code in (
                ("creates_light_content_plan", "A06_PLAN_OWNERSHIP"),
                ("writes_brand_fact", "A02_FACT_WRITE"),
                ("external_call_implemented", "A12_EXTERNAL_CALL"),
            ):
                if flag(mapping, key, "state mapping"):
                    self.error(code, f"state mapping {key} must remain false")
        if len(mapped) != len(set(mapped)) or set(mapped) != self.state_ids:
            self.error("A06_STATE_MAPPING", "each state needs exactly one thin ownership mapping")
        authorities: dict[str, Doc] = {}
        for raw in items(self.mapping, "authority_sources", "mapping"):
            authority = to_doc(raw, "authority source")
            authorities[text(authority, "input_source", "authority source")] = authority
        for source in ("DIFY_USER_FIELD", "SELF_REPORTED_COMPANY_STORE_OR_ACCOUNT", "CONVERSATION_VARIABLE"):
            mapped_authority = authorities.get(source)
            if mapped_authority is None or mapped_authority.get("classification") != "UNTRUSTED_HINT":
                self.error("A05_AUTHORITY_MAPPING", f"{source} must remain an untrusted hint")
            elif mapped_authority.get("may_unlock_confirmed_prepare_placeholder") is not False:
                self.error("A05_AUTHORITY_UNLOCK", f"{source} cannot unlock prepare")
        server = authorities.get("SERVER_CONFIRMED_SCOPE")
        if server is None or server.get("classification") != "TRUSTED_REFERENCE":
            self.error("A05_SERVER_AUTHORITY", "server-confirmed scope mapping is missing")
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
        for name, raw in doc(self.journeys_doc, "candidate_sets", "journeys").items():
            candidate_set = to_doc(raw, f"candidate set {name}")
            candidates = items(candidate_set, "candidates", f"candidate set {name}")
            if not 2 <= len(candidates) <= 3:
                self.error("A07_CANDIDATE_COUNT", f"{name} must contain two or three candidates")
            if candidate_set.get("machine_difference_score") is not None:
                self.error("A07_FALSE_SCORE", f"{name} cannot contain a machine difference score")
            if candidate_set.get("human_difference_review_required") is not True:
                self.error("A07_HUMAN_REVIEW", f"{name} must require human experience review")
            refs: list[str] = []
            for raw_candidate in candidates:
                candidate = to_doc(raw_candidate, f"candidate in {name}")
                refs.append(text(candidate, "candidate_ref", "candidate"))
                if not flag(candidate, "simulation_only", "candidate"):
                    self.error("A11_SIMULATION_LABEL", f"{name} candidate must be simulation-only")
                if flag(candidate, "publish_allowed", "candidate"):
                    self.error("A08_PUBLISHABLE_CANDIDATE", f"{name} candidate cannot be publishable")
            if len(refs) != len(set(refs)):
                self.error("A07_CANDIDATE_REFS", f"{name} candidate references must be unique")
            self.candidate_sets[name] = frozenset(refs)

    @staticmethod
    def guards_pass(route: Doc, markers: dict[str, str]) -> bool:
        return all(markers.get(key) == to_str(value, f"guard {key}") for key, value in doc(route, "requires").items())

    @staticmethod
    def apply_route(runtime: Runtime, route: Doc) -> None:
        effects = doc(route, "effects", "route")
        raw_markers = effects.get("set_markers")
        if raw_markers is not None:
            for key, value in to_doc(raw_markers, "set_markers").items():
                runtime.markers[key] = to_str(value, f"marker {key}")
            if runtime.markers.get("selected_candidate_ref") == "UNBOUND":
                runtime.selected_ref = None
        runtime.prepare_requested |= effects.get("prepare_placeholder_requested") is True
        runtime.author_requested |= effects.get("author_placeholder_requested") is True
        runtime.feedback_recorded |= effects.get("minimal_feedback_recorded") is True
        runtime.external_calls += int(effects.get("external_call_made") is True)
        runtime.state = text(route, "to", "route")

    def check_step(self, case_id: str, step: Doc, runtime: Runtime, route: Doc) -> None:
        event = text(step, "simulated_intent_result", case_id)
        if "expected_direction_count" in step:
            count = to_int(step.get("expected_direction_count"), f"{case_id} direction count")
            if not 2 <= count <= 3:
                self.error("A03_DIRECTION_COUNT", f"{case_id} must show two or three directions")
        if "expected_question_count" in step:
            count = to_int(step.get("expected_question_count"), f"{case_id} question count")
            if not 1 <= count <= 3:
                self.error("A03_QUESTION_COUNT", f"{case_id} must ask one to three questions")
        if event == "AUTHORING_SIMULATED":
            set_name = text(step, "candidate_set_ref", case_id)
            refs = self.candidate_sets.get(set_name)
            if refs is None:
                self.error("A07_UNKNOWN_CANDIDATE_SET", f"{case_id} references unknown set {set_name}")
            else:
                runtime.active_refs = refs
                runtime.candidate_count = len(refs)
                if step.get("expected_candidate_count") != len(refs):
                    self.error("A07_CANDIDATE_COUNT", f"{case_id} candidate count mismatch")
        if event == "SELECT_CANDIDATE":
            selected = text(step, "selected_candidate_ref", case_id)
            if selected not in runtime.active_refs:
                self.error("A07_UNKNOWN_SELECTION", f"{case_id} selected an undisplayed candidate")
            runtime.selected_ref = selected
        if event in {"REVISE_SELECTED", "REVISION_SIMULATED", "ACCEPT_SELECTED"}:
            if text(step, "bound_candidate_ref", case_id) != runtime.selected_ref:
                self.error("A07_REVISION_BINDING", f"{case_id} did not bind the selected candidate")
        if event == "REVISE_SELECTED":
            if (
                not text(step, "necessary_modification", case_id).strip()
                or not text(step, "short_reason", case_id).strip()
            ):
                self.error("A10_FEEDBACK_VALUE", f"{case_id} feedback values cannot be empty")
        if "expected_action_card" in step:
            expected = text(step, "expected_action_card", case_id)
            if doc(route, "effects", "route").get("action_card") != expected:
                self.error("A08_ACTION_CARD_ROUTE", f"{case_id} action card mismatch")

    def check_expected(self, case_id: str, expected: Doc, runtime: Runtime) -> None:
        actual: Doc = {
            "plan_created": False,
            "prepare_placeholder_requested": runtime.prepare_requested,
            "author_placeholder_requested": runtime.author_requested,
            "brand_fact_written": False,
            "external_call_count": runtime.external_calls,
            "candidate_count": runtime.candidate_count,
            "publish_allowed": False,
            "publishable_candidate_created": False,
            "requirement_confirmation": runtime.markers.get("requirement_confirmation"),
            "selected_candidate_ref": runtime.markers.get("selected_candidate_ref"),
            "minimal_feedback_fields": list(FEEDBACK_FIELDS) if runtime.feedback_recorded else [],
        }
        for key, value in expected.items():
            if key not in actual:
                self.error("A11_UNKNOWN_EXPECTATION", f"{case_id} uses unsupported expectation {key}")
            elif actual[key] != value:
                self.error("A11_JOURNEY_EFFECT", f"{case_id} expected {key}={value!r}, got {actual[key]!r}")

    def check_journeys(self) -> None:
        boundary = doc(self.journeys_doc, "simulation_boundary", "journeys")
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
        coverage = tuple(
            to_str(value, "acceptance id") for value in items(self.journeys_doc, "acceptance_coverage", "journeys")
        )
        if coverage != ACCEPTANCE_IDS:
            self.error("A11_ACCEPTANCE_COVERAGE", "coverage must list PKG4-A01 through PKG4-A12")
        self.load_candidate_sets()
        initial = {
            key: to_str(value, f"initial marker {key}")
            for key, value in doc(self.app, "initial_markers", "application").items()
        }
        entry = text(self.app, "entry_state", "application")
        case_ids: set[str] = set()
        no_optional_assets = False
        for raw_group in items(self.journeys_doc, "journey_groups", "journeys"):
            group = to_doc(raw_group, "journey group")
            common_markers = {
                key: to_str(value, f"group marker {key}")
                for key, value in doc(group, "common_initial_markers", "journey group").items()
            }
            common_steps = [to_doc(value, "common step") for value in items(group, "common_steps", "group")]
            for raw_variant in items(group, "variants", "group"):
                variant = to_doc(raw_variant, "journey variant")
                case_id = text(variant, "case_id", "variant")
                if case_id in case_ids:
                    self.error("A11_DUPLICATE_CASE", f"duplicate case {case_id}")
                case_ids.add(case_id)
                self.journey_count += 1
                markers = {**initial, **common_markers}
                if variant.get("initial_marker_overrides") is not None:
                    markers.update(
                        {
                            key: to_str(value, f"override {key}")
                            for key, value in to_doc(
                                variant.get("initial_marker_overrides"), "marker overrides"
                            ).items()
                        }
                    )
                runtime = Runtime(state=entry, markers=markers)
                variant_steps = [to_doc(value, "variant step") for value in items(variant, "steps", case_id)]
                for step in [*common_steps, *variant_steps]:
                    event = text(step, "simulated_intent_result", case_id)
                    expected_state = text(step, "expected_state", case_id)
                    route = self.routes.get((runtime.state, event))
                    usable = route is not None and self.guards_pass(route, runtime.markers)
                    if step.get("expect_rejected") is True:
                        if usable:
                            self.error("A04_EXPECTED_REJECTION", f"{case_id} unexpectedly allowed {event}")
                        if runtime.state != expected_state:
                            self.error("A11_REJECTED_STATE", f"{case_id} rejected event changed state")
                        continue
                    if route is None:
                        self.error("A11_MISSING_ROUTE", f"{case_id} lacks {runtime.state}/{event}")
                        continue
                    if not usable:
                        self.error("A11_GUARD_FAILURE", f"{case_id} failed guard for {runtime.state}/{event}")
                        continue
                    self.check_step(case_id, step, runtime, route)
                    self.apply_route(runtime, route)
                    if runtime.state != expected_state:
                        self.error("A11_STATE_MISMATCH", f"{case_id} expected {expected_state}, got {runtime.state}")
                self.check_expected(case_id, doc(variant, "expected_effects", case_id), runtime)
                if variant.get("optional_expression_asset_refs") == [] and runtime.candidate_count in {2, 3}:
                    no_optional_assets = True
        if case_ids != EXPECTED_CASE_IDS:
            self.error("A11_CASE_COVERAGE", f"journey cases differ: {sorted(case_ids ^ EXPECTED_CASE_IDS)}")
        if not no_optional_assets:
            self.error("A06_OPTIONAL_ASSETS", "a successful candidate journey must omit optional expression assets")

    def check_visible_output(self) -> int:
        strings = [
            *visible_strings(self.flow),
            *visible_strings(self.mapping),
            *visible_strings(self.journeys_doc),
        ]
        for value in strings:
            for pattern in VISIBLE_LEAK_PATTERNS:
                if pattern.search(value):
                    self.error("A09_USER_VISIBLE_LEAK", f"user-visible text matched {pattern.pattern!r}")
        return len(strings)

    def check_repository(self) -> None:
        if [path.name for path in sorted(self.root.glob("conversation_flow*.json"))] != [FLOW_FILE]:
            self.error("A01_FLOW_FILE_COUNT", "exactly one version-neutral flow candidate is allowed")
        if [path.name for path in sorted(self.root.glob("check_*.py"))] != ["check_dify_content_shell.py"]:
            self.error("A11_CHECKER_COUNT", "exactly one package checker is allowed")
        changed: set[str] = set()
        for arguments in (
            ("diff", "--name-only", BASELINE, "--"),
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
            self.error("A12_BASELINE", "exact baseline is not an ancestor of HEAD")
        for relative, expected in PINNED_CORE_FILES.items():
            core_path = self.repo / relative
            if not core_path.is_file() or hashlib.sha256(core_path.read_bytes()).hexdigest() != expected:
                self.error("A12_CORE_NUMBER_GUARD", f"pinned 120/86 evidence changed: {relative}")

    def run(self, *, check_repository: bool) -> Summary:
        self.check_candidate_ui()
        self.check_boundaries()
        self.build_routes()
        self.check_route_guards()
        self.check_mapping()
        self.check_journeys()
        visible_count = self.check_visible_output()
        if check_repository:
            self.check_repository()
        return Summary(tuple(self.errors), self.journey_count, len(self.routes), visible_count)


def validate(flow: Doc, mapping: Doc, journeys: Doc, repo: Path, root: Path, *, check_repository: bool) -> Summary:
    try:
        return PackageChecker(flow, mapping, journeys, repo, root).run(check_repository=check_repository)
    except DataError as exc:
        return Summary((f"A11_DATA_SHAPE: {exc}",), 0, 0, 0)


def route(flow: Doc, source: str, event: str) -> Doc:
    app = doc(flow, "application", "flow")
    for raw in items(app, "routes", "application"):
        candidate = to_doc(raw, "route")
        if candidate.get("from") == source and candidate.get("event") == event:
            return candidate
    raise DataError(f"route {source}/{event} not found")


def selftest(flow: Doc, mapping: Doc, journeys: Doc, repo: Path, root: Path) -> tuple[str, ...]:
    failures: list[str] = []

    def expect(name: str, changed_flow: Doc, changed_mapping: Doc, changed_journeys: Doc, code: str) -> None:
        summary = validate(changed_flow, changed_mapping, changed_journeys, repo, root, check_repository=False)
        if not any(error.startswith(f"{code}:") for error in summary.errors):
            failures.append(f"SELFTEST_{name}: expected {code}")

    changed = copy.deepcopy(flow)
    doc(changed, "candidate", "flow")["application_count"] = 2
    expect("SECOND_APP", changed, mapping, journeys, "A01_APPLICATION_COUNT")
    changed = copy.deepcopy(flow)
    identity = doc(doc(changed, "application", "flow"), "identity_policy", "application")
    identity["hint_may_grant_identity_scope_or_permission"] = True
    expect("HINT_GRANT", changed, mapping, journeys, "A05_HINT_GRANT")
    changed = copy.deepcopy(flow)
    doc(route(changed, "prepare_placeholder", "PREPARE_READY"), "requires", "route").pop(
        "requirement_confirmation", None
    )
    expect("CONFIRM_GUARD", changed, mapping, journeys, "A04_PREPARE_GUARD")
    changed_mapping = copy.deepcopy(mapping)
    changed_mapping["copies_public_models"] = True
    expect("MODEL_COPY", flow, changed_mapping, journeys, "A06_MODEL_COPY")
    changed_mapping = copy.deepcopy(mapping)
    first_card = to_doc(items(changed_mapping, "action_cards", "mapping")[0], "action card")
    first_card["contains_publishable_candidate"] = True
    expect("ACTION_CARD_BODY", flow, changed_mapping, journeys, "A08_FAKE_PUBLISHABLE")
    changed_journeys = copy.deepcopy(journeys)
    candidates = items(doc(doc(changed_journeys, "candidate_sets", "journeys"), "two_candidates"), "candidates")
    candidates.extend(copy.deepcopy(candidates[:2]))
    expect("FOUR_CANDIDATES", flow, mapping, changed_journeys, "A07_CANDIDATE_COUNT")
    changed_journeys = copy.deepcopy(journeys)
    candidates = items(doc(doc(changed_journeys, "candidate_sets", "journeys"), "two_candidates"), "candidates")
    surfaces = doc(to_doc(candidates[0], "candidate"), "user_visible_surfaces", "candidate")
    surfaces["title"] = "CP02"
    expect("VISIBLE_LEAK", flow, mapping, changed_journeys, "A09_USER_VISIBLE_LEAK")
    changed = copy.deepcopy(flow)
    bindings = doc(doc(changed, "application", "flow"), "external_bindings", "application")
    bindings["model_connected"] = True
    expect("EXTERNAL_BINDING", changed, mapping, journeys, "A12_EXTERNAL_BINDING")
    changed = copy.deepcopy(flow)
    feedback = doc(doc(changed, "application", "flow"), "feedback_policy", "application")
    items(feedback, "stored_fields", "feedback").append("long_term_profile")
    expect("HEAVY_FEEDBACK", changed, mapping, journeys, "A10_FEEDBACK_FIELDS")
    changed = copy.deepcopy(flow)
    intent = doc(doc(changed, "application", "flow"), "intent_resolution", "application")
    intent["keyword_classifier_implemented"] = True
    expect("INTENT_ENGINE", changed, mapping, journeys, "A03_FORBIDDEN_INTENT_ENGINE")
    return tuple(failures)


def parse_arguments(arguments: Sequence[str]) -> bool:
    if not arguments:
        return False
    if list(arguments) == ["--selftest"]:
        return True
    raise DataError("usage: check_dify_content_shell.py [--selftest]")


def main(arguments: Sequence[str]) -> int:
    if not __debug__:
        sys.stderr.write("REFUSED: optimized mode disables assertions; deterministic checker will not run.\n")
        return 2
    try:
        run_selftest = parse_arguments(arguments)
        root = Path(__file__).resolve().parent
        repo = root.parents[1]
        flow, mapping, journeys = (load(root / name) for name in (FLOW_FILE, MAPPING_FILE, JOURNEYS_FILE))
        summary = validate(flow, mapping, journeys, repo, root, check_repository=True)
        if summary.errors:
            sys.stderr.write("FAIL_DIFY_CONTENT_SHELL\n" + "\n".join(summary.errors) + "\n")
            return 1
        if run_selftest:
            failures = selftest(flow, mapping, journeys, repo, root)
            if failures:
                sys.stderr.write("FAIL_DIFY_CONTENT_SHELL_SELFTEST\n" + "\n".join(failures) + "\n")
                return 1
        mode = "SELFTEST" if run_selftest else "PACKAGE"
        sys.stdout.write(
            f"PASS_DIFY_CONTENT_SHELL_{mode} journeys={summary.journeys} transitions={summary.transitions} "
            f"visible_strings={summary.visible_strings} external_calls=0 readiness=false\n"
        )
        return 0
    except DataError as exc:
        sys.stderr.write(f"FAIL_DIFY_CONTENT_SHELL_INPUT: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
