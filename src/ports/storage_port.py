"""StoragePort - Generic persistence interface.

Soft dependency. Abstracts key-value and relational storage.
Day-1 implementation: In-memory Map or SQLite.
Real implementation: PostgreSQL + Redis.

Note: MemoryCorePort's PG adapter delegates to StoragePort internally.
      StoragePort is unaware of MemoryCorePort (no reverse dependency).

See: docs/architecture/00-*.md Section 12.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StoragePort(ABC):
    """Port: Generic persistence read/write."""

    @abstractmethod
    async def put(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Store a value with optional TTL.

        Args:
            key: Storage key.
            value: Value to store (must be serializable).
            ttl: Time-to-live in seconds (None = no expiry).
        """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieve a value by key.

        Args:
            key: Storage key.

        Returns:
            Stored value or None if not found.
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value by key.

        Args:
            key: Storage key.
        """

    @abstractmethod
    async def list_keys(self, pattern: str) -> list[str]:
        """List keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*:sessions").

        Returns:
            List of matching keys.
        """
