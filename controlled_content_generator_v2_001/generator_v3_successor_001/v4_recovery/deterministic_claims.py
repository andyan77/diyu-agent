"""已知零容忍成分/结构/性能词的确定性材料绑定门。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from collections.abc import Mapping
from . import contract


REGISTRY_PATH = (Path(__file__).resolve().parent / "registry" /
                 "deterministic_claim_registry.v1.json")


def validate_registry(value: Mapping[str, Any]) -> None:
    contract.exact_fields(value, {
        "schema_version", "registry_id", "registered_before_qualification",
        "coverage_status", "approved_by", "categories", "registry_digest",
    }, "E_V4_CLAIM_REGISTRY_FIELDS")
    contract.require(
        value["schema_version"] == "gate1-v4-deterministic-claim-registry-v1"
        and value["registered_before_qualification"] is True
        and value["coverage_status"] == "KNOWN_RISK_SEED_NOT_COMPLETE_DOMAIN_ONTOLOGY",
        "E_V4_CLAIM_REGISTRY_STATE")
    contract.as_text(value["registry_id"], "E_V4_CLAIM_REGISTRY_ID")
    contract.as_text(value["approved_by"], "E_V4_CLAIM_REGISTRY_APPROVER")
    categories = contract.as_mapping(value["categories"],
                                     "E_V4_CLAIM_REGISTRY_CATEGORIES")
    contract.exact_fields(categories, {
        "fiber_or_composition", "construction", "durability_or_performance",
    }, "E_V4_CLAIM_REGISTRY_CATEGORY_FIELDS")
    all_terms: list[str] = []
    for category, terms in categories.items():
        values = contract.unique_text_list(
            terms, f"E_V4_CLAIM_REGISTRY_TERMS:{category}")
        all_terms.extend(values)
    contract.require(len(all_terms) == len(set(all_terms)),
                     "E_V4_CLAIM_REGISTRY_CROSS_CATEGORY_DUP")
    contract.validate_digest(value, "registry_digest", "E_V4_CLAIM_REGISTRY_DIGEST")


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    contract.require(isinstance(value, dict), "E_V4_CLAIM_REGISTRY_OBJECT")
    validate_registry(value)
    return value


def unsupported_claim_codes(output: Mapping[str, Any], request: Mapping[str, Any],
                            registry: Mapping[str, Any]) -> list[str]:
    """只对已登记词做机械绑定；未登记语义继续交事实审，不宣称全域覆盖。"""
    validate_registry(registry)
    facts = {fact["fact_id"]: fact for fact in request["typed_material"]["facts"]}
    codes: set[str] = set()
    for surface in output["surface_units"]:
        if surface["surface_kind"] == "synthetic_disclosure":
            continue
        text = str(surface["text"]).casefold()
        bound_facts = [facts[fact_id] for fact_id in surface["fact_ids"]
                       if fact_id in facts
                       and facts[fact_id]["surface_policy"] != "CONTROL_ONLY"]
        for category, terms in registry["categories"].items():
            for term in terms:
                normalized_term = str(term).casefold()
                if normalized_term not in text:
                    continue
                supported = any(
                    normalized_term in str(fact["fact_value"]).casefold()
                    and any(
                        normalized_term in str(span["quote"]).casefold()
                        for span in fact["evidence_spans"]
                    )
                    for fact in bound_facts)
                if not supported:
                    codes.add(
                        f"HV_UNSUPPORTED_DETERMINISTIC_CLAIM:{category}:{term}")
    return sorted(codes)


__all__ = ["load_registry", "unsupported_claim_codes", "validate_registry"]
