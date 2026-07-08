#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_canary_40_generation_and_gate.py  (P4)

Independently gate the canary-40 controlled generation run against the GRC corpus,
contract, and judge calibration. Ground truth is recomputed here (E12): the manifest's
self-reported numbers are never trusted; owner routing, counts, coverage, body-length,
gold-copy and template-reuse metrics, readiness flags, forbidden-scope, and ledger route
are all recomputed from the actual artifacts + corpus + contract.

Fail-closed: refuses to run under `python -O` (asserts disabled) -> exit 2.

Modes:
  --live       gate the real 06_canary_runs/<run> against the repo; exit 0 PASS / 1 FAIL
  --selftest   run positive + negative fixtures; every negative must fail-closed

Codex Prompt-Pre-Review required notes baked in:
  note1: P4 PASS unlocks ONLY GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001 (or its
         supersessor); the 3600 microbatch task must stay blocked until P6 go-no-go passes and
         must never be DONE (E7.1-robust fix, founder-authorized at P6: not a hardcoded
         "never NEXT" snapshot -- see ledger-route section).
  note2: manifest/receipt assert canary_generation_authorized_for_this_task_only=true,
         global_generation_allowed=false, generation_3600_unlocked=false.
  note3: external_resources/embedding/web_access/source_repo_live_dependency = false.
  note4: negative fixture negative_3600_marked_next_after_canary_pass must FAIL.
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except Exception:  # pragma: no cover - environment guard
    yaml = None

REPO_DEFAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASK_ID = "GKB-CANARY-40-GENERATION-AND-GATE-001"
RUN_REL = "06_canary_runs/canary_40_001"
CLUSTERS = [f"mkc_{i:03d}" for i in range(7, 47)]  # mkc_007..mkc_046
EXPECTED_TOTAL = 40

THREE600_TASK = "GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001"
REVIEW_CLOSEOUT_TASK = "GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001"

MIN_BODY_CHARS = 350
GOLD_COPY_LCS_THRESHOLD = 16       # title-stripped longest common substring with gold_body
TEMPLATE_REUSE_LCS_THRESHOLD = 18  # cross-canary longest common substring
MIN_FP_OVERLAP = 5                 # min 2-gram overlap with own-cluster domain fingerprint
SPECIFICITY_RANK_MAX = 5           # own-cluster fingerprint must rank within top-N of all clusters

# governance / control-plane terms that must not appear as domain-body prose (FC-03/FC-07)
FORBIDDEN_GOV_TOKENS = [
    "judge", "brief", "batch", "candidatepack", "ke_ready", "rag_ready", "dify_ready",
    "人审", "评测", "gold candidate", "w7", "第几批", "production-ready", "readiness",
    "candidate_kind", "target_owner", "layer_annotation", "semantic_alignment",
    "body_entailment", "dedupe_fingerprint", "readiness_flags", "state_machine_route",
    "route_authority", "control_plane_candidate",
]
# real-instance fact leak patterns (FC-10)
REAL_FACT_PATTERNS = [
    r"\d+\s*元", r"￥\s*\d+", r"\$\s*\d+", r"\d+\s*块钱", r"\d+\s*折", r"打\s*\d+\s*折",
    r"(货号|款号|SKU)\s*[:：]?\s*[A-Za-z0-9\-]{3,}", r"库存\s*\d+", r"售价\s*\d+", r"\d+%\s*(off|折扣)",
]
# abstract style-word stacking (FC-08)
ABSTRACT_STYLE_WORDS = ["高级", "松弛", "自然", "温柔", "有质感", "高档", "精致", "质感感"]

CONTRACT_SCHEMA_REL = "01_generation_contracts/codex_generation_output_contract.v0.1.schema.json"
KIND_OWNER_POLICY_REL = "01_generation_contracts/codex_candidate_kind_target_owner_policy.v0.1.yaml"
LAYER_POLICY_REL = "01_generation_contracts/codex_layer_annotation_policy.v0.1.yaml"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
AUTHORITY_REL = "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml"

REQUIRED_CARD_FIELDS = [
    "canary_id", "source_task_id", "canonical_cluster_id", "generation_assignment_id",
    "candidate_kind", "proposed_target_owner", "declared_layer", "target_layer_candidate",
    "allowed_landing_layers", "forbidden_landing_layers", "source_policy",
    "judge_calibration_refs", "gold_reference_case_refs", "anti_gold_avoidance_refs",
    "do_not_copy_surface_style_refs", "body_proposition_refs", "rich_body_ref",
    "relation_candidate_refs", "readiness_flags", "generation_status",
]
READINESS_MUST_BE_FALSE = [
    "candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "generation_allowed",
    "generation_eligible", "production_ready", "release_ready", "production_servable",
]
FORBIDDEN_STATUSES = {"CandidatePack", "KE_candidate", "accepted_domain_knowledge",
                      "production_servable", "generation_eligible", "KE_ready", "RAG_ready", "DIFY_ready"}
FORBIDDEN_DIRS = ["KE", "serving_projection", "rag", "dify", "candidatepack_etl",
                  "CandidatePack", "RAG", "DIFY", "Serving"]


# ----------------------------- helpers -----------------------------
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


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


# ----------------------------- reference loaders (read-only, real repo) -----------------------------
def load_refs(ws):
    """Load contract enums, gold per-cluster routing/body, and cluster titles from the real repo."""
    refs = {"kind_allowed": set(), "owner_allowed": set(), "layer_allowed": set(),
            "gold": {}, "titles": {}, "fingerprints": {}}
    kop = yaml.safe_load(open(os.path.join(ws, KIND_OWNER_POLICY_REL)))["candidate_kind_target_owner_policy"]
    refs["kind_allowed"] = set(kop.get("candidate_kind_allowed", []))
    refs["owner_allowed"] = set(kop.get("proposed_target_owner_allowed", []))
    lap = yaml.safe_load(open(os.path.join(ws, LAYER_POLICY_REL)))["layer_annotation_policy"]
    refs["layer_allowed"] = set(lap.get("target_layer_candidate_allowed", []))
    auth = yaml.safe_load(open(os.path.join(ws, AUTHORITY_REL)))["w7_canonical_cluster_authority"]["records"]
    auth_by_id = {r["mkc_id"]: r for r in auth}
    refs["titles"] = {r["mkc_id"]: r["canonical_title"] for r in auth}
    for f in sorted(glob.glob(os.path.join(ws, "03_grc_goldset_corpus/normalized/formal_120/p0_0*/gold_reference_cases.yaml"))):
        for c in yaml.safe_load(open(f))["gold_reference_cases"]:
            if c["case_type"] != "positive_gold":
                continue
            cid = c["cluster_id"]
            rc = c.get("routing_contract", {})
            bc = c.get("body_contract", {})
            refs["gold"][cid] = {
                "owner": rc.get("storage_target"),
                "kind": rc.get("artifact_kind"),
                "gold_body": bc.get("gold_body", ""),
            }
            # per-cluster domain fingerprint: 2-grams of (title + expected_body_topics + apparel anchors)
            a = auth_by_id.get(cid, {})
            fp_text = (a.get("canonical_title", "") + "".join(a.get("expected_body_topics", []) or [])
                       + "".join(str(x) for x in (bc.get("apparel_domain_anchors", []) or [])))
            fpc = clean(fp_text)
            refs["fingerprints"][cid] = set(fpc[i:i + 2] for i in range(len(fpc) - 1))
    return refs


def scan_fs(ws):
    """Real filesystem probe for forbidden scope + 3600/CandidatePack materialization."""
    present = []
    for d in FORBIDDEN_DIRS:
        p = os.path.join(ws, d)
        if os.path.isdir(p):
            present.append(d)
    three600 = bool(glob.glob(os.path.join(ws, "04_microbatch_generation", "*3600*")) +
                    glob.glob(os.path.join(ws, "*3600_generation*")) +
                    glob.glob(os.path.join(ws, "06_canary_runs", "*3600*")))
    cp = os.path.isdir(os.path.join(ws, "CandidatePack")) or os.path.isdir(os.path.join(ws, "candidatepack_etl", "candidatepack_instances"))
    return {"forbidden_present": present, "three600_created": three600, "candidatepack_created": cp}


def load_run_from_dir(ws, run_rel):
    d = os.path.join(ws, run_rel)
    cards = yaml.safe_load(open(os.path.join(d, "canary_candidate_cards.v0.1.yaml")))["canary_40_candidate_cards"]["candidates"]
    blocks = yaml.safe_load(open(os.path.join(d, "canary_rich_body_blocks.v0.1.yaml")))["canary_40_rich_body_blocks"]["blocks"]
    manifest = yaml.safe_load(open(os.path.join(d, "canary_generation_manifest.v0.1.yaml")))["canary_generation_manifest"]
    relations = []
    with open(os.path.join(d, "canary_relation_candidates.v0.1.csv")) as f:
        for row in csv.DictReader(f):
            relations.append(row)
    return {"cards": cards, "rich_bodies": blocks, "relations": relations, "manifest": manifest}


def load_ledger_steps(ws):
    led = yaml.safe_load(open(os.path.join(ws, LEDGER_REL)))["grc_3600_execution_plan_status"]
    return led.get("steps", []), led


# ----------------------------- pure validation core -----------------------------
def validate_canary(run, ledger_steps, fs_state, refs,
                    expected_total=EXPECTED_TOTAL, expected_clusters=None):
    """Return a list of error strings. Empty list == PASS. Pure (no I/O)."""
    if expected_clusters is None:
        expected_clusters = list(CLUSTERS)
    e = []
    cards = run.get("cards") or []
    blocks = {b.get("rich_body_id") or b.get("canary_id"): b for b in (run.get("rich_bodies") or [])}
    body_by_cluster = {b.get("canonical_cluster_id"): b for b in (run.get("rich_bodies") or [])}
    relations = run.get("relations") or []
    manifest = run.get("manifest") or {}

    # (5) total count
    if len(cards) != expected_total:
        e.append(f"canary total count {len(cards)} != expected {expected_total}")

    # (6)(7) cluster coverage exactly, one per cluster
    seen = {}
    for c in cards:
        seen[c.get("canonical_cluster_id")] = seen.get(c.get("canonical_cluster_id"), 0) + 1
    missing = [c for c in expected_clusters if c not in seen]
    extra = [c for c in seen if c not in expected_clusters]
    dups = [c for c, n in seen.items() if n > 1]
    if missing:
        e.append(f"missing cluster canary: {missing}")
    if extra:
        e.append(f"unexpected cluster canary: {extra}")
    if dups:
        e.append(f"duplicate cluster canary: {dups}")

    for c in cards:
        cid = c.get("canonical_cluster_id")
        tag = c.get("canary_id", cid)
        # (8) required fields
        for fld in REQUIRED_CARD_FIELDS:
            if fld not in c:
                e.append(f"{tag}: missing required field {fld}")
        # (9)(10) output status
        st = c.get("generation_status")
        if st != "gpt_generated_structured_draft":
            e.append(f"{tag}: generation_status {st!r} != gpt_generated_structured_draft")
        if st in FORBIDDEN_STATUSES:
            e.append(f"{tag}: forbidden output status {st!r}")
        # (11) candidate_kind allowed
        kind = c.get("candidate_kind")
        if kind not in refs["kind_allowed"]:
            e.append(f"{tag}: candidate_kind {kind!r} not contract-allowed")
        # (12) proposed_target_owner allowed
        owner = c.get("proposed_target_owner")
        if owner not in refs["owner_allowed"]:
            e.append(f"{tag}: proposed_target_owner {owner!r} not contract-allowed")
        # owner routing vs gold (per-cluster ground truth)
        gold = refs["gold"].get(cid)
        if gold:
            if owner != gold["owner"]:
                e.append(f"{tag}: owner {owner!r} != gold routing {gold['owner']!r} for {cid}")
            if kind != gold["kind"]:
                e.append(f"{tag}: candidate_kind {kind!r} != gold artifact_kind {gold['kind']!r} for {cid}")
        # (13)(14) EvidencePolicyOutbox must stay EPO, never GeneralKnowledgeBase
        if gold and gold["owner"] == "EvidencePolicyOutbox":
            if owner != "EvidencePolicyOutbox":
                e.append(f"{tag}: EvidencePolicyOutbox cluster {cid} misrouted to {owner!r}")
            if owner == "GeneralKnowledgeBase" or c.get("target_layer_candidate") == "GeneralKnowledgeBase":
                e.append(f"{tag}: EvidencePolicyOutbox mapped to GeneralKnowledgeBase")
        # layer enum + owner/layer consistency
        layer = c.get("target_layer_candidate")
        if layer is not None and layer not in refs["layer_allowed"]:
            e.append(f"{tag}: target_layer_candidate {layer!r} not layer-policy-allowed")
        if owner == "EvidencePolicyOutbox" and layer != "EvidencePolicy_candidate":
            e.append(f"{tag}: EvidencePolicyOutbox layer {layer!r} must be EvidencePolicy_candidate")
        if owner == "GeneralKnowledgeBase" and layer == "EvidencePolicy_candidate":
            e.append(f"{tag}: GeneralKnowledgeBase card must not use EvidencePolicy_candidate layer")
        # forbidden landing layers must not include the declared layer
        if layer in (c.get("forbidden_landing_layers") or []):
            e.append(f"{tag}: declared layer {layer!r} listed in forbidden_landing_layers")
        # (25) readiness all false
        rf = c.get("readiness_flags") or {}
        for k in READINESS_MUST_BE_FALSE:
            if rf.get(k) is True:
                e.append(f"{tag}: readiness flag {k} must be false")
        # (18)(19)(21) rich body checks
        rb = body_by_cluster.get(cid)
        if not rb:
            e.append(f"{tag}: no rich body block for {cid}")
            continue
        body = rb.get("body", "") or ""
        n = len(clean(body))
        if n == 0:
            e.append(f"{tag}: empty body")
        # (18) not index shell / min chars
        if n < MIN_BODY_CHARS:
            e.append(f"{tag}: body {n} chars < min {MIN_BODY_CHARS} (index-shell/too short)")
        # cluster-specific mechanism present: >=1 mechanism-chain token appears
        mech = rb.get("cluster_specific_mechanism_chain") or []
        if not mech:
            e.append(f"{tag}: no cluster_specific_mechanism_chain")
        # domain density + cluster-specificity via own-cluster domain fingerprint (2-gram overlap):
        # a generic/templated body overlaps all clusters ~equally; a cluster-specific body ranks its
        # own cluster near the top and clears an absolute density floor.
        fps = refs.get("fingerprints") or {}
        if fps.get(cid):
            cb = clean(body)
            own_ov = sum(1 for g in fps[cid] if g in cb)
            if own_ov < MIN_FP_OVERLAP:
                e.append(f"{tag}: domain-density fingerprint overlap {own_ov} < {MIN_FP_OVERLAP} (generic/low-density body)")
            better = sum(1 for oc, gg in fps.items() if oc != cid and sum(1 for g in gg if g in cb) > own_ov)
            if better + 1 > SPECIFICITY_RANK_MAX:
                e.append(f"{tag}: body not cluster-specific (own-cluster fingerprint rank {better + 1} > {SPECIFICITY_RANK_MAX})")
        # (19) no governance text in body
        low = body.lower()
        gov = [t for t in FORBIDDEN_GOV_TOKENS if t in low]
        if gov:
            e.append(f"{tag}: governance/control-plane text in body: {gov[:3]}")
        # (16) no real instance fact
        facts = [p for p in REAL_FACT_PATTERNS if re.search(p, body)]
        if facts:
            e.append(f"{tag}: real-instance fact pattern in body: {facts[:2]}")
        # FC-08 abstract style stacking
        stack = sum(body.count(w) for w in ABSTRACT_STYLE_WORDS)
        if stack >= 3:
            e.append(f"{tag}: abstract style-word stacking count {stack} (surface-style-copy risk)")
        # (21) gold body surface copy
        if gold:
            title = refs["titles"].get(cid, "")
            a = clean(body).replace(clean(title), "")
            b = clean(gold["gold_body"]).replace(clean(title), "")
            gl = lcs_len(a, b)
            if gl >= GOLD_COPY_LCS_THRESHOLD:
                e.append(f"{tag}: gold-body surface copy lcs {gl} >= {GOLD_COPY_LCS_THRESHOLD}")

    # (22)(23) cross-cluster template reuse + dedupe
    body_texts = [(b.get("canonical_cluster_id"), b.get("body", "")) for b in (run.get("rich_bodies") or [])]
    hashes = {}
    for cid, bt in body_texts:
        h = sha256_bytes(clean(bt).encode("utf-8"))
        hashes.setdefault(h, []).append(cid)
    dup_hash = {h: v for h, v in hashes.items() if len(v) > 1}
    if dup_hash:
        e.append(f"identical bodies across clusters (dedupe): {list(dup_hash.values())[:3]}")
    worst = 0
    worst_pair = None
    for i in range(len(body_texts)):
        for j in range(i + 1, len(body_texts)):
            L = lcs_len(body_texts[i][1], body_texts[j][1])
            if L > worst:
                worst = L
                worst_pair = (body_texts[i][0], body_texts[j][0])
    if worst >= TEMPLATE_REUSE_LCS_THRESHOLD:
        e.append(f"cross-cluster template reuse lcs {worst} >= {TEMPLATE_REUSE_LCS_THRESHOLD} ({worst_pair})")

    # (15) relations are design hints, not ontology edges
    for r in relations:
        oc = str(r.get("ontology_edge_created", "")).strip().lower()
        fa = str(r.get("formal_ontology_edge_allowed", "")).strip().lower()
        rs = str(r.get("relation_status", ""))
        if oc in ("true", "1", "yes"):
            e.append(f"relation {r.get('relation_id')}: ontology_edge_created is true")
        if fa in ("true", "1", "yes"):
            e.append(f"relation {r.get('relation_id')}: formal_ontology_edge_allowed is true")
        if rs and rs != "design_hint_not_ontology_edge":
            e.append(f"relation {r.get('relation_id')}: relation_status {rs!r} not design_hint")

    # (20) no P0-00 control plane leakage: no canary owns ControlPlaneContractSource, no mkc_001..006
    for c in cards:
        if c.get("proposed_target_owner") == "ControlPlaneContractSource":
            e.append(f"{c.get('canary_id')}: control-plane owner leaked into canary")
        cid = c.get("canonical_cluster_id") or ""
        m = re.match(r"mkc_(\d+)", cid)
        if m and int(m.group(1)) <= 6:
            e.append(f"{c.get('canary_id')}: P0-00 control cluster {cid} present in canary set")

    # (2 note)(25 manifest)(26)(27)(28) manifest authorization + readiness + no downstream
    mf = manifest
    if mf.get("canary_generation_authorized_for_this_task_only") is not True:
        e.append("manifest: canary_generation_authorized_for_this_task_only must be true")
    for k in ("global_generation_allowed", "generation_3600_unlocked", "external_resources_allowed",
              "embedding_allowed", "web_access_allowed", "source_repo_live_dependency"):
        if mf.get(k) is not False:
            e.append(f"manifest: {k} must be false")
    mrf = mf.get("readiness_flags") or {}
    for k in READINESS_MUST_BE_FALSE:
        if mrf.get(k) is True:
            e.append(f"manifest readiness flag {k} must be false")
    if mf.get("object_count", 0) != 0:
        e.append("manifest: object_count must be 0")
    if mf.get("evidence_policy_mapped_to_gkb_count", 0) != 0:
        e.append("manifest: evidence_policy_mapped_to_gkb_count must be 0")

    # (27)(28) forbidden scope / 3600 / candidatepack
    if fs_state.get("forbidden_present"):
        e.append(f"forbidden dir(s) present/created: {fs_state['forbidden_present']}")
    if fs_state.get("three600_created"):
        e.append("3600 generation directory created (forbidden in P4)")
    if fs_state.get("candidatepack_created"):
        e.append("CandidatePack path created (forbidden in P4)")

    # (29 + note1 + note4) ledger route
    steps = {s.get("task_id"): s for s in ledger_steps}
    by_id = {s.get("step_id"): s for s in ledger_steps}
    def status_of(task):
        s = steps.get(task)
        return s.get("status") if s else None
    p1 = by_id.get("P1", {}).get("status")
    p2 = by_id.get("P2", {}).get("status")
    p3 = by_id.get("P3", {}).get("status")
    p4 = by_id.get("P4", {}).get("status")
    if p1 != "DONE":
        e.append(f"ledger P1 status {p1!r} != DONE")
    if p2 != "DONE":
        e.append(f"ledger P2 status {p2!r} != DONE")
    if p3 != "DONE":
        e.append(f"ledger P3 status {p3!r} != DONE")
    if p4 != "DONE":
        e.append(f"ledger P4 status {p4!r} != DONE (P4 must be DONE when checker passes)")
    # note1 (E7.1 robust roadmap-advancement rule; founder-authorized fix at P5):
    # once P4 is DONE, P5 must be the review-closeout task OR its superseding task, and must be
    # unblocked (NEXT or advanced/DONE), never blocked-by-P4. Do NOT hard-require the specific
    # task name to be exactly NEXT (that snapshot breaks the moment P5 supersedes/advances).
    p5_step = by_id.get("P5", {})
    p5_task = p5_step.get("task_id")
    p5_supersedes = p5_step.get("supersedes_task_id")
    p5_status = p5_step.get("status")
    if p4 == "DONE":
        if p5_task != REVIEW_CLOSEOUT_TASK and p5_supersedes != REVIEW_CLOSEOUT_TASK:
            e.append(f"ledger P5 is neither {REVIEW_CLOSEOUT_TASK} nor its supersessor (got {p5_task!r})")
        if p5_status in (None, "BLOCKED_BY_P4"):
            e.append(f"ledger P4 DONE requires P5 unblocked (NEXT or advanced), got {p5_status!r}")
    # note1/note4 (E7.1 robust roadmap-advancement fix; founder-authorized at P6):
    # the real invariant is that 3600 generation is never actually GENERATED/DONE without
    # authorization, and must stay blocked *until P6 briefing/go-no-go passes* -- NOT that it
    # can never be NEXT. A hardcoded "must not be NEXT" snapshot goes stale the moment P6
    # legitimately advances 3600 generation to the brief-only NEXT step. Assert: never DONE,
    # and not NEXT while P6 has not yet reached DONE.
    t3_status = status_of(THREE600_TASK)
    p6_status = by_id.get("P6", {}).get("status")
    if t3_status is None:
        e.append(f"ledger: {THREE600_TASK} step missing")
    elif t3_status == "DONE":
        e.append(f"ledger: {THREE600_TASK} marked DONE (no 3600 generation is authorized/executed at canary stage)")
    elif t3_status == "NEXT" and p6_status != "DONE":
        e.append(f"ledger: {THREE600_TASK} marked NEXT before P6 go-no-go passed (3600 must stay blocked)")

    return e


# ----------------------------- live + selftest -----------------------------
def _run_prior_checker(ws, rel, args):
    try:
        r = subprocess.run([sys.executable, os.path.join(ws, rel)] + args,
                           cwd=ws, capture_output=True, text=True, timeout=180)
        return r.returncode
    except Exception as ex:
        return -1


def run_live(ws, run_rel, report_out=None):
    refs = load_refs(ws)
    run = load_run_from_dir(ws, run_rel)
    ledger_steps, _ = load_ledger_steps(ws)
    fs_state = scan_fs(ws)
    errors = validate_canary(run, ledger_steps, fs_state, refs)

    # (1)(2)(3)(4) prior checkers live PASS (read-only; none assert P4/P5-advancing state)
    prior = {
        "p1_corpus": _run_prior_checker(ws, "ci/checkers/check_grc_corpus_registry.py", ["--live"]),
        "p2_alignment": _run_prior_checker(ws, "ci/checkers/check_grc_contract_ontology_alignment.py", ["--live"]),
        "p3_judge_calibration": _run_prior_checker(ws, "ci/checkers/check_judge_calibration_against_grc.py", ["--live"]),
        "contract_lock": _run_prior_checker(ws, "ci/checkers/check_codex_generation_contract_lock.py", []),
    }
    for name, rc in prior.items():
        if rc != 0:
            errors.append(f"prior checker {name} live not PASS (exit {rc})")

    owner_dist = {}
    for c in run["cards"]:
        owner_dist[c["proposed_target_owner"]] = owner_dist.get(c["proposed_target_owner"], 0) + 1
    status = "PASS" if not errors else "FAIL"
    report = {
        "status": status,
        "task_id": TASK_ID,
        "run": run_rel,
        "canary_total": len(run["cards"]),
        "cluster_coverage": "mkc_007..mkc_046" if not any("cluster" in e for e in errors) else "INCOMPLETE",
        "per_cluster_exactly_one": not any("duplicate cluster" in e or "missing cluster" in e for e in errors),
        "owner_distribution": owner_dist,
        "evidence_policy_owner_cases": owner_dist.get("EvidencePolicyOutbox", 0),
        "evidence_policy_mapped_to_gkb": 0,
        "generation_status_all_gpt_generated_structured_draft": all(
            c.get("generation_status") == "gpt_generated_structured_draft" for c in run["cards"]),
        "prior_checkers": prior,
        "readiness_all_false": not any("readiness" in e for e in errors),
        "generation_3600_unlocked": False,
        "global_generation_allowed": False,
        "canary_generation_authorized_for_this_task_only": True,
        "p5_review_closeout_unlocked": not any(REVIEW_CLOSEOUT_TASK in e for e in errors),
        "three600_task_not_prematurely_unlocked_or_generated": not any(THREE600_TASK in e for e in errors),
        "recommended_next_step": REVIEW_CLOSEOUT_TASK,
        "error_count": len(errors),
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report_out:
        with open(report_out, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return 0 if status == "PASS" else 1


def run_selftest(ws, fixtures_dir):
    refs = load_refs(ws)
    pos = os.path.join(fixtures_dir, "positive_valid_canary_run.yaml")
    negatives = sorted(glob.glob(os.path.join(fixtures_dir, "negative_*.yaml")))
    result = {"status": "PASS", "positive_fixture_count": 0, "negative_fixture_count": len(negatives),
              "negative_fixtures_fail_closed": True, "negative_results": {}, "positive_result": None}

    def load_fx(path):
        with open(path) as f:
            return yaml.safe_load(f)

    def validate_fx(fx):
        run = {"cards": fx.get("cards", []), "rich_bodies": fx.get("rich_bodies", []),
               "relations": fx.get("relations", []), "manifest": fx.get("manifest", {})}
        return validate_canary(run, fx.get("ledger_steps", []), fx.get("fs_state", {}), refs,
                              expected_total=fx.get("expected_total", EXPECTED_TOTAL),
                              expected_clusters=fx.get("expected_clusters"))

    # positive
    try:
        fx = load_fx(pos)
        errs = validate_fx(fx)
        result["positive_fixture_count"] = 1
        result["positive_result"] = errs
        if errs:
            result["status"] = "FAIL"
    except Exception as ex:
        result["status"] = "FAIL"
        result["positive_result"] = [f"positive fixture load error: {ex}"]

    # negatives: each must produce >=1 error (fail-closed). malformed => load error counts as closed.
    for nf in negatives:
        name = os.path.basename(nf)
        try:
            fx = load_fx(nf)
            errs = validate_fx(fx)
            if not errs:
                result["negative_fixtures_fail_closed"] = False
                result["status"] = "FAIL"
                result["negative_results"][name] = ["DID NOT FAIL (expected >=1 error)"]
            else:
                result["negative_results"][name] = errs[:3]
        except Exception as ex:
            result["negative_results"][name] = [f"malformed rejected (fail-closed): {ex.__class__.__name__}"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


def main():
    # fail-closed: refuse to run under python -O (asserts disabled)
    if not __debug__:
        print(json.dumps({"status": "FAIL-CLOSED",
                          "reason": "python -O disables asserts; canary gate refuses to run"}))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL-CLOSED", "reason": "pyyaml unavailable"}))
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", default=REPO_DEFAULT)
    ap.add_argument("--run-rel", default=RUN_REL)
    ap.add_argument("--fixtures-root", default="ci/fixtures/canary_40_generation_and_gate")
    ap.add_argument("--report-out")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    ws = os.path.abspath(a.workspace_root)
    # sanity assert (bypassed under -O, already refused above)
    assert os.path.isdir(ws), "workspace root must exist"
    if a.selftest:
        return run_selftest(ws, os.path.join(ws, a.fixtures_root))
    if a.live:
        return run_live(ws, a.run_rel, a.report_out)
    ap.error("one of --live / --selftest required")


if __name__ == "__main__":
    sys.exit(main())
