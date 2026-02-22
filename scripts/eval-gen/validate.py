#!/usr/bin/env python3
"""
笛语 Agent 评测集生成工具包 — 统一校验脚本 v3.0

Usage:
    python3 scripts/eval-gen/validate.py --round seed
    python3 scripts/eval-gen/validate.py --round adversarial
    python3 scripts/eval-gen/validate.py --round diversity
    python3 scripts/eval-gen/validate.py --round review
    python3 scripts/eval-gen/validate.py --round final
    python3 scripts/eval-gen/validate.py --round final --check all
    python3 scripts/eval-gen/validate.py --round final --check schema,count,industry,anchors
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
        "suffix": None,  # review files have varied names
        "schema": "review-report.schema.json",
    },
    "final": {
        "dir": "final",
        "suffix": "-final.json",
        "schema": None,  # final uses seed schema
    },
}

# Per-eval-set minimum sample counts (from v2.1 spec section 9.9)
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

# Upper-layer eval sets (industry-specific, need 5-industry coverage)
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

    def print_report(self):
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


def load_json(path: Path) -> dict | None:
    """Load a JSON file, return None on error."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# Check: Schema validation (lightweight, no jsonschema dependency)
# ---------------------------------------------------------------------------


def check_schema(result: ValidationResult, round_name: str):
    """Validate basic structure of output files."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]

    if not data_path.exists():
        result.error(f"目录不存在: {data_path}")
        return

    files = sorted(data_path.glob("*.json"))
    if not files:
        result.error(f"目录为空: {data_path}")
        return

    for fp in files:
        data = load_json(fp)
        if data is None:
            result.error(f"JSON 解析失败: {fp.name}")
            continue

        # Basic required fields check
        if round_name in ("seed", "adversarial", "diversity"):
            for field in ["eval_set_id", "source_version"]:
                if field not in data:
                    result.error(f"{fp.name}: 缺少必需字段 '{field}'")

            if data.get("source_version") != "v3.0":
                result.warn(f"{fp.name}: source_version={data.get('source_version')}, 预期 v3.0")

        if round_name in ("seed", "adversarial"):
            samples = data.get("samples", [])
            if not samples:
                result.error(f"{fp.name}: samples 为空")
            else:
                for s in samples:
                    if not s.get("id"):
                        result.error(f"{fp.name}: 样本缺少 id")
                    if s.get("industry") and s["industry"] not in INDUSTRIES:
                        result.error(f"{fp.name}/{s.get('id')}: 无效行业 '{s['industry']}'")

        result.ok(f"{fp.name}: JSON 结构合法")


# ---------------------------------------------------------------------------
# Check: Sample count
# ---------------------------------------------------------------------------


def check_count(result: ValidationResult, round_name: str):
    """Check total sample counts meet minimum requirements."""
    if round_name == "final":
        _check_final_count(result)
        return

    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在，跳过计数: {data_path}")
        return

    total = 0
    for fp in sorted(data_path.glob("*.json")):
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
# Check: Industry distribution
# ---------------------------------------------------------------------------


def check_industry(result: ValidationResult, round_name: str):
    """Check industry coverage for upper-layer eval sets."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在，跳过行业检查: {data_path}")
        return

    for fp in sorted(data_path.glob("*.json")):
        data = load_json(fp)
        if data is None:
            continue

        eid = data.get("eval_set_id", "")
        if eid not in UPPER_LAYER_SETS:
            continue

        samples = data.get("samples", [])
        if not samples:
            continue

        industries_found = set()
        for s in samples:
            ind = s.get("industry", "")
            if ind and ind != "通用":
                industries_found.add(ind)

        expected = {"服装", "美妆", "餐饮", "数码", "家居"}
        missing = expected - industries_found
        if missing:
            result.warn(f"{fp.name} ({eid}): 缺少行业覆盖 {missing}")
        else:
            result.ok(f"{fp.name} ({eid}): 5 行业全覆盖")


# ---------------------------------------------------------------------------
# Check: Architecture anchors validity
# ---------------------------------------------------------------------------


def check_anchors(result: ValidationResult, round_name: str):
    """Check that architecture anchors point to real files."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在，跳过锚点检查: {data_path}")
        return

    checked = 0
    invalid = 0
    for fp in sorted(data_path.glob("*.json")):
        data = load_json(fp)
        if data is None:
            continue

        for s in data.get("samples", []):
            anchor = s.get("architecture_anchor", "")
            if not anchor or ":" not in anchor:
                continue

            # Extract file path (before " —" comment or ":L" line number)
            file_part = anchor.split(" —")[0].split(" -")[0].strip()
            # Handle src/foo.py:L42 format
            if ":L" in file_part:
                file_part = file_part.split(":L")[0]
            elif ":" in file_part:
                file_part = file_part.rsplit(":", 1)[0]

            full_path = PROJECT_ROOT / file_part
            checked += 1
            if not full_path.exists():
                invalid += 1
                if invalid <= 10:  # Only show first 10
                    result.warn(f"{fp.name}/{s.get('id')}: 锚点文件不存在 {file_part}")

    if checked == 0:
        result.warn("未找到架构锚点可校验")
    elif invalid == 0:
        result.ok(f"所有 {checked} 个架构锚点文件均存在")
    else:
        result.warn(f"{invalid}/{checked} 个架构锚点指向不存在的文件")


# ---------------------------------------------------------------------------
# Check: Difficulty distribution
# ---------------------------------------------------------------------------


def check_difficulty(result: ValidationResult, round_name: str):
    """Check difficulty distribution across all samples."""
    cfg = ROUND_CONFIG[round_name]
    data_path = DATA_DIR / cfg["dir"]
    if not data_path.exists():
        result.warn(f"目录不存在，跳过难度检查: {data_path}")
        return

    dist = {"简单": 0, "中等": 0, "困难": 0, "对抗性": 0}
    total = 0

    for fp in sorted(data_path.glob("*.json")):
        data = load_json(fp)
        if data is None:
            continue
        for s in data.get("samples", []):
            d = s.get("difficulty", "")
            if d in dist:
                dist[d] += 1
                total += 1

    if total == 0:
        result.warn("无样本可检查难度分布")
        return

    for level, count in dist.items():
        pct = count / total * 100
        result.ok(f"难度 {level}: {count} ({pct:.1f}%)")

    # Target: 简单 20% / 中等 40% / 困难 25% / 对抗性 15%
    easy_pct = dist["简单"] / total * 100
    if easy_pct > 30:
        result.warn(f"简单样本占比 {easy_pct:.1f}% > 目标 20%")


# ---------------------------------------------------------------------------
# Check: Dedup across rounds
# ---------------------------------------------------------------------------


def check_dedup(result: ValidationResult, round_name: str):
    """Check for duplicate user_messages across files."""
    messages: dict[str, str] = {}  # message -> first seen file:id
    dups = 0

    for subdir in ["seeds", "adversarial", "diversity", "final"]:
        data_path = DATA_DIR / subdir
        if not data_path.exists():
            continue
        for fp in sorted(data_path.glob("*.json")):
            data = load_json(fp)
            if data is None:
                continue
            for s in data.get("samples", []):
                msg = s.get("user_message", "").strip()
                sid = s.get("id", "?")
                if not msg:
                    continue
                if msg in messages:
                    dups += 1
                    if dups <= 10:
                        result.warn(f"重复消息: {fp.name}/{sid} 与 {messages[msg]}")
                else:
                    messages[msg] = f"{fp.name}/{sid}"

    if dups == 0:
        result.ok(f"无重复消息（共检查 {len(messages)} 条）")
    else:
        result.warn(f"发现 {dups} 条重复消息")


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
}


def main():
    parser = argparse.ArgumentParser(description="笛语 Agent 评测集校验脚本 v3.0")
    parser.add_argument(
        "--round",
        required=True,
        choices=["seed", "adversarial", "diversity", "review", "final"],
        help="校验哪一轮的产出",
    )
    parser.add_argument(
        "--check",
        default="all",
        help="逗号分隔的检查项: schema,count,industry,anchors,difficulty,dedup 或 all",
    )
    args = parser.parse_args()

    result = ValidationResult()

    print("笛语 Agent 评测集校验 v3.0")
    print(f"校验轮次: {args.round}")
    print(f"项目路径: {PROJECT_ROOT}")
    print(f"数据目录: {DATA_DIR}")

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

    return result.print_report()


if __name__ == "__main__":
    sys.exit(main())
