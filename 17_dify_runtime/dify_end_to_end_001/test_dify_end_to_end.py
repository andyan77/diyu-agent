#!/usr/bin/env python3
"""Deterministic acceptance and adversarial tests for the current Package 7."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
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
                    "camera": "固定近景后切中景。",
                    "audio": text,
                    "subtitle": "先看选择，再讲理由。",
                },
                {
                    "visual": "建议以同一对象的细节收束，不冒充既有影像。",
                    "camera": "稳定特写。",
                    "audio": "结论只停在当前资料范围。",
                    "subtitle": "资料之外，保持待确认。",
                },
            ],
            "shooting_notes": ["使用未来、示意或条件性画面。"],
            "editing_notes": ["保留自然停顿，不用夸张转场。"],
        }
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

    def test_seed_and_single_runtime_foundation_remain_complete(self) -> None:
        self.assertEqual(self.seed["content_account_count"], 11)
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
            "商品属性或功效、价格、库存、尺寸、授权表述、企业承诺",
            prompt["system"],
        )
        self.assertIn("没有检索资料也要", prompt["system"])
        self.assertIn(
            "只是可选创作参考，不是逐句真值证明",
            prompt["author_materials"]["instruction"],
        )
        self.assertIn("都可作为待人审正文创作", serialized)
        self.assertIn("不授予任何登录或数据访问权限", serialized)
        self.assertNotIn("逐句绑定", serialized)
        self.assertNotIn("required_candidate_count", serialized)
        self.assertEqual(contract["root_fields"]["candidates"], "1至3份；每份按candidate_schema填写")

    def test_public_capability_mapping_exposes_ten_topics_and_seven_formats(
        self,
    ) -> None:
        options = self.runtime.portal_options(self.principal_id)
        self.assertEqual(options["content_formats"], list(CONTENT_FORMATS))
        portal_javascript = (PACKAGE_ROOT / "portal.js").read_text(encoding="utf-8")
        self.assertIn('value === "门店线下物料"', portal_javascript)
        self.assertIn("（暂未开放）", portal_javascript)
        self.assertIn("option.disabled = temporarilyUnavailable", portal_javascript)
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

    def test_all_seven_formats_finalize_select_review_export_and_reference(
        self,
    ) -> None:
        for content_format in CONTENT_FORMATS:
            with self.subTest(content_format=content_format):
                prepared = self.prepare(content_format)
                result = self.finalize(prepared, content_format)
                self.assertEqual(result["result_class"], "SUCCESS")
                self.assertNotIn("CP06", result["user_visible_text"])
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
                for operation in ("审核", "导出", "查看来源"):
                    response = self.scoped_prepare(
                        self.request(operation=operation),
                    )
                    self.assertEqual(response["response_kind"], "DIRECT")
                    self.assertNotIn("PKG5-FRAGMENT", response["user_visible_text"])

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

    def test_creative_claims_enter_human_review_without_evidence_binding(
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

    def test_one_valid_candidate_is_delivered_with_option_warning(
        self,
    ) -> None:
        prepared = self.prepare()
        envelope = candidate_envelope("短视频")
        del envelope["candidates"][0]["deliverable"]
        result = self.finalize(prepared, "短视频", envelope=envelope)
        self.assertEqual(result["result_class"], "SUCCESS")
        self.assertEqual(result["candidate_option_warning"], "本轮可选方案不足")
        self.assertIn("本轮可选方案不足", result["user_visible_text"])
        run = self.repository.model_run(str(prepared["run_id"]))
        self.assertEqual(run.payload["accepted_candidate_count"], 1)
        self.assertEqual(run.payload["candidate_option_warning"], "本轮可选方案不足")
        self.assertEqual(run.state, "FIRST_OUTPUT_ACCEPTED")
        selected = self.scoped_prepare(
            self.request(operation="选择候选", candidate_number=1),
        )
        self.assertIn("已选择", selected["user_visible_text"])
        for operation in ("审核", "导出"):
            response = self.scoped_prepare(self.request(operation=operation))
            self.assertEqual(response["response_kind"], "DIRECT")

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

        fragmented_prepared = self.prepare("短视频")
        fragmented_candidates = candidate_envelope("短视频")["candidates"]
        for candidate in fragmented_candidates:
            candidate["editing_notes"] = candidate["deliverable"].pop(
                "editing_notes"
            )
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
        fragmented_run = self.repository.model_run(
            str(fragmented_prepared["run_id"])
        )
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
        self.assertEqual(bare_candidate_result["result_class"], "SUCCESS")
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

    def test_similarity_is_a_review_hint_not_a_runtime_rejection(self) -> None:
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
        hints = candidates[0].candidate_payload["evidence_panel"][
            "similarity_review_hints"
        ]
        self.assertTrue(hints[0]["review_required"])
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
        for operation in ("选择候选", "局部修改", "审核", "导出", "查看来源"):
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

    def test_same_session_selection_review_export_and_reference_leave_activity(
        self,
    ) -> None:
        prepared = self.prepare(browser_session_id="BRS-ACTIVITY")
        self.finalize(prepared, "短视频")
        self.scoped_prepare(
            self.request(operation="选择候选", candidate_number=1),
            browser_session_id="BRS-ACTIVITY",
        )
        for operation in ("审核", "导出", "查看来源"):
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
            ["SELECT", "REVIEW", "EXPORT", "REFERENCE_LOOKUP"],
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

    def test_portal_unauthorized_account_is_not_reported_as_system_failure(
        self,
    ) -> None:
        fake_chat = FakeDifyChatClient()
        app = create_app(self.runtime, self.repository, fake_chat)
        app.testing = True
        client = app.test_client()
        credentials = {
            "username": "package7-test-owner",
            "password": "package7-test-password",
        }
        self.assertEqual(client.post("/login", json=credentials).status_code, 200)
        response = client.post(
            "/v1/portal/chat",
            json={
                "account_display_name": "未授权账号",
                "operation": "直接做内容",
                "topic_label": "商品为什么这样设计",
                "message": "尝试访问未授权账号。",
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
