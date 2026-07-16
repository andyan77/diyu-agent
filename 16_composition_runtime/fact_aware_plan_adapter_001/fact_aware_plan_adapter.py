#!/usr/bin/env python3
"""Thin Package 5 to Package 2 adapter for server-confirmed production tasks."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, cast


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_2_ROOT = (
    REPOSITORY_ROOT / "12_expression_service/expression_runtime_adapter_001"
)
PACKAGE_5_ROOT = REPOSITORY_ROOT / "15_brand_retrieval/brand_fact_retrieval_001"
IDENTITY_PATH = (
    REPOSITORY_ROOT
    / "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml"
)

for import_root in (PACKAGE_2_ROOT, PACKAGE_5_ROOT):
    import_path = str(import_root)
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from brand_fact_retrieval import (  # type: ignore[import-not-found]  # noqa: E402
    BrandFactRetrievalService,
    IdentityAuthority,
    RetrievalContractError,
    RetrievalIndex,
    digest_object as digest_retrieval_object,
)
from light_expression_service import (  # type: ignore[import-not-found]  # noqa: E402
    LightExpressionService,
    TrustedUpstreamContext,
    digest_object as digest_plan_object,
    parse_time,
)


START_CREATION = "START_CREATION"
SERVER_TASK_AUTHORITY = "SERVER_CONFIRMED_TASK_REGISTRY"
SERVER_ACCESS_AUTHORITY = "SERVER_SESSION_SCOPE"
NEUTRAL_PROFILE_MODE = "NEUTRAL_DEFAULT"
TrustedContextFactory = Callable[[JsonObject], TrustedUpstreamContext]
ExpressionProfileResolver = Callable[["ServerConfirmedProductionTask", JsonObject], JsonObject]


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize one audit value deterministically."""

    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def copy_mapping(value: Mapping[str, Any]) -> JsonObject:
    return copy.deepcopy(dict(value))


@dataclass(frozen=True)
class ServerConfirmedProductionTask:
    """Server-owned task projection; it is never built from a Dify request body."""

    server_task_ref: str
    authority_source: str
    intent: str
    request_id: str
    principal_id: str
    content_account_id: str
    acting_role_id: str
    query_at: str
    confirmed_requirement: Mapping[str, Any]
    confirmation_evidence: Mapping[str, Any]
    retrieval_query_text: str
    precise_fact_queries: tuple[Mapping[str, Any], ...] = ()
    max_fragments: int = 5
    requested_high_level_mode_refs: tuple[str, ...] = ()
    client_soft_preferences: Mapping[str, Any] = field(default_factory=dict)
    output_requirements: Mapping[str, Any] = field(default_factory=dict)
    experimental_diagnostics: Mapping[str, Any] = field(default_factory=dict)
    untrusted_client_claims: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ServerPlanAccess:
    """Current server session scope used for plan-bound material access."""

    authority_source: str
    principal_id: str
    content_account_id: str


class PlanMaterialAccessDenied(PermissionError):
    """Fail-closed author material access error without exposing hidden records."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class FactAwarePlanAdapter:
    """Compose existing retrieval and light-expression services without new contracts."""

    def __init__(
        self,
        retrieval_service: BrandFactRetrievalService,
        expression_service: LightExpressionService,
        identity_path: Path,
        *,
        trusted_context_factory: TrustedContextFactory | None = None,
        expression_profile_resolver: ExpressionProfileResolver | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.expression_service = expression_service
        self.identity_path = identity_path
        self._trusted_context_factory = trusted_context_factory
        self._expression_profile_resolver = expression_profile_resolver
        self._integration_records: list[JsonObject] = []
        self._entrypoint_calls = {
            "package5_retrieve": 0,
            "package2_prepare": 0,
            "package2_validate": 0,
        }

    @classmethod
    def from_repository(
        cls, repository_root: Path = REPOSITORY_ROOT
    ) -> FactAwarePlanAdapter:
        package_5_root = (
            repository_root / "15_brand_retrieval/brand_fact_retrieval_001"
        )
        identity_path = (
            repository_root
            / "11_product_foundation/public_foundation_001/identity/"
            "simulation_tenant.v1.yaml"
        )
        retrieval = BrandFactRetrievalService(
            IdentityAuthority.from_path(identity_path),
            RetrievalIndex.from_package(package_5_root),
        )
        return cls(retrieval, LightExpressionService(repository_root), identity_path)

    @property
    def integration_records(self) -> tuple[JsonObject, ...]:
        return tuple(copy.deepcopy(self._integration_records))

    @property
    def call_audit(self) -> JsonObject:
        return {
            **self._entrypoint_calls,
            "external_model_calls": 0,
            "external_dify_calls": 0,
            "external_database_calls": 0,
            "external_vector_calls": 0,
            "external_network_calls": 0,
        }

    def prepare(
        self,
        task: object,
    ) -> JsonObject:
        """Return the Package 2 plan or action card as the sole business result."""

        if not isinstance(task, ServerConfirmedProductionTask):
            return self._guard_action_card(
                {},
                "只有服务端确认的制作任务可以进入内容计划准备。",
                ["server_confirmed_task"],
            )
        requirement = copy_mapping(task.confirmed_requirement)
        action_request = {"confirmed_requirement": requirement}
        if (
            task.authority_source != SERVER_TASK_AUTHORITY
            or task.intent != START_CREATION
        ):
            result = self._guard_action_card(
                action_request,
                "当前请求不是已经确认的开始内容制作任务。",
                ["confirmed_production_intent"],
            )
            self._append_record(
                task,
                None,
                result,
                package_5_called=False,
                package_2_called=False,
            )
            return result

        retrieval_request: JsonObject = {
            "query_text": task.retrieval_query_text,
            "max_fragments": task.max_fragments,
            "precise_fact_queries": [
                copy_mapping(query) for query in task.precise_fact_queries
            ],
            "client_claims": copy_mapping(task.untrusted_client_claims),
            "requested_high_level_mode_refs": list(
                task.requested_high_level_mode_refs
            ),
            # Package 5 examples are candidates, not Package 2 approved examples.
            "approved_example_refs": [],
        }
        try:
            self._entrypoint_calls["package5_retrieve"] += 1
            retrieval = self.retrieval_service.retrieve(
                retrieval_request,
                principal_id=task.principal_id,
                content_account_id=task.content_account_id,
                query_at=task.query_at,
            )
        except RetrievalContractError:
            result = self._guard_action_card(
                action_request,
                "服务端身份范围或检索请求无效，不能继续准备内容计划。",
                ["trusted_retrieval_request"],
            )
            self._append_record(
                task,
                None,
                result,
                package_5_called=True,
                package_2_called=False,
            )
            return result

        precise_fact_gaps = [
            copy_mapping(gap)
            for gap in retrieval["gaps"]
            if str(gap.get("code", "")).startswith("PRECISE_FACT_")
        ]
        if precise_fact_gaps:
            gap_codes = [str(gap["code"]) for gap in precise_fact_gaps]
            fact_kinds = sorted(
                {
                    str(gap["fact_kind"])
                    for gap in precise_fact_gaps
                    if gap.get("fact_kind")
                }
            )
            result = self._guard_action_card(
                action_request,
                "所需精确事实缺失、冲突或需要重新确认，不能降级为叙事计划。",
                [*gap_codes, *fact_kinds],
                action_type="COLLECT_FACT",
            )
            self._append_record(
                task,
                retrieval,
                result,
                package_5_called=True,
                package_2_called=False,
            )
            return result

        prepare_request = self._build_prepare_request(task, retrieval)
        context = self._trusted_context(prepare_request)
        self._entrypoint_calls["package2_prepare"] += 1
        result = self.expression_service.prepare(
            prepare_request,
            context,
            parse_time(str(retrieval["query_at"])),
        )
        self._append_record(
            task,
            retrieval,
            result,
            package_5_called=True,
            package_2_called=True,
        )
        return cast(JsonObject, result)

    def author_materials(
        self,
        composition_plan_ref: str,
        access: object,
    ) -> JsonObject:
        """Return an immediate copy of exactly the materials allowed by one plan."""

        record, source, scope = self._plan_record_for_access(
            composition_plan_ref, access
        )
        plan = record.plan
        fragment_rows = self._object_rows(
            source.get("scoped_retrieval_fragments"), "PLAN_SOURCE_INVALID"
        )
        fact_rows = self._object_rows(
            source.get("verified_precise_facts"), "PLAN_SOURCE_INVALID"
        )
        fragment_refs = [str(row.get("fragment_id")) for row in fragment_rows]
        fact_refs = [str(row.get("fact_id")) for row in fact_rows]
        allowed_fragment_refs = list(plan["references"]["retrieval_fragment_refs"])
        allowed_fact_refs = list(plan["references"]["precise_fact_refs"])
        if (
            fragment_refs != allowed_fragment_refs
            or fact_refs != allowed_fact_refs
            or len(fragment_refs) != len(set(fragment_refs))
            or len(fact_refs) != len(set(fact_refs))
        ):
            raise PlanMaterialAccessDenied("PLAN_REFERENCE_SET_MISMATCH")
        return {
            "object_type": "EPHEMERAL_AUTHOR_MATERIAL_PROJECTION",
            "composition_plan_ref": composition_plan_ref,
            "trusted_scope_ref": source["trusted_scope_ref"],
            "resolved_scope": copy.deepcopy(scope),
            "retrieval_fragment_refs": allowed_fragment_refs,
            "precise_fact_refs": allowed_fact_refs,
            "scoped_retrieval_fragments": copy.deepcopy(fragment_rows),
            "verified_precise_facts": copy.deepcopy(fact_rows),
            "editable": False,
            "persisted": False,
            "context_bundle_created": False,
            "fact_truth_source_created": False,
        }

    def validate_candidate(
        self,
        composition_plan_ref: str,
        access: object,
        candidate: Mapping[str, Any],
        *,
        actually_used_fact_refs: tuple[str, ...],
        actually_used_material_refs: tuple[str, ...],
        evaluation_at: str,
    ) -> JsonObject:
        """Delegate structural candidate validation to Package 2 unchanged."""

        record, source, _ = self._plan_record_for_access(composition_plan_ref, access)
        context = self._trusted_context(source)
        validation_request: JsonObject = {
            "api_version": "v1",
            "request_id": f"VALIDATE-{digest_object(candidate)[:16].upper()}",
            "trusted_scope_ref": source["trusted_scope_ref"],
            "trusted_scope": copy.deepcopy(source["trusted_scope"]),
            "composition_plan_ref": composition_plan_ref,
            "candidate": copy_mapping(candidate),
            "actually_used_fact_refs": list(actually_used_fact_refs),
            "actually_used_material_refs": list(actually_used_material_refs),
        }
        if record.plan["composition_plan_ref"] != composition_plan_ref:
            raise PlanMaterialAccessDenied("PLAN_REFERENCE_STALE")
        self._entrypoint_calls["package2_validate"] += 1
        return cast(
            JsonObject,
            self.expression_service.validate(
                validation_request,
                context,
                parse_time(evaluation_at),
            ),
        )

    def _build_prepare_request(
        self,
        task: ServerConfirmedProductionTask,
        retrieval: JsonObject,
    ) -> JsonObject:
        scope = copy_mapping(retrieval["resolved_scope"])
        expression_partition = copy_mapping(
            retrieval["expression_candidate_partition"]
        )
        expression_profile = self._resolve_expression_profile(task, retrieval)
        return {
            "api_version": "v1",
            "request_id": task.request_id,
            "trusted_scope_ref": retrieval["trusted_scope_ref"],
            "trusted_scope": scope,
            "acting_role_id": task.acting_role_id,
            "confirmed_requirement": copy_mapping(task.confirmed_requirement),
            "confirmation_evidence": copy_mapping(task.confirmation_evidence),
            "scoped_retrieval_fragments": copy.deepcopy(
                retrieval["scoped_retrieval_fragments"]
            ),
            "verified_precise_facts": copy.deepcopy(
                retrieval["verified_precise_facts"]
            ),
            "server_expression_profile": expression_profile,
            "requested_high_level_mode_refs": copy.deepcopy(
                expression_partition["requested_high_level_mode_refs"]
            ),
            "approved_example_refs": [],
            "client_soft_preferences": copy_mapping(task.client_soft_preferences),
            "output_requirements": copy_mapping(task.output_requirements),
            "evaluation_rules": {
                "hard_check_categories": list(
                    self.expression_service.hard_categories
                ),
                "soft_evaluation_tasks": list(self.expression_service.soft_tasks),
            },
            "experimental_diagnostics": copy_mapping(
                task.experimental_diagnostics
            ),
        }

    def _trusted_context(self, request: JsonObject) -> TrustedUpstreamContext:
        if self._trusted_context_factory is not None:
            return self._trusted_context_factory(copy.deepcopy(request))
        return TrustedUpstreamContext.from_simulation_identity(
            self.identity_path,
            (copy.deepcopy(request["confirmed_requirement"]),),
            tuple(copy.deepcopy(request["scoped_retrieval_fragments"])),
            tuple(copy.deepcopy(request["verified_precise_facts"])),
        )

    def _resolve_expression_profile(
        self,
        task: ServerConfirmedProductionTask,
        retrieval: JsonObject,
    ) -> JsonObject:
        if self._expression_profile_resolver is not None:
            return copy.deepcopy(self._expression_profile_resolver(task, retrieval))
        scope = copy_mapping(retrieval["resolved_scope"])
        profile_ref = str(self.expression_service.neutral_profile["profile_ref"])
        return {
            "resolution_authority": "SERVER_TRUSTED_UPSTREAM",
            "requested_profile_ref": None,
            "resolved_profile_ref": profile_ref,
            "resolution_mode": NEUTRAL_PROFILE_MODE,
            "tenant_id": scope["tenant_id"],
            "content_account_id": scope["content_account_id"],
        }

    def _plan_record_for_access(
        self,
        composition_plan_ref: str,
        access: object,
    ) -> tuple[Any, JsonObject, JsonObject]:
        if (
            not isinstance(access, ServerPlanAccess)
            or access.authority_source != SERVER_ACCESS_AUTHORITY
        ):
            raise PlanMaterialAccessDenied("SERVER_SCOPE_REQUIRED")
        try:
            current_scope = self.retrieval_service.authority.resolve_scope(
                access.principal_id, access.content_account_id
            )
        except RetrievalContractError as exc:
            raise PlanMaterialAccessDenied("CURRENT_SCOPE_INVALID") from exc
        record = self.expression_service.store.get(composition_plan_ref)
        if record is None:
            raise PlanMaterialAccessDenied("PLAN_REFERENCE_NOT_ACTIVE")
        source = copy.deepcopy(record.source_request)
        source_scope = source.get("trusted_scope")
        if not isinstance(source_scope, dict):
            raise PlanMaterialAccessDenied("PLAN_SOURCE_INVALID")
        expected_scope = {
            "tenant_id": current_scope.tenant_id,
            "brand_id": current_scope.brand_id,
            "organization_id": current_scope.organization_id,
            "store_id": current_scope.store_id,
            "login_principal_id": current_scope.principal_id,
            "content_account_id": current_scope.content_account_id,
        }
        expected_ref = current_scope.scope_ref
        plan = record.plan
        if (
            source_scope != expected_scope
            or source.get("trusted_scope_ref") != expected_ref
            or plan.get("tenant_id") != current_scope.tenant_id
            or plan.get("organization_id") != current_scope.organization_id
            or plan.get("content_account_id") != current_scope.content_account_id
            or plan.get("composition_plan_ref") != composition_plan_ref
        ):
            raise PlanMaterialAccessDenied("PLAN_SCOPE_MISMATCH")
        return record, source, expected_scope

    @staticmethod
    def _object_rows(value: object, error_code: str) -> list[JsonObject]:
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            raise PlanMaterialAccessDenied(error_code)
        return [copy.deepcopy(row) for row in value]

    def _guard_action_card(
        self,
        request: JsonObject,
        reason: str,
        refs: list[str],
        *,
        action_type: str = "BLOCK",
    ) -> JsonObject:
        # Package 2 owns the action-card materializer; this adapter does not copy it.
        return cast(
            JsonObject,
            self.expression_service.action_card(request, action_type, reason, refs),
        )

    def _append_record(
        self,
        task: ServerConfirmedProductionTask,
        retrieval: JsonObject | None,
        result: JsonObject,
        *,
        package_5_called: bool,
        package_2_called: bool,
    ) -> None:
        requirement = copy_mapping(task.confirmed_requirement)
        fragment_refs = [] if retrieval is None else [
            str(row["fragment_id"])
            for row in retrieval["scoped_retrieval_fragments"]
        ]
        fact_refs = [] if retrieval is None else [
            str(row["fact_id"]) for row in retrieval["verified_precise_facts"]
        ]
        plan_ref = result.get("composition_plan_ref")
        result_ref = plan_ref or result.get("action_card_id")
        seed = {
            "request_id": task.request_id,
            "data_version_digest": (
                None if retrieval is None else retrieval["data_version_digest"]
            ),
            "query_at": None if retrieval is None else retrieval["query_at"],
            "result_ref": result_ref,
            "result_digest": digest_plan_object(result),
        }
        record: JsonObject = {
            "object_type": "FACT_AWARE_PLAN_INTEGRATION_RUN_RECORD",
            "record_id": f"PKG6-RUN-{digest_object(seed)[:16].upper()}",
            "request_id": task.request_id,
            "server_task_ref": task.server_task_ref,
            "requirement_id": requirement.get("requirement_id"),
            "requirement_version": requirement.get("requirement_version"),
            "selected_internal_content_product_id": requirement.get(
                "selected_internal_content_product_id"
            ),
            "package5": {
                "entrypoint": "BrandFactRetrievalService.retrieve",
                "called": package_5_called,
                "data_version_digest": (
                    None if retrieval is None else retrieval["data_version_digest"]
                ),
                "query_at": None if retrieval is None else retrieval["query_at"],
                "result_digest": (
                    None if retrieval is None else digest_retrieval_object(retrieval)
                ),
                "retrieval_fragment_refs": fragment_refs,
                "precise_fact_refs": fact_refs,
                "gap_codes": []
                if retrieval is None
                else [str(row["code"]) for row in retrieval["gaps"]],
                "hold_or_internal_exclusion_records_consumed": False,
            },
            "package2": {
                "entrypoint": "LightExpressionService.prepare",
                "called": package_2_called,
                "business_result_type": result.get("object_type"),
                "business_result_ref": result_ref,
                "business_result_digest": digest_plan_object(result),
                "approved_example_refs": [],
                "second_plan_or_context_created": False,
            },
            "external_call_count": 0,
        }
        record["record_digest"] = digest_object(record)
        self._integration_records.append(record)


__all__ = [
    "FactAwarePlanAdapter",
    "PlanMaterialAccessDenied",
    "SERVER_ACCESS_AUTHORITY",
    "SERVER_TASK_AUTHORITY",
    "START_CREATION",
    "ServerConfirmedProductionTask",
    "ServerPlanAccess",
]
