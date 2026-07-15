#!/usr/bin/env python3
"""Focused tests for the Phase B light-expression vertical slice."""

from __future__ import annotations

import copy
import concurrent.futures
import http.client
import json
import threading
import unittest
from pathlib import Path
from typing import Any

import yaml

from http_entrypoint import build_server
from light_expression_service import (
    LightExpressionService,
    TrustedUpstreamContext,
    parse_time,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
CONTRACT_PATH = (
    REPOSITORY_ROOT
    / "11_product_foundation/public_foundation_001/contract/public_foundation_contract.v1.yaml"
)
IDENTITY_PATH = (
    REPOSITORY_ROOT
    / "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml"
)
FIXED_TIME = parse_time("2026-07-14T00:00:00Z")


def contract_prepare_request() -> dict[str, Any]:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))["public_foundation_contract"]
    return copy.deepcopy(contract["api_contracts"][0]["request_example"])


def service_and_context() -> tuple[LightExpressionService, TrustedUpstreamContext]:
    return (
        LightExpressionService(REPOSITORY_ROOT),
        TrustedUpstreamContext.from_simulation_identity(IDENTITY_PATH),
    )


def valid_candidate() -> dict[str, Any]:
    return {
        "candidate_id": "CANDIDATE-SIM-001",
        "candidate_version": 1,
        "candidate_user_visible_surfaces": {
            "title": "先看材料留下的线索",
            "body": "这份候选只使用计划中已经允许的模拟资料。",
            "spoken_lines": ["先把能够确认的部分讲清楚。"],
            "CTA": "需要时可以继续核对资料。",
            "execution_payload": {"visual_direction": "只拍已有材料能够支持的画面"},
            "surface_units": [{"kind": "caption", "text": "语义事实仍待独立复核"}],
        },
    }


def valid_validation(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "api_version": "v1",
        "request_id": "REQ-SIM-VALIDATE-001",
        "trusted_scope_ref": plan["references"]["trusted_scope_ref"],
        "trusted_scope": {
            "tenant_id": plan["tenant_id"],
            "brand_id": "BRAND-DIYU-SIM-001",
            "organization_id": plan["organization_id"],
            "store_id": None,
            "login_principal_id": "SIM-LOGIN-DIYU-ACCEPTANCE-001",
            "content_account_id": plan["content_account_id"],
        },
        "composition_plan_ref": plan["composition_plan_ref"],
        "candidate": valid_candidate(),
        "actually_used_fact_refs": list(plan["references"]["precise_fact_refs"]),
        "actually_used_material_refs": list(plan["references"]["retrieval_fragment_refs"]),
    }


def request_json(
    host: str,
    port: int,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    connection = http.client.HTTPConnection(host, port, timeout=5)
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {} if body is None else {"Content-Type": "application/json"}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    parsed = json.loads(response.read().decode("utf-8"))
    connection.close()
    return response.status, parsed


class PrepareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service, self.context = service_and_context()
        self.request = contract_prepare_request()

    def prepare(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.service.prepare(request or self.request, self.context, FIXED_TIME)

    def test_valid_request_without_atom_references_uses_neutral_profile(self) -> None:
        result = self.prepare()
        self.assertEqual(result["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(
            result["references"]["brand_expression_profile_ref"],
            "expression-profile://neutral-default/v1",
        )
        self.assertEqual(result["references"]["experimental_diagnostics"], {})
        self.assertFalse(result["authoring_boundary"]["audience_body_in_plan"])
        self.assertNotIn("body", result)

    def test_request_id_does_not_change_deterministic_plan(self) -> None:
        first = self.prepare()
        changed = copy.deepcopy(self.request)
        changed["request_id"] = "REQ-SIM-PREPARE-CHANGED"
        second = self.prepare(changed)
        self.assertEqual(first, second)

    def test_concurrent_replay_keeps_one_deterministic_plan(self) -> None:
        requests = []
        for index in range(12):
            request = copy.deepcopy(self.request)
            request["request_id"] = f"REQ-CONCURRENT-{index:02d}"
            requests.append(request)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(self.prepare, requests))
        self.assertTrue(all(result == results[0] for result in results))

    def test_changed_semantic_input_creates_new_revision_not_competing_plan(self) -> None:
        first = self.prepare()
        changed = copy.deepcopy(self.request)
        changed["client_soft_preferences"]["rhythm"] = "measured"
        second = self.prepare(changed)
        self.assertEqual(first["plan_id"], second["plan_id"])
        self.assertEqual(second["plan_revision"], 2)
        self.assertIsNone(self.service.store.get(first["composition_plan_ref"]))

    def test_optional_unknown_atom_references_do_not_grant_authority(self) -> None:
        base = self.prepare()
        changed = copy.deepcopy(self.request)
        changed["experimental_diagnostics"] = {
            "component_refs": ["UNKNOWN-COMPONENT"],
            "edge_refs": ["UNKNOWN-EDGE"],
            "structural_path_ref": "UNKNOWN-PATH",
        }
        result = self.prepare(changed)
        self.assertEqual(result["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(result["references"]["precise_fact_refs"], base["references"]["precise_fact_refs"])
        self.assertEqual(
            result["references"]["retrieval_fragment_refs"],
            base["references"]["retrieval_fragment_refs"],
        )
        self.assertTrue(result["diagnostic_warnings"])
        self.assertFalse(result["expression_guidance"]["may_grant_fact_authorization_or_scope"])

    def test_client_cannot_override_hard_prohibitions(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["client_soft_preferences"]["hard_prohibitions"] = []
        result = self.prepare(changed)
        self.assertEqual(result["object_type"], "ACTION_CARD")
        self.assertEqual(result["action_type"], "BLOCK")

    def test_self_claimed_trust_field_is_rejected(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["trusted"] = True
        result = self.prepare(changed)
        self.assertEqual(result["action_type"], "BLOCK")
        self.assertIn("自我声明", result["plain_language_reason"])

    def test_body_cannot_create_trust_without_server_context(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["trusted_scope"]["trusted"] = True
        changed["verified_precise_facts"][0]["verified"] = True
        result = self.service.prepare(changed, None, FIXED_TIME)
        self.assertEqual(result["action_type"], "BLOCK")
        self.assertIn("服务端确认", result["plain_language_reason"])

    def test_fact_only_input_degrades_safely(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["scoped_retrieval_fragments"] = []
        result = self.prepare(changed)
        self.assertEqual(result["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(result["expression_guidance"]["material_mode"], "DEGRADED_FACT_ONLY")

    def test_narrative_only_input_degrades_safely(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["verified_precise_facts"] = []
        result = self.prepare(changed)
        self.assertEqual(result["object_type"], "LIGHT_CONTENT_PLAN")
        self.assertEqual(result["expression_guidance"]["material_mode"], "DEGRADED_NARRATIVE_ONLY")

    def test_empty_material_and_facts_returns_collection_card(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["scoped_retrieval_fragments"] = []
        changed["verified_precise_facts"] = []
        result = self.prepare(changed)
        self.assertEqual(result["object_type"], "ACTION_CARD")
        self.assertEqual(result["action_type"], "COLLECT_MATERIAL")
        self.assertFalse(result["publishable_candidate_included"])

    def test_missing_fact_authorization_requests_authorization(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["verified_precise_facts"][0]["authorization_ref"] = "AUTH-MISSING"
        result = self.prepare(changed)
        self.assertEqual(result["action_type"], "REQUEST_AUTHORIZATION")

    def test_missing_fact_source_requests_fact(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["verified_precise_facts"][0]["source_ref"] = ""
        result = self.prepare(changed)
        self.assertEqual(result["action_type"], "COLLECT_FACT")

    def test_expired_and_revoked_inputs_fail_closed(self) -> None:
        for field, value, expected in (
            ("valid_until", "2026-07-13T00:00:00Z", "COLLECT_FACT"),
            ("status", "REVOKED", "COLLECT_FACT"),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.request)
                changed["verified_precise_facts"][0][field] = value
                result = self.prepare(changed)
                self.assertEqual(result["action_type"], expected)

    def test_cross_tenant_store_and_account_fail_closed(self) -> None:
        mutations = (
            ("tenant", lambda value: value["trusted_scope"].__setitem__("tenant_id", "TENANT-OTHER")),
            (
                "store",
                lambda value: value["verified_precise_facts"][0].__setitem__(
                    "store_id", "STORE-DIYU-SZ-PARK"
                ),
            ),
            (
                "account",
                lambda value: value["trusted_scope"].__setitem__(
                    "content_account_id", "ACCOUNT-NOT-ALLOWED"
                ),
            ),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                changed = copy.deepcopy(self.request)
                mutate(changed)
                result = self.prepare(changed)
                self.assertEqual(result["action_type"], "BLOCK")

    def test_missing_person_confirmation_routes_to_anonymize(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["acting_role_id"] = "ROLE-HQ-CONTENT-TEAM"
        changed["confirmation_evidence"] = {
            "confirmed_by_principal_id": "SIM-LOGIN-DIYU-ACCEPTANCE-001",
            "confirmed_by_role_ids": ["ROLE-GU-JINYAN"],
            "confirmation_scope": "person_and_customer_authorization",
            "authorization_refs": ["AUTH-SIM-CONFIRM-001"],
            "subject_confirmation_ref": None,
        }
        result = self.prepare(changed)
        self.assertEqual(result["action_type"], "ANONYMIZE")

    def test_candidate_count_and_difference_policy_are_explicit(self) -> None:
        result = self.prepare()
        self.assertEqual(result["candidate_policy"]["required_candidate_count"], 3)
        self.assertGreaterEqual(len(result["candidate_policy"]["difference_dimensions"]), 4)
        self.assertFalse(result["candidate_policy"]["near_duplicate_rewording_counts_as_distinct"])
        for count in (1, 4):
            with self.subTest(count=count):
                changed = copy.deepcopy(self.request)
                changed["output_requirements"]["required_candidate_count"] = count
                self.assertEqual(self.prepare(changed)["action_type"], "BLOCK")


class ValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service, self.context = service_and_context()
        self.prepare_request = contract_prepare_request()
        self.plan = self.service.prepare(self.prepare_request, self.context, FIXED_TIME)
        self.request = valid_validation(self.plan)

    def validate(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.service.validate(request or self.request, self.context, FIXED_TIME)

    def test_structured_pass_keeps_semantic_review_pending_and_scores_empty(self) -> None:
        result = self.validate()
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["hard_issues"], [])
        self.assertEqual(result["semantic_fact_review_status"], "PENDING_EXTERNAL_REVIEW")
        self.assertFalse(result["structured_hard_checks_prove_candidate_semantics"])
        self.assertIn("语义事实仍需外部复核", result["plain_language_reason"])
        self.assertTrue(
            all(item["score"] is None for item in result["soft_evaluation_tasks"])
        )

    def test_used_references_must_be_plan_subsets(self) -> None:
        for field, value, category in (
            ("actually_used_fact_refs", ["FACT-NOT-IN-PLAN"], "fact_support"),
            ("actually_used_material_refs", ["FRAGMENT-NOT-IN-PLAN"], "source_provenance"),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.request)
                changed[field] = value
                result = self.validate(changed)
                self.assertEqual(result["decision"], "BLOCK")
                self.assertIn(category, {item["category"] for item in result["hard_issues"]})

    def test_all_user_visible_surfaces_are_scanned_for_internal_leaks(self) -> None:
        paths = (
            ("title", "内部产品 CP02"),
            ("body", "raw E_INTERNAL_FAILURE"),
            ("spoken_lines", ["required_fact_missing"]),
            ("CTA", "查看 BNO-01"),
            ("execution_payload", {"direction": "publish_allowed false"}),
            ("surface_units", [{"component_id": "hidden"}]),
        )
        for field, value in paths:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.request)
                changed["candidate"]["candidate_user_visible_surfaces"][field] = value
                result = self.validate(changed)
                self.assertEqual(result["decision"], "BLOCK")
                self.assertIn(
                    "internal_identifier_leak",
                    {item["category"] for item in result["hard_issues"]},
                )

    def test_unknown_surface_field_is_blocked(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["candidate"]["candidate_user_visible_surfaces"]["internal_trace"] = "hidden"
        result = self.validate(changed)
        self.assertEqual(result["decision"], "BLOCK")

    def test_obvious_contact_information_is_a_privacy_hard_issue(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["candidate"]["candidate_user_visible_surfaces"]["CTA"] = "请联系 13812345678"
        result = self.validate(changed)
        self.assertEqual(result["decision"], "BLOCK")
        self.assertIn("privacy", {item["category"] for item in result["hard_issues"]})

    def test_empty_candidate_is_revise_not_fabricated_quality_score(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["candidate"]["candidate_user_visible_surfaces"] = {}
        result = self.validate(changed)
        self.assertEqual(result["decision"], "REVISE")
        self.assertEqual(result["hard_issues"], [])
        self.assertTrue(all(item["score"] is None for item in result["soft_evaluation_tasks"]))

    def test_pure_creative_difference_is_not_a_fact_hard_issue(self) -> None:
        changed = copy.deepcopy(self.request)
        changed["candidate"]["candidate_user_visible_surfaces"]["body"] = "从另一种叙事顺序展开。"
        result = self.validate(changed)
        self.assertEqual(result["decision"], "PASS")
        self.assertNotIn("candidate_difference", {item["category"] for item in result["hard_issues"]})

    def test_expired_source_after_prepare_blocks_validation(self) -> None:
        result = self.service.validate(
            self.request,
            self.context,
            parse_time("2027-01-01T00:00:00Z"),
        )
        self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(result["semantic_fact_review_status"], "NOT_REACHED")
        self.assertIn(
            "effective_time_and_revocation",
            {item["category"] for item in result["hard_issues"]},
        )

    def test_wrong_scope_and_unknown_plan_fail_closed(self) -> None:
        wrong_scope = copy.deepcopy(self.request)
        wrong_scope["trusted_scope"]["tenant_id"] = "TENANT-OTHER"
        self.assertEqual(self.validate(wrong_scope)["decision"], "BLOCK")
        unknown_plan = copy.deepcopy(self.request)
        unknown_plan["composition_plan_ref"] = "plan://UNKNOWN/revisions/1"
        self.assertEqual(self.validate(unknown_plan)["decision"], "BLOCK")

    def test_validation_is_deterministic(self) -> None:
        first = self.validate()
        changed = copy.deepcopy(self.request)
        changed["request_id"] = "REQ-SIM-VALIDATE-CHANGED"
        second = self.validate(changed)
        self.assertEqual(first, second)


class HttpTests(unittest.TestCase):
    def _run_server(
        self,
        context: TrustedUpstreamContext | None,
    ) -> tuple[Any, threading.Thread, int]:
        service = LightExpressionService(REPOSITORY_ROOT)
        server = build_server("127.0.0.1", 0, service, context)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, int(server.server_address[1])

    def test_four_http_endpoints_run_locally(self) -> None:
        _, context = service_and_context()
        server, thread, port = self._run_server(context)
        try:
            health_status, health = request_json("127.0.0.1", port, "GET", "/healthz")
            ready_status, ready = request_json("127.0.0.1", port, "GET", "/readyz")
            prepare_status, plan = request_json(
                "127.0.0.1", port, "POST", "/v1/content/prepare", contract_prepare_request()
            )
            validation = valid_validation(plan)
            validate_status, decision = request_json(
                "127.0.0.1", port, "POST", "/v1/content/validate", validation
            )
            self.assertEqual((health_status, health["status"]), (200, "ok"))
            self.assertEqual((ready_status, ready["ready"]), (200, True))
            self.assertFalse(ready["global_readiness_changed"])
            self.assertFalse(ready["DIFY_ready"])
            self.assertFalse(ready["production_ready"])
            self.assertEqual((prepare_status, plan["object_type"]), (200, "LIGHT_CONTENT_PLAN"))
            self.assertEqual((validate_status, decision["decision"]), (200, "PASS"))
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_http_body_cannot_self_create_trusted_context(self) -> None:
        server, thread, port = self._run_server(None)
        try:
            payload = contract_prepare_request()
            payload["trusted"] = True
            status, result = request_json("127.0.0.1", port, "POST", "/v1/content/prepare", payload)
            self.assertEqual(status, 403)
            self.assertEqual(result["object_type"], "ACTION_CARD")
            self.assertEqual(result["action_type"], "BLOCK")
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_simulation_context_cannot_bind_non_loopback_host(self) -> None:
        service, context = service_and_context()
        with self.assertRaisesRegex(ValueError, "loopback"):
            build_server("0.0.0.0", 0, service, context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
