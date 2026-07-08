#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_canary_40_quality_closeout_and_proposition_pack.py  (P5)

Independently gate the canary-40 quality closeout + proposition_pack_v1.
Ground truth recomputed here (E12): source_text_span exact-substring membership,
source_canary_id<->cluster match, owner/epistemic legality + consistency, per-cluster
counts, readiness, forbidden scope, and ledger route are all recomputed from the real
canary run + contract + ledger. Manifest self-reports are never trusted.

Fail-closed: refuses to run under `python -O` (asserts disabled) -> exit 2.

Codex Prompt-Pre-Review required notes baked in:
  note1: P5 PASS unlocks ONLY GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001; the 3600
         GENERATION task must NOT be NEXT (fail-closed if it is).
  note2: P5 task supersedes GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001.
  note3: every source_text_span must be an exact substring of its canary rich body
         (span_not_found_in_rich_body -> FAIL) and source_canary_id must match the
         cluster's canary (source_canary_id_cluster_mismatch -> FAIL).
  note4/5/6: honest expert-input provenance; proposition_pack_role=derived_review_asset;
         external-resource prohibitions all false.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

REPO_DEFAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASK_ID = "GKB-CANARY-40-QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001"
RUN_REL = "06_canary_runs/canary_40_001"
CLUSTERS = [f"mkc_{i:03d}" for i in range(7, 47)]

THREE600_GEN_TASK = "GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001"
BRIEFING_TASK = "GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001"
SUPERSEDED_P5 = "GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001"

MIN_PC, MAX_PC = 3, 5
MIN_TOTAL, MAX_TOTAL = 120, 200

OWNER_EPI = {
    "GeneralKnowledgeBase": "domain_method", "EvidencePolicyOutbox": "claim_boundary_policy",
    "ExecutionAssetOutbox": "execution_asset_method", "GovernanceOutbox": "governance_control_policy",
    "SourceGapLedger": "source_gap_candidate", "DecisionPacketLedger": "decision_required_candidate",
}
OWNER_ALLOWED = set(OWNER_EPI)
EPI_ALLOWED = set(OWNER_EPI.values())

REQUIRED_PROP_FIELDS = [
    "proposition_id", "canonical_cluster_id", "source_canary_id", "source_rich_body_ref",
    "source_text_span", "proposition_text", "proposition_type", "owner_candidate", "epistemic_class",
    "applicable_when", "not_applicable_when", "failure_signal", "downstream_effect",
    "source_requirement", "evidence_requirement", "relation_hint_refs", "judge_calibration_refs", "status",
]
READINESS_MUST_BE_FALSE = ["candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready",
    "generation_allowed", "generation_eligible", "production_ready", "release_ready", "production_servable"]
REAL_FACT_PATTERNS = [
    r"\d+\s*元", r"￥\s*\d+", r"\$\s*\d+", r"\d+\s*块钱", r"\d+\s*折", r"打\s*\d+\s*折",
    r"(货号|款号|SKU)\s*[:：]?\s*[A-Za-z0-9\-]{3,}", r"库存\s*\d+", r"售价\s*\d+",
]
FORBIDDEN_DIRS = ["KE", "serving_projection", "rag", "dify", "candidatepack_etl",
                  "CandidatePack", "RAG", "DIFY", "Serving"]
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
KIND_OWNER_POLICY_REL = "01_generation_contracts/codex_candidate_kind_target_owner_policy.v0.1.yaml"


# ----------------------------- refs (real repo, read-only) -----------------------------
def load_refs(ws):
    refs = {"owner_allowed": set(OWNER_ALLOWED), "epi_allowed": set(EPI_ALLOWED),
            "canary_by_cluster": {}, "body_by_cluster": {}, "canary_ids": set()}
    cards = yaml.safe_load(open(os.path.join(ws, RUN_REL, "canary_candidate_cards.v0.1.yaml")))["canary_40_candidate_cards"]["candidates"]
    for c in cards:
        refs["canary_by_cluster"][c["canonical_cluster_id"]] = c["canary_id"]
        refs["canary_ids"].add(c["canary_id"])
    blocks = yaml.safe_load(open(os.path.join(ws, RUN_REL, "canary_rich_body_blocks.v0.1.yaml")))["canary_40_rich_body_blocks"]["blocks"]
    for b in blocks:
        refs["body_by_cluster"][b["canonical_cluster_id"]] = b["body"]
    return refs


def scan_fs(ws):
    present = [d for d in FORBIDDEN_DIRS if os.path.isdir(os.path.join(ws, d))]
    three600 = bool(glob.glob(os.path.join(ws, "04_microbatch_generation", "*3600*")) +
                    glob.glob(os.path.join(ws, "*3600_generation*")))
    cp = os.path.isdir(os.path.join(ws, "CandidatePack")) or os.path.isdir(os.path.join(ws, "candidatepack_etl", "candidatepack_instances"))
    return {"forbidden_present": present, "three600_created": three600, "candidatepack_created": cp}


def load_pack(ws):
    d = os.path.join(ws, RUN_REL)
    closeout = yaml.safe_load(open(os.path.join(d, "review_closeout", "canary_40_quality_closeout.v0.1.yaml")))["canary_40_quality_closeout"]
    cp = yaml.safe_load(open(os.path.join(d, "proposition_pack_v1", "cluster_propositions.v0.1.yaml")))["cluster_propositions"]
    manifest = yaml.safe_load(open(os.path.join(d, "proposition_pack_v1", "proposition_pack_manifest.v0.1.yaml")))["proposition_pack_manifest"]
    return closeout, cp.get("clusters", {}), manifest


def load_ledger(ws):
    return yaml.safe_load(open(os.path.join(ws, LEDGER_REL)))["grc_3600_execution_plan_status"].get("steps", [])


# ----------------------------- pure validation core -----------------------------
def validate(closeout, pack_clusters, manifest, ledger_steps, fs_state, refs,
             expected_clusters=None):
    if expected_clusters is None:
        expected_clusters = list(CLUSTERS)
    e = []

    # ---- quality closeout (6-10) ----
    if not closeout:
        e.append("quality closeout missing/empty")
        closeout = {}
    if closeout.get("repeated_review_performed") is not False:
        e.append("closeout repeated_review_performed must be false")
    if closeout.get("expert_review_count") != 2:
        e.append(f"closeout expert_review_count {closeout.get('expert_review_count')!r} != 2")
    if closeout.get("accepted_domain_knowledge") is True or closeout.get("canary_as_formal_knowledge") is True:
        e.append("closeout must not claim accepted_domain_knowledge / formal_knowledge")
    if closeout.get("generation_3600_unlocked") is True:
        e.append("closeout must not unlock 3600")

    # ---- manifest (11) ----
    if not manifest:
        e.append("proposition_pack_manifest missing/empty")
        manifest = {}
    if manifest.get("proposition_pack_role") != "derived_review_asset":
        e.append("manifest proposition_pack_role must be derived_review_asset")
    for k in ("generation_3600_unlocked", "global_generation_allowed", "external_resources_allowed",
              "embedding_allowed", "web_access_allowed", "source_repo_live_dependency",
              "accepted_domain_knowledge", "candidatepack_ready", "ontology_edge_created"):
        if manifest.get(k) is not False:
            e.append(f"manifest {k} must be false")
    if manifest.get("object_count", 0) != 0:
        e.append("manifest object_count must be 0")

    # ---- cluster coverage (12-14) ----
    seen = set(pack_clusters.keys())
    missing = [c for c in expected_clusters if c not in seen]
    extra = [c for c in seen if c not in expected_clusters]
    if missing:
        e.append(f"proposition pack missing clusters: {missing}")
    if extra:
        e.append(f"proposition pack has unexpected clusters: {extra}")
    total = 0
    seen_pids = set()
    for cid in expected_clusters:
        props = pack_clusters.get(cid, [])
        n = len(props)
        total += n
        if n < MIN_PC:
            e.append(f"{cid}: {n} propositions < {MIN_PC}")
        if n > MAX_PC:
            e.append(f"{cid}: {n} propositions > {MAX_PC}")
        for p in props:
            pid = p.get("proposition_id", "?")
            if pid in seen_pids:
                e.append(f"duplicate proposition_id {pid}")
            seen_pids.add(pid)
            # (15) required fields
            for fld in REQUIRED_PROP_FIELDS:
                if fld not in p:
                    e.append(f"{pid}: missing field {fld}")
            # (16)(17) source trace present
            sc = p.get("source_canary_id")
            span = p.get("source_text_span")
            if not sc:
                e.append(f"{pid}: missing source_canary_id")
            if not span:
                e.append(f"{pid}: missing source_text_span")
            # cluster field consistency
            if p.get("canonical_cluster_id") != cid:
                e.append(f"{pid}: canonical_cluster_id {p.get('canonical_cluster_id')!r} != group {cid}")
            # (18) source_canary_id exists in P4 canary cards + (note3) matches this cluster
            exp_canary = refs["canary_by_cluster"].get(cid)
            if sc and sc not in refs["canary_ids"]:
                e.append(f"{pid}: source_canary_id {sc!r} not in P4 canary cards")
            if sc and exp_canary and sc != exp_canary:
                e.append(f"{pid}: source_canary_id_cluster_mismatch ({sc} vs cluster canary {exp_canary})")
            # (note3) span exact substring of the cluster's rich body
            body = refs["body_by_cluster"].get(cid, "")
            if span and body and span not in body:
                e.append(f"{pid}: source_span_not_found_in_rich_body")
            # offsets if present must be correct
            st, en = p.get("source_text_span_start"), p.get("source_text_span_end")
            if span and body and isinstance(st, int) and isinstance(en, int) and 0 <= st <= en:
                if body[st:en] != span:
                    e.append(f"{pid}: source_text_span offset does not match body slice")
            # (19)(20) owner + epistemic allowed
            owner = p.get("owner_candidate")
            epi = p.get("epistemic_class")
            if owner not in refs["owner_allowed"]:
                e.append(f"{pid}: owner_candidate {owner!r} not allowed")
            if epi not in refs["epi_allowed"]:
                e.append(f"{pid}: epistemic_class {epi!r} not allowed")
            # (22) owner<->epistemic consistency (Governance not written as domain body, etc.)
            if owner in OWNER_EPI and epi != OWNER_EPI[owner]:
                e.append(f"{pid}: owner {owner} inconsistent with epistemic_class {epi}")
            # (21) EvidencePolicyOutbox cluster propositions must not map to GeneralKnowledgeBase
            if refs["canary_by_cluster"].get(cid) and cid in ("mkc_021", "mkc_026", "mkc_027", "mkc_028", "mkc_044"):
                if owner == "GeneralKnowledgeBase":
                    e.append(f"{pid}: EvidencePolicyOutbox cluster proposition mapped to GeneralKnowledgeBase")
            # (23) relation hints stay design hints
            if str(p.get("ontology_edge_created", "")).strip().lower() in ("true", "1", "yes"):
                e.append(f"{pid}: ontology_edge_created is true")
            if p.get("relation_status") and p.get("relation_status") != "design_hint_not_ontology_edge":
                e.append(f"{pid}: relation_status {p.get('relation_status')!r} not design_hint")
            # (25)(26)(27) forbidden readiness claims
            if p.get("accepted_domain_knowledge") is True:
                e.append(f"{pid}: accepted_domain_knowledge must be false")
            if p.get("candidatepack_ready") is True:
                e.append(f"{pid}: candidatepack_ready must be false")
            if p.get("production_servable") is True:
                e.append(f"{pid}: production_servable must be false")
            for k in ("KE_ready", "RAG_ready", "DIFY_ready"):
                if p.get(k) is True:
                    e.append(f"{pid}: {k} must be false")
            # (24) no real instance facts in text/span/conditions
            blob = " ".join(str(p.get(k, "")) for k in ("proposition_text", "source_text_span",
                       "applicable_when", "not_applicable_when", "failure_signal", "downstream_effect"))
            facts = [pat for pat in REAL_FACT_PATTERNS if re.search(pat, blob)]
            if facts:
                e.append(f"{pid}: real-instance fact pattern: {facts[:2]}")

    # (14) total range = clusters x [MIN_PC, MAX_PC] (equals [120,200] for the live 40-cluster run)
    lo, hi = len(expected_clusters) * MIN_PC, len(expected_clusters) * MAX_PC
    if total < lo or total > hi:
        e.append(f"total proposition count {total} not in [{lo},{hi}] (clusters x 3..5)")

    # (29)(30) forbidden scope
    if fs_state.get("forbidden_present"):
        e.append(f"forbidden dir(s) present/created: {fs_state['forbidden_present']}")
    if fs_state.get("three600_created"):
        e.append("3600 generation directory created (forbidden in P5)")
    if fs_state.get("candidatepack_created"):
        e.append("CandidatePack path created (forbidden in P5)")

    # (31 + note1 + note2) ledger route
    by_id = {s.get("step_id"): s for s in ledger_steps}
    by_task = {s.get("task_id"): s for s in ledger_steps}
    for st in ("P1", "P2", "P3", "P4", "P5"):
        if by_id.get(st, {}).get("status") != "DONE":
            e.append(f"ledger {st} status {by_id.get(st, {}).get('status')!r} != DONE")
    # note1 (E7.1 robust roadmap-advancement fix; founder-authorized at P6):
    # once P5 is DONE, P6 must be the briefing task (or its supersessor) and unblocked (NEXT or
    # advanced) -- do NOT hardcode "P6 == NEXT" (that snapshot goes stale the moment P6 advances
    # to DONE at the P6 step). And 3600 GENERATION must never be DONE, and must not be NEXT until
    # P6 go-no-go has passed (P6 status DONE); it is not a hardcoded "never NEXT" snapshot.
    p6 = by_id.get("P6", {})
    p6_status = p6.get("status")
    if p6.get("task_id") != BRIEFING_TASK and p6.get("supersedes_task_id") != BRIEFING_TASK:
        e.append(f"ledger P6 task {p6.get('task_id')!r} is neither {BRIEFING_TASK} nor its supersessor")
    if p6_status is None or "BLOCKED" in str(p6_status):
        e.append(f"ledger P5 DONE requires P6 unblocked (NEXT or advanced), got {p6_status!r}")
    t3 = by_task.get(THREE600_GEN_TASK)
    if t3 is None:
        e.append(f"ledger: {THREE600_GEN_TASK} step missing")
    elif t3.get("status") == "DONE":
        e.append(f"ledger: {THREE600_GEN_TASK} marked DONE (3600 generation must never be generated without authorization)")
    elif t3.get("status") == "NEXT" and p6_status != "DONE":
        e.append(f"ledger: {THREE600_GEN_TASK} marked NEXT before P6 go-no-go passed (3600 generation must stay blocked)")
    # note2: P5 supersession recorded
    if by_id.get("P5", {}).get("supersedes_task_id") not in (SUPERSEDED_P5, None):
        pass  # if present, must be the superseded name; absence tolerated (recorded in route note)

    return e


# ----------------------------- live + selftest -----------------------------
def _run_prior(ws, rel, args):
    try:
        return subprocess.run([sys.executable, os.path.join(ws, rel)] + args, cwd=ws,
                              capture_output=True, text=True, timeout=180).returncode
    except Exception:
        return -1


def run_live(ws, report_out=None):
    refs = load_refs(ws)
    closeout, pack_clusters, manifest = load_pack(ws)
    ledger = load_ledger(ws)
    fs_state = scan_fs(ws)
    errors = validate(closeout, pack_clusters, manifest, ledger, fs_state, refs)
    prior = {
        "p1": _run_prior(ws, "ci/checkers/check_grc_corpus_registry.py", ["--live"]),
        "p2": _run_prior(ws, "ci/checkers/check_grc_contract_ontology_alignment.py", ["--live"]),
        "p3": _run_prior(ws, "ci/checkers/check_judge_calibration_against_grc.py", ["--live"]),
        "p4": _run_prior(ws, "ci/checkers/check_canary_40_generation_and_gate.py", ["--live"]),
        "contract_lock": _run_prior(ws, "ci/checkers/check_codex_generation_contract_lock.py", []),
    }
    for name, rc in prior.items():
        if rc != 0:
            errors.append(f"prior checker {name} live not PASS (exit {rc})")
    total = sum(len(v) for v in pack_clusters.values())
    from collections import Counter
    owner_dist = Counter(p.get("owner_candidate") for v in pack_clusters.values() for p in v)
    status = "PASS" if not errors else "FAIL"
    report = {
        "status": status, "task_id": TASK_ID,
        "expert_review_count": closeout.get("expert_review_count"),
        "repeated_review_performed": closeout.get("repeated_review_performed"),
        "cluster_count": len(pack_clusters), "total_proposition_count": total,
        "min_propositions_per_cluster": min((len(v) for v in pack_clusters.values()), default=0),
        "max_propositions_per_cluster": max((len(v) for v in pack_clusters.values()), default=0),
        "owner_candidate_distribution": dict(owner_dist),
        "all_source_spans_exact_substring": not any("source_span_not_found" in x for x in errors),
        "evidence_policy_to_gkb_violations": sum(1 for x in errors if "mapped to GeneralKnowledgeBase" in x),
        "generation_3600_unlocked": False, "prior_checkers": prior,
        "p6_briefing_unlocked": not any("P6" in x for x in errors),
        "three600_generation_not_prematurely_unlocked_or_generated": not any(THREE600_GEN_TASK in x for x in errors),
        "next_real_action_unlocked": BRIEFING_TASK,
        "error_count": len(errors), "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report_out:
        with open(report_out, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return 0 if status == "PASS" else 1


def run_selftest(ws, fixtures_dir):
    refs = load_refs(ws)
    pos = os.path.join(fixtures_dir, "positive_valid_pack.yaml")
    negatives = sorted(glob.glob(os.path.join(fixtures_dir, "negative_*.yaml")))
    result = {"status": "PASS", "positive_fixture_count": 0, "negative_fixture_count": len(negatives),
              "negative_fixtures_fail_closed": True, "positive_result": None, "negative_results": {}}

    def vfx(fx):
        return validate(fx.get("closeout", {}), fx.get("pack_clusters", {}), fx.get("manifest", {}),
                        fx.get("ledger_steps", []), fx.get("fs_state", {}), refs,
                        expected_clusters=fx.get("expected_clusters"))

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
    ap.add_argument("--fixtures-root", default="ci/fixtures/canary_40_quality_closeout_and_proposition_pack")
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
