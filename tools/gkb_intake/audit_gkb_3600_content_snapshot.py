#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    import yaml
except Exception as exc:
    raise SystemExit("FAIL: PyYAML is required by current YAML workspace tools") from exc


REQUIRED_CARD_FIELDS = [
    "candidate_id",
    "batch_id",
    "source_origin",
    "target_owner",
    "target_domain_module",
    "target_module",
    "object_type",
    "one_sentence_definition",
    "operational_definition",
    "not_this",
    "applicable_when",
    "not_applicable_when",
    "input_context_required",
    "output_effect",
    "relations",
    "risk_boundary",
    "evidence_requirement",
    "claim_policy",
    "capability_group_refs",
    "capability_consumption_hint",
    "serving_projection_hint",
    "semantic_fingerprint",
    "duplicate_control",
    "readiness",
]

REQUIRED_RICH_BLOCKS = [
    "concept_mechanism",
    "domain_logic",
    "content_generation_usage",
    "merchandising_or_retail_usage",
    "transformation_rules",
    "generic_micro_scenarios",
    "anti_patterns",
    "boundary_language",
    "retrieval_phrases",
    "capability_consumption_hint",
]

READINESS_KEYS = [
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
]

RISK_TOKENS = [
    "SKU", "skuid", "货号", "价格", "折扣", "销量", "库存",
    "上海", "北京", "广州", "深圳", "杭州", "成都", "武汉", "南京",
    "小红书爆款", "抖音爆款",
    "客户说", "顾客反馈", "真实客户",
    "检测报告", "国家标准", "医学", "治疗", "功效",
    "某品牌", "品牌A", "品牌B",
]

GENERIC_PHRASES = [
    "提升内容质量",
    "增强用户感知",
    "帮助品牌",
    "适用于多种场景",
    "形成闭环",
    "赋能",
    "高质量内容",
    "差异化表达",
    "沉淀资产",
    "提高转化",
]

FORBIDDEN_TEXT_KEYS = [
    "approved_passage_text",
    "rendered_body",
    "passage_text",
    "context_bundle",
    "DIFY_workflow",
    "dify_workflow",
]


def read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def unwrap_list(data: Any, preferred_keys: list[str]) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in preferred_keys:
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        # fallback: first list of dicts
        for value in data.values():
            if isinstance(value, list) and all(isinstance(x, dict) for x in value):
                return value
    raise SystemExit(f"FAIL cannot unwrap list from YAML keys={preferred_keys}")


def to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def normalize_text(value: Any) -> str:
    text = to_text(value).lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。；：、,.!?！？\-\_\|\[\]\{\}\(\)\"'“”‘’]", "", text)
    return text


def short(value: Any, n: int = 160) -> str:
    text = re.sub(r"\s+", " ", to_text(value)).strip()
    return text[:n]


def digest_text(value: Any) -> str:
    return hashlib.sha256(to_text(value).encode("utf-8")).hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def scan_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    findings = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if k in FORBIDDEN_TEXT_KEYS:
                findings.append(path)
            findings.extend(scan_forbidden_keys(v, path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            findings.extend(scan_forbidden_keys(item, f"{prefix}[{i}]"))
    return findings


def get_rich_block(item: dict, block_name: str) -> Any:
    """Read a rich body block, preferring the nested rich_body_blocks shape.

    Current YAML nests the blocks under item["rich_body_blocks"][block_name];
    older/flat drafts kept them at the top level. Prefer nested, fall back to
    top-level. This fixes the prior bug where nested body text was mis-read as
    empty because only item.get(block_name) (top level) was consulted.
    """
    blocks = item.get("rich_body_blocks")
    if isinstance(blocks, dict) and block_name in blocks:
        return blocks.get(block_name)
    return item.get(block_name)


def selftest() -> None:
    """Regression guard for the rich_body_blocks nesting bug.

    Nested rich_body_blocks must NOT be mis-judged as empty; top-level fallback
    must still work. Optionally validates fixtures when present. This selftest
    does not relax any boundary / readiness / candidatepack / forbidden-path rule.
    """
    nested = {
        "candidate_id": "SELFTEST-NESTED-1",
        "rich_body_blocks": {
            "concept_mechanism": "嵌套机制正文",
            "anti_patterns": ["嵌套反模式"],
        },
    }
    assert get_rich_block(nested, "concept_mechanism") == "嵌套机制正文", "nested str block mis-read"
    assert get_rich_block(nested, "anti_patterns") == ["嵌套反模式"], "nested list block mis-read"
    assert not is_empty(get_rich_block(nested, "concept_mechanism")), "nested block wrongly judged empty"

    flat = {"candidate_id": "SELFTEST-FLAT-1", "concept_mechanism": "顶层机制正文"}
    assert get_rich_block(flat, "concept_mechanism") == "顶层机制正文", "top-level fallback broken"

    absent = {"candidate_id": "SELFTEST-ABSENT-1", "rich_body_blocks": {"concept_mechanism": "x"}}
    assert is_empty(get_rich_block(absent, "domain_logic")), "absent nested block should read empty"

    # Optional fixture validation (skipped silently when fixtures are absent).
    pos = Path("fixtures/gkb_intake/positive/rich_body_nested_shape.yaml")
    neg = Path("fixtures/gkb_intake/negative/rich_body_missing_nested_blocks.yaml")
    if pos.exists():
        items = unwrap_list(read_yaml(pos), ["rich_body_items", "items", "bodies"])
        assert items, "positive fixture has no items"
        for it in items:
            empty_blocks = {blk for blk in REQUIRED_RICH_BLOCKS if is_empty(get_rich_block(it, blk))}
            assert not empty_blocks, f"positive fixture {it.get('candidate_id')} empty blocks: {empty_blocks}"
    if neg.exists():
        items = unwrap_list(read_yaml(neg), ["rich_body_items", "items", "bodies"])
        assert items, "negative fixture has no items"
        assert any(
            sum(1 for blk in REQUIRED_RICH_BLOCKS if is_empty(get_rich_block(it, blk))) >= 3
            for it in items
        ), "negative fixture should miss >=3 required nested blocks"

    print("PASS audit rich_body nested reader selftest")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=False)
    ap.add_argument("--selftest", action="store_true",
                    help="run rich_body nested reader selftest (and fixture validation) then exit")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if not args.workspace:
        ap.error("--workspace is required unless --selftest is given")

    ws = Path(args.workspace)
    reports = ws / "11_reports"
    reports.mkdir(parents=True, exist_ok=True)

    cards_path = ws / "04_aligned_candidates/knowledge_candidate_cards.yaml"
    bodies_path = ws / "05_rich_body_blocks/knowledge_candidate_rich_body_blocks.yaml"
    relations_path = ws / "06_relations/relation_edge_candidates.csv"
    fingerprints_path = ws / "07_fingerprints/semantic_fingerprint_registry.csv"
    source_gaps_path = ws / "08_outbox/source_gap_candidates.yaml"

    cards = unwrap_list(read_yaml(cards_path), ["candidates", "knowledge_candidate_cards", "items"])
    bodies = unwrap_list(read_yaml(bodies_path), ["rich_body_items", "items", "bodies"])
    relations = load_csv(relations_path)
    fingerprints = load_csv(fingerprints_path)
    source_gaps = unwrap_list(read_yaml(source_gaps_path), ["source_gap_candidates", "items"])

    cards_by_id = {}
    duplicate_ids = []
    for c in cards:
        cid = c.get("candidate_id")
        if cid in cards_by_id:
            duplicate_ids.append(cid)
        if cid:
            cards_by_id[cid] = c

    body_by_id = {}
    for b in bodies:
        cid = b.get("candidate_id")
        if cid:
            body_by_id[cid] = b

    # 1. Field coverage
    field_rows = []
    missing_by_candidate = Counter()
    for field in REQUIRED_CARD_FIELDS:
        present = 0
        nonempty = 0
        for c in cards:
            if field in c:
                present += 1
                if not is_empty(c.get(field)):
                    nonempty += 1
                else:
                    missing_by_candidate[c.get("candidate_id", "<missing_id>")] += 1
            else:
                missing_by_candidate[c.get("candidate_id", "<missing_id>")] += 1
        field_rows.append({
            "field": field,
            "present_count": present,
            "nonempty_count": nonempty,
            "missing_or_empty_count": len(cards) - nonempty,
            "nonempty_rate": round(nonempty / len(cards), 4) if cards else 0,
        })

    write_csv(
        reports / "field_coverage_matrix.csv",
        field_rows,
        ["field", "present_count", "nonempty_count", "missing_or_empty_count", "nonempty_rate"],
    )

    # 2. Label/layer distribution
    dist_fields = [
        "batch_id",
        "source_origin",
        "target_owner",
        "target_domain_module",
        "target_module",
        "object_type",
        "declared_layer",
        "route",
        "candidatepack_eligibility",
    ]
    label_rows = []
    for field in dist_fields:
        counter = Counter(to_text(c.get(field, "<missing>")) for c in cards)
        for value, count in counter.most_common():
            label_rows.append({
                "field": field,
                "value": value,
                "count": count,
                "rate": round(count / len(cards), 4) if cards else 0,
            })

    write_csv(
        reports / "layer_label_distribution.csv",
        label_rows,
        ["field", "value", "count", "rate"],
    )

    # 3. Module coverage
    module_counter = Counter()
    batch_module_counter = Counter()
    for c in cards:
        module = to_text(c.get("target_module", "<missing>"))
        domain = to_text(c.get("target_domain_module", "<missing>"))
        batch = to_text(c.get("batch_id", "<missing>"))
        module_counter[(domain, module)] += 1
        batch_module_counter[(batch, domain, module)] += 1

    module_rows = [
        {"target_domain_module": d, "target_module": m, "count": n}
        for (d, m), n in module_counter.most_common()
    ]
    write_csv(
        reports / "module_coverage_matrix.csv",
        module_rows,
        ["target_domain_module", "target_module", "count"],
    )

    # 4. Body block profile
    body_profile_rows = []
    missing_body_blocks = Counter()
    repeated_body_digests = Counter()
    body_risk_token_hits = Counter()
    generic_phrase_hits = Counter()

    for b in bodies:
        cid = b.get("candidate_id", "<missing_id>")
        for block in REQUIRED_RICH_BLOCKS:
            value = get_rich_block(b, block)
            text = to_text(value)
            if is_empty(value):
                missing_body_blocks[block] += 1
            if text:
                repeated_body_digests[(block, digest_text(text))] += 1
            risk_hit_count = sum(1 for token in RISK_TOKENS if token in text)
            generic_hit_count = sum(1 for phrase in GENERIC_PHRASES if phrase in text)
            if risk_hit_count:
                body_risk_token_hits[block] += risk_hit_count
            if generic_hit_count:
                generic_phrase_hits[block] += generic_hit_count
            body_profile_rows.append({
                "candidate_id": cid,
                "block": block,
                "char_len": len(text),
                "is_empty": is_empty(value),
                "risk_token_hits": risk_hit_count,
                "generic_phrase_hits": generic_hit_count,
                "preview": short(text, 120),
            })

    write_csv(
        reports / "body_block_quality_profile.csv",
        body_profile_rows,
        ["candidate_id", "block", "char_len", "is_empty", "risk_token_hits", "generic_phrase_hits", "preview"],
    )

    # 5. Relation integrity
    relation_rows = []
    orphan_source = 0
    orphan_target = 0
    missing_relation_fields = 0
    for r in relations:
        source_id = r.get("source_candidate_id") or r.get("source_id") or ""
        target_id = r.get("target_candidate_id") or r.get("target_id") or ""
        source_exists = source_id in cards_by_id
        target_exists = target_id in cards_by_id
        if not source_exists:
            orphan_source += 1
        if not target_exists:
            orphan_target += 1
        if not source_id or not target_id or not r.get("relation_type"):
            missing_relation_fields += 1
        if not source_exists or not target_exists or missing_relation_fields:
            relation_rows.append({
                "relation_id": r.get("relation_id", ""),
                "source_candidate_id": source_id,
                "target_candidate_id": target_id,
                "relation_type": r.get("relation_type", ""),
                "source_exists": source_exists,
                "target_exists": target_exists,
            })

    write_csv(
        reports / "relation_integrity_report.csv",
        relation_rows[:2000],
        ["relation_id", "source_candidate_id", "target_candidate_id", "relation_type", "source_exists", "target_exists"],
    )

    # 6. Capability routing profile
    capability_rows = []
    capability_missing = 0
    hint_missing = 0
    affects_missing = 0
    capability_counter = Counter()

    for c in cards:
        cid = c.get("candidate_id", "<missing_id>")
        caps = c.get("capability_group_refs", [])
        hint = c.get("capability_consumption_hint", {})
        caps_text = to_text(caps)
        if is_empty(caps):
            capability_missing += 1
        else:
            if isinstance(caps, list):
                for cap in caps:
                    capability_counter[to_text(cap)] += 1
            else:
                capability_counter[caps_text] += 1

        if is_empty(hint):
            hint_missing += 1

        hint_text = to_text(hint)
        has_effect = any(key in hint_text for key in ["route", "strategy", "asset", "checker", "output", "context_bundle", "affects"])
        if not has_effect:
            affects_missing += 1

        capability_rows.append({
            "candidate_id": cid,
            "capability_group_refs": caps_text,
            "hint_present": not is_empty(hint),
            "has_effect_signal": has_effect,
            "hint_preview": short(hint_text, 140),
        })

    write_csv(
        reports / "capability_routing_quality_report.csv",
        capability_rows,
        ["candidate_id", "capability_group_refs", "hint_present", "has_effect_signal", "hint_preview"],
    )

    # 7. Fingerprints
    fp_by_candidate = {}
    fp_counter = Counter()
    for row in fingerprints:
        cid = row.get("candidate_id") or row.get("asset_id") or ""
        fp = row.get("semantic_fingerprint") or row.get("fingerprint") or ""
        if cid and fp:
            fp_by_candidate[cid] = fp
            fp_counter[fp] += 1

    duplicate_fp = {fp: n for fp, n in fp_counter.items() if n > 1}

    # 8. Repetition / template smell
    definition_counter = Counter()
    operational_counter = Counter()
    for c in cards:
        definition_counter[normalize_text(c.get("one_sentence_definition"))] += 1
        operational_counter[normalize_text(c.get("operational_definition"))[:120]] += 1

    repeated_definitions = {k: v for k, v in definition_counter.items() if k and v > 1}
    repeated_operation_prefixes = {k: v for k, v in operational_counter.items() if k and v > 1}

    forbidden_key_paths = []
    for c in cards[:]:
        paths = scan_forbidden_keys(c)
        if paths:
            forbidden_key_paths.append({"candidate_id": c.get("candidate_id"), "paths": paths})

    for b in bodies[:]:
        paths = scan_forbidden_keys(b)
        if paths:
            forbidden_key_paths.append({"candidate_id": b.get("candidate_id"), "paths": paths})

    # 9. Stratified sample
    sample_rows = []
    grouped = defaultdict(list)
    for c in cards:
        key = (to_text(c.get("batch_id", "<missing>")), to_text(c.get("target_domain_module", "<missing>")))
        grouped[key].append(c)

    for key, items in sorted(grouped.items()):
        for c in items[:3]:
            cid = c.get("candidate_id", "")
            b = body_by_id.get(cid, {})
            sample_rows.append({
                "candidate_id": cid,
                "batch_id": c.get("batch_id", ""),
                "target_domain_module": c.get("target_domain_module", ""),
                "target_module": c.get("target_module", ""),
                "object_type": c.get("object_type", ""),
                "declared_layer": c.get("declared_layer", ""),
                "source_origin": c.get("source_origin", ""),
                "route": c.get("route", ""),
                "definition": short(c.get("one_sentence_definition"), 220),
                "operational_definition": short(c.get("operational_definition"), 260),
                "not_this": short(c.get("not_this"), 220),
                "concept_mechanism": short(get_rich_block(b, "concept_mechanism"), 260),
                "content_generation_usage": short(get_rich_block(b, "content_generation_usage"), 260),
                "anti_patterns": short(get_rich_block(b, "anti_patterns"), 260),
            })

    write_csv(
        reports / "stratified_review_sample.csv",
        sample_rows,
        [
            "candidate_id", "batch_id", "target_domain_module", "target_module",
            "object_type", "declared_layer", "source_origin", "route",
            "definition", "operational_definition", "not_this",
            "concept_mechanism", "content_generation_usage", "anti_patterns",
        ],
    )

    md_lines = []
    md_lines.append("# 3600 Draft Content Quality Snapshot")
    md_lines.append("")
    md_lines.append("## Verdict")
    md_lines.append("")
    md_lines.append("This report audits draft quality indicators only. It does not approve CandidatePack, KE, Serving, RAG, DIFY, release, or production readiness.")
    md_lines.append("")
    md_lines.append("## Counts")
    md_lines.append("")
    md_lines.append(f"- candidates: {len(cards)}")
    md_lines.append(f"- rich_body_items: {len(bodies)}")
    md_lines.append(f"- source_gap_candidates: {len(source_gaps)}")
    md_lines.append(f"- relation_edges: {len(relations)}")
    md_lines.append(f"- fingerprints: {len(fingerprints)}")
    md_lines.append(f"- duplicate_candidate_ids: {len(duplicate_ids)}")
    md_lines.append(f"- duplicate_fingerprints: {len(duplicate_fp)}")
    md_lines.append("")
    md_lines.append("## Safety / Boundary Signals")
    md_lines.append("")
    md_lines.append(f"- readiness_true_count: {sum(1 for c in cards for k in READINESS_KEYS if isinstance(c.get('readiness'), dict) and c['readiness'].get(k) is True)}")
    md_lines.append(f"- candidatepack_eligibility_true_count: {sum(1 for c in cards if c.get('candidatepack_eligibility') is True)}")
    md_lines.append(f"- source_pack_refs_nonempty_count: {sum(1 for c in cards if not is_empty(c.get('source_pack_refs')))}")
    md_lines.append(f"- forbidden_text_key_paths_count: {len(forbidden_key_paths)}")
    md_lines.append("")
    md_lines.append("## Field Coverage Worst Fields")
    md_lines.append("")
    for row in sorted(field_rows, key=lambda x: x["nonempty_rate"])[:12]:
        md_lines.append(f"- {row['field']}: nonempty_rate={row['nonempty_rate']} missing_or_empty={row['missing_or_empty_count']}")
    md_lines.append("")
    md_lines.append("## Layer / Label Distribution")
    md_lines.append("")
    for field in ["object_type", "declared_layer", "target_owner", "source_origin", "route", "candidatepack_eligibility"]:
        md_lines.append(f"### {field}")
        for row in [r for r in label_rows if r["field"] == field][:20]:
            md_lines.append(f"- {row['value']}: {row['count']} ({row['rate']})")
        md_lines.append("")
    md_lines.append("## Body Quality Signals")
    md_lines.append("")
    md_lines.append(f"- missing_body_blocks: {dict(missing_body_blocks)}")
    md_lines.append(f"- body_risk_token_hits: {dict(body_risk_token_hits)}")
    md_lines.append(f"- generic_phrase_hits: {dict(generic_phrase_hits)}")
    md_lines.append("")
    md_lines.append("## Relation Integrity")
    md_lines.append("")
    md_lines.append(f"- orphan_source_edges: {orphan_source}")
    md_lines.append(f"- orphan_target_edges: {orphan_target}")
    md_lines.append(f"- relation_missing_fields: {missing_relation_fields}")
    md_lines.append("")
    md_lines.append("## Capability Routing")
    md_lines.append("")
    md_lines.append(f"- capability_missing_count: {capability_missing}")
    md_lines.append(f"- capability_hint_missing_count: {hint_missing}")
    md_lines.append(f"- no_effect_signal_count: {affects_missing}")
    md_lines.append("- capability_distribution:")
    for cap, count in capability_counter.most_common():
        md_lines.append(f"  - {cap}: {count}")
    md_lines.append("")
    md_lines.append("## Template / Repetition Signals")
    md_lines.append("")
    md_lines.append(f"- repeated_one_sentence_definitions: {len(repeated_definitions)}")
    md_lines.append(f"- repeated_operational_definition_prefixes: {len(repeated_operation_prefixes)}")
    md_lines.append("")
    md_lines.append("## Human Review Sample")
    md_lines.append("")
    md_lines.append("See `stratified_review_sample.csv` for full sampled rows.")
    md_lines.append("")
    for row in sample_rows[:30]:
        md_lines.append(f"### {row['candidate_id']} · {row['batch_id']} · {row['target_module']}")
        md_lines.append(f"- object_type: {row['object_type']}")
        md_lines.append(f"- declared_layer: {row['declared_layer']}")
        md_lines.append(f"- definition: {row['definition']}")
        md_lines.append(f"- operational_definition: {row['operational_definition']}")
        md_lines.append(f"- concept_mechanism: {row['concept_mechanism']}")
        md_lines.append("")

    (reports / "3600_content_quality_snapshot.md").write_text("\n".join(md_lines), encoding="utf-8")

    summary = {
        "audit_id": "GKB_INTAKE_3600_DRAFT_CONTENT_QUALITY_SNAPSHOT_AUDIT_001",
        "counts": {
            "candidates": len(cards),
            "rich_body_items": len(bodies),
            "source_gap_candidates": len(source_gaps),
            "relation_edges": len(relations),
            "fingerprints": len(fingerprints),
            "unique_candidate_ids": len(cards_by_id),
            "duplicate_candidate_ids": len(duplicate_ids),
            "unique_fingerprints": len(fp_counter),
            "duplicate_fingerprints": len(duplicate_fp),
        },
        "boundary": {
            "readiness_true_count": sum(1 for c in cards for k in READINESS_KEYS if isinstance(c.get("readiness"), dict) and c["readiness"].get(k) is True),
            "candidatepack_eligibility_true_count": sum(1 for c in cards if c.get("candidatepack_eligibility") is True),
            "source_pack_refs_nonempty_count": sum(1 for c in cards if not is_empty(c.get("source_pack_refs"))),
            "forbidden_text_key_paths_count": len(forbidden_key_paths),
        },
        "field_coverage_worst": sorted(field_rows, key=lambda x: x["nonempty_rate"])[:20],
        "body_quality": {
            "missing_body_blocks": dict(missing_body_blocks),
            "body_risk_token_hits": dict(body_risk_token_hits),
            "generic_phrase_hits": dict(generic_phrase_hits),
        },
        "relation_integrity": {
            "orphan_source_edges": orphan_source,
            "orphan_target_edges": orphan_target,
            "relation_missing_fields": missing_relation_fields,
        },
        "capability_routing": {
            "capability_missing_count": capability_missing,
            "capability_hint_missing_count": hint_missing,
            "no_effect_signal_count": affects_missing,
            "capability_distribution": dict(capability_counter),
        },
        "template_repetition": {
            "repeated_one_sentence_definitions": len(repeated_definitions),
            "repeated_operational_definition_prefixes": len(repeated_operation_prefixes),
        },
        "outputs": {
            "field_coverage_matrix": "11_reports/field_coverage_matrix.csv",
            "layer_label_distribution": "11_reports/layer_label_distribution.csv",
            "module_coverage_matrix": "11_reports/module_coverage_matrix.csv",
            "body_block_quality_profile": "11_reports/body_block_quality_profile.csv",
            "relation_integrity_report": "11_reports/relation_integrity_report.csv",
            "capability_routing_quality_report": "11_reports/capability_routing_quality_report.csv",
            "stratified_review_sample": "11_reports/stratified_review_sample.csv",
            "markdown_report": "11_reports/3600_content_quality_snapshot.md",
        },
    }

    (reports / "3600_content_quality_snapshot.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))
    print("WROTE", reports / "3600_content_quality_snapshot.md")
    print("WROTE", reports / "3600_content_quality_snapshot.json")


if __name__ == "__main__":
    main()