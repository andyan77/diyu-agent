#!/usr/bin/env python3
"""Validate the frozen Q20 qualification pack and its honest stopped terminal."""

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
from collections.abc import Callable, Mapping, Sequence
from typing import cast


LOGGER = logging.getLogger("q20-qualification-checker")

TASK_SCHEMA = "diyu.q20.frozen_task.v1"
REFERENCE_SCHEMA = "diyu.q20.market_reference.v1"
MANIFEST_SCHEMA = "diyu.q20.freeze_manifest.v1"
PREFLIGHT_SCHEMA = "diyu.q20.preflight.v1"
RUN_STATUS_SCHEMA = "diyu.q20.official_run_status.v1"
RESULT_SCHEMA = "diyu.q20.remote_quality_qualification_result.v1"
REVIEW_STATUS_SCHEMA = "diyu.q20.review_execution_status.v1"
BOUNDARY_SNAPSHOT_SCHEMA = "diyu.q20.run_boundary_snapshot.v1"
STOPPED_TERMINAL = "STOPPED_EXTERNAL_OR_BUDGET_BOUNDARY"
EXPECTED_BASE_COMMIT = "a588ca5c44d8243927f1d0b2d2349c29f14f8a4a"

EXPECTED_PRODUCTS = frozenset(f"CP{number:02d}" for number in range(1, 21))
EXPECTED_PRODUCT_LABEL_BY_ID = {
    "CP01": "岗位任务视频日志",
    "CP02": "门店时段微纪录",
    "CP03": "单项手艺全过程",
    "CP04": "多岗位协作纪实",
    "CP05": "人物成长与职业史",
    "CP06": "专业判断切片",
    "CP07": "用户问题诊断室",
    "CP08": "工艺、面料、版型解构",
    "CP09": "适用边界与反选指南",
    "CP10": "长期验证档案",
    "CP11": "产品诞生与设计取舍",
    "CP12": "产品迭代与版本日志",
    "CP13": "产品的生活与衣橱角色",
    "CP14": "物性影像与感官短片",
    "CP15": "商品到店生命周期",
    "CP16": "服务复盘",
    "CP17": "陈列换陈与空间实验",
    "CP18": "城市门店生活志",
    "CP19": "经营取舍与决策复盘",
    "CP20": "承诺与兑现追踪",
}
EXPECTED_ACCOUNT_DISPLAY_NAMES = frozenset(
    {
        "许闻川的产品记录", "唐予安｜内容现场", "许知宁｜搭配与门店服务", "周静宜｜门店与陈列",
        "林知远｜笛语", "顾知夏｜江苏笛语", "笛语童装", "笛语江苏", "笛语杭州滨江店",
        "笛语苏州园区店", "笛语无锡滨湖店",
    }
)
EXPECTED_ORGANIZATION_LEVELS = frozenset({"品牌总部", "区域组织", "门店"})
FUZZY_NULL_FIELDS = frozenset(
    {
        "topic_label", "primary_audience", "content_goal", "key_takeaway", "speaker_role_name",
        "storyline_name", "column_name", "organization_level", "business_goal", "content_direction",
        "content_identity", "long_term_storyline", "expression_method",
    }
)
EXPECTED_SCENARIOS = frozenset(
    {
        "EXPLICIT_REQUIREMENT",
        "AMBIGUOUS_REQUIREMENT",
        "SCOPED_BRAND_MATERIAL",
        "NO_MATERIAL_CREATION",
        "SELECT_THEN_REVISE",
    }
)
ALLOWED_FORMATS = frozenset(
    {
        "短视频",
        "图文",
        "直播内容包",
        "私域沟通内容",
        "培训与门店话术",
        "陈列搭配",
    }
)
DISABLED_FORMAT = "门店线下物料"
EXACT_CURRENT_TOPICS = frozenset(
    {
        "品牌和企业故事",
        "创始人或主理人的工作日常与观点",
        "商品为什么这样设计",
        "穿搭、试穿和选购建议",
        "门店日常与顾客服务",
        "团队幕后、跨岗位协作和岗位成长",
        "陈列调整与空间经营",
        "城市、区域与本地生活",
        "活动、直播、咨询、到店、私域和复购承接",
        "招商、招聘与组织信任",
    }
)
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
    _require(
        set(CURRENT_TOPIC_PRODUCT_MAPPING) == EXACT_CURRENT_TOPICS,
        "embedded current-topic mapping must define exactly the ten current portal topics",
    )
    task_by_id: dict[str, Mapping[str, object]] = {}
    product_counts: Counter[str] = Counter()
    scenario_counts: Counter[str] = Counter()
    product_scenarios: dict[str, set[str]] = {product: set() for product in EXPECTED_PRODUCTS}
    format_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    market_counts: Counter[str] = Counter()
    account_counts: Counter[str] = Counter()
    organization_counts: Counter[str] = Counter()
    audience_counts: Counter[str] = Counter()
    business_goal_counts: Counter[str] = Counter()
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

        ordinal = _integer(task.get("ordinal"), f"{location}.ordinal")
        _require(ordinal not in ordinals, f"duplicate task ordinal {ordinal}")
        ordinals.add(ordinal)

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
        account = _string(request.get("account_display_name"), f"{location}.account_display_name")
        organization = _string(request.get("organization_level"), f"{location}.organization_level")
        audience = _string(request.get("primary_audience"), f"{location}.primary_audience")
        business_goal = _string(request.get("business_goal"), f"{location}.business_goal")
        duration = _string(request.get("duration_label"), f"{location}.duration_label")
        message = _string(request.get("message"), f"{location}.message")
        _require(bool(message.strip()), f"{task_id} has an empty author-visible message")
        _require(duration != "由系统建议", f"{task_id} leaves final duration to the system")
        account_counts[account] += 1
        organization_counts[organization] += 1
        audience_counts[audience] += 1
        business_goal_counts[business_goal] += 1

        content_format = _string(request.get("content_format"), f"{location}.content_format")
        _require(content_format != DISABLED_FORMAT, f"{task_id} uses disabled format {DISABLED_FORMAT}")
        _require(content_format in ALLOWED_FORMATS, f"{task_id} uses an unapproved format: {content_format}")
        if content_format == "私域沟通内容":
            _require("微信一对一或社群" in message, f"{task_id} does not state its private-channel destination")
        if content_format == "培训与门店话术":
            _require("门店晨会或内部培训" in message, f"{task_id} does not state its training destination")
        format_counts[content_format] += 1
        topic = _string(request.get("topic_label"), f"{location}.topic_label")
        _require(topic in EXACT_CURRENT_TOPICS, f"{task_id} uses a non-current portal topic: {topic}")
        _require(
            product_id in CURRENT_TOPIC_PRODUCT_MAPPING[topic],
            f"{task_id} maps topic {topic} to disallowed product {product_id}",
        )
        topic_counts[topic] += 1

        market_task = task.get("market_comparison_task")
        _require(type(market_task) is bool, f"{location}.market_comparison_task must be boolean")
        if market_task is True:
            market_counts[product_id] += 1

        fuzzy_prelude = task.get("fuzzy_prelude")
        fuzzy_confirmation = task.get("fuzzy_confirmation")
        revision_instruction = task.get("revision_instruction")
        if scenario_id == "AMBIGUOUS_REQUIREMENT":
            prelude = _mapping(fuzzy_prelude, f"{location}.fuzzy_prelude")
            confirmation = _string(fuzzy_confirmation, f"{location}.fuzzy_confirmation")
            _require(bool(confirmation.strip()), f"{task_id} has an empty fuzzy confirmation")
            for field in FUZZY_NULL_FIELDS:
                _require(prelude.get(field) is None, f"{task_id}.fuzzy_prelude.{field} must be null")
            _require(prelude.get("operation") == "找点灵感", f"{task_id} has the wrong fuzzy operation")
            _require(prelude.get("target_platform") == "其他", f"{task_id} has the wrong fuzzy platform")
            _require(prelude.get("duration_label") == "由系统建议", f"{task_id} has the wrong fuzzy duration")
            _require(
                prelude.get("expression_feeling") == "由系统建议",
                f"{task_id} has the wrong fuzzy expression feeling",
            )
            _require(prelude.get("content_format") == "图文", f"{task_id} has the wrong fuzzy content format")
            prelude_message = _string(prelude.get("message"), f"{location}.fuzzy_prelude.message")
            _require(bool(prelude_message.strip()), f"{task_id} has an empty fuzzy first-turn message")
            effective_final_message = f"{message}\n确认：{confirmation}"
            _require(
                prelude_message != effective_final_message and prelude_message != confirmation,
                f"{task_id} fuzzy first-turn message duplicates its final message",
            )
        else:
            _require(fuzzy_prelude is None, f"{task_id} unexpectedly has a fuzzy prelude")
            _require(fuzzy_confirmation is None, f"{task_id} unexpectedly has a fuzzy confirmation")

        if scenario_id == "SELECT_THEN_REVISE":
            revision = _string(revision_instruction, f"{location}.revision_instruction")
            _require(bool(revision.strip()), f"{task_id} has an empty revision instruction")
        else:
            _require(revision_instruction is None, f"{task_id} unexpectedly has a revision instruction")

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
    _require(sum(format_counts.values()) == 100, "enabled format counts must total 100")
    _require(set(topic_counts) == EXACT_CURRENT_TOPICS, "all and only the ten current portal topics must be represented")
    _require(sum(topic_counts.values()) == 100, "current portal topic counts must total 100")
    _require(set(market_counts) == EXPECTED_PRODUCTS, "every product must designate a market comparison task")
    _require(all(count == 1 for count in market_counts.values()), "each product must designate exactly one market task")
    _require(
        EXPECTED_ACCOUNT_DISPLAY_NAMES <= set(account_counts),
        "frozen tasks do not cover all eleven remote content accounts",
    )
    _require(
        EXPECTED_ORGANIZATION_LEVELS <= set(organization_counts),
        "frozen tasks must cover headquarters, regional organizations, and stores",
    )
    _require(len(audience_counts) >= 10, "frozen tasks must cover at least ten primary audiences")
    _require(len(business_goal_counts) >= 5, "frozen tasks must cover at least five business goals")
    return task_by_id


def _check_references(
    references: Sequence[Mapping[str, object]],
    tasks: Mapping[str, Mapping[str, object]],
) -> None:
    _require(len(references) == 20, f"expected exactly 20 market references, found {len(references)}")
    product_ids: set[str] = set()
    reference_ids: set[str] = set()
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
        published_date = _string(reference.get("published_date"), f"{location}.published_date")
        _require(bool(published_date.strip()), f"{reference_id} has an empty published date")
        match = REFERENCE_ID_PATTERN.fullmatch(reference_id)
        _require(match is not None and match.group(1) == product_id, f"{reference_id} is not canonical for {product_id}")
        _require(product_id in EXPECTED_PRODUCTS, f"unexpected reference product {product_id}")
        _require(product_id not in product_ids, f"multiple market references for {product_id}")
        _require(reference_id not in reference_ids, f"duplicate market reference id {reference_id}")
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
        _require(reference_format in ALLOWED_FORMATS, f"{reference_id} uses an unapproved format: {reference_format}")
        _require(
            reference_format == task_format,
            f"{reference_id} format {reference_format} does not match {matched_task_id} format {task_format}",
        )
        product_ids.add(product_id)
        reference_ids.add(reference_id)
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
    _require(
        manifest.get("tasks_sha256") == _sha256(root / "frozen_tasks.v1.jsonl"),
        "frozen task SHA-256 does not match the manifest",
    )
    _require(
        manifest.get("market_references_sha256") == _sha256(root / "market_references.v1.jsonl"),
        "market reference SHA-256 does not match the manifest",
    )


def _check_stopped_terminal(root: Path) -> None:
    preflight = _load_json(root / "evidence" / "preflight.v1.json")
    run_status = _load_json(root / "evidence" / "official_run_status.v1.json")
    boundary = _load_json(root / "evidence" / "run_boundary_snapshot.v1.json")
    review_status = _load_json(root / "review" / "review_execution_status.v1.json")
    result = _load_json(root / "result" / "remote_quality_qualification_result.v1.json")

    _require(preflight.get("schema") == PREFLIGHT_SCHEMA, "preflight evidence has the wrong schema")
    _require(preflight.get("terminal_state") == STOPPED_TERMINAL, "preflight has the wrong terminal state")
    _require(preflight.get("official_run_started") is False, "preflight says the official run started")
    _require(preflight.get("old_package10_results_consumed") is False, "preflight reused old Package 10 results")
    _require(preflight.get("real_customer_data_used") is False, "preflight used real customer data")
    budget = _mapping(preflight.get("remote_budget"), "preflight.remote_budget")
    used = _integer(budget.get("model_call_upper_bound_used"), "preflight.remote_budget.model_call_upper_bound_used")
    cap = _integer(budget.get("configured_model_call_cap"), "preflight.remote_budget.configured_model_call_cap")
    remaining = _integer(budget.get("remaining_model_call_capacity"), "preflight.remote_budget.remaining_model_call_capacity")
    recovery_cap = _integer(budget.get("required_recovery_cap"), "preflight.remote_budget.required_recovery_cap")
    _require(budget.get("ledger_row_count") == 204, "preflight ledger row count must remain 204")
    _require(used == 208 and cap == 209, "stopped boundary must record the observed 208/209 upper bound")
    _require(remaining == cap - used == 1, "stopped boundary must record exactly one remaining call")
    _require(recovery_cap >= used + 300 and recovery_cap >= 508, "recovery cap must be at least 508")
    cost_statistics = _mapping(
        budget.get("dify_llm_node_cost_statistics_cny"),
        "preflight.remote_budget.dify_llm_node_cost_statistics_cny",
    )
    historical_p95 = _number(cost_statistics.get("p95"), "preflight.remote_budget cost P95")
    _require(historical_p95 == 0.0187076, "preflight must preserve the observed historical cost P95")

    _require(boundary.get("schema") == BOUNDARY_SNAPSHOT_SCHEMA, "run boundary snapshot has the wrong schema")
    _require(
        boundary.get("cumulative_model_call_upper_bound") == used
        and boundary.get("configured_cumulative_model_call_limit") == cap,
        "run boundary snapshot must bind exactly to the observed 208/209 boundary",
    )
    _require(
        boundary.get("planned_remaining_model_call_upper_bound") == 240,
        "run boundary snapshot must preserve the 240-call frozen plan",
    )
    _require(boundary.get("task_new_model_calls_used") == 0, "run boundary snapshot must record zero new calls")
    _require(_number(boundary.get("task_new_cost_cny_used"), "boundary task cost") == 0, "boundary cost must be zero")
    planning_rate = _number(boundary.get("model_call_cost_planning_rate_cny"), "boundary P95 planning rate")
    _require(planning_rate == historical_p95, "run boundary snapshot must use the observed historical P95")
    _require(
        abs(
            _number(boundary.get("planned_remaining_cost_upper_bound_cny"), "boundary planned cost")
            - historical_p95 * 240
        )
        < 1e-9,
        "run boundary snapshot planned cost must equal P95 times 240 calls",
    )
    _require(
        boundary.get("task_model_call_limit") == 300 and boundary.get("task_cost_limit_cny") == 5,
        "run boundary snapshot has the wrong authorized task limits",
    )
    _require(
        boundary.get("official_tasks_completed") == 0 and boundary.get("event_sequence_at_capture") == 0,
        "run boundary snapshot must precede every official task and event",
    )
    _require(boundary.get("automatic_publish") is False, "run boundary snapshot enables automatic publishing")
    _require(
        boundary.get("old_package10_results_consumed") is False,
        "run boundary snapshot reused old Package 10 results",
    )

    _require(run_status.get("schema") == RUN_STATUS_SCHEMA, "official run status has the wrong schema")
    _require(run_status.get("terminal_state") == STOPPED_TERMINAL, "official run status has the wrong terminal")
    _require(run_status.get("official_model_calls") == 0, "official model calls must remain zero")
    _require(run_status.get("official_tasks_started") == 0, "official tasks started must remain zero")
    _require(run_status.get("official_tasks_completed") == 0, "official tasks completed must remain zero")
    _require(_number(run_status.get("new_cost_cny"), "official_run_status.new_cost_cny") == 0, "new cost must be zero")
    _require(
        run_status.get("outputs_reused_from_old_package10") is False,
        "official run status reused old Package 10 outputs",
    )
    _require(run_status.get("real_customer_data_used") is False, "official run status used real customer data")
    _require(run_status.get("automatic_publish_count") == 0, "automatic publishing must remain zero")

    _require(review_status.get("schema") == REVIEW_STATUS_SCHEMA, "review execution status has the wrong schema")
    _require(
        set(review_status) == {
            "schema", "task_id", "terminal_state", "review_input_candidate_count", "formal_reviews_started",
            "formal_reviews_completed", "reviews", "market_comparisons_completed", "blind_identifications_completed",
            "scores_fabricated", "third_full_review_started",
        },
        "review execution status contains an unexpected field or signature claim",
    )
    _require(review_status.get("terminal_state") == STOPPED_TERMINAL, "review status has the wrong terminal")
    _require(review_status.get("review_input_candidate_count") == 0, "review status claims candidate inputs")
    _require(
        review_status.get("formal_reviews_started") == 0 and review_status.get("formal_reviews_completed") == 0,
        "review status claims formal review execution",
    )
    reviews_raw = review_status.get("reviews")
    _require(isinstance(reviews_raw, list) and len(reviews_raw) == 2, "review status must contain exactly two reviewers")
    reviewer_roles: set[str] = set()
    for index, review_raw in enumerate(cast(list[object], reviews_raw), start=1):
        review = _mapping(review_raw, f"review_execution_status.reviews[{index}]")
        _require(
            set(review) == {"reviewer_role", "status", "score", "reason"},
            f"review {index} contains an unexpected field or signature claim",
        )
        reviewer_roles.add(_string(review.get("reviewer_role"), f"review {index}.reviewer_role"))
        _require(review.get("status") == "NOT_RUN", f"review {index} must remain NOT_RUN")
        _require(review.get("score") is None, f"review {index} contains a fabricated score")
        _require(bool(_string(review.get("reason"), f"review {index}.reason").strip()), f"review {index} lacks a reason")
    _require(
        reviewer_roles == {"服装品牌自媒体内容审查", "企业新手使用与内容生产审查"},
        "review status does not contain the two frozen reviewer roles",
    )
    _require(review_status.get("scores_fabricated") is False, "review status admits fabricated scores")
    _require(review_status.get("third_full_review_started") is False, "review status claims a third full review")

    _require(result.get("schema") == RESULT_SCHEMA, "qualification result has the wrong schema")
    _require(result.get("terminal_state") == STOPPED_TERMINAL, "qualification result has the wrong terminal state")
    _require(result.get("qualification_claimed") is False, "a stopped run cannot claim qualification")
    _require(result.get("official_model_calls") == 0, "result must record zero official model calls")
    _require(result.get("official_tasks_started") == 0, "result must record zero official tasks started")
    readiness = _mapping(result.get("readiness_flags"), "result.readiness_flags")
    _require(bool(readiness), "result must enumerate readiness flags")
    _require(all(value is False for value in readiness.values()), "all readiness flags must remain false")
    recovery = _mapping(result.get("minimum_recovery_condition"), "result.minimum_recovery_condition")
    _require(
        _integer(recovery.get("required_cumulative_model_call_cap"), "recovery.required_cumulative_model_call_cap")
        >= 508,
        "result recovery condition must require a cumulative cap of at least 508",
    )
    _require(
        recovery.get("ledger_model_call_upper_bound_must_remain") == 208,
        "recovery must preserve the observed ledger upper bound of 208",
    )
    _require(recovery.get("configured_cap_before_recovery") == 209, "recovery must record the prior cap of 209")
    _require(
        _number(recovery.get("initial_cost_planning_rate_cny"), "recovery.initial_cost_planning_rate_cny")
        == historical_p95,
        "result recovery condition must preserve the observed historical P95",
    )


def check_package(root: Path) -> None:
    """Check all frozen inputs and the stopped-boundary evidence."""
    resolved_root = root.resolve()
    _require(resolved_root.is_dir(), f"package root does not exist: {resolved_root}")
    tasks = _load_jsonl(resolved_root / "frozen_tasks.v1.jsonl")
    references = _load_jsonl(resolved_root / "market_references.v1.jsonl")
    manifest = _load_json(resolved_root / "freeze_manifest.v1.json")
    task_by_id = _check_tasks(tasks)
    _check_references(references, task_by_id)
    _check_manifest(resolved_root, manifest)
    _check_stopped_terminal(resolved_root)


Mutation = Callable[[Path], None]


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _remove_one_task(root: Path) -> None:
    path = root / "frozen_tasks.v1.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")


def _forge_disabled_format_with_matching_digest(root: Path) -> None:
    task_path = root / "frozen_tasks.v1.jsonl"
    lines = task_path.read_text(encoding="utf-8").splitlines()
    first: object = json.loads(lines[0])
    task = _mapping(first, "selftest task")
    request = _mapping(task.get("author_visible_request"), "selftest task request")
    request["content_format"] = DISABLED_FORMAT
    lines[0] = json.dumps(task, ensure_ascii=False, sort_keys=True)
    task_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest_path = root / "freeze_manifest.v1.json"
    manifest = _load_json(manifest_path)
    manifest["tasks_sha256"] = _sha256(task_path)
    _write_json(manifest_path, manifest)


def _forge_manifest_digest(root: Path) -> None:
    path = root / "freeze_manifest.v1.json"
    manifest = _load_json(path)
    manifest["tasks_sha256"] = "0" * 64
    _write_json(path, manifest)


def _forge_missing_topic_with_matching_digest(root: Path) -> None:
    task_path = root / "frozen_tasks.v1.jsonl"
    rows = [_mapping(json.loads(line), "selftest topic task") for line in task_path.read_text(encoding="utf-8").splitlines()]
    topic_counts: Counter[str] = Counter()
    for row in rows:
        request = _mapping(row.get("author_visible_request"), "selftest topic task request")
        topic_counts[_string(request.get("topic_label"), "selftest topic label")] += 1
    lowest_count = min(topic_counts.values())
    lowest_topics = sorted(topic for topic, count in topic_counts.items() if count == lowest_count)
    _require(len(lowest_topics) == 1, "selftest fixture must have one uniquely lowest-frequency topic")
    removed_topic = lowest_topics[0]
    replacement_topic = next(topic for topic in sorted(EXACT_CURRENT_TOPICS) if topic != removed_topic)
    for row in rows:
        request = _mapping(row.get("author_visible_request"), "selftest topic task request")
        if request.get("topic_label") == removed_topic:
            request["topic_label"] = replacement_topic
    task_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = root / "freeze_manifest.v1.json"
    manifest = _load_json(manifest_path)
    manifest["tasks_sha256"] = _sha256(task_path)
    _write_json(manifest_path, manifest)


def _forge_reference_format_with_matching_digest(root: Path) -> None:
    reference_path = root / "market_references.v1.jsonl"
    rows = [
        _mapping(json.loads(line), "selftest market reference")
        for line in reference_path.read_text(encoding="utf-8").splitlines()
    ]
    first_reference = rows[0]
    current_format = _string(first_reference.get("content_format"), "selftest reference content_format")
    first_reference["content_format"] = next(
        content_format for content_format in sorted(ALLOWED_FORMATS) if content_format != current_format
    )
    reference_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = root / "freeze_manifest.v1.json"
    manifest = _load_json(manifest_path)
    manifest["market_references_sha256"] = _sha256(reference_path)
    _write_json(manifest_path, manifest)


def _forge_disallowed_topic_product_with_matching_digest(root: Path) -> None:
    task_path = root / "frozen_tasks.v1.jsonl"
    rows = [_mapping(json.loads(line), "selftest mapped task") for line in task_path.read_text(encoding="utf-8").splitlines()]
    topic_counts: Counter[str] = Counter()
    for row in rows:
        request = _mapping(row.get("author_visible_request"), "selftest mapped task request")
        topic_counts[_string(request.get("topic_label"), "selftest mapped topic")] += 1

    changed = False
    for row in rows:
        request = _mapping(row.get("author_visible_request"), "selftest mapped task request")
        original_topic = _string(request.get("topic_label"), "selftest mapped topic")
        if topic_counts[original_topic] <= 1:
            continue
        internal = _mapping(row.get("internal"), "selftest mapped task internal")
        product_id = _string(internal.get("expected_product_id"), "selftest mapped product")
        replacement = next(
            (topic for topic in sorted(EXACT_CURRENT_TOPICS) if product_id not in CURRENT_TOPIC_PRODUCT_MAPPING[topic]),
            None,
        )
        if replacement is None or replacement == original_topic:
            continue
        request["topic_label"] = replacement
        changed = True
        break
    _require(changed, "selftest fixture must allow one current but product-disallowed topic mutation")
    mutated_topics = {
        _string(
            _mapping(row.get("author_visible_request"), "selftest mapped task request").get("topic_label"),
            "selftest mapped topic",
        )
        for row in rows
    }
    _require(mutated_topics == EXACT_CURRENT_TOPICS, "mapping selftest must preserve exact ten-topic coverage")
    task_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = root / "freeze_manifest.v1.json"
    manifest = _load_json(manifest_path)
    manifest["tasks_sha256"] = _sha256(task_path)
    _write_json(manifest_path, manifest)


def _forge_started_run(root: Path) -> None:
    path = root / "evidence" / "official_run_status.v1.json"
    status = _load_json(path)
    status["official_model_calls"] = 1
    status["official_tasks_started"] = 1
    _write_json(path, status)


def _forge_visible_product_label_with_matching_digest(root: Path) -> None:
    task_path = root / "frozen_tasks.v1.jsonl"
    rows = task_path.read_text(encoding="utf-8").splitlines()
    task = _mapping(json.loads(rows[0]), "selftest visible task")
    _mapping(task.get("author_visible_request"), "selftest visible request")["message"] = "岗位任务视频日志"
    rows[0] = json.dumps(task, ensure_ascii=False, sort_keys=True)
    task_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    manifest_path = root / "freeze_manifest.v1.json"
    manifest = _load_json(manifest_path)
    manifest["tasks_sha256"] = _sha256(task_path)
    _write_json(manifest_path, manifest)


def _forge_old_package_reuse(root: Path) -> None:
    path = root / "evidence" / "preflight.v1.json"
    preflight = _load_json(path)
    preflight["old_package10_results_consumed"] = True
    _write_json(path, preflight)


def run_selftest(root: Path) -> None:
    """Prove representative frozen-input and evidence tampering is rejected."""
    check_package(root)
    mutations: tuple[tuple[str, Mutation], ...] = (
        ("missing frozen task", _remove_one_task),
        ("forged freeze digest", _forge_manifest_digest),
        ("disabled format with refreshed digest", _forge_disabled_format_with_matching_digest),
        ("missing current topic with refreshed digest", _forge_missing_topic_with_matching_digest),
        ("reference format mismatch with refreshed digest", _forge_reference_format_with_matching_digest),
        ("disallowed topic-product mapping with refreshed digest", _forge_disallowed_topic_product_with_matching_digest),
        ("nonzero official run", _forge_started_run),
        ("visible product label with refreshed digest", _forge_visible_product_label_with_matching_digest),
        ("old Package 10 reuse", _forge_old_package_reuse),
    )
    with tempfile.TemporaryDirectory(prefix="q20-checker-selftest-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        for case_name, mutation in mutations:
            case_root = temporary_root / re.sub(r"[^a-z0-9]+", "-", case_name.lower()).strip("-")
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
        "--package-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="qualification package directory (defaults to this script's directory)",
    )
    parser.add_argument("--selftest", action="store_true", help="run isolated negative mutation tests")
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the checker and return a stable process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not __debug__:
        LOGGER.error("optimized Python mode is forbidden for this checker")
        return 2

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
