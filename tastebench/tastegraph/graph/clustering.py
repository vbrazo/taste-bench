"""Server-side asset clustering into taste regions (Item 1; needs 'embeddings' extra).

Higher-quality than the client's k-means-lite: picks k by silhouette (reusing the approach
in evaluation.clustering), tries agglomerative/HDBSCAN when available, and labels each region
by **distinctive** tags (TF-IDF-ish salience) so a region's name is what sets it apart from
the catalog, not the globally most common tag.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass


@dataclass
class AssetRegion:
    id: str
    label: str
    member_ids: list[str]
    centroid: list[float]

    @property
    def size(self) -> int:
        return len(self.member_ids)

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "memberIds": self.member_ids, "centroid": self.centroid}


def _require_sklearn():
    try:
        import sklearn  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Server clustering requires the 'embeddings' extra: pip install 'tastebench[embeddings]'"
        ) from exc


import re as _re

_HEX = _re.compile(r"^#?[0-9a-fA-F]{6}$")


def _is_hex(tag: str) -> bool:
    return bool(_HEX.match(tag.strip()))


def _titlecase(tag: str) -> str:
    return " ".join(w.capitalize() for w in tag.replace("#", " ").replace("_", " ").split())


def _distinctive_labels(member_tags: list[list[str]], global_df: Counter, n_docs: int, top: int = 2) -> str:
    """Label from tags most salient to this cluster vs the whole catalog (tf * idf)."""
    tf: Counter = Counter()
    for tags in member_tags:
        tf.update(t for t in set(tags) if not _is_hex(t))
    scored = []
    for tag, freq in tf.items():
        idf = math.log((1 + n_docs) / (1 + global_df.get(tag, 0))) + 1
        scored.append((freq * idf, tag))
    scored.sort(reverse=True)
    labels = [_titlecase(t) for _, t in scored[:top] if t]
    return " ".join(labels) or "Region"


def _choose_k(vectors) -> int:
    import numpy as np  # noqa: F401
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    n = len(vectors)
    if n < 3:
        return 1
    best_k, best_score = 2, -1.0
    for cand in range(2, min(8, n - 1) + 1):
        labels = KMeans(n_clusters=cand, n_init=10, random_state=0).fit_predict(vectors)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(vectors, labels)
        if score > best_score:
            best_k, best_score = cand, score
    return best_k


def cluster_assets(vectors: list[list[float]], ids: list[str], tags: list[list[str]], k=None) -> list[AssetRegion]:
    """Cluster asset vectors into labeled regions."""
    _require_sklearn()
    import numpy as np

    if len(ids) == 0:
        return []
    if len(ids) == 1:
        return [AssetRegion("region_0", _titlecase(tags[0][0]) if tags[0] else "Region", [ids[0]], list(vectors[0]))]

    X = np.asarray(vectors, dtype=float)
    kk = k or _choose_k(X)
    kk = max(1, min(kk, len(ids)))

    labels = _fit_labels(X, kk)

    global_df: Counter = Counter()
    for t in tags:
        global_df.update(set(t))
    n_docs = len(ids)

    regions: list[AssetRegion] = []
    for cid in sorted(set(labels)):
        idxs = [i for i, l in enumerate(labels) if l == cid]
        if not idxs:
            continue
        centroid = X[idxs].mean(axis=0)
        regions.append(
            AssetRegion(
                id=f"region_{cid}",
                label=_distinctive_labels([tags[i] for i in idxs], global_df, n_docs),
                member_ids=[ids[i] for i in idxs],
                centroid=[float(x) for x in centroid],
            )
        )
    regions.sort(key=lambda r: r.size, reverse=True)
    return regions


def _fit_labels(X, k: int):
    """Prefer agglomerative (cosine) for compact regions; fall back to KMeans."""
    try:
        from sklearn.cluster import AgglomerativeClustering

        return AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average").fit_predict(X)
    except (ImportError, ValueError, TypeError):  # pragma: no cover - version fallbacks
        from sklearn.cluster import KMeans

        return KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(X)
