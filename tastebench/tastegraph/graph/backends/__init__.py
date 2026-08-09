"""Pluggable vector backends for the taste graph (Item 2)."""

from __future__ import annotations

from .base import VectorBackend
from .memory import MemoryBackend

__all__ = ["VectorBackend", "MemoryBackend", "make_backend"]


def make_backend(kind: str = "memory", **cfg):
    """Factory: 'memory' (default) or 'qdrant'."""
    if kind == "memory":
        return MemoryBackend()
    if kind == "qdrant":
        from .qdrant import QdrantBackend

        return QdrantBackend(**cfg)
    raise ValueError(f"Unknown backend kind: {kind!r} (expected 'memory' or 'qdrant').")
