"""G3-2: Skill API tests.

Tests: list skills, get skill detail, execute skill, error handling.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.gateway.api.skills import create_skill_router
from src.ports.skill_registry import SkillDefinition, SkillStatus
from src.skill.implementations.content_writer import ContentWriterSkill
from src.skill.registry.lifecycle import LifecycleRegistry

ORG_ID = UUID(int=100)
USER_ID = UUID(int=200)


def _inject_auth(app: FastAPI) -> None:
    from starlette.middleware.base import BaseHTTPMiddleware

    class FakeAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.org_id = ORG_ID
            request.state.user_id = USER_ID
            return await call_next(request)

    app.add_middleware(FakeAuthMiddleware)


@pytest.fixture
async def registry() -> LifecycleRegistry:
    reg = LifecycleRegistry()
    defn = SkillDefinition(
        skill_id="content_writer",
        name="Content Writer",
        description="Generate marketing content",
        intent_types=["generate_content"],
    )
    await reg.register(defn)
    await reg.update_status("content_writer", SkillStatus.ACTIVE)
    reg.bind_implementation("content_writer", ContentWriterSkill())
    return reg


@pytest.fixture
def client(registry: LifecycleRegistry) -> TestClient:
    app = FastAPI()
    _inject_auth(app)
    router = create_skill_router(registry=registry)
    app.include_router(router)
    return TestClient(app)


class TestListSkills:
    def test_list_returns_skills(self, client: TestClient) -> None:
        """Task card: skill list is non-empty."""
        resp = client.get("/api/v1/skills/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["skills"][0]["skill_id"] == "content_writer"

    def test_list_filter_by_status(self, client: TestClient) -> None:
        resp = client.get("/api/v1/skills/?status=active")
        assert resp.status_code == 200
        data = resp.json()
        assert all(s["status"] == "active" for s in data["skills"])

    def test_invalid_status_filter(self, client: TestClient) -> None:
        resp = client.get("/api/v1/skills/?status=invalid")
        assert resp.status_code == 400


class TestGetSkill:
    def test_get_existing_skill(self, client: TestClient) -> None:
        resp = client.get("/api/v1/skills/content_writer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_id"] == "content_writer"
        assert data["name"] == "Content Writer"

    def test_get_nonexistent_skill(self, client: TestClient) -> None:
        resp = client.get("/api/v1/skills/nonexistent")
        assert resp.status_code == 404


class TestExecuteSkill:
    def test_execute_success(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/skills/content_writer/execute",
            json={"params": {"topic": "summer sale", "platform": "xiaohongshu"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["skill_id"] == "content_writer"

    def test_execute_nonexistent_skill(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/skills/nonexistent/execute",
            json={"params": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
