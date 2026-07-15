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

import yaml  # type: ignore[import-untyped]


Doc = dict[str, object]
BASELINE: Final = "95b8b1700b7e96b1d2383465713bef8c36e7f6cb"
ALLOWED_ROOT: Final = "14_dify_shell/dify_content_shell_001/"
PUBLIC_TOPIC_PATH: Final = "11_product_foundation/public_foundation_001/taxonomy/topic_product_mapping.v1.yaml"
PUBLIC_CONTRACT_PATH: Final = (
    "11_product_foundation/public_foundation_001/contract/public_foundation_contract.v1.yaml"
)
FLOW_FILE: Final = "conversation_flow.version_neutral.v1.json"
MAPPING_FILE: Final = "state_action_mapping.v1.json"
JOURNEYS_FILE: Final = "journeys.simulated.v1.json"
RESULT_FILE: Final = "result_and_review_request.v1.json"
CORE_PACKAGE_FILES: Final = {FLOW_FILE, MAPPING_FILE, JOURNEYS_FILE, RESULT_FILE, "check_dify_content_shell.py"}
FROZEN_CANDIDATE_STATE: Final = "READY_FOR_TARGETED_INDEPENDENT_REREVIEWS"
SUCCESS_STATE: Final = "PASS_DIFY_CONVERSATION_SHELL_R4_PENDING_PACKAGE_7"
FIXED_IMPLEMENTATION_STAGE: Final = "R4_CONTRACT_ALIGNMENT_CANDIDATE_REVIEW_STATUS_RECORDED_IN_RESULT"
REVIEWED_IMPLEMENTATION_FILES: Final = (FLOW_FILE, MAPPING_FILE, JOURNEYS_FILE, "check_dify_content_shell.py")
TARGETED_REVIEWS: Final = {
    "USER_SEMANTICS_AND_NOVICE_EXPERIENCE_TARGETED_R4_REVIEW": (
        "reviews/novice_experience/targeted-rereview-r4.json",
        "R4_CLOTHING_TOPICS_ACTION_CARD_LANGUAGE_AND_NECESSARY_REGRESSION_ONLY",
    ),
    "PUBLIC_CONTRACT_AND_LIGHTWEIGHT_ARCHITECTURE_TARGETED_R4_REVIEW": (
        "reviews/architecture_trust/targeted-rereview-r4.json",
        "R4_PUBLIC_SOURCE_CONSUMPTION_EIGHT_ACTIONS_TRUST_AND_LIGHTWEIGHT_REGRESSION_ONLY",
    ),
}
ACCEPTANCE_IDS: Final = tuple(f"PKG4-A{number:02d}" for number in range(1, 13)) + tuple(
    f"PKG4-S{number:02d}" for number in range(1, 9)
) + tuple(f"PKG4-R4-A{number:02d}" for number in range(1, 13))
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
    "MISSING-AUTHORIZATION NEEDS-INTERVIEW NEEDS-RESHOOT NEEDS-ANONYMIZATION OUT-OF-SCOPE "
    "DEGRADE-SAFELY BLOCK-UNSAFE-REQUEST".split()
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
    ("NEEDS-INTERVIEW", "expected", "action_card", "INTERVIEW"),
    ("NEEDS-RESHOOT", "expected", "action_card", "RESHOOT"),
    ("NEEDS-ANONYMIZATION", "expected", "action_card", "ANONYMIZE"),
)
FORBIDDEN_ENGINE_KEYS: Final = frozenset("states routes transitions from event to requires effects guards".split())
VISIBLE_LEAK_PATTERNS: Final = (
    re.compile(r"\bCP[0-9]{2}\b"),
    re.compile(r"\bTOPIC-[0-9]{2}\b"),
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
    "reviews/novice_experience/targeted-rereview-r3.json": (
        "003a3490c82da689159ac45b12a1713dbb53ac58630a9d2b218c9c403bcb77b8"
    ),
    "reviews/architecture_trust/targeted-rereview-r3.json": (
        "92c9a28f1d004850d22a907e21ff7b861c788847f317947f54ee23d111aae85c"
    ),
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


def load_yaml(path: Path) -> Doc:
    try:
        value: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load {path}: {exc}") from exc
    return to_doc(value, str(path))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def implementation_hashes(root: Path) -> dict[str, str]:
    return {name: sha256_file(root / name) for name in REVIEWED_IMPLEMENTATION_FILES}


def implementation_digest(hashes: dict[str, str]) -> str:
    return hashlib.sha256(canonical_json(hashes).encode("utf-8")).hexdigest()


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


def external_paths_when_package_changes(changed_paths: set[str]) -> tuple[str, ...]:
    if not any(path.startswith(ALLOWED_ROOT) for path in changed_paths):
        return ()
    return tuple(sorted(path for path in changed_paths if not path.startswith(ALLOWED_ROOT)))


class PackageChecker:
    def __init__(self, flow: Doc, mapping: Doc, journeys: Doc, result: Doc, repo: Path, root: Path) -> None:
        self.flow = flow
        self.mapping = mapping
        self.journeys = journeys
        self.result = result
        self.repo = repo
        self.root = root
        self.app = doc(flow, "application", "flow")
        self.public_topics = doc(load_yaml(repo / PUBLIC_TOPIC_PATH), "topic_product_mapping", "public topic source")
        self.public_contract = doc(
            load_yaml(repo / PUBLIC_CONTRACT_PATH), "public_foundation_contract", "public contract source"
        )
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

    def check_public_topic_alignment(self, experience: Doc) -> None:
        public_pairs: list[tuple[str, str]] = []
        for raw_category in items(self.public_topics, "categories", "public topic source"):
            category = to_doc(raw_category, "public topic category")
            public_pairs.append(
                (
                    text(category, "topic_category_id", "public topic category"),
                    text(category, "display_name", "public topic category"),
                )
            )
        if len(public_pairs) != 8 or len(public_pairs) != len(set(public_pairs)):
            self.error("R4_A02_PUBLIC_TOPIC_SOURCE", "public topic source must contain eight unique id/name pairs")

        if experience.get("public_topic_source_ref") != PUBLIC_TOPIC_PATH:
            self.error("R4_A03_TOPIC_SOURCE_REF", "flow must reference the public topic source directly")
        declared_pairs: list[tuple[str, str]] = []
        for raw_mapping in items(experience, "topic_category_display_mapping", "user experience"):
            mapping = to_doc(raw_mapping, "topic display mapping")
            if set(mapping) != {"topic_category_id", "display_name"}:
                self.error("R4_A08_TOPIC_MAPPING_SHAPE", "topic mapping may contain only public id and display name")
            declared_pairs.append(
                (
                    text(mapping, "topic_category_id", "topic display mapping"),
                    text(mapping, "display_name", "topic display mapping"),
                )
            )
        if len(declared_pairs) != len(set(declared_pairs)) or tuple(declared_pairs) != tuple(public_pairs):
            self.error(
                "R4_A02_TOPIC_ALIGNMENT",
                "topic ids, names, order, presence, and uniqueness must match the public source",
            )

        visible_topics = tuple(
            to_str(value, "user-visible topic")
            for value in items(experience, "user_visible_topic_categories", "user experience")
        )
        public_names = tuple(display_name for _topic_id, display_name in public_pairs)
        if visible_topics != public_names or len(visible_topics) != len(set(visible_topics)):
            self.error("R4_A02_VISIBLE_TOPICS", "users must see only the ordered public display names")

        visibility = doc(experience, "public_topic_visibility", "user experience")
        if visibility.get("display_name_only") is not True:
            self.error("R4_A09_TOPIC_VISIBILITY", "topic user surface must be display-name-only")
        for key in (
            "internal_content_product_id_visible",
            "component_id_visible",
            "relationship_or_path_visible",
            "raw_error_code_visible",
        ):
            if flag(visibility, key, "public topic visibility"):
                self.error("R4_A09_TOPIC_VISIBILITY", f"{key} must remain false")
        if re.search(r"\bCP[0-9]{2}\b", canonical_json(self.flow)):
            self.error("R4_A08_INTERNAL_PRODUCT_COPY", "flow must not copy internal content product ids")

    def check_candidate_and_experience(self) -> None:
        candidate = doc(self.flow, "candidate", "flow")
        expected_values: tuple[tuple[str, object, str], ...] = (
            ("kind", "VERSION_NEUTRAL_FLOW_CANDIDATE", "A01_CANDIDATE_KIND"),
            ("target_dify_version", "UNKNOWN_NOT_VERIFIED", "A12_DIFY_VERSION"),
            ("native_dify_export", False, "A12_NATIVE_EXPORT"),
            ("importable_claimed", False, "A12_IMPORTABLE_CLAIM"),
            ("application_count", 1, "A01_APPLICATION_COUNT"),
            ("current_stage", FIXED_IMPLEMENTATION_STAGE, "S07_CANDIDATE_STAGE"),
        )
        for key, expected, code in expected_values:
            if candidate.get(key) != expected:
                self.error(code, f"candidate {key} must be {expected!r}")

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
        self.check_public_topic_alignment(experience)

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

    def check_review_lifecycle(self) -> None:
        state = self.result.get("candidate_state")
        if state not in {FROZEN_CANDIDATE_STATE, SUCCESS_STATE}:
            self.error("S07_CANDIDATE_STATE", "candidate must be frozen for rereview or backed by completed rereviews")
            return
        targeted = doc(self.result, "targeted_rereviews", "result")
        review_refs = items(targeted, "reviews", "targeted rereviews")
        if state == FROZEN_CANDIDATE_STATE:
            valid_pending = (
                targeted.get("state") == "PENDING_TARGETED_INDEPENDENT_REREVIEWS"
                and not review_refs
                and self.result.get("frozen_candidate") is None
            )
            if not valid_pending:
                self.error("S07_PREMATURE_SUCCESS", "frozen candidate must not claim completed targeted rereviews")
            return
        if targeted.get("state") != "COMPLETED_TARGETED_INDEPENDENT_REREVIEWS":
            self.error("S07_REVIEW_STATE", "successful result requires completed targeted rereviews")
            return
        frozen = doc(self.result, "frozen_candidate", "result")
        commit = text(frozen, "commit", "frozen candidate")
        hashes = implementation_hashes(self.root)
        digest = implementation_digest(hashes)
        frozen_binding = {
            "reviewed_file_sha256": hashes,
            "unified_sha256": digest,
        }
        if re.fullmatch(r"[0-9a-f]{40}", commit) is None or any(
            frozen.get(key) != value for key, value in frozen_binding.items()
        ):
            self.error("S07_FROZEN_BINDING", "frozen commit and four-file digests must match the implementation")
        commit_checks = (
            git(self.repo, ("cat-file", "-e", f"{commit}^{{commit}}")),
            git(self.repo, ("merge-base", "--is-ancestor", commit, "HEAD")),
        )
        if any(check.returncode != 0 for check in commit_checks):
            self.error("S07_FROZEN_COMMIT", "frozen candidate must exist and be an ancestor of HEAD")
        touched = git(self.repo, ("log", "--format=", "--name-only", f"{commit}..HEAD", "--"))
        protected = {f"{ALLOWED_ROOT}{name}" for name in REVIEWED_IMPLEMENTATION_FILES}
        if touched.returncode != 0 or set(touched.stdout.splitlines()) & protected:
            self.error("S07_FROZEN_IMPLEMENTATION_CHANGED", "reviewed implementation changed after freezing")

        refs = {
            text(ref, "review_role"): ref
            for ref in (to_doc(raw_ref, "targeted review reference") for raw_ref in review_refs)
        }
        if len(review_refs) != 2 or set(refs) != set(TARGETED_REVIEWS):
            self.error("S07_REVIEW_ROLES", "exactly the two targeted rereviews are required")
            return
        identities: dict[str, set[str]] = {
            key: set() for key in ("reviewer_identity", "reviewer_session", "review_run_id")
        }
        for role, (relative, scope) in TARGETED_REVIEWS.items():
            ref = refs[role]
            review_path = self.root / relative
            if ref.get("path") != relative or not review_path.is_file():
                self.error("S07_REVIEW_PATH", f"targeted review is missing or misplaced: {relative}")
                continue
            if ref.get("sha256") != sha256_file(review_path):
                self.error("S07_REVIEW_FILE_HASH", f"targeted review digest differs: {relative}")
            evidence = load(review_path)
            binding = {
                "schema_version": "r4-targeted-review-v1",
                "review_role": role,
                "review_scope": scope,
                "reviewed_candidate_commit": commit,
                "reviewed_snapshot_digest": digest,
                "reviewed_file_sha256": hashes,
                "verdict": "PASS",
                "blocking_findings": [],
                "repo_changed": False,
            }
            if any(evidence.get(key) != value for key, value in binding.items()):
                self.error("S07_REVIEW_BINDING", f"targeted review is not bound and passing: {relative}")
            if to_int(evidence.get("score"), f"{relative} score") < 90:
                self.error("S07_REVIEW_SCORE", f"targeted review score is below 90: {relative}")
            to_list(evidence.get("necessary_regression_findings"), f"{relative} necessary regression findings")
            for key in (
                "reviewer_identity",
                "reviewer_session",
                "review_run_id",
                "score",
                "verdict",
                "blocking_findings",
            ):
                if ref.get(key) != evidence.get(key):
                    self.error("S07_RESULT_REVIEW_REF", f"result reference differs from {relative}: {key}")
            for key in identities:
                identities[key].add(text(evidence, key, relative))
        if any(len(values) != 2 for values in identities.values()):
            self.error("S07_REVIEWER_COLLISION", "targeted reviewers must use different identities, sessions, and runs")

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
        if self.mapping.get("contract_ref") != PUBLIC_CONTRACT_PATH:
            self.error("R4_A04_ACTION_SOURCE_REF", "mapping must reference the public contract directly")
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
        delivery = doc(self.public_contract, "delivery_contract", "public contract")
        public_action_types = tuple(
            to_str(value, "public action type")
            for value in items(delivery, "action_card_types", "public delivery contract")
        )
        if len(public_action_types) != 8 or len(public_action_types) != len(set(public_action_types)):
            self.error("R4_A04_PUBLIC_ACTION_SOURCE", "public contract must contain eight unique action types")

        action_types: list[str] = []
        display_values: dict[str, set[str]] = {
            key: set() for key in ("user_visible_title", "user_visible_reason", "user_visible_next_action")
        }
        expected_card_fields = {
            "action_type",
            "user_visible_title",
            "user_visible_reason",
            "user_visible_next_action",
            "contains_publishable_candidate",
            "creates_light_content_plan",
            "writes_brand_fact",
            "external_call_implemented",
        }
        for raw in items(self.mapping, "action_cards", "mapping"):
            card = to_doc(raw, "action card")
            if set(card) != expected_card_fields:
                self.error("R4_A04_ACTION_SHAPE", "action cards must use the single thin display mapping shape")
            action_types.append(text(card, "action_type", "action card"))
            for field, values in display_values.items():
                value = text(card, field, "action card").strip()
                if not value:
                    self.error("R4_A05_ACTION_DISPLAY", f"action card {field} must be non-empty")
                if value in values:
                    self.error("R4_A05_ACTION_DISPLAY", f"action card {field} must not be folded into another action")
                values.add(value)
            for key, code in (
                ("contains_publishable_candidate", "A08_FAKE_PUBLISHABLE"),
                ("creates_light_content_plan", "R4_A08_ACTION_PLAN"),
                ("writes_brand_fact", "R4_A09_ACTION_FACT"),
                ("external_call_implemented", "R4_A10_ACTION_EXTERNAL_CALL"),
            ):
                if flag(card, key, "action card"):
                    self.error(code, f"action card {key} must remain false")
        if tuple(action_types) != public_action_types or len(action_types) != len(set(action_types)):
            self.error("R4_A04_ACTION_SET", "action types must exactly match the ordered public contract set")

        unknown = doc(self.mapping, "unknown_action_behavior", "mapping")
        if unknown.get("behavior") != "REPORT_INCOMPATIBLE_AND_BLOCK":
            self.error("R4_A06_UNKNOWN_ACTION", "unknown actions must report incompatibility and block")
        text(unknown, "user_visible_reason", "unknown action behavior")
        for key in (
            "contains_publishable_candidate",
            "creates_light_content_plan",
            "writes_brand_fact",
            "external_call_implemented",
        ):
            if flag(unknown, key, "unknown action behavior"):
                self.error("R4_A06_UNKNOWN_ACTION", f"unknown action fallback {key} must remain false")

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
            "NEEDS-INTERVIEW": "INTERVIEW",
            "NEEDS-RESHOOT": "RESHOOT",
            "NEEDS-ANONYMIZATION": "ANONYMIZE",
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
            self.error(
                "A11_ACCEPTANCE_COVERAGE",
                "coverage must list PKG4-A01-A12, PKG4-S01-S08, and PKG4-R4-A01-A12",
            )
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
        for changed_path in external_paths_when_package_changes(changed):
            self.error("A12_WRITE_SCOPE", f"package 4 is mixed with an external changed path: {changed_path}")
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
        expected_review_files = set(PINNED_HISTORICAL_REVIEW_FILES)
        if self.result.get("candidate_state") == SUCCESS_STATE:
            expected_review_files.update(relative for relative, _scope in TARGETED_REVIEWS.values())
        actual_review_files = {
            path.relative_to(self.root).as_posix() for path in (self.root / "reviews").rglob("*") if path.is_file()
        }
        if actual_review_files != expected_review_files:
            self.error("S07_REVIEW_FILE_SET", "review evidence files must be exactly the historical and current pair")

    def run(self, *, check_repository: bool) -> Summary:
        self.check_lightweight_shape()
        self.check_candidate_and_experience()
        self.check_review_lifecycle()
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
    if result.get("candidate_state") == FROZEN_CANDIDATE_STATE:
        changed_result["candidate_state"] = SUCCESS_STATE
        expect("PREMATURE_SUCCESS", flow, mapping, journeys, changed_result, "S07_REVIEW_STATE")
    else:
        targeted = doc(changed_result, "targeted_rereviews", "changed result")
        targeted["reviews"] = items(targeted, "reviews", "changed targeted rereviews")[:1]
        expect("MISSING_TARGETED_REVIEW", flow, mapping, journeys, changed_result, "S07_REVIEW_ROLES")

    changed_flow = copy.deepcopy(flow)
    changed_experience = doc(doc(changed_flow, "application", "flow"), "user_experience", "application")
    generic_topics = [f"通用行业占位{index}" for index in range(1, 9)]
    for raw_mapping, generic_name in zip(
        items(changed_experience, "topic_category_display_mapping", "user experience"), generic_topics, strict=True
    ):
        to_doc(raw_mapping, "topic display mapping")["display_name"] = generic_name
    changed_experience["user_visible_topic_categories"] = generic_topics
    expect("GENERIC_TOPIC_REPLACEMENT", changed_flow, mapping, journeys, result, "R4_A02_TOPIC_ALIGNMENT")

    changed_flow = copy.deepcopy(flow)
    changed_experience = doc(doc(changed_flow, "application", "flow"), "user_experience", "application")
    items(changed_experience, "topic_category_display_mapping", "user experience").pop()
    items(changed_experience, "user_visible_topic_categories", "user experience").pop()
    expect("MISSING_TOPIC", changed_flow, mapping, journeys, result, "R4_A02_TOPIC_ALIGNMENT")

    changed_flow = copy.deepcopy(flow)
    changed_experience = doc(doc(changed_flow, "application", "flow"), "user_experience", "application")
    changed_topics = items(changed_experience, "topic_category_display_mapping", "user experience")
    changed_topics[1] = copy.deepcopy(changed_topics[0])
    changed_visible_topics = items(changed_experience, "user_visible_topic_categories", "user experience")
    changed_visible_topics[1] = changed_visible_topics[0]
    expect("DUPLICATE_TOPIC", changed_flow, mapping, journeys, result, "R4_A02_TOPIC_ALIGNMENT")

    changed_flow = copy.deepcopy(flow)
    changed_experience = doc(doc(changed_flow, "application", "flow"), "user_experience", "application")
    changed_topic = to_doc(
        items(changed_experience, "topic_category_display_mapping", "user experience")[0], "topic mapping"
    )
    changed_topic["topic_category_id"] = "TOPIC-99"
    expect("TOPIC_ID_DRIFT", changed_flow, mapping, journeys, result, "R4_A02_TOPIC_ALIGNMENT")

    changed_flow = copy.deepcopy(flow)
    changed_experience = doc(doc(changed_flow, "application", "flow"), "user_experience", "application")
    changed_topic = to_doc(
        items(changed_experience, "topic_category_display_mapping", "user experience")[0], "topic mapping"
    )
    changed_topic["display_name"] = "名称漂移"
    items(changed_experience, "user_visible_topic_categories", "user experience")[0] = "名称漂移"
    expect("TOPIC_NAME_DRIFT", changed_flow, mapping, journeys, result, "R4_A02_TOPIC_ALIGNMENT")

    changed_mapping = copy.deepcopy(mapping)
    items(changed_mapping, "action_cards", "mapping").pop()
    expect("MISSING_ACTION", flow, changed_mapping, journeys, result, "R4_A04_ACTION_SET")

    changed_mapping = copy.deepcopy(mapping)
    changed_actions = items(changed_mapping, "action_cards", "mapping")
    to_doc(changed_actions[-1], "action card")["action_type"] = text(
        to_doc(changed_actions[0], "action card"), "action_type"
    )
    expect("DUPLICATE_ACTION", flow, changed_mapping, journeys, result, "R4_A04_ACTION_SET")

    changed_mapping = copy.deepcopy(mapping)
    changed_actions = items(changed_mapping, "action_cards", "mapping")
    extra_action = copy.deepcopy(to_doc(changed_actions[-1], "action card"))
    extra_action.update(
        {
            "action_type": "CUSTOM_UNKNOWN_ACTION",
            "user_visible_title": "自造行动",
            "user_visible_reason": "这是一条不应通过的自造行动。",
            "user_visible_next_action": "这条自造行动必须被检查器拒绝。",
        }
    )
    changed_actions.append(extra_action)
    expect("EXTRA_ACTION", flow, changed_mapping, journeys, result, "R4_A04_ACTION_SET")

    changed_mapping = copy.deepcopy(mapping)
    fold_actions: list[Doc] = [
        to_doc(raw, "action card") for raw in items(changed_mapping, "action_cards", "mapping")
    ]
    material = next(card for card in fold_actions if card.get("action_type") == "COLLECT_MATERIAL")
    interview = next(card for card in fold_actions if card.get("action_type") == "INTERVIEW")
    for key in ("user_visible_title", "user_visible_reason", "user_visible_next_action"):
        interview[key] = material[key]
    expect("FOLDED_ACTION", flow, changed_mapping, journeys, result, "R4_A05_ACTION_DISPLAY")

    changed_mapping = copy.deepcopy(mapping)
    doc(changed_mapping, "unknown_action_behavior", "mapping")["behavior"] = "GUESS_AND_CONTINUE"
    expect("UNKNOWN_ACTION_GUESS", flow, changed_mapping, journeys, result, "R4_A06_UNKNOWN_ACTION")

    changed_mapping = copy.deepcopy(mapping)
    first_action = to_doc(items(changed_mapping, "action_cards", "mapping")[0], "action card")
    first_action["user_visible_title"] = "TOPIC-01"
    expect("VISIBLE_TOPIC_ID", flow, changed_mapping, journeys, result, "A09_USER_VISIBLE_LEAK")

    scope_cases = (
        ("PACKAGE_ONLY_SCOPE", {f"{ALLOWED_ROOT}{FLOW_FILE}"}, ()),
        (
            "PACKAGE_WITH_EXTERNAL_SCOPE",
            {f"{ALLOWED_ROOT}{FLOW_FILE}", "15_successor_package/change.json"},
            ("15_successor_package/change.json",),
        ),
        ("SUCCESSOR_ONLY_SCOPE", {"15_successor_package/change.json"}, ()),
    )
    for name, changed_paths, expected_external in scope_cases:
        if external_paths_when_package_changes(changed_paths) != expected_external:
            failures.append(f"SELFTEST_{name}: conditional package write scope differs")
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
