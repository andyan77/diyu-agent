"""套路构念的成对记录、聚合与一致性统计。"""

from __future__ import annotations

import itertools
import math
from collections import Counter, defaultdict
from typing import Any, Iterable

from .canonical import digest_json, stable_id
from .calibration import REQUIRED_FAMILIES, family_coverage
from .qualification_data import validate_qualification_records

BINARY = {"FORMULAIC", "NOT_FORMULAIC"}
AXES = ("argument_spine", "evidence_progression", "limitation_function",
        "viewpoint_anchor", "closing_function", "transformation_depth")


def verdict_from_axes(axes: dict[str, Any],
                      necessary_grammar_exception_id: str | None) -> str:
    if set(axes) != set(AXES):
        raise ValueError("formulaic axes field set mismatch")
    for field in AXES[:-1]:
        if axes[field] not in {"SAME", "DIFFERENT", "UNCLEAR", "NECESSARY_GRAMMAR"}:
            raise ValueError(f"invalid formulaic axis: {field}")
    if axes["transformation_depth"] not in {
            "SURFACE_ONLY", "STRUCTURAL_CHANGE", "UNCLEAR", "NECESSARY_GRAMMAR"}:
        raise ValueError("invalid transformation_depth")
    values = list(axes.values())
    necessary = "NECESSARY_GRAMMAR" in values
    if necessary and not str(necessary_grammar_exception_id or "").strip():
        raise ValueError("necessary grammar requires a preregistered exception")
    if sum(value == "UNCLEAR" for value in values) >= 2:
        return "INDETERMINATE"
    abc_same = sum(axes[field] == "SAME" for field in AXES[:3])
    de_same = sum(axes[field] == "SAME" for field in AXES[3:5])
    if (abc_same >= 2 and de_same >= 1
            and axes["transformation_depth"] == "SURFACE_ONLY"):
        return "FORMULAIC"
    if abc_same == 3:
        return "INDETERMINATE"
    if necessary:
        return "NECESSARY_GRAMMAR"
    return "NOT_FORMULAIC"


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> list[float] | None:
    if trials <= 0 or not 0 <= successes <= trials:
        return None
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    radius = (z / denominator
              * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)))
    return [max(0.0, center - radius), min(1.0, center + radius)]


def canonical_pair_id(left_id: str, right_id: str) -> str:
    if left_id == right_id:
        raise ValueError("self pair is invalid")
    left, right = sorted((left_id, right_id))
    return stable_id("PAIR", left, right)


def expand_group_to_pairs(item_ids: Iterable[str]) -> list[tuple[str, str]]:
    return list(itertools.combinations(sorted(set(item_ids)), 2))


def confirmed_item_rate(edges: Iterable[dict[str, Any]], positive_ids: Iterable[str]) -> dict[str, Any]:
    positive = set(positive_ids)
    endpoints: set[str] = set()
    unique_edges: set[tuple[str, str]] = set()
    for edge in edges:
        if edge.get("final_verdict") != "FORMULAIC":
            continue
        pair = tuple(sorted((str(edge["left_id"]), str(edge["right_id"]))))
        unique_edges.add(pair)
        endpoints.update(pair)
    endpoints &= positive
    denominator = len(positive)
    return {"confirmed_edge_count": len(unique_edges),
            "formulaic_item_ids": sorted(endpoints),
            "formulaic_item_count": len(endpoints), "positive_denominator": denominator,
            "formulaic_item_rate": len(endpoints) / denominator if denominator else None}


def _pairwise_counts(judgments: Iterable[dict[str, Any]]) -> tuple[int, int, int, int, int]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in judgments:
        grouped[str(row["pair_id"])].append(str(row["verdict"]))
    pp = nn = pn = agreements = comparisons = 0
    for verdicts in grouped.values():
        for a, b in itertools.combinations(verdicts, 2):
            comparisons += 1
            agreements += int(a == b)
            if a == b == "FORMULAIC":
                pp += 1
            elif a == b == "NOT_FORMULAIC":
                nn += 1
            elif a in BINARY and b in BINARY:
                pn += 1
    return pp, nn, pn, agreements, comparisons


def agreement_metrics(judgments: Iterable[dict[str, Any]], *,
                      dataset_manifest_digest: str | None = None,
                      qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = list(judgments)
    evidence = validate_qualification_records(
        rows, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("axes", "necessary_grammar_exception_id", "verdict"),
        qualification_record_index=qualification_record_index,
        require_gold_review_provenance=False)
    submitted: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        submitted[str(row.get("pair_id", ""))].append(row)
    coverage_errors: list[str] = []
    valid_rows: list[dict[str, Any]] = []
    family_by_pair: dict[str, str] = {}
    reviewers_by_pair: dict[str, list[str]] = {}
    reviewer_independence_valid = True
    for pair_id, group in sorted(submitted.items()):
        reviewers = [str(row.get("reviewer_id", "")) for row in group]
        verdicts = [str(row.get("verdict", "")) for row in group]
        axes_valid = True
        endpoints_valid = all(
            isinstance(row.get("left_id"), str) and row.get("left_id")
            and isinstance(row.get("right_id"), str) and row.get("right_id")
            and row["left_id"] != row["right_id"]
            and canonical_pair_id(row["left_id"], row["right_id"]) == pair_id
            for row in group)
        families = {str(row.get("family_id", "")) for row in group}
        authors = {str(row.get("left_author_identity", "")) for row in group} | {
            str(row.get("right_author_identity", "")) for row in group}
        provenance = [row.get("reviewer_provenance") for row in group]
        provenance_valid = (len(provenance) == 2 and all(
            isinstance(value, dict)
            and set(value) == {"reviewer_identity", "reviewer_kind",
                               "model_revision", "prompt_digest"}
            and value.get("reviewer_identity") == reviewer
            and value.get("reviewer_kind") in {"HUMAN", "AI"}
            and ((value["reviewer_kind"] == "HUMAN"
                  and value.get("model_revision") is None
                  and value.get("prompt_digest") is None)
                 or (value["reviewer_kind"] == "AI"
                     and bool(str(value.get("model_revision", "")).strip())
                     and isinstance(value.get("prompt_digest"), str)
                     and len(value["prompt_digest"]) == 64))
            for value, reviewer in zip(provenance, reviewers)))
        independence_valid = (provenance_valid and "" not in authors
                              and not (set(reviewers) & authors))
        reviewer_independence_valid = reviewer_independence_valid and independence_valid
        for row, verdict in zip(group, verdicts):
            try:
                derived = verdict_from_axes(
                    row.get("axes", {}), row.get("necessary_grammar_exception_id"))
            except (TypeError, ValueError):
                axes_valid = False
                continue
            if verdict != derived:
                axes_valid = False
        if (not pair_id or len(group) != 2 or len(set(reviewers)) != 2
                or not all(reviewers) or not axes_valid
                or not endpoints_valid or not independence_valid or len(families) != 1
                or not families.issubset(REQUIRED_FAMILIES)
                or any(verdict not in BINARY | {"NECESSARY_GRAMMAR", "INDETERMINATE"}
                       for verdict in verdicts)):
            coverage_errors.append(pair_id or "<missing-pair-id>")
            continue
        valid_rows.extend(group)
        family_by_pair[pair_id] = next(iter(families))
        reviewers_by_pair[pair_id] = reviewers
    pp, nn, pn, agreements, comparisons = _pairwise_counts(valid_rows)
    binary_comparisons = pp + nn + pn
    raw = agreements / comparisons if comparisons else None
    positive = (2 * pp / (2 * pp + pn)) if (2 * pp + pn) else None
    negative = (2 * nn / (2 * nn + pn)) if (2 * nn + pn) else None
    positive_assignments = 2 * pp + pn
    total_binary_assignments = 2 * binary_comparisons
    prevalence = (positive_assignments / total_binary_assignments
                  if total_binary_assignments else None)
    observed = (pp + nn) / binary_comparisons if binary_comparisons else None
    expected = ((prevalence ** 2 + (1 - prevalence) ** 2)
                if prevalence is not None else None)
    kappa = ((observed - expected) / (1 - expected)
             if observed is not None and expected is not None and expected < 1 else None)
    ac1_expected = (2 * prevalence * (1 - prevalence)
                    if prevalence is not None else None)
    gwet_ac1 = ((observed - ac1_expected) / (1 - ac1_expected)
                if observed is not None and ac1_expected is not None and ac1_expected < 1
                else None)
    grouped = defaultdict(list)
    for row in valid_rows:
        grouped[str(row["pair_id"])].append(str(row["verdict"]))
    adjudication = sum(1 for values in grouped.values()
                       if "INDETERMINATE" in values or len(set(values)) > 1)
    alpha = (1 - ((pn / binary_comparisons) / (2 * prevalence * (1 - prevalence)))
             if binary_comparisons and prevalence not in (None, 0.0, 1.0) else None)
    return {"submitted_pair_count": len(submitted),
            "reviewed_pair_count": len(grouped), "pairwise_comparisons": comparisons,
            "reviewed_pair_ids": sorted(grouped),
            "first_verdicts_by_pair": {key: list(values)
                                       for key, values in sorted(grouped.items())},
            "family_by_pair": dict(sorted(family_by_pair.items())),
            "reviewers_by_pair": dict(sorted(reviewers_by_pair.items())),
            "review_coverage_valid": not coverage_errors,
            "reviewer_independence_valid": reviewer_independence_valid,
            "coverage_error_pair_ids": coverage_errors,
            "qualification_evidence": evidence,
            "raw_agreement": raw,
            "raw_agreement_ci95": wilson_interval(agreements, comparisons),
            "positive_specific_agreement": positive,
            "positive_specific_agreement_ci95": wilson_interval(2 * pp, 2 * pp + pn),
            "negative_specific_agreement": negative,
            "negative_specific_agreement_ci95": wilson_interval(2 * nn, 2 * nn + pn),
            "cohen_kappa_pairwise": kappa,
            "gwet_ac1_pairwise": gwet_ac1,
            "krippendorff_alpha_nominal": alpha,
            "adjudication_rate": adjudication / len(grouped) if grouped else None,
            "interpretable": bool(binary_comparisons and prevalence not in (0.0, 1.0))}


def candidate_retrieval_metrics(candidate_pair_ids: Iterable[str],
                                confirmed_pair_ids: Iterable[str]) -> dict[str, Any]:
    candidates, confirmed = set(candidate_pair_ids), set(confirmed_pair_ids)
    true = candidates & confirmed
    return {"candidate_count": len(candidates), "confirmed_count": len(confirmed),
            "true_candidate_count": len(true),
            "precision": len(true) / len(candidates) if candidates else None,
            "recall": len(true) / len(confirmed) if confirmed else None}


def qualify_formulaic_construct(judgments: Iterable[dict[str, Any]], *,
                                adjudications: Iterable[dict[str, Any]] | None = None,
                                candidate_audit_records: Iterable[dict[str, Any]] | None = None,
                                candidate_audit_manifest: dict[str, Any] | None = None,
                                rubric_manifest: dict[str, Any] | None = None,
                                necessary_grammar_exceptions: Iterable[dict[str, Any]] | None = None,
                                dataset_manifest_digest: str | None = None,
                                qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    """套路构念资格门。

    样本构成、候选召回和量规冻结是独立前提，不能靠一个漂亮的 κ 值替代。
    二元判定使用 Cohen κ；等级加权 κ 属于内容等级审核，不混入本门。
    """
    judgment_rows = list(judgments)
    metrics = agreement_metrics(
        judgment_rows, dataset_manifest_digest=dataset_manifest_digest,
        qualification_record_index=qualification_record_index)
    adjudicated = list(adjudications or [])
    adjudication_evidence = validate_qualification_records(
        adjudicated, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("final_verdict", "necessary_grammar_exception_id"),
        qualification_record_index=qualification_record_index)
    adjudication_by_pair: dict[str, dict[str, Any]] = {}
    duplicate_adjudications: list[str] = []
    invalid_adjudications: list[str] = []
    exception_rows = list(necessary_grammar_exceptions or [])
    exception_by_id: dict[str, dict[str, Any]] = {}
    exception_errors: list[str] = []
    for row in exception_rows:
        exception_id = str(row.get("exception_id", ""))
        unsigned = dict(row)
        supplied = unsigned.pop("exception_digest", None)
        valid = (bool(exception_id)
                 and set(row) == {"exception_id", "registered_before_batch",
                                  "batch_id", "approved_by", "product_definition_ref",
                                  "applicable_pair_ids_digest", "maximum_pair_count",
                                  "registry_manifest_digest", "exception_digest"}
                 and row.get("registered_before_batch") is True
                 and bool(str(row.get("batch_id", "")).strip())
                 and bool(str(row.get("approved_by", "")).strip())
                 and bool(str(row.get("product_definition_ref", "")).strip())
                 and isinstance(row.get("maximum_pair_count"), int)
                 and row["maximum_pair_count"] > 0
                 and isinstance(row.get("applicable_pair_ids_digest"), str)
                 and len(row["applicable_pair_ids_digest"]) == 64
                 and isinstance(row.get("registry_manifest_digest"), str)
                 and len(row["registry_manifest_digest"]) == 64
                 and supplied == digest_json(unsigned))
        if not valid or exception_id in exception_by_id:
            exception_errors.append(exception_id or "<missing-exception-id>")
        else:
            exception_by_id[exception_id] = row
    first_verdicts = metrics.get("first_verdicts_by_pair", {})
    family_by_pair = metrics.get("family_by_pair", {})
    reviewers_by_pair = metrics.get("reviewers_by_pair", {})
    for row in adjudicated:
        pair_id = str(row.get("pair_id", ""))
        verdict = row.get("final_verdict")
        initial = first_verdicts.get(pair_id, []) if isinstance(first_verdicts, dict) else []
        requires_adjudicator = (len(initial) != 2 or len(set(initial)) != 1
                                or "INDETERMINATE" in initial)
        exception_id = row.get("necessary_grammar_exception_id")
        endpoints_valid = (
            isinstance(row.get("left_id"), str) and isinstance(row.get("right_id"), str)
            and row.get("left_id") != row.get("right_id")
            and canonical_pair_id(row["left_id"], row["right_id"]) == pair_id)
        family_valid = (row.get("family_id") in REQUIRED_FAMILIES
                        and row.get("family_id") == family_by_pair.get(pair_id))
        final_matches_first = (not requires_adjudicator and initial
                               and verdict == initial[0])
        adjudicator_valid = (not requires_adjudicator or (
            bool(str(row.get("adjudicator_identity", "")).strip())
            and row.get("adjudicator_identity") not in reviewers_by_pair.get(pair_id, [])
            and isinstance(row.get("adjudication_evidence_digest"), str)
            and len(row["adjudication_evidence_digest"]) == 64
            and verdict != "INDETERMINATE"))
        exception_valid = (verdict != "NECESSARY_GRAMMAR"
                           or exception_id in exception_by_id)
        if (not pair_id
                or not endpoints_valid or not family_valid
                or verdict not in {"FORMULAIC", "NOT_FORMULAIC", "NECESSARY_GRAMMAR"}
                or (not requires_adjudicator and not final_matches_first)
                or not adjudicator_valid or not exception_valid):
            invalid_adjudications.append(pair_id or "<missing-pair-id>")
            continue
        if pair_id in adjudication_by_pair:
            duplicate_adjudications.append(pair_id)
            continue
        adjudication_by_pair[pair_id] = row
    positive_ids = {pair_id for pair_id, row in adjudication_by_pair.items()
                    if row["final_verdict"] == "FORMULAIC"}
    grammar_ids = {pair_id for pair_id, row in adjudication_by_pair.items()
                   if row["final_verdict"] == "NECESSARY_GRAMMAR"}
    for exception_id, exception in exception_by_id.items():
        used_ids = sorted(pair_id for pair_id in grammar_ids
                          if adjudication_by_pair[pair_id].get(
                              "necessary_grammar_exception_id") == exception_id)
        if (not used_ids
                or len(used_ids) > exception["maximum_pair_count"]
                or exception["applicable_pair_ids_digest"] != digest_json(used_ids)):
            exception_errors.append(exception_id)
    negative_ids = set(adjudication_by_pair) - positive_ids
    counts = {"formulaic_pairs": len(positive_ids),
              "non_formulaic_pairs": len(negative_ids),
              "necessary_grammar_pairs": len(grammar_ids)}
    candidate_audit = list(candidate_audit_records or [])
    candidate_evidence = validate_qualification_records(
        candidate_audit, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("gold_formulaic",),
        qualification_record_index=qualification_record_index)
    candidate_ids = [str(row.get("pair_id", "")) for row in candidate_audit
                     if row.get("candidate_selected") is True]
    candidate_confirmed = [str(row.get("pair_id", "")) for row in candidate_audit
                           if row.get("gold_formulaic") is True]
    candidate_shape_valid = all(
        bool(str(row.get("pair_id", "")).strip())
        and isinstance(row.get("left_id"), str)
        and isinstance(row.get("right_id"), str)
        and row.get("left_id") != row.get("right_id")
        and canonical_pair_id(row["left_id"], row["right_id"]) == row.get("pair_id")
        and row.get("family_id") == family_by_pair.get(str(row.get("pair_id")))
        and isinstance(row.get("candidate_selected"), bool)
        and isinstance(row.get("gold_formulaic"), bool)
        and row.get("audit_scope") == "RANDOM_RECALL_AUDIT"
        for row in candidate_audit)
    candidate_pair_ids = [str(row.get("pair_id", "")) for row in candidate_audit]
    candidate_pair_set = set(candidate_pair_ids)
    reviewed_count = metrics.get("reviewed_pair_count", 0)
    reviewed_ids = set(map(str, metrics.get("reviewed_pair_ids", [])))
    candidate_pairs_bound = (len(candidate_pair_ids) == len(candidate_pair_set)
                             and candidate_pair_set.issubset(reviewed_ids))
    candidate_gold_matches = candidate_pairs_bound and all(
        row.get("gold_formulaic") is (
            adjudication_by_pair[str(row.get("pair_id"))]["final_verdict"] == "FORMULAIC")
        for row in candidate_audit
        if str(row.get("pair_id")) in adjudication_by_pair)
    candidate_manifest = candidate_audit_manifest or {}
    unsigned_candidate_manifest = dict(candidate_manifest)
    supplied_candidate_manifest_digest = unsigned_candidate_manifest.pop(
        "manifest_digest", None)
    candidate_manifest_valid = (
        set(candidate_manifest) == {
            "schema_version", "status", "registered_before_miner_run",
            "batch_id", "miner_run_id", "custodian_identity",
            "registry_manifest_digest", "sampling_algorithm",
            "population_pair_ids_digest",
            "sampled_pair_ids_digest", "sample_count",
            "randomization_seed_commitment", "candidate_miner_blinded_to_gold",
            "gold_attached_after_candidate_run", "manifest_digest"}
        and candidate_manifest.get("schema_version")
        == "eval-spine-formulaic-candidate-audit-manifest-v1"
        and candidate_manifest.get("status") == "SEALED"
        and candidate_manifest.get("registered_before_miner_run") is True
        and bool(str(candidate_manifest.get("batch_id", "")).strip())
        and bool(str(candidate_manifest.get("miner_run_id", "")).strip())
        and bool(str(candidate_manifest.get("custodian_identity", "")).strip())
        and isinstance(candidate_manifest.get("registry_manifest_digest"), str)
        and len(candidate_manifest["registry_manifest_digest"]) == 64
        and candidate_manifest.get("sampling_algorithm")
        == "PREREGISTERED_STRATIFIED_RANDOM_SAMPLE_V1"
        and candidate_manifest.get("population_pair_ids_digest")
        == digest_json(sorted(reviewed_ids))
        and candidate_manifest.get("sampled_pair_ids_digest")
        == digest_json(sorted(candidate_pair_set))
        and candidate_manifest.get("sample_count") == len(candidate_pair_ids)
        and isinstance(candidate_manifest.get("randomization_seed_commitment"), str)
        and len(candidate_manifest["randomization_seed_commitment"]) == 64
        and candidate_manifest.get("candidate_miner_blinded_to_gold") is True
        and candidate_manifest.get("gold_attached_after_candidate_run") is True
        and supplied_candidate_manifest_digest == digest_json(unsigned_candidate_manifest)
    )
    retrieval = candidate_retrieval_metrics(candidate_ids, candidate_confirmed)
    family = {
        "judgments": family_coverage(judgment_rows, 120),
        "adjudications": family_coverage(adjudicated, 60),
        "candidate_audit": family_coverage(candidate_audit, 20),
    }
    positive_count = len(positive_ids)
    negative_count = len(negative_ids)
    grammar_count = len(grammar_ids)
    class_counts_valid = all(isinstance(value, int) and not isinstance(value, bool)
                             and value >= 0
                             for value in (positive_count, negative_count, grammar_count))
    rubric = rubric_manifest or {}
    unsigned_rubric = dict(rubric)
    supplied_rubric_digest = unsigned_rubric.pop("rubric_digest", None)
    rubric_valid = (
        set(rubric) == {"schema_version", "status", "frozen_before_qualification",
                        "rubric_version", "batch_id", "rubric_content_digest",
                        "registry_manifest_digest", "custodian_identity", "frozen_at",
                        "rubric_digest"}
        and
        rubric.get("schema_version") == "eval-spine-formulaic-rubric-freeze-v1"
        and rubric.get("status") == "FROZEN"
        and rubric.get("frozen_before_qualification") is True
        and isinstance(rubric.get("rubric_version"), str)
        and bool(rubric.get("rubric_version"))
        and bool(str(rubric.get("batch_id", "")).strip())
        and bool(str(rubric.get("custodian_identity", "")).strip())
        and bool(str(rubric.get("frozen_at", "")).strip())
        and isinstance(rubric.get("rubric_content_digest"), str)
        and len(rubric["rubric_content_digest"]) == 64
        and isinstance(rubric.get("registry_manifest_digest"), str)
        and len(rubric["registry_manifest_digest"]) == 64
        and supplied_rubric_digest == digest_json(unsigned_rubric)
    )
    registry_cross_binding = (
        candidate_manifest.get("batch_id") == rubric.get("batch_id")
        and candidate_manifest.get("registry_manifest_digest")
        == rubric.get("registry_manifest_digest")
        and all(row.get("batch_id") == rubric.get("batch_id")
                and row.get("registry_manifest_digest")
                == rubric.get("registry_manifest_digest") for row in exception_rows))
    gates = {
        "rubric_frozen_before_qualification": rubric_valid,
        "judgment_qualification_evidence_bound":
            metrics.get("qualification_evidence", {}).get("passed") is True,
        "adjudication_qualification_evidence_bound": adjudication_evidence["passed"],
        "candidate_audit_qualification_evidence_bound": candidate_evidence["passed"],
        "candidate_audit_shape_valid": candidate_shape_valid,
        "candidate_audit_manifest_valid": candidate_manifest_valid,
        "candidate_audit_pairs_bound": candidate_pairs_bound,
        "candidate_gold_matches_adjudication": candidate_gold_matches,
        "family_coverage": all(value["passed"] for value in family.values()),
        "review_coverage_valid": metrics.get("review_coverage_valid") is True,
        "reviewer_independence_valid":
            metrics.get("reviewer_independence_valid") is True,
        "registry_cross_binding": registry_cross_binding,
        "fresh_pair_count": reviewed_count >= 300,
        "adjudication_records_valid": not invalid_adjudications
                                      and not duplicate_adjudications
                                      and not exception_errors,
        "adjudication_covers_reviewed_pairs":
            set(adjudication_by_pair) == reviewed_ids and len(reviewed_ids) == reviewed_count,
        "class_counts_valid": class_counts_valid,
        "class_counts_close_reviewed_denominator":
            class_counts_valid and positive_count + negative_count == reviewed_count,
        "necessary_grammar_is_negative_subset":
            class_counts_valid and grammar_count <= negative_count,
        "positive_pair_count": positive_count >= 100,
        "negative_pair_count": negative_count >= 100,
        "necessary_grammar_pair_count":
            grammar_count >= 20,
        "candidate_miner_confirmed_sample":
            retrieval.get("confirmed_count", 0) >= 100,
        "candidate_miner_recall": retrieval.get("recall") is not None
                                  and retrieval["recall"] >= .95,
        "interpretable": metrics.get("interpretable") is True,
        "raw_agreement": metrics.get("raw_agreement") is not None
                         and metrics["raw_agreement"] >= .90,
        "kappa": metrics.get("cohen_kappa_pairwise") is not None
                 and metrics["cohen_kappa_pairwise"] >= .60,
        "positive_agreement": metrics.get("positive_specific_agreement") is not None
                              and metrics["positive_specific_agreement"] >= .80,
        "negative_agreement": metrics.get("negative_specific_agreement") is not None
                              and metrics["negative_specific_agreement"] >= .80,
        "adjudication_rate": metrics.get("adjudication_rate") is not None
                             and metrics["adjudication_rate"] <= .20,
    }
    return {"qualified": all(gates.values()), "gates": gates,
            "class_counts": counts, "candidate_retrieval": retrieval,
            "invalid_adjudication_pair_ids": sorted(invalid_adjudications),
            "duplicate_adjudication_pair_ids": sorted(duplicate_adjudications),
            "necessary_grammar_exception_errors": sorted(exception_errors),
            "family_coverage": family,
            "rubric_manifest_digest": supplied_rubric_digest,
            "candidate_audit_manifest_digest": supplied_candidate_manifest_digest}
