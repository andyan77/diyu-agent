"""事实链校准、混淆矩阵与二项分布单侧上界。"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable

from .canonical import digest_json
from .qualification_data import validate_qualification_records

RISK_LEVELS = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
REQUIRED_FAMILIES = {
    "F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
    "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
    "F5_ENTERPRISE_LONG_TERM_TRUST",
}


def family_coverage(records: Iterable[dict[str, Any]], minimum_per_family: int) -> dict[str, Any]:
    counts = Counter(str(row.get("family_id", "")) for row in records
                     if isinstance(row, dict))
    return {
        "passed": set(counts) == REQUIRED_FAMILIES
                  and all(counts[family] >= minimum_per_family
                          for family in REQUIRED_FAMILIES),
        "counts": {key: counts[key] for key in sorted(counts)},
        "required_families": sorted(REQUIRED_FAMILIES),
        "minimum_per_family": minimum_per_family,
    }


def detection_metrics(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    tp = sum(1 for r in rows if r.get("gold_present") is True
             and r.get("predicted_present") is True)
    fp = sum(1 for r in rows if r.get("gold_present") is False
             and r.get("predicted_present") is True)
    fn = sum(1 for r in rows if r.get("gold_present") is True
             and r.get("predicted_present") is False)
    tn = len(rows) - tp - fp - fn
    critical_fn = sum(1 for r in rows if r.get("gold_present") is True
                      and r.get("predicted_present") is False
                      and r.get("gold_risk") in {"HIGH", "CRITICAL"})
    return {"count": len(rows), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "recall": tp / (tp + fn) if tp + fn else None,
            "precision": tp / (tp + fp) if tp + fp else None,
            "critical_false_negatives": critical_fn,
            "false_negative_upper_95": one_sided_binomial_upper(fn, tp + fn),
            "false_positive_upper_95": one_sided_binomial_upper(fp, fp + tn)}


def qualify_detection(records: Iterable[dict[str, Any]], *,
                      dataset_manifest_digest: str | None = None,
                      qualification_record_index: dict[str, Any] | None = None,
                      gold_field_names: tuple[str, ...] = (
                          "gold_present", "gold_risk")) -> dict[str, Any]:
    rows = list(records)
    metrics = detection_metrics(rows)
    evidence = validate_qualification_records(
        rows, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=gold_field_names,
        qualification_record_index=qualification_record_index)
    shape_valid = all(
        isinstance(row.get("gold_present"), bool)
        and isinstance(row.get("predicted_present"), bool)
        and row.get("gold_risk") in RISK_LEVELS
        and row.get("predicted_risk") in RISK_LEVELS
        and bool(str(row.get("field_type", "")).strip())
        and bool(str(row.get("family_id", "")).strip())
        for row in rows)
    positive_count = sum(row.get("gold_present") is True for row in rows)
    negative_count = sum(row.get("gold_present") is False for row in rows)
    family = family_coverage(rows, 20)
    gates = {"qualification_evidence_bound": evidence["passed"],
             "record_shape_valid": shape_valid,
             "sample_count": len(rows) >= 300,
             "positive_sample_count": positive_count >= 100,
             "negative_control_count": negative_count >= 100,
             "family_coverage": family["passed"],
             "recall": metrics["recall"] is not None and metrics["recall"] >= .95,
             "precision": metrics["precision"] is not None
                          and metrics["precision"] >= .90,
             "critical_omissions_zero": metrics["critical_false_negatives"] == 0}
    by_field: dict[str, list[dict[str, Any]]] = {}
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_field.setdefault(str(row.get("field_type", "UNSPECIFIED")), []).append(row)
        by_family.setdefault(str(row.get("family_id", "UNSPECIFIED")), []).append(row)
    return {"qualified": all(gates.values()), "gates": gates, "metrics": metrics,
            "positive_case_count": positive_count,
            "negative_control_count": negative_count,
            "qualification_evidence": evidence,
            "family_coverage": family,
            "by_field": {key: detection_metrics(by_field[key]) for key in sorted(by_field)},
            "by_family": {key: detection_metrics(by_family[key]) for key in sorted(by_family)}}


def qualify_reference_extraction(
        records: Iterable[dict[str, Any]], *,
        dataset_manifest_digest: str | None = None,
        qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    """参考断言抽取门；存在性和语义属性不能互相代替。"""
    rows = list(records)
    detection = qualify_detection(
        rows, dataset_manifest_digest=dataset_manifest_digest,
        qualification_record_index=qualification_record_index,
        gold_field_names=("gold_attributes", "gold_present", "gold_risk"))
    matched = [row for row in rows
               if row.get("gold_present") is True and row.get("predicted_present") is True]
    attributes = ("polarity", "modality", "time_scope", "preconditions")
    accuracies = {
        field: (sum(row.get("gold_attributes", {}).get(field)
                    == row.get("predicted_attributes", {}).get(field)
                    for row in matched) / len(matched)
                if matched else None)
        for field in attributes
    }
    complete = bool(matched) and all(
        isinstance(row.get("gold_attributes"), dict)
        and isinstance(row.get("predicted_attributes"), dict)
        and set(row["gold_attributes"]) == set(attributes)
        and set(row["predicted_attributes"]) == set(attributes)
        for row in matched)
    semantic_gates = {
        "attribute_annotations_complete": complete,
        **{f"{field}_correct_accuracy": value is not None and value >= .95
           for field, value in accuracies.items()},
    }
    gates = {f"detection_{key}": value for key, value in detection["gates"].items()}
    gates.update(semantic_gates)
    return {
        "qualified": all(gates.values()),
        "gates": gates,
        "detection": detection,
        "attribute_accuracies": accuracies,
        "matched_assertion_count": len(matched),
    }


def qualify_claim_atomization(
        records: Iterable[dict[str, Any]], *,
        dataset_manifest_digest: str | None = None,
        qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    """主张原子化门；漏拆、误抽和错误合并分别计量。"""
    rows = list(records)
    detection = qualify_detection(
        rows, dataset_manifest_digest=dataset_manifest_digest,
        qualification_record_index=qualification_record_index,
        gold_field_names=("gold_atom_partition", "gold_present", "gold_risk"))
    predicted = [row for row in rows if row.get("predicted_present") is True]
    def valid_partition(value: Any) -> bool:
        return (isinstance(value, list) and value
                and all(isinstance(group, list) and group
                        and all(isinstance(item, str) and item for item in group)
                        for group in value))

    partition_complete = bool(predicted) and all(
        valid_partition(row.get("gold_atom_partition"))
        and valid_partition(row.get("predicted_atom_partition")) for row in predicted)

    def derived_flags(row: dict[str, Any]) -> tuple[bool, bool]:
        gold = row["gold_atom_partition"]
        predicted_partition = row["predicted_atom_partition"]
        gold_group_by_item = {item: group_index for group_index, group in enumerate(gold)
                              for item in group}
        incorrect_merge = any(
            len({gold_group_by_item.get(item) for item in group}) > 1
            for group in predicted_partition)
        flat_predicted = [item for group in predicted_partition for item in group]
        cross_surface_duplicate = len(flat_predicted) != len(set(flat_predicted))
        return incorrect_merge, cross_surface_duplicate

    flags = [derived_flags(row) for row in predicted
             if valid_partition(row.get("gold_atom_partition"))
             and valid_partition(row.get("predicted_atom_partition"))]
    merge_count = sum(merge for merge, _ in flags)
    duplicate_count = sum(duplicate for _, duplicate in flags)
    merge_rate = merge_count / len(predicted) if predicted else None
    duplicate_rate = duplicate_count / len(predicted) if predicted else None
    semantic_gates = {
        "merge_annotations_complete": partition_complete,
        "cross_surface_duplicate_annotations_complete": partition_complete,
        "incorrect_merge_rate": merge_rate is not None
                                and merge_rate <= .05,
    }
    gates = {f"detection_{key}": value for key, value in detection["gates"].items()}
    gates.update(semantic_gates)
    return {
        "qualified": all(gates.values()),
        "gates": gates,
        "detection": detection,
        "predicted_atom_count": len(predicted),
        "incorrect_merge_count": merge_count,
        "incorrect_merge_rate": merge_rate,
        "cross_surface_duplicate_count": duplicate_count,
        "cross_surface_duplicate_rate": duplicate_rate,
    }


def _binomial_cdf(k: int, n: int, p: float) -> float:
    if k >= n:
        return 1.0
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0
    # n<=数千的资格集足够；逐项用 lgamma 避免组合数溢出。
    total = 0.0
    for i in range(k + 1):
        log_term = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                    + i * math.log(p) + (n - i) * math.log1p(-p))
        total += math.exp(log_term)
    return min(1.0, total)


def one_sided_binomial_upper(events: int, trials: int, confidence: float = .95) -> float | None:
    """Clopper-Pearson 单侧上界；零事件时等于 1-(1-confidence)^(1/n)。"""
    if trials <= 0 or not 0 <= events <= trials:
        return None
    if events == trials:
        return 1.0
    alpha = 1 - confidence
    lo, hi = events / trials, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _binomial_cdf(events, trials, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def confusion_metrics(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    matrix: Counter[tuple[str, str]] = Counter()
    for row in rows:
        matrix[(str(row["gold_label"]), str(row["predicted_label"]))] += 1
    tp = matrix[("CONTRADICTED", "CONTRADICTED")]
    gold_contra = sum(value for (gold, _), value in matrix.items() if gold == "CONTRADICTED")
    pred_contra = sum(value for (_, pred), value in matrix.items() if pred == "CONTRADICTED")
    return {"count": len(rows),
            "matrix": {f"{gold}->{pred}": value
                       for (gold, pred), value in sorted(matrix.items())},
            "contradicted_recall": tp / gold_contra if gold_contra else None,
            "contradicted_precision": tp / pred_contra if pred_contra else None}


def per_label_metrics(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows = list(records)
    result: dict[str, dict[str, Any]] = {}
    for label in ("SUPPORTED", "CONTRADICTED", "UNKNOWN"):
        tp = sum(row.get("gold_label") == label and row.get("predicted_label") == label
                 for row in rows)
        gold_count = sum(row.get("gold_label") == label for row in rows)
        predicted_count = sum(row.get("predicted_label") == label for row in rows)
        fn = gold_count - tp
        fp = predicted_count - tp
        result[label] = {
            "gold_count": gold_count, "predicted_count": predicted_count,
            "true_positive": tp,
            "recall": tp / gold_count if gold_count else None,
            "precision": tp / predicted_count if predicted_count else None,
            "false_negative_upper_95": one_sided_binomial_upper(fn, gold_count),
            "false_positive_upper_95": one_sided_binomial_upper(
                fp, len(rows) - gold_count),
        }
    return result


def _known_regression_metrics(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    required = {"case_id", "fixture_digest", "output_digest",
                "expected_finding_codes", "observed_finding_codes",
                "registered_manifest_digest"}
    valid = True
    ids: list[str] = []
    fixture_digests: list[str] = []
    manifest_digests: set[str] = set()
    detected = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            valid = False
            continue
        ids.append(str(row.get("case_id", "")))
        fixture_digests.append(str(row.get("fixture_digest", "")))
        manifest_digests.add(str(row.get("registered_manifest_digest", "")))
        expected = row.get("expected_finding_codes")
        observed = row.get("observed_finding_codes")
        shape = (bool(ids[-1])
                 and all(isinstance(row.get(field), str) and len(row[field]) == 64
                         for field in ("fixture_digest", "output_digest",
                                       "registered_manifest_digest"))
                 and isinstance(expected, list) and bool(expected)
                 and isinstance(observed, list)
                 and all(isinstance(value, str) and value for value in expected + observed))
        valid = valid and shape
        detected += int(shape and set(expected).issubset(observed))
    unique = (len(ids) == len(set(ids)) and len(fixture_digests) == len(set(fixture_digests)))
    bound = len(manifest_digests) == 1 and all(
        len(value) == 64 for value in manifest_digests)
    return {"case_count": len(rows), "detected_count": detected,
            "recall": detected / len(rows) if rows else None,
            "shape_valid": valid, "unique_cases": unique,
            "single_registered_manifest_bound": bound,
            "registered_manifest_digest": next(iter(manifest_digests), None)}


def stratified_confusion(records: Iterable[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        groups.setdefault(str(row.get(field, "UNSPECIFIED")), []).append(row)
    return {key: confusion_metrics(groups[key]) for key in sorted(groups)}


def qualify_entailment(records: Iterable[dict[str, Any]], *,
                       known_risk_results: Iterable[dict[str, Any]] | None = None,
                       dataset_manifest_digest: str | None = None,
                       qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = list(records)
    evidence = validate_qualification_records(
        rows, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("gold_label", "gold_risk"),
        qualification_record_index=qualification_record_index)
    valid_rows = [row for row in rows
                  if row.get("gold_label") in {"SUPPORTED", "CONTRADICTED", "UNKNOWN"}
                  and row.get("predicted_label") in {"SUPPORTED", "CONTRADICTED", "UNKNOWN"}
                  and row.get("gold_risk") in RISK_LEVELS
                  and row.get("predicted_risk") in RISK_LEVELS
                  and isinstance(row.get("abstain"), bool)
                  and row.get("action") in {"ALLOW", "HUMAN_REVIEW", "HARD_VETO"}
                  and row.get("case_origin") in {"NATURAL", "CHALLENGE"}
                  and bool(str(row.get("family_id", "")).strip())]
    confusion = confusion_metrics(valid_rows)
    labels = per_label_metrics(valid_rows)
    family = family_coverage(valid_rows, 20)
    high_risk_contradicted = [
        row for row in valid_rows if row["gold_label"] == "CONTRADICTED"
        and row.get("gold_risk") in {"HIGH", "CRITICAL"}
    ]
    high_risk_unknown = [
        row for row in valid_rows if row["gold_label"] == "UNKNOWN"
        and row.get("gold_risk") in {"HIGH", "CRITICAL"}
    ]
    dangerous = [r for r in valid_rows if r["gold_label"] in {"CONTRADICTED", "UNKNOWN"}
                 and r.get("gold_risk") in {"HIGH", "CRITICAL"}]
    auto_pass_fn = sum(1 for r in dangerous if r.get("action") == "ALLOW")
    legal = [r for r in valid_rows if r.get("case_origin") == "NATURAL"
             and r["gold_label"] == "SUPPORTED"]
    false_hard = sum(1 for r in legal if r.get("action") == "HARD_VETO")
    danger_upper = one_sided_binomial_upper(auto_pass_fn, len(dangerous))
    legal_upper = one_sided_binomial_upper(false_hard, len(legal))
    unknown_auto_allow = sum(1 for r in valid_rows if r["gold_label"] == "UNKNOWN"
                             and r.get("action") == "ALLOW")
    joint_risk_action_failures = sum(
        RISK_LEVELS[row["predicted_risk"]] < RISK_LEVELS[row["gold_risk"]]
        and row.get("action") == "ALLOW" for row in dangerous)
    known = list(known_risk_results or [])
    known_metrics = _known_regression_metrics(known)
    gates = {
        "qualification_evidence_bound": evidence["passed"],
        "record_shape_valid": len(valid_rows) == len(rows),
        "family_coverage": family["passed"],
        "contradicted_recall": confusion["contradicted_recall"] is not None
                               and confusion["contradicted_recall"] >= .95,
        "contradicted_precision": confusion["contradicted_precision"] is not None
                                  and confusion["contradicted_precision"] >= .85,
        "supported_recall": labels["SUPPORTED"]["recall"] is not None
                            and labels["SUPPORTED"]["recall"] >= .90,
        "supported_precision": labels["SUPPORTED"]["precision"] is not None
                               and labels["SUPPORTED"]["precision"] >= .90,
        "unknown_recall": labels["UNKNOWN"]["recall"] is not None
                          and labels["UNKNOWN"]["recall"] >= .90,
        "unknown_precision": labels["UNKNOWN"]["precision"] is not None
                             and labels["UNKNOWN"]["precision"] >= .90,
        "abstention_annotations_complete": all(
            isinstance(row.get("abstain"), bool) for row in rows),
        "high_risk_contradicted_sample":
            len(high_risk_contradicted) >= 300,
        "high_risk_unknown_sample": len(high_risk_unknown) >= 100,
        "high_risk_auto_pass_fn_zero": auto_pass_fn == 0,
        "high_risk_upper_below_one_percent": danger_upper is not None and danger_upper < .01,
        "natural_legal_sample": len(legal) >= 300,
        "natural_false_hard_upper_at_most_five_percent": legal_upper is not None
                                                          and legal_upper <= .05,
        "unknown_never_auto_allow": unknown_auto_allow == 0,
        "known_risk_regression_sample": len(known) >= 5,
        "known_risk_regression_shape_valid": known_metrics["shape_valid"],
        "known_risk_regression_unique": known_metrics["unique_cases"],
        "known_risk_regression_manifest_bound":
            known_metrics["single_registered_manifest_bound"],
        "known_risk_regression_recall_one": known_metrics["recall"] == 1.0,
        "joint_risk_downclass_and_unsafe_allow_zero": joint_risk_action_failures == 0,
    }
    return {"qualified": all(gates.values()), "gates": gates, "confusion": confusion,
            "per_label_metrics": labels,
            "abstention_rate": (sum(row.get("abstain") is True for row in valid_rows)
                                / len(valid_rows) if valid_rows else None),
            "confusion_by_risk": stratified_confusion(valid_rows, "gold_risk"),
            "confusion_by_family": stratified_confusion(valid_rows, "family_id"),
            "family_coverage": family,
            "high_risk_contradicted_count": len(high_risk_contradicted),
            "high_risk_unknown_count": len(high_risk_unknown),
            "high_risk_dangerous_count": len(dangerous),
            "auto_pass_false_negatives": auto_pass_fn,
            "high_risk_fn_upper_95": danger_upper, "natural_supported_count": len(legal),
            "false_hard_blocks": false_hard, "false_hard_upper_95": legal_upper,
            "unknown_auto_allow_count": unknown_auto_allow,
            "joint_risk_downclass_and_unsafe_allow_count": joint_risk_action_failures,
            "known_risk": known_metrics,
            "qualification_evidence": evidence}


def qualify_risk_classification(records: Iterable[dict[str, Any]], *,
                                dataset_manifest_digest: str | None = None,
                                qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    """风险等级本身也需资格化；HIGH/CRITICAL 下调漏判为零。"""
    rows = list(records)
    evidence = validate_qualification_records(
        rows, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("gold_risk",),
        qualification_record_index=qualification_record_index)
    valid = [row for row in rows if row.get("gold_risk") in RISK_LEVELS
             and row.get("predicted_risk") in RISK_LEVELS
             and row.get("case_origin") in {"NATURAL", "CHALLENGE"}
             and bool(str(row.get("family_id", "")).strip())]
    high = [row for row in valid if row["gold_risk"] in {"HIGH", "CRITICAL"}]
    controls = [row for row in valid if row.get("case_origin") == "NATURAL"
                and row["gold_risk"] in {"LOW", "MEDIUM"}]
    downclassified = sum(RISK_LEVELS[row["predicted_risk"]]
                         < RISK_LEVELS[row["gold_risk"]]
                         for row in high)
    false_high = sum(row["predicted_risk"] in {"HIGH", "CRITICAL"}
                     for row in controls)
    accuracy = (sum(row["predicted_risk"] == row["gold_risk"] for row in valid)
                / len(valid) if valid else None)
    down_upper = one_sided_binomial_upper(downclassified, len(high))
    false_high_upper = one_sided_binomial_upper(false_high, len(controls))
    matrix = Counter((row["gold_risk"], row["predicted_risk"]) for row in valid)
    family = family_coverage(valid, 40)
    gates = {
        "qualification_evidence_bound": evidence["passed"],
        "record_shape_valid": len(valid) == len(rows),
        "family_coverage": family["passed"],
        "high_risk_sample": len(high) >= 300,
        "legal_control_sample": len(controls) >= 300,
        "high_risk_downclassification_zero": downclassified == 0,
        "high_risk_downclassification_upper_below_one_percent":
            down_upper is not None and down_upper < .01,
        "overall_accuracy": accuracy is not None and accuracy >= .95,
        "legal_false_high_upper_at_most_five_percent":
            false_high_upper is not None and false_high_upper <= .05,
    }
    return {
        "qualified": all(gates.values()), "gates": gates,
        "high_risk_count": len(high), "legal_control_count": len(controls),
        "downclassified_high_risk_count": downclassified,
        "downclassified_high_risk_upper_95": down_upper,
        "legal_false_high_count": false_high,
        "legal_false_high_upper_95": false_high_upper,
        "accuracy": accuracy,
        "family_coverage": family,
        "confusion": {f"{gold}->{pred}": count
                      for (gold, pred), count in sorted(matrix.items())},
        "confusion_by_family": {
            family: {f"{gold}->{pred}": count for (gold, pred), count in sorted(
                Counter((row["gold_risk"], row["predicted_risk"])
                        for row in valid if row["family_id"] == family).items())}
            for family in sorted({row["family_id"] for row in valid})},
        "qualification_evidence": evidence,
    }


def _action_strata(records: Iterable[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        groups.setdefault(str(row.get(field, "UNSPECIFIED")), []).append(row)
    return {
        key: {
            "count": len(group),
            "allow_count": sum(row.get("final_action") == "ALLOW" for row in group),
            "review_count": sum(row.get("final_action") == "HUMAN_REVIEW" for row in group),
            "hard_veto_count": sum(row.get("final_action") == "HARD_VETO" for row in group),
        }
        for key, group in sorted(groups.items())
    }


CHAIN_ROLES = ("source_evidence", "reference_assertion", "claim_atom",
               "risk_classification", "entailment", "final_action")


def verify_chain_manifest(manifest: Any) -> bool:
    if not isinstance(manifest, dict) or set(manifest) != {
            "schema_version", "object_digests", "links", "chain_digest"}:
        return False
    objects = manifest.get("object_digests")
    links = manifest.get("links")
    if (manifest.get("schema_version") != "eval-spine-e2e-chain-manifest-v1"
            or not isinstance(objects, dict) or set(objects) != set(CHAIN_ROLES)
            or not all(isinstance(value, str) and len(value) == 64
                       for value in objects.values())
            or not isinstance(links, list) or len(links) != len(CHAIN_ROLES) - 1):
        return False
    expected_links = [
        {"from_role": left, "to_role": right,
         "from_digest": objects[left], "to_digest": objects[right]}
        for left, right in zip(CHAIN_ROLES, CHAIN_ROLES[1:])]
    if links != expected_links:
        return False
    unsigned = dict(manifest)
    supplied = unsigned.pop("chain_digest", None)
    return supplied == digest_json(unsigned)


def qualify_end_to_end(records: Iterable[dict[str, Any]], *,
                       dataset_manifest_digest: str | None = None,
                       qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    """从源材料到最终动作的联合门，不能由各模块分别通过来替代。"""
    rows = list(records)
    evidence = validate_qualification_records(
        rows, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("gold_risk", "gold_safe_to_clear"),
        qualification_record_index=qualification_record_index)
    shape_valid = all(
        row.get("gold_risk") in RISK_LEVELS
        and row.get("predicted_risk") in RISK_LEVELS
        and row.get("case_origin") in {"NATURAL", "CHALLENGE"}
        and isinstance(row.get("gold_safe_to_clear"), bool)
        and row.get("final_action") in {"ALLOW", "HUMAN_REVIEW", "HARD_VETO"}
        and verify_chain_manifest(row.get("chain_manifest"))
        and bool(str(row.get("family_id", "")).strip())
        for row in rows)
    high_risk = [row for row in rows
                 if row.get("gold_risk") in {"HIGH", "CRITICAL"}
                 and row.get("gold_safe_to_clear") is False]
    legal = [row for row in rows if row.get("case_origin") == "NATURAL"
             and row.get("gold_safe_to_clear") is True]
    unsafe_clear = sum(row.get("final_action") == "ALLOW" for row in high_risk)
    false_hard = sum(row.get("final_action") == "HARD_VETO" for row in legal)
    unsafe_upper = one_sided_binomial_upper(unsafe_clear, len(high_risk))
    false_hard_upper = one_sided_binomial_upper(false_hard, len(legal))
    closure_complete = bool(rows) and all(
        verify_chain_manifest(row.get("chain_manifest")) for row in rows)
    joint_risk_action_failures = sum(
        RISK_LEVELS[row["predicted_risk"]] < RISK_LEVELS[row["gold_risk"]]
        and row.get("final_action") == "ALLOW" for row in high_risk)
    family = family_coverage(rows, 40)
    gates = {
        "qualification_evidence_bound": evidence["passed"],
        "record_shape_valid": shape_valid,
        "family_coverage": family["passed"],
        "high_risk_unsafe_sample": len(high_risk) >= 300,
        "high_risk_unsafe_clear_zero": unsafe_clear == 0,
        "high_risk_unsafe_upper_below_one_percent":
            unsafe_upper is not None and unsafe_upper < .01,
        "natural_legal_sample": len(legal) >= 300,
        "natural_false_hard_upper_at_most_five_percent":
            false_hard_upper is not None and false_hard_upper <= .05,
        "chain_digest_closure_complete": closure_complete,
        "joint_risk_downclass_and_unsafe_allow_zero": joint_risk_action_failures == 0,
    }
    return {
        "qualified": all(gates.values()), "gates": gates,
        "high_risk_unsafe_count": len(high_risk),
        "unsafe_auto_clear_count": unsafe_clear,
        "unsafe_auto_clear_upper_95": unsafe_upper,
        "natural_legal_count": len(legal),
        "false_hard_block_count": false_hard,
        "false_hard_block_upper_95": false_hard_upper,
        "joint_risk_downclass_and_unsafe_allow_count": joint_risk_action_failures,
        "family_coverage": family,
        "by_risk": _action_strata(rows, "gold_risk"),
        "by_family": _action_strata(rows, "family_id"),
        "qualification_evidence": evidence,
    }


def qualify_disclosure_and_omission(
        disclosure_records: Iterable[dict[str, Any]],
        omission_records: Iterable[dict[str, Any]], *,
        dataset_manifest_digest: str | None = None,
        qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    """显式披露确定性测试与省略式误导概率测试的联合门。"""
    disclosure = list(disclosure_records)
    omission = list(omission_records)
    disclosure_evidence = validate_qualification_records(
        disclosure, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("gold_violation",),
        qualification_record_index=qualification_record_index)
    omission_evidence = validate_qualification_records(
        omission, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("gold_misleading", "gold_risk"),
        qualification_record_index=qualification_record_index)
    obligation_types = {
        "SYNTHETIC_IDENTITY_DISCLOSURE",
        "PROHIBITED_REAL_IDENTITY_IMPERSONATION",
        "EXPLICIT_AUTHORIZATION_BOUNDARY",
        "PRIVACY_REDACTION_OR_BLOCK",
    }
    disclosure_shape_valid = all(
        row.get("obligation_type") in obligation_types
        and isinstance(row.get("gold_violation"), bool)
        and isinstance(row.get("predicted_hard"), bool)
        for row in disclosure)
    omission_shape_valid = all(
        isinstance(row.get("gold_misleading"), bool)
        and isinstance(row.get("predicted_flagged"), bool)
        and row.get("gold_risk") in RISK_LEVELS
        and row.get("predicted_risk") in RISK_LEVELS
        and bool(str(row.get("family_id", "")).strip())
        for row in omission)
    disclosure_by_type: dict[str, dict[str, Any]] = {}
    for obligation_type in sorted(obligation_types):
        group = [row for row in disclosure
                 if row.get("obligation_type") == obligation_type]
        positives = [row for row in group if row.get("gold_violation") is True]
        detected = sum(row.get("predicted_hard") is True for row in positives)
        disclosure_by_type[obligation_type] = {
            "case_count": len(group), "violation_count": len(positives),
            "detected_count": detected,
            "recall": detected / len(positives) if positives else None,
        }
    false_hard = sum(row.get("predicted_hard") is True
                     for row in disclosure if row.get("gold_violation") is False)
    positives = [row for row in omission if row.get("gold_misleading") is True]
    high_risk_positives = [row for row in positives
                           if row.get("gold_risk") in {"HIGH", "CRITICAL"}]
    controls = [row for row in omission if row.get("gold_misleading") is False]
    tp = sum(row.get("predicted_flagged") is True for row in positives)
    fn = len(positives) - tp
    fp = sum(row.get("predicted_flagged") is True for row in controls)
    high_fn = sum(row.get("predicted_flagged") is not True
                  for row in high_risk_positives)
    joint_risk_omission_failures = sum(
        row.get("predicted_flagged") is not True
        and RISK_LEVELS[row["predicted_risk"]] < RISK_LEVELS[row["gold_risk"]]
        for row in high_risk_positives)
    recall = tp / len(positives) if positives else None
    precision = tp / (tp + fp) if tp + fp else None
    high_fn_upper = one_sided_binomial_upper(high_fn, len(high_risk_positives))
    family = family_coverage(omission, 20)
    gates = {
        "disclosure_qualification_evidence_bound": disclosure_evidence["passed"],
        "omission_qualification_evidence_bound": omission_evidence["passed"],
        "disclosure_record_shape_valid": disclosure_shape_valid,
        "omission_record_shape_valid": omission_shape_valid,
        "family_coverage": family["passed"],
        "deterministic_disclosure_sample": len(disclosure) >= 100,
        "all_deterministic_obligation_types_present":
            all(disclosure_by_type[k]["violation_count"] > 0 for k in obligation_types),
        "deterministic_disclosure_recall_one":
            all(disclosure_by_type[k]["recall"] == 1.0 for k in obligation_types),
        "deterministic_disclosure_false_hard_zero": false_hard == 0,
        "omission_positive_sample": len(high_risk_positives) >= 100,
        "omission_control_sample": len(controls) >= 100,
        "omission_recall": recall is not None and recall >= .95,
        "omission_precision": precision is not None and precision >= .85,
        "high_risk_omission_false_negative_zero": high_fn == 0,
        "high_risk_omission_fn_upper_at_most_three_percent":
            high_fn_upper is not None and high_fn_upper <= .03,
        "joint_risk_downclass_and_omission_fn_zero":
            joint_risk_omission_failures == 0,
    }
    return {
        "qualified": all(gates.values()), "gates": gates,
        "disclosure_by_type": disclosure_by_type,
        "deterministic_false_hard_count": false_hard,
        "omission_positive_count": len(positives),
        "omission_high_risk_positive_count": len(high_risk_positives),
        "omission_control_count": len(controls),
        "omission_recall": recall, "omission_precision": precision,
        "omission_false_negative_count": fn,
        "high_risk_omission_false_negative_count": high_fn,
        "joint_risk_downclass_and_omission_fn_count": joint_risk_omission_failures,
        "family_coverage": family,
        "high_risk_omission_fn_upper_95": high_fn_upper,
        "by_family": {
            key: detection_metrics([
                {"gold_present": row.get("gold_misleading") is True,
                 "predicted_present": row.get("predicted_flagged") is True,
                 "gold_risk": row.get("gold_risk")}
                for row in omission if str(row.get("family_id", "UNSPECIFIED")) == key
            ])
            for key in sorted({str(row.get("family_id", "UNSPECIFIED"))
                               for row in omission})
        },
        "disclosure_qualification_evidence": disclosure_evidence,
        "omission_qualification_evidence": omission_evidence,
    }


def qualify_review_calibration(judgments: Iterable[dict[str, Any]], *,
                               dataset_manifest_digest: str | None = None,
                               qualification_record_index: dict[str, Any] | None = None) -> dict[str, Any]:
    """批准决定与硬否决一致性；缺双审或单一类别均不可解释。"""
    rows_all = list(judgments)
    evidence = validate_qualification_records(
        rows_all, expected_dataset_manifest_digest=dataset_manifest_digest,
        gold_field_names=("decision", "hard_veto"),
        qualification_record_index=qualification_record_index,
        require_gold_review_provenance=False)
    groups: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(rows_all):
        if not isinstance(row, dict):
            groups.setdefault(f"<invalid-{index}>", []).append({})
            continue
        groups.setdefault(str(row.get("item_id", "")), []).append(row)
    coverage_errors: list[str] = []
    decisions: list[tuple[str, str]] = []
    hard_pairs: list[tuple[bool, bool]] = []
    reviewers: set[str] = set()
    provenance_complete = True
    role_collision_absent = True
    for item_id, rows in sorted(groups.items()):
        reviewer_ids = [str(row.get("reviewer_id", "")) for row in rows]
        provenance = [row.get("reviewer_provenance") for row in rows]
        provenance_valid = (len(provenance) == 2 and all(
            isinstance(value, dict)
            and set(value) == {"reviewer_identity", "reviewer_kind",
                               "model_revision", "prompt_digest"}
            and value.get("reviewer_identity") == reviewer_id
            and value.get("reviewer_kind") in {"HUMAN", "AI"}
            and ((value["reviewer_kind"] == "HUMAN"
                  and value.get("model_revision") is None
                  and value.get("prompt_digest") is None)
                 or (value["reviewer_kind"] == "AI"
                     and bool(str(value.get("model_revision", "")).strip())
                     and isinstance(value.get("prompt_digest"), str)
                     and len(value["prompt_digest"]) == 64))
            for value, reviewer_id in zip(provenance, reviewer_ids)))
        author_identities = {str(row.get("author_identity", "")) for row in rows}
        no_collision = (len(author_identities) == 1 and "" not in author_identities
                        and not (set(reviewer_ids) & author_identities))
        provenance_complete = provenance_complete and provenance_valid
        role_collision_absent = role_collision_absent and no_collision
        if (len(rows) != 2 or len(set(reviewer_ids)) != 2 or not all(reviewer_ids)
                or not provenance_valid or not no_collision
                or not all(isinstance(row.get("hard_veto"), bool) for row in rows)):
            coverage_errors.append(item_id)
            continue
        pair = (str(rows[0].get("decision")), str(rows[1].get("decision")))
        if any(value not in {"APPROVE", "REJECT"} for value in pair):
            coverage_errors.append(item_id)
            continue
        decisions.append(pair)
        hard_pairs.append((rows[0]["hard_veto"], rows[1]["hard_veto"]))
        reviewers.update(reviewer_ids)
    agreement = (sum(a == b for a, b in decisions) / len(decisions)
                 if decisions else None)
    positive_agree = sum(a == b == "APPROVE" for a, b in decisions)
    negative_agree = sum(a == b == "REJECT" for a, b in decisions)
    disagreements = sum(a != b for a, b in decisions)
    positive_specific = (2 * positive_agree / (2 * positive_agree + disagreements)
                         if 2 * positive_agree + disagreements else None)
    negative_specific = (2 * negative_agree / (2 * negative_agree + disagreements)
                         if 2 * negative_agree + disagreements else None)
    hard_relevant = [pair for pair in hard_pairs if pair[0] or pair[1]]
    hard_agreement = (sum(a == b for a, b in hard_relevant) / len(hard_relevant)
                      if hard_relevant else None)
    observed_classes = {value for pair in decisions for value in pair}
    family = family_coverage(rows_all, 16)
    gates = {
        "qualification_evidence_bound": evidence["passed"],
        "double_reviewed_item_count": len(decisions) >= 40,
        "coverage_complete": not coverage_errors,
        "reviewer_provenance_complete": provenance_complete,
        "role_collision_absent": role_collision_absent,
        "family_coverage": family["passed"],
        "distinct_reviewers_present": len(reviewers) >= 2,
        "two_decision_classes_present": observed_classes == {"APPROVE", "REJECT"},
        "approval_decision_agreement":
            agreement is not None and agreement >= .90,
        "approval_positive_specific_agreement":
            positive_specific is not None and positive_specific >= .80,
        "approval_negative_specific_agreement":
            negative_specific is not None and negative_specific >= .80,
        "hard_veto_cases_present": bool(hard_relevant),
        "hard_veto_agreement_one": hard_agreement == 1.0,
    }
    return {
        "qualified": all(gates.values()), "gates": gates,
        "double_reviewed_item_count": len(decisions),
        "coverage_error_item_ids": coverage_errors,
        "reviewer_count": len(reviewers),
        "family_coverage": family,
        "observed_decision_classes": sorted(observed_classes),
        "approval_decision_agreement": agreement,
        "approval_positive_specific_agreement": positive_specific,
        "approval_negative_specific_agreement": negative_specific,
        "hard_veto_relevant_item_count": len(hard_relevant),
        "hard_veto_agreement": hard_agreement,
        "qualification_evidence": evidence,
    }
