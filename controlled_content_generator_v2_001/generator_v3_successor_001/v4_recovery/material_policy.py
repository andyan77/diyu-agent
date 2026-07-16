"""Evidence material and three-way audience-surface policy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import contract


def _normalize_source(raw: Mapping[str, Any]) -> dict[str, Any]:
    source_id = contract.as_text(raw.get("source_id"), "E_V4_SOURCE_ID")
    source_text = contract.as_text(raw.get("source_text"), "E_V4_SOURCE_TEXT")
    expected = contract.sha256_text(source_text)
    supplied = raw.get("source_digest")
    if supplied is not None:
        contract.require(supplied == expected, "E_V4_SOURCE_DIGEST", source_id)
    return {"source_id": source_id, "source_text": source_text,
            "source_digest": expected}


def _normalize_authorization(raw: Mapping[str, Any]) -> dict[str, Any]:
    authorization_id = contract.as_text(raw.get("authorization_id"),
                                        "E_V4_AUTHORIZATION_ID")
    scope = contract.as_text(raw.get("scope"), "E_V4_AUTHORIZATION_SCOPE")
    expected = contract.sha256_text(scope)
    supplied = raw.get("authorization_digest")
    if supplied is not None:
        contract.require(supplied == expected, "E_V4_AUTHORIZATION_DIGEST",
                         authorization_id)
    return {"authorization_id": authorization_id, "scope": scope,
            "authorization_digest": expected}


def _normalize_evidence_span(
    raw: Mapping[str, Any],
    source_by_id: Mapping[str, Mapping[str, Any]],
    fact_id: str,
) -> dict[str, Any]:
    contract.exact_fields(
        raw, {"source_id", "byte_start", "byte_end", "quote"},
        "E_V4_FACT_EVIDENCE_SPAN_FIELDS")
    source_id = contract.as_text(raw.get("source_id"),
                                 "E_V4_FACT_EVIDENCE_SOURCE_ID")
    contract.require(source_id in source_by_id,
                     "E_V4_FACT_EVIDENCE_SOURCE_UNKNOWN", fact_id)
    byte_start = raw.get("byte_start")
    byte_end = raw.get("byte_end")
    contract.require(type(byte_start) is int and type(byte_end) is int and
                     byte_start >= 0 and byte_end > byte_start,
                     "E_V4_FACT_EVIDENCE_BYTE_RANGE", fact_id)
    quote = contract.as_text(raw.get("quote"), "E_V4_FACT_EVIDENCE_QUOTE")
    source_bytes = source_by_id[source_id]["source_text"].encode("utf-8")
    contract.require(byte_end <= len(source_bytes) and
                     source_bytes[byte_start:byte_end] == quote.encode("utf-8"),
                     "E_V4_FACT_EVIDENCE_QUOTE_MISMATCH", fact_id)
    return {
        "source_id": source_id,
        "byte_start": byte_start,
        "byte_end": byte_end,
        "quote": quote,
    }


def _normalize_fact(
    raw: Mapping[str, Any],
    source_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    fact_id = contract.as_text(raw.get("fact_id"), "E_V4_FACT_ID")
    fact_value = contract.as_text(raw.get("fact_value"), "E_V4_FACT_VALUE")
    policy = contract.as_text(raw.get("surface_policy"), "E_V4_FACT_POLICY")
    contract.require(policy in contract.SURFACE_POLICIES, "E_V4_FACT_POLICY", policy)
    expected = contract.sha256_text(fact_value)
    supplied = raw.get("fact_value_digest")
    if supplied is not None:
        contract.require(supplied == expected, "E_V4_FACT_DIGEST", fact_id)
    source_ids = sorted(contract.unique_text_list(raw.get("source_ids"),
                                                   "E_V4_FACT_SOURCES"))
    raw_spans = raw.get("evidence_spans")
    contract.require(isinstance(raw_spans, list) and raw_spans,
                     "E_V4_FACT_EVIDENCE_SPANS", fact_id)
    evidence_spans = [
        _normalize_evidence_span(
            contract.as_mapping(span, "E_V4_FACT_EVIDENCE_SPAN"),
            source_by_id,
            fact_id,
        )
        for span in raw_spans
    ]
    evidence_spans = sorted(
        evidence_spans,
        key=lambda span: (span["source_id"], span["byte_start"],
                          span["byte_end"], span["quote"]),
    )
    contract.require({span["source_id"] for span in evidence_spans} ==
                     set(source_ids),
                     "E_V4_FACT_EVIDENCE_SOURCE_COVERAGE", fact_id)
    return {
        "fact_id": fact_id,
        "slot_id": contract.as_text(raw.get("slot_id"), "E_V4_FACT_SLOT"),
        "fact_value": fact_value,
        "fact_value_digest": expected,
        "source_ids": source_ids,
        "evidence_spans": evidence_spans,
        "authorization_ids": sorted(contract.unique_text_list(
            raw.get("authorization_ids"), "E_V4_FACT_AUTHS")),
        "surface_policy": policy,
        "conditions": sorted(contract.unique_text_list(raw.get("conditions", []),
                                                        "E_V4_FACT_CONDITIONS",
                                                        allow_empty=True)),
        "prohibited_surface_terms": sorted(contract.unique_text_list(
            raw.get("prohibited_surface_terms", []), "E_V4_FACT_PROHIBITED",
            allow_empty=True)),
    }


def normalize_material(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize and digest-close one scenario's structured evidence material."""
    scenario_id = contract.as_text(raw.get("scenario_id"), "E_V4_MATERIAL_SCENARIO")
    profile_id = contract.as_text(raw.get("profile_id"), "E_V4_MATERIAL_PROFILE")
    raw_sources = raw.get("sources")
    raw_auths = raw.get("authorizations")
    raw_facts = raw.get("facts")
    contract.require(isinstance(raw_sources, list) and raw_sources,
                     "E_V4_MATERIAL_SOURCES")
    contract.require(isinstance(raw_auths, list) and raw_auths,
                     "E_V4_MATERIAL_AUTHS")
    contract.require(isinstance(raw_facts, list) and raw_facts,
                     "E_V4_MATERIAL_FACTS")
    sources = [_normalize_source(contract.as_mapping(row, "E_V4_SOURCE"))
               for row in raw_sources]
    authorizations = [_normalize_authorization(
        contract.as_mapping(row, "E_V4_AUTHORIZATION")) for row in raw_auths]
    source_by_id = contract.unique_by(sources, "source_id", "E_V4_SOURCE_DUP")
    auth_by_id = contract.unique_by(authorizations, "authorization_id", "E_V4_AUTH_DUP")
    facts = [_normalize_fact(contract.as_mapping(row, "E_V4_FACT"), source_by_id)
             for row in raw_facts]
    contract.unique_by(facts, "fact_id", "E_V4_FACT_DUP")
    for fact in facts:
        contract.require(set(fact["source_ids"]).issubset(source_by_id),
                         "E_V4_FACT_SOURCE_UNKNOWN", fact["fact_id"])
        contract.require(set(fact["authorization_ids"]).issubset(auth_by_id),
                         "E_V4_FACT_AUTH_UNKNOWN", fact["fact_id"])
    contract.require(any(fact["surface_policy"] == "MUST_SURFACE" for fact in facts),
                     "E_V4_MATERIAL_NO_MUST")
    material: dict[str, Any] = {
        "schema_version": contract.MATERIAL_SCHEMA,
        "scenario_id": scenario_id,
        "profile_id": profile_id,
        "sources": sorted(sources, key=lambda row: row["source_id"]),
        "authorizations": sorted(authorizations,
                                 key=lambda row: row["authorization_id"]),
        "facts": sorted(facts, key=lambda row: row["fact_id"]),
        "material_digest": "",
    }
    contract.close_digest(material, "material_digest")
    validate_material(material)
    return material


def validate_material(material: Mapping[str, Any]) -> None:
    contract.exact_fields(material, {"schema_version", "scenario_id", "profile_id",
                                     "sources", "authorizations", "facts",
                                     "material_digest"}, "E_V4_MATERIAL_FIELDS")
    contract.require(material["schema_version"] == contract.MATERIAL_SCHEMA,
                     "E_V4_MATERIAL_SCHEMA")
    contract.as_text(material["scenario_id"], "E_V4_MATERIAL_SCENARIO")
    contract.as_text(material["profile_id"], "E_V4_MATERIAL_PROFILE")
    contract.validate_digest(material, "material_digest", "E_V4_MATERIAL_DIGEST")
    contract.require(isinstance(material["sources"], list) and material["sources"],
                     "E_V4_MATERIAL_SOURCES")
    contract.require(isinstance(material["authorizations"], list) and
                     material["authorizations"], "E_V4_MATERIAL_AUTHS")
    contract.require(isinstance(material["facts"], list) and material["facts"],
                     "E_V4_MATERIAL_FACTS")
    # Normalization is idempotent and independently re-checks every nested digest.
    seen_sources: set[str] = set()
    source_by_id: dict[str, Mapping[str, Any]] = {}
    for source in material["sources"]:
        source = contract.as_mapping(source, "E_V4_SOURCE")
        contract.exact_fields(source, {"source_id", "source_text", "source_digest"},
                              "E_V4_SOURCE_FIELDS")
        source_id = contract.as_text(source["source_id"], "E_V4_SOURCE_ID")
        contract.require(source_id not in seen_sources, "E_V4_SOURCE_DUP", source_id)
        seen_sources.add(source_id)
        source_by_id[source_id] = source
        contract.as_text(source["source_text"], "E_V4_SOURCE_TEXT")
        contract.require(source["source_digest"] ==
                         contract.sha256_text(source["source_text"]),
                         "E_V4_SOURCE_DIGEST", source_id)
    seen_authorizations: set[str] = set()
    for authorization in material["authorizations"]:
        authorization = contract.as_mapping(authorization, "E_V4_AUTHORIZATION")
        contract.exact_fields(authorization,
                              {"authorization_id", "scope", "authorization_digest"},
                              "E_V4_AUTHORIZATION_FIELDS")
        authorization_id = contract.as_text(
            authorization["authorization_id"], "E_V4_AUTHORIZATION_ID")
        contract.require(authorization_id not in seen_authorizations,
                         "E_V4_AUTH_DUP", authorization_id)
        seen_authorizations.add(authorization_id)
        contract.as_text(authorization["scope"], "E_V4_AUTHORIZATION_SCOPE")
        contract.require(authorization["authorization_digest"] ==
                         contract.sha256_text(authorization["scope"]),
                         "E_V4_AUTHORIZATION_DIGEST",
                         authorization_id)
    source_ids = seen_sources
    auth_ids = seen_authorizations
    seen_facts: set[str] = set()
    for fact in material["facts"]:
        fact = contract.as_mapping(fact, "E_V4_FACT")
        contract.exact_fields(
            fact, {"fact_id", "slot_id", "fact_value", "fact_value_digest",
                   "source_ids", "evidence_spans", "authorization_ids",
                   "surface_policy", "conditions",
                   "prohibited_surface_terms"}, "E_V4_FACT_FIELDS")
        fact_id = contract.as_text(fact["fact_id"], "E_V4_FACT_ID")
        contract.require(fact_id not in seen_facts, "E_V4_FACT_DUP", fact_id)
        seen_facts.add(fact_id)
        contract.as_text(fact["slot_id"], "E_V4_FACT_SLOT")
        contract.as_text(fact["fact_value"], "E_V4_FACT_VALUE")
        contract.require(fact["fact_value_digest"] ==
                         contract.sha256_text(fact["fact_value"]),
                         "E_V4_FACT_DIGEST", fact_id)
        contract.require(fact["surface_policy"] in contract.SURFACE_POLICIES,
                         "E_V4_FACT_POLICY", fact_id)
        fact_sources = set(contract.unique_text_list(
            fact["source_ids"], "E_V4_FACT_SOURCES"))
        raw_spans = fact["evidence_spans"]
        contract.require(isinstance(raw_spans, list) and raw_spans,
                         "E_V4_FACT_EVIDENCE_SPANS", fact_id)
        spans = [
            _normalize_evidence_span(
                contract.as_mapping(span, "E_V4_FACT_EVIDENCE_SPAN"),
                source_by_id,
                fact_id,
            )
            for span in raw_spans
        ]
        canonical_spans = sorted(
            spans,
            key=lambda span: (span["source_id"], span["byte_start"],
                              span["byte_end"], span["quote"]),
        )
        contract.require(spans == canonical_spans,
                         "E_V4_FACT_EVIDENCE_SPAN_ORDER", fact_id)
        contract.require({span["source_id"] for span in spans} == fact_sources,
                         "E_V4_FACT_EVIDENCE_SOURCE_COVERAGE", fact_id)
        fact_authorizations = set(contract.unique_text_list(
            fact["authorization_ids"], "E_V4_FACT_AUTHS"))
        contract.unique_text_list(fact["conditions"], "E_V4_FACT_CONDITIONS",
                                  allow_empty=True)
        contract.unique_text_list(fact["prohibited_surface_terms"],
                                  "E_V4_FACT_PROHIBITED", allow_empty=True)
        contract.require(fact_sources.issubset(source_ids),
                         "E_V4_FACT_SOURCE_UNKNOWN", fact_id)
        contract.require(fact_authorizations.issubset(auth_ids),
                         "E_V4_FACT_AUTH_UNKNOWN", fact_id)
    contract.require(any(fact["surface_policy"] == "MUST_SURFACE"
                         for fact in material["facts"]), "E_V4_MATERIAL_NO_MUST")


def compile_surface_policy(material: Mapping[str, Any]) -> dict[str, Any]:
    validate_material(material)
    grouped = {policy: [] for policy in sorted(contract.SURFACE_POLICIES)}
    for fact in material["facts"]:
        grouped[fact["surface_policy"]].append(fact["fact_id"])
    policy: dict[str, Any] = {
        "schema_version": contract.POLICY_SCHEMA,
        "scenario_id": material["scenario_id"],
        "profile_id": material["profile_id"],
        "material_digest": material["material_digest"],
        "must_surface_fact_ids": sorted(grouped["MUST_SURFACE"]),
        "may_surface_fact_ids": sorted(grouped["MAY_SURFACE"]),
        "control_only_fact_ids": sorted(grouped["CONTROL_ONLY"]),
        "author_visible_fact_ids": sorted(fact["fact_id"] for fact in material["facts"]),
        "policy_digest": "",
    }
    contract.close_digest(policy, "policy_digest")
    validate_surface_policy(policy, material)
    return policy


def validate_surface_policy(policy: Mapping[str, Any], material: Mapping[str, Any]) -> None:
    contract.exact_fields(
        policy, {"schema_version", "scenario_id", "profile_id", "material_digest",
                 "must_surface_fact_ids", "may_surface_fact_ids",
                 "control_only_fact_ids", "author_visible_fact_ids", "policy_digest"},
        "E_V4_POLICY_FIELDS")
    contract.require(policy["schema_version"] == contract.POLICY_SCHEMA,
                     "E_V4_POLICY_SCHEMA")
    contract.require(policy["scenario_id"] == material["scenario_id"] and
                     policy["profile_id"] == material["profile_id"],
                     "E_V4_POLICY_MATERIAL_ID")
    contract.require(policy["material_digest"] == material["material_digest"],
                     "E_V4_POLICY_MATERIAL_DIGEST")
    groups = [set(contract.unique_text_list(policy[name], f"E_V4_POLICY_LIST:{name}",
                                           allow_empty=True))
              for name in ("must_surface_fact_ids", "may_surface_fact_ids",
                           "control_only_fact_ids")]
    contract.require(not (groups[0] & groups[1] or groups[0] & groups[2] or
                          groups[1] & groups[2]), "E_V4_POLICY_OVERLAP")
    all_ids = {fact["fact_id"] for fact in material["facts"]}
    contract.require(bool(groups[0]), "E_V4_POLICY_NO_MUST")
    contract.require(set.union(*groups) == all_ids, "E_V4_POLICY_COVERAGE")
    visible_ids = set(contract.unique_text_list(
        policy["author_visible_fact_ids"], "E_V4_POLICY_AUTHOR_VISIBILITY"))
    contract.require(visible_ids == all_ids,
                     "E_V4_POLICY_AUTHOR_VISIBILITY")
    contract.validate_digest(policy, "policy_digest", "E_V4_POLICY_DIGEST")


__all__ = ["compile_surface_policy", "normalize_material", "validate_material",
           "validate_surface_policy"]
