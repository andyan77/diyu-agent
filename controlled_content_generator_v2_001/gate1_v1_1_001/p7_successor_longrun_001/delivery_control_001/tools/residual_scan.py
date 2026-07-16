#!/usr/bin/env python3
"""全仓旧语义残留扫描（v2.5 §五 出口 + P1 §十-C2：不得只依赖文件名或 23 个已知行号）。

对全部 git tracked 文件扫描旧规则语义模式，并按三类分类：
  - SEALED_HISTORY：封存历史文件（v1 合同、v2.3/v2.4 方案、pkg1 证据等）——允许存在；
  - DOCUMENTATION：活跃文件中对旧语义的**文档性提及**（迁移注记、supersession 登记、
    断言其不存在的测试与 checker、警示性模板）——允许存在；
  - ACTIVE_VIOLATION：活跃层的真实旧语义（代码符号、合同键、状态值）——零容忍。

Python 活跃代码先剥离注释与 docstring 再匹配（文档性提及不算残留）。
退出码：存在 ACTIVE_VIOLATION = 1。
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tokenize
from pathlib import Path

DC = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = DC.parents[3]

# 旧语义模式（家族 → 正则）；\b 界定避免 STOP_EXTERNAL_LLM_DAILY_BUDGET 误伤
PATTERNS = {
    "budget_gate_symbol": re.compile(r"\bbudget_gate\b"),
    "ceiling_keys_symbol": re.compile(r"\bREQUIRED_CEILING_KEYS\b"),
    "hard_ceilings_key": re.compile(r"\bhard_ceilings\b"),
    "founder_budget_entry_key": re.compile(r"\bFOUNDER_APPROVED_BUDGET_CEILINGS\b"),
    "projected_cost_exit_key": re.compile(
        r"\bPROJECTED_300_COST_WITHIN_ALL_APPROVED_CEILINGS\b"),
    "cost_reforecast_entry_key": re.compile(r"\bCOST_REFORECAST_WITHIN_BUDGET\b"),
    "stop_budget_kill": re.compile(r"\bSTOP_BUDGET\b"),
    "stop_budget_exceeded": re.compile(r"\bSTOP_BUDGET_ALREADY_EXCEEDED\b"),
    "stop_scale_infeasible": re.compile(r"\bSTOP_SCALE_INFEASIBLE\b"),
    "blocked_budget_unset": re.compile(r"\bBLOCKED_BUDGET_UNSET\b"),
    "old_truth_decision": re.compile(
        r"\bS2_AND_LATER_BLOCKED_PENDING_FOUNDER_BUDGET_APPROVAL\b"),
    "budget_unapproved_reason": re.compile(r"\bBUDGET_UNAPPROVED\b"),
    "b_track_s1_dependency": re.compile(r"\bS1_PASS\b"),
    "s3_auto_kill": re.compile(r"\bSTOP_S3_NO_CAUSAL_LIFT\b"),
    "locked_no_authorization": re.compile(r"\bLOCKED_NO_AUTHORIZATION\b"),
    "approval_status_key": re.compile(r"\bapproval_status\b"),
    # 中文旧语义（语义扫描 wf_f2827efe 抓到 README :33 漏迁移后补入——
    # 确定性扫描不得只覆盖英文符号）
    "budget_approval_zh": re.compile(
        r"预算审批|预算获批|批准预算|总体预算上限|预算批准"),
}

# 封存历史（允许旧语义原样存在——历史文件零改写纪律）
SEALED_PREFIXES = (
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/AB_DUAL_PRODUCT_DELIVERY_PLAN.v2.3.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/AB_DUAL_PRODUCT_DELIVERY_PLAN.v2.4.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/EXECUTION_RETROSPECTIVE.v1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/execution_review_request.v1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/contract/longrun_execution_contract.v1.1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/contract/execution_authorization.v1.1.yaml",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/contract/source_execution_prompt.r1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/freeze/",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/ledger/",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/pkg1_open_regression/",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/stage_and_kill.v1.json",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/cost_budget.v1.json",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/measurement_qualification.v1.json",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/implementation_authorization_record.v1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/implementation_charter.v1.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/review/",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/evidence/",
    # v2 取代后的封存 schema（活跃代码与测试已全部指向 cost.v2.schema.json）
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/schema/cost.v1.schema.json",
)

# 活跃层允许的文档性提及（迁移注记 / 取代登记 / 断言不存在的守卫 / 真源引用）
DOCUMENTATION_PREFIXES = (
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/AB_DUAL_PRODUCT_DELIVERY_PLAN.v2.5.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.2.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/delivery_control_001/",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/checker/",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/contract/longrun_execution_contract.v2.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/contract/execution_authorization.v2.yaml",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/implementation_authorization_record.v2.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/implementation_charter.v2.md",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/tests/",
)

# 活跃 JSON 合同中允许的文档性字段（值内提及旧键 = 迁移注记）
JSON_NOTE_FIELDS = {"migration_note", "entry_migration_note",
                    "exit_migration_note", "kill_migration_note",
                    "fail_closed_migration_note", "reason_code_migration_note",
                    "retention_note", "old_truth_removed", "supersedes",
                    "actual_status_note", "description", "notes", "note",
                    "funding_rules", "required_cost_event_fields_note",
                    "authority", "principle", "track_independence_rule",
                    "anti_patterns_rejected", "forbidden_status_values",
                    "forbidden_regressions", "manifest_consistency",
                    "invalid_if", "external_narrow_gates_retained"}

# 保留面白名单（合法包含 approval 字段语义的窄授权与外部合同）
RETAINED_FACE = (
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/external_llm_budget.v1.json",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/contract/deepseek_rate_card.v1.json",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/spine/external_llm.py",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/tests/test_external_llm.py",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/scripts/run_deepseek_formulaic_judge.py",
    # expected/scale 清单的 approved_by/approved_at 字段（登记性审批元数据，非预算门）
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/spine/cost.py",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/schema/cost.v2.schema.json",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/schema/cost.v1.schema.json",
    "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/schema/external_judge.v1.schema.json",
)


def _classify(path: str) -> str:
    if any(path.startswith(prefix) for prefix in SEALED_PREFIXES):
        return "SEALED_HISTORY"
    if any(path.startswith(prefix) for prefix in DOCUMENTATION_PREFIXES):
        return "DOCUMENTATION"
    return "ACTIVE"


def _strip_python_comments(source: str) -> str:
    """剥离 # 注释与独立字符串表达式（docstring）后返回代码文本。"""
    out: list[str] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        prev_end = (1, 0)
        for tok in tokens:
            if tok.type in (tokenize.COMMENT,):
                continue
            if tok.type == tokenize.STRING:
                # docstring 判定：语句级独立字符串（行首缩进后直接是字符串）
                line_prefix = tok.line[: tok.start[1]]
                if line_prefix.strip() == "":
                    continue
            out.append(tok.string)
    except tokenize.TokenizeError:
        return source
    return " ".join(out)


def _searchable_text(path: Path, rel: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    if rel.endswith(".py") and _classify(rel) == "ACTIVE":
        return _strip_python_comments(text)
    if rel.endswith(".json") and _classify(rel) == "ACTIVE":
        # 活跃 JSON：剔除文档性字段后再匹配
        try:
            value = json.loads(text)
        except ValueError:
            return text

        def scrub(node):
            if isinstance(node, dict):
                return {k: scrub(v) for k, v in node.items()
                        if k not in JSON_NOTE_FIELDS}
            if isinstance(node, list):
                return [scrub(v) for v in node]
            return node
        return json.dumps(scrub(value), ensure_ascii=False)
    return text


def scan(root: Path) -> dict:
    r = subprocess.run(["git", "-C", str(root), "ls-files"],
                       capture_output=True, text=True, check=True)
    tracked = [line for line in r.stdout.splitlines() if line.strip()]
    active_violations: list[dict] = []
    documentation_hits = 0
    sealed_hits = 0
    for rel in tracked:
        if not rel.startswith("controlled_content_generator_v2_001/"):
            continue  # 本任务写面外的历史仓区域不属于本次迁移面
        path = root / rel
        cls = _classify(rel)
        text = _searchable_text(path, rel)
        if not text:
            continue
        for family, pattern in PATTERNS.items():
            hits = pattern.findall(text)
            if not hits:
                continue
            if cls == "SEALED_HISTORY":
                sealed_hits += len(hits)
            elif cls == "DOCUMENTATION":
                documentation_hits += len(hits)
            else:
                if rel in RETAINED_FACE and family in (
                        "approval_status_key",):
                    documentation_hits += len(hits)
                    continue
                active_violations.append(
                    {"path": rel, "family": family, "count": len(hits)})
    return {"schema_version": "p7-residual-scan-report-v1",
            "tracked_files_scanned": len(tracked),
            "pattern_families": sorted(PATTERNS),
            "active_violations": active_violations,
            "documentation_hits": documentation_hits,
            "sealed_history_hits": sealed_hits,
            "verdict": "PASS" if not active_violations else "FAIL"}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out")
    args = ap.parse_args()
    report = scan(Path(args.root))
    blob = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(blob + "\n", encoding="utf-8")
    print(blob)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
