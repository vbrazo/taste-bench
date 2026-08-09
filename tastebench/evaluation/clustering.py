"""Semantic clustering of disagreement rationales (optional; ``tastebench[embeddings]``).

The keyword tagger in :mod:`disagreement` is the always-on, zero-dependency default.
This module is the opt-in upgrade: embed each disagreement's model rationale and group
them, surfacing systematic failure themes the fixed keyword buckets miss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .disagreement import Disagreement, _tag_rationale


@dataclass
class RationaleCluster:
    label: str
    example_ids: list[str]
    representative: str

    @property
    def size(self) -> int:
        return len(self.example_ids)


Embedder = Callable[[list[str]], "list"]  # list[str] -> array-like (n, d)


def _default_embedder(model_name: str = "all-MiniLM-L6-v2") -> Embedder:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Semantic clustering requires the 'embeddings' extra: "
            "pip install 'tastebench[embeddings]'"
        ) from exc
    model = SentenceTransformer(model_name)
    return lambda texts: model.encode(list(texts), normalize_embeddings=True)


def _label_from_members(members: list[Disagreement]) -> str:
    """Cheap label: most common keyword tag among members, else a snippet."""
    from collections import Counter

    tags: Counter = Counter()
    for d in members:
        tags.update(d.tags or _tag_rationale(d.model_rationale))
    if tags:
        return tags.most_common(1)[0][0]
    text = next((d.model_rationale for d in members if d.model_rationale), "") or "unlabeled"
    return text[:40]


def cluster_rationales(
    disagreements: list[Disagreement],
    *,
    k: Optional[int] = None,
    embedder: Optional[Embedder] = None,
    model_name: str = "all-MiniLM-L6-v2",
) -> list[RationaleCluster]:
    """Cluster disagreements by the semantics of their model rationale.

    ``k`` fixes the cluster count; when omitted, a small silhouette search picks it.
    Disagreements without a rationale are ignored.
    """
    import numpy as np
    from sklearn.cluster import KMeans

    items = [d for d in disagreements if d.model_rationale]
    if len(items) < 2:
        return [
            RationaleCluster(
                label=_label_from_members([d]),
                example_ids=[d.example_id],
                representative=d.model_rationale or "",
            )
            for d in items
        ]

    embed = embedder or _default_embedder(model_name)
    vectors = np.asarray(embed([d.model_rationale for d in items]))

    best_k = k or _choose_k(vectors)
    best_k = max(1, min(best_k, len(items)))
    labels = KMeans(n_clusters=best_k, n_init=10, random_state=0).fit_predict(vectors)

    clusters: list[RationaleCluster] = []
    for cid in range(best_k):
        idxs = [i for i, lab in enumerate(labels) if lab == cid]
        if not idxs:
            continue
        members = [items[i] for i in idxs]
        centroid = vectors[idxs].mean(axis=0)
        medoid_i = min(idxs, key=lambda i: float(((vectors[i] - centroid) ** 2).sum()))
        clusters.append(
            RationaleCluster(
                label=_label_from_members(members),
                example_ids=[items[i].example_id for i in idxs],
                representative=items[medoid_i].model_rationale or "",
            )
        )
    clusters.sort(key=lambda c: c.size, reverse=True)
    return clusters


def _choose_k(vectors) -> int:
    """Pick k in [2, min(6, n-1)] by best silhouette; fall back to 2."""
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    n = len(vectors)
    if n < 3:
        return 1
    best_k, best_score = 2, -1.0
    for cand in range(2, min(6, n - 1) + 1):
        labels = KMeans(n_clusters=cand, n_init=10, random_state=0).fit_predict(vectors)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(vectors, labels)
        if score > best_score:
            best_k, best_score = cand, score
    return best_k
