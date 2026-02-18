"""Shared Fake adapters for testing without unittest.mock.

All Fake implementations follow the Port DI adapter pattern:
real Python classes with preset return values, no AsyncMock/MagicMock.
"""

from tests.fakes.session import (
    FakeAsyncSession,
    FakeOrmRow,
    FakeResult,
    FakeScalarsResult,
    FakeSessionFactory,
)

__all__ = [
    "FakeAsyncSession",
    "FakeOrmRow",
    "FakeResult",
    "FakeScalarsResult",
    "FakeSessionFactory",
]
