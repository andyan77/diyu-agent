#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_generator_capability_proof_microbatch.py  (P7A)

Independently gate the P7A proof microbatch: 40 AI-authored structured drafts
(one per formal cluster mkc_007..046), held to the SAME deterministic dual-gate
bar as the P4 canary. Ground truth is RECOMPUTED here (E12), never trusted from
the proof's own gate reports:

  * anti-copy LCS is recomputed vs gold bodies (<16), vs the P4 canary bodies
    (<18) and cross-cluster (<18); the report's claims are then cross-checked;
  * cluster-specific fingerprint overlap + specificity rank recomputed;
  * red-line scans (no brand/SKU/price real facts, no pipeline governance tokens,
    no abstract style-word stacking) recomputed on every body;
  * owner routing / readiness-all-false / proposition grounding recomputed;
  * the 8 upstream checkers (P1..P6 + P6R + contract-lock) are re-run live inside
    an ephemeral git worktree pinned to HEAD (so P6R's task-scoped git-purity is
    evaluated against the clean committed tree, NOT this task's in-flight files);
  * the ledger route (P1..P6R DONE, P7A DONE, P7 [=P7B] NEXT + re-scoped +
    generation forbidden, P8 blocked) and git-diff-only-allowed-surface recomputed.

HONEST re-scope (founder Option 2): this proves an AI can author 40 gate-passing
drafts; it does NOT prove automatic/stable generation. The checker REQUIRES the
honest labels to be present and false: human_authored=false, generator_capability
_proven=false, ready_for_P7B_3600_generation_brief=false, counts_toward_3600=false.

Fail-closed: refuses to run under `python -O` (asserts disabled) -> exit 2.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

REPO_DEFAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASK_ID = "GKB-GENERATOR-CAPABILITY-PROOF-MICROBATCH-001"
RUN_REL = "07_microbatch_runs/proof_microbatch_001"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
PROP_PACK_REL = "06_canary_runs/canary_40_001/proposition_pack_v1/cluster_propositions.v0.1.yaml"
CANARY_BLOCKS_REL = "06_canary_runs/canary_40_001/canary_rich_body_blocks.v0.1.yaml"
AUTHORITY_REL = "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml"
KIND_OWNER_POLICY_REL = "01_generation_contracts/codex_candidate_kind_target_owner_policy.v0.1.yaml"
LAYER_POLICY_REL = "01_generation_contracts/codex_layer_annotation_policy.v0.1.yaml"

CLUSTERS = [f"mkc_{i:03d}" for i in range(7, 47)]
EXPECTED_TOTAL = 40

MIN_BODY_CHARS = 350
GOLD_COPY_LCS_THRESHOLD = 16
CANARY_COPY_LCS_THRESHOLD = 18
CROSS_CLUSTER_LCS_THRESHOLD = 18
MIN_FP_OVERLAP = 5
SPECIFICITY_RANK_MAX = 5

FORBIDDEN_GOV_TOKENS = [
    "judge", "brief", "batch", "candidatepack", "ke_ready", "rag_ready", "dify_ready",
    "人审", "评测", "gold candidate", "w7", "第几批", "production-ready", "readiness",
    "candidate_kind", "target_owner", "layer_annotation", "semantic_alignment",
    "body_entailment", "dedupe_fingerprint", "readiness_flags", "state_machine_route",
    "route_authority", "control_plane_candidate",
]
REAL_FACT_PATTERNS = [
    r"\d+\s*元", r"￥\s*\d+", r"\$\s*\d+", r"\d+\s*块钱", r"\d+\s*折", r"打\s*\d+\s*折",
    r"(货号|款号|SKU)\s*[:：]?\s*[A-Za-z0-9\-]{3,}", r"库存\s*\d+", r"售价\s*\d+", r"\d+%\s*(off|折扣)",
]
ABSTRACT_STYLE_WORDS = ["高级", "松弛", "自然", "温柔", "有质感", "高档", "精致", "质感感"]

REQUIRED_CARD_FIELDS = [
    "candidate_id", "proof_microbatch_id", "canonical_cluster_id", "generation_assignment_id",
    "candidate_kind", "proposed_target_owner", "declared_layer", "target_layer_candidate",
    "allowed_landing_layers", "forbidden_landing_layers", "source_policy",
    "judge_calibration_refs", "gold_reference_case_refs", "anti_gold_avoidance_refs",
    "do_not_copy_surface_style_refs", "proposition_refs", "body_proposition_refs",
    "creative_gate_refs", "governance_gate_refs", "rich_body_ref", "relation_candidate_refs",
    "readiness_flags", "generation_status",
]
READINESS_KEYS = ["candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "generation_allowed",
                  "generation_eligible", "production_ready", "release_ready", "production_servable"]

# dirs that must NOT be created by this task
NEW_FORBIDDEN_DIRS = ["KE", "serving_projection", "rag", "dify", "candidatepack_etl", "CandidatePack",
                      "RAG", "DIFY", "Serving", "08_consolidated_outputs", "09_candidatepack_eligibility"]
FORBIDDEN_MICROBATCH_SUBDIRS = ["07_microbatch_runs/microbatches", "07_microbatch_runs/batch_summaries"]

ALLOWED_WRITE_PREFIXES = (
    "07_microbatch_runs/proof_microbatch_001/",
    "ci/checkers/check_generator_capability_proof_microbatch.py",
    "ci/fixtures/generator_capability_proof_microbatch/",
    "ci/reports/generator_capability_proof_microbatch_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/grc_generator_capability_proof_microbatch_report.md",
    "docs/reports/grc_generator_capability_proof_microbatch_receipt.json",
)

PRIORS = [
    ("p1", "ci/checkers/check_grc_corpus_registry.py", ["--live"]),
    ("p2", "ci/checkers/check_grc_contract_ontology_alignment.py", ["--live"]),
    ("p3", "ci/checkers/check_judge_calibration_against_grc.py", ["--live"]),
    ("p4", "ci/checkers/check_canary_40_generation_and_gate.py", ["--live"]),
    ("p5", "ci/checkers/check_canary_40_quality_closeout_and_proposition_pack.py", ["--live"]),
    ("p6", "ci/checkers/check_3600_microbatch_briefing_go_nogo.py", ["--live"]),
    ("p6r", "ci/checkers/check_grc_legacy_lock_retire_and_governed_unlock.py", ["--live"]),
    ("contract_lock", "ci/checkers/check_codex_generation_contract_lock.py", []),
]


# ----------------------------- deterministic helpers (mirror P4 math) -----------------------------
def clean(s):
    return re.sub(r"\s+", "", s or "")


def lcs_len(a, b):
    a = clean(a); b = clean(b)
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(len(a)):
        cur = [0] * (len(b) + 1)
        ai = a[i]
        for j in range(len(b)):
            if ai == b[j]:
                cur[j + 1] = prev[j] + 1
                if cur[j + 1] > best:
                    best = cur[j + 1]
        prev = cur
    return best


def body_hash(body):
    return hashlib.sha256(clean(body).encode("utf-8")).hexdigest()


def two_grams(text):
    c = clean(text)
    return set(c[i:i + 2] for i in range(len(c) - 1))


def fingerprint(title, topics, anchors):
    txt = (title or "") + "".join(topics or []) + "".join(str(x) for x in (anchors or []))
    return two_grams(txt)


def gov_tokens_found(body):
    low = (body or "").lower()
    return [t for t in FORBIDDEN_GOV_TOKENS if t.lower() in low]


def real_fact_found(body):
    return [p for p in REAL_FACT_PATTERNS if re.search(p, body or "")]


def abstract_stack_found(body):
    return sum(1 for w in ABSTRACT_STYLE_WORDS if w in (body or "")) >= 3


def specificity(body, cluster_id, fp_by_cluster):
    bg = two_grams(body)
    overlaps = {cid: len(bg & fp) for cid, fp in fp_by_cluster.items()}
    own = overlaps.get(cluster_id, 0)
    rank = 1 + sum(1 for v in overlaps.values() if v > own)
    return own, rank


# ----------------------------- reference loader (read-only, real repo) -----------------------------
def load_refs(ws):
    refs = {"gold": {}, "canary_bodies": {}, "p5_prop_ids": {}, "titles": {}, "topics": {}, "anchors": {},
            "owner_allowed": set(), "kind_allowed": set(), "layer_allowed": set()}
    auth = yaml.safe_load(open(os.path.join(ws, AUTHORITY_REL)))["w7_canonical_cluster_authority"]["records"]
    for r in auth:
        refs["titles"][r["mkc_id"]] = r.get("canonical_title", "")
        refs["topics"][r["mkc_id"]] = r.get("expected_body_topics", []) or []
    for f in sorted(glob.glob(os.path.join(ws, "03_grc_goldset_corpus/normalized/formal_120/p0_0*/gold_reference_cases.yaml"))):
        for c in yaml.safe_load(open(f))["gold_reference_cases"]:
            if c.get("case_type") != "positive_gold":
                continue
            cid = c["cluster_id"]
            bc = c.get("body_contract", {})
            refs["gold"][cid] = {"gold_body": bc.get("gold_body", "")}
            refs["anchors"][cid] = bc.get("apparel_domain_anchors", []) or []
    cb = yaml.safe_load(open(os.path.join(ws, CANARY_BLOCKS_REL)))["canary_40_rich_body_blocks"]["blocks"]
    for b in cb:
        refs["canary_bodies"][b["canonical_cluster_id"]] = b.get("body", "")
    p5 = yaml.safe_load(open(os.path.join(ws, PROP_PACK_REL)))["cluster_propositions"]["clusters"]
    for cid, plist in p5.items():
        refs["p5_prop_ids"][cid] = {p["proposition_id"] for p in plist}
    kop = yaml.safe_load(open(os.path.join(ws, KIND_OWNER_POLICY_REL)))["candidate_kind_target_owner_policy"]
    refs["owner_allowed"] = set(kop.get("proposed_target_owner_allowed", []))
    refs["kind_allowed"] = set(kop.get("candidate_kind_allowed", []))
    lap = yaml.safe_load(open(os.path.join(ws, LAYER_POLICY_REL)))["layer_annotation_policy"]
    refs["layer_allowed"] = set(lap.get("target_layer_candidate_allowed", []))
    return refs


def load_proof(ws):
    d = os.path.join(ws, RUN_REL)

    def j(name):
        return json.load(open(os.path.join(d, name)))

    cards = yaml.safe_load(open(os.path.join(d, "knowledge_candidate_cards.yaml")))["proof_microbatch_candidate_cards"]
    blocks = yaml.safe_load(open(os.path.join(d, "rich_body_blocks.yaml")))["proof_microbatch_rich_body_blocks"]["blocks"]
    trace = yaml.safe_load(open(os.path.join(d, "generator_trace_manifest.v0.1.yaml")))["generator_capability_proof_microbatch_trace"]
    relations = []
    import csv as _csv
    with open(os.path.join(d, "relation_candidates.csv")) as f:
        for row in _csv.DictReader(f):
            relations.append(row)
    return {
        "cards_container": cards, "cards": cards["candidates"], "rich_bodies": blocks, "relations": relations,
        "trace": trace, "dedupe": j("dedupe_report.json"), "style": j("style_copy_report.json"),
        "creative": j("creative_gate_report.json"), "governance": j("governance_gate_report.json"),
        "semantic": j("semantic_alignment_report.json"), "entailment": j("body_entailment_report.json"),
        "receipt": j("generation_receipt.json"),
    }


def load_ledger(ws):
    return yaml.safe_load(open(os.path.join(ws, LEDGER_REL)))["grc_3600_execution_plan_status"]


# ----------------------------- pure validation core -----------------------------
def validate(proof, refs, ledger, fs_state, live, expected_total=EXPECTED_TOTAL, expected_clusters=None):
    """Return list of error strings. Empty == PASS. Pure (no I/O)."""
    if expected_clusters is None:
        expected_clusters = list(CLUSTERS)
    e = []
    cont = proof.get("cards_container") or {}
    cards = proof.get("cards") or []
    blocks = {b.get("canonical_cluster_id"): b for b in (proof.get("rich_bodies") or [])}
    relations = proof.get("relations") or []
    trace = proof.get("trace") or {}

    fp_by_cluster = {cid: fingerprint(refs["titles"].get(cid, ""), refs["topics"].get(cid, []),
                                      refs["anchors"].get(cid, [])) for cid in expected_clusters}

    # (A) top-level honest labels (Option 2)
    for k in ["human_authored", "generator_capability_proven", "automatic_stable_generation_demonstrated",
              "ready_for_P7B_3600_generation_brief", "counts_toward_3600"]:
        if cont.get(k) is not False:
            e.append(f"cards container {k} must be false (honest re-scope), got {cont.get(k)!r}")
    if cont.get("deliverable_kind") != "agent_authored_quality_probe":
        e.append("cards container deliverable_kind must be agent_authored_quality_probe")

    # (B) count / coverage / uniqueness
    if len(cards) != expected_total:
        e.append(f"card count {len(cards)} != {expected_total}")
    seen, ids = {}, {}
    for c in cards:
        cid = c.get("canonical_cluster_id")
        seen[cid] = seen.get(cid, 0) + 1
        cand = c.get("candidate_id")
        ids[cand] = ids.get(cand, 0) + 1
    missing = [c for c in expected_clusters if c not in seen]
    extra = [c for c in seen if c not in expected_clusters]
    dups = [c for c, n in seen.items() if n > 1]
    dup_ids = [i for i, n in ids.items() if n > 1]
    if missing:
        e.append(f"missing clusters: {missing}")
    if extra:
        e.append(f"unexpected clusters: {extra}")
    if dups:
        e.append(f"duplicate cluster: {dups}")
    if dup_ids:
        e.append(f"duplicate candidate_id: {dup_ids}")

    # (C) per-card structural + status + readiness + fields + proposition grounding
    owner_dist = {}
    for c in cards:
        cid = c.get("canonical_cluster_id")
        tag = c.get("candidate_id", cid)
        for fld in REQUIRED_CARD_FIELDS:
            if fld not in c:
                e.append(f"{tag}: missing required field {fld}")
        if c.get("generation_status") != "gpt_generated_structured_draft":
            e.append(f"{tag}: generation_status must be gpt_generated_structured_draft")
        for bad, val in [("accepted_domain_knowledge", c.get("accepted_domain_knowledge")),
                         ("candidatepack_ready", c.get("candidatepack_ready")),
                         ("KE_ready", c.get("KE_ready")), ("RAG_ready", c.get("RAG_ready")),
                         ("DIFY_ready", c.get("DIFY_ready")), ("production_servable", c.get("production_servable"))]:
            if val is not False:
                e.append(f"{tag}: {bad} must be false")
        rf = c.get("readiness_flags") or {}
        for k in READINESS_KEYS:
            if rf.get(k) is not False:
                e.append(f"{tag}: readiness_flags.{k} must be false")
        owner = c.get("proposed_target_owner")
        owner_dist[owner] = owner_dist.get(owner, 0) + 1
        if owner not in refs["owner_allowed"]:
            e.append(f"{tag}: proposed_target_owner {owner!r} not contract-allowed")
        if c.get("candidate_kind") not in refs["kind_allowed"]:
            e.append(f"{tag}: candidate_kind not contract-allowed")
        if c.get("target_layer_candidate") not in refs["layer_allowed"]:
            e.append(f"{tag}: target_layer_candidate not contract-allowed")
        # proposition refs valid against P5
        for pid in (c.get("proposition_refs") or []):
            if pid not in refs["p5_prop_ids"].get(cid, set()):
                e.append(f"{tag}: proposition_ref {pid} not in P5 pack for {cid}")
        if not (c.get("proposition_refs")):
            e.append(f"{tag}: empty proposition_refs")

    # (D) rich body recompute: dual-gate math per body (independent of report claims)
    bodies = {}
    for cid in expected_clusters:
        b = blocks.get(cid)
        if not b:
            e.append(f"missing rich body for {cid}")
            continue
        bodies[cid] = b.get("body", "")
    # per-body checks
    hashes = {}
    for cid, body in bodies.items():
        tag = cid
        n = len(clean(body))
        if n < MIN_BODY_CHARS:
            e.append(f"{tag}: body {n} chars < {MIN_BODY_CHARS}")
        gl = lcs_len(body, refs["gold"].get(cid, {}).get("gold_body", ""))
        if gl >= GOLD_COPY_LCS_THRESHOLD:
            e.append(f"{tag}: gold-body surface copy lcs {gl} >= {GOLD_COPY_LCS_THRESHOLD}")
        cl = lcs_len(body, refs["canary_bodies"].get(cid, ""))
        if cl >= CANARY_COPY_LCS_THRESHOLD:
            e.append(f"{tag}: P4 canary body copy lcs {cl} >= {CANARY_COPY_LCS_THRESHOLD}")
        gt = gov_tokens_found(body)
        if gt:
            e.append(f"{tag}: governance tokens in body: {gt}")
        realf = real_fact_found(body)
        if realf:
            e.append(f"{tag}: real-instance fact leak: {realf}")
        if abstract_stack_found(body):
            e.append(f"{tag}: abstract style-word stacking")
        own, rank = specificity(body, cid, fp_by_cluster)
        if own < MIN_FP_OVERLAP:
            e.append(f"{tag}: fingerprint overlap {own} < {MIN_FP_OVERLAP} (not cluster-anchored)")
        if rank > SPECIFICITY_RANK_MAX:
            e.append(f"{tag}: specificity rank {rank} > {SPECIFICITY_RANK_MAX} (not cluster-specific)")
        b = blocks.get(cid, {})
        if len(b.get("cluster_specific_mechanism_chain") or []) < 3:
            e.append(f"{tag}: mechanism_chain < 3")
        if not b.get("hard_claim_routing"):
            e.append(f"{tag}: missing hard_claim_routing")
        for sub in ["concrete_apparel_anchor", "domain_mechanism", "downstream_content_effect", "risk_boundary_handling"]:
            if not b.get(sub):
                e.append(f"{tag}: missing creative sub-field {sub}")
        # source proposition ids valid
        for pid in (b.get("source_proposition_ids") or []):
            if pid not in refs["p5_prop_ids"].get(cid, set()):
                e.append(f"{tag}: source_proposition_id {pid} not in P5 for {cid}")
        h = body_hash(body)
        if h in hashes:
            e.append(f"{tag}: duplicate body hash with {hashes[h]}")
        hashes[h] = cid

    # cross-cluster LCS
    present = [cid for cid in expected_clusters if cid in bodies]
    worst = 0
    for i in range(len(present)):
        for j in range(i + 1, len(present)):
            L = lcs_len(bodies[present[i]], bodies[present[j]])
            if L > worst:
                worst = L
            if L >= CROSS_CLUSTER_LCS_THRESHOLD:
                e.append(f"cross-cluster template reuse lcs {L} ({present[i]},{present[j]}) >= {CROSS_CLUSTER_LCS_THRESHOLD}")

    # (E) gate reports must exist AND claim PASS AND agree with recompute
    ded = proof.get("dedupe") or {}
    if ded.get("dedupe_pass") is not True:
        e.append("dedupe_report dedupe_pass not true")
    if ded.get("unique_body_hashes") != len(hashes) or ded.get("body_count") != len(present):
        e.append("dedupe_report counts disagree with recompute")
    sty = proof.get("style") or {}
    if sty.get("style_copy_pass") is not True:
        e.append("style_copy_report style_copy_pass not true")
    if sty.get("p4_canary_body_copy_found") is not False:
        e.append("style_copy_report p4_canary_body_copy_found must be false")
    for rep, key in [("creative", "creative_gate_pass"), ("governance", "governance_gate_pass"),
                     ("semantic", "semantic_alignment_pass"), ("entailment", "body_entailment_pass")]:
        r = proof.get(rep) or {}
        if r.get(key) is not True:
            e.append(f"{rep} report {key} not true")
    gov = proof.get("governance") or {}
    if gov.get("evidence_policy_mapped_to_gkb_count") not in (0, None) and gov.get("evidence_policy_mapped_to_gkb_count") != 0:
        e.append("governance_gate evidence_policy_mapped_to_gkb_count must be 0")
    if gov.get("readiness_all_false") is not True:
        e.append("governance_gate readiness_all_false must be true")

    # (F) relations are design hints, not ontology edges
    for r in relations:
        oc = str(r.get("ontology_edge_created", "")).strip().lower()
        fa = str(r.get("formal_ontology_edge_allowed", "")).strip().lower()
        if oc not in ("false", "0", "no", ""):
            e.append(f"relation {r.get('relation_id')} ontology_edge_created must be false")
        if fa not in ("false", "0", "no", ""):
            e.append(f"relation {r.get('relation_id')} formal_ontology_edge_allowed must be false")

    # (G) generator trace manifest — honest provenance
    if trace.get("human_authored") is not False:
        e.append("trace human_authored must be false")
    if trace.get("reused_old_pilot_artifacts") is not False:
        e.append("trace reused_old_pilot_artifacts must be false")
    if trace.get("reused_p4_canary_body") is not False:
        e.append("trace reused_p4_canary_body must be false")
    if trace.get("generated_item_count") != EXPECTED_TOTAL:
        e.append("trace generated_item_count must be 40")
    lim = trace.get("limitations") or {}
    for k in ["generator_capability_proven", "automatic_stable_generation_demonstrated",
              "ready_for_P7B_3600_generation_brief", "counts_toward_3600"]:
        if lim.get(k) is not False:
            e.append(f"trace.limitations.{k} must be false (honest)")
    if not lim.get("does_not_prove"):
        e.append("trace.limitations.does_not_prove must be present (honest)")

    # (H) filesystem: no forbidden materialization
    if fs_state.get("forbidden_present"):
        e.append(f"forbidden dirs present: {fs_state.get('forbidden_present')}")
    if fs_state.get("three600_created"):
        e.append("full 3600 run directory created (forbidden)")
    if fs_state.get("microbatches_created"):
        e.append("official microbatches/batch_summaries directory created (forbidden)")
    if fs_state.get("consolidated_created"):
        e.append("08_consolidated_outputs created (forbidden)")
    if fs_state.get("eligibility_created"):
        e.append("09_candidatepack_eligibility created (forbidden)")

    # (I) ledger route (recomputed on the CURRENT ledger; keeps P6/P6R invariants intact)
    by_id = {s.get("step_id"): s for s in (ledger.get("steps") or [])}
    for sid in ["P1", "P2", "P3", "P4", "P5", "P6", "P6R"]:
        if (by_id.get(sid) or {}).get("status") != "DONE":
            e.append(f"ledger {sid} status must be DONE")
    p7a = by_id.get("P7A") or {}
    if p7a.get("status") != "DONE":
        e.append("ledger P7A status must be DONE")
    if p7a.get("task_id") != TASK_ID:
        e.append(f"ledger P7A task_id must be {TASK_ID}")
    if p7a.get("three600_generation_executed") is not False:
        e.append("ledger P7A three600_generation_executed must be false")
    if p7a.get("generator_capability_proven") is not False:
        e.append("ledger P7A generator_capability_proven must be false (honest)")
    if p7a.get("ready_for_P7B_3600_generation_brief") is not False:
        e.append("ledger P7A ready_for_P7B_3600_generation_brief must be false (honest)")
    p7 = by_id.get("P7") or {}
    if not p7:
        e.append("ledger P7 step missing")
    if p7.get("status") == "DONE":
        e.append("ledger P7 (3600 generation) must not be DONE")
    if p7.get("status") not in ("NEXT", "IN_PROGRESS"):
        e.append(f"ledger P7 must stay NEXT/IN_PROGRESS, got {p7.get('status')!r}")
    if p7.get("unlock_kind") != "governed_incremental_microbatch":
        e.append("ledger P7 unlock_kind must be governed_incremental_microbatch")
    if p7.get("generation_allowed") is not False:
        e.append("ledger P7 generation_allowed must be false")
    if p7.get("one_shot_3600_generation_allowed") is not False:
        e.append("ledger P7 one_shot_3600_generation_allowed must be false")
    p8 = by_id.get("P8") or {}
    if "BLOCKED" not in str(p8.get("status") or "").upper():
        e.append(f"ledger P8 must stay blocked, got {p8.get('status')!r}")
    if ledger.get("generation_unlocked") is not False:
        e.append("ledger generation_unlocked must stay false")
    led_rd = ledger.get("readiness") or {}
    for k, v in led_rd.items():
        if k == "readiness_all_false":
            if v is not True:
                e.append("ledger readiness_all_false must be true")
            continue
        if v not in (False, None):
            e.append(f"ledger readiness {k} must be false")

    # (J) git surface + priors
    outside = live.get("git_changed_outside_allowed")
    if outside:
        e.append(f"git changes outside allowed write surface: {outside}")
    if live.get("project_infra_modified"):
        e.append("project-infra modified (forbidden)")
    if live.get("brief_pack_unmodified") is False:
        e.append("02_generation_brief_pack modified (forbidden)")
    if live.get("contract_or_pilot_modified"):
        e.append("contract / pilot / canary evidence modified (forbidden)")
    priors = live.get("prior_checkers") or {}
    for name, rc in priors.items():
        if rc != 0:
            e.append(f"prior checker {name} not PASS (exit {rc})")

    return e


# ----------------------------- live wiring -----------------------------
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


def compute_live(ws):
    changed = _git_changed(ws)
    outside = [p for p in changed if not p.startswith(ALLOWED_WRITE_PREFIXES)]
    contract_pilot = any(p.startswith("01_generation_contracts/") or p.startswith("03_pilot/")
                         or p.startswith("03_grc_goldset_corpus/") or p.startswith("06_canary_runs/")
                         or p.startswith("04_judge_calibration/") for p in changed)
    return {
        "git_changed": changed,
        "git_changed_outside_allowed": outside,
        "project_infra_modified": "project-infra/current_workspace_status.yaml" in changed,
        "brief_pack_unmodified": not any(p.startswith("02_generation_brief_pack/") for p in changed),
        "contract_or_pilot_modified": contract_pilot,
    }


def scan_fs(ws):
    present = [d for d in NEW_FORBIDDEN_DIRS if os.path.isdir(os.path.join(ws, d))]
    three600 = bool(glob.glob(os.path.join(ws, "04_microbatch_generation", "*3600*")) +
                    glob.glob(os.path.join(ws, "07_microbatch_runs", "*3600*")))
    micro = any(os.path.isdir(os.path.join(ws, d)) for d in FORBIDDEN_MICROBATCH_SUBDIRS)
    return {"forbidden_present": present, "three600_created": three600,
            "microbatches_created": micro,
            "consolidated_created": os.path.isdir(os.path.join(ws, "08_consolidated_outputs")),
            "eligibility_created": os.path.isdir(os.path.join(ws, "09_candidatepack_eligibility"))}


P7A_DELIVERABLE_PATHS = [
    "07_microbatch_runs",
    "ci/checkers/check_generator_capability_proof_microbatch.py",
    "ci/fixtures/generator_capability_proof_microbatch",
    "ci/reports/generator_capability_proof_microbatch_report.v0.1.json",
]


def run_priors_snapshot(ws):
    """Run the 8 upstream checkers against a PRE-P7A snapshot of the working tree.

    Why a snapshot, not the live tree or a git worktree/archive:
      * p6/p6r assert the phase-scoped invariant "07_microbatch_runs must not exist"
        (zero generation); P7A legitimately creates it -> they'd fail on the live tree;
      * p6r's task-scoped git-purity would flag P7A's own in-flight files;
      * p1/p3 read an UNTRACKED working-tree input, so a git-archive/worktree HEAD
        snapshot (tracked-only) makes their nested priors fail.
    The snapshot = working-tree copy MINUS .git and the P7A deliverables, with the
    ledger reset to HEAD. That is exactly the state the upstream checkers validated:
    their untracked deps present, 07_microbatch_runs absent, pre-P7A ledger, and no
    .git (so git-purity is trivially clean). All 8 then pass outright -- no whitelisting."""
    import shutil
    snap = tempfile.mkdtemp(prefix="p7a_snap_")
    try:
        excludes = ["--exclude=.git"] + [f"--exclude={p}" for p in P7A_DELIVERABLE_PATHS]
        rs = subprocess.run(["rsync", "-a"] + excludes + [ws.rstrip("/") + "/", snap + "/"],
                            capture_output=True, text=True)
        if rs.returncode != 0:  # rsync missing -> cp + prune fallback
            subprocess.run(["cp", "-a", ws.rstrip("/") + "/.", snap], capture_output=True, text=True)
        # belt-and-suspenders: ensure .git + P7A deliverables absent in the snapshot
        for rel in [".git"] + P7A_DELIVERABLE_PATHS:
            p = os.path.join(snap, rel)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                os.remove(p)
        # reset ledger to HEAD (pre-P7A state the upstream checkers expect)
        for rel in ["10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
                    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"]:
            h = subprocess.run(["git", "-C", ws, "show", "HEAD:" + rel], capture_output=True, text=True)
            if h.returncode == 0:
                with open(os.path.join(snap, rel), "w") as f:
                    f.write(h.stdout)
        results = {}
        for name, rel, args in PRIORS:
            chk = os.path.join(snap, rel)
            if not os.path.exists(chk):
                results[name] = 98
                continue
            r = subprocess.run([sys.executable, chk] + args, cwd=snap, capture_output=True, text=True)
            results[name] = r.returncode
        return results
    finally:
        shutil.rmtree(snap, ignore_errors=True)


def run_live(ws, report_out=None):
    proof = load_proof(ws)
    refs = load_refs(ws)
    ledger = load_ledger(ws)
    fs_state = scan_fs(ws)
    live = compute_live(ws)
    live["prior_checkers"] = run_priors_snapshot(ws)
    errors = validate(proof, refs, ledger, fs_state, live)
    status = "PASS" if not errors else "FAIL"
    report = {
        "checker": "check_generator_capability_proof_microbatch.py", "task_id": TASK_ID,
        "status": status, "error_count": len(errors), "errors": errors,
        "card_count": len(proof.get("cards") or []),
        "deliverable_kind": (proof.get("cards_container") or {}).get("deliverable_kind"),
        "generator_capability_proven": (proof.get("cards_container") or {}).get("generator_capability_proven"),
        "ready_for_P7B_3600_generation_brief": (proof.get("cards_container") or {}).get("ready_for_P7B_3600_generation_brief"),
        "dedupe": {"unique": (proof.get("dedupe") or {}).get("unique_body_hashes"),
                   "worst_cross_lcs": (proof.get("dedupe") or {}).get("max_cross_cluster_lcs")},
        "style": {"max_gold_lcs": (proof.get("style") or {}).get("max_gold_surface_lcs_title_stripped"),
                  "max_canary_lcs": (proof.get("style") or {}).get("max_p4_canary_body_lcs")},
        "git_changed_outside_allowed": live.get("git_changed_outside_allowed"),
        "prior_checkers": live.get("prior_checkers"),
    }
    if report_out:
        json.dump(report, open(report_out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if status == "PASS" else 1


# ----------------------------- selftest -----------------------------
def _load_fixture(path):
    return yaml.safe_load(open(path))


def selftest(ws):
    fx_dir = os.path.join(ws, "ci/fixtures/generator_capability_proof_microbatch")
    pos = os.path.join(fx_dir, "positive_valid_proof.yaml")
    if not os.path.exists(pos):
        print(json.dumps({"status": "FAIL", "reason": "positive fixture missing"}))
        return 1
    def _run(fx):
        return validate(fx["proof"], _rebuild_refs(fx["refs"]), fx["ledger"], fx["fs_state"], fx["live"],
                        expected_total=fx.get("expected_total", EXPECTED_TOTAL),
                        expected_clusters=fx.get("expected_clusters"))

    fails = []
    fx = _load_fixture(pos)
    perr = _run(fx)
    if perr:
        fails.append(f"positive fixture not clean: {perr}")
    negatives = sorted(glob.glob(os.path.join(fx_dir, "negative_*.yaml")))
    not_failed = []
    for nf in negatives:
        try:
            n = _load_fixture(nf)
            nerr = _run(n)
            if not nerr:
                not_failed.append(os.path.basename(nf))
        except Exception:
            pass  # malformed fixture fails closed by construction
    if not_failed:
        fails.append(f"negatives did NOT fail-closed: {not_failed}")
    status = "PASS" if not fails else "FAIL"
    print(json.dumps({"status": status, "negative_count": len(negatives),
                      "negative_fixtures_fail_closed": not not_failed, "fails": fails}, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def _rebuild_refs(r):
    """Fixtures store refs as plain dicts; fingerprints are recomputed inside validate()."""
    for k in ["gold", "canary_bodies", "titles", "topics", "anchors", "p5_prop_ids"]:
        r.setdefault(k, {})
    for k in ["owner_allowed", "kind_allowed", "layer_allowed"]:
        r[k] = set(r.get(k, []))
    r["p5_prop_ids"] = {cid: set(v) for cid, v in r.get("p5_prop_ids", {}).items()}
    return r


def main():
    if not __debug__:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "refuses to run under python -O (asserts disabled)"}))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "pyyaml unavailable"}))
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO_DEFAULT)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report-out", default=None)
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.repo)
    if a.live:
        return run_live(a.repo, a.report_out)
    ap.error("one of --live / --selftest required")


if __name__ == "__main__":
    sys.exit(main())
