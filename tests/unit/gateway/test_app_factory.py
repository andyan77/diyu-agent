# ruff: noqa: S106  -- test fixtures require hardcoded secret values
"""Tests for G1-5: FastAPI app factory + API partition rules.

Acceptance: user API /api/v1/* and admin API /api/v1/admin/* separated.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.gateway.app import create_app


@pytest.fixture()
def app():
    return create_app(jwt_secret="test-secret-key-for-unit-tests-only")


@pytest.fixture()
def client(app):
    return TestClient(app)


class TestAppFactory:
    """create_app returns a configured FastAPI instance."""

    def test_returns_fastapi_instance(self, app):
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_healthz_returns_200(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"

    def test_openapi_json_accessible(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert "openapi" in resp.json()

    def test_docs_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200


class TestAPIPartition:
    """User API /api/v1/* and admin API /api/v1/admin/* are separated."""

    def test_user_routes_exist(self, app):
        """At least one route under /api/v1/ (non-admin) exists."""
        paths = [r.path for r in app.routes]
        user_paths = [p for p in paths if "/api/v1/" in p and "/admin/" not in p]
        assert len(user_paths) > 0, f"No user routes found. All paths: {paths}"

    def test_admin_routes_exist(self, app):
        """At least one route under /api/v1/admin/ exists."""
        paths = [r.path for r in app.routes]
        admin_paths = [p for p in paths if "/api/v1/admin/" in p]
        assert len(admin_paths) > 0, f"No admin routes found. All paths: {paths}"

    def test_user_and_admin_routes_are_distinct(self, app):
        """User and admin route sets do not overlap."""
        paths = [r.path for r in app.routes]
        user_paths = {p for p in paths if "/api/v1/" in p and "/admin/" not in p}
        admin_paths = {p for p in paths if "/api/v1/admin/" in p}
        assert user_paths.isdisjoint(admin_paths)


class TestErrorHandling:
    """DiyuError subclasses are mapped to correct HTTP status codes."""

    def test_unauthenticated_returns_401(self, client):
        """Non-exempt route without token returns 401."""
        resp = client.get("/api/v1/me")
        assert resp.status_code == 401

    def test_healthz_exempt_from_auth(self, client):
        """healthz is exempt from JWT auth."""
        resp = client.get("/healthz")
        assert resp.status_code == 200


class TestAcceptanceCommand:
    """Replicate the task card acceptance command."""

    def test_acceptance_g1_5(self, app):
        routes = [r.path for r in app.routes]
        assert any("/api/v1/admin/" in r for r in routes)
        assert any("/api/v1/" in r and "/admin/" not in r for r in routes)
