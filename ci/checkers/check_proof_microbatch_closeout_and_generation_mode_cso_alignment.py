#!/usr/bin/env python3
"""
check_proof_microbatch_closeout_and_generation_mode_cso_alignment.py  (P7B)

Independently gate the P7A proof-microbatch closeout + the generation_mode / fact_binding
/ Ontology-x-CSO composition alignment layer. This task generates NO new draft, no 3600,
no CandidatePack/KE/RAG/DIFY, and flips no readiness flag.

Independent-recompute discipline (never trust self-reports):
  * All content invariants (four generation modes, fact-binding rules, Ontology-x-CSO
    relationship, >=6 creative patterns, P0_00 control-plane, P7C brief-only scale) are
    recomputed from the files themselves.
  * The 9 upstream checkers (P1..P6R, contract-lock, P7A proof) are RE-RUN, not assumed.
  * Codex Pre-Review required notes are enforced as hard checks:
      note 1/2 (route-sync, option a): the committed P7A checker hard-reads step_id P7A
        (status DONE) and step_id P7 (status NEXT / governed_incremental / gen_allowed=false);
        that checker is NOT in this task's allowed writes, so P7A/P7 step fields are kept
        backward-compatible and P7B/P7C/P7D are ADDED. This checker asserts the old fields
        are intact AND the new route + a route_migration block are present.
      note 3: P7C unlock is brief/go-no-go only (generation_authorized_by_this_task=false).
      note 4: scale default 120, 320 requires separate founder authorization.
      note 5: these are briefing_orchestration_contracts (formal_schema_contract=false,
        ontology_truth_source=false), not 01_generation_contracts formal schema.
      note 6: P7A original artifacts are immutable (only closeout/** may be written).

Why the 9 priors run in SNAPSHOTS, not live:
  * P6/P6R assert the phase invariant "07_microbatch_runs must not exist"; P7A legitimately
    created it, so they cannot pass on the live tree -> run them in a pre-microbatch snapshot
    (working-tree copy minus .git, minus 07_microbatch_runs and this task's new briefing subdir,
    ledger reset to HEAD) = exactly the state they validated at their own commits.
  * The P7A proof checker must SEE the proof (07_microbatch_runs/proof_microbatch_001) to
    validate the 40 drafts, but must NOT see this task's uncommitted files -> run it in a
    second snapshot that keeps the proof but drops this task's deliverables, no .git.
  No whitelisting: each prior passes outright on the exact tree it was designed for.

Fail-closed: refuses to run under `python -O` (asserts disabled) and without pyyaml.
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

TASK_ID = "GKB-PROOF-MICROBATCH-CLOSEOUT-AND-GENERATION-MODE-CSO-ALIGNMENT-001"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"

CLOSEOUT_DIR = "07_microbatch_runs/proof_microbatch_001/closeout"
ALIGN_DIR = "07_microbatch_briefing/generation_mode_cso_alignment"

REQUIRED_MODES = {"creative_prototype", "fact_slot_script", "evidence_bound_candidate", "display_solution"}
REQUIRED_P0 = ["P0_00", "P0_01", "P0_02", "P0_03", "P0_04", "P0_05"]

# Codex note 5 applies to every briefing/closeout contract file (by docs key).
NOTE5_DOCS = ["identity", "not_3600", "closeout", "gen_mode", "fact_binding",
              "cso_comp", "creative_pat", "p0_matrix", "p7c_plan", "p7d"]

ALLOWED_WRITE_PREFIXES = (
    "07_microbatch_runs/proof_microbatch_001/closeout/",
    "07_microbatch_briefing/generation_mode_cso_alignment/",
    "ci/checkers/check_proof_microbatch_closeout_and_generation_mode_cso_alignment.py",
    "ci/fixtures/proof_microbatch_closeout_and_generation_mode_cso_alignment/",
    "ci/reports/proof_microbatch_closeout_and_generation_mode_cso_alignment_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/grc_proof_microbatch_closeout_and_generation_mode_cso_alignment_report.md",
    "docs/reports/grc_proof_microbatch_closeout_and_generation_mode_cso_alignment_receipt.json",
)

PROOF_ROOT = "07_microbatch_runs/proof_microbatch_001/"
PROOF_CLOSEOUT_ROOT = "07_microbatch_runs/proof_microbatch_001/closeout/"

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
PRIOR_P7A = ("p7a", "ci/checkers/check_generator_capability_proof_microbatch.py", ["--live"])


# ----------------------------- validation core (pure) -----------------------------
def validate(docs, ledger, fs_state, live):
    e = []

    def need(cond, msg):
        if not cond:
            e.append(msg)

    identity = docs.get("identity")
    not_3600 = docs.get("not_3600")
    gen = docs.get("gen_mode")
    fb = docs.get("fact_binding")
    cso = docs.get("cso_comp")
    cpat = docs.get("creative_pat")
    p0 = docs.get("p0_matrix")
    p7c = docs.get("p7c_plan")

    # (10-14, note 6) P7A closeout identity decision
    if not identity:
        e.append("P7A closeout identity_decision missing/unparsed")
    else:
        need(identity.get("agent_authored_quality_probe_pass") is True,
             "identity_decision.agent_authored_quality_probe_pass must be true")
        gca = identity.get("generator_capability_assessment") or {}
        need(gca.get("automatic_generator_capability_proven") is False,
             "identity_decision.automatic_generator_capability_proven must be false")
        need(gca.get("direct_3600_unlocked") is False,
             "identity_decision.direct_3600_unlocked must be false")
        pmi = identity.get("proof_microbatch_identity") or {}
        need(pmi.get("counts_toward_3600") is False,
             "identity_decision.counts_toward_3600 must be false")
        need(pmi.get("accepted_domain_knowledge") is False,
             "identity_decision.accepted_domain_knowledge must be false")
        need(identity.get("P7A_original_artifacts_modified") is False,
             "identity_decision.P7A_original_artifacts_modified must be false (note 6)")

    # not-3600-unlock decision
    if not not_3600:
        e.append("not_3600_unlock_decision missing/unparsed")
    else:
        dec = not_3600.get("decision") or {}
        need(dec.get("proof_microbatch_counts_toward_3600") is False,
             "not_3600.proof_microbatch_counts_toward_3600 must be false")
        need(dec.get("direct_3600_unlocked") is False,
             "not_3600.direct_3600_unlocked must be false")

    # (15-19) generation_mode_contract: exactly 4 modes + per-mode semantics
    if not gen:
        e.append("generation_mode_contract missing/unparsed")
    else:
        modes = gen.get("generation_modes") or {}
        if set(modes.keys()) != REQUIRED_MODES:
            e.append(f"generation_mode_contract must define exactly {sorted(REQUIRED_MODES)}, got {sorted(modes.keys())}")
        cp = modes.get("creative_prototype") or {}
        need(cp.get("allowed_without_brand_facts") is True,
             "creative_prototype.allowed_without_brand_facts must be true (must not require brand facts)")
        need(cp.get("required_fact_binding") == "none",
             "creative_prototype.required_fact_binding must be none")
        fss = modes.get("fact_slot_script") or {}
        need(fss.get("missing_facts_must_be_slots") is True,
             "fact_slot_script.missing_facts_must_be_slots must be true")
        need("fill_missing_fact_with_invention" in (fss.get("forbidden_fabrication") or []),
             "fact_slot_script must forbid fill_missing_fact_with_invention")
        ebc = modes.get("evidence_bound_candidate") or {}
        need(ebc.get("fact_evidence_required") is True,
             "evidence_bound_candidate.fact_evidence_required must be true")
        need(ebc.get("required_fact_binding") == "required",
             "evidence_bound_candidate.required_fact_binding must be required")
        ds = modes.get("display_solution") or {}
        need(ds.get("general_method_allowed_first") is True,
             "display_solution.general_method_allowed_first must be true")
        need(ds.get("scene_fact_required_for_final_execution") is True,
             "display_solution.scene_fact_required_for_final_execution must be true")

    # (20-21) fact_binding_policy
    if not fb:
        e.append("fact_binding_policy missing/unparsed")
    else:
        core = fb.get("core_principles") or {}
        need(core.get("no_fact_does_not_block_creative_generation") is True,
             "fact_binding_policy.no_fact_does_not_block_creative_generation must be true")
        bk = fb.get("BrandKB_slot_contract") or {}
        need(bk.get("status") == "interface_boundary_only",
             "fact_binding_policy.BrandKB_slot_contract.status must be interface_boundary_only")
        need(bk.get("creates_BrandKB_instance") is False,
             "fact_binding_policy.BrandKB_slot_contract.creates_BrandKB_instance must be false")

    # (22-23) ontology_cso_composition_contract
    if not cso:
        e.append("ontology_cso_composition_contract missing/unparsed")
    else:
        rel = cso.get("relationship") or {}
        need(rel.get("conceptual_model") == "orthogonal_cross_cutting",
             "ontology_cso relationship.conceptual_model must be orthogonal_cross_cutting")
        need(rel.get("runtime_model") == "compositional_overlay",
             "ontology_cso relationship.runtime_model must be compositional_overlay")
        need(cso.get("cso_written_to_ontology_truth") is False,
             "ontology_cso cso_written_to_ontology_truth must be false")
        need(cso.get("cso_fields_forbidden_in_abox") is True,
             "ontology_cso cso_fields_forbidden_in_abox must be true")

    # (24) creative_pattern_requirements: >=6 families
    if not cpat:
        e.append("creative_pattern_requirements missing/unparsed")
    else:
        fams = cpat.get("creative_patterns") or {}
        if len(fams) < 6:
            e.append(f"creative_pattern_requirements must cover >=6 pattern families, got {len(fams)}")

    # (25-26) p0_generation_mode_matrix
    if not p0:
        e.append("p0_generation_mode_matrix missing/unparsed")
    else:
        groups = p0.get("p0_groups") or {}
        for g in REQUIRED_P0:
            if g not in groups:
                e.append(f"p0_generation_mode_matrix missing {g}")
        p000 = groups.get("P0_00") or {}
        need(p000.get("role") == "route_and_generation_mode_decision",
             "P0_00.role must be route_and_generation_mode_decision")
        need(p000.get("enters_gkb_body_generation") is False,
             "P0_00 must not enter GKB body generation")

    # (27, notes 3+4) p7c route plan: scoped brief-only, scale 120 default, not direct 3600
    if not p7c:
        e.append("p7c_scoped_microbatch_route_plan missing/unparsed")
    else:
        blk = p7c.get("P7C") or {}
        rc = blk.get("recommended_count") or {}
        need(120 in (rc.get("allowed_values") or []) and 320 in (rc.get("allowed_values") or []),
             "P7C.recommended_count.allowed_values must include 120 and 320")
        need(rc.get("default_recommendation") == 120, "P7C default_recommendation must be 120")
        need(rc.get("max_without_additional_founder_decision") == 120,
             "P7C max_without_additional_founder_decision must be 120 (note 4)")
        need(rc.get("320_requires_separate_founder_authorization") is True,
             "P7C 320_requires_separate_founder_authorization must be true (note 4)")
        need(blk.get("next_unlocked") == "P7C_execution_brief_and_go_nogo_only",
             "P7C.next_unlocked must be P7C_execution_brief_and_go_nogo_only (note 3)")
        need(blk.get("generation_authorized_by_this_task") is False,
             "P7C.generation_authorized_by_this_task must be false (note 3)")
        need(blk.get("directly_unlocks_3600") is False,
             "P7C must not directly unlock 3600")
        pd = p7c.get("P7D") or {}
        need("BLOCKED" in str(pd.get("status") or "").upper(),
             "P7D must be blocked by P7C")

    # (note 5) every briefing/closeout contract is briefing_orchestration only, not formal schema
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

    # (28-30) filesystem: no new draft, no 3600 run manifest, no forbidden materialization
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
    if fs_state.get("proof_candidate_count") not in (None, 40):
        e.append(f"proof candidate_count changed from 40 to {fs_state.get('proof_candidate_count')} (no new/edited draft allowed)")

    # (31) readiness all false (ledger authoritative + closeout mirror)
    led_rd = ledger.get("readiness") or {}
    for k in READINESS_KEYS:
        if led_rd.get(k) is not False:
            e.append(f"ledger readiness {k} must be false")
    if led_rd.get("readiness_all_false") is not True:
        e.append("ledger readiness_all_false must be true")
    if ledger.get("generation_unlocked") is not False:
        e.append("ledger generation_unlocked must be false")
    co = docs.get("closeout") or {}
    co_rd = co.get("readiness") or {}
    for k in ("candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "production_ready",
              "generation_allowed", "generation_eligible", "production_servable", "release_ready"):
        if co_rd and co_rd.get(k) is not False:
            e.append(f"closeout readiness {k} must be false")

    # (32, notes 1+2) ledger route: old anchors intact + new P7B/P7C/P7D added + route_migration
    by_id = {s.get("step_id"): s for s in (ledger.get("steps") or [])}
    for sid in ["P1", "P2", "P3", "P4", "P5", "P6", "P6R"]:
        if (by_id.get(sid) or {}).get("status") != "DONE":
            e.append(f"ledger {sid} status must be DONE")
    p7a = by_id.get("P7A") or {}
    if p7a.get("status") != "DONE":
        e.append("ledger P7A status must stay DONE (option a back-compat for committed P7A checker)")
    if p7a.get("classification") != "agent_authored_quality_probe_pass":
        e.append("ledger P7A.classification must be agent_authored_quality_probe_pass")
    p7 = by_id.get("P7") or {}
    if p7.get("status") not in ("NEXT", "IN_PROGRESS"):
        e.append(f"ledger P7 (legacy anchor) must stay NEXT/IN_PROGRESS, got {p7.get('status')!r}")
    if p7.get("unlock_kind") != "governed_incremental_microbatch":
        e.append("ledger P7 unlock_kind must stay governed_incremental_microbatch")
    if p7.get("generation_allowed") is not False:
        e.append("ledger P7 generation_allowed must be false")
    p7b = by_id.get("P7B") or {}
    if p7b.get("status") != "DONE":
        e.append(f"ledger P7B status must be DONE, got {p7b.get('status')!r}")
    if p7b.get("task_id") != TASK_ID:
        e.append("ledger P7B task_id must be this task")
    p7cs = by_id.get("P7C") or {}
    if p7cs.get("status") not in ("NEXT", "IN_PROGRESS"):
        e.append(f"ledger P7C status must be NEXT, got {p7cs.get('status')!r}")
    if p7cs.get("next_unlocked") != "P7C_execution_brief_and_go_nogo_only":
        e.append("ledger P7C.next_unlocked must be P7C_execution_brief_and_go_nogo_only (note 3)")
    if p7cs.get("generation_authorized_by_this_task") is not False:
        e.append("ledger P7C.generation_authorized_by_this_task must be false (note 3)")
    p7d = by_id.get("P7D") or {}
    if "BLOCKED" not in str(p7d.get("status") or "").upper():
        e.append(f"ledger P7D must be blocked by P7C, got {p7d.get('status')!r}")
    p8 = by_id.get("P8") or {}
    if "BLOCKED" not in str(p8.get("status") or "").upper():
        e.append(f"ledger P8 must stay blocked, got {p8.get('status')!r}")
    rm = ledger.get("route_migration") or {}
    if not rm:
        e.append("ledger route_migration block missing (notes 1+2)")
    else:
        if rm.get("no_old_checker_edited") is not True:
            e.append("route_migration.no_old_checker_edited must be true (option a)")
        if rm.get("no_readiness_flipped") is not True:
            e.append("route_migration.no_readiness_flipped must be true")

    # (J) git surface: immutability (note 6) + allowed write surface + priors
    if live.get("git_changed_outside_allowed"):
        e.append(f"git changes outside allowed write surface: {live['git_changed_outside_allowed']}")
    if live.get("p7a_original_modified"):
        e.append(f"P7A original artifact modified (note 6 immutability): {live['p7a_original_modified']}")
    if live.get("forbidden_touched"):
        e.append(f"forbidden path touched: {live['forbidden_touched']}")
    priors = live.get("prior_checkers") or {}
    for name, rc in priors.items():
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
    return {
        "identity": _load_top(ws, f"{CLOSEOUT_DIR}/proof_microbatch_identity_decision.v0.1.yaml"),
        "not_3600": _load_top(ws, f"{CLOSEOUT_DIR}/proof_microbatch_not_3600_unlock_decision.v0.1.yaml"),
        "closeout": _load_top(ws, f"{CLOSEOUT_DIR}/proof_microbatch_closeout.v0.1.yaml"),
        "gen_mode": _load_top(ws, f"{ALIGN_DIR}/generation_mode_contract.v0.1.yaml"),
        "fact_binding": _load_top(ws, f"{ALIGN_DIR}/fact_binding_policy.v0.1.yaml"),
        "cso_comp": _load_top(ws, f"{ALIGN_DIR}/ontology_cso_composition_contract.v0.1.yaml"),
        "creative_pat": _load_top(ws, f"{ALIGN_DIR}/creative_pattern_requirements.v0.1.yaml"),
        "p0_matrix": _load_top(ws, f"{ALIGN_DIR}/p0_generation_mode_matrix.v0.1.yaml"),
        "p7c_plan": _load_top(ws, f"{ALIGN_DIR}/p7c_scoped_microbatch_route_plan.v0.1.yaml"),
        "p7d": _load_top(ws, f"{ALIGN_DIR}/p7d_3600_deferral_decision.v0.1.yaml"),
    }


def load_ledger(ws):
    d = yaml.safe_load(open(os.path.join(ws, LEDGER_REL)))
    return d["grc_3600_execution_plan_status"]


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


def compute_live(ws, prior_checkers):
    changed = _git_changed(ws)
    outside = [p for p in changed if not p.startswith(ALLOWED_WRITE_PREFIXES)]
    p7a_orig = [p for p in changed
                if p.startswith(PROOF_ROOT) and not p.startswith(PROOF_CLOSEOUT_ROOT)]
    forbidden = [p for p in changed
                 if any(p.startswith(d + "/") or p == d for d in NEW_FORBIDDEN_DIRS)]
    return {
        "git_changed": changed,
        "git_changed_outside_allowed": outside,
        "p7a_original_modified": p7a_orig,
        "forbidden_touched": forbidden,
        "prior_checkers": prior_checkers,
    }


def scan_fs(ws):
    present = [d for d in NEW_FORBIDDEN_DIRS if os.path.isdir(os.path.join(ws, d))]
    run_manifest = bool(glob.glob(os.path.join(ws, "07_microbatch_runs", "run_manifest*")) +
                        glob.glob(os.path.join(ws, "07_microbatch_runs", "microbatch_index*")))
    three600 = bool(glob.glob(os.path.join(ws, "04_microbatch_generation", "*3600*")) +
                    glob.glob(os.path.join(ws, "07_microbatch_runs", "*3600*")))
    micro = any(os.path.isdir(os.path.join(ws, d))
                for d in ["07_microbatch_runs/microbatches", "07_microbatch_runs/batch_summaries"])
    runs_dir = os.path.join(ws, "07_microbatch_runs")
    proof_run_dirs = [d for d in os.listdir(runs_dir)
                      if os.path.isdir(os.path.join(runs_dir, d))] if os.path.isdir(runs_dir) else []
    cc = None
    cards = os.path.join(ws, "07_microbatch_runs/proof_microbatch_001/knowledge_candidate_cards.yaml")
    if os.path.exists(cards):
        try:
            cd = yaml.safe_load(open(cards))
            cc = (cd.get("proof_microbatch_candidate_cards") or {}).get("candidate_count")
        except Exception:
            cc = "unparsed"
    return {
        "forbidden_present": present,
        "run_manifest_present": run_manifest,
        "microbatches_present": micro,
        "three600_present": three600,
        "proof_run_dirs": proof_run_dirs,
        "proof_candidate_count": cc,
    }


# ----------------------------- snapshot prior runner -----------------------------
def _build_snapshot(ws, extra_excludes):
    import shutil
    snap = tempfile.mkdtemp(prefix="p7b_snap_")
    excludes = ["--exclude=.git"] + [f"--exclude={p}" for p in extra_excludes]
    rs = subprocess.run(["rsync", "-a"] + excludes + [ws.rstrip("/") + "/", snap + "/"],
                        capture_output=True, text=True)
    if rs.returncode != 0:  # rsync missing -> cp + prune fallback
        subprocess.run(["cp", "-a", ws.rstrip("/") + "/.", snap], capture_output=True, text=True)
    # belt-and-suspenders: physically remove .git + excluded paths from the copy
    for rel in [".git"] + extra_excludes:
        p = os.path.join(snap, rel)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p):
            os.remove(p)
    # reset ledger to HEAD (the pre-this-task state the upstream checkers validated)
    for rel in ["10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
                "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"]:
        h = subprocess.run(["git", "-C", ws, "show", "HEAD:" + rel], capture_output=True, text=True)
        if h.returncode == 0:
            os.makedirs(os.path.dirname(os.path.join(snap, rel)), exist_ok=True)
            with open(os.path.join(snap, rel), "w") as f:
                f.write(h.stdout)
    return snap


def run_priors(ws):
    """Run all 9 priors across two snapshots (see module docstring)."""
    import shutil
    results = {}
    this_task_deliverables = [
        "07_microbatch_runs/proof_microbatch_001/closeout",
        ALIGN_DIR,
        "ci/checkers/check_proof_microbatch_closeout_and_generation_mode_cso_alignment.py",
        "ci/fixtures/proof_microbatch_closeout_and_generation_mode_cso_alignment",
        "ci/reports/proof_microbatch_closeout_and_generation_mode_cso_alignment_report.v0.1.json",
        "docs/reports/grc_proof_microbatch_closeout_and_generation_mode_cso_alignment_report.md",
        "docs/reports/grc_proof_microbatch_closeout_and_generation_mode_cso_alignment_receipt.json",
    ]
    # snapshot A: pre-microbatch (drop ALL of 07_microbatch_runs so P6/P6R see no gen dir)
    snap_a = _build_snapshot(ws, ["07_microbatch_runs"] + this_task_deliverables[1:])
    try:
        for name, rel, args in PRIORS_SNAPSHOT_A:
            chk = os.path.join(snap_a, rel)
            results[name] = 98 if not os.path.exists(chk) else subprocess.run(
                [sys.executable, chk] + args, cwd=snap_a, capture_output=True, text=True).returncode
    finally:
        shutil.rmtree(snap_a, ignore_errors=True)
    # snapshot B: keep the P7A proof, drop only this task's deliverables (so the P7A checker
    # validates the 40 drafts against the exact committed proof, without our in-flight files)
    snap_b = _build_snapshot(ws, this_task_deliverables)
    try:
        name, rel, args = PRIOR_P7A
        chk = os.path.join(snap_b, rel)
        results[name] = 98 if not os.path.exists(chk) else subprocess.run(
            [sys.executable, chk] + args, cwd=snap_b, capture_output=True, text=True).returncode
    finally:
        shutil.rmtree(snap_b, ignore_errors=True)
    return results


# ----------------------------- live / selftest -----------------------------
def run_live(ws, report_out=None):
    docs = load_docs(ws)
    ledger = load_ledger(ws)
    fs_state = scan_fs(ws)
    live = compute_live(ws, run_priors(ws))
    errors = validate(docs, ledger, fs_state, live)
    status = "PASS" if not errors else "FAIL"
    report = {
        "checker": "check_proof_microbatch_closeout_and_generation_mode_cso_alignment.py",
        "task_id": TASK_ID, "step_id": "P7B",
        "status": status, "error_count": len(errors), "errors": errors,
        "generation_modes": sorted(((docs.get("gen_mode") or {}).get("generation_modes") or {}).keys()),
        "creative_pattern_families": len(((docs.get("creative_pat") or {}).get("creative_patterns") or {})),
        "p7c_default_count": (((docs.get("p7c_plan") or {}).get("P7C") or {}).get("recommended_count") or {}).get("default_recommendation"),
        "git_changed_outside_allowed": live.get("git_changed_outside_allowed"),
        "p7a_original_modified": live.get("p7a_original_modified"),
        "prior_checkers": live.get("prior_checkers"),
    }
    if report_out:
        json.dump(report, open(report_out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def selftest(ws):
    fx_dir = os.path.join(ws, "ci/fixtures/proof_microbatch_closeout_and_generation_mode_cso_alignment")
    pos = os.path.join(fx_dir, "positive_valid.yaml")
    if not os.path.exists(pos):
        print(json.dumps({"status": "FAIL", "reason": "positive fixture missing"}))
        return 1

    def _run(fx):
        return validate(fx["docs"], fx["ledger"], fx["fs_state"], fx["live"])

    pf = yaml.safe_load(open(pos))
    pos_err = _run(pf)
    if pos_err:
        print(json.dumps({"status": "FAIL", "reason": "positive fixture did not pass", "errors": pos_err},
                         ensure_ascii=False))
        return 1
    negatives = sorted(glob.glob(os.path.join(fx_dir, "negative_*.yaml")))
    fails = []
    for nf in negatives:
        try:
            fx = yaml.safe_load(open(nf))
            errs = _run(fx)
        except Exception as ex:
            errs = [f"malformed: {ex}"]
        if not errs:
            fails.append(os.path.basename(nf))
    status = "PASS" if not fails else "FAIL"
    print(json.dumps({"status": status, "negative_count": len(negatives),
                      "negatives_that_wrongly_passed": fails, "positive_ok": True},
                     ensure_ascii=False))
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
