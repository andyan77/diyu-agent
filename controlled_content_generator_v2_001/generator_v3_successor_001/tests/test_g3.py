#!/usr/bin/env python3
"""G3 单元与反向测试（fail-closed 证明）。

运行：python3 tests/test_g3.py  （在 generator_v3_successor_001 目录或仓库根均可）
每个反向案例都必须让相应校验/门失败，证明检查不是摆设。
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

G3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(G3))

import g3_author_contract as contract  # noqa: E402
import g3_expression  # noqa: E402
import g3_gates  # noqa: E402
import g3_lexicon  # noqa: E402
import g3_request_builder as rb  # noqa: E402
import g3_similarity  # noqa: E402

PASSED: list[str] = []


def check(name: str, condition: bool) -> None:
    if not condition:
        print(f"[FAIL] {name}")
        raise SystemExit(1)
    PASSED.append(name)


def expect_error(name: str, fn, code_fragment: str) -> None:
    try:
        fn()
    except contract.AuthorContractError as error:
        check(name, code_fragment in str(error))
        return
    print(f"[FAIL] {name}: no error raised (expected {code_fragment})")
    raise SystemExit(1)


def make_scenario() -> dict:
    """CP01 lane A 全槽位合成场景（测试专用）。"""
    ab_paths, components = rb.load_frozen_base()
    slots = rb.lane_slot_union(ab_paths["CP01"]["lane_a"], components)
    slot_facts = {}
    for index, slot in enumerate(slots, 1):
        slot_facts[slot] = (
            f"测试素材{index}号：样衣师余念在工作台前完成第{index}道检查，"
            f"用镊子对齐0.5厘米缝份并记录状态。"
        )
    return {
        "schema_version": rb.SCENARIO_SCHEMA,
        "scenario_id": "G3-CUR-CP01-901",
        "profile_id": "CP01",
        "scenario_label": "测试场景",
        "lane_id": "A",
        "user_goal": "帮助观众看懂一次岗位检查如何完成。",
        "slot_facts": slot_facts,
        "audience_safe_boundary": "这次检查只做了一件样衣，其他批次还没有看过。",
        "claim_boundary_governance": "不能把单件检查结果外推为整批结论。",
        "authorization_scope": "合成测试材料，允许在本回归内引用。",
        "source_summary_a": "工作台记录摘要了检查顺序与缝份数值。",
        "source_summary_b": "样衣间便笺记录了工具与状态。",
        "synthetic_test_only": True,
        "provenance": {"base_scenario_id": "NEW", "invention_note": "单元测试场景"},
    }


AUTHOR = {
    "author_identity": "G3-AUTHOR-TEST-01",
    "author_session_logical_id": "G3-AUTHOR-SESSION-TEST-01",
    "author_platform_agent_id": "G3-AUTHOR-SESSION-TEST-01",
}


def make_valid_raw(request: dict) -> dict:
    """参考作者：从请求机械构造一份满足全部合同与门的输出。"""
    material = request["typed_material"]
    facts = material["facts"]
    src = [s["source_id"] for s in material["sources"]]
    auth = [a["authorization_id"] for a in material["authorizations"]]
    body = []
    fact_ids_per_body = []
    for fact in facts:
        body.append(str(fact["fact_value"]))
        fact_ids_per_body.append([fact["fact_id"]])
    title = "余念把缝份对齐之后"
    title_facts = [facts[0]["fact_id"]]
    capture_fact_ids = [f["fact_id"] for f in facts
                        if f["slot_id"] in ("authorized_action_evidence",
                                            "start_and_stop_state_evidence")]
    av_facts = sorted({facts[0]["fact_id"], *capture_fact_ids})
    visual = ["镜头贴近工作台，跟随镊子对齐缝份的动作。"]
    visual_facts = [av_facts]
    audio = ["保留镊子与纸样翻动的原声。"]
    audio_facts = [av_facts]
    disclosure = "本条为合成测试内容，不代表真实门店或人物。"
    surfaces = [
        {"surface_kind": "synthetic_disclosure", "text": disclosure,
         "fact_ids": [], "source_ids": [], "authorization_ids": []},
        {"surface_kind": "title", "text": title,
         "fact_ids": title_facts, "source_ids": src, "authorization_ids": auth},
    ]
    for text, fids in zip(body, fact_ids_per_body, strict=True):
        surfaces.append({"surface_kind": "body", "text": text,
                         "fact_ids": fids, "source_ids": src,
                         "authorization_ids": auth})
    for text, fids in zip(visual, visual_facts, strict=True):
        surfaces.append({"surface_kind": "visual_execution", "text": text,
                         "fact_ids": fids, "source_ids": src,
                         "authorization_ids": auth})
    for text, fids in zip(audio, audio_facts, strict=True):
        surfaces.append({"surface_kind": "audio_execution", "text": text,
                         "fact_ids": fids, "source_ids": src,
                         "authorization_ids": auth})
    # 组件指针：每组件指向绑定其 required slot 事实的表面
    slot_by_fact = {f["fact_id"]: f["slot_id"] for f in facts}
    surface_slot = []
    for surface in surfaces:
        slots = {slot_by_fact.get(fid) for fid in surface["fact_ids"]}
        surface_slot.append(slots)
    usage = []
    core_fact_ids = {fid for req in request["product_core_requirements"]
                     for fid in req["fact_ids"]}
    role_allowed = request["exact_author_contract"]["role_allowed_surface_kinds"]
    for component in request["approved_components"]:
        cid = component["component_id"]
        role = component["component_role"]
        kinds = set(role_allowed[role])
        required = set(map(str, component.get("required_fact_slots", [])))
        target = None
        for ordinal, surface in enumerate(surfaces, 1):
            if surface["surface_kind"] not in kinds:
                continue
            if cid.startswith("G1V11-P2-AXIS"):
                if set(surface["fact_ids"]) & core_fact_ids:
                    target = ordinal
                    break
            elif surface_slot[ordinal - 1] & required:
                target = ordinal
                break
        assert target is not None, f"no surface for {cid}"
        usage.append({"component_id": cid,
                      "implementation_note": f"在第{target}号表面实现{role}机制。",
                      "surface_ordinals": [target]})
    claim = body[0][:20]
    raw = {
        "schema_version": contract.RAW_SCHEMA,
        "request_id": request["request_id"],
        "run_id": f"G3RUN-{request['request_id']}-t1",
        "title": title,
        "body": body,
        "spoken_lines": [],
        "cta": "",
        "visual_execution": visual,
        "audio_execution": audio,
        "synthetic_disclosure": disclosure,
        "semantic_surfaces": surfaces,
        "semantic_claims": [
            {"claim_text": claim, "fact_ids": [facts[0]["fact_id"]],
             "source_ids": src, "authorization_ids": auth,
             "claim_boundary": material["claim_boundary"]}
        ],
        "semantic_component_usage": usage,
        "author_attestation": dict(contract.EXPECTED_ATTESTATION),
    }
    return raw


def main() -> int:
    scenario = make_scenario()
    plans = g3_expression.assign_plans("CP01", "TESTBATCH", 6)
    check("plans_deterministic",
          plans == g3_expression.assign_plans("CP01", "TESTBATCH", 6))
    from collections import Counter
    for key in ("opening_archetype", "ending_archetype", "title_archetype"):
        counts = Counter(p[key] for p in plans)
        check(f"plans_cap_{key}", max(counts.values()) <= 2)

    ab_paths, components = rb.load_frozen_base()
    request = rb.build_request(scenario, plans[0], ab_paths["CP01"], components,
                               AUTHOR, 1, "0" * 64, "contract/test")
    contract.validate_request(request)
    PASSED.append("request_valid")

    raw = make_valid_raw(request)
    output = contract.serialize(raw, request)
    check("serialize_ok", output["output_digest"])
    check("serialize_deterministic",
          contract.serialize(raw, request) == output)

    # ---- 反向案例（必须失败）----
    bad = copy.deepcopy(raw)
    bad["extra_field"] = 1
    expect_error("neg_extra_field", lambda: contract.validate_raw(bad, request),
                 "E_RAW_FIELD_SET")
    bad = copy.deepcopy(raw)
    bad["semantic_surfaces"][1]["text"] = "被篡改的标题"
    expect_error("neg_surface_join", lambda: contract.validate_raw(bad, request),
                 "E_RAW_SURFACE_EXACT_JOIN")
    bad = copy.deepcopy(raw)
    bad["semantic_claims"][0]["claim_text"] = "这句话不在任何表面上"
    expect_error("neg_claim_offsurface", lambda: contract.validate_raw(bad, request),
                 "E_RAW_CLAIM_NOT_ON_SURFACE")
    bad = copy.deepcopy(raw)
    bad["author_attestation"]["review_performed_by_author"] = True
    expect_error("neg_attestation", lambda: contract.validate_raw(bad, request),
                 "E_RAW_ATTESTATION")
    bad = copy.deepcopy(raw)
    bad["semantic_surfaces"][2]["source_ids"] = [request["typed_material"]
                                                 ["sources"][0]["source_id"]]
    expect_error("neg_source_closure", lambda: contract.validate_raw(bad, request),
                 "E_SURFACE_SOURCE_CLOSURE")
    bad = copy.deepcopy(raw)
    bad["semantic_claims"][0]["fact_ids"] = ["G3-CP01-901-FACT-99"]
    expect_error("neg_claim_unknown_fact", lambda: contract.validate_raw(bad, request),
                 "E_CLAIM_FACT_UNKNOWN")

    # ---- 门反向案例 ----
    frozen = {"REF-1": "完全无关的冻结参考文本，不会相似。"}
    good_report = g3_gates.gate_batch([output], [request], frozen)
    check("gate_clean_pass", good_report["machine_hard_fail_count"] == 0)
    check("gate_deterministic",
          g3_gates.gate_batch([output], [request], frozen) == good_report)

    def tampered_output(**edits):
        bad_raw = copy.deepcopy(raw)
        bad_raw.update(edits)
        # 表面重建，保持 exact join
        rebuilt = make_valid_raw(request)
        for key, value in edits.items():
            rebuilt[key] = value
        # 重新拼接表面
        seq = contract.surface_sequence(rebuilt)
        old_by_text = {s["text"]: s for s in rebuilt["semantic_surfaces"]}
        surfaces = []
        for kind, text in seq:
            base_surface = old_by_text.get(text)
            if base_surface and base_surface["surface_kind"] == kind:
                surfaces.append(base_surface)
            else:
                surfaces.append({"surface_kind": kind, "text": text,
                                 "fact_ids": [request["typed_material"]["facts"][0]["fact_id"]],
                                 "source_ids": [s["source_id"] for s in request["typed_material"]["sources"]],
                                 "authorization_ids": [a["authorization_id"] for a in request["typed_material"]["authorizations"]]}
                                if kind != "synthetic_disclosure" else
                                {"surface_kind": kind, "text": text, "fact_ids": [],
                                 "source_ids": [], "authorization_ids": []})
        rebuilt["semantic_surfaces"] = surfaces
        return contract.serialize(rebuilt, request)

    leak = tampered_output(title="这条 CP01 内容已获准上线")
    report = g3_gates.gate_batch([leak], [request], frozen)
    codes = report["per_output"][0]["hard_codes"]
    check("neg_gate_governance",
          any("GOV_APPROVAL" in c or "GOV_PUBLISH" in c for c in codes))
    check("neg_gate_label_leak", any("LEAK_CP_CODE" in c for c in codes))

    num = tampered_output(title="她量出了37.5厘米的缝份")
    report = g3_gates.gate_batch([num], [request], frozen)
    check("neg_gate_number", any("NUM_UNBOUND_37.5" in c
                                 for c in report["per_output"][0]["hard_codes"]))

    dropped = copy.deepcopy(raw)
    dropped["semantic_component_usage"] = dropped["semantic_component_usage"][1:]
    out2 = contract.serialize(dropped, request)
    report = g3_gates.gate_batch([out2], [request], frozen)
    check("neg_gate_component_coverage",
          any("E_G3_COMPONENT_USAGE_COVERAGE" in c
              for c in report["per_output"][0]["hard_codes"]))

    defer = tampered_output(body=[*raw["body"][:-1],
                                  "剩下的复杂修改仍由样衣组长决定。"])
    report = g3_gates.gate_batch([defer], [request], frozen)
    check("neg_gate_gov_defer_ending",
          "E_G3_GOV_DEFER_ENDING" in report["per_output"][0]["hard_codes"])

    reuse_frozen = {"REF-120-001": g3_similarity.audience_fulltext(output)}
    report = g3_gates.gate_batch([output], [request], reuse_frozen)
    check("neg_gate_frozen_reuse",
          any("E_G3_FROZEN_REUSE" in c
              for c in report["per_output"][0]["hard_codes"]))

    dup_run = copy.deepcopy(output)
    report = g3_gates.gate_batch([output, dup_run], [request], frozen)
    check("neg_gate_run_id_dup",
          any("E_G3_RUN_ID_DUPLICATE" in c
              for row in report["per_output"] for c in row["hard_codes"]))

    # 词典回归锚：上一轮 10 条泄漏的代表句必须命中
    for text in ("图片已经获准上线", "没有把它说成完成", "发布由其他岗位批准",
                 "没有给它补上所属人，也没有把状态写进画面"):
        hard, _ = g3_lexicon.scan_governance(text)
        check(f"lexicon_recall_{text[:6]}", bool(hard))

    print(f"ALL {len(PASSED)} CHECKS PASSED")
    for name in PASSED:
        print("  ok", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
