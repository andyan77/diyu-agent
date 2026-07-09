#!/usr/bin/env python3
"""
check_scoped_content_microbatch_brief_go_nogo.py  (P7C-BRIEF)

Independently gate the scoped-120 content-production microbatch brief + go/no-go.
This task generates NO draft; it plans 120 future assignments and decides GO/NO-GO for the
next (generation) task. Nothing here authorizes real generation.

Independent-recompute discipline (Codex Pre-Review notes 4 + 5):
  * REFERENCE EXISTENCE: every assignment's proposition_refs must exist in the P5 proposition
    pack; gold/anti-gold refs must exist in the goldset; creative_pattern_refs must exist in the
    P7B creative_pattern_requirements; generation_mode must exist in the P7B generation_mode
    contract; owner/cluster/p0_group must be real. No invented references pass.
  * RECOMPUTE (never trust the manifest): assignment count, cluster coverage (mkc_007..046, >=2
    each), per-mode counts (>=10 each), per-creative-pattern counts (>=10 each), P0-00/mkc_001..006
    absence from body assignments, per-mode fact-binding rules, readiness-all-false.
  * The 10 upstream checkers (P1..P6R, P7A, P7B, contract-lock) are RE-RUN, not assumed.

Route (founder chose the additive option): the committed P7A checker reads P7A(DONE)/P7(NEXT);
the committed P7B checker reads P7A(DONE)+classification / P7C(NEXT)/generation_authorized_by_
this_task=false. Neither is in this task's allowed writes. So those anchor steps are kept intact
and P7C-BRIEF (this task, DONE) + P7C-GEN (next, NEXT) are ADDED; P7D -> BLOCKED_BY_P7C_GEN.

Prior snapshots (Codex note 6): P6/P6R assert "no 07_microbatch_runs" -> run them (and P1..P5 +
contract-lock) in a pre-microbatch snapshot; P7A/P7B must see the proof + alignment but not this
task's in-flight files -> run them in a proof-present snapshot. No .git in either -> git-purity
trivially clean; ledger reset to HEAD. No whitelisting.

Fail-closed: refuses to run under `python -O` and without pyyaml.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

try:
    import yaml
except Exception:
    yaml = None

TASK_ID = "GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-BRIEF-AND-GO-NOGO-001"
GEN_TASK_ID = "GKB-SCOPED-120-CONTENT-PRODUCTION-MICROBATCH-GENERATION-001"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
SCOPE_DIR = "07_microbatch_briefing/scoped_content_microbatch_120"
ALIGN_DIR = "07_microbatch_briefing/generation_mode_cso_alignment"

REQUIRED_MODES = {"creative_prototype", "fact_slot_script", "evidence_bound_candidate", "display_solution"}
VALID_P0 = {"P0_01", "P0_02", "P0_03", "P0_04", "P0_05"}
VALID_CLUSTERS = [f"mkc_{i:03d}" for i in range(7, 47)]
CSO_FIELDS = {"narrative_rhythm", "emotional_temperature", "platform_native_expression", "role_voice",
              "aesthetic_framing", "creative_tension", "human_scene", "real_scene_feeling"}
GO_ALLOWED = {"GO_TO_SCOPED_120_GENERATION_BRIEF", "NO_GO_FIX_REQUIRED", "HOLD_FOR_FOUNDER_DECISION"}

REQUIRED_ASSIGNMENT_FIELDS = [
    "assignment_id", "target_output_id", "canonical_cluster_id", "p0_group", "generation_mode",
    "candidate_kind_target", "proposed_target_owner_target", "proposition_refs",
    "gold_reference_case_refs", "anti_gold_avoidance_refs", "creative_pattern_refs",
    "cso_overlay_requirements", "ontology_axis_constraints", "fact_binding_requirements",
    "governance_gate_refs", "creative_gate_refs", "expected_body_role", "forbidden_body_risks",
    "readiness_flags_required_false", "output_allowed_only_in_next_generation_task",
]

NOTE5_DOCS = ["manifest", "plan", "mode_dist", "p0_dist", "cso", "cpat", "fb",
              "go_no_go", "gate_req", "stop_cond", "next_contract", "brief"]

ALLOWED_WRITE_PREFIXES = (
    "07_microbatch_briefing/scoped_content_microbatch_120/",
    "ci/checkers/check_scoped_content_microbatch_brief_go_nogo.py",
    "ci/fixtures/scoped_content_microbatch_brief_go_nogo/",
    "ci/reports/scoped_content_microbatch_brief_go_nogo_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/grc_scoped_content_microbatch_brief_go_nogo_report.md",
    "docs/reports/grc_scoped_content_microbatch_brief_go_nogo_receipt.json",
)

NEW_FORBIDDEN_DIRS = [
    "KE", "serving_projection", "rag", "dify", "candidatepack_etl", "CandidatePack",
    "RAG", "DIFY", "08_consolidated_outputs", "09_candidatepack_eligibility",
    "07_microbatch_runs/microbatches", "07_microbatch_runs/batch_summaries",
]
READINESS_KEYS = ["candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "generation_allowed"]

PRIORS_SNAPSHOT_A = [
    ("p1", "ci/checkers/check_grc_corpus_registry.py", ["--live"]),
    ("p2", "ci/checkers/check_grc_contract_ontology_alignment.py", ["--live"]),
    ("p3", "ci/checkers/check_judge_calibration_against_grc.py", ["--live"]),
    ("p4", "ci/checkers/check_canary_40_generation_and_gate.py", ["--live"]),
    ("p5", "ci/checkers/check_canary_40_quality_closeout_and_proposition_pack.py", ["--live"]),
    ("p6", "ci/checkers/check_3600_microbatch_briefing_go_nogo.py", ["--live"]),
    ("p6r", "ci/checkers/check_grc_legacy_lock_retire_and_governed_unlock.py", ["--live"]),
    ("contract_lock", "ci/checkers/check_codex_generation_contract_lock.py", []),
]
PRIORS_SNAPSHOT_B = [
    ("p7a", "ci/checkers/check_generator_capability_proof_microbatch.py", ["--live"]),
    ("p7b", "ci/checkers/check_proof_microbatch_closeout_and_generation_mode_cso_alignment.py", ["--live"]),
]


# ----------------------------- validation core (pure) -----------------------------
def validate(docs, refs, ledger, fs_state, live):
    e = []

    def need(cond, msg):
        if not cond:
            e.append(msg)

    manifest = docs.get("manifest")
    plan = docs.get("plan")
    cso = docs.get("cso")
    cpat = docs.get("cpat")
    fb = docs.get("fb")
    gng = docs.get("go_no_go")

    valid_props = set(refs.get("valid_props") or [])
    valid_gold = set(refs.get("valid_gold") or [])
    valid_patterns = set(refs.get("valid_patterns") or [])
    valid_modes = set(refs.get("valid_modes") or [])
    valid_owners = set(refs.get("valid_owners") or [])

    # ref universe sanity (independent recompute must have real universes)
    need(REQUIRED_MODES <= valid_modes, "P7B generation_mode contract missing required modes")
    need(len(valid_props) >= 120, "P5 proposition universe too small / unloaded")
    need(len(valid_gold) >= 100, "goldset case universe too small / unloaded")
    need(len(valid_patterns) >= 6, "P7B creative pattern universe too small / unloaded")

    # (11-14) manifest
    if not manifest:
        e.append("scoped_120 manifest missing/unparsed")
    else:
        sm = manifest.get("scoped_microbatch") or {}
        need(sm.get("target_count") == 120, "manifest target_count must be 120")
        need(sm.get("generation_authorized_by_this_task") is False,
             "manifest generation_authorized_by_this_task must be false")
        need(sm.get("direct_3600_allowed") is False, "manifest direct_3600_allowed must be false")
        need(sm.get("max_count_without_new_authorization") == 120,
             "manifest max_count_without_new_authorization must be 120")
        need(sm.get("count_320_requires_new_founder_authorization") is True,
             "manifest count_320_requires_new_founder_authorization must be true")

    # (15-26, note 4) assignment plan recompute + reference existence
    assignments = (plan or {}).get("assignments") or []
    if len(assignments) != 120:
        e.append(f"assignment count must be 120, got {len(assignments)}")
    mode_counts = {}
    pat_counts = {}
    cluster_counts = {}
    for a in assignments:
        aid = a.get("assignment_id", "?")
        missing = [f for f in REQUIRED_ASSIGNMENT_FIELDS if f not in a]
        if missing:
            e.append(f"{aid}: missing fields {missing}")
        cl = a.get("canonical_cluster_id")
        p0 = a.get("p0_group")
        mode = a.get("generation_mode")
        if cl not in VALID_CLUSTERS:
            e.append(f"{aid}: cluster {cl!r} outside mkc_007..046 (P0-00/mkc_001..006 forbidden as body assignment)")
        if p0 not in VALID_P0:
            e.append(f"{aid}: p0_group {p0!r} not in P0_01..P0_05 (P0_00 forbidden as body assignment)")
        if mode not in valid_modes:
            e.append(f"{aid}: generation_mode {mode!r} not in P7B generation_mode contract")
        cluster_counts[cl] = cluster_counts.get(cl, 0) + 1
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        # reference existence (note 4)
        for pr in (a.get("proposition_refs") or []):
            if pr not in valid_props:
                e.append(f"{aid}: proposition_ref {pr!r} not in P5 pack")
        for gr in (a.get("gold_reference_case_refs") or []):
            if gr not in valid_gold:
                e.append(f"{aid}: gold_reference_case_ref {gr!r} not in goldset")
        for gr in (a.get("anti_gold_avoidance_refs") or []):
            if gr not in valid_gold:
                e.append(f"{aid}: anti_gold_avoidance_ref {gr!r} not in goldset")
        cprs = a.get("creative_pattern_refs") or []
        if not cprs:
            e.append(f"{aid}: must have >=1 creative_pattern_ref")
        for cp in cprs:
            if cp not in valid_patterns:
                e.append(f"{aid}: creative_pattern_ref {cp!r} not in P7B contract")
            pat_counts[cp] = pat_counts.get(cp, 0) + 1
        if a.get("proposed_target_owner_target") not in valid_owners:
            e.append(f"{aid}: owner {a.get('proposed_target_owner_target')!r} not a real P5 owner")
        # per-mode fact-binding rules (21-24)
        fbr = a.get("fact_binding_requirements") or {}
        if mode == "creative_prototype" and fbr.get("brand_facts_required") is not False:
            e.append(f"{aid}: creative_prototype must not require brand facts")
        if mode == "fact_slot_script" and "slot" not in str(fbr.get("missing_fact_behavior") or ""):
            e.append(f"{aid}: fact_slot_script missing facts must be slot behavior")
        if mode == "evidence_bound_candidate" and fbr.get("evidence_requirement") != "required":
            e.append(f"{aid}: evidence_bound_candidate must require evidence")
        if mode == "display_solution" and "scene_facts_required_for_final_execution" != fbr.get("evidence_requirement"):
            e.append(f"{aid}: display_solution must require scene facts for final execution")
        if a.get("output_allowed_only_in_next_generation_task") is not True:
            e.append(f"{aid}: output_allowed_only_in_next_generation_task must be true")
        rf = a.get("readiness_flags_required_false") or {}
        for k, v in rf.items():
            if v is not False:
                e.append(f"{aid}: readiness flag {k} must be required-false")

    # (17-18) cluster coverage
    if set(cluster_counts) != set(VALID_CLUSTERS):
        e.append("assignments must cover exactly mkc_007..mkc_046")
    under2 = [c for c, n in cluster_counts.items() if n < 2]
    if under2:
        e.append(f"clusters with <2 assignments: {sorted(under2)}")
    # (20) mode >=10 + all present
    if set(mode_counts) != REQUIRED_MODES:
        e.append(f"modes present {sorted(mode_counts)} != required {sorted(REQUIRED_MODES)}")
    for m, n in mode_counts.items():
        if n < 10:
            e.append(f"generation_mode {m} has <10 assignments ({n})")
    # (26) pattern >=10
    for p, n in pat_counts.items():
        if n < 10:
            e.append(f"creative_pattern {p} used <10 times ({n})")
    if len(pat_counts) < 6:
        e.append(f"fewer than 6 creative pattern families used ({len(pat_counts)})")

    # (27-28) CSO overlay
    if not cso:
        e.append("cso_overlay_plan missing/unparsed")
    else:
        if not (CSO_FIELDS <= set(cso.get("cso_fields") or [])):
            e.append("cso_overlay_plan missing required CSO fields")
        if cso.get("cso_written_to_ontology_truth") is not False:
            e.append("cso_written_to_ontology_truth must be false")
        if cso.get("cso_may_make_evidence_bound_fabricate") is not False:
            e.append("cso must not let evidence_bound fabricate")

    # (29) BrandKB interface only
    bk = (fb or {}).get("BrandKB_slot_contract") or {}
    if bk.get("creates_BrandKB_instance") is not False:
        e.append("fact_binding BrandKB_slot_contract.creates_BrandKB_instance must be false")
    if (fb or {}).get("no_fact_does_not_block_creative_generation") is not True:
        e.append("fact_binding no_fact_does_not_block_creative_generation must be true")

    # (35, note 3) go/no-go
    if not gng:
        e.append("go_no_go_decision missing/unparsed")
    else:
        dec = gng.get("decision")
        if dec not in GO_ALLOWED:
            e.append(f"go/no-go decision {dec!r} not in allowed values")
        gm = gng.get("GO_meaning") or {}
        if gm.get("next_unlocked") != "P7C_GEN_execution_brief_and_founder_authorization_only":
            e.append("go/no-go next_unlocked must be P7C_GEN_execution_brief_and_founder_authorization_only (note 3)")
        if gm.get("generation_authorized_now") is not False:
            e.append("go/no-go generation_authorized_now must be false (note 3)")

    # (note 5) briefing_orchestration_contract on every file
    for key in NOTE5_DOCS:
        d = docs.get(key)
        if not d:
            continue
        if d.get("contract_status") != "briefing_orchestration_contract":
            e.append(f"{key}.contract_status must be briefing_orchestration_contract (note 5)")
        if d.get("formal_schema_contract") is not False:
            e.append(f"{key}.formal_schema_contract must be false (note 5)")
        if d.get("ontology_truth_source") is not False:
            e.append(f"{key}.ontology_truth_source must be false (note 5)")

    # (30-33) filesystem: no new draft / no 3600 manifest / no forbidden materialization
    if fs_state.get("forbidden_present"):
        e.append(f"forbidden dirs present: {fs_state['forbidden_present']}")
    if fs_state.get("run_manifest_present"):
        e.append("3600 run_manifest / microbatch_index created (forbidden)")
    if fs_state.get("microbatches_present"):
        e.append("microbatches / batch_summaries created (forbidden)")
    if fs_state.get("three600_present"):
        e.append("*3600* generation dir created (forbidden)")
    pd = fs_state.get("proof_run_dirs")
    if pd is not None and set(pd) != {"proof_microbatch_001"}:
        e.append(f"unexpected new microbatch run dirs (no new draft allowed): {pd}")

    # (34) readiness all false
    led_rd = ledger.get("readiness") or {}
    for k in READINESS_KEYS:
        if led_rd.get(k) is not False:
            e.append(f"ledger readiness {k} must be false")
    if led_rd.get("readiness_all_false") is not True:
        e.append("ledger readiness_all_false must be true")
    if ledger.get("generation_unlocked") is not False:
        e.append("ledger generation_unlocked must be false")

    # (36) ledger route: anchors intact + P7C-BRIEF/P7C-GEN added + P7D->P7C_GEN + route_migration_2
    by = {s.get("step_id"): s for s in (ledger.get("steps") or [])}
    for sid in ["P1", "P2", "P3", "P4", "P5", "P6", "P6R"]:
        if (by.get(sid) or {}).get("status") != "DONE":
            e.append(f"ledger {sid} must be DONE")
    if (by.get("P7A") or {}).get("status") != "DONE":
        e.append("ledger P7A must stay DONE (committed-checker anchor)")
    if (by.get("P7A") or {}).get("classification") != "agent_authored_quality_probe_pass":
        e.append("ledger P7A.classification must stay agent_authored_quality_probe_pass")
    if (by.get("P7B") or {}).get("status") != "DONE":
        e.append("ledger P7B must stay DONE")
    p7c = by.get("P7C") or {}
    if p7c.get("status") not in ("NEXT", "IN_PROGRESS"):
        e.append("ledger P7C (anchor) must stay NEXT (committed P7B checker reads it)")
    if p7c.get("generation_authorized_by_this_task") is not False:
        e.append("ledger P7C.generation_authorized_by_this_task must stay false")
    pcb = by.get("P7C-BRIEF") or {}
    if pcb.get("status") != "DONE":
        e.append(f"ledger P7C-BRIEF must be DONE, got {pcb.get('status')!r}")
    if pcb.get("task_id") != TASK_ID:
        e.append("ledger P7C-BRIEF task_id must be this task")
    pcg = by.get("P7C-GEN") or {}
    if pcg.get("status") not in ("NEXT", "IN_PROGRESS"):
        e.append(f"ledger P7C-GEN must be NEXT, got {pcg.get('status')!r}")
    if pcg.get("task_id") != GEN_TASK_ID:
        e.append("ledger P7C-GEN task_id must be the generation task")
    if pcg.get("generation_authorized_by_this_task") is not False:
        e.append("ledger P7C-GEN.generation_authorized_by_this_task must be false")
    p7d = by.get("P7D") or {}
    if "BLOCKED" not in str(p7d.get("status") or "").upper():
        e.append(f"ledger P7D must be blocked, got {p7d.get('status')!r}")
    if "P7C_GEN" not in str(p7d.get("status") or "").upper().replace("-", "_"):
        e.append("ledger P7D must be blocked by P7C-GEN")
    if "BLOCKED" not in str((by.get("P8") or {}).get("status") or "").upper():
        e.append("ledger P8 must stay blocked")
    rm2 = ledger.get("route_migration_2") or {}
    if not rm2:
        e.append("ledger route_migration_2 block missing (additive P7C-BRIEF/P7C-GEN extension)")
    else:
        if rm2.get("no_old_checker_edited") is not True:
            e.append("route_migration_2.no_old_checker_edited must be true")
        if rm2.get("no_readiness_flipped") is not True:
            e.append("route_migration_2.no_readiness_flipped must be true")

    # (J) git surface + priors
    if live.get("git_changed_outside_allowed"):
        e.append(f"git changes outside allowed write surface: {live['git_changed_outside_allowed']}")
    if live.get("forbidden_touched"):
        e.append(f"forbidden path touched: {live['forbidden_touched']}")
    if live.get("committed_artifacts_modified"):
        e.append(f"committed P7A/P7B artifacts modified: {live['committed_artifacts_modified']}")
    for name, rc in (live.get("prior_checkers") or {}).items():
        if rc != 0:
            e.append(f"prior checker {name} not PASS (exit {rc})")

    return e


# ----------------------------- loading (live) -----------------------------
def _load_top(ws, rel):
    p = os.path.join(ws, rel)
    if not os.path.exists(p):
        return None
    d = yaml.safe_load(open(p))
    if not isinstance(d, dict) or not d:
        return None
    return d[list(d.keys())[0]]


def load_docs(ws):
    def s(name):
        return _load_top(ws, f"{SCOPE_DIR}/{name}")
    return {
        "manifest": s("scoped_120_microbatch_manifest.v0.1.yaml"),
        "plan": s("scoped_120_assignment_plan.v0.1.yaml"),
        "mode_dist": s("scoped_120_generation_mode_distribution.v0.1.yaml"),
        "p0_dist": s("scoped_120_p0_group_distribution.v0.1.yaml"),
        "cso": s("scoped_120_cso_overlay_plan.v0.1.yaml"),
        "cpat": s("scoped_120_creative_pattern_assignment.v0.1.yaml"),
        "fb": s("scoped_120_fact_binding_assignment.v0.1.yaml"),
        "go_no_go": s("scoped_120_go_no_go_decision.v0.1.yaml"),
        "gate_req": s("scoped_120_gate_requirements.v0.1.yaml"),
        "stop_cond": s("scoped_120_stop_conditions.v0.1.yaml"),
        "next_contract": s("scoped_120_next_execution_contract.v0.1.yaml"),
        "brief": s("scoped_120_generation_brief.v0.1.yaml"),
    }


def load_refs(ws):
    # valid propositions + owners from P5 pack
    valid_props, valid_owners = set(), set()
    pp = _load_top(ws, "06_canary_runs/canary_40_001/proposition_pack_v1/cluster_propositions.v0.1.yaml")
    for cl, plist in ((pp or {}).get("clusters") or {}).items():
        for p in plist:
            valid_props.add(p.get("proposition_id"))
            if p.get("owner_candidate"):
                valid_owners.add(p.get("owner_candidate"))
    # valid gold case ids
    valid_gold = set()
    for f in glob.glob(os.path.join(ws, "03_grc_goldset_corpus/normalized/formal_120/p0_0*/gold_reference_cases.yaml")):
        d = yaml.safe_load(open(f))
        cases = d if isinstance(d, list) else (d[list(d.keys())[0]] if isinstance(d, dict) else [])
        if isinstance(cases, dict):
            cases = next((v for v in cases.values() if isinstance(v, list)), [])
        for c in cases:
            if isinstance(c, dict) and c.get("case_id"):
                valid_gold.add(c["case_id"])
    # valid patterns + modes from P7B contracts
    cpr = _load_top(ws, f"{ALIGN_DIR}/creative_pattern_requirements.v0.1.yaml")
    valid_patterns = set(((cpr or {}).get("creative_patterns") or {}).keys())
    gmc = _load_top(ws, f"{ALIGN_DIR}/generation_mode_contract.v0.1.yaml")
    valid_modes = set(((gmc or {}).get("generation_modes") or {}).keys())
    return {"valid_props": sorted(valid_props), "valid_gold": sorted(valid_gold),
            "valid_patterns": sorted(valid_patterns), "valid_modes": sorted(valid_modes),
            "valid_owners": sorted(valid_owners)}


def load_ledger(ws):
    return yaml.safe_load(open(os.path.join(ws, LEDGER_REL)))["grc_3600_execution_plan_status"]


def _git_changed(ws):
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                             cwd=ws, capture_output=True, text=True).stdout
    except Exception:
        return []
    changed = []
    for ln in out.splitlines():
        if ln.strip():
            p = ln[3:].strip().strip('"')
            if " -> " in p:
                p = p.split(" -> ", 1)[1]
            changed.append(p)
    return changed


def compute_live(ws, priors):
    changed = _git_changed(ws)
    outside = [p for p in changed if not p.startswith(ALLOWED_WRITE_PREFIXES)]
    forbidden = [p for p in changed if any(p.startswith(d + "/") or p == d for d in NEW_FORBIDDEN_DIRS)]
    committed = [p for p in changed if p.startswith("07_microbatch_runs/proof_microbatch_001/")
                 or p.startswith(ALIGN_DIR + "/")
                 or p.startswith("ci/checkers/check_generator_capability_proof_microbatch.py")
                 or p.startswith("ci/checkers/check_proof_microbatch_closeout_and_generation_mode_cso_alignment.py")]
    return {"git_changed": changed, "git_changed_outside_allowed": outside,
            "forbidden_touched": forbidden, "committed_artifacts_modified": committed,
            "prior_checkers": priors}


def scan_fs(ws):
    present = [d for d in NEW_FORBIDDEN_DIRS if os.path.isdir(os.path.join(ws, d))]
    run_manifest = bool(glob.glob(os.path.join(ws, "07_microbatch_runs", "run_manifest*")) +
                        glob.glob(os.path.join(ws, "07_microbatch_runs", "microbatch_index*")))
    three600 = bool(glob.glob(os.path.join(ws, "04_microbatch_generation", "*3600*")) +
                    glob.glob(os.path.join(ws, "07_microbatch_runs", "*3600*")))
    micro = any(os.path.isdir(os.path.join(ws, d))
                for d in ["07_microbatch_runs/microbatches", "07_microbatch_runs/batch_summaries"])
    runs = os.path.join(ws, "07_microbatch_runs")
    proof_run_dirs = [d for d in os.listdir(runs) if os.path.isdir(os.path.join(runs, d))] if os.path.isdir(runs) else []
    return {"forbidden_present": present, "run_manifest_present": run_manifest,
            "microbatches_present": micro, "three600_present": three600, "proof_run_dirs": proof_run_dirs}


# ----------------------------- snapshot prior runner -----------------------------
def _build_snapshot(ws, extra_excludes):
    import shutil
    snap = tempfile.mkdtemp(prefix="p7c_snap_")
    excludes = ["--exclude=.git"] + [f"--exclude={p}" for p in extra_excludes]
    rs = subprocess.run(["rsync", "-a"] + excludes + [ws.rstrip("/") + "/", snap + "/"],
                        capture_output=True, text=True)
    if rs.returncode != 0:
        subprocess.run(["cp", "-a", ws.rstrip("/") + "/.", snap], capture_output=True, text=True)
    for rel in [".git"] + extra_excludes:
        p = os.path.join(snap, rel)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p):
            os.remove(p)
    for rel in ["10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
                "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"]:
        h = subprocess.run(["git", "-C", ws, "show", "HEAD:" + rel], capture_output=True, text=True)
        if h.returncode == 0:
            os.makedirs(os.path.dirname(os.path.join(snap, rel)), exist_ok=True)
            with open(os.path.join(snap, rel), "w") as f:
                f.write(h.stdout)
    return snap


def run_priors(ws):
    import shutil
    results = {}
    this_task = [
        SCOPE_DIR,
        "ci/checkers/check_scoped_content_microbatch_brief_go_nogo.py",
        "ci/fixtures/scoped_content_microbatch_brief_go_nogo",
        "ci/reports/scoped_content_microbatch_brief_go_nogo_report.v0.1.json",
        "docs/reports/grc_scoped_content_microbatch_brief_go_nogo_report.md",
        "docs/reports/grc_scoped_content_microbatch_brief_go_nogo_receipt.json",
    ]
    # snapshot A: no 07_microbatch_runs (P6/P6R phase invariant) -> P1..P6R + contract-lock
    snap_a = _build_snapshot(ws, ["07_microbatch_runs"] + this_task[1:])
    try:
        for name, rel, args in PRIORS_SNAPSHOT_A:
            chk = os.path.join(snap_a, rel)
            results[name] = 98 if not os.path.exists(chk) else subprocess.run(
                [sys.executable, chk] + args, cwd=snap_a, capture_output=True, text=True).returncode
    finally:
        shutil.rmtree(snap_a, ignore_errors=True)
    # snapshot B: keep proof + P7B alignment, drop only this task's files -> P7A + P7B
    snap_b = _build_snapshot(ws, this_task)
    try:
        for name, rel, args in PRIORS_SNAPSHOT_B:
            chk = os.path.join(snap_b, rel)
            results[name] = 98 if not os.path.exists(chk) else subprocess.run(
                [sys.executable, chk] + args, cwd=snap_b, capture_output=True, text=True).returncode
    finally:
        shutil.rmtree(snap_b, ignore_errors=True)
    return results


# ----------------------------- live / selftest -----------------------------
def run_live(ws, report_out=None):
    docs = load_docs(ws)
    refs = load_refs(ws)
    ledger = load_ledger(ws)
    fs_state = scan_fs(ws)
    live = compute_live(ws, run_priors(ws))
    errors = validate(docs, refs, ledger, fs_state, live)
    status = "PASS" if not errors else "FAIL"
    plan = docs.get("plan") or {}
    report = {
        "checker": "check_scoped_content_microbatch_brief_go_nogo.py", "task_id": TASK_ID, "step_id": "P7C-BRIEF",
        "status": status, "error_count": len(errors), "errors": errors[:60],
        "assignment_count": len((plan.get("assignments") or [])),
        "go_no_go": (docs.get("go_no_go") or {}).get("decision"),
        "git_changed_outside_allowed": live.get("git_changed_outside_allowed"),
        "committed_artifacts_modified": live.get("committed_artifacts_modified"),
        "prior_checkers": live.get("prior_checkers"),
    }
    if report_out:
        json.dump(report, open(report_out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def selftest(ws):
    fx = os.path.join(ws, "ci/fixtures/scoped_content_microbatch_brief_go_nogo")
    pos = os.path.join(fx, "positive_valid.yaml")
    if not os.path.exists(pos):
        print(json.dumps({"status": "FAIL", "reason": "positive fixture missing"}))
        return 1

    def _run(f):
        return validate(f["docs"], f["refs"], f["ledger"], f["fs_state"], f["live"])

    pos_err = _run(yaml.safe_load(open(pos)))
    if pos_err:
        print(json.dumps({"status": "FAIL", "reason": "positive did not pass", "errors": pos_err[:20]}, ensure_ascii=False))
        return 1
    negatives = sorted(glob.glob(os.path.join(fx, "negative_*.yaml")))
    wrong = []
    for nf in negatives:
        try:
            errs = _run(yaml.safe_load(open(nf)))
        except Exception as ex:
            errs = [f"malformed: {ex}"]
        if not errs:
            wrong.append(os.path.basename(nf))
    status = "PASS" if not wrong else "FAIL"
    print(json.dumps({"status": status, "negative_count": len(negatives),
                      "negatives_that_wrongly_passed": wrong, "positive_ok": True}, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def main():
    if not __debug__:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "refuses to run under python -O (asserts disabled)"}))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "pyyaml unavailable"}))
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report-out", default=None)
    ap.add_argument("--workspace-root", default=".")
    a = ap.parse_args()
    ws = os.path.abspath(a.workspace_root)
    if a.selftest:
        return selftest(ws)
    if a.live:
        return run_live(ws, a.report_out)
    ap.error("one of --live / --selftest required")


if __name__ == "__main__":
    sys.exit(main())
