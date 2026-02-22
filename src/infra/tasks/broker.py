"""Celery broker entry point for Docker worker container.

Task card: I2-2
Creates the actual Celery app instance that the `celery -A` CLI references.
The InMemoryTaskExecutor in celery_app.py is used for unit testing;
this module provides the real Redis-backed broker for production.
"""

from __future__ import annotations

import os

from celery import Celery

# Redis URL from environment (docker-compose injects REDIS_URL)
_broker_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_backend_url = os.environ.get("CELERY_RESULT_BACKEND", _broker_url)

app = Celery(
    "diyu",
    broker=_broker_url,
    backend=_backend_url,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks from the src.infra.tasks package
app.autodiscover_tasks(["src.infra.tasks"])
