"""Tests for 3-step file upload protocol (G2-6).

Acceptance: pytest tests/unit/gateway/test_upload.py -v
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.gateway.api.upload import _reset_uploads, create_upload_router
from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token

_JWT_SECRET = "test-secret-for-g2-6"  # noqa: S105


@pytest.fixture(autouse=True)
def _clean_uploads():
    _reset_uploads()
    yield
    _reset_uploads()


@pytest.fixture()
def test_user():
    return {"user_id": uuid4(), "org_id": uuid4()}


@pytest.fixture()
def auth_headers(test_user):
    token = encode_token(
        user_id=test_user["user_id"],
        org_id=test_user["org_id"],
        secret=_JWT_SECRET,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def client():
    app = create_app(jwt_secret=_JWT_SECRET)
    app.include_router(create_upload_router())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestUploadInit:
    """Step 1: POST /api/v1/uploads/init"""

    @pytest.mark.asyncio
    async def test_init_success(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "file_size": 1024,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "upload_id" in data
        UUID(data["upload_id"])  # valid UUID
        assert "upload_url" in data
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_invalid_mime_type(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "virus.exe",
                "content_type": "application/x-executable",
                "file_size": 1024,
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_file_too_large(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "huge.pdf",
                "content_type": "application/pdf",
                "file_size": 100 * 1024 * 1024,  # 100MB
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "../../../etc/passwd",
                "content_type": "text/plain",
                "file_size": 100,
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_filename_rejected(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "",
                "content_type": "text/plain",
                "file_size": 100,
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/uploads/init",
            json={
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "file_size": 1024,
            },
        )
        assert resp.status_code == 401


class TestUploadComplete:
    """Step 3: POST /api/v1/uploads/{id}/complete"""

    @pytest.mark.asyncio
    async def test_complete_success(self, client: AsyncClient, auth_headers):
        # Step 1: init
        init_resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "data.csv",
                "content_type": "text/csv",
                "file_size": 512,
            },
        )
        upload_id = init_resp.json()["upload_id"]

        # Step 3: complete
        resp = await client.post(
            f"/api/v1/uploads/{upload_id}/complete",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["filename"] == "data.csv"

    @pytest.mark.asyncio
    async def test_complete_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            f"/api/v1/uploads/{uuid4()}/complete",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_double_complete_returns_409(self, client: AsyncClient, auth_headers):
        init_resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "data.csv",
                "content_type": "text/csv",
                "file_size": 512,
            },
        )
        uid = init_resp.json()["upload_id"]

        await client.post(f"/api/v1/uploads/{uid}/complete", headers=auth_headers, json={})
        resp = await client.post(
            f"/api/v1/uploads/{uid}/complete",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 409


class TestUploadStatus:
    """GET /api/v1/uploads/{id}"""

    @pytest.mark.asyncio
    async def test_status_pending(self, client: AsyncClient, auth_headers):
        init_resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "doc.pdf",
                "content_type": "application/pdf",
                "file_size": 2048,
            },
        )
        uid = init_resp.json()["upload_id"]

        resp = await client.get(f"/api/v1/uploads/{uid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_status_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get(f"/api/v1/uploads/{uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_org_isolation(self, client: AsyncClient, auth_headers):
        """Upload from org A should not be visible to org B."""
        # Create upload with org A
        init_resp = await client.post(
            "/api/v1/uploads/init",
            headers=auth_headers,
            json={
                "filename": "secret.pdf",
                "content_type": "application/pdf",
                "file_size": 1024,
            },
        )
        uid = init_resp.json()["upload_id"]

        # Try to access with org B
        other_token = encode_token(
            user_id=uuid4(),
            org_id=uuid4(),
            secret=_JWT_SECRET,
        )
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.get(f"/api/v1/uploads/{uid}", headers=other_headers)
        assert resp.status_code == 404
