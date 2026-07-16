#!/usr/bin/env python3
"""Package 7 persistence adapters and transactional repository."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_2_ROOT = REPOSITORY_ROOT / "12_expression_service/expression_runtime_adapter_001"
if str(PACKAGE_2_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_2_ROOT))

from light_expression_service import PlanFactory, PlanRecord  # type: ignore[import-not-found]  # noqa: E402

from runtime_models import (  # noqa: E402
    Base,
    RuntimeAccount,
    RuntimeAuthorization,
    RuntimeCandidate,
    RuntimeDifyConversation,
    RuntimeDifyInvocation,
    RuntimeFeedback,
    RuntimeModelRun,
    RuntimeNarrativeFragment,
    RuntimePlan,
    RuntimePreciseFact,
    RuntimePrincipal,
    RuntimeRequirement,
    RuntimeSetting,
    RuntimeSubjectConfirmation,
    RuntimeValidation,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
    def serialize(item: object) -> str:
        if isinstance(item, datetime):
            normalized = item if item.tzinfo is not None else item.replace(tzinfo=timezone.utc)
            return normalized.astimezone(timezone.utc).isoformat()
        return str(item)

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=serialize,
    )


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def create_runtime_engine(database_url: str) -> Engine:
    """Build a reconnect-safe engine without embedding environment defaults."""

    if not database_url or "://" not in database_url:
        raise ValueError("A valid runtime database URL is required")
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


class SqlAlchemyPlanStore:
    """Persistent implementation of the Package 2 plan-store boundary."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    @staticmethod
    def _key_text(key: tuple[str, str, str, int]) -> str:
        return canonical_json(list(key))

    def materialize(
        self,
        key: tuple[str, str, str, int],
        input_digest: str,
        factory: PlanFactory,
    ) -> JsonObject:
        key_text = self._key_text(key)
        with self.sessions.begin() as session:
            row = session.scalar(select(RuntimePlan).where(RuntimePlan.plan_key == key_text).with_for_update())
            if row is not None and row.input_digest == input_digest:
                return copy.deepcopy(row.plan_payload)
            revision = 1 if row is None else row.plan_revision + 1
            plan = copy.deepcopy(factory(revision))
            if row is None:
                row = RuntimePlan(
                    plan_key=key_text,
                    plan_ref=str(plan["composition_plan_ref"]),
                    input_digest=input_digest,
                    plan_revision=revision,
                    plan_payload=plan,
                    source_request={},
                    updated_at=utc_now(),
                )
                session.add(row)
            else:
                row.plan_ref = str(plan["composition_plan_ref"])
                row.input_digest = input_digest
                row.plan_revision = revision
                row.plan_payload = plan
                row.source_request = {}
                row.updated_at = utc_now()
            session.flush()
            return copy.deepcopy(plan)

    def attach_source(self, plan_ref: str, source_request: JsonObject) -> None:
        with self.sessions.begin() as session:
            row = session.scalar(select(RuntimePlan).where(RuntimePlan.plan_ref == plan_ref).with_for_update())
            if row is None:
                raise KeyError(plan_ref)
            row.source_request = copy.deepcopy(source_request)
            row.updated_at = utc_now()

    def get(self, plan_ref: str) -> PlanRecord | None:
        with self.sessions() as session:
            row = session.scalar(select(RuntimePlan).where(RuntimePlan.plan_ref == plan_ref))
            if row is None:
                return None
            key_value = json.loads(row.plan_key)
            if not isinstance(key_value, list) or len(key_value) != 4:
                raise ValueError("Stored plan key is invalid")
            key = (str(key_value[0]), str(key_value[1]), str(key_value[2]), int(key_value[3]))
            return PlanRecord(
                key=key,
                input_digest=row.input_digest,
                plan=copy.deepcopy(row.plan_payload),
                source_request=copy.deepcopy(row.source_request),
            )


class RuntimeRepository:
    """Small transaction boundary for identity, evidence and user choices."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def initialize_schema(self, engine: Engine) -> None:
        Base.metadata.create_all(engine)

    def principal_by_username(self, username: str) -> RuntimePrincipal | None:
        with self.sessions() as session:
            return session.scalar(select(RuntimePrincipal).where(RuntimePrincipal.username == username))

    def principal_by_id(self, principal_id: str) -> RuntimePrincipal | None:
        with self.sessions() as session:
            return session.get(RuntimePrincipal, principal_id)

    def account_by_display_name(self, display_name: str) -> RuntimeAccount | None:
        with self.sessions() as session:
            return session.scalar(select(RuntimeAccount).where(RuntimeAccount.display_name == display_name))

    def account_by_id(self, account_id: str) -> RuntimeAccount | None:
        with self.sessions() as session:
            return session.get(RuntimeAccount, account_id)

    def all_accounts(self) -> tuple[RuntimeAccount, ...]:
        with self.sessions() as session:
            return tuple(session.scalars(select(RuntimeAccount).order_by(RuntimeAccount.account_id)).all())

    def identity_payloads(self) -> JsonObject:
        with self.sessions() as session:
            return {
                "principals": [copy.deepcopy(row.payload) for row in session.scalars(select(RuntimePrincipal)).all()],
                "accounts": [copy.deepcopy(row.payload) for row in session.scalars(select(RuntimeAccount)).all()],
                "authorizations": [
                    copy.deepcopy(row.payload) for row in session.scalars(select(RuntimeAuthorization)).all()
                ],
                "subject_confirmations": [
                    copy.deepcopy(row.payload) for row in session.scalars(select(RuntimeSubjectConfirmation)).all()
                ],
            }

    def narrative_fragments(self, fragment_ids: list[str] | None = None) -> tuple[JsonObject, ...]:
        with self.sessions() as session:
            statement = select(RuntimeNarrativeFragment)
            if fragment_ids is not None:
                statement = statement.where(RuntimeNarrativeFragment.fragment_id.in_(fragment_ids))
            rows = session.scalars(statement.order_by(RuntimeNarrativeFragment.fragment_id)).all()
            return tuple(copy.deepcopy(row.payload) for row in rows)

    def precise_facts(self) -> tuple[JsonObject, ...]:
        with self.sessions() as session:
            rows = session.scalars(select(RuntimePreciseFact).order_by(RuntimePreciseFact.fact_id)).all()
            return tuple(copy.deepcopy(row.payload) for row in rows)

    def bind_dify_documents(self, mapping: dict[str, JsonObject]) -> None:
        with self.sessions.begin() as session:
            known_ids = set(
                session.scalars(
                    select(RuntimeNarrativeFragment.fragment_id).where(
                        RuntimeNarrativeFragment.fragment_id.in_(mapping)
                    )
                ).all()
            )
            if known_ids != set(mapping):
                raise ValueError("Dify document mapping contains an unknown fragment")
            for fragment_id, binding in mapping.items():
                row = session.get(RuntimeNarrativeFragment, fragment_id)
                if row is None:
                    raise RuntimeError("unreachable")
                document_id = binding.get("document_id")
                index_digest = binding.get("index_content_sha256")
                if (
                    not isinstance(document_id, str)
                    or not isinstance(index_digest, str)
                    or len(index_digest) != 64
                ):
                    raise ValueError("Dify document binding is invalid")
                row.dify_document_id = document_id
                row.content_digest = index_digest
                row.updated_at = utc_now()

    def set_fragment_state(
        self,
        fragment_id: str,
        *,
        status: str,
        revocation_ref: str | None,
    ) -> None:
        with self.sessions.begin() as session:
            row = session.get(RuntimeNarrativeFragment, fragment_id, with_for_update=True)
            if row is None:
                raise KeyError(fragment_id)
            row.status = status
            row.revocation_ref = revocation_ref
            payload = copy.deepcopy(row.payload)
            payload["status"] = status
            payload["revocation_ref"] = revocation_ref
            row.payload = payload
            row.updated_at = utc_now()

    def setting(self, key: str) -> JsonObject:
        with self.sessions() as session:
            row = session.get(RuntimeSetting, key)
            if row is None:
                raise KeyError(key)
            return copy.deepcopy(row.payload)

    def reserve_dify_invocation(
        self,
        *,
        invocation_id: str,
        principal_id: str,
        model_call_upper_bound: int = 2,
        maximum_model_calls: int = 40,
    ) -> None:
        if model_call_upper_bound < 1:
            raise ValueError("A positive model-call upper bound is required")
        with self.sessions.begin() as session:
            used = sum(
                session.scalars(select(RuntimeDifyInvocation.model_call_upper_bound)).all()
            )
            if used + model_call_upper_bound > maximum_model_calls:
                raise ValueError("Package 7 model-call budget is exhausted")
            if session.get(RuntimeDifyInvocation, invocation_id) is not None:
                raise ValueError("Dify invocation identity was reused")
            now = utc_now()
            session.add(
                RuntimeDifyInvocation(
                    invocation_id=invocation_id,
                    principal_id=principal_id,
                    state="RESERVED",
                    model_call_upper_bound=model_call_upper_bound,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    total_price="0",
                    currency="UNKNOWN",
                    response_digest=None,
                    failure_class=None,
                    created_at=now,
                    updated_at=now,
                )
            )

    def complete_dify_invocation(
        self,
        invocation_id: str,
        *,
        account_id: str,
        usage: JsonObject,
        response_digest: str,
        dify_user_key: str,
        conversation_id: str,
    ) -> None:
        if not dify_user_key or not conversation_id:
            raise ValueError("Dify conversation binding is incomplete")
        with self.sessions.begin() as session:
            row = session.get(RuntimeDifyInvocation, invocation_id, with_for_update=True)
            if row is None or row.state != "RESERVED":
                raise ValueError("Unknown or completed Dify invocation")
            principal = session.get(RuntimePrincipal, row.principal_id)
            account = session.get(RuntimeAccount, account_id)
            if (
                principal is None
                or account is None
                or account_id not in principal.allowed_account_ids
            ):
                raise ValueError("Dify conversation account is outside the principal scope")
            binding = session.scalar(
                select(RuntimeDifyConversation)
                .where(
                    RuntimeDifyConversation.principal_id == row.principal_id,
                    RuntimeDifyConversation.account_id == account_id,
                )
                .with_for_update()
            )
            if binding is None:
                now = utc_now()
                session.add(
                    RuntimeDifyConversation(
                        principal_id=row.principal_id,
                        account_id=account_id,
                        dify_user_key=dify_user_key,
                        conversation_id=conversation_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
            elif (
                binding.dify_user_key != dify_user_key
                or binding.conversation_id != conversation_id
            ):
                raise ValueError("Dify conversation identity changed unexpectedly")
            row.state = "SUCCEEDED"
            row.prompt_tokens = int(usage.get("prompt_tokens", 0))
            row.completion_tokens = int(usage.get("completion_tokens", 0))
            row.total_tokens = int(usage.get("total_tokens", 0))
            row.total_price = str(usage.get("total_price", "0"))
            row.currency = str(usage.get("currency", "UNKNOWN"))
            row.response_digest = response_digest
            row.updated_at = utc_now()

    def dify_conversation(self, principal_id: str, account_id: str) -> tuple[str, str] | None:
        with self.sessions() as session:
            row = session.scalar(
                select(RuntimeDifyConversation).where(
                    RuntimeDifyConversation.principal_id == principal_id,
                    RuntimeDifyConversation.account_id == account_id,
                )
            )
            if row is None:
                return None
            return row.dify_user_key, row.conversation_id

    def adopt_dify_conversation(
        self,
        *,
        principal_id: str,
        account_id: str,
        dify_user_key: str,
        conversation_id: str,
    ) -> None:
        """Bind one current-app conversation when no runtime binding exists yet."""

        if not dify_user_key or not conversation_id:
            raise ValueError("Dify conversation binding is incomplete")
        with self.sessions.begin() as session:
            principal = session.get(RuntimePrincipal, principal_id)
            account = session.get(RuntimeAccount, account_id)
            if (
                principal is None
                or account is None
                or account_id not in principal.allowed_account_ids
            ):
                raise ValueError("Dify conversation account is outside the principal scope")
            row = session.scalar(
                select(RuntimeDifyConversation)
                .where(
                    RuntimeDifyConversation.principal_id == principal_id,
                    RuntimeDifyConversation.account_id == account_id,
                )
                .with_for_update()
            )
            if row is not None:
                if (
                    row.dify_user_key != dify_user_key
                    or row.conversation_id != conversation_id
                ):
                    raise ValueError("Existing Dify conversation binding is immutable")
                return
            now = utc_now()
            session.add(
                RuntimeDifyConversation(
                    principal_id=principal_id,
                    account_id=account_id,
                    dify_user_key=dify_user_key,
                    conversation_id=conversation_id,
                    created_at=now,
                    updated_at=now,
                )
            )

    def fail_dify_invocation(self, invocation_id: str, *, failure_class: str) -> None:
        with self.sessions.begin() as session:
            row = session.get(RuntimeDifyInvocation, invocation_id, with_for_update=True)
            if row is None or row.state != "RESERVED":
                raise ValueError("Unknown or completed Dify invocation")
            row.state = "FAILED_OR_UNKNOWN_BILLING"
            row.failure_class = failure_class[:80]
            row.updated_at = utc_now()

    def dify_invocation_audit(self) -> JsonObject:
        with self.sessions() as session:
            rows = list(
                session.scalars(
                    select(RuntimeDifyInvocation).order_by(RuntimeDifyInvocation.created_at)
                ).all()
            )
            return {
                "invocation_count": len(rows),
                "model_call_upper_bound": sum(row.model_call_upper_bound for row in rows),
                "known_total_tokens": sum(row.total_tokens for row in rows),
                "known_prices": [
                    {"total_price": row.total_price, "currency": row.currency}
                    for row in rows
                    if row.state == "SUCCEEDED"
                ],
                "failed_or_unknown_billing_count": sum(
                    row.state == "FAILED_OR_UNKNOWN_BILLING" for row in rows
                ),
            }

    def save_requirement(self, payload: JsonObject, principal_id: str, account_id: str) -> None:
        requirement_id = str(payload["requirement_id"])
        version = int(payload["requirement_version"])
        with self.sessions.begin() as session:
            existing = session.scalar(
                select(RuntimeRequirement).where(
                    RuntimeRequirement.requirement_id == requirement_id,
                    RuntimeRequirement.requirement_version == version,
                )
            )
            if existing is not None:
                if digest_object(existing.payload) != digest_object(payload):
                    raise ValueError("Requirement identity was reused with different content")
                return
            session.add(
                RuntimeRequirement(
                    requirement_id=requirement_id,
                    requirement_version=version,
                    principal_id=principal_id,
                    account_id=account_id,
                    status=str(payload["status"]),
                    payload=copy.deepcopy(payload),
                    created_at=utc_now(),
                )
            )

    def start_model_run(
        self,
        *,
        run_id: str,
        principal_id: str,
        account_id: str,
        operation: str,
        plan_ref: str | None,
        prompt_digest: str,
        payload: JsonObject,
    ) -> None:
        with self.sessions.begin() as session:
            if session.get(RuntimeModelRun, run_id) is not None:
                raise ValueError("Model run already exists")
            now = utc_now()
            session.add(
                RuntimeModelRun(
                    run_id=run_id,
                    principal_id=principal_id,
                    account_id=account_id,
                    operation=operation,
                    state="AWAITING_FIRST_MODEL_OUTPUT",
                    plan_ref=plan_ref,
                    prompt_digest=prompt_digest,
                    model_output_digest=None,
                    first_output_preserved=False,
                    payload=copy.deepcopy(payload),
                    created_at=now,
                    updated_at=now,
                )
            )

    def model_run(self, run_id: str) -> RuntimeModelRun | None:
        with self.sessions() as session:
            return session.get(RuntimeModelRun, run_id)

    def recent_chat_turns(
        self,
        *,
        principal_id: str,
        account_id: str,
        limit: int = 6,
    ) -> tuple[JsonObject, ...]:
        """Return only accepted, sanitized chat surfaces for bounded continuity."""

        if limit < 1 or limit > 12:
            raise ValueError("Chat continuity limit must be between 1 and 12")
        with self.sessions() as session:
            rows = list(
                session.scalars(
                    select(RuntimeModelRun)
                    .where(
                        RuntimeModelRun.principal_id == principal_id,
                        RuntimeModelRun.account_id == account_id,
                        RuntimeModelRun.operation.in_(("普通聊天", "找灵感")),
                        RuntimeModelRun.state == "FIRST_OUTPUT_ACCEPTED",
                    )
                    .order_by(RuntimeModelRun.created_at.desc())
                    .limit(limit)
                ).all()
            )
        turns: list[JsonObject] = []
        for row in reversed(rows):
            prompt = row.payload.get("prompt")
            envelope = row.payload.get("envelope")
            user_message = prompt.get("user_message") if isinstance(prompt, dict) else None
            reply = envelope.get("reply") if isinstance(envelope, dict) else None
            if isinstance(user_message, str) and isinstance(reply, str):
                turns.append({"user_message": user_message, "assistant_reply": reply})
        return tuple(turns)

    def preserve_first_output(self, run_id: str, output_digest: str, state: str, payload: JsonObject) -> RuntimeModelRun:
        with self.sessions.begin() as session:
            row = session.get(RuntimeModelRun, run_id, with_for_update=True)
            if row is None:
                raise KeyError(run_id)
            if row.first_output_preserved:
                raise ValueError("Content reroll is forbidden for a completed run")
            row.model_output_digest = output_digest
            row.first_output_preserved = True
            row.state = state
            merged_payload = copy.deepcopy(row.payload)
            merged_payload.update(copy.deepcopy(payload))
            row.payload = merged_payload
            row.updated_at = utc_now()
            session.flush()
            return row

    def save_candidate_set(
        self,
        *,
        run_id: str,
        account_id: str,
        plan_ref: str,
        candidates: list[JsonObject],
        validations: list[JsonObject],
        preserved_revalidation_digest: str | None = None,
        preserved_revalidation_payload: JsonObject | None = None,
    ) -> None:
        if len(candidates) != len(validations):
            raise ValueError("Every candidate needs one validation")
        if (preserved_revalidation_digest is None) != (
            preserved_revalidation_payload is None
        ):
            raise ValueError("Preserved revalidation fields must be supplied together")
        with self.sessions.begin() as session:
            revalidated_run = None
            if preserved_revalidation_digest is not None:
                revalidated_run = session.get(
                    RuntimeModelRun,
                    run_id,
                    with_for_update=True,
                )
                if (
                    revalidated_run is None
                    or not revalidated_run.first_output_preserved
                    or revalidated_run.state != "FIRST_OUTPUT_REJECTED"
                    or revalidated_run.model_output_digest != preserved_revalidation_digest
                ):
                    raise ValueError("Preserved model output is not eligible for revalidation")
                existing_candidate = session.scalar(
                    select(RuntimeCandidate.candidate_id)
                    .where(RuntimeCandidate.run_id == run_id)
                    .limit(1)
                )
                if existing_candidate is not None:
                    raise ValueError("Preserved model output was already materialized")
            for ordinal, (candidate, validation) in enumerate(zip(candidates, validations, strict=True), 1):
                candidate_id = str(candidate["candidate_id"])
                session.add(
                    RuntimeCandidate(
                        candidate_id=candidate_id,
                        run_id=run_id,
                        plan_ref=plan_ref,
                        account_id=account_id,
                        ordinal=ordinal,
                        selected=False,
                        candidate_payload=copy.deepcopy(candidate),
                        used_fact_refs=list(candidate["used_fact_refs"]),
                        used_material_refs=list(candidate["used_material_refs"]),
                        created_at=utc_now(),
                    )
                )
                session.add(
                    RuntimeValidation(
                        validation_id=str(validation["decision_id"]),
                        candidate_id=candidate_id,
                        decision=str(validation["decision"]),
                        payload=copy.deepcopy(validation),
                        created_at=utc_now(),
                    )
                )
            if revalidated_run is not None:
                merged_payload = copy.deepcopy(revalidated_run.payload)
                merged_payload["deterministic_revalidation"] = copy.deepcopy(
                    preserved_revalidation_payload
                )
                revalidated_run.payload = merged_payload
                revalidated_run.state = (
                    "FIRST_OUTPUT_ACCEPTED_AFTER_DETERMINISTIC_REVALIDATION"
                )
                revalidated_run.updated_at = utc_now()

    def latest_candidates(self, account_id: str) -> tuple[RuntimeCandidate, ...]:
        with self.sessions() as session:
            latest_run = session.scalar(
                select(RuntimeCandidate.run_id)
                .where(RuntimeCandidate.account_id == account_id)
                .order_by(RuntimeCandidate.created_at.desc())
                .limit(1)
            )
            if latest_run is None:
                return ()
            return tuple(
                session.scalars(
                    select(RuntimeCandidate)
                    .where(RuntimeCandidate.run_id == latest_run)
                    .order_by(RuntimeCandidate.ordinal)
                ).all()
            )

    def select_candidate(self, account_id: str, ordinal: int) -> RuntimeCandidate:
        with self.sessions.begin() as session:
            candidates = list(
                session.scalars(
                    select(RuntimeCandidate)
                    .where(RuntimeCandidate.account_id == account_id)
                    .order_by(RuntimeCandidate.created_at.desc(), RuntimeCandidate.ordinal)
                ).all()
            )
            if not candidates:
                raise KeyError("No candidate set exists")
            latest_run = candidates[0].run_id
            current = [row for row in candidates if row.run_id == latest_run]
            chosen = next((row for row in current if row.ordinal == ordinal), None)
            if chosen is None:
                raise KeyError("Candidate number is unavailable")
            for row in current:
                row.selected = row.candidate_id == chosen.candidate_id
            session.flush()
            return chosen

    def selected_candidate(self, account_id: str) -> RuntimeCandidate | None:
        with self.sessions() as session:
            return session.scalar(
                select(RuntimeCandidate)
                .where(RuntimeCandidate.account_id == account_id, RuntimeCandidate.selected.is_(True))
                .order_by(RuntimeCandidate.created_at.desc())
                .limit(1)
            )

    def candidate_belongs_to_account(self, candidate_id: str, account_id: str) -> bool:
        with self.sessions() as session:
            row = session.get(RuntimeCandidate, candidate_id)
            return row is not None and row.account_id == account_id

    def latest_candidate(self, account_id: str) -> RuntimeCandidate | None:
        with self.sessions() as session:
            return session.scalar(
                select(RuntimeCandidate)
                .where(RuntimeCandidate.account_id == account_id)
                .order_by(RuntimeCandidate.created_at.desc(), RuntimeCandidate.ordinal)
                .limit(1)
            )

    def requirement_id_for_run(self, run_id: str) -> str | None:
        with self.sessions() as session:
            run = session.get(RuntimeModelRun, run_id)
            if run is None or run.plan_ref is None:
                return None
            plan = session.scalar(select(RuntimePlan).where(RuntimePlan.plan_ref == run.plan_ref))
            if plan is None:
                return None
            requirement = plan.source_request.get("confirmed_requirement")
            if not isinstance(requirement, dict):
                return None
            value = requirement.get("requirement_id")
            return value if isinstance(value, str) else None

    def requirement_context_for_run(self, run_id: str) -> JsonObject:
        with self.sessions() as session:
            run = session.get(RuntimeModelRun, run_id)
            if run is None or run.plan_ref is None:
                return {}
            plan = session.scalar(select(RuntimePlan).where(RuntimePlan.plan_ref == run.plan_ref))
            if plan is None:
                return {}
            requirement = plan.source_request.get("confirmed_requirement")
            return copy.deepcopy(requirement) if isinstance(requirement, dict) else {}

    def save_feedback(
        self,
        *,
        principal_id: str,
        account_id: str,
        candidate_id: str | None,
        requirement_id: str | None,
        role_id: str | None,
        storyline_id: str | None,
        column_id: str | None,
        previous_content_ref: str | None,
        fact_refs: list[str],
        material_refs: list[str],
        short_reason: str,
    ) -> str:
        seed = [principal_id, account_id, candidate_id, short_reason, utc_now().isoformat()]
        feedback_id = f"FEEDBACK-{digest_object(seed)[:20].upper()}"
        with self.sessions.begin() as session:
            session.add(
                RuntimeFeedback(
                    feedback_id=feedback_id,
                    principal_id=principal_id,
                    account_id=account_id,
                    candidate_id=candidate_id,
                    requirement_id=requirement_id,
                    role_id=role_id,
                    storyline_id=storyline_id,
                    column_id=column_id,
                    previous_content_ref=previous_content_ref,
                    fact_refs=list(fact_refs),
                    material_refs=list(material_refs),
                    review_state="PENDING_REVIEW",
                    short_reason=short_reason,
                    created_at=utc_now(),
                )
            )
        return feedback_id

    def transactional_probe(self, mutation: Callable[[Session], None]) -> None:
        """Exercise rollback behavior without permitting a partial commit."""

        session = self.sessions()
        try:
            mutation(session)
            raise RuntimeError("intentional rollback probe")
        except RuntimeError:
            session.rollback()
        finally:
            session.close()
