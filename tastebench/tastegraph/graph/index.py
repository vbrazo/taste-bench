"""Backward-compatible alias for the default vector backend (Item 2).

``TasteGraphIndex`` was the original in-memory numpy k-NN index. It now lives in
``graph/backends/memory.py`` as ``MemoryBackend``; this name is kept as a thin alias so
existing imports/tests keep working.
"""

from __future__ import annotations

from .backends.memory import MemoryBackend as TasteGraphIndex

__all__ = ["TasteGraphIndex"]
