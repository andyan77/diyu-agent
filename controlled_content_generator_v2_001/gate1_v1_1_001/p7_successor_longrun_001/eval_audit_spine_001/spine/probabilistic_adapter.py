"""可替换的概率适配层；默认保守弃权。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelFinding:
    label: str | None
    confidence: float | None
    evidence_ids: tuple[str, ...]
    abstain: bool
    model_revision: str


class EntailmentAdapter(Protocol):
    def classify(self, claim_text: str, reference_text: str) -> ModelFinding: ...


def independent_claim_candidates(surface: str, extractor_revision: str) -> list[dict[str, object]]:
    """薄前门的开发候选器，不声称主张拆分完整或已资格化。"""
    candidates: list[dict[str, object]] = []
    for match in re.finditer(r"[^。！？!?\n]+[。！？!?]?", surface):
        text = match.group(0).strip()
        if text:
            start = match.start() + len(match.group(0)) - len(match.group(0).lstrip())
            candidates.append({"candidate_id": f"CAND-{len(candidates)+1:04d}",
                               "start": start, "end": start + len(text), "text": text,
                               "extractor_revision": extractor_revision,
                               "qualification_status": "UNQUALIFIED"})
    return candidates


class AbstainingAdapter:
    """没有经验证的评估器时，正确行为是显式弃权。"""

    def __init__(self, revision: str = "abstain-baseline-v1") -> None:
        self.revision = revision

    def classify(self, claim_text: str, reference_text: str) -> ModelFinding:
        del claim_text, reference_text
        return ModelFinding(label=None, confidence=None, evidence_ids=(), abstain=True,
                            model_revision=self.revision)
