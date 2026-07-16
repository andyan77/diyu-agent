"""独立主张链、已知高风险回归规则与动作边界。"""

from __future__ import annotations

from typing import Any, Iterable

from .canonical import stable_id


def covered_claim_candidates(surface: str, candidates: Iterable[dict[str, Any]],
                             atoms: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """审计独立抽取候选是否全部进入主张原子集。

    author semantic_claims 故意不作为参数：作者自报只能作提示，不能证明全集。
    """
    atom_spans = {(a.get("char_start", a.get("start")),
                   a.get("char_end", a.get("end"))) for a in atoms}
    missing: list[str] = []
    malformed: list[str] = []
    for candidate in candidates:
        start, end = candidate.get("start"), candidate.get("end")
        if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(surface)):
            malformed.append(str(candidate.get("candidate_id")))
        elif (start, end) not in atom_spans:
            missing.append(str(candidate.get("candidate_id")))
    return {"passed": not missing and not malformed, "missing_candidate_ids": sorted(missing),
            "malformed_candidate_ids": sorted(malformed)}


def make_claim_atom(output_id: str, surface: str, start: int, end: int,
                    extractor_ref: str, *, surface_kind: str = "BODY",
                    risk_class: str = "MEDIUM") -> dict[str, Any]:
    if not (0 <= start < end <= len(surface)):
        raise ValueError("invalid claim atom span")
    text = surface[start:end]
    from .canonical import digest_json
    atom: dict[str, Any] = {
        "schema_version": "eval-spine-claim-atom-v1",
        "claim_atom_id": stable_id("CL", output_id, start, end, text),
        "output_id": output_id, "surface_kind": surface_kind, "text": text,
        "char_start": start, "char_end": end, "extraction_origin": "DETERMINISTIC_RULE",
        "engine_provenance": {"engine_kind": "RULE", "engine_id": extractor_ref,
                              "engine_revision": extractor_ref,
                              "prompt_or_rule_digest": None, "provider_call_id": None},
        "risk_class": risk_class, "verification_status": "PROPOSED",
        "review_ids": [], "object_digest": "",
    }
    unsigned = dict(atom)
    unsigned.pop("object_digest")
    atom["object_digest"] = digest_json(unsigned)
    return atom


def runtime_action(*, relation: str | None, risk: str, deterministic: bool,
                   reference_adjudicated: bool, evaluator_qualified: bool,
                   abstain: bool = False) -> str:
    """只有已裁决结构事实上的确定性矛盾可自动 HARD。

    概率门未资格化时，即使给出 SUPPORTED 也不能自动清除高风险。
    """
    if abstain or relation is None:
        return "HUMAN_REVIEW"
    if (deterministic and reference_adjudicated and relation == "CONTRADICTED"):
        return "HARD_VETO"
    if relation in {"CONTRADICTED", "UNKNOWN"}:
        return "HUMAN_REVIEW"
    if relation == "SUPPORTED":
        if not evaluator_qualified or not reference_adjudicated:
            return "HUMAN_REVIEW"
        if risk in {"HIGH", "CRITICAL"}:
            return "HUMAN_REVIEW"
        if risk in {"LOW", "MEDIUM"}:
            return "ALLOW"
    return "HUMAN_REVIEW"


def known_risk_findings(output_id: str, surface: str) -> list[dict[str, Any]]:
    """仅供开发回归的高精度规则；不得冒充通用语义门。"""
    rules = [
        ("R5_DURABILITY_UNSUPPORTED", ("反复套脱", "不走形")),
        ("R5_FIBER_UNSUPPORTED", ("粗棉纹",)),
        ("R5_QUILTED_COTTON_UNSUPPORTED", ("绗缝的棉层",)),
        ("R5_EMPTY_NUMBER_CALLBACK_CONTRADICTION", ("4位", "回访电话", "逐个打")),
        ("R5_INQUIRY_TO_PREFERENCE_OVERREACH", ("六次", "都指", "这摞")),
    ]
    findings = []
    for code, needles in rules:
        if all(needle in surface for needle in needles):
            findings.append({
                "finding_id": stable_id("RF", output_id, code),
                "output_id": output_id,
                "code": code,
                "layer": "DETERMINISTIC_DEVELOPMENT_REGRESSION",
                "action": "HUMAN_REVIEW",
                "qualification_use": False,
            })
    return findings
