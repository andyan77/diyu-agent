#!/usr/bin/env python3
"""Deterministic acceptance and adversarial tests for the current Package 7."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

from author_contract import AUTHOR_CONTRACT_VERSION, CANDIDATE_MODELS
from brand_import import load_simulation_bundle, preflight_brand_bundle
from bridge_app import create_app, selected_account_database_scope
from contracts import BridgePrepareRequest
from dify_chat import DifyChatClient, DifyChatError
from persistence import (
    PROFESSIONAL_PERSONA_DIRECTIONS,
    RuntimeRepository,
    SqlAlchemyPlanStore,
    TrustedDatabaseScope,
    create_runtime_engine,
    create_session_factory,
    current_trusted_database_scope,
    digest_object,
    runtime_browser_session,
    trusted_database_scope,
)
from provision_dify import _content_sha256, _dify_import_text
from runtime_models import RuntimeFeedback
from runtime_retrieval import RuntimeBrandFactRetrievalService
from runtime_service import (
    Package7Runtime,
    RuntimeContractError,
    protected_detail_is_supported,
)
from security import hash_password, issue_session, verify_password, verify_session
from seed_runtime import seed_database


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
CONTENT_FORMATS = tuple(CANDIDATE_MODELS)


def encoded(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def author_candidate(
    content_format: str,
    ordinal: int,
    *,
    body: str | None = None,
) -> JsonObject:
    text = body or (
        f"从第{ordinal}个观察角度进入：先呈现一个日常选择，再把判断停在现有资料能够支持的位置。"
    )
    common: JsonObject = {
        "creative_difference": f"第{ordinal}种独立切入与呈现",
        "title": f"把一个日常选择讲清楚·方案{ordinal}",
        "body": text,
        "spoken_lines": [text],
        "cta": "先核对，再决定下一步。",
    }
    if content_format == "短视频":
        deliverable = {
            "shots": [
                {
                    "visual": f"建议用第{ordinal}种构图呈现选择发生前的状态。",
                    "action": "人物停下动作，先看清手中的选择。",
                    "camera": "固定近景后切中景。",
                    "audio": f"旁白：{text}",
                    "subtitle": "先看选择，再讲理由。",
                    "edit_note": "在动作停顿处切到细节。",
                },
                {
                    "visual": "建议以同一对象的细节收束，不冒充既有影像。",
                    "action": "人物把对象放回原位，镜头停在细节。",
                    "camera": "稳定特写。",
                    "audio": "旁白：结论只停在当前资料范围。",
                    "subtitle": "资料之外，保持待确认。",
                    "edit_note": "保留自然停顿后结束。",
                },
            ],
            "shooting_notes": ["使用未来、示意或条件性画面。"],
            "editing_notes": ["保留自然停顿，不用夸张转场。"],
        }
        common["spoken_lines"] = [shot["audio"] for shot in deliverable["shots"]]
    elif content_format == "图文":
        deliverable = {
            "cover_brief": f"用方案{ordinal}的核心问题做封面。",
            "frames": [
                {"image_brief": "建议拍整体关系。", "accompanying_copy": text},
                {
                    "image_brief": "建议拍可核对细节。",
                    "accompanying_copy": "未知项明确留白。",
                },
            ],
            "layout_notes": ["先问题，后资料，再给边界。"],
        }
    elif content_format == "直播内容包":
        deliverable = {
            "theme": f"日常选择直播·方案{ordinal}",
            "opening": "先说明今天只讲资料能够支持的部分。",
            "segments": [
                {
                    "segment_title": "问题从哪里来",
                    "talking_points": [text],
                    "interaction_prompt": "你最想先确认哪一点？",
                },
                {
                    "segment_title": "怎么做判断",
                    "talking_points": ["把已知与待确认分开。"],
                    "interaction_prompt": "还有哪项资料需要补充？",
                },
            ],
            "interaction_qa": ["问题：没有资料怎么办？回答：停在待确认，不补造。"],
            "risk_reminders": ["不承诺库存、价格或效果。"],
            "closing": "把待确认项留下，资料齐了再继续。",
        }
    elif content_format == "私域沟通内容":
        deliverable = {
            "applicable_scenario": "用于内部模拟的一次日常咨询承接。",
            "messages": [
                {"channel": "朋友圈", "copy": text},
                {"channel": "一对一", "copy": "可以先说你最在意的判断点。"},
            ],
            "follow_up_actions": ["收集用户真正关心的问题。"],
            "communication_boundaries": ["不写未确认价格、库存或承诺。"],
        }
    elif content_format == "门店线下物料":
        deliverable = {
            "core_copy": text,
            "information_hierarchy": ["先说问题", "再给判断方法", "最后留待确认项"],
            "layout_or_placement_notes": ["标题与边界提示分区呈现。"],
            "action_guidance": "请先向工作人员确认当前信息。",
            "validity_boundary": "内部模拟，不代表实时库存、价格或活动。",
        }
    elif content_format == "培训与门店话术":
        deliverable = {
            "training_goal": "学会把已知、未知和建议分开表达。",
            "outline": ["识别用户问题", "核对资料范围", "给出诚实回答"],
            "exercises": ["把一句绝对承诺改成边界清楚的回答。"],
            "situational_qa": [
                {
                    "question": "资料没有写怎么办？",
                    "suggested_answer": "明确说待确认，不自行补充。",
                }
            ],
            "allowed_phrasing": ["现有资料支持的是……"],
            "prohibited_phrasing": ["一定有效。"],
        }
    elif content_format == "陈列搭配":
        deliverable = {
            "arrangement_relationship": f"方案{ordinal}按问题、证据和未知项组织陈列。",
            "spatial_layers": "整体、局部和边界提示形成三层。",
            "color_relationship": "颜色只作视觉建议，不代替商品事实。",
            "availability_caution": "执行前核对当前可用对象与范围。",
            "shooting_angles": ["入口全景", "主展示中景", "细节近景"],
        }
    else:
        raise ValueError(content_format)
    return {**common, "deliverable": deliverable}


def candidate_envelope(content_format: str, *, count: int = 2) -> JsonObject:
    return {
        "candidates": [
            author_candidate(content_format, index) for index in range(1, count + 1)
        ],
    }


class FakeKnowledgeClient:
    def __init__(self, repository: RuntimeRepository) -> None:
        self.repository = repository
        self.requests: list[JsonObject] = []

    def retrieve(
        self,
        *,
        query: str,
        scope: JsonObject,
        query_at: str,
        limit: int,
    ) -> JsonObject:
        self.requests.append(
            {
                "query": query,
                "scope": copy.deepcopy(scope),
                "query_at": query_at,
                "limit": limit,
            }
        )
        if query.startswith("NO_MATCH:"):
            return {"results": [], "usage": {}, "prefilter_applied": True}
        compact = query.replace(" ", "")
        terms = {
            compact[index : index + 2] for index in range(max(0, len(compact) - 1))
        }
        results = []
        for row in self.repository.narrative_fragments():
            if (
                scope["content_account_id"] not in row["applicable_content_account_ids"]
                or scope["organization_id"] not in row["applicable_organization_ids"]
                or scope.get("store_id") not in row["applicable_store_ids"]
            ):
                continue
            text = str(row["text"])
            if terms and not any(term in text.replace(" ", "") for term in terms):
                continue
            results.append(
                {
                    "metadata": {
                        "document_id": f"DOC-{row['fragment_id']}",
                        "score": 1.0,
                    },
                    "content": text.replace("\r\n", "\n").replace("\r", "\n").strip(),
                    "title": "authorized fragment",
                }
            )
        return {"results": results[:limit], "usage": {}, "prefilter_applied": True}


class FakeDifyChatClient:
    def __init__(self) -> None:
        self.calls: list[JsonObject] = []

    def invoke(self, **kwargs: Any) -> JsonObject:
        self.calls.append(copy.deepcopy(kwargs))
        phase = kwargs["inputs"]["execution_phase"]
        if phase == "CLASSIFY":
            answer = {"selected_content_product_id": "CP06"}
        else:
            prompt_raw = kwargs["inputs"].get("author_prompt", "")
            prompt = json.loads(prompt_raw) if prompt_raw else {}
            contract = prompt.get("output_contract", {})
            if "candidate_schema" in contract:
                content_format = str(prompt["task_brief"]["content_format"])
                answer = candidate_envelope(content_format)
            elif "方向1｜短标题" in str(prompt.get("system", "")):
                subject = str(prompt.get("user_message", "本次内容")).splitlines()[0]
                lines = [
                    f"方向1｜先讲发生了什么｜围绕“{subject}”交代起因和过程。",
                    f"方向2｜解释专业判断｜说清“{subject}”背后的比较与取舍。",
                    f"方向3｜回答常见问题｜把“{subject}”变成普通人会关心的问题。",
                ]
                if "第1集｜短标题" in str(prompt.get("system", "")):
                    lines.extend(
                        [
                            f"第1集｜事情的起点｜先讲“{subject}”从哪里开始。",
                            f"第2集｜关键的过程｜继续讲“{subject}”中间怎样推进。",
                            f"第3集｜最后的变化｜用“{subject}”带来的结果收束。",
                        ]
                    )
                answer = {"reply": "\n".join(lines)}
            else:
                answer = {"reply": "已从Dify内部编排返回。"}
        return {
            "answer": json.dumps(answer, ensure_ascii=False),
            "usage": {"total_tokens": 12},
        }


class DifyMaterializationCompatibilityTests(unittest.TestCase):
    def test_import_normalizes_line_endings_without_hiding_content_changes(
        self,
    ) -> None:
        source = "## 资料范围\r\n字段A：保留。\r\n## 内部原文标题"
        self.assertEqual(
            _dify_import_text(source),
            "资料范围\n字段A：保留。\n## 内部原文标题",
        )
        self.assertNotEqual(
            _content_sha256(_dify_import_text(source)),
            _content_sha256(_dify_import_text(source.replace("保留", "改变"))),
        )


class Package7RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["DIYU_SESSION_SIGNING_KEY"] = "s" * 32
        os.environ["DIYU_BRIDGE_SECRET"] = "b" * 32
        os.environ["DIYU_COOKIE_SECURE"] = "false"
        self.tempdir = tempfile.TemporaryDirectory()
        database_url = f"sqlite:///{Path(self.tempdir.name) / 'runtime.sqlite3'}"
        self.engine = create_runtime_engine(database_url)
        self.sessions = create_session_factory(self.engine)
        self.repository = RuntimeRepository(self.sessions)
        self.repository.initialize_schema(self.engine)
        self.seed = seed_database(
            self.engine,
            self.sessions,
            username="package7-test-owner",
            password="package7-test-password",
        )
        mapping = {
            row["fragment_id"]: {
                "document_id": f"DOC-{row['fragment_id']}",
                "source_content_sha256": hashlib.sha256(
                    str(row["text"])
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .strip()
                    .encode("utf-8")
                ).hexdigest(),
                "index_content_sha256": hashlib.sha256(
                    str(row["text"])
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .strip()
                    .encode("utf-8")
                ).hexdigest(),
            }
            for row in self.repository.narrative_fragments()
        }
        self.repository.bind_dify_documents(mapping)
        self.knowledge = FakeKnowledgeClient(self.repository)
        self.runtime = Package7Runtime(
            self.repository,
            SqlAlchemyPlanStore(self.sessions),
            RuntimeBrandFactRetrievalService(self.repository, self.knowledge),
        )
        self.principal_id = "SIM-LOGIN-DIYU-ACCEPTANCE-001"

    def tearDown(self) -> None:
        self.engine.dispose()
        self.tempdir.cleanup()

    @staticmethod
    def request(**updates: Any) -> BridgePrepareRequest:
        payload: JsonObject = {
            "session_token": "x" * 64,
            "account_display_name": "笛语童装",
            "operation": "确认制作",
            "topic_label": "用户问题与理性选择",
            "selected_content_product_id": "CP06",
            "primary_audience": "正在为孩子判断尺码的家长",
            "message": "尺码不能只看身高，请讲清还要观察什么",
            "target_platform": "内部图文测试",
            "content_format": "短视频",
        }
        payload.update(updates)
        return BridgePrepareRequest.model_validate(payload)

    def prepare(
        self,
        content_format: str = "短视频",
        *,
        browser_session_id: str = "BRS-LOCAL-UNIT-TEST",
        **updates: Any,
    ) -> JsonObject:
        result = self.scoped_prepare(
            self.request(content_format=content_format, **updates),
            browser_session_id=browser_session_id,
        )
        self.assertEqual(result["response_kind"], "MODEL_REQUIRED")
        return result

    def finalize(
        self,
        prepared: JsonObject,
        content_format: str,
        *,
        envelope: JsonObject | None = None,
    ) -> JsonObject:
        return self.scoped_finalize(
            str(prepared["run_id"]),
            encoded(envelope or candidate_envelope(content_format)),
        )

    def runtime_scope(self, browser_session_id: str) -> TrustedDatabaseScope:
        _, account = self.repository.require_active_scope(
            self.principal_id,
            "ACCOUNT-DIYU-HQ-OFFICIAL",
        )
        return selected_account_database_scope(
            trusted_tenant_id="TENANT-DIYU-SIM-001",
            principal_id=self.principal_id,
            browser_session_id=browser_session_id,
            account=account,
        )

    def scoped_prepare(
        self,
        request: BridgePrepareRequest,
        *,
        browser_session_id: str = "BRS-LOCAL-UNIT-TEST",
        selected_account: bool = True,
    ) -> JsonObject:
        scope = (
            self.runtime_scope(browser_session_id)
            if selected_account
            else TrustedDatabaseScope(
                tenant_id="TENANT-DIYU-SIM-001",
                principal_id=self.principal_id,
                browser_session_id=browser_session_id,
            )
        )
        return self.runtime.prepare(
            request,
            self.principal_id,
            trusted_scope=scope,
        )

    def scoped_finalize(self, run_id: str, model_output_b64: str) -> JsonObject:
        run = self.repository.model_run(run_id)
        self.assertIsNotNone(run)
        return self.runtime.finalize_model_output(
            run_id,
            model_output_b64,
            trusted_scope=self.runtime_scope(run.browser_session_id),
        )

    def test_seed_has_seven_account_families_and_twelve_isolated_principals(
        self,
    ) -> None:
        admin_id = "SIM-LOGIN-DIYU-ADMIN-001"
        authority = self.repository.identity_authority("TENANT-DIYU-SIM-001")
        principals = authority["login_principals"]
        accounts = authority["content_accounts"]
        matrix = self.repository.account_management_matrix(admin_id)

        self.assertEqual(self.seed["principal_count"], 12)
        self.assertEqual(self.seed["content_account_count"], 11)
        self.assertEqual(len(principals), 12)
        self.assertEqual(len(accounts), 11)
        self.assertEqual(len(matrix["account_families"]), 7)
        self.assertEqual(len(matrix["creatable_account_families"]), 4)
        self.assertEqual(
            {row["account_family"] for row in accounts},
            {
                "HEADQUARTERS_BRAND",
                "FOUNDER",
                "HEADQUARTERS_PROFESSIONAL_PERSONA",
                "PROVINCIAL_AGENT",
                "HEADQUARTERS_DIRECT_STORE",
                "FRANCHISE_STORE",
            },
        )

        all_account_ids = {str(row["account_id"]) for row in accounts}
        usernames = set()
        assigned_accounts: set[str] = set()
        for principal_payload in principals:
            principal_id = str(principal_payload["principal_id"])
            principal = self.repository.principal_by_id(principal_id)
            self.assertIsNotNone(principal)
            if principal is None:
                continue
            usernames.add(principal.username)
            allowed = list(principal_payload["allowed_content_account_ids"])
            expected_count = 0 if principal_id == admin_id else 1
            self.assertEqual(len(allowed), expected_count, principal_id)
            if not allowed:
                continue
            own_account_id = str(allowed[0])
            assigned_accounts.add(own_account_id)
            _, own_account = self.repository.require_active_scope(
                principal_id,
                own_account_id,
            )
            self.assertEqual(own_account.account_id, own_account_id)
            foreign_account_id = next(
                account_id
                for account_id in all_account_ids
                if account_id != own_account_id
            )
            with self.assertRaises(ValueError):
                self.repository.require_active_scope(principal_id, foreign_account_id)

        self.assertEqual(len(usernames), 12)
        self.assertEqual(assigned_accounts, all_account_ids)
        self.assertEqual(self.seed["narrative_fragment_count"], 29)
        self.assertEqual(self.seed["precise_fact_count"], 16)
        self.assertEqual(self.seed["import_preflight_state"], "CAN_IMPORT")
        second = seed_database(
            self.engine,
            self.sessions,
            username="package7-test-owner",
            password="package7-test-password",
        )
        self.assertEqual(second["created_or_updated"], 0)

    def test_six_creator_families_have_distinct_directions_and_open_topics(
        self,
    ) -> None:
        family_principals = {
            "HEADQUARTERS_BRAND": "SIM-LOGIN-DIYU-ACCEPTANCE-001",
            "FOUNDER": "SIM-LOGIN-DIYU-FOUNDER-001",
            "HEADQUARTERS_PROFESSIONAL_PERSONA": "SIM-LOGIN-DIYU-PRODUCT-001",
            "PROVINCIAL_AGENT": "SIM-LOGIN-DIYU-JS-OFFICIAL-001",
            "HEADQUARTERS_DIRECT_STORE": "SIM-LOGIN-DIYU-HZ-BINJIANG-001",
            "FRANCHISE_STORE": "SIM-LOGIN-DIYU-SZ-PARK-001",
        }
        directions_by_family: dict[str, tuple[str, ...]] = {}
        professional_account: JsonObject | None = None
        for family, principal_id in family_principals.items():
            options = self.runtime.portal_options(principal_id)
            self.assertEqual(options["workspace_kind"], "CONTENT_CREATOR")
            self.assertEqual(len(options["accounts"]), 1)
            account = options["accounts"][0]
            self.assertEqual(account["account_family"], family)
            directions = tuple(map(str, account["directions"]))
            self.assertGreaterEqual(len(directions), 3)
            self.assertLessEqual(len(directions), 5)
            directions_by_family[family] = directions
            if family == "HEADQUARTERS_PROFESSIONAL_PERSONA":
                professional_account = account

        self.assertEqual(len(set(directions_by_family.values())), 6)
        self.assertIsNotNone(professional_account)
        if professional_account is None:
            return
        self.assertNotIn("allowed_topics", professional_account)
        self.assertNotIn("priority_topic", professional_account)

        required_professional_personas = {
            "商品人设",
            "设计师人设",
            "终端运营人设",
            "品控人设",
            "陈列搭配人设",
            "供应链人设",
        }
        self.assertTrue(
            required_professional_personas.issubset(PROFESSIONAL_PERSONA_DIRECTIONS)
        )
        for persona_type in required_professional_personas:
            self.assertGreaterEqual(
                len(PROFESSIONAL_PERSONA_DIRECTIONS[persona_type]), 3
            )
            self.assertLessEqual(len(PROFESSIONAL_PERSONA_DIRECTIONS[persona_type]), 5)

        professional_principals = {
            "商品人设": "SIM-LOGIN-DIYU-PRODUCT-001",
            "终端运营人设": "SIM-LOGIN-DIYU-RETAIL-001",
        }
        professional_directions: dict[str, tuple[str, ...]] = {}
        topic_label = "城市、区域与本地生活"
        product_id = str(
            self.runtime.classification_options(topic_label)[0]["content_product_id"]
        )
        for persona_type, principal_id in professional_principals.items():
            options = self.runtime.portal_options(principal_id)
            persona_account = options["accounts"][0]
            self.assertEqual(persona_account["persona_type"], persona_type)
            professional_directions[persona_type] = tuple(
                map(str, persona_account["directions"])
            )
            principal = self.repository.principal_by_id(principal_id)
            self.assertIsNotNone(principal)
            if principal is None:
                return
            account_id = principal.allowed_account_ids[0]
            _, account = self.repository.require_active_scope(principal_id, account_id)
            scope = selected_account_database_scope(
                trusted_tenant_id="TENANT-DIYU-SIM-001",
                principal_id=principal_id,
                browser_session_id=f"BRS-PROFESSIONAL-OPEN-TOPIC-{persona_type}",
                account=account,
            )
            prepared = self.runtime.prepare(
                self.request(
                    account_display_name=account.display_name,
                    topic_label=topic_label,
                    selected_content_product_id=product_id,
                    message=f"从{persona_type}的观察讲一次城市门店里的真实选择。",
                ),
                principal_id,
                trusted_scope=scope,
            )
            self.assertEqual(prepared["response_kind"], "MODEL_REQUIRED")
            self.assertEqual(
                prepared["author_prompt"]["task_brief"]["public_topic"],
                topic_label,
            )
        self.assertNotEqual(
            professional_directions["商品人设"],
            professional_directions["终端运营人设"],
        )
        self.assertIn("面料与版型判断", professional_directions["商品人设"])
        self.assertIn("门店经营复盘", professional_directions["终端运营人设"])

    def test_admin_matrix_creates_uses_and_disables_four_extensible_families(
        self,
    ) -> None:
        fake_chat = FakeDifyChatClient()
        app = create_app(self.runtime, self.repository, fake_chat)
        app.testing = True
        admin_client = app.test_client()
        headers = {"X-Diyu-Portal": "same-origin-v1"}
        self.assertEqual(
            admin_client.post(
                "/login",
                json={
                    "username": "package7-test-owner-admin",
                    "password": "package7-test-password",
                },
            ).status_code,
            200,
        )
        matrix_response = admin_client.get("/v1/admin/accounts", headers=headers)
        self.assertEqual(matrix_response.status_code, 200)
        matrix = matrix_response.get_json()
        self.assertEqual(len(matrix["account_families"]), 7)
        self.assertEqual(len(matrix["creatable_account_families"]), 4)

        fixed_family = admin_client.post(
            "/v1/admin/accounts",
            json={
                "organization_id": "ORG-DIYU-HQ",
                "account_family": "HEADQUARTERS_BRAND",
                "persona_type": "品牌官方人设",
                "outward_account_name": "不可新增的固定品牌账号",
                "principal_id": "SIM-LOGIN-DIYU-PRODUCT-001",
            },
            headers=headers,
        )
        self.assertEqual(fixed_family.status_code, 400)
        wrong_organization = admin_client.post(
            "/v1/admin/accounts",
            json={
                "organization_id": "ORG-DIYU-JS-AGENT",
                "account_family": "HEADQUARTERS_PROFESSIONAL_PERSONA",
                "persona_type": "设计师人设",
                "outward_account_name": "组织类型不匹配",
                "principal_id": "SIM-LOGIN-DIYU-JS-OFFICIAL-001",
            },
            headers=headers,
        )
        self.assertEqual(wrong_organization.status_code, 400)
        wrong_principal_scope = admin_client.post(
            "/v1/admin/accounts",
            json={
                "organization_id": "ORG-DIYU-HQ",
                "account_family": "HEADQUARTERS_PROFESSIONAL_PERSONA",
                "persona_type": "设计师人设",
                "outward_account_name": "主体范围不匹配",
                "principal_id": "SIM-LOGIN-DIYU-JS-OFFICIAL-001",
            },
            headers=headers,
        )
        self.assertEqual(wrong_principal_scope.status_code, 400)

        specifications = (
            (
                "HEADQUARTERS_PROFESSIONAL_PERSONA",
                "ORG-DIYU-HQ",
                "设计师人设",
                "SIM-LOGIN-DIYU-PRODUCT-001",
                "动态设计师账号",
            ),
            (
                "PROVINCIAL_AGENT",
                "ORG-DIYU-JS-AGENT",
                "区域官方人设",
                "SIM-LOGIN-DIYU-JS-OFFICIAL-001",
                "动态江苏区域账号",
            ),
            (
                "HEADQUARTERS_DIRECT_STORE",
                "ORG-DIYU-HZ-BINJIANG",
                "门店员工人设",
                "SIM-LOGIN-DIYU-HZ-BINJIANG-001",
                "动态滨江直营账号",
            ),
            (
                "FRANCHISE_STORE",
                "ORG-DIYU-SZ-PARK",
                "店主人设",
                "SIM-LOGIN-DIYU-SZ-PARK-001",
                "动态苏州加盟账号",
            ),
        )
        created_accounts: list[JsonObject] = []
        for (
            family,
            organization_id,
            persona,
            principal_id,
            outward_name,
        ) in specifications:
            response = admin_client.post(
                "/v1/admin/accounts",
                json={
                    "organization_id": organization_id,
                    "account_family": family,
                    "persona_type": persona,
                    "outward_account_name": outward_name,
                    "principal_id": principal_id,
                },
                headers=headers,
            )
            self.assertEqual(response.status_code, 201, response.get_json())
            created = response.get_json()["account"]
            self.assertEqual(created["account_family"], family)
            self.assertEqual(created["bound_principal_ids"], [principal_id])
            if family == "HEADQUARTERS_PROFESSIONAL_PERSONA":
                self.assertEqual(
                    created["directions"],
                    list(PROFESSIONAL_PERSONA_DIRECTIONS[persona]),
                )
            created_accounts.append(created)

        creator_client = app.test_client()
        login = creator_client.post(
            "/login",
            json={
                "username": "package7-test-owner-product",
                "password": "package7-test-password",
            },
        )
        self.assertEqual(login.status_code, 200)
        dynamic_name = str(created_accounts[0]["outward_account_name"])
        self.assertIn(dynamic_name, login.get_json()["options"]["content_accounts"])
        generated = creator_client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": dynamic_name,
                "operation": "直接做内容",
                "topic_label": "用户问题与理性选择",
                "message": "从设计师岗位讲清一次真实取舍。",
                "primary_audience": "关注设计过程的家长",
                "content_format": "短视频",
            },
            headers=headers,
        )
        self.assertEqual(generated.status_code, 200, generated.get_json())
        generated_payload = generated.get_json()
        self.assertIn("candidates", generated_payload, generated_payload)
        self.assertGreaterEqual(len(generated_payload["candidates"]), 1)

        for created in created_accounts:
            response = admin_client.post(
                f"/v1/admin/accounts/{created['account_id']}/disable",
                headers=headers,
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertEqual(response.get_json()["account"]["status"], "INACTIVE")
        refreshed = creator_client.get("/v1/portal/options").get_json()
        self.assertNotIn(dynamic_name, refreshed["content_accounts"])
        with self.assertRaises(ValueError):
            self.repository.require_active_scope(
                "SIM-LOGIN-DIYU-PRODUCT-001",
                str(created_accounts[0]["account_id"]),
            )

    def test_admin_workspace_has_five_real_sections_and_scoped_usage(self) -> None:
        app = create_app(self.runtime, self.repository, FakeDifyChatClient())
        app.testing = True
        headers = {"X-Diyu-Portal": "same-origin-v1"}
        admin_client = app.test_client()
        creator_client = app.test_client()
        self.assertEqual(
            admin_client.post(
                "/login",
                json={
                    "username": "package7-test-owner-admin",
                    "password": "package7-test-password",
                },
            ).status_code,
            200,
        )
        self.assertEqual(
            creator_client.post(
                "/login",
                json={
                    "username": "package7-test-owner",
                    "password": "package7-test-password",
                },
            ).status_code,
            200,
        )
        self.assertEqual(
            creator_client.get("/v1/admin/accounts", headers=headers).status_code,
            403,
        )

        before_response = admin_client.get("/v1/admin/accounts", headers=headers)
        self.assertEqual(before_response.status_code, 200)
        before = before_response.get_json()
        expected_sections = {
            "enterprise_profile",
            "organization_people",
            "accounts",
            "usage",
            "system_status",
        }
        self.assertTrue(expected_sections.issubset(before))
        self.assertEqual(before["workspace_kind"], "ENTERPRISE_ADMIN")
        self.assertEqual(before["enterprise_profile"]["display_name"], "笛语童装")
        self.assertTrue(before["organization_people"])
        self.assertEqual(len(before["accounts"]), 11)
        self.assertEqual(len(before["usage"]), 11)
        self.assertEqual(len(before["content_products"]), 20)
        self.assertEqual(
            {row["label"] for row in before["system_status"]["services"]},
            {"网页服务", "品牌资料", "检索服务", "内容模型", "导出服务"},
        )
        usage_before = next(
            row for row in before["usage"] if row["outward_account_name"] == "笛语童装"
        )

        portal_response = creator_client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "笛语童装",
                "operation": "随便聊聊",
                "message": "今天先聊聊门店里值得记录的一件小事。",
            },
            headers=headers,
        )
        self.assertEqual(portal_response.status_code, 200, portal_response.get_json())
        after = admin_client.get("/v1/admin/accounts", headers=headers).get_json()
        usage_after = next(
            row for row in after["usage"] if row["outward_account_name"] == "笛语童装"
        )
        self.assertEqual(
            usage_after["activity_count"],
            usage_before["activity_count"] + 1,
        )
        self.assertIsInstance(usage_after["last_activity_at"], str)
        self.assertTrue(usage_after["last_activity_at"])

        def nested_keys(value: object) -> set[str]:
            if isinstance(value, dict):
                return {
                    str(key).lower()
                    for key in value
                }.union(*(nested_keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(nested_keys(item) for item in value))
            return set()

        response_keys = nested_keys(after)
        for marker in ("password", "token", "prompt", "candidate"):
            self.assertFalse(
                any(marker in key for key in response_keys),
                f"administrator response leaked {marker}",
            )
        self.assertTrue(
            {"content", "body", "answer", "message", "copy", "text"}.isdisjoint(
                response_keys
            )
        )

        portal_html = (PACKAGE_ROOT / "portal.html").read_text(encoding="utf-8")
        self.assertEqual(portal_html.count("data-admin-tab="), 5)
        self.assertEqual(portal_html.count("data-admin-panel="), 5)
        for heading in ("企业资料", "组织与人员", "账号矩阵", "使用情况", "系统状态"):
            self.assertIn(heading, portal_html)
        enterprise_panel = portal_html.split(
            'data-admin-panel="enterprise"', maxsplit=1
        )[1].split("</section>", maxsplit=1)[0]
        people_panel = portal_html.split(
            'data-admin-panel="organizations"', maxsplit=1
        )[1].split("</section>", maxsplit=1)[0]
        self.assertNotIn("<button", enterprise_panel)
        self.assertNotIn("<button", people_panel)
        for fake_action in (
            "上传资料",
            "导入资料",
            "编辑企业资料",
            "新增人员",
            "删除人员",
        ):
            self.assertNotIn(fake_action, portal_html)

    def test_progressive_ui_payload_and_twenty_classification_pairs(self) -> None:
        node_script = r"""
const {buildPortalTaskPayload} = require("./portal.js");
const payload = buildPortalTaskPayload({
  accountDisplayName: "测试对外账号",
  operation: "直接做内容",
  topicLabel: "测试题材",
  primaryAudience: "测试受众",
  message: "测试主题",
  targetPlatform: "测试平台",
  durationLabel: "测试时长",
  expressionFeeling: "测试感觉",
  contentFormat: "测试成品",
  existingMaterialKinds: ["测试材料"],
  businessGoal: "测试目标",
  speakerRoleName: "测试讲述人"
});
process.stdout.write(JSON.stringify(payload));
"""
        completed = subprocess.run(
            ["node", "-e", node_script],
            cwd=PACKAGE_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(
            {
                "target_platform": payload["target_platform"],
                "duration_label": payload["duration_label"],
                "primary_audience": payload["primary_audience"],
                "expression_feeling": payload["expression_feeling"],
                "content_format": payload["content_format"],
                "existing_material_kinds": payload["existing_material_kinds"],
                "business_goal": payload["business_goal"],
                "speaker_role_name": payload["speaker_role_name"],
            },
            {
                "target_platform": "测试平台",
                "duration_label": "测试时长",
                "primary_audience": "测试受众",
                "expression_feeling": "测试感觉",
                "content_format": "测试成品",
                "existing_material_kinds": ["测试材料"],
                "business_goal": "测试目标",
                "speaker_role_name": "测试讲述人",
            },
        )

        classification_options = self.runtime.classification_options(None)
        self.assertEqual(len(classification_options), 20)
        self.assertEqual(
            {row["content_product_id"] for row in classification_options},
            {f"CP{index:02d}" for index in range(1, 21)},
        )
        for option in classification_options:
            product_id = str(option["content_product_id"])
            public_topic = str(option["public_topic_label"])
            self.assertIn(product_id, self.runtime.topic_by_label[public_topic]["internal_product_ids"])
            self.assertEqual(
                self.runtime.validate_classification_choice(
                    product_id,
                    classification_options,
                ),
                {
                    "selected_content_product_id": product_id,
                    "topic_label": public_topic,
                },
            )

        portal_html = (PACKAGE_ROOT / "portal.html").read_text(encoding="utf-8")
        for label in (
            "陪我想",
            "快速填写",
            "1. 谁来讲",
            "2. 手里有什么",
            "3. 做成什么",
            "4. 希望带来什么",
            "看看例子",
            "更多调整",
            "搜索其他内容方向",
        ):
            self.assertIn(label, portal_html)
        portal_js = (PACKAGE_ROOT / "portal.js").read_text(encoding="utf-8")
        portal_css = (PACKAGE_ROOT / "portal.css").read_text(encoding="utf-8")
        self.assertIn('id="copy-result"', portal_html)
        self.assertIn("navigator.clipboard.writeText", portal_js)
        self.assertIn("尚未选择候选：请先点选一份候选", portal_js)
        self.assertNotIn(
            "await selectCandidate(state.selectedOrdinal, true)",
            portal_js,
        )
        self.assertIn(
            'ui.workspace.classList.toggle("admin-mode", state.isAdmin)',
            portal_js,
        )
        self.assertIn(
            ".workspace.admin-mode .identity-list, .use-boundary { display: none; }",
            portal_css,
        )
        self.assertNotIn(
            "\n  .identity-list, .use-boundary { display: none; }\n",
            portal_css,
        )

    def test_portal_state_contract_keeps_four_error_types_distinct(self) -> None:
        headers = {"X-Diyu-Portal": "same-origin-v1"}
        app = create_app(self.runtime, self.repository, FakeDifyChatClient())
        app.testing = True
        anonymous = app.test_client()
        expired = anonymous.get("/v1/portal/options")
        self.assertEqual(expired.status_code, 401)
        self.assertEqual(expired.get_json()["error_type"], "SESSION_EXPIRED")

        client = app.test_client()
        self.assertEqual(
            client.post(
                "/login",
                json={
                    "username": "package7-test-owner",
                    "password": "package7-test-password",
                },
            ).status_code,
            200,
        )
        common_payload = {
            "account_display_name": "笛语童装",
            "topic_label": "用户问题与理性选择",
            "message": "围绕孩子选衣的一次真实判断开始创作。",
            "primary_audience": "正在挑选童装的家长",
            "content_format": "短视频",
        }
        unselected = client.post(
            "/v1/portal/chat",
            json={**common_payload, "operation": "导出"},
            headers=headers,
        )
        self.assertEqual(unselected.status_code, 200)
        self.assertEqual(
            unselected.get_json()["error_type"],
            "CANDIDATE_NOT_SELECTED",
        )

        material_gap = client.post(
            "/v1/portal/chat",
            json={
                **common_payload,
                "operation": "直接做内容",
                "message": "请使用我尚未上传的视频文件直接剪成短视频。",
            },
            headers=headers,
        )
        self.assertEqual(material_gap.status_code, 200, material_gap.get_json())
        self.assertEqual(material_gap.get_json()["error_type"], "MORE_CONTEXT_NEEDED")
        self.assertTrue(material_gap.get_json()["answer"].startswith("还需补一句"))

        completed = client.post(
            "/v1/portal/chat",
            json={**common_payload, "operation": "直接做内容"},
            headers=headers,
        )
        self.assertEqual(completed.status_code, 200, completed.get_json())
        completed_payload = completed.get_json()
        self.assertTrue(
            {
                "current_stage",
                "confirmation_card",
                "candidate_cards",
                "legal_next_actions",
            }.issubset(completed_payload)
        )
        self.assertEqual(
            completed_payload["confirmation_card"]["primary_audience"],
            common_payload["primary_audience"],
        )
        self.assertTrue(completed_payload["candidate_cards"])
        self.assertTrue(completed_payload["legal_next_actions"])
        self.assertEqual(
            completed_payload["resolved_classification"]["content_product"],
            "专业判断切片",
        )
        self.assertNotIn(
            "selected_content_product_id",
            completed_payload["resolved_classification"],
        )

        class ProviderFailureChat(FakeDifyChatClient):
            def invoke(self, **kwargs: Any) -> JsonObject:
                if kwargs["inputs"]["execution_phase"] == "AUTHOR":
                    raise DifyChatError("simulated provider failure")
                return super().invoke(**kwargs)

        provider_app = create_app(
            self.runtime,
            self.repository,
            ProviderFailureChat(),
        )
        provider_app.testing = True
        provider_client = provider_app.test_client()
        self.assertEqual(
            provider_client.post(
                "/login",
                json={
                    "username": "package7-test-owner",
                    "password": "package7-test-password",
                },
            ).status_code,
            200,
        )
        provider_error = provider_client.post(
            "/v1/portal/chat",
            json={
                **common_payload,
                "operation": "随便聊聊",
                "message": "验证内容服务故障不会被说成资料不足。",
            },
            headers=headers,
        )
        self.assertEqual(provider_error.status_code, 503)
        provider_payload = provider_error.get_json()
        self.assertEqual(provider_payload["error_type"], "SYSTEM_TEMPORARY")
        self.assertNotEqual(
            provider_payload["error_type"],
            material_gap.get_json()["error_type"],
        )
        self.assertNotIn("还需补一句", provider_payload["user_visible_text"])

    def test_brand_import_contract_still_fails_closed(self) -> None:
        bundle = load_simulation_bundle()
        self.assertEqual(preflight_brand_bundle(bundle)["state"], "CAN_IMPORT")
        changed_manifest = copy.deepcopy(bundle.source_manifest)
        changed_manifest["publish_allowed"] = True
        changed = replace(bundle, source_manifest=changed_manifest)
        self.assertEqual(preflight_brand_bundle(changed)["state"], "CANNOT_IMPORT")

    def test_scope_contains_browser_session_and_rejects_wrong_tenant(self) -> None:
        _, account = self.repository.require_active_scope(
            self.principal_id,
            "ACCOUNT-DIYU-HQ-OFFICIAL",
        )
        scope = selected_account_database_scope(
            trusted_tenant_id="TENANT-DIYU-SIM-001",
            principal_id=self.principal_id,
            browser_session_id="BRS-TEST-A",
            account=account,
        )
        self.assertEqual(scope.browser_session_id, "BRS-TEST-A")
        self.assertEqual(scope.account_id, account.account_id)
        with self.assertRaises(ValueError):
            selected_account_database_scope(
                trusted_tenant_id="TENANT-OTHER",
                principal_id=self.principal_id,
                browser_session_id="BRS-TEST-A",
                account=account,
            )

    def test_signed_session_contains_server_generated_browser_scope(self) -> None:
        encoded_password = hash_password(
            "a-secure-package7-password", salt=b"fixed-test-salt-01"
        )
        self.assertTrue(verify_password("a-secure-package7-password", encoded_password))
        token = issue_session(
            principal_id=self.principal_id,
            allowed_account_ids=["ACCOUNT-DIYU-HQ-OFFICIAL"],
            signing_key="s" * 32,
            now=100,
        )
        payload = verify_session(token, "s" * 32, now=101)
        self.assertRegex(str(payload["browser_session_id"]), r"^BRS-")
        with self.assertRaises(ValueError):
            verify_session(f"{token}x", "s" * 32, now=101)
        with self.assertRaises(ValueError):
            verify_session(token, "s" * 32, now=4_000)

    def test_browser_session_lifecycle_is_persisted_and_revocable(self) -> None:
        from datetime import datetime, timedelta, timezone

        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        self.repository.start_browser_session(
            browser_session_id="BRS-LIFECYCLE-A",
            principal_id=self.principal_id,
            expires_at=expires,
        )
        self.repository.require_browser_session(
            browser_session_id="BRS-LIFECYCLE-A",
            principal_id=self.principal_id,
        )
        self.repository.revoke_browser_session(
            browser_session_id="BRS-LIFECYCLE-A",
            principal_id=self.principal_id,
        )
        with self.assertRaises(ValueError):
            self.repository.require_browser_session(
                browser_session_id="BRS-LIFECYCLE-A",
                principal_id=self.principal_id,
            )

    def test_light_author_contract_has_one_current_format_and_no_server_fields(
        self,
    ) -> None:
        prepared = self.prepare("短视频")
        prompt = prepared["author_prompt"]
        contract = prompt["output_contract"]
        properties = set(contract["candidate_schema"]["properties"])
        self.assertEqual(
            properties,
            {
                "creative_difference",
                "title",
                "body",
                "spoken_lines",
                "cta",
                "deliverable",
            },
        )
        serialized = json.dumps(prompt, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "PKG5-FRAGMENT-",
            '"fact_id"',
            '"fragment_id"',
            '"claim_bindings"',
            '"used_fact_refs"',
            '"used_material_refs"',
            '"composition_plan_ref"',
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertIn("narrative_materials", prompt["author_materials"])
        self.assertNotIn("retrieval_fragment_refs", prompt["author_materials"])
        self.assertIn(
            "人物经历、顾客故事、门店事件、未来拍摄和已有素材描述均可作为创意演绎",
            prompt["system"],
        )
        self.assertIn(
            "只对儿童直接人身安全保留最小护栏",
            prompt["system"],
        )
        self.assertIn(
            "时间顺序、地点、岗位交接、操作步骤、最终决定",
            prompt["system"],
        )
        self.assertIn("不得用创作出来的阈值宣称儿童可以安全继续活动", prompt["system"])
        self.assertIn("没有检索资料也要", prompt["system"])
        self.assertIn(
            "只是可选创作参考，不是逐句真值证明",
            prompt["author_materials"]["instruction"],
        )
        self.assertIn("不要求逐项提供来源证明", serialized)
        self.assertNotIn("未经task_brief或author_materials支持，不得编造", serialized)
        self.assertIn("不授予任何登录或数据访问权限", serialized)
        self.assertNotIn("逐句绑定", serialized)
        self.assertNotIn("required_candidate_count", serialized)
        self.assertIn("一次写2至3份候选", prompt["system"])
        self.assertEqual(
            contract["root_fields"]["candidates"], "2至3份；每份按candidate_schema填写"
        )
        dsl = yaml.safe_load(
            (PACKAGE_ROOT / "dify_app.v1.yaml").read_text(encoding="utf-8")
        )
        author_node = next(
            node
            for node in dsl["workflow"]["graph"]["nodes"]
            if node.get("id") == "author"
        )
        candidate_array = author_node["data"]["structured_output"]["schema"][
            "properties"
        ]["candidates"]
        self.assertEqual(candidate_array["minItems"], 2)
        self.assertEqual(candidate_array["maxItems"], 3)

    def test_public_capability_mapping_exposes_ten_topics_and_seven_formats(
        self,
    ) -> None:
        options = self.runtime.portal_options(self.principal_id)
        self.assertEqual(options["content_formats"], list(CONTENT_FORMATS))
        portal_javascript = (PACKAGE_ROOT / "portal.js").read_text(encoding="utf-8")
        portal_html = (PACKAGE_ROOT / "portal.html").read_text(encoding="utf-8")
        self.assertNotIn("temporarilyUnavailable", portal_javascript)
        self.assertNotIn("（暂未开放）", portal_javascript)
        self.assertNotIn("option.disabled", portal_javascript)
        self.assertNotIn("审核", portal_javascript)
        self.assertNotIn("审核", portal_html)
        self.assertNotIn("候选编号", portal_html)
        self.assertNotIn("candidate_number", portal_html)
        self.assertNotRegex(
            portal_html,
            r"<(?:input|select)[^>]+(?:candidate|ordinal)",
        )
        self.assertIn("function renderFormatSpecific", portal_javascript)
        for content_format in CONTENT_FORMATS:
            self.assertIn(f'"{content_format}"', portal_javascript)
        for structured_section in (
            "逐镜分镜",
            "图文页序",
            "直播流程",
            "沟通内容",
            "版面或摆放建议",
            "情境问答",
            "陈列关系",
        ):
            self.assertIn(structured_section, portal_javascript)
        self.assertTrue(
            {
                "品牌和企业故事",
                "商品为什么这样设计",
                "招商、招聘与组织信任",
            }.issubset(options["topics"])
        )
        self.assertEqual(len(options["organization_levels"]), 3)
        self.assertEqual(len(options["business_goals"]), 8)
        dsl = yaml.safe_load(
            (PACKAGE_ROOT / "dify_app.v1.yaml").read_text(encoding="utf-8")
        )
        start = next(
            row for row in dsl["workflow"]["graph"]["nodes"] if row["id"] == "start"
        )
        topic_input = next(
            row
            for row in start["data"]["variables"]
            if row["variable"] == "topic_label"
        )
        self.assertTrue(set(options["topics"]).issubset(set(topic_input["options"])))
        capability = yaml.safe_load(
            (PACKAGE_ROOT / "content_capability_mapping.v1.yaml").read_text(
                encoding="utf-8"
            )
        )
        product_design_topic = next(
            row
            for row in capability["public_topics"]
            if row["display_name"] == "商品为什么这样设计"
        )
        self.assertIn("CP14", product_design_topic["internal_product_ids"])
        for topic in capability["public_topics"]:
            for product_id in topic["internal_product_ids"]:
                with self.subTest(topic=topic["display_name"], product_id=product_id):
                    prepared = self.scoped_prepare(
                        self.request(
                            topic_label=topic["display_name"],
                            selected_content_product_id=product_id,
                        ),
                    )
                    self.assertEqual(prepared["response_kind"], "MODEL_REQUIRED")
                    context = self.repository.requirement_context_for_run(
                        str(prepared["run_id"])
                    )
                    self.assertRegex(
                        str(context["topic_category_id"]), r"^TOPIC-0[1-8]$"
                    )
                    self.assertEqual(
                        context["selected_internal_content_product_id"],
                        product_id,
                    )

    def test_portal_classifier_receives_confirmed_goal_and_takeaway(self) -> None:
        fake_chat = FakeDifyChatClient()
        app = create_app(self.runtime, self.repository, fake_chat)
        app.testing = True
        client = app.test_client()
        self.assertEqual(
            client.post(
                "/login",
                json={
                    "username": "package7-test-owner",
                    "password": "package7-test-password",
                },
            ).status_code,
            200,
        )
        response = client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "笛语童装",
                "operation": "直接做内容",
                "topic_label": "商品为什么这样设计",
                "message": "用近景和环境声拍清灯芯绒纹路。",
                "content_goal": "呈现材料在光线、触感和声音里的可见物性",
                "key_takeaway": "只做单一物性母题，不改成设计取舍档案",
                "content_format": "短视频",
                "expression_method": "演示",
            },
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(response.status_code, 200)
        response_payload = response.get_json()
        self.assertGreaterEqual(len(response_payload["candidates"]), 1)
        classifier_call = next(
            call
            for call in fake_chat.calls
            if call["inputs"]["execution_phase"] == "CLASSIFY"
        )
        classifier_request = classifier_call["inputs"]["message"]
        for confirmed_value in (
            "用近景和环境声拍清灯芯绒纹路。",
            "呈现材料在光线、触感和声音里的可见物性",
            "只做单一物性母题，不改成设计取舍档案",
            "成品形式：短视频",
            "表达方式：演示",
        ):
            self.assertIn(confirmed_value, classifier_request)
        author_call = next(
            call
            for call in fake_chat.calls
            if call["inputs"]["execution_phase"] == "AUTHOR"
        )
        author_prompt = json.loads(author_call["inputs"]["author_prompt"])
        self.assertTrue(author_prompt["task_brief"]["primary_audience"])

        inspiration = client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "笛语童装",
                "operation": "找点灵感",
                "message": "面料改版反复打样，想讲清为什么值得。",
            },
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(inspiration.status_code, 200)
        inspiration_payload = inspiration.get_json()
        self.assertEqual(len(inspiration_payload["angles"]), 3)
        self.assertTrue(
            all(
                "面料改版反复打样" in angle["description"]
                for angle in inspiration_payload["angles"]
            )
        )

        other_inspiration = client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "笛语童装",
                "operation": "找点灵感",
                "message": "公司为什么坚持做童装，想从创始人的选择讲起。",
            },
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(other_inspiration.status_code, 200)
        self.assertNotEqual(
            inspiration_payload["angles"],
            other_inspiration.get_json()["angles"],
        )

        series_inspiration = client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "笛语童装",
                "operation": "找点灵感",
                "message": "面料改版反复打样，做成三集连续内容。",
                "series_mode": "SERIES",
                "episode_index": 1,
            },
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(series_inspiration.status_code, 200)
        outline = series_inspiration.get_json()["series"]["outline"]
        self.assertEqual([row["episode_index"] for row in outline], [1, 2, 3])
        self.assertEqual(len({row["title"] for row in outline}), 3)

    def test_all_seven_formats_render_select_revise_export_and_reference(
        self,
    ) -> None:
        complete_format_phrases = {
            "短视频": (
                "人物停下动作，先看清手中的选择。",
                "固定近景后切中景。",
                "旁白：结论只停在当前资料范围。",
                "资料之外，保持待确认。",
                "在动作停顿处切到细节。",
                "使用未来、示意或条件性画面。",
                "保留自然停顿，不用夸张转场。",
            ),
            "图文": (
                "用方案1的核心问题做封面。",
                "建议拍整体关系。",
                "建议拍可核对细节。",
                "未知项明确留白。",
                "先问题，后资料，再给边界。",
            ),
            "直播内容包": (
                "日常选择直播·方案1",
                "先说明今天只讲资料能够支持的部分。",
                "问题从哪里来",
                "你最想先确认哪一点？",
                "问题：没有资料怎么办？回答：停在待确认，不补造。",
                "不承诺库存、价格或效果。",
                "把待确认项留下，资料齐了再继续。",
            ),
            "私域沟通内容": (
                "用于内部模拟的一次日常咨询承接。",
                "朋友圈",
                "可以先说你最在意的判断点。",
                "收集用户真正关心的问题。",
                "不写未确认价格、库存或承诺。",
            ),
            "门店线下物料": (
                "先说问题",
                "标题与边界提示分区呈现。",
                "请先向工作人员确认当前信息。",
                "内部模拟，不代表实时库存、价格或活动。",
            ),
            "培训与门店话术": (
                "学会把已知、未知和建议分开表达。",
                "识别用户问题",
                "把一句绝对承诺改成边界清楚的回答。",
                "资料没有写怎么办？",
                "现有资料支持的是……",
                "一定有效。",
            ),
            "陈列搭配": (
                "方案1按问题、证据和未知项组织陈列。",
                "整体、局部和边界提示形成三层。",
                "颜色只作视觉建议，不代替商品事实。",
                "执行前核对当前可用对象与范围。",
                "入口全景",
            ),
        }
        for content_format in CONTENT_FORMATS:
            with self.subTest(content_format=content_format):
                prepared = self.prepare(content_format)
                result = self.finalize(prepared, content_format)
                self.assertEqual(result["result_class"], "SUCCESS")
                self.assertEqual(result["ui_state"], "result")
                self.assertEqual(len(result["candidates"]), 2)
                for workbench_candidate in result["candidates"]:
                    self.assertEqual(
                        workbench_candidate["content_format"],
                        content_format,
                    )
                    surfaces = workbench_candidate["candidate_user_visible_surfaces"]
                    self.assertTrue(str(surfaces["title"]).strip())
                    self.assertTrue(str(surfaces["body"]).strip())
                    self.assertEqual(
                        surfaces["execution_payload"]["production_format"],
                        content_format,
                    )
                visible_text = result["user_visible_text"]
                for phrase in complete_format_phrases[content_format]:
                    self.assertIn(phrase, visible_text)
                for hidden_metadata in (
                    "CP06",
                    "方向：",
                    "核心创意：",
                    "参考范围：",
                    "精确事实",
                    "content_direction",
                    "core_idea",
                ):
                    self.assertNotIn(hidden_metadata, visible_text)
                if content_format == "短视频":
                    with trusted_database_scope(
                        self.runtime_scope("BRS-LOCAL-UNIT-TEST")
                    ):
                        candidates = self.repository.latest_candidates(
                            self.principal_id,
                            "ACCOUNT-DIYU-HQ-OFFICIAL",
                        )
                    surfaces = candidates[0].candidate_payload[
                        "candidate_user_visible_surfaces"
                    ]
                    shots = surfaces["execution_payload"]["video"]["shots"]
                    for shot in shots:
                        for field in (
                            "visual",
                            "action",
                            "camera",
                            "audio",
                            "subtitle",
                            "edit_note",
                        ):
                            self.assertTrue(str(shot[field]).strip())
                    self.assertEqual(
                        surfaces["spoken_lines"],
                        [shot["audio"] for shot in shots],
                    )
                selected = self.scoped_prepare(
                    self.request(operation="选择候选", candidate_number=1),
                )
                self.assertIn("已选择", selected["user_visible_text"])
                revision = self.scoped_prepare(
                    self.request(
                        operation="局部修改",
                        candidate_number=1,
                        content_format=content_format,
                        message="保持事实边界，把选中候选改得更自然。",
                    ),
                )
                self.assertEqual(revision["response_kind"], "MODEL_REQUIRED")
                revised = self.finalize(revision, content_format)
                self.assertEqual(revised["result_class"], "SUCCESS")
                reselected = self.scoped_prepare(
                    self.request(operation="选择候选", candidate_number=1),
                )
                self.assertIn("已选择", reselected["user_visible_text"])
                for operation in ("导出", "查看来源"):
                    response = self.scoped_prepare(
                        self.request(operation=operation),
                    )
                    self.assertEqual(response["response_kind"], "DIRECT")
                    self.assertNotIn("PKG5-FRAGMENT", response["user_visible_text"])

    def test_generation_select_revision_export_and_feedback_need_no_approval_fields(
        self,
    ) -> None:
        approval_fields = {
            "acting_role_id",
            "approval_state",
            "confirmation_evidence",
            "confirmer_role_ids",
            "subject_confirmation_ref",
        }
        self.assertTrue(approval_fields.isdisjoint(BridgePrepareRequest.model_fields))

        prepared = self.prepare("短视频")
        run = self.repository.model_run(str(prepared["run_id"]))
        self.assertIsNotNone(run)
        if run is None or run.plan_ref is None:
            return
        plan_record = self.runtime.adapter.expression_service.store.get(run.plan_ref)
        self.assertIsNotNone(plan_record)
        if plan_record is None:
            return
        self.assertTrue(approval_fields.isdisjoint(plan_record.source_request))

        generated = self.finalize(prepared, "短视频")
        self.assertEqual(generated["result_class"], "SUCCESS")
        selected = self.scoped_prepare(
            self.request(operation="选择候选", candidate_number=1),
        )
        self.assertIn("已选择", selected["user_visible_text"])
        revision = self.scoped_prepare(
            self.request(
                operation="局部修改",
                candidate_number=None,
                message="开头更像真实工作对话，保留第二个镜头。",
            ),
        )
        self.assertEqual(revision["response_kind"], "MODEL_REQUIRED")
        revised = self.finalize(revision, "短视频")
        self.assertEqual(revised["result_class"], "SUCCESS")
        self.scoped_prepare(
            self.request(operation="选择候选", candidate_number=1),
        )
        exported = self.scoped_prepare(self.request(operation="导出"))
        self.assertEqual(exported["response_kind"], "DIRECT")
        self.assertIn("制作安排", exported["export_text"])

        feedback = self.scoped_prepare(
            self.request(operation="提交反馈", message="开头已经自然，可以继续使用。"),
        )
        feedback_id = str(feedback["internal_feedback_ref"])
        with self.sessions() as session:
            saved_feedback = session.get(RuntimeFeedback, feedback_id)
            self.assertIsNotNone(saved_feedback)
            if saved_feedback is not None:
                self.assertEqual(saved_feedback.review_state, "RECORDED")

    def test_series_returns_three_episode_outline_and_creates_a_continuation(
        self,
    ) -> None:
        browser_session_id = "BRS-SERIES-JOURNEY"
        first = self.prepare(
            "短视频",
            browser_session_id=browser_session_id,
            series_mode="SERIES",
            episode_index=1,
            content_direction="真实组织与幕后",
            message="做一个三集系列，讲一次跨岗位协作怎样完成。",
        )
        first_result = self.finalize(first, "短视频")
        self.assertEqual(first_result["series"]["mode"], "SERIES")
        self.assertEqual(first_result["series"]["current_episode"], 1)
        self.assertEqual(first_result["series"]["next_episode"], 2)
        outline = first_result["series"]["outline"]
        self.assertEqual([row["episode_index"] for row in outline], [1, 2, 3])
        self.assertTrue(all(str(row["title"]).strip() for row in outline))

        with (
            trusted_database_scope(self.runtime_scope(browser_session_id)),
            runtime_browser_session(browser_session_id),
        ):
            first_candidates = self.repository.latest_candidates(
                self.principal_id,
                "ACCOUNT-DIYU-HQ-OFFICIAL",
            )
        self.assertGreaterEqual(len(first_candidates), 2)
        previous_content_ref = first_candidates[0].candidate_id
        continuation = self.prepare(
            "短视频",
            browser_session_id=browser_session_id,
            series_mode="SERIES",
            episode_index=2,
            previous_content_ref=previous_content_ref,
            content_direction="真实组织与幕后",
            message="继续第二集，聚焦具体选择与交接过程。",
        )
        continuation_brief = continuation["author_prompt"]["task_brief"]
        self.assertEqual(continuation_brief["episode_index"], 2)
        self.assertIsNotNone(continuation_brief["previous_content_context"])
        self.assertEqual(continuation_brief["series_outline"], outline)
        continuation_result = self.finalize(continuation, "短视频")
        self.assertEqual(continuation_result["series"]["current_episode"], 2)
        self.assertEqual(continuation_result["series"]["next_episode"], 3)
        self.assertEqual(
            [row["episode_index"] for row in continuation_result["series"]["outline"]],
            [1, 2, 3],
        )

    def test_series_generation_waits_for_delayed_outline_before_first_request(
        self,
    ) -> None:
        node_script = r"""
const assert = require("node:assert/strict");
const {
  createSeriesOutlineGate,
  formatSeriesOutline,
  runGenerationAfterOutline
} = require("./portal.js");

let releaseOutline;
let outlineRequestCount = 0;
const gate = createSeriesOutlineGate(() => {
  outlineRequestCount += 1;
  return new Promise((resolve) => { releaseOutline = resolve; });
});
const outlineFromSelection = gate.ensure([]);
const generationRequests = [];
const generation = runGenerationAfterOutline({
  seriesMode: "SERIES",
  currentOutline: [],
  ensureOutline: (outline) => gate.ensure(outline),
  buildPayload: (outline) => ({message: formatSeriesOutline(outline)}),
  sendGeneration: async (payload) => {
    generationRequests.push(payload);
    return {result: "generated"};
  }
});

setImmediate(async () => {
  try {
    assert.equal(outlineRequestCount, 1);
    assert.equal(generationRequests.length, 0);
    releaseOutline([
      {index: 1, title: "第一集标题", description: "第一集重点"},
      {index: 2, title: "第二集标题", description: "第二集重点"},
      {index: 3, title: "第三集标题", description: "第三集重点"}
    ]);
    await Promise.all([outlineFromSelection, generation]);
    assert.equal(generationRequests.length, 1);
    for (const expected of [
      "第一集标题", "第一集重点",
      "第二集标题", "第二集重点",
      "第三集标题", "第三集重点"
    ]) assert.match(generationRequests[0].message, new RegExp(expected));
    console.log(JSON.stringify({outlineRequestCount, generationRequestCount: 1}));
  } catch (error) {
    console.error(error);
    process.exitCode = 1;
  }
});
"""
        process = subprocess.run(
            ["node", "-e", node_script],
            cwd=PACKAGE_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(
            json.loads(process.stdout),
            {"outlineRequestCount": 1, "generationRequestCount": 1},
        )

    def test_server_records_reference_scope_without_author_self_reporting(self) -> None:
        prepared = self.prepare()
        result = self.finalize(prepared, "短视频")
        self.assertEqual(result["result_class"], "SUCCESS")
        with trusted_database_scope(self.runtime_scope("BRS-LOCAL-UNIT-TEST")):
            candidates = self.repository.latest_candidates(
                self.principal_id,
                "ACCOUNT-DIYU-HQ-OFFICIAL",
            )
        self.assertEqual(len(candidates), 2)
        self.assertGreater(len(candidates[0].used_material_refs), 0)
        panel = candidates[0].candidate_payload["evidence_panel"]
        self.assertEqual(panel["panel_label"], "本次参考资料范围")
        self.assertFalse(panel["machine_proves_every_sentence"])

    def test_one_bad_candidate_does_not_erase_two_safe_siblings(self) -> None:
        prepared = self.prepare()
        valid = candidate_envelope("短视频")
        envelope = {"candidates": ["不是候选对象", *valid["candidates"]]}
        result = self.finalize(prepared, "短视频", envelope=envelope)
        self.assertEqual(result["result_class"], "SUCCESS")
        run = self.repository.model_run(str(prepared["run_id"]))
        self.assertEqual(run.payload["accepted_candidate_count"], 2)
        self.assertEqual(run.payload["candidate_failures"][0]["candidate_ordinal"], 1)

        echoed = self.prepare("短视频", duration_label="30秒左右")
        echoed_envelope = candidate_envelope("短视频")
        echoed_envelope["contract_version"] = AUTHOR_CONTRACT_VERSION
        for candidate in echoed_envelope["candidates"]:
            candidate["deliverable"]["duration_label"] = "30秒左右"
        echoed_result = self.finalize(
            echoed,
            "短视频",
            envelope=echoed_envelope,
        )
        self.assertEqual(echoed_result["result_class"], "SUCCESS")
        echoed_run = self.repository.model_run(str(echoed["run_id"]))
        self.assertIn(
            "REMOVED_EXACT_SERVER_DURATION_ECHO:2",
            echoed_run.payload["model_wrapper_normalization"],
        )
        self.assertIn(
            "REMOVED_EXACT_SERVER_CONTRACT_VERSION_ECHO",
            echoed_run.payload["model_wrapper_normalization"],
        )

        root_defaults = self.prepare("短视频")
        root_default_envelope = candidate_envelope("短视频")
        for candidate in root_default_envelope["candidates"]:
            del candidate["spoken_lines"]
            del candidate["cta"]
        root_default_envelope["spoken_lines"] = []
        root_default_envelope["cta"] = ""
        root_default_result = self.finalize(
            root_defaults,
            "短视频",
            envelope=root_default_envelope,
        )
        self.assertEqual(root_default_result["result_class"], "SUCCESS")
        root_default_run = self.repository.model_run(str(root_defaults["run_id"]))
        self.assertIn(
            "REMOVED_EMPTY_ROOT_CANDIDATE_DEFAULTS:cta,spoken_lines",
            root_default_run.payload["model_wrapper_normalization"],
        )

        nonempty_root = self.prepare("短视频")
        nonempty_envelope = candidate_envelope("短视频")
        nonempty_envelope["cta"] = "不得静默丢弃"
        nonempty_result = self.finalize(
            nonempty_root,
            "短视频",
            envelope=nonempty_envelope,
        )
        self.assertEqual(
            nonempty_result["result_class"],
            "MODEL_OUTPUT_CONTRACT_ERROR",
        )

        null_defaults = self.prepare("图文")
        null_default_envelope = candidate_envelope("图文")
        for candidate in null_default_envelope["candidates"]:
            candidate["spoken_lines"] = None
            candidate["cta"] = None
        null_default_result = self.finalize(
            null_defaults,
            "图文",
            envelope=null_default_envelope,
        )
        self.assertEqual(null_default_result["result_class"], "SUCCESS")
        null_default_run = self.repository.model_run(str(null_defaults["run_id"]))
        self.assertIn(
            "REPLACED_NULL_CANDIDATE_DEFAULTS:4",
            null_default_run.payload["model_wrapper_normalization"],
        )

        invalid_default = self.prepare("图文")
        invalid_default_envelope = candidate_envelope("图文")
        for candidate in invalid_default_envelope["candidates"]:
            candidate["cta"] = {"unexpected": True}
        invalid_default_result = self.finalize(
            invalid_default,
            "图文",
            envelope=invalid_default_envelope,
        )
        self.assertEqual(
            invalid_default_result["result_class"],
            "MODEL_OUTPUT_CONTRACT_ERROR",
        )

    def test_creative_claims_remain_editable_without_evidence_binding(
        self,
    ) -> None:
        claims = (
            "这款商品售价99999元，当前库存还有12件，长度999厘米。",
            "本账号已经获准代表总部，公司承诺下周完成活动。",
            "昨天一位顾客选择了红色上衣，已有照片和视频可直接使用。",
            "这套方法百分百适合所有孩子，顾客都说好。",
        )
        for text in claims:
            with self.subTest(text=text):
                prepared = self.prepare("直播内容包")
                envelope = candidate_envelope("直播内容包")
                for candidate in envelope["candidates"]:
                    candidate["body"] = text
                result = self.finalize(
                    prepared,
                    "直播内容包",
                    envelope=envelope,
                )
                self.assertEqual(result["result_class"], "SUCCESS")

    def test_one_valid_candidate_is_rejected_without_partial_delivery(
        self,
    ) -> None:
        prepared = self.prepare()
        envelope = candidate_envelope("短视频")
        del envelope["candidates"][0]["deliverable"]
        result = self.finalize(prepared, "短视频", envelope=envelope)
        self.assertEqual(result["result_class"], "MODEL_OUTPUT_CONTRACT_ERROR")
        run = self.repository.model_run(str(prepared["run_id"]))
        self.assertEqual(run.payload["accepted_candidate_count"], 1)
        self.assertEqual(
            run.payload["failure_reason"],
            "INSUFFICIENT_COMPLETE_CANDIDATES",
        )
        self.assertEqual(run.state, "FIRST_OUTPUT_REJECTED")
        with trusted_database_scope(self.runtime_scope("BRS-LOCAL-UNIT-TEST")):
            self.assertEqual(
                self.repository.latest_candidates(
                    self.principal_id,
                    "ACCOUNT-DIYU-HQ-OFFICIAL",
                ),
                (),
            )

        exact_one = self.prepare("短视频")
        exact_one_envelope = candidate_envelope("短视频")
        exact_one_envelope["candidates"] = exact_one_envelope["candidates"][:1]
        exact_one_output = encoded(exact_one_envelope)
        exact_one_result = self.scoped_finalize(
            str(exact_one["run_id"]),
            exact_one_output,
        )
        self.assertEqual(
            exact_one_result["result_class"],
            "MODEL_OUTPUT_CONTRACT_ERROR",
        )
        exact_one_run = self.repository.model_run(str(exact_one["run_id"]))
        self.assertEqual(
            exact_one_run.payload["original_envelope"],
            exact_one_envelope,
        )
        with trusted_database_scope(self.runtime_scope("BRS-LOCAL-UNIT-TEST")):
            self.assertEqual(
                self.repository.latest_candidates(
                    self.principal_id,
                    "ACCOUNT-DIYU-HQ-OFFICIAL",
                ),
                (),
            )
        with self.assertRaisesRegex(RuntimeContractError, "already completed"):
            self.scoped_finalize(str(exact_one["run_id"]), exact_one_output)

        mismatched = self.prepare("短视频", duration_label="30秒左右")
        mismatched_envelope = candidate_envelope("短视频")
        for candidate in mismatched_envelope["candidates"]:
            candidate["deliverable"]["duration_label"] = "15秒左右"
        mismatch_result = self.finalize(
            mismatched,
            "短视频",
            envelope=mismatched_envelope,
        )
        self.assertEqual(
            mismatch_result["result_class"],
            "MODEL_OUTPUT_CONTRACT_ERROR",
        )

    def test_malformed_json_is_preserved_as_model_contract_error(self) -> None:
        array_prepared = self.prepare("短视频")
        array_envelope = candidate_envelope("短视频")["candidates"]
        array_result = self.scoped_finalize(
            str(array_prepared["run_id"]),
            encoded(array_envelope),
        )
        self.assertEqual(array_result["result_class"], "SUCCESS")
        array_run = self.repository.model_run(str(array_prepared["run_id"]))
        self.assertIn(
            "WRAPPED_TOP_LEVEL_CANDIDATE_ARRAY",
            array_run.payload["model_wrapper_normalization"],
        )

        prepared = self.prepare()
        result = self.scoped_finalize(
            str(prepared["run_id"]),
            base64.b64encode(b"not-json").decode("ascii"),
        )
        self.assertEqual(result["result_class"], "MODEL_OUTPUT_CONTRACT_ERROR")
        run = self.repository.model_run(str(prepared["run_id"]))
        self.assertTrue(run.first_output_preserved)
        self.assertEqual(run.payload["failure_stage"], "DECODE_OR_JSON")

        prepared_controls = self.prepare("图文")
        envelope = candidate_envelope("图文")
        envelope["candidates"][0]["body"] = "第一行\n第二行"
        raw = json.dumps(envelope, ensure_ascii=False).replace(
            "第一行\\n第二行",
            "第一行\n第二行",
        )
        recovered = self.scoped_finalize(
            str(prepared_controls["run_id"]),
            base64.b64encode(raw.encode("utf-8")).decode("ascii"),
        )
        self.assertEqual(recovered["result_class"], "SUCCESS")
        recovered_run = self.repository.model_run(str(prepared_controls["run_id"]))
        self.assertIn(
            "ESCAPED_RAW_JSON_STRING_CONTROLS",
            recovered_run.payload["model_wrapper_normalization"],
        )

        prepared_extra_closer = self.prepare("短视频")
        valid_raw = json.dumps(candidate_envelope("短视频"), ensure_ascii=False)
        recovered_extra_closer = self.scoped_finalize(
            str(prepared_extra_closer["run_id"]),
            base64.b64encode(f"{valid_raw}]".encode()).decode("ascii"),
        )
        self.assertEqual(recovered_extra_closer["result_class"], "SUCCESS")
        extra_closer_run = self.repository.model_run(
            str(prepared_extra_closer["run_id"])
        )
        self.assertIn(
            "STRIPPED_TRAILING_REDUNDANT_ARRAY_CLOSER",
            extra_closer_run.payload["model_wrapper_normalization"],
        )

        prepared_quotes = self.prepare("短视频")
        quoted_envelope = candidate_envelope("短视频")
        quoted_envelope["candidates"][0]["body"] = '记录“前版"返修-验收"节点”。'
        quoted_raw = json.dumps(quoted_envelope, ensure_ascii=False).replace(
            '\\"返修-验收\\"',
            '"返修-验收"',
        )
        recovered_quotes = self.scoped_finalize(
            str(prepared_quotes["run_id"]),
            base64.b64encode(quoted_raw.encode()).decode("ascii"),
        )
        self.assertEqual(recovered_quotes["result_class"], "SUCCESS")
        quoted_run = self.repository.model_run(str(prepared_quotes["run_id"]))
        self.assertIn(
            "ESCAPED_UNAMBIGUOUS_JSON_STRING_QUOTES",
            quoted_run.payload["model_wrapper_normalization"],
        )

        prepared_structural_quote = self.prepare("图文")
        structural_quote_raw = json.dumps(
            candidate_envelope("图文"),
            ensure_ascii=False,
            indent=2,
        ).replace(
            '"accompanying_copy": "未知项明确留白。"',
            '"accompanying_copy": "未知项明确留白。”',
            1,
        )
        recovered_structural_quote = self.scoped_finalize(
            str(prepared_structural_quote["run_id"]),
            base64.b64encode(structural_quote_raw.encode()).decode("ascii"),
        )
        self.assertEqual(recovered_structural_quote["result_class"], "SUCCESS")
        structural_quote_run = self.repository.model_run(
            str(prepared_structural_quote["run_id"])
        )
        self.assertIn(
            "NORMALIZED_UNAMBIGUOUS_JSON_STRUCTURAL_QUOTES:1",
            structural_quote_run.payload["model_wrapper_normalization"],
        )

        trailing_comma_prepared = self.prepare("短视频")
        trailing_comma_raw = json.dumps(
            candidate_envelope("短视频"),
            ensure_ascii=False,
            separators=(",", ":"),
        ).replace(
            '"edit_note":"保留自然停顿后结束。"}',
            '"edit_note":"保留自然停顿后结束。",}',
            1,
        )
        trailing_comma_result = self.scoped_finalize(
            str(trailing_comma_prepared["run_id"]),
            base64.b64encode(trailing_comma_raw.encode()).decode("ascii"),
        )
        self.assertEqual(trailing_comma_result["result_class"], "SUCCESS")
        trailing_comma_run = self.repository.model_run(
            str(trailing_comma_prepared["run_id"])
        )
        self.assertIn(
            "REMOVED_UNAMBIGUOUS_JSON_TRAILING_COMMAS:1",
            trailing_comma_run.payload["model_wrapper_normalization"],
        )

        fragmented_prepared = self.prepare("短视频")
        fragmented_candidates = candidate_envelope("短视频")["candidates"]
        for candidate in fragmented_candidates:
            candidate["editing_notes"] = candidate["deliverable"].pop("editing_notes")
        candidate_fragments = [
            json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
            for candidate in fragmented_candidates
        ]
        fragmented_raw = (
            '{"candidates":['
            + candidate_fragments[0]
            + "}]},"
            + candidate_fragments[1]
            + "}]}]}"
        )
        fragmented_result = self.scoped_finalize(
            str(fragmented_prepared["run_id"]),
            base64.b64encode(fragmented_raw.encode()).decode("ascii"),
        )
        self.assertEqual(fragmented_result["result_class"], "SUCCESS")
        fragmented_run = self.repository.model_run(str(fragmented_prepared["run_id"]))
        self.assertIn(
            "REBUILT_FRAGMENTED_CANDIDATE_ENVELOPE:2",
            fragmented_run.payload["model_wrapper_normalization"],
        )
        self.assertIn(
            "MOVED_CANDIDATE_ROOT_DELIVERABLE_FIELDS:2",
            fragmented_run.payload["model_wrapper_normalization"],
        )

        unsafe_fragment_prepared = self.prepare("短视频")
        unsafe_fragment = fragmented_raw.replace("}]},", "}]},unexpected", 1)
        unsafe_fragment_result = self.scoped_finalize(
            str(unsafe_fragment_prepared["run_id"]),
            base64.b64encode(unsafe_fragment.encode()).decode("ascii"),
        )
        self.assertEqual(
            unsafe_fragment_result["result_class"],
            "MODEL_OUTPUT_CONTRACT_ERROR",
        )

        bare_candidate_prepared = self.prepare("图文")
        bare_candidate_raw = json.dumps(
            author_candidate("图文", 1),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        bare_candidate_result = self.scoped_finalize(
            str(bare_candidate_prepared["run_id"]),
            base64.b64encode(bare_candidate_raw.encode()).decode("ascii"),
        )
        self.assertEqual(
            bare_candidate_result["result_class"],
            "MODEL_OUTPUT_CONTRACT_ERROR",
        )
        bare_candidate_run = self.repository.model_run(
            str(bare_candidate_prepared["run_id"])
        )
        self.assertIn(
            "WRAPPED_BARE_CANDIDATE_OBJECT",
            bare_candidate_run.payload["model_wrapper_normalization"],
        )

        unknown_bare_prepared = self.prepare("图文")
        unknown_bare = author_candidate("图文", 1)
        unknown_bare["unknown_field"] = "不得静默丢弃"
        unknown_bare_result = self.scoped_finalize(
            str(unknown_bare_prepared["run_id"]),
            encoded(unknown_bare),
        )
        self.assertEqual(
            unknown_bare_result["result_class"],
            "MODEL_OUTPUT_CONTRACT_ERROR",
        )

    def test_unlabeled_short_video_audio_is_classified_without_content_loss(
        self,
    ) -> None:
        prepared = self.prepare("短视频")
        envelope = candidate_envelope("短视频")
        envelope["candidates"][0]["deliverable"]["shots"][0]["audio"] = (
            "检验员：这颗按扣需要再确认。"
        )
        envelope["candidates"][1]["deliverable"]["shots"][0]["audio"] = (
            "按扣声，脚步声。"
        )
        result = self.finalize(prepared, "短视频", envelope=envelope)
        self.assertEqual(result["result_class"], "SUCCESS")
        self.assertIn("台词：检验员：这颗按扣需要再确认。", result["user_visible_text"])
        self.assertIn("环境声：按扣声，脚步声。", result["user_visible_text"])
        run = self.repository.model_run(str(prepared["run_id"]))
        self.assertIn(
            "CLASSIFIED_UNLABELED_SHOT_AUDIO:dialogue=1,ambient=1",
            run.payload["model_wrapper_normalization"],
        )

    def test_internal_identifiers_sensitive_data_and_secrets_are_blocked(
        self,
    ) -> None:
        for text in (
            "把CP01作为标题展示。",
            "联系电话是13812345678。",
            "调用令牌是sk-ABCDEFGHIJKLMNOPQRSTUV。",
        ):
            with self.subTest(text=text):
                prepared = self.prepare()
                envelope = candidate_envelope("短视频")
                for row in envelope["candidates"]:
                    row["title"] = text
                result = self.finalize(prepared, "短视频", envelope=envelope)
                self.assertEqual(result["result_class"], "MODEL_OUTPUT_CONTRACT_ERROR")
                self.assertFalse(result["action_card"])

    def test_reference_panel_records_scope_without_sentence_binding(self) -> None:
        prepared = self.prepare()
        envelope = candidate_envelope("短视频")
        supported = "笛语商品使用100厘米至150厘米的常用尺码范围。"
        for row in envelope["candidates"]:
            row["title"] = supported
        result = self.finalize(prepared, "短视频", envelope=envelope)
        self.assertEqual(result["result_class"], "SUCCESS")
        with trusted_database_scope(self.runtime_scope("BRS-LOCAL-UNIT-TEST")):
            candidates = self.repository.latest_candidates(
                self.principal_id,
                "ACCOUNT-DIYU-HQ-OFFICIAL",
            )
        bindings = candidates[0].candidate_payload["claim_bindings"]
        self.assertEqual(bindings, [])
        self.assertEqual(
            candidates[0].candidate_payload["evidence_panel"][
                "server_bound_explicit_fact_count"
            ],
            0,
        )
        self.assertFalse(
            candidates[0].candidate_payload["evidence_panel"][
                "machine_proves_every_sentence"
            ]
        )
        self.assertEqual(
            candidates[0].candidate_payload["author_declared_claim_bindings"],
            [],
        )

    def test_anonymous_daily_scene_and_future_shooting_remain_creatively_allowed(
        self,
    ) -> None:
        prepared = self.prepare()
        envelope = candidate_envelope("短视频")
        envelope["candidates"][0]["body"] = (
            "一位顾客选择了红色上衣，故事停在这个匿名日常选择。"
        )
        envelope["candidates"][1]["body"] = (
            "建议拍摄孩子试穿后的转身示意，不把它写成已发生事件。"
        )
        result = self.finalize(prepared, "短视频", envelope=envelope)
        self.assertEqual(result["result_class"], "SUCCESS")

        prepared = self.prepare("短视频")
        envelope = candidate_envelope("短视频")
        envelope["candidates"][0]["body"] = (
            "不讲任何已经完成的事情，只分享品牌授权管理的基本流程。"
        )
        envelope["candidates"][1]["body"] = (
            "强调可观察条件比品牌承诺更有用，尺码从来不是一个数字能决定的。"
        )
        result = self.finalize(prepared, "短视频", envelope=envelope)
        self.assertEqual(result["result_class"], "SUCCESS")

    def test_similarity_diagnostic_does_not_reject_candidates(self) -> None:
        prepared = self.prepare()
        envelope = candidate_envelope("短视频")
        envelope["candidates"][1] = copy.deepcopy(envelope["candidates"][0])
        envelope["candidates"][1]["creative_difference"] = "另一种声明的切入"
        result = self.finalize(prepared, "短视频", envelope=envelope)
        self.assertEqual(result["result_class"], "SUCCESS")
        with trusted_database_scope(self.runtime_scope("BRS-LOCAL-UNIT-TEST")):
            candidates = self.repository.latest_candidates(
                self.principal_id,
                "ACCOUNT-DIYU-HQ-OFFICIAL",
            )
        hints = candidates[0].candidate_payload["evidence_panel"]["similarity_notes"]
        self.assertTrue(hints[0]["worth_comparing"])
        self.assertFalse(hints[0]["runtime_rejection"])

    def test_first_output_is_preserved_and_reroll_is_forbidden(self) -> None:
        prepared = self.prepare()
        self.finalize(prepared, "短视频")
        with self.assertRaisesRegex(ValueError, "already completed"):
            self.finalize(prepared, "短视频")

        interrupted = self.prepare()
        with patch.object(
            self.runtime.adapter,
            "validate_candidate",
            side_effect=RuntimeError("deterministic downstream fault"),
        ):
            interrupted_result = self.finalize(interrupted, "短视频")
        self.assertEqual(
            interrupted_result["result_class"],
            "SYSTEM_OR_PROVIDER_ERROR",
        )
        interrupted_run = self.repository.model_run(str(interrupted["run_id"]))
        self.assertTrue(interrupted_run.first_output_preserved)
        self.assertEqual(
            interrupted_run.payload["failure_stage"], "DOWNSTREAM_VALIDATION"
        )

        rejected = self.prepare("短视频", browser_session_id="BRS-CORRECTION")
        rejected_envelope = candidate_envelope("短视频")
        for candidate in rejected_envelope["candidates"]:
            candidate["body"] = "把CP01内部编号直接写给用户。"
        rejected_output = encoded(rejected_envelope)
        rejected_result = self.scoped_finalize(
            str(rejected["run_id"]),
            rejected_output,
        )
        self.assertEqual(
            rejected_result["result_class"],
            "MODEL_OUTPUT_CONTRACT_ERROR",
        )
        before = copy.deepcopy(
            self.repository.model_run(str(rejected["run_id"])).payload
        )
        with self.assertRaisesRegex(RuntimeContractError, "read-only replay evidence"):
            self.runtime.prepare_preserved_output_correction(
                str(rejected["run_id"]),
                rejected_output,
                trusted_scope=self.runtime_scope("BRS-CORRECTION"),
            )
        after = self.repository.model_run(str(rejected["run_id"]))
        self.assertEqual(before, after.payload)
        self.assertEqual(after.state, "FIRST_OUTPUT_REJECTED")
        with self.assertRaisesRegex(RuntimeContractError, "cannot write runtime state"):
            self.runtime.revalidate_preserved_candidate_output(str(rejected["run_id"]))
        with self.assertRaisesRegex(RuntimeContractError, "cannot write runtime state"):
            self.runtime.revalidate_preserved_parse_error(
                str(rejected["run_id"]),
                rejected_output,
            )

        provider_failed = self.prepare(
            "短视频", browser_session_id="BRS-PROVIDER-FAILURE"
        )
        with (
            trusted_database_scope(self.runtime_scope("BRS-PROVIDER-FAILURE")),
            runtime_browser_session("BRS-PROVIDER-FAILURE"),
        ):
            failed_run = self.repository.fail_model_run_before_output(
                str(provider_failed["run_id"]),
                failure_stage="AUTHOR_INVOKE",
                error_type="DifyChatError",
            )
        self.assertEqual(failed_run.state, "PROVIDER_FAILED_BEFORE_OUTPUT")
        self.assertFalse(failed_run.first_output_preserved)
        self.assertEqual(
            failed_run.payload["result_class"],
            "SYSTEM_OR_PROVIDER_ERROR",
        )

    def test_portal_provider_failure_is_a_system_error(self) -> None:
        portal_javascript = (PACKAGE_ROOT / "portal.js").read_text(encoding="utf-8")
        self.assertIn("系统暂时无法完成登录，请稍后重试。", portal_javascript)
        self.assertIn("系统暂时无法完成请求，请稍后重试。", portal_javascript)
        self.assertNotIn("资料不足", portal_javascript)

        class ProviderFailureChat(FakeDifyChatClient):
            def invoke(self, **kwargs: Any) -> JsonObject:
                if kwargs["inputs"]["execution_phase"] == "AUTHOR":
                    raise DifyChatError("simulated provider failure")
                return super().invoke(**kwargs)

        app = create_app(self.runtime, self.repository, ProviderFailureChat())
        app.testing = True
        client = app.test_client()
        self.assertEqual(
            client.post(
                "/login",
                json={
                    "username": "package7-test-owner",
                    "password": "package7-test-password",
                },
            ).status_code,
            200,
        )
        response = client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "笛语童装",
                "operation": "随便聊聊",
                "message": "测试内容服务故障的诚实返回。",
            },
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json()["result_class"],
            "SYSTEM_OR_PROVIDER_ERROR",
        )

    def test_remote_deployment_uses_secure_session_cookie(self) -> None:
        deploy = (PACKAGE_ROOT / "deploy_remote.sh").read_text(encoding="utf-8")
        self.assertIn('"DIYU_COOKIE_SECURE": "true"', deploy)
        with patch.dict(os.environ, {"DIYU_COOKIE_SECURE": "true"}):
            app = create_app(self.runtime, self.repository, FakeDifyChatClient())
        app.testing = True
        response = app.test_client().post(
            "/login",
            base_url="https://localhost",
            json={
                "username": "package7-test-owner",
                "password": "package7-test-password",
            },
        )
        self.assertEqual(response.status_code, 200)
        session_cookie = response.headers["Set-Cookie"]
        self.assertIn("Secure", session_cookie)
        self.assertIn("HttpOnly", session_cookie)
        self.assertIn("SameSite=Strict", session_cookie)

    def test_paid_author_response_survives_completion_transaction_failure(
        self,
    ) -> None:
        browser_session_id = "BRS-STAGED-RESPONSE"
        prepared = self.prepare(browser_session_id=browser_session_id)
        answer = json.dumps(candidate_envelope("短视频"), ensure_ascii=False)
        response_value = {
            "answer": answer,
            "conversation_id": "CONV-STAGED-001",
            "metadata": {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "total_price": "0.01",
                    "currency": "CNY",
                }
            },
        }

        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            @staticmethod
            def read(_limit: int) -> bytes:
                return json.dumps(response_value, ensure_ascii=False).encode("utf-8")

        chat = DifyChatClient(
            base_url="https://dify.invalid/v1",
            app_api_token="t" * 32,
            repository=self.repository,
            maximum_model_calls=40,
        )
        invocation_id = "INV-STAGED-RESPONSE-001"
        scope = self.runtime_scope(browser_session_id)
        with (
            trusted_database_scope(scope),
            runtime_browser_session(browser_session_id),
            patch("urllib.request.urlopen", return_value=Response()),
            patch.object(
                self.repository,
                "complete_dify_invocation",
                side_effect=RuntimeError("simulated completion transaction failure"),
            ),
            self.assertRaisesRegex(RuntimeError, "completion transaction failure"),
        ):
            chat.invoke(
                invocation_id=invocation_id,
                principal_id=self.principal_id,
                conversation_scope="ACCOUNT-DIYU-HQ-OFFICIAL",
                user_key="pkg7-staged-response-user",
                query="执行服务端受控的首次内部内容任务。",
                inputs={"execution_phase": "AUTHOR"},
                reuse_conversation=False,
                recovery_run_id=str(prepared["run_id"]),
            )

        with (
            trusted_database_scope(scope),
            runtime_browser_session(browser_session_id),
        ):
            recovered = self.repository.recoverable_staged_model_output(
                principal_id=self.principal_id,
                account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
            )
            self.assertIsNotNone(recovered)
            assert recovered is not None
            self.assertEqual(recovered["answer"], answer)
            self.repository.complete_dify_invocation(
                invocation_id,
                account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
                usage=dict(recovered["usage"]),
                response_digest=str(recovered["response_digest"]),
                dify_user_key=str(recovered["dify_user_key"]),
                conversation_id=str(recovered["conversation_id"]),
                persist_conversation=bool(recovered["persist_conversation"]),
            )
        finalized = self.scoped_finalize(
            str(prepared["run_id"]),
            base64.b64encode(answer.encode("utf-8")).decode("ascii"),
        )
        self.assertEqual(finalized["result_class"], "SUCCESS")
        saved = self.repository.model_run(str(prepared["run_id"]))
        self.assertEqual(saved.state, "FIRST_OUTPUT_ACCEPTED")
        self.assertNotIn("provider_response_staging", saved.payload)

    def test_received_staged_response_can_resume_without_a_second_call(self) -> None:
        browser_session_id = "BRS-RECEIVED-REPLAY"
        prepared = self.prepare(browser_session_id=browser_session_id)
        answer = json.dumps(candidate_envelope("短视频"), ensure_ascii=False)
        answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
        usage = {"total_tokens": 30, "total_price": "0.01", "currency": "CNY"}
        invocation_id = "INV-RECEIVED-REPLAY-001"
        scope = self.runtime_scope(browser_session_id)
        with (
            trusted_database_scope(scope),
            runtime_browser_session(browser_session_id),
        ):
            self.repository.reserve_dify_invocation(
                invocation_id=invocation_id,
                principal_id=self.principal_id,
                model_call_upper_bound=1,
                maximum_model_calls=40,
            )
            public_result = {"answer": answer, "usage": usage}
            response_digest = digest_object(public_result)
            self.repository.stage_dify_response(
                invocation_id,
                run_id=str(prepared["run_id"]),
                account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
                response_payload=public_result,
                response_digest=response_digest,
                dify_user_key="pkg7-received-replay-user",
                conversation_id="CONV-RECEIVED-REPLAY-001",
                persist_conversation=False,
            )
            self.repository.complete_dify_invocation(
                invocation_id,
                account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
                usage=usage,
                response_digest=response_digest,
                dify_user_key="pkg7-received-replay-user",
                conversation_id="CONV-RECEIVED-REPLAY-001",
                persist_conversation=False,
            )
            self.repository.receive_first_output(
                str(prepared["run_id"]),
                output_digest=answer_digest,
                output_size_bytes=len(answer.encode("utf-8")),
            )
            recovered = self.repository.recoverable_staged_model_output(
                principal_id=self.principal_id,
                account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
            )
            self.assertIsNotNone(recovered)
        finalized = self.scoped_finalize(
            str(prepared["run_id"]),
            base64.b64encode(answer.encode("utf-8")).decode("ascii"),
        )
        self.assertEqual(finalized["result_class"], "SUCCESS")

    def test_concurrent_budget_reservation_cannot_exceed_the_limit(self) -> None:
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        outcomes_lock = threading.Lock()

        def reserve(invocation_id: str) -> None:
            barrier.wait()
            try:
                self.repository.reserve_dify_invocation(
                    invocation_id=invocation_id,
                    principal_id=self.principal_id,
                    model_call_upper_bound=1,
                    maximum_model_calls=1,
                )
                outcome = "RESERVED"
            except ValueError as exc:
                outcome = str(exc)
            with outcomes_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=reserve, args=(f"INV-CONCURRENT-{index}",))
            for index in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(outcomes.count("RESERVED"), 1)
        self.assertEqual(
            outcomes.count("Package 7 model-call budget is exhausted"),
            1,
        )
        audit = self.repository.dify_invocation_audit()
        self.assertEqual(audit["model_call_upper_bound"], 1)

    def test_managed_migration_is_atomic_and_browser_rls_is_restrictive(self) -> None:
        deployment = (PACKAGE_ROOT / "deploy_remote.sh").read_text(encoding="utf-8")
        self.assertIn("SELECT pg_advisory_xact_lock(744970072);", deployment)
        self.assertGreaterEqual(deployment.count("AS RESTRICTIVE"), 6)
        self.assertIn("app.browser_session_id", deployment)
        self.assertIn("CREATE TABLE package7_migration_rollback_probe", deployment)
        self.assertIn("ROLLBACK;", deployment)
        self.assertIn("-e PYTHONDONTWRITEBYTECODE=1", deployment)
        self.assertIn(
            "Package 7 migration rollback probe was not rolled back",
            deployment,
        )

    def test_five_failure_classes_do_not_impersonate_material_gaps(self) -> None:
        material = self.runtime._plain_action("COLLECT_MATERIAL")
        authorization = self.runtime._plain_action("REQUEST_AUTHORIZATION")
        model = self.runtime._failure_result("MODEL_OUTPUT_CONTRACT_ERROR", "RUN-TEST")
        hard_fact = self.runtime._failure_result(
            "HARD_FACT_REFERENCE_ERROR", "RUN-TEST"
        )
        system = self.runtime._failure_result("SYSTEM_OR_PROVIDER_ERROR", "RUN-TEST")
        self.assertEqual(material["result_class"], "MATERIAL_GAP")
        self.assertTrue(material["action_card"])
        for row in (authorization, model, hard_fact, system):
            self.assertFalse(row["action_card"])
        for row in (model, hard_fact, system):
            self.assertEqual(row["run_id"], "RUN-TEST")
            self.assertNotIn("RUN-TEST", row["user_visible_text"])
        self.assertEqual(
            {
                row["result_class"]
                for row in (material, authorization, model, hard_fact, system)
            },
            {
                "MATERIAL_GAP",
                "AUTHORIZATION_OR_SCOPE_BLOCK",
                "MODEL_OUTPUT_CONTRACT_ERROR",
                "HARD_FACT_REFERENCE_ERROR",
                "SYSTEM_OR_PROVIDER_ERROR",
            },
        )

    def test_real_material_gap_and_authorization_block_are_distinct(self) -> None:
        creative_without_match = self.scoped_prepare(
            self.request(message="NO_MATCH:请创作一个轻松的门店日常故事。"),
        )
        self.assertEqual(creative_without_match["response_kind"], "MODEL_REQUIRED")
        creative_result = self.finalize(creative_without_match, "短视频")
        self.assertEqual(creative_result["result_class"], "SUCCESS")

        gap = self.scoped_prepare(
            self.request(
                message="请使用我上传的视频素材制作内容，但当前没有上传文件。"
            ),
        )
        self.assertEqual(gap["result_class"], "MATERIAL_GAP")
        self.assertIn("明确要求使用", gap["user_visible_text"])
        audio_gap = self.scoped_prepare(
            self.request(message="请分析这段未提供的录音并改写成门店话术。"),
        )
        self.assertEqual(audio_gap["result_class"], "MATERIAL_GAP")
        for generic_reference in (
            "NO_MATCH:请参考素材创作一篇轻松图文。",
            "NO_MATCH:请结合图片讲一个春日搭配故事。",
        ):
            creative = self.scoped_prepare(self.request(message=generic_reference))
            self.assertEqual(creative["response_kind"], "MODEL_REQUIRED")
        denied = self.scoped_prepare(
            self.request(account_display_name="未授权账号"),
            selected_account=False,
        )
        self.assertEqual(denied["result_class"], "AUTHORIZATION_OR_SCOPE_BLOCK")
        self.assertFalse(denied["action_card"])

    def test_chat_continuity_is_same_browser_only(self) -> None:
        first = self.scoped_prepare(
            self.request(operation="普通聊天", message="临时代号是纸舟。"),
            browser_session_id="BRS-A",
        )
        reply = {
            "reply": "已记住纸舟，它不是品牌事实。",
        }
        finalized = self.scoped_finalize(str(first["run_id"]), encoded(reply))
        self.assertEqual(finalized["user_visible_text"], reply["reply"])
        same = self.scoped_prepare(
            self.request(operation="普通聊天", message="刚才的代号是什么？"),
            browser_session_id="BRS-A",
        )
        other = self.scoped_prepare(
            self.request(operation="普通聊天", message="刚才的代号是什么？"),
            browser_session_id="BRS-B",
        )
        self.assertEqual(len(same["author_prompt"]["conversation_context"]), 1)
        self.assertEqual(other["author_prompt"]["conversation_context"], [])
        malformed = self.scoped_prepare(
            self.request(operation="普通聊天", message="不要接受额外字段。"),
            browser_session_id="BRS-A",
        )
        rejected = self.scoped_finalize(
            str(malformed["run_id"]),
            encoded({"reply": "不能放行", "server_ref": "伪造字段"}),
        )
        self.assertEqual(rejected["result_class"], "MODEL_OUTPUT_CONTRACT_ERROR")

        cross_browser = self.scoped_prepare(
            self.request(operation="普通聊天", message="只能由浏览器A完成。"),
            browser_session_id="BRS-A",
        )
        with self.assertRaises(RuntimeContractError):
            self.runtime.finalize_model_output(
                str(cross_browser["run_id"]),
                encoded({"reply": "浏览器B不应完成这条运行。"}),
                trusted_scope=self.runtime_scope("BRS-B"),
            )

    def test_same_account_candidates_and_actions_do_not_cross_browser_sessions(
        self,
    ) -> None:
        prepared = self.prepare(browser_session_id="BRS-A")
        self.finalize(prepared, "短视频")
        selected = self.scoped_prepare(
            self.request(operation="选择候选", candidate_number=1),
            browser_session_id="BRS-A",
        )
        self.assertIn("已选择", selected["user_visible_text"])
        for operation in ("选择候选", "局部修改", "导出", "查看来源"):
            updates: JsonObject = {"operation": operation}
            if operation in {"选择候选", "局部修改"}:
                updates["candidate_number"] = 1
            blocked = self.scoped_prepare(
                self.request(**updates),
                browser_session_id="BRS-B",
            )
            self.assertEqual(
                blocked["result_class"],
                "AUTHORIZATION_OR_SCOPE_BLOCK",
                operation,
            )

    def test_same_session_selection_export_and_reference_leave_activity(
        self,
    ) -> None:
        prepared = self.prepare(browser_session_id="BRS-ACTIVITY")
        self.finalize(prepared, "短视频")
        self.scoped_prepare(
            self.request(operation="选择候选", candidate_number=1),
            browser_session_id="BRS-ACTIVITY",
        )
        for operation in ("导出", "查看来源"):
            self.scoped_prepare(
                self.request(operation=operation),
                browser_session_id="BRS-ACTIVITY",
            )
        with (
            trusted_database_scope(self.runtime_scope("BRS-ACTIVITY")),
            runtime_browser_session("BRS-ACTIVITY"),
        ):
            selected = self.repository.selected_candidate(
                self.principal_id,
                "ACCOUNT-DIYU-HQ-OFFICIAL",
            )
        self.assertIsNotNone(selected)
        activities = selected.candidate_payload["runtime_activity"]
        self.assertEqual(
            [row["operation"] for row in activities],
            ["SELECT", "EXPORT", "REFERENCE_LOOKUP"],
        )

    def test_portal_two_clients_receive_distinct_sessions_and_do_not_cross(
        self,
    ) -> None:
        fake_chat = FakeDifyChatClient()
        app = create_app(self.runtime, self.repository, fake_chat)
        app.testing = True
        first = app.test_client()
        second = app.test_client()
        credentials = {
            "username": "package7-test-owner",
            "password": "package7-test-password",
        }
        login_scopes: list[TrustedDatabaseScope] = []
        start_browser_session = self.repository.start_browser_session

        def scoped_start_browser_session(**kwargs: Any) -> None:
            login_scopes.append(current_trusted_database_scope())
            start_browser_session(**kwargs)

        with patch.object(
            self.repository,
            "start_browser_session",
            side_effect=scoped_start_browser_session,
        ):
            self.assertEqual(first.post("/login", json=credentials).status_code, 200)
            self.assertEqual(second.post("/login", json=credentials).status_code, 200)
        self.assertEqual(len(login_scopes), 2)
        self.assertTrue(
            all(
                scope.tenant_id == "TENANT-DIYU-SIM-001"
                and scope.principal_id == self.principal_id
                and isinstance(scope.browser_session_id, str)
                and scope.browser_session_id.startswith("BRS-")
                for scope in login_scopes
            )
        )
        self.assertNotEqual(
            login_scopes[0].browser_session_id,
            login_scopes[1].browser_session_id,
        )
        sessions = self.repository.active_browser_sessions(self.principal_id)
        self.assertEqual(len(sessions), 2)
        payload = {
            "account_display_name": "笛语童装",
            "operation": "随便聊聊",
            "message": "先记住当前浏览器里的纸舟。",
        }
        response = first.post(
            "/v1/portal/chat",
            json=payload,
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(response.status_code, 200)
        payload["message"] = "刚才说了什么？"
        response = second.post(
            "/v1/portal/chat",
            json=payload,
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(response.status_code, 200)
        author_calls = [
            row
            for row in fake_chat.calls
            if row["inputs"]["execution_phase"] == "AUTHOR"
        ]
        second_prompt = json.loads(author_calls[-1]["inputs"]["author_prompt"])
        self.assertEqual(second_prompt["conversation_context"], [])

    def test_portal_recovers_staged_output_before_any_new_model_call(self) -> None:
        fake_chat = FakeDifyChatClient()
        app = create_app(self.runtime, self.repository, fake_chat)
        app.testing = True
        client = app.test_client()
        browser_sessions: list[str] = []
        start_browser_session = self.repository.start_browser_session

        def capture_browser_session(**kwargs: Any) -> None:
            browser_sessions.append(str(kwargs["browser_session_id"]))
            start_browser_session(**kwargs)

        with patch.object(
            self.repository,
            "start_browser_session",
            side_effect=capture_browser_session,
        ):
            self.assertEqual(
                client.post(
                    "/login",
                    json={
                        "username": "package7-test-owner",
                        "password": "package7-test-password",
                    },
                ).status_code,
                200,
            )
        browser_session_id = browser_sessions[0]
        prepared = self.prepare(browser_session_id=browser_session_id)
        answer = json.dumps(candidate_envelope("短视频"), ensure_ascii=False)
        public_result = {"answer": answer, "usage": {"total_tokens": 30}}
        invocation_id = "INV-PORTAL-RECOVERY-001"
        with (
            trusted_database_scope(self.runtime_scope(browser_session_id)),
            runtime_browser_session(browser_session_id),
        ):
            self.repository.reserve_dify_invocation(
                invocation_id=invocation_id,
                principal_id=self.principal_id,
                model_call_upper_bound=1,
                maximum_model_calls=40,
            )
            self.repository.stage_dify_response(
                invocation_id,
                run_id=str(prepared["run_id"]),
                account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
                response_payload=public_result,
                response_digest=digest_object(public_result),
                dify_user_key="pkg7-portal-recovery-user",
                conversation_id="CONV-PORTAL-RECOVERY-001",
                persist_conversation=False,
            )
        response = client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "笛语童装",
                "operation": "随便聊聊",
                "message": "这次请求必须先恢复已付费结果。",
            },
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("方案1", response.get_json()["answer"])
        self.assertEqual(fake_chat.calls, [])
        saved = self.repository.model_run(str(prepared["run_id"]))
        self.assertEqual(saved.state, "FIRST_OUTPUT_ACCEPTED")
        self.assertNotIn("provider_response_staging", saved.payload)

    def test_portal_unauthenticated_and_cross_account_requests_are_isolated(
        self,
    ) -> None:
        fake_chat = FakeDifyChatClient()
        app = create_app(self.runtime, self.repository, fake_chat)
        app.testing = True
        client = app.test_client()
        self.assertEqual(client.get("/v1/portal/options").status_code, 401)
        credentials = {
            "username": "package7-test-owner",
            "password": "package7-test-password",
        }
        self.assertEqual(client.post("/login", json=credentials).status_code, 200)
        response = client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "林知远｜笛语",
                "operation": "直接做内容",
                "topic_label": "商品为什么这样设计",
                "message": "尝试访问另一个真实存在但未授权的账号。",
            },
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("确认使用权限", response.get_json()["answer"])
        self.assertEqual(fake_chat.calls, [])

    def test_logout_revokes_the_persisted_browser_session(self) -> None:
        app = create_app(self.runtime, self.repository, FakeDifyChatClient())
        app.testing = True
        client = app.test_client()
        credentials = {
            "username": "package7-test-owner",
            "password": "package7-test-password",
        }
        self.assertEqual(client.post("/login", json=credentials).status_code, 200)
        sessions = self.repository.active_browser_sessions(self.principal_id)
        self.assertEqual(len(sessions), 1)
        response = client.post(
            "/logout",
            headers={"X-Diyu-Portal": "same-origin-v1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.repository.active_browser_sessions(self.principal_id), ())

    def test_numeric_range_normalization_is_narrow(self) -> None:
        corpus = "尺码范围为100厘米至150厘米。"
        self.assertTrue(protected_detail_is_supported("100cm-150cm", corpus))
        self.assertFalse(protected_detail_is_supported("100cm-160cm", corpus))

    def test_readiness_and_historical_core_numbers_are_not_runtime_outputs(
        self,
    ) -> None:
        serialized = json.dumps(
            self.runtime.portal_options(self.principal_id), ensure_ascii=False
        )
        for value in (
            "production_ready",
            "release_ready",
            "generation_allowed",
            '"300"',
            '"120"',
            '"86"',
        ):
            self.assertNotIn(value, serialized)


if __name__ == "__main__":
    unittest.main()
