"""User<->asset affinity over the taste graph (Layer 3).

A user's taste vector is the signal-weighted mean of the vectors of assets they engaged
with. Affinity is cosine similarity between that vector and an asset. Cold start: a user
with no signals has no taste vector, so ranking falls back to content similarity against a
context/seed asset — the shared embedding space means new users/products still rank
sensibly (the "why, not what" point from the Problem slide).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .index import TasteGraphIndex


@dataclass
class UserTaste:
    user_id: str
    vector: Optional[object]  # numpy array or None (cold start)
    n_signals: int
    confidence: float


def build_user_taste(user_id: str, weighted_assets: list[tuple[str, float]], index: TasteGraphIndex) -> UserTaste:
    """weighted_assets: list of (asset_id, weight). Missing assets are skipped."""
    import numpy as np

    vecs, weights = [], []
    for aid, w in weighted_assets:
        if aid in index:
            vecs.append(index.vector(aid))
            weights.append(w)
    if not vecs:
        return UserTaste(user_id=user_id, vector=None, n_signals=0, confidence=0.0)

    m = np.vstack(vecs)
    w = np.asarray(weights, dtype=float)
    wsum = w.sum()
    if wsum == 0:
        wsum = 1.0
    taste = (m * w[:, None]).sum(axis=0) / wsum
    n = np.linalg.norm(taste)
    taste = taste / n if n else taste
    return UserTaste(
        user_id=user_id,
        vector=taste,
        n_signals=len(vecs),
        confidence=_confidence(len(vecs), w),
    )


def _confidence(n_signals: int, weights) -> float:
    """A 0..1 confidence that more/stronger signals push toward 1."""
    import numpy as np

    if n_signals == 0:
        return 0.0
    # saturating function of total positive evidence
    evidence = float(np.clip(weights, 0, None).sum())
    return round(1.0 - 1.0 / (1.0 + evidence), 3)


def affinity(user: UserTaste, asset_id: str, index: TasteGraphIndex) -> float:
    if user.vector is None or asset_id not in index:
        return 0.0
    return index.score_ids(user.vector, [asset_id]).get(asset_id, 0.0)


def rank_candidates(
    user: UserTaste,
    candidate_ids: list[str],
    index: TasteGraphIndex,
    *,
    cold_start_seed: Optional[str] = None,
) -> list[tuple[str, float]]:
    """Return candidates sorted by affinity (desc).

    With a taste vector, rank by affinity to it. Cold start (no vector): rank by content
    similarity to ``cold_start_seed`` if given, else preserve input order with 0 scores.
    """
    present = [c for c in candidate_ids if c in index]
    if user.vector is not None:
        scores = index.score_ids(user.vector, present)
    elif cold_start_seed is not None and cold_start_seed in index:
        scores = index.score_ids(index.vector(cold_start_seed), present)
    else:
        scores = {c: 0.0 for c in present}
    # keep unknown candidates at the end with score 0
    ranked = sorted(present, key=lambda c: scores.get(c, 0.0), reverse=True)
    ranked += [c for c in candidate_ids if c not in index]
    return [(c, round(scores.get(c, 0.0), 4)) for c in ranked]
