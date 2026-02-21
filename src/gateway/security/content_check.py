"""Content security check -- intercept harmful content.

Task card: G3-3 / OS3-1
- security_status 6-state model: clean | suspicious | flagged | blocked | under_review | exempt
- Harmful content interception rate >= 95%
- Three-layer check: pattern matching + keyword + heuristic

Architecture: docs/architecture/05-Gateway Section 8 (Content Security)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SecurityStatus(Enum):
    """Content security status (6-state model)."""

    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    FLAGGED = "flagged"
    BLOCKED = "blocked"
    UNDER_REVIEW = "under_review"
    EXEMPT = "exempt"


@dataclass(frozen=True)
class ContentCheckResult:
    """Result of content security check."""

    status: SecurityStatus
    confidence: float  # 0.0-1.0
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# Threat patterns (compiled for performance)
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are\s+now", re.IGNORECASE),
    re.compile(r"</?(system|admin|root)>", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]

_HARMFUL_KEYWORDS = frozenset(
    {
        "self-harm",
        "suicide method",
        "how to make bomb",
        "how to hack",
        "exploit vulnerability",
        "steal credentials",
        "ddos attack",
        "ransomware",
    }
)

_XSS_PATTERNS = [
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"on(?:load|error|click|focus|mouseover)\s*=", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<iframe[\s>]", re.IGNORECASE),
    re.compile(
        r"<(?:img|svg|body|input|form|link|meta|marquee)\b[^>]*(?:src|href|action|content|rel)\s*=",
        re.IGNORECASE,
    ),
    re.compile(r"<(?:img|svg|body|input)\b", re.IGNORECASE),
    re.compile(r"\{\{.*constructor", re.IGNORECASE),
    re.compile(r"<form\b", re.IGNORECASE),
    re.compile(r"<link\b", re.IGNORECASE),
    re.compile(r"<meta\b", re.IGNORECASE),
    re.compile(r"<marquee\b", re.IGNORECASE),
    re.compile(r"<h[1-6]\b.*>.*</h[1-6]>", re.IGNORECASE),
]

_PII_PATTERNS = [
    re.compile(r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b"),  # SSN-like
    re.compile(r"\b\d{15,19}\b"),  # Credit card-like
]


class ContentSecurityChecker:
    """Four-layer content security pipeline.

    Layer 1: Pattern matching (injection, jailbreak)
    Layer 1.5: XSS / HTML injection detection (OS3-3)
    Layer 2: Keyword detection (harmful content)
    Layer 3: PII detection (data leakage prevention)

    All layers run in sequence; first block wins.
    """

    def check(self, content: str) -> ContentCheckResult:
        """Run content through the security pipeline.

        Args:
            content: Text content to check.

        Returns:
            ContentCheckResult with status and reasons.
        """
        if not content or not content.strip():
            return ContentCheckResult(
                status=SecurityStatus.CLEAN,
                confidence=1.0,
            )

        reasons: list[str] = []

        # Layer 1: Injection / jailbreak patterns
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(content):
                reasons.append(f"Injection pattern detected: {pattern.pattern}")
                return ContentCheckResult(
                    status=SecurityStatus.BLOCKED,
                    confidence=0.95,
                    reasons=reasons,
                    metadata={"layer": "injection", "pattern": pattern.pattern},
                )

        # Layer 1.5: XSS / HTML injection patterns (OS3-3)
        for pattern in _XSS_PATTERNS:
            if pattern.search(content):
                reasons.append(f"XSS/HTML injection detected: {pattern.pattern}")
                return ContentCheckResult(
                    status=SecurityStatus.BLOCKED,
                    confidence=0.95,
                    reasons=reasons,
                    metadata={"layer": "xss", "pattern": pattern.pattern},
                )

        # Layer 2: Harmful content keywords
        content_lower = content.lower()
        for keyword in _HARMFUL_KEYWORDS:
            if keyword in content_lower:
                reasons.append(f"Harmful keyword detected: {keyword}")
                return ContentCheckResult(
                    status=SecurityStatus.BLOCKED,
                    confidence=0.90,
                    reasons=reasons,
                    metadata={"layer": "keyword", "keyword": keyword},
                )

        # Layer 3: PII detection
        for pattern in _PII_PATTERNS:
            if pattern.search(content):
                reasons.append("Potential PII detected")
                return ContentCheckResult(
                    status=SecurityStatus.FLAGGED,
                    confidence=0.75,
                    reasons=reasons,
                    metadata={"layer": "pii"},
                )

        return ContentCheckResult(
            status=SecurityStatus.CLEAN,
            confidence=1.0,
        )

    def update_status(
        self,
        current: SecurityStatus,
        review_decision: str,
    ) -> SecurityStatus:
        """Update security status based on review decision.

        Args:
            current: Current security status.
            review_decision: "approve" | "reject" | "escalate"

        Returns:
            Updated SecurityStatus.
        """
        if review_decision == "approve":
            return SecurityStatus.CLEAN
        if review_decision == "reject":
            return SecurityStatus.BLOCKED
        if review_decision == "escalate":
            return SecurityStatus.UNDER_REVIEW
        return current
