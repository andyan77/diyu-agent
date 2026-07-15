#!/usr/bin/env python3
"""G3 · 路线60异常处置驱动器（编译→求值→比对→结果）。

复用冻结基座（零修改）：
- 编译器/引擎装载：p3_route_input_compiler_recovery_001/route_contract.py
  （compile_route_input / evaluate_compiled_route，fail-closed，禁答案键）
- 路由引擎：p2_generator_core.evaluate_route（gate1-v1.1-route-successor-v0.1）
- 冻结金标：p1b .../route_60_gold_answers.v0.1.jsonl（sha f87d984d…）
- 60条 canonical 输入：p5_p6 .../route/route_inputs.v1.0.jsonl（冻结证据）

高风险漏放与"全阻止造绿"防线继承机器化实现：
audience 字段全 False 硬断言 + 金标动作分布内建非阻止动作 +
动作/原因三枚举覆盖闸。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import g3_author_contract as contract  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GATE1 = ROOT / "controlled_content_generator_v2_001/gate1_v1_1_001"
ROUTE_CONTRACT_PY = GATE1 / "p3_route_input_compiler_recovery_001/route_contract.py"
GOLD_FILE = GATE1 / ("p1b_signed_review_closeout_and_baseline_freeze_001"
                     "/route/route_60_gold_answers.v0.1.jsonl")
ROUTE_INPUTS_FILE = GATE1 / ("p5_p6_300_baseline_scale_and_freeze_001"
                             "/route/route_inputs.v1.0.jsonl")
GOLD_SHA256 = "f87d984d1780423e7ace0d78c54ba40e97ab5b48c39950f691c7ffca6652e054"

EXPECTED_ACTIONS = {"BLOCK", "REQUEST_INPUT", "DEGRADE"}
EXPECTED_REASONS = {"输入冲突", "事实缺失", "授权缺失"}


def _load_route_contract() -> Any:
    spec = importlib.util.spec_from_file_location("route_contract", ROUTE_CONTRACT_PY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def run_route_60(out_dir: Path) -> dict[str, Any]:
    """跑完整 60 案：返回 result dict 并物化 4 个确定性文件。"""
    import hashlib

    gold_bytes = GOLD_FILE.read_bytes()
    contract.require(hashlib.sha256(gold_bytes).hexdigest() == GOLD_SHA256,
                     "E_G3_ROUTE_GOLD_DRIFT")
    gold_rows = {str(r["case_id"]): r for r in _read_jsonl(GOLD_FILE)}
    inputs = _read_jsonl(ROUTE_INPUTS_FILE)
    contract.require(len(inputs) == 60, "E_G3_ROUTE_INPUT_COUNT", str(len(inputs)))
    rc = _load_route_contract()

    compiled_rows: list[dict[str, Any]] = []
    actual_rows: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    action_match = reason_match = audience_created = 0
    for record in sorted(inputs, key=lambda r: str(r["case_id"])):
        case_id = str(record["case_id"])
        compiled = rc.compile_route_input(record["route_input_contract"]
                                          if "route_input_contract" in record
                                          else record)
        compiled_rows.append(compiled)
        actual = rc.evaluate_compiled_route(compiled)
        actual_rows.append(actual)
        gold = gold_rows[case_id]
        actual_action = str(actual["actual_primary_action"])
        actual_reason = str(actual["actual_primary_reason_category"])
        gold_action = str(gold["gold_primary_action"])
        gold_reason = str(gold["gold_reason_code"])
        audience = any(
            bool(actual.get(key, False))
            for key in (
                "audience_title_created", "audience_body_created",
                "spoken_script_created", "runtime_plan_created",
                "runtime_consumable",
            )
        )
        row = {
            "case_id": case_id,
            "profile_id": str(gold["profile_id"]),
            "actual_primary_action": actual_action,
            "actual_primary_reason_category": actual_reason,
            "gold_primary_action": gold_action,
            "gold_primary_reason_category": gold_reason,
            "audience_content_created": audience,
            "primary_action_matches_gold": actual_action == gold_action,
            "primary_reason_matches_gold": actual_reason == gold_reason,
        }
        comparisons.append(row)
        action_match += row["primary_action_matches_gold"]
        reason_match += row["primary_reason_matches_gold"]
        audience_created += audience

    actions = {row["actual_primary_action"] for row in comparisons}
    reasons = {row["actual_primary_reason_category"] for row in comparisons}
    result = {
        "schema_version": "gate1-g3-route-60-result-v3.0",
        "task_id": contract.TASK_ID,
        "case_count": len(comparisons),
        "action_match_count": action_match,
        "reason_match_count": reason_match,
        "audience_content_created_count": audience_created,
        "action_distribution_complete": actions == EXPECTED_ACTIONS,
        "reason_distribution_complete": reasons == EXPECTED_REASONS,
        "gold_sha256": GOLD_SHA256,
        "pass": (action_match == 60 and reason_match == 60
                 and audience_created == 0
                 and actions == EXPECTED_ACTIONS
                 and reasons == EXPECTED_REASONS),
    }
    result["result_digest"] = contract.object_digest(result, "result_digest")

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (
        ("route_compiled.g3.jsonl", compiled_rows),
        ("route_actuals.g3.jsonl", actual_rows),
        ("route_comparisons.g3.jsonl", comparisons),
    ):
        with open(out_dir / name, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(contract.canonical_json(row) + "\n")
    (out_dir / "route_result.g3.yaml").write_text(
        "".join(f"{k}: {json.dumps(v, ensure_ascii=False)}\n"
                for k, v in result.items()),
        encoding="utf-8")
    return result


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("route_out")
    r = run_route_60(out)
    print(contract.canonical_json(r))
    raise SystemExit(0 if r["pass"] else 1)
