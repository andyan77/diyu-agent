"""Security headers middleware tests.

Task card: G1-6
- HSTS with configurable max-age, includeSubDomains, preload
- CSP with configurable directives
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 0
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: restricted defaults

Acceptance: pytest tests/unit/gateway/test_security_headers.py -v
"""

from __future__ import annotations

import pytest

from src.gateway.middleware.security_headers import (
    SecurityHeadersConfig,
    SecurityHeadersMiddleware,
)


@pytest.fixture()
def default_mw():
    return SecurityHeadersMiddleware()


@pytest.fixture()
def default_headers(default_mw):
    return default_mw.get_headers()


class TestHSTS:
    """Strict-Transport-Security header."""

    def test_hsts_present(self, default_headers):
        assert "Strict-Transport-Security" in default_headers

    def test_hsts_default_max_age(self, default_headers):
        hsts = default_headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts

    def test_hsts_includes_subdomains_by_default(self, default_headers):
        hsts = default_headers["Strict-Transport-Security"]
        assert "includeSubDomains" in hsts

    def test_hsts_no_preload_by_default(self, default_headers):
        hsts = default_headers["Strict-Transport-Security"]
        assert "preload" not in hsts

    def test_hsts_with_preload(self):
        cfg = SecurityHeadersConfig(hsts_preload=True)
        mw = SecurityHeadersMiddleware(config=cfg)
        hsts = mw.get_headers()["Strict-Transport-Security"]
        assert "preload" in hsts

    def test_hsts_custom_max_age(self):
        cfg = SecurityHeadersConfig(hsts_max_age=86400)
        mw = SecurityHeadersMiddleware(config=cfg)
        hsts = mw.get_headers()["Strict-Transport-Security"]
        assert "max-age=86400" in hsts

    def test_hsts_without_subdomains(self):
        cfg = SecurityHeadersConfig(hsts_include_subdomains=False)
        mw = SecurityHeadersMiddleware(config=cfg)
        hsts = mw.get_headers()["Strict-Transport-Security"]
        assert "includeSubDomains" not in hsts


class TestCSP:
    """Content-Security-Policy header."""

    def test_csp_present(self, default_headers):
        assert "Content-Security-Policy" in default_headers

    def test_csp_default_self(self, default_headers):
        csp = default_headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp

    def test_csp_script_src(self, default_headers):
        csp = default_headers["Content-Security-Policy"]
        assert "script-src 'self'" in csp

    def test_csp_object_none(self, default_headers):
        csp = default_headers["Content-Security-Policy"]
        assert "object-src 'none'" in csp

    def test_csp_frame_ancestors_none(self, default_headers):
        csp = default_headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp

    def test_csp_base_uri(self, default_headers):
        csp = default_headers["Content-Security-Policy"]
        assert "base-uri 'self'" in csp

    def test_csp_custom_directives(self):
        cfg = SecurityHeadersConfig(
            csp_directives={
                "default-src": "'self'",
                "script-src": "'self' https://cdn.example.com",
            }
        )
        mw = SecurityHeadersMiddleware(config=cfg)
        csp = mw.get_headers()["Content-Security-Policy"]
        assert "https://cdn.example.com" in csp


class TestOtherHeaders:
    """X-Content-Type-Options, X-Frame-Options, etc."""

    def test_content_type_options_nosniff(self, default_headers):
        assert default_headers["X-Content-Type-Options"] == "nosniff"

    def test_frame_options_deny(self, default_headers):
        assert default_headers["X-Frame-Options"] == "DENY"

    def test_xss_protection_disabled(self, default_headers):
        assert default_headers["X-XSS-Protection"] == "0"

    def test_referrer_policy(self, default_headers):
        assert default_headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, default_headers):
        pp = default_headers["Permissions-Policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp
        assert "geolocation=()" in pp


class TestCustomConfiguration:
    """Custom security header configurations."""

    def test_custom_frame_options(self):
        cfg = SecurityHeadersConfig(frame_options="SAMEORIGIN")
        mw = SecurityHeadersMiddleware(config=cfg)
        headers = mw.get_headers()
        assert headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_custom_referrer_policy(self):
        cfg = SecurityHeadersConfig(referrer_policy="no-referrer")
        mw = SecurityHeadersMiddleware(config=cfg)
        headers = mw.get_headers()
        assert headers["Referrer-Policy"] == "no-referrer"

    def test_all_seven_headers_present(self, default_headers):
        expected = {
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
        }
        assert expected == set(default_headers.keys())

    def test_frozen_config(self):
        cfg = SecurityHeadersConfig()
        with pytest.raises(AttributeError):
            cfg.hsts_max_age = 0  # type: ignore[misc]
