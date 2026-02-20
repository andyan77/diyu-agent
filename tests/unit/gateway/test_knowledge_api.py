"""G3-1: Knowledge Admin API tests.

Tests: CRUD operations, RBAC context, validation, error handling.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.gateway.api.admin.knowledge import create_knowledge_admin_router


class FakeKnowledgeWriter:
    """Fake knowledge writer for testing (no mock/patch)."""

    def __init__(self) -> None:
        self._store: dict[UUID, dict[str, Any]] = {}

    async def create_entry(
        self,
        *,
        org_id: UUID,
        entity_type: str,
        properties: dict[str, Any],
        user_id: UUID,
    ) -> dict[str, Any]:
        entry_id = uuid4()
        entry = {
            "entry_id": entry_id,
            "org_id": org_id,
            "entity_type": entity_type,
            "properties": properties,
            "created_by": user_id,
        }
        self._store[entry_id] = entry
        return entry

    async def get_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
    ) -> dict[str, Any] | None:
        entry = self._store.get(entry_id)
        if entry and entry["org_id"] == org_id:
            return entry
        return None

    async def update_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
        properties: dict[str, Any],
        user_id: UUID,
    ) -> dict[str, Any]:
        entry = self._store.get(entry_id)
        if entry is None:
            return {"entry_id": entry_id, "properties": properties}
        entry["properties"] = properties
        return entry

    async def delete_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
        user_id: UUID,
    ) -> bool:
        if entry_id in self._store:
            del self._store[entry_id]
            return True
        return False

    async def list_entries(
        self,
        *,
        org_id: UUID,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        entries = [
            e
            for e in self._store.values()
            if e["org_id"] == org_id and (entity_type is None or e["entity_type"] == entity_type)
        ]
        return entries[offset : offset + limit]


ORG_ID = UUID(int=100)
USER_ID = UUID(int=200)


def _inject_auth(app: FastAPI) -> None:
    """Add middleware to inject org_id and user_id into request state."""

    from starlette.middleware.base import BaseHTTPMiddleware

    class FakeAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.org_id = ORG_ID
            request.state.user_id = USER_ID
            return await call_next(request)

    app.add_middleware(FakeAuthMiddleware)


@pytest.fixture
def client() -> TestClient:
    writer = FakeKnowledgeWriter()
    app = FastAPI()
    _inject_auth(app)
    router = create_knowledge_admin_router(knowledge_writer=writer)
    app.include_router(router)
    return TestClient(app)


class TestCreateEntry:
    def test_create_returns_201(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/admin/knowledge/",
            json={"entity_type": "BrandKnowledge", "properties": {"name": "Test"}},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_type"] == "BrandKnowledge"
        assert data["org_id"] == str(ORG_ID)
        assert data["entry_id"]

    def test_empty_entity_type_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/admin/knowledge/",
            json={"entity_type": "", "properties": {}},
        )
        assert resp.status_code == 422


class TestListEntries:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/api/v1/admin/knowledge/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["entries"] == []

    def test_list_after_create(self, client: TestClient) -> None:
        client.post(
            "/api/v1/admin/knowledge/",
            json={"entity_type": "Product", "properties": {"sku": "SKU-1"}},
        )
        resp = client.get("/api/v1/admin/knowledge/")
        data = resp.json()
        assert data["total"] == 1


class TestGetEntry:
    def test_get_existing(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/admin/knowledge/",
            json={"entity_type": "Brand", "properties": {"name": "X"}},
        )
        entry_id = create_resp.json()["entry_id"]
        resp = client.get(f"/api/v1/admin/knowledge/{entry_id}")
        assert resp.status_code == 200
        assert resp.json()["entity_type"] == "Brand"

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        fake_id = str(uuid4())
        resp = client.get(f"/api/v1/admin/knowledge/{fake_id}")
        assert resp.status_code == 404


class TestUpdateEntry:
    def test_update_properties(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/admin/knowledge/",
            json={"entity_type": "Brand", "properties": {"name": "Old"}},
        )
        entry_id = create_resp.json()["entry_id"]
        resp = client.put(
            f"/api/v1/admin/knowledge/{entry_id}",
            json={"properties": {"name": "New"}},
        )
        assert resp.status_code == 200


class TestDeleteEntry:
    def test_delete_existing(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/admin/knowledge/",
            json={"entity_type": "Brand", "properties": {"name": "Delete Me"}},
        )
        entry_id = create_resp.json()["entry_id"]
        resp = client.delete(f"/api/v1/admin/knowledge/{entry_id}")
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        fake_id = str(uuid4())
        resp = client.delete(f"/api/v1/admin/knowledge/{fake_id}")
        assert resp.status_code == 404
