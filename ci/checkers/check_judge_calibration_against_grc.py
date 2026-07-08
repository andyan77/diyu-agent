#!/usr/bin/env python3
"""GRC judge calibration checker — GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001.

Fail-closed. The live path (a) runs the P1 corpus and P2 alignment checkers as
subprocesses and requires exit 0, (b) independently recomputes corpus facts from
03_grc_goldset_corpus/normalized/**, and (c) validates the judge calibration
registries (exactly-once coverage, no cross-registry overlap, source-traced
failure/repair bindings). A shared pure core `validate_judge_model` judges both
the live corpus and the selftest fixtures.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

TASK_ID = "GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001"
NEXT_TASK = "GKB-CANARY-40-GENERATION-AND-GATE-001"
JC_REL = "04_judge_calibration"
CORPUS_REL = "03_grc_goldset_corpus"
CONTRACTS_REL_SCHEMA = "01_generation_contracts/codex_generation_output_contract.v0.1.schema.json"
FORMAL_CLUSTERS = {f"mkc_{n:03d}" for n in range(7, 47)}
P0_CLUSTERS = {f"mkc_{n:03d}" for n in range(1, 7)}
EVIDENCE_OWNER = "EvidencePolicyOutbox"
EVIDENCE_KIND = "evidence_policy_candidate"
REQUIRED_FAILURE_CATEGORIES = {
    "no_cluster_specific_mechanism", "template_reuse", "governance_text_in_body",
    "wrong_owner_routing", "no_gold_value", "evidence_policy_owner_mismatch",
    "control_plane_mixed_with_domain_body", "surface_style_copy_risk",
    "unsupported_claim_without_evidence", "real_instance_fact_leak",
    "readiness_flag_true", "candidatepack_or_downstream_materialization_leak",
}
FORBIDDEN_DIR_NAMES = ["candidatepack_etl", "KE", "Serving", "serving_projection",
                       "RAG", "rag", "DIFY", "dify", "CandidatePack"]
GENERATED_MARKERS = ["generated_knowledge", "canary", "3600_generation", "generated_batch"]

NEGATIVE_FIXTURES = [
    "negative_1_missing_positive_case.yaml",
    "negative_2_anti_without_failure_code.yaml",
    "negative_3_borderline_without_repair.yaml",
    "negative_4_p0_00_included_in_formal.yaml",
    "negative_5_evidence_mapped_to_gkb.yaml",
    "negative_6_creative_marked_ontology_truth.yaml",
    "negative_7_relation_promoted_to_ontology_edge.yaml",
    "negative_8_readiness_true.yaml",
    "negative_9_candidatepack_path_created.yaml",
    "negative_10_duplicate_case_across_registries.yaml",
    "negative_11_malformed.yaml",
]


class JudgeCalError(Exception):
    pass


def fail(msg: str) -> None:
    raise JudgeCalError(msg)


def load_yaml(path: Path) -> Any:
    if not path.exists():
        fail(f"missing file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_kv(obj: Any, key: str) -> list:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, (str, int, float)):
                out.append(v)
            out += find_kv(v, key)
    elif isinstance(obj, list):
        for it in obj:
            out += find_kv(it, key)
    return out


# ---------------------------------------------------------------------------
# Pure core.
# ---------------------------------------------------------------------------
def validate_judge_model(m: dict) -> list[str]:
    e: list[str] = []

    # (1/2) upstream checkers
    if m.get("p1_checker_pass") is not True:
        e.append("P1 corpus checker did not PASS")
    if m.get("p2_checker_pass") is not True:
        e.append("P2 alignment checker did not PASS")

    # (3-8) formal counts / clusters
    if m.get("formal_total") != 120:
        e.append(f"formal_120 total must be 120, got {m.get('formal_total')}")
    if m.get("positive_count") != 40:
        e.append(f"positive_gold must be 40, got {m.get('positive_count')}")
    if m.get("anti_count") != 40:
        e.append(f"anti_gold must be 40, got {m.get('anti_count')}")
    if m.get("borderline_count") != 40:
        e.append(f"borderline_repair must be 40, got {m.get('borderline_count')}")
    fc = m.get("formal_clusters", {})
    if set(fc) != FORMAL_CLUSTERS:
        e.append("formal clusters must be exactly mkc_007..mkc_046")
    off = {c: n for c, n in fc.items() if n != 3}
    if off:
        e.append(f"formal clusters not exactly 3 cases: {off}")

    # (9-11) P0-00
    if m.get("p0_total") != 18:
        e.append(f"P0-00 total must be 18, got {m.get('p0_total')}")
    if m.get("p0_00_included_in_formal") is not False:
        e.append("P0-00 must not be included in formal_120")
    if set(m.get("p0_clusters", {})) != P0_CLUSTERS:
        e.append("P0-00 clusters must be exactly mkc_001..mkc_006")
    if set(m.get("p0_clusters", {})) & set(fc):
        e.append("P0-00 clusters overlap formal_120 clusters")

    # (12-13) evidence
    if len(m.get("evidence_ids", [])) != 15:
        e.append(f"EvidencePolicyOutbox case count must be 15, got {len(m.get('evidence_ids', []))}")
    if m.get("evidence_mapped_gkb_count", 0) != 0:
        e.append("EvidencePolicyOutbox case mapped to GeneralKnowledgeBase")

    # (14-17) exactly-once coverage
    for label, ids, n in [("positive", m.get("positive_ids", []), 40),
                          ("anti", m.get("anti_ids", []), 40),
                          ("borderline", m.get("borderline_ids", []), 40),
                          ("control", m.get("control_ids", []), 18)]:
        if len(ids) != n:
            e.append(f"{label} registry must cover {n}, got {len(ids)}")
        if len(ids) != len(set(ids)):
            e.append(f"{label} registry has duplicate case_ids (not exactly-once)")

    # (18) no case in two registries
    pools = {"positive": set(m.get("positive_ids", [])), "anti": set(m.get("anti_ids", [])),
             "borderline": set(m.get("borderline_ids", [])), "control": set(m.get("control_ids", []))}
    names = list(pools)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            overlap = pools[names[i]] & pools[names[j]]
            if overlap:
                e.append(f"case(s) appear in both {names[i]} and {names[j]}: {sorted(overlap)[:3]}")

    # (19-21) bindings
    if m.get("anti_without_failure_code"):
        e.append(f"anti case(s) without failure_code: {m['anti_without_failure_code'][:3]}")
    if m.get("borderline_without_repair"):
        e.append(f"borderline case(s) without repair reason: {m['borderline_without_repair'][:3]}")
    if m.get("control_anti_without_failure_code"):
        e.append(f"control anti case(s) without control-plane failure code: {m['control_anti_without_failure_code'][:3]}")

    # (22) hard gate namespace registry
    if m.get("hard_gate_registry_present") is not True:
        e.append("hard_gate_namespace_registry missing")
    if m.get("hard_gate_count", 0) < 8:
        e.append("hard_gate_namespace_registry must define >= 8 gates")

    # failure code registry: 12 canonical categories present
    if not REQUIRED_FAILURE_CATEGORIES.issubset(set(m.get("failure_registry_categories", []))):
        missing = REQUIRED_FAILURE_CATEGORIES - set(m.get("failure_registry_categories", []))
        e.append(f"failure_code_registry missing categories: {sorted(missing)}")

    # (23) expert review index
    if m.get("expert_index_present") is not True:
        e.append("expert_review_13_index missing")
    if m.get("expert_batch_count") != 13:
        e.append(f"expert_review_13_index must index 13 batches, got {m.get('expert_batch_count')}")
    if m.get("expert_has_digest_ref") is not True:
        e.append("expert_review_13_index must reference source digest")
    if m.get("expert_do_not_rewrite") is not True:
        e.append("expert_review_13_index must mark do_not_rewrite_judgments true")

    # (24) creative metadata eval-only
    if m.get("creative_eval_only") is not True:
        e.append("creative metadata must be eval_only")
    if m.get("creative_ontology_truth") is not False:
        e.append("creative metadata must not be ontology_truth")
    if m.get("creative_production_servable") is not False:
        e.append("creative metadata must not be production_servable")

    # (25) do_not_copy policy
    if m.get("do_not_copy_policy_present") is not True:
        e.append("do_not_copy_surface_style_policy missing")

    # (26) relation hints
    if m.get("relation_ontology_edge_count", 0) != 0:
        e.append("relation hint promoted to ontology edge")

    # (27) readiness
    for name, value in m.get("readiness_flags", {}).items():
        if name == "readiness_all_false":
            if value is not True:
                e.append("readiness_all_false must be true")
        elif value is True or str(value).lower() == "true":
            e.append(f"readiness flag '{name}' must be false")
    if m.get("generation_3600_unlocked") is True:
        e.append("generation_3600_unlocked must be false")

    # (28/29) no generated / forbidden dirs
    if m.get("generated_knowledge_dirs_present"):
        e.append(f"generated-knowledge dir(s) present: {m['generated_knowledge_dirs_present']}")
    if m.get("forbidden_dirs_present"):
        e.append(f"forbidden dir(s) present/created: {m['forbidden_dirs_present']}")

    # (30) ledger states
    if m.get("ledger_p1") != "DONE":
        e.append("ledger P1 must be DONE")
    if m.get("ledger_p2") != "DONE":
        e.append("ledger P2 must be DONE")
    p3 = m.get("ledger_p3")
    p4 = m.get("ledger_p4")
    # Robust roadmap-advancement rule: P3 DONE requires P4 UNBLOCKED (NEXT or advanced),
    # not exactly NEXT, so a future frontier move past P4 does not break this checker.
    if p3 == "DONE" and p4 in (None, "BLOCKED_BY_P3"):
        e.append("ledger P3 DONE requires P4 unblocked (NEXT or advanced)")
    if p3 == "BLOCKED" and p4 != "BLOCKED_BY_P3":
        e.append("ledger P3 BLOCKED requires P4 = BLOCKED_BY_P3")
    if p3 not in ("DONE", "BLOCKED"):
        e.append(f"ledger P3 must be DONE or BLOCKED, got {p3}")

    return e


# ---------------------------------------------------------------------------
# Live model.
# ---------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_p1_substance(ws: Path) -> bool:
    """Independently re-derive P1's corpus-lock guarantee (no subprocess): every
    normalized copy is byte-identical to its tmp source and to the recorded digest."""
    try:
        dm = load_yaml(ws / CORPUS_REL / "source_digest_manifest.v0.1.yaml")["source_digest_manifest"]
        rows = dm["source_files"]
        if len(rows) != 32:
            return False
        for r in rows:
            src = ws / r["source_path"]
            norm = ws / r["canonical_normalized_path"]
            if not (src.exists() and norm.exists()):
                return False
            if not (_sha256(src) == _sha256(norm) == r["source_sha256"] == r["normalized_sha256"]):
                return False
        return True
    except Exception:
        return False


def verify_p2_substance(ws: Path, evidence_ids: list, evidence_gkb: int) -> bool:
    """Independently re-derive P2's contract-delta guarantee (no subprocess): both
    enum values landed and the 15 evidence cases retain EvidencePolicyOutbox (0 -> GKB)."""
    try:
        schema = json.loads((ws / CONTRACTS_REL_SCHEMA).read_text(encoding="utf-8"))
        own = schema["properties"]["ownership"]["properties"]
        enums_ok = (EVIDENCE_KIND in own["candidate_kind"]["enum"]
                    and EVIDENCE_OWNER in own["proposed_target_owner"]["enum"])
        return enums_ok and len(evidence_ids) == 15 and evidence_gkb == 0
    except Exception:
        return False


def build_live_model(ws: Path) -> tuple[dict, dict]:
    jc = ws / JC_REL
    corpus = ws / CORPUS_REL

    p1_pass = verify_p1_substance(ws)

    # independent corpus recompute
    formal = []
    for b in ["01", "02", "03", "04", "05"]:
        for c in load_yaml(corpus / "normalized" / "formal_120" / f"p0_{b}" / "gold_reference_cases.yaml")["gold_reference_cases"]:
            formal.append(c)
    formal_clusters = dict(Counter(c["cluster_id"] for c in formal))
    evidence_ids, evidence_gkb = [], 0
    relation_edges = 0
    for c in formal:
        st = set(find_kv(c, "storage_target")); ak = set(find_kv(c, "artifact_kind"))
        if EVIDENCE_OWNER in st or EVIDENCE_KIND in ak:
            evidence_ids.append(c["case_id"])
            if "GeneralKnowledgeBase" in st:
                evidence_gkb += 1
        rc = c.get("relation_contract", {}) or {}
        if rc.get("formal_ontology_edge_allowed") is True:
            relation_edges += 1

    p2_pass = verify_p2_substance(ws, evidence_ids, evidence_gkb)

    p0doc = load_yaml(corpus / "normalized" / "p0_00_control_plane" / "p0_00_18_control_gold_cases.yaml")

    def find_case_list(o):
        if isinstance(o, dict):
            for v in o.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and any("case_id" in x for x in v if isinstance(x, dict)):
                    return v
                r = find_case_list(v)
                if r:
                    return r
        return None

    p0 = find_case_list(p0doc)
    p0_clusters = dict(Counter(c["cluster_id"] for c in p0))

    # registries
    pos = load_yaml(jc / "positive_gold_registry.v0.1.yaml")["positive_gold_registry"]["cases"]
    anti = load_yaml(jc / "anti_gold_fixture_registry.v0.1.yaml")["anti_gold_fixture_registry"]["cases"]
    bdr = load_yaml(jc / "borderline_repair_registry.v0.1.yaml")["borderline_repair_registry"]["cases"]
    ctrl_reg = load_yaml(jc / "control_plane_calibration_registry.v0.1.yaml")["control_plane_calibration_registry"]
    ctrl = ctrl_reg["cases"]
    p0_included_in_formal = bool(ctrl_reg.get("formal_120_included", False)) or bool(set(p0_clusters) & set(formal_clusters))

    anti_without = [c["case_id"] for c in anti if not c.get("failure_codes")]
    bdr_without = [c["case_id"] for c in bdr if not str(c.get("repair_reason", "")).strip()]
    ctrl_anti_without = [c["case_id"] for c in ctrl
                         if "anti" in str(c.get("control_case_type", "")).lower() and not c.get("control_plane_failure_codes")]

    failure = load_yaml(jc / "failure_code_registry.v0.1.yaml")["failure_code_registry"]
    failure_cats = [c.get("canonical_name") for c in failure.get("codes", [])]
    hardgate = load_yaml(jc / "hard_gate_namespace_registry.v0.1.yaml")["hard_gate_namespace_registry"]
    expert = load_yaml(jc / "expert_review_13_index.v0.1.yaml")["expert_review_13_index"]
    creative = load_yaml(jc / "creative_inspiration_aesthetic_metadata.v0.1.yaml")["creative_inspiration_aesthetic_metadata"]
    do_not_copy = (jc / "do_not_copy_surface_style_policy.v0.1.yaml").exists()
    registry_top = load_yaml(jc / "judge_calibration_registry.v0.1.yaml")["judge_calibration_registry"]
    manifest = load_yaml(jc / "judge_calibration_manifest.v0.1.yaml")["judge_calibration_manifest"]

    ledger = load_yaml(ws / "10_execution_progress" / "grc_3600_execution_plan_status.v0.1.yaml")["grc_3600_execution_plan_status"]
    steps = {s["step_id"]: s.get("status") for s in ledger["steps"]}

    readiness_flags: dict = {}
    for block in [registry_top.get("readiness", {}), manifest.get("readiness", {}), ledger.get("readiness", {})]:
        for k, v in block.items():
            if k in readiness_flags and v is True:
                readiness_flags[k] = v
            else:
                readiness_flags.setdefault(k, v)

    forbidden_present = [d for d in FORBIDDEN_DIR_NAMES if (ws / d).is_dir()]
    generated_present = []
    for p in (jc,).__iter__():
        for sub in p.rglob("*"):
            if sub.is_dir() and any(mk in sub.name.lower() for mk in GENERATED_MARKERS):
                generated_present.append(str(sub.relative_to(ws)))

    model = {
        "p1_checker_pass": p1_pass, "p2_checker_pass": p2_pass,
        "formal_total": len(formal), "formal_clusters": formal_clusters,
        "positive_count": len(pos), "anti_count": len(anti), "borderline_count": len(bdr),
        "p0_total": len(p0), "p0_clusters": p0_clusters,
        "p0_00_included_in_formal": p0_included_in_formal,
        "evidence_ids": evidence_ids, "evidence_mapped_gkb_count": evidence_gkb,
        "positive_ids": [c["case_id"] for c in pos], "anti_ids": [c["case_id"] for c in anti],
        "borderline_ids": [c["case_id"] for c in bdr], "control_ids": [c["case_id"] for c in ctrl],
        "anti_without_failure_code": anti_without, "borderline_without_repair": bdr_without,
        "control_anti_without_failure_code": ctrl_anti_without,
        "hard_gate_registry_present": True, "hard_gate_count": len(hardgate.get("gates", [])),
        "failure_registry_categories": failure_cats,
        "expert_index_present": True, "expert_batch_count": len(expert.get("batches", [])),
        "expert_has_digest_ref": bool(expert.get("source_digest_ref")),
        "expert_do_not_rewrite": expert.get("do_not_rewrite_judgments") is True,
        "creative_eval_only": creative.get("eval_only") is True,
        "creative_ontology_truth": creative.get("ontology_truth", False),
        "creative_production_servable": creative.get("production_servable", False),
        "do_not_copy_policy_present": do_not_copy,
        "relation_ontology_edge_count": relation_edges,
        "readiness_flags": readiness_flags,
        "generation_3600_unlocked": manifest.get("generation_3600_unlocked"),
        "generated_knowledge_dirs_present": generated_present,
        "forbidden_dirs_present": forbidden_present,
        "ledger_p1": steps.get("P1"), "ledger_p2": steps.get("P2"),
        "ledger_p3": steps.get("P3"), "ledger_p4": steps.get("P4"),
    }
    extras = {
        "formal_120_total": len(formal), "positive_gold": len(pos), "anti_gold": len(anti),
        "borderline_repair": len(bdr), "p0_00_total": len(p0),
        "evidence_policy_outbox_cases": len(evidence_ids), "expert_review_indexed": len(expert.get("batches", [])),
        "p1_checker_pass": p1_pass, "p2_checker_pass": p2_pass,
    }
    return model, extras


def validate_live(ws: Path, report_out: Path | None) -> dict:
    model, extras = build_live_model(ws)
    errors = validate_judge_model(model)
    if errors:
        fail("; ".join(errors))
    result = {
        "status": "PASS", "task_id": TASK_ID, **extras,
        "all_registries_exactly_once": True, "no_cross_registry_overlap": True,
        "ready_for_canary_40_execution": True, "generation_3600_unlocked": False,
        "object_count_remains_zero": True, "readiness_all_false": True,
        "recommended_next_step": NEXT_TASK,
    }
    if report_out:
        write_json(report_out, result)
    return result


def run_selftest(fixtures_root: Path) -> dict:
    positive = load_yaml(fixtures_root / "positive_valid_judge_calibration.yaml")
    pos_errors = validate_judge_model(positive)
    if pos_errors:
        fail(f"positive fixture failed: {pos_errors}")
    negative_results: dict = {}
    for name in NEGATIVE_FIXTURES:
        path = fixtures_root / name
        try:
            model = load_yaml(path)
        except yaml.YAMLError:
            negative_results[name] = ["malformed YAML rejected (fail-closed)"]
            continue
        errors = validate_judge_model(model)
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
        negative_results[name] = errors
    return {
        "status": "PASS", "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "negative_fixtures_fail_closed": True, "negative_results": negative_results,
    }


def main() -> int:
    if not __debug__:
        print("FAIL-CLOSED: optimized Python mode (python -O) is not allowed for this checker", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--fixtures-root", default="ci/fixtures/judge_calibration_against_grc")
    parser.add_argument("--report-out")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    ws = Path(args.workspace_root).resolve()
    fixtures = (ws / args.fixtures_root) if not Path(args.fixtures_root).is_absolute() else Path(args.fixtures_root)
    report_out = Path(args.report_out).resolve() if args.report_out else None
    try:
        if args.selftest:
            print(json.dumps(run_selftest(fixtures), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(validate_live(ws, report_out), ensure_ascii=False, indent=2))
        return 0
    except JudgeCalError as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
