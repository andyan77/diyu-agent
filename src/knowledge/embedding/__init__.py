"""Knowledge embedding adapters.

Provides a pluggable EmbeddingAdapter protocol and a deterministic
dummy implementation for CI/testing.  The real LLM-backed adapter
can be swapped in later without touching any call-sites.

Decision ref: Audit R2 -- Decision 1 (B: deterministic dummy).
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol


class EmbeddingAdapter(Protocol):
    """Protocol for text -> vector embedding."""

    def embed(self, text: str) -> list[float]:
        """Return a dense vector for *text*."""
        ...


class DeterministicEmbedder:
    """Hash-based deterministic embedder for CI/testing.

    Produces a normalized 1536-dim vector derived from the SHA-256
    digest of the input text.  Same text always yields the same vector.
    NOT suitable for semantic search -- use only as a structural
    placeholder until a real embedding model is wired (Decision 1-A).
    """

    def __init__(self, dim: int = 1536) -> None:
        self._dim = dim

    def embed(self, text: str) -> list[float]:
        """Generate a deterministic embedding from *text*."""
        digest = hashlib.sha256(text.encode()).digest()
        # Expand 32 bytes into `dim` floats using sin-hash mixing
        raw: list[float] = []
        for i in range(self._dim):
            byte_val = digest[i % len(digest)]
            raw.append((math.sin(byte_val * 0.1 + i * 0.01) + 1.0) / 2.0)
        norm = math.sqrt(sum(x * x for x in raw))
        if norm == 0:
            return [0.0] * self._dim
        return [x / norm for x in raw]


__all__ = ["DeterministicEmbedder", "EmbeddingAdapter"]
