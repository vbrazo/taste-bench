"""Joint embedding of an asset fingerprint into one vector (Layer 3).

Combines the VLM ``advanced.embedding`` (semantic content) with a small deterministic
encoding of categorical aesthetic/emotional attributes (style, mood, trend, palette), so
two assets that are semantically similar *and* share a look land near each other. Pure
numpy; the semantic part can come from a real embedder or the mock one.
"""

from __future__ import annotations

import hashlib

from ..assets.schema import AssetFingerprint

_ATTR_DIM = 16  # size of the categorical attribute block


def _hash_unit(text: str, dim: int):
    """Deterministic unit-norm vector for a categorical token."""
    import numpy as np

    if not text:
        return np.zeros(dim)
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vals = np.array([digest[i % len(digest)] for i in range(dim)], dtype=float)
    vals = vals / 255.0 * 2 - 1
    norm = np.linalg.norm(vals)
    return vals / norm if norm else vals


def encode_attributes(fp: AssetFingerprint):
    """A small vector encoding the categorical taste attributes."""
    import numpy as np

    tokens = [
        fp.aesthetic.style,
        fp.emotional.mood,
        fp.contextual.trend,
        fp.aesthetic.composition,
        fp.aesthetic.silhouette,
        fp.aesthetic.texture,
        fp.contextual.season,
        fp.contextual.setting,
        *fp.aesthetic.palette,
        *fp.semantic.topics[:2],
    ]
    vec = np.zeros(_ATTR_DIM)
    for t in tokens:
        vec = vec + _hash_unit(t, _ATTR_DIM)
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def joint_embedding(fp: AssetFingerprint, attr_weight: float = 0.5):
    """Concatenate a normalized semantic block and attribute block into one vector."""
    import numpy as np

    sem = np.asarray(fp.advanced.embedding, dtype=float)
    if sem.size:
        n = np.linalg.norm(sem)
        sem = sem / n if n else sem
    attr = encode_attributes(fp) * attr_weight
    vec = np.concatenate([sem, attr]) if sem.size else attr
    n = np.linalg.norm(vec)
    return vec / n if n else vec


class MockEmbedder:
    """Seeded deterministic text embedder (stand-in for sentence-transformers)."""

    def __init__(self, dim: int = 32):
        self.dim = dim

    def __call__(self, texts):
        import numpy as np

        out = []
        for t in texts:
            digest = hashlib.sha256(t.encode("utf-8")).digest()
            vals = np.array([digest[i % len(digest)] for i in range(self.dim)], dtype=float)
            vals = vals / 255.0 * 2 - 1
            n = np.linalg.norm(vals)
            out.append(vals / n if n else vals)
        return np.asarray(out)
