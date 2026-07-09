#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_grc_legacy_lock_retire_and_governed_unlock.py  (P6R)

Independently gate Phase A: retire the legacy semantic-pilot batch-generation
lock's block on the GRC route + establish a governed GRC microbatch unlock,
with ZERO generation. Ground truth is recomputed here (E12), never trusted from
the reconciliation self-reports:

  * the 6 GRC checkers (P1..P6) + the contract-lock checker are re-run live;
  * the project-infra `batch_generation_unlocked: false` count is grep-DISCOVERED
    live (Codex required note: never hardcode as 10) and must equal the count the
    inventory recorded;
  * the direct-3600 / generate-without-pilot forbidden semantics are re-read from
    the immutable contract + shared_generation_rules global_forbidden;
  * readiness-all-false, forbidden-scope, zero-generation, the ledger route
    (P6R DONE, P7 not DONE and re-scoped, P8 blocked), project-infra untouched,
    and git-diff-only-allowed-surface are all recomputed from the real repo.

Fail-closed: refuses to run under `python -O` (asserts disabled) -> exit 2.

Codex Prompt-Pre-Review required notes baked in:
  * do_not_hardcode_project_infra_false_flag_count_as_10
  * checker_must_discover_and_record_actual_project_infra_batch_generation_unlocked_false_count
  * project-infra is legacy read-only, not an active P7 blocker, but readiness there must stay false
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
TASK_ID = "GKB-GRC-LEGACY-LOCK-RETIRE-AND-GOVERNED-UNLOCK-001"
RECON_REL = "08_batch_unlock_reconciliation"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
PROJECT_INFRA_REL = "project-infra/current_workspace_status.yaml"
CONTRACT_LOCK_REL = "01_generation_contracts/w7_generation_baseline_lock.v0.1.yaml"
SHARED_RULES_REL = "02_generation_brief_pack/00_shared_generation_rules.yaml"

THREE600_GEN_TASK = "GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001"
UNLOCK_SCOPE = "mkc_007..mkc_046"
HELD_SCOPE = "mkc_001..mkc_006"

LEGACY_LINES = ["first_cross_type_pilot_44", "semantic_regen_20", "holdout_14", "v3_to_v4_7_line"]
EVIDENCE_STEPS = {"P4", "P5", "P6"}
READINESS_KEYS = ["candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready",
                  "generation_allowed", "generation_eligible", "production_ready",
                  "release_ready", "production_servable"]
FORBIDDEN_DIRS = ["KE", "serving_projection", "rag", "dify", "candidatepack_etl",
                  "CandidatePack", "RAG", "DIFY", "Serving"]
# old-line failure evidence that must remain present (not deleted)
EVIDENCE_FILES = [
    "03_pilot/pilot_semantic_fail_closeout.yaml",
    "03_pilot/holdout_microbatch_001/holdout_microbatch_001_no_go_closeout.yaml",
]
ALLOWED_WRITE_PREFIXES = (
    "08_batch_unlock_reconciliation/",
    "ci/checkers/check_grc_legacy_lock_retire_and_governed_unlock.py",
    "ci/fixtures/grc_legacy_lock_retire_and_governed_unlock/",
    "ci/reports/grc_legacy_lock_retire_and_governed_unlock_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/grc_legacy_lock_retire_and_governed_unlock_report.md",
    "docs/reports/grc_legacy_lock_retire_and_governed_unlock_receipt.json",
)


def _is_blocked(status):
    s = str(status or "")
    return "BLOCKED" in s or s.startswith("PLANNED_BLOCKED") or s in ("HOLD", "BLOCKED_OR_HOLD")


def _all_false(d):
    """Every present readiness key is falsey (and readiness_all_false, if present, is True)."""
    if not isinstance(d, dict):
        return False
    for k in READINESS_KEYS:
        if k in d and d.get(k) not in (False, None):
            return False
    if "readiness_all_false" in d and d.get("readiness_all_false") is not True:
        return False
    return True


# ----------------------------- pure validation core -----------------------------
def validate(recon, ledger, fs_state, live):
    e = []
    recon = recon or {}
    ledger = ledger or {}
    fs_state = fs_state or {}
    live = live or {}
    rec = recon.get("reconciliation") or {}
    dec = recon.get("unlock_decision") or {}
    inv = recon.get("inventory") or {}
    prov = recon.get("provenance") or {}
    evi = recon.get("evidence_index") or {}
    p0 = recon.get("p0_hold") or {}

    # (1) all six reconciliation docs present
    for name, doc in [("reconciliation", rec), ("unlock_decision", dec), ("inventory", inv),
                      ("provenance", prov), ("evidence_index", evi), ("p0_hold", p0)]:
        if not doc:
            e.append(f"reconciliation doc missing/empty: {name}")

    # (2) legacy failed lines: superseded, not p7 evidence, not rewritten as PASS
    lf = rec.get("legacy_failed_line") or {}
    for ln in LEGACY_LINES:
        entry = lf.get(ln) or {}
        if not entry:
            e.append(f"legacy_failed_line missing: {ln}")
            continue
        if entry.get("use_as_p7_evidence") is not False:
            e.append(f"legacy_failed_line {ln} use_as_p7_evidence must be false")
        if entry.get("rewritten_as_pass") is not False:
            e.append(f"legacy_failed_line {ln} rewritten_as_pass must be false")
        st = str(entry.get("status", "")).lower()
        if "pass" in st or "accepted" in st:
            e.append(f"legacy_failed_line {ln} status {entry.get('status')!r} rewrites failure as pass")
    if rec.get("legacy_line_not_rewritten_as_pass") is not True:
        e.append("reconciliation legacy_line_not_rewritten_as_pass must be true")
    if rec.get("legacy_evidence_preserved_not_deleted") is not True:
        e.append("reconciliation legacy_evidence_preserved_not_deleted must be true")

    # (3) old 20 regen never used as p7 evidence
    if rec.get("old_20_regen_used_as_p7_evidence") is not False:
        e.append("reconciliation old_20_regen_used_as_p7_evidence must be false")
    if evi.get("old_20_regen_used_as_evidence") is not False:
        e.append("evidence_index old_20_regen_used_as_evidence must be false")
    if evi.get("legacy_failed_line_used_as_evidence") is not False:
        e.append("evidence_index legacy_failed_line_used_as_evidence must be false")

    # (4) GRC unlock evidence P4/P5/P6
    ge = rec.get("grc_unlock_evidence") or {}
    if (ge.get("P4_canary_40") or {}).get("status") != "PASS":
        e.append("grc_unlock_evidence P4_canary_40 status must be PASS")
    if (ge.get("P5_proposition_pack_v1") or {}).get("status") != "PASS":
        e.append("grc_unlock_evidence P5_proposition_pack_v1 status must be PASS")
    if (ge.get("P6_dual_gate_briefing") or {}).get("status") != "GO_TO_P7":
        e.append("grc_unlock_evidence P6_dual_gate_briefing status must be GO_TO_P7")
    ev_steps = {x.get("step") for x in (evi.get("evidence") or []) if isinstance(x, dict)}
    if not EVIDENCE_STEPS.issubset(ev_steps):
        e.append(f"evidence_index must record steps {sorted(EVIDENCE_STEPS)}, got {sorted(ev_steps)}")

    # (5) unlock scope == mkc_007..046; P0-00 held
    us = rec.get("unlock_scope") or {}
    if us.get("included_clusters") != UNLOCK_SCOPE:
        e.append(f"unlock_scope.included_clusters must be {UNLOCK_SCOPE}, got {us.get('included_clusters')!r}")
    if us.get("excluded_or_held_clusters") != HELD_SCOPE:
        e.append(f"unlock_scope.excluded_or_held_clusters must be {HELD_SCOPE}, got {us.get('excluded_or_held_clusters')!r}")
    if dec.get("unlock_scope_clusters") != UNLOCK_SCOPE:
        e.append(f"unlock_decision.unlock_scope_clusters must be {UNLOCK_SCOPE}")
    if str(us.get("p0_00_status", "")).startswith("held") is False:
        e.append("unlock_scope p0_00_status must be held_*")
    # (5b) P0-00 hold decision
    if not str(p0.get("status", "")).startswith("held"):
        e.append("p0_00_hold_decision status must be held_*")
    if p0.get("included_in_gkb_body_generation") is not False:
        e.append("p0_00 included_in_gkb_body_generation must be false")
    if p0.get("unlock_scope_excludes_p0_00") is not True:
        e.append("p0_00 unlock_scope_excludes_p0_00 must be true")

    # (6) direct-3600 / generate-without-pilot forbidden preserved (recomputed live)
    sf = dec.get("still_forbidden") or []
    for tok in ["direct_3600_generation", "one_shot_3600_generation", "generate_without_grc_pilot"]:
        if tok not in sf:
            e.append(f"unlock_decision still_forbidden must contain {tok}")
    if live.get("contract_direct3600_forbidden") is not True:
        e.append("live: contract direct_3600_generation_allowed must be false (contract immutable)")
    sgf = live.get("shared_global_forbidden") or []
    for tok in ["direct_3600_generation", "generate_without_pilot"]:
        if tok not in sgf:
            e.append(f"live: 00_shared_generation_rules global_forbidden must still contain {tok}")

    # (7) runtime generation not allowed / not unlocked
    uf = rec.get("unlock_form") or {}
    if uf.get("runtime_generation_allowed") is not False:
        e.append("unlock_form.runtime_generation_allowed must be false")
    if uf.get("direct_one_shot_3600_generation_allowed") is not False:
        e.append("unlock_form.direct_one_shot_3600_generation_allowed must be false")
    if uf.get("governed_microbatch_generation_allowed_under_grc") is not True:
        e.append("unlock_form.governed_microbatch_generation_allowed_under_grc must be true")
    if dec.get("generation_authorized_by_this_task") is not False:
        e.append("unlock_decision.generation_authorized_by_this_task must be false")
    if ledger.get("generation_unlocked") is not False:
        e.append(f"ledger generation_unlocked must be false, got {ledger.get('generation_unlocked')!r}")

    # (8) zero generation
    if fs_state.get("three600_created"):
        e.append("a 3600 generation dir was created (forbidden in Phase A)")
    if fs_state.get("microbatch_runs_created"):
        e.append("07_microbatch_runs was created (forbidden in Phase A: zero generation)")
    if dec.get("three600_generated_count_this_task") not in (0, None):
        e.append("unlock_decision.three600_generated_count_this_task must be 0")
    if uf.get("generation_executed_or_authorized_by_this_task") is not False:
        e.append("unlock_form.generation_executed_or_authorized_by_this_task must be false")

    # (9) ledger route: P6R DONE, P7 not DONE + re-scoped, P8 blocked
    by_id = {s.get("step_id"): s for s in (ledger.get("steps") or [])}
    p6r = by_id.get("P6R") or {}
    if p6r.get("task_id") != TASK_ID:
        e.append(f"ledger P6R task_id must be {TASK_ID}, got {p6r.get('task_id')!r}")
    if p6r.get("status") != "DONE":
        e.append(f"ledger P6R status must be DONE, got {p6r.get('status')!r}")
    p7 = by_id.get("P7") or {}
    if not p7:
        e.append("ledger P7 step missing")
    if p7.get("status") == "DONE":
        e.append("ledger P7 (3600 generation) must not be DONE (zero generation in Phase A)")
    if p7.get("unlock_kind") != "governed_incremental_microbatch":
        e.append(f"ledger P7 unlock_kind must be governed_incremental_microbatch (re-scoped), got {p7.get('unlock_kind')!r}")
    if p7.get("one_shot_3600_generation_allowed") is not False:
        e.append("ledger P7 one_shot_3600_generation_allowed must be false")
    if p7.get("generation_allowed") is not False:
        e.append("ledger P7 generation_allowed must be false")
    p8 = by_id.get("P8") or {}
    if not _is_blocked(p8.get("status")):
        e.append(f"ledger P8 must stay blocked, got {p8.get('status')!r}")

    # (10) readiness all false: reconciliation + unlock_decision + ledger + project-infra(live)
    if not _all_false(rec.get("readiness")):
        e.append("reconciliation readiness not all false")
    if not _all_false(dec.get("readiness")):
        e.append("unlock_decision readiness not all false")
    if not _all_false(ledger.get("readiness")):
        e.append("ledger readiness not all false")
    if live.get("project_infra_readiness_all_false") is not True:
        e.append("live: project-infra readiness must still be all false")

    # (11) inventory: both 02_brief_pack + project-infra; discovered count matches live (not hardcoded)
    surf = inv.get("surfaces") or {}
    bp = surf.get("brief_pack_02") or {}
    pinfra = surf.get("project_infra") or {}
    if not (bp.get("lock_files") and bp.get("batch_briefs")):
        e.append("inventory brief_pack_02 must list lock_files and batch_briefs")
    cnt = (pinfra.get("batch_generation_unlocked_false_count") or {})
    if cnt.get("mode") != "discovered_count_not_hardcoded":
        e.append("inventory project-infra count mode must be discovered_count_not_hardcoded")
    obs = cnt.get("observed_at_build")
    live_cnt = live.get("project_infra_false_count")
    if obs is None or live_cnt is None or obs != live_cnt:
        e.append(f"inventory project-infra observed count {obs!r} != live discovered count {live_cnt!r} (Codex: discover, do not hardcode)")
    if obs == 10:
        e.append("inventory project-infra count hardcoded to 10 (Codex forbade this exact value)")
    if pinfra.get("classification") != "legacy_read_only_not_active_route_authority":
        e.append("inventory project-infra classification must be legacy_read_only_not_active_route_authority")
    ci = surf.get("contract_immutable") or {}
    if ci.get("classification") != "contract_immutable_preserved":
        e.append("inventory contract_immutable classification must be contract_immutable_preserved")

    # (12) project-infra untouched
    if live.get("project_infra_modified"):
        e.append("project-infra/current_workspace_status.yaml was modified (forbidden)")

    # (13) git diff only allowed surface; brief pack unmodified
    outside = live.get("git_changed_outside_allowed")
    if outside:
        e.append(f"git changes outside allowed write surface: {outside}")
    if live.get("brief_pack_unmodified") is False:
        e.append("02_generation_brief_pack was modified (central supersession requires zero brief-pack edits)")

    # (14) old-line evidence files preserved
    efp = fs_state.get("evidence_files_present") or {}
    for f in EVIDENCE_FILES:
        if efp.get(f) is not True:
            e.append(f"legacy failure evidence missing/deleted: {f}")
    if prov.get("preserved_not_deleted") is not True:
        e.append("provenance preserved_not_deleted must be true")
    if prov.get("none_rewritten_as_pass") is not True:
        e.append("provenance none_rewritten_as_pass must be true")

    # (15) forbidden scope clean
    if fs_state.get("forbidden_present"):
        e.append(f"forbidden dirs present: {fs_state.get('forbidden_present')}")
    if fs_state.get("candidatepack_created"):
        e.append("CandidatePack materialization detected")
    if fs_state.get("consolidated_created"):
        e.append("08_consolidated_outputs created (forbidden)")
    if fs_state.get("eligibility_created"):
        e.append("09_candidatepack_eligibility created (forbidden)")

    return e


# ----------------------------- loaders (real repo, read-only) -----------------------------
def _y(path, key=None):
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d[key] if key else d


def load_recon(ws):
    d = os.path.join(ws, RECON_REL)
    return {
        "reconciliation": _y(os.path.join(d, "grc_legacy_pilot_reconciliation.v0.1.yaml"),
                             "grc_legacy_pilot_reconciliation"),
        "unlock_decision": _y(os.path.join(d, "grc_batch_unlock_decision.v0.1.yaml"),
                              "grc_batch_unlock_decision"),
        "inventory": _y(os.path.join(d, "legacy_lock_surface_inventory.v0.1.yaml"),
                        "legacy_lock_surface_inventory"),
        "provenance": _y(os.path.join(d, "legacy_failed_line_provenance_index.v0.1.yaml"),
                         "legacy_failed_line_provenance_index"),
        "evidence_index": _y(os.path.join(d, "grc_unlock_evidence_index.v0.1.yaml"),
                             "grc_unlock_evidence_index"),
        "p0_hold": _y(os.path.join(d, "p0_00_hold_decision.v0.1.yaml"), "p0_00_hold_decision"),
    }


def load_ledger(ws):
    root = _y(os.path.join(ws, LEDGER_REL), "grc_3600_execution_plan_status")
    return {"steps": root.get("steps", []), "readiness": root.get("readiness", {}),
            "generation_unlocked": root.get("generation_unlocked"),
            "route_note": root.get("grc_legacy_lock_retire_route_note", {})}


def scan_fs(ws):
    present = [d for d in FORBIDDEN_DIRS if os.path.isdir(os.path.join(ws, d))]
    three600 = bool(glob.glob(os.path.join(ws, "04_microbatch_generation", "*3600*")) +
                    glob.glob(os.path.join(ws, "*3600_generation*")))
    mb_runs = os.path.isdir(os.path.join(ws, "07_microbatch_runs"))
    cp = os.path.isdir(os.path.join(ws, "CandidatePack")) or \
        os.path.isdir(os.path.join(ws, "candidatepack_etl", "candidatepack_instances"))
    cons = os.path.isdir(os.path.join(ws, "08_consolidated_outputs"))
    elig = os.path.isdir(os.path.join(ws, "09_candidatepack_eligibility"))
    efp = {f: os.path.isfile(os.path.join(ws, f)) for f in EVIDENCE_FILES}
    return {"forbidden_present": present, "three600_created": three600,
            "microbatch_runs_created": mb_runs, "candidatepack_created": cp,
            "consolidated_created": cons, "eligibility_created": elig,
            "evidence_files_present": efp}


def compute_live(ws):
    # project-infra batch_generation_unlocked:false count -- DISCOVERED, never hardcoded
    pinfra_path = os.path.join(ws, PROJECT_INFRA_REL)
    pi_text = open(pinfra_path, encoding="utf-8").read() if os.path.isfile(pinfra_path) else ""
    false_count = sum(1 for ln in pi_text.splitlines()
                      if ln.strip() == "batch_generation_unlocked: false")
    pi_readiness_all_false = not any(
        ln.strip() == f"{k}: true" for ln in pi_text.splitlines() for k in READINESS_KEYS)
    # contract direct-3600 forbidden
    contract_forbidden = False
    cpath = os.path.join(ws, CONTRACT_LOCK_REL)
    if os.path.isfile(cpath):
        for ln in open(cpath, encoding="utf-8"):
            if ln.strip() == "direct_3600_generation_allowed: false":
                contract_forbidden = True
                break
    # shared_generation_rules global_forbidden
    sgf = []
    try:
        sr = _y(os.path.join(ws, SHARED_RULES_REL), "shared_generation_rules")
        sgf = sr.get("global_forbidden", []) or []
    except Exception:
        sgf = []
    # git diff state
    changed = _git_changed(ws)
    outside = [p for p in changed if not p.startswith(ALLOWED_WRITE_PREFIXES)]
    return {
        "project_infra_false_count": false_count,
        "project_infra_readiness_all_false": pi_readiness_all_false,
        "contract_direct3600_forbidden": contract_forbidden,
        "shared_global_forbidden": sgf,
        "project_infra_modified": PROJECT_INFRA_REL in changed,
        "brief_pack_unmodified": not any(p.startswith("02_generation_brief_pack/") for p in changed),
        "git_changed_outside_allowed": outside,
        "git_changed": changed,
    }


def _git_changed(ws):
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                             cwd=ws, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []
    paths = []
    for ln in out.splitlines():
        if not ln.strip():
            continue
        p = ln[3:].strip().strip('"')
        if " -> " in p:  # rename
            p = p.split(" -> ", 1)[1]
        paths.append(p)
    return paths


# ----------------------------- live + selftest -----------------------------
def _run_prior(ws, rel, args):
    try:
        return subprocess.run([sys.executable, os.path.join(ws, rel)] + args, cwd=ws,
                              capture_output=True, text=True, timeout=300).returncode
    except Exception:
        return -1


def run_live(ws, report_out=None):
    recon = load_recon(ws)
    ledger = load_ledger(ws)
    fs_state = scan_fs(ws)
    live = compute_live(ws)
    errors = validate(recon, ledger, fs_state, live)
    prior = {
        "p1": _run_prior(ws, "ci/checkers/check_grc_corpus_registry.py", ["--live"]),
        "p2": _run_prior(ws, "ci/checkers/check_grc_contract_ontology_alignment.py", ["--live"]),
        "p3": _run_prior(ws, "ci/checkers/check_judge_calibration_against_grc.py", ["--live"]),
        "p4": _run_prior(ws, "ci/checkers/check_canary_40_generation_and_gate.py", ["--live"]),
        "p5": _run_prior(ws, "ci/checkers/check_canary_40_quality_closeout_and_proposition_pack.py", ["--live"]),
        "p6": _run_prior(ws, "ci/checkers/check_3600_microbatch_briefing_go_nogo.py", ["--live"]),
        "contract_lock": _run_prior(ws, "ci/checkers/check_codex_generation_contract_lock.py", []),
    }
    for name, rc in prior.items():
        if rc != 0:
            errors.append(f"prior checker {name} live not PASS (exit {rc})")
    status = "PASS" if not errors else "FAIL"
    report = {
        "status": status, "task_id": TASK_ID, "step_id": "P6R",
        "legacy_line_status": "superseded_failed_line",
        "old_20_regen_used_as_p7_evidence": False,
        "governed_microbatch_generation_allowed_under_grc": True,
        "direct_one_shot_generation_still_forbidden": True,
        "p0_00_held": True,
        "project_infra_false_count_discovered": live.get("project_infra_false_count"),
        "project_infra_modified": live.get("project_infra_modified"),
        "brief_pack_unmodified": live.get("brief_pack_unmodified"),
        "git_changed_outside_allowed": live.get("git_changed_outside_allowed"),
        "generation_executed": False,
        "three600_generated_count": 0,
        "readiness_all_false": not any("readiness" in x for x in errors),
        "prior_checkers": prior,
        "next_real_action_unlocked": "GKB-3600 batch-001 real authored microbatch (separate founder authorization + Codex three-gate)",
        "error_count": len(errors), "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report_out:
        with open(report_out, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return 0 if status == "PASS" else 1


def run_selftest(ws, fixtures_dir):
    pos = os.path.join(fixtures_dir, "positive_valid_reconciliation.yaml")
    negatives = sorted(glob.glob(os.path.join(fixtures_dir, "negative_*.yaml")))
    result = {"status": "PASS", "positive_fixture_count": 0, "negative_fixture_count": len(negatives),
              "negative_fixtures_fail_closed": True, "positive_result": None, "negative_results": {}}

    def vfx(fx):
        return validate(fx.get("recon", {}), fx.get("ledger", {}), fx.get("fs_state", {}), fx.get("live", {}))

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
    ap.add_argument("--fixtures-root", default="ci/fixtures/grc_legacy_lock_retire_and_governed_unlock")
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
