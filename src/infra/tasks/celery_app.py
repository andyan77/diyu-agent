"""Celery-based async task manager.

Task card: I2-2
- Send async task -> Worker executes -> Result written back
- Task retry with exponential backoff
- Result persistence for status queries

Architecture: 06 Section 2 (Celery + Redis Broker)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4


class TaskStatus(enum.Enum):
    """Task lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"


@dataclass
class TaskResult:
    """Result of an async task execution."""

    task_id: UUID
    task_name: str
    status: TaskStatus
    result: Any = None
    error: str | None = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class TaskExecutor(Protocol):
    """Protocol for task execution backends.

    Production: Celery worker
    Testing: In-memory executor
    """

    def send_task(
        self,
        task_name: str,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> UUID:
        """Submit a task for async execution. Returns task ID."""
        ...

    def get_result(self, task_id: UUID) -> TaskResult | None:
        """Retrieve result for a given task ID."""
        ...


class InMemoryTaskExecutor:
    """In-memory task executor for unit testing.

    Executes tasks synchronously and stores results.
    No external dependencies required.
    """

    def __init__(self) -> None:
        self._registry: dict[str, Any] = {}
        self._results: dict[UUID, TaskResult] = {}
        self._callbacks: dict[str, list[Any]] = {}

    def register(self, task_name: str, func: Any) -> None:
        """Register a task handler function."""
        self._registry[task_name] = func

    def on_success(self, task_name: str, callback: Any) -> None:
        """Register a success callback for a task."""
        self._callbacks.setdefault(task_name, []).append(callback)

    def send_task(
        self,
        task_name: str,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> UUID:
        """Execute task synchronously (in-memory) and store result."""
        task_id = uuid4()
        func = self._registry.get(task_name)

        if func is None:
            self._results[task_id] = TaskResult(
                task_id=task_id,
                task_name=task_name,
                status=TaskStatus.FAILURE,
                error=f"Unknown task: {task_name}",
            )
            return task_id

        result = TaskResult(
            task_id=task_id,
            task_name=task_name,
            status=TaskStatus.RUNNING,
        )
        self._results[task_id] = result

        try:
            output = func(*(args or ()), **(kwargs or {}))
            result.status = TaskStatus.SUCCESS
            result.result = output
            result.completed_at = datetime.now(UTC)

            for cb in self._callbacks.get(task_name, []):
                cb(result)

        except Exception as exc:
            result.status = TaskStatus.FAILURE
            result.error = str(exc)
            result.completed_at = datetime.now(UTC)

        return task_id

    def get_result(self, task_id: UUID) -> TaskResult | None:
        """Retrieve result by task ID."""
        return self._results.get(task_id)


class CeleryTaskManager:
    """High-level task management facade.

    Wraps a TaskExecutor (real Celery or in-memory stub) to provide
    task submission, retry, and result retrieval.
    """

    def __init__(self, executor: TaskExecutor) -> None:
        self._executor = executor
        self._max_retries: dict[str, int] = {}

    def configure_retries(self, task_name: str, max_retries: int) -> None:
        """Set max retry count for a task type."""
        self._max_retries[task_name] = max_retries

    def submit(
        self,
        task_name: str,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> UUID:
        """Submit a task for execution."""
        return self._executor.send_task(task_name, args=args, kwargs=kwargs)

    def get_status(self, task_id: UUID) -> TaskResult | None:
        """Get current status/result of a task."""
        return self._executor.get_result(task_id)

    def retry(self, task_id: UUID) -> UUID | None:
        """Retry a failed task if retries remain.

        Returns new task ID on success, None if retries exhausted.
        """
        original = self._executor.get_result(task_id)
        if original is None or original.status != TaskStatus.FAILURE:
            return None

        max_r = self._max_retries.get(original.task_name, 3)
        if original.retry_count >= max_r:
            return None

        new_id = self._executor.send_task(original.task_name)
        new_result = self._executor.get_result(new_id)
        if new_result is not None:
            new_result.retry_count = original.retry_count + 1
        return new_id
