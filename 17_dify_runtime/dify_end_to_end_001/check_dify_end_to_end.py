#!/usr/bin/env python3
"""Fail-closed checker for the Package 7 Dify end-to-end candidate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, cast

import yaml  # type: ignore[import-untyped]


if not __debug__:
    sys.stderr.write("check_dify_end_to_end refuses python -O\n")
    raise SystemExit(2)


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_RELATIVE_ROOT = Path("17_dify_runtime/dify_end_to_end_001")
TASK_ID = "DIYU_DIFY_END_TO_END_001"
BASELINE_COMMIT = "a8fe258b8f8693247a46f1dbba3c2553b778bfaa"

MANIFEST_PATH = Path("dify_end_to_end_manifest.v1.json")
EXTERNAL_EVIDENCE_PATH = Path("evidence/external_runtime_evidence.v1.json")
MODEL_EVIDENCE_PATH = Path("evidence/model_run_evidence.v1.json")
RESULT_PATH = Path("result/dify_end_to_end_result.v1.json")
DELIVERY_PATH = Path("delivery/execution_review_request.v1.yaml")
REVIEW_PATHS = (
    Path("review/content_experience_and_organization_review.v1.yaml"),
    Path("review/trust_fact_authorization_runtime_review.v1.yaml"),
)
REVIEW_TYPES = {
    "CONTENT_EXPERIENCE_AND_ORGANIZATION",
    "TRUST_FACT_AUTHORIZATION_PRIVACY_AND_RUNTIME",
}
REQUIRED_FALSE_FLAGS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "generator_qualified",
        "retrieval_ready",
        "runtime_ready",
        "release_ready",
        "production_ready",
    }
)
EXPECTED_PACKAGE_FILES = frozenset(
    {
        Path("brand_import.py"),
        Path("brand_import_contract.v1.yaml"),
        Path("brand_runtime_profile.v1.yaml"),
        Path("bridge_app.py"),
        Path("check_dify_end_to_end.py"),
        Path("contracts.py"),
        Path("deploy_remote.sh"),
        Path("dify_app.v1.yaml"),
        Path("dify_chat.py"),
        Path("dify_end_to_end_manifest.v1.json"),
        Path("dify_knowledge.py"),
        Path("persistence.py"),
        Path("portal.css"),
        Path("portal.html"),
        Path("portal.js"),
        Path("provision_dify.py"),
        Path("runtime_models.py"),
        Path("runtime_retrieval.py"),
        Path("runtime_service.py"),
        Path("security.py"),
        Path("seed_runtime.py"),
        Path("test_dify_end_to_end.py"),
        EXTERNAL_EVIDENCE_PATH,
        MODEL_EVIDENCE_PATH,
        RESULT_PATH,
        DELIVERY_PATH,
        *REVIEW_PATHS,
    }
)

RECOVERY_TASK_ID = "DIYU_DIFY_END_TO_END_OUTPUT_CONTRACT_RECOVERY_002"
RECOVERY_BASELINE_COMMIT = "0f066c6ee2e871ad67be3ae07ed80df1153b4df1"
HISTORICAL_PACKAGE7_COMMIT = "f046ec6e3d1a34345c97292e9ab1f5a13a2bd031"
FAILED_PACKAGE10_COMMIT = "82b253c2b0ac362f1c5397bafb789ee400453944"
FAILED_PACKAGE10_EVIDENCE_SHA256 = (
    "46147ee16d9ae70a1d93d0f0689ae5e8de229608978d299fc0d312998e991cea"
)
RECOVERY_ROOT = Path("output_contract_recovery_002")
RECOVERY_REPLAY_PATH = RECOVERY_ROOT / "evidence/p10_zero_call_replay.v1.json"
RECOVERY_LOCAL_EVIDENCE_PATH = RECOVERY_ROOT / "evidence/local_acceptance.v1.json"
RECOVERY_PRIOR_REMOTE_EVIDENCE_PATH = RECOVERY_ROOT / "evidence/remote_probe.v1.json"
RECOVERY_REMOTE_EVIDENCE_PATH = RECOVERY_ROOT / "evidence/remote_probe.v2.json"
RECOVERY_PRIOR_RESULT_PATH = RECOVERY_ROOT / "result/output_contract_recovery_result.v1.json"
RECOVERY_RESULT_PATH = RECOVERY_ROOT / "result/output_contract_recovery_result.v2.json"
RECOVERY_PRIOR_DELIVERY_PATH = RECOVERY_ROOT / "delivery/execution_review_request.v1.yaml"
RECOVERY_DELIVERY_PATH = RECOVERY_ROOT / "delivery/execution_review_request.v2.yaml"
RECOVERY_PRIOR_REVIEW_PATHS = (
    RECOVERY_ROOT / "review/content_novice_review.v1.yaml",
    RECOVERY_ROOT / "review/trust_isolation_review.v1.yaml",
)
RECOVERY_REVIEW_PATHS = (
    RECOVERY_ROOT / "review/content_novice_review.v2.yaml",
    RECOVERY_ROOT / "review/trust_isolation_review.v2.yaml",
)
RECOVERY_REVIEW_TYPES = {
    "CONTENT_NOVICE_SEVEN_FORMATS_AND_CREATIVE_FREEDOM",
    "TRUST_RUNTIME_IDENTITY_DATA_ACCESS_PRIVACY_SESSION_AND_OPERATIONS",
}
RECOVERY_SUCCESS_STATE = "PASS_TO_NEW_PACKAGE10_EVALUATION_DRAFT_ONLY"
RECOVERY_DEGRADED_STATE = "PASS_TO_NEW_PACKAGE10_WITH_OFFLINE_MATERIAL_DISABLED"
RECOVERY_PRIOR_REVIEW_EVIDENCE_COMMIT = (
    "dfe35f82e09e9bc190a1b99e543b2ab0a109291a"
)
RECOVERY_PRIOR_ARTIFACT_COMMIT = "b7d61ef086e5d1ac618f4660117f7b161e387b25"
RECOVERY_PRIOR_REVIEWED_CANDIDATE_COMMIT = (
    "b14a3bfc2ffe1acdb9b56337f16fc07493e0f374"
)
RECOVERY_PRIOR_REVIEWED_CANDIDATE_TREE = (
    "4a4e3ddf7b75e4a1451571e5640ed513044c7b89"
)
RECOVERY_RESULT_CLASSES = {
    "MATERIAL_GAP",
    "AUTHORIZATION_OR_SCOPE_BLOCK",
    "MODEL_OUTPUT_CONTRACT_ERROR",
    "HARD_FACT_REFERENCE_ERROR",
    "SYSTEM_OR_PROVIDER_ERROR",
}
RECOVERY_FORMATS = (
    "短视频",
    "图文",
    "直播内容包",
    "私域沟通内容",
    "门店线下物料",
    "培训与门店话术",
    "陈列搭配",
)
RECOVERY_IMPLEMENTATION_FILES = frozenset(
    {
        Path("author_contract.py"),
        Path("content_capability_mapping.v1.yaml"),
        Path("bridge_app.py"),
        Path("contracts.py"),
        Path("persistence.py"),
        Path("portal.html"),
        Path("portal.js"),
        Path("runtime_models.py"),
        Path("runtime_service.py"),
        Path("security.py"),
        Path("test_dify_end_to_end.py"),
        Path("check_dify_end_to_end.py"),
    }
)
RECOVERY_DELIVERY_FILES = frozenset(
    {
        RECOVERY_REPLAY_PATH,
        RECOVERY_LOCAL_EVIDENCE_PATH,
        RECOVERY_PRIOR_REMOTE_EVIDENCE_PATH,
        RECOVERY_REMOTE_EVIDENCE_PATH,
        RECOVERY_PRIOR_RESULT_PATH,
        RECOVERY_RESULT_PATH,
        RECOVERY_PRIOR_DELIVERY_PATH,
        RECOVERY_DELIVERY_PATH,
        *RECOVERY_PRIOR_REVIEW_PATHS,
        *RECOVERY_REVIEW_PATHS,
    }
)
RECOVERY_EXPECTED_PACKAGE_FILES = (
    EXPECTED_PACKAGE_FILES | RECOVERY_IMPLEMENTATION_FILES | RECOVERY_DELIVERY_FILES
)
ACCOUNT_PERSONA_TASK_ID = "DIYU_ACCOUNT_PERSONA_UI_AND_NO_APPROVAL_FLOW_001"
ACCOUNT_PERSONA_BASELINE_COMMIT = "bb11e8cdfd9584136c0be85d4d7fcfc52caf614c"
ACCOUNT_PERSONA_RESULT_PATH = Path(
    "result/account_persona_ui_no_approval_result.v1.json"
)
ACCOUNT_PERSONA_DELIVERY_PATH = Path(
    "delivery/account_persona_ui_no_approval_execution_review_request.v1.yaml"
)
ACCOUNT_PERSONA_SCREENSHOT_PATHS = (
    Path("result/account_persona_ui_screenshots/admin-desktop.png"),
    Path("result/account_persona_ui_screenshots/professional-desktop.png"),
    Path("result/account_persona_ui_screenshots/franchise-desktop.png"),
    Path("result/account_persona_ui_screenshots/mobile-result.png"),
)
ACCOUNT_PERSONA_EXPECTED_PACKAGE_FILES = RECOVERY_EXPECTED_PACKAGE_FILES | {
    ACCOUNT_PERSONA_RESULT_PATH,
    ACCOUNT_PERSONA_DELIVERY_PATH,
    *ACCOUNT_PERSONA_SCREENSHOT_PATHS,
}
ACCOUNT_PERSONA_FAMILIES = {
    "ENTERPRISE_ADMIN",
    "HEADQUARTERS_BRAND",
    "FOUNDER",
    "HEADQUARTERS_PROFESSIONAL_PERSONA",
    "PROVINCIAL_AGENT",
    "HEADQUARTERS_DIRECT_STORE",
    "FRANCHISE_STORE",
}
ACCOUNT_PERSONA_REVIEW_TYPES = {
    "ACCOUNT_PRODUCT_STRUCTURE_AND_NOVICE_EXPERIENCE",
    "ISOLATION_CONTRACT_COMPATIBILITY_AND_NO_APPROVAL",
}
RECOVERY_HISTORICAL_FROZEN_FILES = frozenset(
    {
        MANIFEST_PATH,
        EXTERNAL_EVIDENCE_PATH,
        MODEL_EVIDENCE_PATH,
        RESULT_PATH,
        DELIVERY_PATH,
        *REVIEW_PATHS,
    }
)
RECOVERY_AUTHORIZED_REPOSITORY_PATHS = frozenset(
    {
        Path("AGENTS.md"),
        Path(".github/workflows/ci.yml"),
        Path("ci/checkers/check_product_foundation.py"),
        Path("ci/checkers/check_gate1_v1_1_current.py"),
        Path("project-infra/current_product_status.v1.yaml"),
        Path(
            "20_internal_pilot/release_evaluation_001/"
            "result/package10_final_closeout_result.v1.json"
        ),
        Path(
            "20_internal_pilot/release_evaluation_001/"
            "review/content_competitiveness_apparel_review.v1.json"
        ),
        Path(
            "20_internal_pilot/release_evaluation_001/"
            "review/novice_isolation_operations_review.v1.json"
        ),
        Path(
            "20_internal_pilot/release_evaluation_001/"
            "delivery/internal_production_entry.v1.yaml"
        ),
    }
)
PACKAGE10_FINAL_CLOSEOUT_PATHS = frozenset(
    path
    for path in RECOVERY_AUTHORIZED_REPOSITORY_PATHS
    if Path("20_internal_pilot/release_evaluation_001") in path.parents
)
PACKAGE10_FINAL_RUNTIME_PATHS = frozenset(
    {
        PACKAGE_RELATIVE_ROOT / "author_contract.py",
        PACKAGE_RELATIVE_ROOT / "bridge_app.py",
        PACKAGE_RELATIVE_ROOT / "check_dify_end_to_end.py",
        PACKAGE_RELATIVE_ROOT / "content_capability_mapping.v1.yaml",
        PACKAGE_RELATIVE_ROOT / "contracts.py",
        PACKAGE_RELATIVE_ROOT / "dify_app.v1.yaml",
        PACKAGE_RELATIVE_ROOT / "portal.js",
        PACKAGE_RELATIVE_ROOT / "runtime_service.py",
        PACKAGE_RELATIVE_ROOT / "test_dify_end_to_end.py",
    }
)
POST_CANDIDATE_ALLOWED_PATHS = frozenset(
    {PACKAGE_RELATIVE_ROOT / RESULT_PATH, PACKAGE_RELATIVE_ROOT / DELIVERY_PATH}
    | {PACKAGE_RELATIVE_ROOT / path for path in REVIEW_PATHS}
)
AUTHORIZED_COMPATIBILITY_PATHS = frozenset(
    {
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "light_expression_service.py"
        ),
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "test_light_expression_service.py"
        ),
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "check_light_expression_service.py"
        ),
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "service_manifest.v1.yaml"
        ),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "fact_aware_plan_adapter.py"
        ),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "test_fact_aware_plan_adapter.py"
        ),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "check_fact_aware_plan_adapter.py"
        ),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "adapter_manifest.v1.yaml"
        ),
        Path("ci/checkers/check_product_foundation.py"),
        Path("ci/checkers/check_gate1_v1_1_current.py"),
        Path(".github/workflows/ci.yml"),
    }
)
EXPECTED_FORMATS = {
    "article": ("图文", "article"),
    "display": ("陈列搭配", "display"),
    "short_video": ("短视频", "video"),
}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"Bearer [A-Za-z0-9._-]{20,}"),
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
CONDITIONAL_AUTHORIZATION_PATTERN = re.compile(
    r"^(?:建议|计划)?(?:如有|若有|如果有|假如有|仅在有).{0,24}(?:已授权|经授权|获准|批准|允许)"
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
KEY_FACT_CONTEXT_PATTERN = re.compile(
    r"(?:售价|价格|库存|现货|可售|售罄|剩余|尺码|规格|身高|年龄|日期|截至|折扣|比例|承诺)"
)


class CheckFailure(RuntimeError):
    """Raised by one fail-closed validation boundary."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CheckFailure(code)


def require_fields(
    value: Mapping[str, Any], required: Iterable[str], code: str
) -> None:
    missing = sorted(set(required) - set(value))
    require(not missing, f"{code}:{missing}")


def high_risk_fact_clauses(path: str, text: str) -> tuple[str, ...]:
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
    return bool(high_risk_fact_clauses(path, text))


def surface_text_map(surfaces: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}

    def visit(value: object, path: str) -> None:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                result[path] = normalized
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
            return
        if isinstance(value, dict):
            for key, child in value.items():
                if key != "surface_units":
                    visit(child, f"{path}.{key}" if path else str(key))

    visit(surfaces, "")
    return result


def load_json(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"E_JSON_OBJECT:{path}")
    return cast(JsonObject, value)


def load_yaml_root(path: Path, root_key: str) -> JsonObject:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(
        isinstance(value, dict) and isinstance(value.get(root_key), dict),
        f"E_YAML_ROOT:{path}:{root_key}",
    )
    return cast(JsonObject, value[root_key])


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_output(*args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    require(process.returncode == 0, f"E_GIT:{' '.join(args)}:{process.stderr.strip()}")
    return process.stdout.strip()


def candidate_tree(candidate_commit: str) -> str:
    return git_output("rev-parse", f"{candidate_commit}^{{tree}}")


def validate_file_set(root: Path) -> None:
    actual = {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    require(
        actual == EXPECTED_PACKAGE_FILES,
        f"E_FILE_SET:{sorted(map(str, actual ^ EXPECTED_PACKAGE_FILES))}",
    )
    require(not list(root.rglob("*.pyc")), "E_BYTECODE_PRESENT")
    require(not list(root.rglob("__pycache__")), "E_PYCACHE_PRESENT")


def validate_readiness(value: Mapping[str, Any], code: str) -> None:
    require(set(value) == REQUIRED_FALSE_FLAGS, f"{code}:FLAG_SET")
    for key in REQUIRED_FALSE_FLAGS:
        require(value.get(key) is False, f"{code}:{key}")


def validate_core_numbers(value: Mapping[str, Any], code: str) -> None:
    require(value.get("target_total") == 300, f"{code}:300")
    require(value.get("reference_inventory") == 120, f"{code}:120")
    require(value.get("historical_component_inventory") == 86, f"{code}:86")
    require(value.get("changed") is False, f"{code}:CHANGED")


def validate_manifest(manifest: JsonObject) -> None:
    require(
        manifest.get("schema") == "diyu.package7.dify_end_to_end_manifest.v1",
        "E_MANIFEST_SCHEMA",
    )
    require(manifest.get("task_id") == TASK_ID, "E_MANIFEST_TASK")
    require(manifest.get("package_number") == 7, "E_MANIFEST_PACKAGE")
    require(
        manifest.get("baseline_master_commit") == BASELINE_COMMIT, "E_MANIFEST_BASELINE"
    )
    require(
        manifest.get("package_root") == PACKAGE_RELATIVE_ROOT.as_posix(),
        "E_MANIFEST_ROOT",
    )
    candidate = cast(Mapping[str, Any], manifest.get("single_candidate", {}))
    require(
        candidate.get("dify_app_id") == "98eb36f1-50b7-42ca-8184-976512fbef9d",
        "E_APP_ID",
    )
    require(
        candidate.get("dataset_id") == "3c9d73cc-c120-4f84-81a1-1bc95f7b6d4b",
        "E_DATASET_ID",
    )
    require(candidate.get("runtime_database") == "diyu_pkg7_runtime", "E_DATABASE_ID")
    require(candidate.get("runtime_bridge") == "diyu-package7-bridge", "E_BRIDGE_ID")
    require(candidate.get("api_only") is True, "E_API_ONLY")
    require(candidate.get("simulation_only") is True, "E_SIMULATION_ONLY")
    require(candidate.get("production_ready") is False, "E_CANDIDATE_PRODUCTION")
    ownership = cast(Mapping[str, Any], manifest.get("ownership", {}))
    for key in (
        "package2_owns_light_content_plan_and_validation",
        "package5_owns_retrieval_contract_and_scope_filtering",
        "package6_owns_fact_aware_plan_adaptation",
        "package7_owns_only_runtime_persistence_dify_bridge_and_portal",
    ):
        require(ownership.get(key) is True, f"E_OWNERSHIP:{key}")
    for key in (
        "second_plan_created",
        "second_retrieval_truth_created",
        "second_bridge_created",
    ):
        require(ownership.get(key) is False, f"E_PARALLEL_OWNER:{key}")
    contracts = cast(Mapping[str, Any], manifest.get("contracts", {}))
    require(contracts.get("content_product_count") == 20, "E_CONTRACT_CP")
    require(contracts.get("topic_count") == 8, "E_CONTRACT_TOPIC")
    require(contracts.get("action_card_count") == 8, "E_CONTRACT_ACTION")
    require(contracts.get("content_account_count") == 11, "E_CONTRACT_ACCOUNT")
    require(contracts.get("storyline_count") == 4, "E_CONTRACT_STORYLINE")
    require(contracts.get("candidate_count_policy") == "2_TO_3", "E_CANDIDATE_POLICY")
    require(
        set(contracts.get("user_visible_formats", []))
        == {"短视频", "图文", "陈列搭配"},
        "E_FORMAT_SET",
    )
    retrieval = cast(Mapping[str, Any], manifest.get("retrieval_decision", {}))
    require(retrieval.get("parallel_vector_truth") is False, "E_PARALLEL_RETRIEVAL")
    continuity = cast(Mapping[str, Any], manifest.get("continuous_dialogue", {}))
    require(
        continuity.get("dify_conversation_id_persisted") is True, "E_CONTINUITY_PERSIST"
    )
    require(
        continuity.get("scope") == "PRINCIPAL_PLUS_CONTENT_ACCOUNT",
        "E_CONTINUITY_SCOPE",
    )
    require(continuity.get("sanitized_context_window") == 6, "E_CONTINUITY_WINDOW")
    require(continuity.get("raw_dify_memory_enabled") is False, "E_DIFY_RAW_MEMORY")
    require(
        continuity.get("raw_provider_reasoning_reused") is False,
        "E_RAW_REASONING_REUSE",
    )
    require(
        continuity.get("history_may_not_grant_fact_or_authorization") is True,
        "E_HISTORY_AUTHORITY",
    )
    budget = cast(Mapping[str, Any], manifest.get("model_budget", {}))
    require(budget.get("original_request_upper_bound") == 40, "E_BUDGET_ORIGINAL")
    require(
        budget.get("founder_additional_request_upper_bound") == 60,
        "E_BUDGET_ADDITIONAL",
    )
    require(budget.get("effective_request_upper_bound") == 100, "E_BUDGET_EFFECTIVE")
    require(budget.get("cost_cny_upper_bound") == 50, "E_BUDGET_COST")
    require(budget.get("content_quality_reroll_allowed") is False, "E_REROLL_POLICY")
    legacy = cast(Mapping[str, Any], manifest.get("legacy_boundary", {}))
    require(legacy.get("compatibility_research_stopped") is True, "E_LEGACY_RESEARCH")
    require(legacy.get("old_object_mutation_allowed") is False, "E_LEGACY_MUTATION")
    validate_core_numbers(
        cast(Mapping[str, Any], manifest.get("core_numbers", {})), "E_MANIFEST_CORE"
    )
    validate_readiness(
        cast(Mapping[str, Any], manifest.get("readiness", {})), "E_MANIFEST_READINESS"
    )


def validate_external_evidence(evidence: JsonObject) -> None:
    require(
        evidence.get("schema") == "diyu.package7.external_runtime_evidence.v1",
        "E_EXTERNAL_SCHEMA",
    )
    environment = cast(Mapping[str, Any], evidence.get("environment", {}))
    require(environment.get("dify_version") == "1.15.0", "E_DIFY_VERSION")
    require(
        environment.get("lifecycle") == "NON_PRODUCTION_INTERNAL_ACCEPTANCE",
        "E_RUNTIME_LIFECYCLE",
    )
    require(environment.get("production_ready") is False, "E_EXTERNAL_PRODUCTION")
    owner = cast(Mapping[str, Any], evidence.get("approved_workspace_and_owner", {}))
    require(owner.get("binding_source") == "LOCKED_PACKAGE7_STATE", "E_OWNER_BINDING")
    require(
        owner.get("oldest_preexisting_app_used_for_owner_inference") is False,
        "E_OWNER_INFERENCE",
    )
    require(owner.get("identity_drift_fails_closed") is True, "E_OWNER_DRIFT")
    for key in ("tenant_id_sha256", "owner_account_id_sha256"):
        require(
            bool(re.fullmatch(r"[0-9a-f]{64}", str(owner.get(key, "")))),
            f"E_OWNER_DIGEST:{key}",
        )
    objects = cast(Mapping[str, Any], evidence.get("dify_objects", {}))
    require(objects.get("package7_app_name_count") == 1, "E_APP_COUNT")
    require(objects.get("package7_dataset_name_count") == 1, "E_DATASET_COUNT")
    require(objects.get("preexisting_app_count_preserved") == 2, "E_PREEXISTING_APPS")
    require(
        objects.get("package7_app_id") == "98eb36f1-50b7-42ca-8184-976512fbef9d",
        "E_EXTERNAL_APP_ID",
    )
    require(
        objects.get("package7_dataset_id") == "3c9d73cc-c120-4f84-81a1-1bc95f7b6d4b",
        "E_EXTERNAL_DATASET_ID",
    )
    require(objects.get("package7_public_site_enabled") is False, "E_PUBLIC_SITE")
    require(
        objects.get("package7_dataset_permission") == "only_me", "E_DATASET_PERMISSION"
    )
    require(objects.get("package7_document_count") == 29, "E_DOCUMENT_COUNT")
    require(objects.get("package7_segment_count") == 29, "E_SEGMENT_COUNT")
    require(
        objects.get("repeated_provision_preserved_object_ids") is True,
        "E_PROVISION_IDEMPOTENCE",
    )
    database = cast(Mapping[str, Any], evidence.get("runtime_database", {}))
    require(database.get("database_name") == "diyu_pkg7_runtime", "E_EXTERNAL_DATABASE")
    require(database.get("isolated_namespace") is True, "E_DATABASE_ISOLATION")
    for key in (
        "empty_initialization_pass",
        "repeat_initialization_idempotent",
        "transaction_rollback_pass",
        "bridge_restart_persistence_pass",
    ):
        require(database.get(key) is True, f"E_DATABASE_PROOF:{key}")
    counts = cast(Mapping[str, Any], database.get("row_counts", {}))
    require(counts.get("content_accounts") == 11, "E_ACCOUNT_ROWS")
    require(counts.get("narrative_fragments") == 29, "E_FRAGMENT_ROWS")
    require(counts.get("dify_invocations") == 79, "E_INVOCATION_ROWS")
    require(counts.get("dify_conversations") == 5, "E_CONVERSATION_ROWS")
    isolation = cast(Mapping[str, Any], evidence.get("bridge_isolation", {}))
    require(isolation.get("container_name") == "diyu-package7-bridge", "E_CONTAINER")
    require(isolation.get("container_user") == "1001:1001", "E_CONTAINER_USER")
    require(isolation.get("read_only_root_filesystem") is True, "E_READONLY_ROOT")
    require(isolation.get("capabilities_dropped") == ["ALL"], "E_CAP_DROP")
    require(isolation.get("no_new_privileges") is True, "E_NO_NEW_PRIVILEGES")
    require(isolation.get("host_bindings") == ["127.0.0.1:18471"], "E_HOST_BINDING")
    require(
        set(isolation.get("networks", []))
        == {"dify-staging_default", "diyu-package7-runtime"},
        "E_NETWORKS",
    )
    require(
        isolation.get("shared_business_network_attached") is False, "E_SHARED_NETWORK"
    )
    require(isolation.get("source_file_mode") == "400", "E_SOURCE_MODE")
    require(isolation.get("state_file_mode") == "400", "E_STATE_MODE")
    retrieval = cast(Mapping[str, Any], evidence.get("retrieval", {}))
    for key in (
        "trusted_prefilter_before_ranking",
        "authoritative_metadata_postcheck",
        "authorized_current_record_accepted",
        "expired_record_rejected",
        "revoked_record_rejected",
        "index_content_drift_rejected",
    ):
        require(retrieval.get(key) is True, f"E_RETRIEVAL:{key}")
    require(retrieval.get("probe_mutations_persisted") is False, "E_RETRIEVAL_MUTATION")
    portal = cast(Mapping[str, Any], evidence.get("portal_and_scope", {}))
    for key in (
        "trusted_login_success",
        "wrong_password_rejected",
        "missing_session_rejected",
        "session_cookie_http_only",
        "login_response_has_no_token_fields",
        "forged_account_rejected",
        "forged_account_model_budget_unchanged",
        "invalid_bridge_secret_rejected",
        "public_network_portal_rejected",
    ):
        require(portal.get(key) is True, f"E_PORTAL:{key}")
    require(portal.get("content_account_option_count") == 11, "E_PORTAL_ACCOUNTS")
    continuity = cast(Mapping[str, Any], evidence.get("continuous_dialogue", {}))
    require(
        continuity.get("binding_scope") == "principal plus content account",
        "E_EXTERNAL_CONTINUITY_SCOPE",
    )
    require(
        continuity.get("binding_count")
        == continuity.get("distinct_scope_count")
        == continuity.get("distinct_conversation_id_count")
        == 5,
        "E_CONVERSATION_UNIQUENESS",
    )
    for key in (
        "second_turn_recalled_marker",
        "marker_declared_not_brand_fact",
        "dify_conversation_id_reused",
        "sanitized_runtime_context_used",
        "failed_preceding_attempts_retained_in_model_audit",
    ):
        require(continuity.get(key) is True, f"E_CONTINUITY:{key}")
    for key in (
        "raw_provider_reasoning_reused_as_context",
        "cross_account_context_visible",
        "publish_allowed",
    ):
        require(continuity.get(key) is False, f"E_CONTINUITY_BOUNDARY:{key}")
    legacy = cast(Mapping[str, Any], evidence.get("legacy_objects", {}))
    require(
        legacy.get("compatibility_research_stopped") is True,
        "E_EXTERNAL_LEGACY_RESEARCH",
    )
    require(legacy.get("old_object_mutation_count") == 0, "E_OLD_MUTATION")
    require(legacy.get("old_object_deletion_count") == 0, "E_OLD_DELETION")
    for key in (
        "parallel_package7_app_created",
        "parallel_package7_dataset_created",
        "parallel_package7_database_created",
        "parallel_package7_bridge_created",
    ):
        require(legacy.get(key) is False, f"E_PARALLEL_OBJECT:{key}")
    boundaries = cast(Mapping[str, Any], evidence.get("boundaries", {}))
    for key in (
        "core_300_changed",
        "core_120_changed",
        "core_86_changed",
        "public_release_performed",
        "domain_or_proxy_changed",
        "package8_or_later_action_performed",
    ):
        require(boundaries.get(key) is False, f"E_EXTERNAL_BOUNDARY:{key}")
    require(boundaries.get("readiness_transition_count") == 0, "E_EXTERNAL_READINESS")


def validate_candidate_record(
    record: JsonObject, expected_format: str, payload_key: str
) -> None:
    require(
        set(record) == {"candidate", "ordinal", "selected", "validation"},
        "E_REPRESENTATIVE_RECORD_FIELDS",
    )
    candidate = cast(Mapping[str, Any], record.get("candidate", {}))
    validation = cast(Mapping[str, Any], record.get("validation", {}))
    require(isinstance(record.get("ordinal"), int), "E_CANDIDATE_ORDINAL")
    require(record.get("selected") is False, "E_CANDIDATE_PRESELECTED")
    require(
        candidate.get("narrative_architecture")
        in {None, "EVIDENCE_FIRST", "QUESTION_ANSWER", "OBJECT_OR_TIMELINE"},
        "E_CANDIDATE_ARCHITECTURE",
    )
    require(
        isinstance(candidate.get("difference_dimensions"), list)
        and len(candidate["difference_dimensions"]) >= 2,
        "E_CANDIDATE_DIFFERENCE",
    )
    fact_refs = candidate.get("used_fact_refs")
    material_refs = candidate.get("used_material_refs")
    require(
        isinstance(fact_refs, list) and isinstance(material_refs, list),
        "E_CANDIDATE_REFS",
    )
    require(
        fact_refs == validation.get("actually_used_fact_refs"), "E_FACT_REF_MISMATCH"
    )
    require(
        material_refs == validation.get("actually_used_material_refs"),
        "E_MATERIAL_REF_MISMATCH",
    )
    require(validation.get("decision") == "PASS", "E_STRUCTURAL_VALIDATION")
    require(
        validation.get("semantic_fact_review_status") == "PENDING_EXTERNAL_REVIEW",
        "E_SEMANTIC_SELF_APPROVAL",
    )
    require(
        validation.get("structured_hard_checks_prove_candidate_semantics") is False,
        "E_SEMANTIC_MACHINE_CLAIM",
    )
    surfaces = cast(
        Mapping[str, Any], candidate.get("candidate_user_visible_surfaces", {})
    )
    require_fields(
        surfaces,
        {"title", "body", "spoken_lines", "CTA", "execution_payload", "surface_units"},
        "E_SURFACE_FIELDS",
    )
    require(
        isinstance(surfaces.get("title"), str) and bool(surfaces["title"].strip()),
        "E_TITLE",
    )
    require(
        isinstance(surfaces.get("body"), str) and bool(surfaces["body"].strip()),
        "E_BODY",
    )
    require(isinstance(surfaces.get("spoken_lines"), list), "E_SPOKEN_LINES")
    bindings = candidate.get("claim_bindings")
    require(isinstance(bindings, list), "E_CLAIM_BINDINGS")
    author_bindings = candidate.get("author_declared_claim_bindings")
    require(isinstance(author_bindings, list), "E_AUTHOR_CLAIM_BINDINGS")

    surface_text = surface_text_map(surfaces)
    binding_paths = [
        row.get("surface_path") for row in bindings if isinstance(row, dict)
    ]
    require(
        len(binding_paths) == len(bindings) == len(set(binding_paths)),
        "E_CLAIM_BINDING_PATHS",
    )
    require(set(binding_paths).issubset(surface_text), "E_CLAIM_SURFACE_COVERAGE")
    binding_by_path: dict[str, Mapping[str, Any]] = {}
    for row in bindings:
        require(isinstance(row, dict), "E_CLAIM_BINDING_ROW")
        path = row.get("surface_path")
        require(
            isinstance(path, str) and row.get("exact_text") == surface_text.get(path),
            "E_CLAIM_BINDING_EXACT_TEXT",
        )
        require(
            row.get("binding_origin")
            in {
                "AUTHOR_DECLARED",
                "EXACT_TEXT_INHERITED",
                "SERVER_STRUCTURAL_FIELD",
                "SERVER_PATH_CLASSIFICATION",
                "SERVER_PENDING_SOURCE_REVIEW",
            },
            "E_CLAIM_BINDING_ORIGIN",
        )
        if isinstance(path, str):
            binding_by_path[path] = row
    for path, text in surface_text.items():
        if not surface_requires_evidence_binding(path, text):
            continue
        row = binding_by_path.get(path)
        require(row is not None, "E_CLAIM_HIGH_RISK_COVERAGE")
        require(
            row.get("claim_class") == "SOURCE_CLAIM"
            and isinstance(row.get("source_refs"), list)
            and bool(row["source_refs"]),
            "E_CLAIM_HIGH_RISK_SOURCE",
        )
    author_paths = [
        row.get("surface_path") for row in author_bindings if isinstance(row, dict)
    ]
    require(
        len(author_paths) == len(author_bindings) == len(set(author_paths))
        and set(author_paths).issubset(binding_by_path),
        "E_AUTHOR_CLAIM_BINDING_PATHS",
    )
    declared_refs = set(fact_refs) | set(material_refs)
    cited_refs = {
        ref
        for row in bindings
        if isinstance(row, dict) and row.get("claim_class") == "SOURCE_CLAIM"
        for ref in cast(list[Any], row.get("source_refs", []))
        if isinstance(ref, str)
    }
    require(cited_refs.issubset(declared_refs), "E_CLAIM_REF_CLOSURE")
    payload = cast(Mapping[str, Any], surfaces.get("execution_payload", {}))
    require(payload.get("production_format") == expected_format, "E_PRODUCTION_FORMAT")
    require(
        isinstance(payload.get(payload_key), dict), f"E_FORMAT_PAYLOAD:{payload_key}"
    )
    joined = json.dumps(surfaces, ensure_ascii=False)
    require(
        "<think>" not in joined and "</think>" not in joined,
        "E_PRIVATE_REASONING_SURFACE",
    )
    require(
        not any(pattern.search(joined) for pattern in SECRET_PATTERNS),
        "E_SECRET_SURFACE",
    )


def validate_model_evidence(evidence: JsonObject) -> None:
    require(
        evidence.get("schema") == "diyu.package7.model_run_evidence.v1",
        "E_MODEL_SCHEMA",
    )
    model = cast(Mapping[str, Any], evidence.get("model", {}))
    require(model.get("model_name") == "deepseek-v4-flash", "E_MODEL_NAME")
    require(
        model.get("configuration_frozen_during_formal_evidence") is True,
        "E_MODEL_FREEZE",
    )
    require(model.get("content_reroll_for_quality_count") == 0, "E_MODEL_REROLL")
    budget = cast(Mapping[str, Any], evidence.get("founder_budget_authorization", {}))
    require(
        budget
        == {
            "additional_request_upper_bound": 60,
            "cost_cny_upper_bound": 50,
            "effective_request_upper_bound": 100,
            "original_request_upper_bound": 40,
        },
        "E_MODEL_AUTHORIZATION",
    )
    confirmation = cast(
        Mapping[str, Any],
        evidence.get("founder_budget_authorization_confirmation", {}),
    )
    require(
        confirmation
        == {
            "confirmation_date": "2026-07-16",
            "confirmation_source": "execution_prompt.addendum_v2",
            "new_content_model_calls_after_existing_stop": 0,
            "new_remote_deployments_after_existing_stop": 0,
            "confirmed_additional_request_upper_bound": 60,
            "confirmed_effective_request_upper_bound": 100,
        },
        "E_MODEL_AUTHORIZATION_CONFIRMATION",
    )
    audit = cast(Mapping[str, Any], evidence.get("invocation_audit", {}))
    require(audit.get("invocation_count") == 79, "E_MODEL_INVOCATIONS")
    require(
        isinstance(audit.get("model_call_upper_bound"), int)
        and 0 < audit["model_call_upper_bound"] <= 100,
        "E_MODEL_CALL_BOUND",
    )
    require(
        audit.get("request_upper_bound_within_authorization") is True,
        "E_MODEL_BUDGET_CLAIM",
    )
    try:
        known_cost = Decimal(str(audit.get("known_cost_rmb")))
    except InvalidOperation as exc:
        raise CheckFailure("E_MODEL_COST") from exc
    require(known_cost <= Decimal("50"), "E_MODEL_COST_BOUND")
    require(audit.get("known_cost_within_authorization") is True, "E_MODEL_COST_CLAIM")
    require(evidence.get("run_count") == 39, "E_RUN_COUNT")
    distribution = cast(Mapping[str, Any], evidence.get("run_state_distribution", {}))
    require(
        sum(int(value) for value in distribution.values()) == 39, "E_RUN_DISTRIBUTION"
    )
    require(
        int(distribution.get("FIRST_OUTPUT_REJECTED", 0)) >= 1,
        "E_FAILED_OUTPUTS_NOT_RETAINED",
    )
    require(
        isinstance(evidence.get("run_index"), list)
        and len(evidence["run_index"]) == 39,
        "E_RUN_INDEX",
    )
    representative = cast(
        Mapping[str, Any], evidence.get("representative_first_outputs", {})
    )
    require(set(representative) == set(EXPECTED_FORMATS), "E_REPRESENTATIVE_FORMATS")
    for key, (expected_format, payload_key) in EXPECTED_FORMATS.items():
        run = cast(Mapping[str, Any], representative[key])
        require(run.get("first_output_preserved") is True, f"E_FIRST_OUTPUT:{key}")
        candidates = run.get("candidates")
        require(
            isinstance(candidates, list) and 2 <= len(candidates) <= 3,
            f"E_CANDIDATE_COUNT:{key}",
        )
        for record in cast(list[Any], candidates):
            require(isinstance(record, dict), f"E_CANDIDATE_OBJECT:{key}")
            validate_candidate_record(
                cast(JsonObject, record), expected_format, payload_key
            )
    continuity = cast(Mapping[str, Any], evidence.get("continuous_dialogue", {}))
    require(
        continuity.get("conversation_binding_reused") is True,
        "E_MODEL_CONTINUITY_BINDING",
    )
    require(
        continuity.get("dify_message_count_for_binding") == 2,
        "E_MODEL_CONTINUITY_MESSAGES",
    )
    require(
        continuity.get("second_turn_recalled_marker") is True,
        "E_MODEL_CONTINUITY_RECALL",
    )
    require(continuity.get("marker_is_brand_fact") is False, "E_MODEL_CONTINUITY_FACT")
    require(continuity.get("publish_allowed") is False, "E_MODEL_CONTINUITY_PUBLISH")
    require(
        continuity.get("raw_provider_reasoning_used_as_continuity_context") is False,
        "E_MODEL_CONTINUITY_REASONING",
    )
    turns = continuity.get("accepted_sanitized_turns")
    require(isinstance(turns, list) and len(turns) == 2, "E_MODEL_CONTINUITY_TURNS")
    limits = cast(Mapping[str, Any], evidence.get("evidence_limits", {}))
    require(
        limits.get("all_provider_private_reasoning_excluded_from_repository_evidence")
        is True,
        "E_REASONING_EVIDENCE",
    )
    require(
        limits.get("free_text_truth_requires_independent_review") is True,
        "E_FREE_TEXT_REVIEW",
    )
    require(
        limits.get("production_or_publish_approval") is False,
        "E_MODEL_PUBLISH_APPROVAL",
    )


def validate_brand_contracts(root: Path) -> None:
    contract = load_yaml_root(
        root / "brand_import_contract.v1.yaml", "brand_import_contract"
    )
    require(
        contract.get("brand_specific_constants_allowed_in_runtime_logic") is False,
        "E_IMPORT_BRAND_CONSTANTS",
    )
    transaction = cast(Mapping[str, Any], contract.get("transaction_policy", {}))
    require(transaction.get("all_or_nothing") is True, "E_IMPORT_ATOMICITY")
    require(
        transaction.get("partial_brand_left_after_failure") is False, "E_IMPORT_PARTIAL"
    )
    isolation = cast(Mapping[str, Any], contract.get("isolation_policy", {}))
    require(
        isolation.get("cross_tenant_reference_allowed") is False,
        "E_IMPORT_CROSS_TENANT",
    )
    validate_readiness(
        cast(Mapping[str, Any], contract.get("readiness", {})), "E_IMPORT_READINESS"
    ) if set(
        cast(Mapping[str, Any], contract.get("readiness", {}))
    ) == REQUIRED_FALSE_FLAGS else None
    require(
        cast(Mapping[str, Any], contract.get("readiness", {})).get("DIFY_ready")
        is False,
        "E_IMPORT_DIFY_READY",
    )
    require(
        cast(Mapping[str, Any], contract.get("readiness", {})).get("production_ready")
        is False,
        "E_IMPORT_PRODUCTION_READY",
    )
    profile = load_yaml_root(
        root / "brand_runtime_profile.v1.yaml", "brand_runtime_profile"
    )
    require(profile.get("simulation_only") is True, "E_PROFILE_SIMULATION")
    require(profile.get("publish_allowed") is False, "E_PROFILE_PUBLISH")
    require(profile.get("runtime_publishable") is False, "E_PROFILE_RUNTIME")
    require(
        profile.get("may_grant_fact_authorization_or_scope") is False,
        "E_PROFILE_AUTHORITY",
    )
    require(
        profile.get("cross_tenant_borrowing_allowed") is False, "E_PROFILE_CROSS_TENANT"
    )
    require(
        len(cast(list[Any], profile.get("principal_roles", []))) == 3, "E_PROFILE_ROLES"
    )
    require(
        len(cast(list[Any], profile.get("storylines", []))) == 4, "E_PROFILE_STORYLINES"
    )
    require(
        len(cast(list[Any], profile.get("account_role_cards", []))) == 11,
        "E_PROFILE_ACCOUNTS",
    )
    import_source = (root / "brand_import.py").read_text(encoding="utf-8")
    for token in ("TENANT-DIYU", "BRAND-DIYU", "ACCOUNT-DIYU", "笛语"):
        require(token not in import_source, f"E_IMPORT_SHORTCUT:{token}")


def validate_dify_graph(root: Path) -> None:
    app = yaml.safe_load((root / "dify_app.v1.yaml").read_text(encoding="utf-8"))
    require(isinstance(app, dict), "E_DIFY_GRAPH_OBJECT")
    workflow = cast(Mapping[str, Any], app.get("workflow", {}))
    graph = cast(Mapping[str, Any], workflow.get("graph", {}))
    nodes = cast(list[Mapping[str, Any]], graph.get("nodes", []))
    llm_nodes = [
        node
        for node in nodes
        if cast(Mapping[str, Any], node.get("data", {})).get("type") == "llm"
    ]
    require(len(llm_nodes) == 2, "E_DIFY_LLM_NODE_COUNT")
    for node in llm_nodes:
        data = cast(Mapping[str, Any], node.get("data", {}))
        require(
            cast(Mapping[str, Any], data.get("memory", {})).get("window")
            == {"enabled": False, "size": 1},
            "E_DIFY_MEMORY",
        )
        require(
            cast(Mapping[str, Any], data.get("model", {})).get("name")
            == "deepseek-v4-flash",
            "E_DIFY_NODE_MODEL",
        )
    require(
        not [
            node
            for node in nodes
            if cast(Mapping[str, Any], node.get("data", {})).get("type")
            in {"http-request", "knowledge-retrieval"}
        ],
        "E_DIFY_PARALLEL_IO_NODE",
    )
    require(workflow.get("environment_variables") == [], "E_DIFY_SECRET_VARIABLE")


def validate_source_boundaries(
    root: Path,
    source_override: Mapping[str, str] | None = None,
) -> None:
    source = (
        dict(source_override)
        if source_override is not None
        else {
            path.name: path.read_text(encoding="utf-8")
            for path in root.glob("*.py")
            if path.name != Path(__file__).name
        }
    )
    all_source = "\n".join(source.values())
    require(
        "order_by(App.created_at" not in source["provision_dify.py"],
        "E_OLDEST_APP_OWNER_INFERENCE",
    )
    for token in (
        "PACKAGE7_APPROVED_DIFY_TENANT_ID",
        "PACKAGE7_APPROVED_DIFY_OWNER_ACCOUNT_ID",
    ):
        require(
            token in source["provision_dify.py"], f"E_EXPLICIT_OWNER_BINDING:{token}"
        )
    models = source["runtime_models.py"]
    for token in (
        "UniqueConstraint(",
        '"principal_id"',
        '"account_id"',
        "uq_runtime_dify_conversation_scope",
    ):
        require(token in models, f"E_CONVERSATION_MODEL:{token}")
    persistence = source["persistence.py"]
    for token in (
        "def dify_conversation(self, principal_id: str, account_id: str)",
        "def recent_chat_turns(",
        "RuntimeDifyConversation.account_id == account_id",
        "def require_active_scope(",
        "if source_digest != row.content_digest",
        "row.index_content_digest = index_digest",
        "continuity_only_not_a_fact_source",
    ):
        require(token in persistence, f"E_CONVERSATION_PERSISTENCE:{token}")
    runtime = source["runtime_service.py"]
    for token in (
        "conversation_context",
        "recent_chat_turns",
        "previous_content_context",
        "claim_bindings",
        "_claim_bindings_are_closed",
        "normalize_numeric_detail",
        "不得把未提供的信息写成已经存在、已经发生或已经获得授权的事实",
        "标题、文案、口播、分镜、人物动作、拍摄和剪辑建议可以创意新写",
        "有限等价格式转换",
        '"claim_bindings": []',
    ):
        require(token in runtime, f"E_SANITIZED_CONTINUITY:{token}")
    for forbidden in (
        "不得补写数字、人物、动作、因果、结果",
        "必须逐字写明‘待补拍’或‘待取得’",
        "来源使用‘厘米’时不得改成cm",
    ):
        require(
            forbidden not in runtime, f"E_AUTHOR_CONTRACT_CONTRADICTION:{forbidden}"
        )
    chat = source["dify_chat.py"]
    require("maximum_model_calls > 100" in chat, "E_MODEL_BUDGET_HARD_CAP")
    require(
        "dify_conversation(principal_id, conversation_scope)" in chat,
        "E_DIFY_CONVERSATION_SCOPE",
    )
    require("if reuse_conversation" in chat, "E_DIFY_TASK_CONVERSATION_ISOLATION")
    bridge = source["bridge_app.py"]
    require(
        "package7-dify-user:{principal_id}:{conversation_scope}" in bridge,
        "E_DIFY_USER_SCOPE",
    )
    require("query=payload.message" in bridge, "E_CHAT_QUERY_NOT_REAL")
    require(
        "require_active_scope_by_display_name" in bridge, "E_PORTAL_CURRENT_AUTHORITY"
    )
    require(
        bridge.count("reuse_conversation=False") == 1, "E_CLASSIFIER_FRESH_CONVERSATION"
    )
    require(
        'in {"普通聊天", "找灵感"}' in bridge,
        "E_CHAT_ONLY_CONTINUOUS_CONVERSATION",
    )
    provision = source["provision_dify.py"]
    for token in (
        "The locked Package 7 Dify application owner drifted",
        "The Package 7 Dify application is not unique",
        "The locked Package 7 Dify dataset drifted",
        "The Package 7 Dify dataset is not unique",
    ):
        require(token in provision, f"E_SINGLE_OBJECT_LOCK:{token}")
    for forbidden in (
        "import openai",
        "from openai",
        "import anthropic",
        "from anthropic",
        "api.deepseek.com",
    ):
        require(forbidden not in all_source, f"E_DIRECT_PROVIDER:{forbidden}")
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or path.name == Path(__file__).name
            or "__pycache__" in path.parts
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        require(
            not any(pattern.search(text) for pattern in SECRET_PATTERNS),
            f"E_SECRET:{path.relative_to(root)}",
        )


def validate_candidate_binding(result: JsonObject) -> tuple[str, str]:
    candidate_commit = str(result.get("reviewed_candidate_commit", ""))
    candidate_snapshot = str(result.get("reviewed_snapshot_sha256", ""))
    require(bool(re.fullmatch(r"[0-9a-f]{40}", candidate_commit)), "E_CANDIDATE_COMMIT")
    require(bool(re.fullmatch(r"[0-9a-f]{40}", candidate_snapshot)), "E_CANDIDATE_TREE")
    require(
        candidate_tree(candidate_commit) == candidate_snapshot,
        "E_CANDIDATE_TREE_MISMATCH",
    )
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate_commit, "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    require(process.returncode == 0, "E_CANDIDATE_NOT_ANCESTOR")
    changed = {
        Path(line)
        for line in git_output(
            "diff", "--name-only", f"{candidate_commit}..HEAD"
        ).splitlines()
        if line
    }
    require(
        changed <= POST_CANDIDATE_ALLOWED_PATHS,
        f"E_POST_CANDIDATE_IMPLEMENTATION:{sorted(map(str, changed - POST_CANDIDATE_ALLOWED_PATHS))}",
    )
    return candidate_commit, candidate_snapshot


def validate_reviews(
    root: Path, result: JsonObject, candidate_commit: str, candidate_snapshot: str
) -> list[JsonObject]:
    reviews: list[JsonObject] = []
    for path in REVIEW_PATHS:
        review = load_yaml_root(root / path, "review")
        require(review.get("task_id") == TASK_ID, f"E_REVIEW_TASK:{path}")
        require(
            review.get("candidate_commit") == candidate_commit,
            f"E_REVIEW_COMMIT:{path}",
        )
        require(
            review.get("candidate_snapshot_digest") == candidate_snapshot,
            f"E_REVIEW_TREE:{path}",
        )
        require(review.get("verdict") == "PASS", f"E_REVIEW_VERDICT:{path}")
        require(
            isinstance(review.get("score"), int) and review["score"] >= 90,
            f"E_REVIEW_SCORE:{path}",
        )
        require(review.get("hard_blockers") == [], f"E_REVIEW_BLOCKER:{path}")
        require(
            review.get("independent_from_executor_and_other_reviewer") is True,
            f"E_REVIEW_INDEPENDENCE:{path}",
        )
        for key in (
            "reviewer_identity",
            "reviewer_session_id",
            "reviewer_run_id",
            "signed_at",
        ):
            require(
                isinstance(review.get(key), str) and bool(review[key]),
                f"E_REVIEW_IDENTITY:{path}:{key}",
            )
        require(
            isinstance(review.get("evidence"), list) and len(review["evidence"]) >= 3,
            f"E_REVIEW_EVIDENCE:{path}",
        )
        reviews.append(review)
    require(
        {str(review.get("review_type")) for review in reviews} == REVIEW_TYPES,
        "E_REVIEW_TYPES",
    )
    for key in ("reviewer_identity", "reviewer_session_id", "reviewer_run_id"):
        require(
            len({str(review[key]) for review in reviews}) == 2,
            f"E_REVIEW_COLLISION:{key}",
        )
    declared = result.get("independent_reviews")
    require(isinstance(declared, list) and len(declared) == 2, "E_RESULT_REVIEW_COUNT")
    require(
        {
            str(item.get("review_id"))
            for item in cast(list[Any], declared)
            if isinstance(item, dict)
        }
        == {str(review.get("review_id")) for review in reviews},
        "E_RESULT_REVIEW_BINDING",
    )
    return reviews


def validate_result_and_delivery(root: Path, result: JsonObject) -> None:
    require(
        result.get("schema") == "diyu.package7.dify_end_to_end_result.v1",
        "E_RESULT_SCHEMA",
    )
    require(result.get("task_id") == TASK_ID, "E_RESULT_TASK")
    require(
        result.get("state") == "PASS_DIFY_END_TO_END_PENDING_PACKAGE_8",
        "E_RESULT_STATE",
    )
    require(
        result.get("success_claim")
        == "PACKAGE7_ACCEPTANCE_COMPLETE_NOT_PRODUCTION_READY",
        "E_RESULT_CLAIM",
    )
    require(result.get("blocking_items") == [], "E_RESULT_BLOCKERS")
    candidate_commit, snapshot = validate_candidate_binding(result)
    objects = cast(Mapping[str, Any], result.get("external_objects", {}))
    for key in (
        "dify_app_count",
        "dataset_count",
        "runtime_database_count",
        "runtime_bridge_count",
    ):
        require(objects.get(key) == 1, f"E_RESULT_OBJECT:{key}")
    require(objects.get("parallel_object_count") == 0, "E_RESULT_PARALLEL_OBJECT")
    require(objects.get("production_ready") is False, "E_RESULT_PRODUCTION")
    coverage = cast(Mapping[str, Any], result.get("coverage", {}))
    require(coverage.get("content_products_deterministic") == 20, "E_RESULT_CP")
    require(coverage.get("formats_with_real_model_outputs") == 3, "E_RESULT_FORMATS")
    for key in (
        "representative_continuous_dialogue_pass",
        "representative_missing_material_degrade_pass",
        "representative_scope_rejection_pass",
    ):
        require(coverage.get(key) is True, f"E_RESULT_COVERAGE:{key}")
    audit = cast(Mapping[str, Any], result.get("model_audit", {}))
    call_upper_bound = audit.get("model_call_upper_bound")
    authorized_upper_bound = audit.get("effective_authorized_request_upper_bound")
    require(
        isinstance(call_upper_bound, int)
        and isinstance(authorized_upper_bound, int)
        and call_upper_bound <= authorized_upper_bound == 100,
        "E_RESULT_MODEL_BUDGET",
    )
    require(
        Decimal(str(audit.get("known_cost_rmb")))
        <= Decimal(str(audit.get("authorized_cost_cny_upper_bound"))),
        "E_RESULT_COST",
    )
    require(audit.get("content_quality_reroll_count") == 0, "E_RESULT_REROLL")
    require(
        result.get("core_numbers")
        == {"300_changed": False, "120_changed": False, "86_changed": False},
        "E_RESULT_CORE",
    )
    require(result.get("readiness_transition_count") == 0, "E_RESULT_READINESS")
    require(result.get("merge_allowed") is False, "E_RESULT_MERGE")
    checks = cast(Mapping[str, Any], result.get("checks", {}))
    for key in (
        "package7_unit_tests",
        "package2_regression",
        "package6_regression",
        "package7_checker",
        "gate1_current_checker",
    ):
        require(str(checks.get(key, "")).startswith("PASS"), f"E_RESULT_CHECK:{key}")
    validate_reviews(root, result, candidate_commit, snapshot)
    delivery = load_yaml_root(root / DELIVERY_PATH, "execution_review_request")
    require(delivery.get("task_id") == TASK_ID, "E_DELIVERY_TASK")
    require(
        delivery.get("status") == "REQUESTING_APPROVE_PACKAGE_7_MERGE",
        "E_DELIVERY_STATUS",
    )
    require(delivery.get("candidate_commit") == candidate_commit, "E_DELIVERY_COMMIT")
    require(delivery.get("candidate_snapshot_digest") == snapshot, "E_DELIVERY_TREE")
    require(
        delivery.get("requested_root_decision") == "APPROVE_PACKAGE_7_MERGE",
        "E_DELIVERY_REQUEST",
    )
    require(delivery.get("merge_authorization") == "NOT_GRANTED", "E_DELIVERY_MERGE")
    require(delivery.get("draft_pull_request_required") is True, "E_DELIVERY_DRAFT")
    require(delivery.get("package8_unlocked") is False, "E_DELIVERY_PACKAGE8")
    require(
        delivery.get("implementation_changes_after_candidate_freeze_allowed") is False,
        "E_DELIVERY_FREEZE",
    )
    require(
        delivery.get("readiness_transition_authorized") is False, "E_DELIVERY_READINESS"
    )


def validate_repository_scope(candidate_commit: str) -> None:
    changed = {
        Path(line)
        for line in git_output(
            "diff", "--name-only", f"{BASELINE_COMMIT}..{candidate_commit}"
        ).splitlines()
        if line
    }
    allowed = AUTHORIZED_COMPATIBILITY_PATHS | {
        path
        for path in changed
        if path == PACKAGE_RELATIVE_ROOT or PACKAGE_RELATIVE_ROOT in path.parents
    }
    require(changed <= allowed, f"E_WRITE_SCOPE:{sorted(map(str, changed - allowed))}")


def validate_all(root: Path = PACKAGE_ROOT) -> JsonObject:
    validate_file_set(root)
    manifest = load_json(root / MANIFEST_PATH)
    external = load_json(root / EXTERNAL_EVIDENCE_PATH)
    model = load_json(root / MODEL_EVIDENCE_PATH)
    result = load_json(root / RESULT_PATH)
    validate_manifest(manifest)
    validate_external_evidence(external)
    validate_model_evidence(model)
    validate_brand_contracts(root)
    validate_dify_graph(root)
    validate_source_boundaries(root)
    validate_result_and_delivery(root, result)
    validate_repository_scope(str(result["reviewed_candidate_commit"]))
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "model_call_upper_bound": model["invocation_audit"]["model_call_upper_bound"],
        "review_count": len(REVIEW_PATHS),
        "readiness_transition_count": 0,
        "core_numbers_changed": False,
    }


def expect_failure(callback: Any, code: str) -> None:
    try:
        callback()
    except CheckFailure as exc:
        require(code in str(exc), f"E_SELFTEST_WRONG_FAILURE:{code}:{exc}")
        return
    raise CheckFailure(f"E_SELFTEST_FALSE_NEGATIVE:{code}")


def run_selftest(root: Path = PACKAGE_ROOT) -> JsonObject:
    manifest = load_json(root / MANIFEST_PATH)
    external = load_json(root / EXTERNAL_EVIDENCE_PATH)
    model = load_json(root / MODEL_EVIDENCE_PATH)
    result = load_json(root / RESULT_PATH)

    changed = copy.deepcopy(manifest)
    changed["readiness"]["DIFY_ready"] = True
    expect_failure(
        lambda: validate_manifest(changed), "E_MANIFEST_READINESS:DIFY_ready"
    )

    changed = copy.deepcopy(manifest)
    changed["model_budget"]["effective_request_upper_bound"] = 101
    expect_failure(lambda: validate_manifest(changed), "E_BUDGET_EFFECTIVE")

    changed = copy.deepcopy(external)
    changed["dify_objects"]["package7_app_name_count"] = 2
    expect_failure(lambda: validate_external_evidence(changed), "E_APP_COUNT")

    changed = copy.deepcopy(external)
    changed["continuous_dialogue"]["cross_account_context_visible"] = True
    expect_failure(
        lambda: validate_external_evidence(changed),
        "E_CONTINUITY_BOUNDARY:cross_account_context_visible",
    )

    changed = copy.deepcopy(model)
    changed["continuous_dialogue"][
        "raw_provider_reasoning_used_as_continuity_context"
    ] = True
    expect_failure(
        lambda: validate_model_evidence(changed), "E_MODEL_CONTINUITY_REASONING"
    )

    changed = copy.deepcopy(model)
    changed["invocation_audit"]["model_call_upper_bound"] = 101
    expect_failure(lambda: validate_model_evidence(changed), "E_MODEL_CALL_BOUND")

    changed = copy.deepcopy(model)
    changed["founder_budget_authorization_confirmation"][
        "new_content_model_calls_after_existing_stop"
    ] = 1
    expect_failure(
        lambda: validate_model_evidence(changed),
        "E_MODEL_AUTHORIZATION_CONFIRMATION",
    )

    changed = copy.deepcopy(model)
    changed["representative_first_outputs"]["display"]["candidates"][0]["candidate"][
        "used_material_refs"
    ] = []
    expect_failure(lambda: validate_model_evidence(changed), "E_MATERIAL_REF_MISMATCH")

    sparse = copy.deepcopy(model)
    sparse_record = sparse["representative_first_outputs"]["short_video"]["candidates"][
        0
    ]
    sparse_candidate = sparse_record["candidate"]
    sparse_path = "execution_payload.content_direction"
    sparse_candidate["claim_bindings"] = [
        row
        for row in sparse_candidate["claim_bindings"]
        if row["surface_path"] != sparse_path
    ]
    sparse_candidate["author_declared_claim_bindings"] = [
        row
        for row in sparse_candidate["author_declared_claim_bindings"]
        if row["surface_path"] != sparse_path
    ]
    validate_model_evidence(sparse)

    changed = copy.deepcopy(sparse)
    changed_record = changed["representative_first_outputs"]["short_video"][
        "candidates"
    ][0]
    changed_candidate = changed_record["candidate"]
    changed_candidate["candidate_user_visible_surfaces"]["title"] = (
        "待补拍；现有样衣已经确认100厘米"
    )
    changed_candidate["claim_bindings"] = [
        row
        for row in changed_candidate["claim_bindings"]
        if row["surface_path"] != "title"
    ]
    changed_candidate["author_declared_claim_bindings"] = [
        row
        for row in changed_candidate["author_declared_claim_bindings"]
        if row["surface_path"] != "title"
    ]
    expect_failure(
        lambda: validate_model_evidence(changed), "E_CLAIM_HIGH_RISK_COVERAGE"
    )

    changed = copy.deepcopy(sparse)
    changed_record = changed["representative_first_outputs"]["short_video"][
        "candidates"
    ][0]
    changed_candidate = changed_record["candidate"]
    creative_path = "execution_payload.video.shots[0].visual"
    changed_candidate["candidate_user_visible_surfaces"]["execution_payload"]["video"][
        "shots"
    ][0]["visual"] = "建议拍一件红色上衣放在画面中央"
    changed_candidate["claim_bindings"] = [
        row
        for row in changed_candidate["claim_bindings"]
        if row["surface_path"] != creative_path
    ]
    changed_candidate["author_declared_claim_bindings"] = [
        row
        for row in changed_candidate["author_declared_claim_bindings"]
        if row["surface_path"] != creative_path
    ]
    validate_model_evidence(changed)

    creative_cases = (
        ("title", "三件衣服，拍出一个春天"),
        (creative_path, "建议拍一件红色上衣放在画面中央"),
        (
            "execution_payload.video.shots[0].action",
            "如有已授权出镜的孩子，可以试穿后在镜头前转身",
        ),
        ("body", "一位顾客选择了红色上衣，故事停在匿名日常选择"),
        ("execution_payload.video.shots[0].camera", "镜头向内移动20厘米"),
        (creative_path, "镜头从左向右缓慢移动"),
        ("title", "也不讲任何已经完成的事情"),
        ("title", "分享品牌授权管理的基本流程"),
        ("title", "不替家长决定是否接受授权变化"),
        ("title", "任何宣称所有孩子都适合的承诺都应避免"),
        ("title", "强调可观察条件比品牌承诺更有用"),
        ("title", "尺码从来不是一个数字能决定的"),
    )
    for path, text in creative_cases:
        require(
            not surface_requires_evidence_binding(path, text),
            f"E_CREATIVE_FALSE_POSITIVE:{text}",
        )

    factual_cases = (
        ("title", "本店库存还有三件"),
        ("title", "这款上衣采用纯棉面料"),
        ("title", "这名儿童已经获准出镜"),
        ("title", "门店上周举办了春季活动"),
        ("title", "企业已经承诺本月完成调整"),
        ("title", "已有照片可直接使用"),
        (creative_path, "镜头展示本店库存充足"),
        (creative_path, "如有已授权出镜人员这款上衣采用纯棉面料"),
    )
    for path, text in factual_cases:
        require(
            surface_requires_evidence_binding(path, text),
            f"E_FACT_FALSE_NEGATIVE:{text}",
        )

    changed = copy.deepcopy(sparse)
    changed_record = changed["representative_first_outputs"]["short_video"][
        "candidates"
    ][0]
    changed_candidate = changed_record["candidate"]
    changed_candidate["candidate_user_visible_surfaces"]["title"] = "本店库存充足"
    changed_candidate["claim_bindings"] = [
        row
        for row in changed_candidate["claim_bindings"]
        if row["surface_path"] != "title"
    ]
    changed_candidate["author_declared_claim_bindings"] = [
        row
        for row in changed_candidate["author_declared_claim_bindings"]
        if row["surface_path"] != "title"
    ]
    expect_failure(
        lambda: validate_model_evidence(changed), "E_CLAIM_HIGH_RISK_COVERAGE"
    )

    changed = copy.deepcopy(sparse)
    changed_record = changed["representative_first_outputs"]["short_video"][
        "candidates"
    ][0]
    changed_candidate = changed_record["candidate"]
    changed_candidate["candidate_user_visible_surfaces"]["title"] = (
        "这件上衣采用纯棉面料"
    )
    changed_candidate["claim_bindings"] = [
        row
        for row in changed_candidate["claim_bindings"]
        if row["surface_path"] != "title"
    ]
    changed_candidate["author_declared_claim_bindings"] = [
        row
        for row in changed_candidate["author_declared_claim_bindings"]
        if row["surface_path"] != "title"
    ]
    expect_failure(
        lambda: validate_model_evidence(changed), "E_CLAIM_HIGH_RISK_COVERAGE"
    )

    changed = copy.deepcopy(result)
    changed["core_numbers"]["300_changed"] = True
    expect_failure(
        lambda: require(
            changed.get("core_numbers")
            == {"300_changed": False, "120_changed": False, "86_changed": False},
            "E_RESULT_CORE",
        ),
        "E_RESULT_CORE",
    )

    expect_failure(
        lambda: require(
            not SECRET_PATTERNS[0].search("sk-ABCDEFGHIJKLMNOPQRSTUV"),
            "E_SECRET_SYNTHETIC",
        ),
        "E_SECRET_SYNTHETIC",
    )

    source = (root / "provision_dify.py").read_text(encoding="utf-8")
    expect_failure(
        lambda: require(
            "order_by(App.created_at" not in source + "\norder_by(App.created_at)",
            "E_OLDEST_APP_OWNER_INFERENCE",
        ),
        "E_OLDEST_APP_OWNER_INFERENCE",
    )

    source_map = {
        path.name: path.read_text(encoding="utf-8")
        for path in root.glob("*.py")
        if path.name != Path(__file__).name
    }
    source_map["persistence.py"] = source_map["persistence.py"].replace(
        "continuity_only_not_a_fact_source",
        "continuity_boundary_removed",
    )
    expect_failure(
        lambda: validate_source_boundaries(root, source_map),
        "E_CONVERSATION_PERSISTENCE:continuity_only_not_a_fact_source",
    )

    return {
        "task_id": TASK_ID,
        "selftest": "PASS",
        "negative_case_count": 23,
        "optimized_mode_fail_closed": True,
    }


def git_blob(commit: str, relative_path: Path) -> bytes:
    process = subprocess.run(
        ["git", "show", f"{commit}:{relative_path.as_posix()}"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    require(
        process.returncode == 0,
        f"E_RECOVERY_GIT_BLOB:{commit}:{relative_path}",
    )
    return process.stdout


def package_file_set(root: Path) -> set[Path]:
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def validate_recovery_file_set(root: Path, *, implementation_only: bool) -> None:
    actual = package_file_set(root)
    require(not list(root.rglob("*.pyc")), "E_RECOVERY_BYTECODE_PRESENT")
    require(not list(root.rglob("__pycache__")), "E_RECOVERY_PYCACHE_PRESENT")
    if implementation_only:
        required = (
            EXPECTED_PACKAGE_FILES
            | RECOVERY_IMPLEMENTATION_FILES
            | {RECOVERY_REPLAY_PATH}
        )
        require(required <= actual, "E_RECOVERY_IMPLEMENTATION_FILE_MISSING")
        require(
            actual <= RECOVERY_EXPECTED_PACKAGE_FILES,
            f"E_RECOVERY_FILE_SET_EXTRA:{sorted(map(str, actual - RECOVERY_EXPECTED_PACKAGE_FILES))}",
        )
        return
    require(
        actual == RECOVERY_EXPECTED_PACKAGE_FILES,
        "E_RECOVERY_FILE_SET:"
        f"{sorted(map(str, actual ^ RECOVERY_EXPECTED_PACKAGE_FILES))}",
    )


def validate_recovery_historical_bytes(root: Path) -> None:
    for relative_path in RECOVERY_HISTORICAL_FROZEN_FILES:
        expected = git_blob(
            HISTORICAL_PACKAGE7_COMMIT,
            PACKAGE_RELATIVE_ROOT / relative_path,
        )
        require(
            (root / relative_path).read_bytes() == expected,
            f"E_RECOVERY_HISTORICAL_BYTES:{relative_path}",
        )


def recovery_changed_paths() -> set[Path]:
    changed = {
        Path(line)
        for line in git_output(
            "diff", "--name-only", RECOVERY_BASELINE_COMMIT
        ).splitlines()
        if line
    }
    changed.update(
        Path(line)
        for line in git_output(
            "ls-files", "--others", "--exclude-standard"
        ).splitlines()
        if line
    )
    return changed


def validate_recovery_write_scope() -> None:
    changed = recovery_changed_paths()
    outside_package = {
        path
        for path in changed
        if path != PACKAGE_RELATIVE_ROOT and PACKAGE_RELATIVE_ROOT not in path.parents
    }
    require(
        outside_package <= RECOVERY_AUTHORIZED_REPOSITORY_PATHS,
        f"E_RECOVERY_WRITE_SCOPE:{sorted(map(str, outside_package - RECOVERY_AUTHORIZED_REPOSITORY_PATHS))}",
    )
    require(
        not any(
            (
                path == Path("20_internal_pilot/release_evaluation_001")
                or Path("20_internal_pilot/release_evaluation_001") in path.parents
            )
            and path not in PACKAGE10_FINAL_CLOSEOUT_PATHS
            for path in changed
        ),
        "E_RECOVERY_PACKAGE10_MUTATION",
    )


def author_contract_projection(root: Path) -> JsonObject:
    script = """
import json
from author_contract import (
    AUTHOR_CONTRACT_VERSION,
    CANDIDATE_MODELS,
    contract_descriptor,
)

print(json.dumps({
    "contract_version": AUTHOR_CONTRACT_VERSION,
    "formats": list(CANDIDATE_MODELS),
    "model_fields": {
        key: sorted(model.model_fields)
        for key, model in CANDIDATE_MODELS.items()
    },
    "schemas": {
        key: model.model_json_schema()
        for key, model in CANDIDATE_MODELS.items()
    },
    "descriptors": {
        key: contract_descriptor(key)
        for key in CANDIDATE_MODELS
    },
}, ensure_ascii=False, sort_keys=True))
"""
    process = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    require(
        process.returncode == 0,
        f"E_RECOVERY_AUTHOR_IMPORT:{process.stderr.strip()}",
    )
    value = json.loads(process.stdout)
    require(isinstance(value, dict), "E_RECOVERY_AUTHOR_PROJECTION")
    return cast(JsonObject, value)


def recursive_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(recursive_keys(child))
    return keys


def validate_author_contract_projection(projection: Mapping[str, Any]) -> None:
    require(
        projection.get("contract_version") == "diyu.author-output.v2.0",
        "E_RECOVERY_AUTHOR_VERSION",
    )
    formats = projection.get("formats")
    require(formats == list(RECOVERY_FORMATS), "E_RECOVERY_AUTHOR_FORMATS")
    fields = cast(Mapping[str, Any], projection.get("model_fields", {}))
    expected_fields = {
        "body",
        "creative_difference",
        "cta",
        "deliverable",
        "spoken_lines",
        "title",
    }
    require(set(fields) == set(RECOVERY_FORMATS), "E_RECOVERY_AUTHOR_MODELS")
    for content_format in RECOVERY_FORMATS:
        require(
            set(cast(list[str], fields.get(content_format, []))) == expected_fields,
            f"E_RECOVERY_AUTHOR_FIELDS:{content_format}",
        )
    schemas = cast(Mapping[str, Any], projection.get("schemas", {}))
    descriptors = cast(Mapping[str, Any], projection.get("descriptors", {}))
    forbidden = {
        "tenant_id",
        "organization_id",
        "store_id",
        "account_id",
        "principal_id",
        "browser_session_id",
        "used_fact_refs",
        "used_material_refs",
        "claim_bindings",
        "surface_units",
        "component_ids",
        "composition_plan",
    }
    for content_format in RECOVERY_FORMATS:
        schema = cast(Mapping[str, Any], schemas.get(content_format, {}))
        descriptor = cast(Mapping[str, Any], descriptors.get(content_format, {}))
        require(
            not (recursive_keys(schema) & forbidden),
            f"E_RECOVERY_AUTHOR_SERVER_FIELD:{content_format}",
        )
        require(
            descriptor.get("contract_version") == "diyu.author-output.v2.0",
            f"E_RECOVERY_DESCRIPTOR_VERSION:{content_format}",
        )
        require(
            descriptor.get("candidate_schema") == schema,
            f"E_RECOVERY_DESCRIPTOR_SCHEMA:{content_format}",
        )
        require(
            descriptor.get("root_fields")
            == {"candidates": "1至3份；每份按candidate_schema填写"},
            f"E_RECOVERY_DESCRIPTOR_CANDIDATE_RANGE:{content_format}",
        )


def validate_capability_mapping(root: Path) -> None:
    value = yaml.safe_load(
        (root / "content_capability_mapping.v1.yaml").read_text(encoding="utf-8")
    )
    require(isinstance(value, dict), "E_RECOVERY_CAPABILITY_ROOT")
    topics = value.get("public_topics")
    require(isinstance(topics, list) and len(topics) == 10, "E_RECOVERY_TOPIC_COUNT")
    canonical = yaml.safe_load(
        (
            REPOSITORY_ROOT / "11_product_foundation/public_foundation_001/taxonomy/"
            "topic_product_mapping.v1.yaml"
        ).read_text(encoding="utf-8")
    )["topic_product_mapping"]["categories"]
    canonical_by_label = {
        str(row["display_name"]): row for row in canonical if isinstance(row, dict)
    }
    labels: set[str] = set()
    for row in topics:
        require(isinstance(row, dict), "E_RECOVERY_TOPIC_ROW")
        label = str(row.get("display_name", ""))
        product_ids = row.get("internal_product_ids")
        legacy_labels = row.get("legacy_topic_labels")
        require(bool(label) and label not in labels, "E_RECOVERY_TOPIC_LABEL")
        require(
            isinstance(product_ids, list)
            and bool(product_ids)
            and all(
                re.fullmatch(r"CP(?:0[1-9]|1[0-9]|20)", str(item))
                for item in product_ids
            ),
            f"E_RECOVERY_TOPIC_PRODUCTS:{label}",
        )
        require(
            isinstance(legacy_labels, list)
            and bool(legacy_labels)
            and all(str(item) in canonical_by_label for item in legacy_labels),
            f"E_RECOVERY_TOPIC_CANONICAL_LABELS:{label}",
        )
        for product_id in cast(list[object], product_ids):
            require(
                any(
                    str(product_id)
                    in canonical_by_label[str(legacy_label)]["internal_product_ids"]
                    for legacy_label in cast(list[object], legacy_labels)
                ),
                f"E_RECOVERY_TOPIC_CANONICAL_CLOSURE:{label}:{product_id}",
            )
        labels.add(label)
    dsl = yaml.safe_load((root / "dify_app.v1.yaml").read_text(encoding="utf-8"))
    require(isinstance(dsl, dict), "E_RECOVERY_DIFY_DSL_ROOT")
    workflow = cast(Mapping[str, Any], dsl.get("workflow", {}))
    graph = cast(Mapping[str, Any], workflow.get("graph", {}))
    nodes = graph.get("nodes")
    require(isinstance(nodes, list), "E_RECOVERY_DIFY_GRAPH_NODES")
    start_nodes = [
        row for row in nodes if isinstance(row, dict) and row.get("id") == "start"
    ]
    require(len(start_nodes) == 1, "E_RECOVERY_DIFY_START_NODE")
    start_data = cast(Mapping[str, Any], start_nodes[0].get("data", {}))
    variables = start_data.get("variables")
    require(isinstance(variables, list), "E_RECOVERY_DIFY_INPUTS")
    topic_inputs = [
        row
        for row in variables
        if isinstance(row, dict) and row.get("variable") == "topic_label"
    ]
    require(len(topic_inputs) == 1, "E_RECOVERY_DIFY_TOPIC_INPUT")
    dify_topic_options = topic_inputs[0].get("options")
    require(
        isinstance(dify_topic_options, list)
        and labels.issubset(set(dify_topic_options)),
        "E_RECOVERY_DIFY_PUBLIC_TOPIC_PARITY",
    )
    require(
        value.get("content_formats") == list(RECOVERY_FORMATS),
        "E_RECOVERY_CAPABILITY_FORMATS",
    )
    invariants = cast(Mapping[str, Any], value.get("invariants", {}))
    require(invariants.get("one_generation_chain") is True, "E_RECOVERY_ONE_CHAIN")
    require(
        invariants.get("internal_product_ids_hidden_from_users") is True,
        "E_RECOVERY_INTERNAL_IDS_HIDDEN",
    )
    require(invariants.get("production_ready") is False, "E_RECOVERY_CAPABILITY_READY")


def validate_recovery_source_contract(root: Path) -> None:
    sources = {
        name: (root / name).read_text(encoding="utf-8")
        for name in (
            "runtime_service.py",
            "contracts.py",
            "persistence.py",
            "runtime_models.py",
            "security.py",
            "bridge_app.py",
            "portal.js",
            "deploy_remote.sh",
            "dify_chat.py",
            "test_dify_end_to_end.py",
        )
    }
    runtime = sources["runtime_service.py"]
    for marker in (
        "parse_candidate_envelope(",
        "contract_descriptor(",
        "_finalize_lightweight_candidates(",
        "_server_reference_scope(",
        "_validator_surface_projection(",
        "NEGATED_PROHIBITION_PREFIX_PATTERN",
        "fact_refs, material_refs = self._server_reference_scope",
        '"audience_surface_fields": ["title", "body", "execution_payload"]',
        '"本次参考资料范围"',
        "逐句证明",
        '"MATERIAL_GAP"',
        '"AUTHORIZATION_OR_SCOPE_BLOCK"',
        '"MODEL_OUTPUT_CONTRACT_ERROR"',
        '"HARD_FACT_REFERENCE_ERROR"',
        '"SYSTEM_OR_PROVIDER_ERROR"',
        "Historical and rejected outputs are read-only replay evidence",
        "_server_sensitive_surface_failures(",
        "_server_fact_resolution(",
        "_explicit_required_object_missing(",
        "NO_COMPLETE_SAFE_CANDIDATE",
        "本轮可选方案不足",
        "都可作为待人工审核的创意候选",
        "不授予任何登录或数据访问权限",
    ):
        require(marker in runtime, f"E_RECOVERY_RUNTIME_MARKER:{marker}")
    current_finalizer = runtime[
        runtime.index("    def _finalize_lightweight_candidates(") : runtime.index(
            "    @staticmethod\n    def _server_reference_scope("
        )
    ]
    require(
        "WRAPPED_TOP_LEVEL_CANDIDATE_ARRAY" in sources["contracts.py"],
        "E_RECOVERY_ARRAY_WRAPPER",
    )
    for marker in (
        "_server_fact_resolution(",
        "surface_requires_evidence_binding(",
        "_claim_bindings_are_closed(",
        '"HARD_FACT_REFERENCE_ERROR"',
    ):
        require(
            marker not in current_finalizer,
            f"E_RECOVERY_CURRENT_FACT_GATE_REACHABLE:{marker}",
        )
    for marker in (
        '"claim_bindings": []',
        '"server_bound_explicit_fact_count": 0',
        "if not accepted:",
        '"failure_reason": "NO_COMPLETE_SAFE_CANDIDATE"',
        '"本轮可选方案不足" if len(accepted) == 1 else None',
    ):
        require(marker in current_finalizer, f"E_RECOVERY_CURRENT_CONTRACT:{marker}")
    persistence = sources["persistence.py"]
    models = sources["runtime_models.py"]
    security = sources["security.py"]
    bridge = sources["bridge_app.py"]
    portal = sources["portal.js"]
    deploy = sources["deploy_remote.sh"]
    chat = sources["dify_chat.py"]
    require(
        'fillSelect("content_format", value.content_formats);' in portal,
        "E_RECOVERY_FORMAT_ENTRY_ENABLED",
    )
    for marker in ("（暂未开放）", "temporarilyUnavailable"):
        require(marker not in portal, f"E_RECOVERY_FORMAT_ENTRY_DISABLED:{marker}")
    for marker in (
        "runtime_browser_session",
        "start_browser_session",
        "require_browser_session",
        "revoke_browser_session",
        "RuntimeDifyConversation.browser_session_id",
        "RuntimeCandidate.browser_session_id",
    ):
        require(marker in persistence, f"E_RECOVERY_SESSION_PERSISTENCE:{marker}")
    for marker in (
        "stage_dify_response(",
        "recoverable_staged_model_output(",
        '"PROVIDER_RESPONSE_STAGED"',
        'merged_payload["provider_response_staging"]',
        'merged_payload.pop("provider_response_staging", None)',
    ):
        require(marker in persistence, f"E_RECOVERY_RESPONSE_RECOVERY:{marker}")
    require(
        'UniqueConstraint(\n            "principal_id",\n            "account_id",\n            "browser_session_id"'
        in models,
        "E_RECOVERY_CONVERSATION_UNIQUE_SCOPE",
    )
    for marker in (
        '"browser_session_id"',
        'startswith("BRS-")',
    ):
        require(marker in security, f"E_RECOVERY_SIGNED_SESSION:{marker}")
    for marker in (
        "secrets.token_urlsafe(18)",
        "start_browser_session(",
        "require_browser_session(",
        "revoke_browser_session(",
        "recoverable_staged_model_output(",
        "recovery_run_id=run_id",
    ):
        require(marker in bridge, f"E_RECOVERY_BRIDGE_SESSION:{marker}")
    require(
        "ALTER ROLE %I LOGIN PASSWORD %L" in deploy,
        "E_RECOVERY_DATABASE_LOGIN_MIGRATION",
    )
    for marker in (
        "PACKAGE7_PRESERVED_DATABASE_URL",
        "DIYU_PKG9_MANAGED_DATABASE",
        "CREATE TABLE IF NOT EXISTS runtime_browser_sessions",
        "FORCE ROW LEVEL SECURITY",
        "CREATE POLICY diyu_scope_policy ON runtime_browser_sessions",
        "SELECT pg_advisory_xact_lock(744970072);",
        "AS RESTRICTIVE",
        "package7_migration_rollback_probe",
        "diyu_pkg9_runtime",
        "-e PYTHONDONTWRITEBYTECODE=1",
    ):
        require(marker in deploy, f"E_RECOVERY_MANAGED_DATABASE:{marker}")
    require(
        "MAXIMUM_CUMULATIVE_MODEL_CALLS = 1096" in chat,
        "E_RECOVERY_CUMULATIVE_MODEL_LIMIT",
    )
    require(
        'os.environ.get("PACKAGE7_MAX_MODEL_CALLS", "1096")' in deploy,
        "E_RECOVERY_DEPLOY_CUMULATIVE_MODEL_LIMIT",
    )
    require(
        '"DIYU_COOKIE_SECURE": "true"' in deploy,
        "E_RECOVERY_DEPLOY_SECURE_COOKIE",
    )
    tests = sources["test_dify_end_to_end.py"]
    required_tests = (
        "test_light_author_contract_has_one_current_format_and_no_server_fields",
        "test_all_seven_formats_finalize_select_review_export_and_reference",
        "test_one_bad_candidate_does_not_erase_two_safe_siblings",
        "test_creative_claims_enter_human_review_without_evidence_binding",
        "test_internal_identifiers_sensitive_data_and_secrets_are_blocked",
        "test_reference_panel_records_scope_without_sentence_binding",
        "test_one_valid_candidate_is_delivered_with_option_warning",
        "test_first_output_is_preserved_and_reroll_is_forbidden",
        "test_paid_author_response_survives_completion_transaction_failure",
        "test_received_staged_response_can_resume_without_a_second_call",
        "test_portal_recovers_staged_output_before_any_new_model_call",
        "test_portal_provider_failure_is_a_system_error",
        "test_remote_deployment_uses_secure_session_cookie",
        "test_concurrent_budget_reservation_cannot_exceed_the_limit",
        "test_managed_migration_is_atomic_and_browser_rls_is_restrictive",
        "test_five_failure_classes_do_not_impersonate_material_gaps",
        "test_chat_continuity_is_same_browser_only",
        "test_same_account_candidates_and_actions_do_not_cross_browser_sessions",
        "test_logout_revokes_the_persisted_browser_session",
    )
    for marker in required_tests:
        require(marker in tests, f"E_RECOVERY_TEST_COVERAGE:{marker}")


def validate_recovery_replay(replay: Mapping[str, Any]) -> None:
    require(
        replay.get("schema")
        == "diyu.package7.output_contract_recovery.p10_zero_call_replay.v1",
        "E_RECOVERY_REPLAY_SCHEMA",
    )
    require(replay.get("task_id") == RECOVERY_TASK_ID, "E_RECOVERY_REPLAY_TASK")
    require(
        replay.get("source_failed_commit") == FAILED_PACKAGE10_COMMIT,
        "E_RECOVERY_REPLAY_COMMIT",
    )
    require(
        replay.get("source_restricted_evidence_sha256")
        == FAILED_PACKAGE10_EVIDENCE_SHA256,
        "E_RECOVERY_REPLAY_SOURCE_DIGEST",
    )
    require(
        replay.get("new_content_model_call_increment") == 0, "E_RECOVERY_REPLAY_CALLS"
    )
    require(
        replay.get("source_private_bytes_modified") is False,
        "E_RECOVERY_REPLAY_SOURCE_MUTATION",
    )
    require(
        replay.get("old_output_digest_preserved") is True, "E_RECOVERY_REPLAY_DIGEST"
    )
    aggregate = cast(Mapping[str, Any], replay.get("aggregate_classification", {}))
    require(
        aggregate
        == {
            "task_count": 30,
            "MATERIAL_GAP": 1,
            "AUTHORIZATION_OR_SCOPE_BLOCK": 0,
            "MODEL_OUTPUT_CONTRACT_ERROR": 20,
            "HARD_FACT_REFERENCE_ERROR": 8,
            "SYSTEM_OR_PROVIDER_ERROR": 1,
        },
        "E_RECOVERY_REPLAY_AGGREGATE",
    )
    cases = replay.get("cases")
    require(isinstance(cases, list) and len(cases) == 30, "E_RECOVERY_REPLAY_CASES")
    ids = {str(row.get("task_id")) for row in cases if isinstance(row, dict)}
    require(
        ids == {f"DAY-{number:02d}" for number in range(1, 31)}, "E_RECOVERY_REPLAY_IDS"
    )
    gaps = {
        str(row.get("task_id"))
        for row in cases
        if isinstance(row, dict) and row.get("replay_class") == "MATERIAL_GAP"
    }
    require(gaps == {"DAY-09"}, "E_RECOVERY_REPLAY_GAPS")
    day09 = next(
        cast(Mapping[str, Any], row)
        for row in cases
        if isinstance(row, dict) and row.get("task_id") == "DAY-09"
    )
    require(
        day09.get("classification_resolution")
        == "CURRENT_REMOTE_RETRIEVAL_CONFIRMED_MATERIAL_GAP",
        "E_RECOVERY_REPLAY_DAY09_RESOLUTION",
    )
    require(
        day09.get("current_remote_retrieval_retested") is True
        and day09.get("current_remote_retrieval_account_id")
        == "ACCOUNT-DIYU-JS-STYLING-SERVICE"
        and day09.get("current_remote_retrieval_accepted_fragment_count") == 0
        and day09.get("current_remote_retrieval_fragment_ids") == []
        and day09.get("current_remote_retrieval_gap_codes")
        == ["MATERIAL_MISSING_FOR_SCOPE"]
        and day09.get("current_remote_retrieval_prefilter_applied") is True
        and day09.get("current_remote_retrieval_content_model_call_count") == 0,
        "E_RECOVERY_REPLAY_DAY09_LIVE_RETEST",
    )
    require(
        bool(
            re.fullmatch(
                r"[0-9a-f]{64}",
                str(day09.get("current_remote_retrieval_query_sha256", "")),
            )
        ),
        "E_RECOVERY_REPLAY_DAY09_QUERY_DIGEST",
    )
    mapping_errors = {
        str(row.get("task_id"))
        for row in cases
        if isinstance(row, dict)
        and row.get("classification_resolution")
        == "SOURCE_PERSON_ACCOUNT_MAPPING_ERROR"
    }
    require(mapping_errors == {"DAY-13"}, "E_RECOVERY_REPLAY_MAPPING_ERRORS")
    for row in cases:
        require(isinstance(row, dict), "E_RECOVERY_REPLAY_CASE")
        require(row.get("new_model_call_increment") == 0, "E_RECOVERY_REPLAY_CASE_CALL")
        require(
            bool(re.fullmatch(r"[0-9a-f]{64}", str(row.get("old_answer_sha256", "")))),
            "E_RECOVERY_REPLAY_ANSWER_DIGEST",
        )
        task_id = str(row.get("task_id"))
        if task_id in gaps:
            expected_classes = ["MATERIAL_GAP"]
        elif task_id in mapping_errors:
            expected_classes = ["SYSTEM_OR_PROVIDER_ERROR"]
        else:
            expected_classes = [
                "MODEL_OUTPUT_CONTRACT_ERROR",
                "HARD_FACT_REFERENCE_ERROR",
            ]
        require(
            row.get("proven_candidate_classes") == expected_classes,
            f"E_RECOVERY_REPLAY_CLASS:{task_id}",
        )
    limit = cast(Mapping[str, Any], replay.get("evidence_limit", {}))
    require(
        limit.get("per_task_model_vs_hard_fact_subclass_binding_retained") is False,
        "E_RECOVERY_REPLAY_FALSE_PRECISION",
    )


def run_recovery_unit_tests(root: Path) -> int:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, "-m", "unittest", "test_dify_end_to_end.py"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
        env=environment,
    )
    require(
        process.returncode == 0,
        f"E_RECOVERY_UNIT_TESTS:{process.stdout[-500:]}:{process.stderr[-500:]}",
    )
    combined = process.stdout + process.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    require(match is not None and "OK" in combined, "E_RECOVERY_UNIT_TEST_SUMMARY")
    return int(match.group(1))


def validate_recovery_implementation(
    root: Path, *, implementation_only: bool
) -> JsonObject:
    validate_recovery_file_set(root, implementation_only=implementation_only)
    validate_recovery_historical_bytes(root)
    validate_recovery_write_scope()
    projection = author_contract_projection(root)
    validate_author_contract_projection(projection)
    validate_capability_mapping(root)
    validate_recovery_source_contract(root)
    replay = load_json(root / RECOVERY_REPLAY_PATH)
    validate_recovery_replay(replay)
    unit_test_count = run_recovery_unit_tests(root)
    return {
        "author_contract_version": projection["contract_version"],
        "format_count": len(RECOVERY_FORMATS),
        "topic_count": 10,
        "unit_test_count": unit_test_count,
        "p10_replay_case_count": 30,
        "p10_replay_model_call_increment": 0,
    }


def validate_recovery_readiness(value: Mapping[str, Any], code: str) -> None:
    require(set(value) == REQUIRED_FALSE_FLAGS, f"{code}:FLAG_SET")
    for key in REQUIRED_FALSE_FLAGS:
        require(value.get(key) is False, f"{code}:{key}")


def validate_failure_matrix(value: Mapping[str, Any]) -> None:
    require(set(value) == RECOVERY_RESULT_CLASSES, "E_RECOVERY_FAILURE_CLASS_SET")
    for result_class in RECOVERY_RESULT_CLASSES:
        expected_card = result_class == "MATERIAL_GAP"
        require(
            value.get(result_class) is expected_card,
            f"E_RECOVERY_FAILURE_CARD:{result_class}",
        )


def validate_local_acceptance(evidence: Mapping[str, Any]) -> None:
    require(
        evidence.get("schema")
        == "diyu.package7.output_contract_recovery.local_acceptance.v1",
        "E_RECOVERY_LOCAL_SCHEMA",
    )
    require(evidence.get("task_id") == RECOVERY_TASK_ID, "E_RECOVERY_LOCAL_TASK")
    require(
        evidence.get("author_contract_version") == "diyu.author-output.v2.0",
        "E_RECOVERY_LOCAL_CONTRACT",
    )
    require(
        evidence.get("content_formats") == list(RECOVERY_FORMATS),
        "E_RECOVERY_LOCAL_FORMATS",
    )
    require(evidence.get("public_topic_count") == 10, "E_RECOVERY_LOCAL_TOPICS")
    tests = cast(Mapping[str, Any], evidence.get("unit_tests", {}))
    require(
        isinstance(tests.get("count"), int)
        and int(tests["count"]) > 0
        and tests.get("pass") is True,
        "E_RECOVERY_LOCAL_TESTS",
    )
    require(
        evidence.get("candidate_count_range") == [1, 3],
        "E_RECOVERY_LOCAL_CANDIDATE_RANGE",
    )
    validate_failure_matrix(
        cast(Mapping[str, Any], evidence.get("action_card_by_result_class", {}))
    )
    for key in (
        "single_bad_candidate_preserves_two_safe_siblings",
        "server_owned_reference_scope",
        "anonymous_daily_scene_allowed",
        "future_shooting_scene_allowed",
        "similarity_is_review_hint_only",
        "ordinary_creative_surfaces_do_not_require_fact_binding",
        "creative_claims_without_evidence_binding_allowed",
        "single_complete_candidate_delivered",
        "ordinary_creation_without_retrieval_allowed",
        "explicit_missing_object_requires_material_card",
        "internal_and_sensitive_reference_leakage_blocked",
        "manual_review_required_before_publish",
        "failed_user_surface_internal_run_id_free",
        "paid_provider_response_staged_before_completion",
        "concurrent_budget_reservation_atomic",
        "managed_migration_transaction_and_rollback_declared",
        "legacy_contract_replay_read_only",
        "two_browser_candidate_isolation",
        "two_browser_chat_isolation",
        "logout_revokes_session",
        "historical_package7_bytes_unchanged",
        "package10_zero_call_replay_pass",
    ):
        require(evidence.get(key) is True, f"E_RECOVERY_LOCAL_INVARIANT:{key}")
    require(
        evidence.get("current_entry_fact_gate_reachable") is False
        and evidence.get("current_hard_fact_reference_error_reachable") is False,
        "E_RECOVERY_LOCAL_RETIRED_FACT_GATE",
    )
    require(
        evidence.get("single_candidate_option_warning") == "本轮可选方案不足",
        "E_RECOVERY_LOCAL_SINGLE_WARNING",
    )
    require(
        evidence.get("staged_response_recovery_new_model_call_count") == 0,
        "E_RECOVERY_LOCAL_STAGED_RECOVERY_CALLS",
    )
    require(
        evidence.get("package10_replay_model_call_increment") == 0,
        "E_RECOVERY_LOCAL_REPLAY_CALLS",
    )
    core = cast(Mapping[str, Any], evidence.get("core_numbers", {}))
    require(
        core == {"300": 300, "120": 120, "86": 86, "changed": False},
        "E_RECOVERY_LOCAL_CORE",
    )
    validate_recovery_readiness(
        cast(Mapping[str, Any], evidence.get("readiness", {})),
        "E_RECOVERY_LOCAL_READINESS",
    )


def validate_remote_probe(evidence: Mapping[str, Any]) -> None:
    require(
        evidence.get("schema")
        == "diyu.package7.output_contract_recovery.remote_probe.v2",
        "E_RECOVERY_REMOTE_SCHEMA",
    )
    require(evidence.get("task_id") == RECOVERY_TASK_ID, "E_RECOVERY_REMOTE_TASK")
    state = evidence.get("state")
    require(
        state in {RECOVERY_SUCCESS_STATE, RECOVERY_DEGRADED_STATE},
        "E_RECOVERY_REMOTE_STATE",
    )
    offline_enabled = state == RECOVERY_SUCCESS_STATE
    require(
        evidence.get("offline_material_enabled") is offline_enabled,
        "E_RECOVERY_REMOTE_OFFLINE_STATE",
    )
    objects = cast(Mapping[str, Any], evidence.get("existing_objects", {}))
    require(
        objects
        == {
            "dify_app_count": 1,
            "dataset_count": 1,
            "runtime_database_count": 1,
            "runtime_bridge_count": 1,
            "parallel_object_count": 0,
            "reused_in_place": True,
        },
        "E_RECOVERY_REMOTE_OBJECTS",
    )
    deployment = cast(Mapping[str, Any], evidence.get("deployment", {}))
    for key in (
        "backup_before_update",
        "in_place_update",
        "migration_pass",
        "rollback_test_pass",
        "post_rollback_redeploy_pass",
    ):
        require(deployment.get(key) is True, f"E_RECOVERY_REMOTE_DEPLOYMENT:{key}")
    require(
        deployment.get("final_service_health") == "healthy"
        and deployment.get("simulation_only") is True
        and deployment.get("production_ready") is False,
        "E_RECOVERY_REMOTE_HEALTH",
    )

    audit = cast(Mapping[str, Any], evidence.get("model_call_audit", {}))
    call_count = audit.get("new_content_model_call_count")
    require(
        audit.get("baseline_invocation_count") == 203
        and audit.get("baseline_cumulative_model_call_upper_bound") == 207
        and audit.get("authorized_new_content_model_call_limit") == 2,
        "E_RECOVERY_REMOTE_CALL_BASELINE",
    )
    require(
        isinstance(call_count, int)
        and 1 <= int(call_count) <= 2
        and audit.get("new_model_call_upper_bound") == call_count
        and audit.get("final_invocation_count") == 203 + int(call_count)
        and audit.get("final_cumulative_model_call_upper_bound")
        == 207 + int(call_count)
        and audit.get("model_call_limit_exceeded") is False,
        "E_RECOVERY_REMOTE_CALLS",
    )
    require(audit.get("content_quality_reroll_count") == 0, "E_RECOVERY_REMOTE_REROLL")
    require(
        audit.get("failed_calls_retained") is True,
        "E_RECOVERY_REMOTE_FAILURE_RETENTION",
    )
    try:
        cost = Decimal(str(audit.get("known_new_cost_rmb")))
    except InvalidOperation as exc:
        raise CheckFailure("E_RECOVERY_REMOTE_COST_FORMAT") from exc
    require(cost <= Decimal("1"), "E_RECOVERY_REMOTE_COST")
    require(
        isinstance(audit.get("ledger_digest"), str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", str(audit.get("ledger_digest")))),
        "E_RECOVERY_REMOTE_LEDGER_DIGEST",
    )

    replay = cast(Mapping[str, Any], evidence.get("six_format_zero_call_replay", {}))
    require(
        replay.get("format_count") == 6
        and replay.get("new_content_model_call_count") == 0,
        "E_RECOVERY_REMOTE_REPLAY_SUMMARY",
    )
    for key in (
        "selection_pass",
        "natural_language_revision_pass",
        "review_pass",
        "export_pass",
        "reference_lookup_pass",
    ):
        require(replay.get(key) is True, f"E_RECOVERY_REMOTE_REPLAY:{key}")

    probes = evidence.get("format_probes")
    require(
        isinstance(probes, list) and len(probes) == 7,
        "E_RECOVERY_REMOTE_PROBE_COUNT",
    )
    formats: set[str] = set()
    for row in probes:
        require(isinstance(row, dict), "E_RECOVERY_REMOTE_PROBE")
        content_format = str(row.get("content_format", ""))
        formats.add(content_format)
        probe_state = row.get("probe_state")
        if content_format == "门店线下物料" and not offline_enabled:
            require(
                probe_state == "DISABLED"
                and row.get("candidate_count") == 0
                and row.get("entry_enabled") is False
                and row.get("attempt_count") == call_count
                and isinstance(row.get("blocking_item"), str)
                and bool(row["blocking_item"]),
                "E_RECOVERY_REMOTE_OFFLINE_DISABLED",
            )
            continue
        expected_state = (
            "LIVE_PASS" if content_format == "门店线下物料" else "REPLAY_PASS"
        )
        require(
            probe_state == expected_state,
            f"E_RECOVERY_REMOTE_PROBE_STATE:{content_format}",
        )
        candidate_count = row.get("candidate_count")
        require(
            isinstance(candidate_count, int) and 1 <= int(candidate_count) <= 3,
            f"E_RECOVERY_REMOTE_CANDIDATE_COUNT:{content_format}",
        )
        expected_warning = "本轮可选方案不足" if candidate_count == 1 else None
        require(
            row.get("candidate_option_warning") == expected_warning,
            f"E_RECOVERY_REMOTE_CANDIDATE_WARNING:{content_format}",
        )
        expected_calls = call_count if content_format == "门店线下物料" else 0
        require(
            row.get("new_model_call_increment") == expected_calls,
            f"E_RECOVERY_REMOTE_FORMAT_CALLS:{content_format}",
        )
        for key in (
            "first_output_retained",
            "selection_pass",
            "natural_language_revision_pass",
            "review_pass",
            "export_pass",
            "reference_scope_pass",
            "internal_identifier_leak_free",
            "sensitive_information_leak_free",
        ):
            require(
                row.get(key) is True,
                f"E_RECOVERY_REMOTE_PROBE:{content_format}:{key}",
            )
    require(formats == set(RECOVERY_FORMATS), "E_RECOVERY_REMOTE_FORMATS")

    journeys = cast(Mapping[str, Any], evidence.get("representative_journeys", {}))
    require(
        cast(Mapping[str, Any], journeys.get("ordinary_creation_without_retrieval", {})).get(
            "result_class"
        )
        == "SUCCESS",
        "E_RECOVERY_REMOTE_NO_RETRIEVAL",
    )
    material = cast(Mapping[str, Any], journeys.get("explicit_missing_object", {}))
    require(
        material.get("result_class") == "MATERIAL_GAP"
        and material.get("action_card") is True
        and material.get("model_call_increment") == 0,
        "E_RECOVERY_REMOTE_MATERIAL_GAP",
    )
    authorization = cast(Mapping[str, Any], journeys.get("authorization_block", {}))
    require(
        authorization.get("result_class") == "AUTHORIZATION_OR_SCOPE_BLOCK"
        and authorization.get("action_card") is False
        and authorization.get("model_call_increment") == 0,
        "E_RECOVERY_REMOTE_AUTHORIZATION",
    )
    browsers = cast(Mapping[str, Any], journeys.get("two_browser_sessions", {}))
    for key in (
        "chat_isolated",
        "candidates_isolated",
        "selection_isolated",
        "revision_isolated",
        "review_isolated",
        "export_isolated",
        "reference_scope_isolated",
        "same_session_continuity_pass",
        "revoked_session_rejected",
    ):
        require(browsers.get(key) is True, f"E_RECOVERY_REMOTE_BROWSER:{key}")
    require(
        evidence.get("staged_response_recovery_new_model_calls") == 0,
        "E_RECOVERY_REMOTE_STAGED_RECOVERY",
    )
    require(
        evidence.get("package10_replay_new_model_calls") == 0,
        "E_RECOVERY_REMOTE_REPLAY_CALLS",
    )
    core = cast(Mapping[str, Any], evidence.get("core_numbers", {}))
    require(
        core == {"300": 300, "120": 120, "86": 86, "changed": False},
        "E_RECOVERY_REMOTE_CORE",
    )
    validate_recovery_readiness(
        cast(Mapping[str, Any], evidence.get("readiness", {})),
        "E_RECOVERY_REMOTE_READINESS",
    )

def validate_recovery_candidate_binding(result: Mapping[str, Any]) -> tuple[str, str]:
    candidate_commit = str(result.get("reviewed_candidate_commit", ""))
    candidate_tree_digest = str(result.get("reviewed_candidate_tree", ""))
    require(
        bool(re.fullmatch(r"[0-9a-f]{40}", candidate_commit)),
        "E_RECOVERY_CANDIDATE_COMMIT",
    )
    require(
        bool(re.fullmatch(r"[0-9a-f]{40}", candidate_tree_digest)),
        "E_RECOVERY_CANDIDATE_TREE",
    )
    require(
        candidate_tree(candidate_commit) == candidate_tree_digest,
        "E_RECOVERY_CANDIDATE_TREE_MISMATCH",
    )
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate_commit, "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    require(process.returncode == 0, "E_RECOVERY_CANDIDATE_NOT_ANCESTOR")
    allowed_after_freeze = {
        PACKAGE_RELATIVE_ROOT / RECOVERY_RESULT_PATH,
        PACKAGE_RELATIVE_ROOT / RECOVERY_DELIVERY_PATH,
        *(PACKAGE_RELATIVE_ROOT / path for path in RECOVERY_REVIEW_PATHS),
        *RECOVERY_AUTHORIZED_REPOSITORY_PATHS,
        *PACKAGE10_FINAL_RUNTIME_PATHS,
    }
    changed = {
        Path(line)
        for line in git_output(
            "diff", "--name-only", f"{candidate_commit}..HEAD"
        ).splitlines()
        if line
    }
    require(
        changed <= allowed_after_freeze,
        f"E_RECOVERY_POST_FREEZE_IMPLEMENTATION:{sorted(map(str, changed - allowed_after_freeze))}",
    )
    return candidate_commit, candidate_tree_digest


def validate_recovery_reviews(
    root: Path,
    result: Mapping[str, Any],
    candidate_commit: str,
    candidate_tree_digest: str,
) -> None:
    reviews: list[JsonObject] = []
    for path in RECOVERY_REVIEW_PATHS:
        review = load_yaml_root(root / path, "review")
        require(
            review.get("task_id") == RECOVERY_TASK_ID, f"E_RECOVERY_REVIEW_TASK:{path}"
        )
        require(
            review.get("candidate_commit") == candidate_commit,
            f"E_RECOVERY_REVIEW_COMMIT:{path}",
        )
        require(
            review.get("candidate_tree") == candidate_tree_digest,
            f"E_RECOVERY_REVIEW_TREE:{path}",
        )
        require(review.get("verdict") == "PASS", f"E_RECOVERY_REVIEW_VERDICT:{path}")
        require(
            isinstance(review.get("score"), int) and int(review["score"]) >= 90,
            f"E_RECOVERY_REVIEW_SCORE:{path}",
        )
        require(review.get("hard_veto") is False, f"E_RECOVERY_REVIEW_VETO:{path}")
        require(
            review.get("blocking_items") == [], f"E_RECOVERY_REVIEW_BLOCKERS:{path}"
        )
        require(
            review.get("independent_from_executor_and_other_reviewer") is True,
            f"E_RECOVERY_REVIEW_INDEPENDENCE:{path}",
        )
        for key in (
            "review_id",
            "reviewer_identity",
            "reviewer_session_id",
            "reviewer_run_id",
            "signed_at",
            "signature_sha256",
        ):
            require(
                isinstance(review.get(key), str) and bool(review[key]),
                f"E_RECOVERY_REVIEW_ID:{path}:{key}",
            )
        require(
            bool(re.fullmatch(r"[0-9a-f]{64}", str(review["signature_sha256"]))),
            f"E_RECOVERY_REVIEW_SIGNATURE:{path}",
        )
        require(
            isinstance(review.get("evidence"), list) and len(review["evidence"]) >= 5,
            f"E_RECOVERY_REVIEW_EVIDENCE:{path}",
        )
        reviews.append(review)
    validate_review_pair_bindings(
        reviews,
        candidate_commit=candidate_commit,
        candidate_tree_digest=candidate_tree_digest,
    )
    require(
        {str(row.get("review_type")) for row in reviews} == RECOVERY_REVIEW_TYPES,
        "E_RECOVERY_REVIEW_TYPES",
    )
    declared = result.get("independent_reviews")
    require(
        isinstance(declared, list) and len(declared) == 2,
        "E_RECOVERY_RESULT_REVIEW_COUNT",
    )
    require(
        {
            str(row.get("review_id"))
            for row in cast(list[Any], declared)
            if isinstance(row, dict)
        }
        == {str(row.get("review_id")) for row in reviews},
        "E_RECOVERY_RESULT_REVIEW_BINDING",
    )


def validate_review_pair_bindings(
    reviews: list[JsonObject],
    *,
    candidate_commit: str,
    candidate_tree_digest: str,
) -> None:
    require(len(reviews) == 2, "E_RECOVERY_REVIEW_PAIR_COUNT")
    for review in reviews:
        require(
            review.get("candidate_commit") == candidate_commit,
            "E_RECOVERY_REVIEW_PAIR_COMMIT",
        )
        require(
            review.get("candidate_tree") == candidate_tree_digest,
            "E_RECOVERY_REVIEW_PAIR_TREE",
        )
    for key in (
        "reviewer_identity",
        "reviewer_session_id",
        "reviewer_run_id",
        "signature_sha256",
    ):
        require(
            len({str(row.get(key, "")) for row in reviews}) == 2,
            f"E_RECOVERY_REVIEW_COLLISION:{key}",
        )


def validate_recovery_prior_failed_reviews(
    root: Path,
    result: Mapping[str, Any],
) -> None:
    reviews: list[JsonObject] = []
    for path in RECOVERY_PRIOR_REVIEW_PATHS:
        absolute_path = root / path
        repository_path = PACKAGE_RELATIVE_ROOT / path
        require(
            absolute_path.read_bytes()
            == git_blob(RECOVERY_PRIOR_REVIEW_EVIDENCE_COMMIT, repository_path),
            f"E_RECOVERY_PRIOR_REVIEW_CHANGED:{path}",
        )
        loaded = yaml.safe_load(absolute_path.read_text(encoding="utf-8"))
        require(isinstance(loaded, dict), f"E_RECOVERY_PRIOR_REVIEW_OBJECT:{path}")
        review = cast(JsonObject, loaded)
        require(
            review.get("task_id") == RECOVERY_TASK_ID,
            f"E_RECOVERY_PRIOR_REVIEW_TASK:{path}",
        )
        require(
            review.get("candidate_commit")
            == RECOVERY_PRIOR_REVIEWED_CANDIDATE_COMMIT
            and review.get("candidate_tree")
            == RECOVERY_PRIOR_REVIEWED_CANDIDATE_TREE,
            f"E_RECOVERY_PRIOR_REVIEW_BINDING:{path}",
        )
        require(
            review.get("verdict") == "FAIL" and review.get("hard_veto") is True,
            f"E_RECOVERY_PRIOR_REVIEW_VERDICT:{path}",
        )
        reviews.append(review)
    declared = result.get("prior_failed_reviews")
    require(
        isinstance(declared, list) and len(declared) == 2,
        "E_RECOVERY_PRIOR_REVIEW_COUNT",
    )
    require(
        {
            str(row.get("review_id"))
            for row in cast(list[Any], declared)
            if isinstance(row, dict)
        }
        == {str(review.get("review_id")) for review in reviews},
        "E_RECOVERY_PRIOR_REVIEW_DECLARATION",
    )
    require(
        all(
            isinstance(row, dict)
            and row.get("status") == "HISTORICAL_FAILED_REVIEW_NOT_CURRENT_APPROVAL"
            for row in cast(list[Any], declared)
        ),
        "E_RECOVERY_PRIOR_REVIEW_STATUS",
    )
    for path in (RECOVERY_PRIOR_RESULT_PATH, RECOVERY_PRIOR_DELIVERY_PATH):
        require(
            (root / path).read_bytes()
            == git_blob(RECOVERY_PRIOR_ARTIFACT_COMMIT, PACKAGE_RELATIVE_ROOT / path),
            f"E_RECOVERY_PRIOR_ARTIFACT_CHANGED:{path}",
        )


def validate_recovery_result(root: Path, result: Mapping[str, Any]) -> None:
    require(
        result.get("schema") == "diyu.package7.output_contract_recovery.result.v2",
        "E_RECOVERY_RESULT_SCHEMA",
    )
    require(result.get("task_id") == RECOVERY_TASK_ID, "E_RECOVERY_RESULT_TASK")
    state = result.get("state")
    require(
        state in {RECOVERY_SUCCESS_STATE, RECOVERY_DEGRADED_STATE},
        "E_RECOVERY_RESULT_STATE",
    )
    require(result.get("blocking_items") == [], "E_RECOVERY_RESULT_BLOCKERS")
    require(
        result.get("offline_material_enabled") is (state == RECOVERY_SUCCESS_STATE),
        "E_RECOVERY_RESULT_OFFLINE_STATE",
    )
    candidate_commit, candidate_tree_digest = validate_recovery_candidate_binding(
        result
    )
    acceptance = cast(Mapping[str, Any], result.get("acceptance", {}))
    expected_acceptance = {f"P7F-A{number:02d}" for number in range(1, 15)}
    require(set(acceptance) == expected_acceptance, "E_RECOVERY_RESULT_ACCEPTANCE_SET")
    for key in expected_acceptance:
        require(acceptance.get(key) is True, f"E_RECOVERY_RESULT_ACCEPTANCE:{key}")

    calls = cast(Mapping[str, Any], result.get("model_call_audit", {}))
    call_count = calls.get("new_content_model_call_count")
    require(
        isinstance(call_count, int)
        and 1 <= int(call_count) <= 2
        and calls.get("authorized_new_content_model_call_limit") == 2,
        "E_RECOVERY_RESULT_CALLS",
    )
    require(
        Decimal(str(calls.get("new_cost_rmb"))) <= Decimal("1"),
        "E_RECOVERY_RESULT_COST",
    )
    require(calls.get("content_quality_reroll_count") == 0, "E_RECOVERY_RESULT_REROLL")
    require(
        result.get("core_numbers")
        == {"300": 300, "120": 120, "86": 86, "changed": False},
        "E_RECOVERY_RESULT_CORE",
    )
    validate_recovery_readiness(
        cast(Mapping[str, Any], result.get("readiness", {})),
        "E_RECOVERY_RESULT_READINESS",
    )
    require(result.get("merge_allowed") is False, "E_RECOVERY_RESULT_MERGE")
    require(result.get("package10_started") is False, "E_RECOVERY_RESULT_PACKAGE10")
    require(
        isinstance(result.get("draft_pull_request_url"), str)
        and str(result["draft_pull_request_url"]).startswith("https://"),
        "E_RECOVERY_RESULT_DRAFT_PR",
    )
    checks = cast(Mapping[str, Any], result.get("checks", {}))
    for key in (
        "package7_unit_tests",
        "package7_implementation_checker",
        "package7_current_checker",
        "package7_current_selftest",
        "package7_optimized_fail_closed",
        "ruff",
        "type_check",
        "git_diff_check",
        "current_branch_secret_scan",
        "full_history_secret_scan",
        "public_foundation_checker",
        "gate1_current_checker",
        "remote_checker_compatibility",
        "remote_secret_scan",
    ):
        require(
            str(checks.get(key, "")).startswith("PASS"),
            f"E_RECOVERY_RESULT_CHECK:{key}",
        )
    validate_recovery_reviews(
        root,
        result,
        candidate_commit,
        candidate_tree_digest,
    )
    validate_recovery_prior_failed_reviews(root, result)
    delivery = load_yaml_root(root / RECOVERY_DELIVERY_PATH, "execution_review_request")
    require(delivery.get("task_id") == RECOVERY_TASK_ID, "E_RECOVERY_DELIVERY_TASK")
    require(
        delivery.get("candidate_commit") == candidate_commit
        and delivery.get("candidate_tree") == candidate_tree_digest,
        "E_RECOVERY_DELIVERY_BINDING",
    )
    require(
        delivery.get("status") == "REQUESTING_APPROVE_PACKAGE_7_RECOVERY_MERGE",
        "E_RECOVERY_DELIVERY_STATUS",
    )
    require(
        delivery.get("requested_root_decision") == "APPROVE_PACKAGE_7_RECOVERY_MERGE",
        "E_RECOVERY_DELIVERY_REQUEST",
    )
    require(
        delivery.get("merge_authorization") == "NOT_GRANTED",
        "E_RECOVERY_DELIVERY_MERGE",
    )
    require(
        delivery.get("draft_pull_request_url") == result.get("draft_pull_request_url"),
        "E_RECOVERY_DELIVERY_PR",
    )
    require(
        delivery.get("draft_pull_request_required") is True,
        "E_RECOVERY_DELIVERY_DRAFT",
    )
    require(delivery.get("package10_started") is False, "E_RECOVERY_DELIVERY_PACKAGE10")

def validate_recovery_workflow() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )
    historical_call = (
        'run_downstream_package_checker "17_dify_runtime/dify_end_to_end_001" '
        '"17_dify_runtime/dify_end_to_end_001/check_dify_end_to_end.py" "true" '
        f'"{HISTORICAL_PACKAGE7_COMMIT}"'
    )
    historical_optimized = historical_call.replace(
        "run_downstream_package_checker ",
        "run_downstream_package_checker_optimized ",
    )
    require(historical_call in workflow, "E_RECOVERY_WORKFLOW_HISTORICAL")
    require(
        historical_optimized in workflow, "E_RECOVERY_WORKFLOW_HISTORICAL_OPTIMIZED"
    )
    current_call = (
        'run_downstream_package_checker "17_dify_runtime/dify_end_to_end_001" '
        '"17_dify_runtime/dify_end_to_end_001/check_dify_end_to_end.py" "true"'
    )
    current_optimized_call = (
        "run_downstream_package_checker_optimized "
        '"17_dify_runtime/dify_end_to_end_001" '
        '"17_dify_runtime/dify_end_to_end_001/check_dify_end_to_end.py" "true"'
    )
    require(current_call in workflow, "E_RECOVERY_WORKFLOW_CURRENT")
    require(
        current_optimized_call in workflow,
        "E_RECOVERY_WORKFLOW_CURRENT_OPTIMIZED",
    )


def validate_recovery_all(root: Path = PACKAGE_ROOT) -> JsonObject:
    implementation = validate_recovery_implementation(root, implementation_only=False)
    local = load_json(root / RECOVERY_LOCAL_EVIDENCE_PATH)
    remote = load_json(root / RECOVERY_REMOTE_EVIDENCE_PATH)
    result = load_json(root / RECOVERY_RESULT_PATH)
    validate_local_acceptance(local)
    validate_remote_probe(remote)
    validate_recovery_result(root, result)
    validate_recovery_workflow()
    return {
        "task_id": RECOVERY_TASK_ID,
        "status": "PASS",
        "success_state": result["state"],
        **implementation,
        "model_call_count": remote["model_call_audit"]["new_content_model_call_count"],
        "review_count": 2,
        "acceptance_pass": True,
        "readiness_transition_count": 0,
        "core_numbers_changed": False,
    }


def run_recovery_selftest(root: Path = PACKAGE_ROOT) -> JsonObject:
    projection = author_contract_projection(root)
    changed_projection = copy.deepcopy(projection)
    first_format = RECOVERY_FORMATS[0]
    changed_projection["model_fields"][first_format].append("used_fact_refs")
    expect_failure(
        lambda: validate_author_contract_projection(changed_projection),
        "E_RECOVERY_AUTHOR_FIELDS",
    )

    changed_projection = copy.deepcopy(projection)
    changed_projection["model_fields"][first_format].append("article")
    expect_failure(
        lambda: validate_author_contract_projection(changed_projection),
        "E_RECOVERY_AUTHOR_FIELDS",
    )

    replay = load_json(root / RECOVERY_REPLAY_PATH)
    changed_replay = copy.deepcopy(replay)
    changed_replay["source_restricted_evidence_sha256"] = "0" * 64
    expect_failure(
        lambda: validate_recovery_replay(changed_replay),
        "E_RECOVERY_REPLAY_SOURCE_DIGEST",
    )

    changed_replay = copy.deepcopy(replay)
    changed_replay["new_content_model_call_increment"] = 1
    expect_failure(
        lambda: validate_recovery_replay(changed_replay),
        "E_RECOVERY_REPLAY_CALLS",
    )

    changed_replay = copy.deepcopy(replay)
    changed_replay["cases"][8]["replay_class"] = "AUTHORIZATION_OR_SCOPE_BLOCK"
    expect_failure(
        lambda: validate_recovery_replay(changed_replay),
        "E_RECOVERY_REPLAY_GAPS",
    )

    valid_matrix = {key: key == "MATERIAL_GAP" for key in RECOVERY_RESULT_CLASSES}
    changed_matrix = dict(valid_matrix)
    changed_matrix["MODEL_OUTPUT_CONTRACT_ERROR"] = True
    expect_failure(
        lambda: validate_failure_matrix(changed_matrix),
        "E_RECOVERY_FAILURE_CARD:MODEL_OUTPUT_CONTRACT_ERROR",
    )

    valid_readiness = {key: False for key in REQUIRED_FALSE_FLAGS}
    changed_readiness = dict(valid_readiness)
    changed_readiness["production_ready"] = True
    expect_failure(
        lambda: validate_recovery_readiness(
            changed_readiness,
            "E_RECOVERY_SELFTEST_READINESS",
        ),
        "E_RECOVERY_SELFTEST_READINESS:production_ready",
    )

    synthetic_remote: JsonObject = {
        "schema": "diyu.package7.output_contract_recovery.remote_probe.v2",
        "task_id": RECOVERY_TASK_ID,
        "state": RECOVERY_SUCCESS_STATE,
        "offline_material_enabled": True,
        "existing_objects": {
            "dify_app_count": 1,
            "dataset_count": 1,
            "runtime_database_count": 1,
            "runtime_bridge_count": 1,
            "parallel_object_count": 0,
            "reused_in_place": True,
        },
        "deployment": {
            "backup_before_update": True,
            "in_place_update": True,
            "migration_pass": True,
            "rollback_test_pass": True,
            "post_rollback_redeploy_pass": True,
            "final_service_health": "healthy",
            "simulation_only": True,
            "production_ready": False,
        },
        "model_call_audit": {
            "baseline_invocation_count": 203,
            "baseline_cumulative_model_call_upper_bound": 207,
            "authorized_new_content_model_call_limit": 2,
            "new_content_model_call_count": 1,
            "new_model_call_upper_bound": 1,
            "final_invocation_count": 204,
            "final_cumulative_model_call_upper_bound": 208,
            "model_call_limit_exceeded": False,
            "known_new_cost_rmb": "0",
            "content_quality_reroll_count": 0,
            "failed_calls_retained": True,
            "ledger_digest": "a" * 64,
        },
        "six_format_zero_call_replay": {
            "format_count": 6,
            "new_content_model_call_count": 0,
            "selection_pass": True,
            "natural_language_revision_pass": True,
            "review_pass": True,
            "export_pass": True,
            "reference_lookup_pass": True,
        },
        "format_probes": [
            {
                "content_format": content_format,
                "probe_state": (
                    "LIVE_PASS"
                    if content_format == "门店线下物料"
                    else "REPLAY_PASS"
                ),
                "candidate_count": 2,
                "candidate_option_warning": None,
                "new_model_call_increment": (
                    1 if content_format == "门店线下物料" else 0
                ),
                "first_output_retained": True,
                "selection_pass": True,
                "natural_language_revision_pass": True,
                "review_pass": True,
                "export_pass": True,
                "reference_scope_pass": True,
                "internal_identifier_leak_free": True,
                "sensitive_information_leak_free": True,
            }
            for content_format in RECOVERY_FORMATS
        ],
        "representative_journeys": {
            "ordinary_creation_without_retrieval": {"result_class": "SUCCESS"},
            "explicit_missing_object": {
                "result_class": "MATERIAL_GAP",
                "action_card": True,
                "model_call_increment": 0,
            },
            "authorization_block": {
                "result_class": "AUTHORIZATION_OR_SCOPE_BLOCK",
                "action_card": False,
                "model_call_increment": 0,
            },
            "two_browser_sessions": {
                "chat_isolated": True,
                "candidates_isolated": True,
                "selection_isolated": True,
                "revision_isolated": True,
                "review_isolated": True,
                "export_isolated": True,
                "reference_scope_isolated": True,
                "same_session_continuity_pass": True,
                "revoked_session_rejected": True,
            },
        },
        "staged_response_recovery_new_model_calls": 0,
        "package10_replay_new_model_calls": 0,
        "core_numbers": {"300": 300, "120": 120, "86": 86, "changed": False},
        "readiness": valid_readiness,
    }
    changed_remote = copy.deepcopy(synthetic_remote)
    changed_remote["model_call_audit"]["new_content_model_call_count"] = 3
    expect_failure(
        lambda: validate_remote_probe(changed_remote),
        "E_RECOVERY_REMOTE_CALLS",
    )

    changed_remote = copy.deepcopy(synthetic_remote)
    changed_remote["format_probes"][0]["candidate_count"] = 1
    expect_failure(
        lambda: validate_remote_probe(changed_remote),
        "E_RECOVERY_REMOTE_CANDIDATE_WARNING:短视频",
    )

    changed_remote = copy.deepcopy(synthetic_remote)
    changed_remote["representative_journeys"]["two_browser_sessions"][
        "candidates_isolated"
    ] = False
    expect_failure(
        lambda: validate_remote_probe(changed_remote),
        "E_RECOVERY_REMOTE_BROWSER:candidates_isolated",
    )

    synthetic_degraded = copy.deepcopy(synthetic_remote)
    synthetic_degraded["state"] = RECOVERY_DEGRADED_STATE
    synthetic_degraded["offline_material_enabled"] = False
    synthetic_degraded["model_call_audit"].update(
        {
            "new_content_model_call_count": 2,
            "new_model_call_upper_bound": 2,
            "final_invocation_count": 205,
            "final_cumulative_model_call_upper_bound": 209,
        }
    )
    synthetic_degraded["format_probes"][4] = {
        "content_format": "门店线下物料",
        "probe_state": "DISABLED",
        "candidate_count": 0,
        "entry_enabled": False,
        "attempt_count": 2,
        "blocking_item": "REMOTE_OFFLINE_DELIVERABLE_NOT_FINALIZED",
    }
    validate_remote_probe(synthetic_degraded)

    changed_degraded = copy.deepcopy(synthetic_degraded)
    changed_degraded["offline_material_enabled"] = True
    expect_failure(
        lambda: validate_remote_probe(changed_degraded),
        "E_RECOVERY_REMOTE_OFFLINE_STATE",
    )

    synthetic_reviews = [
        {
            "candidate_commit": "1" * 40,
            "candidate_tree": "2" * 40,
            "reviewer_identity": "reviewer-a",
            "reviewer_session_id": "session-a",
            "reviewer_run_id": "run-a",
            "signature_sha256": "a" * 64,
        },
        {
            "candidate_commit": "1" * 40,
            "candidate_tree": "2" * 40,
            "reviewer_identity": "reviewer-a",
            "reviewer_session_id": "session-b",
            "reviewer_run_id": "run-b",
            "signature_sha256": "b" * 64,
        },
    ]
    expect_failure(
        lambda: validate_review_pair_bindings(
            synthetic_reviews,
            candidate_commit="1" * 40,
            candidate_tree_digest="2" * 40,
        ),
        "E_RECOVERY_REVIEW_COLLISION:reviewer_identity",
    )

    return {
        "task_id": RECOVERY_TASK_ID,
        "selftest": "PASS",
        "negative_cases": "PASS",
        "optimized_mode_fail_closed": True,
    }


def account_persona_task_active() -> bool:
    status_path = REPOSITORY_ROOT / "project-infra/current_product_status.v1.yaml"
    if not status_path.is_file():
        return False
    document = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        return False
    status = document.get("current_product_status")
    if not isinstance(status, dict):
        return False
    semantics = status.get("active_product_semantics")
    return bool(
        isinstance(semantics, dict)
        and semantics.get("task_id") == ACCOUNT_PERSONA_TASK_ID
    )


def validate_account_persona_file_set(
    root: Path, *, implementation_only: bool
) -> None:
    actual = package_file_set(root)
    require(not list(root.rglob("*.pyc")), "E_ACCOUNT_PERSONA_BYTECODE_PRESENT")
    require(not list(root.rglob("__pycache__")), "E_ACCOUNT_PERSONA_PYCACHE_PRESENT")
    if implementation_only:
        required = RECOVERY_EXPECTED_PACKAGE_FILES | set(
            ACCOUNT_PERSONA_SCREENSHOT_PATHS
        )
        require(
            required <= actual,
            "E_ACCOUNT_PERSONA_IMPLEMENTATION_FILE_MISSING",
        )
        require(
            actual <= ACCOUNT_PERSONA_EXPECTED_PACKAGE_FILES,
            "E_ACCOUNT_PERSONA_FILE_SET_EXTRA:"
            f"{sorted(map(str, actual - ACCOUNT_PERSONA_EXPECTED_PACKAGE_FILES))}",
        )
        return
    require(
        actual == ACCOUNT_PERSONA_EXPECTED_PACKAGE_FILES,
        "E_ACCOUNT_PERSONA_FILE_SET:"
        f"{sorted(map(str, actual ^ ACCOUNT_PERSONA_EXPECTED_PACKAGE_FILES))}",
    )


def validate_account_persona_source_contract(root: Path) -> None:
    identity_path = (
        REPOSITORY_ROOT
        / "11_product_foundation/public_foundation_001/identity/"
        "simulation_tenant.v1.yaml"
    )
    identity = load_yaml_root(identity_path, "simulation_tenant")
    principals = identity.get("login_principals")
    accounts = identity.get("content_accounts")
    families = identity.get("account_families")
    require(
        isinstance(principals, list) and len(principals) == 12,
        "E_ACCOUNT_PERSONA_PRINCIPAL_COUNT",
    )
    require(
        isinstance(accounts, list) and len(accounts) == 11,
        "E_ACCOUNT_PERSONA_ACCOUNT_COUNT",
    )
    require(
        isinstance(families, list)
        and {
            str(row.get("account_family"))
            for row in families
            if isinstance(row, dict)
        }
        == ACCOUNT_PERSONA_FAMILIES,
        "E_ACCOUNT_PERSONA_FAMILY_SET",
    )
    portal = (root / "portal.html").read_text(encoding="utf-8") + (
        root / "portal.js"
    ).read_text(encoding="utf-8")
    for prohibited in ("审核", "送审", "批准"):
        require(
            prohibited not in portal,
            f"E_ACCOUNT_PERSONA_PORTAL_APPROVAL:{prohibited}",
        )
    contracts = (root / "contracts.py").read_text(encoding="utf-8")
    bridge = (root / "bridge_app.py").read_text(encoding="utf-8")
    dify_app = (root / "dify_app.v1.yaml").read_text(encoding="utf-8")
    for source_name, source in (
        ("contracts", contracts),
        ("bridge", bridge),
        ("dify", dify_app),
    ):
        require(
            '"审核"' not in source and '"送审"' not in source,
            f"E_ACCOUNT_PERSONA_ACTIVE_APPROVAL_OPERATION:{source_name}",
        )
    tests = (root / "test_dify_end_to_end.py").read_text(encoding="utf-8")
    required_tests = (
        "test_seed_has_seven_account_families_and_twelve_isolated_principals",
        "test_six_creator_families_have_distinct_directions_and_open_topics",
        "test_admin_matrix_creates_uses_and_disables_four_extensible_families",
        "test_public_capability_mapping_exposes_ten_topics_and_seven_formats",
        "test_all_seven_formats_render_select_revise_export_and_reference",
        "test_generation_select_revision_export_and_feedback_need_no_approval_fields",
        "test_series_returns_three_episode_outline_and_creates_a_continuation",
        "test_internal_identifiers_sensitive_data_and_secrets_are_blocked",
        "test_same_account_candidates_and_actions_do_not_cross_browser_sessions",
        "test_portal_unauthenticated_and_cross_account_requests_are_isolated",
    )
    for test_name in required_tests:
        require(test_name in tests, f"E_ACCOUNT_PERSONA_TEST:{test_name}")
    status = load_yaml_root(
        REPOSITORY_ROOT / "project-infra/current_product_status.v1.yaml",
        "current_product_status",
    )
    semantics = cast(Mapping[str, Any], status.get("active_product_semantics", {}))
    require(
        semantics.get("account_family_count") == 7
        and semantics.get("representative_login_principal_count") == 12
        and semantics.get("enterprise_content_approval_enabled") is False
        and semantics.get("cross_level_content_confirmation_required") is False
        and semantics.get("account_user_self_check_before_use") is True
        and semantics.get("self_check_is_persisted_as_approval") is False
        and semantics.get("export_requires_approval_event") is False
        and semantics.get("automatic_external_publish") is False
        and semantics.get("data_access_authorization_enforced") is True,
        "E_ACCOUNT_PERSONA_CURRENT_SEMANTICS",
    )


def validate_account_persona_screenshots(root: Path) -> None:
    for path in ACCOUNT_PERSONA_SCREENSHOT_PATHS:
        payload = (root / path).read_bytes()
        require(
            payload.startswith(b"\x89PNG\r\n\x1a\n") and len(payload) >= 10_000,
            f"E_ACCOUNT_PERSONA_SCREENSHOT:{path}",
        )


def run_account_persona_unit_tests(root: Path) -> int:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, "-m", "unittest", "test_dify_end_to_end.py"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
        env=environment,
    )
    require(
        process.returncode == 0,
        f"E_ACCOUNT_PERSONA_UNIT_TESTS:{process.stdout[-500:]}:{process.stderr[-500:]}",
    )
    combined = process.stdout + process.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    require(
        match is not None and "OK" in combined,
        "E_ACCOUNT_PERSONA_UNIT_TEST_SUMMARY",
    )
    node = subprocess.run(
        ["node", "--check", "portal.js"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    require(node.returncode == 0, f"E_ACCOUNT_PERSONA_PORTAL_JS:{node.stderr}")
    return int(match.group(1))


def validate_account_persona_implementation(
    root: Path, *, implementation_only: bool
) -> JsonObject:
    validate_account_persona_file_set(root, implementation_only=implementation_only)
    validate_recovery_historical_bytes(root)
    validate_account_persona_source_contract(root)
    validate_account_persona_screenshots(root)
    unit_test_count = run_account_persona_unit_tests(root)
    return {
        "task_id": ACCOUNT_PERSONA_TASK_ID,
        "status": "PASS",
        "account_family_count": 7,
        "representative_login_principal_count": 12,
        "content_account_count": 11,
        "content_product_count": 20,
        "format_count": 7,
        "screenshot_count": len(ACCOUNT_PERSONA_SCREENSHOT_PATHS),
        "unit_test_count": unit_test_count,
        "model_call_count": 0,
    }


def validate_account_persona_reviews(
    reviews: object, *, candidate_commit: str, candidate_tree: str
) -> None:
    require(
        isinstance(reviews, list) and len(reviews) == 2,
        "E_ACCOUNT_PERSONA_REVIEW_COUNT",
    )
    typed_reviews = [
        cast(Mapping[str, Any], review)
        for review in reviews
        if isinstance(review, dict)
    ]
    require(len(typed_reviews) == 2, "E_ACCOUNT_PERSONA_REVIEW_OBJECTS")
    require(
        {str(review.get("review_type")) for review in typed_reviews}
        == ACCOUNT_PERSONA_REVIEW_TYPES,
        "E_ACCOUNT_PERSONA_REVIEW_TYPES",
    )
    for review in typed_reviews:
        require(
            review.get("candidate_commit") == candidate_commit
            and review.get("candidate_tree") == candidate_tree
            and review.get("verdict") == "PASS"
            and isinstance(review.get("score"), int)
            and int(review["score"]) >= 90
            and review.get("hard_blockers") == []
            and isinstance(review.get("acceptance_ids"), list)
            and bool(review["acceptance_ids"]),
            "E_ACCOUNT_PERSONA_REVIEW_RESULT",
        )
        for key in (
            "review_id",
            "reviewer_identity",
            "reviewer_session_id",
            "reviewer_run_id",
        ):
            require(
                isinstance(review.get(key), str) and bool(review[key]),
                f"E_ACCOUNT_PERSONA_REVIEW_BINDING:{key}",
            )
    for key in (
        "reviewer_identity",
        "reviewer_session_id",
        "reviewer_run_id",
    ):
        require(
            len({str(review.get(key)) for review in typed_reviews}) == 2,
            f"E_ACCOUNT_PERSONA_REVIEW_INDEPENDENCE:{key}",
        )


def validate_account_persona_all(root: Path = PACKAGE_ROOT) -> JsonObject:
    implementation = validate_account_persona_implementation(
        root, implementation_only=False
    )
    result = load_json(root / ACCOUNT_PERSONA_RESULT_PATH)
    delivery = load_yaml_root(
        root / ACCOUNT_PERSONA_DELIVERY_PATH,
        "execution_review_request",
    )
    require(
        result.get("schema")
        == "diyu.package7.account_persona_ui_no_approval.result.v1"
        and result.get("task_id") == ACCOUNT_PERSONA_TASK_ID
        and result.get("baseline_commit") == ACCOUNT_PERSONA_BASELINE_COMMIT,
        "E_ACCOUNT_PERSONA_RESULT_IDENTITY",
    )
    candidate_commit = str(result.get("candidate_commit", ""))
    candidate_tree = str(result.get("candidate_tree", ""))
    require(
        bool(re.fullmatch(r"[0-9a-f]{40}", candidate_commit))
        and git_output("rev-parse", f"{candidate_commit}^{{tree}}") == candidate_tree
        and subprocess.run(
            ["git", "merge-base", "--is-ancestor", candidate_commit, "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=False,
        ).returncode
        == 0,
        "E_ACCOUNT_PERSONA_CANDIDATE_BINDING",
    )
    acceptance = result.get("acceptance")
    expected_acceptance = {f"A{number:02d}" for number in range(1, 16)}
    require(
        isinstance(acceptance, dict)
        and set(acceptance) == expected_acceptance
        and all(acceptance.get(key) is True for key in expected_acceptance),
        "E_ACCOUNT_PERSONA_ACCEPTANCE",
    )
    validate_account_persona_reviews(
        result.get("independent_reviews"),
        candidate_commit=candidate_commit,
        candidate_tree=candidate_tree,
    )
    screenshots = result.get("screenshots")
    require(
        isinstance(screenshots, list)
        and {
            str(row.get("path"))
            for row in screenshots
            if isinstance(row, dict)
        }
        == {
            (PACKAGE_RELATIVE_ROOT / path).as_posix()
            for path in ACCOUNT_PERSONA_SCREENSHOT_PATHS
        },
        "E_ACCOUNT_PERSONA_RESULT_SCREENSHOTS",
    )
    for row in cast(list[Any], screenshots):
        require(isinstance(row, dict), "E_ACCOUNT_PERSONA_RESULT_SCREENSHOT_OBJECT")
        path = Path(str(row["path"]))
        require(
            row.get("sha256") == sha256_file(REPOSITORY_ROOT / path),
            f"E_ACCOUNT_PERSONA_RESULT_SCREENSHOT_DIGEST:{path}",
        )
    controls = cast(Mapping[str, Any], result.get("controls", {}))
    require(
        controls.get("automatic_publish") is False
        and controls.get("public_self_registration") is False
        and controls.get("real_customer_data_imported") is False
        and controls.get("enterprise_content_approval") is False
        and controls.get("user_self_check_not_persisted") is True
        and controls.get("data_access_authorization_enforced") is True,
        "E_ACCOUNT_PERSONA_CONTROLS",
    )
    require(
        result.get("model_calls") == 0
        and result.get("paid_model_calls") == 0
        and result.get("deployment_performed") is False
        and result.get("ecs_operation_performed") is False
        and result.get("secrets_read_or_disclosed") is False
        and result.get("core_numbers")
        == {"300": 300, "120": 120, "86": 86, "changed": False},
        "E_ACCOUNT_PERSONA_BOUNDARIES",
    )
    require(
        delivery.get("task_id") == ACCOUNT_PERSONA_TASK_ID
        and delivery.get("candidate_commit") == candidate_commit
        and delivery.get("candidate_tree") == candidate_tree
        and delivery.get("required_founder_approval")
        == "APPROVE_UI_ACCOUNT_PERSONA_NO_APPROVAL_MERGE"
        and delivery.get("merge_authorized") is False
        and delivery.get("deployment_authorized") is False
        and delivery.get("draft_pull_request_url")
        == result.get("draft_pull_request_url"),
        "E_ACCOUNT_PERSONA_DELIVERY",
    )
    return {
        **implementation,
        "draft_pull_request_url": result.get("draft_pull_request_url"),
        "review_count": 2,
        "acceptance_pass": True,
        "core_numbers_changed": False,
    }


def run_account_persona_selftest(root: Path = PACKAGE_ROOT) -> JsonObject:
    result = load_json(root / ACCOUNT_PERSONA_RESULT_PATH)
    changed = copy.deepcopy(result)
    changed["acceptance"]["A11"] = False
    expect_failure(
        lambda: require(
            all(changed["acceptance"].values()),
            "E_ACCOUNT_PERSONA_SELFTEST_ACCEPTANCE",
        ),
        "E_ACCOUNT_PERSONA_SELFTEST_ACCEPTANCE",
    )
    reviews = copy.deepcopy(result["independent_reviews"])
    reviews[0]["score"] = 89
    expect_failure(
        lambda: validate_account_persona_reviews(
            reviews,
            candidate_commit=str(result["candidate_commit"]),
            candidate_tree=str(result["candidate_tree"]),
        ),
        "E_ACCOUNT_PERSONA_REVIEW_RESULT",
    )
    return {
        "task_id": ACCOUNT_PERSONA_TASK_ID,
        "selftest": "PASS",
        "negative_cases": 2,
        "optimized_mode_fail_closed": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--implementation", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.selftest and args.implementation:
            raise CheckFailure("E_ARGUMENT_MODE_CONFLICT")
        current_task_active = account_persona_task_active()
        recovery_active = (PACKAGE_ROOT / RECOVERY_REPLAY_PATH).is_file()
        if current_task_active and args.selftest:
            result = run_account_persona_selftest()
        elif current_task_active and args.implementation:
            result = validate_account_persona_implementation(
                PACKAGE_ROOT,
                implementation_only=True,
            )
        elif current_task_active:
            result = validate_account_persona_all()
        elif recovery_active and args.selftest:
            result = run_recovery_selftest()
        elif recovery_active and args.implementation:
            result = validate_recovery_implementation(
                PACKAGE_ROOT,
                implementation_only=True,
            )
        elif recovery_active:
            result = validate_recovery_all()
        else:
            result = run_selftest() if args.selftest else validate_all()
    except (CheckFailure, KeyError, TypeError, ValueError, OSError) as exc:
        print(
            json.dumps(
                {"task_id": TASK_ID, "status": "FAIL", "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
