#!/usr/bin/env python3
"""
笛语 Agent 评测集生成工具包 — 统一校验脚本 v3.1

版本语义说明:
  - 脚本版本 (validate.py): v3.1
  - Prompt 文档版本: v3.1 (prompt 头部 > 版本: v3.1)
  - Schema 版本: 3.1 (schema_version 字段值)
  - source_version: v3.0 (数据来源的基线规格版本, 不随 Schema 升级)
  - prompt_version: *-v3.1 (各 prompt 的追踪标识)

修复 Production Audit Round 1 (F1~F9+P0) + Round 2 (F1~F5)。

Usage:
    python3 scripts/eval-gen/validate.py --round seed
    python3 scripts/eval-gen/validate.py --round adversarial
    python3 scripts/eval-gen/validate.py --round diversity
    python3 scripts/eval-gen/validate.py --round review
    python3 scripts/eval-gen/validate.py --round final
    python3 scripts/eval-gen/validate.py --round final --check all
    python3 scripts/eval-gen/validate.py --round final --check schema,count,industry,anchors
    python3 scripts/eval-gen/validate.py --mode gate   # CI gate mode (any error -> exit 1)

Checks (10, all executable):
  schema       — JSON Schema 严格校验 (F3)
  count        — 各评测集样本计数 vs 最低要求
  industry     — 上层评测集行业覆盖 ≥15% 阈值 (F2)
  anchors      — 架构锚点文件:行号验证 (F4)
  difficulty   — 难度分布四区间校验 (F7)
  dedup        — dedup (exact + fuzzy diversity variants) (F9)
  case-types   — case_type 枚举覆盖率 100% (F1)
  naturalness  — 口语真实度 ≥80% realistic (F1)
  agreement    — 交叉审核争议率 ≤15% (F1)
  v11-format   — E-29~E-33 v1.1 模板字段完整性 (F1)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional: try to import jsonschema for strict validation (F3)
# ---------------------------------------------------------------------------
try:
    import jsonschema  # type: ignore

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "eval"
SCHEMA_DIR = PROJECT_ROOT / "scripts" / "eval-gen" / "schemas"
SRC_DIR = PROJECT_ROOT / "src"

EVAL_SETS = [f"E-{i:02d}" for i in range(1, 34)]

ROUND_CONFIG = {
    "seed": {
        "dir": "seeds",
        "suffix": "-seeds.json",
        "schema": "seed-sample.schema.json",
    },
    "adversarial": {
        "dir": "adversarial",
        "suffix": "-adversarial.json",
        "schema": "adversarial-sample.schema.json",
    },
    "diversity": {
        "dir": "diversity",
        "suffix": "-diversity.json",
        "schema": "diversity-variant.schema.json",
    },
    "review": {
        "dir": "review",
        "suffix": None,
        "schema": "review-report.schema.json",
    },
    "final": {
        "dir": "final",
        "suffix": "-final.json",
        "schema": None,  # final uses seed schema
    },
}

# Per-eval-set minimum sample counts (v2.1 spec section 9.9, updated for 5-industry)
MIN_SAMPLES = {
    "E-01": 200,
    "E-02": 150,
    "E-03": 50,
    "E-04": 100,
    "E-05": 60,
    "E-06": 60,
    "E-07": 100,
    "E-08": 80,
    "E-09": 50,
    "E-10": 30,
    "E-11": 100,
    "E-12": 40,
    "E-13": 150,
    "E-14": 100,
    "E-15": 75,
    "E-16": 50,
    "E-17": 30,
    "E-18": 75,
    "E-19": 120,
    "E-20": 100,
    "E-21": 100,
    "E-22": 60,
    "E-23": 75,
    "E-24": 60,
    "E-25": 40,
    "E-26": 40,
    "E-27": 60,
    "E-28": 40,
    "E-29": 80,
    "E-30": 80,
    "E-31": 100,
    "E-32": 60,
    "E-33": 40,
}

# Upper-layer eval sets (industry-specific, need 5-industry coverage ≥15% each)
UPPER_LAYER_SETS = {
    "E-02",
    "E-13",
    "E-14",
    "E-15",
    "E-16",
    "E-17",
    "E-18",
    "E-19",
    "E-20",
    "E-21",
    "E-22",
    "E-23",
    "E-26",
    "E-29",
    "E-31",
}

INDUSTRIES = {"服装", "美妆", "餐饮", "数码", "家居", "通用"}
NON_GENERAL_INDUSTRIES = {"服装", "美妆", "餐饮", "数码", "家居"}
INDUSTRY_MIN_PCT = 15.0  # F2: 每个行业最低占比阈值

# v1.1 新增评测集
V11_EVAL_SETS = {"E-29", "E-30", "E-31", "E-32", "E-33"}

# v1.1 每个评测集的必需专用字段 (F5)
V11_REQUIRED_FIELDS = {
    "E-29": {"knowledge_context", "personal_context"},
    "E-30": {"risk_level", "evidence_available"},
    "E-31": {"tools"},
    "E-32": {"human_gold", "judge_output"},
    "E-33": {"pre_memory_items", "operation", "followup_query"},
}

# Difficulty distribution targets (F7): 全区间校验
DIFFICULTY_TARGETS = {
    "简单": {"target": 20.0, "min": 10.0, "max": 30.0},
    "中等": {"target": 40.0, "min": 30.0, "max": 50.0},
    "困难": {"target": 25.0, "min": 15.0, "max": 35.0},
    "对抗性": {"target": 15.0, "min": 5.0, "max": 25.0},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class ValidationResult:
    def __init__(self):
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def ok(self, msg: str):
        self.passed.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def error(self, msg: str):
        self.errors.append(msg)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def print_report(self) -> int:
        total = len(self.passed) + len(self.warnings) + len(self.errors)
        print(f"\n{'=' * 60}")
        print(
            f"校验结果: {len(self.passed)}/{total} passed, "
            f"{len(self.warnings)} warnings, {len(self.errors)} errors"
        )
        print(f"{'=' * 60}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for e in self.errors:
                print(f"  - {e}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  - {w}")

        if self.passed and not self.errors:
            print(f"\n✅ ALL CHECKS PASSED ({len(self.passed)})")

        print()
        return 0 if self.success else 1


def load_json(path: Path) -> dict | list | None:
    """Load a JSON file, return None on error."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def _get_files(round_name: str) -> list[Path]:
    """Get all JSON data files for a round."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        return []
    return sorted(data_path.glob("*.json"))


def _load_case_type_registry() -> dict[str, list[str]]:
    """Load case_type registry from JSON."""
    registry_path = SCHEMA_DIR / "case-type-registry.json"
    data = load_json(registry_path)
    if data is None:
        return {}
    result = {}
    for eid, info in data.get("registry", {}).items():
        result[eid] = info.get("case_types", [])
    return result


def _load_v11_templates() -> dict:
    """Load v1.1 sample template schema."""
    template_path = SCHEMA_DIR / "v11-sample-templates.schema.json"
    return load_json(template_path) or {}


def _get_samples(data: dict, round_name: str) -> list[dict]:
    """Extract sample list from a data file based on round type."""
    if round_name in ("seed", "adversarial", "final"):
        return data.get("samples", [])
    elif round_name == "diversity":
        # Flatten diversity variants
        samples = []
        for variant_group in data.get("variants", []):
            for v in variant_group.get("variants", []):
                samples.append(v)
            for ci in variant_group.get("cross_industry_variants", []):
                samples.append(ci)
        return samples
    elif round_name == "review":
        return data.get("reviews", [])
    return []


# ---------------------------------------------------------------------------
# Check 1: Schema validation (F3 — strict jsonschema when available)
# ---------------------------------------------------------------------------


def check_schema(result: ValidationResult, round_name: str):
    """Validate JSON files against their schema (strict mode with jsonschema)."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]

    if not data_path.exists():
        result.error(f"目录不存在: {data_path}")
        return

    files = [f for f in sorted(data_path.glob("*.json")) if f.name != ".gitkeep"]
    if not files:
        result.warn(f"目录无 JSON 数据文件: {data_path} (尚未生成数据)")
        return

    # Load the default schema file for this round
    default_schema_name = cfg["schema"]
    if default_schema_name is None and round_name == "final":
        default_schema_name = "seed-sample.schema.json"

    default_schema = None
    if default_schema_name:
        schema_path = SCHEMA_DIR / default_schema_name
        default_schema = load_json(schema_path)
        if default_schema is None:
            result.error(f"无法加载 Schema: {schema_path}")
            return

    # F1-fix: Load review-summary schema separately for review round
    summary_schema = None
    if round_name == "review":
        summary_schema_path = SCHEMA_DIR / "review-summary.schema.json"
        summary_schema = load_json(summary_schema_path)
        if summary_schema is None:
            result.warn("无法加载 review-summary.schema.json, summary 文件将跳过严格校验")

    for fp in files:
        if fp.name == ".gitkeep":
            continue
        data = load_json(fp)
        if data is None:
            result.error(f"JSON 解析失败: {fp.name}")
            continue

        # F1-fix: Route review-summary.json to its own schema
        if round_name == "review" and fp.name == "review-summary.json":
            schema = summary_schema
        else:
            schema = default_schema

        # Strict jsonschema validation if available (F3)
        if schema and HAS_JSONSCHEMA:
            try:
                jsonschema.validate(instance=data, schema=schema)
                result.ok(f"{fp.name}: JSON Schema 严格校验通过")
            except jsonschema.ValidationError as e:
                # Show first path element for context
                path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
                result.error(f"{fp.name}: Schema 校验失败 [{path}] {e.message[:120]}")
        elif schema:
            # Fallback: lightweight field check
            _check_lightweight_schema(result, data, fp, round_name)
        else:
            result.ok(f"{fp.name}: JSON 结构合法 (无指定 Schema)")

        # Skip further sample-level checks for summary files
        if round_name == "review" and fp.name == "review-summary.json":
            continue

        # Always check source_version
        if (
            round_name in ("seed", "adversarial", "diversity")
            and data.get("source_version") != "v3.0"
        ):
            result.warn(f"{fp.name}: source_version={data.get('source_version')}, 预期 v3.0")

        # Check sample-level field validity
        if round_name in ("seed", "adversarial"):
            for s in data.get("samples", []):
                if not s.get("id"):
                    result.error(f"{fp.name}: 样本缺少 id")
                if s.get("industry") and s["industry"] not in INDUSTRIES:
                    result.error(f"{fp.name}/{s.get('id')}: 无效行业 '{s['industry']}'")


def _check_lightweight_schema(result: ValidationResult, data: dict, fp: Path, round_name: str):
    """Lightweight schema check when jsonschema is not installed."""
    if round_name in ("seed", "adversarial", "diversity"):
        for field in ["eval_set_id", "source_version"]:
            if field not in data:
                result.error(f"{fp.name}: 缺少必需字段 '{field}'")
    if round_name in ("seed", "adversarial"):
        samples = data.get("samples", [])
        if not samples:
            result.error(f"{fp.name}: samples 为空")
    result.ok(f"{fp.name}: JSON 基础结构合法 (建议安装 jsonschema 以启用严格校验)")


# ---------------------------------------------------------------------------
# Check 2: Sample count
# ---------------------------------------------------------------------------


def check_count(result: ValidationResult, round_name: str):
    """Check total sample counts meet minimum requirements."""
    if round_name == "final":
        _check_final_count(result)
        return

    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在, 跳过计数: {data_path}")
        return

    total = 0
    for fp in sorted(data_path.glob("*.json")):
        if fp.name == ".gitkeep":
            continue
        # F1-fix: skip summary file from per-file count
        if round_name == "review" and fp.name == "review-summary.json":
            continue
        data = load_json(fp)
        if data is None:
            continue
        if round_name in ("seed", "adversarial"):
            count = len(data.get("samples", []))
        elif round_name == "diversity":
            count = sum(
                len(v.get("variants", [])) + len(v.get("cross_industry_variants", []))
                for v in data.get("variants", [])
            )
        else:
            count = len(data.get("reviews", []))
        total += count
        result.ok(f"{fp.name}: {count} 条")

    result.ok(f"{round_name} 轮合计: {total} 条")


def _check_final_count(result: ValidationResult):
    """Check final round meets per-eval-set minimums."""
    data_path = DATA_DIR / "final"
    if not data_path.exists():
        result.error(f"final 目录不存在: {data_path}")
        return

    total = 0
    for eid in EVAL_SETS:
        fp = data_path / f"{eid}-final.json"
        if not fp.exists():
            result.error(f"缺少: {fp.name}")
            continue
        data = load_json(fp)
        if data is None:
            result.error(f"JSON 解析失败: {fp.name}")
            continue
        count = len(data.get("samples", []))
        minimum = MIN_SAMPLES.get(eid, 30)
        if count < minimum:
            result.error(f"{eid}: {count} 条 < 最低要求 {minimum} 条")
        else:
            result.ok(f"{eid}: {count} 条 >= {minimum} 条")
        total += count

    if total < 2555:
        result.error(f"总样本量 {total} < 最低要求 2,555")
    else:
        result.ok(f"总样本量: {total} >= 2,555")


# ---------------------------------------------------------------------------
# Check 3: Industry distribution (F2 — threshold ≥15%, error not just warn)
# ---------------------------------------------------------------------------


def check_industry(result: ValidationResult, round_name: str):
    """Check industry coverage for upper-layer eval sets with ≥15% threshold."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在, 跳过行业检查: {data_path}")
        return

    for fp in sorted(data_path.glob("*.json")):
        if fp.name == ".gitkeep":
            continue
        # Skip summary files (no eval_set_id)
        if round_name == "review" and fp.name == "review-summary.json":
            continue
        data = load_json(fp)
        if data is None:
            continue

        eid = data.get("eval_set_id", "")
        if eid not in UPPER_LAYER_SETS:
            continue

        # F2-fix: use _get_samples() for round-aware sample extraction
        samples = _get_samples(data, round_name)
        if not samples:
            continue

        # Count per-industry distribution (excluding 通用)
        industry_counts: dict[str, int] = {}
        total_non_general = 0
        for s in samples:
            ind = s.get("industry", "")
            if ind and ind != "通用":
                industry_counts[ind] = industry_counts.get(ind, 0) + 1
                total_non_general += 1

        if total_non_general == 0:
            result.error(f"{fp.name} ({eid}): 上层评测集无行业标注样本")
            continue

        # F2: Check each of 5 industries meets ≥15% threshold
        missing_industries = []
        below_threshold = []
        for ind in NON_GENERAL_INDUSTRIES:
            count = industry_counts.get(ind, 0)
            if count == 0:
                missing_industries.append(ind)
            else:
                pct = count / total_non_general * 100
                if pct < INDUSTRY_MIN_PCT:
                    below_threshold.append(f"{ind}={pct:.1f}%")

        if missing_industries:
            result.error(f"{fp.name} ({eid}): 缺少行业 {missing_industries}")
        elif below_threshold:
            result.error(
                f"{fp.name} ({eid}): 行业占比低于 {INDUSTRY_MIN_PCT}% 阈值: "
                f"{', '.join(below_threshold)}"
            )
        else:
            result.ok(f"{fp.name} ({eid}): 5 行业全覆盖且均 ≥{INDUSTRY_MIN_PCT}%")


# ---------------------------------------------------------------------------
# Check 4: Architecture anchors (F4 — verify file + line number)
# ---------------------------------------------------------------------------


def check_anchors(result: ValidationResult, round_name: str):
    """Check that architecture anchors point to real files and valid line numbers."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在, 跳过锚点检查: {data_path}")
        return

    checked = 0
    file_invalid = 0
    line_invalid = 0
    for fp in sorted(data_path.glob("*.json")):
        if fp.name == ".gitkeep":
            continue
        if round_name == "review" and fp.name == "review-summary.json":
            continue
        data = load_json(fp)
        if data is None:
            continue

        # F2-fix: use _get_samples() for round-aware sample extraction
        for s in _get_samples(data, round_name):
            anchor = s.get("architecture_anchor", "")
            if not anchor:
                continue

            # Parse anchor: src/brain/engine/conversation.py:L42 — description
            # Remove trailing description after " —" or " -"
            file_part = re.split(r"\s+[—\-]", anchor)[0].strip()

            line_num = None
            # Handle :L42 or :42 format
            match = re.match(r"^(.+?):L?(\d+)$", file_part)
            if match:
                file_path_str = match.group(1)
                line_num = int(match.group(2))
            elif ":" in file_part:
                file_path_str = file_part.rsplit(":", 1)[0]
            else:
                file_path_str = file_part

            full_path = PROJECT_ROOT / file_path_str
            checked += 1

            # F4a: Check file exists
            if not full_path.exists():
                file_invalid += 1
                if file_invalid <= 10:
                    result.warn(f"{fp.name}/{s.get('id')}: 锚点文件不存在 {file_path_str}")
                continue

            # F4b: Check line number validity
            if line_num is not None:
                try:
                    with open(full_path, encoding="utf-8") as f:
                        total_lines = sum(1 for _ in f)
                    if line_num > total_lines:
                        line_invalid += 1
                        if line_invalid <= 10:
                            result.warn(
                                f"{fp.name}/{s.get('id')}: 锚点行号 L{line_num} 超出"
                                f"文件总行数 {total_lines} ({file_path_str})"
                            )
                except OSError:
                    pass

    if checked == 0:
        result.warn("未找到架构锚点可校验")
    else:
        msgs = []
        if file_invalid:
            msgs.append(f"{file_invalid} 文件不存在")
        if line_invalid:
            msgs.append(f"{line_invalid} 行号无效")
        if msgs:
            result.warn(f"{checked} 个锚点已检查, 问题: {', '.join(msgs)}")
        else:
            result.ok(f"所有 {checked} 个架构锚点文件及行号均有效")


# ---------------------------------------------------------------------------
# Check 5: Difficulty distribution (F7 — all 4 intervals)
# ---------------------------------------------------------------------------


def check_difficulty(result: ValidationResult, round_name: str):
    """Check difficulty distribution across all 4 intervals with thresholds."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在, 跳过难度检查: {data_path}")
        return

    dist: dict[str, int] = {"简单": 0, "中等": 0, "困难": 0, "对抗性": 0}
    total = 0

    for fp in sorted(data_path.glob("*.json")):
        if fp.name == ".gitkeep":
            continue
        if round_name == "review" and fp.name == "review-summary.json":
            continue
        data = load_json(fp)
        if data is None:
            continue
        # F2-fix: use _get_samples() for round-aware sample extraction
        for s in _get_samples(data, round_name):
            d = s.get("difficulty", "")
            if d in dist:
                dist[d] += 1
                total += 1

    if total == 0:
        result.warn("无样本可检查难度分布")
        return

    # F7: Check all 4 intervals
    violations = []
    for level, count in dist.items():
        pct = count / total * 100
        target = DIFFICULTY_TARGETS[level]
        status = "✓" if target["min"] <= pct <= target["max"] else "✗"
        result.ok(
            f"难度 {level}: {count} ({pct:.1f}%) "
            f"[目标 {target['target']}%, 范围 {target['min']}-{target['max']}%] {status}"
        )
        if pct < target["min"] or pct > target["max"]:
            violations.append(f"{level}={pct:.1f}% 不在 [{target['min']}-{target['max']}%] 范围内")

    if violations:
        result.error(f"难度分布不达标: {'; '.join(violations)}")
    else:
        result.ok("难度分布四区间均达标")


# ---------------------------------------------------------------------------
# Check 6: Dedup (F9 — exact + fuzzy for diversity)
# ---------------------------------------------------------------------------


def check_dedup(result: ValidationResult, round_name: str):
    """Check for duplicate user_messages across files (exact + diversity variants)."""
    messages: dict[str, str] = {}  # normalized message -> first seen file:id
    dups = 0

    for subdir in ["seeds", "adversarial", "diversity", "final"]:
        data_path = DATA_DIR / subdir
        if not data_path.exists():
            continue
        for fp in sorted(data_path.glob("*.json")):
            if fp.name == ".gitkeep":
                continue
            data = load_json(fp)
            if data is None:
                continue

            # Get messages from samples or diversity variants
            if subdir == "diversity":
                for variant_group in data.get("variants", []):
                    for v in variant_group.get("variants", []):
                        msg = v.get("user_message", "").strip()
                        vid = v.get("id", "?")
                        if not msg:
                            continue
                        # F9: Normalize for fuzzy match
                        norm = _normalize_message(msg)
                        if norm in messages:
                            dups += 1
                            if dups <= 10:
                                result.warn(f"重复消息: {fp.name}/{vid} 与 {messages[norm]}")
                        else:
                            messages[norm] = f"{fp.name}/{vid}"
                    for ci in variant_group.get("cross_industry_variants", []):
                        msg = ci.get("user_message", "").strip()
                        cid = ci.get("id", "?")
                        if not msg:
                            continue
                        norm = _normalize_message(msg)
                        if norm in messages:
                            dups += 1
                            if dups <= 10:
                                result.warn(f"重复消息: {fp.name}/{cid} 与 {messages[norm]}")
                        else:
                            messages[norm] = f"{fp.name}/{cid}"
            else:
                for s in data.get("samples", []):
                    msg = s.get("user_message", "").strip()
                    sid = s.get("id", "?")
                    if not msg:
                        continue
                    norm = _normalize_message(msg)
                    if norm in messages:
                        dups += 1
                        if dups <= 10:
                            result.warn(f"重复消息: {fp.name}/{sid} 与 {messages[norm]}")
                    else:
                        messages[norm] = f"{fp.name}/{sid}"

    if dups == 0:
        result.ok(f"无重复消息 (共检查 {len(messages)} 条)")
    else:
        result.warn(f"发现 {dups} 条重复消息")


def _normalize_message(msg: str) -> str:
    """Normalize message for fuzzy dedup (F9).

    Strips punctuation, whitespace, and common filler words to catch
    diversity variants that are semantically identical.
    """
    # Remove CJK punctuation and extra whitespace
    normalized = re.sub(r"[\u3000-\u303f\uff00-\uffef\u2018-\u201f\s]+", "", msg)
    # Lowercase for mixed-language messages
    normalized = normalized.lower()
    return normalized


# ---------------------------------------------------------------------------
# Check 7: case_type coverage (F1 — new check)
# ---------------------------------------------------------------------------


def check_case_types(result: ValidationResult, round_name: str):
    """Check that each eval set covers 100% of its required case_types."""
    registry = _load_case_type_registry()
    if not registry:
        result.error("无法加载 case_type 枚举注册表 (case-type-registry.json)")
        return

    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在, 跳过 case_type 检查: {data_path}")
        return

    for fp in sorted(data_path.glob("*.json")):
        if fp.name == ".gitkeep":
            continue
        # F1-fix: skip summary files (no eval_set_id)
        if round_name == "review" and fp.name == "review-summary.json":
            continue
        data = load_json(fp)
        if data is None:
            continue

        eid = data.get("eval_set_id", "")
        if eid not in registry:
            continue

        expected_types = set(registry[eid])
        found_types = set()
        invalid_types = set()

        # F2-fix: use _get_samples() to handle diversity/review data structures
        for s in _get_samples(data, round_name):
            ct = s.get("case_type", "")
            if ct:
                found_types.add(ct)
                if ct not in expected_types:
                    invalid_types.add(ct)

        if not found_types:
            # diversity/review rounds may not carry case_type — skip silently
            if round_name in ("diversity", "review"):
                continue
            # seed/adversarial/final: case_type is BLOCK-level required
            result.error(f"{fp.name} ({eid}): 无 case_type 标注 (BLOCK)")
            continue

        missing = expected_types - found_types
        if missing:
            result.error(f"{fp.name} ({eid}): 缺少 case_type 覆盖: {missing}")
        else:
            result.ok(f"{fp.name} ({eid}): case_type 100% 覆盖 ({len(expected_types)} 种)")

        if invalid_types:
            result.warn(f"{fp.name} ({eid}): 发现注册表外 case_type: {invalid_types}")


# ---------------------------------------------------------------------------
# Check 8: Naturalness (F1 — new check, requires review round data)
# ---------------------------------------------------------------------------


def _build_org_tier_index() -> dict[str, str]:
    """Build a sample_id → org_tier lookup from seed and adversarial data.

    Used by check_naturalness to filter franchise_store samples (F3-fix).
    """
    index: dict[str, str] = {}
    for subdir in ("seeds", "adversarial"):
        data_path = DATA_DIR / subdir
        if not data_path.exists():
            continue
        for fp in sorted(data_path.glob("*.json")):
            if fp.name == ".gitkeep":
                continue
            data = load_json(fp)
            if data is None:
                continue
            for s in data.get("samples", []):
                sid = s.get("id", "")
                org_tier = s.get("org_tier", "")
                if sid and org_tier:
                    index[sid] = org_tier
    return index


def check_naturalness(result: ValidationResult, round_name: str):
    """Check that ≥80% of franchise_store samples are marked 'realistic'.

    F3-fix: Cross-references org_tier from source samples instead of
    counting all review items indiscriminately.
    """
    # This check reads review reports to validate naturalness ratings
    review_path = DATA_DIR / "review"
    if not review_path.exists():
        result.warn("review 目录不存在, 跳过口语真实度检查")
        return

    # F3-fix: Build org_tier index from source samples
    org_tier_index = _build_org_tier_index()
    has_index = bool(org_tier_index)

    total_franchise = 0
    realistic_count = 0
    total_all = 0
    realistic_all = 0

    for fp in sorted(review_path.glob("*.json")):
        if fp.name == ".gitkeep" or fp.name == "review-summary.json":
            continue
        data = load_json(fp)
        if data is None:
            continue

        for r in data.get("reviews", []):
            naturalness = r.get("naturalness", "")
            if not naturalness:
                continue
            sample_id = r.get("sample_id", "")

            # Track all samples for fallback reporting
            total_all += 1
            if naturalness == "realistic":
                realistic_all += 1

            # F3-fix: Only count franchise_store samples for the ≥80% gate
            if has_index:
                if org_tier_index.get(sample_id) == "franchise_store":
                    total_franchise += 1
                    if naturalness == "realistic":
                        realistic_count += 1
            else:
                # Fallback: no source data available, count all
                total_franchise += 1
                if naturalness == "realistic":
                    realistic_count += 1

    if total_franchise == 0:
        if has_index:
            result.warn("无 franchise_store 样本的口语真实度标注可检查")
        else:
            result.warn("无口语真实度标注可检查")
        return

    pct = realistic_count / total_franchise * 100
    scope_label = "franchise_store" if has_index else "全部"
    if pct >= 80.0:
        result.ok(
            f"口语真实度 ({scope_label}): {realistic_count}/{total_franchise} ({pct:.1f}%) ≥ 80%"
        )
    else:
        result.error(
            f"口语真实度 ({scope_label}): {realistic_count}/{total_franchise} "
            f"({pct:.1f}%) < 80% 阈值"
        )

    # Also report all-samples stat for reference
    if has_index and total_all > 0:
        pct_all = realistic_all / total_all * 100
        result.ok(f"口语真实度 (全部): {realistic_all}/{total_all} ({pct_all:.1f}%) [参考]")


# ---------------------------------------------------------------------------
# Check 9: Agreement (F1 — new check, cross-review consistency)
# ---------------------------------------------------------------------------


def check_agreement(result: ValidationResult, round_name: str):
    """Check that cross-review dispute rate ≤15%."""
    review_path = DATA_DIR / "review"
    if not review_path.exists():
        result.warn("review 目录不存在, 跳过交叉审核一致率检查")
        return

    total_reviewed = 0
    disputed = 0
    errored = 0

    for fp in sorted(review_path.glob("*.json")):
        if fp.name == ".gitkeep" or fp.name == "review-summary.json":
            continue
        data = load_json(fp)
        if data is None:
            continue

        # Use per-file summary if available
        summary = data.get("summary", {})
        if summary:
            total_reviewed += summary.get("total_reviewed", 0)
            disputed += summary.get("disputed_count", 0)
            errored += summary.get("error_count", 0)
        else:
            for r in data.get("reviews", []):
                total_reviewed += 1
                aq = r.get("answer_quality", "")
                if aq == "disputed":
                    disputed += 1
                elif aq == "error":
                    errored += 1

    if total_reviewed == 0:
        result.warn("无交叉审核数据可检查")
        return

    dispute_rate = (disputed + errored) / total_reviewed * 100
    if dispute_rate <= 15.0:
        result.ok(
            f"交叉审核一致率: 争议 {disputed} + 错误 {errored} / {total_reviewed}"
            f" = {dispute_rate:.1f}% ≤ 15%"
        )
    else:
        result.error(
            f"交叉审核争议率 {dispute_rate:.1f}% > 15% 阈值"
            f" (争议 {disputed}, 错误 {errored}, 总计 {total_reviewed})"
        )


# ---------------------------------------------------------------------------
# Check 10: v1.1 format (F1+F5 — new check)
# ---------------------------------------------------------------------------


def check_v11_format(result: ValidationResult, round_name: str):
    """Check E-29~E-33 use v1.1 template format with required fields.

    Only applies to seed/adversarial/final rounds — diversity variants and
    review items have different structures and do NOT carry v1.1 template fields.
    """
    # v1.1 template fields only exist in sample-bearing rounds
    if round_name in ("diversity", "review"):
        result.ok(f"v1.1 格式检查: 不适用于 {round_name} 轮次 (跳过)")
        return

    v11_templates = _load_v11_templates()
    v11_required = v11_templates.get("v11_required_fields", V11_REQUIRED_FIELDS)

    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在, 跳过 v1.1 格式检查: {data_path}")
        return

    checked = 0
    for fp in sorted(data_path.glob("*.json")):
        if fp.name == ".gitkeep":
            continue
        if round_name == "review" and fp.name == "review-summary.json":
            continue
        data = load_json(fp)
        if data is None:
            continue

        eid = data.get("eval_set_id", "")
        if eid not in V11_EVAL_SETS:
            continue

        # F2-fix: use _get_samples() for round-aware sample extraction
        samples = _get_samples(data, round_name)
        if not samples:
            result.error(f"{fp.name} ({eid}): v1.1 评测集样本为空")
            continue

        # Get required fields for this eval set
        required = set()
        if isinstance(v11_required, dict):
            req = v11_required.get(eid, [])
            required = set(req) if isinstance(req, list) else req

        for s in samples:
            checked += 1
            sid = s.get("id", s.get("case_id", "?"))
            missing_fields = []
            for field in required:
                if field not in s:
                    missing_fields.append(field)
            if missing_fields:
                result.error(f"{fp.name}/{sid}: v1.1 缺少必需字段 {missing_fields}")

        # Check expected_answer structure for E-29~E-31
        if eid == "E-29":
            for s in samples:
                ea = s.get("expected_answer", {})
                if isinstance(ea, dict):
                    if "must_supported_claims" not in ea:
                        result.error(
                            f"{fp.name}/{s.get('id')}: E-29 expected_answer "
                            f"缺少 must_supported_claims"
                        )
                else:
                    result.error(f"{fp.name}/{s.get('id')}: E-29 expected_answer 必须是对象")

        if eid == "E-31":
            for s in samples:
                ea = s.get("expected_answer", {})
                if isinstance(ea, dict):
                    if "tool_sequence" not in ea:
                        result.error(
                            f"{fp.name}/{s.get('id')}: E-31 expected_answer 缺少 tool_sequence"
                        )
                else:
                    result.error(f"{fp.name}/{s.get('id')}: E-31 expected_answer 必须是对象")

        if eid == "E-32":
            for s in samples:
                if "human_gold" in s and "judge_output" in s:
                    hg = s["human_gold"]
                    if not isinstance(hg, dict) or "overall" not in hg:
                        result.error(f"{fp.name}/{s.get('id')}: E-32 human_gold 格式不合法")
                    jo = s["judge_output"]
                    if not isinstance(jo, dict) or "overall" not in jo:
                        result.error(f"{fp.name}/{s.get('id')}: E-32 judge_output 格式不合法")

        if eid == "E-33":
            for s in samples:
                ea = s.get("expected_answer", {})
                if isinstance(ea, dict) and (
                    "should_retrieve_ids" not in ea or "pii_exposed" not in ea
                ):
                    result.error(
                        f"{fp.name}/{s.get('id')}: E-33 expected_answer "
                        f"missing should_retrieve_ids or pii_exposed"
                    )

        result.ok(f"{fp.name} ({eid}): v1.1 模板格式检查完成")

    if checked == 0:
        result.warn("未找到 v1.1 评测集样本 (E-29~E-33)")
    else:
        result.ok(f"共检查 {checked} 个 v1.1 样本")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_CHECKS = {
    "schema": check_schema,
    "count": check_count,
    "industry": check_industry,
    "anchors": check_anchors,
    "difficulty": check_difficulty,
    "dedup": check_dedup,
    "case-types": check_case_types,
    "naturalness": check_naturalness,
    "agreement": check_agreement,
    "v11-format": check_v11_format,
}


def main():
    parser = argparse.ArgumentParser(
        description="笛语 Agent 评测集校验脚本 v3.1 (10 项检查 + 门禁硬化)"
    )
    parser.add_argument(
        "--round",
        required=True,
        choices=["seed", "adversarial", "diversity", "review", "final"],
        help="校验哪一轮的产出",
    )
    parser.add_argument(
        "--check",
        default="all",
        help="逗号分隔的检查项: " + ",".join(ALL_CHECKS.keys()) + " 或 all",
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "gate"],
        default="normal",
        help="gate 模式下任何 error 都返回 exit 1 (CI 门禁)",
    )
    args = parser.parse_args()

    result = ValidationResult()

    print("笛语 Agent 评测集校验 v3.1 (Production Audit F1~F9 修复)")
    print(f"校验轮次: {args.round}")
    print(f"校验模式: {args.mode}")
    print(f"项目路径: {PROJECT_ROOT}")
    print(f"数据目录: {DATA_DIR}")
    if not HAS_JSONSCHEMA:
        print("⚠️  jsonschema 未安装, Schema 校验降级为轻量模式")
        print("   安装: pip install jsonschema")

    if args.check == "all":
        checks = list(ALL_CHECKS.keys())
    else:
        checks = [c.strip() for c in args.check.split(",")]

    for check_name in checks:
        if check_name not in ALL_CHECKS:
            result.error(f"未知检查项: {check_name}")
            continue
        print(f"\n--- 检查: {check_name} ---")
        ALL_CHECKS[check_name](result, args.round)

    exit_code = result.print_report()

    # Gate mode: always return non-zero on errors
    if args.mode == "gate" and not result.success:
        print("GATE BLOCKED -- blocking errors found")
        return 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
