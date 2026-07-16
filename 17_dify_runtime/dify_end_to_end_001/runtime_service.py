#!/usr/bin/env python3
"""Thin Package 7 coordinator that reuses Package 6 and Package 2."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from contracts import BridgePrepareRequest, ModelEnvelope, normalize_model_json_text
from persistence import RuntimeRepository, SqlAlchemyPlanStore, digest_object
from runtime_models import RuntimeModelRun
from runtime_retrieval import RuntimeBrandFactRetrievalService


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_2_ROOT = REPOSITORY_ROOT / "12_expression_service/expression_runtime_adapter_001"
PACKAGE_6_ROOT = REPOSITORY_ROOT / "16_composition_runtime/fact_aware_plan_adapter_001"
for root in (PACKAGE_2_ROOT, PACKAGE_6_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from fact_aware_plan_adapter import (  # type: ignore[import-not-found]  # noqa: E402
    FactAwarePlanAdapter,
    SERVER_ACCESS_AUTHORITY,
    SERVER_TASK_AUTHORITY,
    START_CREATION,
    ServerConfirmedProductionTask,
    ServerPlanAccess,
)
from light_expression_service import (  # type: ignore[import-not-found]  # noqa: E402
    AccountAuthority,
    ConfirmationRoute,
    LightExpressionService,
    TrustedUpstreamContext,
    digest_object as digest_plan_object,
)


TOPIC_PATH = REPOSITORY_ROOT / "11_product_foundation/public_foundation_001/taxonomy/topic_product_mapping.v1.yaml"
ACTION_PATH = REPOSITORY_ROOT / "14_dify_shell/dify_content_shell_001/state_action_mapping.v1.json"


class RuntimeContractError(ValueError):
    """Fail-closed runtime error whose raw value is never shown to users."""


class Package7Runtime:
    """Coordinate persistence, retrieval, planning and candidate validation."""

    def __init__(
        self,
        repository: RuntimeRepository,
        plan_store: SqlAlchemyPlanStore,
        retrieval: RuntimeBrandFactRetrievalService,
    ) -> None:
        self.repository = repository
        expression = LightExpressionService(
            REPOSITORY_ROOT,
            plan_store=plan_store,
            expression_profile_resolver=self._resolve_runtime_profile,
        )
        self.adapter = FactAwarePlanAdapter(
            retrieval,
            expression,
            Path("runtime://package7/identity"),
            trusted_context_factory=self._trusted_context,
            expression_profile_resolver=self._expression_profile,
        )
        topic_doc = yaml.safe_load(TOPIC_PATH.read_text(encoding="utf-8"))
        categories = topic_doc["topic_product_mapping"]["categories"]
        self.topic_by_label = {str(row["display_name"]): copy.deepcopy(row) for row in categories}
        self.product_labels = {
            str(row["content_product_id"]): str(row["internal_label"])
            for row in topic_doc["topic_product_mapping"]["internal_products"]
        }
        action_doc = json.loads(ACTION_PATH.read_text(encoding="utf-8"))
        self.action_cards = {str(row["action_type"]): copy.deepcopy(row) for row in action_doc["action_cards"]}
        self.unknown_action = copy.deepcopy(action_doc["unknown_action_behavior"])

    def _trusted_context(self, request: JsonObject) -> TrustedUpstreamContext:
        active = self.repository.setting("active_runtime_brand")
        root = self.repository.setting(str(active["identity_setting_key"]))
        tenant = root["tenant"]
        principal_id = str(request["trusted_scope"]["login_principal_id"])
        principal = next(
            row for row in root["login_principals"] if row["principal_id"] == principal_id
        )
        allowed = set(principal["allowed_content_account_ids"])
        accounts: dict[str, AccountAuthority] = {}
        for raw in root["content_accounts"]:
            if raw["account_id"] not in allowed:
                continue
            routes = tuple(
                ConfirmationRoute(
                    scope=str(route["scope"]),
                    confirmer_role_ids=tuple(str(value) for value in route["confirmer_role_ids"]),
                    approval_mode=str(route["approval_mode"]),
                    subject_confirmation_required=bool(route["subject_confirmation_required"]),
                )
                for route in raw["confirmation_routes"]
            )
            accounts[str(raw["account_id"])] = AccountAuthority(
                account_id=str(raw["account_id"]),
                organization_id=str(raw["organization_id"]),
                store_id=raw.get("store_id"),
                maker_role_ids=tuple(str(value) for value in raw["maker_role_ids"]),
                confirmation_routes=routes,
            )
        return TrustedUpstreamContext(
            tenant_id=str(tenant["tenant_id"]),
            brand_id=str(tenant["brand_id"]),
            login_principal_id=str(principal["principal_id"]),
            accounts=accounts,
            authorization_grants={
                str(row["authorization_id"]): copy.deepcopy(row)
                for row in root["authorization_grants"]
            },
            subject_confirmations={
                str(row["subject_confirmation_id"]): copy.deepcopy(row)
                for row in root["subject_confirmation_records"]
            },
            trusted_requirement_digests=frozenset(
                {digest_plan_object(request["confirmed_requirement"])}
            ),
            trusted_fragment_digests=frozenset(
                digest_plan_object(row) for row in request["scoped_retrieval_fragments"]
            ),
            trusted_fact_digests=frozenset(
                digest_plan_object(row) for row in request["verified_precise_facts"]
            ),
            simulation_only=True,
            publish_allowed=False,
            source_digest=digest_object(root),
        )

    def _expression_profile(
        self,
        task: ServerConfirmedProductionTask,
        retrieval: JsonObject,
    ) -> JsonObject:
        del task
        active = self.repository.setting("active_runtime_brand")
        profile = self.repository.setting(str(active["profile_setting_key"]))
        scope = retrieval["resolved_scope"]
        return {
            "resolution_authority": "SERVER_TRUSTED_UPSTREAM",
            "requested_profile_ref": None,
            "resolved_profile_ref": profile["profile_ref"],
            "resolution_mode": profile["resolution_mode"],
            "tenant_id": scope["tenant_id"],
            "content_account_id": scope["content_account_id"],
        }

    def _resolve_runtime_profile(
        self,
        supplied: JsonObject,
        context: TrustedUpstreamContext,
        neutral_profile: JsonObject,
    ) -> JsonObject:
        active = self.repository.setting("active_runtime_brand")
        if active["tenant_id"] != context.tenant_id:
            return copy.deepcopy(neutral_profile)
        profile = self.repository.setting(str(active["profile_setting_key"]))
        if (
            profile.get("tenant_id") != context.tenant_id
            or profile.get("brand_id") != context.brand_id
            or profile.get("profile_ref") != supplied.get("resolved_profile_ref")
        ):
            raise RuntimeContractError("Brand profile scope mismatch")
        return copy.deepcopy(profile)

    def prepare(self, request: BridgePrepareRequest, principal_id: str) -> JsonObject:
        account = self.repository.account_by_display_name(request.account_display_name)
        if account is None or account.status != "ACTIVE":
            return self._plain_action("BLOCK")
        principal = self.repository.principal_by_id(principal_id)
        if principal is None or account.account_id not in principal.allowed_account_ids:
            return self._plain_action("REQUEST_AUTHORIZATION")

        if request.operation == "普通聊天":
            return self._start_chat_run(request, principal_id, account.account_id, inspiration=False)
        if request.operation == "找灵感":
            return self._start_chat_run(request, principal_id, account.account_id, inspiration=True)
        if request.operation == "确认制作":
            account_payload = {
                **copy.deepcopy(account.payload),
                "tenant_id": account.tenant_id,
                "brand_id": account.brand_id,
                "account_id": account.account_id,
                "organization_id": account.organization_id,
                "store_id": account.store_id,
            }
            return self._prepare_creation(request, principal_id, account_payload)
        if request.operation == "选择候选":
            chosen = self.repository.select_candidate(account.account_id, int(request.candidate_number or 0))
            return {
                "response_kind": "DIRECT",
                "user_visible_text": f"已选择第{chosen.ordinal}份候选。需要时可以继续说想修改哪里。",
            }
        if request.operation == "局部修改":
            return self._prepare_revision(request, principal_id, account.account_id)
        if request.operation == "审核":
            return self._review_selected(account.account_id)
        if request.operation == "导出":
            return self._export_selected(account.account_id)
        if request.operation == "查看来源":
            return self._source_lookup(account.account_id)
        if request.operation == "提交反馈":
            selected = self.repository.selected_candidate(account.account_id)
            context = (
                {}
                if selected is None
                else self.repository.requirement_context_for_run(selected.run_id)
            )
            feedback_id = self.repository.save_feedback(
                principal_id=principal_id,
                account_id=account.account_id,
                candidate_id=None if selected is None else selected.candidate_id,
                requirement_id=(
                    None
                    if selected is None
                    else self.repository.requirement_id_for_run(selected.run_id)
                ),
                role_id=request.speaker_role_id or context.get("speaker_role_id"),
                storyline_id=request.storyline_id or context.get("storyline_id"),
                column_id=request.column_id or context.get("column_id"),
                previous_content_ref=(
                    request.previous_content_ref or context.get("previous_content_ref")
                ),
                fact_refs=[] if selected is None else list(selected.used_fact_refs),
                material_refs=[] if selected is None else list(selected.used_material_refs),
                short_reason=request.message,
            )
            return {
                "response_kind": "DIRECT",
                "user_visible_text": "反馈已记录。这里只保存必要的简短原因。",
                "internal_feedback_ref": feedback_id,
            }
        raise RuntimeContractError("Unknown operation")

    def portal_options(self, principal_id: str) -> JsonObject:
        principal = self.repository.principal_by_id(principal_id)
        if principal is None or principal.status != "ACTIVE":
            raise RuntimeContractError("Unknown portal principal")
        active = self.repository.setting("active_runtime_brand")
        profile = self.repository.setting(str(active["profile_setting_key"]))
        allowed = set(principal.allowed_account_ids)
        accounts = [
            account
            for account in self.repository.all_accounts()
            if account.status == "ACTIVE" and account.account_id in allowed
        ]
        role_cards = {
            str(row["account_id"]): row
            for row in profile.get("account_role_cards", [])
            if isinstance(row, dict) and isinstance(row.get("account_id"), str)
        }
        roles = {
            str(row["role_id"]): row
            for row in profile.get("principal_roles", [])
            if isinstance(row, dict) and isinstance(row.get("role_id"), str)
        }
        return {
            "content_accounts": [account.display_name for account in accounts],
            "roles_by_account": {
                account.display_name: [
                    str(roles[str(role_cards[account.account_id]["default_role_id"])]["display_name"])
                ]
                for account in accounts
                if account.account_id in role_cards
                and str(role_cards[account.account_id].get("default_role_id")) in roles
            },
            "storylines": [str(row["display_name"]) for row in profile.get("storylines", [])],
            "columns_by_storyline": {
                str(storyline["display_name"]): [
                    str(column["display_name"])
                    for column in profile.get("columns", [])
                    if column.get("storyline_id") == storyline.get("storyline_id")
                ]
                for storyline in profile.get("storylines", [])
            },
            "topics": sorted(self.topic_by_label),
            "platforms": ["抖音", "视频号", "小红书", "公众号或图文", "其他"],
            "durations": ["15秒左右", "30秒左右", "60秒左右", "1至3分钟", "由系统建议"],
            "feelings": [
                "真实记录",
                "专业讲明白",
                "生活分享",
                "搭配演示",
                "门店日常",
                "情绪故事",
                "质感画面",
                "由系统建议",
            ],
            "content_formats": ["短视频", "图文", "陈列搭配"],
            "material_kinds": ["一个想法", "一段故事或概要", "商品或活动事实", "图片或视频", "什么都没有"],
            "simulation_only": True,
            "publish_allowed": False,
        }

    def classification_options(self, topic_label: str | None) -> list[JsonObject]:
        topic = self.topic_by_label.get(str(topic_label))
        if topic is None:
            return []
        return [
            {
                "content_product_id": product_id,
                "internal_label": self.product_labels[product_id],
            }
            for product_id in topic["internal_product_ids"]
        ]

    def _start_chat_run(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        account_id: str,
        *,
        inspiration: bool,
    ) -> JsonObject:
        instruction = (
            "给出三种通俗内容方向，每种只说方向和需要补充的一项信息，不使用任何品牌私有事实。"
            if inspiration
            else "自然回应用户；不要声称任何企业事实，不读取或猜测品牌私有信息。"
        )
        instruction += (
            "conversation_context只用于理解本账号内用户的延续意图，"
            "不能成为品牌事实、授权、资料或内容引用来源。"
            "当前消息出现继续、刚才、上一轮等延续表达时，必须先读取其中已接受的用户表达和回复，"
            "直接回答可由上下文确定的问题，不得要求用户重复提供。"
        )
        conversation_context = self.repository.recent_chat_turns(
            principal_id=principal_id,
            account_id=account_id,
            limit=6,
        )
        run_id = self._new_run_id(principal_id, account_id, request.operation, request.message)
        prompt = {
            "system": instruction,
            "user_message": request.message,
            "conversation_context": list(conversation_context),
            "output_contract": {"kind": "CHAT_REPLY", "reply": "string", "candidates": []},
        }
        self.repository.start_model_run(
            run_id=run_id,
            principal_id=principal_id,
            account_id=account_id,
            operation=request.operation,
            plan_ref=None,
            prompt_digest=digest_object(prompt),
            payload={"prompt": prompt, "private_retrieval_performed": False},
        )
        return {"response_kind": "MODEL_REQUIRED", "run_id": run_id, "author_prompt": prompt}

    def _prepare_creation(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        account: JsonObject,
    ) -> JsonObject:
        topic = self.topic_by_label.get(str(request.topic_label))
        product_id = str(request.selected_content_product_id)
        if topic is None or product_id not in topic["internal_product_ids"]:
            return self._plain_action("COLLECT_MATERIAL")
        profile = self._brand_profile_for_account(str(account["brand_id"]))
        role_card = self._role_card(
            profile,
            str(account["account_id"]),
            request.speaker_role_id,
            request.speaker_role_name,
        )
        storyline = self._storyline(profile, request.storyline_id, request.storyline_name)
        column = self._column(
            profile,
            request.column_id,
            request.column_name,
            str(storyline["storyline_id"]),
        )
        if request.previous_content_ref is not None and not self.repository.candidate_belongs_to_account(
            request.previous_content_ref,
            str(account["account_id"]),
        ):
            return self._plain_action("BLOCK")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        requirement_id = f"REQ-{digest_object([principal_id, account['account_id'], request.message, now])[:20].upper()}"
        precise_queries = self._precise_fact_queries(request, account)
        requirement = {
            "requirement_id": requirement_id,
            "requirement_version": 1,
            "status": "CONFIRMED",
            "plain_language_summary": request.message,
            "tenant_id": account["tenant_id"],
            "content_account_id": account["account_id"],
            "topic_category_id": topic["topic_category_id"],
            "target_platform": request.target_platform,
            "confirmed_by_principal_id": principal_id,
            "confirmed_at": now,
            "selected_internal_content_product_id": product_id,
            "primary_audience": request.primary_audience,
            "required_precise_fact_kinds": sorted(
                {str(row["fact_kind"]) for row in precise_queries}
            ),
            "content_goal": request.content_goal or request.message,
            "key_takeaway": request.key_takeaway or request.message,
            "speaker_role_id": role_card["role_id"],
            "speaker_role_display_name": role_card["display_name"],
            "storyline_id": storyline["storyline_id"],
            "storyline_display_name": storyline["display_name"],
            "column_id": column["column_id"],
            "column_display_name": column["display_name"],
            "previous_content_ref": request.previous_content_ref,
            "localization_allowed": request.localization_allowed,
            "duration_label": request.duration_label,
            "expression_feeling": request.expression_feeling,
            "content_format": request.content_format,
            "existing_material_kinds": list(request.existing_material_kinds),
            "user_material_refs": list(request.user_material_refs),
        }
        self.repository.save_requirement(requirement, principal_id, str(account["account_id"]))
        route = account["confirmation_routes"][0]
        task = ServerConfirmedProductionTask(
            server_task_ref=f"server-task://{requirement_id}",
            authority_source=SERVER_TASK_AUTHORITY,
            intent=START_CREATION,
            request_id=f"REQUEST-{requirement_id}",
            principal_id=principal_id,
            content_account_id=str(account["account_id"]),
            acting_role_id=str(account["maker_role_ids"][0]),
            query_at=now,
            confirmed_requirement=requirement,
            confirmation_evidence={
                "confirmed_by_principal_id": principal_id,
                "confirmed_by_role_ids": list(route["confirmer_role_ids"]),
                "confirmation_scope": route["scope"],
                "authorization_refs": [account["runtime_confirmation_authorization_ref"]],
                "subject_confirmation_ref": None,
            },
            retrieval_query_text=request.message,
            precise_fact_queries=tuple(precise_queries),
            requested_high_level_mode_refs=("expression-mode://documentary-observation/v1",),
            client_soft_preferences={
                "rhythm": self._rhythm_for_duration(request.duration_label),
                "emotional_intensity": self._intensity_for_feeling(request.expression_feeling),
            },
            output_requirements={
                "target_platform": request.target_platform,
                "required_candidate_count": 3,
                "audience_surface_fields": ["title", "body", "spoken_lines", "CTA"],
            },
        )
        result = self.adapter.prepare(task)
        if result.get("object_type") != "LIGHT_CONTENT_PLAN":
            return self._plain_action(str(result.get("action_type", "BLOCK")))
        plan_ref = str(result["composition_plan_ref"])
        materials = self.adapter.author_materials(plan_ref, self._access(principal_id, str(account["account_id"])))
        if not materials.get("scoped_retrieval_fragments"):
            return self._plain_action("COLLECT_MATERIAL")
        return self._start_author_run(
            request,
            principal_id,
            str(account["account_id"]),
            result,
            materials,
            profile,
            role_card,
            storyline,
            column,
        )

    def _prepare_revision(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        account_id: str,
    ) -> JsonObject:
        selected = self.repository.select_candidate(account_id, int(request.candidate_number or 0))
        if not selected.plan_ref:
            return self._plain_action("BLOCK")
        plan_record = self.adapter.expression_service.store.get(selected.plan_ref)
        if plan_record is None:
            return self._plain_action("BLOCK")
        materials = self.adapter.author_materials(selected.plan_ref, self._access(principal_id, account_id))
        original_run = self.repository.model_run(selected.run_id)
        task_brief = {} if original_run is None else copy.deepcopy(original_run.payload.get("task_brief", {}))
        prompt = self._author_prompt(
            plan_record.plan,
            materials,
            task_brief=task_brief,
            revision_instruction=request.message,
            selected_candidate=selected.candidate_payload,
        )
        run_id = self._new_run_id(principal_id, account_id, request.operation, request.message)
        self.repository.start_model_run(
            run_id=run_id,
            principal_id=principal_id,
            account_id=account_id,
            operation=request.operation,
            plan_ref=selected.plan_ref,
            prompt_digest=digest_object(prompt),
            payload={"prompt": prompt, "source_candidate_id": selected.candidate_id},
        )
        return {"response_kind": "MODEL_REQUIRED", "run_id": run_id, "author_prompt": prompt}

    def _start_author_run(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        account_id: str,
        plan: JsonObject,
        materials: JsonObject,
        profile: JsonObject,
        role_card: JsonObject,
        storyline: JsonObject,
        column: JsonObject,
    ) -> JsonObject:
        task_brief = {
            "content_goal": request.content_goal or request.message,
            "key_takeaway": request.key_takeaway or request.message,
            "speaker_role": role_card["display_name"],
            "speaker_boundary": role_card["boundary"],
            "storyline": storyline["display_name"],
            "storyline_purpose": storyline["purpose"],
            "column": column["display_name"],
            "previous_content_ref_present": request.previous_content_ref is not None,
            "localization_allowed": request.localization_allowed,
            "target_platform": request.target_platform,
            "duration_label": request.duration_label,
            "expression_feeling": request.expression_feeling,
            "content_format": request.content_format,
            "primary_audience": request.primary_audience,
            "existing_material_kinds": list(request.existing_material_kinds),
            "brand_guidance": self._public_brand_guidance(profile),
        }
        prompt = self._author_prompt(plan, materials, task_brief=task_brief)
        run_id = self._new_run_id(principal_id, account_id, request.operation, request.message)
        self.repository.start_model_run(
            run_id=run_id,
            principal_id=principal_id,
            account_id=account_id,
            operation=request.operation,
            plan_ref=str(plan["composition_plan_ref"]),
            prompt_digest=digest_object(prompt),
            payload={"prompt": prompt, "requirement_summary": request.message, "task_brief": task_brief},
        )
        return {"response_kind": "MODEL_REQUIRED", "run_id": run_id, "author_prompt": prompt}

    @staticmethod
    def _author_prompt(
        plan: JsonObject,
        materials: JsonObject,
        *,
        task_brief: JsonObject,
        revision_instruction: str | None = None,
        selected_candidate: JsonObject | None = None,
    ) -> JsonObject:
        format_payload = Package7Runtime._format_payload_contract(
            str(task_brief.get("content_format", "短视频"))
        )
        author_materials = copy.deepcopy(materials)
        precise_facts = author_materials.get("verified_precise_facts", [])
        if isinstance(precise_facts, list):
            author_materials["verified_precise_facts"] = [
                row
                for row in precise_facts
                if isinstance(row, dict) and row.get("fact_kind") != "AUTHORIZATION"
            ]
            author_materials["precise_fact_refs"] = [
                str(row["fact_id"])
                for row in author_materials["verified_precise_facts"]
                if isinstance(row.get("fact_id"), str)
            ]
        return {
            "system": (
                "你是受控内容作者。只能使用所给事实和资料，不得补写数字、人物、动作、因果、结果、承诺或授权。"
                "返回严格JSON，不要Markdown。输出2至3份候选，每份至少在核心创意、切入问题或场景、情绪钩子、"
                "叙事视角、事实或证明路径、画面组织方法中的两项真正不同；换标题、换词或调段落不算差异。"
                "每份候选分别列出实际使用的事实引用和资料引用；没使用就留空。引用只能从允许列表选择。"
                "每份生产候选必须至少使用一条资料引用；资料不足时不要生成候选。"
                "不要输出任何内部编号、字段名或授权术语。所有合同中的string都必须填写非空文字，"
                "图文必须至少给出两帧，短视频必须至少给出两个镜头。publishing_copy须明确写内部测试不可发布。"
                "根对象必须且只能包含kind、reply、candidates三个键；kind固定为CANDIDATE_SET，reply固定为null。"
                "短视频的shooting_notes和editing_notes必须写在video对象内，不能写在execution_payload同级。"
                "历史事件没有现成影像时，只能拍当前物件、文档或静态证据；不得新增孩子、家长、员工、台词或动作来摆拍重演。"
                "资料只说感受存在差异时，不得改写成某人说了具体话或某个动作成功、失败。"
                "不得把未提供的照片、视频、样衣、设计稿或记录写成已经存在；需要这些材料时只能写成待补拍或待取得。"
                "陈列资料没有明确商品颜色、厚度、尺码交集、库存或空间关系时，不得自行配对或推断；"
                "可以用证据卡和核对清单说明方法，并把未知项明确列为待确认。"
                "短视频、图文、陈列搭配必须分别按合同给出可直接拍摄或制作的细节。"
            ),
            "plan": plan,
            "author_materials": author_materials,
            "task_brief": task_brief,
            "revision_instruction": revision_instruction,
            "selected_candidate": selected_candidate,
            "output_contract": {
                "kind": "CANDIDATE_SET",
                "reply": None,
                "candidates": [
                    {
                        "difference_label": "string",
                        "difference_dimensions": ["核心创意", "画面组织方法"],
                        "surfaces": {
                            "title": "string",
                            "body": "string",
                            "spoken_lines": ["string"],
                            "CTA": "string",
                            "execution_payload": {
                                "production_format": "短视频|图文|陈列搭配（与任务一致）",
                                "task_summary": "string",
                                "content_direction": "string",
                                "core_idea": "string",
                                "cover_or_first_screen_copy": "string",
                                "opening_hook": "string",
                                "story_or_full_script": "string",
                                "target_platform": "string",
                                "duration_label": "string",
                                "ending_and_action": "string",
                                "publishing_copy": "string",
                                "next_actions": ["换开头", "缩短", "提交审核"],
                                **format_payload,
                            },
                            "surface_units": [],
                        },
                        "used_fact_refs": ["allowed fact ref"],
                        "used_material_refs": ["allowed material ref"],
                    }
                ],
            },
        }

    @staticmethod
    def _format_payload_contract(content_format: str) -> JsonObject:
        if content_format == "短视频":
            return {
                "video": {
                    "shots": [
                        {
                            "time_range": "string",
                            "visual": "string",
                            "action": "string",
                            "camera": "string",
                            "audio": "string",
                            "subtitle": "string or empty",
                            "scene_product_props": "string or empty",
                            "edit_note": "string or empty",
                        },
                        {
                            "time_range": "string",
                            "visual": "string",
                            "action": "string",
                            "camera": "string",
                            "audio": "string",
                            "subtitle": "string or empty",
                            "scene_product_props": "string or empty",
                            "edit_note": "string or empty",
                        },
                    ],
                    "shooting_notes": ["string"],
                    "editing_notes": ["string"],
                },
                "article": None,
                "display": None,
            }
        if content_format == "图文":
            return {
                "video": None,
                "article": {
                    "frames": [
                        {"order": 1, "image_brief": "string", "accompanying_copy": "string"},
                        {"order": 2, "image_brief": "string", "accompanying_copy": "string"},
                    ],
                    "cover_brief": "string",
                    "layout_notes": ["string"],
                },
                "display": None,
            }
        if content_format == "陈列搭配":
            return {
                "video": None,
                "article": None,
                "display": {
                    "referenced_items_or_facts": ["allowed fact or material description"],
                    "arrangement_relationship": "string",
                    "spatial_layers": "string",
                    "color_relationship": "string",
                    "availability_caution": "string",
                    "shooting_angles": ["string"],
                },
            }
        raise RuntimeContractError("Unknown content format")

    def finalize_model_output(self, run_id: str, model_output_b64: str) -> JsonObject:
        run = self.repository.model_run(run_id)
        if run is None or run.first_output_preserved:
            raise RuntimeContractError("Unknown or already completed run")
        try:
            raw = base64.b64decode(model_output_b64, validate=True).decode("utf-8")
            raw_output_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            normalized, normalization = normalize_model_json_text(raw)
            parsed = json.loads(normalized)
            if (
                run.plan_ref is not None
                and isinstance(parsed, dict)
                and set(parsed) == {"candidates"}
            ):
                parsed = {
                    "kind": "CANDIDATE_SET",
                    "reply": None,
                    "candidates": parsed["candidates"],
                }
                normalization = f"{normalization}+ADDED_FIXED_CANDIDATE_ENVELOPE"
            relocated_video_notes = 0
            if run.plan_ref is not None and isinstance(parsed, dict):
                raw_candidates = parsed.get("candidates")
                if isinstance(raw_candidates, list):
                    for raw_candidate in raw_candidates:
                        surfaces = (
                            raw_candidate.get("surfaces")
                            if isinstance(raw_candidate, dict)
                            else None
                        )
                        production = (
                            surfaces.get("execution_payload")
                            if isinstance(surfaces, dict)
                            else None
                        )
                        video = production.get("video") if isinstance(production, dict) else None
                        if not isinstance(video, dict) or not isinstance(production, dict):
                            continue
                        for field in ("shooting_notes", "editing_notes"):
                            if field in production and field not in video:
                                video[field] = production.pop(field)
                                relocated_video_notes += 1
            if relocated_video_notes:
                normalization = f"{normalization}+RELOCATED_VIDEO_NOTES"
            for marker in self._normalize_known_model_contract_variants(parsed):
                normalization = f"{normalization}+{marker}"
            envelope = ModelEnvelope.model_validate(parsed)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            digest = hashlib.sha256(model_output_b64.encode("utf-8")).hexdigest()
            self.repository.preserve_first_output(run_id, digest, "FIRST_OUTPUT_REJECTED", {"parse_error": True})
            return self._plain_action("BLOCK")
        output = envelope.model_dump()
        output_digest = raw_output_digest
        if envelope.kind == "CHAT_REPLY":
            self.repository.preserve_first_output(
                run_id,
                output_digest,
                "FIRST_OUTPUT_ACCEPTED",
                {
                    "envelope": output,
                    "private_retrieval_performed": False,
                    "model_wrapper_normalization": normalization,
                },
            )
            return {"response_kind": "DIRECT", "user_visible_text": str(envelope.reply)}
        if run.plan_ref is None:
            self.repository.preserve_first_output(run_id, output_digest, "FIRST_OUTPUT_REJECTED", output)
            return self._plain_action("BLOCK")
        return self._finalize_candidate_envelope(
            run,
            envelope,
            output_digest=output_digest,
            normalization=normalization,
        )

    def revalidate_preserved_candidate_output(self, run_id: str) -> JsonObject:
        """Re-run deterministic gates against one unchanged preserved first output."""
        run = self.repository.model_run(run_id)
        if (
            run is None
            or not run.first_output_preserved
            or run.state != "FIRST_OUTPUT_REJECTED"
            or not isinstance(run.model_output_digest, str)
            or run.payload.get("parse_error") is True
        ):
            raise RuntimeContractError("Run is not eligible for deterministic revalidation")
        try:
            envelope = ModelEnvelope.model_validate(
                {
                    "kind": copy.deepcopy(run.payload["kind"]),
                    "reply": copy.deepcopy(run.payload["reply"]),
                    "candidates": copy.deepcopy(run.payload["candidates"]),
                }
            )
        except (KeyError, ValueError) as exc:
            raise RuntimeContractError("Preserved candidate envelope is incomplete") from exc
        if envelope.kind != "CANDIDATE_SET" or run.plan_ref is None:
            raise RuntimeContractError("Preserved output is not a candidate set")
        return self._finalize_candidate_envelope(
            run,
            envelope,
            output_digest=run.model_output_digest,
            normalization="PRESERVED_FIRST_OUTPUT_DETERMINISTIC_REVALIDATION",
            preserved_revalidation=True,
        )

    def revalidate_preserved_parse_error(
        self,
        run_id: str,
        model_output_b64: str,
    ) -> JsonObject:
        """Recover one exact first output after a deterministic parser repair."""
        run = self.repository.model_run(run_id)
        encoded_digest = hashlib.sha256(model_output_b64.encode("utf-8")).hexdigest()
        if (
            run is None
            or not run.first_output_preserved
            or run.state != "FIRST_OUTPUT_REJECTED"
            or run.payload.get("parse_error") is not True
            or run.model_output_digest != encoded_digest
            or run.plan_ref is None
        ):
            raise RuntimeContractError("Parse-rejected run is not eligible for revalidation")
        try:
            raw = base64.b64decode(model_output_b64, validate=True).decode("utf-8")
            normalized, normalization = normalize_model_json_text(raw)
            provider_json_b64 = base64.b64encode(normalized.encode("utf-8")).decode("ascii")
            parsed = json.loads(normalized)
            if isinstance(parsed, dict) and set(parsed) == {"candidates"}:
                parsed = {
                    "kind": "CANDIDATE_SET",
                    "reply": None,
                    "candidates": parsed["candidates"],
                }
                normalization = f"{normalization}+ADDED_FIXED_CANDIDATE_ENVELOPE"
            relocated_video_notes = 0
            if isinstance(parsed, dict) and isinstance(parsed.get("candidates"), list):
                for raw_candidate in parsed["candidates"]:
                    surfaces = raw_candidate.get("surfaces") if isinstance(raw_candidate, dict) else None
                    production = (
                        surfaces.get("execution_payload")
                        if isinstance(surfaces, dict)
                        else None
                    )
                    video = production.get("video") if isinstance(production, dict) else None
                    if not isinstance(video, dict) or not isinstance(production, dict):
                        continue
                    for field in ("shooting_notes", "editing_notes"):
                        if field in production and field not in video:
                            video[field] = production.pop(field)
                            relocated_video_notes += 1
            if relocated_video_notes:
                normalization = f"{normalization}+RELOCATED_VIDEO_NOTES"
            markers = self._normalize_known_model_contract_variants(parsed)
            for marker in markers:
                normalization = f"{normalization}+{marker}"
            envelope = ModelEnvelope.model_validate(parsed)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeContractError("Preserved parse error remains invalid") from exc
        if envelope.kind != "CANDIDATE_SET":
            raise RuntimeContractError("Preserved output is not a candidate set")
        return self._finalize_candidate_envelope(
            run,
            envelope,
            output_digest=run.model_output_digest,
            normalization=normalization,
            preserved_revalidation=True,
            preserved_revalidation_details={
                "repair_id": "PKG7-NARROW-MODEL-CONTRACT-NORMALIZATION-001",
                "provider_response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                "provider_candidate_json_b64": provider_json_b64,
                "private_reasoning_retained": False,
                "provider_output_digest_unchanged": True,
                "user_visible_content_unchanged": True,
                "contract_normalizations": markers,
            },
        )

    @staticmethod
    def _normalize_known_model_contract_variants(parsed: object) -> list[str]:
        """Normalize only closed, semantics-preserving provider contract variants."""
        if not isinstance(parsed, dict) or not isinstance(parsed.get("candidates"), list):
            return []
        dimension_alias_count = 0
        material_fact_ref_count = 0
        empty_cta_mapping_count = 0
        for candidate in parsed["candidates"]:
            if not isinstance(candidate, dict):
                continue
            dimensions = candidate.get("difference_dimensions")
            if isinstance(dimensions, list):
                for index, value in enumerate(dimensions):
                    if value == "切入问题":
                        dimensions[index] = "切入问题或场景"
                        dimension_alias_count += 1
            fact_refs = candidate.get("used_fact_refs")
            material_refs = candidate.get("used_material_refs")
            if isinstance(fact_refs, list) and isinstance(material_refs, list):
                material_ref_set = set(value for value in material_refs if isinstance(value, str))
                normalized_fact_refs = []
                for value in fact_refs:
                    if (
                        isinstance(value, str)
                        and value.startswith("PKG5-FRAGMENT-")
                        and value in material_ref_set
                    ):
                        material_fact_ref_count += 1
                        continue
                    normalized_fact_refs.append(value)
                candidate["used_fact_refs"] = normalized_fact_refs
            surfaces = candidate.get("surfaces")
            execution_payload = (
                surfaces.get("execution_payload") if isinstance(surfaces, dict) else None
            )
            ending_and_action = (
                execution_payload.get("ending_and_action")
                if isinstance(execution_payload, dict)
                else None
            )
            if (
                isinstance(surfaces, dict)
                and surfaces.get("CTA") == ""
                and isinstance(ending_and_action, str)
                and ending_and_action.strip()
            ):
                surfaces["CTA"] = ending_and_action.strip()
                empty_cta_mapping_count += 1
        markers = []
        if dimension_alias_count:
            markers.append("NORMALIZED_EXACT_DIFFERENCE_DIMENSION_ALIAS")
        if material_fact_ref_count:
            markers.append("REMOVED_DUPLICATE_MATERIAL_REF_FROM_FACT_REFS")
        if empty_cta_mapping_count:
            markers.append("COPIED_EXISTING_ENDING_AND_ACTION_TO_EMPTY_CTA")
        return markers

    def _finalize_candidate_envelope(
        self,
        run: RuntimeModelRun,
        envelope: ModelEnvelope,
        *,
        output_digest: str,
        normalization: str,
        preserved_revalidation: bool = False,
        preserved_revalidation_details: JsonObject | None = None,
    ) -> JsonObject:
        if run.plan_ref is None:
            raise RuntimeContractError("Candidate run has no composition plan")
        output = envelope.model_dump()

        def reject(payload: JsonObject) -> JsonObject:
            if not preserved_revalidation:
                self.repository.preserve_first_output(
                    run.run_id,
                    output_digest,
                    "FIRST_OUTPUT_REJECTED",
                    payload,
                )
            return self._plain_action("BLOCK")

        access = self._access(run.principal_id, run.account_id)
        materials = self.adapter.author_materials(run.plan_ref, access)
        allowed_fact_refs = {
            str(row["fact_id"])
            for row in materials.get("verified_precise_facts", [])
            if isinstance(row, dict)
            and row.get("fact_kind") != "AUTHORIZATION"
            and isinstance(row.get("fact_id"), str)
        }
        allowed_material_refs = set(materials["retrieval_fragment_refs"])
        task_brief = run.payload.get("task_brief", {})
        expected_format = task_brief.get("content_format") if isinstance(task_brief, dict) else None
        candidates: list[JsonObject] = []
        validations: list[JsonObject] = []
        labels: set[str] = set()
        core_ideas: set[str] = set()
        creative_signatures: set[str] = set()
        for ordinal, candidate in enumerate(envelope.candidates, 1):
            if candidate.difference_label in labels:
                return reject(output)
            labels.add(candidate.difference_label)
            production = candidate.surfaces.execution_payload
            core_ideas.add(production.core_idea.strip())
            creative_signatures.add(
                digest_object(
                    {
                        "content_direction": production.content_direction,
                        "core_idea": production.core_idea,
                        "opening_hook": production.opening_hook,
                        "format_payload": {
                            "video": None if production.video is None else production.video.model_dump(),
                            "article": None if production.article is None else production.article.model_dump(),
                            "display": None if production.display is None else production.display.model_dump(),
                        },
                    }
                )
            )
            if (
                expected_format is not None
                and production.production_format != expected_format
            ):
                return reject(output)
            if not set(candidate.used_fact_refs).issubset(allowed_fact_refs) or not set(
                candidate.used_material_refs
            ).issubset(allowed_material_refs):
                return reject(output)
            if not candidate.used_material_refs:
                return reject(output)
            candidate_id = f"CAND-{run.run_id[-16:]}-{ordinal}"
            payload = {
                "candidate_id": candidate_id,
                "candidate_version": 1,
                "difference_label": candidate.difference_label,
                "difference_dimensions": list(candidate.difference_dimensions),
                "candidate_user_visible_surfaces": candidate.surfaces.model_dump(),
                "used_fact_refs": list(candidate.used_fact_refs),
                "used_material_refs": list(candidate.used_material_refs),
                "evidence_panel": {
                    "used_fact_count": len(candidate.used_fact_refs),
                    "used_material_count": len(candidate.used_material_refs),
                    "scope_and_authorization_checked": True,
                    "semantic_fact_review": "待人工确认",
                    "pending_confirmation": [],
                    "publishable": False,
                },
            }
            validator_candidate = {
                "candidate_id": candidate_id,
                "candidate_version": 1,
                "candidate_user_visible_surfaces": candidate.surfaces.model_dump(),
            }
            validation = self.adapter.validate_candidate(
                run.plan_ref,
                access,
                validator_candidate,
                actually_used_fact_refs=tuple(candidate.used_fact_refs),
                actually_used_material_refs=tuple(candidate.used_material_refs),
                evaluation_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
            candidates.append(payload)
            validations.append(validation)
        if (
            len(core_ideas) != len(envelope.candidates)
            or len(creative_signatures) != len(envelope.candidates)
        ):
            return reject(output)
        if any(row.get("decision") != "PASS" for row in validations):
            return reject({"envelope": output, "validations": validations})
        self.repository.save_candidate_set(
            run_id=run.run_id,
            account_id=run.account_id,
            plan_ref=run.plan_ref,
            candidates=candidates,
            validations=validations,
            preserved_revalidation_digest=(
                output_digest if preserved_revalidation else None
            ),
            preserved_revalidation_payload=(
                {
                    "repair_id": "PKG7-DIVERGENCE-CATEGORY-FALSE-REJECT-001",
                    "model_output_unchanged": True,
                    "model_call_count_increment": 0,
                    "validations": validations,
                    "normalization": normalization,
                    **copy.deepcopy(preserved_revalidation_details or {}),
                }
                if preserved_revalidation
                else None
            ),
        )
        if not preserved_revalidation:
            self.repository.preserve_first_output(
                run.run_id,
                output_digest,
                "FIRST_OUTPUT_ACCEPTED",
                {
                    "envelope": output,
                    "validations": validations,
                    "model_wrapper_normalization": normalization,
                },
            )
        return {
            "response_kind": "DIRECT",
            "user_visible_text": self._render_candidates(candidates),
        }

    @staticmethod
    def _render_candidates(candidates: list[JsonObject]) -> str:
        blocks = ["已准备好推荐候选和备选。它们仍是内部测试内容，请先人工确认。"]
        for ordinal, candidate in enumerate(candidates, 1):
            surfaces = candidate["candidate_user_visible_surfaces"]
            package = surfaces["execution_payload"]
            prefix = "推荐候选" if ordinal == 1 else f"备选{ordinal - 1}"
            blocks.append(
                f"\n【{prefix}】\n{surfaces['title']}\n{surfaces['body']}\n"
                f"方向：{package['content_direction']}\n核心创意：{package['core_idea']}"
            )
        blocks.append("\n可以选择第1、2或3份，也可以说明想局部修改哪里。")
        return "\n".join(blocks)

    def _review_selected(self, account_id: str) -> JsonObject:
        selected = self.repository.selected_candidate(account_id)
        if selected is None:
            return self._plain_action("BLOCK")
        return {
            "response_kind": "DIRECT",
            "user_visible_text": "结构、范围和引用检查已通过；正文事实语义仍需人工确认，当前不可直接发布。",
        }

    def _export_selected(self, account_id: str) -> JsonObject:
        selected = self.repository.selected_candidate(account_id)
        if selected is None:
            return self._plain_action("BLOCK")
        surfaces = selected.candidate_payload["candidate_user_visible_surfaces"]
        package = surfaces["execution_payload"]
        return {
            "response_kind": "DIRECT",
            "user_visible_text": (
                f"{surfaces['title']}\n\n{surfaces['body']}\n\n"
                f"制作包：\n{json.dumps(package, ensure_ascii=False, indent=2)}\n\n"
                "内部测试稿，不可直接发布。"
            ),
        }

    def _source_lookup(self, account_id: str) -> JsonObject:
        selected = self.repository.selected_candidate(account_id)
        if selected is None:
            return self._plain_action("BLOCK")
        rows = self.repository.narrative_fragments(list(selected.used_material_refs))
        facts = {row["fact_id"]: row for row in self.repository.precise_facts()}
        labels = [f"资料记录时间：{row['observed_at'][:10]}" for row in rows]
        labels.extend(
            f"精确事实：{facts[ref]['fact_kind']}，生效时间 {facts[ref]['effective_at'][:10]}"
            for ref in selected.used_fact_refs
            if ref in facts
        )
        return {
            "response_kind": "DIRECT",
            "user_visible_text": "来源回查：\n" + ("\n".join(labels) if labels else "这份候选没有使用品牌资料。"),
        }

    def _plain_action(self, action_type: str) -> JsonObject:
        card = self.action_cards.get(action_type)
        if card is None:
            return {
                "response_kind": "DIRECT",
                "user_visible_text": str(self.unknown_action["user_visible_reason"]),
                "action_card": True,
            }
        return {
            "response_kind": "DIRECT",
            "user_visible_text": (
                f"{card['user_visible_title']}\n{card['user_visible_reason']}\n"
                f"下一步：{card['user_visible_next_action']}"
            ),
            "action_card": True,
        }

    @staticmethod
    def _access(principal_id: str, account_id: str) -> ServerPlanAccess:
        return ServerPlanAccess(
            authority_source=SERVER_ACCESS_AUTHORITY,
            principal_id=principal_id,
            content_account_id=account_id,
        )

    def _brand_profile_for_account(self, brand_id: str) -> JsonObject:
        active = self.repository.setting("active_runtime_brand")
        if active["brand_id"] != brand_id:
            return self.repository.setting("neutral_expression_profile")
        profile = self.repository.setting(str(active["profile_setting_key"]))
        if profile.get("brand_id") != brand_id:
            raise RuntimeContractError("Brand profile isolation failed")
        return profile

    @staticmethod
    def _role_card(
        profile: JsonObject,
        account_id: str,
        requested_role_id: str | None,
        requested_role_name: str | None,
    ) -> JsonObject:
        account_card = next(
            (row for row in profile.get("account_role_cards", []) if row.get("account_id") == account_id),
            None,
        )
        if not isinstance(account_card, dict):
            raise RuntimeContractError("Account role card is unavailable")
        named_role = next(
            (
                row
                for row in profile.get("principal_roles", [])
                if requested_role_name is not None and row.get("display_name") == requested_role_name
            ),
            None,
        )
        if requested_role_name is not None and not isinstance(named_role, dict):
            raise RuntimeContractError("Requested role name is unavailable")
        role_id = requested_role_id or (
            str(named_role["role_id"]) if isinstance(named_role, dict) else str(account_card["default_role_id"])
        )
        if role_id != account_card["default_role_id"]:
            raise RuntimeContractError("Requested role is outside the account role card")
        role = next(
            (row for row in profile.get("principal_roles", []) if row.get("role_id") == role_id),
            None,
        )
        if not isinstance(role, dict):
            raise RuntimeContractError("Brand role is unavailable")
        return copy.deepcopy(role)

    @staticmethod
    def _storyline(
        profile: JsonObject,
        requested_storyline_id: str | None,
        requested_storyline_name: str | None,
    ) -> JsonObject:
        rows = profile.get("storylines", [])
        if requested_storyline_id is not None:
            row = next(
                (item for item in rows if item.get("storyline_id") == requested_storyline_id),
                None,
            )
        elif requested_storyline_name is not None:
            row = next(
                (item for item in rows if item.get("display_name") == requested_storyline_name),
                None,
            )
        else:
            row = rows[0] if rows else None
        if not isinstance(row, dict):
            raise RuntimeContractError("Long-term storyline is unavailable")
        return copy.deepcopy(row)

    @staticmethod
    def _column(
        profile: JsonObject,
        requested_column_id: str | None,
        requested_column_name: str | None,
        storyline_id: str,
    ) -> JsonObject:
        rows = profile.get("columns", [])
        row = next(
            (
                item
                for item in rows
                if item.get("column_id") == requested_column_id
                or (
                    requested_column_id is None
                    and requested_column_name is not None
                    and item.get("display_name") == requested_column_name
                )
                or (
                    requested_column_id is None
                    and requested_column_name is None
                    and item.get("storyline_id") == storyline_id
                )
            ),
            None,
        )
        if not isinstance(row, dict) or row.get("storyline_id") != storyline_id:
            raise RuntimeContractError("Column does not belong to the selected storyline")
        return copy.deepcopy(row)

    @staticmethod
    def _public_brand_guidance(profile: JsonObject) -> JsonObject:
        proposition = copy.deepcopy(profile.get("operating_proposition", {}))
        protections = copy.deepcopy(profile.get("hard_protections", {}))
        if isinstance(proposition, dict):
            proposition.pop("evidence_refs", None)
            proposition.pop("source_refs", None)
        if isinstance(protections, dict):
            protections.pop("evidence_refs", None)
            protections.pop("source_refs", None)
        return {
            "operating_proposition": proposition,
            "hard_protections": protections,
            "tone_tendencies": copy.deepcopy(profile.get("tone_tendencies", [])),
            "preferred_phrasing": copy.deepcopy(profile.get("preferred_phrasing", [])),
            "prohibited_expression_categories": copy.deepcopy(
                profile.get("prohibited_expression_categories", [])
            ),
        }

    @staticmethod
    def _precise_fact_queries(request: BridgePrepareRequest, account: JsonObject) -> list[JsonObject]:
        queries = [
            {
                "fact_kind": "AUTHORIZATION",
                "selectors": {"account_id": account["account_id"]},
                "required": True,
            }
        ]
        queries.extend(row.model_dump() for row in request.precise_fact_requests)
        return queries

    @staticmethod
    def _rhythm_for_duration(duration_label: str) -> str:
        return "compact" if duration_label in {"15秒左右", "30秒左右"} else "natural"

    @staticmethod
    def _intensity_for_feeling(expression_feeling: str) -> str:
        return "warm" if expression_feeling in {"生活分享", "情绪故事"} else "restrained"

    @staticmethod
    def _new_run_id(principal_id: str, account_id: str, operation: str, message: str) -> str:
        seed = [principal_id, account_id, operation, message, datetime.now(timezone.utc).isoformat()]
        return f"RUN-{digest_object(seed)[:24].upper()}"
