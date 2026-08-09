"""In-memory cosine k-NN backend (Item 2).

The original numpy index, unchanged in behaviour — a numpy matrix plus an id map,
persisted to ``.npz``. Default backend; no external services.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]


class MemoryBackend:
    def __init__(self):
        self._ids: list[str] = []
        self._pos: dict[str, int] = {}
        self._matrix = None  # lazily-built numpy array (n, d)
        self._vectors: list = []
        self._dirty = False

    # ---- building ----------------------------------------------------------

    def add(self, asset_id: str, vector) -> None:
        import numpy as np

        vec = np.asarray(vector, dtype=float)
        if asset_id in self._pos:
            self._vectors[self._pos[asset_id]] = vec
        else:
            self._pos[asset_id] = len(self._ids)
            self._ids.append(asset_id)
            self._vectors.append(vec)
        self._dirty = True

    def remove(self, asset_id: str) -> bool:
        """Delete a vector and compact the id map. Idempotent; returns whether it existed."""
        pos = self._pos.get(asset_id)
        if pos is None:
            return False
        del self._ids[pos]
        del self._vectors[pos]
        # reindex positions for everything after the removed slot
        self._pos = {aid: i for i, aid in enumerate(self._ids)}
        self._dirty = True  # matrix rebuilds from surviving vectors (compaction)
        return True

    def _build(self):
        import numpy as np

        if self._dirty or self._matrix is None:
            self._matrix = np.vstack(self._vectors) if self._vectors else np.zeros((0, 0))
            self._dirty = False
        return self._matrix

    def __len__(self) -> int:
        return len(self._ids)

    def __contains__(self, asset_id: str) -> bool:
        return asset_id in self._pos

    def vector(self, asset_id: str):
        return self._vectors[self._pos[asset_id]]

    # ---- queries -----------------------------------------------------------

    def _cosine_scores(self, query):
        import numpy as np

        m = self._build()
        if m.shape[0] == 0:
            return np.zeros(0)
        q = np.asarray(query, dtype=float)
        qn = np.linalg.norm(q)
        mn = np.linalg.norm(m, axis=1)
        denom = mn * (qn if qn else 1.0)
        denom[denom == 0] = 1.0
        return (m @ q) / denom

    def knn(self, query, k: int = 10, exclude: Optional[set] = None) -> list[tuple[str, float]]:
        import numpy as np

        scores = self._cosine_scores(query)
        if scores.size == 0:
            return []
        order = np.argsort(-scores)
        exclude = exclude or set()
        out: list[tuple[str, float]] = []
        for i in order:
            aid = self._ids[i]
            if aid in exclude:
                continue
            out.append((aid, float(scores[i])))
            if len(out) >= k:
                break
        return out

    def score_ids(self, query, asset_ids: list[str]) -> dict[str, float]:
        """Cosine score of the query against a specific subset of ids."""
        scores = self._cosine_scores(query)
        return {aid: float(scores[self._pos[aid]]) for aid in asset_ids if aid in self._pos}

    # ---- persistence -------------------------------------------------------

    def save(self, path: PathLike) -> None:
        import numpy as np

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, ids=np.array(self._ids, dtype=object), matrix=self._build())

    @classmethod
    def load(cls, path: PathLike) -> "MemoryBackend":
        import numpy as np

        data = np.load(path, allow_pickle=True)
        idx = cls()
        for aid, vec in zip(list(data["ids"]), data["matrix"]):
            idx.add(str(aid), vec)
        return idx
