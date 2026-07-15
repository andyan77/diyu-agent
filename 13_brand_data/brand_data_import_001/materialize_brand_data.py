#!/usr/bin/env python3
"""Materialize deterministic brand-data import candidates from frozen snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
SNAPSHOT_ROOT = PACKAGE_ROOT / "source_snapshots"
DATA_ROOT = PACKAGE_ROOT / "data"
FIXTURE_ROOT = PACKAGE_ROOT / "fixtures"
TASK_ID = "DIYU_BRAND_DATA_IMPORT_READY_001"
TENANT_ID = "TENANT-DIYU-SIM-001"
BRAND_ID = "BRAND-DIYU-SIM-001"
NEUTRAL_PROFILE_REF = "expression-profile://neutral-default/v1"
PACKAGE_EVALUATED_AT = "2026-07-15T00:00:00Z"


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    filename: str
    sha256: str
    byte_size: int
    observed_from: str | None
    observed_until: str | None
    temporal_note: str


@dataclass(frozen=True)
class Scope:
    organization_id: str | None
    store_id: str | None
    content_account_id: str | None
    label: str


SOURCES = (
    SourceSpec(
        "SOURCE-01",
        "第一批：品牌世界设定、组织结构与事实治理基线.md",
        "db876e2ebcddb905df8e000eefbd4abcc306bfc6172b0635221df5a9aeefb163",
        30537,
        None,
        None,
        "UNDATED_SOURCE",
    ),
    SourceSpec(
        "SOURCE-02",
        "第二批：商品体系、尺码规格、库存流转与真实到店资料.md",
        "ca39dc31f5ce9faff74aec55186b22c6ab784bfef202b56991edf7de7c9adfa5",
        32616,
        "2026-07-10",
        "2026-07-10",
        "SOURCE_STATES_END_OF_BUSINESS_LOCAL_WITHOUT_TIMEZONE",
    ),
    SourceSpec(
        "SOURCE-03",
        "第三批：门店空间、陈列现状、动线调整与真实商品搭配.md",
        "90e6c1da841acdee1eef0abd3fae41bf0230f8aa6e549e738c988707c665503c",
        27389,
        "2026-07-11",
        "2026-07-11",
        "SOURCE_STATES_END_OF_BUSINESS_LOCAL_WITHOUT_TIMEZONE",
    ),
    SourceSpec(
        "SOURCE-04",
        "第四批：每日真实记录、顾客服务、研发验证、经营选择与承诺.md",
        "1560ace1e15affb5a20e9a80df2b7184aa826af6811fe8a54eeca32f33eabe23",
        33847,
        "2026-07-03",
        "2026-07-12",
        "SOURCE_STATES_DATE_RANGE_WITHOUT_TIMEZONE",
    ),
    SourceSpec(
        "SOURCE-05",
        "第五批：图片、视频、文件、人物授权与使用范围.md",
        "8f53d4d510a754ba34ebbc21d86b539874fc180005e28baedb8ff6b62aa99b0e",
        32559,
        "2026-07-12",
        "2026-07-12",
        "SOURCE_STATES_STATUS_DATE_WITHOUT_TIMEZONE",
    ),
    SourceSpec(
        "SOURCE-06",
        "第六批：已发布内容、审核修改、实际反馈、重复控制与能力覆盖.md",
        "698a1636493f46d80ed91c5957b0f07ea4e901928b8321152a85ab2a153d7172",
        35731,
        "2026-07-12",
        "2026-07-12",
        "SOURCE_STATES_END_OF_BUSINESS_LOCAL_WITHOUT_TIMEZONE",
    ),
    SourceSpec(
        "SOURCE-07",
        "第七批：真实业务请求、生成裁决、越权阻断与缺料反馈.md",
        "94988999e4ff256f70e579c710696024f79f5e15705493da2e58a13ab3c6c31f",
        27411,
        None,
        None,
        "UNDATED_SCENARIO_SOURCE",
    ),
    SourceSpec(
        "SOURCE-08",
        "第八批：11账号矩阵、人物岗位档案与30天连续事实记录.md",
        "3b4577c411ea34ce46db5e8fe13b0af3ce751dcc443a4db95f59a32a1ca923f9",
        53719,
        "2026-08-03",
        "2026-09-01",
        "EXPLICIT_SIMULATED_FUTURE_CYCLE",
    ),
    SourceSpec(
        "SOURCE-09",
        "综合补充增强包：经营责任、交易售后、本地生活、人物成长与事实纠错.md",
        "d4d6089fa03f58676ea72022ee8c99e3d44d2bf63f44e1a268814b491d430a3d",
        28678,
        None,
        None,
        "UNDATED_SOURCE",
    ),
)

HQ_SCOPE = Scope("ORG-DIYU-HQ", None, "ACCOUNT-DIYU-HQ-OFFICIAL", "笛语童装总部")
REGISTERED_SCOPE_MARKERS = (
    ("杭州滨江", Scope("ORG-DIYU-HZ-BINJIANG", "STORE-DIYU-HZ-BINJIANG", None, "杭州滨江店")),
    ("苏州园区", Scope("ORG-DIYU-SZ-PARK", "STORE-DIYU-SZ-PARK", None, "苏州园区店")),
    ("无锡滨湖", Scope("ORG-DIYU-WX-BINHU", "STORE-DIYU-WX-BINHU", None, "无锡滨湖店")),
    ("江苏", Scope("ORG-DIYU-JS-AGENT", None, None, "江苏区域")),
    ("总部", HQ_SCOPE),
)
UNREGISTERED_SCOPE_MARKERS = (
    "宁波",
    "武汉",
    "长沙",
    "成都",
    "重庆",
    "昆明",
    "八家门店",
    "蒋书宁",
)

# These headings were manually selected as headquarters-authored narrative candidates.
# The checker validates reference closure and authority metadata, not semantic quality.
READY_HQ_HEADINGS = {
    "SOURCE-01": {
        "二、品牌为什么成立",
        "四、笛语相信什么",
        "五、笛语不希望成为怎样的品牌",
        "十二、什么资料可以被认为是品牌事实",
        "十三、资料的生命过程",
        "十四、系统建议为什么不能自动成为事实",
        "十五、资料不足时怎样处理",
        "十六、人物表达的共同边界",
        "十七、第一批资料的使用结论",
    },
    "SOURCE-02": {"五、尺码不能只看身高"},
    "SOURCE-03": {
        "一、笛语怎样理解门店陈列",
        "二、门店空间资料怎样形成",
        "十一、模特使用原则",
        "十二、墙面与中岛的分工",
        "十三、陈列搭配依据",
        "十四、陈列调整前后怎样记录",
        "十七、陈列建议怎样避免编造",
        "十八、第三批结论",
    },
    "SOURCE-04": {
        "二、总部的每日真实记录",
        "十二、产品研发与验证记录",
        "十三、经营选择与实际代价",
        "十四、品牌当前公开承诺",
        "十五、尚未兑现或仍在处理的事项",
        "十八、第四批结论",
    },
    "SOURCE-05": {
        "一、笛语为什么把素材治理单独处理",
        "二、素材不是越多越好",
        "三、总部品牌素材",
        "四、商品图片和文件",
        "十、图片和视频的编辑边界",
        "十二、授权期限和撤回",
        "十四、离职人员素材怎样处理",
        "十五、文件原件与内容引用",
        "十六、历史素材清查",
        "十七、缺少授权时系统应该怎样回答",
        "二十二、第五批结论",
    },
    "SOURCE-06": {
        "一、为什么发布记录不能只保存最终文案",
        "三、总部官方账号已发布内容",
        "十五、没有发布的内容同样需要保存",
        "十六、内容反馈怎样被理解",
        "十七、不能从反馈中自动得出的结论",
        "十八、重复内容是怎样出现的",
        "十九、内容重复控制原则",
        "二十、账号之间的内容连续性",
        "二十三、当前最明显的资料缺口",
        "二十四、系统接到内容请求时应该怎样检查",
        "二十五、发布内容怎样失效",
        "二十六、第六批结论",
    },
}

HIGH_LEVEL_MODES = (
    "expression-mode://documentary-observation/v1",
    "expression-mode://professional-explanation/v1",
    "expression-mode://life-scene/v1",
    "expression-mode://styling-demonstration/v1",
    "expression-mode://store-micro-documentary/v1",
    "expression-mode://product-role-narrative/v1",
)

ACCOUNT_SOURCE_RANGES = (
    ("ACCOUNT-DIYU-HQ-OFFICIAL", 97, 129),
    ("ACCOUNT-DIYU-FOUNDER", 133, 155),
    ("ACCOUNT-DIYU-PRODUCT-LEAD", 159, 180),
    ("ACCOUNT-DIYU-RETAIL-DISPLAY", 184, 205),
    ("ACCOUNT-DIYU-CONTENT-LEAD", 209, 229),
    ("ACCOUNT-DIYU-HZ-BINJIANG", 233, 255),
    ("ACCOUNT-DIYU-JS-OFFICIAL", 259, 280),
    ("ACCOUNT-DIYU-JS-PRINCIPAL", 284, 303),
    ("ACCOUNT-DIYU-JS-STYLING-SERVICE", 307, 326),
    ("ACCOUNT-DIYU-SZ-PARK", 330, 349),
    ("ACCOUNT-DIYU-WX-BINHU", 353, 374),
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def canonical_jsonl(values: list[dict[str, Any]]) -> bytes:
    lines = [json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) for value in values]
    return ("\n".join(lines) + "\n").encode()


def snapshot_bytes(source: SourceSpec) -> bytes:
    value = (SNAPSHOT_ROOT / source.filename).read_bytes()
    if len(value) != source.byte_size or sha256_bytes(value) != source.sha256:
        raise ValueError(f"snapshot mismatch: {source.filename}")
    return value


def line_locator(source: SourceSpec, line_start: int, line_end: int) -> tuple[dict[str, Any], str]:
    value = snapshot_bytes(source)
    lines = value.splitlines(keepends=True)
    if line_start < 1 or line_end < line_start or line_end > len(lines):
        raise ValueError(f"invalid line range for {source.source_id}: {line_start}-{line_end}")
    byte_start = sum(len(line) for line in lines[: line_start - 1])
    byte_end = sum(len(line) for line in lines[:line_end])
    excerpt = value[byte_start:byte_end].decode("utf-8")
    locator = {
        "byte_end_exclusive": byte_end,
        "byte_start": byte_start,
        "line_end": line_end,
        "line_start": line_start,
    }
    return locator, excerpt


def split_level_one_sections(source: SourceSpec) -> list[dict[str, Any]]:
    value = snapshot_bytes(source)
    lines = value.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith(b"# ")]
    if not starts or starts[0] != 0:
        raise ValueError(f"source does not start with a level-one heading: {source.filename}")
    byte_starts: list[int] = []
    cursor = 0
    for line in lines:
        byte_starts.append(cursor)
        cursor += len(line)

    sections: list[dict[str, Any]] = []
    for section_index, start_index in enumerate(starts, start=1):
        next_index = starts[section_index] if section_index < len(starts) else len(lines)
        byte_start = byte_starts[start_index]
        byte_end = byte_starts[next_index] if next_index < len(lines) else len(value)
        body = value[byte_start:byte_end].decode("utf-8")
        heading = lines[start_index].decode("utf-8").strip()[2:]
        sections.append(
            {
                "body": body,
                "heading": heading,
                "locator": {
                    "byte_end_exclusive": byte_end,
                    "byte_start": byte_start,
                    "line_end": next_index,
                    "line_start": start_index + 1,
                },
                "section_index": section_index,
            }
        )
    if "".join(section["body"] for section in sections).encode("utf-8") != value:
        raise ValueError(f"segmentation is not byte complete: {source.filename}")
    return sections


def explicit_heading_scope(heading: str) -> Scope | None:
    for marker, scope in REGISTERED_SCOPE_MARKERS:
        if marker in heading:
            return scope
    return None


def narrative_classification(source: SourceSpec, heading: str, body: str) -> tuple[str, Scope | None, str]:
    if any(marker in body for marker in UNREGISTERED_SCOPE_MARKERS):
        return "HOLD_UNREGISTERED_SCOPE", None, "SOURCE_SCOPE_NOT_IN_PUBLIC_IDENTITY_CONTRACT"
    if source.source_id == "SOURCE-07":
        return "HOLD_NON_FACT_SCENARIO", None, "REQUEST_AND_DECISION_SCENARIO_ONLY"
    if source.source_id == "SOURCE-08":
        return "HOLD_FUTURE_SIMULATION", None, "EXPLICIT_FUTURE_SIMULATION_NOT_OBSERVED"
    if heading in READY_HQ_HEADINGS.get(source.source_id, set()):
        return "READY_FOR_PACKAGE_5_REVIEW", HQ_SCOPE, "MANUALLY_CURATED_HQ_SCOPE"
    registered_scope = explicit_heading_scope(heading)
    if registered_scope is not None and registered_scope != HQ_SCOPE:
        return "HOLD_AUTHORIZATION_SCOPE", registered_scope, "NO_MATCHING_NARRATIVE_DISCLOSURE_GRANT"
    return "HOLD_SEMANTIC_SCOPE_REVIEW", registered_scope, "SCOPE_OR_SEMANTIC_REVIEW_REQUIRED"


def materialize_narrative_units() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source in SOURCES:
        for section in split_level_one_sections(source):
            import_state, scope, reason = narrative_classification(source, section["heading"], section["body"])
            ready = import_state == "READY_FOR_PACKAGE_5_REVIEW"
            record = {
                "applicable_content_account_ids": [scope.content_account_id] if ready and scope else [],
                "applicable_organization_ids": [scope.organization_id] if ready and scope else [],
                "applicable_store_ids": [scope.store_id] if ready and scope else [],
                "authorization_ref": "AUTH-SIM-001" if ready else None,
                "authorization_state": "GRANTED" if ready else "MISSING_OR_NOT_APPLICABLE",
                "body": section["body"],
                "body_sha256": sha256_bytes(section["body"].encode("utf-8")),
                "brand_id": BRAND_ID,
                "disclosure_scope": "CONTENT_ACCOUNT_ONLY" if ready else "NONE",
                "heading": section["heading"],
                "hold_reason": None if ready else reason,
                "import_review_state": import_state,
                "locator": section["locator"],
                "observed_at": source.observed_until,
                "publish_allowed": False,
                "revocation_ref": None,
                "runtime_consumable": False,
                "semantic_review_required": True,
                "source_id": source.source_id,
                "source_organization_id": scope.organization_id if scope else None,
                "source_scope_label": scope.label if scope else None,
                "source_sha256": source.sha256,
                "source_status": (
                    "FUTURE_SIMULATION"
                    if source.source_id == "SOURCE-08"
                    else "MISSING_OBSERVATION_TIME"
                    if source.observed_until is None
                    else "SOURCE_ASSERTED"
                ),
                "source_store_id": scope.store_id if scope else None,
                "tenant_id": TENANT_ID,
                "unit_id": f"BD-NARR-{source.source_id[-2:]}-{section['section_index']:03d}",
                "valid_until": None,
            }
            records.append(record)
    return records


def precise_fact(
    fact_id: str,
    fact_kind: str,
    value: Any,
    line_start: int,
    line_end: int,
    *,
    organization_id: str | None = "ORG-DIYU-HQ",
    store_id: str | None = None,
    account_id: str | None = "ACCOUNT-DIYU-HQ-OFFICIAL",
    authorization_ref: str | None = "AUTH-SIM-001",
    status: str = "SOURCE_ASSERTED",
    import_review_state: str = "READY_FOR_PACKAGE_5_REVIEW",
    valid_until: str | None = None,
    hold_reason: str | None = None,
) -> dict[str, Any]:
    source = SOURCES[1]
    locator, excerpt = line_locator(source, line_start, line_end)
    return {
        "applicable_content_account_ids": [account_id] if account_id else [],
        "authorization_ref": authorization_ref,
        "authorization_state": "GRANTED" if authorization_ref else "MISSING_OR_NOT_APPLICABLE",
        "brand_id": BRAND_ID,
        "conflict_group_id": None,
        "disclosure_scope": "CONTENT_ACCOUNT_ONLY" if authorization_ref else "NONE",
        "effective_at": "2026-07-10",
        "fact_id": fact_id,
        "fact_kind": fact_kind,
        "hold_reason": hold_reason,
        "import_review_state": import_review_state,
        "locator": locator,
        "organization_id": organization_id,
        "publish_allowed": False,
        "revocation_ref": None,
        "runtime_consumable": False,
        "semantic_review_required": True,
        "source_excerpt": excerpt,
        "source_excerpt_sha256": sha256_bytes(excerpt.encode("utf-8")),
        "source_id": source.source_id,
        "source_ref": f"snapshot://{source.source_id}/L{line_start}-L{line_end}",
        "source_sha256": source.sha256,
        "status": status,
        "store_id": store_id,
        "tenant_id": TENANT_ID,
        "valid_until": valid_until,
        "value": value,
    }


def materialize_precise_facts() -> list[dict[str, Any]]:
    return [
        precise_fact(
            "BD-FACT-001",
            "SKU",
            {"product_name": "云感圆领长袖上衣", "sku": "DY26A001"},
            41,
            43,
        ),
        precise_fact(
            "BD-FACT-002",
            "SPECIFICATION",
            {"colors": ["米杏", "雾蓝", "深灰"], "size_step_cm": 10, "size_range_cm": [100, 150]},
            45,
            45,
        ),
        precise_fact(
            "BD-FACT-003",
            "SKU",
            {"product_name": "松弛活动卫衣", "sku": "DY26A002"},
            63,
            65,
        ),
        precise_fact(
            "BD-FACT-004",
            "SKU",
            {"product_name": "灯芯绒衬衫夹克", "sku": "DY26A009"},
            215,
            217,
        ),
        precise_fact(
            "BD-FACT-005",
            "SPECIFICATION",
            {"colors": ["焦糖棕", "苔绿色", "深蓝色"], "size_range_cm": [110, 150], "size_100_produced": False},
            219,
            227,
        ),
        precise_fact(
            "BD-FACT-006",
            "STOCK",
            {"affected_sample_count": 12, "color": "雾蓝", "size_cm": 130, "state": "PAUSED_SHIPMENT"},
            57,
            59,
            status="RECONFIRMATION_REQUIRED",
        ),
        precise_fact(
            "BD-FACT-007",
            "STOCK",
            {"color": "浅卡其", "quantity": 1, "size_cm": 130, "store": "杭州滨江店"},
            249,
            251,
            organization_id="ORG-DIYU-HZ-BINJIANG",
            store_id="STORE-DIYU-HZ-BINJIANG",
            account_id="ACCOUNT-DIYU-PRODUCT-LEAD",
            authorization_ref="AUTH-SIM-PRODUCT-CROSS-ORG-001",
            status="EXPIRED",
            import_review_state="HOLD_EXPIRED",
            valid_until="2026-07-10",
            hold_reason="SOURCE_REQUIRES_CURRENT_DAY_RECONFIRMATION",
        ),
        precise_fact(
            "BD-FACT-008",
            "STOCK",
            {"normally_sellable_new_style_count": 8, "store": "苏州园区店"},
            413,
            423,
            organization_id="ORG-DIYU-SZ-PARK",
            store_id="STORE-DIYU-SZ-PARK",
            account_id="ACCOUNT-DIYU-SZ-PARK",
            authorization_ref="AUTH-SIM-SPOOFED-SCOPE-001",
            status="EXPIRED",
            import_review_state="HOLD_EXPIRED",
            valid_until="2026-07-10",
            hold_reason="SOURCE_REQUIRES_CURRENT_STATE_RECONFIRMATION",
        ),
        precise_fact(
            "BD-FACT-009",
            "STOCK",
            {"color": "藏青", "size_cm": 110, "state": "OUT_OF_STOCK", "store": "武汉江汉店"},
            63,
            79,
            organization_id=None,
            store_id=None,
            account_id=None,
            authorization_ref=None,
            status="HOLD_UNREGISTERED_SCOPE",
            import_review_state="HOLD_UNREGISTERED_SCOPE",
            valid_until="2026-07-10",
            hold_reason="SOURCE_SCOPE_NOT_IN_PUBLIC_IDENTITY_CONTRACT",
        ),
    ]


def materialize_examples() -> list[dict[str, Any]]:
    source = SOURCES[0]
    ranges = (("BD-EXAMPLE-001", 75, 79), ("BD-EXAMPLE-002", 89, 91), ("BD-EXAMPLE-003", 498, 510))
    records: list[dict[str, Any]] = []
    for example_id, line_start, line_end in ranges:
        locator, excerpt = line_locator(source, line_start, line_end)
        records.append(
            {
                "example_id": example_id,
                "example_status": "CANDIDATE_PENDING_INDEPENDENT_EXPRESSION_REVIEW",
                "locator": locator,
                "may_grant_authorization": False,
                "may_grant_fact": False,
                "may_grant_scope": False,
                "publish_allowed": False,
                "runtime_authoritative": False,
                "source_id": source.source_id,
                "source_sha256": source.sha256,
                "text": excerpt,
                "text_sha256": sha256_bytes(excerpt.encode("utf-8")),
            }
        )
    return records


def materialize_expression_candidates() -> dict[str, Any]:
    account_mappings = []
    for account_id, line_start, line_end in ACCOUNT_SOURCE_RANGES:
        account_mappings.append(
            {
                "account_id": account_id,
                "account_specific_persona_created": False,
                "default_profile_ref": NEUTRAL_PROFILE_REF,
                "publish_allowed": False,
                "requested_high_level_mode_refs": [],
                "runtime_profile_resolution_claimed": False,
                "source_ref": f"snapshot://SOURCE-08/L{line_start}-L{line_end}",
            }
        )
    return {
        "account_mappings": account_mappings,
        "available_high_level_mode_refs": list(HIGH_LEVEL_MODES),
        "brand_guidance_candidate": {
            "candidate_only": True,
            "default_profile_ref": NEUTRAL_PROFILE_REF,
            "guidance_notes": [
                "TRUTH_BEFORE_POLISH",
                "PROFESSIONAL_WITHOUT_UNSUPPORTED_CERTAINTY",
                "CHARACTER_SHOWN_THROUGH_CONFIRMED_ACTION",
            ],
            "hard_prohibitions_may_be_weakened": False,
            "runtime_profile_ref": None,
            "source_example_refs": ["BD-EXAMPLE-001", "BD-EXAMPLE-002", "BD-EXAMPLE-003"],
        },
        "brand_id": BRAND_ID,
        "expression_service_owns_runtime_resolution": True,
        "fact_or_authorization_authority": False,
        "light_content_plan_created": False,
        "publish_allowed": False,
        "runtime_authoritative": False,
        "schema_version": "v1.0",
        "task_id": TASK_ID,
        "tenant_id": TENANT_ID,
    }


def materialize_cases() -> list[dict[str, Any]]:
    return [
        {"acceptance": "PKG3-A10", "case_id": "normal_review_ready", "expected_pass": True, "mutation": "NONE"},
        {"acceptance": "PKG3-A10", "case_id": "needs_more_information_hold", "expected_pass": True, "mutation": "ASSERT_HOLD_PRESENT"},
        {"acceptance": "PKG3-A10", "case_id": "degraded_reconfirmation", "expected_pass": True, "mutation": "ASSERT_RECONFIRMATION_PRESENT"},
        {"acceptance": "PKG3-A01", "case_id": "changed_source_digest", "expected_pass": False, "mutation": "CHANGE_SOURCE_DIGEST"},
        {"acceptance": "PKG3-A04", "case_id": "unknown_identifier", "expected_pass": False, "mutation": "SET_UNKNOWN_ORGANIZATION"},
        {"acceptance": "PKG3-A05", "case_id": "unregistered_scope_leak", "expected_pass": False, "mutation": "MAKE_UNREGISTERED_FACT_READY"},
        {"acceptance": "PKG3-A05", "case_id": "unregistered_narrative_scope_leak", "expected_pass": False, "mutation": "MAKE_UNREGISTERED_NARRATIVE_READY"},
        {"acceptance": "PKG3-A06", "case_id": "unauthorized_direct_use", "expected_pass": False, "mutation": "REMOVE_READY_AUTHORIZATION"},
        {"acceptance": "PKG3-A06", "case_id": "wrong_authorization_kind", "expected_pass": False, "mutation": "USE_REQUIREMENT_CONFIRMATION_GRANT"},
        {"acceptance": "PKG3-A06", "case_id": "expired_authorization_grant", "expected_pass": False, "mutation": "EXPIRE_READY_GRANT"},
        {"acceptance": "PKG3-A06", "case_id": "not_yet_valid_authorization_grant", "expected_pass": False, "mutation": "DEFER_READY_GRANT"},
        {"acceptance": "PKG3-A06", "case_id": "revoked_fact_authorization_state", "expected_pass": False, "mutation": "REVOKE_READY_FACT_AUTHORIZATION_STATE"},
        {"acceptance": "PKG3-A06", "case_id": "expired_fact_validity", "expected_pass": False, "mutation": "EXPIRE_READY_FACT_VALIDITY"},
        {"acceptance": "PKG3-A07", "case_id": "unsupported_fact_kind", "expected_pass": False, "mutation": "SET_UNSUPPORTED_FACT_KIND"},
        {"acceptance": "PKG3-A06", "case_id": "revoked_direct_use", "expected_pass": False, "mutation": "MAKE_REVOKED_RUNTIME_CONSUMABLE"},
        {"acceptance": "PKG3-A06", "case_id": "expired_direct_use", "expected_pass": False, "mutation": "MAKE_EXPIRED_RUNTIME_CONSUMABLE"},
        {"acceptance": "PKG3-A06", "case_id": "conflict_direct_use", "expected_pass": False, "mutation": "MAKE_CONFLICT_RUNTIME_CONSUMABLE"},
        {"acceptance": "PKG3-A08", "case_id": "expression_authority_escalation", "expected_pass": False, "mutation": "MAKE_EXPRESSION_AUTHORITATIVE"},
        {"acceptance": "PKG3-A12", "case_id": "false_readiness", "expected_pass": False, "mutation": "SET_DATABASE_IMPORTED_TRUE"},
    ]


def write_materialized_files() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    narrative_units = materialize_narrative_units()
    precise_facts = materialize_precise_facts()
    examples = materialize_examples()
    expression_candidates = materialize_expression_candidates()
    cases = materialize_cases()
    outputs = {
        "data/example_references.v1.jsonl": canonical_jsonl(examples),
        "data/expression_import_candidates.v1.json": canonical_json(expression_candidates),
        "data/narrative_units.v1.jsonl": canonical_jsonl(narrative_units),
        "data/precise_facts.v1.jsonl": canonical_jsonl(precise_facts),
        "fixtures/check_cases.v1.jsonl": canonical_jsonl(cases),
    }
    for relative_path, value in outputs.items():
        (PACKAGE_ROOT / relative_path).write_bytes(value)

    manifest = {
        "artifacts": [
            {
                "byte_size": len(value),
                "path": path,
                "sha256": sha256_bytes(value),
            }
            for path, value in sorted(outputs.items())
        ],
        "baseline_commit": "95b8b1700b7e96b1d2383465713bef8c36e7f6cb",
        "external_calls": {"database": 0, "dify": 0, "model": 0, "production": 0, "retrieval": 0},
        "materialization": {
            "body_preservation": "EXACT_UTF8_TEXT_FROM_BYTE_RANGE",
            "narrative_segmentation": "MARKDOWN_LEVEL_ONE_SECTIONS",
            "scope_classification": "EXPLICIT_MANUAL_ALLOWLIST_WITH_FAIL_CLOSED_HOLDS",
            "semantic_quality_machine_claimed": False,
        },
        "public_anchors": [
            {
                "path": "11_product_foundation/public_foundation_001/contract/public_foundation_contract.v1.yaml",
                "sha256": "a3aec92fdcc22635bb07bc5d2595ebaa5cfa1f1c9d5fad42cc39481808bbc1af",
            },
            {
                "path": "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml",
                "sha256": "65b8242b9b760e64f8e441c4334c68fa76f6dc3a11e2fe2f8f62ad6a887c3cbc",
            },
        ],
        "readiness": {
            "DIFY_ready": False,
            "KE_ready": False,
            "RAG_ready": False,
            "candidatepack_ready": False,
            "database_imported": False,
            "generation_allowed": False,
            "generation_eligible": False,
            "generator_qualified": False,
            "production_ready": False,
            "production_servable": False,
            "publish_allowed": False,
            "release_ready": False,
            "retrieval_available": False,
            "retrieval_ready": False,
            "runtime_ready": False,
        },
        "schema_version": "v1.0",
        "sources": [
            {
                "byte_size": source.byte_size,
                "expected_external_path": (
                    "/mnt/c/Users/Administrator/Documents/笛语agent/笛语童装专属数据库数据/" + source.filename
                ),
                "observed_from": source.observed_from,
                "observed_until": source.observed_until,
                "sha256": source.sha256,
                "snapshot_path": "source_snapshots/" + source.filename,
                "source_id": source.source_id,
                "temporal_note": source.temporal_note,
            }
            for source in SOURCES
        ],
        "task_id": TASK_ID,
    }
    (PACKAGE_ROOT / "materialization_manifest.v1.json").write_bytes(canonical_json(manifest))


if __name__ == "__main__":
    write_materialized_files()
