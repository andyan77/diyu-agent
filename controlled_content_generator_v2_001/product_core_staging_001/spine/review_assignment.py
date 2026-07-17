"""确定性的平衡交叉分派。"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Iterable


def _rank(seed: str, *values: str) -> str:
    return hashlib.sha256("\x1f".join((seed, *values)).encode()).hexdigest()


def balanced_cross_assign(items: Iterable[dict[str, Any]], reviewers: Iterable[str],
                          *, seed: str, reviews_per_item: int = 2) -> list[dict[str, Any]]:
    reviewer_ids = sorted(set(map(str, reviewers)))
    if reviews_per_item < 1 or len(reviewer_ids) < reviews_per_item:
        raise ValueError("not enough reviewers")
    loads: Counter[str] = Counter()
    assignments: list[dict[str, Any]] = []
    ordered = sorted(items, key=lambda x: _rank(seed, str(x["item_id"])))
    for item in ordered:
        selected: list[str] = []
        for slot in range(reviews_per_item):
            candidates = [reviewer for reviewer in reviewer_ids if reviewer not in selected]
            reviewer = min(candidates, key=lambda rid: (loads[rid],
                           _rank(seed, str(item["item_id"]), str(slot), rid)))
            selected.append(reviewer)
            loads[reviewer] += 1
            assignments.append({"item_id": str(item["item_id"]),
                                "profile_id": str(item.get("profile_id", "")),
                                "reviewer_id": reviewer, "review_slot": slot + 1})
    return sorted(assignments, key=lambda x: (x["item_id"], x["review_slot"]))


def assignment_audit(assignments: Iterable[dict[str, Any]], *, reviews_per_item: int,
                     author_by_item: dict[str, str] | None = None) -> dict[str, Any]:
    by_item: dict[str, list[str]] = {}
    loads: Counter[str] = Counter()
    errors: list[str] = []
    for row in assignments:
        item = str(row["item_id"])
        reviewer = str(row["reviewer_id"])
        by_item.setdefault(item, []).append(reviewer)
        loads[reviewer] += 1
        if author_by_item and author_by_item.get(item) == reviewer:
            errors.append(f"author_reviewer_collision:{item}:{reviewer}")
    for item, reviewers in by_item.items():
        if len(reviewers) != reviews_per_item or len(set(reviewers)) != reviews_per_item:
            errors.append(f"invalid_cross_coverage:{item}")
    spread = max(loads.values()) - min(loads.values()) if loads else 0
    if spread > 1:
        errors.append(f"reviewer_load_imbalance:{spread}")
    return {"passed": not errors, "errors": sorted(errors),
            "reviewer_loads": dict(sorted(loads.items())), "load_spread": spread}
