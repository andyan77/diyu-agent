#!/usr/bin/env python3
"""Validate the frozen Q20 pack and completed 100-task qualification artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from typing import cast

LOGGER = logging.getLogger("q20-qualification-checker")
TASK_SCHEMA = "diyu.q20.frozen_task.v1"
REFERENCE_SCHEMA = "diyu.q20.market_reference.v1"
MANIFEST_SCHEMA = "diyu.q20.freeze_manifest.v1"
RESULT_SCHEMA = "diyu.q20.remote_quality_qualification_result.v1"
REVIEW_STATUS_SCHEMA = "diyu.q20.review_execution_status.v1"
BOUNDARY_SNAPSHOT_SCHEMA = "diyu.q20.run_boundary_snapshot.v1"
EVENT_SCHEMA = "diyu.q20.official_run_event.v1"
TASK_RECORD_SCHEMA = "diyu.q20.official_task_record.v1"
BLIND_INPUT_SCHEMA = "diyu.q20.blind_review_input.v1"
COST_RECONCILIATION_SCHEMA = "diyu.q20.model_cost_reconciliation.v1"
EXPECTED_BASE_COMMIT = "a588ca5c44d8243927f1d0b2d2349c29f14f8a4a"
EXPECTED_CANDIDATE_COMMIT = "41623d6bcbcc338eb7745a186ab7da7538faedee"
EXPECTED_BLIND_LOCK_COMMIT = "be3de48"
SCORE_LIMITS = {
    "appeal_creativity": 20, "task_product_fit": 20, "completeness_user_value": 20,
    "brand_account_person_fit": 15, "platform_executability": 15, "natural_diverse_anti_template": 10,
}
REVIEW_FILES = {
    "服装品牌自媒体内容审查": ("apparel_media_blind_identification.v1.json", "apparel_media_review.v1.json"),
    "企业新手使用与内容生产审查": ("enterprise_novice_blind_identification.v1.json", "enterprise_novice_review.v1.json"),
}

EXPECTED_PRODUCTS = frozenset(f"CP{number:02d}" for number in range(1, 21))
_PRODUCT_LABELS = (
    "岗位任务视频日志", "门店时段微纪录", "单项手艺全过程", "多岗位协作纪实", "人物成长与职业史",
    "专业判断切片", "用户问题诊断室", "工艺、面料、版型解构", "适用边界与反选指南", "长期验证档案",
    "产品诞生与设计取舍", "产品迭代与版本日志", "产品的生活与衣橱角色", "物性影像与感官短片", "商品到店生命周期",
    "服务复盘", "陈列换陈与空间实验", "城市门店生活志", "经营取舍与决策复盘", "承诺与兑现追踪",
)
EXPECTED_PRODUCT_LABEL_BY_ID = {f"CP{index:02d}": label for index, label in enumerate(_PRODUCT_LABELS, start=1)}
FUZZY_NULL_FIELDS = frozenset(
    {"topic_label", "primary_audience", "content_goal", "key_takeaway", "speaker_role_name", "storyline_name",
     "column_name", "organization_level", "business_goal", "content_direction", "content_identity",
     "long_term_storyline", "expression_method"}
)
EXPECTED_SCENARIOS = frozenset({"EXPLICIT_REQUIREMENT", "AMBIGUOUS_REQUIREMENT", "SCOPED_BRAND_MATERIAL",
                                "NO_MATERIAL_CREATION", "SELECT_THEN_REVISE"})
ALLOWED_FORMATS = frozenset({"短视频", "图文", "直播内容包", "私域沟通内容", "培训与门店话术", "陈列搭配"})
DISABLED_FORMAT = "门店线下物料"
EXACT_CURRENT_TOPICS = frozenset({"品牌和企业故事", "创始人或主理人的工作日常与观点", "商品为什么这样设计",
                                  "穿搭、试穿和选购建议", "门店日常与顾客服务", "团队幕后、跨岗位协作和岗位成长",
                                  "陈列调整与空间经营", "城市、区域与本地生活", "活动、直播、咨询、到店、私域和复购承接",
                                  "招商、招聘与组织信任"})
CURRENT_TOPIC_PRODUCT_MAPPING = {
    "品牌和企业故事": frozenset({"CP05", "CP11", "CP19", "CP20"}),
    "创始人或主理人的工作日常与观点": frozenset({"CP01", "CP05", "CP19", "CP20"}),
    "商品为什么这样设计": frozenset({"CP06", "CP08", "CP10", "CP11", "CP12"}),
    "穿搭、试穿和选购建议": frozenset({"CP07", "CP09", "CP13", "CP14", "CP16"}),
    "门店日常与顾客服务": frozenset({"CP01", "CP02", "CP15", "CP16", "CP18"}),
    "团队幕后、跨岗位协作和岗位成长": frozenset({"CP01", "CP04", "CP05", "CP15"}),
    "陈列调整与空间经营": frozenset({"CP03", "CP15", "CP17"}),
    "城市、区域与本地生活": frozenset({"CP02", "CP16", "CP18", "CP19"}),
    "活动、直播、咨询、到店、私域和复购承接": frozenset({"CP06", "CP15", "CP16", "CP19", "CP20"}),
    "招商、招聘与组织信任": frozenset({"CP04", "CP05", "CP19", "CP20"}),
}
TASK_ID_PATTERN = re.compile(r"Q20-(CP(?:0[1-9]|1[0-9]|20))-S([1-5])\Z")
REFERENCE_ID_PATTERN = re.compile(r"Q20-MARKET-(CP(?:0[1-9]|1[0-9]|20))\Z")
VISIBLE_PRODUCT_ID_PATTERN = re.compile(r"CP\d{2}")


class QualificationCheckError(RuntimeError):
    """Raised when a qualification artifact violates the frozen contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise QualificationCheckError(message)


def _mapping(value: object, location: str) -> dict[str, object]:
    _require(isinstance(value, dict), f"{location} must be a JSON object")
    return cast(dict[str, object], value)


def _string(value: object, location: str) -> str:
    _require(isinstance(value, str), f"{location} must be a string")
    return cast(str, value)


def _integer(value: object, location: str) -> int:
    _require(type(value) is int, f"{location} must be an integer")
    return cast(int, value)


def _number(value: object, location: str) -> int | float:
    _require(type(value) in {int, float}, f"{location} must be a number")
    return cast(int | float, value)


def _list(value: object, location: str) -> list[object]:
    _require(isinstance(value, list), f"{location} must be a JSON array")
    return cast(list[object], value)


def _close(value: object, expected: float, location: str) -> None:
    _require(abs(float(_number(value, location)) - expected) < 1e-9, f"{location} must equal {expected}")


def _load_json(path: Path) -> dict[str, object]:
    _require(path.is_file(), f"missing required artifact: {path.relative_to(path.parent.parent)}")
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationCheckError(f"cannot parse JSON artifact {path}: {exc}") from exc
    return _mapping(parsed, str(path))


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    _require(path.is_file(), f"missing required artifact: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise QualificationCheckError(f"cannot read JSONL artifact {path}: {exc}") from exc

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        _require(bool(line.strip()), f"{path.name}:{line_number} contains a blank record")
        try:
            parsed: object = json.loads(line)
        except json.JSONDecodeError as exc:
            raise QualificationCheckError(f"{path.name}:{line_number} is invalid JSON: {exc}") from exc
        records.append(_mapping(parsed, f"{path.name}:{line_number}"))
    return records


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_no_product_identity_leak(value: object, location: str) -> None:
    visible = json.dumps(value, ensure_ascii=False, sort_keys=True)
    leaked_labels = sorted(label for label in EXPECTED_PRODUCT_LABEL_BY_ID.values() if label in visible)
    _require(not leaked_labels, f"{location} leaks exact product label(s): {', '.join(leaked_labels)}")
    _require(VISIBLE_PRODUCT_ID_PATTERN.search(visible) is None, f"{location} leaks a CPxx product id")


def _task_identity(task: Mapping[str, object], index: int) -> tuple[str, str, str]:
    location = f"frozen_tasks.v1.jsonl record {index}"
    task_id = _string(task.get("task_id"), f"{location}.task_id")
    match = TASK_ID_PATTERN.fullmatch(task_id)
    _require(match is not None, f"{location}.task_id is not canonical: {task_id}")
    if match is None:  # Keeps type narrowing independent of assertions and -O.
        raise QualificationCheckError(f"cannot decode task id: {task_id}")

    product = _mapping(task.get("internal"), f"{location}.internal")
    product_id = _string(product.get("expected_product_id"), f"{location}.internal.expected_product_id")
    scenario = _mapping(task.get("scenario"), f"{location}.scenario")
    scenario_id = _string(scenario.get("id"), f"{location}.scenario.id")
    _require(match.group(1) == product_id, f"{task_id} disagrees with expected product {product_id}")
    return task_id, product_id, scenario_id


def _check_tasks(tasks: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    _require(len(tasks) == 100, f"expected exactly 100 frozen tasks, found {len(tasks)}")
    task_by_id: dict[str, Mapping[str, object]] = {}
    product_counts: Counter[str] = Counter()
    scenario_counts: Counter[str] = Counter()
    product_scenarios: dict[str, set[str]] = {product: set() for product in EXPECTED_PRODUCTS}
    format_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    market_counts: Counter[str] = Counter()
    ordinals: set[int] = set()

    for index, task in enumerate(tasks, start=1):
        location = f"frozen_tasks.v1.jsonl record {index}"
        _require(task.get("schema") == TASK_SCHEMA, f"{location} has the wrong schema")
        _require(task.get("frozen_before_official_output") is True, f"{location} was not frozen in time")
        _require(task.get("real_customer_data") is False, f"{location} declares real customer data")
        _require(task.get("automatic_publish") is False, f"{location} enables automatic publishing")
        _require(
            task.get("selection_policy") == "BLIND_ORDINARY_USER_BEFORE_REVIEW",
            f"{location} does not preserve blind selection",
        )

        ordinals.add(_integer(task.get("ordinal"), f"{location}.ordinal"))
        task_id, product_id, scenario_id = _task_identity(task, index)
        _require(task_id not in task_by_id, f"duplicate task id {task_id}")
        _require(product_id in EXPECTED_PRODUCTS, f"unexpected product id {product_id}")
        _require(scenario_id in EXPECTED_SCENARIOS, f"unexpected scenario id {scenario_id}")
        internal = _mapping(task.get("internal"), f"{location}.internal")
        _require(
            internal.get("expected_product_label") == EXPECTED_PRODUCT_LABEL_BY_ID[product_id],
            f"{task_id} has the wrong exact product label",
        )
        task_by_id[task_id] = task
        product_counts[product_id] += 1
        scenario_counts[scenario_id] += 1
        product_scenarios[product_id].add(scenario_id)

        request = _mapping(task.get("author_visible_request"), f"{location}.author_visible_request")
        _check_no_product_identity_leak(request, f"{task_id}.author_visible_request")
        _check_no_product_identity_leak(task.get("fuzzy_prelude"), f"{task_id}.fuzzy_prelude")
        _check_no_product_identity_leak(task.get("fuzzy_confirmation"), f"{task_id}.fuzzy_confirmation")
        _check_no_product_identity_leak(task.get("revision_instruction"), f"{task_id}.revision_instruction")
        duration = _string(request.get("duration_label"), f"{location}.duration_label")
        message = _string(request.get("message"), f"{location}.message")
        _require(bool(message.strip()), f"{task_id} has an empty author-visible message")
        _require(duration != "由系统建议", f"{task_id} leaves final duration to the system")
        content_format = _string(request.get("content_format"), f"{location}.content_format")
        _require(content_format != DISABLED_FORMAT, f"{task_id} uses disabled format {DISABLED_FORMAT}")
        _require(content_format in ALLOWED_FORMATS, f"{task_id} uses an unapproved format: {content_format}")
        format_counts[content_format] += 1
        topic = _string(request.get("topic_label"), f"{location}.topic_label")
        _require(topic in EXACT_CURRENT_TOPICS, f"{task_id} uses a non-current portal topic: {topic}")
        _require(
            product_id in CURRENT_TOPIC_PRODUCT_MAPPING[topic],
            f"{task_id} maps topic {topic} to disallowed product {product_id}",
        )
        topic_counts[topic] += 1

        if task.get("market_comparison_task") is True:
            market_counts[product_id] += 1

        fuzzy_prelude = task.get("fuzzy_prelude")
        if scenario_id == "AMBIGUOUS_REQUIREMENT":
            prelude = _mapping(fuzzy_prelude, f"{location}.fuzzy_prelude")
            for field in FUZZY_NULL_FIELDS:
                _require(prelude.get(field) is None, f"{task_id}.fuzzy_prelude.{field} must be null")
            _require(prelude.get("operation") == "找点灵感", f"{task_id} has the wrong fuzzy operation")
            _require(prelude.get("duration_label") == "由系统建议", f"{task_id} has the wrong fuzzy duration")
            _require(bool(_string(task.get("fuzzy_confirmation"), f"{location}.fuzzy_confirmation").strip()),
                     f"{task_id} has an empty fuzzy confirmation")
        else:
            _require(fuzzy_prelude is None, f"{task_id} unexpectedly has a fuzzy prelude")
            _require(task.get("fuzzy_confirmation") is None, f"{task_id} unexpectedly has a fuzzy confirmation")
        has_revision = task.get("revision_instruction") is not None
        _require(has_revision is (scenario_id == "SELECT_THEN_REVISE"), f"{task_id} revision contract mismatch")

    _require(ordinals == set(range(1, 101)), "task ordinals must be exactly 1 through 100")
    _require(set(product_counts) == EXPECTED_PRODUCTS, "frozen tasks do not cover exactly CP01 through CP20")
    _require(all(count == 5 for count in product_counts.values()), "every content product must have exactly 5 tasks")
    _require(set(scenario_counts) == EXPECTED_SCENARIOS, "the five required scenarios are not exact")
    _require(all(count == 20 for count in scenario_counts.values()), "each required scenario must appear exactly 20 times")
    _require(
        all(scenarios == EXPECTED_SCENARIOS for scenarios in product_scenarios.values()),
        "each product must contain each of the five scenarios exactly once",
    )
    _require(set(format_counts) == ALLOWED_FORMATS, "all and only the six enabled formats must be represented")
    _require(set(topic_counts) == EXACT_CURRENT_TOPICS, "all and only the ten current portal topics must be represented")
    _require(set(market_counts) == EXPECTED_PRODUCTS, "every product must designate a market comparison task")
    _require(all(count == 1 for count in market_counts.values()), "each product must designate exactly one market task")
    return task_by_id


def _check_references(
    references: Sequence[Mapping[str, object]],
    tasks: Mapping[str, Mapping[str, object]],
) -> None:
    _require(len(references) == 20, f"expected exactly 20 market references, found {len(references)}")
    product_ids: set[str] = set()
    matched_tasks: set[str] = set()

    for index, reference in enumerate(references, start=1):
        location = f"market_references.v1.jsonl record {index}"
        _require(reference.get("schema") == REFERENCE_SCHEMA, f"{location} has the wrong schema")
        _require(reference.get("frozen_before_official_output") is True, f"{location} was not frozen in time")
        _require(reference.get("private_access_used") is False, f"{location} used private access")
        _require(reference.get("full_copyrighted_body_copied") is False, f"{location} copied a full protected body")

        product_id = _string(reference.get("product_id"), f"{location}.product_id")
        reference_id = _string(reference.get("reference_id"), f"{location}.reference_id")
        matched_task_id = _string(reference.get("matched_task_id"), f"{location}.matched_task_id")
        url = _string(reference.get("url"), f"{location}.url")
        reference_format = _string(reference.get("content_format"), f"{location}.content_format")
        match = REFERENCE_ID_PATTERN.fullmatch(reference_id)
        _require(match is not None and match.group(1) == product_id, f"{reference_id} is not canonical for {product_id}")
        _require(product_id in EXPECTED_PRODUCTS, f"unexpected reference product {product_id}")
        _require(product_id not in product_ids, f"multiple market references for {product_id}")
        _require(matched_task_id not in matched_tasks, f"market task {matched_task_id} is referenced more than once")
        _require(url.startswith(("https://", "http://")), f"{reference_id} does not contain a public web URL")

        task = tasks.get(matched_task_id)
        _require(task is not None, f"{reference_id} points to missing task {matched_task_id}")
        if task is None:
            raise QualificationCheckError(f"cannot inspect missing task {matched_task_id}")
        internal = _mapping(task.get("internal"), f"task {matched_task_id}.internal")
        request = _mapping(task.get("author_visible_request"), f"task {matched_task_id}.author_visible_request")
        task_format = _string(request.get("content_format"), f"task {matched_task_id}.content_format")
        _require(
            internal.get("expected_product_id") == product_id,
            f"{reference_id} and {matched_task_id} belong to different products",
        )
        _require(task.get("market_comparison_task") is True, f"{matched_task_id} was not preselected for comparison")
        _require(
            reference_format == task_format,
            f"{reference_id} format {reference_format} does not match {matched_task_id} format {task_format}",
        )
        product_ids.add(product_id)
        matched_tasks.add(matched_task_id)

    _require(product_ids == EXPECTED_PRODUCTS, "market references must map one-to-one to CP01 through CP20")


def _check_manifest(root: Path, manifest: Mapping[str, object]) -> None:
    _require(manifest.get("schema") == MANIFEST_SCHEMA, "freeze manifest has the wrong schema")
    _require(manifest.get("base_commit") == EXPECTED_BASE_COMMIT, "freeze manifest has the wrong base commit")
    _require(manifest.get("frozen_once") is True, "task inputs were not declared frozen once")
    _require(manifest.get("official_model_calls_before_freeze") == 0, "model output existed before the freeze")
    _require(manifest.get("old_package10_results_consumed") is False, "old Package 10 results were reused")
    _require(manifest.get("official_task_count") == 100, "manifest official task count is not 100")
    _require(manifest.get("content_product_count") == 20, "manifest product count is not 20")
    _require(manifest.get("tasks_per_product") == 5, "manifest tasks-per-product is not 5")
    _require(manifest.get("market_reference_count") == 20, "manifest market reference count is not 20")
    _require(manifest.get("tasks_sha256") == _sha256(root / "frozen_tasks.v1.jsonl"), "frozen task digest mismatch")
    _require(manifest.get("market_references_sha256") == _sha256(root / "market_references.v1.jsonl"),
             "market reference digest mismatch")


def _check_preflight_and_boundary(root: Path) -> None:
    recovery = _load_json(root / "evidence" / "cap_recovery.v1.json")
    boundary = _load_json(root / "evidence" / "run_boundary_snapshot.v1.json")
    authorization = _mapping(recovery.get("authorization"), "cap_recovery.authorization")
    _require(
        recovery.get("schema") == "diyu.q20.cap_recovery.v1"
        and authorization.get("runtime_configured_cumulative_limit_before") == 209
        and authorization.get("runtime_configured_cumulative_limit_after") == 600
        and authorization.get("q20_maximum_new_model_calls_after") == 600,
        "cap recovery must record exactly 209 to 600",
    )
    _require(boundary.get("schema") == BOUNDARY_SNAPSHOT_SCHEMA, "run boundary snapshot has the wrong schema")
    _require(
        boundary.get("cumulative_model_call_upper_bound") == 590
        and boundary.get("configured_cumulative_model_call_limit") == 600
        and boundary.get("task_new_model_calls_used") == 382
        and boundary.get("official_tasks_completed") == 100
        and boundary.get("event_sequence_at_capture") == 1223,
        "run boundary does not bind the completed run",
    )
    _close(boundary.get("task_new_cost_cny_used"), 1.369708, "boundary.task_new_cost_cny_used")
    _require(
        boundary.get("planned_remaining_model_call_upper_bound") == 0
        and boundary.get("task_model_call_limit") == 600
        and boundary.get("task_cost_limit_cny") == 5,
        "completed boundary has planned work or wrong limits",
    )
    _require(boundary.get("automatic_publish") is False, "run boundary enables automatic publishing")
    _require(boundary.get("old_package10_results_consumed") is False, "run boundary reused old Package 10 results")


def _expected_task_steps(task: Mapping[str, object]) -> set[str]:
    steps = {"FIRST_CANDIDATE_SET", "SELECT_FIRST_CANDIDATE", "MANUAL_REVIEW_STATUS", "INTERNAL_EXPORT"}
    scenario = _mapping(task.get("scenario"), "frozen task scenario")
    if scenario.get("id") == "AMBIGUOUS_REQUIREMENT":
        steps.add("FUZZY_INSPIRATION")
    if scenario.get("id") == "SELECT_THEN_REVISE":
        steps.update({"ONE_LOCAL_REVISION", "SELECT_REVISED_CANDIDATE"})
    return steps


def _check_events(events: Sequence[Mapping[str, object]], tasks: Mapping[str, Mapping[str, object]]) -> None:
    _require(len(events) == 1223, f"official event ledger must contain 1223 events, found {len(events)}")
    previous = "0" * 64
    for index, event in enumerate(events, start=1):
        _require(event.get("schema") == EVENT_SCHEMA, f"event {index} has the wrong schema")
        _require(event.get("sequence") == index, f"event {index} has the wrong sequence")
        _require(event.get("previous_event_sha256") == previous, f"event {index} breaks the digest chain")
        unsigned = {key: value for key, value in event.items() if key != "event_sha256"}
        digest = hashlib.sha256(
            json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        _require(event.get("event_sha256") == digest, f"event {index} has the wrong digest")
        previous = digest
    counts = Counter(_string(event.get("event_type"), "event.event_type") for event in events)
    _require(
        counts == Counter(
            {
                "RUN_STARTED": 1,
                "PORTAL_REQUEST_STARTED": 460,
                "PORTAL_REQUEST_COMPLETED": 460,
                "BLIND_USER_SELECTION_RECORDED": 100,
                "TASK_COMPLETED": 100,
                "RUN_PAUSED_FOR_LEDGER_REFRESH": 99,
                "PORTAL_TRANSPORT_INCOMPLETE": 1,
                "PORTAL_REQUEST_REPLAYED": 1,
                "RUN_COMPLETED": 1,
            }
        ),
        "official event-type counts do not describe one complete 100-task run",
    )
    _require(events[0].get("event_type") == "RUN_STARTED", "event ledger does not start with RUN_STARTED")
    _require(events[-1].get("event_type") == "RUN_COMPLETED", "event ledger does not end with RUN_COMPLETED")
    _require(events[-1].get("completed_tasks") == 100, "RUN_COMPLETED does not record 100 tasks")
    expected_pairs = Counter((task_id, step) for task_id, task in tasks.items() for step in _expected_task_steps(task))
    started_pairs: Counter[tuple[str, str]] = Counter()
    completed_pairs: Counter[tuple[str, str]] = Counter()
    for event in events:
        event_type = event.get("event_type")
        if event_type not in {"PORTAL_REQUEST_STARTED", "PORTAL_REQUEST_COMPLETED"}:
            continue
        pair = (_string(event.get("task_id"), "portal event.task_id"), _string(event.get("step"), "portal event.step"))
        if event_type == "PORTAL_REQUEST_STARTED":
            started_pairs[pair] += 1
        else:
            completed_pairs[pair] += 1
            _require(event.get("http_status") == 200, f"{pair[0]} {pair[1]} did not return HTTP 200")
            _require(event.get("publish_allowed") is False, f"{pair[0]} {pair[1]} allowed publishing")
            _require(bool(_string(event.get("user_visible_answer"), f"{pair}.user_visible_answer").strip()),
                     f"{pair[0]} {pair[1]} has no visible result")
    _require(started_pairs == expected_pairs, "portal request starts do not close the frozen task step matrix")
    _require(completed_pairs == expected_pairs, "portal request completions do not close the frozen task step matrix")
    task_completions = [event for event in events if event.get("event_type") == "TASK_COMPLETED"]
    selections = [event for event in events if event.get("event_type") == "BLIND_USER_SELECTION_RECORDED"]
    _require({event.get("task_id") for event in task_completions} == set(tasks), "TASK_COMPLETED coverage is incomplete")
    _require({event.get("task_id") for event in selections} == set(tasks), "blind selection coverage is incomplete")
    _require(all(event.get("candidate_number") == 1 for event in selections), "selection was not uniformly blind-first")
    _require(
        all(event.get("selection_policy") == "FIRST_AVAILABLE_WITHOUT_SCORE_OR_PRODUCT_ANSWER" for event in selections),
        "blind selection policy changed during the run",
    )
    transport = next(event for event in events if event.get("event_type") == "PORTAL_TRANSPORT_INCOMPLETE")
    replay = next(event for event in events if event.get("event_type") == "PORTAL_REQUEST_REPLAYED")
    _require(
        (transport.get("task_id"), transport.get("step"), transport.get("request_sha256"))
        == (replay.get("task_id"), replay.get("step"), replay.get("request_sha256")),
        "the single technical replay does not match the incomplete transport",
    )
    _require(replay.get("technical_replay") is True, "the replay is not marked technical")
    _require(not any(event.get("publish_allowed") is True for event in events), "event ledger contains a publish allowance")


def _check_task_records(
    records: Sequence[Mapping[str, object]],
    blind_inputs: Sequence[Mapping[str, object]],
    tasks: Mapping[str, Mapping[str, object]],
) -> None:
    _require(len(records) == 100, f"expected 100 official task records, found {len(records)}")
    _require(len(blind_inputs) == 100, f"expected 100 blind review inputs, found {len(blind_inputs)}")
    seen_tasks: set[str] = set()
    seen_blind_ids: set[str] = set()
    selected_texts: Counter[str] = Counter()
    model_calls = 0
    actual_cost = 0.0
    for index, record in enumerate(records, start=1):
        location = f"official task record {index}"
        _require(record.get("schema") == TASK_RECORD_SCHEMA, f"{location} has the wrong schema")
        task_id = _string(record.get("task_id"), f"{location}.task_id")
        task = tasks.get(task_id)
        _require(task is not None and task_id not in seen_tasks, f"{location} has an unknown or duplicate task id")
        if task is None:
            raise QualificationCheckError(f"cannot inspect missing frozen task {task_id}")
        seen_tasks.add(task_id)
        _require(record.get("ordinal") == task.get("ordinal"), f"{task_id} has the wrong ordinal")
        internal = _mapping(task.get("internal"), f"{task_id}.internal")
        _require(record.get("expected_product_id") == internal.get("expected_product_id"), f"{task_id} product mismatch")
        _require(record.get("expected_product_label") == internal.get("expected_product_label"), f"{task_id} label mismatch")
        request = _mapping(task.get("author_visible_request"), f"{task_id}.author_visible_request")
        _require(record.get("account_display_name") == request.get("account_display_name"), f"{task_id} account mismatch")
        scenario = _mapping(record.get("scenario"), f"{location}.scenario")
        frozen_scenario = _mapping(task.get("scenario"), f"{task_id}.scenario")
        _require(scenario.get("id") == frozen_scenario.get("id"), f"{task_id} scenario mismatch")
        selected = _string(record.get("selected_first_candidate"), f"{location}.selected_first_candidate")
        selected_texts[selected] += 1
        for field in (
            "first_candidate_set_user_visible",
            "selection_result_user_visible",
            "manual_review_status_user_visible",
            "internal_export_user_visible",
        ):
            _require(bool(_string(record.get(field), f"{location}.{field}").strip()), f"{task_id} is missing {field}")
        _require(record.get("selected_candidate_number") == 1, f"{task_id} did not preserve first-candidate selection")
        is_revision = scenario.get("id") == "SELECT_THEN_REVISE"
        _require((record.get("revision_instruction") is not None) is is_revision, f"{task_id} revision request mismatch")
        _require((record.get("revision_result_user_visible") is not None) is is_revision, f"{task_id} revision result mismatch")
        _require(record.get("automatic_publish") is False, f"{task_id} enabled automatic publishing")
        _require(record.get("real_customer_data_used") is False, f"{task_id} used real customer data")
        model_calls += _integer(record.get("actual_model_calls"), f"{location}.actual_model_calls")
        actual_cost += float(_number(record.get("actual_cost_cny"), f"{location}.actual_cost_cny"))
        blind_id = _string(record.get("blind_item_id"), f"{location}.blind_item_id")
        _require(blind_id not in seen_blind_ids, f"duplicate blind item id {blind_id}")
        seen_blind_ids.add(blind_id)
    _require(seen_tasks == set(tasks), "official task records do not cover the frozen tasks")
    _require(seen_blind_ids == {f"R{ordinal:03d}" for ordinal in range(1, 101)}, "blind ids must be R001 through R100")
    _require(model_calls == 246, "task records must reconcile to 246 final-batch model calls")
    _require(abs(actual_cost - 0.897012) < 1e-9, "task records must reconcile to CNY 0.897012")

    blind_texts: Counter[str] = Counter()
    blind_ids: set[str] = set()
    for index, item in enumerate(blind_inputs, start=1):
        location = f"blind review input {index}"
        _require(item.get("schema") == BLIND_INPUT_SCHEMA, f"{location} has the wrong schema")
        _check_no_product_identity_leak(item, location)
        blind_id = _string(item.get("blind_item_id"), f"{location}.blind_item_id")
        _require(blind_id not in blind_ids, f"duplicate blind input id {blind_id}")
        blind_ids.add(blind_id)
        blind_candidate = _mapping(item.get("selected_first_candidate"), f"{location}.selected_first_candidate")
        _require(blind_candidate.get("candidate_number") == 1, f"{blind_id} does not contain candidate one")
        blind_texts[_string(blind_candidate.get("visible_text"), f"{location}.visible_text")] += 1
    _require(blind_ids == seen_blind_ids, "blind review inputs do not cover all task records")
    _require(blind_texts == selected_texts, "blind review inputs are not the selected first-candidate corpus")


def _check_cost_reconciliation(root: Path, reconciliation: Mapping[str, object]) -> None:
    run_root = root / "evidence" / "official_remote_run"
    _require(reconciliation.get("schema") == COST_RECONCILIATION_SCHEMA, "cost reconciliation has the wrong schema")
    _require(reconciliation.get("event_ledger_sha256") == _sha256(run_root / "official_run_events.v1.jsonl"),
             "cost reconciliation has the wrong event digest")
    _require(reconciliation.get("official_task_records_sha256") == _sha256(run_root / "official_task_records.v1.jsonl"),
             "cost reconciliation has the wrong task-record digest")
    _require(reconciliation.get("blind_review_inputs_sha256") == _sha256(run_root / "blind_review_inputs.v1.jsonl"),
             "cost reconciliation has the wrong blind-input digest")
    final_run = _mapping(reconciliation.get("official_final_run_window"), "reconciliation.official_final_run_window")
    _require(
        final_run.get("actual_model_calls") == 246
        and final_run.get("remote_invocation_rows") == 246
        and final_run.get("successful_remote_invocations") == 246,
        "final run must reconcile to 246 successful remote invocations",
    )
    _close(final_run.get("actual_cost_cny"), 0.897012, "reconciliation.final_run.actual_cost_cny")
    pre_final = _mapping(reconciliation.get("pre_final_recovery"), "reconciliation.pre_final_recovery")
    _require(pre_final.get("actual_model_calls") == 136, "pre-final recovery must preserve 136 calls")
    _close(pre_final.get("actual_cost_cny"), 0.472696, "reconciliation.pre_final_recovery.actual_cost_cny")
    for ledger_raw in _list(pre_final.get("preserved_attempt_ledgers"), "reconciliation.preserved_attempt_ledgers"):
        ledger = _string(ledger_raw, "preserved attempt ledger")
        _require((run_root / ledger).is_file(), f"missing preserved attempt ledger: {ledger}")
    task_total = _mapping(reconciliation.get("task_total"), "reconciliation.task_total")
    _require(
        task_total.get("actual_model_calls") == 382
        and task_total.get("authorized_model_call_limit") == 600,
        "whole task must reconcile to 382/600 calls",
    )
    _close(task_total.get("actual_cost_cny"), 1.369708, "reconciliation.task_total.actual_cost_cny")
    _require(task_total.get("authorized_cost_limit_cny") == 5, "authorized cost limit must remain CNY 5")
    remote = _mapping(reconciliation.get("remote_cumulative_after_completion"), "reconciliation.remote_cumulative")
    _require(remote.get("actual_model_calls") == 590 and remote.get("configured_limit") == 600,
             "remote cumulative must reconcile to 590/600")
    _require(reconciliation.get("technical_replays") == 1, "cost reconciliation must record one technical replay")
    _require(reconciliation.get("quality_rerolls") == 0, "quality rerolls are forbidden")
    _require(reconciliation.get("automatic_publish_count") == 0, "automatic publishing must remain zero")


def _check_reviews(
    root: Path,
    records: Sequence[Mapping[str, object]],
    tasks: Mapping[str, Mapping[str, object]],
) -> dict[str, bool]:
    run_root = root / "evidence" / "official_remote_run"
    event_sha = _sha256(run_root / "official_run_events.v1.jsonl")
    blind_sha = _sha256(run_root / "blind_review_inputs.v1.jsonl")
    reveal_sha = _sha256(run_root / "review" / "review_reveal_inputs.v1.jsonl")
    truth = {
        _string(record.get("blind_item_id"), "task record blind id"): (
            _string(record.get("task_id"), "task record task id"),
            _string(record.get("expected_product_id"), "task record product id"),
            _string(record.get("expected_product_label"), "task record product label"),
        )
        for record in records
    }
    truth_by_task = {value[0]: (blind_id, value[1]) for blind_id, value in truth.items()}
    market_tasks = {task_id for task_id, task in tasks.items() if task.get("market_comparison_task") is True}
    reviewer_scores: list[dict[str, float]] = []
    reviewer_blind_pass: list[bool] = []
    reviewer_markets: list[dict[str, str]] = []
    reviewer_averages: list[float] = []
    reviewer_clean: list[bool] = []
    reviewer_instances: set[str] = set()
    cliche_tasks: set[str] = set()
    fixed_structure_pass = True
    for role, (blind_name, review_name) in REVIEW_FILES.items():
        blind_path, review_path = root / "review" / blind_name, root / "review" / review_name
        blind = _load_json(blind_path)
        review = _load_json(review_path)
        for artifact, location in ((blind, blind_name), (review, review_name)):
            _require(artifact.get("reviewer_role") == role, f"{location} has the wrong reviewer role")
            _require(artifact.get("candidate_commit") == EXPECTED_CANDIDATE_COMMIT, f"{location} candidate mismatch")
            _require(artifact.get("blind_review_inputs_sha256") == blind_sha, f"{location} blind digest mismatch")
            _require(artifact.get("event_ledger_sha256") == event_sha, f"{location} event digest mismatch")
            _require(artifact.get("production_model_calls") == 0, f"{location} used production model calls")
        _require(blind.get("schema") == "diyu.q20.blind_identification.v1", f"{blind_name} has the wrong schema")
        _require(blind.get("stage") == "BLIND_IDENTIFICATION_LOCKED", f"{blind_name} was not locked blind")
        predictions: dict[str, str] = {}
        for raw in _list(blind.get("items"), f"{blind_name}.items"):
            item = _mapping(raw, f"{blind_name} item")
            blind_id = _string(item.get("blind_item_id"), f"{blind_name}.blind_item_id")
            prediction = _string(item.get("predicted_product_label"), f"{blind_name}.predicted_product_label")
            _require(blind_id in truth and blind_id not in predictions, f"{blind_name} has unknown/duplicate {blind_id}")
            _require(prediction in EXPECTED_PRODUCT_LABEL_BY_ID.values(), f"{blind_name} has an unknown product label")
            predictions[blind_id] = prediction
        _require(set(predictions) == set(truth), f"{blind_name} does not contain 100 blind choices")
        _require(review.get("schema") == "diyu.q20.independent_review.v1", f"{review_name} has the wrong schema")
        _require(review.get("reviewer_instance") == blind.get("reviewer_instance"), f"{review_name} reviewer instance drift")
        _require(review.get("blind_lock_commit") == EXPECTED_BLIND_LOCK_COMMIT, f"{review_name} blind lock mismatch")
        _require(review.get("blind_identification_sha256") == _sha256(blind_path), f"{review_name} blind file mismatch")
        _require(review.get("review_reveal_inputs_sha256") == reveal_sha, f"{review_name} reveal digest mismatch")
        reviewer_instances.add(_string(review.get("reviewer_instance"), f"{review_name}.reviewer_instance"))
        scores: dict[str, float] = {}
        blind_counts: Counter[str] = Counter()
        cliche_count = 0
        task_vetoes = 0
        for raw in _list(review.get("task_reviews"), f"{review_name}.task_reviews"):
            item = _mapping(raw, f"{review_name} task review")
            blind_id = _string(item.get("blind_item_id"), "task review blind id")
            _require(blind_id in truth and truth[blind_id][0] not in scores, f"{review_name} repeats/does not know {blind_id}")
            task_id, product_id, label = truth[blind_id]
            _require((item.get("task_id"), item.get("expected_product_id"), item.get("expected_product_label"))
                     == (task_id, product_id, label), f"{review_name} task identity mismatch for {blind_id}")
            correct = predictions[blind_id] == label
            _require(item.get("blind_predicted_product_label") == predictions[blind_id], f"{review_name} changed blind choice")
            _require(item.get("blind_correct") is correct, f"{review_name} has the wrong blind result")
            blind_counts[product_id] += int(correct)
            dimensions = _mapping(item.get("scores"), f"{review_name} {task_id}.scores")
            _require(set(dimensions) == set(SCORE_LIMITS), f"{review_name} {task_id} has the wrong score dimensions")
            total = sum(float(_number(dimensions.get(key), f"{task_id}.{key}")) for key in SCORE_LIMITS)
            _require(all(0 <= float(_number(dimensions.get(key), key)) <= limit for key, limit in SCORE_LIMITS.items()),
                     f"{review_name} {task_id} has an out-of-range score")
            _close(item.get("total_score"), total, f"{review_name} {task_id}.total_score")
            scores[task_id] = total
            task_vetoes += int(item.get("hard_veto") is True)
            cliche_count += int(item.get("cliche_or_near_duplicate") is True)
            if item.get("cliche_or_near_duplicate") is True:
                cliche_tasks.add(task_id)
        _require(set(scores) == set(tasks), f"{review_name} does not score all 100 tasks")
        average = sum(scores.values()) / 100
        _close(review.get("overall_average"), round(average, 2), f"{review_name}.overall_average")
        _require(review.get("tasks_ge85") == sum(score >= 85 for score in scores.values()), f"{review_name} tasks_ge85 drift")
        _require(review.get("cliche_or_near_duplicate_count") == cliche_count, f"{review_name} cliche count drift")
        summaries = {_string(_mapping(raw, "product summary").get("product_id"), "summary product id"):
                     _mapping(raw, "product summary") for raw in _list(review.get("product_summaries"), "product summaries")}
        _require(len(summaries) == 20, f"{review_name} must contain exactly 20 product summaries")
        for product_id in EXPECTED_PRODUCTS:
            values = [scores[task_id] for task_id, task in tasks.items()
                      if _mapping(task.get("internal"), "task internal").get("expected_product_id") == product_id]
            summary = summaries.get(product_id)
            _require(summary is not None, f"{review_name} lacks summary for {product_id}")
            if summary is None:
                raise QualificationCheckError(f"cannot inspect missing summary {product_id}")
            _require(summary.get("task_count") == 5 and summary.get("count_ge85") == sum(v >= 85 for v in values)
                     and summary.get("blind_correct_count") == blind_counts[product_id], f"{review_name} {product_id} summary drift")
            _close(summary.get("average_score"), round(sum(values) / 5, 2), f"{review_name} {product_id}.average_score")
        markets: dict[str, str] = {}
        for raw in _list(review.get("market_comparisons"), f"{review_name}.market_comparisons"):
            item = _mapping(raw, f"{review_name} market comparison")
            task_id = _string(item.get("task_id"), "market task id")
            result = _string(item.get("result"), "market result")
            _require(task_id in market_tasks and task_id not in markets
                     and (item.get("blind_item_id"), item.get("product_id")) == truth_by_task[task_id],
                     f"{review_name} market task mismatch")
            _require(result in {"明显更强", "基本相当", "明显更弱"}, f"{review_name} has an invalid market result")
            markets[task_id] = result
        _require(set(markets) == market_tasks, f"{review_name} does not compare all 20 market tasks")
        _require(review.get("market_at_least_comparable_count") == sum(v != "明显更弱" for v in markets.values()),
                 f"{review_name} market aggregate drift")
        reviewer_scores.append(scores)
        reviewer_blind_pass.append(all(blind_counts[product_id] >= 4 for product_id in EXPECTED_PRODUCTS))
        reviewer_markets.append(markets)
        reviewer_averages.append(average)
        _require(review.get("hard_vetoes") == task_vetoes, f"{review_name} hard-veto count drift")
        reviewer_clean.append(task_vetoes == 0)
        fixed_structure_pass &= review.get("fixed_structure_dominates_majority") is False
    _require(len(reviewer_instances) == 2, "the two reviews are not instance-isolated")
    formal = {task_id: sum(scores[task_id] for scores in reviewer_scores) / 2 for task_id in tasks}
    a04 = all(sum(formal[task_id] >= 85 for task_id in tasks if task_id.startswith(f"Q20-{product_id}-")) >= 4
              and sum(formal[task_id] for task_id in tasks if task_id.startswith(f"Q20-{product_id}-")) / 5 >= 85
              for product_id in EXPECTED_PRODUCTS)
    return {
        "Q20-A03": True, "Q20-A04": a04, "Q20-A05": sum(value >= 85 for value in formal.values()) >= 90,
        "Q20-A06": all(reviewer_blind_pass), "Q20-A07": len(cliche_tasks) <= 10 and fixed_structure_pass,
        "Q20-A08": sum(all(markets[task_id] != "明显更弱" for markets in reviewer_markets) for task_id in market_tasks) >= 14,
        "Q20-A09": all(value >= 90 for value in reviewer_averages) and all(reviewer_clean), "Q20-A13": True,
    }


def _check_result(root: Path, quality: Mapping[str, bool]) -> None:
    status = _load_json(root / "review" / "review_execution_status.v1.json")
    _require(status.get("schema") == REVIEW_STATUS_SCHEMA, "review execution status has the wrong schema")
    _require(
        status.get("review_input_candidate_count") == 100
        and status.get("formal_reviews_started") == 2
        and status.get("formal_reviews_completed") == 2,
        "review status does not close exactly two 100-item reviews",
    )
    reviews = [_mapping(raw, "review execution entry") for raw in _list(status.get("reviews"), "review status.reviews")]
    _require({entry.get("reviewer_role") for entry in reviews} == set(REVIEW_FILES), "review status roles are wrong")
    _require(all(entry.get("status") == "COMPLETED" for entry in reviews), "a formal review is not complete")
    _require(status.get("scores_fabricated") is False, "review status marks fabricated scores")
    _require(status.get("third_full_review_started") is False, "a forbidden third full review was started")

    result = _load_json(root / "result" / "remote_quality_qualification_result.v1.json")
    _require(result.get("schema") == RESULT_SCHEMA, "qualification result has the wrong schema")
    _require(result.get("official_model_calls") == 382, "result does not use reconciled model calls")
    _require(result.get("official_tasks_started") == 100 and result.get("official_tasks_completed") == 100,
             "result does not close the official tasks")
    _close(result.get("new_cost_cny"), 1.369708, "result.new_cost_cny")
    expected = {f"Q20-A{number:02d}": True for number in range(1, 16)}
    expected.update(quality)
    acceptance = _mapping(result.get("acceptance"), "result.acceptance")
    _require(acceptance == expected, "result acceptance does not match recomputed qualification booleans")
    failures = sorted(key for key, passed in expected.items() if not passed)
    _require(result.get("acceptance_failures") == failures, "result acceptance_failures drift from acceptance")
    passed = not failures
    terminal = "PASS_20_OF_20_REMOTE_QUALITY_QUALIFIED" if passed else "FAIL_20_PRODUCT_REMOTE_QUALITY_QUALIFICATION"
    _require(result.get("terminal_state") == terminal, "result terminal does not match acceptance")
    _require(result.get("qualification_claimed") is passed, "qualification claim does not match acceptance")
    readiness = _mapping(result.get("readiness_flags"), "result.readiness_flags")
    _require(bool(readiness) and all(value is False for value in readiness.values()), "readiness flags must remain false")


def check_package(root: Path) -> None:
    """Check frozen inputs, the completed remote run, and two independent reviews."""
    resolved_root = root.resolve()
    _require(resolved_root.is_dir(), f"package root does not exist: {resolved_root}")
    tasks = _load_jsonl(resolved_root / "frozen_tasks.v1.jsonl")
    references = _load_jsonl(resolved_root / "market_references.v1.jsonl")
    manifest = _load_json(resolved_root / "freeze_manifest.v1.json")
    task_by_id = _check_tasks(tasks)
    _check_references(references, task_by_id)
    _check_manifest(resolved_root, manifest)
    _check_preflight_and_boundary(resolved_root)
    run_root = resolved_root / "evidence" / "official_remote_run"
    _check_events(_load_jsonl(run_root / "official_run_events.v1.jsonl"), task_by_id)
    records = _load_jsonl(run_root / "official_task_records.v1.jsonl")
    blind_inputs = _load_jsonl(run_root / "blind_review_inputs.v1.jsonl")
    _check_task_records(records, blind_inputs, task_by_id)
    _check_cost_reconciliation(resolved_root, _load_json(run_root / "model_cost_reconciliation.v1.json"))
    _check_result(resolved_root, _check_reviews(resolved_root, records, task_by_id))


def _remove_one_task(root: Path) -> None:
    path = root / "frozen_tasks.v1.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")


def _break_event_chain(root: Path) -> None:
    path = root / "evidence" / "official_remote_run" / "official_run_events.v1.jsonl"
    rows = path.read_text(encoding="utf-8").splitlines()
    event = _mapping(json.loads(rows[1]), "selftest event")
    event["previous_event_sha256"] = "f" * 64
    rows[1] = json.dumps(event, ensure_ascii=False, sort_keys=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def run_selftest(root: Path) -> None:
    """Prove representative frozen-input and event-chain mutations are rejected."""
    check_package(root)
    mutations = (("missing-frozen-task", _remove_one_task), ("broken-event-chain", _break_event_chain))
    with tempfile.TemporaryDirectory(prefix="q20-checker-selftest-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        for case_name, mutation in mutations:
            case_root = temporary_root / case_name
            shutil.copytree(root, case_root)
            mutation(case_root)
            try:
                check_package(case_root)
            except QualificationCheckError:
                continue
            raise QualificationCheckError(f"selftest mutation was incorrectly accepted: {case_name}")


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-root", type=Path,
        default=Path(__file__).resolve().parent,
        help="qualification package directory (defaults to this script's directory)",
    )
    parser.add_argument("--selftest", action="store_true", help="run isolated negative mutation tests")
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the checker and return a stable process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not __debug__:
        LOGGER.error("Q20 qualification checker refuses optimized mode")
        return 1
    args = _parse_args(arguments)
    try:
        package_root = cast(Path, args.package_root)
        if cast(bool, args.selftest):
            run_selftest(package_root)
            LOGGER.info("Q20 qualification checker selftest passed")
        else:
            check_package(package_root)
            LOGGER.info("Q20 qualification pack passed structural checks")
    except (OSError, QualificationCheckError) as exc:
        LOGGER.error("Q20 qualification check failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
