#!/usr/bin/env python3
"""M2-C1b S0 真实运行的确定性构建与复算校验工具。

本脚本只服务本次运行（结构差异不强行通用化）；一切阶段可从已提交输入
纯确定性重建，`verify-all` 是唯一裁决出口（复算不一致即非零退出）。

子命令：
  build-bundle             输入冻结 → 请求 bundle（分配/材料/请求三闭合）
  build-expected-manifest  bundle → 12 事件预登记清单（registered_before_run）
  gate                     首次尝试 → 序列化输出 + 确定性门报告
  metrics                  + 双评审 → 批度量
  telemetry                run_log → v4 遥测事件 + 摘要 + 运行清单
  cost-events              遥测/回执 → 12 条 spine 成本事件 + 来源清单 + 计量 + 记账门
  stage-gate               六门布尔复算 → S0 stage_decision
  verify-all               全链从盘复算，输出裁决 JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parents[1]
ES = RUN_DIR.parents[1]
P7 = ES.parent
GENERATOR_DIR = P7.parents[1] / "generator_v3_successor_001"
sys.path.insert(0, str(ES))
sys.path.insert(0, str(GENERATOR_DIR))

from spine import cost as spine_cost  # noqa: E402
from spine import stage_gate as spine_stage_gate  # noqa: E402
from spine.canonical import digest_json  # noqa: E402
from v4_recovery import (author_contract, contract, deterministic_gates,  # noqa: E402
                         material_policy, metrics, request_builder,
                         telemetry, test_allocator)

RUN_ID = "S0M2-RUN-001"
BATCH_ID = "S0M2-BATCH-001"
ASSIGNMENT_SET_ID = "S0M2-ASSIGNMENT-SET-001"
STAGE_ID = "S0_DETERMINISTIC_HYGIENE"
BUDGET_CATEGORY = "one_time_gold_and_measurement_usd"
AUTHOR_IDENTITY = "M2-S0-AUTHOR-FABLE5"
MODEL_CONFIG_REF = "MODEL-CONFIG-S0M2-001"
PAIRS = [
    ("PAIR-S0M2-01", "CASE-S0M2-CP01-001", "CASE-S0M2-CP02-001"),
    ("PAIR-S0M2-02", "CASE-S0M2-CP04-001", "CASE-S0M2-CP07-001"),
    ("PAIR-S0M2-03", "CASE-S0M2-CP01-001", "CASE-S0M2-CP04-001"),
]
REVIEWERS = {
    "CONTENT_REVIEW": "M2-S0-CONTENT-REVIEWER",
    "FACT_REVIEW": "M2-S0-FACT-REVIEWER",
    "METRICS_AUDIT": "M2-S0-METRICS-AUDITOR",
}
FORBIDDEN_PLAN_FIELD_NAMES = {"content_composition_plan", "expression_plan",
                              "runtime_plan"}


def _read(rel: str):
    return json.loads((RUN_DIR / rel).read_text(encoding="utf-8"))


def _write(rel: str, value) -> None:
    path = RUN_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")


def _span(source_id: str, source_text: str, quote: str) -> dict:
    char_start = source_text.index(quote)
    byte_start = len(source_text[:char_start].encode("utf-8"))
    return {"source_id": source_id, "byte_start": byte_start,
            "byte_end": byte_start + len(quote.encode("utf-8")), "quote": quote}


def _raw_materials() -> list[dict]:
    spec = _read("inputs/materials_spec.v1.json")
    raws: list[dict] = []
    for material in spec["materials"]:
        source_by_id = {row["source_id"]: row["source_text"]
                        for row in material["sources"]}
        facts = []
        for fact in material["facts"]:
            source_id = material["sources"][0]["source_id"]
            facts.append({
                "fact_id": fact["fact_id"], "slot_id": fact["slot_id"],
                "fact_value": fact["fact_value"], "source_ids": [source_id],
                "evidence_spans": [_span(source_id, source_by_id[source_id],
                                         fact["quote"])],
                "authorization_ids": [material["authorizations"][0][
                    "authorization_id"]],
                "surface_policy": fact["surface_policy"],
                "conditions": list(fact["conditions"]),
                "prohibited_surface_terms": list(
                    fact["prohibited_surface_terms"]),
            })
        raws.append({"scenario_id": material["scenario_id"],
                     "profile_id": material["profile_id"],
                     "sources": [dict(row) for row in material["sources"]],
                     "authorizations": [dict(row) for row in
                                        material["authorizations"]],
                     "facts": facts})
    return raws


def build_bundle() -> dict:
    scenarios = _read("inputs/scenarios.v1.json")["scenarios"]
    materials = [material_policy.normalize_material(raw)
                 for raw in _raw_materials()]
    material_by_id = {m["scenario_id"]: m for m in materials}
    cases = []
    for scenario in scenarios:
        material = material_by_id[scenario["scenario_id"]]
        case = dict(scenario)
        case["scenario_digest"] = test_allocator.scenario_digest_for_case(
            scenario)
        case["material_packet_digest"] = material["material_digest"]
        case["evidence_surface_policy"] = [
            {"reference_assertion_id": fact["fact_id"],
             "policy": fact["surface_policy"],
             "reason_code": f"EXPLICIT_{fact['surface_policy']}"}
            for fact in material["facts"]]
        case["forbidden_inferences"] = list(scenario["forbidden_inferences"])
        case["paired_assignment_id"] = None
        cases.append(case)
    assignments = test_allocator.allocate_test_assignments(
        cases, ASSIGNMENT_SET_ID)
    authors = {scenario["profile_id"]: {
        "author_identity": AUTHOR_IDENTITY,
        "model_config_ref": MODEL_CONFIG_REF} for scenario in scenarios}
    requests = request_builder.build_batch(
        scenarios, materials, assignments, batch_id=BATCH_ID, run_id=RUN_ID,
        authors_by_profile=authors)
    bundle = {
        "schema_version": "s0m2-request-bundle-v1",
        "run_id": RUN_ID, "batch_id": BATCH_ID,
        "assignment_set_id": ASSIGNMENT_SET_ID,
        "assignments": assignments, "materials": materials,
        "requests": requests, "bundle_digest": "",
    }
    contract.close_digest(bundle, "bundle_digest")
    return bundle


def cmd_build_bundle() -> int:
    bundle = build_bundle()
    _write("bundle/request_bundle.v1.json", bundle)
    print(json.dumps({"bundle_digest": bundle["bundle_digest"],
                      "requests": len(bundle["requests"])},
                     ensure_ascii=False))
    return 0


def expected_events(bundle: dict) -> list[dict]:
    request_ids = sorted(r["request_id"] for r in bundle["requests"])
    rows = []
    for kind, prefix in (("CONTENT_REVIEW", "CR"), ("FACT_REVIEW", "FR")):
        for index, request_id in enumerate(request_ids, 1):
            rows.append({"event_id": f"EV-S0M2-{prefix}-{index:02d}",
                         "stage_id": STAGE_ID, "task_kind": kind,
                         "resource_kind": "HUMAN_REVIEW",
                         "budget_category": BUDGET_CATEGORY,
                         "object_id": request_id})
    for index, (pair_id, _, _) in enumerate(PAIRS, 1):
        rows.append({"event_id": f"EV-S0M2-DS-{index:02d}",
                     "stage_id": STAGE_ID,
                     "task_kind": "FORMULAIC_PAIR_SCREEN",
                     "resource_kind": "MODEL_CALL",
                     "budget_category": BUDGET_CATEGORY,
                     "object_id": pair_id})
    rows.append({"event_id": "EV-S0M2-MA-01", "stage_id": STAGE_ID,
                 "task_kind": "METRICS_AUDIT",
                 "resource_kind": "HUMAN_REVIEW",
                 "budget_category": BUDGET_CATEGORY,
                 "object_id": f"BATCH::{BATCH_ID}"})
    return rows


def cmd_build_expected_manifest() -> int:
    bundle = _read("bundle/request_bundle.v1.json")
    manifest = {
        "schema_version": "eval-spine-expected-cost-events-v1",
        "stage_scope": STAGE_ID,
        "registered_before_run": True,
        "custodian_identity": "M2_PRINCIPAL_ORCHESTRATOR",
        "approved_by": ("v2.5 §〇 流水线内默认授权 + "
                        "S0_REAL_RUN_AUTHORIZATION.v1.json"),
        "approved_at": "2026-07-17T04:45:00+00:00",
        "source_run_manifest_digest": bundle["bundle_digest"],
        "expected_events": expected_events(bundle),
        "manifest_digest": "",
    }
    unsigned = {k: v for k, v in manifest.items() if k != "manifest_digest"}
    manifest["manifest_digest"] = digest_json(unsigned)
    _write("cost/expected_event_manifest.v1.json", manifest)
    print(json.dumps({"manifest_digest": manifest["manifest_digest"],
                      "expected_events": len(manifest["expected_events"])},
                     ensure_ascii=False))
    return 0


def _sealed_outputs(bundle: dict, raws: list[dict]) -> list[dict]:
    request_by_id = {r["request_id"]: r for r in bundle["requests"]}
    raw_by_id = {r["request_id"]: r for r in raws}
    assert set(raw_by_id) == set(request_by_id), "raw/request coverage"
    return [author_contract.serialize(raw_by_id[request_id],
                                      request_by_id[request_id])
            for request_id in sorted(request_by_id)]


def cmd_gate() -> int:
    bundle = _read("bundle/request_bundle.v1.json")
    raws = _read("outputs/raw_first_attempts.v1.json")["attempts"]
    outputs = _sealed_outputs(bundle, raws)
    _write("outputs/sealed_outputs.v1.json", {"outputs": outputs})
    report = deterministic_gates.gate_batch(outputs, bundle["requests"])
    _write("gates/gate_report.v1.json", report)
    print(json.dumps({
        "report_digest": report["report_digest"],
        "hard_fail_count": report["machine_hard_fail_count"],
        "hard_veto_count": report["machine_hard_veto_count"],
        "whole_batch_machine_hard_veto_zero": report[
            "whole_batch_machine_hard_veto_zero"]}, ensure_ascii=False))
    return 0


def cmd_metrics() -> int:
    bundle = _read("bundle/request_bundle.v1.json")
    outputs = _read("outputs/sealed_outputs.v1.json")["outputs"]
    report = _read("gates/gate_report.v1.json")
    content = _read("reviews/content_reviews.v1.json")["reviews"]
    fact = _read("reviews/fact_reviews.v1.json")["reviews"]
    batch_metrics = metrics.compute_batch_metrics(
        outputs, bundle["requests"], report, content, fact)
    _write("gates/batch_metrics.v1.json", batch_metrics)
    print(json.dumps({
        "metrics_digest": batch_metrics["metrics_digest"],
        "first_acceptance_rate": batch_metrics["first_acceptance_rate"],
        "whole_batch_hard_veto_count": batch_metrics[
            "whole_batch_hard_veto_count"]}, ensure_ascii=False))
    return 0


def _model_unavailable(reason: str) -> dict:
    return telemetry.unavailable(reason)


def _usage_unavailable() -> dict:
    reason = "Claude Code 会话/子代理推理不向会话暴露逐次令牌用量"
    return {field: telemetry.unavailable(reason)
            for field in telemetry.USAGE_FIELDS}


def _cost_unavailable() -> dict:
    reason = "会话内推理无独立计费回执（成本账范围声明见 plan/S0_RUN_PLAN.v1.md）"
    return {"amount": telemetry.unavailable(reason),
            "currency": telemetry.unavailable(reason),
            "rate_card_ref": telemetry.unavailable(reason)}


def _v4_events(bundle: dict, outputs: list[dict], report: dict,
               content: list[dict], fact: list[dict],
               batch_metrics: dict, log: dict) -> list[dict]:
    request_by_id = {r["request_id"]: r for r in bundle["requests"]}
    output_by_id = {o["request_id"]: o for o in outputs}
    content_by_id = {r["request_id"]: r for r in content}
    fact_by_id = {r["request_id"]: r for r in fact}
    author_cfg = log["author_model_config"]
    reviewer_cfg = log["reviewer_model_config"]
    local_cfg = {"provider": "local", "model_family": "deterministic-v4",
                 "model_revision": f"v4-recovery-{contract.RULE_VERSION}",
                 "reasoning_effort": "none", "temperature": 0, "top_p": 1,
                 "seed": 0}
    events: list[dict] = []
    for index, request_id in enumerate(sorted(request_by_id), 1):
        window = log["author_windows"][request_id]
        events.append(telemetry.make_event(
            event_id=f"V4EV-AU-{index:02d}", run_id=RUN_ID, batch_id=BATCH_ID,
            stage="AUTHOR_GENERATION", operation_kind="AUTHOR_GENERATION",
            request_id=request_id, attempt_index=1, status="SUCCESS",
            started_at=window["started_at"], completed_at=window["completed_at"],
            input_digest=request_by_id[request_id]["request_digest"],
            output_digest=output_by_id[request_id]["output_digest"],
            provider_call_id=f"s0m2:author:{request_id}:attempt:1",
            reviewer_minutes=0,
            model_config=author_cfg, usage=_usage_unavailable(),
            cost=_cost_unavailable()))
    for index, request_id in enumerate(sorted(request_by_id), 1):
        events.append(telemetry.make_event(
            event_id=f"V4EV-DG-{index:02d}", run_id=RUN_ID, batch_id=BATCH_ID,
            stage="MACHINE_GATE", operation_kind="DETERMINISTIC_GATE",
            request_id=request_id, attempt_index=0, status="SUCCESS",
            started_at=log["gate_window"]["started_at"],
            completed_at=log["gate_window"]["completed_at"],
            input_digest=output_by_id[request_id]["output_digest"],
            output_digest=report["report_digest"],
            provider_call_id=f"s0m2:gate:{request_id}",
            reviewer_minutes=0, model_config=local_cfg,
            usage={field: 0 for field in telemetry.USAGE_FIELDS},
            cost={"amount": 0, "currency": "USD",
                  "rate_card_ref": "LOCAL-DETERMINISTIC-ZERO-COST"}))
    for kind, rows_by_id, prefix in (("CONTENT_REVIEW", content_by_id, "CR"),
                                     ("FACT_REVIEW", fact_by_id, "FR")):
        window = log["review_windows"][kind]
        for index, request_id in enumerate(sorted(request_by_id), 1):
            events.append(telemetry.make_event(
                event_id=f"V4EV-{prefix}-{index:02d}", run_id=RUN_ID,
                batch_id=BATCH_ID, stage="HUMAN_REVIEW", operation_kind=kind,
                request_id=request_id, attempt_index=0, status="SUCCESS",
                started_at=window["started_at"],
                completed_at=window["completed_at"],
                input_digest=output_by_id[request_id]["output_digest"],
                output_digest=telemetry.review_record_digest(
                    rows_by_id[request_id]),
                provider_call_id=f"s0m2:{kind.lower()}:{request_id}",
                reviewer_minutes=window["reviewer_minutes_per_item"],
                model_config=reviewer_cfg, usage=_usage_unavailable(),
                cost=_cost_unavailable()))
    events.append(telemetry.make_event(
        event_id="V4EV-ME-01", run_id=RUN_ID, batch_id=BATCH_ID,
        stage="METRICS", operation_kind="METRICS_AGGREGATION",
        request_id=f"BATCH::{BATCH_ID}", attempt_index=0, status="SUCCESS",
        started_at=log["metrics_window"]["started_at"],
        completed_at=log["metrics_window"]["completed_at"],
        input_digest=telemetry.evaluation_input_digest(report, content, fact),
        output_digest=batch_metrics["metrics_digest"],
        provider_call_id=f"s0m2:metrics:{BATCH_ID}",
        reviewer_minutes=0, model_config=local_cfg,
        usage={field: 0 for field in telemetry.USAGE_FIELDS},
        cost={"amount": 0, "currency": "USD",
              "rate_card_ref": "LOCAL-DETERMINISTIC-ZERO-COST"}))
    return events


def cmd_telemetry() -> int:
    bundle = _read("bundle/request_bundle.v1.json")
    outputs = _read("outputs/sealed_outputs.v1.json")["outputs"]
    report = _read("gates/gate_report.v1.json")
    content = _read("reviews/content_reviews.v1.json")["reviews"]
    fact = _read("reviews/fact_reviews.v1.json")["reviews"]
    batch_metrics = _read("gates/batch_metrics.v1.json")
    log = _read("telemetry/run_log.v1.json")
    events = _v4_events(bundle, outputs, report, content, fact,
                        batch_metrics, log)
    telemetry.validate_qualification_coverage(
        events, bundle["requests"], outputs, report, content, fact,
        batch_metrics, run_id=RUN_ID, batch_id=BATCH_ID)
    summary = telemetry.summarize_events(events)
    manifest = telemetry.build_run_manifest(
        run_id=RUN_ID, stage_gate="GATE1_QUALIFICATION", batch_id=BATCH_ID,
        schema_version_ref=contract.REQUEST_SCHEMA,
        content_product_profile_version="CP-PROFILES-V1",
        evaluation_case_set_version="S0M2-CASESET-V1",
        checker_versions={"v4_recovery": contract.RULE_VERSION},
        model_or_engine_config_ref=telemetry.model_config_binding_ref(
            bundle["requests"]),
        randomization_config={"seed": 0,
                              "batch_id_affects_assignment": False},
        input_manifest_ref="bundle/request_bundle.v1.json#requests",
        input_manifest_digest=telemetry.object_manifest_digest(
            bundle["requests"], id_field="request_id",
            digest_field="request_digest"),
        output_manifest_ref="outputs/sealed_outputs.v1.json#outputs",
        output_manifest_digest=telemetry.object_manifest_digest(
            outputs, id_field="request_id", digest_field="output_digest"),
        started_at=log["run_window"]["started_at"],
        completed_at=log["run_window"]["completed_at"],
        human_review_batch_ref="reviews/",
        telemetry_summary_digest=summary["summary_digest"])
    _write("telemetry/v4_events.v1.json", {"events": events})
    _write("telemetry/telemetry_summary.v1.json", summary)
    _write("telemetry/run_manifest.v1.json", manifest)
    print(json.dumps({"events": len(events),
                      "telemetry_complete": summary["telemetry_complete"],
                      "summary_digest": summary["summary_digest"],
                      "run_manifest_digest": manifest["manifest_digest"]},
                     ensure_ascii=False))
    return 0


def _receipts() -> list[dict]:
    rows = []
    for index in range(1, len(PAIRS) + 1):
        rows.append(_read(f"external/deepseek_receipt_pair{index:02d}.v1.json"))
    return rows


def _cost_events(log: dict, v4_events: list[dict],
                 rate_card: dict) -> list[dict]:
    events: list[dict] = []
    v4_by_id = {e["event_id"]: e for e in v4_events}
    request_ids = sorted({e["request_id"] for e in v4_events
                          if e["operation_kind"] == "AUTHOR_GENERATION"})

    def human_event(event_id: str, task_kind: str, object_id: str,
                    reviewer_identity: str, minutes: float,
                    source_digest: str, wall_seconds: float) -> dict:
        hourly = rate_card["labor_rates"][reviewer_identity]
        event = {
            "schema_version": "eval-spine-cost-event-v1",
            "event_id": event_id, "stage_id": STAGE_ID,
            "task_kind": task_kind, "object_id": object_id,
            "resource_kind": "HUMAN_REVIEW",
            "budget_category": BUDGET_CATEGORY,
            "outcome_status": "SUCCEEDED",
            "source_telemetry_event_digest": source_digest,
            "attempt_id": None, "provider": None, "model_revision": None,
            "provider_call_id": None, "input_tokens": None,
            "cached_input_tokens": None, "output_tokens": None,
            "price_snapshot_id": None, "model_cost_usd": None,
            "reviewer_minutes": minutes,
            "reviewer_identity": reviewer_identity,
            "labor_rate_snapshot_id": rate_card["snapshot_id"],
            "human_cost_usd": hourly * minutes / 60,
            "wall_clock_seconds": wall_seconds,
            "unavailable_reasons": {
                "attempt_id": "not applicable to review work",
                "provider": "模型角色评审无外部提供方",
                "model_revision": "同上（角色登记见 AGENT_LEDGER.M2）",
                "provider_call_id": "无外部调用回执",
                "input_tokens": "会话/子代理推理不暴露令牌用量",
                "cached_input_tokens": "同上",
                "output_tokens": "同上",
                "price_snapshot_id": "无模型计费（劳务快照见 labor_rate_snapshot_id）",
                "model_cost_usd": "无模型计费；劳务成本已按费率卡复算",
            },
            "event_digest": "",
        }
        unsigned = {k: v for k, v in event.items() if k != "event_digest"}
        event["event_digest"] = digest_json(unsigned)
        return event

    for prefix, kind in (("CR", "CONTENT_REVIEW"), ("FR", "FACT_REVIEW")):
        window = log["review_windows"][kind]
        minutes = window["reviewer_minutes_per_item"]
        wall = minutes * 60
        for index, request_id in enumerate(request_ids, 1):
            source = v4_by_id[f"V4EV-{prefix}-{index:02d}"]["event_digest"]
            events.append(human_event(
                f"EV-S0M2-{prefix}-{index:02d}", kind, request_id,
                REVIEWERS[kind], minutes, source, wall))

    for index, receipt in enumerate(_receipts(), 1):
        usage = receipt["usage"]
        cached = usage.get("prompt_cache_hit_tokens", 0)
        event = {
            "schema_version": "eval-spine-cost-event-v1",
            "event_id": f"EV-S0M2-DS-{index:02d}", "stage_id": STAGE_ID,
            "task_kind": "FORMULAIC_PAIR_SCREEN",
            "object_id": PAIRS[index - 1][0],
            "resource_kind": "MODEL_CALL",
            "budget_category": BUDGET_CATEGORY,
            "outcome_status": ("SUCCEEDED"
                               if receipt["call_status"] == "VALID"
                               else "FAILED"),
            "source_telemetry_event_digest": receipt["receipt_digest"],
            "attempt_id": f"{PAIRS[index - 1][0]}:attempt:1",
            "provider": receipt["provider"],
            "model_revision": receipt["model_revision"],
            "provider_call_id": receipt["provider_call_id"],
            "input_tokens": usage["prompt_tokens"],
            "cached_input_tokens": cached,
            "output_tokens": usage["completion_tokens"],
            "price_snapshot_id": "S0M2-RATE-SNAPSHOT-001",
            "model_cost_usd": receipt["cost_usd"],
            "reviewer_minutes": 0, "reviewer_identity": None,
            "labor_rate_snapshot_id": None, "human_cost_usd": 0,
            "wall_clock_seconds": receipt["wall_clock_seconds"],
            "unavailable_reasons": {
                "reviewer_identity": "模型调用无人工劳务",
                "labor_rate_snapshot_id": "同上",
            },
            "event_digest": "",
        }
        unsigned = {k: v for k, v in event.items() if k != "event_digest"}
        event["event_digest"] = digest_json(unsigned)
        events.append(event)

    window = log["metrics_audit_window"]
    events.append(human_event(
        "EV-S0M2-MA-01", "METRICS_AUDIT", f"BATCH::{BATCH_ID}",
        REVIEWERS["METRICS_AUDIT"], window["reviewer_minutes"],
        v4_by_id["V4EV-ME-01"]["event_digest"],
        window["reviewer_minutes"] * 60))
    return events


def cmd_cost_events() -> int:
    log = _read("telemetry/run_log.v1.json")
    v4_events = _read("telemetry/v4_events.v1.json")["events"]
    rate_card = _read("cost/rate_card_snapshot.v1.json")
    expected = _read("cost/expected_event_manifest.v1.json")
    events = _cost_events(log, v4_events, rate_card)
    source = {
        "schema_version": "eval-spine-source-cost-events-v1",
        "run_id": RUN_ID,
        "source_run_manifest_digest": expected["source_run_manifest_digest"],
        "generated_from_append_only_log": True,
        "includes_failed_attempts": True,
        "source_events": [
            {"event_id": row["event_id"],
             "resource_kind": row["resource_kind"],
             "outcome_status": row["outcome_status"],
             "source_telemetry_event_digest": row[
                 "source_telemetry_event_digest"],
             "provider_call_id": row["provider_call_id"],
             "wall_clock_seconds": row["wall_clock_seconds"]}
            for row in events],
        "manifest_digest": "",
    }
    unsigned = {k: v for k, v in source.items() if k != "manifest_digest"}
    source["manifest_digest"] = digest_json(unsigned)
    report = spine_cost.metering_report(
        events, rate_card=rate_card, expected_event_manifest=expected,
        source_event_manifest=source)
    decision = spine_cost.accounting_integrity_gate(
        events, rate_card=rate_card, expected_event_manifest=expected,
        source_event_manifest=source,
        as_of=_read("telemetry/run_log.v1.json")["run_window"]["completed_at"])
    _write("cost/cost_events.v1.json", {"events": events})
    _write("cost/source_event_manifest.v1.json", source)
    _write("cost/metering_report.v1.json", report)
    _write("cost/accounting_decision.v1.json", decision)
    print(json.dumps({"events": len(events),
                      "metering_qualified": report["qualified"],
                      "accounting_status": decision["status"],
                      "failed_gates": decision["failed_gates"]},
                     ensure_ascii=False))
    return 0


def _six_gates() -> tuple[dict, list[str]]:
    notes: list[str] = []
    bundle = _read("bundle/request_bundle.v1.json")
    outputs = _read("outputs/sealed_outputs.v1.json")["outputs"]
    report = _read("gates/gate_report.v1.json")
    batch_metrics = _read("gates/batch_metrics.v1.json")
    decision = _read("cost/accounting_decision.v1.json")

    rebuilt = build_bundle()
    single_assignment = (rebuilt["bundle_digest"] == bundle["bundle_digest"]
                         and len(bundle["assignments"])
                         == len(bundle["requests"])
                         and all(r["assignment_digest"] == a[
                             "assignment_digest"]
                             for r, a in zip(
                                 sorted(bundle["requests"],
                                        key=lambda x: x["scenario_id"]),
                                 sorted(bundle["assignments"],
                                        key=lambda x: x["scenario_id"]))))
    notes.append(f"single_assignment: bundle 复建摘要一致={rebuilt['bundle_digest'] == bundle['bundle_digest']}")

    material_by_id = {m["scenario_id"]: m for m in bundle["materials"]}
    mismatches = [r["request_id"] for r in bundle["requests"]
                  if r["material_digest"] != material_by_id[r["scenario_id"]][
                      "material_digest"]]
    mismatches += [a["assignment_id"] for a in bundle["assignments"]
                   if a["material_packet_digest"] != material_by_id[
                       a["scenario_id"]]["material_digest"]]
    assignment_material_match = not mismatches
    notes.append(f"assignment_material_mismatch_count={len(mismatches)}")

    veto_metric_present = (
        "whole_batch_machine_hard_veto_zero" in report
        and "machine_hard_veto_count" in report
        and "whole_batch_hard_veto_count" in batch_metrics)
    notes.append(f"veto_metric_present={veto_metric_present} "
                 f"(gate={report['machine_hard_veto_count']}, "
                 f"metrics={batch_metrics['whole_batch_hard_veto_count']})")

    output_by_id = {o["request_id"]: o for o in outputs}
    first_ok = all(o["attempt_index"] == 1
                   and o["attempt_id"] == f"{rid}:attempt:1"
                   for rid, o in output_by_id.items())
    receipts = _receipts()
    receipt_ok = all(len(r.get("response_digest", "")) == 64
                     and r.get("receipt_digest") for r in receipts)
    first_response_retained = bool(first_ok and receipt_ok
                                   and len(outputs) == 4
                                   and len(receipts) == len(PAIRS))
    notes.append(f"first_response_retained: outputs一次尝试={first_ok}, "
                 f"外部回执内容寻址={receipt_ok}")

    cost_provenance = decision["status"] == "PASS"
    notes.append(f"cost_provenance: accounting={decision['status']}")

    impersonation_hits = []
    for assignment in bundle["assignments"]:
        if FORBIDDEN_PLAN_FIELD_NAMES & set(assignment):
            impersonation_hits.append(assignment["assignment_id"])
        for key, expected_value in (
                ("not_formal_content_composition_plan", True),
                ("runtime_consumable", False), ("publishable", False),
                ("binds_enterprise_runtime_input", False),
                ("counts_toward_300", False),
                ("stage_scope", "GATE1_QUALIFICATION_ONLY")):
            if assignment.get(key) != expected_value:
                impersonation_hits.append(
                    f"{assignment['assignment_id']}:{key}")
    for output in outputs:
        for key, expected_value in (("qualification_only", True),
                                    ("publishable", False),
                                    ("runtime_consumable", False),
                                    ("counts_toward_300", False)):
            if output.get(key) != expected_value:
                impersonation_hits.append(f"{output['request_id']}:{key}")
    no_plan_impersonation = not impersonation_hits
    notes.append(f"gate1_plan_impersonation_count={len(impersonation_hits)}")

    gates = {
        "single_assignment": bool(single_assignment),
        "assignment_material_match": bool(assignment_material_match),
        "whole_batch_hard_veto_metric": bool(veto_metric_present),
        "first_response_retained": bool(first_response_retained),
        "cost_provenance": bool(cost_provenance),
        "no_plan_impersonation": bool(no_plan_impersonation),
    }
    return gates, notes


def cmd_stage_gate() -> int:
    gates, notes = _six_gates()
    decision = spine_stage_gate.stage_decision(stage="S0", gates=gates,
                                               revision_count=0)
    record = {"schema_version": "s0m2-stage-decision-v1",
              "run_id": RUN_ID, "batch_id": BATCH_ID,
              "stage_id": STAGE_ID, "decision": decision,
              "gate_notes": notes, "record_digest": ""}
    unsigned = {k: v for k, v in record.items() if k != "record_digest"}
    record["record_digest"] = digest_json(unsigned)
    _write("s0/stage_decision.v1.json", record)
    print(json.dumps({"status": decision["status"], "gates": gates},
                     ensure_ascii=False))
    return 0 if decision["status"] == "PASS" else 1


def cmd_verify_all() -> int:
    problems: list[str] = []
    bundle = _read("bundle/request_bundle.v1.json")
    rebuilt = build_bundle()
    if rebuilt["bundle_digest"] != bundle["bundle_digest"]:
        problems.append("bundle recompute mismatch")
    raws = _read("outputs/raw_first_attempts.v1.json")["attempts"]
    outputs = _read("outputs/sealed_outputs.v1.json")["outputs"]
    resealed = _sealed_outputs(bundle, raws)
    if resealed != outputs:
        problems.append("sealed outputs recompute mismatch")
    report = _read("gates/gate_report.v1.json")
    deterministic_gates.validate_gate_report(report, outputs,
                                             bundle["requests"])
    content = _read("reviews/content_reviews.v1.json")["reviews"]
    fact = _read("reviews/fact_reviews.v1.json")["reviews"]
    batch_metrics = _read("gates/batch_metrics.v1.json")
    recomputed_metrics = metrics.compute_batch_metrics(
        outputs, bundle["requests"], report, content, fact)
    if recomputed_metrics != batch_metrics:
        problems.append("batch metrics recompute mismatch")
    log = _read("telemetry/run_log.v1.json")
    v4_events = _read("telemetry/v4_events.v1.json")["events"]
    if _v4_events(bundle, outputs, report, content, fact, batch_metrics,
                  log) != v4_events:
        problems.append("v4 telemetry recompute mismatch")
    telemetry.validate_qualification_coverage(
        v4_events, bundle["requests"], outputs, report, content, fact,
        batch_metrics, run_id=RUN_ID, batch_id=BATCH_ID)
    summary = _read("telemetry/telemetry_summary.v1.json")
    if telemetry.summarize_events(v4_events) != summary:
        problems.append("telemetry summary recompute mismatch")
    manifest = _read("telemetry/run_manifest.v1.json")
    telemetry.validate_run_manifest(manifest)
    rate_card = _read("cost/rate_card_snapshot.v1.json")
    if spine_cost.validate_rate_card(rate_card):
        problems.append("rate card invalid")
    expected = _read("cost/expected_event_manifest.v1.json")
    if expected["source_run_manifest_digest"] != bundle["bundle_digest"]:
        problems.append("expected manifest not bound to bundle digest")
    events = _read("cost/cost_events.v1.json")["events"]
    if _cost_events(log, v4_events, rate_card) != events:
        problems.append("cost events recompute mismatch")
    source = _read("cost/source_event_manifest.v1.json")
    metering = _read("cost/metering_report.v1.json")
    recomputed_metering = spine_cost.metering_report(
        events, rate_card=rate_card, expected_event_manifest=expected,
        source_event_manifest=source)
    if recomputed_metering != metering:
        problems.append("metering report recompute mismatch")
    decision = _read("cost/accounting_decision.v1.json")
    if decision["status"] != "PASS" or not metering["qualified"]:
        problems.append(f"accounting not PASS: {decision['failed_gates']}")
    stage = _read("s0/stage_decision.v1.json")
    gates, _ = _six_gates()
    if gates != stage["decision"]["gates"]:
        problems.append("six-gate recompute mismatch")
    if stage["decision"]["status"] != spine_stage_gate.stage_decision(
            stage="S0", gates=gates, revision_count=0)["status"]:
        problems.append("stage decision recompute mismatch")
    verdict = {"verify_all": "PASS" if not problems else "FAIL",
               "problems": problems,
               "s0_status": stage["decision"]["status"],
               "accounting_status": decision["status"],
               "telemetry_complete": summary["telemetry_complete"]}
    print(json.dumps(verdict, ensure_ascii=False))
    return 0 if not problems and stage["decision"]["status"] == "PASS" else 1


def main() -> int:
    commands = {
        "build-bundle": cmd_build_bundle,
        "build-expected-manifest": cmd_build_expected_manifest,
        "gate": cmd_gate,
        "metrics": cmd_metrics,
        "telemetry": cmd_telemetry,
        "cost-events": cmd_cost_events,
        "stage-gate": cmd_stage_gate,
        "verify-all": cmd_verify_all,
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(commands))
    args = parser.parse_args()
    return commands[args.command]()


if __name__ == "__main__":
    sys.exit(main())
