#!/usr/bin/env python3
"""
check_scoped_120_content_production_microbatch_generation.py  (P7C-GEN)

Independently gate the scoped-120 content-production microbatch generation. This task GENERATES
exactly 120 execution-AI-authored structured drafts (07_microbatch_runs/scoped_content_microbatch_
120_001/**), one per P7C-BRIEF assignment. It does NOT authorize 320 / 3600 / CandidatePack /
Four-Gate / KE / Serving / RAG / DIFY / production, and flips no readiness flag.

Independent-recompute discipline (Codex Pre-Review required fixes 3-5):
  * REFERENCE INTEGRITY (fix 4): every draft's assignment_id / target_output_id / cluster / p0_group /
    generation_mode / proposition_refs / gold+anti-gold refs / creative_pattern_refs / owner must
    EQUAL the consumed P7C-BRIEF assignment. Drafts consume assignments; they never rewrite them.
  * ASSIGNMENTS IMMUTABLE (fix 3): the P7C-BRIEF briefing dir + P7B alignment + proof + every
    committed checker must be unmodified in the live git surface.
  * BODY RECOMPUTE (fix 5): every quality gate (min chars, anti-copy LCS vs gold/canary/proof +
    cross-draft, governance/meta-vocab, real-fact leak, abstract-style stacking, cluster fingerprint,
    checklist leakage, per-mode fact rule) is RE-DERIVED from the body text, not read off a report.
    Report files must ALSO exist, claim PASS, and AGREE with the recompute.
  * Provenance honesty (fix 6): generation_receipt must declare execution-AI-authored scoped drafts
    and must NOT re-badge this as "automatic generator capability proven".

Route (Codex fix 2 / founder additive precedent): P7A stays status=DONE with classification=
agent_authored_quality_probe_pass (committed P7A/P7B checkers read P7A==DONE). This task ADDS the
generation outcome: P7C-GEN=DONE, P7C-REVIEW=NEXT, P7D=BLOCKED_BY_P7C_REVIEW, P8=BLOCKED_BY_P7D;
generation_unlocked stays false; route_migration_3 records it. No committed checker is edited.

Prior snapshots: the committed P7C-BRIEF checker hard-reads P7C-GEN==NEXT / P7D==BLOCKED_BY_P7C_GEN
and asserts 07_microbatch_runs == {proof_microbatch_001}. After this task both are false on the live
tree, so P7C-BRIEF (and P7A/P7B, which reject unexpected run dirs) run in a PRE-GENERATION snapshot:
07_microbatch_runs/scoped_content_microbatch_120_001 removed and the ledger reset to HEAD. P1..P6R +
contract-lock run in a no-07_microbatch_runs snapshot. No .git in either -> git-purity trivially
clean. No whitelisting.

Fail-closed: refuses to run under `python -O`; refuses without pyyaml.
"""
import argparse
import csv as _csv
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
except Exception:
    yaml = None

REPO_DEFAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASK_ID = "GKB-SCOPED-120-CONTENT-PRODUCTION-MICROBATCH-GENERATION-001"
RUN_ID = "scoped_content_microbatch_120_001"
RUN_REL = f"07_microbatch_runs/{RUN_ID}"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
# Immutable pre-generation baseline (this task's HEAD_BEFORE). Priors run in a snapshot whose ledger
# is pinned here so "pre-generation snapshot" stays pre-generation after this task's own commit —
# keeps the checker idempotent / re-verifiable at any HEAD.
PRE_GEN_BASELINE = "f99e9608238e799d6647df2c6aee8945844ad491"
PROP_PACK_REL = "06_canary_runs/canary_40_001/proposition_pack_v1/cluster_propositions.v0.1.yaml"
CANARY_BLOCKS_REL = "06_canary_runs/canary_40_001/canary_rich_body_blocks.v0.1.yaml"
PROOF_BLOCKS_REL = "07_microbatch_runs/proof_microbatch_001/rich_body_blocks.yaml"
AUTHORITY_REL = "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml"
KIND_OWNER_POLICY_REL = "01_generation_contracts/codex_candidate_kind_target_owner_policy.v0.1.yaml"
LAYER_POLICY_REL = "01_generation_contracts/codex_layer_annotation_policy.v0.1.yaml"
SCOPE_DIR = "07_microbatch_briefing/scoped_content_microbatch_120"
ALIGN_DIR = "07_microbatch_briefing/generation_mode_cso_alignment"
ASSIGN_PLAN_REL = f"{SCOPE_DIR}/scoped_120_assignment_plan.v0.1.yaml"

CLUSTERS = [f"mkc_{i:03d}" for i in range(7, 47)]
EXPECTED_TOTAL = 120
EXPECTED_MODE_DIST = {"creative_prototype": 36, "fact_slot_script": 36,
                      "evidence_bound_candidate": 24, "display_solution": 24}

# ---- canonical deterministic bar (identical to P7A) ----
MIN_BODY_CHARS = 350
GOLD_COPY_LCS_THRESHOLD = 16
CANARY_COPY_LCS_THRESHOLD = 18
CROSS_LCS_THRESHOLD = 18
MIN_FP_OVERLAP = 5
SPECIFICITY_RANK_MAX = 5
CHECKLIST_SCAFFOLD_MAX = 3

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
SLOT_MARKER_RE = re.compile(r"【[^】]{2,}】")
CHECKLIST_SCAFFOLD_RE = re.compile(r"(?:^|\n|；|;)\s*(?:[0-9]{1,2}|[一二三四五六七八九十])\s*[、.)．：:]")

OWNER_KIND_LAYER = {
    "GeneralKnowledgeBase": ("general_knowledge_candidate", "TBox_candidate"),
    "EvidencePolicyOutbox": ("evidence_policy_candidate", "EvidencePolicy_candidate"),
    "GovernanceOutbox": ("governance_outbox_candidate", "GovernanceContract_candidate"),
    "ExecutionAssetOutbox": ("execution_asset_outbox_candidate", "ExecutionAssetOutbox_candidate"),
    "SourceGapLedger": ("source_gap", "SourceGapLedger"),
}
DOWNGRADE_SIGNALS = ["待补", "先按住", "挂起", "无源", "无法断言", "需官方", "需检测", "需来源",
                     "缺来源", "缺材料", "观察", "先空", "暂不下结论", "不硬下", "有依据"]

REQUIRED_CARD_FIELDS = [
    "candidate_id", "run_id", "canonical_cluster_id", "generation_assignment_id", "target_output_id",
    "p0_group", "candidate_kind", "proposed_target_owner", "declared_layer", "target_layer_candidate",
    "allowed_landing_layers", "forbidden_landing_layers", "source_policy", "proposition_refs",
    "body_proposition_refs", "gold_reference_case_refs", "anti_gold_avoidance_refs",
    "creative_pattern_refs", "generation_mode", "cso_overlay_requirements", "creative_gate_refs",
    "governance_gate_refs", "rich_body_ref", "relation_candidate_refs", "readiness_flags",
    "generation_status",
]
REQUIRED_BODY_SUBFIELDS = ["concrete_apparel_anchor", "domain_mechanism",
                           "downstream_content_effect", "risk_boundary_handling"]
READINESS_KEYS = ["candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "generation_allowed",
                  "generation_eligible", "production_ready", "release_ready", "production_servable"]

NEW_FORBIDDEN_DIRS = ["KE", "serving_projection", "rag", "dify", "candidatepack_etl", "CandidatePack",
                      "RAG", "DIFY", "Serving", "08_consolidated_outputs", "09_candidatepack_eligibility",
                      "07_microbatch_runs/microbatches", "07_microbatch_runs/batch_summaries"]

ALLOWED_WRITE_PREFIXES = (
    f"07_microbatch_runs/{RUN_ID}/",
    "ci/checkers/check_scoped_120_content_production_microbatch_generation.py",
    "ci/fixtures/scoped_120_content_production_microbatch_generation/",
    "ci/reports/scoped_120_content_production_microbatch_generation_report.v0.1.json",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
    "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    "docs/reports/grc_scoped_120_content_production_microbatch_generation_report.md",
    "docs/reports/grc_scoped_120_content_production_microbatch_generation_receipt.json",
)
COMMITTED_CHECKERS = [
    "ci/checkers/check_grc_corpus_registry.py",
    "ci/checkers/check_grc_contract_ontology_alignment.py",
    "ci/checkers/check_judge_calibration_against_grc.py",
    "ci/checkers/check_canary_40_generation_and_gate.py",
    "ci/checkers/check_canary_40_quality_closeout_and_proposition_pack.py",
    "ci/checkers/check_3600_microbatch_briefing_go_nogo.py",
    "ci/checkers/check_grc_legacy_lock_retire_and_governed_unlock.py",
    "ci/checkers/check_codex_generation_contract_lock.py",
    "ci/checkers/check_generator_capability_proof_microbatch.py",
    "ci/checkers/check_proof_microbatch_closeout_and_generation_mode_cso_alignment.py",
    "ci/checkers/check_scoped_content_microbatch_brief_go_nogo.py",
]

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
    ("p7c_brief", "ci/checkers/check_scoped_content_microbatch_brief_go_nogo.py", ["--live"]),
]


# ----------------------------- deterministic helpers (mirror P4/P7A math) -----------------------------
def clean(s):
    return re.sub(r"\s+", "", s or "")

def lcs_len(a, b):
    a = clean(a); b = clean(b)
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1); best = 0
    for i in range(len(a)):
        cur = [0] * (len(b) + 1); ai = a[i]
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

def kgrams(text, k):
    c = clean(text)
    return set(c[i:i + k] for i in range(len(c) - k + 1))

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

def checklist_scaffold_count(body):
    return len(CHECKLIST_SCAFFOLD_RE.findall(body or ""))

def specificity(body, cluster_id, fp_by_cluster):
    bg = two_grams(body)
    overlaps = {cid: len(bg & fp) for cid, fp in fp_by_cluster.items()}
    own = overlaps.get(cluster_id, 0)
    rank = 1 + sum(1 for v in overlaps.values() if v > own)
    return own, rank

def cross_draft_collisions(bodies_by_tag, k=CROSS_LCS_THRESHOLD):
    gram_owner = {}; hits = []
    for tag, body in bodies_by_tag.items():
        for g in kgrams(body, k):
            if g in gram_owner and gram_owner[g] != tag:
                hits.append((gram_owner[g], tag))
            else:
                gram_owner[g] = tag
    return hits


# ----------------------------- pure validation core -----------------------------
def validate(gen, refs, ledger, fs_state, live):
    e = []
    cont = gen.get("cards_container") or {}
    cards = gen.get("cards") or []
    blocks = {b.get("generation_assignment_id"): b for b in (gen.get("rich_bodies") or [])}
    relations = gen.get("relations") or []
    reports = gen.get("reports") or {}
    receipt = gen.get("receipt") or {}
    assigns = refs.get("assignments") or {}
    fp_by_cluster = refs.get("fp") or {}

    # (A) container honest labels (fix 6)
    if cont.get("automatic_generator_capability_proven") is not False:
        e.append("cards container automatic_generator_capability_proven must be false (honest)")
    if cont.get("human_authored") is not False:
        e.append("cards container human_authored must be false")
    if cont.get("counts_toward_3600") is not False:
        e.append("cards container counts_toward_3600 must be false")
    if cont.get("deliverable_kind") != "execution_ai_authored_scoped_content_draft":
        e.append("cards container deliverable_kind must be execution_ai_authored_scoped_content_draft")
    if cont.get("candidate_count") != EXPECTED_TOTAL:
        e.append(f"cards container candidate_count must be {EXPECTED_TOTAL}")

    # (B) count / bijection / uniqueness
    if len(cards) != EXPECTED_TOTAL:
        e.append(f"card count {len(cards)} != {EXPECTED_TOTAL}")
    if len(assigns) != EXPECTED_TOTAL:
        e.append(f"P7C-BRIEF assignment count {len(assigns)} != {EXPECTED_TOTAL} (reference plan)")
    aid_seen, out_seen, cand_seen = {}, {}, {}
    for c in cards:
        aid_seen[c.get("generation_assignment_id")] = aid_seen.get(c.get("generation_assignment_id"), 0) + 1
        out_seen[c.get("target_output_id")] = out_seen.get(c.get("target_output_id"), 0) + 1
        cand_seen[c.get("candidate_id")] = cand_seen.get(c.get("candidate_id"), 0) + 1
    orphans = [a for a in aid_seen if a not in assigns]
    missing_draft = [a for a in assigns if a not in aid_seen]
    if orphans:
        e.append(f"orphan drafts (assignment_id not in P7C-BRIEF plan): {sorted(orphans)[:8]}")
    if missing_draft:
        e.append(f"assignments with no draft: {sorted(missing_draft)[:8]}")
    dup_aid = [a for a, n in aid_seen.items() if n > 1]
    dup_out = [a for a, n in out_seen.items() if n > 1]
    dup_cand = [a for a, n in cand_seen.items() if n > 1]
    if dup_aid:
        e.append(f"assignment mapped to >1 draft: {dup_aid[:8]}")
    if dup_out:
        e.append(f"duplicate target_output_id: {dup_out[:8]}")
    if dup_cand:
        e.append(f"duplicate candidate_id: {dup_cand[:8]}")

    # (C) per-card: fields + reference integrity (fix 4) + owner routing + readiness
    mode_counts = {}
    cluster_counts = {}
    for c in cards:
        aid = c.get("generation_assignment_id")
        tag = c.get("candidate_id", aid)
        a = assigns.get(aid)
        for fld in REQUIRED_CARD_FIELDS:
            if fld not in c:
                e.append(f"{tag}: missing card field {fld}")
        if c.get("generation_status") != "gpt_generated_structured_draft":
            e.append(f"{tag}: generation_status must be gpt_generated_structured_draft")
        cl = c.get("canonical_cluster_id")
        cluster_counts[cl] = cluster_counts.get(cl, 0) + 1
        mode = c.get("generation_mode")
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        if cl not in CLUSTERS:
            e.append(f"{tag}: cluster {cl!r} outside mkc_007..046 (P0-00/mkc_001..006 forbidden as body draft)")
        p0 = str(c.get("p0_group") or "")
        if p0 in ("P0_00", "P0-00") or p0 not in {"P0_01", "P0_02", "P0_03", "P0_04", "P0_05"}:
            e.append(f"{tag}: p0_group {p0!r} invalid (P0_00 forbidden as body draft)")
        if not a:
            continue  # orphan already flagged; skip ref-integrity
        # (fix 4) faithful consumption of the assignment
        checks = [
            ("target_output_id", c.get("target_output_id"), a.get("target_output_id")),
            ("canonical_cluster_id", cl, a.get("canonical_cluster_id")),
            ("p0_group", c.get("p0_group"), a.get("p0_group")),
            ("generation_mode", mode, a.get("generation_mode")),
            ("proposed_target_owner", c.get("proposed_target_owner"), a.get("proposed_target_owner_target")),
        ]
        for name, got, want in checks:
            if got != want:
                e.append(f"{tag}: {name}={got!r} != assignment {want!r} (fix 4 reference integrity)")
        for lname, cardv, av in [
            ("proposition_refs", c.get("proposition_refs"), a.get("proposition_refs")),
            ("gold_reference_case_refs", c.get("gold_reference_case_refs"), a.get("gold_reference_case_refs")),
            ("anti_gold_avoidance_refs", c.get("anti_gold_avoidance_refs"), a.get("anti_gold_avoidance_refs")),
            ("creative_pattern_refs", c.get("creative_pattern_refs"), a.get("creative_pattern_refs")),
        ]:
            if list(cardv or []) != list(av or []):
                e.append(f"{tag}: {lname} does not match assignment (fix 4)")
        # owner -> kind/layer routing
        owner = c.get("proposed_target_owner")
        exp = OWNER_KIND_LAYER.get(owner)
        if not exp:
            e.append(f"{tag}: owner {owner!r} not a known routing owner")
        else:
            if c.get("candidate_kind") != exp[0]:
                e.append(f"{tag}: candidate_kind {c.get('candidate_kind')!r} != {exp[0]!r} for owner {owner}")
            if c.get("target_layer_candidate") != exp[1]:
                e.append(f"{tag}: target_layer_candidate {c.get('target_layer_candidate')!r} != {exp[1]!r}")
        # (fix, req 33) EvidencePolicyOutbox must not map to GeneralKnowledgeBase / TBox
        if owner == "EvidencePolicyOutbox":
            all_land = set(c.get("allowed_landing_layers") or [])
            if "TBox_candidate" in all_land or "GeneralKnowledgeBase" in all_land:
                e.append(f"{tag}: EvidencePolicyOutbox draft must not land in GeneralKnowledgeBase/TBox (req 33)")
        # body_proposition_refs subset of assignment proposition_refs and valid in P5
        aprops = set(a.get("proposition_refs") or [])
        bpr = c.get("body_proposition_refs") or []
        if not bpr:
            e.append(f"{tag}: empty body_proposition_refs")
        for pid in bpr:
            if pid not in aprops:
                e.append(f"{tag}: body_proposition_ref {pid} not in assignment proposition_refs")
            if pid not in refs["p5_prop_ids"].get(cl, set()):
                e.append(f"{tag}: body_proposition_ref {pid} not in P5 pack for {cl}")
        # readiness all false
        for bad in ["accepted_domain_knowledge", "candidatepack_ready", "KE_ready", "RAG_ready",
                    "DIFY_ready", "production_servable"]:
            if c.get(bad) is not False:
                e.append(f"{tag}: {bad} must be false")
        rf = c.get("readiness_flags") or {}
        for k in READINESS_KEYS:
            if rf.get(k) is not False:
                e.append(f"{tag}: readiness_flags.{k} must be false")

    # (D) coverage + distribution
    if set(cluster_counts) != set(CLUSTERS):
        miss = [c for c in CLUSTERS if c not in cluster_counts]
        e.append(f"cluster coverage != mkc_007..046 (missing {miss[:6]})")
    if mode_counts != EXPECTED_MODE_DIST:
        e.append(f"generation_mode distribution {mode_counts} != {EXPECTED_MODE_DIST}")

    # (E) rich body recompute (fix 5) — everything re-derived from body text
    bodies_by_tag = {}
    hashes = {}
    for c in cards:
        aid = c.get("generation_assignment_id")
        b = blocks.get(aid)
        tag = c.get("candidate_id", aid)
        cl = c.get("canonical_cluster_id")
        mode = c.get("generation_mode")
        if not b:
            e.append(f"{tag}: missing rich body for assignment {aid}")
            continue
        body = b.get("body", "")
        bodies_by_tag[tag] = body
        n = len(clean(body))
        if n < MIN_BODY_CHARS:
            e.append(f"{tag}: body {n} chars < {MIN_BODY_CHARS}")
        for gb in (refs["gold"].get(cl) or []):
            if lcs_len(body, gb) >= GOLD_COPY_LCS_THRESHOLD:
                e.append(f"{tag}: gold-body surface copy lcs >= {GOLD_COPY_LCS_THRESHOLD}")
                break
        if refs["canary"].get(cl) and lcs_len(body, refs["canary"][cl]) >= CANARY_COPY_LCS_THRESHOLD:
            e.append(f"{tag}: P4 canary body copy lcs >= {CANARY_COPY_LCS_THRESHOLD}")
        if refs["proof"].get(cl) and lcs_len(body, refs["proof"][cl]) >= CANARY_COPY_LCS_THRESHOLD:
            e.append(f"{tag}: P7A proof body copy lcs >= {CANARY_COPY_LCS_THRESHOLD}")
        gt = gov_tokens_found(body)
        if gt:
            e.append(f"{tag}: governance/meta tokens in body: {gt}")
        rff = real_fact_found(body)
        if rff:
            e.append(f"{tag}: real-instance fact leak: {rff}")
        if abstract_stack_found(body):
            e.append(f"{tag}: abstract style-word stacking (>=3)")
        if checklist_scaffold_count(body) > CHECKLIST_SCAFFOLD_MAX:
            e.append(f"{tag}: checklist/courseware scaffold (> {CHECKLIST_SCAFFOLD_MAX} numbered items)")
        own, rank = specificity(body, cl, fp_by_cluster)
        if own < MIN_FP_OVERLAP:
            e.append(f"{tag}: fingerprint overlap {own} < {MIN_FP_OVERLAP} (not cluster-anchored)")
        if rank > SPECIFICITY_RANK_MAX:
            e.append(f"{tag}: specificity rank {rank} > {SPECIFICITY_RANK_MAX} (not cluster-specific)")
        if len(b.get("cluster_specific_mechanism_chain") or []) < 3:
            e.append(f"{tag}: mechanism_chain < 3")
        if not b.get("hard_claim_routing"):
            e.append(f"{tag}: missing hard_claim_routing")
        for sub in REQUIRED_BODY_SUBFIELDS:
            if not b.get(sub):
                e.append(f"{tag}: missing creative sub-field {sub}")
        if len(b.get("domain_anchors") or []) < 3:
            e.append(f"{tag}: domain_anchors < 3")
        for pid in (b.get("source_proposition_ids") or []):
            if pid not in refs["p5_prop_ids"].get(cl, set()):
                e.append(f"{tag}: source_proposition_id {pid} not in P5 for {cl}")
        # (fix 5, req 24-25) CSO overlay present, not ontology truth
        cso = b.get("cso_overlay_applied") or c.get("cso_overlay_requirements") or []
        if not cso:
            e.append(f"{tag}: missing cso_overlay")
        if b.get("cso_marked_ontology_truth") is True:
            e.append(f"{tag}: cso marked ontology truth (forbidden)")
        # (req 26-29) per-mode fact rule recomputed from body
        has_slot = bool(SLOT_MARKER_RE.search(body)) or bool(b.get("slots"))
        has_downgrade = any(s in body for s in DOWNGRADE_SIGNALS) or \
            any(s in str(b.get("hard_claim_routing") or "") for s in ["missing_source", "observation", "待补", "降级"])
        if mode == "fact_slot_script" and not (SLOT_MARKER_RE.search(body) and b.get("slots")):
            e.append(f"{tag}: fact_slot_script must render missing facts as explicit body slots (req 27)")
        if mode == "evidence_bound_candidate" and not (has_slot or has_downgrade):
            e.append(f"{tag}: evidence_bound_candidate needs evidence slot or downgraded claim (req 28)")
        if mode == "display_solution" and not (has_slot or has_downgrade):
            e.append(f"{tag}: display_solution needs scene-fact slot for final execution (req 29)")
        if mode == "creative_prototype" and (real_fact_found(body) or b.get("brand_facts_required") is True):
            e.append(f"{tag}: creative_prototype must not require/assert brand facts (req 26)")
        # SourceGapLedger draft must be honestly slotted, not asserted fact
        if c.get("proposed_target_owner") == "SourceGapLedger" and not (has_slot or has_downgrade):
            e.append(f"{tag}: SourceGapLedger draft must slot/flag the gap, not assert it (req 31)")
        # provenance flags on the block
        if b.get("governance_text_in_body") is not False:
            e.append(f"{tag}: rich body governance_text_in_body must be false")
        h = body_hash(body)
        if h in hashes:
            e.append(f"{tag}: duplicate body hash with {hashes[h]}")
        hashes[h] = tag

    # cross-draft collisions (>=18-gram shared) — recompute
    coll = cross_draft_collisions(bodies_by_tag)
    if coll:
        e.append(f"cross-draft template reuse (>= {CROSS_LCS_THRESHOLD}-gram) pairs: {coll[:5]}")

    # (F) relations are design hints, not ontology edges
    for r in relations:
        oc = str(r.get("ontology_edge_created", "")).strip().lower()
        fa = str(r.get("formal_ontology_edge_allowed", "")).strip().lower()
        if oc not in ("false", "0", "no", ""):
            e.append(f"relation {r.get('relation_id')} ontology_edge_created must be false")
        if fa not in ("false", "0", "no", ""):
            e.append(f"relation {r.get('relation_id')} formal_ontology_edge_allowed must be false")

    # (G) gate reports exist + claim PASS + agree with recompute (fix 5)
    recomputed_pass = not e  # if any body/structural error above, gates cannot claim pass
    gate_expect = {
        "governance": "governance_gate_pass", "creative": "creative_gate_pass",
        "entailment": "body_entailment_pass", "semantic": "semantic_alignment_pass",
        "dedupe": "dedupe_pass", "style": "style_copy_pass",
        "generation_mode": "generation_mode_pass", "fact_binding": "fact_binding_pass",
        "cso_overlay": "cso_overlay_pass",
    }
    for rep, key in gate_expect.items():
        r = reports.get(rep)
        if not r:
            e.append(f"{rep} report missing/unparsed")
            continue
        if r.get(key) is not True:
            e.append(f"{rep} report {key} not true")
    ded = reports.get("dedupe") or {}
    if ded.get("body_count") not in (None, len(bodies_by_tag)):
        e.append("dedupe_report body_count disagrees with recompute")
    if ded.get("unique_body_hashes") not in (None, len(hashes)):
        e.append("dedupe_report unique_body_hashes disagrees with recompute")
    sty = reports.get("style") or {}
    if sty.get("gold_body_copy_found") not in (None, False) or sty.get("p4_canary_body_copy_found") not in (None, False):
        e.append("style_copy_report claims a copy but must be false")
    gov = reports.get("governance") or {}
    if gov.get("readiness_all_false") is not True:
        e.append("governance_gate readiness_all_false must be true")
    if gov.get("evidence_policy_mapped_to_gkb_count") not in (0, None):
        e.append("governance_gate evidence_policy_mapped_to_gkb_count must be 0")
    md = reports.get("generation_mode") or {}
    if md.get("mode_distribution") not in (None, EXPECTED_MODE_DIST):
        e.append("generation_mode_report distribution disagrees with expected 36/36/24/24")

    # (H) receipt honest provenance (fix 6)
    if receipt.get("execution_ai_authored") is not True:
        e.append("generation_receipt.execution_ai_authored must be true (honest source)")
    if receipt.get("automatic_generator_capability_proven") is not False:
        e.append("generation_receipt.automatic_generator_capability_proven must be false (fix 6)")
    if receipt.get("counts_toward_3600") is not False:
        e.append("generation_receipt.counts_toward_3600 must be false")
    if receipt.get("generation_3600_completed") is not False:
        e.append("generation_receipt.generation_3600_completed must be false")
    for k in ["candidatepack_ready", "KE_ready", "RAG_ready", "DIFY_ready", "production_ready", "generation_allowed"]:
        if receipt.get(k) is not False:
            e.append(f"generation_receipt.{k} must be false")

    # (I) filesystem: no 320 / 3600 / candidatepack / extra run dirs
    if fs_state.get("forbidden_present"):
        e.append(f"forbidden dirs present: {fs_state['forbidden_present']}")
    if fs_state.get("run_manifest_present"):
        e.append("3600 run_manifest / microbatch_index created (forbidden)")
    if fs_state.get("microbatches_present"):
        e.append("microbatches / batch_summaries created (forbidden)")
    if fs_state.get("three600_present"):
        e.append("*3600* generation dir created (forbidden)")
    rd = fs_state.get("run_dirs")
    if rd is not None and set(rd) != {"proof_microbatch_001", RUN_ID}:
        e.append(f"unexpected microbatch run dirs (only proof + this scoped run allowed): {rd}")

    # (J) ledger route (fix 2 + additive P7C-GEN/P7C-REVIEW)
    by = {s.get("step_id"): s for s in (ledger.get("steps") or [])}
    for sid in ["P1", "P2", "P3", "P4", "P5", "P6", "P6R"]:
        if (by.get(sid) or {}).get("status") != "DONE":
            e.append(f"ledger {sid} must be DONE")
    p7a = by.get("P7A") or {}
    if p7a.get("status") != "DONE":
        e.append("ledger P7A must stay DONE (committed-checker anchor, fix 2)")
    if p7a.get("classification") != "agent_authored_quality_probe_pass":
        e.append("ledger P7A.classification must stay agent_authored_quality_probe_pass (fix 2)")
    for sid in ["P7B", "P7C-BRIEF"]:
        if (by.get(sid) or {}).get("status") != "DONE":
            e.append(f"ledger {sid} must be DONE")
    p7 = by.get("P7") or {}
    if p7.get("status") not in ("NEXT", "IN_PROGRESS"):
        e.append("ledger P7 (legacy anchor) must stay NEXT/IN_PROGRESS")
    p7c = by.get("P7C") or {}
    if p7c.get("status") not in ("NEXT", "IN_PROGRESS"):
        e.append("ledger P7C (anchor) must stay NEXT (committed P7B checker reads it)")
    pcg = by.get("P7C-GEN") or {}
    if pcg.get("status") != "DONE":
        e.append(f"ledger P7C-GEN must be DONE, got {pcg.get('status')!r}")
    if pcg.get("task_id") != TASK_ID:
        e.append("ledger P7C-GEN task_id must be this task")
    if pcg.get("scoped_120_generated") is not True:
        e.append("ledger P7C-GEN.scoped_120_generated must be true")
    if pcg.get("counts_toward_3600") is not False:
        e.append("ledger P7C-GEN.counts_toward_3600 must be false")
    if pcg.get("generation_3600_unlocked") is not False:
        e.append("ledger P7C-GEN.generation_3600_unlocked must be false")
    pcr = by.get("P7C-REVIEW") or {}
    if pcr.get("status") not in ("NEXT", "IN_PROGRESS"):
        e.append(f"ledger P7C-REVIEW must be NEXT, got {pcr.get('status')!r}")
    p7d = by.get("P7D") or {}
    if "BLOCKED" not in str(p7d.get("status") or "").upper() or \
            "P7C_REVIEW" not in str(p7d.get("status") or "").upper().replace("-", "_"):
        e.append(f"ledger P7D must be BLOCKED_BY_P7C_REVIEW, got {p7d.get('status')!r}")
    if "BLOCKED" not in str((by.get("P8") or {}).get("status") or "").upper():
        e.append("ledger P8 must stay blocked")
    if ledger.get("generation_unlocked") is not False:
        e.append("ledger generation_unlocked must stay false")
    led_rd = ledger.get("readiness") or {}
    if led_rd.get("readiness_all_false") is not True:
        e.append("ledger readiness_all_false must be true")
    for k, v in led_rd.items():
        if k == "readiness_all_false":
            continue
        if v not in (False, None):
            e.append(f"ledger readiness {k} must be false")
    rm3 = ledger.get("route_migration_3") or {}
    if not rm3:
        e.append("ledger route_migration_3 block missing (additive P7C-GEN/P7C-REVIEW extension)")
    else:
        if rm3.get("no_old_checker_edited") is not True:
            e.append("route_migration_3.no_old_checker_edited must be true")
        if rm3.get("no_readiness_flipped") is not True:
            e.append("route_migration_3.no_readiness_flipped must be true")

    # (K) git surface + committed immutability (fix 3) + priors
    if live.get("git_changed_outside_allowed"):
        e.append(f"git changes outside allowed write surface: {live['git_changed_outside_allowed']}")
    if live.get("committed_artifacts_modified"):
        e.append(f"committed assignments/alignment/proof/checkers modified (fix 3): {live['committed_artifacts_modified']}")
    if live.get("forbidden_touched"):
        e.append(f"forbidden path touched: {live['forbidden_touched']}")
    for name, rc in (live.get("prior_checkers") or {}).items():
        if rc != 0:
            e.append(f"prior checker {name} not PASS (exit {rc})")

    return e


# ----------------------------- loaders (live) -----------------------------
def _top(ws, rel):
    p = os.path.join(ws, rel)
    if not os.path.exists(p):
        return None
    d = yaml.safe_load(open(p))
    return d[list(d.keys())[0]] if isinstance(d, dict) and d else d


def load_refs(ws):
    refs = {"gold": {}, "canary": {}, "proof": {}, "p5_prop_ids": {}, "fp": {}, "assignments": {}}
    auth = _top(ws, AUTHORITY_REL)["records"]
    titles = {r["mkc_id"]: r.get("canonical_title", "") for r in auth}
    topics = {r["mkc_id"]: (r.get("expected_body_topics") or []) for r in auth}
    anchors = {}
    for f in sorted(glob.glob(os.path.join(ws, "03_grc_goldset_corpus/normalized/formal_120/p0_0*/gold_reference_cases.yaml"))):
        for c in yaml.safe_load(open(f))["gold_reference_cases"]:
            cid = c["cluster_id"]; bc = c.get("body_contract") or {}
            if bc.get("gold_body"):
                refs["gold"].setdefault(cid, []).append(bc["gold_body"])
            if c.get("case_type") == "positive_gold":
                anchors[cid] = bc.get("apparel_domain_anchors") or []
    for b in _top(ws, CANARY_BLOCKS_REL)["blocks"]:
        refs["canary"][b["canonical_cluster_id"]] = b.get("body", "")
    if os.path.exists(os.path.join(ws, PROOF_BLOCKS_REL)):
        for b in _top(ws, PROOF_BLOCKS_REL)["blocks"]:
            refs["proof"][b["canonical_cluster_id"]] = b.get("body", "")
    p5 = _top(ws, PROP_PACK_REL)["clusters"]
    for cid, plist in p5.items():
        refs["p5_prop_ids"][cid] = {p["proposition_id"] for p in plist}
    refs["fp"] = {cid: fingerprint(titles.get(cid, ""), topics.get(cid, []), anchors.get(cid, [])) for cid in CLUSTERS}
    plan = _top(ws, ASSIGN_PLAN_REL)
    for a in (plan or {}).get("assignments") or []:
        refs["assignments"][a["assignment_id"]] = a
    return refs


def load_gen(ws):
    d = os.path.join(ws, RUN_REL)

    def j(name):
        p = os.path.join(d, name)
        return json.load(open(p)) if os.path.exists(p) else None

    cont = _top(ws, f"{RUN_REL}/knowledge_candidate_cards.yaml") or {}
    blocks = _top(ws, f"{RUN_REL}/rich_body_blocks.yaml") or {}
    relations = []
    rc = os.path.join(d, "relation_candidates.csv")
    if os.path.exists(rc):
        with open(rc) as f:
            relations = list(_csv.DictReader(f))
    reports = {
        "governance": j("governance_gate_report.json"), "creative": j("creative_gate_report.json"),
        "entailment": j("body_entailment_report.json"), "semantic": j("semantic_alignment_report.json"),
        "dedupe": j("dedupe_report.json"), "style": j("style_copy_report.json"),
        "generation_mode": j("generation_mode_report.json"), "fact_binding": j("fact_binding_report.json"),
        "cso_overlay": j("cso_overlay_report.json"),
    }
    return {"cards_container": cont, "cards": cont.get("candidates") or [],
            "rich_bodies": (blocks.get("blocks") or []), "relations": relations,
            "reports": reports, "receipt": j("generation_receipt.json") or {}}


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
    forbidden = [p for p in changed if any(p.startswith(x + "/") or p == x for x in NEW_FORBIDDEN_DIRS)]
    protected = (["07_microbatch_runs/proof_microbatch_001/", ALIGN_DIR + "/", SCOPE_DIR + "/"] + COMMITTED_CHECKERS)
    committed = [p for p in changed if any(p == x or p.startswith(x) for x in protected)
                 and not p.startswith(f"07_microbatch_runs/{RUN_ID}/")]
    return {"git_changed": changed, "git_changed_outside_allowed": outside,
            "forbidden_touched": forbidden, "committed_artifacts_modified": committed,
            "prior_checkers": priors}


def scan_fs(ws):
    present = [d for d in NEW_FORBIDDEN_DIRS if os.path.isdir(os.path.join(ws, d))]
    run_manifest = bool(glob.glob(os.path.join(ws, "07_microbatch_runs", "run_manifest*")) +
                        glob.glob(os.path.join(ws, "07_microbatch_runs", "microbatch_index*")))
    three600 = bool(glob.glob(os.path.join(ws, "07_microbatch_runs", "*3600*")) +
                    glob.glob(os.path.join(ws, "04_microbatch_generation", "*3600*")))
    micro = any(os.path.isdir(os.path.join(ws, d))
                for d in ["07_microbatch_runs/microbatches", "07_microbatch_runs/batch_summaries"])
    runs = os.path.join(ws, "07_microbatch_runs")
    run_dirs = [d for d in os.listdir(runs) if os.path.isdir(os.path.join(runs, d))] if os.path.isdir(runs) else []
    return {"forbidden_present": present, "run_manifest_present": run_manifest,
            "microbatches_present": micro, "three600_present": three600, "run_dirs": run_dirs}


# ----------------------------- snapshot prior runner -----------------------------
def _build_snapshot(ws, extra_excludes):
    import shutil
    snap = tempfile.mkdtemp(prefix="p7cgen_snap_")
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
    # Reset ledger to the IMMUTABLE pre-generation baseline commit (not `git show HEAD`) so the
    # committed P7C-BRIEF/P7A/P7B anchors (which read P7C-GEN==NEXT / P7D==BLOCKED_BY_P7C_GEN) are
    # satisfied REGARDLESS of what HEAD is now. This makes the checker idempotent: it stays green
    # when re-run after this task's own commit moves HEAD (avoids the E7.1 snapshot-supersession
    # trap where a HEAD-relative reset re-exposes the post-generation phase to a pre-generation
    # prior). Falls back to HEAD only if the baseline commit is unreachable (e.g. shallow clone).
    for rel in [LEDGER_REL, "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"]:
        h = subprocess.run(["git", "-C", ws, "show", PRE_GEN_BASELINE + ":" + rel],
                           capture_output=True, text=True)
        if h.returncode != 0:
            h = subprocess.run(["git", "-C", ws, "show", "HEAD:" + rel], capture_output=True, text=True)
        if h.returncode == 0:
            os.makedirs(os.path.dirname(os.path.join(snap, rel)), exist_ok=True)
            with open(os.path.join(snap, rel), "w") as f:
                f.write(h.stdout)
    return snap


THIS_TASK_FILES = [
    "ci/checkers/check_scoped_120_content_production_microbatch_generation.py",
    "ci/fixtures/scoped_120_content_production_microbatch_generation",
    "ci/reports/scoped_120_content_production_microbatch_generation_report.v0.1.json",
    "docs/reports/grc_scoped_120_content_production_microbatch_generation_report.md",
    "docs/reports/grc_scoped_120_content_production_microbatch_generation_receipt.json",
]


def run_priors(ws):
    import shutil
    results = {}
    # snapshot A: no 07_microbatch_runs at all (P6/P6R phase invariant) -> P1..P6R + contract-lock
    snap_a = _build_snapshot(ws, ["07_microbatch_runs"] + THIS_TASK_FILES)
    try:
        for name, rel, cargs in PRIORS_SNAPSHOT_A:
            chk = os.path.join(snap_a, rel)
            results[name] = 98 if not os.path.exists(chk) else subprocess.run(
                [sys.executable, chk] + cargs, cwd=snap_a, capture_output=True, text=True).returncode
    finally:
        shutil.rmtree(snap_a, ignore_errors=True)
    # snapshot B: pre-generation — keep proof + alignment + briefing, drop THIS run dir + task files,
    # ledger reset to HEAD -> P7A, P7B, P7C-BRIEF see P7C-GEN==NEXT and run_dirs=={proof}
    snap_b = _build_snapshot(ws, [RUN_REL] + THIS_TASK_FILES)
    try:
        for name, rel, cargs in PRIORS_SNAPSHOT_B:
            chk = os.path.join(snap_b, rel)
            results[name] = 98 if not os.path.exists(chk) else subprocess.run(
                [sys.executable, chk] + cargs, cwd=snap_b, capture_output=True, text=True).returncode
    finally:
        shutil.rmtree(snap_b, ignore_errors=True)
    return results


# ----------------------------- live / selftest -----------------------------
def run_live(ws, report_out=None):
    gen = load_gen(ws)
    refs = load_refs(ws)
    ledger = load_ledger(ws)
    fs_state = scan_fs(ws)
    live = compute_live(ws, run_priors(ws))
    errors = validate(gen, refs, ledger, fs_state, live)
    status = "PASS" if not errors else "FAIL"
    cards = gen.get("cards") or []
    mode_counts = {}
    for c in cards:
        mode_counts[c.get("generation_mode")] = mode_counts.get(c.get("generation_mode"), 0) + 1
    report = {
        "checker": "check_scoped_120_content_production_microbatch_generation.py",
        "task_id": TASK_ID, "step_id": "P7C-GEN", "status": status,
        "error_count": len(errors), "errors": errors[:80],
        "draft_count": len(cards), "assignment_count": len(refs.get("assignments") or {}),
        "generation_mode_distribution": mode_counts,
        "git_changed_outside_allowed": live.get("git_changed_outside_allowed"),
        "committed_artifacts_modified": live.get("committed_artifacts_modified"),
        "prior_checkers": live.get("prior_checkers"),
    }
    if report_out:
        json.dump(report, open(report_out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def selftest(ws):
    fx = os.path.join(ws, "ci/fixtures/scoped_120_content_production_microbatch_generation")
    pos = os.path.join(fx, "positive_valid.yaml")
    if not os.path.exists(pos):
        print(json.dumps({"status": "FAIL", "reason": "positive fixture missing"}))
        return 1

    def _run(f):
        return validate(f["gen"], _rebuild_refs(f["refs"]), f["ledger"], f["fs_state"], f["live"])

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


def _rebuild_refs(r):
    """Fixtures store fp as {cluster: [terms]}; rebuild 2-gram fingerprint sets. gold/canary/proof as strings."""
    out = dict(r)
    fp = {}
    for cid, terms in (r.get("fp") or {}).items():
        fp[cid] = two_grams("".join(terms)) if isinstance(terms, list) else two_grams(str(terms))
    out["fp"] = fp
    out["p5_prop_ids"] = {k: set(v) for k, v in (r.get("p5_prop_ids") or {}).items()}
    out["gold"] = {k: (v if isinstance(v, list) else [v]) for k, v in (r.get("gold") or {}).items()}
    return out


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
    ap.add_argument("--workspace-root", default=REPO_DEFAULT)
    a = ap.parse_args()
    ws = os.path.abspath(a.workspace_root)
    if a.selftest:
        return selftest(ws)
    if a.live:
        return run_live(ws, a.report_out)
    ap.error("one of --live / --selftest required")


if __name__ == "__main__":
    sys.exit(main())
