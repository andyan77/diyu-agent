"""v2.5 状态感知检查节（M1-C2 迁移）。

被 `p7_master_check.py` 作为内部模块加载——不是第二个总检查入口（P1 §十七）。

职责：
  1. 实际态/期望态分离校验：实际状态文件（M0_STATUS / 两 manifest / stage_actual_state）
     只承载真实结果；期望由 STATE_EXPECTATION 按里程碑给出；本模块比较两者。
     不再把 NOT_QUALIFIED / case_count==0 / B 未推进钉死为永恒正确答案；
     合法未来状态（金标物化、M0 合格、B 轨推进、拨付发生）不会使检查失败。
  2. 阶段合同 v2 结构校验（Y 三状态机、B 轨独立、S3 诊断门、S6 记账入口）。
  3. 成本记账合同校验（拨付制、24 字段保留、DeepSeek 30 元/日保留、预算阻断零残留）。
  4. ACTIVE_CONTRACT_SET / D0 五条件 / RUN_JOURNAL 复算。
  5. FINAL 模式 typed 回执与签字回执复核（缺字段=未签）。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

GATE1 = "controlled_content_generator_v2_001/gate1_v1_1_001"
P7 = f"{GATE1}/p7_successor_longrun_001"
G3 = "controlled_content_generator_v2_001/generator_v3_successor_001"
EVAL_SPINE = f"{P7}/eval_audit_spine_001"
DC = f"{P7}/delivery_control_001"

LEGAL_M0_STATUSES = {"NOT_QUALIFIED", "QUALIFIED", "DIAGNOSTIC_FINAL"}
TERMINAL_RESULTS = {"PASS", "DIAGNOSTIC_FINAL", "FAIL", "HONEST_STOP"}
HEX64 = set("0123456789abcdef")


def _j(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX64


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_digest(record: dict, digest_field: str) -> str:
    unsigned = {k: v for k, v in record.items() if k != digest_field}
    return hashlib.sha256(json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _expectation(root: Path, ctx: dict) -> tuple[dict | None, dict | None, str | None]:
    state_file = ctx.get("state_file") or (root / DC / "state/STATE_EXPECTATION.v1.json")
    state_file = Path(state_file)
    if not state_file.is_file():
        return None, None, f"STATE_EXPECTATION missing: {state_file}"
    spec = _j(state_file)
    milestone = ctx.get("milestone", "M1")
    exp = spec.get("milestone_expectations", {}).get(milestone)
    if exp is None:
        return spec, None, f"no expectation registered for milestone {milestone}"
    return spec, exp, None


# ---------------------------------------------------------------- sections

def check_m0_state_integrity(root: Path, ctx: dict) -> tuple[bool, list[str]]:
    """实际态一致性不变量 + 里程碑期望比较（取代 v1 的钉死初始值检查）。"""
    es = root / EVAL_SPINE
    paths = {
        "m0": es / "calibration/M0_STATUS.v1.json",
        "v11": es / "calibration/V11_STATUS.v1.json",
        "qm": es / "calibration/qualification_manifest.v1.json",
        "dm": es / "calibration/dev_manifest.v1.json",
        "stage_actual": es / "calibration/stage_actual_state.v1.json",
    }
    missing = [k for k, p in paths.items() if not p.is_file()]
    if missing:
        return False, [f"missing actual-state files: {missing}"]
    m0, v11, qm, dm, sa = (_j(paths[k])
                           for k in ("m0", "v11", "qm", "dm", "stage_actual"))
    errors: list[str] = []

    status = m0.get("status")
    if status not in LEGAL_M0_STATUSES:
        errors.append(f"m0 status illegal: {status}")
    if status == "QUALIFIED":
        if not m0.get("evidence_manifest_digests"):
            errors.append("QUALIFIED without evidence_manifest_digests")
        if not m0.get("decided_by") or not m0.get("decision_digest"):
            errors.append("QUALIFIED without decided_by/decision_digest")
    if status == "NOT_QUALIFIED":
        forbidden = set(m0.get("claims_forbidden", []))
        if not {"TRUSTED_EVALUATION", "READY_FOR_300"} <= forbidden:
            errors.append("NOT_QUALIFIED but forbidden-claims discipline dropped")
    if "BUDGET_UNAPPROVED" in m0.get("reason_codes", []):
        errors.append("m0 reason_codes still carries removed budget-approval concept")

    # V1.1 实际资格态（Codex R2 BLOCKING 修复）：磁盘真源 + 一致性 + 期望比较
    v11_status = v11.get("status")
    if v11_status not in {"NOT_QUALIFIED", "QUALIFIED"}:
        errors.append(f"v11 status illegal: {v11_status}")
    b_track_all = ["S2_FEASIBILITY_AND_COST_TELEMETRY", "S3_CAUSAL_PILOT_60",
                   "S4_OPEN_REGRESSION_120", "S5_HIDDEN_QUALIFICATION_40",
                   "S6_BASELINE_240_PLUS_60", "S7_INDEPENDENT_FINAL_AUDIT"]
    if v11_status == "QUALIFIED":
        if not v11.get("evidence_manifest_digests"):
            errors.append("v11 QUALIFIED without evidence_manifest_digests")
        if not v11.get("decided_by") or not v11.get("decision_digest"):
            errors.append("v11 QUALIFIED without decided_by/decision_digest")
        executed_now = set(sa.get("executed_stages", []))
        missing_stages = [s for s in b_track_all if s not in executed_now]
        if missing_stages:
            errors.append(f"v11 QUALIFIED but B-track stages never executed: "
                          f"{missing_stages}")
    if v11_status == "NOT_QUALIFIED":
        if "READY_FOR_300" not in set(v11.get("claims_forbidden", [])):
            errors.append("v11 NOT_QUALIFIED but forbidden-claims discipline dropped")

    for name, manifest, needs_dataset in (("qm", qm, True), ("dm", dm, False)):
        count = manifest.get("case_count")
        content = manifest.get("content_status")
        src, gold = manifest.get("source_manifest_digest"), manifest.get("gold_manifest_digest")
        if not isinstance(count, int) or count < 0:
            errors.append(f"{name}: case_count invalid")
            continue
        if count == 0:
            if content != "NOT_MATERIALIZED":
                errors.append(f"{name}: case_count==0 but content_status={content}")
            if src is not None or gold is not None:
                errors.append(f"{name}: empty set carries manifest digests")
        else:
            if content != "MATERIALIZED":
                errors.append(f"{name}: case_count>0 but content_status={content}")
            if not (_is_hex64(src) and _is_hex64(gold)):
                errors.append(f"{name}: materialized without valid source/gold digests")
            if needs_dataset and not _is_hex64(manifest.get("dataset_manifest_digest")):
                errors.append(f"{name}: materialized without dataset_manifest_digest")

    executed = sa.get("executed_stages", [])
    receipts = sa.get("stage_receipts", {})
    for stage in executed:
        if stage not in receipts:
            errors.append(f"executed stage without receipt: {stage}")
    contract_path = root / EVAL_SPINE / "contract/stage_and_kill.v2.json"
    if contract_path.is_file():
        contract = _j(contract_path)
        known = {s["stage_id"] for s in contract.get("stages", [])}
        track_b = contract.get("topology", {}).get("track_B", [])
        for stage in executed:
            if stage not in known:
                errors.append(f"executed stage unknown to contract: {stage}")
        executed_b = [s for s in track_b if s in executed]
        if executed_b != track_b[:len(executed_b)]:
            errors.append(f"B-track stages skipped: executed={executed_b}")
    else:
        errors.append("stage_and_kill.v2.json missing")

    spec, exp, exp_error = _expectation(root, ctx)
    if exp_error:
        errors.append(exp_error)
    else:
        assert exp is not None
        if status not in exp.get("m0_status", []):
            errors.append(f"m0 status {status} outside expectation for "
                          f"{ctx.get('milestone')}: {exp.get('m0_status')}")
        if v11_status not in exp.get("v11_status", []):
            errors.append(f"v11 status {v11_status} outside expectation for "
                          f"{ctx.get('milestone')}: {exp.get('v11_status')}")
        if qm.get("content_status") not in exp.get(
                "qualification_manifest_content_status", []):
            errors.append("qualification manifest status outside expectation")
        if dm.get("content_status") not in exp.get(
                "dev_manifest_content_status", []):
            errors.append("dev manifest status outside expectation")
        allowed = set(exp.get("executed_stages_allowed", []))
        overrun = [s for s in executed if s not in allowed]
        if overrun:
            errors.append(f"executed stages beyond milestone expectation: {overrun}")
        if sa.get("real_run_executed") not in exp.get("real_run_executed", []):
            errors.append("real_run_executed outside milestone expectation")

    return not errors, ([f"milestone={ctx.get('milestone')}",
                         f"m0_actual_status={status}",
                         f"v11_actual_status={v11_status}",
                         f"qualification_cases={qm.get('case_count')}",
                         f"executed_stages={len(executed)}"]
                        + errors)


def check_stage_contract_v2(root: Path, ctx: dict) -> tuple[bool, list[str]]:
    """阶段合同 v2：Y 三状态机 / B 轨独立 / S3 诊断门 / S6 记账入口 / 旧预算键零残留。"""
    path = root / EVAL_SPINE / "contract/stage_and_kill.v2.json"
    if not path.is_file():
        return False, ["stage_and_kill.v2.json missing"]
    contract = _j(path)
    errors: list[str] = []
    stages = {s["stage_id"]: s for s in contract.get("stages", [])}
    topo = contract.get("topology", {})

    if "current_state" in contract:
        errors.append("contract embeds current_state (actual/expected separation breach)")
    if topo.get("model") != "Y_THREE_TRACK_STATE_MACHINE":
        errors.append("topology model not Y three-track")
    if topo.get("shared_trunk") != ["S0_DETERMINISTIC_HYGIENE"]:
        errors.append("shared trunk drifted")
    if topo.get("track_A") != ["S1_M0_MEASUREMENT_QUALIFICATION"]:
        errors.append("track A drifted")

    s2 = stages.get("S2_FEASIBILITY_AND_COST_TELEMETRY", {})
    expected_s2_entry = {"S0_PASS", "FIVE_FAMILY_STRATEGIES_FROZEN",
                         "INDEPENDENT_REVIEW_ROLES_ASSIGNED",
                         "B_EVAL_ROUTE_FROZEN",
                         "NARRATIVE_FACT_REVIEW_CAPABILITY_READY"}
    if set(s2.get("entry_requires", [])) != expected_s2_entry:
        errors.append(f"S2 entry keys drifted: {sorted(s2.get('entry_requires', []))}")
    if "PROJECTED_300_COST_WITHIN_ALL_APPROVED_CEILINGS" in s2.get("exit_requires", []):
        errors.append("S2 exit still carries projected-cost ceiling key")
    if "P50_AND_P95_COST_AND_LATENCY_REPORTED" not in s2.get("exit_requires", []):
        errors.append("S2 exit lost P50/P95 telemetry key (retention breach)")

    for stage_id in topo.get("track_B", []):
        entry = set(stages.get(stage_id, {}).get("entry_requires", []))
        if "S1_PASS" in entry or "M0_STATUS_QUALIFIED" in entry or any(
                key.startswith("A2") for key in entry):
            errors.append(f"B-track stage {stage_id} depends on A track: {sorted(entry)}")

    s3 = stages.get("S3_CAUSAL_PILOT_60", {})
    if s3.get("gate_type") != "DIAGNOSTIC":
        errors.append("S3 not a diagnostic gate")
    if "S3_DIAGNOSTIC_COMPLETE" not in s3.get("legal_exit_states", {}):
        errors.append("S3 lacks S3_DIAGNOSTIC_COMPLETE legal exit")
    if "STOP_S3_NO_CAUSAL_LIFT" in s3.get("kill_codes", []):
        errors.append("S3 still auto-kills on missing causal lift")
    if not {"CAUSAL_COMPARISON_INTERPRETABLE", "HIGH_RISK_HARD_VETO_COUNT_ZERO",
            "ANOMALIES_FULLY_REPORTED"} <= set(s3.get("safety_exit_requires", [])):
        errors.append("S3 safety exit keys incomplete")

    s4_entry = set(stages.get("S4_OPEN_REGRESSION_120", {}).get("entry_requires", []))
    if "S3_PASS" in s4_entry:
        errors.append("S4 entry still hard-requires S3_PASS")
    if not {"S3_DIAGNOSTIC_COMPLETE_OR_S3_PASS", "S3_SAFETY_EXIT_ALL_GREEN"} <= s4_entry:
        errors.append("S4 entry lacks diagnostic-complete + safety-green keys")

    s6_entry = set(stages.get("S6_BASELINE_240_PLUS_60", {}).get("entry_requires", []))
    if "COST_REFORECAST_WITHIN_BUDGET" in s6_entry:
        errors.append("S6 entry still budget-blocked")
    if "COST_ACCOUNTING_COMPLETE_AND_RECOMPUTABLE" not in s6_entry:
        errors.append("S6 entry lacks accounting-completeness key")

    kills = {rule.get("code") for rule in contract.get("global_kill_rules", [])}
    if "STOP_BUDGET" in kills:
        errors.append("global STOP_BUDGET resurrected")
    if "STOP_COST_ACCOUNTING_MISSING" not in kills:
        errors.append("accounting-missing stop absent")
    for retained in ("STOP_EXTERNAL_LLM_DAILY_BUDGET", "STOP_DATA_LEAKAGE",
                     "STOP_FIRST_OUTPUT_LAUNDERING", "REQUEST_STANDARD_REVISION"):
        if retained not in kills:
            errors.append(f"retained kill rule missing: {retained}")

    return not errors, ([f"stages={len(stages)}",
                         "track_independence=B_not_gated_by_A"] + errors)


def check_cost_accounting_contract(root: Path, ctx: dict) -> tuple[bool, list[str]]:
    """拨付制记账合同 + 保留面（24 字段、DeepSeek 30 元/日）+ 运行时符号迁移。"""
    es = root / EVAL_SPINE
    v2_path = es / "contract/cost_accounting.v2.json"
    v1_path = es / "contract/cost_budget.v1.json"
    ext_path = es / "contract/external_llm_budget.v1.json"
    if not v2_path.is_file():
        return False, ["cost_accounting.v2.json missing"]
    v2 = _j(v2_path)
    errors: list[str] = []

    for dead_key in ("approval_status", "hard_ceilings", "approved_by",
                     "current_decision", "budget_digest"):
        if dead_key in v2:
            errors.append(f"cost contract resurrects budget key: {dead_key}")
    rules = set(v2.get("fail_closed_rules", []))
    for retained in ("NO_MISSING_CALL_OR_REVIEW_COSTS",
                     "NO_ZERO_COST_PLACEHOLDERS_FOR_UNKNOWN_COSTS"):
        if retained not in rules:
            errors.append(f"retained fail-closed rule missing: {retained}")
    for removed in ("NO_SCALE_WHILE_APPROVAL_STATUS_IS_NOT_APPROVED",
                    "NO_NEW_COST_EVENT_AFTER_ANY_HARD_CEILING_IS_REACHED",
                    "NO_SCALE_WHEN_P95_FORECAST_EXCEEDS_ANY_HARD_CEILING"):
        if removed in rules:
            errors.append(f"budget-blocking rule resurrected: {removed}")
    if v2.get("funding_model") != "FOUNDER_ON_DEMAND_DISBURSEMENT":
        errors.append("funding model drifted from disbursement")
    ledger = v2.get("disbursement_ledger")
    if not isinstance(ledger, list):
        errors.append("disbursement_ledger missing/invalid")
    else:
        required_fields = set(v2.get("disbursement_entry_required_fields", []))
        for i, entry in enumerate(ledger):
            if not isinstance(entry, dict) or not required_fields <= set(entry):
                errors.append(f"disbursement entry {i} missing required fields")

    if v1_path.is_file():
        v1 = _j(v1_path)
        if v2.get("required_cost_event_fields") != v1.get("required_cost_event_fields"):
            errors.append("24-field cost event list drifted from sealed v1 (retention breach)")
    else:
        errors.append("sealed cost_budget.v1.json missing (history integrity)")

    if not ext_path.is_file():
        errors.append("external_llm_budget.v1.json missing (retention breach)")
    else:
        ext = _j(ext_path)
        if (ext.get("daily_hard_ceiling_cny") != 30.0
                or ext.get("currency") != "CNY"):
            errors.append("DeepSeek 30 CNY/day narrow gate drifted")

    sys.path.insert(0, str(es))
    try:
        import importlib
        for mod_name in [m for m in list(sys.modules)
                         if m == "spine" or m.startswith("spine.")]:
            del sys.modules[mod_name]
        cost = importlib.import_module("spine.cost")
        stage_gate = importlib.import_module("spine.stage_gate")
        if hasattr(cost, "budget_gate"):
            errors.append("runtime still exposes budget_gate")
        if not hasattr(cost, "accounting_integrity_gate"):
            errors.append("runtime lacks accounting_integrity_gate")
        if "budget" in stage_gate.STAGE_GATE_KEYS.get("S2", set()):
            errors.append("stage_gate S2 still requires budget key")
        if not hasattr(stage_gate, "S3_SAFETY_KEYS"):
            errors.append("stage_gate lacks S3 safety key split")
    finally:
        if sys.path and sys.path[0] == str(es):
            sys.path.pop(0)

    return not errors, (["funding_model=FOUNDER_ON_DEMAND_DISBURSEMENT",
                         f"disbursements_recorded={len(v2.get('disbursement_ledger', []))}",
                         "deepseek_30cny_daily_gate=retained"] + errors)


def check_active_contract_set(root: Path, ctx: dict) -> tuple[bool, list[str]]:
    """活跃合同集合成员存在且摘要可复算；冻结清单存在时逐成员比对。"""
    tool = root / DC / "tools/contract_set.py"
    set_file = root / DC / "ACTIVE_CONTRACT_SET.v1.json"
    frozen_path = root / DC / "state/ACTIVE_CONTRACT_DIGESTS.v1.json"
    if not tool.is_file() or not set_file.is_file():
        return False, ["contract_set tool or set file missing"]
    module = _load_module(tool, "p7_contract_set")
    frozen_exists = frozen_path.is_file()
    live = module.compute(set_file, root, allow_pending=not frozen_exists)
    errors = list(live["errors"])
    details = [f"members={len(live['members'])}",
               f"pending={live['pending_count']}",
               f"frozen_manifest_present={frozen_exists}"]
    if frozen_exists:
        frozen = _j(frozen_path)
        if frozen.get("pending_count", 0) > 0:
            live = module.compute(set_file, root, allow_pending=True)
            errors = list(live["errors"])
        frozen_map = {m["id"]: m.get("sha256") for m in frozen.get("members", [])}
        live_map = {m["id"]: m.get("sha256") for m in live["members"]}
        if set(frozen_map) != set(live_map):
            errors.append(f"member set drift: {sorted(set(frozen_map) ^ set(live_map))}")
        else:
            drifted = sorted(mid for mid in frozen_map if frozen_map[mid] != live_map[mid])
            if drifted:
                errors.append(f"member digest drift: {drifted}")
        if frozen.get("active_contract_set_digest") != live.get("active_contract_set_digest"):
            errors.append("active_contract_set_digest drift")
    return not errors, details + errors


def check_d0_status(root: Path, ctx: dict) -> tuple[bool, list[str]]:
    """D0 五条件从磁盘复算；d0_approved 布尔速记与复算不符 = FAIL。"""
    status_path = root / DC / "state/D0_STATUS.v1.json"
    if not status_path.is_file():
        return False, ["D0_STATUS missing"]
    status = _j(status_path)
    errors: list[str] = []
    charter = root / Path(status.get("charter_path", ""))
    text_on_disk = charter.is_file()
    digest_frozen = False
    if text_on_disk and _is_hex64(status.get("charter_sha256")):
        digest_frozen = sha256_file(charter) == status["charter_sha256"]
        if not digest_frozen:
            errors.append("charter digest recompute mismatch")
    acs_frozen = False
    frozen_path = root / DC / "state/ACTIVE_CONTRACT_DIGESTS.v1.json"
    if frozen_path.is_file() and _is_hex64(status.get("active_contract_set_digest")):
        acs_frozen = (_j(frozen_path).get("active_contract_set_digest")
                      == status["active_contract_set_digest"])
        if not acs_frozen:
            errors.append("active contract set digest mismatch vs frozen manifest")
    review_ok = False
    isolation_ok = False
    rp = status.get("review_receipt_path")
    if rp:
        receipt_path = root / rp
        if receipt_path.is_file():
            receipt_errors = validate_signer_receipt(root, receipt_path)
            review_ok = not receipt_errors and _j(receipt_path).get("verdict") == "ACCEPT"
            isolation_ok = review_ok
            if receipt_errors:
                errors.append(f"d0 review receipt invalid: {receipt_errors[:3]}")
            if _is_hex64(status.get("review_receipt_digest")):
                if sha256_file(receipt_path) != status["review_receipt_digest"]:
                    errors.append("d0 review receipt digest mismatch")
                    review_ok = isolation_ok = False
        else:
            errors.append("d0 review receipt path dangling")
    recomputed = (text_on_disk and digest_frozen and acs_frozen
                  and review_ok and isolation_ok)
    if bool(status.get("d0_approved")) != recomputed:
        errors.append(
            f"d0_approved={status.get('d0_approved')} contradicts recomputation="
            f"{recomputed} (boolean shortcut forbidden)")
    return not errors, ([
        f"text_on_disk={text_on_disk}", f"digest_frozen={digest_frozen}",
        f"active_contract_digest_frozen={acs_frozen}",
        f"independent_review_pass={review_ok}",
        f"reviewer_isolation_valid={isolation_ok}",
        f"d0_approved_recomputed={recomputed}"] + errors)


def check_run_journal(root: Path, ctx: dict) -> tuple[bool, list[str]]:
    """RUN_JOURNAL 链复算 + 与 Git 互校；缺失/损坏/矛盾 = FAIL（STOP_RUN_JOURNAL_INVALID）。"""
    tool = root / DC / "tools/run_journal.py"
    journal = root / DC / "journal/RUN_JOURNAL.v1.jsonl"
    if not tool.is_file():
        return False, ["run_journal tool missing"]
    module = _load_module(tool, "p7_run_journal")
    state = module.parse_journal(journal)
    errors = list(state["errors"])
    if state["status"] not in ("VALID",):
        errors.append(f"journal status={state['status']} -> STOP_RUN_JOURNAL_INVALID")
    if state["records"]:
        last = state["records"][-1]
        head_exists = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e",
             f"{last.get('git_head')}^{{commit}}"],
            capture_output=True).returncode == 0
        if not head_exists:
            errors.append("journal last git_head unknown to repository")
        if last.get("session_id", "") == "":
            errors.append("journal last record missing session identity")
    return not errors, ([f"journal_status={state['status']}",
                         f"records={len(state['records'])}"] + errors)


def validate_signer_receipt(root: Path, receipt_path: Path) -> list[str]:
    """签字回执复核：schema、摘要复算、隔离声明。缺任一必填字段 = 未签。"""
    errors: list[str] = []
    try:
        receipt = _j(receipt_path)
    except (OSError, ValueError):
        return ["receipt unreadable"]
    schema_path = root / DC / "schema/signer_receipt.v1.schema.json"
    try:
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(_j(schema_path))
        for error in sorted(validator.iter_errors(receipt),
                            key=lambda item: list(item.path)):
            errors.append(f"schema:{error.message[:80]}")
    except ImportError:
        errors.append("jsonschema unavailable; receipt cannot be verified -> unsigned")
    if receipt.get("receipt_digest") != _canonical_digest(receipt, "receipt_digest"):
        errors.append("receipt_digest recompute mismatch")
    attestation = receipt.get("session_isolation_attestation", {})
    if not isinstance(attestation, dict) or not all(
            attestation.get(key) is True for key in (
                "fresh_session_not_fork_not_resume",
                "did_not_author_reviewed_scope",
                "auto_memory_disabled_or_not_applicable")):
        errors.append("isolation attestation invalid -> unsigned")
    return errors


def check_final_receipts(root: Path, ctx: dict) -> tuple[bool, list[str]]:
    """FINAL 模式硬门：typed PASS + ≥2 份有效独立签字绑定同一候选。"""
    milestone = ctx.get("milestone", "M1")
    mdir = root / DC / "milestones" / milestone
    receipt_path = mdir / "CLOSEOUT_RECEIPT.v1.json"
    decision_path = mdir / "STAGE_DECISION.v1.json"
    errors: list[str] = []
    if not receipt_path.is_file() or not decision_path.is_file():
        return False, [f"typed receipts missing under milestones/{milestone}"]
    schema_path = root / DC / "schema/typed_receipt.v1.schema.json"
    try:
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(_j(schema_path))
    except ImportError:
        return False, ["jsonschema unavailable; FINAL cannot verify typed receipts"]
    receipts = {}
    for name, path in (("CLOSEOUT_RECEIPT", receipt_path),
                       ("STAGE_DECISION", decision_path)):
        value = _j(path)
        receipts[name] = value
        for error in sorted(validator.iter_errors(value),
                            key=lambda item: list(item.path)):
            errors.append(f"{name}:schema:{error.message[:80]}")
        if value.get("receipt_digest") != _canonical_digest(value, "receipt_digest"):
            errors.append(f"{name}: receipt_digest recompute mismatch")
        if value.get("result") not in TERMINAL_RESULTS:
            errors.append(f"{name}: non-terminal result {value.get('result')} "
                          "cannot close a milestone (REVIEW_READY is not PASS)")
    closeout = receipts["CLOSEOUT_RECEIPT"]
    if closeout.get("result") == "PASS":
        bindings = closeout.get("review_bindings", [])
        if len(bindings) < 2:
            errors.append("PASS without two independent review bindings")
        kinds = {b.get("reviewer_kind") for b in bindings}
        if len(kinds) < 2:
            errors.append("review bindings not from two distinct reviewer kinds")
        for binding in bindings:
            rp = root / str(binding.get("receipt_path", ""))
            if not rp.is_file():
                errors.append(f"review receipt missing: {binding.get('receipt_path')}")
                continue
            if sha256_file(rp) != binding.get("receipt_digest"):
                errors.append(f"review receipt digest mismatch: {rp.name}")
            receipt_errors = validate_signer_receipt(root, rp)
            if receipt_errors:
                errors.append(f"review receipt invalid ({rp.name}): {receipt_errors[:2]}")
                continue
            receipt = _j(rp)
            if receipt.get("input_commit") != closeout.get("candidate_commit"):
                errors.append(f"review not bound to candidate commit: {rp.name}")
            if receipt.get("verdict") != "ACCEPT":
                errors.append(f"review verdict not ACCEPT: {rp.name}")
    return not errors, ([f"milestone={milestone}",
                         f"closeout_result={closeout.get('result')}"] + errors)
