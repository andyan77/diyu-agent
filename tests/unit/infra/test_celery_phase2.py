"""Unit tests for Celery task manager (I2-2) -- phase2.

Uses InMemoryTaskExecutor stub. No external dependencies.
Complies with no-mock policy.
"""

from __future__ import annotations

import pytest

from src.infra.tasks.celery_app import (
    CeleryTaskManager,
    InMemoryTaskExecutor,
    TaskResult,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def executor() -> InMemoryTaskExecutor:
    ex = InMemoryTaskExecutor()
    ex.register("add", lambda a, b: a + b)
    ex.register("greet", lambda name: f"hello {name}")
    ex.register("fail_task", _always_fail)
    return ex


@pytest.fixture()
def manager(executor: InMemoryTaskExecutor) -> CeleryTaskManager:
    return CeleryTaskManager(executor)


def _always_fail() -> None:
    msg = "intentional failure"
    raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCeleryTaskManagerPhase2:
    """CeleryTaskManager unit tests (phase2)."""

    def test_register_and_execute_task(
        self,
        manager: CeleryTaskManager,
        executor: InMemoryTaskExecutor,
    ) -> None:
        task_id = manager.submit("add", args=(2, 3))
        result = manager.get_status(task_id)
        assert result is not None
        assert result.status == TaskStatus.SUCCESS
        assert result.result == 5

    def test_execute_with_kwargs(
        self,
        manager: CeleryTaskManager,
    ) -> None:
        task_id = manager.submit("greet", kwargs={"name": "world"})
        result = manager.get_status(task_id)
        assert result is not None
        assert result.status == TaskStatus.SUCCESS
        assert result.result == "hello world"

    def test_unknown_task_returns_failure(
        self,
        manager: CeleryTaskManager,
    ) -> None:
        task_id = manager.submit("nonexistent")
        result = manager.get_status(task_id)
        assert result is not None
        assert result.status == TaskStatus.FAILURE
        assert "Unknown task" in (result.error or "")

    def test_failed_task_has_error_message(
        self,
        manager: CeleryTaskManager,
    ) -> None:
        task_id = manager.submit("fail_task")
        result = manager.get_status(task_id)
        assert result is not None
        assert result.status == TaskStatus.FAILURE
        assert result.error == "intentional failure"

    def test_retry_failed_task(
        self,
        manager: CeleryTaskManager,
        executor: InMemoryTaskExecutor,
    ) -> None:
        """Retry a failed task, which re-submits with incremented retry_count."""
        task_id = manager.submit("fail_task")
        result = manager.get_status(task_id)
        assert result is not None
        assert result.status == TaskStatus.FAILURE

        manager.configure_retries("fail_task", max_retries=3)
        new_id = manager.retry(task_id)
        assert new_id is not None

        new_result = manager.get_status(new_id)
        assert new_result is not None
        assert new_result.retry_count == 1

    def test_retry_exhausted_returns_none(
        self,
        manager: CeleryTaskManager,
    ) -> None:
        """After max retries, retry returns None."""
        manager.configure_retries("fail_task", max_retries=0)
        task_id = manager.submit("fail_task")
        assert manager.retry(task_id) is None

    def test_retry_non_failed_task_returns_none(
        self,
        manager: CeleryTaskManager,
    ) -> None:
        task_id = manager.submit("add", args=(1, 1))
        assert manager.retry(task_id) is None

    def test_get_status_unknown_id_returns_none(
        self,
        manager: CeleryTaskManager,
    ) -> None:
        from uuid import uuid4

        assert manager.get_status(uuid4()) is None

    def test_success_callback_invoked(
        self,
        executor: InMemoryTaskExecutor,
    ) -> None:
        results_collected: list[TaskResult] = []
        executor.on_success("add", results_collected.append)

        manager = CeleryTaskManager(executor)
        manager.submit("add", args=(10, 20))

        assert len(results_collected) == 1
        assert results_collected[0].result == 30

    def test_completed_at_set_on_success(
        self,
        manager: CeleryTaskManager,
    ) -> None:
        task_id = manager.submit("add", args=(1, 2))
        result = manager.get_status(task_id)
        assert result is not None
        assert result.completed_at is not None

    def test_completed_at_set_on_failure(
        self,
        manager: CeleryTaskManager,
    ) -> None:
        task_id = manager.submit("fail_task")
        result = manager.get_status(task_id)
        assert result is not None
        assert result.completed_at is not None
