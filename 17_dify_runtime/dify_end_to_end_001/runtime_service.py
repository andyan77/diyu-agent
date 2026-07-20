#!/usr/bin/env python3
"""Thin Package 7 coordinator that reuses Package 6 and Package 2."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from author_contract import (
    AUTHOR_CONTRACT_VERSION,
    CANDIDATE_MODELS,
    CandidateBase,
    ChatEnvelope,
    ContentFormat,
    contract_descriptor,
    deliverable_field_names,
    parse_candidate_envelope,
)
from contracts import (
    BridgePrepareRequest,
    CandidateSurfaces,
    ModelCandidate,
    ModelEnvelope,
    ProductionPackage,
    escape_json_string_control_characters,
    escape_unambiguous_json_string_quotes,
    normalize_model_json_text,
    normalize_unambiguous_json_structural_quotes,
    rebuild_fragmented_candidate_envelope,
    remove_unambiguous_json_trailing_commas,
)
from persistence import (
    RuntimeRepository,
    SqlAlchemyPlanStore,
    TrustedDatabaseScope,
    current_trusted_database_scope,
    digest_object,
    recommended_directions,
    runtime_browser_session,
    trusted_database_scope,
)
from runtime_models import RuntimeCandidate, RuntimeModelRun
from runtime_retrieval import RuntimeBrandFactRetrievalService


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_2_ROOT = (
    REPOSITORY_ROOT / "12_expression_service/expression_runtime_adapter_001"
)
PACKAGE_6_ROOT = REPOSITORY_ROOT / "16_composition_runtime/fact_aware_plan_adapter_001"
for root in (PACKAGE_2_ROOT, PACKAGE_6_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from fact_aware_plan_adapter import (  # type: ignore[import-not-found]  # noqa: E402
    FactAwarePlanAdapter,
    SERVER_ACCESS_AUTHORITY,
    SERVER_TASK_AUTHORITY,
    START_CREATION,
    ServerConfirmedProductionTask,
    ServerPlanAccess,
)
from light_expression_service import (  # type: ignore[import-not-found]  # noqa: E402
    AccountAuthority,
    LightExpressionService,
    TrustedUpstreamContext,
    digest_object as digest_plan_object,
)


TOPIC_PATH = (
    REPOSITORY_ROOT
    / "11_product_foundation/public_foundation_001/taxonomy/topic_product_mapping.v1.yaml"
)
ACTION_PATH = (
    REPOSITORY_ROOT
    / "14_dify_shell/dify_content_shell_001/state_action_mapping.v1.json"
)
CAPABILITY_PATH = PACKAGE_ROOT / "content_capability_mapping.v1.yaml"
NARRATIVE_ARCHITECTURES = (
    "EVIDENCE_FIRST",
    "QUESTION_ANSWER",
    "OBJECT_OR_TIMELINE",
)
PROTECTED_SOURCE_DETAIL_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s*(?:厘米|cm|毫米|mm|米|m|元|折|%|件|款|次|天|月|年|号|码)?"
    r"\s*(?:至|到|[-–—~～])\s*"
    r"\d+(?:\.\d+)?\s*(?:厘米|cm|毫米|mm|米|m|元|折|%|件|款|次|天|月|年|号|码)?"
    r"|\d+(?:\.\d+)?\s*(?:厘米|cm|毫米|mm|米|m|元|折|%|件|款|次|天|月|年|号|码)?"
    r"|薄针织|同色|双重厚度|春季|夏季|秋季|冬季|设计稿|样衣|照片|视频|"
    r"截图|工作台|品牌色|品牌字体|logo|Logo|库存|售价|价格|折扣|顾客|家长|员工|儿童|孩子|人物|模特|"
    r"更自在|更舒服|更轻松|永久解决|彻底解决|解决了|不再|所有"
    r"|[零〇一二两三四五六七八九十百千万]+(?:厘米|cm|元|折|件|款|天|月|年|号|码)"
)
CREATIVE_INSTRUCTION_SURFACE_PATH = re.compile(
    r"^execution_payload\.(?:production_format|task_summary|content_direction|core_idea|"
    r"target_platform|duration_label|next_actions\[[0-9]+\]|"
    r"video\.shots\[[0-9]+\]\.(?:time_range|visual|action|camera|scene_product_props|edit_note)|"
    r"video\.(?:shooting_notes|editing_notes)\[[0-9]+\]|"
    r"article\.frames\[[0-9]+\]\.image_brief|article\.(?:cover_brief|layout_notes\[[0-9]+\])|"
    r"display\.(?:arrangement_relationship|spatial_layers|color_relationship|availability_caution|"
    r"shooting_angles\[[0-9]+\]))$"
)
KEY_NUMBER_PATTERN = re.compile(
    r"(?:尺码|售价|价格|库存|数量|比例|折扣|身高|年龄|日期|截至).{0,12}"
    r"(?:\d|[零〇一二两三四五六七八九十百千万])"
    r"|(?:\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百千万]+)\s*"
    r"(?:厘米|cm|毫米|mm|米|m|元|折|%|天|月|年|号|码)"
    r"|(?:\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百千万]+)\s*"
    r"(?:件|款).{0,8}(?:库存|现货|可售|售罄|剩余)"
)
NATURAL_DIALOGUE_AUDIO_PATTERN = re.compile(
    r"^(?:[^：:\n]{0,16}(?:员|同事|店长|主持人|主理人|创始人|顾客|家长|妈妈|爸爸|孩子|老师|负责人|记录者|观察者|设计师|陈列师))[：:]\s*\S"
    r"|[“\"][^”\"]+[”\"]"
    r"|(?:说|问|回应|回答|自言自语|话语|对话|问候)[：:]?\s*[“\"]"
)
PRODUCT_FACT_ASSERTION_PATTERN = re.compile(
    r"(?:这款|该款|本款|这件|该件|商品|产品|上衣|童装|样衣|面料|材质|尺码|颜色|厚度|售价|价格|库存)"
    r".{0,20}(?:采用|使用|为|是|具有|具备|包含|支持|适合|来自|属于|可售|备有)"
    r"|(?:上衣|商品|产品).{0,12}(?:纯棉|亚麻|针织|羊毛|涤纶|棉质)"
    r"|(?:采用|使用|具备|包含).{0,16}(?:薄针织|双重厚度|纯棉|亚麻|羊毛|涤纶|棉质|面料|材质)"
    r"|(?:本店|门店|当前)?.{0,6}库存.{0,10}(?:充足|不足|有货|缺货|可售|售罄|剩余|紧张)"
    r"|(?:百分百|完全|绝对).{0,8}适合|适合所有|所有孩子都"
    r"|(?:这款|该款|本款|这件|该件|商品|产品|上衣|童装).{0,20}"
    r"(?:改善|缓解|治愈|解决|更舒服|更轻松|更自在)"
)
AUTHORIZATION_CLAIM_PATTERN = re.compile(
    r"(?:已|已经|此前|目前).{0,24}(?:授权|获准|批准|允许|有权|代表)"
    r"|(?:总部|区域|门店|品牌|本账号|该账号|这个账号).{0,18}(?:批准|授权|获准|允许|有权)"
    r"|(?:本账号|该账号|这个账号|区域账号|门店账号).{0,12}代表(?:当前|总部|区域|门店|组织)"
    r"|(?:代表当前|有权|获准|已授权|经授权|官方账号)"
)
REAL_EVENT_CLAIM_PATTERN = re.compile(
    r"(?:已|已经|昨天|今天|上周|本周|上月|本月|去年|今年|日前|近期|此前).{0,24}"
    r"(?:发生|举办|完成|发布|上线|售出|到店|调整|拍摄|反馈|决定|承诺|购买|选择|试穿)"
    r"|(?:顾客|员工|家长|儿童|孩子).{0,18}(?:说|反馈|购买|完成|决定|承诺)"
    r"|(?:企业|品牌|公司|总部|门店).{0,18}(?:决定|承诺|保证)"
)
INTERNAL_REFERENCE_PATTERN = re.compile(
    r"(?:PKG5-FRAGMENT|FACT-|AUTH-|ACCOUNT-|TENANT-|ORG-|STORE-|CP(?:0[1-9]|1[0-9]|20))"
)
PERSONAL_INFORMATION_PATTERN = re.compile(
    r"(?<!\d)1[3-9]\d{9}(?!\d)|(?<!\d)\d{17}[0-9Xx](?!\d)"
)
SECRET_SURFACE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"Bearer [A-Za-z0-9._-]{20,}"),
)
EXPLICIT_REQUIRED_OBJECT_PATTERN = re.compile(
    r"(?:使用|采用|根据|基于|结合|参考|拿|把|分析|改写|解读).{0,16}"
    r"(?:这份|这个|这张|这段|该份|该张|该段|上述|前述|刚才提到的|"
    r"我上传的|已上传的|上传的|提供的|未提供的|未上传的).{0,8}"
    r"(?:文件|图片|照片|视频|声音|音频|录音|素材|截图|海报|设计稿)"
)
FUTURE_OR_HYPOTHETICAL_PATTERN = re.compile(
    r"(?:建议|可以|可拍|计划|如果|若有|如有|假设|示意|未来|待确认|需准备|"
    r"不代表|不能确认|不得视为|不可假设|不把.{0,16}写成|并非|不是已发生)"
)
ENTERPRISE_COMMITMENT_PATTERN = re.compile(
    r"(?:企业|品牌|公司|总部|区域|门店).{0,24}(?:承诺|保证|确保|永久|全部解决|一定会)"
)
ANONYMOUS_DAILY_EVENT_PATTERN = re.compile(
    r"^(?:一位|有位|匿名)?(?:顾客|孩子|儿童|家长|员工).{0,24}"
    r"(?:选择|试穿|拿起|放下|走进|看了|问|比较|转身)"
)
EXISTING_ASSET_CLAIM_PATTERN = re.compile(
    r"(?:已有|现有|已经|已提供|已拍摄|可直接使用).{0,18}(?:照片|视频|样衣|设计稿|截图|工作台|库存)"
    r"|(?:照片|视频|样衣|设计稿|截图|工作台|库存).{0,18}(?:已有|现有|已经|已提供|可用|存在|确认)"
    r"|(?:门店|现场|当前)?.{0,6}(?:备有|备着|提供了|准备了).{0,12}(?:照片|视频|样衣|设计稿|截图|工作台|库存)"
)
CLAUSE_SPLIT_PATTERN = re.compile(r"[，,。；;！？!?：:\n]+")
NON_ASSERTIVE_BOUNDARY_PATTERN = re.compile(
    r"(?:不代表|只代表组织层级|不能确认|不得视为|不可假设|尚待确认|待确认|仅用于内部|不可发布|暂时不发布|还没有新的本地事实)"
    r"|(?:(?:也)?不讲|不写|不声称|不宣称|不承诺|不能承诺|不可承诺|不保证|不替|禁止|不得|不要|避免|拒绝)"
    r".{0,24}(?:已完成|已经完成|授权|决定|承诺|保证)"
    r"|任何宣称"
    r"|(?:授权管理|授权流程|授权变化|授权边界)"
    r"|(?:讨论|分享|说明|识别|区分|提醒|强调).{0,28}(?:授权|承诺|保证)"
    r"|(?:不能|不可|不要|不得|避免|禁止|拒绝).{0,48}"
    r"(?:承诺|保证|证言|顾客都说|所有孩子都|百分百适合)"
    r"|(?:看到|听到|遇到).{0,48}(?:说|写|讲|声称)"
    r"|(?:待核对|需要核对|先核对)"
    r"|(?:尺码表|尺码).{0,12}(?:从来)?不是.{0,12}(?:一个数字|简单表格|单一依据|唯一依据)"
)
NEGATED_PROHIBITION_PREFIX_PATTERN = re.compile(
    r"(?:(?:不说|不要说|请勿说|不讲|不写|不使用|不得使用|不要使用|避免使用|"
    r"禁止使用|禁用|请勿使用|拒绝使用|不能说|不可写|不要把|不能把|不承诺|"
    r"不能承诺|不得承诺).{0,48}"
    r"|(?:不要|不得|不能|避免|禁止|拒绝).{0,48}(?:使用|采用|写|说|讲|承诺).{0,12}"
    r"|(?:看到|听到|遇到).{0,24}(?:说|写|讲|声称).{0,16})$"
)
NEGATED_PROHIBITION_SUFFIX_PATTERN = re.compile(
    r"^[\"'“”‘’「」『』《》（）()]{0,2}"
    r"(?:不能|不可|不应|不作为|不等于|并非|不是|只作|仅作|这类)"
)
CONDITIONAL_AUTHORIZATION_PATTERN = re.compile(
    r"^(?:建议|计划)?(?:如有|若有|如果有|假如有|仅在有).{0,24}(?:已授权|经授权|获准|批准|允许)"
)
KEY_FACT_CONTEXT_PATTERN = re.compile(
    r"(?:售价|价格|库存|现货|可售|售罄|剩余|尺码|规格|身高|年龄|日期|截至|折扣|比例|承诺)"
)
NUMERIC_DETAIL_PATTERN = re.compile(
    r"^(?P<first>\d+(?:\.\d+)?)"
    r"(?P<first_unit>厘米|cm|毫米|mm|米|m|元|折|%|件|款|次|天|月|年|号|码)?"
    r"(?:\s*(?:至|到|[-–—~～])\s*(?P<second>\d+(?:\.\d+)?)"
    r"(?P<second_unit>厘米|cm|毫米|mm|米|m|元|折|%|件|款|次|天|月|年|号|码)?)?$",
    re.IGNORECASE,
)


def normalize_support_text(value: str) -> str:
    return value.lower().replace("cm", "厘米").replace("孩子", "儿童")


def normalize_numeric_detail(value: str) -> str | None:
    """Normalize only finite number, unit, and range spelling equivalents."""

    compact = re.sub(r"\s+", "", value).lower()
    match = NUMERIC_DETAIL_PATTERN.fullmatch(compact)
    if match is None:
        return None

    def number(raw: str) -> str:
        try:
            normalized = Decimal(raw).normalize()
        except InvalidOperation:
            return raw
        return format(normalized, "f")

    def unit(raw: str | None) -> str:
        if raw is None:
            return ""
        return {
            "厘米": "cm",
            "cm": "cm",
            "毫米": "mm",
            "mm": "mm",
            "米": "m",
            "m": "m",
        }.get(raw.lower(), raw.lower())

    first_unit = unit(match.group("first_unit"))
    second = match.group("second")
    if second is None:
        return f"{number(match.group('first'))}{first_unit}"
    second_unit = unit(match.group("second_unit"))
    shared_unit = first_unit or second_unit
    return (
        f"{number(match.group('first'))}{first_unit or shared_unit}~"
        f"{number(second)}{second_unit or shared_unit}"
    )


def protected_detail_is_supported(detail: str, corpus: str) -> bool:
    if any(character.isdigit() for character in detail):
        normalized_detail = normalize_numeric_detail(detail)
        if normalized_detail is None:
            return False
        return normalized_detail in {
            normalized
            for token in PROTECTED_SOURCE_DETAIL_PATTERN.findall(corpus)
            if (normalized := normalize_numeric_detail(token)) is not None
        }
    return normalize_support_text(detail) in normalize_support_text(corpus)


def high_risk_fact_clauses(path: str, text: str) -> tuple[str, ...]:
    """Classify explicit reality claims while leaving creative directions open."""

    clauses: list[str] = []
    for clause in filter(
        None, (part.strip() for part in CLAUSE_SPLIT_PATTERN.split(text))
    ):
        if EXISTING_ASSET_CLAIM_PATTERN.search(clause):
            clauses.append(clause)
            continue
        if NON_ASSERTIVE_BOUNDARY_PATTERN.search(clause):
            continue
        product_fact = PRODUCT_FACT_ASSERTION_PATTERN.search(clause) is not None
        authorization_fact = (
            AUTHORIZATION_CLAIM_PATTERN.search(clause) is not None
            and CONDITIONAL_AUTHORIZATION_PATTERN.search(clause) is None
        )
        enterprise_commitment = ENTERPRISE_COMMITMENT_PATTERN.search(clause) is not None
        real_event = REAL_EVENT_CLAIM_PATTERN.search(clause) is not None
        if real_event and (
            FUTURE_OR_HYPOTHETICAL_PATTERN.search(clause)
            or ANONYMOUS_DAILY_EVENT_PATTERN.search(clause)
        ):
            real_event = False
        key_number = KEY_NUMBER_PATTERN.search(clause) is not None
        if (
            key_number
            and CREATIVE_INSTRUCTION_SURFACE_PATH.fullmatch(path)
            and KEY_FACT_CONTEXT_PATTERN.search(clause) is None
        ):
            key_number = False
        if any(
            (
                key_number,
                product_fact,
                authorization_fact,
                enterprise_commitment,
                real_event,
            )
        ):
            clauses.append(clause)
    return tuple(clauses)


def surface_requires_evidence_binding(path: str, text: str) -> bool:
    """Require bindings only for explicit factual assertions, not creative prose."""

    return bool(high_risk_fact_clauses(path, text))


def audience_surface_text_map(value: object) -> dict[str, str]:
    """Enumerate every non-empty audience-facing text leaf exactly once."""

    result: dict[str, str] = {}

    def visit(child: object, path: str) -> None:
        if isinstance(child, str):
            normalized = child.strip()
            if normalized:
                result[path] = normalized
            return
        if isinstance(child, list):
            for index, item in enumerate(child):
                visit(item, f"{path}[{index}]")
            return
        if isinstance(child, dict):
            for key, item in child.items():
                if key == "surface_units":
                    continue
                visit(item, f"{path}.{key}" if path else str(key))

    visit(value, "")
    return result


def normalized_fact_support_text(value: str) -> str:
    return re.sub(
        r"[\s，,。；;！？!?：:\"'“”‘’（）()【】\[\]]+",
        "",
        normalize_support_text(value),
    )


def source_supports_fact_clause(clause: str, source_text: str) -> bool:
    """Conservatively accept direct source wording or closed numeric semantics."""

    if normalized_fact_support_text(clause) in normalized_fact_support_text(
        source_text
    ):
        return True
    numeric_details = tuple(
        token
        for token in PROTECTED_SOURCE_DETAIL_PATTERN.findall(clause)
        if normalize_numeric_detail(token) is not None
    )
    if not numeric_details or not all(
        protected_detail_is_supported(token, source_text) for token in numeric_details
    ):
        return False
    context_aliases = {
        "价格": ("价格", "售价", '"fact_kind":"PRICE"'),
        "库存": ("库存", "现货", "可售", '"fact_kind":"STOCK"'),
        "尺码": ("尺码", "规格", "身高", '"fact_kind":"SPECIFICATION"'),
        "日期": ("日期", "截至", "时效", '"fact_kind":"TIME_POINT"'),
    }
    required_aliases = [
        aliases
        for marker, aliases in context_aliases.items()
        if marker in clause
        or (marker == "价格" and "售价" in clause)
        or (marker == "库存" and any(value in clause for value in aliases[:3]))
        or (marker == "尺码" and any(value in clause for value in aliases[:3]))
        or (marker == "日期" and "截至" in clause)
    ]
    normalized_source = normalize_support_text(source_text)
    return all(
        any(alias.lower() in normalized_source for alias in aliases)
        for aliases in required_aliases
    )


class RuntimeContractError(ValueError):
    """Fail-closed runtime error whose raw value is never shown to users."""


class Package7Runtime:
    """Coordinate persistence, retrieval, planning and candidate validation."""

    def __init__(
        self,
        repository: RuntimeRepository,
        plan_store: SqlAlchemyPlanStore,
        retrieval: RuntimeBrandFactRetrievalService,
    ) -> None:
        self.repository = repository
        expression = LightExpressionService(
            REPOSITORY_ROOT,
            plan_store=plan_store,
            expression_profile_resolver=self._resolve_runtime_profile,
        )
        self.adapter = FactAwarePlanAdapter(
            retrieval,
            expression,
            Path("runtime://package7/identity"),
            trusted_context_factory=self._trusted_context,
            expression_profile_resolver=self._expression_profile,
        )
        topic_doc = yaml.safe_load(TOPIC_PATH.read_text(encoding="utf-8"))
        categories = topic_doc["topic_product_mapping"]["categories"]
        self.topic_by_label = {
            str(row["display_name"]): copy.deepcopy(row) for row in categories
        }
        canonical_topics = copy.deepcopy(self.topic_by_label)
        self.product_labels = {
            str(row["content_product_id"]): str(row["internal_label"])
            for row in topic_doc["topic_product_mapping"]["internal_products"]
        }
        capability_doc = yaml.safe_load(CAPABILITY_PATH.read_text(encoding="utf-8"))
        if not isinstance(capability_doc, dict):
            raise RuntimeContractError("Content capability mapping is invalid")
        public_topics = capability_doc.get("public_topics")
        content_formats = capability_doc.get("content_formats")
        content_products = capability_doc.get("content_products")
        if (
            not isinstance(public_topics, list)
            or not isinstance(content_formats, list)
            or not isinstance(content_products, list)
        ):
            raise RuntimeContractError("Content capability mapping is incomplete")
        self.user_product_labels: dict[str, str] = {}
        self.product_search_aliases: dict[str, tuple[str, ...]] = {}
        for row in content_products:
            if not isinstance(row, dict):
                raise RuntimeContractError("Content product display mapping is invalid")
            product_id = str(row.get("content_product_id", ""))
            display_name = str(row.get("display_name", ""))
            aliases = row.get("search_aliases")
            if (
                product_id not in self.product_labels
                or not display_name
                or not isinstance(aliases, list)
                or not aliases
                or any(not isinstance(value, str) or not value for value in aliases)
            ):
                raise RuntimeContractError("Content product display mapping is invalid")
            self.user_product_labels[product_id] = display_name
            self.product_search_aliases[product_id] = tuple(aliases)
        if set(self.user_product_labels) != set(self.product_labels):
            raise RuntimeContractError("Content product display mapping is incomplete")
        for row in public_topics:
            if not isinstance(row, dict):
                raise RuntimeContractError("Public topic mapping is invalid")
            label = str(row.get("display_name", ""))
            product_ids = row.get("internal_product_ids")
            if (
                not label
                or not isinstance(product_ids, list)
                or not product_ids
                or not set(map(str, product_ids)).issubset(self.product_labels)
            ):
                raise RuntimeContractError("Public topic mapping is invalid")
            legacy_labels = row.get("legacy_topic_labels")
            if not isinstance(legacy_labels, list) or not legacy_labels:
                raise RuntimeContractError("Public topic mapping is invalid")
            canonical_topic_by_product: dict[str, str] = {}
            for product_id in map(str, product_ids):
                matching_categories: list[JsonObject] = []
                for legacy_label in legacy_labels:
                    category = canonical_topics.get(str(legacy_label))
                    if not isinstance(category, dict):
                        continue
                    category_products = category.get("internal_product_ids")
                    if (
                        isinstance(category_products, list)
                        and product_id in category_products
                    ):
                        matching_categories.append(category)
                if not matching_categories:
                    raise RuntimeContractError(
                        "Public topic mapping is not canonically closed"
                    )
                canonical_topic_by_product[product_id] = str(
                    matching_categories[0]["topic_category_id"]
                )
            self.topic_by_label[label] = {
                "display_name": label,
                "internal_product_ids": list(map(str, product_ids)),
                "legacy_topic_labels": list(map(str, legacy_labels)),
                "canonical_topic_category_id_by_product": canonical_topic_by_product,
            }
        if tuple(content_formats) != tuple(
            [
                "短视频",
                "图文",
                "直播内容包",
                "私域沟通内容",
                "门店线下物料",
                "培训与门店话术",
                "陈列搭配",
            ]
        ):
            raise RuntimeContractError("Content format mapping drifted")
        self.content_formats = tuple(str(value) for value in content_formats)
        action_doc = json.loads(ACTION_PATH.read_text(encoding="utf-8"))
        self.action_cards = {
            str(row["action_type"]): copy.deepcopy(row)
            for row in action_doc["action_cards"]
        }
        self.unknown_action = copy.deepcopy(action_doc["unknown_action_behavior"])

    def _trusted_context(self, request: JsonObject) -> TrustedUpstreamContext:
        principal_id = str(request["trusted_scope"]["login_principal_id"])
        runtime_principal = self.repository.principal_by_id(principal_id)
        if runtime_principal is None or runtime_principal.status != "ACTIVE":
            raise RuntimeContractError("Trusted principal is unavailable")
        root = self.repository.identity_authority(runtime_principal.tenant_id)
        tenant = root["tenant"]
        principal = next(
            row
            for row in root["login_principals"]
            if row["principal_id"] == principal_id
        )
        allowed = set(principal["allowed_content_account_ids"])
        accounts: dict[str, AccountAuthority] = {}
        for raw in root["content_accounts"]:
            if raw["account_id"] not in allowed:
                continue
            accounts[str(raw["account_id"])] = AccountAuthority(
                account_id=str(raw["account_id"]),
                organization_id=str(raw["organization_id"]),
                store_id=raw.get("store_id"),
                maker_role_ids=tuple(str(value) for value in raw["maker_role_ids"]),
                confirmation_routes=(),
            )
        return TrustedUpstreamContext(
            tenant_id=str(tenant["tenant_id"]),
            brand_id=str(tenant["brand_id"]),
            login_principal_id=str(principal["principal_id"]),
            accounts=accounts,
            authorization_grants={
                str(row["authorization_id"]): copy.deepcopy(row)
                for row in root["authorization_grants"]
            },
            subject_confirmations={},
            trusted_requirement_digests=frozenset(
                {digest_plan_object(request["confirmed_requirement"])}
            ),
            trusted_fragment_digests=frozenset(
                digest_plan_object(row) for row in request["scoped_retrieval_fragments"]
            ),
            trusted_fact_digests=frozenset(
                digest_plan_object(row) for row in request["verified_precise_facts"]
            ),
            simulation_only=True,
            publish_allowed=False,
            source_digest=digest_object(root),
        )

    def _expression_profile(
        self,
        task: ServerConfirmedProductionTask,
        retrieval: JsonObject,
    ) -> JsonObject:
        del task
        scope = retrieval["resolved_scope"]
        profile = self._brand_profile_for_account(str(scope["brand_id"]))
        return {
            "resolution_authority": "SERVER_TRUSTED_UPSTREAM",
            "requested_profile_ref": None,
            "resolved_profile_ref": profile["profile_ref"],
            "resolution_mode": profile["resolution_mode"],
            "tenant_id": scope["tenant_id"],
            "content_account_id": scope["content_account_id"],
        }

    def _resolve_runtime_profile(
        self,
        supplied: JsonObject,
        context: TrustedUpstreamContext,
        neutral_profile: JsonObject,
    ) -> JsonObject:
        profile = self._brand_profile_for_account(context.brand_id)
        if profile.get("tenant_specific") is not True:
            return copy.deepcopy(neutral_profile)
        if (
            profile.get("tenant_id") != context.tenant_id
            or profile.get("brand_id") != context.brand_id
            or profile.get("profile_ref") != supplied.get("resolved_profile_ref")
        ):
            raise RuntimeContractError("Brand profile scope mismatch")
        return copy.deepcopy(profile)

    def prepare(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        *,
        trusted_scope: TrustedDatabaseScope,
    ) -> JsonObject:
        """Prepare one request inside a server-issued browser-session boundary."""

        if (
            trusted_scope.principal_id != principal_id
            or not isinstance(trusted_scope.browser_session_id, str)
            or not trusted_scope.browser_session_id
        ):
            raise RuntimeContractError("Trusted request scope is incomplete")
        with (
            trusted_database_scope(trusted_scope),
            runtime_browser_session(trusted_scope.browser_session_id),
        ):
            return self._prepare_scoped(request, principal_id)

    def _prepare_scoped(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
    ) -> JsonObject:
        try:
            principal, account = self.repository.require_active_scope_by_display_name(
                principal_id,
                request.account_display_name,
            )
        except ValueError:
            return self._plain_action("REQUEST_AUTHORIZATION")
        request_scope = current_trusted_database_scope()
        if request_scope.account_id != account.account_id:
            raise RuntimeContractError("Trusted account scope mismatch")

        if request.operation == "普通聊天":
            return self._start_chat_run(
                request, principal_id, account.account_id, inspiration=False
            )
        if request.operation == "找灵感":
            return self._start_chat_run(
                request, principal_id, account.account_id, inspiration=True
            )
        if request.operation == "确认制作":
            if (
                request.topic_label is None
                or request.selected_content_product_id is None
            ):
                return self._start_chat_run(
                    request,
                    principal_id,
                    account.account_id,
                    inspiration=True,
                )
            account_payload = {
                **copy.deepcopy(account.payload),
                "tenant_id": account.tenant_id,
                "brand_id": account.brand_id,
                "account_id": account.account_id,
                "organization_id": account.organization_id,
                "store_id": account.store_id,
            }
            return self._prepare_creation(request, principal_id, account_payload)
        if request.operation == "选择候选":
            try:
                chosen = self.repository.select_candidate(
                    principal_id,
                    account.account_id,
                    int(request.candidate_number or 0),
                )
            except (KeyError, ValueError):
                return self._failure_result("AUTHORIZATION_OR_SCOPE_BLOCK", None)
            return {
                "response_kind": "DIRECT",
                "user_visible_text": f"已选择第{chosen.ordinal}份候选。需要时可以继续说想修改哪里。",
                "ui_state": "result",
                "candidates": self._candidate_workbench(
                    self.repository.latest_candidates(
                        principal_id,
                        account.account_id,
                    )
                ),
            }
        if request.operation == "局部修改":
            try:
                return self._prepare_revision(request, principal_id, account.account_id)
            except (KeyError, ValueError):
                return self._failure_result("AUTHORIZATION_OR_SCOPE_BLOCK", None)
        if request.operation == "查看上一版":
            return self._previous_version(principal_id, account.account_id)
        if request.operation == "导出":
            return self._export_selected(principal_id, account.account_id)
        if request.operation == "查看来源":
            return self._source_lookup(principal_id, account.account_id)
        if request.operation == "提交反馈":
            selected = self.repository.selected_candidate(
                principal_id, account.account_id
            )
            context = (
                {}
                if selected is None
                else self.repository.requirement_context_for_run(selected.run_id)
            )
            feedback_id = self.repository.save_feedback(
                principal_id=principal_id,
                account_id=account.account_id,
                candidate_id=None if selected is None else selected.candidate_id,
                requirement_id=(
                    None
                    if selected is None
                    else self.repository.requirement_id_for_run(selected.run_id)
                ),
                role_id=request.speaker_role_id or context.get("speaker_role_id"),
                storyline_id=request.storyline_id or context.get("storyline_id"),
                column_id=request.column_id or context.get("column_id"),
                previous_content_ref=(
                    request.previous_content_ref or context.get("previous_content_ref")
                ),
                fact_refs=[] if selected is None else list(selected.used_fact_refs),
                material_refs=[]
                if selected is None
                else list(selected.used_material_refs),
                short_reason=request.message,
            )
            return {
                "response_kind": "DIRECT",
                "user_visible_text": "反馈已记录。这里只保存必要的简短原因。",
                "internal_feedback_ref": feedback_id,
            }
        raise RuntimeContractError("Unknown operation")

    def portal_options(self, principal_id: str) -> JsonObject:
        principal = self.repository.principal_by_id(principal_id)
        if principal is None or principal.status != "ACTIVE":
            raise RuntimeContractError("Unknown portal principal")
        principal_payload = copy.deepcopy(principal.payload)
        identity = {
            "principal_id": principal.principal_id,
            "login_principal_id": principal.principal_id,
            "display_name": principal_payload.get(
                "display_name",
                principal_payload.get("principal_display_name", principal.username),
            ),
            "login_display_name": principal_payload.get(
                "display_name",
                principal_payload.get("principal_display_name", principal.username),
            ),
            "business_role_id": principal_payload.get("business_role_id"),
            "business_role_name": principal_payload.get("business_role_name", ""),
            "employee_role": principal_payload.get("business_role_name", ""),
            "organization_scope_ids": list(
                principal_payload.get("organization_scope_ids", [])
            ),
            "workspace_kind": principal_payload.get(
                "workspace_kind", "CONTENT_CREATOR"
            ),
        }
        if identity["workspace_kind"] == "ENTERPRISE_ADMIN":
            return {
                "workspace_kind": "ENTERPRISE_ADMIN",
                "identity": identity,
                "content_accounts": [],
                "accounts": [],
                "management": self.repository.account_management_matrix(principal_id),
                "simulation_only": True,
                "publish_allowed": False,
            }
        allowed = set(principal.allowed_account_ids)
        accounts = [
            account
            for account in self.repository.all_accounts()
            if account.status == "ACTIVE" and account.account_id in allowed
        ]
        authority = self.repository.identity_authority(principal.tenant_id)
        organization_names = {
            str(row["organization_id"]): str(row.get("display_name", ""))
            for row in authority["organizations"]
        }
        direction_fallbacks = {
            "HEADQUARTERS_BRAND": ["品牌为什么存在", "真实生活里的衣服", "商品为什么这样设计", "团队幕后"],
            "FOUNDER": ["创业经历", "价值判断", "重要选择", "工作日常"],
            "HEADQUARTERS_PROFESSIONAL_PERSONA": ["岗位日常", "专业判断", "产品怎样改变", "真实工作过程"],
            "PROVINCIAL_AGENT": ["本地市场", "区域门店协作", "培训服务", "区域经营"],
            "HEADQUARTERS_DIRECT_STORE": ["新品到店", "顾客常问", "陈列变化", "总部活动落地", "店员日常"],
            "FRANCHISE_STORE": ["店里今天", "商品搭配", "顾客常问", "到店陈列", "店主人设"],
        }
        audience_fallbacks = {
            "HEADQUARTERS_BRAND": "关注品牌理念、商品与真实团队故事的人",
            "FOUNDER": "关注创业判断、品牌价值与真实工作过程的人",
            "HEADQUARTERS_PROFESSIONAL_PERSONA": "希望理解商品与专业工作过程的人",
            "PROVINCIAL_AGENT": "关注本地市场、门店服务与区域经营的人",
            "HEADQUARTERS_DIRECT_STORE": "关注到店体验、商品搭配与门店日常的人",
            "FRANCHISE_STORE": "关注本地门店、商品选择与店主日常的人",
        }
        family_labels = {
            "HEADQUARTERS_BRAND": "总部品牌账号",
            "FOUNDER": "创始人账号",
            "HEADQUARTERS_PROFESSIONAL_PERSONA": "总部专业人设账号",
            "PROVINCIAL_AGENT": "省级代理商账号",
            "HEADQUARTERS_DIRECT_STORE": "总部直营门店账号",
            "FRANCHISE_STORE": "加盟门店账号",
        }
        roles_by_account: dict[str, list[str]] = {}
        storylines: dict[str, JsonObject] = {}
        columns: dict[str, JsonObject] = {}
        account_projections: list[JsonObject] = []
        for account in accounts:
            profile = self._brand_profile_for_account(account.brand_id)
            payload = copy.deepcopy(account.payload)
            family = str(payload.get("account_family", ""))
            role_cards = {
                str(row["account_id"]): row
                for row in profile.get("account_role_cards", [])
                if isinstance(row, dict) and isinstance(row.get("account_id"), str)
            }
            roles = {
                str(row["role_id"]): row
                for row in profile.get("principal_roles", [])
                if isinstance(row, dict) and isinstance(row.get("role_id"), str)
            }
            role_card = role_cards.get(account.account_id)
            if isinstance(role_card, dict):
                role = roles.get(str(role_card.get("default_role_id")))
                if isinstance(role, dict):
                    roles_by_account[account.display_name] = [str(role["display_name"])]
            if account.display_name not in roles_by_account:
                roles_by_account[account.display_name] = [
                    str(
                        payload.get("persona_display_name")
                        or principal_payload.get("business_role_name")
                        or "账号使用人"
                    )
                ]
            persona_type = str(payload.get("persona_type", ""))
            configured_directions = recommended_directions(family, persona_type)
            directions = payload.get("directions")
            if family == "HEADQUARTERS_PROFESSIONAL_PERSONA" and configured_directions:
                directions = configured_directions
            elif not isinstance(directions, list) or not 3 <= len(directions) <= 5:
                directions = configured_directions or direction_fallbacks.get(
                    family,
                    direction_fallbacks["HEADQUARTERS_PROFESSIONAL_PERSONA"],
                )
            account_projections.append(
                {
                    "display_name": account.display_name,
                    "outward_account_name": payload.get(
                        "outward_account_name", account.display_name
                    ),
                    "account_family": family,
                    "account_family_display_name": payload.get(
                        "account_family_display_name",
                        family_labels.get(family, "内容账号"),
                    ),
                    "persona_type": persona_type,
                    "persona_display_name": payload.get(
                        "persona_display_name",
                        payload.get(
                            "persona_type", roles_by_account[account.display_name][0]
                        ),
                    ),
                    "organization_display_name": organization_names.get(
                        account.organization_id, ""
                    ),
                    "directions": list(map(str, directions)),
                    "primary_audience": payload.get(
                        "primary_audience",
                        audience_fallbacks.get(
                            family,
                            audience_fallbacks[
                                "HEADQUARTERS_PROFESSIONAL_PERSONA"
                            ],
                        ),
                    ),
                    "recommended_content_format": payload.get(
                        "recommended_content_format", "短视频"
                    ),
                }
            )
            for storyline in profile.get("storylines", []):
                if isinstance(storyline, dict) and isinstance(
                    storyline.get("storyline_id"), str
                ):
                    storylines[str(storyline["storyline_id"])] = storyline
            for column in profile.get("columns", []):
                if isinstance(column, dict) and isinstance(
                    column.get("column_id"), str
                ):
                    columns[str(column["column_id"])] = column
        return {
            "workspace_kind": "CONTENT_CREATOR",
            "identity": identity,
            "accounts": account_projections,
            "content_accounts": [account.display_name for account in accounts],
            "roles_by_account": roles_by_account,
            "storylines": [
                str(row["display_name"])
                for row in sorted(
                    storylines.values(), key=lambda item: str(item["storyline_id"])
                )
            ],
            "columns_by_storyline": {
                str(storyline["display_name"]): [
                    str(column["display_name"])
                    for column in columns.values()
                    if column.get("storyline_id") == storyline.get("storyline_id")
                ]
                for storyline in storylines.values()
            },
            "topics": sorted(self.topic_by_label),
            "content_products": [
                {
                    "display_name": self.user_product_labels[product_id],
                    "search_aliases": list(self.product_search_aliases[product_id]),
                }
                for product_id in sorted(self.user_product_labels)
            ],
            "platforms": ["抖音", "视频号", "小红书", "公众号或图文", "其他"],
            "durations": [
                "15秒左右",
                "30秒左右",
                "60秒左右",
                "1至3分钟",
                "5至15分钟",
                "15至30分钟",
                "30至60分钟",
                "由系统建议",
            ],
            "feelings": [
                "真实记录",
                "专业讲明白",
                "生活分享",
                "搭配演示",
                "门店日常",
                "情绪故事",
                "质感画面",
                "由系统建议",
            ],
            "content_formats": list(self.content_formats),
            "organization_levels": ["品牌总部", "区域组织", "门店"],
            "content_identities": [
                "品牌价值身份",
                "专业身份",
                "区域经营身份",
                "门店关系身份",
                "商品或栏目身份",
            ],
            "long_term_storylines": [
                "品牌为什么存在",
                "衣服如何服务真实生活",
                "商品为什么这样设计",
                "一群人如何把品牌做好",
            ],
            "content_directions": [
                "品牌与价值叙事",
                "商品专业解释",
                "真实组织与幕后",
                "消费者生活与穿搭判断",
                "活动、交易与关系承接",
            ],
            "business_goals": [
                "品牌认知",
                "商品理解",
                "建立信任",
                "引发咨询",
                "到店",
                "复购",
                "招商",
                "招聘",
            ],
            "expression_methods": [
                "故事",
                "问答",
                "对比",
                "观察",
                "幕后",
                "演示",
                "纪实",
            ],
            "material_kinds": [
                "一个想法",
                "一段故事或概要",
                "商品或活动事实",
                "图片或视频",
                "什么都没有",
            ],
            "simulation_only": True,
            "publish_allowed": False,
        }

    def classification_options(self, topic_label: str | None) -> list[JsonObject]:
        if topic_label is not None:
            topic = self.topic_by_label.get(topic_label)
            if topic is None:
                return []
            return [
                {
                    "content_product_id": product_id,
                    "internal_label": self.product_labels[product_id],
                    "user_visible_label": self.user_product_labels[product_id],
                    "search_aliases": list(self.product_search_aliases[product_id]),
                    "public_topic_label": topic_label,
                }
                for product_id in topic["internal_product_ids"]
            ]

        options_by_product: dict[str, JsonObject] = {}
        for public_topic_label, topic in self.topic_by_label.items():
            if "canonical_topic_category_id_by_product" not in topic:
                continue
            for product_id in topic["internal_product_ids"]:
                options_by_product.setdefault(
                    product_id,
                    {
                        "content_product_id": product_id,
                        "internal_label": self.product_labels[product_id],
                        "user_visible_label": self.user_product_labels[product_id],
                        "search_aliases": list(self.product_search_aliases[product_id]),
                        "public_topic_label": public_topic_label,
                    },
                )
        return [options_by_product[product_id] for product_id in sorted(options_by_product)]

    def validate_classification_choice(
        self,
        selected_content_product_id: str | None,
        candidates: list[JsonObject],
    ) -> JsonObject | None:
        if selected_content_product_id is None:
            return None
        for candidate in candidates:
            if candidate.get("content_product_id") != selected_content_product_id:
                continue
            public_topic_label = candidate.get("public_topic_label")
            if not isinstance(public_topic_label, str):
                continue
            topic = self.topic_by_label.get(public_topic_label)
            if topic is None or selected_content_product_id not in topic[
                "internal_product_ids"
            ]:
                continue
            return {
                "selected_content_product_id": selected_content_product_id,
                "topic_label": public_topic_label,
            }
        return None

    def _start_chat_run(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        account_id: str,
        *,
        inspiration: bool,
    ) -> JsonObject:
        if inspiration:
            instruction = (
                "结合用户本次输入给出三种真正不同、可以直接选择的通俗内容角度，不使用任何品牌私有事实。"
                "reply字段先严格逐行输出三行：方向1｜短标题｜一句说明、方向2｜短标题｜一句说明、"
                "方向3｜短标题｜一句说明；角度必须具体回应当前输入，不能复述固定首页方向。"
            )
            if request.series_mode == "SERIES":
                instruction += (
                    "随后严格逐行输出：第1集｜短标题｜本集讲什么、第2集｜短标题｜本集讲什么、"
                    "第3集｜短标题｜本集讲什么；三集主题连续且内容彼此不同。"
                )
            instruction += "最后只追问一个真正影响下一步的关键问题，不要一次抛出整张表单。"
        else:
            instruction = "自然回应用户；不要声称任何企业事实，不读取或猜测品牌私有信息。"
        instruction += (
            "conversation_context只用于理解本账号内用户的延续意图，"
            "不能成为品牌事实、授权、资料或内容引用来源。"
            "当前消息出现继续、刚才、上一轮等延续表达时，必须先读取其中已接受的用户表达和回复，"
            "直接回答可由上下文确定的问题，不得要求用户重复提供。"
        )
        conversation_context = self.repository.recent_chat_turns(
            principal_id=principal_id,
            account_id=account_id,
            limit=6,
        )
        run_id = self._new_run_id(
            principal_id, account_id, request.operation, request.message
        )
        prompt = {
            "system": instruction,
            "user_message": request.message,
            "conversation_context": list(conversation_context),
            "output_contract": {
                "server_bound_contract_version": AUTHOR_CONTRACT_VERSION,
                "author_fields": {"reply": "非空字符串"},
            },
        }
        self.repository.start_model_run(
            run_id=run_id,
            principal_id=principal_id,
            account_id=account_id,
            operation=request.operation,
            plan_ref=None,
            prompt_digest=digest_object(prompt),
            payload={"prompt": prompt, "private_retrieval_performed": False},
        )
        return {
            "response_kind": "MODEL_REQUIRED",
            "run_id": run_id,
            "author_prompt": prompt,
        }

    def _prepare_creation(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        account: JsonObject,
    ) -> JsonObject:
        topic = self.topic_by_label.get(str(request.topic_label))
        product_id = str(request.selected_content_product_id)
        if topic is None or product_id not in topic["internal_product_ids"]:
            topic = next(
                (
                    candidate
                    for candidate in self.topic_by_label.values()
                    if product_id in candidate["internal_product_ids"]
                ),
                None,
            )
        if topic is None:
            return self._plain_action("COLLECT_MATERIAL")
        if self._explicit_required_object_missing(request):
            return self._missing_object_result()
        profile = self._brand_profile_for_account(str(account["brand_id"]))
        role_card = self._role_card(
            profile,
            account,
            request.speaker_role_id,
            request.speaker_role_name,
        )
        storyline = self._storyline(
            profile, request.storyline_id, request.storyline_name
        )
        column = self._column(
            profile,
            request.column_id,
            request.column_name,
            str(storyline["storyline_id"]),
        )
        if (
            request.previous_content_ref is not None
            and not self.repository.candidate_belongs_to_account(
                request.previous_content_ref,
                principal_id,
                str(account["account_id"]),
            )
        ):
            return self._plain_action("BLOCK")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        requirement_id = f"REQ-{digest_object([principal_id, account['account_id'], request.message, now])[:20].upper()}"
        precise_queries = self._precise_fact_queries(request, account)
        requirement = {
            "requirement_id": requirement_id,
            "requirement_version": 1,
            "status": "CONFIRMED",
            "plain_language_summary": request.message,
            "tenant_id": account["tenant_id"],
            "content_account_id": account["account_id"],
            "topic_category_id": topic.get(
                "canonical_topic_category_id_by_product", {}
            ).get(product_id, topic.get("topic_category_id")),
            "target_platform": request.target_platform,
            "confirmed_by_principal_id": principal_id,
            "confirmed_at": now,
            "selected_internal_content_product_id": product_id,
            "primary_audience": request.primary_audience,
            "required_precise_fact_kinds": sorted(
                {str(row["fact_kind"]) for row in precise_queries}
            ),
            "content_goal": request.content_goal or request.message,
            "key_takeaway": request.key_takeaway or request.message,
            "speaker_role_id": role_card["role_id"],
            "speaker_role_display_name": role_card["display_name"],
            "storyline_id": storyline["storyline_id"],
            "storyline_display_name": storyline["display_name"],
            "column_id": column["column_id"],
            "column_display_name": column["display_name"],
            "previous_content_ref": request.previous_content_ref,
            "localization_allowed": request.localization_allowed,
            "duration_label": request.duration_label,
            "expression_feeling": request.expression_feeling,
            "content_format": request.content_format,
            "series_mode": request.series_mode,
            "episode_index": request.episode_index,
            "organization_level": request.organization_level,
            "content_identity": request.content_identity,
            "long_term_storyline": request.long_term_storyline,
            "content_direction": request.content_direction,
            "business_goal": request.business_goal,
            "expression_method": request.expression_method,
            "existing_material_kinds": list(request.existing_material_kinds),
            "user_material_refs": list(request.user_material_refs),
        }
        self.repository.save_requirement(
            requirement, principal_id, str(account["account_id"])
        )
        task = ServerConfirmedProductionTask(
            server_task_ref=f"server-task://{requirement_id}",
            authority_source=SERVER_TASK_AUTHORITY,
            intent=START_CREATION,
            request_id=f"REQUEST-{requirement_id}",
            principal_id=principal_id,
            content_account_id=str(account["account_id"]),
            query_at=now,
            confirmed_requirement=requirement,
            retrieval_query_text=request.message,
            precise_fact_queries=tuple(precise_queries),
            requested_high_level_mode_refs=(
                "expression-mode://documentary-observation/v1",
            ),
            client_soft_preferences={
                "rhythm": self._rhythm_for_duration(request.duration_label),
                "emotional_intensity": self._intensity_for_feeling(
                    request.expression_feeling
                ),
            },
            output_requirements={
                "target_platform": request.target_platform,
                "required_candidate_count": 3,
                "audience_surface_fields": ["title", "body", "execution_payload"],
            },
        )
        result = self.adapter.prepare(task)
        if result.get("object_type") != "LIGHT_CONTENT_PLAN":
            return self._plain_action(str(result.get("action_type", "BLOCK")))
        plan_ref = str(result["composition_plan_ref"])
        materials = self.adapter.author_materials(
            plan_ref, self._access(principal_id, str(account["account_id"]))
        )
        return self._start_author_run(
            request,
            principal_id,
            str(account["account_id"]),
            result,
            materials,
            profile,
            role_card,
            storyline,
            column,
        )

    def _prepare_revision(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        account_id: str,
    ) -> JsonObject:
        selected = (
            self.repository.selected_candidate(principal_id, account_id)
            if request.candidate_number is None
            else self.repository.select_candidate(
                principal_id,
                account_id,
                request.candidate_number,
            )
        )
        if selected is None:
            raise KeyError("No selected candidate exists")
        if not selected.plan_ref:
            return self._plain_action("BLOCK")
        plan_record = self.adapter.expression_service.store.get(selected.plan_ref)
        if plan_record is None:
            return self._plain_action("BLOCK")
        materials = self.adapter.author_materials(
            selected.plan_ref, self._access(principal_id, account_id)
        )
        original_run = self.repository.model_run(selected.run_id)
        task_brief = (
            {}
            if original_run is None
            else copy.deepcopy(original_run.payload.get("task_brief", {}))
        )
        prompt = self._author_prompt(
            plan_record.plan,
            materials,
            task_brief=task_brief,
            revision_instruction=request.message,
            selected_candidate=selected.candidate_payload,
        )
        run_id = self._new_run_id(
            principal_id, account_id, request.operation, request.message
        )
        self.repository.start_model_run(
            run_id=run_id,
            principal_id=principal_id,
            account_id=account_id,
            operation=request.operation,
            plan_ref=selected.plan_ref,
            prompt_digest=digest_object(prompt),
            payload={
                "prompt": prompt,
                "source_candidate_id": selected.candidate_id,
                "task_brief": task_brief,
            },
        )
        return {
            "response_kind": "MODEL_REQUIRED",
            "run_id": run_id,
            "author_prompt": prompt,
        }

    def prepare_preserved_output_correction(
        self,
        source_run_id: str,
        model_output_b64: str,
        *,
        trusted_scope: TrustedDatabaseScope,
    ) -> JsonObject:
        """Reject write-back from any historical or rejected author contract."""

        del source_run_id, model_output_b64, trusted_scope
        raise RuntimeContractError(
            "Historical and rejected outputs are read-only replay evidence"
        )

    def _start_author_run(
        self,
        request: BridgePrepareRequest,
        principal_id: str,
        account_id: str,
        plan: JsonObject,
        materials: JsonObject,
        profile: JsonObject,
        role_card: JsonObject,
        storyline: JsonObject,
        column: JsonObject,
    ) -> JsonObject:
        previous_context = (
            None
            if request.previous_content_ref is None
            else self.repository.candidate_context(
                request.previous_content_ref,
                principal_id,
                account_id,
            )
        )
        previous_outline = (
            previous_context.get("series_outline", [])
            if isinstance(previous_context, dict)
            else []
        )
        if request.series_mode != "SERIES":
            series_outline: list[JsonObject] = []
        elif isinstance(previous_outline, list) and len(previous_outline) == 3:
            series_outline = copy.deepcopy(previous_outline)
        else:
            series_outline = self._series_outline(
                request.message, request.content_direction
            )
        task_brief = {
            "confirmed_user_request": request.message,
            "public_topic": str(request.topic_label),
            "content_goal": request.content_goal or request.message,
            "key_takeaway": request.key_takeaway or request.message,
            "speaker_role": role_card["display_name"],
            "speaker_boundary": role_card["boundary"],
            "storyline": storyline["display_name"],
            "storyline_purpose": storyline["purpose"],
            "column": column["display_name"],
            "previous_content_ref_present": request.previous_content_ref is not None,
            "previous_content_context": previous_context,
            "localization_allowed": request.localization_allowed,
            "target_platform": request.target_platform,
            "duration_label": request.duration_label,
            "expression_feeling": request.expression_feeling,
            "content_format": request.content_format,
            "series_mode": request.series_mode,
            "series_outline": series_outline,
            "episode_index": request.episode_index,
            "primary_audience": request.primary_audience,
            "organization_level": request.organization_level,
            "content_identity": request.content_identity,
            "long_term_storyline": request.long_term_storyline,
            "content_direction": request.content_direction,
            "business_goal": request.business_goal,
            "expression_method": request.expression_method,
            "existing_material_kinds": list(request.existing_material_kinds),
            "scope_identity_only_authoring_allowed": self._scope_identity_only_request(
                request
            ),
            "brand_guidance": self._public_brand_guidance(profile),
        }
        prompt = self._author_prompt(plan, materials, task_brief=task_brief)
        run_id = self._new_run_id(
            principal_id, account_id, request.operation, request.message
        )
        self.repository.start_model_run(
            run_id=run_id,
            principal_id=principal_id,
            account_id=account_id,
            operation=request.operation,
            plan_ref=str(plan["composition_plan_ref"]),
            prompt_digest=digest_object(prompt),
            payload={
                "prompt": prompt,
                "requirement_summary": request.message,
                "task_brief": task_brief,
            },
        )
        return {
            "response_kind": "MODEL_REQUIRED",
            "run_id": run_id,
            "author_prompt": prompt,
        }

    @staticmethod
    def _series_outline(
        user_request: str,
        content_direction: str | None,
    ) -> list[JsonObject]:
        subject = (content_direction or user_request).strip()[:80]
        return [
            {
                "episode_index": 1,
                "title": "先把问题讲清",
                "summary": f"从真实场景切入，讲清“{subject}”为什么值得关注。",
            },
            {
                "episode_index": 2,
                "title": "再看专业判断",
                "summary": f"换到具体选择与工作过程，展开“{subject}”背后的判断。",
            },
            {
                "episode_index": 3,
                "title": "最后落到行动",
                "summary": f"用不同场景收束“{subject}”，给出可以继续观察或尝试的方向。",
            },
        ]

    @staticmethod
    def _author_prompt(
        plan: JsonObject,
        materials: JsonObject,
        *,
        task_brief: JsonObject,
        revision_instruction: str | None = None,
        selected_candidate: JsonObject | None = None,
    ) -> JsonObject:
        content_format = str(task_brief.get("content_format", "短视频"))
        if content_format not in {
            "短视频",
            "图文",
            "直播内容包",
            "私域沟通内容",
            "门店线下物料",
            "培训与门店话术",
            "陈列搭配",
        }:
            raise RuntimeContractError("Unknown content format")
        author_materials = Package7Runtime._author_material_projection(
            materials,
            scope_identity_only=bool(
                task_brief.get("scope_identity_only_authoring_allowed")
            ),
        )
        selected_projection = None
        if isinstance(selected_candidate, dict):
            surfaces = selected_candidate.get("candidate_user_visible_surfaces")
            selected_projection = (
                copy.deepcopy(surfaces) if isinstance(surfaces, dict) else None
            )
        return cast(
            JsonObject,
            Package7Runtime._sanitize_author_projection(
                {
                    "system": (
                        "你是受控内容作者，只负责把已给任务和资料写成内容。返回严格JSON，不要Markdown。"
                        "task_brief是用户已确认的任务：confirmed_user_request、public_topic、品牌层级、"
                        "账号身份、受众、平台、时长、成品形式和用户要求的场景都必须原样遵守，"
                        "不得把事件、人物、商品或任务对象换成另一件事。童装或儿童任务只能使用儿童、"
                        "家长与童装语境，不得漂移到成人身材、面试或成人女装。"
                        "用户明确要求标注‘演绎’时，必须在正文、分镜字幕或其他成品可见位置标注；"
                        "用户未要求时不要自行添加演绎声明或免责声明。"
                        "一次写2至3份候选；根据题材自然采用纪实、故事、问答、对比、观察或演示，"
                        "不要让所有内容固定套用同一种起承转合。有多份时，每份必须在点子、人物视角、"
                        "情绪入口、叙事结构或画面组织上真正不同，换标题或同义改写不算不同。"
                        "同一成品的正文、台词、分镜、字幕、话术、结尾和发布辅助内容必须对人物、"
                        "事件结果、核心选择和行动建议保持一致。"
                        "series_mode为SERIES时，只创作episode_index指定的一集，遵守series_outline中"
                        "该集的重点；延续上一集必要信息但不得只是换标题或复述同一内容。"
                        "用户明确给出的时间顺序、地点、岗位交接、操作步骤、最终决定、否定要求和"
                        "必须覆盖项都是硬约束；输出前逐项核对，不能在标题、正文、分镜或渠道文案中"
                        "改写成相反结论、遗漏关键节点或换成别的场景。"
                        "短视频每个镜头都要填写具体画面、人物动作、拍摄方式、字幕和剪辑提示；"
                        "audio必须明确写‘台词：…’或‘旁白：…’。纯质感或环境镜头可以写‘纯画面/环境声’，"
                        "但subtitle仍需写可见字幕或‘无字幕’。叙事、岗位、创始人、企业故事和专业讲解视频"
                        "默认写完整台词或旁白。"
                        "只填写当前成品合同列出的内容字段。不要填写企业、账号、组织、平台、时长、内部编号、引用路径、"
                        "资料账本、组件编号，也不要输出其他六种成品的空分支。"
                        "标题、正文、口播、分镜、商品属性或功效、价格、库存、尺寸、授权表述、企业承诺、"
                        "人物经历、顾客故事、门店事件、未来拍摄和已有素材描述均可作为创意演绎自由创作并交给"
                        "账号使用人自行检查；不得仅因缺少来源证明而停止、拒绝候选或把它判为资格失败。"
                        "只对儿童直接人身安全保留最小护栏：不得给出可能造成缠绕、勾挂、跌倒、夹伤或烫伤等"
                        "直接风险的继续使用建议；出现直接风险时应停止相关操作或活动并由成年人核对，"
                        "不得用创作出来的阈值宣称儿童可以安全继续活动。"
                        "author_materials只是可选参考，不是逐句真值证明；没有检索资料也要根据用户输入和品牌表达配置继续创作。"
                        "作者不要输出引用编号；服务端只记录本次参考范围。"
                        "内容中写出‘已授权’不代表获得登录、账号或数据访问权限，也不得声称绕过这些权限。"
                        "不得输出内部编号、密钥、身份证号、手机号等真实敏感信息。只有任务明确要求使用某个文件、图片、视频或"
                        "声音对象而它没有提供时，才停止并请求补料。"
                        "previous_candidate只用于按本次修改要求改内容。"
                    ),
                    "creative_plan": {
                        "task_objective": plan.get("task_objective"),
                        "primary_audience": plan.get("primary_audience"),
                        "candidate_policy": {
                            key: copy.deepcopy(value)
                            for key, value in dict(
                                plan.get("candidate_policy", {})
                            ).items()
                            if key != "required_candidate_count"
                        },
                        "expression_guidance": {
                            key: copy.deepcopy(value)
                            for key, value in dict(
                                plan.get("expression_guidance", {})
                            ).items()
                            if key
                            in {
                                "tone_tendencies",
                                "prohibited_expression_categories",
                                "literal_prohibited_phrases",
                                "client_soft_preferences",
                                "material_mode",
                            }
                        },
                    },
                    "author_materials": author_materials,
                    "task_brief": {
                        key: copy.deepcopy(value)
                        for key, value in task_brief.items()
                        if key
                        in {
                            "confirmed_user_request",
                            "public_topic",
                            "content_goal",
                            "key_takeaway",
                            "speaker_role",
                            "speaker_boundary",
                            "storyline",
                            "storyline_purpose",
                            "column",
                            "previous_content_context",
                            "localization_allowed",
                            "target_platform",
                            "duration_label",
                            "expression_feeling",
                            "content_format",
                            "series_mode",
                            "series_outline",
                            "episode_index",
                            "primary_audience",
                            "organization_level",
                            "content_identity",
                            "long_term_storyline",
                            "content_direction",
                            "business_goal",
                            "expression_method",
                            "existing_material_kinds",
                            "brand_guidance",
                        }
                    },
                    "revision_instruction": revision_instruction,
                    "previous_candidate": selected_projection,
                    "output_contract": contract_descriptor(
                        cast(ContentFormat, content_format)
                    ),
                }
            ),
        )

    @staticmethod
    def _sanitize_author_projection(value: object) -> Any:
        """Remove server-only identifiers without altering business fact values."""

        if isinstance(value, str):
            return INTERNAL_REFERENCE_PATTERN.sub("[内部标识已隐藏]", value)
        if isinstance(value, list):
            return [Package7Runtime._sanitize_author_projection(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): Package7Runtime._sanitize_author_projection(item)
                for key, item in value.items()
            }
        return copy.deepcopy(value)

    @staticmethod
    def _author_material_projection(
        materials: JsonObject,
        *,
        scope_identity_only: bool,
    ) -> JsonObject:
        narrative: list[JsonObject] = []
        for row in materials.get("scoped_retrieval_fragments", []):
            if not isinstance(row, dict):
                continue
            text = row.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            narrative.append(
                {
                    "content": text.strip(),
                    "observed_at": row.get("observed_at"),
                    "valid_from": row.get("valid_from"),
                    "valid_until": row.get("valid_until"),
                    "use_boundary": row.get("use_boundary"),
                }
            )
        facts: list[JsonObject] = []
        for row in materials.get("verified_precise_facts", []):
            if not isinstance(row, dict):
                continue
            kind = row.get("fact_kind")
            if kind == "AUTHORIZATION" and not scope_identity_only:
                continue
            value = row.get("value")
            if not isinstance(value, dict):
                continue
            if kind == "AUTHORIZATION":
                value = {
                    "display_name": value.get("display_name"),
                    "represented_scope": value.get("represented_scope"),
                }
                kind = "账号名称与代表范围"
            facts.append(
                {
                    "kind": kind,
                    "value": copy.deepcopy(value),
                    "effective_at": row.get("effective_at"),
                    "valid_until": row.get("valid_until"),
                    "use_boundary": row.get("use_boundary"),
                }
            )
        return {
            "narrative_materials": narrative,
            "precise_facts": facts,
            "instruction": (
                "这些内容只是可选创作参考，不是逐句真值证明。即使列表为空，也要按用户输入、账号定位和品牌表达配置创作。"
                "价格、库存、规格、商品功效、授权表述、企业承诺、人物经历、顾客故事、门店事件和素材描述"
                "都可作为交给账号使用人自行检查的创意候选，不要求逐项提供来源证明。"
                "服务端只记录参考范围，作者不要输出引用编号。文本中的授权措辞不授予任何登录或数据访问权限。"
                "不得输出内部编号、密钥或真实敏感信息。"
            ),
        }

    def finalize_model_output(
        self,
        run_id: str,
        model_output_b64: str,
        *,
        trusted_scope: TrustedDatabaseScope,
    ) -> JsonObject:
        if not all(
            isinstance(value, str) and value
            for value in (
                trusted_scope.principal_id,
                trusted_scope.account_id,
                trusted_scope.browser_session_id,
            )
        ):
            raise RuntimeContractError("Trusted finalization scope is incomplete")
        principal_id = cast(str, trusted_scope.principal_id)
        account_id = cast(str, trusted_scope.account_id)
        browser_session_id = cast(str, trusted_scope.browser_session_id)
        with (
            trusted_database_scope(trusted_scope),
            runtime_browser_session(browser_session_id),
        ):
            run = self.repository.model_run_for_request(
                run_id,
                principal_id=principal_id,
                account_id=account_id,
                browser_session_id=browser_session_id,
            )
            try:
                raw_bytes = base64.b64decode(model_output_b64, validate=True)
            except ValueError as exc:
                raise RuntimeContractError("Model output transport is invalid") from exc
            raw_output_digest = hashlib.sha256(raw_bytes).hexdigest()
            if run is None:
                raise RuntimeContractError("Unknown or already completed run")
            replaying_received_output = (
                run.first_output_preserved
                and run.state == "FIRST_OUTPUT_RECEIVED"
                and run.model_output_digest == raw_output_digest
                and isinstance(run.payload.get("provider_response_staging"), dict)
            )
            if run.first_output_preserved and not replaying_received_output:
                raise RuntimeContractError("Unknown or already completed run")
            if not replaying_received_output:
                self.repository.receive_first_output(
                    run_id,
                    output_digest=raw_output_digest,
                    output_size_bytes=len(raw_bytes),
                )
            try:
                return self._finalize_model_output_scoped(
                    run,
                    raw_bytes,
                    raw_output_digest=raw_output_digest,
                )
            except Exception as exc:
                received = self.repository.model_run_for_request(
                    run_id,
                    principal_id=principal_id,
                    account_id=account_id,
                    browser_session_id=browser_session_id,
                )
                if received is None or received.state != "FIRST_OUTPUT_RECEIVED":
                    raise
                self.repository.preserve_first_output(
                    run_id,
                    raw_output_digest,
                    "FIRST_OUTPUT_REJECTED",
                    {
                        "result_class": "SYSTEM_OR_PROVIDER_ERROR",
                        "failure_stage": "DOWNSTREAM_VALIDATION",
                        "error_type": type(exc).__name__,
                        "run_id": run_id,
                        "first_output_preserved": True,
                    },
                )
                return self._failure_result("SYSTEM_OR_PROVIDER_ERROR", run_id)

    def _finalize_model_output_scoped(
        self,
        run: RuntimeModelRun,
        raw_bytes: bytes,
        *,
        raw_output_digest: str,
    ) -> JsonObject:
        try:
            self.repository.require_active_scope(run.principal_id, run.account_id)
        except ValueError as exc:
            raise RuntimeContractError("Run authority is no longer active") from exc
        try:
            raw = raw_bytes.decode("utf-8")
            normalized, normalization = normalize_model_json_text(raw)
            try:
                parsed = json.loads(normalized)
            except json.JSONDecodeError:
                repair_markers: list[str] = []
                repaired, structural_quote_count = (
                    normalize_unambiguous_json_structural_quotes(normalized)
                )
                repaired, control_count = escape_json_string_control_characters(
                    repaired
                )
                repaired, quote_count = escape_unambiguous_json_string_quotes(
                    repaired
                )
                repaired, trailing_comma_count = (
                    remove_unambiguous_json_trailing_commas(repaired)
                )
                if structural_quote_count:
                    repair_markers.append(
                        "NORMALIZED_UNAMBIGUOUS_JSON_STRUCTURAL_QUOTES:"
                        f"{structural_quote_count}"
                    )
                if control_count:
                    repair_markers.append("ESCAPED_RAW_JSON_STRING_CONTROLS")
                if quote_count:
                    repair_markers.append("ESCAPED_UNAMBIGUOUS_JSON_STRING_QUOTES")
                if trailing_comma_count:
                    repair_markers.append(
                        "REMOVED_UNAMBIGUOUS_JSON_TRAILING_COMMAS:"
                        f"{trailing_comma_count}"
                    )
                try:
                    parsed = json.loads(repaired)
                except json.JSONDecodeError:
                    rebuilt, candidate_count = rebuild_fragmented_candidate_envelope(
                        repaired
                    )
                    if candidate_count == 0:
                        raise
                    parsed = json.loads(rebuilt)
                    repaired = rebuilt
                    repair_markers.append(
                        "REBUILT_FRAGMENTED_CANDIDATE_ENVELOPE:"
                        f"{candidate_count}"
                    )
                normalized = repaired
                for marker in repair_markers:
                    normalization = (
                        marker
                        if normalization == "NONE"
                        else f"{normalization}+{marker}"
                    )
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.repository.preserve_first_output(
                run.run_id,
                raw_output_digest,
                "FIRST_OUTPUT_REJECTED",
                {
                    "result_class": "MODEL_OUTPUT_CONTRACT_ERROR",
                    "failure_stage": "DECODE_OR_JSON",
                    "error_type": type(exc).__name__,
                    "run_id": run.run_id,
                    "first_output_preserved": True,
                },
            )
            return self._failure_result("MODEL_OUTPUT_CONTRACT_ERROR", run.run_id)

        if run.plan_ref is None:
            try:
                envelope = ChatEnvelope.model_validate(parsed)
            except ValueError as exc:
                self.repository.preserve_first_output(
                    run.run_id,
                    raw_output_digest,
                    "FIRST_OUTPUT_REJECTED",
                    {
                        "result_class": "MODEL_OUTPUT_CONTRACT_ERROR",
                        "failure_stage": "CHAT_CONTRACT",
                        "error_type": type(exc).__name__,
                        "run_id": run.run_id,
                        "first_output_preserved": True,
                    },
                )
                return self._failure_result("MODEL_OUTPUT_CONTRACT_ERROR", run.run_id)
            output = envelope.model_dump()
            self.repository.preserve_first_output(
                run.run_id,
                raw_output_digest,
                "FIRST_OUTPUT_ACCEPTED",
                {
                    "envelope": output,
                    "server_bound_contract_version": AUTHOR_CONTRACT_VERSION,
                    "private_retrieval_performed": False,
                    "model_wrapper_normalization": normalization,
                    "result_class": "SUCCESS",
                },
            )
            return {"response_kind": "DIRECT", "user_visible_text": envelope.reply}

        task_brief = run.payload.get("task_brief")
        expected_format = (
            task_brief.get("content_format") if isinstance(task_brief, dict) else None
        )
        if expected_format not in self.content_formats or not isinstance(
            task_brief, dict
        ):
            self.repository.preserve_first_output(
                run.run_id,
                raw_output_digest,
                "FIRST_OUTPUT_REJECTED",
                {
                    "result_class": "SYSTEM_OR_PROVIDER_ERROR",
                    "failure_stage": "SERVER_TASK_CONTRACT",
                    "run_id": run.run_id,
                    "first_output_preserved": True,
                },
            )
            return self._failure_result("SYSTEM_OR_PROVIDER_ERROR", run.run_id)
        transport_markers: list[str] = []
        candidate_fields = CANDIDATE_MODELS[
            cast(ContentFormat, expected_format)
        ].model_fields
        if isinstance(parsed, dict) and "candidates" not in parsed:
            parsed_fields = set(parsed)
            required_fields = {
                field
                for field, descriptor in candidate_fields.items()
                if descriptor.is_required()
            }
            if required_fields <= parsed_fields <= set(candidate_fields):
                parsed = {"candidates": [parsed]}
                transport_markers.append("WRAPPED_BARE_CANDIDATE_OBJECT")
        transport_markers.extend(self._normalize_server_owned_author_echo(
            parsed,
            expected_format=expected_format,
            task_brief=task_brief,
        ))
        for marker in transport_markers:
            normalization = (
                marker if normalization == "NONE" else f"{normalization}+{marker}"
            )
        try:
            candidates, schema_failures = parse_candidate_envelope(
                parsed,
                expected_format,
            )
        except ValueError as exc:
            self.repository.preserve_first_output(
                run.run_id,
                raw_output_digest,
                "FIRST_OUTPUT_REJECTED",
                {
                    "result_class": "MODEL_OUTPUT_CONTRACT_ERROR",
                    "failure_stage": "CANDIDATE_ENVELOPE",
                    "error_type": type(exc).__name__,
                    "model_wrapper_normalization": normalization,
                    "original_envelope": copy.deepcopy(parsed),
                    "run_id": run.run_id,
                    "first_output_preserved": True,
                },
            )
            return self._failure_result("MODEL_OUTPUT_CONTRACT_ERROR", run.run_id)
        return self._finalize_lightweight_candidates(
            run,
            candidates,
            schema_failures=schema_failures,
            original_envelope=parsed,
            output_digest=raw_output_digest,
            normalization=normalization,
        )

    @staticmethod
    def _normalize_server_owned_author_echo(
        parsed: object,
        *,
        expected_format: str,
        task_brief: JsonObject,
    ) -> list[str]:
        """Remove only exact echoes of server-owned contract metadata."""

        if not isinstance(parsed, dict) or not isinstance(
            parsed.get("candidates"), list
        ):
            return []
        markers: list[str] = []
        candidates = cast(list[object], parsed["candidates"])
        removed_defaults: list[str] = []
        for field, empty_value in (("cta", ""), ("spoken_lines", [])):
            if parsed.get(field) == empty_value and all(
                isinstance(candidate, dict) and field not in candidate
                for candidate in candidates
            ):
                del parsed[field]
                removed_defaults.append(field)
        if removed_defaults:
            markers.append(
                "REMOVED_EMPTY_ROOT_CANDIDATE_DEFAULTS:"
                + ",".join(removed_defaults)
            )
        replaced_null_defaults = 0
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            for field in ("cta", "spoken_lines"):
                if field in candidate and candidate[field] is None:
                    candidate[field] = "" if field == "cta" else []
                    replaced_null_defaults += 1
        if replaced_null_defaults:
            markers.append(
                "REPLACED_NULL_CANDIDATE_DEFAULTS:"
                f"{replaced_null_defaults}"
            )
        deliverable_fields = deliverable_field_names(
            cast(ContentFormat, expected_format)
        )
        moved_fields = 0
        for candidate in candidates:
            deliverable = (
                candidate.get("deliverable") if isinstance(candidate, dict) else None
            )
            if not isinstance(candidate, dict) or not isinstance(deliverable, dict):
                continue
            for field in deliverable_fields:
                if field in candidate and field not in deliverable:
                    deliverable[field] = candidate.pop(field)
                    moved_fields += 1
        if moved_fields:
            markers.append(
                f"MOVED_CANDIDATE_ROOT_DELIVERABLE_FIELDS:{moved_fields}"
            )
        if parsed.get("contract_version") == AUTHOR_CONTRACT_VERSION:
            del parsed["contract_version"]
            markers.append("REMOVED_EXACT_SERVER_CONTRACT_VERSION_ECHO")
        if expected_format == "短视频":
            dialogue_count = 0
            ambient_count = 0
            for candidate in candidates:
                deliverable = (
                    candidate.get("deliverable")
                    if isinstance(candidate, dict)
                    else None
                )
                shots = (
                    deliverable.get("shots")
                    if isinstance(deliverable, dict)
                    else None
                )
                if not isinstance(shots, list):
                    continue
                for shot in shots:
                    audio = shot.get("audio") if isinstance(shot, dict) else None
                    if not isinstance(audio, str):
                        continue
                    normalized_audio = audio.strip()
                    if not normalized_audio or any(
                        label in normalized_audio
                        for label in ("台词", "旁白", "纯画面", "环境声")
                    ):
                        continue
                    if NATURAL_DIALOGUE_AUDIO_PATTERN.search(normalized_audio):
                        shot["audio"] = f"台词：{normalized_audio}"
                        dialogue_count += 1
                    else:
                        shot["audio"] = f"环境声：{normalized_audio}"
                        ambient_count += 1
            if dialogue_count or ambient_count:
                markers.append(
                    "CLASSIFIED_UNLABELED_SHOT_AUDIO:"
                    f"dialogue={dialogue_count},ambient={ambient_count}"
                )
        expected_duration = task_brief.get("duration_label")
        if expected_format != "短视频" or not isinstance(expected_duration, str):
            return markers
        removed = 0
        for candidate in candidates:
            deliverable = (
                candidate.get("deliverable") if isinstance(candidate, dict) else None
            )
            if (
                isinstance(deliverable, dict)
                and deliverable.get("duration_label") == expected_duration
            ):
                del deliverable["duration_label"]
                removed += 1
        if removed:
            markers.append(f"REMOVED_EXACT_SERVER_DURATION_ECHO:{removed}")
        return markers

    def _finalize_lightweight_candidates(
        self,
        run: RuntimeModelRun,
        candidates: list[CandidateBase],
        *,
        schema_failures: list[JsonObject],
        original_envelope: object,
        output_digest: str,
        normalization: str,
    ) -> JsonObject:
        if run.plan_ref is None:
            raise RuntimeContractError("Candidate run has no composition plan")
        access = self._access(run.principal_id, run.account_id)
        materials = self.adapter.author_materials(run.plan_ref, access)
        task_brief = run.payload.get("task_brief")
        if not isinstance(task_brief, dict):
            task_brief = {}
        expected_format = str(task_brief.get("content_format", ""))
        fact_refs, material_refs = self._server_reference_scope(materials, task_brief)
        plan_record = self.adapter.expression_service.store.get(run.plan_ref)
        if plan_record is None:
            raise RuntimeContractError("Candidate plan is unavailable")
        literal_prohibitions = tuple(
            str(value)
            for value in plan_record.plan["expression_guidance"].get(
                "literal_prohibited_phrases", []
            )
            if isinstance(value, str) and value
        )
        accepted: list[JsonObject] = []
        validations: list[JsonObject] = []
        candidate_failures = copy.deepcopy(schema_failures)
        comparison_texts: list[str] = []
        for ordinal, candidate in enumerate(candidates, 1):
            try:
                surfaces = self._server_candidate_surfaces(
                    candidate,
                    content_format=expected_format,
                    task_brief=task_brief,
                )
            except ValueError as exc:
                candidate_failures.append(
                    {
                        "candidate_ordinal": ordinal,
                        "error_type": "SERVER_MATERIALIZATION_ERROR",
                        "error_count": 1,
                        "error_locations": [type(exc).__name__],
                    }
                )
                continue
            validator_surfaces = self._validator_surface_projection(
                surfaces,
                literal_prohibitions,
            )
            sensitive_failures = self._server_sensitive_surface_failures(surfaces)
            if sensitive_failures:
                candidate_failures.append(
                    {
                        "candidate_ordinal": ordinal,
                        "error_type": "SENSITIVE_SURFACE_ERROR",
                        "error_count": len(sensitive_failures),
                        "error_locations": sensitive_failures,
                    }
                )
                continue
            candidate_id = f"CAND-{run.run_id[-16:]}-{len(accepted) + 1}"
            payload: JsonObject = {
                "candidate_id": candidate_id,
                "candidate_version": 2,
                "creative_difference": candidate.creative_difference,
                "difference_label": candidate.creative_difference,
                "candidate_user_visible_surfaces": surfaces,
                "claim_bindings": [],
                "author_declared_claim_bindings": [],
                "used_fact_refs": list(fact_refs),
                "used_material_refs": list(material_refs),
                "evidence_panel": {
                    "panel_label": "本次参考资料范围",
                    "used_fact_count": len(fact_refs),
                    "used_material_count": len(material_refs),
                    "scope_and_authorization_checked": True,
                    "machine_proves_every_sentence": False,
                    "server_bound_explicit_fact_count": 0,
                    "usage_note": "请自行检查后使用",
                    "publishable": False,
                },
            }
            validator_candidate = {
                "candidate_id": candidate_id,
                "candidate_version": 2,
                "candidate_user_visible_surfaces": validator_surfaces,
            }
            validation = self.adapter.validate_candidate(
                run.plan_ref,
                access,
                validator_candidate,
                actually_used_fact_refs=tuple(fact_refs),
                actually_used_material_refs=tuple(material_refs),
                evaluation_at=datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            )
            if validation.get("decision") != "PASS":
                candidate_failures.append(
                    {
                        "candidate_ordinal": ordinal,
                        "error_type": "REFERENCE_SCOPE_VALIDATION_ERROR",
                        "error_count": 1,
                        "error_locations": [str(validation.get("decision", "UNKNOWN"))],
                    }
                )
                continue
            accepted.append(payload)
            validations.append(validation)
            comparison_texts.append(
                re.sub(
                    r"\s+",
                    "",
                    json.dumps(surfaces, ensure_ascii=False, sort_keys=True),
                )
            )
        similarity_notes = self._similarity_notes(comparison_texts)
        for ordinal, payload in enumerate(accepted, 1):
            evidence_panel = cast(JsonObject, payload["evidence_panel"])
            evidence_panel["similarity_notes"] = [
                row for row in similarity_notes if ordinal in row["candidate_ordinals"]
            ]
        if len(accepted) < 2:
            result_class = "MODEL_OUTPUT_CONTRACT_ERROR"
            failure_reason = (
                "NO_COMPLETE_SAFE_CANDIDATE"
                if not accepted
                else "INSUFFICIENT_COMPLETE_CANDIDATES"
            )
            self.repository.preserve_first_output(
                run.run_id,
                output_digest,
                "FIRST_OUTPUT_REJECTED",
                {
                    "result_class": result_class,
                    "failure_stage": "CANDIDATE_VALIDATION",
                    "candidate_failures": candidate_failures,
                    "accepted_candidate_count": len(accepted),
                    "failure_reason": failure_reason,
                    "original_envelope": copy.deepcopy(original_envelope),
                    "run_id": run.run_id,
                    "first_output_preserved": True,
                },
            )
            return self._failure_result(result_class, run.run_id)
        candidate_option_warning = None
        self.repository.save_candidate_set(
            run_id=run.run_id,
            account_id=run.account_id,
            plan_ref=run.plan_ref,
            candidates=accepted,
            validations=validations,
        )
        self.repository.preserve_first_output(
            run.run_id,
            output_digest,
            "FIRST_OUTPUT_ACCEPTED",
            {
                "result_class": "SUCCESS",
                "candidate_failures": candidate_failures,
                "accepted_candidate_count": len(accepted),
                "candidate_option_warning": candidate_option_warning,
                "model_wrapper_normalization": normalization,
                "similarity_notes": similarity_notes,
                "first_output_preserved": True,
            },
        )
        return {
            "response_kind": "DIRECT",
            "result_class": "SUCCESS",
            "run_id": run.run_id,
            "candidate_option_warning": candidate_option_warning,
            "user_visible_text": "\n".join(
                value
                for value in (
                    candidate_option_warning,
                    self._render_candidates(accepted),
                )
                if value
            ),
            "ui_state": "result",
            "candidates": self._candidate_workbench(
                self.repository.latest_candidates(run.principal_id, run.account_id)
            ),
            "series": self._series_projection(task_brief),
        }

    @staticmethod
    def _server_reference_scope(
        materials: JsonObject,
        task_brief: JsonObject,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        scope_identity_only = bool(
            task_brief.get("scope_identity_only_authoring_allowed")
        )
        fact_refs = tuple(
            str(row["fact_id"])
            for row in materials.get("verified_precise_facts", [])
            if isinstance(row, dict)
            and isinstance(row.get("fact_id"), str)
            and (row.get("fact_kind") != "AUTHORIZATION" or scope_identity_only)
        )
        material_refs = tuple(
            str(value)
            for value in materials.get("retrieval_fragment_refs", [])
            if isinstance(value, str)
        )
        return fact_refs, material_refs

    @staticmethod
    def _validator_surface_projection(
        surfaces: JsonObject,
        literal_prohibitions: tuple[str, ...],
    ) -> JsonObject:
        """Keep legacy brand wording preferences out of the runtime hard gate."""

        def mask_clause(clause: str) -> str:
            masked = clause
            for phrase in literal_prohibitions:
                if phrase:
                    masked = masked.replace(phrase, "[表达偏好由使用人自行检查]")
            return masked

        def visit(value: object) -> object:
            if isinstance(value, str):
                parts = re.split(r"([，,。；;！？!?：:\n]+)", value)
                return "".join(
                    part if index % 2 else mask_clause(part)
                    for index, part in enumerate(parts)
                )
            if isinstance(value, list):
                return [visit(item) for item in value]
            if isinstance(value, dict):
                return {str(key): visit(item) for key, item in value.items()}
            return copy.deepcopy(value)

        projected = visit(surfaces)
        if not isinstance(projected, dict):
            raise RuntimeContractError("Validator surface projection is invalid")
        return projected

    @staticmethod
    def _server_candidate_surfaces(
        candidate: CandidateBase,
        *,
        content_format: str,
        task_brief: JsonObject,
    ) -> JsonObject:
        deliverable = candidate.deliverable_payload()
        branches: JsonObject = {
            "video": None,
            "article": None,
            "live": None,
            "private_communication": None,
            "offline_material": None,
            "training": None,
            "display": None,
        }
        spoken = list(candidate.spoken_lines)
        if content_format == "短视频":
            shots = [
                {
                    "time_range": f"镜头{index}",
                    "visual": row["visual"],
                    "action": row["action"],
                    "camera": row["camera"],
                    "audio": row["audio"],
                    "subtitle": row["subtitle"],
                    "scene_product_props": "",
                    "edit_note": row["edit_note"],
                }
                for index, row in enumerate(deliverable["shots"], 1)
            ]
            branches["video"] = {
                "shots": shots,
                "shooting_notes": deliverable["shooting_notes"],
                "editing_notes": deliverable["editing_notes"],
            }
            spoken = [
                str(row["audio"])
                for row in shots
                if "台词" in str(row["audio"]) or "旁白" in str(row["audio"])
            ]
        elif content_format == "图文":
            branches["article"] = {
                "frames": [
                    {"order": index, **row}
                    for index, row in enumerate(deliverable["frames"], 1)
                ],
                "cover_brief": deliverable["cover_brief"],
                "layout_notes": deliverable["layout_notes"],
            }
        elif content_format == "直播内容包":
            branches["live"] = deliverable
        elif content_format == "私域沟通内容":
            branches["private_communication"] = deliverable
        elif content_format == "门店线下物料":
            branches["offline_material"] = deliverable
        elif content_format == "培训与门店话术":
            branches["training"] = deliverable
        elif content_format == "陈列搭配":
            branches["display"] = {
                "referenced_items_or_facts": ["以本次确认任务中的商品或陈列对象为准"],
                **deliverable,
            }
        else:
            raise RuntimeContractError("Unknown content format")
        opening = spoken[0] if spoken else candidate.body[:500]
        ending = candidate.cta or "请自行检查后使用。"
        production = ProductionPackage.model_validate(
            {
                "production_format": content_format,
                "task_summary": str(
                    task_brief.get("confirmed_user_request")
                    or task_brief.get("content_goal")
                    or task_brief.get("key_takeaway")
                    or "完成当前内部内容任务"
                ),
                "content_direction": str(
                    task_brief.get("content_direction") or candidate.creative_difference
                ),
                "core_idea": candidate.creative_difference,
                "cover_or_first_screen_copy": candidate.title,
                "opening_hook": opening,
                "story_or_full_script": candidate.body,
                "target_platform": str(task_brief.get("target_platform") or "内部测试"),
                "duration_label": str(task_brief.get("duration_label") or "由系统建议"),
                "ending_and_action": ending,
                "publishing_copy": candidate.body,
                "next_actions": ["选择候选", "提出局部修改", "直接导出"],
                **branches,
            }
        )
        return CandidateSurfaces.model_validate(
            {
                "title": candidate.title,
                "body": candidate.body,
                "spoken_lines": spoken,
                "CTA": candidate.cta,
                "execution_payload": production.model_dump(by_alias=True),
                "surface_units": [],
            }
        ).model_dump(by_alias=True)

    @staticmethod
    def _server_fact_resolution(
        surfaces: JsonObject,
        *,
        classification_surfaces: JsonObject,
        source_corpus: dict[str, str],
    ) -> tuple[list[JsonObject], list[str]]:
        """Bind supported explicit facts and reject unsupported or sensitive claims."""

        failures: set[str] = set()
        bindings: list[JsonObject] = []
        classification_text = audience_surface_text_map(classification_surfaces)
        for path, text in audience_surface_text_map(surfaces).items():
            supporting_refs: set[str] = set()
            unsupported = False
            for clause in high_risk_fact_clauses(
                path,
                classification_text.get(path, text),
            ):
                clause_refs = {
                    ref
                    for ref, source_text in source_corpus.items()
                    if source_supports_fact_clause(clause, source_text)
                }
                if not clause_refs:
                    unsupported = True
                    failures.add(f"{path}:UNSUPPORTED_EXPLICIT_FACT")
                    continue
                supporting_refs.update(clause_refs)
            if supporting_refs and not unsupported:
                bindings.append(
                    {
                        "surface_path": path,
                        "exact_text": text,
                        "claim_class": "SOURCE_CLAIM",
                        "source_refs": sorted(supporting_refs),
                        "binding_origin": "SERVER_PATH_CLASSIFICATION",
                    }
                )
        return sorted(bindings, key=lambda row: str(row["surface_path"])), sorted(
            failures
        )

    @staticmethod
    def _server_sensitive_surface_failures(surfaces: JsonObject) -> list[str]:
        """Reject only internal identifiers, direct PII, and credential material."""

        failures: set[str] = set()
        for path, text in audience_surface_text_map(surfaces).items():
            if INTERNAL_REFERENCE_PATTERN.search(text):
                failures.add(f"{path}:INTERNAL_REFERENCE")
            if PERSONAL_INFORMATION_PATTERN.search(text):
                failures.add(f"{path}:PERSONAL_INFORMATION")
            if any(pattern.search(text) for pattern in SECRET_SURFACE_PATTERNS):
                failures.add(f"{path}:SECRET")
        return sorted(failures)

    @staticmethod
    def _similarity_notes(texts: list[str]) -> list[JsonObject]:
        return [
            {
                "candidate_ordinals": [index + 1, other_index + 1],
                "similarity_ratio": round(
                    SequenceMatcher(None, left, right, autojunk=False).ratio(),
                    4,
                ),
                "worth_comparing": SequenceMatcher(
                    None,
                    left,
                    right,
                    autojunk=False,
                ).ratio()
                >= 0.90,
                "runtime_rejection": False,
            }
            for index, left in enumerate(texts)
            for other_index, right in enumerate(texts[index + 1 :], start=index + 1)
        ]

    def revalidate_preserved_candidate_output(self, run_id: str) -> JsonObject:
        """Keep legacy candidate contracts as read-only historical evidence."""

        del run_id
        raise RuntimeContractError("Legacy contract replay cannot write runtime state")

    def revalidate_preserved_parse_error(
        self,
        run_id: str,
        model_output_b64: str,
    ) -> JsonObject:
        """Keep malformed legacy envelopes immutable and out of current state."""

        del run_id, model_output_b64
        raise RuntimeContractError("Legacy contract replay cannot write runtime state")

    @staticmethod
    def _normalize_known_model_contract_variants(parsed: object) -> list[str]:
        """Normalize only closed, semantics-preserving provider contract variants."""
        if not isinstance(parsed, dict) or not isinstance(
            parsed.get("candidates"), list
        ):
            return []
        dimension_alias_count = 0
        dimension_detail_suffix_count = 0
        material_fact_ref_count = 0
        empty_cta_mapping_count = 0
        execution_path_prefix_count = 0
        singleton_spoken_path_count = 0
        execution_roots = {
            "production_format",
            "task_summary",
            "content_direction",
            "core_idea",
            "cover_or_first_screen_copy",
            "opening_hook",
            "story_or_full_script",
            "target_platform",
            "duration_label",
            "ending_and_action",
            "publishing_copy",
            "next_actions",
            "video",
            "article",
            "display",
        }
        for candidate in parsed["candidates"]:
            if not isinstance(candidate, dict):
                continue
            dimensions = candidate.get("difference_dimensions")
            if isinstance(dimensions, list):
                for index, value in enumerate(dimensions):
                    if value == "切入问题":
                        dimensions[index] = "切入问题或场景"
                        dimension_alias_count += 1
                        continue
                    if isinstance(value, str) and "：" in value:
                        category = value.split("：", 1)[0].strip()
                        if category in {
                            "核心创意",
                            "切入问题或场景",
                            "情绪钩子",
                            "叙事视角",
                            "事实或证明路径",
                            "画面组织方法",
                        }:
                            dimensions[index] = category
                            dimension_detail_suffix_count += 1
            fact_refs = candidate.get("used_fact_refs")
            material_refs = candidate.get("used_material_refs")
            if isinstance(fact_refs, list) and isinstance(material_refs, list):
                material_ref_set = set(
                    value for value in material_refs if isinstance(value, str)
                )
                normalized_fact_refs = []
                for value in fact_refs:
                    if (
                        isinstance(value, str)
                        and value.startswith("PKG5-FRAGMENT-")
                        and value in material_ref_set
                    ):
                        material_fact_ref_count += 1
                        continue
                    normalized_fact_refs.append(value)
                candidate["used_fact_refs"] = normalized_fact_refs
            surfaces = candidate.get("surfaces")
            execution_payload = (
                surfaces.get("execution_payload")
                if isinstance(surfaces, dict)
                else None
            )
            ending_and_action = (
                execution_payload.get("ending_and_action")
                if isinstance(execution_payload, dict)
                else None
            )
            if (
                isinstance(surfaces, dict)
                and surfaces.get("CTA") == ""
                and isinstance(ending_and_action, str)
                and ending_and_action.strip()
            ):
                surfaces["CTA"] = ending_and_action.strip()
                bindings = candidate.get("claim_bindings")
                if isinstance(bindings, list):
                    bindings[:] = [
                        row
                        for row in bindings
                        if not isinstance(row, dict) or row.get("surface_path") != "CTA"
                    ]
                    ending_binding = next(
                        (
                            row
                            for row in bindings
                            if isinstance(row, dict)
                            and row.get("surface_path")
                            == "execution_payload.ending_and_action"
                            and row.get("exact_text") == ending_and_action.strip()
                        ),
                        None,
                    )
                    if ending_binding is not None:
                        bindings.append(
                            {**copy.deepcopy(ending_binding), "surface_path": "CTA"}
                        )
                empty_cta_mapping_count += 1
            bindings = candidate.get("claim_bindings")
            if isinstance(bindings, list):
                for binding in bindings:
                    if not isinstance(binding, dict):
                        continue
                    path = binding.get("surface_path")
                    if (
                        isinstance(path, str)
                        and path
                        and path.split(".", 1)[0].split("[", 1)[0] in execution_roots
                    ):
                        binding["surface_path"] = f"execution_payload.{path}"
                        execution_path_prefix_count += 1
                    elif (
                        path == "spoken_lines"
                        and isinstance(surfaces, dict)
                        and isinstance(surfaces.get("spoken_lines"), list)
                        and len(surfaces["spoken_lines"]) == 1
                        and binding.get("exact_text") == surfaces["spoken_lines"][0]
                    ):
                        binding["surface_path"] = "spoken_lines[0]"
                        singleton_spoken_path_count += 1
        markers = []
        if dimension_alias_count:
            markers.append("NORMALIZED_EXACT_DIFFERENCE_DIMENSION_ALIAS")
        if dimension_detail_suffix_count:
            markers.append("REMOVED_DIFFERENCE_DIMENSION_DETAIL_SUFFIX")
        if material_fact_ref_count:
            markers.append("REMOVED_DUPLICATE_MATERIAL_REF_FROM_FACT_REFS")
        if empty_cta_mapping_count:
            markers.append("COPIED_EXISTING_ENDING_AND_ACTION_TO_EMPTY_CTA")
        if execution_path_prefix_count:
            markers.append("PREFIXED_EXECUTION_PAYLOAD_CLAIM_PATH")
        if singleton_spoken_path_count:
            markers.append("INDEXED_SINGLETON_SPOKEN_LINE_CLAIM_PATH")
        return markers

    @staticmethod
    def _surface_text_map(candidate: ModelCandidate) -> dict[str, str]:
        """Enumerate every non-empty audience-facing text leaf exactly once."""

        return audience_surface_text_map(candidate.surfaces.model_dump())

    @staticmethod
    def _source_corpus_by_ref(materials: JsonObject) -> dict[str, str]:
        corpus: dict[str, str] = {}
        for row in materials.get("scoped_retrieval_fragments", []):
            if isinstance(row, dict) and isinstance(row.get("fragment_id"), str):
                corpus[str(row["fragment_id"])] = json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                )
        for row in materials.get("verified_precise_facts", []):
            if isinstance(row, dict) and isinstance(row.get("fact_id"), str):
                corpus[str(row["fact_id"])] = json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                )
        return corpus

    @staticmethod
    def _resolve_claim_bindings(
        candidate: ModelCandidate,
        *,
        allowed_fact_refs: set[str],
        allowed_material_refs: set[str],
        source_corpus: dict[str, str],
        trusted_task_text: str = "",
    ) -> list[JsonObject] | None:
        text_by_path = Package7Runtime._surface_text_map(candidate)
        bindings = candidate.claim_bindings
        binding_paths = [binding.surface_path for binding in bindings]
        if len(binding_paths) != len(set(binding_paths)) or not set(
            binding_paths
        ).issubset(text_by_path):
            return None
        cited_refs: set[str] = set()
        allowed_refs = allowed_fact_refs | allowed_material_refs
        effective: list[JsonObject] = []
        for binding in bindings:
            if text_by_path.get(binding.surface_path) != binding.exact_text:
                return None
            if not set(binding.source_refs).issubset(allowed_refs):
                return None
            declared_refs = set(candidate.used_fact_refs) | set(
                candidate.used_material_refs
            )
            if not set(binding.source_refs).issubset(declared_refs):
                return None
            if binding.claim_class == "SOURCE_CLAIM":
                cited_refs.update(binding.source_refs)
                support_text = "\n".join(
                    source_corpus[ref] for ref in binding.source_refs
                )
                if any(
                    not protected_detail_is_supported(token, support_text)
                    for token in PROTECTED_SOURCE_DETAIL_PATTERN.findall(
                        binding.exact_text
                    )
                ):
                    return None
            elif surface_requires_evidence_binding(
                binding.surface_path,
                binding.exact_text,
            ):
                return None
            effective.append(
                {**binding.model_dump(), "binding_origin": "AUTHOR_DECLARED"}
            )

        declared_paths = set(binding_paths)
        for path, exact_text in text_by_path.items():
            if path in declared_paths:
                continue
            if surface_requires_evidence_binding(path, exact_text):
                return None
        declared_refs = set(candidate.used_fact_refs) | set(
            candidate.used_material_refs
        )
        if not cited_refs.issubset(declared_refs):
            return None
        return sorted(effective, key=lambda row: str(row["surface_path"]))

    @staticmethod
    def _claim_bindings_are_closed(
        candidate: ModelCandidate,
        *,
        allowed_fact_refs: set[str],
        allowed_material_refs: set[str],
        source_corpus: dict[str, str],
    ) -> bool:
        return (
            Package7Runtime._resolve_claim_bindings(
                candidate,
                allowed_fact_refs=allowed_fact_refs,
                allowed_material_refs=allowed_material_refs,
                source_corpus=source_corpus,
                trusted_task_text="",
            )
            is not None
        )

    @staticmethod
    def _candidate_comparison_text(candidate: ModelCandidate) -> str:
        production = candidate.surfaces.execution_payload
        selected = {
            "body": candidate.surfaces.body,
            "spoken_lines": candidate.surfaces.spoken_lines,
            "opening_hook": production.opening_hook,
            "story_or_full_script": production.story_or_full_script,
            "ending_and_action": production.ending_and_action,
            "format_payload": {
                "video": None
                if production.video is None
                else production.video.model_dump(),
                "article": None
                if production.article is None
                else production.article.model_dump(),
                "display": None
                if production.display is None
                else production.display.model_dump(),
            },
        }
        return re.sub(
            r"\s+", "", json.dumps(selected, ensure_ascii=False, sort_keys=True)
        )

    def _finalize_candidate_envelope(
        self,
        run: RuntimeModelRun,
        envelope: ModelEnvelope,
        *,
        output_digest: str,
        normalization: str,
        preserved_revalidation: bool = False,
        preserved_revalidation_details: JsonObject | None = None,
    ) -> JsonObject:
        if run.plan_ref is None:
            raise RuntimeContractError("Candidate run has no composition plan")
        output = envelope.model_dump()

        def reject(payload: JsonObject) -> JsonObject:
            if not preserved_revalidation:
                self.repository.preserve_first_output(
                    run.run_id,
                    output_digest,
                    "FIRST_OUTPUT_REJECTED",
                    payload,
                )
            return self._plain_action("BLOCK")

        access = self._access(run.principal_id, run.account_id)
        materials = self.adapter.author_materials(run.plan_ref, access)
        task_brief = run.payload.get("task_brief", {})
        scope_identity_only = bool(
            isinstance(task_brief, dict)
            and task_brief.get("scope_identity_only_authoring_allowed")
        )
        allowed_fact_refs = {
            str(row["fact_id"])
            for row in materials.get("verified_precise_facts", [])
            if isinstance(row, dict)
            and (row.get("fact_kind") != "AUTHORIZATION" or scope_identity_only)
            and isinstance(row.get("fact_id"), str)
        }
        allowed_material_refs = set(materials["retrieval_fragment_refs"])
        source_corpus = self._source_corpus_by_ref(materials)
        expected_format = (
            task_brief.get("content_format") if isinstance(task_brief, dict) else None
        )
        candidates: list[JsonObject] = []
        validations: list[JsonObject] = []
        comparison_texts: list[str] = []
        for ordinal, candidate in enumerate(envelope.candidates, 1):
            production = candidate.surfaces.execution_payload
            if (
                expected_format is not None
                and production.production_format != expected_format
            ):
                return reject(output)
            if not set(candidate.used_fact_refs).issubset(allowed_fact_refs) or not set(
                candidate.used_material_refs
            ).issubset(allowed_material_refs):
                return reject(output)
            if not candidate.used_material_refs and not candidate.used_fact_refs:
                return reject(output)
            if not candidate.used_material_refs and not scope_identity_only:
                return reject(output)
            effective_claim_bindings = self._resolve_claim_bindings(
                candidate,
                allowed_fact_refs=allowed_fact_refs,
                allowed_material_refs=allowed_material_refs,
                source_corpus=source_corpus,
                trusted_task_text=json.dumps(
                    task_brief, ensure_ascii=False, sort_keys=True
                ),
            )
            if effective_claim_bindings is None:
                return reject(output)
            comparison_texts.append(self._candidate_comparison_text(candidate))
            candidate_id = f"CAND-{run.run_id[-16:]}-{ordinal}"
            payload = {
                "candidate_id": candidate_id,
                "candidate_version": 1,
                "difference_label": candidate.difference_label,
                "narrative_architecture": candidate.narrative_architecture,
                "difference_dimensions": list(candidate.difference_dimensions),
                "candidate_user_visible_surfaces": candidate.surfaces.model_dump(),
                "claim_bindings": effective_claim_bindings,
                "author_declared_claim_bindings": [
                    row.model_dump() for row in candidate.claim_bindings
                ],
                "used_fact_refs": list(candidate.used_fact_refs),
                "used_material_refs": list(candidate.used_material_refs),
                "evidence_panel": {
                    "used_fact_count": len(candidate.used_fact_refs),
                    "used_material_count": len(candidate.used_material_refs),
                    "surface_claim_binding_count": len(effective_claim_bindings),
                    "author_declared_claim_binding_count": len(
                        candidate.claim_bindings
                    ),
                    "server_derived_claim_binding_count": (
                        len(effective_claim_bindings) - len(candidate.claim_bindings)
                    ),
                    "scope_and_authorization_checked": True,
                    "usage_note": "请自行检查后使用",
                    "publishable": False,
                },
            }
            validator_candidate = {
                "candidate_id": candidate_id,
                "candidate_version": 1,
                "candidate_user_visible_surfaces": candidate.surfaces.model_dump(),
            }
            validation = self.adapter.validate_candidate(
                run.plan_ref,
                access,
                validator_candidate,
                actually_used_fact_refs=tuple(candidate.used_fact_refs),
                actually_used_material_refs=tuple(candidate.used_material_refs),
                evaluation_at=datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            )
            candidates.append(payload)
            validations.append(validation)
        similarity_review_hints: list[JsonObject] = [
            {
                "candidate_ordinals": [index + 1, other_index + 1],
                "similarity_ratio": round(
                    SequenceMatcher(None, left, right, autojunk=False).ratio(),
                    4,
                ),
                "review_required": SequenceMatcher(
                    None,
                    left,
                    right,
                    autojunk=False,
                ).ratio()
                >= 0.90,
                "runtime_rejection": False,
            }
            for index, left in enumerate(comparison_texts)
            for other_index, right in enumerate(
                comparison_texts[index + 1 :],
                start=index + 1,
            )
        ]
        for ordinal, payload in enumerate(candidates, 1):
            evidence_panel = cast(JsonObject, payload["evidence_panel"])
            evidence_panel["similarity_review_hints"] = [
                row
                for row in similarity_review_hints
                if ordinal in row["candidate_ordinals"]
            ]
        if any(row.get("decision") != "PASS" for row in validations):
            return reject({"envelope": output, "validations": validations})
        self.repository.save_candidate_set(
            run_id=run.run_id,
            account_id=run.account_id,
            plan_ref=run.plan_ref,
            candidates=candidates,
            validations=validations,
            preserved_revalidation_digest=(
                output_digest if preserved_revalidation else None
            ),
            preserved_revalidation_payload=(
                {
                    "repair_id": "PKG7-DIVERGENCE-CATEGORY-FALSE-REJECT-001",
                    "model_output_unchanged": True,
                    "model_call_count_increment": 0,
                    "validations": validations,
                    "normalization": normalization,
                    **copy.deepcopy(preserved_revalidation_details or {}),
                }
                if preserved_revalidation
                else None
            ),
        )
        if not preserved_revalidation:
            self.repository.preserve_first_output(
                run.run_id,
                output_digest,
                "FIRST_OUTPUT_ACCEPTED",
                {
                    "envelope": output,
                    "validations": validations,
                    "model_wrapper_normalization": normalization,
                    "similarity_review_hints": similarity_review_hints,
                },
            )
        return {
            "response_kind": "DIRECT",
            "user_visible_text": self._render_candidates(candidates),
            "ui_state": "result",
            "candidates": self._candidate_workbench(
                self.repository.latest_candidates(run.principal_id, run.account_id)
            ),
            "series": self._series_projection(task_brief),
        }

    @staticmethod
    def _candidate_workbench(
        candidates: tuple[RuntimeCandidate, ...],
    ) -> list[JsonObject]:
        result: list[JsonObject] = []
        for candidate in candidates:
            surfaces = candidate.candidate_payload.get(
                "candidate_user_visible_surfaces", {}
            )
            package = surfaces.get("execution_payload", {})
            if not isinstance(surfaces, dict) or not isinstance(package, dict):
                continue
            result.append(
                {
                    "key": f"candidate-{candidate.ordinal}",
                    "ordinal": candidate.ordinal,
                    "label": (
                        "推荐候选" if candidate.ordinal == 1 else f"备选{candidate.ordinal - 1}"
                    ),
                    "selected": candidate.selected,
                    "creative_difference": str(
                        candidate.candidate_payload.get("creative_difference", "")
                    ),
                    "content_format": str(package.get("production_format", "")),
                    "candidate_user_visible_surfaces": copy.deepcopy(surfaces),
                }
            )
        return result

    @staticmethod
    def _series_projection(task_brief: JsonObject) -> JsonObject:
        mode = str(task_brief.get("series_mode", "SINGLE"))
        episode_index = int(task_brief.get("episode_index", 1))
        outline = task_brief.get("series_outline", [])
        return {
            "mode": mode,
            "outline": copy.deepcopy(outline) if isinstance(outline, list) else [],
            "current_episode": episode_index,
            "next_episode": episode_index + 1 if mode == "SERIES" and episode_index < 3 else None,
        }

    def _previous_version(self, principal_id: str, account_id: str) -> JsonObject:
        previous = self.repository.previous_candidates(principal_id, account_id)
        if not previous:
            return {
                "response_kind": "DIRECT",
                "user_visible_text": "当前还没有更早的版本。",
                "ui_state": "result",
                "candidates": [],
            }
        return {
            "response_kind": "DIRECT",
            "user_visible_text": "已显示上一版；当前版本仍保留，不会被覆盖。",
            "ui_state": "result",
            "candidates": self._candidate_workbench(previous),
            "viewing_previous_version": True,
        }

    @staticmethod
    def _render_candidates(candidates: list[JsonObject]) -> str:
        candidate_count = len(candidates)
        opening = (
            "已准备好1份候选。它仍是内部测试内容，请自行检查后使用。"
            if candidate_count == 1
            else "已准备好推荐候选和备选。它们仍是内部测试内容，请自行检查后使用。"
        )
        blocks = [opening]
        for ordinal, candidate in enumerate(candidates, 1):
            surfaces = candidate["candidate_user_visible_surfaces"]
            package = surfaces["execution_payload"]
            prefix = (
                "候选1"
                if candidate_count == 1
                else ("推荐候选" if ordinal == 1 else f"备选{ordinal - 1}")
            )
            blocks.append(
                f"\n【{prefix}】\n标题：{surfaces['title']}\n"
                f"首屏或封面：{package['cover_or_first_screen_copy']}\n"
                f"正文或完整脚本：{surfaces['body']}\n"
                f"{Package7Runtime._format_production_package(package)}\n"
                f"使用平台与时长：{package['target_platform']}｜{package['duration_label']}\n"
                f"结尾与行动：{package['ending_and_action']}\n"
                f"发布辅助文案：{package['publishing_copy']}\n"
                f"接下来可以：{'、'.join(package['next_actions'])}"
            )
        if candidate_count == 1:
            blocks.append("\n可以直接点选候选卡片，也可以说明想局部修改哪里。")
        else:
            blocks.append("\n可以直接点选喜欢的候选卡片，也可以说明想局部修改哪里。")
        return "\n".join(blocks)

    @staticmethod
    def _format_production_package(package: JsonObject) -> str:
        if package.get("production_format") == "短视频":
            shots = package.get("video", {}).get("shots", [])
            lines = ["分镜："]
            for index, shot in enumerate(shots, 1):
                lines.append(
                    f"{index}. {shot['time_range']}\n"
                    f"画面：{shot['visual']}\n"
                    f"动作：{shot['action']}\n"
                    f"台词或声音：{shot['audio']}\n"
                    f"字幕：{shot['subtitle']}\n"
                    f"拍摄方式：{shot['camera']}\n"
                    f"剪辑提示：{shot['edit_note']}"
                )
            video = package.get("video", {})
            lines.append(
                "拍摄补充：" + "；".join(video.get("shooting_notes", []))
            )
            lines.append(
                "剪辑补充：" + "；".join(video.get("editing_notes", []))
            )
            return "\n".join(lines)
        if package.get("production_format") == "图文":
            article = package.get("article", {})
            frames = article.get("frames", [])
            lines = [f"封面画面：{article.get('cover_brief', '')}", "图片顺序与配文："]
            for frame in frames:
                lines.append(
                    f"{frame['order']}. {frame['image_brief']}｜{frame['accompanying_copy']}"
                )
            lines.append("版式建议：" + "；".join(article.get("layout_notes", [])))
            return "\n".join(lines)
        if package.get("production_format") == "直播内容包":
            live = package.get("live", {})
            segments = "\n".join(
                f"{index}. {row.get('segment_title', '')}｜"
                f"{'；'.join(row.get('talking_points', []))}｜互动：{row.get('interaction_prompt', '')}"
                for index, row in enumerate(live.get("segments", []), 1)
            )
            return (
                f"直播主题：{live.get('theme', '')}\n开场：{live.get('opening', '')}\n"
                f"环节：\n{segments}\n"
                f"互动问答：{'；'.join(live.get('interaction_qa', []))}\n"
                f"风险提醒：{'；'.join(live.get('risk_reminders', []))}\n"
                f"收束：{live.get('closing', '')}"
            )
        if package.get("production_format") == "私域沟通内容":
            private = package.get("private_communication", {})
            messages = "\n".join(
                f"{row.get('channel', '')}：{row.get('copy', '')}"
                for row in private.get("messages", [])
            )
            return (
                f"适用场景：{private.get('applicable_scenario', '')}\n{messages}\n"
                f"后续动作：{'；'.join(private.get('follow_up_actions', []))}\n"
                f"沟通边界：{'；'.join(private.get('communication_boundaries', []))}"
            )
        if package.get("production_format") == "门店线下物料":
            offline = package.get("offline_material", {})
            return (
                f"核心文案：{offline.get('core_copy', '')}\n"
                f"信息顺序：{' → '.join(offline.get('information_hierarchy', []))}\n"
                f"版面或摆放建议：{'；'.join(offline.get('layout_or_placement_notes', []))}\n"
                f"行动提示：{offline.get('action_guidance', '')}\n"
                f"有效边界：{offline.get('validity_boundary', '')}"
            )
        if package.get("production_format") == "培训与门店话术":
            training = package.get("training", {})
            questions = "\n".join(
                f"问：{row.get('question', '')}\n答：{row.get('suggested_answer', '')}"
                for row in training.get("situational_qa", [])
            )
            return (
                f"培训目标：{training.get('training_goal', '')}\n"
                f"提纲：{'；'.join(training.get('outline', []))}\n"
                f"练习：{'；'.join(training.get('exercises', []))}\n{questions}\n"
                f"可以这样说：{'；'.join(training.get('allowed_phrasing', []))}\n"
                f"不要这样说：{'；'.join(training.get('prohibited_phrasing', []))}"
            )
        display = package.get("display", {})
        return (
            "陈列执行：\n"
            f"适用对象：{'；'.join(display.get('referenced_items_or_facts', []))}\n"
            f"关系：{display.get('arrangement_relationship', '')}\n"
            f"层次：{display.get('spatial_layers', '')}\n"
            f"颜色：{display.get('color_relationship', '')}\n"
            f"可用性提醒：{display.get('availability_caution', '')}\n"
            f"拍摄角度：{'；'.join(display.get('shooting_angles', []))}"
        )

    def _export_selected(self, principal_id: str, account_id: str) -> JsonObject:
        selected = self.repository.selected_candidate(principal_id, account_id)
        if selected is None:
            return self._failure_result("AUTHORIZATION_OR_SCOPE_BLOCK", None)
        self.repository.record_selected_candidate_activity(
            principal_id=principal_id,
            account_id=account_id,
            operation="EXPORT",
        )
        surfaces = selected.candidate_payload["candidate_user_visible_surfaces"]
        package = surfaces["execution_payload"]
        spoken = "\n".join(f"- {line}" for line in surfaces.get("spoken_lines", []))
        export_text = (
            f"标题\n{surfaces['title']}\n\n正文\n{surfaces['body']}\n\n"
            f"口播\n{spoken or '无单独口播'}\n\n"
            f"结尾\n{surfaces.get('CTA') or package['ending_and_action']}\n\n"
            f"制作安排\n{self._format_production_package(package)}\n\n"
            f"发布辅助文案\n{package['publishing_copy']}\n\n"
            "内部测试稿，不可直接发布。"
        )
        return {
            "response_kind": "DIRECT",
            "user_visible_text": export_text,
            "ui_state": "result",
            "export_text": export_text,
            "candidates": self._candidate_workbench((selected,)),
        }

    def _source_lookup(self, principal_id: str, account_id: str) -> JsonObject:
        selected = self.repository.selected_candidate(principal_id, account_id)
        if selected is None:
            return self._failure_result("AUTHORIZATION_OR_SCOPE_BLOCK", None)
        self.repository.record_selected_candidate_activity(
            principal_id=principal_id,
            account_id=account_id,
            operation="REFERENCE_LOOKUP",
        )
        rows = self.repository.narrative_fragments(list(selected.used_material_refs))
        facts = {row["fact_id"]: row for row in self.repository.precise_facts()}
        labels = [
            f"资料{index}｜品牌资料｜记录于 {str(row.get('observed_at', ''))[:10]}｜当前范围可用"
            for index, row in enumerate(rows, 1)
        ]
        fact_labels = {
            "SKU": "商品编号",
            "SPECIFICATION": "商品规格",
            "PRICE": "价格",
            "STOCK": "库存",
            "TIME_POINT": "时间点",
            "AUTHORIZATION": "账号身份与范围",
            "REVOCATION": "撤回状态",
        }
        labels.extend(
            f"精确事实｜{fact_labels.get(str(facts[ref]['fact_kind']), '已确认记录')}｜"
            f"生效于 {str(facts[ref]['effective_at'])[:10]}｜当前范围可用"
            for ref in selected.used_fact_refs
            if ref in facts
        )
        return {
            "response_kind": "DIRECT",
            "user_visible_text": (
                "本次参考资料范围（不代表逐句证明全文）：\n"
                + ("\n".join(labels) if labels else "这份候选没有使用品牌资料。")
            ),
        }

    def _plain_action(self, action_type: str) -> JsonObject:
        if action_type in {
            "COLLECT_FACT",
            "COLLECT_MATERIAL",
            "INTERVIEW",
            "RESHOOT",
            "DEGRADE",
        }:
            result_class = "MATERIAL_GAP"
        elif action_type in {"REQUEST_AUTHORIZATION", "ANONYMIZE", "BLOCK"}:
            result_class = "AUTHORIZATION_OR_SCOPE_BLOCK"
        else:
            return self._failure_result("SYSTEM_OR_PROVIDER_ERROR", None)
        card = self.action_cards.get(action_type)
        if card is None:
            return self._failure_result("SYSTEM_OR_PROVIDER_ERROR", None)
        return {
            "response_kind": "DIRECT",
            "result_class": result_class,
            "user_visible_text": (
                f"{card['user_visible_title']}\n{card['user_visible_reason']}\n"
                f"下一步：{card['user_visible_next_action']}"
            ),
            "action_card": result_class == "MATERIAL_GAP",
        }

    @staticmethod
    def _missing_object_result() -> JsonObject:
        return {
            "response_kind": "DIRECT",
            "result_class": "MATERIAL_GAP",
            "user_visible_text": (
                "补充指定素材\n本次任务明确要求使用的文件、图片或视频尚未提供。\n"
                "下一步：上传对应对象后再继续；普通创作不受影响。"
            ),
            "action_card": True,
        }

    @staticmethod
    def _failure_result(
        result_class: str,
        run_id: str | None,
    ) -> JsonObject:
        messages = {
            "MATERIAL_GAP": "现有资料还不足以完成这项内容，请按补料提示补充后再继续。",
            "AUTHORIZATION_OR_SCOPE_BLOCK": "当前账号、使用范围或授权条件不成立，已停止本次操作。",
            "MODEL_OUTPUT_CONTRACT_ERROR": "内容模型已经返回，但系统未能稳定接收其格式；无需补资料，请由系统处理。",
            "HARD_FACT_REFERENCE_ERROR": "候选中出现当前资料无法支持的明确事实、内部编号或真实敏感信息，已停止使用。",
            "SYSTEM_OR_PROVIDER_ERROR": "当前系统或模型服务未完成处理，请稍后重试或由系统维护人员处理。",
        }
        message = messages.get(result_class, messages["SYSTEM_OR_PROVIDER_ERROR"])
        return {
            "response_kind": "DIRECT",
            "result_class": result_class,
            "run_id": run_id,
            "user_visible_text": message,
            "action_card": result_class == "MATERIAL_GAP",
        }

    @staticmethod
    def _access(principal_id: str, account_id: str) -> ServerPlanAccess:
        return ServerPlanAccess(
            authority_source=SERVER_ACCESS_AUTHORITY,
            principal_id=principal_id,
            content_account_id=account_id,
        )

    def _brand_profile_for_account(self, brand_id: str) -> JsonObject:
        try:
            profile = self.repository.setting(f"brand_expression_profile:{brand_id}")
        except KeyError:
            return self.repository.setting("neutral_expression_profile")
        if profile.get("brand_id") != brand_id:
            raise RuntimeContractError("Brand profile isolation failed")
        return profile

    @staticmethod
    def _role_card(
        profile: JsonObject,
        account: JsonObject,
        requested_role_id: str | None,
        requested_role_name: str | None,
    ) -> JsonObject:
        account_id = str(account["account_id"])
        account_card = next(
            (
                row
                for row in profile.get("account_role_cards", [])
                if row.get("account_id") == account_id
            ),
            None,
        )
        if not isinstance(account_card, dict):
            maker_role_ids = account.get("maker_role_ids")
            if (
                not isinstance(maker_role_ids, list)
                or not maker_role_ids
                or requested_role_id not in {None, maker_role_ids[0]}
                or requested_role_name
                not in {None, account.get("persona_display_name")}
            ):
                raise RuntimeContractError("Account role card is unavailable")
            return {
                "role_id": str(maker_role_ids[0]),
                "display_name": str(
                    account.get("persona_display_name")
                    or account.get("outward_account_name")
                    or account.get("display_name")
                ),
                "boundary": (
                    "只以当前账号和组织范围表达，不冒充其他组织或真实个人经历。"
                ),
            }
        named_role = next(
            (
                row
                for row in profile.get("principal_roles", [])
                if requested_role_name is not None
                and row.get("display_name") == requested_role_name
            ),
            None,
        )
        if requested_role_name is not None and not isinstance(named_role, dict):
            raise RuntimeContractError("Requested role name is unavailable")
        role_id = requested_role_id or (
            str(named_role["role_id"])
            if isinstance(named_role, dict)
            else str(account_card["default_role_id"])
        )
        if role_id != account_card["default_role_id"]:
            raise RuntimeContractError(
                "Requested role is outside the account role card"
            )
        role = next(
            (
                row
                for row in profile.get("principal_roles", [])
                if row.get("role_id") == role_id
            ),
            None,
        )
        if not isinstance(role, dict):
            raise RuntimeContractError("Brand role is unavailable")
        return copy.deepcopy(role)

    @staticmethod
    def _storyline(
        profile: JsonObject,
        requested_storyline_id: str | None,
        requested_storyline_name: str | None,
    ) -> JsonObject:
        rows = profile.get("storylines", [])
        if requested_storyline_id is not None:
            row = next(
                (
                    item
                    for item in rows
                    if item.get("storyline_id") == requested_storyline_id
                ),
                None,
            )
        elif requested_storyline_name is not None:
            row = next(
                (
                    item
                    for item in rows
                    if item.get("display_name") == requested_storyline_name
                ),
                None,
            )
        else:
            row = rows[0] if rows else None
        if not isinstance(row, dict):
            raise RuntimeContractError("Long-term storyline is unavailable")
        return copy.deepcopy(row)

    @staticmethod
    def _column(
        profile: JsonObject,
        requested_column_id: str | None,
        requested_column_name: str | None,
        storyline_id: str,
    ) -> JsonObject:
        rows = profile.get("columns", [])
        row = next(
            (
                item
                for item in rows
                if item.get("column_id") == requested_column_id
                or (
                    requested_column_id is None
                    and requested_column_name is not None
                    and item.get("display_name") == requested_column_name
                )
                or (
                    requested_column_id is None
                    and requested_column_name is None
                    and item.get("storyline_id") == storyline_id
                )
            ),
            None,
        )
        if not isinstance(row, dict) or row.get("storyline_id") != storyline_id:
            raise RuntimeContractError(
                "Column does not belong to the selected storyline"
            )
        return copy.deepcopy(row)

    @staticmethod
    def _public_brand_guidance(profile: JsonObject) -> JsonObject:
        proposition = copy.deepcopy(profile.get("operating_proposition", {}))
        protections = copy.deepcopy(profile.get("hard_protections", {}))
        if isinstance(proposition, dict):
            proposition.pop("evidence_refs", None)
            proposition.pop("source_refs", None)
        if isinstance(protections, dict):
            protections.pop("evidence_refs", None)
            protections.pop("source_refs", None)
        return {
            "operating_proposition": proposition,
            "hard_protections": protections,
            "tone_tendencies": copy.deepcopy(profile.get("tone_tendencies", [])),
            "preferred_phrasing": copy.deepcopy(profile.get("preferred_phrasing", [])),
            "prohibited_expression_categories": copy.deepcopy(
                profile.get("prohibited_expression_categories", [])
            ),
        }

    @staticmethod
    def _precise_fact_queries(
        request: BridgePrepareRequest, account: JsonObject
    ) -> list[JsonObject]:
        del account
        return [row.model_dump() for row in request.precise_fact_requests]

    @staticmethod
    def _scope_identity_only_request(request: BridgePrepareRequest) -> bool:
        """Allow a narrow account-introduction task without narrative material."""

        text = " ".join(
            value
            for value in (request.message, request.content_goal, request.key_takeaway)
            if isinstance(value, str)
        )
        return any(
            phrase in text
            for phrase in (
                "账号介绍",
                "账号说明",
                "账号身份",
                "账号范围",
                "内容边界",
                "能讲什么",
                "可以讲什么",
                "内容原则",
            )
        )

    @staticmethod
    def _explicit_required_object_missing(request: BridgePrepareRequest) -> bool:
        """Ask for material only when the task names an unavailable concrete object."""

        if request.user_material_refs:
            return False
        text = " ".join(
            value
            for value in (request.message, request.content_goal, request.key_takeaway)
            if isinstance(value, str)
        )
        return EXPLICIT_REQUIRED_OBJECT_PATTERN.search(text) is not None

    @staticmethod
    def _rhythm_for_duration(duration_label: str) -> str:
        return "compact" if duration_label in {"15秒左右", "30秒左右"} else "natural"

    @staticmethod
    def _intensity_for_feeling(expression_feeling: str) -> str:
        return (
            "warm" if expression_feeling in {"生活分享", "情绪故事"} else "restrained"
        )

    @staticmethod
    def _new_run_id(
        principal_id: str, account_id: str, operation: str, message: str
    ) -> str:
        seed = [
            principal_id,
            account_id,
            operation,
            message,
            datetime.now(timezone.utc).isoformat(),
        ]
        return f"RUN-{digest_object(seed)[:24].upper()}"
