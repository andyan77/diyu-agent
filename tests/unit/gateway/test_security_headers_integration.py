# ruff: noqa: S106  -- test fixtures require hardcoded secret values
"""Security headers integration test with app factory.

Task card: OS1-5
- HSTS header present on healthz response
- CSP header present
- X-Content-Type-Options present
- CORS middleware configured when origins provided

Acceptance: curl -I localhost:8000/healthz (includes all security headers)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.gateway.app import create_app


@pytest.fixture()
def client():
    app = create_app(
        jwt_secret="test-secret-key-minimum-length-32-chars!",
        cors_origins=["https://example.com"],
    )
    return TestClient(app)


class TestSecurityHeadersOnResponse:
    """Verify security headers are injected into actual HTTP responses."""

    def test_healthz_has_hsts(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert "Strict-Transport-Security" in resp.headers

    def test_healthz_has_csp(self, client):
        resp = client.get("/healthz")
        assert "Content-Security-Policy" in resp.headers

    def test_healthz_has_content_type_options(self, client):
        resp = client.get("/healthz")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_healthz_has_frame_options(self, client):
        resp = client.get("/healthz")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_healthz_has_xss_protection(self, client):
        resp = client.get("/healthz")
        assert resp.headers.get("X-XSS-Protection") == "0"

    def test_healthz_has_referrer_policy(self, client):
        resp = client.get("/healthz")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_healthz_has_permissions_policy(self, client):
        resp = client.get("/healthz")
        assert "Permissions-Policy" in resp.headers

    def test_401_response_has_security_headers(self, client):
        """Even error responses must include security headers."""
        resp = client.get("/api/v1/me")
        assert resp.status_code == 401
        assert "Strict-Transport-Security" in resp.headers
        assert "Content-Security-Policy" in resp.headers
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_all_seven_security_headers_present(self, client):
        resp = client.get("/healthz")
        expected = [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
        ]
        for header in expected:
            assert header in resp.headers, f"Missing security header: {header}"


class TestCORSIntegration:
    """CORS middleware is active when origins are configured."""

    def test_cors_preflight_allowed_origin(self, client):
        resp = client.options(
            "/api/v1/me",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "https://example.com"

    def test_cors_disallowed_origin(self, client):
        resp = client.options(
            "/api/v1/me",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in resp.headers

    def test_no_cors_when_no_origins(self):
        app = create_app(
            jwt_secret="test-secret-key-minimum-length-32-chars!",
        )
        c = TestClient(app)
        resp = c.options(
            "/api/v1/me",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in resp.headers
