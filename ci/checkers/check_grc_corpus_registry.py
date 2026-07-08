#!/usr/bin/env python3
"""GRC corpus registry checker — GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001.

Fail-closed. The live path recomputes every critical count/cluster/evidence set
*independently* from the normalized corpus files (it never trusts a manifest's
self-reported number), then cross-checks the manifests against that recompute.
A shared pure core `validate_corpus_model` judges both the live corpus and the
selftest fixtures, so the 8 negative fixtures exercise the same logic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

TASK_ID = "GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001"
NEXT_TASK = "GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001"

CORPUS_REL = "03_grc_goldset_corpus"
SCHEMA_REL = f"{CORPUS_REL}/schema"

EXPECTED_SOURCE_FILE_COUNT = 32
FORMAL_TOTAL = 120
FORMAL_CLUSTERS = [f"mkc_{n:03d}" for n in range(7, 47)]          # mkc_007..mkc_046 (40)
P0_00_CLUSTERS = [f"mkc_{n:03d}" for n in range(1, 7)]            # mkc_001..mkc_006 (6)
PER_CLUSTER = 3
TYPE_KEYS = ("positive_gold", "anti_gold", "borderline_repair")
EVIDENCE_STORAGE = "EvidencePolicyOutbox"
EVIDENCE_ARTIFACT = "evidence_policy_candidate"
EVIDENCE_COUNT = 15
EXPERT_CANONICAL_FILENAME = "expert_review_13_batches.v0.1.txt"

FORBIDDEN_DIR_NAMES = [
    "candidatepack_etl", "KE", "Serving", "serving_projection",
    "RAG", "rag", "DIFY", "dify",
]
GENERATED_KNOWLEDGE_MARKERS = ["generated_knowledge", "candidatepack", "canary", "3600_generation", "generated_batch"]

BATCHES = ["01", "02", "03", "04", "05"]

NEGATIVE_FIXTURES = [
    "negative_1_formal_count_119.yaml",
    "negative_2_p0_00_included_in_formal.yaml",
    "negative_3_missing_source_digest.yaml",
    "negative_4_chinese_filename_as_canonical.yaml",
    "negative_5_evidence_policy_silently_mapped.yaml",
    "negative_6_readiness_flag_true.yaml",
    "negative_7_malformed_yaml.yaml",
    "negative_8_duplicate_case_id.yaml",
]


class CorpusCheckError(Exception):
    pass


def fail(message: str) -> None:
    raise CorpusCheckError(message)


def is_ascii(text: str) -> bool:
    try:
        str(text).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
# Pure validation core — judges an in-memory corpus model.
# Both the live recompute and the selftest fixtures feed this.
# ---------------------------------------------------------------------------
def validate_corpus_model(m: dict[str, Any]) -> list[str]:
    e: list[str] = []

    # --- source digest coverage / count
    digest = m.get("source_digest_files", [])
    if m.get("expected_source_files_count") != EXPECTED_SOURCE_FILE_COUNT:
        e.append(f"expected_source_files_count must be {EXPECTED_SOURCE_FILE_COUNT}")
    if len(digest) != EXPECTED_SOURCE_FILE_COUNT:
        e.append(f"source_digest must cover exactly {EXPECTED_SOURCE_FILE_COUNT} files, got {len(digest)}")
    if len({d["source_path"] for d in digest}) != len(digest):
        e.append("source_digest has duplicate source_path entries")

    # --- registry references each normalized file exactly once
    reg = m.get("registered_normalized_files", [])
    disk = m.get("normalized_files_on_disk", [])
    if len(reg) != len(set(reg)):
        e.append("registered_normalized_files contains duplicates (not exactly-once)")
    if set(reg) != set(disk):
        e.append("registered_normalized_files does not equal normalized files on disk")
    if len(reg) != EXPECTED_SOURCE_FILE_COUNT:
        e.append(f"registered_normalized_files count must be {EXPECTED_SOURCE_FILE_COUNT}, got {len(reg)}")

    # --- formal_120 counts (independent recompute lives in caller; here we judge it)
    fids = m.get("formal_case_ids", [])
    fclusters = m.get("formal_clusters", {})       # cluster_id -> count
    ftypes = m.get("formal_type_counts", {})
    if len(fids) != FORMAL_TOTAL:
        e.append(f"formal_120 total case count must be {FORMAL_TOTAL}, got {len(fids)}")
    if len(fids) != len(set(fids)):
        dup = [k for k, v in Counter(fids).items() if v > 1]
        e.append(f"formal_120 duplicate case_id: {dup}")
    if sum(fclusters.values()) != FORMAL_TOTAL:
        e.append(f"formal_120 cluster case sum must be {FORMAL_TOTAL}, got {sum(fclusters.values())}")
    if sorted(fclusters) != FORMAL_CLUSTERS:
        e.append("formal_120 cluster coverage must be exactly mkc_007..mkc_046")
    off = {c: n for c, n in fclusters.items() if n != PER_CLUSTER}
    if off:
        e.append(f"formal_120 clusters not exactly {PER_CLUSTER} cases: {off}")
    for k in TYPE_KEYS:
        if ftypes.get(k) != FORMAL_TOTAL // 3:
            e.append(f"formal_120 {k} must be {FORMAL_TOTAL // 3}, got {ftypes.get(k)}")

    # --- P0-00
    pids = m.get("p0_case_ids", [])
    pclusters = m.get("p0_clusters", {})
    if len(pids) != 18:
        e.append(f"P0-00 case count must be 18, got {len(pids)}")
    if len(pids) != len(set(pids)):
        e.append("P0-00 duplicate case_id")
    if sorted(pclusters) != P0_00_CLUSTERS:
        e.append("P0-00 cluster coverage must be exactly mkc_001..mkc_006")
    if m.get("p0_00_included_in_formal") is not False:
        e.append("P0-00 must NOT be included in formal_120 (formal_120_included must be false)")
    # P0-00 cluster ids must not overlap formal ids
    if set(pclusters) & set(fclusters):
        e.append("P0-00 clusters overlap formal_120 clusters (mixed into formal)")

    # --- readiness flags
    for name, value in m.get("readiness_flags", {}).items():
        if name == "readiness_all_false":
            if value is not True:
                e.append("readiness_all_false must be true")
        elif value is True or str(value).lower() == "true":
            e.append(f"readiness flag '{name}' must be false")

    # --- canonical machine paths must be ASCII
    for p in m.get("canonical_machine_paths", []):
        if not is_ascii(p):
            e.append(f"canonical machine path is not ASCII: {p!r}")
    if m.get("expert_canonical_filename") != EXPERT_CANONICAL_FILENAME:
        e.append("expert_review_13 canonical filename mismatch")
    if not is_ascii(m.get("expert_canonical_filename", "")):
        e.append("expert_review_13 canonical filename not ASCII")

    # --- EvidencePolicy gap recorded, not silently mapped
    rec = sorted(m.get("evidence_recomputed_ids", []))
    led = sorted(m.get("evidence_ledger_ids", []))
    if len(rec) != EVIDENCE_COUNT:
        e.append(f"EvidencePolicy recomputed case count must be {EVIDENCE_COUNT}, got {len(rec)}")
    if rec != led:
        e.append("EvidencePolicy blocking-gap ledger ids do not match recomputed ids")
    if m.get("evidence_silently_mapped_to_gkb") is not False:
        e.append("EvidencePolicyOutbox silently mapped to GeneralKnowledgeBase")
    if m.get("evidence_resolved_in_task") is not False:
        e.append("EvidencePolicy gap must not be resolved in this task")

    # --- no forbidden / generated-knowledge dirs
    if m.get("forbidden_dirs_present"):
        e.append(f"forbidden dirs present/created: {m['forbidden_dirs_present']}")
    if m.get("generated_knowledge_dirs_present"):
        e.append(f"generated-knowledge dirs present: {m['generated_knowledge_dirs_present']}")

    return e


# ---------------------------------------------------------------------------
# Live: build the model by INDEPENDENT recompute, then cross-check manifests.
# ---------------------------------------------------------------------------
def build_live_model(ws: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    corpus = ws / CORPUS_REL
    norm = corpus / "normalized"

    # -- independently enumerate the 32 source files
    source_files = []
    for d in ["GRC-P0-00", "GRC-P0-01", "GRC-P0-02", "GRC-P0-03", "GRC-P0-04", "GRC-P0-05"]:
        for f in sorted((ws / "tmp" / d).glob("*")):
            if f.is_file():
                source_files.append(f)
    txt = ws / "tmp/13个批次专家评审.txt"
    if not txt.exists():
        fail("expert review source TXT missing")
    source_files.append(txt)
    if len(source_files) != EXPECTED_SOURCE_FILE_COUNT:
        fail(f"independent source enumeration found {len(source_files)}, expected {EXPECTED_SOURCE_FILE_COUNT}")

    # -- source_digest_manifest: must exist, parse, cover exactly the 32 sources with correct sha256
    digest = load_yaml(corpus / "source_digest_manifest.v0.1.yaml")["source_digest_manifest"]
    digest_rows = digest["source_files"]
    digest_by_src = {r["source_path"]: r for r in digest_rows}
    for f in source_files:
        rel = str(f.relative_to(ws))
        if rel not in digest_by_src:
            fail(f"source_digest missing coverage for {rel}")
        row = digest_by_src[rel]
        real_sha = sha256_file(f)
        if row["source_sha256"] != real_sha:
            fail(f"source_digest sha256 mismatch for {rel}")
        # normalized copy must exist and be byte-identical
        ncanon = ws / row["canonical_normalized_path"]
        if not ncanon.exists():
            fail(f"normalized copy missing: {row['canonical_normalized_path']}")
        if sha256_file(ncanon) != real_sha:
            fail(f"normalized copy not byte-identical to source: {row['canonical_normalized_path']}")

    # -- walk normalized dir independently
    disk = sorted(str(p.relative_to(ws)) for p in norm.rglob("*") if p.is_file())

    # -- registry
    registry = load_yaml(corpus / "corpus_registry.v0.1.yaml")["corpus_registry"]
    registered = registry["registered_normalized_files"]

    # -- INDEPENDENT recompute of formal_120 from normalized case files
    formal_rows = []
    for b in BATCHES:
        gp = norm / "formal_120" / f"p0_{b}" / "gold_reference_cases.yaml"
        doc = load_yaml(gp)
        for c in doc["gold_reference_cases"]:
            st = set(find_kv(c, "storage_target"))
            ak = set(find_kv(c, "artifact_kind"))
            formal_rows.append({
                "case_id": c["case_id"],
                "cluster_id": c["cluster_id"],
                "case_type": c["case_type"],
                "is_evidence": EVIDENCE_STORAGE in st or EVIDENCE_ARTIFACT in ak,
                "mapped_to_gkb": "GeneralKnowledgeBase" in st,
            })
    formal_ids = [r["case_id"] for r in formal_rows]
    formal_clusters = dict(Counter(r["cluster_id"] for r in formal_rows))
    formal_types = dict(Counter(r["case_type"] for r in formal_rows))
    evidence_rows = [r for r in formal_rows if r["is_evidence"]]
    evidence_ids = [r["case_id"] for r in evidence_rows]
    # silently-mapped detection: an evidence case whose normalized copy routes to GKB
    silently_mapped = any(r["mapped_to_gkb"] for r in evidence_rows)

    # -- INDEPENDENT recompute of P0-00
    p0_doc = load_yaml(norm / "p0_00_control_plane" / "p0_00_18_control_gold_cases.yaml")

    def find_case_list(o):
        if isinstance(o, dict):
            for v in o.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and any(
                    "case_id" in x for x in v if isinstance(x, dict)
                ):
                    return v
                r = find_case_list(v)
                if r:
                    return r
        return None

    p0_cases = find_case_list(p0_doc)
    p0_ids = [c["case_id"] for c in p0_cases]
    p0_clusters = dict(Counter(c["cluster_id"] for c in p0_cases))

    # -- manifests (cross-check self-reports against recompute)
    fman = load_yaml(corpus / "formal_120_manifest.v0.1.yaml")["formal_120_manifest"]
    if fman.get("total_case_count") != len(formal_ids):
        fail(f"formal_120_manifest.total_case_count ({fman.get('total_case_count')}) != recomputed ({len(formal_ids)})")
    if fman.get("p0_00_included") is not False:
        fail("formal_120_manifest.p0_00_included must be false")
    for k in TYPE_KEYS:
        if fman.get("case_type_distribution", {}).get(k) != formal_types.get(k):
            fail(f"formal_120_manifest {k} disagrees with recompute")

    p0man = load_yaml(corpus / "p0_00_control_plane_manifest.v0.1.yaml")["p0_00_control_plane_manifest"]
    if p0man.get("case_count") != len(p0_ids):
        fail("p0_00 manifest case_count disagrees with recompute")
    p0_included = p0man.get("formal_120_included")

    ledger = load_yaml(corpus / "blocking_gap_ledger.v0.1.yaml")["blocking_gap_ledger"]
    gap = next((g for g in ledger["gaps"] if g.get("storage_target") == EVIDENCE_STORAGE), None)
    if gap is None:
        fail("blocking_gap_ledger missing EvidencePolicyOutbox gap")
    ledger_ids = gap.get("case_ids", [])
    if gap.get("requires_next_task") != NEXT_TASK:
        fail("blocking_gap_ledger requires_next_task mismatch")

    expert = load_yaml(corpus / "expert_review_13_manifest.v0.1.yaml")["expert_review_13_manifest"]

    # -- schema validation of normalized outputs (Codex note #7)
    schema_validate_live(ws)

    # -- gather readiness flags across registry + all manifests
    readiness_flags: dict[str, Any] = {}
    for block in [registry.get("readiness", {}), fman.get("readiness", {}),
                  p0man.get("readiness", {}), ledger.get("readiness", {})]:
        for k, v in block.items():
            # if the same flag appears with conflicting values, keep the offending (true) one visible
            if k in readiness_flags and readiness_flags[k] != v:
                if v is True:
                    readiness_flags[k] = v
            else:
                readiness_flags[k] = v

    # -- canonical machine paths (must be ASCII)
    canonical_paths = list(registered)
    canonical_paths += [r["canonical_normalized_path"] for r in digest_rows]
    canonical_paths.append(expert.get("canonical_ascii_path", ""))
    for g in registry.get("groups", {}).values():
        canonical_paths.append(g.get("manifest", ""))

    # -- forbidden / generated dir filesystem scan
    forbidden_present = [name for name in FORBIDDEN_DIR_NAMES if (ws / name).is_dir()]
    generated_present = []
    for p in corpus.rglob("*"):
        if p.is_dir() and any(marker in p.name.lower() for marker in GENERATED_KNOWLEDGE_MARKERS):
            generated_present.append(str(p.relative_to(ws)))

    model = {
        "expected_source_files_count": digest.get("expected_source_files_count"),
        "source_digest_files": digest_rows,
        "registered_normalized_files": registered,
        "normalized_files_on_disk": disk,
        "formal_case_ids": formal_ids,
        "formal_clusters": formal_clusters,
        "formal_type_counts": formal_types,
        "p0_case_ids": p0_ids,
        "p0_clusters": p0_clusters,
        "p0_00_included_in_formal": p0_included,
        "readiness_flags": readiness_flags,
        "canonical_machine_paths": canonical_paths,
        "expert_canonical_filename": expert.get("canonical_filename"),
        "evidence_recomputed_ids": evidence_ids,
        "evidence_ledger_ids": ledger_ids,
        "evidence_silently_mapped_to_gkb": silently_mapped,
        "evidence_resolved_in_task": gap.get("resolved_in_this_task"),
        "forbidden_dirs_present": forbidden_present,
        "generated_knowledge_dirs_present": generated_present,
    }

    report_extras = {
        "source_files_count": len(source_files),
        "normalized_files_count": len(disk),
        "formal_120_case_count": len(formal_ids),
        "formal_cluster_count": len(formal_clusters),
        "positive_gold_count": formal_types.get("positive_gold"),
        "anti_gold_count": formal_types.get("anti_gold"),
        "borderline_repair_count": formal_types.get("borderline_repair"),
        "p0_00_case_count": len(p0_ids),
        "evidence_policy_case_count": len(evidence_ids),
        "evidence_policy_case_ids": sorted(evidence_ids),
        "byte_identity_verified": True,
    }
    return model, report_extras


def schema_validate_live(ws: Path) -> None:
    corpus = ws / CORPUS_REL
    norm = corpus / "normalized"
    sc = corpus / "schema"
    schemas = {name: load_json(sc / f"{name}.schema.v0.1.json") for name in [
        "grc_case", "grc_batch_manifest", "grc_owner_storage_audit",
        "grc_hard_gate_selfcheck", "grc_judge_calibration_index",
    ]}
    pairs = [
        ("batch_manifest.yaml", "grc_batch_manifest"),
        ("owner_storage_audit.yaml", "grc_owner_storage_audit"),
        ("hard_gate_selfcheck.yaml", "grc_hard_gate_selfcheck"),
        ("judge_calibration_index.yaml", "grc_judge_calibration_index"),
    ]
    for b in BATCHES:
        base = norm / "formal_120" / f"p0_{b}"
        for fname, sname in pairs:
            doc = load_yaml(base / fname)
            errs = list(Draft7Validator(schemas[sname]).iter_errors(doc))
            if errs:
                fail(f"schema {sname} failed for p0_{b}/{fname}: {errs[0].message}")
        doc = load_yaml(base / "gold_reference_cases.yaml")
        for c in doc["gold_reference_cases"]:
            errs = list(Draft7Validator(schemas["grc_case"]).iter_errors(c))
            if errs:
                fail(f"schema grc_case failed for {c.get('case_id')}: {errs[0].message}")


def validate_live(ws: Path, report_out: Path | None) -> dict[str, Any]:
    model, extras = build_live_model(ws)
    errors = validate_corpus_model(model)
    if errors:
        fail("; ".join(errors))
    result = {
        "status": "PASS",
        "task_id": TASK_ID,
        **extras,
        "formal_cluster_exactness": "all_clusters_exactly_3",
        "p0_00_formal_120_included": False,
        "chinese_filename_used_as_canonical_path": False,
        "evidence_policy_silently_mapped": False,
        "evidence_policy_resolved_in_this_task": False,
        "readiness_all_false": True,
        "candidatepack_created": False,
        "KE_touched": False,
        "Serving_touched": False,
        "RAG_touched": False,
        "DIFY_touched": False,
        "generation_unlocked": False,
        "recommended_next_step": NEXT_TASK,
    }
    if report_out:
        write_json(report_out, result)
    return result


def run_selftest(fixtures_root: Path) -> dict[str, Any]:
    positive = fixtures_root / "positive_valid_minimal_corpus.yaml"
    pos_model = load_yaml(positive)
    pos_errors = validate_corpus_model(pos_model)
    if pos_errors:
        fail(f"positive fixture failed: {pos_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        path = fixtures_root / name
        try:
            model = load_yaml(path)
        except yaml.YAMLError:
            negative_results[name] = ["malformed YAML rejected (fail-closed)"]
            continue
        errors = validate_corpus_model(model)
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
    parser.add_argument("--fixtures-root", default="ci/fixtures/grc_corpus_registry")
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
    except CorpusCheckError as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
