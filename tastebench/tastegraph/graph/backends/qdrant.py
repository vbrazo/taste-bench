"""Qdrant vector backend (Item 2; needs 'vectordb' extra).

Stores vectors in a Qdrant collection with cosine distance. Point ids are a deterministic
hash of the asset id (Qdrant needs int/UUID ids); the original asset id is kept in the
payload and in a local id map so ``vector``/``score_ids`` can resolve it.

Use ``location=":memory:"`` (the default) for a dependency-only, service-free instance —
ideal for tests and local dev; pass ``url=`` for a real server.
"""

from __future__ import annotations

import hashlib
from typing import Optional


def _require_qdrant():
    try:
        import qdrant_client  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "The Qdrant backend requires the 'vectordb' extra: pip install 'tastebench[vectordb]'"
        ) from exc


def _point_id(asset_id: str) -> int:
    return int.from_bytes(hashlib.sha256(asset_id.encode("utf-8")).digest()[:8], "big")


class QdrantBackend:
    def __init__(
        self,
        collection: str = "tastegraph",
        *,
        dim: Optional[int] = None,
        location: str = ":memory:",
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        _require_qdrant()
        from qdrant_client import QdrantClient

        self.collection = collection
        self._dim = dim
        self._client = QdrantClient(url=url, api_key=api_key) if url else QdrantClient(location=location)
        self._ids: dict[str, int] = {}  # asset_id -> point id
        self._vectors: dict[str, list] = {}  # local cache for vector()/exclusion
        if dim is not None:
            self._ensure_collection(dim)

    def _ensure_collection(self, dim: int) -> None:
        from qdrant_client import models

        self._dim = dim
        existing = {c.name for c in self._client.get_collections().collections}
        if self.collection not in existing:
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )

    # ---- building ----------------------------------------------------------

    def add(self, asset_id: str, vector) -> None:
        from qdrant_client import models

        vec = [float(x) for x in vector]
        if self._dim is None:
            self._ensure_collection(len(vec))
        pid = _point_id(asset_id)
        self._ids[asset_id] = pid
        self._vectors[asset_id] = vec
        self._client.upsert(
            collection_name=self.collection,
            points=[models.PointStruct(id=pid, vector=vec, payload={"asset_id": asset_id})],
        )

    def remove(self, asset_id: str) -> bool:
        if asset_id not in self._ids:
            return False
        pid = self._ids.pop(asset_id)
        self._vectors.pop(asset_id, None)
        self._client.delete(collection_name=self.collection, points_selector=[pid])
        return True

    def __contains__(self, asset_id: str) -> bool:
        return asset_id in self._ids

    def __len__(self) -> int:
        return len(self._ids)

    def vector(self, asset_id: str):
        return self._vectors[asset_id]

    # ---- queries -----------------------------------------------------------

    def knn(self, query, k: int = 10, exclude: Optional[set] = None) -> list[tuple[str, float]]:
        exclude = exclude or set()
        hits = self._client.search(
            collection_name=self.collection,
            query_vector=[float(x) for x in query],
            limit=k + len(exclude),
            with_payload=True,
        )
        out: list[tuple[str, float]] = []
        for h in hits:
            aid = h.payload["asset_id"]
            if aid in exclude:
                continue
            out.append((aid, float(h.score)))
            if len(out) >= k:
                break
        return out

    def score_ids(self, query, asset_ids: list[str]) -> dict[str, float]:
        import numpy as np

        q = np.asarray(query, dtype=float)
        qn = np.linalg.norm(q) or 1.0
        out: dict[str, float] = {}
        for aid in asset_ids:
            if aid not in self._vectors:
                continue
            v = np.asarray(self._vectors[aid], dtype=float)
            vn = np.linalg.norm(v) or 1.0
            out[aid] = float(v @ q / (vn * qn))
        return out

    def save(self, path) -> None:  # pragma: no cover - server persists itself
        # Qdrant persists on its own; nothing to do for the in-memory instance.
        pass
