"""Pattern-based sanitizer for PII redaction and prompt injection detection.

Task card: B4-5
- PII patterns: phone, email, ID card, bank card
- Prompt injection patterns: jailbreak, override, system-prompt leak
- Acceptance: >= 99% interception rate on known injection patterns

Architecture: Section 2.1 (Input Sanitization Layer)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# -- Numeric PII classifier --
# A single pattern captures all long digit sequences, then a callback
# classifies them by length and prefix to avoid overlapping-match bugs.
_NUMERIC_PII_RE = re.compile(r"\d{11,19}[\dXx]?")

# Email pattern (applied separately since it's not numeric)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def _classify_numeric(match: re.Match[str]) -> str:
    """Classify a numeric PII match by length and prefix."""
    digits = match.group(0)
    length = len(digits)

    # Chinese ID card: exactly 18 chars, 6-digit area + 8-digit date + 3-digit seq + check
    if length == 18 and (digits[-1].isdigit() or digits[-1] in "Xx") and digits[0] in "12345678":
        return "[ID_CARD]"

    # Bank card: 16-19 digits, starts with 3-6 (Visa/MC/UnionPay/AmEx)
    if 16 <= length <= 19 and digits[0] in "3456":
        return "[BANK_CARD]"

    # Chinese mobile phone: 11 digits starting with 1[3-9]
    if length == 11 and digits[0] == "1" and digits[1] in "3456789":
        return "[PHONE]"

    # Unknown long number — leave as-is
    return digits


# -- Prompt injection detection patterns --

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(your\s+)?instructions", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(above|previous)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer|DAN|admin)\s+mode", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+have\s+no\s+restrictions", re.IGNORECASE),
    re.compile(r"system\s*:?\s*(prompt\s*:?\s*)?override", re.IGNORECASE),
    re.compile(r"system\s*:?\s*forget\s+all", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"(from\s+now\s+on|i\s+want\s+you\s+to)\s*,?\s*act\s+as", re.IGNORECASE),
    re.compile(r"bypass\s+(your\s+)?content\s+policy", re.IGNORECASE),
    re.compile(r"new\s+instruction\s*:?\s*ignore", re.IGNORECASE),
    re.compile(r"override\s*:?\s*you\s+can\s+do\s+anything", re.IGNORECASE),
    re.compile(
        r"(reveal|tell\s+me|what\s+is)\s+(your\s+)?(system\s+prompt|initial\s+instructions)",
        re.IGNORECASE,
    ),
    re.compile(r"repeat\s+everything\s+above", re.IGNORECASE),
    re.compile(r"ignore\s+safety\s+guidelines", re.IGNORECASE),
    re.compile(r"act\s+without\s+restrictions", re.IGNORECASE),
]


@dataclass(frozen=True)
class SanitizeResult:
    """Result of sanitization."""

    text: str
    redacted_count: int
    blocked: bool
    block_reason: str

    @property
    def is_clean(self) -> bool:
        """True if no PII was found and the message is not blocked."""
        return self.redacted_count == 0 and not self.blocked


class PatternSanitizer:
    """Pattern-based input sanitizer.

    1. Check for prompt injection patterns -> block if found.
    2. Redact PII patterns -> replace with tokens.
    """

    def sanitize(self, text: str) -> SanitizeResult:
        """Sanitize input text."""
        # Step 1: Prompt injection check
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                return SanitizeResult(
                    text="",
                    redacted_count=0,
                    blocked=True,
                    block_reason=f"Prompt injection detected: {pattern.pattern}",
                )

        # Step 2: PII redaction (numeric)
        redacted_count = 0

        def _replace_numeric(m: re.Match[str]) -> str:
            nonlocal redacted_count
            replacement = _classify_numeric(m)
            if replacement != m.group(0):
                redacted_count += 1
            return replacement

        result_text = _NUMERIC_PII_RE.sub(_replace_numeric, text)

        # Step 3: PII redaction (email)
        result_text, email_count = _EMAIL_RE.subn("[EMAIL]", result_text)
        redacted_count += email_count

        return SanitizeResult(
            text=result_text,
            redacted_count=redacted_count,
            blocked=False,
            block_reason="",
        )
