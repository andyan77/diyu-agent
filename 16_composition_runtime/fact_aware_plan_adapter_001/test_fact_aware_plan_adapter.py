#!/usr/bin/env python3
"""Focused integration tests for the Package 6 thin adapter."""

from __future__ import annotations

import copy
import json
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from fact_aware_plan_adapter import (
    FactAwarePlanAdapter,
    PlanMaterialAccessDenied,
    SERVER_ACCESS_AUTHORITY,
    SERVER_TASK_AUTHORITY,
    START_CREATION,
    ServerConfirmedProductionTask,
    ServerPlanAccess,
)
from brand_fact_retrieval import BrandFactRetrievalService  # type: ignore[import-not-found]


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
CASES_PATH = PACKAGE_ROOT / "fixtures/integration_cases.v1.jsonl"
FIXED_TIME = "2026-07-15T00:00:00Z"


def load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def fixed_candidate() -> dict[str, Any]:
    return {
        "candidate_id": "PKG6-LOCAL-STRUCTURE-CANDIDATE",
        "candidate_version": 1,
        "candidate_user_visible_surfaces": {
            "title": "先核对现有材料",
            "body": "这是一条固定的本地结构校验文本，不是生成内容成品。",
            "spoken_lines": ["只使用计划允许的材料。"],
            "CTA": "继续核对来源。",
        },
    }


class FactAwarePlanAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = FactAwarePlanAdapter.from_repository(REPOSITORY_ROOT)
        self.base_request = self.adapter.expression_service.local_simulation_request()
        self.cases = load_cases()

    def task_for_case(
        self,
        case: Mapping[str, Any],
        *,
        intent: str = START_CREATION,
        authority_source: str = SERVER_TASK_AUTHORITY,
        requirement_updates: Mapping[str, Any] | None = None,
        soft_preferences: Mapping[str, Any] | None = None,
        diagnostics: Mapping[str, Any] | None = None,
        client_claims: Mapping[str, Any] | None = None,
        request_id: str | None = None,
    ) -> ServerConfirmedProductionTask:
        requirement = copy.deepcopy(self.base_request["confirmed_requirement"])
        case_id = str(case["case_id"])
        requirement.update(
            {
                "requirement_id": f"REQ-{case_id}",
                "topic_category_id": case["topic_category_id"],
                "selected_internal_content_product_id": case["content_product_id"],
                "primary_audience": f"{case['content_product_id']}已确认测试受众",
                "required_precise_fact_kinds": list(
                    case.get("required_precise_fact_kinds", [])
                ),
                "plain_language_summary": f"验证{case['content_product_id']}事实感知计划",
            }
        )
        if requirement_updates:
            requirement.update(copy.deepcopy(dict(requirement_updates)))
        return ServerConfirmedProductionTask(
            server_task_ref=f"server-task://{case_id}",
            authority_source=authority_source,
            intent=intent,
            request_id=request_id or f"REQUEST-{case_id}",
            principal_id="SIM-LOGIN-DIYU-ACCEPTANCE-001",
            content_account_id="ACCOUNT-DIYU-HQ-OFFICIAL",
            acting_role_id="ROLE-HQ-CONTENT-TEAM",
            query_at=FIXED_TIME,
            confirmed_requirement=requirement,
            confirmation_evidence=copy.deepcopy(
                self.base_request["confirmation_evidence"]
            ),
            retrieval_query_text=str(case.get("query_text", "")),
            precise_fact_queries=tuple(
                copy.deepcopy(case.get("precise_fact_queries", []))
            ),
            requested_high_level_mode_refs=(
                "expression-mode://documentary-observation/v1",
            ),
            client_soft_preferences=copy.deepcopy(
                soft_preferences
                if soft_preferences is not None
                else self.base_request["client_soft_preferences"]
            ),
            output_requirements=copy.deepcopy(
                self.base_request["output_requirements"]
            ),
            experimental_diagnostics=copy.deepcopy(diagnostics or {}),
            untrusted_client_claims=copy.deepcopy(client_claims or {}),
        )

    @staticmethod
    def access(account_id: str = "ACCOUNT-DIYU-HQ-OFFICIAL") -> ServerPlanAccess:
        return ServerPlanAccess(
            authority_source=SERVER_ACCESS_AUTHORITY,
            principal_id="SIM-LOGIN-DIYU-ACCEPTANCE-001",
            content_account_id=account_id,
        )

    def case(self, product_id: str) -> dict[str, Any]:
        return next(
            row for row in self.cases if row["content_product_id"] == product_id
        )

    def test_twenty_products_and_eight_topics_have_honest_results(self) -> None:
        products = {str(row["content_product_id"]) for row in self.cases}
        topics = {str(row["topic_category_id"]) for row in self.cases}
        self.assertEqual(products, {f"CP{index:02d}" for index in range(1, 21)})
        self.assertEqual(topics, {f"TOPIC-{index:02d}" for index in range(1, 9)})
        plan_count = 0
        action_count = 0
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                result = self.adapter.prepare(self.task_for_case(case))
                self.assertEqual(result["object_type"], case["expected_result_type"])
                record = self.adapter.integration_records[-1]
                self.assertEqual(
                    record["selected_internal_content_product_id"],
                    case["content_product_id"],
                )
                if result["object_type"] == "LIGHT_CONTENT_PLAN":
                    plan_count += 1
                    self.assertEqual(
                        result["references"]["selected_internal_content_product_id"],
                        case["content_product_id"],
                    )
                else:
                    action_count += 1
                    self.assertEqual(result["action_type"], "COLLECT_MATERIAL")
        self.assertGreater(plan_count, 0)
        self.assertGreater(action_count, 0)
        self.assertEqual(plan_count + action_count, 20)

    def test_precise_fact_plan_calls_package5_then_package2(self) -> None:
        result = self.adapter.prepare(self.task_for_case(self.case("CP03")))
        self.assertEqual(result["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(
            result["references"]["precise_fact_refs"],
            ["PKG5-BD-FACT-001", "PKG5-BD-FACT-002"],
        )
        self.assertTrue(result["references"]["retrieval_fragment_refs"])
        self.assertEqual(result["expression_guidance"]["approved_example_refs"], [])
        self.assertNotIn("body", result)
        audit = self.adapter.call_audit
        self.assertEqual(audit["package5_retrieve"], 1)
        self.assertEqual(audit["package2_prepare"], 1)
        record = self.adapter.integration_records[-1]
        self.assertEqual(
            record["package5"]["entrypoint"],
            "BrandFactRetrievalService.retrieve",
        )
        self.assertEqual(
            record["package2"]["entrypoint"], "LightExpressionService.prepare"
        )
        self.assertFalse(
            record["package5"]["hold_or_internal_exclusion_records_consumed"]
        )
        self.assertFalse(record["package2"]["second_plan_or_context_created"])

    def test_runtime_expression_profile_resolver_is_injected_without_a_second_plan(self) -> None:
        calls: list[str] = []

        def resolve_profile(
            task: ServerConfirmedProductionTask,
            retrieval: dict[str, Any],
        ) -> dict[str, Any]:
            calls.append(str(task.server_task_ref))
            scope = retrieval["resolved_scope"]
            profile = self.adapter.expression_service.neutral_profile
            return {
                "resolution_authority": "SERVER_TRUSTED_UPSTREAM",
                "requested_profile_ref": None,
                "resolved_profile_ref": profile["profile_ref"],
                "resolution_mode": profile["resolution_mode"],
                "tenant_id": scope["tenant_id"],
                "content_account_id": scope["content_account_id"],
            }

        adapter = FactAwarePlanAdapter(
            self.adapter.retrieval_service,
            self.adapter.expression_service,
            self.adapter.identity_path,
            expression_profile_resolver=resolve_profile,
        )
        result = adapter.prepare(self.task_for_case(self.case("CP03")))
        self.assertEqual(result["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(len(calls), 1)
        self.assertEqual(adapter.call_audit["package2_prepare"], 1)

    def test_narrative_only_plan_does_not_require_a_precise_fact(self) -> None:
        result = self.adapter.prepare(self.task_for_case(self.case("CP17")))
        self.assertEqual(result["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(result["references"]["precise_fact_refs"], [])
        self.assertEqual(
            result["expression_guidance"]["material_mode"],
            "DEGRADED_NARRATIVE_ONLY",
        )

    def test_untrusted_or_nonproduction_requests_do_not_enter_both_services(self) -> None:
        spoofed_mapping = {
            "authority_source": SERVER_TASK_AUTHORITY,
            "intent": START_CREATION,
            "trusted": True,
        }
        untrusted = self.adapter.prepare(spoofed_mapping)
        self.assertEqual(untrusted["object_type"], "ACTION_CARD")
        self.assertEqual(self.adapter.call_audit["package5_retrieve"], 0)
        nonproduction = self.adapter.prepare(
            self.task_for_case(self.case("CP03"), intent="FIND_INSPIRATION")
        )
        self.assertEqual(nonproduction["object_type"], "ACTION_CARD")
        unsupported_alias = self.adapter.prepare(
            self.task_for_case(
                self.case("CP03"), intent="START_CONTENT_PRODUCTION"
            )
        )
        self.assertEqual(unsupported_alias["object_type"], "ACTION_CARD")
        self.assertEqual(self.adapter.call_audit["package5_retrieve"], 0)
        self.assertEqual(self.adapter.call_audit["package2_prepare"], 0)

    def test_package5_required_fact_gap_cannot_degrade_to_narrative_plan(self) -> None:
        case = copy.deepcopy(self.case("CP17"))
        case["case_id"] = "PKG6-REQUIRED-FACT-GAP"
        case["precise_fact_queries"] = [
            {
                "fact_kind": "STOCK",
                "selectors": {"quantity": 1},
                "required": True,
            }
        ]
        case["required_precise_fact_kinds"] = []
        result = self.adapter.prepare(self.task_for_case(case))
        self.assertEqual(result["object_type"], "ACTION_CARD")
        self.assertEqual(result["action_type"], "COLLECT_FACT")
        self.assertIn(
            "PRECISE_FACT_RECONFIRMATION_REQUIRED",
            result["missing_or_invalid_refs"],
        )
        self.assertEqual(self.adapter.call_audit["package5_retrieve"], 1)
        self.assertEqual(self.adapter.call_audit["package2_prepare"], 0)

    def test_missing_product_audience_or_fact_returns_owner_action_card(self) -> None:
        missing_product_base = self.task_for_case(self.case("CP03"))
        missing_product_requirement = copy.deepcopy(
            dict(missing_product_base.confirmed_requirement)
        )
        missing_product_requirement.pop("selected_internal_content_product_id")
        missing_product = replace(
            missing_product_base,
            confirmed_requirement=missing_product_requirement,
        )
        missing_audience = self.task_for_case(
            self.case("CP03"), requirement_updates={"primary_audience": ""}
        )
        stock_case = copy.deepcopy(self.case("CP03"))
        stock_case["case_id"] = "PKG6-MISSING-STOCK"
        stock_case["precise_fact_queries"] = [
            {"fact_kind": "STOCK", "selectors": {"quantity": 1}, "required": True}
        ]
        stock_case["required_precise_fact_kinds"] = ["STOCK"]
        for task, expected in (
            (missing_product, "COLLECT_MATERIAL"),
            (missing_audience, "COLLECT_MATERIAL"),
            (self.task_for_case(stock_case), "COLLECT_FACT"),
        ):
            with self.subTest(expected=expected):
                result = self.adapter.prepare(task)
                self.assertEqual(result["object_type"], "ACTION_CARD")
                self.assertEqual(result["action_type"], expected)

    def test_client_scope_claims_cannot_expand_resolved_scope(self) -> None:
        task = self.task_for_case(
            self.case("CP17"),
            client_claims={
                "tenant_id": "TENANT-OTHER",
                "content_account_id": "ACCOUNT-DIYU-FOUNDER",
                "trusted": True,
                "administrator": True,
            },
        )
        result = self.adapter.prepare(task)
        self.assertEqual(result["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(result["content_account_id"], "ACCOUNT-DIYU-HQ-OFFICIAL")
        record = self.adapter.integration_records[-1]
        self.assertEqual(record["package5"]["gap_codes"], [])

    def test_expression_hints_never_grant_fact_or_remove_hard_rules(self) -> None:
        plan = self.adapter.prepare(self.task_for_case(self.case("CP17")))
        self.assertEqual(plan["expression_guidance"]["approved_example_refs"], [])
        self.assertFalse(
            plan["expression_guidance"]["may_grant_fact_authorization_or_scope"]
        )
        blocked = self.adapter.prepare(
            self.task_for_case(
                self.case("CP17"),
                soft_preferences={"hard_prohibitions": []},
            )
        )
        self.assertEqual(blocked["object_type"], "ACTION_CARD")
        self.assertEqual(blocked["action_type"], "BLOCK")

    def test_optional_atoms_and_ab_refs_are_diagnostics_only(self) -> None:
        plain = self.adapter.prepare(self.task_for_case(self.case("CP17")))
        diagnostic = self.adapter.prepare(
            self.task_for_case(
                self.case("CP17"),
                diagnostics={
                    "component_refs": ["UNKNOWN-COMPONENT"],
                    "edge_refs": ["UNKNOWN-EDGE"],
                    "structural_path_ref": "UNKNOWN-AB-PATH",
                },
            )
        )
        self.assertEqual(diagnostic["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(
            diagnostic["references"]["precise_fact_refs"],
            plain["references"]["precise_fact_refs"],
        )
        self.assertEqual(
            diagnostic["references"]["retrieval_fragment_refs"],
            plain["references"]["retrieval_fragment_refs"],
        )
        self.assertTrue(diagnostic["diagnostic_warnings"])

    def test_plan_material_projection_is_exact_ephemeral_and_scope_bound(self) -> None:
        plan = self.adapter.prepare(self.task_for_case(self.case("CP03")))
        projection = self.adapter.author_materials(
            plan["composition_plan_ref"], self.access()
        )
        self.assertEqual(
            projection["retrieval_fragment_refs"],
            plan["references"]["retrieval_fragment_refs"],
        )
        self.assertEqual(
            projection["precise_fact_refs"], plan["references"]["precise_fact_refs"]
        )
        self.assertTrue(
            all(row.get("text") for row in projection["scoped_retrieval_fragments"])
        )
        self.assertTrue(
            all(row.get("value") for row in projection["verified_precise_facts"])
        )
        self.assertFalse(projection["editable"])
        self.assertFalse(projection["persisted"])
        self.assertFalse(projection["context_bundle_created"])
        projection["verified_precise_facts"][0]["value"] = "MUTATED-CALLER-COPY"
        replay = self.adapter.author_materials(
            plan["composition_plan_ref"], self.access()
        )
        self.assertNotEqual(
            replay["verified_precise_facts"][0]["value"], "MUTATED-CALLER-COPY"
        )
        for ref, access in (
            (plan["composition_plan_ref"], self.access("ACCOUNT-DIYU-FOUNDER")),
            ("plan://UNKNOWN/revisions/1", self.access()),
        ):
            with self.subTest(ref=ref, account=access.content_account_id):
                with self.assertRaises(PlanMaterialAccessDenied):
                    self.adapter.author_materials(ref, access)

    def test_action_card_cannot_be_used_as_author_material_plan(self) -> None:
        action = self.adapter.prepare(self.task_for_case(self.case("CP01")))
        with self.assertRaises(PlanMaterialAccessDenied):
            self.adapter.author_materials(action["action_card_id"], self.access())

    def test_fixed_candidate_uses_package2_validate_and_rejects_outside_refs(self) -> None:
        plan = self.adapter.prepare(self.task_for_case(self.case("CP03")))
        fact_refs = tuple(plan["references"]["precise_fact_refs"])
        material_refs = tuple(plan["references"]["retrieval_fragment_refs"])
        passed = self.adapter.validate_candidate(
            plan["composition_plan_ref"],
            self.access(),
            fixed_candidate(),
            actually_used_fact_refs=fact_refs,
            actually_used_material_refs=material_refs,
            evaluation_at=FIXED_TIME,
        )
        self.assertEqual(passed["decision"], "PASS")
        self.assertEqual(
            passed["semantic_fact_review_status"], "PENDING_EXTERNAL_REVIEW"
        )
        blocked = self.adapter.validate_candidate(
            plan["composition_plan_ref"],
            self.access(),
            fixed_candidate(),
            actually_used_fact_refs=(*fact_refs, "FACT-OUTSIDE-PLAN"),
            actually_used_material_refs=material_refs,
            evaluation_at=FIXED_TIME,
        )
        self.assertEqual(blocked["decision"], "BLOCK")
        self.assertFalse(blocked["structured_hard_checks_prove_candidate_semantics"])
        self.assertEqual(self.adapter.call_audit["package2_validate"], 2)

    def test_same_input_is_deterministic_and_requirement_version_is_bound(self) -> None:
        case = self.case("CP17")
        task = self.task_for_case(case)
        first = self.adapter.prepare(task)
        second = self.adapter.prepare(task)
        replay_request = self.task_for_case(case, request_id="REQUEST-REPLAY-OTHER")
        third = self.adapter.prepare(replay_request)
        self.assertEqual(first, second)
        self.assertEqual(first, third)
        next_version = self.adapter.prepare(
            self.task_for_case(
                case,
                requirement_updates={"requirement_version": 2},
                request_id="REQUEST-NEXT-VERSION",
            )
        )
        self.assertNotEqual(first["plan_id"], next_version["plan_id"])
        self.assertEqual(next_version["requirement_version"], 2)

    def test_fact_conflict_and_expiry_cannot_form_a_plan(self) -> None:
        base_index = self.adapter.retrieval_service.index
        original = next(
            row for row in base_index.facts if row["fact_id"] == "PKG5-BD-FACT-001"
        )
        conflict = copy.deepcopy(original)
        conflict["fact_id"] = "PKG6-INJECT-CONFLICT"
        conflict["value"] = {
            "product_name": "云感圆领长袖上衣",
            "sku": "CONFLICTING-SKU",
        }
        conflict_index = replace(base_index, facts=(*base_index.facts, conflict))
        conflict_adapter = FactAwarePlanAdapter(
            BrandFactRetrievalService(
                self.adapter.retrieval_service.authority, conflict_index
            ),
            self.adapter.expression_service.__class__(REPOSITORY_ROOT),
            self.adapter.identity_path,
        )
        conflict_result = conflict_adapter.prepare(
            self.task_for_case(self.case("CP03"))
        )
        self.assertEqual(conflict_result["object_type"], "ACTION_CARD")
        self.assertEqual(conflict_result["action_type"], "COLLECT_FACT")

        expired_facts = []
        for row in base_index.facts:
            changed = copy.deepcopy(row)
            if changed["fact_id"] == "PKG5-BD-FACT-001":
                changed["valid_until"] = "2026-07-14T23:59:59Z"
            expired_facts.append(changed)
        expired_index = replace(base_index, facts=tuple(expired_facts))
        expired_adapter = FactAwarePlanAdapter(
            BrandFactRetrievalService(
                self.adapter.retrieval_service.authority, expired_index
            ),
            self.adapter.expression_service.__class__(REPOSITORY_ROOT),
            self.adapter.identity_path,
        )
        expired_result = expired_adapter.prepare(
            self.task_for_case(self.case("CP03"))
        )
        self.assertEqual(expired_result["object_type"], "ACTION_CARD")
        self.assertEqual(expired_result["action_type"], "COLLECT_FACT")

        revoked_fragments = []
        for row in base_index.fragments:
            changed = copy.deepcopy(row)
            changed["revocation_ref"] = "REVOCATION-PKG6-TEST"
            revoked_fragments.append(changed)
        revoked_index = replace(base_index, fragments=tuple(revoked_fragments))
        revoked_adapter = FactAwarePlanAdapter(
            BrandFactRetrievalService(
                self.adapter.retrieval_service.authority, revoked_index
            ),
            self.adapter.expression_service.__class__(REPOSITORY_ROOT),
            self.adapter.identity_path,
        )
        revoked_result = revoked_adapter.prepare(
            self.task_for_case(self.case("CP17"))
        )
        self.assertEqual(revoked_result["object_type"], "ACTION_CARD")
        self.assertEqual(revoked_result["action_type"], "COLLECT_MATERIAL")

    def test_all_external_call_counters_and_readiness_remain_closed(self) -> None:
        self.adapter.prepare(self.task_for_case(self.case("CP17")))
        audit = self.adapter.call_audit
        external = {key: value for key, value in audit.items() if key.startswith("external_")}
        self.assertTrue(external)
        self.assertTrue(all(value == 0 for value in external.values()))
        readiness = self.adapter.expression_service.readiness()
        self.assertFalse(readiness["DIFY_ready"])
        self.assertFalse(readiness["production_ready"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
