#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_3600_microbatch_briefing_go_nogo.py  (P6)

Independently gate the 3600 microbatch briefing + go/no-go pack.
Ground truth recomputed here (E12): the 6 prior checkers are re-run live (never
trusting the go/no-go self-reported preconditions), the briefing structure
(creative principle markers, 8 creative-gate dimensions, 10 governance-gate
checks, 6 capability families, consumption rules, go/no-go semantics), readiness
all-false, forbidden-scope, P5 hash-hygiene immutability, and the ledger route
are all recomputed from the real repo. Manifest/decision self-reports are checked
for consistency but never taken as proof.

Fail-closed: refuses to run under `python -O` (asserts disabled) -> exit 2.

Codex Prompt-Pre-Review required notes baked in:
  note1: GO_TO_P7 is a brief-only unlock. generation_allowed / generation_eligible /
         generation_3600_executed must stay false; no real 07_microbatch_runs/3600
         generation dir; ledger P7 must not be DONE. (fail-closed otherwise)
  note2: go/no-go must state GO_TO_P7_does_not_mean = authorized_to_generate_3600.
  note3: Creative Score must not be a production/readiness condition and the Creative
         Gate must not replace/weaken the Governance Gate.
  note4: the 6 capability families are briefing_requirement_only and are NOT registered
         as ontology objects (allowed only under 07_microbatch_briefing/**).
  note5: P5 hash hygiene may only fill the recorded-hash placeholder; P5 facts
         (verdict/counts) must be unchanged.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

REPO_DEFAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASK_ID = "GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001"
BRIEF_REL = "07_microbatch_briefing"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
P5_RECEIPT_REL = "docs/reports/grc_canary_40_quality_closeout_and_proposition_pack_receipt.json"

BRIEFING_TASK = TASK_ID
THREE600_GEN_TASK = "GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001"
P5_TASK = "GKB-CANARY-40-QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001"
P5_SUPERSEDED = "GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001"
P5_COMMIT = "f71f4425b3f54458f5f65889ce9101d6ff66bb68"
HASH_PLACEHOLDER = "recorded_in_git_log_for_this_commit"

CAPABILITY_FAMILIES = ["AestheticFrame", "VisualScene", "StylingLogic",
                       "NarrativeBeat", "HumanVoice", "CreativePattern"]
CREATIVE_DIMENSIONS = ["visual_scene_quality", "apparel_detail_density", "real_scene_feeling",
                       "aesthetic_judgment", "narrative_beat", "human_voice_quality",
                       "platform_fit", "inspiration_and_actionability"]
CREATIVE_DIM_FIELDS = ["definition", "positive_signals", "negative_signals", "machine_proxy",
                       "human_review_note", "failure_code_if_missing", "applies_to_owner_types"]
GOVERNANCE_CHECKS = ["owner_routing_correct", "readiness_all_false", "no_real_instance_fact_leak",
                     "no_hard_claim_without_evidence_policy", "no_governance_text_in_domain_body",
                     "no_gold_body_surface_copy", "no_template_reuse",
                     "no_candidatepack_or_downstream_materialization", "no_KE_RAG_DIFY_touch",
                     "no_generation_allowed_true"]
GO_ALLOWED = {"GO_TO_P7", "NO_GO_FIX_REQUIRED", "HOLD_FOR_FOUNDER_DECISION"}
GO_PRECONDITIONS = ["p1_checker_live_pass", "p2_checker_live_pass", "p3_checker_live_pass",
                    "p4_checker_live_pass", "p5_checker_live_pass", "contract_lock_checker_live_pass",
                    "proposition_pack_v1_valid", "creative_content_principle_landed",
                    "creative_gate_landed", "governance_gate_landed", "p7_stop_conditions_landed",
                    "no_3600_generation_created", "readiness_flags_all_false",
                    "execution_progress_ledger_updated",
                    "no_unresolved_blocker_except_p7_execution_authorization"]
READINESS_MUST_BE_FALSE = ["candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready",
                           "generation_allowed", "generation_eligible", "production_ready",
                           "release_ready", "production_servable"]
REQUIRED_PRINCIPLE_MARKERS = [
    "笛语不是安全合规模型", "服装行业内容生产系统", "治理门", "Creative Gate",
    "只过治理门，不算好知识", "只过创意门", "compiler / judge / sidecar / route",
    "服装内容生产语言", "正文不得被治理话术污染",
]
FORBIDDEN_DIRS = ["KE", "serving_projection", "rag", "dify", "candidatepack_etl",
                  "CandidatePack", "RAG", "DIFY", "Serving"]
P5_IMMUTABLE_FACTS = {"verdict": "PASS", "total_proposition_count": 160, "cluster_count": 40,
                      "min_propositions_per_cluster": 4, "max_propositions_per_cluster": 4}

UNBLOCKED_STATES = {"NEXT", "IN_PROGRESS", "DONE"}


def _is_blocked(status):
    s = str(status or "")
    return "BLOCKED" in s or s.startswith("PLANNED_BLOCKED") or s in ("HOLD", "BLOCKED_OR_HOLD")


# ----------------------------- loaders (real repo, read-only) -----------------------------
def load_pack(ws):
    d = os.path.join(ws, BRIEF_REL)

    def y(name, key):
        return yaml.safe_load(open(os.path.join(d, name)))[key]

    principle = open(os.path.join(d, "creative_content_principle.v0.1.md"), encoding="utf-8").read()
    return {
        "principle_text": principle,
        "creative_gate": y("creative_gate_for_3600.v0.1.yaml", "creative_gate_for_3600"),
        "governance_gate": y("governance_gate_for_3600.v0.1.yaml", "governance_gate_for_3600"),
        "creative_score_rubric": y("creative_score_rubric.v0.1.yaml", "creative_score_rubric"),
        "capabilities": y("creative_production_capability_requirements.v0.1.yaml",
                          "creative_production_capability_requirements"),
        "consumption_plan": y("proposition_pack_consumption_plan.v0.1.yaml",
                              "proposition_pack_consumption_plan"),
        "go_no_go": y("p6_go_no_go_decision.v0.1.yaml", "p6_go_no_go_decision"),
        "manifest": y("microbatch_3600_briefing_manifest.v0.1.yaml", "microbatch_3600_briefing_manifest"),
    }


def load_ledger(ws):
    root = yaml.safe_load(open(os.path.join(ws, LEDGER_REL)))["grc_3600_execution_plan_status"]
    return {"steps": root.get("steps", []), "readiness": root.get("readiness", {}),
            "generation_unlocked": root.get("generation_unlocked")}


def load_p5_receipt(ws):
    p = os.path.join(ws, P5_RECEIPT_REL)
    if not os.path.isfile(p):
        return {}
    return json.load(open(p))


def scan_fs(ws):
    present = [d for d in FORBIDDEN_DIRS if os.path.isdir(os.path.join(ws, d))]
    three600 = bool(glob.glob(os.path.join(ws, "04_microbatch_generation", "*3600*")) +
                    glob.glob(os.path.join(ws, "*3600_generation*")) +
                    glob.glob(os.path.join(ws, "08_consolidated_outputs", "*3600*")))
    mb_runs = os.path.isdir(os.path.join(ws, "07_microbatch_runs"))
    cp = os.path.isdir(os.path.join(ws, "CandidatePack")) or \
        os.path.isdir(os.path.join(ws, "candidatepack_etl", "candidatepack_instances"))
    return {"forbidden_present": present, "three600_created": three600,
            "microbatch_runs_created": mb_runs, "candidatepack_created": cp}


# ----------------------------- pure validation core -----------------------------
def validate(pack, fs_state, ledger, p5_receipt):
    e = []
    pack = pack or {}
    fs_state = fs_state or {}
    ledger = ledger or {}
    steps = ledger.get("steps", [])

    # (7) creative_content_principle exists + required principles
    principle = pack.get("principle_text") or ""
    if not principle:
        e.append("creative_content_principle missing/empty")
    for m in REQUIRED_PRINCIPLE_MARKERS:
        if m not in principle:
            e.append(f"principle missing required marker: {m!r}")

    # (8)(9) creative gate: 8 dimensions each with required fields; (note3) does not replace governance
    cg = pack.get("creative_gate") or {}
    if not cg:
        e.append("creative_gate missing/empty")
    if cg.get("does_not_replace_governance_gate") is not True:
        e.append("creative_gate must set does_not_replace_governance_gate: true")
    if cg.get("does_not_weaken_governance_gate") is not True:
        e.append("creative_gate must set does_not_weaken_governance_gate: true")
    if cg.get("does_not_produce_production_readiness") is not True:
        e.append("creative_gate must set does_not_produce_production_readiness: true")
    dims = cg.get("dimensions") or []
    dim_names = [d.get("dimension") for d in dims]
    for want in CREATIVE_DIMENSIONS:
        if want not in dim_names:
            e.append(f"creative_gate missing dimension: {want}")
    if len(dims) != 8:
        e.append(f"creative_gate must have exactly 8 dimensions, got {len(dims)}")
    for d in dims:
        for fld in CREATIVE_DIM_FIELDS:
            if fld not in d:
                e.append(f"creative_gate dimension {d.get('dimension')!r} missing field {fld}")

    # (10) governance gate: required safety checks present + not weakened
    gg = pack.get("governance_gate") or {}
    if not gg:
        e.append("governance_gate missing/empty")
    if gg.get("not_weakened_by_creative_gate") is not True:
        e.append("governance_gate must set not_weakened_by_creative_gate: true")
    if gg.get("not_replaced_by_creative_gate") is not True:
        e.append("governance_gate must set not_replaced_by_creative_gate: true")
    gchecks = [c.get("check") for c in (gg.get("checks") or [])]
    for want in GOVERNANCE_CHECKS:
        if want not in gchecks:
            e.append(f"governance_gate missing check: {want}")

    # (note3) creative score rubric must not be production readiness / must not replace governance
    csr = pack.get("creative_score_rubric") or {}
    if csr.get("creative_score_used_as_production_readiness") is not False:
        e.append("creative_score_used_as_production_readiness must be false")
    if csr.get("creative_score_replaces_governance_gate") is not False:
        e.append("creative_score_replaces_governance_gate must be false")
    if csr.get("creative_score_can_override_governance_veto") is not False:
        e.append("creative_score_can_override_governance_veto must be false")

    # (11)(12)(13 + note4) capability families
    cap = pack.get("capabilities") or {}
    fams = cap.get("capability_families") or []
    fam_names = [f.get("family") for f in fams]
    for want in CAPABILITY_FAMILIES:
        if want not in fam_names:
            e.append(f"capability family missing: {want}")
    if len(fams) != 6:
        e.append(f"capability_families must be exactly 6, got {len(fams)}")
    gc = cap.get("global_constraint") or {}
    if gc.get("registered_as_ontology_object") is not False:
        e.append("capabilities global_constraint.registered_as_ontology_object must be false")
    for f in fams:
        if f.get("status") != "briefing_requirement_only":
            e.append(f"capability {f.get('family')!r} status must be briefing_requirement_only")
        if f.get("registered_as_ontology_object") is not False:
            e.append(f"capability {f.get('family')!r} registered_as_ontology_object must be false")

    # (14)(15)(16)(17) consumption plan
    cp = pack.get("consumption_plan") or {}
    if cp.get("proposition_pack_is_accepted_domain_knowledge") is not False:
        e.append("consumption_plan must mark proposition_pack_is_accepted_domain_knowledge false")
    if cp.get("proposition_pack_is_candidatepack_ready") is not False:
        e.append("consumption_plan must mark proposition_pack_is_candidatepack_ready false")
    if cp.get("proposition_pack_can_enter_KE_directly") is not False:
        e.append("consumption_plan must mark proposition_pack_can_enter_KE_directly false")
    rules = {r.get("owner_candidate"): r for r in (cp.get("owner_type_consumption_rules") or [])}
    if rules.get("SourceGapLedger", {}).get("used_as_positive_domain_fact") is not False:
        e.append("SourceGapLedger proposition must not be used as positive domain fact")
    if rules.get("GovernanceOutbox", {}).get("allowed_in_domain_body") is not False:
        e.append("GovernanceOutbox proposition must not be allowed in domain body")
    if rules.get("EvidencePolicyOutbox", {}).get("mapped_to_general_knowledge_base") is not False:
        e.append("EvidencePolicyOutbox proposition must not be mapped to GeneralKnowledgeBase")

    # (18)(19 + note1 + note2) go/no-go
    gng = pack.get("go_no_go") or {}
    gd = gng.get("go_decision") or {}
    val = gd.get("value")
    allowed_vals = set(gd.get("allowed_values") or [])
    if allowed_vals != GO_ALLOWED:
        e.append(f"go_decision allowed_values {sorted(allowed_vals)} != {sorted(GO_ALLOWED)}")
    if val not in GO_ALLOWED:
        e.append(f"go_decision value {val!r} not in allowed values")
    # note2
    if gng.get("GO_TO_P7_means") != "ready_to_prepare_or_submit_P7_execution_brief":
        e.append("go/no-go GO_TO_P7_means must be ready_to_prepare_or_submit_P7_execution_brief")
    if gng.get("GO_TO_P7_does_not_mean") != "authorized_to_generate_3600":
        e.append("go/no-go GO_TO_P7_does_not_mean must be authorized_to_generate_3600")
    # note1
    if gng.get("P7_unlocked_for_execution_brief_only") is not True:
        e.append("go/no-go P7_unlocked_for_execution_brief_only must be true")
    if gng.get("P7_real_generation_requires_separate_founder_authorization") is not True:
        e.append("go/no-go P7_real_generation_requires_separate_founder_authorization must be true")
    if gng.get("generation_allowed") is not False:
        e.append("go/no-go generation_allowed must be false")
    if gng.get("generation_eligible") is not False:
        e.append("go/no-go generation_eligible must be false")
    if gng.get("generation_3600_executed") is not False:
        e.append("go/no-go generation_3600_executed must be false")
    # (19) GO_TO_P7 requires all preconditions
    if val == "GO_TO_P7":
        pre = gng.get("preconditions_for_GO_TO_P7") or {}
        for k in GO_PRECONDITIONS:
            if pre.get(k) is not True:
                e.append(f"GO_TO_P7 precondition not satisfied: {k}")

    # (20)(21)(22) forbidden fs scope
    if fs_state.get("three600_created"):
        e.append("3600 generation directory exists (forbidden in P6)")
    if fs_state.get("microbatch_runs_created"):
        e.append("07_microbatch_runs directory created (forbidden in P6)")
    if fs_state.get("candidatepack_created"):
        e.append("CandidatePack path created (forbidden in P6)")
    if fs_state.get("forbidden_present"):
        e.append(f"forbidden dir(s) present/created: {fs_state['forbidden_present']}")

    # (23) readiness flags all false (manifest + ledger)
    manifest = pack.get("manifest") or {}
    rd = manifest.get("readiness") or {}
    for k in READINESS_MUST_BE_FALSE:
        if rd.get(k) is not False:
            e.append(f"manifest readiness {k} must be false")
    if rd.get("generation_3600_completed") is not False:
        e.append("manifest readiness generation_3600_completed must be false")
    if rd.get("generation_3600_unlocked") is not False:
        e.append("manifest readiness generation_3600_unlocked must be false")
    for k in ("external_resources_allowed", "embedding_allowed", "web_access_allowed",
              "source_repo_live_dependency", "google_drive_live_access"):
        if manifest.get(k) is not False:
            e.append(f"manifest {k} must be false")
    if manifest.get("ontology_object_count_added", 0) != 0:
        e.append("manifest ontology_object_count_added must be 0")
    # manifest go_decision must agree with go/no-go
    if manifest.get("go_decision") != val:
        e.append(f"manifest go_decision {manifest.get('go_decision')!r} != decision {val!r}")
    # ledger-level readiness
    lrd = ledger.get("readiness") or {}
    for k in ("candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "generation_allowed"):
        if lrd.get(k) is True:
            e.append(f"ledger readiness {k} must not be true")
    if ledger.get("generation_unlocked") is True:
        e.append("ledger generation_unlocked must not be true")

    # (24 + note5) P5 hash hygiene: facts immutable; head_after only placeholder or the P5 commit
    if p5_receipt:
        for k, want in P5_IMMUTABLE_FACTS.items():
            if p5_receipt.get(k) != want:
                e.append(f"P5 receipt fact altered: {k}={p5_receipt.get(k)!r} (expected {want!r})")
        ha = p5_receipt.get("head_after")
        if ha not in (HASH_PLACEHOLDER, P5_COMMIT):
            e.append(f"P5 hash hygiene: head_after {ha!r} is neither placeholder nor P5 commit")

    # (25) ledger route
    by_id = {s.get("step_id"): s for s in steps}
    by_task = {s.get("task_id"): s for s in steps}
    for st in ("P1", "P2", "P3", "P4", "P5"):
        if by_id.get(st, {}).get("status") != "DONE":
            e.append(f"ledger {st} status {by_id.get(st, {}).get('status')!r} != DONE")
    # P5 head_after hygiene in ledger too
    p5_ha = by_id.get("P5", {}).get("head_after")
    if p5_ha is not None and p5_ha not in (HASH_PLACEHOLDER, P5_COMMIT):
        e.append(f"ledger P5 head_after {p5_ha!r} is neither placeholder nor P5 commit")
    # P6 is this task; must be DONE (or its supersessor) once the pack is landed
    p6 = by_id.get("P6", {})
    if p6.get("task_id") != BRIEFING_TASK and p6.get("supersedes_task_id") != BRIEFING_TASK:
        e.append(f"ledger P6 task {p6.get('task_id')!r} is neither {BRIEFING_TASK} nor its supersessor")
    if p6.get("status") != "DONE":
        e.append(f"ledger P6 status {p6.get('status')!r} != DONE")
    # P7 = the 3600 generation task; route depends on decision (robust unblocked rule, not ==NEXT snapshot)
    p7 = by_id.get("P7", {})
    t3 = by_task.get(THREE600_GEN_TASK)
    if t3 is None:
        e.append(f"ledger: {THREE600_GEN_TASK} step missing")
    if p7.get("task_id") != THREE600_GEN_TASK and p7.get("supersedes_task_id") != THREE600_GEN_TASK:
        e.append(f"ledger P7 task {p7.get('task_id')!r} is neither {THREE600_GEN_TASK} nor its supersessor")
    # note1: 3600 generation must not be DONE (no generation executed/authorized in P6)
    if p7.get("status") == "DONE":
        e.append("ledger P7 (3600 generation) marked DONE — no 3600 generation is authorized/executed in P6")
    if val == "GO_TO_P7":
        if _is_blocked(p7.get("status")):
            e.append(f"go_decision GO_TO_P7 but ledger P7 still blocked ({p7.get('status')!r})")
        if p7.get("status") not in UNBLOCKED_STATES:
            e.append(f"go_decision GO_TO_P7 requires P7 unblocked (NEXT/advanced), got {p7.get('status')!r}")
    else:  # NO_GO_FIX_REQUIRED / HOLD_FOR_FOUNDER_DECISION
        if not _is_blocked(p7.get("status")):
            e.append(f"go_decision {val!r} requires ledger P7 blocked, got {p7.get('status')!r}")

    return e


# ----------------------------- live + selftest -----------------------------
def _run_prior(ws, rel, args):
    try:
        return subprocess.run([sys.executable, os.path.join(ws, rel)] + args, cwd=ws,
                              capture_output=True, text=True, timeout=300).returncode
    except Exception:
        return -1


def run_live(ws, report_out=None):
    pack = load_pack(ws)
    ledger = load_ledger(ws)
    p5_receipt = load_p5_receipt(ws)
    fs_state = scan_fs(ws)
    errors = validate(pack, fs_state, ledger, p5_receipt)
    prior = {
        "p1": _run_prior(ws, "ci/checkers/check_grc_corpus_registry.py", ["--live"]),
        "p2": _run_prior(ws, "ci/checkers/check_grc_contract_ontology_alignment.py", ["--live"]),
        "p3": _run_prior(ws, "ci/checkers/check_judge_calibration_against_grc.py", ["--live"]),
        "p4": _run_prior(ws, "ci/checkers/check_canary_40_generation_and_gate.py", ["--live"]),
        "p5": _run_prior(ws, "ci/checkers/check_canary_40_quality_closeout_and_proposition_pack.py", ["--live"]),
        "contract_lock": _run_prior(ws, "ci/checkers/check_codex_generation_contract_lock.py", []),
    }
    for name, rc in prior.items():
        if rc != 0:
            errors.append(f"prior checker {name} live not PASS (exit {rc})")
    gng = pack.get("go_no_go", {}).get("go_decision", {})
    status = "PASS" if not errors else "FAIL"
    report = {
        "status": status, "task_id": TASK_ID,
        "go_decision": gng.get("value"),
        "p7_unlocked_for_execution_brief_only": pack.get("go_no_go", {}).get("P7_unlocked_for_execution_brief_only"),
        "generation_3600_executed": pack.get("go_no_go", {}).get("generation_3600_executed"),
        "creative_gate_dimensions": len(pack.get("creative_gate", {}).get("dimensions", [])),
        "governance_gate_checks": len(pack.get("governance_gate", {}).get("checks", [])),
        "capability_families": len(pack.get("capabilities", {}).get("capability_families", [])),
        "readiness_all_false": not any("readiness" in x for x in errors),
        "prior_checkers": prior,
        "next_real_action_unlocked": THREE600_GEN_TASK + " (execution brief only; real generation needs separate founder authorization)",
        "error_count": len(errors), "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report_out:
        with open(report_out, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return 0 if status == "PASS" else 1


def run_selftest(ws, fixtures_dir):
    pos = os.path.join(fixtures_dir, "positive_valid_briefing.yaml")
    negatives = sorted(glob.glob(os.path.join(fixtures_dir, "negative_*.yaml")))
    result = {"status": "PASS", "positive_fixture_count": 0, "negative_fixture_count": len(negatives),
              "negative_fixtures_fail_closed": True, "positive_result": None, "negative_results": {}}

    def vfx(fx):
        return validate(fx.get("pack", {}), fx.get("fs_state", {}), fx.get("ledger", {}),
                        fx.get("p5_receipt", {}))

    try:
        fx = yaml.safe_load(open(pos))
        errs = vfx(fx)
        result["positive_fixture_count"] = 1
        result["positive_result"] = errs
        if errs:
            result["status"] = "FAIL"
    except Exception as ex:
        result["status"] = "FAIL"
        result["positive_result"] = [f"positive load error: {ex}"]

    for nf in negatives:
        name = os.path.basename(nf)
        try:
            fx = yaml.safe_load(open(nf))
            errs = vfx(fx)
            if not errs:
                result["negative_fixtures_fail_closed"] = False
                result["status"] = "FAIL"
                result["negative_results"][name] = ["DID NOT FAIL"]
            else:
                result["negative_results"][name] = errs[:3]
        except Exception as ex:
            result["negative_results"][name] = [f"malformed rejected (fail-closed): {ex.__class__.__name__}"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


def main():
    if not __debug__:
        print(json.dumps({"status": "FAIL-CLOSED", "reason": "python -O disables asserts; refuse"}))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL-CLOSED", "reason": "pyyaml unavailable"}))
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", default=REPO_DEFAULT)
    ap.add_argument("--fixtures-root", default="ci/fixtures/3600_microbatch_briefing_go_nogo")
    ap.add_argument("--report-out")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    ws = os.path.abspath(a.workspace_root)
    assert os.path.isdir(ws), "workspace root must exist"
    if a.selftest:
        return run_selftest(ws, os.path.join(ws, a.fixtures_root))
    if a.live:
        return run_live(ws, a.report_out)
    ap.error("one of --live / --selftest required")


if __name__ == "__main__":
    sys.exit(main())
