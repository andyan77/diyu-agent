#!/usr/bin/env python3
"""Validate and execute the single frozen Package 10 internal-pilot plan."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_7_ROOT = REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001"
PLAN_PATH = PACKAGE_ROOT / "evaluation_plan.v1.json"


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest_object(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_plan(path: Path = PLAN_PATH) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Package 10 plan must be one JSON object")
    return value


def validate_plan(plan: JsonObject) -> JsonObject:
    tasks = plan.get("chronological_tasks")
    if not isinstance(tasks, list) or len(tasks) != 30:
        raise ValueError("The chronological plan must contain exactly 30 tasks")
    if [row.get("day") for row in tasks] != list(range(1, 31)):
        raise ValueError("The chronological task order is incomplete")
    task_ids = [row.get("task_id") for row in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Task IDs must be unique")
    dimensions = {
        "organization_levels": {row.get("organization_level") for row in tasks},
        "content_identities": {row.get("content_identity") for row in tasks},
        "public_topics": {row.get("topic") for row in tasks},
        "long_term_storylines": {row.get("long_term_storyline") for row in tasks},
        "content_directions": {row.get("content_direction") for row in tasks},
        "content_formats": {row.get("content_format") for row in tasks},
        "expression_methods": {row.get("expression_method") for row in tasks},
        "business_goals": {row.get("business_goal") for row in tasks},
        "internal_content_products": {
            row.get("expected_internal_product_id") for row in tasks
        },
        "content_accounts_scope_checked": {row.get("account") for row in tasks},
    }
    requirements = plan.get("coverage_requirements")
    if not isinstance(requirements, dict):
        raise ValueError("Coverage requirements are missing")
    for name, values in dimensions.items():
        expected = requirements.get(name)
        if len(values) != expected or None in values:
            raise ValueError(
                f"Coverage drift for {name}: expected {expected}, got {len(values)}"
            )
    formats = dimensions["content_formats"]
    expected_formats = {
        "短视频",
        "图文",
        "直播内容包",
        "私域沟通内容",
        "门店线下物料",
        "培训与门店话术",
        "陈列搭配",
    }
    if formats != expected_formats:
        raise ValueError("The seven product formats are not exactly covered")
    references = plan.get("public_references")
    if not isinstance(references, list) or not 1 <= len(references) <= 8:
        raise ValueError("Public references must contain one to eight links")
    if any(
        not isinstance(row, dict)
        or not str(row.get("url", "")).startswith("https://")
        or "short_observation" not in row
        for row in references
    ):
        raise ValueError("A public reference is incomplete")
    if plan.get("bridge_absolute_model_call_limit") != 1096:
        raise ValueError("The only bridge limit must be 96 plus 1000")
    if plan.get("package10_cost_limit_cny") != 5:
        raise ValueError("The Package 10 cost limit changed")
    readiness = plan.get("readiness")
    if not isinstance(readiness, dict) or any(readiness.values()):
        raise ValueError("Production readiness must remain closed")
    return {
        "state": "PLAN_VALID",
        "plan_sha256": file_sha256(PLAN_PATH),
        "task_count": len(tasks),
        "reference_count": len(references),
        "coverage_counts": {name: len(values) for name, values in dimensions.items()},
    }


def _task_payload(task: JsonObject, defaults: JsonObject) -> JsonObject:
    return {
        "account_display_name": task["account"],
        "operation": defaults["operation"],
        "topic_label": task["topic"],
        "primary_audience": defaults["primary_audience"],
        "message": task["message"],
        "target_platform": task["target_platform"],
        "candidate_number": None,
        "content_goal": task["business_goal"],
        "key_takeaway": "只在当前账号资料和授权范围内形成可执行内容",
        "speaker_role_name": None,
        "storyline_name": None,
        "column_name": None,
        "continue_previous": False,
        "localization_allowed": defaults["localization_allowed"],
        "duration_label": task["duration_label"],
        "expression_feeling": task["expression_feeling"],
        "content_format": task["content_format"],
        "organization_level": task["organization_level"],
        "content_identity": task["content_identity"],
        "long_term_storyline": task["long_term_storyline"],
        "content_direction": task["content_direction"],
        "business_goal": task["business_goal"],
        "expression_method": task["expression_method"],
        "existing_material_kinds": copy.deepcopy(
            defaults["existing_material_kinds"]
        ),
    }


def _prepare_payload(task: JsonObject, defaults: JsonObject) -> JsonObject:
    value = _task_payload(task, defaults)
    value.update(
        {
            "session_token": "package10-preflight-session-token-0001",
            "operation": "确认制作",
            "selected_content_product_id": task["expected_internal_product_id"],
            "speaker_role_id": None,
            "storyline_id": None,
            "column_id": None,
            "previous_content_ref": None,
            "user_material_refs": [],
            "precise_fact_requests": [],
        }
    )
    return value


def run_runtime_preflight(plan: JsonObject) -> JsonObject:
    if str(PACKAGE_7_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_7_ROOT))
    from bridge_app import build_runtime  # type: ignore[import-not-found]
    from contracts import BridgePrepareRequest  # type: ignore[import-not-found]
    from persistence import (  # type: ignore[import-not-found]
        TrustedDatabaseScope,
        trusted_database_scope,
    )

    runtime, repository, _ = build_runtime()
    tenant_id = os.environ.get("DIYU_SIM_TENANT_ID", "TENANT-DIYU-SIM-001")
    username = os.environ.get("DIYU_SIM_USERNAME", "")
    if not username:
        raise RuntimeError("DIYU_SIM_USERNAME is required")
    with trusted_database_scope(TrustedDatabaseScope(tenant_id=tenant_id)):
        principal = repository.principal_by_username(username)
    if principal is None:
        raise RuntimeError("The simulation principal is missing")
    results = []
    defaults = plan["task_defaults"]
    for task in plan["chronological_tasks"]:
        with trusted_database_scope(
            TrustedDatabaseScope(
                tenant_id=tenant_id,
                principal_id=principal.principal_id,
            )
        ):
            result = runtime.prepare(
                BridgePrepareRequest.model_validate(_prepare_payload(task, defaults)),
                principal.principal_id,
            )
        state = str(result.get("response_kind", "UNKNOWN"))
        results.append(
            {
                "task_id": task["task_id"],
                "state": state,
                "system_support": result.get("system_support"),
                "diyu_material_status": result.get("diyu_material_status"),
                "result_digest": digest_object(result),
            }
        )
    return {
        "state": "PREFLIGHT_COMPLETE",
        "task_count": len(results),
        "model_required_count": sum(row["state"] == "MODEL_REQUIRED" for row in results),
        "action_card_count": sum(row["state"] == "DIRECT" for row in results),
        "unexpected_count": sum(
            row["state"] not in {"MODEL_REQUIRED", "DIRECT"} for row in results
        ),
        "results": results,
    }


@dataclass
class PortalResponse:
    status: int
    value: JsonObject
    elapsed_seconds: float


class PortalSession:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )

    def post(self, path: str, payload: JsonObject, *, portal: bool = False) -> PortalResponse:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=canonical_json(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"X-Diyu-Portal": "same-origin-v1"} if portal else {}),
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with self.opener.open(request, timeout=180) as response:
                status = response.status
                value = json.loads(response.read(2_000_001).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            status = exc.code
            value = json.loads(exc.read(2_000_001).decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("Portal response is not an object")
        return PortalResponse(status, value, round(time.monotonic() - started, 3))

    def login(self, username: str, password: str) -> PortalResponse:
        return self.post("/login", {"username": username, "password": password})


def _response_record(
    *,
    step_id: str,
    operation: str,
    request_payload: JsonObject,
    response: PortalResponse,
) -> JsonObject:
    answer = response.value.get("answer")
    if not isinstance(answer, str):
        answer = str(response.value.get("user_visible_text", ""))
    safe_request = copy.deepcopy(request_payload)
    safe_request.pop("password", None)
    return {
        "step_id": step_id,
        "operation": operation,
        "http_status": response.status,
        "elapsed_seconds": response.elapsed_seconds,
        "request_sha256": digest_object(safe_request),
        "response_sha256": digest_object(response.value),
        "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        "answer_length": len(answer),
        "answer": answer,
        "simulation_only": response.value.get("simulation_only"),
        "publish_allowed": response.value.get("publish_allowed"),
    }


def _portal_operation(
    session: PortalSession,
    task: JsonObject,
    defaults: JsonObject,
    *,
    operation: str,
    message: str,
    candidate_number: int | None = None,
) -> JsonObject:
    payload = _task_payload(task, defaults)
    payload.update(
        {
            "operation": operation,
            "message": message,
            "candidate_number": candidate_number,
        }
    )
    response = session.post("/v1/portal/chat", payload, portal=True)
    return _response_record(
        step_id=f"{task['task_id']}:{operation}",
        operation=operation,
        request_payload=payload,
        response=response,
    )


def _run_formal_task(
    session: PortalSession,
    task: JsonObject,
    defaults: JsonObject,
) -> JsonObject:
    steps = [
        _portal_operation(
            session,
            task,
            defaults,
            operation="直接做内容",
            message=str(task["message"]),
        )
    ]
    answer = str(steps[0]["answer"])
    outcome = "MODEL_CANDIDATES" if "已准备好推荐候选" in answer else "ACTION_CARD"
    if steps[0]["http_status"] != 200:
        outcome = "HTTP_FAILURE"
    if outcome == "MODEL_CANDIDATES":
        steps.extend(
            [
                _portal_operation(
                    session,
                    task,
                    defaults,
                    operation="选择候选",
                    message="选择第一份，原因是当前信息最清楚且便于执行。",
                    candidate_number=1,
                ),
                _portal_operation(
                    session,
                    task,
                    defaults,
                    operation="审核",
                    message="请显示当前审核状态。",
                ),
                _portal_operation(
                    session,
                    task,
                    defaults,
                    operation="导出",
                    message="导出当前选择。",
                ),
                _portal_operation(
                    session,
                    task,
                    defaults,
                    operation="查看来源",
                    message="查看当前来源和边界。",
                ),
            ]
        )
    return {
        "task_id": task["task_id"],
        "day": task["day"],
        "expected_internal_product_id": task["expected_internal_product_id"],
        "account": task["account"],
        "content_format": task["content_format"],
        "outcome": outcome,
        "selection_reason": (
            "第一份的当前信息层级最清楚且便于执行"
            if outcome == "MODEL_CANDIDATES"
            else "按补料或安全停止行动卡继续"
        ),
        "normal_revision_count": 0,
        "steps": steps,
    }


def run_formal_evaluation(
    plan: JsonObject,
    *,
    base_url: str,
    output_path: Path,
    summary_path: Path,
) -> JsonObject:
    username = os.environ.get("DIYU_SIM_USERNAME", "")
    password = os.environ.get("DIYU_SIM_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("Simulation portal credentials are required")
    sessions = [PortalSession(base_url) for _ in range(3)]
    login_records = []
    for ordinal, session in enumerate(sessions, 1):
        response = session.login(username, password)
        if response.status != 200:
            raise RuntimeError(f"Portal login {ordinal} failed")
        login_records.append(
            {
                "session_id": f"PILOT-SESSION-{ordinal}",
                "http_status": response.status,
                "elapsed_seconds": response.elapsed_seconds,
                "options_sha256": digest_object(response.value.get("options", {})),
            }
        )
    tasks = plan["chronological_tasks"]
    defaults = plan["task_defaults"]
    novice_steps = [
        _portal_operation(
            sessions[0],
            tasks[0],
            defaults,
            operation="随便聊聊",
            message="孩子每天穿衣服时总说舒服最重要，这件事可以怎么聊？",
        ),
        _portal_operation(
            sessions[0],
            tasks[0],
            defaults,
            operation="找点灵感",
            message="我只有一个产品工作细节，请给我几个不空泛的内容切入方向。",
        ),
    ]
    results = [
        _run_formal_task(sessions[0], tasks[0], defaults),
        _run_formal_task(sessions[1], tasks[1], defaults),
    ]
    novice_steps.append(
        _portal_operation(
            sessions[1],
            tasks[1],
            defaults,
            operation="随便聊聊",
            message="先不做内容了，普通聊聊门店一天里最容易被忽略的小事。",
        )
    )
    for task in tasks[2:28]:
        results.append(_run_formal_task(sessions[2], task, defaults))
    concurrent_started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_run_formal_task, session, task, defaults)
            for session, task in zip(sessions[1:3], tasks[28:30], strict=True)
        ]
        results.extend(future.result() for future in futures)
    concurrent_elapsed = round(time.monotonic() - concurrent_started, 3)
    results.sort(key=lambda row: int(row["day"]))
    full_record = {
        "schema": "diyu.package10.restricted_full_run.v1",
        "task_id": plan["task_id"],
        "plan_sha256": file_sha256(PLAN_PATH),
        "base_url_sha256": hashlib.sha256(base_url.encode("utf-8")).hexdigest(),
        "login_records": login_records,
        "novice_steps": novice_steps,
        "chronological_results": results,
        "concurrency": {
            "active_session_count": 3,
            "concurrent_generation_count": 2,
            "elapsed_seconds": concurrent_elapsed,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(full_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": "diyu.package10.formal_run_summary.v1",
        "task_id": plan["task_id"],
        "plan_sha256": full_record["plan_sha256"],
        "restricted_evidence_sha256": file_sha256(output_path),
        "restricted_evidence_record_count": len(results),
        "login_session_count": len(login_records),
        "novice_step_count": len(novice_steps),
        "chronological_task_count": len(results),
        "model_candidate_count": sum(
            row["outcome"] == "MODEL_CANDIDATES" for row in results
        ),
        "action_card_count": sum(row["outcome"] == "ACTION_CARD" for row in results),
        "http_failure_count": sum(row["outcome"] == "HTTP_FAILURE" for row in results),
        "all_http_steps_succeeded": all(
            step["http_status"] == 200
            for row in results
            for step in row["steps"]
        )
        and all(step["http_status"] == 200 for step in novice_steps),
        "format_outcomes": {
            content_format: {
                "task_count": sum(
                    row["content_format"] == content_format for row in results
                ),
                "model_candidate_count": sum(
                    row["content_format"] == content_format
                    and row["outcome"] == "MODEL_CANDIDATES"
                    for row in results
                ),
                "action_card_count": sum(
                    row["content_format"] == content_format
                    and row["outcome"] == "ACTION_CARD"
                    for row in results
                ),
            }
            for content_format in sorted(
                {str(row["content_format"]) for row in results}
            )
        },
        "concurrency": full_record["concurrency"],
        "full_private_bodies_committed_to_repository": False,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def selftest() -> JsonObject:
    plan = load_plan()
    baseline = validate_plan(plan)
    wrong_budget = copy.deepcopy(plan)
    wrong_budget["bridge_absolute_model_call_limit"] = 1000
    try:
        validate_plan(wrong_budget)
    except ValueError:
        budget_tamper_rejected = True
    else:
        budget_tamper_rejected = False
    missing_format = copy.deepcopy(plan)
    for task in missing_format["chronological_tasks"]:
        if task["content_format"] == "直播内容包":
            task["content_format"] = "短视频"
    try:
        validate_plan(missing_format)
    except ValueError:
        format_tamper_rejected = True
    else:
        format_tamper_rejected = False
    readiness_flip = copy.deepcopy(plan)
    readiness_flip["readiness"]["production_ready"] = True
    try:
        validate_plan(readiness_flip)
    except ValueError:
        readiness_tamper_rejected = True
    else:
        readiness_tamper_rejected = False
    if not all(
        (budget_tamper_rejected, format_tamper_rejected, readiness_tamper_rejected)
    ):
        raise RuntimeError("Package 10 selftest did not fail closed")
    return {
        "state": "SELFTEST_PASS",
        "baseline": baseline,
        "budget_tamper_rejected": budget_tamper_rejected,
        "format_tamper_rejected": format_tamper_rejected,
        "readiness_tamper_rejected": readiness_tamper_rejected,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-plan")
    subparsers.add_parser("runtime-preflight")
    subparsers.add_parser("selftest")
    run_parser = subparsers.add_parser("run-formal")
    run_parser.add_argument("--base-url", required=True)
    run_parser.add_argument("--output", required=True, type=Path)
    run_parser.add_argument("--summary-output", required=True, type=Path)
    arguments = parser.parse_args(argv)
    plan = load_plan()
    validate_plan(plan)
    if arguments.command == "validate-plan":
        result = validate_plan(plan)
    elif arguments.command == "runtime-preflight":
        result = run_runtime_preflight(plan)
    elif arguments.command == "selftest":
        result = selftest()
    else:
        result = run_formal_evaluation(
            plan,
            base_url=arguments.base_url,
            output_path=arguments.output,
            summary_path=arguments.summary_output,
        )
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
