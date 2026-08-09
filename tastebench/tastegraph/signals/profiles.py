"""Aggregate a user's signals into an anonymized taste profile (Layer 2).

Combines the behavioral signals with asset fingerprints to produce (a) the weighted
(asset_id, weight) list used to build the taste vector, and (b) a human-readable Taste
Card reusing the existing :class:`tastebench.profiles.taste_profile.TasteProfile`, so the
eval-side and product-side notions of a profile stay unified.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from ...profiles.taste_profile import TasteProfile
from ..assets.store import FingerprintStore
from .schema import Signal


def weighted_assets(signals: list[Signal]) -> list[tuple[str, float]]:
    """Sum effective weights per asset for one user's signals."""
    totals: dict[str, float] = defaultdict(float)
    for s in signals:
        totals[s.asset_id] += s.effective_weight()
    return list(totals.items())


def taste_card(user_id: str, signals: list[Signal], store: FingerprintStore, top_n: int = 5) -> TasteProfile:
    """Build a human-readable, anonymized Taste Card from positive engagements."""
    liked: Counter = Counter()
    disliked: Counter = Counter()
    preferred_examples: list[str] = []
    rejected_examples: list[str] = []

    for aid, w in weighted_assets(signals):
        if aid not in store:
            continue
        tags = store.get(aid).tags()
        bucket = liked if w >= 0 else disliked
        for t in tags:
            bucket[t] += abs(w)
        (preferred_examples if w >= 0 else rejected_examples).append(aid)

    principles = [t for t, _ in liked.most_common(top_n)]
    avoid = [t for t, _ in disliked.most_common(top_n)]
    return TasteProfile(
        name=f"taste:{user_id}",
        principles=principles,
        preferences=principles,
        avoid=avoid,
        preferred_examples=preferred_examples,
        rejected_examples=rejected_examples,
    )
