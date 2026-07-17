"""确定性合成披露与概率性省略风险分层。"""

from __future__ import annotations

from typing import Any, Iterable

from .canonical import digest_json


def check_required_disclosures(surface: str, obligation_manifest: dict[str, Any],
                               *, structured_state: dict[str, Any] | None = None
                               ) -> dict[str, Any]:
    required = {"schema_version", "source_input_digest", "complete",
                "obligations", "manifest_digest"}
    if set(obligation_manifest) != required:
        return {"passed": False, "missing_obligation_ids": [],
                "action": "HUMAN_REVIEW", "reason": "MANIFEST_FIELD_SET"}
    unsigned = dict(obligation_manifest)
    supplied = unsigned.pop("manifest_digest", None)
    if (obligation_manifest.get("schema_version")
            != "eval-spine-disclosure-obligation-manifest-v1"
            or obligation_manifest.get("complete") is not True
            or not isinstance(obligation_manifest.get("source_input_digest"), str)
            or len(obligation_manifest["source_input_digest"]) != 64
            or supplied != digest_json(unsigned)
            or not isinstance(obligation_manifest.get("obligations"), list)):
        return {"passed": False, "missing_obligation_ids": [],
                "action": "HUMAN_REVIEW", "reason": "MANIFEST_NOT_CLOSED"}
    obligations = obligation_manifest["obligations"]
    missing: list[str] = []
    for obligation in obligations:
        if not obligation.get("required", False):
            continue
        check_kind = obligation.get("check_kind", "MARKER_ANY")
        if check_kind == "MARKER_ANY":
            alternatives = [str(x) for x in obligation.get("accepted_markers", [])]
            satisfied = bool(alternatives) and any(marker in surface for marker in alternatives)
        elif check_kind == "STRUCTURED_BOOLEAN":
            field = str(obligation.get("state_field", ""))
            satisfied = bool(field) and (structured_state or {}).get(field) is True
        else:
            satisfied = False
        if not satisfied:
            missing.append(str(obligation["obligation_id"]))
    return {"passed": not missing, "missing_obligation_ids": sorted(missing),
            "action": "ALLOW" if not missing else "HARD_VETO",
            "reason": "COMPLETE_MANIFEST_EVALUATED"}


def omission_risk_action(*, detector_flagged: bool, detector_qualified: bool,
                         risk: str = "HIGH",
                         human_adjudicated_misleading: bool = False,
                         human_adjudicated_nonmisleading: bool = False) -> str:
    if human_adjudicated_misleading and human_adjudicated_nonmisleading:
        raise ValueError("human omission adjudication cannot have two outcomes")
    if human_adjudicated_misleading:
        return "HARD_VETO"
    if human_adjudicated_nonmisleading:
        return "ALLOW"
    if detector_flagged or not detector_qualified:
        return "HUMAN_REVIEW"
    if risk in {"HIGH", "CRITICAL"}:
        return "HUMAN_REVIEW"
    return "ALLOW"
