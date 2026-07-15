#!/usr/bin/env python3
"""G3 · 近重复检测（字符 4-gram Jaccard，确定性、无依赖）。

用途：
- 批内两两近重复（REVIEW_FLAG，人审确认后计入近重复率）
- 对冻结 120 参考原文 / 29 既有批准项的跨来源复现（HARD：标准 L767
  "来源近原文复现数量必须为0"、硬否决 #13 实质性复制）

阈值经上一轮 211 条真实输出校准（见 evidence/gate_calibration_report）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_PUNCT_RE = re.compile(r"[\s，。；：、！？「」『』“”‘’（）()《》…—\-·,.;:!?\"']+")

BATCH_FLAG_THRESHOLD = 0.22   # 批内两两 ≥ 0.22 → 近重复复核队列
FROZEN_HARD_THRESHOLD = 0.35  # 对 120/29 冻结文本 ≥ 0.35 → 机器硬失败


def normalize(text: str) -> str:
    return _PUNCT_RE.sub("", text)


def audience_fulltext(output: Mapping[str, Any]) -> str:
    parts = [str(output["title"]), *map(str, output["body"]),
             *map(str, output.get("spoken_lines", []))]
    cta = str(output.get("cta", ""))
    if cta:
        parts.append(cta)
    return "\n".join(parts)


def char_ngrams(text: str, n: int = 4) -> set[str]:
    s = normalize(text)
    if len(s) < n:
        return {s} if s else set()
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def pairwise_batch_findings(
    outputs: Sequence[Mapping[str, Any]],
    threshold: float = BATCH_FLAG_THRESHOLD,
) -> list[dict[str, Any]]:
    grams = [(str(o["request_id"]), char_ngrams(audience_fulltext(o)))
             for o in outputs]
    findings = []
    for i in range(len(grams)):
        for j in range(i + 1, len(grams)):
            score = jaccard(grams[i][1], grams[j][1])
            if score >= threshold:
                findings.append(
                    {"kind": "NEAR_DUP_IN_BATCH",
                     "request_ids": sorted([grams[i][0], grams[j][0]]),
                     "jaccard": round(score, 4)}
                )
    return sorted(findings, key=lambda f: (-f["jaccard"], f["request_ids"]))


def frozen_reuse_findings(
    outputs: Sequence[Mapping[str, Any]],
    frozen_texts: Mapping[str, str],
    threshold: float = FROZEN_HARD_THRESHOLD,
) -> list[dict[str, Any]]:
    """对冻结文本（120 参考 / 既有批准项）的近原文复现（HARD）。"""
    frozen_grams = {key: char_ngrams(text) for key, text in frozen_texts.items()}
    findings = []
    for output in outputs:
        grams = char_ngrams(audience_fulltext(output))
        for key in sorted(frozen_grams):
            score = jaccard(grams, frozen_grams[key])
            if score >= threshold:
                findings.append(
                    {"kind": "FROZEN_TEXT_REUSE",
                     "request_id": str(output["request_id"]),
                     "frozen_key": key, "jaccard": round(score, 4)}
                )
    return sorted(findings,
                  key=lambda f: (-f["jaccard"], f["request_id"], f["frozen_key"]))


__all__ = [
    "BATCH_FLAG_THRESHOLD",
    "FROZEN_HARD_THRESHOLD",
    "audience_fulltext",
    "char_ngrams",
    "frozen_reuse_findings",
    "jaccard",
    "normalize",
    "pairwise_batch_findings",
]
