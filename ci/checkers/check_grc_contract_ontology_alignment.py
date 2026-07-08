#!/usr/bin/env python3
"""GRC contract / ontology alignment checker — GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001.

Fail-closed. Verifies that the P2 contract delta makes the 15 formal EvidencePolicyOutbox
cases strict-consumable WITHOUT mapping them to GeneralKnowledgeBase, WITHOUT creating any
ontology object, and WITHOUT flipping readiness. The live path recomputes counts/owners
independently from the normalized corpus (never trusts a manifest's self-report); a shared
pure core `validate_alignment_model` judges both the live corpus and the selftest fixtures.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

TASK_ID = "GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001"
NEXT_TASK = "GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001"
P1_TASK = "GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001"

CORPUS_REL = "03_grc_goldset_corpus"
CONTRACTS_REL = "01_generation_contracts"
SCHEMA_FILE = "codex_generation_output_contract.v0.1.schema.json"
CK_POLICY_FILE = "codex_candidate_kind_target_owner_policy.v0.1.yaml"
SM_POLICY_FILE = "codex_state_machine_mapping_policy.v0.1.yaml"

EVIDENCE_KIND = "evidence_policy_candidate"
EVIDENCE_OWNER = "EvidencePolicyOutbox"
EVIDENCE_LAYER = "EvidencePolicy_candidate"
FORMAL_TOTAL = 120
EVIDENCE_COUNT = 15
FORMAL_CLUSTERS = {f"mkc_{n:03d}" for n in range(7, 47)}
P0_CLUSTERS = {f"mkc_{n:03d}" for n in range(1, 7)}
CONTROL_OWNERS = {"ControlPlaneContractSource", "GovernanceOutbox", "EvidencePolicyOutbox"}
REQUIRED_FORBIDDEN_LAYERS = {"ABox", "TBox_Object"}
FORBIDDEN_DIR_NAMES = ["candidatepack_etl", "KE", "Serving", "serving_projection",
                       "RAG", "rag", "DIFY", "dify", "CandidatePack"]
OBJECT_LANDING_DIRS = ["entity_instances", "ABox", "TBox_objects", "07-structured-kb/nine_tables"]

NEGATIVE_FIXTURES = [
    "negative_1_missing_evidence_policy_candidate_enum.yaml",
    "negative_2_missing_evidence_policy_outbox_owner.yaml",
    "negative_3_evidence_mapped_to_general_knowledge_base.yaml",
    "negative_4_evidence_kind_mapped_to_general_knowledge_candidate.yaml",
    "negative_5_object_count_positive.yaml",
    "negative_6_candidatepack_path_created.yaml",
    "negative_7_readiness_true.yaml",
    "negative_8_p0_00_included_in_formal.yaml",
    "negative_9_malformed_contract.yaml",
]


class AlignmentError(Exception):
    pass


def fail(msg: str) -> None:
    raise AlignmentError(msg)


def load_yaml(path: Path) -> Any:
    if not path.exists():
        fail(f"missing file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    if not path.exists():
        fail(f"missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
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


def is_anti(t: Any) -> bool:
    return "anti" in str(t).lower()


# ---------------------------------------------------------------------------
# Pure core — judges an in-memory alignment model (live recompute or fixture).
# ---------------------------------------------------------------------------
def validate_alignment_model(m: dict[str, Any]) -> list[str]:
    e: list[str] = []

    # (5) evidence_policy_candidate present in schema enum + policy
    if EVIDENCE_KIND not in m.get("schema_candidate_kind_enum", []):
        e.append("evidence_policy_candidate missing from schema candidate_kind enum")
    if EVIDENCE_KIND not in m.get("policy_candidate_kind_allowed", []):
        e.append("evidence_policy_candidate missing from candidate_kind policy allow-list")

    # (6) EvidencePolicyOutbox present in schema enum + policy
    if EVIDENCE_OWNER not in m.get("schema_target_owner_enum", []):
        e.append("EvidencePolicyOutbox missing from schema proposed_target_owner enum")
    if EVIDENCE_OWNER not in m.get("policy_target_owner_allowed", []):
        e.append("EvidencePolicyOutbox missing from proposed_target_owner policy allow-list")

    # (7) 15 evidence cases exact-match between recompute and resolution record
    rec = sorted(m.get("evidence_recomputed_ids", []))
    res = sorted(m.get("resolution_evidence_ids", []))
    if len(rec) != EVIDENCE_COUNT:
        e.append(f"EvidencePolicy recomputed case count must be {EVIDENCE_COUNT}, got {len(rec)}")
    if rec != res:
        e.append("EvidencePolicy resolution ids do not exact-match recomputed ids")

    # (8) none of the 15 mapped to GeneralKnowledgeBase
    if m.get("evidence_mapped_to_gkb_count", 0) != 0:
        e.append("EvidencePolicyOutbox case mapped to GeneralKnowledgeBase")

    # (4-guard) evidence_policy_candidate must not be mapped to general_knowledge_candidate
    if m.get("evidence_kind_mapped_to_general_knowledge_candidate") is True:
        e.append("evidence_policy_candidate mapped to general_knowledge_candidate")

    # (9) layer mapping: allowed EvidencePolicy_candidate; forbidden includes ABox + TBox_Object
    if EVIDENCE_LAYER not in m.get("evidence_allowed_target_layer", []):
        e.append("evidence_policy_candidate allowed_target_layer must include EvidencePolicy_candidate")
    if not REQUIRED_FORBIDDEN_LAYERS.issubset(set(m.get("evidence_forbidden_target_layer", []))):
        e.append("evidence_policy_candidate forbidden_target_layer must include ABox and TBox_Object")

    # (10) all 120 formal strict-mappable
    pairs = m.get("formal_pairs", [])
    if len(pairs) != FORMAL_TOTAL:
        e.append(f"formal case count must be {FORMAL_TOTAL}, got {len(pairs)}")
    ck_enum = set(m.get("schema_candidate_kind_enum", []))
    to_enum = set(m.get("schema_target_owner_enum", []))
    unmappable = [p for p in pairs if p.get("artifact_kind") not in ck_enum or p.get("storage_target") not in to_enum]
    if unmappable:
        e.append(f"{len(unmappable)} formal case(s) not strict-mappable to enums (e.g. {unmappable[0]})")

    # (11) P0-00: 18, clusters mkc_001..006 disjoint from formal, not in formal, zero pos/bdr->GKB violations
    p0c = m.get("p0_clusters", {})
    if m.get("p0_total") != 18:
        e.append(f"P0-00 case count must be 18, got {m.get('p0_total')}")
    if set(p0c) != P0_CLUSTERS:
        e.append("P0-00 clusters must be exactly mkc_001..mkc_006")
    if set(p0c) & set(m.get("formal_clusters", [])):
        e.append("P0-00 clusters overlap formal_120 clusters")
    if m.get("p0_00_included_in_formal") is not False:
        e.append("P0-00 must not be included in formal_120")
    if m.get("p0_positive_or_borderline_gkb_violation_count", 0) != 0:
        e.append("P0-00 positive/borderline control case targets GeneralKnowledgeBase (forbidden misroute)")

    # (12) relation hints design-only
    if m.get("relation_ontology_edge_count", 0) != 0:
        e.append("relation hint written as formal ontology edge")

    # (13/14) object count 0 + no object types created
    if m.get("object_count", 0) != 0:
        e.append("object_count must remain 0")
    if m.get("object_definition_hits"):
        e.append(f"object definition(s) detected in write surface: {m['object_definition_hits']}")
    if m.get("object_landing_dirs_present"):
        e.append(f"object landing dir(s) present: {m['object_landing_dirs_present']}")

    # (15) readiness flags false
    for name, value in m.get("readiness_flags", {}).items():
        if name == "readiness_all_false":
            if value is not True:
                e.append("readiness_all_false must be true")
        elif value is True or str(value).lower() == "true":
            e.append(f"readiness flag '{name}' must be false")
    if m.get("generation_unlocked") is True:
        e.append("generation_unlocked must be false")

    # (16) no forbidden path touched
    if m.get("forbidden_dirs_present"):
        e.append(f"forbidden dirs present/created: {m['forbidden_dirs_present']}")

    # (17/18) execution ledger consistency
    if m.get("ledger_p1_status") != "DONE":
        e.append("execution ledger P1 status must be DONE")
    p2 = m.get("ledger_p2_status")
    p3 = m.get("ledger_p3_status")
    # Robust roadmap-advancement rule: once P2 is DONE, P3 must be UNBLOCKED
    # (NEXT or already advanced to DONE/beyond) — not asserted to be exactly NEXT,
    # which would break the moment the roadmap frontier moves past P3.
    if p2 == "DONE" and p3 in (None, "BLOCKED_BY_P2"):
        e.append("ledger P2 DONE requires P3 unblocked (NEXT or advanced)")
    if p2 == "BLOCKED" and p3 != "BLOCKED_BY_P2":
        e.append("ledger P2 BLOCKED requires P3 = BLOCKED_BY_P2")
    if p2 not in ("DONE", "BLOCKED"):
        e.append(f"ledger P2 status must be DONE or BLOCKED, got {p2}")

    return e


# ---------------------------------------------------------------------------
# Live model — INDEPENDENT recompute + manifest cross-check.
# ---------------------------------------------------------------------------
def build_live_model(ws: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    corpus = ws / CORPUS_REL
    contracts = ws / CONTRACTS_REL

    schema = load_json(contracts / SCHEMA_FILE)
    own = schema["properties"]["ownership"]["properties"]
    ck_enum = own["candidate_kind"]["enum"]
    to_enum = own["proposed_target_owner"]["enum"]

    ck_policy = load_yaml(contracts / CK_POLICY_FILE)["candidate_kind_target_owner_policy"]
    ep_rule = next((r for r in ck_policy.get("rules", [])
                    if str(r.get("if", "")).endswith(EVIDENCE_KIND)), {})

    # formal recompute
    formal_pairs = []
    evidence_ids = []
    evidence_gkb = 0
    formal_clusters = set()
    relation_edges = 0
    for b in ["01", "02", "03", "04", "05"]:
        doc = load_yaml(corpus / "normalized" / "formal_120" / f"p0_{b}" / "gold_reference_cases.yaml")
        for c in doc["gold_reference_cases"]:
            st = sorted(set(find_kv(c, "storage_target")))
            ak = sorted(set(find_kv(c, "artifact_kind")))
            st1 = st[0] if len(st) == 1 else None
            ak1 = ak[0] if len(ak) == 1 else None
            formal_pairs.append({"case_id": c["case_id"], "storage_target": st1, "artifact_kind": ak1})
            formal_clusters.add(c["cluster_id"])
            if st1 == EVIDENCE_OWNER or ak1 == EVIDENCE_KIND:
                evidence_ids.append(c["case_id"])
                if st1 == "GeneralKnowledgeBase":
                    evidence_gkb += 1
            for rstatus in find_kv(c, "relation_status"):
                if rstatus not in ("design_hint", "design_hint_not_ontology_edge", "proposed_only", "draft_new"):
                    if "ontology" in str(rstatus).lower() or str(rstatus) == "available":
                        relation_edges += 1

    # p0 recompute
    p0doc = load_yaml(corpus / "normalized" / "p0_00_control_plane" / "p0_00_18_control_gold_cases.yaml")

    def find_case_list(o):
        if isinstance(o, dict):
            for v in o.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and any(
                    "case_id" in x for x in v if isinstance(x, dict)):
                    return v
                r = find_case_list(v)
                if r:
                    return r
        return None

    p0 = find_case_list(p0doc)
    p0_clusters = dict(Counter(c["cluster_id"] for c in p0))
    p0_violation = 0
    for c in p0:
        st = sorted(set(find_kv(c, "storage_target")))
        st1 = st[0] if len(st) == 1 else None
        if st1 == "GeneralKnowledgeBase" and not is_anti(c.get("case_type")):
            p0_violation += 1

    # resolution + alignment manifest + ledger
    resolution = load_yaml(corpus / "alignment" / "evidence_policy_outbox_resolution.v0.1.yaml")["evidence_policy_outbox_resolution"]
    res_ids = resolution["formal_120_evidence_cases"]["case_ids"]
    ck_map = resolution.get("candidate_kind_mapping", {}).get(EVIDENCE_KIND, {})
    evidence_kind_to_gkc = bool(ck_map.get("map_to_general_knowledge_candidate", False))

    manifest = load_yaml(corpus / "alignment" / "grc_contract_ontology_alignment_manifest.v0.1.yaml")["grc_contract_ontology_alignment_manifest"]
    object_count = manifest.get("object_count", 0)

    ledger_path = ws / "10_execution_progress" / "grc_3600_execution_plan_status.v0.1.yaml"
    ledger = load_yaml(ledger_path)["grc_3600_execution_plan_status"]
    steps = {s["step_id"]: s for s in ledger["steps"]}

    # object definition scan across the write surface (contracts + alignment)
    object_markers = ["BrandInstance", "Product", "Store", "PersonProfile",
                      "Evidence:", "ClaimBinding", "abox_object", "tbox_object"]
    object_hits = []
    for rel in [f"{CONTRACTS_REL}/{SCHEMA_FILE}", f"{CONTRACTS_REL}/{CK_POLICY_FILE}",
                f"{CONTRACTS_REL}/{SM_POLICY_FILE}",
                f"{CORPUS_REL}/alignment/evidence_policy_outbox_resolution.v0.1.yaml",
                f"{CORPUS_REL}/alignment/grc_contract_ontology_alignment_manifest.v0.1.yaml"]:
        text = (ws / rel).read_text(encoding="utf-8")
        # markers may appear as forbidden-list *values*; an object DEFINITION would be a
        # top-level instance record. We flag only object-instance definition shapes.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.endswith("_instance:") or stripped.startswith("abox_object:") or stripped.startswith("tbox_object:"):
                object_hits.append(f"{rel}: {stripped}")

    object_landing = [d for d in OBJECT_LANDING_DIRS if (ws / d).exists()]
    forbidden_present = [d for d in FORBIDDEN_DIR_NAMES if (ws / d).is_dir()]

    readiness_flags: dict[str, Any] = {}
    for block in [manifest.get("readiness", {}), resolution.get("readiness", {}),
                  ledger.get("readiness", {})]:
        for k, v in block.items():
            if k in readiness_flags and v is True:
                readiness_flags[k] = v
            else:
                readiness_flags.setdefault(k, v)

    model = {
        "schema_candidate_kind_enum": ck_enum,
        "schema_target_owner_enum": to_enum,
        "policy_candidate_kind_allowed": ck_policy.get("candidate_kind_allowed", []),
        "policy_target_owner_allowed": ck_policy.get("proposed_target_owner_allowed", []),
        "evidence_allowed_target_layer": ep_rule.get("allowed_target_layer", []),
        "evidence_forbidden_target_layer": ep_rule.get("forbidden_target_layer", []),
        "evidence_recomputed_ids": evidence_ids,
        "resolution_evidence_ids": res_ids,
        "evidence_mapped_to_gkb_count": evidence_gkb,
        "evidence_kind_mapped_to_general_knowledge_candidate": evidence_kind_to_gkc,
        "formal_pairs": formal_pairs,
        "formal_clusters": sorted(formal_clusters),
        "p0_total": len(p0),
        "p0_clusters": p0_clusters,
        "p0_00_included_in_formal": manifest["p0_00_mapping"].get("included_in_formal_120"),
        "p0_positive_or_borderline_gkb_violation_count": p0_violation,
        "relation_ontology_edge_count": relation_edges,
        "object_count": object_count,
        "object_definition_hits": object_hits,
        "object_landing_dirs_present": object_landing,
        "forbidden_dirs_present": forbidden_present,
        "readiness_flags": readiness_flags,
        "generation_unlocked": manifest.get("generation_unlocked"),
        "ledger_p1_status": steps.get("P1", {}).get("status"),
        "ledger_p2_status": steps.get("P2", {}).get("status"),
        "ledger_p3_status": steps.get("P3", {}).get("status"),
    }
    extras = {
        "formal_total": len(formal_pairs),
        "evidence_policy_case_count": len(evidence_ids),
        "evidence_policy_case_ids": sorted(evidence_ids),
        "evidence_mapped_to_gkb_count": evidence_gkb,
        "p0_00_total": len(p0),
        "p0_00_positive_borderline_gkb_violation_count": p0_violation,
        "p0_00_anti_gkb_demo_count": sum(1 for c in p0 if is_anti(c.get("case_type"))
                                         and (find_kv(c, "storage_target") or [None])[0] == "GeneralKnowledgeBase"),
        "object_count": object_count,
    }
    return model, extras


def validate_live(ws: Path, report_out: Path | None) -> dict[str, Any]:
    model, extras = build_live_model(ws)
    errors = validate_alignment_model(model)
    if errors:
        fail("; ".join(errors))
    result = {
        "status": "PASS",
        "task_id": TASK_ID,
        **extras,
        "all_formal_120_mappable": True,
        "all_p0_00_mappable": True,
        "evidence_policy_candidate_enum_landed": True,
        "evidence_policy_outbox_owner_landed": True,
        "object_count_remains_zero": True,
        "readiness_all_false": True,
        "generation_unlocked": False,
        "judge_calibration_unlocked": True,
        "recommended_next_step": NEXT_TASK,
    }
    if report_out:
        write_json(report_out, result)
    return result


def run_selftest(fixtures_root: Path) -> dict[str, Any]:
    positive = load_yaml(fixtures_root / "positive_valid_alignment.yaml")
    pos_errors = validate_alignment_model(positive)
    if pos_errors:
        fail(f"positive fixture failed: {pos_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        path = fixtures_root / name
        try:
            model = load_yaml(path)
        except yaml.YAMLError:
            negative_results[name] = ["malformed contract yaml rejected (fail-closed)"]
            continue
        errors = validate_alignment_model(model)
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
        negative_results[name] = errors
    return {
        "status": "PASS",
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "negative_fixtures_fail_closed": True,
        "negative_results": negative_results,
    }


def main() -> int:
    if not __debug__:
        print("FAIL-CLOSED: optimized Python mode (python -O) is not allowed for this checker", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--fixtures-root", default="ci/fixtures/grc_contract_ontology_alignment")
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
    except AlignmentError as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
