#!/usr/bin/env python3
"""G3 · 批级机器门（fail-closed，确定性，重复运行零差异）。

分级语义：
- HARD 码：机器硬失败 → 该条首次输出不可接受，永久留在分母；
- FLAG 码：进入人审复核队列，由内容/事实主审裁决，不自动判死。

覆盖（源指令 §8）：治理语言、标签泄漏、未绑定数字、组件表面真实消费、
核心事实覆盖、批内骨架集中度、近重复（批内 FLAG / 对冻结文本 HARD）、
run_id 批级唯一。
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import g3_author_contract as contract  # noqa: E402
import g3_expression  # noqa: E402
import g3_fingerprint  # noqa: E402
import g3_lexicon  # noqa: E402
import g3_similarity  # noqa: E402

_DIGIT_RUN_RE = re.compile(r"\d+(?:\.\d+)?")


def _material_text(request: Mapping[str, Any]) -> str:
    material = request["typed_material"]
    parts = [str(f["fact_value"]) for f in material["facts"]]
    parts += [str(s["source_summary"]) for s in material["sources"]]
    parts += [str(a["scope_summary"]) for a in material["authorizations"]]
    parts.append(str(request.get("user_goal", "")))
    return "\n".join(parts)


def number_findings(
    output: Mapping[str, Any], request: Mapping[str, Any]
) -> tuple[list[str], list[str]]:
    """受众表面的数字必须在材料中出现。多位数字/小数 HARD，单个数字 FLAG。"""
    material = _material_text(request)
    hard: set[str] = set()
    flag: set[str] = set()
    for kind, text in contract.audience_texts(_as_raw_view(output)):
        del kind
        for run in _DIGIT_RUN_RE.findall(text):
            if run in material:
                continue
            if len(run) == 1:
                flag.add(f"NUM_SINGLE_{run}")
            else:
                hard.add(f"NUM_UNBOUND_{run}")
    return sorted(hard), sorted(flag)


def _as_raw_view(output: Mapping[str, Any]) -> dict[str, Any]:
    """序列化输出的受众文本视图（兼容 surface_sequence 的字段读取）。"""
    return {
        "synthetic_disclosure": output["synthetic_disclosure"],
        "title": output["title"],
        "body": list(output["body"]),
        "spoken_lines": list(output["spoken_lines"]),
        "cta": output["cta"],
        "visual_execution": list(output["visual_execution"]),
        "audio_execution": list(output["audio_execution"]),
    }


def component_usage_findings(
    output: Mapping[str, Any], request: Mapping[str, Any]
) -> list[str]:
    """组件表面真实消费（HARD）：
    - 覆盖：approved_components 每个组件都必须有 usage 指针；
    - 角色兼容：每组件至少一个指针落在其 role 允许的表面类型；
    - 槽位绑定：普通组件该指针表面必须绑定其 required_fact_slots 的事实；
      轴算子组件该指针表面必须绑定 ≥1 核心事实。"""
    hard: list[str] = []
    surfaces = {s["surface_unit_id"]: s for s in output["surface_units"]}
    usage_by_component = {str(u["component_id"]): u
                          for u in output["component_usage"]}
    fact_slot = {str(f["fact_id"]): str(f["slot_id"])
                 for f in request["typed_material"]["facts"]}
    core_fact_ids = {fid for req in request["product_core_requirements"]
                     for fid in req["fact_ids"]}
    role_allowed = request["exact_author_contract"]["role_allowed_surface_kinds"]
    for component in request["approved_components"]:
        component_id = str(component["component_id"])
        role = str(component["component_role"])
        usage = usage_by_component.get(component_id)
        if usage is None:
            hard.append(f"E_G3_COMPONENT_USAGE_COVERAGE:{component_id}")
            continue
        allowed_kinds = set(role_allowed[role])
        required_slots = set(map(str, component.get("required_fact_slots", [])))
        is_axis = component_id.startswith("G1V11-P2-AXIS")
        satisfied = False
        for unit_id in usage["implementation_surface_unit_ids"]:
            surface = surfaces.get(str(unit_id))
            if surface is None or str(surface["surface_kind"]) not in allowed_kinds:
                continue
            bound_slots = {fact_slot.get(fid, "") for fid in surface["fact_ids"]}
            if is_axis:
                if set(surface["fact_ids"]) & core_fact_ids:
                    satisfied = True
                    break
            elif bound_slots & required_slots:
                satisfied = True
                break
        if not satisfied:
            hard.append(f"E_G3_COMPONENT_SURFACE_BINDING:{component_id}")
    return sorted(hard)


def core_coverage_findings(
    output: Mapping[str, Any], request: Mapping[str, Any]
) -> list[str]:
    """每个核心要求的每个 fact_id 至少绑定到一个真实受审表面（HARD）。"""
    bound: set[str] = set()
    for surface in output["surface_units"]:
        bound.update(map(str, surface["fact_ids"]))
    missing = sorted(
        fid
        for req in request["product_core_requirements"]
        for fid in req["fact_ids"]
        if fid not in bound
    )
    return [f"E_G3_CORE_FACT_UNBOUND:{fid}" for fid in missing]


def gate_batch(
    outputs: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, Any]],
    frozen_texts: Mapping[str, str],
) -> dict[str, Any]:
    """整批机器门。返回确定性报告 dict（可直接 canonical json 落盘）。"""
    request_by_id = {str(r["request_id"]): r for r in requests}
    per_output: list[dict[str, Any]] = []
    run_ids: dict[str, str] = {}
    for output in sorted(outputs, key=lambda o: str(o["request_id"])):
        request_id = str(output["request_id"])
        request = request_by_id[request_id]
        hard: list[str] = []
        flag: list[str] = []
        # 1. 治理语言 + 标签泄漏（受众表面，不含披露表面）
        for kind, text in contract.audience_texts(_as_raw_view(output)):
            del kind
            gov_hard, gov_flag = g3_lexicon.scan_governance(text)
            hard += [f"E_G3_GOVERNANCE:{c}" for c in gov_hard]
            flag += [f"F_G3_GOVERNANCE:{c}" for c in gov_flag]
            hard += [f"E_G3_LABEL_LEAK:{c}" for c in g3_lexicon.scan_label_leak(text)]
        # 2. 数字绑定
        num_hard, num_flag = number_findings(output, request)
        hard += [f"E_G3_{c}" for c in num_hard]
        flag += [f"F_G3_{c}" for c in num_flag]
        # 3. 组件表面真实消费 + 核心覆盖
        hard += component_usage_findings(output, request)
        hard += core_coverage_findings(output, request)
        # 4. 指纹谓词（FLAG）
        flag += [f"F_G3_FINGERPRINT:{p}"
                 for p in g3_fingerprint.predicate_findings(output)]
        # 5. run_id 唯一
        run_id = str(output["run_id"])
        if run_id in run_ids:
            hard.append(f"E_G3_RUN_ID_DUPLICATE:{run_ids[run_id]}")
        run_ids[run_id] = request_id
        per_output.append(
            {
                "request_id": request_id,
                "profile_id": str(output["profile_id"]),
                "hard_codes": sorted(set(hard)),
                "flag_codes": sorted(set(flag)),
                "machine_first_fail": bool(hard),
            }
        )
    # 6. 批级：骨架集中度（FLAG，含 END_GOV_DEFER 升 HARD）+ 近重复
    concentration = g3_expression.concentration_findings(list(outputs))
    for finding in concentration:
        if finding["kind"] == "GOV_DEFER_ENDING":
            for row in per_output:
                if row["request_id"] in finding["request_ids"]:
                    row["hard_codes"] = sorted(
                        set(row["hard_codes"]) | {"E_G3_GOV_DEFER_ENDING"})
                    row["machine_first_fail"] = True
    near_dup_batch = g3_similarity.pairwise_batch_findings(list(outputs))
    frozen_reuse = g3_similarity.frozen_reuse_findings(list(outputs), frozen_texts)
    for finding in frozen_reuse:
        for row in per_output:
            if row["request_id"] == finding["request_id"]:
                row["hard_codes"] = sorted(
                    set(row["hard_codes"])
                    | {f"E_G3_FROZEN_REUSE:{finding['frozen_key']}"})
                row["machine_first_fail"] = True
    hard_fail_count = sum(1 for row in per_output if row["machine_first_fail"])
    report = {
        "schema_version": "gate1-g3-machine-gate-report-v3.0",
        "task_id": contract.TASK_ID,
        "output_count": len(per_output),
        "machine_hard_fail_count": hard_fail_count,
        "per_output": per_output,
        "concentration_findings": concentration,
        "near_dup_batch_findings": near_dup_batch,
        "frozen_reuse_findings": frozen_reuse,
    }
    report["report_digest"] = contract.object_digest(report, "report_digest")
    return report


__all__ = [
    "component_usage_findings",
    "core_coverage_findings",
    "gate_batch",
    "number_findings",
]
