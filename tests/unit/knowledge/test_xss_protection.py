"""OS3-3: Knowledge write XSS / injection protection tests.

Validates that all text content written through the Knowledge Write API
is sanitized against XSS, HTML injection, and script injection.

Acceptance: injection sanitization rate 100%.
Test path: `uv run pytest tests/unit/knowledge/test_xss_protection.py -q`
"""

from __future__ import annotations

import pytest

from src.gateway.security.content_check import (
    ContentSecurityChecker,
    SecurityStatus,
)

# -- XSS payloads that MUST be detected --
XSS_PAYLOADS: list[str] = [
    '<script>alert("xss")</script>',
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    'javascript:alert("xss")',
    '<iframe src="javascript:alert(1)">',
    "<body onload=alert(1)>",
    "<input onfocus=alert(1) autofocus>",
    '<a href="javascript:void(0)" onclick="alert(1)">click</a>',
    "{{constructor.constructor('return this')()}}",
    '<div style="background:url(javascript:alert(1))">',
]

# -- HTML injection payloads --
HTML_INJECTION_PAYLOADS: list[str] = [
    "<h1>Injected heading</h1>",
    '<form action="http://evil.com"><input type="submit"></form>',
    "<marquee>scrolling text</marquee>",
    '<link rel="stylesheet" href="http://evil.com/style.css">',
    "<meta http-equiv='refresh' content='0;url=http://evil.com'>",
]


@pytest.mark.unit
class TestXSSDetection:
    """Content security pipeline must detect XSS payloads."""

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_payload_not_clean(self, payload: str) -> None:
        """XSS payloads must NOT pass as clean content."""
        checker = ContentSecurityChecker()
        result = checker.check(payload)
        assert result.status != SecurityStatus.CLEAN, f"XSS payload passed as clean: {payload!r}"

    @pytest.mark.parametrize("payload", XSS_PAYLOADS[:5])
    def test_xss_payload_blocked_or_flagged(self, payload: str) -> None:
        """Core XSS payloads must be BLOCKED or FLAGGED."""
        checker = ContentSecurityChecker()
        result = checker.check(payload)
        assert result.status in (SecurityStatus.BLOCKED, SecurityStatus.FLAGGED), (
            f"XSS payload not blocked/flagged: {payload!r} -> {result.status}"
        )


@pytest.mark.unit
class TestHTMLInjectionDetection:
    """Content security pipeline must detect HTML injection."""

    @pytest.mark.parametrize("payload", HTML_INJECTION_PAYLOADS)
    def test_html_injection_not_clean(self, payload: str) -> None:
        """HTML injection payloads must NOT pass as clean."""
        checker = ContentSecurityChecker()
        result = checker.check(payload)
        assert result.status != SecurityStatus.CLEAN, f"HTML injection passed as clean: {payload!r}"


@pytest.mark.unit
class TestSanitizationRate:
    """Injection sanitization rate must be 100% for known vectors."""

    def test_overall_xss_sanitization_rate(self) -> None:
        """All XSS payloads must be caught (100% rate)."""
        checker = ContentSecurityChecker()
        caught = 0
        for payload in XSS_PAYLOADS:
            result = checker.check(payload)
            if result.status != SecurityStatus.CLEAN:
                caught += 1

        rate = caught / len(XSS_PAYLOADS)
        assert rate == 1.0, (
            f"XSS sanitization rate {rate:.0%} < 100%: "
            f"{len(XSS_PAYLOADS) - caught} payloads escaped"
        )


@pytest.mark.unit
class TestCleanContentNotBlocked:
    """Legitimate content must not trigger false positives."""

    def test_product_description_clean(self) -> None:
        checker = ContentSecurityChecker()
        result = checker.check("This silk dress features a beautiful floral pattern.")
        assert result.status == SecurityStatus.CLEAN

    def test_knowledge_entry_clean(self) -> None:
        checker = ContentSecurityChecker()
        result = checker.check(
            "Brand ABC was founded in 2020. It specializes in sustainable fashion."
        )
        assert result.status == SecurityStatus.CLEAN

    def test_technical_content_with_angle_brackets_clean(self) -> None:
        """Generic angle brackets in non-HTML context should be clean."""
        checker = ContentSecurityChecker()
        result = checker.check("Temperature must be > 0 and < 100 degrees.")
        assert result.status == SecurityStatus.CLEAN
