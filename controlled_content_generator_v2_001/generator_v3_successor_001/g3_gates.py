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
# v3：中文数量词绑定（第2轮 CP15-001 以"十七件"绕过阿拉伯数字门的教训）。
# 数值≥2 的中文数字+量词若在材料中无对应（同形或阿拉伯等值）→ FLAG 进人审。
_CN_NUM_RE = re.compile(
    r"[零一二两三四五六七八九十百]{1,4}"
    r"(?=[件条处次个位张只段道趟遍轮回批组层排步声人款码格页间店家杆摞])")
_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_to_int(token: str) -> int | None:
    """一~九百九十九 的窄解析；解析失败返回 None（不判）。"""
    if not token or any(c not in _CN_DIGITS and c not in "十百" for c in token):
        return None
    value, section, num = 0, 0, 0
    for ch in token:
        if ch in _CN_DIGITS:
            num = _CN_DIGITS[ch]
        elif ch == "十":
            section += (num or 1) * 10
            num = 0
        elif ch == "百":
            section += (num or 1) * 100
            num = 0
    value = section + num
    return value if value > 0 else None


def cn_number_findings(
    output: Mapping[str, Any], request: Mapping[str, Any]
) -> list[str]:
    """受众表面中文数量词（值≥2）须在材料中有对应（同形中文或阿拉伯等值）。FLAG。"""
    material = _material_text(request)
    flag: set[str] = set()
    for kind, text in contract.audience_texts(_as_raw_view(output)):
        # 只查事实承载表面；画面/声音是导演性描写（三格/两层），不作数量断言
        if kind in ("visual_execution", "audio_execution"):
            continue
        for m in _CN_NUM_RE.finditer(text):
            token = m.group(0)
            value = _cn_to_int(token)
            if value is None or value < 2:
                continue
            measure = text[m.end():m.end() + 1]
            # 成对绑定：中文同形对 或 阿拉伯等值+同量词 对（裸数值在材料中
            # 他处出现不算——第2轮 CP05-005"两只"即因材料他处含 2 而漏检）
            if (token + measure) in material or f"{value}{measure}" in material:
                continue
            flag.add(f"CN_NUM_UNBOUND_{token}{measure}")
    return sorted(flag)
# v2：合成披露语句内嵌受众正文（第1轮 CP18 病灶的机器化，HARD）
_DISCLOSURE_IN_BODY_RE = re.compile(
    r"(是|均为|都是|为)合成(的)?|合成的?(门店|人物|顾客|城市|场景|品牌|内容)|"
    r"不是真实(的)?(门店|人物|顾客|品牌|城市)|非真实(门店|人物|品牌)")


def cross_output_reuse_findings(
    outputs: "Sequence[Mapping[str, Any]]",
    requests_by_id: Mapping[str, Mapping[str, Any]],
    min_len: int = 10,
) -> list[dict[str, Any]]:
    """同产品跨条近逐字复用（FLAG）：两条输出共享 ≥min_len 字的连续片段，
    且该片段不出自任一方的材料文本（事实/来源/目标里的引用不算复用）。"""
    by_profile: dict[str, list[tuple[str, str, str]]] = {}
    for output in outputs:
        rid = str(output["request_id"])
        text = g3_similarity.normalize(g3_similarity.audience_fulltext(output))
        material = g3_similarity.normalize(
            _material_text(requests_by_id[rid]))
        by_profile.setdefault(str(output["profile_id"]), []).append(
            (rid, text, material))
    findings: list[dict[str, Any]] = []
    for profile_id in sorted(by_profile):
        rows = by_profile[profile_id]
        for i in range(len(rows)):
            rid_a, text_a, mat_a = rows[i]
            grams_a = {text_a[k:k + min_len]
                       for k in range(max(0, len(text_a) - min_len + 1))}
            for j in range(i + 1, len(rows)):
                rid_b, text_b, mat_b = rows[j]
                grams_b = {text_b[k:k + min_len]
                           for k in range(max(0, len(text_b) - min_len + 1))}
                shared = sorted(
                    g for g in grams_a & grams_b
                    if g not in mat_a and g not in mat_b)
                if shared:
                    findings.append(
                        {"kind": "CROSS_OUTPUT_REUSE", "profile_id": profile_id,
                         "request_ids": sorted([rid_a, rid_b]),
                         "shared_count": len(shared),
                         "samples": shared[:3]})
    return findings


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
        # 1. 治理语言 + 标签泄漏 + 披露内嵌（受众表面，不含披露表面）
        for kind, text in contract.audience_texts(_as_raw_view(output)):
            del kind
            gov_hard, gov_flag = g3_lexicon.scan_governance(text)
            hard += [f"E_G3_GOVERNANCE:{c}" for c in gov_hard]
            flag += [f"F_G3_GOVERNANCE:{c}" for c in gov_flag]
            hard += [f"E_G3_LABEL_LEAK:{c}" for c in g3_lexicon.scan_label_leak(text)]
            if _DISCLOSURE_IN_BODY_RE.search(text):
                hard.append("E_G3_DISCLOSURE_IN_BODY")
        # 2. 数字绑定（阿拉伯 HARD/FLAG + 中文数量词 FLAG）
        num_hard, num_flag = number_findings(output, request)
        hard += [f"E_G3_{c}" for c in num_hard]
        flag += [f"F_G3_{c}" for c in num_flag]
        flag += [f"F_G3_{c}" for c in cn_number_findings(output, request)]
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
    _HARD_CONCENTRATION = {
        "GOV_DEFER_ENDING": "E_G3_GOV_DEFER_ENDING",
        # v3：第2轮病灶——同产品限度句族/声音模板家族成套复用（>2/产品）升 HARD
        "BOUNDARY_FAMILY_CONCENTRATION": "E_G3_BOUNDARY_FAMILY_CONCENTRATION",
        "AUDIO_TEMPLATE_CONCENTRATION": "E_G3_AUDIO_TEMPLATE_CONCENTRATION",
    }
    # 批级坍缩（跨产品同族 >8/批）降 FLAG：连坐会误伤同族中偶发合法用者
    # （第2轮 9 条良品中 6 条即因他人过量使用被批级扫入），交人审裁决
    _FLAG_CONCENTRATION = {
        "BOUNDARY_FAMILY_BATCH_CONCENTRATION":
            "F_G3_BOUNDARY_FAMILY_BATCH_CONCENTRATION",
        "AUDIO_TEMPLATE_BATCH_CONCENTRATION":
            "F_G3_AUDIO_TEMPLATE_BATCH_CONCENTRATION",
    }
    for finding in concentration:
        kind = str(finding["kind"])
        code = _HARD_CONCENTRATION.get(kind)
        if code:
            if kind != "GOV_DEFER_ENDING":
                code = f"{code}:{finding['class']}"
            for row in per_output:
                if row["request_id"] in finding["request_ids"]:
                    row["hard_codes"] = sorted(set(row["hard_codes"]) | {code})
                    row["machine_first_fail"] = True
        flag_code = _FLAG_CONCENTRATION.get(kind)
        if flag_code:
            for row in per_output:
                if row["request_id"] in finding["request_ids"]:
                    row["flag_codes"] = sorted(
                        set(row["flag_codes"]) | {f"{flag_code}:{finding['class']}"})
    near_dup_batch = g3_similarity.pairwise_batch_findings(list(outputs))
    frozen_reuse = g3_similarity.frozen_reuse_findings(list(outputs), frozen_texts)
    cross_reuse = cross_output_reuse_findings(list(outputs), request_by_id)
    for finding in cross_reuse:
        for row in per_output:
            if row["request_id"] in finding["request_ids"]:
                row["flag_codes"] = sorted(
                    set(row["flag_codes"]) | {"F_G3_CROSS_OUTPUT_REUSE"})
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
        "cross_output_reuse_findings": cross_reuse,
    }
    report["report_digest"] = contract.object_digest(report, "report_digest")
    return report


__all__ = [
    "cn_number_findings",
    "component_usage_findings",
    "core_coverage_findings",
    "gate_batch",
    "number_findings",
]
