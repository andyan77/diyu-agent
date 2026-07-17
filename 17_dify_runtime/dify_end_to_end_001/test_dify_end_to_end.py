#!/usr/bin/env python3
"""Deterministic Package 7 acceptance and adversarial tests."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

from contracts import BridgePrepareRequest, ModelEnvelope, PortalTaskRequest
from bridge_app import _selected_product, create_app, selected_account_database_scope
from brand_import import BrandImportBundle, load_simulation_bundle, preflight_brand_bundle
from dify_chat import DifyChatClient
from dify_knowledge import DifyKnowledgeClient
from persistence import (
    RuntimeRepository,
    SqlAlchemyPlanStore,
    create_runtime_engine,
    create_session_factory,
)
from provision_dify import _content_sha256, _dify_import_text
from runtime_retrieval import RuntimeBrandFactRetrievalService
from runtime_service import Package7Runtime, protected_detail_is_supported
from security import hash_password, issue_session, verify_password, verify_session
from seed_runtime import seed_database


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
P6_CASES = (
    REPOSITORY_ROOT
    / "16_composition_runtime/fact_aware_plan_adapter_001/fixtures/integration_cases.v1.jsonl"
)
DSL_PATH = PACKAGE_ROOT / "dify_app.v1.yaml"


class DifyMaterializationCompatibilityTests(unittest.TestCase):
    def test_dify_import_removes_only_the_outer_presentation_heading(self) -> None:
        source = "## 资料范围\r\n字段A：保留。\r\n## 内部原文标题"
        self.assertEqual(
            _dify_import_text(source),
            "资料范围\n字段A：保留。\n## 内部原文标题",
        )

    def test_dify_import_does_not_hide_semantic_mutation(self) -> None:
        source = "# 资料范围\n字段A：保留。"
        mutated = "# 资料范围\n字段A：改变。"
        self.assertNotEqual(
            _content_sha256(_dify_import_text(source)),
            _content_sha256(_dify_import_text(mutated)),
        )


class FakeKnowledgeClient:
    def __init__(self, repository: RuntimeRepository) -> None:
        self.repository = repository
        self.requests: list[JsonObject] = []

    def retrieve(self, *, query: str, scope: JsonObject, query_at: str, limit: int) -> JsonObject:
        self.requests.append(
            {"query": query, "scope": copy.deepcopy(scope), "query_at": query_at, "limit": limit}
        )
        if not query.strip():
            return {"results": [], "usage": {}, "prefilter_applied": True}
        terms = {query.replace(" ", "")[index : index + 2] for index in range(max(0, len(query) - 1))}
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
            document_id = f"DOC-{row['fragment_id']}"
            results.append(
                {
                    "metadata": {"document_id": document_id, "score": 1.0},
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
        return {
            "answer": json.dumps(
                {
                    "kind": "CHAT_REPLY",
                    "reply": "已从Dify内部编排返回。",
                    "candidates": [],
                },
                ensure_ascii=False,
            ),
            "usage": {"total_tokens": 12},
        }


class Package7Tests(unittest.TestCase):
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
        retrieval = RuntimeBrandFactRetrievalService(self.repository, self.knowledge)
        self.runtime = Package7Runtime(
            self.repository,
            SqlAlchemyPlanStore(self.sessions),
            retrieval,
        )
        self.principal_id = "SIM-LOGIN-DIYU-ACCEPTANCE-001"

    def tearDown(self) -> None:
        self.engine.dispose()
        self.tempdir.cleanup()

    @staticmethod
    def request(**updates: Any) -> BridgePrepareRequest:
        payload = {
            "session_token": "x" * 64,
            "account_display_name": "笛语童装",
            "operation": "确认制作",
            "topic_label": "用户问题与理性选择",
            "selected_content_product_id": "CP06",
            "primary_audience": "正在为孩子判断尺码的家长",
            "message": "尺码不能只看身高，请讲清还要观察什么",
            "target_platform": "内部图文测试",
        }
        payload.update(updates)
        return BridgePrepareRequest.model_validate(payload)

    def test_seed_is_idempotent_and_complete(self) -> None:
        self.assertEqual(self.seed["principal_count"], 1)
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
        self.assertEqual(second["content_account_count"], 11)
        self.assertTrue(all(row.dify_document_id for row in self._fragment_rows()))

    def test_selected_account_installs_all_database_scope_dimensions(self) -> None:
        _, account = self.repository.require_active_scope(
            self.principal_id,
            "ACCOUNT-DIYU-HQ-OFFICIAL",
        )
        scope = selected_account_database_scope(
            trusted_tenant_id="TENANT-DIYU-SIM-001",
            principal_id=self.principal_id,
            account=account,
        )
        self.assertEqual(scope.tenant_id, account.tenant_id)
        self.assertEqual(scope.brand_id, account.brand_id)
        self.assertEqual(scope.organization_id, account.organization_id)
        self.assertEqual(scope.store_id, account.store_id)
        self.assertEqual(scope.account_id, account.account_id)
        self.assertEqual(scope.principal_id, self.principal_id)
        with self.assertRaisesRegex(ValueError, "outside the trusted tenant"):
            selected_account_database_scope(
                trusted_tenant_id="TENANT-OTHER",
                principal_id=self.principal_id,
                account=account,
            )

    def test_password_and_signed_session_fail_closed(self) -> None:
        encoded = hash_password("a-secure-package7-password", salt=b"fixed-test-salt-01")
        self.assertTrue(verify_password("a-secure-package7-password", encoded))
        self.assertFalse(verify_password("wrong-package7-password", encoded))
        token = issue_session(
            principal_id=self.principal_id,
            allowed_account_ids=["ACCOUNT-DIYU-HQ-OFFICIAL"],
            signing_key="s" * 32,
            now=100,
        )
        self.assertEqual(verify_session(token, "s" * 32, now=101)["principal_id"], self.principal_id)
        with self.assertRaises(ValueError):
            verify_session(f"{token}x", "s" * 32, now=101)
        with self.assertRaises(ValueError):
            verify_session(token, "s" * 32, now=4_000)

    def test_ordinary_chat_does_not_retrieve_or_create_plan(self) -> None:
        result = self.runtime.prepare(
            self.request(
                operation="普通聊天",
                topic_label=None,
                selected_content_product_id=None,
                primary_audience=None,
                message="今天有点忙，先聊两句。",
            ),
            self.principal_id,
        )
        self.assertEqual(result["response_kind"], "MODEL_REQUIRED")
        self.assertEqual(self.knowledge.requests, [])
        run = self.repository.model_run(result["run_id"])
        self.assertIsNotNone(run)
        self.assertIsNone(run.plan_ref if run else "unexpected")
        self.assertFalse(run.payload["private_retrieval_performed"] if run else True)

    def test_chat_continuity_uses_only_accepted_sanitized_account_history(self) -> None:
        first = self.runtime.prepare(
            self.request(operation="普通聊天", message="临时代号是纸舟。"),
            self.principal_id,
        )
        self.runtime.finalize_model_output(
            first["run_id"],
            base64.b64encode(
                json.dumps(
                    {
                        "kind": "CHAT_REPLY",
                        "reply": "已记住纸舟，它不是品牌事实。",
                        "candidates": [],
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            ).decode("ascii"),
        )
        second = self.runtime.prepare(
            self.request(operation="普通聊天", message="继续上一轮。"),
            self.principal_id,
        )
        self.assertEqual(
            second["author_prompt"]["conversation_context"],
            [
                {
                    "user_message": "临时代号是纸舟。",
                    "assistant_reply": "已记住纸舟，它不是品牌事实。",
                }
            ],
        )
        self.assertIn("不得要求用户重复提供", second["author_prompt"]["system"])
        other_account = self.runtime.prepare(
            self.request(
                account_display_name="笛语苏州园区店",
                operation="普通聊天",
                message="这里不应看到上一账号历史。",
            ),
            self.principal_id,
        )
        self.assertEqual(other_account["author_prompt"]["conversation_context"], [])

    def test_dify_dataset_retrieval_uses_server_owned_filter_contract(self) -> None:
        captured: dict[str, Any] = {}

        class Response:
            def __enter__(self) -> BytesIO:
                return BytesIO(b'{"query":{"content":"test"},"records":[]}')

            def __exit__(self, *_args: object) -> None:
                return None

        def fake_open(request: Any, *, timeout: float) -> Response:
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return Response()

        client = DifyKnowledgeClient(
            base_url="http://dify-api/v1",
            dataset_api_token="ds-" + "k" * 32,
            dataset_id="33333333-3333-3333-3333-333333333333",
        )
        with patch("urllib.request.urlopen", side_effect=fake_open):
            result = client.retrieve(
                query="尺码判断",
                scope={
                    "tenant_id": "TENANT-DIYU-SIM-001",
                    "brand_id": "BRAND-DIYU-SIM-001",
                    "principal_id": self.principal_id,
                    "content_account_id": "ACCOUNT-DIYU-HQ-OFFICIAL",
                    "organization_id": "ORG-DIYU-HQ",
                    "store_id": None,
                },
                query_at="2026-07-15T00:00:00Z",
                limit=3,
            )
        self.assertEqual(result["results"], [])
        self.assertNotIn(self.principal_id, json.dumps(captured["payload"]))
        self.assertIn(
            "metadata_filtering_conditions",
            captured["payload"]["retrieval_model"],
        )

    def test_creation_calls_runtime_retrieval_package6_and_package2(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        self.assertEqual(prepared["response_kind"], "MODEL_REQUIRED")
        self.assertEqual(len(self.knowledge.requests), 1)
        run = self.repository.model_run(prepared["run_id"])
        self.assertIsNotNone(run)
        self.assertIsNotNone(run.plan_ref if run else None)
        audit = self.runtime.adapter.call_audit
        self.assertEqual(audit["package5_retrieve"], 1)
        self.assertEqual(audit["package2_prepare"], 1)
        materials = prepared["author_prompt"]["author_materials"]
        self.assertGreater(len(materials["scoped_retrieval_fragments"]), 0)
        self.assertFalse(materials["persisted"])
        guidance = prepared["author_prompt"]["task_brief"]["brand_guidance"]
        self.assertNotIn("evidence_refs", json.dumps(guidance, ensure_ascii=False))
        self.assertNotIn("source_refs", json.dumps(guidance, ensure_ascii=False))
        self.assertIn("历史事件没有现成影像", prepared["author_prompt"]["system"])
        self.assertIn("不得把未提供的照片", prepared["author_prompt"]["system"])
        self.assertIn("陈列资料没有明确商品颜色", prepared["author_prompt"]["system"])
        self.assertIn("所有文字都不得显示来源编号", prepared["author_prompt"]["system"])
        self.assertIn("不得把未提供的信息写成已经存在", prepared["author_prompt"]["system"])
        self.assertIn("人物动作、拍摄和剪辑建议可以创意新写", prepared["author_prompt"]["system"])
        self.assertIn("有限等价格式转换", prepared["author_prompt"]["system"])
        self.assertIn("普通标题、正文、口播、分镜和拍摄建议不需要逐项绑定", prepared["author_prompt"]["system"])
        self.assertIn("只作为可选创作建议", prepared["author_prompt"]["system"])
        self.assertNotIn("三份候选必须依次使用", prepared["author_prompt"]["system"])
        self.assertNotIn("不得补写数字、人物、动作、因果、结果", prepared["author_prompt"]["system"])
        self.assertNotIn("必须逐字写明‘待补拍’或‘待取得’", prepared["author_prompt"]["system"])
        self.assertEqual(
            prepared["author_prompt"]["output_contract"]["candidates"][0]["claim_bindings"],
            [],
        )

    def test_named_storyline_and_column_override_defaults(self) -> None:
        prepared = self.runtime.prepare(
            self.request(
                account_display_name="笛语童装",
                topic_label="用户问题与理性选择",
                selected_content_product_id="CP06",
                speaker_role_name="品牌价值判断者",
                storyline_name="门店、陈列与服务的真实条件",
                column_name="门店调整前后",
                content_format="图文",
                message="尺码判断还要观察真实试穿和活动状态。",
            ),
            self.principal_id,
        )
        self.assertEqual(prepared["response_kind"], "MODEL_REQUIRED")
        task_brief = prepared["author_prompt"]["task_brief"]
        self.assertEqual(task_brief["storyline"], "门店、陈列与服务的真实条件")
        self.assertEqual(task_brief["column"], "门店调整前后")

    def test_first_model_output_is_preserved_and_cannot_reroll(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        materials = prepared["author_prompt"]["author_materials"]
        refs = materials["retrieval_fragment_refs"][:1]
        envelope = {
            "kind": "CANDIDATE_SET",
            "reply": None,
            "candidates": [
                self._candidate(
                    "从判断问题进入",
                    "先看身高之外的观察条件。",
                    refs,
                    ["核心创意", "事实或证明路径"],
                ),
                self._candidate(
                    "从试穿观察进入",
                    "把判断留给真实试穿与观察。",
                    refs,
                    ["切入问题或场景", "画面组织方法"],
                ),
            ],
        }
        encoded = base64.b64encode(json.dumps(envelope, ensure_ascii=False).encode("utf-8")).decode("ascii")
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertEqual(result["response_kind"], "DIRECT")
        self.assertIn("推荐候选", result["user_visible_text"])
        run = self.repository.model_run(prepared["run_id"])
        self.assertTrue(run.first_output_preserved if run else False)
        self.assertIn("prompt", run.payload if run else {})
        with self.assertRaises(ValueError):
            self.runtime.finalize_model_output(prepared["run_id"], encoded)

    def test_ordinary_creative_surfaces_do_not_require_claim_bindings(self) -> None:
        creative_cases = (
            ("title", "三件衣服，拍出一个春天"),
            (
                "execution_payload.video.shots[0].visual",
                "建议拍一件红色上衣放在画面中央",
            ),
            (
                "execution_payload.video.shots[0].action",
                "如有已授权出镜的孩子，可以试穿后在镜头前转身",
            ),
            (
                "execution_payload.video.shots[0].camera",
                "镜头从左向右缓慢移动",
            ),
            (
                "execution_payload.video.shooting_notes[0]",
                "如有条件，可拍摄一幅示意画面",
            ),
        )
        for surface_path, creative_text in creative_cases:
            with self.subTest(surface_path=surface_path, creative_text=creative_text):
                prepared = self.runtime.prepare(self.request(), self.principal_id)
                refs = prepared["author_prompt"]["author_materials"][
                    "retrieval_fragment_refs"
                ][:1]
                candidates = [
                    self._candidate(
                        "证据路径",
                        "只使用当前资料支持的观察。",
                        refs,
                        ["核心创意", "事实或证明路径"],
                    ),
                    self._candidate(
                        "问题路径",
                        "只回答当前资料支持的问题。",
                        refs,
                        ["切入问题或场景", "画面组织方法"],
                    ),
                ]
                if surface_path == "title":
                    candidates[0]["surfaces"]["title"] = creative_text
                elif surface_path.endswith("visual"):
                    candidates[0]["surfaces"]["execution_payload"]["video"]["shots"][0][
                        "visual"
                    ] = creative_text
                elif surface_path.endswith("action"):
                    candidates[0]["surfaces"]["execution_payload"]["video"]["shots"][0][
                        "action"
                    ] = creative_text
                elif surface_path.endswith("camera"):
                    candidates[0]["surfaces"]["execution_payload"]["video"]["shots"][0][
                        "camera"
                    ] = creative_text
                else:
                    candidates[0]["surfaces"]["execution_payload"]["video"][
                        "shooting_notes"
                    ][0] = creative_text
                candidates[0]["claim_bindings"] = [
                    row
                    for row in candidates[0]["claim_bindings"]
                    if row["surface_path"] != surface_path
                ]
                encoded = base64.b64encode(
                    json.dumps(
                        {
                            "kind": "CANDIDATE_SET",
                            "reply": None,
                            "candidates": candidates,
                        },
                        ensure_ascii=False,
                    ).encode()
                ).decode()
                result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
                self.assertIn("推荐候选", result["user_visible_text"])
                run = self.repository.model_run(prepared["run_id"])
                self.assertEqual(run.state if run else None, "FIRST_OUTPUT_ACCEPTED")

    def test_unbound_key_number_on_a_spoken_surface_is_rejected(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"]
        size_ref = next(ref for ref in refs if ref == "PKG5-FRAGMENT-BD-NARR-02-006")
        candidates = [
            self._candidate(
                "尺码证据",
                "笛语商品使用100厘米至150厘米的常用尺码范围。",
                [size_ref],
                ["核心创意", "事实或证明路径"],
            ),
            self._candidate(
                "问题路径",
                "只回答当前资料支持的问题。",
                [size_ref],
                ["切入问题或场景", "画面组织方法"],
            ),
        ]
        candidates[0]["claim_bindings"] = [
            row
            for row in candidates[0]["claim_bindings"]
            if row["surface_path"] != "spoken_lines[0]"
        ]
        encoded = base64.b64encode(
            json.dumps(
                {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
                ensure_ascii=False,
            ).encode()
        ).decode()
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertTrue(result.get("action_card"))
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(run.state if run else None, "FIRST_OUTPUT_REJECTED")

    def test_unbound_factual_claim_patterns_and_mixed_disclosures_fail_closed(self) -> None:
        claims = (
            "这件上衣采用纯棉面料",
            "这件上衣采用亚麻面料",
            "本店库存充足",
            "这件样衣采用双重厚度",
            "这款商品采用薄针织",
            "这款商品售价九十九元",
            "总部批准本账号发布新品信息",
            "门店上周举办了春季活动",
            "门店备有样衣可供拍摄",
            "尺码100cm-150cm，细节待确认",
            "现有库存100件，细节待确认",
            "已授权发布，当前内容不可发布",
            "这名儿童已经获准出镜",
            "企业已经承诺本月完成调整",
            "已有顾客照片，库存待确认",
            "已有视频可直接使用",
            "镜头展示本店库存充足",
            "如有已授权出镜人员这款上衣采用纯棉面料",
            "待补拍；现有样衣已经确认100厘米",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                prepared = self.runtime.prepare(self.request(), self.principal_id)
                refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
                candidates = [
                    self._candidate(
                        "事实探针甲",
                        "只使用当前资料支持的观察。",
                        refs,
                        ["核心创意", "事实或证明路径"],
                    ),
                    self._candidate(
                        "事实探针乙",
                        "只回答当前资料支持的问题。",
                        refs,
                        ["切入问题或场景", "画面组织方法"],
                    ),
                ]
                candidates[0]["surfaces"]["title"] = claim
                candidates[0]["claim_bindings"] = [
                    row
                    for row in candidates[0]["claim_bindings"]
                    if row["surface_path"] != "title"
                ]
                encoded = base64.b64encode(
                    json.dumps(
                        {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
                        ensure_ascii=False,
                    ).encode()
                ).decode()

                result = self.runtime.finalize_model_output(prepared["run_id"], encoded)

                self.assertTrue(result.get("action_card"))
                run = self.repository.model_run(prepared["run_id"])
                self.assertEqual(run.state if run else None, "FIRST_OUTPUT_REJECTED")

        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        candidates = [
            self._candidate(
                "普通拍摄建议",
                "只使用当前资料支持的观察。",
                refs,
                ["核心创意", "画面组织方法"],
            ),
            self._candidate(
                "普通问题建议",
                "只回答当前资料支持的问题。",
                refs,
                ["切入问题或场景", "叙事视角"],
            ),
        ]
        fact_path = "execution_payload.video.shots[0].visual"
        candidates[0]["surfaces"]["execution_payload"]["video"]["shots"][0][
            "visual"
        ] = "拍摄时使用已有样衣"
        candidates[0]["claim_bindings"] = [
            row
            for row in candidates[0]["claim_bindings"]
            if row["surface_path"] != fact_path
        ]
        encoded = base64.b64encode(
            json.dumps(
                {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
                ensure_ascii=False,
            ).encode()
        ).decode()

        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)

        self.assertTrue(result.get("action_card"))
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(run.state if run else None, "FIRST_OUTPUT_REJECTED")

    def test_similarity_and_narrative_skeleton_are_review_hints_not_runtime_blocks(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        first = self._candidate(
            "证据路径甲",
            "只使用当前资料支持的观察。",
            refs,
            ["核心创意", "事实或证明路径"],
            architecture="EVIDENCE_FIRST",
        )
        second = copy.deepcopy(first)
        second["difference_label"] = "问题路径乙"
        second["narrative_architecture"] = "QUESTION_ANSWER"
        second["surfaces"]["title"] = "问题路径乙"
        next(
            row for row in second["claim_bindings"] if row["surface_path"] == "title"
        )["exact_text"] = "问题路径乙"
        first.pop("narrative_architecture")
        second.pop("narrative_architecture")
        encoded = base64.b64encode(
            json.dumps(
                {"kind": "CANDIDATE_SET", "reply": None, "candidates": [first, second]},
                ensure_ascii=False,
            ).encode()
        ).decode()
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertIn("推荐候选", result["user_visible_text"])
        run = self.repository.model_run(prepared["run_id"])
        hints = run.payload["similarity_review_hints"] if run else []
        self.assertTrue(hints)
        self.assertTrue(hints[0]["review_required"])
        self.assertFalse(hints[0]["runtime_rejection"])

    def test_fixed_candidate_envelope_normalization_does_not_change_content(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        candidates = [
            self._candidate(
                "证据先行",
                "只使用当前材料支持的观察。",
                refs,
                ["核心创意", "事实或证明路径"],
            ),
            self._candidate(
                "动作先行",
                "只使用当前材料支持的另一路径。",
                refs,
                ["切入问题或场景", "画面组织方法"],
            ),
        ]
        raw = json.dumps({"candidates": candidates}, ensure_ascii=False)
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertEqual(result["response_kind"], "DIRECT")
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(
            run.payload["model_wrapper_normalization"] if run else None,
            "NONE+ADDED_FIXED_CANDIDATE_ENVELOPE",
        )
        self.assertEqual(
            run.payload["envelope"]["candidates"] if run else None,
            candidates,
        )

    def test_video_note_relocation_is_narrow_and_audited(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        candidates = [
            self._candidate(
                "镜头证据",
                "只使用当前资料支持的镜头路径。",
                refs,
                ["核心创意", "画面组织方法"],
            ),
            self._candidate(
                "观察证据",
                "只使用当前资料支持的观察路径。",
                refs,
                ["叙事视角", "事实或证明路径"],
            ),
        ]
        for candidate in candidates:
            production = candidate["surfaces"]["execution_payload"]
            video = production["video"]
            production["shooting_notes"] = video.pop("shooting_notes")
            production["editing_notes"] = video.pop("editing_notes")
        raw = json.dumps(
            {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
            ensure_ascii=False,
        )
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertEqual(result["response_kind"], "DIRECT")
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(
            run.payload["model_wrapper_normalization"] if run else None,
            "NONE+RELOCATED_VIDEO_NOTES",
        )

    def test_closed_provider_aliases_are_normalized_without_expanding_scope(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        candidates = [
            self._candidate(
                "问题路径",
                "从当前问题进入。",
                refs,
                ["切入问题或场景", "画面组织方法"],
            ),
            self._candidate(
                "证据路径",
                "从当前证据进入。",
                refs,
                ["核心创意", "事实或证明路径"],
            ),
        ]
        candidates[0]["difference_dimensions"][0] = "切入问题"
        candidates[1]["difference_dimensions"][0] = "核心创意：从证据进入"
        candidates[0]["surfaces"]["CTA"] = ""
        for candidate in candidates:
            candidate["used_fact_refs"] = list(refs)
        encoded = base64.b64encode(
            json.dumps(
                {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
                ensure_ascii=False,
            ).encode("utf-8")
        ).decode("ascii")
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertIn("推荐候选", result["user_visible_text"])
        run = self.repository.model_run(prepared["run_id"])
        normalization = run.payload["model_wrapper_normalization"] if run else ""
        self.assertIn("NORMALIZED_EXACT_DIFFERENCE_DIMENSION_ALIAS", normalization)
        self.assertIn("REMOVED_DIFFERENCE_DIMENSION_DETAIL_SUFFIX", normalization)
        self.assertIn("REMOVED_DUPLICATE_MATERIAL_REF_FROM_FACT_REFS", normalization)
        self.assertIn("COPIED_EXISTING_ENDING_AND_ACTION_TO_EMPTY_CTA", normalization)
        from runtime_models import RuntimeCandidate

        with self.sessions() as session:
            rows = session.query(RuntimeCandidate).filter_by(run_id=prepared["run_id"]).all()
            self.assertEqual([row.used_fact_refs for row in rows], [[], []])

    def test_execution_payload_claim_path_prefix_is_narrowly_normalized(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        candidates = [
            self._candidate(
                "证据路径",
                "从当前证据进入。",
                refs,
                ["核心创意", "事实或证明路径"],
            ),
            self._candidate(
                "问题路径",
                "从当前问题进入。",
                refs,
                ["切入问题或场景", "画面组织方法"],
            ),
        ]
        for candidate in candidates:
            binding = next(
                row
                for row in candidate["claim_bindings"]
                if row["surface_path"] == "execution_payload.story_or_full_script"
            )
            binding["surface_path"] = "story_or_full_script"
            spoken = next(
                row
                for row in candidate["claim_bindings"]
                if row["surface_path"] == "spoken_lines[0]"
            )
            spoken["surface_path"] = "spoken_lines"
        encoded = base64.b64encode(
            json.dumps(
                {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
                ensure_ascii=False,
            ).encode()
        ).decode()
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertIn("推荐候选", result["user_visible_text"])
        run = self.repository.model_run(prepared["run_id"])
        self.assertIn(
            "PREFIXED_EXECUTION_PAYLOAD_CLAIM_PATH",
            run.payload["model_wrapper_normalization"] if run else "",
        )
        self.assertIn(
            "INDEXED_SINGLETON_SPOKEN_LINE_CLAIM_PATH",
            run.payload["model_wrapper_normalization"] if run else "",
        )

    def test_parse_rejected_output_revalidation_keeps_exact_provider_evidence(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        candidates = [
            self._candidate(
                "问题路径",
                "从当前问题进入。",
                refs,
                ["切入问题或场景", "画面组织方法"],
            ),
            self._candidate(
                "证据路径",
                "从当前证据进入。",
                refs,
                ["核心创意", "事实或证明路径"],
            ),
        ]
        candidates[0]["difference_dimensions"][0] = "切入问题"
        for candidate in candidates:
            candidate["used_fact_refs"] = list(refs)
        provider_json = json.dumps(
            {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
            ensure_ascii=False,
        )
        raw = f"<think>private provider reasoning</think>{provider_json}"
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        encoded_digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        self.repository.preserve_first_output(
            prepared["run_id"],
            encoded_digest,
            "FIRST_OUTPUT_REJECTED",
            {"parse_error": True},
        )
        result = self.runtime.revalidate_preserved_parse_error(prepared["run_id"], encoded)
        self.assertIn("推荐候选", result["user_visible_text"])
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(run.model_output_digest if run else None, encoded_digest)
        self.assertNotIn("private provider reasoning", json.dumps(run.payload if run else {}))
        evidence = run.payload["deterministic_revalidation"] if run else {}
        self.assertFalse(evidence["private_reasoning_retained"])
        self.assertTrue(evidence["provider_output_digest_unchanged"])

    def test_leading_reasoning_wrapper_is_removed_without_storing_it(self) -> None:
        prepared = self.runtime.prepare(
            self.request(
                operation="普通聊天",
                topic_label=None,
                selected_content_product_id=None,
            ),
            self.principal_id,
        )
        raw = (
            "<think>private model reasoning must not be retained</think>"
            '{"kind":"CHAT_REPLY","reply":"只回答已确认范围。","candidates":[]}'
        )
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertEqual(result["user_visible_text"], "只回答已确认范围。")
        run = self.repository.model_run(prepared["run_id"])
        if run is None:
            self.fail("model run was not persisted")
        self.assertNotIn("private model reasoning", json.dumps(run.payload))
        self.assertEqual(
            run.payload["model_wrapper_normalization"],
            "STRIPPED_LEADING_REASONING_WRAPPER",
        )

    def test_feedback_inherits_task_account_role_storyline_and_sources(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        envelope = {
            "kind": "CANDIDATE_SET",
            "reply": None,
            "candidates": [
                self._candidate(
                    "判断路径",
                    "只在当前资料支持的范围内说明判断。",
                    refs,
                    ["核心创意", "事实或证明路径"],
                ),
                self._candidate(
                    "观察路径",
                    "只在当前资料支持的范围内说明观察。",
                    refs,
                    ["叙事视角", "画面组织方法"],
                ),
            ],
        }
        encoded = base64.b64encode(
            json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.runtime.prepare(
            self.request(operation="选择候选", candidate_number=1),
            self.principal_id,
        )
        feedback = self.runtime.prepare(
            self.request(
                operation="提交反馈",
                topic_label=None,
                selected_content_product_id=None,
                primary_audience=None,
                message="这个切入更容易继续。",
            ),
            self.principal_id,
        )
        self.assertIn("反馈已记录", feedback["user_visible_text"])
        from runtime_models import RuntimeFeedback

        with self.sessions() as session:
            row = session.query(RuntimeFeedback).one()
            self.assertIsNotNone(row.requirement_id)
            self.assertIsNotNone(row.role_id)
            self.assertIsNotNone(row.storyline_id)
            self.assertIsNotNone(row.column_id)
            self.assertEqual(row.material_refs, refs)
            self.assertEqual(row.review_state, "PENDING_REVIEW")

    def test_wrong_production_format_is_rejected_without_reroll(self) -> None:
        prepared = self.runtime.prepare(
            self.request(content_format="图文"),
            self.principal_id,
        )
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        envelope = {
            "kind": "CANDIDATE_SET",
            "reply": None,
            "candidates": [
                self._candidate(
                    "错误格式一",
                    "当前内容。",
                    refs,
                    ["核心创意", "事实或证明路径"],
                    content_format="短视频",
                ),
                self._candidate(
                    "错误格式二",
                    "另一条当前内容。",
                    refs,
                    ["叙事视角", "画面组织方法"],
                    content_format="短视频",
                ),
            ],
        }
        encoded = base64.b64encode(
            json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertTrue(result["action_card"])
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(run.state if run else None, "FIRST_OUTPUT_REJECTED")
        self.assertIn("prompt", run.payload if run else {})

    def test_eleven_accounts_are_server_checked_and_missing_scope_degrades(self) -> None:
        accounts = self.repository.all_accounts()
        self.assertEqual(len(accounts), 11)
        results = []
        for account in accounts:
            result = self.runtime.prepare(
                self.request(account_display_name=account.display_name),
                self.principal_id,
            )
            results.append(result)
        self.assertEqual(
            sum(row["response_kind"] == "MODEL_REQUIRED" for row in results),
            1,
        )
        direct_results = [row for row in results if row["response_kind"] == "DIRECT"]
        self.assertEqual(len(direct_results), 10)
        self.assertTrue(all(row["action_card"] for row in direct_results))
        principal = self.repository.principal_by_id(self.principal_id)
        assert principal is not None
        original = list(principal.allowed_account_ids)
        principal.allowed_account_ids = ["ACCOUNT-DIYU-HQ-OFFICIAL"]
        with self.sessions.begin() as session:
            stored = session.get(type(principal), principal.principal_id)
            assert stored is not None
            stored.allowed_account_ids = principal.allowed_account_ids
        denied = self.runtime.prepare(
            self.request(account_display_name="林知远｜笛语"),
            self.principal_id,
        )
        self.assertTrue(denied["action_card"])
        self.assertNotEqual(original, principal.allowed_account_ids)

    def test_brand_import_is_generic_and_cross_brand_profile_cannot_leak(self) -> None:
        bundle = load_simulation_bundle(REPOSITORY_ROOT)
        self.assertEqual(preflight_brand_bundle(bundle)["state"], "CAN_IMPORT")
        foreign_profile = copy.deepcopy(bundle.expression_profile)
        foreign_profile["brand_id"] = "BRAND-OTHER-SIM-001"
        mismatched = BrandImportBundle(
            identity=copy.deepcopy(bundle.identity),
            narrative_fragments=copy.deepcopy(bundle.narrative_fragments),
            precise_facts=copy.deepcopy(bundle.precise_facts),
            expression_profile=foreign_profile,
            source_manifest=copy.deepcopy(bundle.source_manifest),
        )
        result = preflight_brand_bundle(mismatched)
        self.assertEqual(result["state"], "CANNOT_IMPORT")
        self.assertIn("expression_profile_cross_brand_scope", result["fatal_reasons"])

    def test_four_storylines_and_headquarters_region_store_tasks_are_consumed(self) -> None:
        profile = self.repository.setting(
            self.repository.setting("active_runtime_brand")["profile_setting_key"]
        )
        storylines = profile["storylines"]
        for storyline in storylines:
            result = self.runtime.prepare(
                self.request(
                    account_display_name="笛语童装",
                    storyline_id=storyline["storyline_id"],
                    column_id=next(
                        row["column_id"]
                        for row in profile["columns"]
                        if row["storyline_id"] == storyline["storyline_id"]
                    ),
                ),
                self.principal_id,
            )
            self.assertEqual(result["response_kind"], "MODEL_REQUIRED")
            self.assertEqual(
                result["author_prompt"]["task_brief"]["storyline"],
                storyline["display_name"],
            )
        for account in ("笛语江苏", "笛语苏州园区店"):
            result = self.runtime.prepare(
                self.request(account_display_name=account, localization_allowed=True),
                self.principal_id,
            )
            self.assertEqual(result["response_kind"], "DIRECT")
            self.assertTrue(result["action_card"])

    def test_three_production_formats_have_closed_distinct_contracts(self) -> None:
        for content_format in ("短视频", "图文", "陈列搭配"):
            prepared = self.runtime.prepare(
                self.request(content_format=content_format),
                self.principal_id,
            )
            refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
            envelope = ModelEnvelope.model_validate(
                {
                    "kind": "CANDIDATE_SET",
                    "reply": None,
                    "candidates": [
                        self._candidate(
                            "问题路径",
                            "从当前证据支持的问题进入。",
                            refs,
                            ["核心创意", "事实或证明路径"],
                            content_format=content_format,
                        ),
                        self._candidate(
                            "观察路径",
                            "从当前资料支持的观察进入。",
                            refs,
                            ["叙事视角", "画面组织方法"],
                            content_format=content_format,
                        ),
                    ],
                }
            )
            payloads = [row.surfaces.execution_payload for row in envelope.candidates]
            self.assertTrue(all(row.production_format == content_format for row in payloads))
            self.assertEqual(
                {sum(item is not None for item in (row.video, row.article, row.display)) for row in payloads},
                {1},
            )

    def test_same_difference_categories_allow_distinct_creative_realizations(self) -> None:
        prepared = self.runtime.prepare(
            self.request(content_format="陈列搭配"),
            self.principal_id,
        )
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        envelope = {
            "kind": "CANDIDATE_SET",
            "reply": None,
            "candidates": [
                self._candidate(
                    "从空间层次进入",
                    "先看空间层次，再说明搭配依据。",
                    refs,
                    ["核心创意", "画面组织方法"],
                    content_format="陈列搭配",
                ),
                self._candidate(
                    "从可售状态进入",
                    "先核对可售状态，再说明搭配边界。",
                    refs,
                    ["核心创意", "画面组织方法"],
                    content_format="陈列搭配",
                ),
            ],
        }
        encoded = base64.b64encode(
            json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertIn("推荐候选", result["user_visible_text"])
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(run.state if run else None, "FIRST_OUTPUT_ACCEPTED")

    def test_preserved_first_output_can_only_be_revalidated_without_content_change(self) -> None:
        prepared = self.runtime.prepare(
            self.request(content_format="陈列搭配"),
            self.principal_id,
        )
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        envelope = ModelEnvelope.model_validate(
            {
                "kind": "CANDIDATE_SET",
                "reply": None,
                "candidates": [
                    self._candidate(
                        "从厚度关系进入",
                        "先核对厚度关系。",
                        refs,
                        ["核心创意", "画面组织方法"],
                        content_format="陈列搭配",
                    ),
                    self._candidate(
                        "从尺码交集进入",
                        "先核对尺码交集。",
                        refs,
                        ["核心创意", "画面组织方法"],
                        content_format="陈列搭配",
                    ),
                ],
            }
        ).model_dump()
        output_digest = hashlib.sha256(
            json.dumps(envelope, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        self.repository.preserve_first_output(
            prepared["run_id"],
            output_digest,
            "FIRST_OUTPUT_REJECTED",
            envelope,
        )
        result = self.runtime.revalidate_preserved_candidate_output(prepared["run_id"])
        self.assertIn("推荐候选", result["user_visible_text"])
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(
            run.state if run else None,
            "FIRST_OUTPUT_ACCEPTED_AFTER_DETERMINISTIC_REVALIDATION",
        )
        self.assertEqual(run.model_output_digest if run else None, output_digest)
        self.assertTrue(
            run.payload["deterministic_revalidation"]["model_output_unchanged"]
            if run
            else False
        )
        with self.assertRaises(ValueError):
            self.runtime.revalidate_preserved_candidate_output(prepared["run_id"])

    def test_portal_never_returns_tokens_or_internal_ids(self) -> None:
        fake_chat = FakeDifyChatClient()
        app = create_app(self.runtime, self.repository, fake_chat)  # type: ignore[arg-type]
        client = app.test_client()
        login = client.post(
            "/login",
            json={"username": "package7-test-owner", "password": "package7-test-password"},
        )
        self.assertEqual(login.status_code, 200)
        login_text = login.get_data(as_text=True)
        self.assertNotIn("session_token", login_text)
        self.assertNotIn("ACCOUNT-", login_text)
        self.assertIn("HttpOnly", login.headers["Set-Cookie"])
        options = client.get("/v1/portal/options")
        self.assertEqual(options.status_code, 200)
        option_text = options.get_data(as_text=True)
        for internal_prefix in ("ACCOUNT-", "STORYLINE-", "COLUMN-", "TENANT-", "BRAND-"):
            self.assertNotIn(internal_prefix, option_text)

        response = client.post(
            "/v1/portal/chat",
            headers={"X-Diyu-Portal": "same-origin-v1"},
            json={
                "account_display_name": "笛语童装",
                "operation": "随便聊聊",
                "topic_label": "用户问题与理性选择",
                "primary_audience": "正在做具体判断的家长",
                "message": "请用当前资料讲清选择条件。",
                "target_platform": "小红书",
                "duration_label": "30秒左右",
                "expression_feeling": "专业讲明白",
                "content_format": "图文",
                "existing_material_kinds": ["一个想法"],
                "localization_allowed": False,
                "continue_previous": False,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["answer"], "已从Dify内部编排返回。")
        self.assertNotIn("session", response.get_data(as_text=True).lower())
        self.assertEqual(fake_chat.calls[0]["inputs"]["execution_phase"], "AUTHOR")
        self.assertEqual(fake_chat.calls[0]["query"], "请用当前资料讲清选择条件。")
        self.assertNotIn("session_token", fake_chat.calls[0]["inputs"])
        self.assertEqual(
            fake_chat.calls[0]["conversation_scope"],
            "ACCOUNT-DIYU-HQ-OFFICIAL",
        )

        ordinary = client.post(
            "/v1/portal/chat",
            headers={"X-Diyu-Portal": "same-origin-v1"},
            json={
                "account_display_name": "笛语童装",
                "operation": "随便聊聊",
                "message": "你好",
                "target_platform": "其他",
                "duration_label": "由系统建议",
                "expression_feeling": "由系统建议",
                "content_format": "短视频",
                "existing_material_kinds": [],
                "localization_allowed": False,
                "continue_previous": False,
            },
        )
        self.assertEqual(ordinary.status_code, 200)
        self.assertEqual(fake_chat.calls[1]["inputs"]["topic_label"], "未指定题材")

        forged = client.post(
            "/v1/portal/chat",
            headers={"X-Diyu-Portal": "same-origin-v1"},
            json={
                "account_display_name": "不存在的账号",
                "operation": "随便聊聊",
                "message": "你好",
                "target_platform": "其他",
                "duration_label": "由系统建议",
                "expression_feeling": "由系统建议",
                "content_format": "短视频",
                "existing_material_kinds": [],
                "localization_allowed": False,
                "continue_previous": False,
            },
        )
        self.assertEqual(forged.status_code, 400)
        self.assertEqual(len(fake_chat.calls), 2)

    def test_portal_contract_has_no_client_token_or_internal_product_choice(self) -> None:
        fields = PortalTaskRequest.model_fields
        self.assertNotIn("session_token", fields)
        self.assertNotIn("selected_content_product_id", fields)

    def test_classifier_uses_foundation_labels_and_strips_provider_wrapper(self) -> None:
        options = self.runtime.classification_options("用户问题与理性选择")
        self.assertEqual(
            {row["content_product_id"] for row in options},
            {"CP06", "CP07", "CP09", "CP13", "CP16", "CP19"},
        )
        self.assertIn(
            {"content_product_id": "CP06", "internal_label": "专业判断切片"},
            options,
        )
        self.assertEqual(
            _selected_product(
                '<think>provider wrapper</think>{"selected_content_product_id":"CP06"}'
            ),
            "CP06",
        )
        self.assertIsNone(_selected_product('{"selected_content_product_id":"CP6"}'))

    def test_portal_uses_progressive_fields_and_one_click_suggestions(self) -> None:
        html = (PACKAGE_ROOT / "portal.html").read_text(encoding="utf-8")
        script = (PACKAGE_ROOT / "portal.js").read_text(encoding="utf-8")
        self.assertIn('id="production-fields"', html)
        self.assertIn('id="candidate-fields"', html)
        self.assertIn('id="advanced-fields"', html)
        self.assertIn("更多偏好", html)
        self.assertIn("updateTaskMode", script)
        self.assertIn("从一个真实细节开始", script)
        self.assertIn("讲清一个选择问题", script)
        self.assertNotIn("access_token", html + script)

    def test_previous_candidate_context_continues_creative_direction_only(self) -> None:
        from runtime_models import RuntimeCandidate

        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        envelope = {
            "kind": "CANDIDATE_SET",
            "reply": None,
            "candidates": [
                self._candidate(
                    "证据路径",
                    "只使用当前资料支持的观察。",
                    refs,
                    ["核心创意", "事实或证明路径"],
                ),
                self._candidate(
                    "问题路径",
                    "只回答当前资料支持的问题。",
                    refs,
                    ["切入问题或场景", "画面组织方法"],
                ),
            ],
        }
        encoded = base64.b64encode(json.dumps(envelope, ensure_ascii=False).encode()).decode()
        self.runtime.finalize_model_output(prepared["run_id"], encoded)
        with self.sessions() as session:
            first = session.query(RuntimeCandidate).order_by(RuntimeCandidate.ordinal).first()
            self.assertIsNotNone(first)
            previous_ref = first.candidate_id if first is not None else ""
        continued = self.runtime.prepare(
            self.request(
                message="继续这个系列，但不要从上一条补任何事实",
                previous_content_ref=previous_ref,
            ),
            self.principal_id,
        )
        context = continued["author_prompt"]["task_brief"]["previous_content_context"]
        self.assertEqual(context["title"], "证据路径")
        self.assertTrue(context["continuity_only_not_a_fact_source"])
        self.assertNotIn(previous_ref, json.dumps(context, ensure_ascii=False))

    def test_review_export_and_source_lookup_are_user_friendly(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        envelope = {
            "kind": "CANDIDATE_SET",
            "reply": None,
            "candidates": [
                self._candidate(
                    "证据路径",
                    "只使用当前资料支持的观察。",
                    refs,
                    ["核心创意", "事实或证明路径"],
                ),
                self._candidate(
                    "问题路径",
                    "只回答当前资料支持的问题。",
                    refs,
                    ["切入问题或场景", "画面组织方法"],
                ),
            ],
        }
        encoded = base64.b64encode(json.dumps(envelope, ensure_ascii=False).encode()).decode()
        self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.runtime.prepare(
            self.request(operation="选择候选", candidate_number=1),
            self.principal_id,
        )
        review = self.runtime.prepare(self.request(operation="审核"), self.principal_id)
        exported = self.runtime.prepare(self.request(operation="导出"), self.principal_id)
        sources = self.runtime.prepare(self.request(operation="查看来源"), self.principal_id)
        self.assertIn("事实与来源语义：待人工确认", review["user_visible_text"])
        self.assertIn("制作安排", exported["user_visible_text"])
        self.assertIn("分镜", exported["user_visible_text"])
        self.assertNotIn('"production_format"', exported["user_visible_text"])
        self.assertIn("当前范围可用", sources["user_visible_text"])
        self.assertNotIn("PKG5-", sources["user_visible_text"])

    def test_public_network_cannot_open_portal_or_login(self) -> None:
        app = create_app(self.runtime, self.repository, FakeDifyChatClient())  # type: ignore[arg-type]
        client = app.test_client()
        portal = client.get("/portal", environ_base={"REMOTE_ADDR": "203.10.20.30"})
        login = client.post(
            "/login",
            json={"username": "package7-test-owner", "password": "package7-test-password"},
            environ_base={"REMOTE_ADDR": "203.10.20.30"},
        )
        self.assertEqual(portal.status_code, 404)
        self.assertEqual(login.status_code, 404)

    def test_dify_budget_reservation_is_conservative_and_fail_closed(self) -> None:
        for index in range(20):
            self.repository.reserve_dify_invocation(
                invocation_id=f"DIFY-BUDGET-{index:02d}",
                principal_id=self.principal_id,
                model_call_upper_bound=2,
            )
        self.assertEqual(self.repository.dify_invocation_audit()["model_call_upper_bound"], 40)
        with self.assertRaises(ValueError):
            self.repository.reserve_dify_invocation(
                invocation_id="DIFY-BUDGET-OVER",
                principal_id=self.principal_id,
                model_call_upper_bound=1,
            )

    def test_authorized_budget_extension_is_explicit_and_capped_at_100(self) -> None:
        self.repository.reserve_dify_invocation(
            invocation_id="DIFY-BUDGET-EXTENDED",
            principal_id=self.principal_id,
            model_call_upper_bound=100,
            maximum_model_calls=100,
        )
        with self.assertRaises(ValueError):
            self.repository.reserve_dify_invocation(
                invocation_id="DIFY-BUDGET-EXTENDED-OVER",
                principal_id=self.principal_id,
                model_call_upper_bound=1,
                maximum_model_calls=100,
            )
        with self.assertRaises(ValueError):
            DifyChatClient(
                base_url="https://dify.internal/v1",
                app_api_token="app-" + "x" * 32,
                repository=self.repository,
                maximum_model_calls=101,
            )

    def test_dify_conversation_is_persisted_and_reused_for_the_same_user(self) -> None:
        requests: list[dict[str, Any]] = []

        def fake_open(request: Any, timeout: int) -> BytesIO:
            self.assertGreater(timeout, 0)
            requests.append(json.loads(request.data.decode("utf-8")))
            return BytesIO(
                json.dumps(
                    {
                        "answer": "受控回复",
                        "conversation_id": "CONVERSATION-PKG7-001",
                        "metadata": {"usage": {"total_tokens": 3}},
                    }
                ).encode("utf-8")
            )

        client = DifyChatClient(
            base_url="https://dify.internal/v1",
            app_api_token="app-" + "x" * 32,
            repository=self.repository,
        )
        with patch("urllib.request.urlopen", side_effect=fake_open):
            client.invoke(
                invocation_id="DIFY-CONVERSATION-001",
                principal_id=self.principal_id,
                conversation_scope="ACCOUNT-DIYU-HQ-OFFICIAL",
                user_key="pkg7-stable-user",
                query="第一条",
                inputs={},
            )
            client.invoke(
                invocation_id="DIFY-CONVERSATION-002",
                principal_id=self.principal_id,
                conversation_scope="ACCOUNT-DIYU-HQ-OFFICIAL",
                user_key="pkg7-stable-user",
                query="继续上一条",
                inputs={},
            )
        self.assertEqual(requests[0]["conversation_id"], "")
        self.assertEqual(requests[1]["conversation_id"], "CONVERSATION-PKG7-001")
        self.assertEqual(
            self.repository.dify_conversation(
                self.principal_id,
                "ACCOUNT-DIYU-HQ-OFFICIAL",
            ),
            ("pkg7-stable-user", "CONVERSATION-PKG7-001"),
        )

    def test_classification_and_authoring_can_use_fresh_dify_conversations(self) -> None:
        requests: list[dict[str, Any]] = []

        def fake_open(request: Any, timeout: int) -> BytesIO:
            self.assertGreater(timeout, 0)
            requests.append(json.loads(request.data.decode("utf-8")))
            return BytesIO(
                json.dumps(
                    {
                        "answer": "受控回复",
                        "conversation_id": f"CONVERSATION-FRESH-{len(requests)}",
                        "metadata": {"usage": {"total_tokens": 3}},
                    }
                ).encode("utf-8")
            )

        client = DifyChatClient(
            base_url="https://dify.internal/v1",
            app_api_token="app-" + "x" * 32,
            repository=self.repository,
        )
        with patch("urllib.request.urlopen", side_effect=fake_open):
            for ordinal in (1, 2):
                client.invoke(
                    invocation_id=f"DIFY-FRESH-{ordinal:03d}",
                    principal_id=self.principal_id,
                    conversation_scope="ACCOUNT-DIYU-HQ-OFFICIAL",
                    user_key="pkg7-stable-user",
                    query="本次冻结任务",
                    inputs={"ordinal": ordinal},
                    reuse_conversation=False,
                )
        self.assertEqual([row["conversation_id"] for row in requests], ["", ""])
        self.assertIsNone(
            self.repository.dify_conversation(
                self.principal_id,
                "ACCOUNT-DIYU-HQ-OFFICIAL",
            )
        )

    def test_dify_conversation_history_is_isolated_between_content_accounts(self) -> None:
        self.repository.adopt_dify_conversation(
            principal_id=self.principal_id,
            account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
            dify_user_key="pkg7-hq-user",
            conversation_id="CONVERSATION-PKG7-HQ",
        )
        self.assertIsNone(
            self.repository.dify_conversation(
                self.principal_id,
                "ACCOUNT-DIYU-SZ-PARK",
            )
        )
        self.repository.adopt_dify_conversation(
            principal_id=self.principal_id,
            account_id="ACCOUNT-DIYU-SZ-PARK",
            dify_user_key="pkg7-sz-user",
            conversation_id="CONVERSATION-PKG7-SZ",
        )
        self.assertEqual(
            self.repository.dify_conversation(
                self.principal_id,
                "ACCOUNT-DIYU-HQ-OFFICIAL",
            ),
            ("pkg7-hq-user", "CONVERSATION-PKG7-HQ"),
        )
        self.assertEqual(
            self.repository.dify_conversation(
                self.principal_id,
                "ACCOUNT-DIYU-SZ-PARK",
            ),
            ("pkg7-sz-user", "CONVERSATION-PKG7-SZ"),
        )

    def test_current_app_conversation_adoption_is_immutable(self) -> None:
        response = BytesIO(
            json.dumps(
                {
                    "data": [
                        {"id": "CONVERSATION-PKG7-EXISTING"},
                        {"id": "CONVERSATION-PKG7-OLDER"},
                    ]
                }
            ).encode("utf-8")
        )
        client = DifyChatClient(
            base_url="https://dify.internal/v1",
            app_api_token="app-" + "x" * 32,
            repository=self.repository,
        )
        with patch("urllib.request.urlopen", return_value=response):
            result = client.adopt_latest_conversation(
                principal_id=self.principal_id,
                conversation_scope="ACCOUNT-DIYU-HQ-OFFICIAL",
                user_key="pkg7-existing-user",
            )
        self.assertTrue(result["adopted"])
        self.assertEqual(result["conversation_count_seen"], 2)
        with self.assertRaises(ValueError):
            self.repository.adopt_dify_conversation(
                principal_id=self.principal_id,
                account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
                dify_user_key="pkg7-different-user",
                conversation_id="CONVERSATION-PKG7-DIFFERENT",
            )

    def test_revoked_account_scope_fact_returns_an_action_card(self) -> None:
        from runtime_models import RuntimePreciseFact

        with self.sessions.begin() as session:
            row = next(
                item
                for item in session.query(RuntimePreciseFact).filter(
                    RuntimePreciseFact.fact_kind == "AUTHORIZATION"
                )
                if item.payload["value"]["account_id"] == "ACCOUNT-DIYU-SZ-PARK"
            )
            row.status = "REVOKED"
            payload = copy.deepcopy(row.payload)
            payload["status"] = "REVOKED"
            payload["revocation_ref"] = "REV-PKG7-ACCOUNT-TEST"
            row.payload = payload
            row.revocation_ref = "REV-PKG7-ACCOUNT-TEST"
        result = self.runtime.prepare(
            self.request(account_display_name="笛语苏州园区店"),
            self.principal_id,
        )
        self.assertTrue(result["action_card"])

    def test_postcheck_blocks_revoked_and_stale_index_rows(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        self.assertEqual(prepared["response_kind"], "MODEL_REQUIRED")
        first_id = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][0]
        self.repository.set_fragment_state(first_id, status="REVOKED", revocation_ref="REV-PKG7-TEST")
        retrieval = RuntimeBrandFactRetrievalService(self.repository, self.knowledge)
        result = retrieval.retrieve(
            {"query_text": "尺码", "max_fragments": 20, "precise_fact_queries": [], "client_claims": {}},
            principal_id=self.principal_id,
            content_account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
            query_at="2026-07-15T00:00:00Z",
        )
        self.assertNotIn(first_id, [row["fragment_id"] for row in result["scoped_retrieval_fragments"]])
        self.assertTrue(result["retrieval_audit"]["postcheck"]["authoritative_metadata_recheck"])

    def test_dify_index_binding_cannot_replace_the_frozen_source_digest(self) -> None:
        row = self._fragment_rows()[0]
        original_digest = row.content_digest
        original_index_digest = row.index_content_digest
        with self.assertRaises(ValueError):
            self.repository.bind_dify_documents(
                {
                    row.payload["fragment_id"]: {
                        "document_id": row.dify_document_id,
                        "source_content_sha256": "0" * 64,
                        "index_content_sha256": "1" * 64,
                    }
                }
            )
        refreshed = next(
            item for item in self._fragment_rows() if item.payload["fragment_id"] == row.payload["fragment_id"]
        )
        self.assertEqual(refreshed.content_digest, original_digest)
        self.assertEqual(refreshed.index_content_digest, original_index_digest)

    def test_dify_binding_clears_fragments_outside_the_current_projection(self) -> None:
        first, second = self._fragment_rows()[:2]
        self.repository.bind_dify_documents(
            {
                first.payload["fragment_id"]: {
                    "document_id": first.dify_document_id,
                    "source_content_sha256": first.content_digest,
                    "index_content_sha256": first.index_content_digest,
                }
            }
        )
        refreshed = {
            row.payload["fragment_id"]: row for row in self._fragment_rows()
        }
        self.assertIsNotNone(
            refreshed[first.payload["fragment_id"]].dify_document_id
        )
        self.assertIsNone(refreshed[second.payload["fragment_id"]].dify_document_id)
        self.assertIsNone(
            refreshed[second.payload["fragment_id"]].index_content_digest
        )

    def test_revoked_principal_is_rechecked_before_portal_model_invocation(self) -> None:
        from runtime_models import RuntimePrincipal

        fake_chat = FakeDifyChatClient()
        app = create_app(self.runtime, self.repository, fake_chat)  # type: ignore[arg-type]
        client = app.test_client()
        login = client.post(
            "/login",
            json={"username": "package7-test-owner", "password": "package7-test-password"},
        )
        self.assertEqual(login.status_code, 200)
        with self.sessions.begin() as session:
            principal = session.get(RuntimePrincipal, self.principal_id)
            self.assertIsNotNone(principal)
            if principal is not None:
                principal.status = "REVOKED"
        response = client.post(
            "/v1/portal/chat",
            headers={"X-Diyu-Portal": "same-origin-v1"},
            json={
                "account_display_name": "笛语童装",
                "operation": "随便聊聊",
                "topic_label": None,
                "primary_audience": None,
                "message": "聊聊今天的内容方向",
                "target_platform": "其他",
                "candidate_number": None,
                "content_goal": None,
                "key_takeaway": None,
                "speaker_role_name": None,
                "storyline_name": None,
                "column_name": None,
                "continue_previous": False,
                "localization_allowed": False,
                "duration_label": "由系统建议",
                "expression_feeling": "由系统建议",
                "content_format": "短视频",
                "existing_material_kinds": [],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(fake_chat.calls, [])

    def test_account_scope_is_rechecked_before_candidate_persistence(self) -> None:
        from runtime_models import RuntimeCandidate, RuntimePrincipal

        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        envelope = {
            "kind": "CANDIDATE_SET",
            "reply": None,
            "candidates": [
                self._candidate(
                    "证据路径",
                    "只使用当前资料支持的观察。",
                    refs,
                    ["核心创意", "事实或证明路径"],
                ),
                self._candidate(
                    "问题路径",
                    "只回答当前资料支持的问题。",
                    refs,
                    ["切入问题或场景", "画面组织方法"],
                ),
            ],
        }
        with self.sessions.begin() as session:
            principal = session.get(RuntimePrincipal, self.principal_id)
            self.assertIsNotNone(principal)
            if principal is not None:
                principal.allowed_account_ids = []
        encoded = base64.b64encode(json.dumps(envelope, ensure_ascii=False).encode()).decode()
        with self.assertRaises(ValueError):
            self.runtime.finalize_model_output(prepared["run_id"], encoded)
        with self.sessions() as session:
            self.assertEqual(session.query(RuntimeCandidate).count(), 0)

    def test_region_and_store_can_author_only_their_verified_account_scope(self) -> None:
        for display_name in ("笛语江苏", "笛语苏州园区店"):
            result = self.runtime.prepare(
                self.request(
                    account_display_name=display_name,
                    message="做一份区域账号说明，只说明账号身份，不展开具体事件",
                    content_goal="说明账号定位",
                    key_takeaway="没有本地材料就不补写本地事实",
                ),
                self.principal_id,
            )
            self.assertEqual(result["response_kind"], "MODEL_REQUIRED")
            prompt = result["author_prompt"]
            self.assertTrue(prompt["task_brief"]["scope_identity_only_authoring_allowed"])
            self.assertEqual(prompt["author_materials"]["scoped_retrieval_fragments"], [])
            facts = prompt["author_materials"]["verified_precise_facts"]
            self.assertEqual(len(facts), 1)
            self.assertEqual(facts[0]["fact_kind"], "ACCOUNT_SCOPE_IDENTITY")

    def test_verified_store_scope_fact_can_support_a_narrow_candidate_set(self) -> None:
        prepared = self.runtime.prepare(
            self.request(
                account_display_name="笛语苏州园区店",
                message="做一份账号介绍，只说明这个账号可以讲什么和内容边界",
                content_goal="说明账号范围",
                key_takeaway="没有本地材料就不补写本地事实",
            ),
            self.principal_id,
        )
        fact_ref = prepared["author_prompt"]["author_materials"]["precise_fact_refs"][0]
        candidates = [
            self._candidate(
                "账号证据先行",
                "笛语苏州园区店代表当前门店范围。",
                [fact_ref],
                ["核心创意", "事实或证明路径"],
                architecture="EVIDENCE_FIRST",
            ),
            self._candidate(
                "边界问题先行",
                "这个账号能讲什么？只讲当前门店范围内已确认的内容。",
                [fact_ref],
                ["切入问题或场景", "画面组织方法"],
                architecture="QUESTION_ANSWER",
            ),
        ]
        for candidate in candidates:
            candidate["used_fact_refs"] = [fact_ref]
            candidate["used_material_refs"] = []
        encoded = base64.b64encode(
            json.dumps(
                {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
                ensure_ascii=False,
            ).encode()
        ).decode()
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertIn("推荐候选", result["user_visible_text"])

    def test_unseen_high_risk_product_detail_is_rejected_even_with_a_valid_ref(self) -> None:
        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"][:1]
        candidates = [
            self._candidate(
                "证据路径",
                "现有样衣已经确认双重厚度。",
                refs,
                ["核心创意", "事实或证明路径"],
            ),
            self._candidate(
                "问题路径",
                "只回答当前资料能够回答的问题。",
                refs,
                ["切入问题或场景", "画面组织方法"],
            ),
        ]
        encoded = base64.b64encode(
            json.dumps(
                {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
                ensure_ascii=False,
            ).encode()
        ).decode()
        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)
        self.assertTrue(result.get("action_card"))

    def test_numeric_unit_and_range_equivalence_preserves_semantics(self) -> None:
        self.assertTrue(protected_detail_is_supported("100cm", "规格为100厘米"))
        self.assertTrue(
            protected_detail_is_supported(
                "100 cm ～ 150 cm",
                "尺码为100厘米至150厘米",
            )
        )
        self.assertFalse(protected_detail_is_supported("110厘米", "规格为100厘米"))
        self.assertFalse(protected_detail_is_supported("100米", "规格为100厘米"))
        self.assertFalse(
            protected_detail_is_supported(
                "100厘米至160厘米",
                "尺码为100厘米至150厘米",
            )
        )

        prepared = self.runtime.prepare(self.request(), self.principal_id)
        refs = prepared["author_prompt"]["author_materials"]["retrieval_fragment_refs"]
        size_ref = next(
            ref
            for ref in refs
            if ref == "PKG5-FRAGMENT-BD-NARR-02-006"
        )
        candidates = [
            self._candidate(
                "尺码范围",
                "笛语商品使用100 cm ～ 150 cm的常用尺码范围。",
                [size_ref],
                ["核心创意", "事实或证明路径"],
                architecture="EVIDENCE_FIRST",
            ),
            self._candidate(
                "尺码问题",
                "尺码不能只看身高。",
                [size_ref],
                ["切入问题或场景", "画面组织方法"],
                architecture="QUESTION_ANSWER",
            ),
        ]
        encoded = base64.b64encode(
            json.dumps(
                {"kind": "CANDIDATE_SET", "reply": None, "candidates": candidates},
                ensure_ascii=False,
            ).encode()
        ).decode()

        result = self.runtime.finalize_model_output(prepared["run_id"], encoded)

        self.assertIn("推荐候选", result["user_visible_text"])
        run = self.repository.model_run(prepared["run_id"])
        self.assertEqual(run.state if run else None, "FIRST_OUTPUT_ACCEPTED")

        for changed_range in ("100cm-160cm", "100米-150米"):
            with self.subTest(changed_range=changed_range):
                changed_prepared = self.runtime.prepare(self.request(), self.principal_id)
                changed_candidates = [
                    self._candidate(
                        "篡改尺码范围",
                        f"笛语商品使用{changed_range}的常用尺码范围。",
                        [size_ref],
                        ["核心创意", "事实或证明路径"],
                        architecture="EVIDENCE_FIRST",
                    ),
                    self._candidate(
                        "尺码问题",
                        "尺码不能只看身高。",
                        [size_ref],
                        ["切入问题或场景", "画面组织方法"],
                        architecture="QUESTION_ANSWER",
                    ),
                ]
                changed_encoded = base64.b64encode(
                    json.dumps(
                        {
                            "kind": "CANDIDATE_SET",
                            "reply": None,
                            "candidates": changed_candidates,
                        },
                        ensure_ascii=False,
                    ).encode()
                ).decode()
                changed_result = self.runtime.finalize_model_output(
                    changed_prepared["run_id"],
                    changed_encoded,
                )
                self.assertTrue(changed_result.get("action_card"))
                changed_run = self.repository.model_run(changed_prepared["run_id"])
                self.assertEqual(
                    changed_run.state if changed_run else None,
                    "FIRST_OUTPUT_REJECTED",
                )

    def test_twenty_products_eight_topics_and_eight_action_cards_remain_covered(self) -> None:
        cases = [json.loads(line) for line in P6_CASES.read_text(encoding="utf-8").splitlines()]
        self.assertEqual({row["content_product_id"] for row in cases}, {f"CP{i:02d}" for i in range(1, 21)})
        self.assertEqual({row["topic_category_id"] for row in cases}, {f"TOPIC-{i:02d}" for i in range(1, 9)})
        self.assertEqual(
            set(self.runtime.action_cards),
            {"COLLECT_FACT", "COLLECT_MATERIAL", "REQUEST_AUTHORIZATION", "INTERVIEW", "RESHOOT", "ANONYMIZE", "DEGRADE", "BLOCK"},
        )

    def test_dify_graph_is_single_importable_nonproduction_app(self) -> None:
        document = DSL_PATH.read_text(encoding="utf-8")
        parsed = yaml_safe_load(document)
        self.assertEqual(parsed["version"], "0.6.0")
        self.assertEqual(parsed["app"]["mode"], "advanced-chat")
        self.assertIn("non-production", parsed["app"]["name"])
        nodes = parsed["workflow"]["graph"]["nodes"]
        self.assertEqual(sum(node["data"]["type"] == "llm" for node in nodes), 2)
        llm_nodes = [node for node in nodes if node["data"]["type"] == "llm"]
        self.assertTrue(
            all(node["data"]["memory"]["window"]["enabled"] is False for node in llm_nodes)
        )
        self.assertEqual(parsed["workflow"]["environment_variables"], [])
        self.assertFalse(any(node["data"]["type"] == "http-request" for node in nodes))
        self.assertNotIn("sk-", document)
        self.assertNotIn("__PACKAGE7_", document)
        self.assertNotIn("请先取得模拟访问凭证", document)
        self.assertIn("execution_phase", document)
        self.assertIn("author_prompt", document)
        self.assertIn("不能作为事实、授权、资料或候选引用来源", document)

    def test_dify_provisioning_never_infers_owner_from_an_oldest_app(self) -> None:
        provisioner = (PACKAGE_ROOT / "provision_dify.py").read_text(encoding="utf-8")
        self.assertNotIn("order_by(App.created_at)", provisioner)
        self.assertIn("LOCKED_PACKAGE7_STATE", provisioner)
        self.assertIn("PACKAGE7_APPROVED_DIFY_OWNER_ACCOUNT_ID", provisioner)
        self.assertIn("The locked Package 7 Dify application owner drifted", provisioner)
        self.assertIn("The Package 7 Dify application is not unique", provisioner)
        self.assertIn("The locked Package 7 Dify dataset drifted", provisioner)
        self.assertIn("The Package 7 Dify dataset is not unique", provisioner)

    def test_static_evidence_shot_does_not_require_an_invented_action(self) -> None:
        candidate = self._candidate(
            "静态证据",
            "现有资料只支持这一项判断。",
            ["PKG5-FRAGMENT-BD-NARR-04-013-S01"],
            ["事实或证明路径", "画面组织方法"],
        )
        second = self._candidate(
            "问题回答",
            "先问清问题，再停在资料能够回答的位置。",
            ["PKG5-FRAGMENT-BD-NARR-04-013-S01"],
            ["切入问题或场景", "情绪钩子"],
            architecture="QUESTION_ANSWER",
        )
        candidate["surfaces"]["execution_payload"]["video"]["shots"][0]["action"] = ""
        envelope = ModelEnvelope.model_validate(
            {"kind": "CANDIDATE_SET", "reply": None, "candidates": [candidate, second]}
        )
        self.assertEqual(
            envelope.candidates[0].surfaces.execution_payload.video.shots[0].action,
            "",
        )

    @staticmethod
    def _candidate(
        label: str,
        body: str,
        refs: list[str],
        dimensions: list[str],
        *,
        content_format: str = "短视频",
        architecture: str | None = None,
    ) -> JsonObject:
        if architecture is None:
            if "切入问题或场景" in dimensions or "切入问题" in dimensions:
                architecture = "QUESTION_ANSWER"
            elif "叙事视角" in dimensions or any(
                token in label for token in ("空间", "厚度", "观察", "动作")
            ):
                architecture = "OBJECT_OR_TIMELINE"
            elif any(token in label for token in ("可售", "尺码")):
                architecture = "QUESTION_ANSWER"
            else:
                architecture = "EVIDENCE_FIRST"
        format_payload: JsonObject
        if content_format == "短视频":
            format_payload = {
                "video": {
                    "shots": [
                        {
                            "time_range": "0至5秒",
                            "visual": "拍摄已有资料中能确认的商品细节。",
                            "action": "镜头缓慢靠近细节。",
                            "camera": "近景，固定机位。",
                            "audio": body,
                            "subtitle": body,
                            "scene_product_props": "仅使用已确认材料。",
                            "edit_note": "保留同期声。",
                        },
                        {
                            "time_range": "5至15秒",
                            "visual": "回到完整画面说明判断边界。",
                            "action": "保持画面稳定。",
                            "camera": "中景。",
                            "audio": "把结论留在当前证据范围内。",
                            "subtitle": "先核对，再判断。",
                            "scene_product_props": "不增加新道具。",
                            "edit_note": "不使用夸张转场。",
                        },
                    ],
                    "shooting_notes": ["只拍已有材料支持的画面。"],
                    "editing_notes": ["节奏自然，不伪造前后对比。"],
                },
                "article": None,
                "display": None,
            }
        elif content_format == "图文":
            format_payload = {
                "video": None,
                "article": {
                    "frames": [
                        {"order": 1, "image_brief": "拍整体。", "accompanying_copy": body},
                        {"order": 2, "image_brief": "拍细节。", "accompanying_copy": "说明证据边界。"},
                    ],
                    "cover_brief": "用真实细节做封面。",
                    "layout_notes": ["先整体后细节。"],
                },
                "display": None,
            }
        else:
            format_payload = {
                "video": None,
                "article": None,
                "display": {
                    "referenced_items_or_facts": ["只使用已确认商品或事实"],
                    "arrangement_relationship": "按真实场景与厚度关系组织。",
                    "spatial_layers": "入口、主展示和细节形成三层。",
                    "color_relationship": "颜色关系不代替搭配依据。",
                    "availability_caution": "拍摄前再次核对状态与可用范围。",
                    "shooting_angles": ["入口全景", "主展示中景", "细节近景"],
                },
            }
        if architecture == "QUESTION_ANSWER":
            if content_format == "短视频":
                format_payload["video"]["shots"][0].update(
                    {
                        "visual": "先呈现一个待回答的问题，不补充问题之外的事实。",
                        "action": "画面停留在问题文字与现有资料上。",
                        "camera": "先固定全景，再切资料近景。",
                        "audio": "先提出问题，再用当前资料回答。",
                    }
                )
                format_payload["video"]["shots"][1].update(
                    {
                        "visual": "答案与尚待确认的边界并列出现。",
                        "action": "依次显示可回答项与待确认项。",
                        "camera": "静态分栏画面。",
                        "audio": "答案止步于来源能够支持的位置。",
                    }
                )
            elif content_format == "图文":
                format_payload["article"]["frames"] = [
                    {"order": 1, "image_brief": "问题作为首屏。", "accompanying_copy": body},
                    {"order": 2, "image_brief": "答案和边界并列。", "accompanying_copy": "只回答已有资料支持的部分。"},
                ]
            else:
                format_payload["display"]["arrangement_relationship"] = "先列待确认问题，再按已确认事实安排可执行部分。"
                format_payload["display"]["spatial_layers"] = "问题、证据和待确认项分成三个清楚区域。"
        elif architecture == "OBJECT_OR_TIMELINE":
            if content_format == "短视频":
                format_payload["video"]["shots"][0].update(
                    {
                        "visual": "镜头沿一个已确认对象的可见状态移动。",
                        "action": "只记录对象当前可见部分。",
                        "camera": "固定锚点近景。",
                        "audio": "以对象状态串联内容，不补事件。",
                    }
                )
                format_payload["video"]["shots"][1].update(
                    {
                        "visual": "同一对象停在当前证据边界。",
                        "action": "保持对象位置不变。",
                        "camera": "回到固定锚点全景。",
                        "audio": "用状态变化或未变化收束。",
                    }
                )
            elif content_format == "图文":
                format_payload["article"]["frames"] = [
                    {"order": 1, "image_brief": "同一对象的整体状态。", "accompanying_copy": body},
                    {"order": 2, "image_brief": "同一对象的证据细节。", "accompanying_copy": "停在当前可确认状态。"},
                ]
            else:
                format_payload["display"]["arrangement_relationship"] = "沿同一对象的状态证据组织，不借其他对象补足叙事。"
                format_payload["display"]["spatial_layers"] = "整体状态、局部证据和未知项依次展开。"
        surfaces = {
            "title": label,
            "body": body,
            "spoken_lines": [body],
            "CTA": "先核对现有资料。",
            "execution_payload": {
                "production_format": content_format,
                "task_summary": "用当前材料完成一份内部测试内容。",
                "content_direction": label,
                "core_idea": f"{label}的独立创意",
                "cover_or_first_screen_copy": label,
                "opening_hook": body,
                "story_or_full_script": body,
                "target_platform": "内部测试",
                "duration_label": "15秒左右",
                "ending_and_action": "请先核对来源再进入审核。",
                "publishing_copy": body,
                "next_actions": ["换开头", "缩短", "提交审核"],
                **format_payload,
            },
            "surface_units": [],
        }
        claim_bindings: list[JsonObject] = []

        def bind(value: object, path: str) -> None:
            if isinstance(value, str) and value.strip():
                source_bound = value.strip() == body.strip()
                claim_bindings.append(
                    {
                        "surface_path": path,
                        "exact_text": value.strip(),
                        "claim_class": "SOURCE_CLAIM" if source_bound else "CREATIVE_DIRECTION",
                        "source_refs": list(refs) if source_bound else [],
                    }
                )
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    bind(child, f"{path}[{index}]")
            elif isinstance(value, dict):
                for key, child in value.items():
                    if key != "surface_units":
                        bind(child, f"{path}.{key}" if path else key)

        bind(surfaces, "")
        return {
            "difference_label": label,
            "narrative_architecture": architecture,
            "difference_dimensions": dimensions,
            "surfaces": surfaces,
            "claim_bindings": claim_bindings,
            "used_fact_refs": [],
            "used_material_refs": refs,
        }

    def _fragment_rows(self) -> list[Any]:
        from runtime_models import RuntimeNarrativeFragment

        with self.sessions() as session:
            return list(session.query(RuntimeNarrativeFragment).all())


def yaml_safe_load(value: str) -> JsonObject:
    import yaml  # type: ignore[import-untyped]

    parsed = yaml.safe_load(value)
    if not isinstance(parsed, dict):
        raise ValueError("Expected YAML object")
    return parsed


if __name__ == "__main__":
    unittest.main()
