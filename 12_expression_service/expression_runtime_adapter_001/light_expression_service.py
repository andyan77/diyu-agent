#!/usr/bin/env python3
"""Deterministic light-expression preparation and candidate validation core."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
FOUNDATION_ROOT = REPOSITORY_ROOT / "11_product_foundation/public_foundation_001"
PUBLIC_CONTRACT_PATH = FOUNDATION_ROOT / "contract/public_foundation_contract.v1.yaml"
SIMULATION_IDENTITY_PATH = FOUNDATION_ROOT / "identity/simulation_tenant.v1.yaml"
TOPIC_MAPPING_PATH = FOUNDATION_ROOT / "taxonomy/topic_product_mapping.v1.yaml"
NEUTRAL_PROFILE_PATH = PACKAGE_ROOT / "neutral_expression_profile.v1.yaml"
SERVICE_MANIFEST_PATH = PACKAGE_ROOT / "service_manifest.v1.yaml"

PREPARE_FIELDS = frozenset(
    {
        "api_version",
        "request_id",
        "trusted_scope_ref",
        "trusted_scope",
        "acting_role_id",
        "confirmed_requirement",
        "confirmation_evidence",
        "scoped_retrieval_fragments",
        "verified_precise_facts",
        "server_expression_profile",
        "requested_high_level_mode_refs",
        "approved_example_refs",
        "client_soft_preferences",
        "output_requirements",
        "evaluation_rules",
        "experimental_diagnostics",
    }
)
VALIDATE_FIELDS = frozenset(
    {
        "api_version",
        "request_id",
        "trusted_scope_ref",
        "trusted_scope",
        "composition_plan_ref",
        "candidate",
        "actually_used_fact_refs",
        "actually_used_material_refs",
    }
)
REQUIRED_PREPARE_FIELDS = frozenset(
    {
        "api_version",
        "request_id",
        "trusted_scope_ref",
        "trusted_scope",
        "acting_role_id",
        "confirmed_requirement",
        "confirmation_evidence",
        "scoped_retrieval_fragments",
        "verified_precise_facts",
        "server_expression_profile",
        "output_requirements",
    }
)
REQUIRED_VALIDATE_FIELDS = frozenset(VALIDATE_FIELDS)
REQUIRED_SCOPE_FIELDS = frozenset(
    {
        "tenant_id",
        "brand_id",
        "organization_id",
        "store_id",
        "login_principal_id",
        "content_account_id",
    }
)
REQUIRED_REQUIREMENT_FIELDS = frozenset(
    {
        "requirement_id",
        "requirement_version",
        "status",
        "plain_language_summary",
        "tenant_id",
        "content_account_id",
        "topic_category_id",
        "target_platform",
        "confirmed_by_principal_id",
        "confirmed_at",
    }
)
REQUIRED_ROUTING_REQUIREMENT_FIELDS = frozenset(
    {
        "selected_internal_content_product_id",
        "primary_audience",
        "required_precise_fact_kinds",
    }
)
REQUIRED_CONFIRMATION_FIELDS = frozenset(
    {
        "confirmed_by_principal_id",
        "confirmed_by_role_ids",
        "confirmation_scope",
        "authorization_refs",
        "subject_confirmation_ref",
    }
)
REQUIRED_FRAGMENT_FIELDS = frozenset(
    {
        "fragment_id",
        "tenant_id",
        "brand_id",
        "source_organization_id",
        "source_store_id",
        "source_ref",
        "applicable_organization_ids",
        "applicable_store_ids",
        "applicable_content_account_ids",
        "observed_at",
        "valid_until",
        "authorization_ref",
        "authorization_state",
        "disclosure_scope",
        "status",
    }
)
REQUIRED_FACT_FIELDS = frozenset(
    {
        "fact_id",
        "tenant_id",
        "brand_id",
        "organization_id",
        "store_id",
        "applicable_content_account_ids",
        "fact_kind",
        "value",
        "source_ref",
        "effective_at",
        "valid_until",
        "authorization_ref",
        "disclosure_scope",
        "status",
    }
)
ALLOWED_FACT_KINDS = frozenset(
    {"SKU", "SPECIFICATION", "PRICE", "STOCK", "TIME_POINT", "AUTHORIZATION", "REVOCATION"}
)
ALLOWED_SOFT_PREFERENCE_FIELDS = frozenset(
    {"rhythm", "emotional_intensity", "narrative_entry", "visual_focus", "ending_tendency"}
)
FORBIDDEN_CLIENT_OVERRIDE_FIELDS = frozenset(
    {
        "hard_prohibitions",
        "prohibited_expression_categories",
        "facts",
        "authorization",
        "privacy",
        "trusted_scope",
        "server_expression_profile",
    }
)
ALLOWED_SURFACE_FIELDS = frozenset(
    {"title", "body", "spoken_lines", "CTA", "execution_payload", "surface_units"}
)
ALLOWED_CANDIDATE_FIELDS = frozenset(
    {"candidate_id", "candidate_version", "candidate_user_visible_surfaces"}
)
HIDDEN_SURFACE_KEYS = frozenset(
    {
        "tenant_id",
        "brand_id",
        "organization_id",
        "store_id",
        "login_principal_id",
        "content_account_id",
        "authorization_ref",
        "source_ref",
        "fact_id",
        "fragment_id",
        "requirement_id",
        "plan_id",
        "trusted_scope",
        "trusted_scope_ref",
        "content_product_id",
        "component_id",
        "route_code",
        "raw_error_code",
        "internal_route_id",
        "simulation_only",
        "publish_allowed",
    }
)
PROHIBITED_SURFACE_PATTERN = re.compile(
    r"(?:(?<![A-Z0-9])CP\d{2}(?!\d)|(?<![A-Z0-9])(?:BNO|BRV|VGA|BCL|FC)-\d{2}(?!\d)|"
    r"(?<![A-Z0-9])(?:G1V11|RCV2)-[A-Z0-9-]+|(?<![A-Z0-9])E_[A-Z0-9_]+|"
    r"(?<![A-Z0-9])(?:TENANT|BRAND|ORG|STORE|ACCOUNT|AUTH|FACT|FRAGMENT|ROLE|SIM-LOGIN)-[A-Z0-9-]+|"
    r"\b(?:plan|scope|requirement)://[^\s\"']+|"
    r"(?<![A-Z0-9])(?:all_required_inputs_present|required_source_missing|required_fact_missing|"
    r"required_authorization_missing)(?![A-Z0-9_])|\b(?:simulation_only|publish_allowed)\b)",
    re.IGNORECASE,
)
PII_SURFACE_PATTERN = re.compile(
    r"(?:\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|(?<!\d)1[3-9]\d{9}(?!\d)|"
    r"(?<!\d)\d{17}[0-9X](?!\d)|身份证|家庭住址|(?:^|[，。；;])住址[:：])",
    re.IGNORECASE,
)


def canonical_json(value: Any) -> str:
    """Return one stable serialization for identifiers and comparisons."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> JsonObject:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return payload


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("time must be a non-empty ISO-8601 string")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("time must include an offset")
    return parsed.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def require_mapping(value: Any, name: str) -> JsonObject:
    if not isinstance(value, dict):
        raise PreparationIssue("BLOCK", f"{name}格式不完整，暂不能继续。", [name])
    return value


def require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise PreparationIssue("BLOCK", f"{name}格式不完整，暂不能继续。", [name])
    return value


def require_fields(value: JsonObject, required: frozenset[str], name: str) -> None:
    missing = sorted(required - value.keys())
    if missing:
        raise PreparationIssue("BLOCK", f"{name}缺少必要信息，暂不能继续。", missing)


@dataclass(frozen=True)
class ConfirmationRoute:
    scope: str
    confirmer_role_ids: tuple[str, ...]
    approval_mode: str
    subject_confirmation_required: bool


@dataclass(frozen=True)
class AccountAuthority:
    account_id: str
    organization_id: str
    store_id: str | None
    maker_role_ids: tuple[str, ...]
    confirmation_routes: tuple[ConfirmationRoute, ...]


@dataclass(frozen=True)
class TrustedUpstreamContext:
    """Server-owned authority that cannot be constructed from request labels."""

    tenant_id: str
    brand_id: str
    login_principal_id: str
    accounts: dict[str, AccountAuthority]
    authorization_grants: dict[str, JsonObject]
    subject_confirmations: dict[str, JsonObject]
    trusted_requirement_digests: frozenset[str]
    trusted_fragment_digests: frozenset[str]
    trusted_fact_digests: frozenset[str]
    simulation_only: bool
    publish_allowed: bool
    source_digest: str

    @classmethod
    def from_simulation_identity(
        cls,
        path: Path = SIMULATION_IDENTITY_PATH,
        trusted_requirements: tuple[JsonObject, ...] = (),
        trusted_fragments: tuple[JsonObject, ...] = (),
        trusted_facts: tuple[JsonObject, ...] = (),
    ) -> TrustedUpstreamContext:
        raw = load_yaml(path)["simulation_tenant"]
        tenant = require_mapping(raw.get("tenant"), "simulation tenant")
        principal_rows = require_list(raw.get("login_principals"), "login principals")
        if len(principal_rows) != 1:
            raise ValueError("The local simulation must expose exactly one server-owned principal")
        principal = require_mapping(principal_rows[0], "simulation principal")
        allowed_accounts = set(require_list(principal.get("allowed_content_account_ids"), "allowed accounts"))
        accounts: dict[str, AccountAuthority] = {}
        for item in require_list(raw.get("content_accounts"), "content accounts"):
            account = require_mapping(item, "content account")
            account_id = str(account.get("account_id"))
            if account_id not in allowed_accounts:
                continue
            routes = tuple(
                ConfirmationRoute(
                    scope=str(route["scope"]),
                    confirmer_role_ids=tuple(str(value) for value in route["confirmer_role_ids"]),
                    approval_mode=str(route["approval_mode"]),
                    subject_confirmation_required=bool(route["subject_confirmation_required"]),
                )
                for route in account.get("confirmation_routes", [])
            )
            accounts[account_id] = AccountAuthority(
                account_id=account_id,
                organization_id=str(account["organization_id"]),
                store_id=account.get("store_id"),
                maker_role_ids=tuple(str(value) for value in account.get("maker_role_ids", [])),
                confirmation_routes=routes,
            )
        grants = {
            str(item["authorization_id"]): copy.deepcopy(item)
            for item in require_list(raw.get("authorization_grants"), "authorization grants")
        }
        confirmations = {
            str(item["subject_confirmation_id"]): copy.deepcopy(item)
            for item in require_list(raw.get("subject_confirmation_records"), "subject confirmations")
        }
        return cls(
            tenant_id=str(tenant["tenant_id"]),
            brand_id=str(tenant["brand_id"]),
            login_principal_id=str(principal["principal_id"]),
            accounts=accounts,
            authorization_grants=grants,
            subject_confirmations=confirmations,
            trusted_requirement_digests=frozenset(digest_object(item) for item in trusted_requirements),
            trusted_fragment_digests=frozenset(digest_object(item) for item in trusted_fragments),
            trusted_fact_digests=frozenset(digest_object(item) for item in trusted_facts),
            simulation_only=bool(tenant["simulation_only"]),
            publish_allowed=bool(tenant["publish_allowed"]),
            source_digest=hashlib.sha256(path.read_bytes()).hexdigest(),
        )


class PreparationIssue(Exception):
    def __init__(self, action_type: str, reason: str, refs: list[str] | None = None) -> None:
        super().__init__(reason)
        self.action_type = action_type
        self.reason = reason
        self.refs = refs or []


@dataclass
class PlanRecord:
    key: tuple[str, str, str, int]
    input_digest: str
    plan: JsonObject
    source_request: JsonObject


class InMemoryPlanStore:
    """One-process store for the non-production vertical slice."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str, str, int], PlanRecord] = {}
        self._by_ref: dict[str, PlanRecord] = {}
        self._lock = threading.RLock()

    def materialize(
        self,
        key: tuple[str, str, str, int],
        input_digest: str,
        factory: Any,
    ) -> JsonObject:
        with self._lock:
            existing = self._by_key.get(key)
            if existing is not None and existing.input_digest == input_digest:
                return copy.deepcopy(existing.plan)
            revision = 1 if existing is None else int(existing.plan["plan_revision"]) + 1
            plan = factory(revision)
            if existing is not None:
                self._by_ref.pop(str(existing.plan["composition_plan_ref"]), None)
            record = PlanRecord(key, input_digest, copy.deepcopy(plan), {})
            self._by_key[key] = record
            self._by_ref[str(plan["composition_plan_ref"])] = record
            return copy.deepcopy(plan)

    def attach_source(self, plan_ref: str, source_request: JsonObject) -> None:
        with self._lock:
            record = self._by_ref[plan_ref]
            record.source_request = copy.deepcopy(source_request)

    def get(self, plan_ref: str) -> PlanRecord | None:
        with self._lock:
            return self._by_ref.get(plan_ref)


class LightExpressionService:
    """Public-contract implementation without model, database, or Dify calls."""

    def __init__(self, repository_root: Path = REPOSITORY_ROOT) -> None:
        self.repository_root = repository_root
        foundation = repository_root / "11_product_foundation/public_foundation_001"
        self.contract_path = foundation / "contract/public_foundation_contract.v1.yaml"
        self.topic_path = foundation / "taxonomy/topic_product_mapping.v1.yaml"
        self.profile_path = repository_root / NEUTRAL_PROFILE_PATH.relative_to(REPOSITORY_ROOT)
        self.contract = load_yaml(self.contract_path)["public_foundation_contract"]
        self.topic_mapping = load_yaml(self.topic_path)["topic_product_mapping"]
        self.neutral_profile = load_yaml(self.profile_path)["neutral_expression_profile"]
        self.service_manifest = load_yaml(SERVICE_MANIFEST_PATH)["light_expression_service_manifest"]
        expression = self.contract["light_expression_contract"]
        self.allowed_modes = frozenset(
            str(row["mode_ref"]) for row in expression["high_level_modes"]
        )
        self.hard_categories = tuple(str(value) for value in expression["hard_check_categories"])
        self.soft_tasks = tuple(str(value) for value in expression["soft_evaluation_tasks"])
        self.topic_products = {
            str(row["topic_category_id"]): tuple(str(value) for value in row["internal_product_ids"])
            for row in self.topic_mapping["categories"]
        }
        self.store = InMemoryPlanStore()

    def local_simulation_request(self) -> JsonObject:
        """Return the public example with the package-owned confirmed-task extension."""

        prepare_api = require_mapping(next(
            row
            for row in self.contract["api_contracts"]
            if row.get("method") == "POST" and row.get("path") == "/v1/content/prepare"
        ), "本地模拟准备合同")
        request = copy.deepcopy(require_mapping(prepare_api["request_example"], "本地模拟准备请求"))
        requirement = require_mapping(request["confirmed_requirement"], "本地模拟确认任务")
        extension = require_mapping(
            self.service_manifest["confirmed_requirement_extension"],
            "确认任务扩展",
        )
        values = require_mapping(extension["local_simulation_values"], "本地模拟任务扩展值")
        requirement.update(copy.deepcopy(values))
        return request

    def local_simulation_context(self) -> TrustedUpstreamContext:
        """Build the explicit local server context from registered public fixture evidence."""

        request = self.local_simulation_request()
        return TrustedUpstreamContext.from_simulation_identity(
            self.repository_root / SIMULATION_IDENTITY_PATH.relative_to(REPOSITORY_ROOT),
            (copy.deepcopy(request["confirmed_requirement"]),),
            tuple(copy.deepcopy(request["scoped_retrieval_fragments"])),
            tuple(copy.deepcopy(request["verified_precise_facts"])),
        )

    def readiness(self) -> JsonObject:
        loaded = all(path.is_file() for path in (self.contract_path, self.topic_path, self.profile_path))
        return {
            "object_type": "LOCAL_INTERFACE_READINESS",
            "ready": loaded,
            "scope": "LOCAL_STATIC_CONTRACTS_ONLY",
            "global_readiness_changed": False,
            "DIFY_ready": False,
            "production_ready": False,
        }

    def prepare(
        self,
        request: JsonObject,
        trusted_context: TrustedUpstreamContext | None,
        evaluation_time: datetime | None = None,
    ) -> JsonObject:
        try:
            if trusted_context is None:
                raise PreparationIssue(
                    "BLOCK",
                    "缺少服务端确认的身份和企业范围，不能依据请求中的自我声明继续。",
                    ["server_confirmed_scope"],
                )
            now = evaluation_time or utc_now()
            self._validate_top_level(request, PREPARE_FIELDS, REQUIRED_PREPARE_FIELDS, "准备请求")
            self._validate_scope(request, trusted_context)
            account = self._validate_requirement_and_confirmation(request, trusted_context, now)
            profile = self._resolve_profile(request, trusted_context)
            modes, soft_preferences, expression_warnings = self._validate_expression_hints(request)
            output_requirements = self._validate_output_and_evaluation(request)
            fragments = self._validate_fragments(request, trusted_context, account, now)
            facts = self._validate_facts(request, trusted_context, account, now)
            requirement = require_mapping(request["confirmed_requirement"], "确认任务书")
            required_fact_kinds = set(
                self._string_list(requirement["required_precise_fact_kinds"], "所需精确事实类型")
            )
            available_fact_kinds = {str(item["fact_kind"]) for item in facts}
            missing_fact_kinds = sorted(required_fact_kinds - available_fact_kinds)
            if missing_fact_kinds:
                raise PreparationIssue(
                    "COLLECT_FACT",
                    "已确认任务需要的精确事实尚未齐全，请先补充对应事实。",
                    missing_fact_kinds,
                )
            if not fragments and not facts:
                raise PreparationIssue(
                    "COLLECT_MATERIAL",
                    "当前没有可追溯的叙事资料或精确事实，请先补充材料。",
                    ["scoped_retrieval_fragments", "verified_precise_facts"],
                )
            return self._materialize_plan(
                request,
                trusted_context,
                profile,
                modes,
                soft_preferences,
                expression_warnings,
                output_requirements,
                fragments,
                facts,
            )
        except PreparationIssue as issue:
            return self._action_card(request, issue)
        except (KeyError, TypeError, ValueError):
            return self._action_card(
                request,
                PreparationIssue("BLOCK", "输入格式或时间信息无效，暂不能继续。", []),
            )

    def validate(
        self,
        request: JsonObject,
        trusted_context: TrustedUpstreamContext | None,
        evaluation_time: datetime | None = None,
    ) -> JsonObject:
        if trusted_context is None:
            return self._validation_block(
                request,
                "缺少服务端确认的身份和企业范围，不能依据请求中的自我声明校验。",
                "trusted_scope",
            )
        try:
            now = evaluation_time or utc_now()
            self._validate_top_level(request, VALIDATE_FIELDS, REQUIRED_VALIDATE_FIELDS, "校验请求")
            self._validate_scope(request, trusted_context)
            plan_ref = str(request["composition_plan_ref"])
            record = self.store.get(plan_ref)
            if record is None:
                return self._validation_block(request, "找不到当前进程内对应的有效计划。", "plan_consistency")
            plan = record.plan
            scope = require_mapping(request["trusted_scope"], "可信范围")
            if (
                plan["tenant_id"] != scope["tenant_id"]
                or plan["organization_id"] != scope["organization_id"]
                or plan["content_account_id"] != scope["content_account_id"]
            ):
                return self._validation_block(request, "计划与当前企业或账号范围不一致。", "trusted_scope")
            source = record.source_request
            account = trusted_context.accounts[str(scope["content_account_id"])]
            self._validate_fragments(source, trusted_context, account, now)
            self._validate_facts(source, trusted_context, account, now)
            hard_issues: list[JsonObject] = []
            revise_reasons: list[str] = []
            candidate = require_mapping(request["candidate"], "候选")
            unknown_candidate = sorted(candidate.keys() - ALLOWED_CANDIDATE_FIELDS)
            missing_candidate = sorted(ALLOWED_CANDIDATE_FIELDS - candidate.keys())
            if unknown_candidate or missing_candidate:
                hard_issues.append(
                    {"category": "internal_identifier_leak", "reason": "候选结构包含未知或缺失字段。"}
                )
            surfaces = require_mapping(candidate.get("candidate_user_visible_surfaces"), "用户可见内容")
            unknown_surfaces = sorted(surfaces.keys() - ALLOWED_SURFACE_FIELDS)
            if unknown_surfaces:
                hard_issues.append(
                    {"category": "internal_identifier_leak", "reason": "用户可见内容包含未批准字段。"}
                )
            if not surfaces or not any(value not in (None, "", [], {}) for value in surfaces.values()):
                revise_reasons.append("候选没有可检查的用户可见内容。")
            required_surfaces = set(plan["output_requirements"]["audience_surface_fields"])
            missing_surfaces = {
                field
                for field in required_surfaces
                if field not in surfaces or surfaces[field] in (None, "", [], {})
            }
            if missing_surfaces:
                revise_reasons.append("候选缺少计划要求的用户可见内容字段。")
            leak = self._find_surface_leak(surfaces)
            if leak is not None:
                hard_issues.append(
                    {"category": "internal_identifier_leak", "reason": "候选包含内部标识或内部状态。"}
                )
            if PII_SURFACE_PATTERN.search(canonical_json(surfaces)):
                hard_issues.append(
                    {"category": "privacy", "reason": "候选包含未经授权的直接联系方式。"}
                )
            fact_refs = self._string_list(request["actually_used_fact_refs"], "实际使用事实引用")
            material_refs = self._string_list(request["actually_used_material_refs"], "实际使用资料引用")
            allowed_facts = set(plan["references"]["precise_fact_refs"])
            allowed_materials = set(plan["references"]["retrieval_fragment_refs"])
            if not set(fact_refs).issubset(allowed_facts):
                hard_issues.append(
                    {"category": "fact_support", "reason": "候选声明使用了计划未授权的事实引用。"}
                )
            if not set(material_refs).issubset(allowed_materials):
                hard_issues.append(
                    {"category": "source_provenance", "reason": "候选声明使用了计划未授权的资料引用。"}
                )
            literal_prohibitions = self.neutral_profile.get("literal_prohibited_phrases", [])
            surface_text = canonical_json(surfaces)
            if any(str(value) and str(value) in surface_text for value in literal_prohibitions):
                hard_issues.append(
                    {"category": "explicit_brand_prohibition", "reason": "候选触发了服务端表达禁区。"}
                )
            if hard_issues:
                decision = "BLOCK"
                semantic_status = "NOT_REACHED"
                reason = "结构化硬边界检查发现问题，候选暂不能继续。"
            elif revise_reasons:
                decision = "REVISE"
                semantic_status = "PENDING_EXTERNAL_REVIEW"
                reason = revise_reasons[0]
            else:
                decision = "PASS"
                semantic_status = "PENDING_EXTERNAL_REVIEW"
                reason = "结构化引用和硬边界检查通过；正文语义事实仍需外部复核。"
            decision_seed = {
                "plan_ref": plan_ref,
                "candidate": candidate,
                "fact_refs": fact_refs,
                "material_refs": material_refs,
                "decision": decision,
            }
            return {
                "object_type": "VALIDATION_DECISION",
                "decision": decision,
                "decision_id": f"DECISION-{digest_object(decision_seed)[:16].upper()}",
                "composition_plan_ref": plan_ref,
                "hard_issues": hard_issues,
                "soft_evaluation_tasks": self._pending_soft_tasks(),
                "semantic_fact_review_status": semantic_status,
                "structured_hard_checks_prove_candidate_semantics": False,
                "actually_used_fact_refs": fact_refs,
                "actually_used_material_refs": material_refs,
                "plain_language_reason": reason,
            }
        except PreparationIssue as issue:
            category = {
                "COLLECT_FACT": "effective_time_and_revocation",
                "COLLECT_MATERIAL": "effective_time_and_revocation",
                "REQUEST_AUTHORIZATION": "authorization",
                "ANONYMIZE": "privacy",
            }.get(issue.action_type, "plan_consistency")
            return self._validation_block(request, issue.reason, category)
        except (KeyError, TypeError, ValueError):
            return self._validation_block(request, "校验输入格式无效，候选暂不能继续。", "plan_consistency")

    def _validate_top_level(
        self,
        request: JsonObject,
        allowed: frozenset[str],
        required: frozenset[str],
        name: str,
    ) -> None:
        if not isinstance(request, dict):
            raise PreparationIssue("BLOCK", f"{name}必须是对象。", [name])
        unknown = sorted(request.keys() - allowed)
        if unknown:
            raise PreparationIssue(
                "BLOCK",
                "请求包含未经合同批准的字段，不能用自我声明提升信任等级。",
                unknown,
            )
        require_fields(request, required, name)
        if request.get("api_version") != "v1":
            raise PreparationIssue("BLOCK", "接口版本不受支持。", ["api_version"])

    def _validate_scope(self, request: JsonObject, context: TrustedUpstreamContext) -> None:
        scope = require_mapping(request.get("trusted_scope"), "可信范围")
        require_fields(scope, REQUIRED_SCOPE_FIELDS, "可信范围")
        account_id = str(scope["content_account_id"])
        account = context.accounts.get(account_id)
        expected_ref = f"scope://{context.tenant_id}/{context.login_principal_id}/{account_id}"
        if (
            scope["tenant_id"] != context.tenant_id
            or scope["brand_id"] != context.brand_id
            or scope["login_principal_id"] != context.login_principal_id
            or account is None
            or scope["organization_id"] != account.organization_id
            or scope["store_id"] != account.store_id
            or request.get("trusted_scope_ref") != expected_ref
        ):
            raise PreparationIssue("BLOCK", "请求范围与服务端确认的企业或账号范围不一致。", ["trusted_scope"])

    def _validate_requirement_and_confirmation(
        self,
        request: JsonObject,
        context: TrustedUpstreamContext,
        now: datetime,
    ) -> AccountAuthority:
        scope = require_mapping(request["trusted_scope"], "可信范围")
        account = context.accounts[str(scope["content_account_id"])]
        requirement = require_mapping(request["confirmed_requirement"], "确认任务书")
        require_fields(requirement, REQUIRED_REQUIREMENT_FIELDS, "确认任务书")
        missing_routing = sorted(REQUIRED_ROUTING_REQUIREMENT_FIELDS - requirement.keys())
        if missing_routing:
            raise PreparationIssue(
                "COLLECT_MATERIAL",
                "已确认任务还缺少明确的内容方向、主要受众或精确事实需求，请补充后再继续。",
                missing_routing,
            )
        if digest_object(requirement) not in context.trusted_requirement_digests:
            raise PreparationIssue(
                "BLOCK",
                "确认任务书没有出现在服务端受信上游登记中。",
                [str(requirement.get("requirement_id", "unresolved"))],
            )
        if requirement["status"] != "CONFIRMED":
            raise PreparationIssue("BLOCK", "任务书尚未由用户确认。", ["confirmed_requirement"])
        if (
            requirement["tenant_id"] != context.tenant_id
            or requirement["content_account_id"] != account.account_id
            or requirement["confirmed_by_principal_id"] != context.login_principal_id
        ):
            raise PreparationIssue("BLOCK", "任务书与当前企业、账号或登录身份不一致。", ["confirmed_requirement"])
        topic_id = str(requirement["topic_category_id"])
        if topic_id not in self.topic_products:
            raise PreparationIssue("BLOCK", "题材入口不在当前公共分类中。", ["topic_category_id"])
        selected_product = str(requirement["selected_internal_content_product_id"])
        if selected_product not in self.topic_products[topic_id]:
            raise PreparationIssue(
                "BLOCK",
                "已确认的内部内容方向不属于当前所选通俗题材。",
                ["selected_internal_content_product_id"],
            )
        if not isinstance(requirement["primary_audience"], str) or not requirement["primary_audience"].strip():
            raise PreparationIssue(
                "COLLECT_MATERIAL",
                "已确认任务还缺少明确的主要受众，请补充后再继续。",
                ["primary_audience"],
            )
        required_fact_kinds = self._string_list(
            requirement["required_precise_fact_kinds"],
            "所需精确事实类型",
        )
        if not set(required_fact_kinds).issubset(ALLOWED_FACT_KINDS):
            raise PreparationIssue(
                "BLOCK",
                "已确认任务包含当前合同不支持的精确事实类型。",
                sorted(set(required_fact_kinds) - ALLOWED_FACT_KINDS),
            )
        if not isinstance(requirement["requirement_version"], int) or requirement["requirement_version"] < 1:
            raise PreparationIssue("BLOCK", "任务书版本无效。", ["requirement_version"])
        if not str(requirement["plain_language_summary"]).strip():
            raise PreparationIssue("BLOCK", "任务目标不能为空。", ["plain_language_summary"])
        acting_role = str(request["acting_role_id"])
        if acting_role not in account.maker_role_ids:
            raise PreparationIssue("BLOCK", "当前岗位无权为这个内容账号准备任务。", [acting_role])
        evidence = require_mapping(request["confirmation_evidence"], "确认记录")
        require_fields(evidence, REQUIRED_CONFIRMATION_FIELDS, "确认记录")
        if evidence["confirmed_by_principal_id"] != context.login_principal_id:
            raise PreparationIssue("BLOCK", "确认记录不属于当前登录身份。", ["confirmed_by_principal_id"])
        route = next(
            (item for item in account.confirmation_routes if item.scope == evidence["confirmation_scope"]),
            None,
        )
        if route is None:
            raise PreparationIssue("BLOCK", "当前内容账号没有这类任务的确认路径。", ["confirmation_scope"])
        confirmed_roles = set(self._string_list(evidence["confirmed_by_role_ids"], "确认岗位"))
        required_roles = set(route.confirmer_role_ids)
        approved = required_roles.issubset(confirmed_roles) if route.approval_mode == "ALL_OF" else bool(
            required_roles & confirmed_roles
        )
        if not approved:
            raise PreparationIssue("BLOCK", "任务尚未由所需责任岗位确认。", sorted(required_roles))
        confirmation_refs = self._string_list(evidence["authorization_refs"], "确认授权引用")
        if not confirmation_refs:
            raise PreparationIssue("REQUEST_AUTHORIZATION", "缺少任务确认授权。", ["authorization_refs"])
        if not any(
            self._grant_is_valid(
                context.authorization_grants.get(ref),
                context,
                account,
                now,
                allowed_kinds=frozenset({"REQUIREMENT_CONFIRMATION"}),
                allowed_disclosure_scopes=frozenset({"REQUIREMENT_CONFIRMATION_ONLY"}),
            )
            for ref in confirmation_refs
        ):
            raise PreparationIssue("REQUEST_AUTHORIZATION", "任务确认授权无效或已过期。", confirmation_refs)
        subject_ref = evidence.get("subject_confirmation_ref")
        if route.subject_confirmation_required:
            subject = context.subject_confirmations.get(str(subject_ref)) if subject_ref else None
            if not self._subject_confirmation_is_valid(
                subject,
                context,
                account,
                now,
                route.scope,
            ):
                raise PreparationIssue("ANONYMIZE", "人物观点尚无有效本人确认，请补确认或改为匿名表达。", [str(subject_ref)])
        return account

    def _resolve_profile(self, request: JsonObject, context: TrustedUpstreamContext) -> JsonObject:
        scope = require_mapping(request["trusted_scope"], "可信范围")
        supplied = require_mapping(request["server_expression_profile"], "服务端表达配置")
        required = {
            "resolution_authority",
            "requested_profile_ref",
            "resolved_profile_ref",
            "resolution_mode",
            "tenant_id",
            "content_account_id",
        }
        if not required.issubset(supplied):
            raise PreparationIssue("BLOCK", "服务端表达配置封装不完整。", sorted(required - supplied.keys()))
        if supplied["resolution_authority"] != "SERVER_TRUSTED_UPSTREAM":
            raise PreparationIssue("BLOCK", "表达配置必须由服务端解析。", ["resolution_authority"])
        if supplied["tenant_id"] != context.tenant_id or supplied["content_account_id"] != scope["content_account_id"]:
            raise PreparationIssue("BLOCK", "表达配置与当前企业或账号不一致。", ["server_expression_profile"])
        if (
            supplied["resolved_profile_ref"] != self.neutral_profile["profile_ref"]
            or supplied["resolution_mode"] != "NEUTRAL_DEFAULT"
            or supplied["requested_profile_ref"] not in (None, self.neutral_profile["profile_ref"])
        ):
            raise PreparationIssue("BLOCK", "企业专属表达配置尚未由后续品牌模块载入。", ["resolved_profile_ref"])
        return copy.deepcopy(self.neutral_profile)

    def _validate_expression_hints(self, request: JsonObject) -> tuple[list[str], JsonObject, list[str]]:
        modes = self._string_list(request.get("requested_high_level_mode_refs", []), "高层表达模式")
        accepted_modes = [mode for mode in modes if mode in self.allowed_modes]
        unknown_modes = sorted(set(modes) - self.allowed_modes)
        examples = self._string_list(request.get("approved_example_refs", []), "示例引用")
        if any(not value.startswith("example://") for value in examples):
            raise PreparationIssue("BLOCK", "示例引用格式无效。", examples)
        soft = require_mapping(request.get("client_soft_preferences", {}), "临时软偏好")
        unknown_soft = sorted(soft.keys() - ALLOWED_SOFT_PREFERENCE_FIELDS)
        forbidden_overrides = sorted(set(unknown_soft) & FORBIDDEN_CLIENT_OVERRIDE_FIELDS)
        if forbidden_overrides:
            raise PreparationIssue("BLOCK", "临时偏好不能修改服务端硬禁区。", forbidden_overrides)
        accepted_soft = {
            key: copy.deepcopy(value)
            for key, value in soft.items()
            if key in ALLOWED_SOFT_PREFERENCE_FIELDS
        }
        warnings: list[str] = []
        if unknown_modes:
            warnings.append("未知高层表达模式已忽略，不影响事实、授权或范围。")
        if unknown_soft:
            warnings.append("未知临时软偏好已忽略，不影响服务端硬保护。")
        diagnostics = require_mapping(request.get("experimental_diagnostics", {}), "实验诊断")
        allowed_diagnostic = {
            "expression_baseline_ref",
            "component_refs",
            "control_rule_refs",
            "edge_refs",
            "structural_path_ref",
        }
        if set(diagnostics) - allowed_diagnostic:
            raise PreparationIssue("BLOCK", "实验诊断包含未知字段。", sorted(set(diagnostics) - allowed_diagnostic))
        return accepted_modes, accepted_soft, warnings

    def _validate_output_and_evaluation(self, request: JsonObject) -> JsonObject:
        output = require_mapping(request["output_requirements"], "输出要求")
        required = {"target_platform", "required_candidate_count", "audience_surface_fields"}
        if not required.issubset(output):
            raise PreparationIssue("BLOCK", "输出要求不完整。", sorted(required - output.keys()))
        count = output["required_candidate_count"]
        if not isinstance(count, int) or not 2 <= count <= 3:
            raise PreparationIssue("BLOCK", "候选数量必须为2至3个。", ["required_candidate_count"])
        fields = self._string_list(output["audience_surface_fields"], "用户可见字段")
        if not fields or not set(fields).issubset(ALLOWED_SURFACE_FIELDS):
            raise PreparationIssue("BLOCK", "输出包含未知的用户可见字段。", fields)
        supplied_rules = request.get("evaluation_rules")
        if supplied_rules is not None:
            rules = require_mapping(supplied_rules, "评审规则")
            hard = self._string_list(rules.get("hard_check_categories"), "硬检查类别")
            soft = self._string_list(rules.get("soft_evaluation_tasks"), "软评价任务")
            if tuple(hard) != self.hard_categories or tuple(soft) != self.soft_tasks:
                raise PreparationIssue("BLOCK", "调用方不得删除或改写服务端评审规则。", ["evaluation_rules"])
        return copy.deepcopy(output)

    def _validate_fragments(
        self,
        request: JsonObject,
        context: TrustedUpstreamContext,
        account: AccountAuthority,
        now: datetime,
    ) -> list[JsonObject]:
        fragments = require_list(request.get("scoped_retrieval_fragments"), "叙事资料")
        validated: list[JsonObject] = []
        for raw in fragments:
            item = require_mapping(raw, "叙事资料")
            require_fields(item, REQUIRED_FRAGMENT_FIELDS, "叙事资料")
            if digest_object(item) not in context.trusted_fragment_digests:
                raise PreparationIssue(
                    "BLOCK",
                    "叙事资料没有出现在服务端受信上游登记中。",
                    [str(item["fragment_id"])],
                )
            if item["status"] != "ACTIVE" or parse_time(item["valid_until"]) < now:
                raise PreparationIssue("COLLECT_MATERIAL", "叙事资料已失效或被撤回。", [str(item["fragment_id"])])
            if parse_time(item["observed_at"]) > now:
                raise PreparationIssue("COLLECT_MATERIAL", "叙事资料的记录时间尚未到达。", [str(item["fragment_id"])])
            grant = context.authorization_grants.get(str(item["authorization_ref"]))
            if item["authorization_state"] != "GRANTED" or not self._grant_is_valid(
                grant,
                context,
                account,
                now,
                allowed_kinds=frozenset({"MATERIAL_AND_FACT_DISCLOSURE"}),
            ):
                raise PreparationIssue("REQUEST_AUTHORIZATION", "叙事资料缺少当前有效授权。", [str(item["fragment_id"])])
            if (
                item["tenant_id"] != context.tenant_id
                or item["brand_id"] != context.brand_id
                or grant is None
                or item["source_organization_id"] != grant["source_organization_id"]
                or item["source_store_id"] != grant["source_store_id"]
                or account.organization_id not in item["applicable_organization_ids"]
                or account.store_id not in item["applicable_store_ids"]
                or account.account_id not in item["applicable_content_account_ids"]
                or item["disclosure_scope"] != grant["disclosure_scope"]
            ):
                raise PreparationIssue("BLOCK", "叙事资料与当前企业、门店或账号范围不一致。", [str(item["fragment_id"])])
            if not str(item["source_ref"]).strip():
                raise PreparationIssue("COLLECT_MATERIAL", "叙事资料缺少可追溯来源。", [str(item["fragment_id"])])
            validated.append(copy.deepcopy(item))
        return validated

    def _validate_facts(
        self,
        request: JsonObject,
        context: TrustedUpstreamContext,
        account: AccountAuthority,
        now: datetime,
    ) -> list[JsonObject]:
        facts = require_list(request.get("verified_precise_facts"), "精确事实")
        validated: list[JsonObject] = []
        for raw in facts:
            item = require_mapping(raw, "精确事实")
            require_fields(item, REQUIRED_FACT_FIELDS, "精确事实")
            if digest_object(item) not in context.trusted_fact_digests:
                raise PreparationIssue(
                    "BLOCK",
                    "精确事实没有出现在服务端受信上游登记中。",
                    [str(item["fact_id"])],
                )
            if item["status"] != "ACTIVE" or parse_time(item["valid_until"]) < now:
                raise PreparationIssue("COLLECT_FACT", "精确事实已失效或被撤回。", [str(item["fact_id"])])
            if parse_time(item["effective_at"]) > now:
                raise PreparationIssue("COLLECT_FACT", "精确事实尚未生效。", [str(item["fact_id"])])
            if item["value"] in (None, "", [], {}):
                raise PreparationIssue("COLLECT_FACT", "精确事实缺少可用值。", [str(item["fact_id"])])
            grant = context.authorization_grants.get(str(item["authorization_ref"]))
            if not self._grant_is_valid(
                grant,
                context,
                account,
                now,
                allowed_kinds=frozenset({"MATERIAL_AND_FACT_DISCLOSURE", "FACT_DISCLOSURE"}),
            ):
                raise PreparationIssue("REQUEST_AUTHORIZATION", "精确事实缺少当前有效授权。", [str(item["fact_id"])])
            if (
                item["tenant_id"] != context.tenant_id
                or item["brand_id"] != context.brand_id
                or grant is None
                or item["organization_id"] != grant["source_organization_id"]
                or item["store_id"] != grant["source_store_id"]
                or account.account_id not in item["applicable_content_account_ids"]
                or item["disclosure_scope"] != grant["disclosure_scope"]
            ):
                raise PreparationIssue("BLOCK", "精确事实与当前企业、门店或账号范围不一致。", [str(item["fact_id"])])
            if item["fact_kind"] not in ALLOWED_FACT_KINDS:
                raise PreparationIssue("BLOCK", "精确事实类型不受支持。", [str(item["fact_id"])])
            if not str(item["source_ref"]).strip():
                raise PreparationIssue("COLLECT_FACT", "精确事实缺少可追溯来源。", [str(item["fact_id"])])
            validated.append(copy.deepcopy(item))
        return validated

    def _grant_is_valid(
        self,
        grant: JsonObject | None,
        context: TrustedUpstreamContext,
        account: AccountAuthority,
        now: datetime,
        allowed_kinds: frozenset[str] | None = None,
        allowed_disclosure_scopes: frozenset[str] | None = None,
    ) -> bool:
        if grant is None or grant.get("status") != "GRANTED":
            return False
        if allowed_kinds is not None and grant.get("authorization_kind") not in allowed_kinds:
            return False
        if (
            allowed_disclosure_scopes is not None
            and grant.get("disclosure_scope") not in allowed_disclosure_scopes
        ):
            return False
        try:
            within_time = parse_time(grant["valid_from"]) <= now <= parse_time(grant["valid_until"])
        except (KeyError, TypeError, ValueError):
            return False
        return bool(
            within_time
            and grant.get("tenant_id") == context.tenant_id
            and grant.get("brand_id") == context.brand_id
            and account.organization_id in grant.get("permitted_organization_ids", [])
            and account.store_id in grant.get("permitted_store_ids", [])
            and account.account_id in grant.get("permitted_content_account_ids", [])
        )

    def _subject_confirmation_is_valid(
        self,
        record: JsonObject | None,
        context: TrustedUpstreamContext,
        account: AccountAuthority,
        now: datetime,
        expected_scope: str,
    ) -> bool:
        if record is None:
            return False
        try:
            return bool(
                record.get("status") == "ACTIVE"
                and record.get("tenant_id") == context.tenant_id
                and record.get("brand_id") == context.brand_id
                and record.get("organization_id") == account.organization_id
                and record.get("store_id") == account.store_id
                and record.get("content_account_id") == account.account_id
                and record.get("confirmation_scope") == expected_scope
                and parse_time(record["confirmed_at"]) <= now
                and parse_time(record["valid_until"]) >= now
            )
        except (KeyError, TypeError, ValueError):
            return False

    def _materialize_plan(
        self,
        request: JsonObject,
        context: TrustedUpstreamContext,
        profile: JsonObject,
        modes: list[str],
        soft_preferences: JsonObject,
        expression_warnings: list[str],
        output: JsonObject,
        fragments: list[JsonObject],
        facts: list[JsonObject],
    ) -> JsonObject:
        scope = request["trusted_scope"]
        requirement = request["confirmed_requirement"]
        key = (
            str(scope["tenant_id"]),
            str(scope["content_account_id"]),
            str(requirement["requirement_id"]),
            int(requirement["requirement_version"]),
        )
        semantic_request = copy.deepcopy(request)
        semantic_request.pop("request_id", None)
        input_digest = digest_object(semantic_request)
        plan_id = f"PLAN-{digest_object(key)[:16].upper()}"
        selected_product = str(requirement["selected_internal_content_product_id"])
        diagnostics = copy.deepcopy(request.get("experimental_diagnostics", {}))
        diagnostic_values: list[str] = []
        for field, value in diagnostics.items():
            if isinstance(value, list):
                diagnostic_values.extend(str(item) for item in value)
            elif value is not None:
                diagnostic_values.append(str(value))
        diagnostic_warnings = list(expression_warnings)
        if diagnostic_values:
            diagnostic_warnings.append("可选实验引用未解析，不影响事实、授权或范围。")

        def factory(revision: int) -> JsonObject:
            composition_ref = f"plan://{plan_id}/revisions/{revision}"
            material_mode = "FULL_MATERIAL" if fragments and facts else (
                "DEGRADED_FACT_ONLY" if facts else "DEGRADED_NARRATIVE_ONLY"
            )
            return {
                "object_type": "LIGHT_CONTENT_PLAN",
                "plan_id": plan_id,
                "plan_revision": revision,
                "composition_plan_ref": composition_ref,
                "tenant_id": scope["tenant_id"],
                "organization_id": scope["organization_id"],
                "content_account_id": scope["content_account_id"],
                "requirement_id": requirement["requirement_id"],
                "requirement_version": requirement["requirement_version"],
                "task_objective": requirement["plain_language_summary"],
                "primary_audience": requirement["primary_audience"],
                "output_requirements": copy.deepcopy(output),
                "candidate_policy": {
                    "required_candidate_count": output["required_candidate_count"],
                    "difference_dimensions": [
                        "narrative_entry",
                        "information_order",
                        "visual_focus",
                        "rhythm",
                        "emotional_intensity",
                        "ending",
                    ],
                    "near_duplicate_rewording_counts_as_distinct": False,
                },
                "expression_guidance": {
                    "brand_expression_profile_ref": profile["profile_ref"],
                    "tone_tendencies": copy.deepcopy(profile["tone_tendencies"]),
                    "prohibited_expression_categories": copy.deepcopy(
                        profile["prohibited_expression_categories"]
                    ),
                    "high_level_mode_refs": modes,
                    "approved_example_refs": copy.deepcopy(request.get("approved_example_refs", [])),
                    "client_soft_preferences": copy.deepcopy(soft_preferences),
                    "material_mode": material_mode,
                    "may_grant_fact_authorization_or_scope": False,
                },
                "hard_check_policy": list(self.hard_categories),
                "soft_evaluation_tasks": self._pending_soft_tasks(),
                "references": {
                    "trusted_scope_ref": request["trusted_scope_ref"],
                    "confirmed_requirement_ref": (
                        f"requirement://{requirement['requirement_id']}/versions/"
                        f"{requirement['requirement_version']}"
                    ),
                    "retrieval_fragment_refs": [item["fragment_id"] for item in fragments],
                    "precise_fact_refs": [item["fact_id"] for item in facts],
                    "brand_expression_profile_ref": profile["profile_ref"],
                    "selected_internal_content_product_id": selected_product,
                    "required_precise_fact_kinds": copy.deepcopy(
                        requirement["required_precise_fact_kinds"]
                    ),
                    "high_level_mode_refs": modes,
                    "approved_example_refs": copy.deepcopy(request.get("approved_example_refs", [])),
                    "experimental_diagnostics": diagnostics,
                },
                "diagnostic_warnings": diagnostic_warnings,
                "authoring_boundary": {
                    "may_add_facts": False,
                    "audience_body_in_plan": False,
                    "semantic_fact_review_status": "PENDING_EXTERNAL_REVIEW",
                },
            }

        plan = self.store.materialize(key, input_digest, factory)
        self.store.attach_source(str(plan["composition_plan_ref"]), request)
        return plan

    def _action_card(self, request: Any, issue: PreparationIssue) -> JsonObject:
        request_map = request if isinstance(request, dict) else {}
        requirement = request_map.get("confirmed_requirement")
        requirement_map = requirement if isinstance(requirement, dict) else {}
        requirement_id = str(requirement_map.get("requirement_id", "unresolved"))
        requirement_version = str(requirement_map.get("requirement_version", "unresolved"))
        seed = {
            "action_type": issue.action_type,
            "reason": issue.reason,
            "refs": issue.refs,
            "requirement_id": requirement_id,
            "requirement_version": requirement_version,
        }
        digest = digest_object(seed)[:16].upper()
        return {
            "object_type": "ACTION_CARD",
            "action_type": issue.action_type,
            "decision_id": f"DECISION-{digest}",
            "action_card_id": f"ACTION-{digest}",
            "plan_key_or_requirement_ref": f"requirement://{requirement_id}/versions/{requirement_version}",
            "plain_language_reason": issue.reason,
            "missing_or_invalid_refs": issue.refs,
            "next_action": self._next_action(issue.action_type),
            "publishable_candidate_included": False,
        }

    def _validation_block(self, request: Any, reason: str, category: str) -> JsonObject:
        request_map = request if isinstance(request, dict) else {}
        plan_ref = str(request_map.get("composition_plan_ref", "plan://unresolved"))
        fact_refs = request_map.get("actually_used_fact_refs", [])
        material_refs = request_map.get("actually_used_material_refs", [])
        if not isinstance(fact_refs, list):
            fact_refs = []
        if not isinstance(material_refs, list):
            material_refs = []
        digest = digest_object({"plan_ref": plan_ref, "reason": reason})[:16].upper()
        return {
            "object_type": "VALIDATION_DECISION",
            "decision": "BLOCK",
            "decision_id": f"DECISION-{digest}",
            "composition_plan_ref": plan_ref,
            "hard_issues": [{"category": category, "reason": reason}],
            "soft_evaluation_tasks": self._pending_soft_tasks(),
            "semantic_fact_review_status": "NOT_REACHED",
            "structured_hard_checks_prove_candidate_semantics": False,
            "actually_used_fact_refs": fact_refs,
            "actually_used_material_refs": material_refs,
            "plain_language_reason": reason,
        }

    def _pending_soft_tasks(self) -> list[JsonObject]:
        return [
            {"task_id": task_id, "status": "PENDING_EXTERNAL_EVALUATION", "score": None}
            for task_id in self.soft_tasks
        ]

    def _find_surface_leak(self, value: Any) -> str | None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).casefold() in HIDDEN_SURFACE_KEYS:
                    return str(key)
                found = self._find_surface_leak(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = self._find_surface_leak(child)
                if found is not None:
                    return found
        elif isinstance(value, str) and PROHIBITED_SURFACE_PATTERN.search(value):
            return value
        return None

    @staticmethod
    def _string_list(value: Any, name: str) -> list[str]:
        values = require_list(value, name)
        if any(not isinstance(item, str) or not item.strip() for item in values):
            raise PreparationIssue("BLOCK", f"{name}必须只包含非空字符串。", [name])
        if len(values) != len(set(values)):
            raise PreparationIssue("BLOCK", f"{name}不能包含重复项。", [name])
        return [str(item) for item in values]

    @staticmethod
    def _next_action(action_type: str) -> str:
        return {
            "COLLECT_FACT": "补充或确认当前有效事实后重新准备。",
            "COLLECT_MATERIAL": "补充可追溯资料后重新准备。",
            "REQUEST_AUTHORIZATION": "取得有效授权后重新准备。",
            "INTERVIEW": "完成采访和本人确认后重新准备。",
            "RESHOOT": "完成所需补拍后重新准备。",
            "ANONYMIZE": "补齐本人确认，或改为不识别具体人物的表达。",
            "DEGRADE": "按当前可用资料缩小表达范围。",
            "BLOCK": "由可信上游修正范围或输入后再试。",
        }.get(action_type, "修正输入后重新准备。")
