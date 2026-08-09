"""Convert TasteGraph behavioral signals into TasteBench training examples (Item 6).

Each user's engagement is turned into pairwise preferences: a positively-engaged asset is
``chosen`` over a negative one. Explicit negatives (dismiss) are used when present; otherwise
a low-affinity asset from the user's own candidate space is sampled as the rejected side.
The candidate "content" is the asset's caption/render, so the resulting `PreferenceExample`s
feed the existing `to_pairwise_pairs` / `RewardModel.fit` unchanged.
"""

from __future__ import annotations

import random
from typing import Optional

from ..datasets.schema import Candidate, ExpertJudgment, PreferenceExample


def _asset_text(engine, asset_id: str) -> str:
    if asset_id in engine.store:
        cap = engine.store.get(asset_id).semantic.caption
        if cap:
            return cap
    return asset_id


def signals_to_examples(engine, users: Optional[list[str]] = None, *, seed: int = 0) -> list[PreferenceExample]:
    """Build pairwise PreferenceExamples from a populated TasteGraphEngine."""
    from ..tastegraph.signals.profiles import weighted_assets

    rng = random.Random(seed)
    users = users or list(engine._signals.keys())
    examples: list[PreferenceExample] = []

    for user in users:
        wa = dict(weighted_assets(engine._signals.get(user, [])))
        positives = [a for a, w in wa.items() if w > 0 and a in engine.store]
        negatives = [a for a, w in wa.items() if w < 0 and a in engine.store]
        pool = [a for a in engine.store.ids() if a not in wa]

        for i, pos in enumerate(positives):
            if negatives:
                neg = negatives[i % len(negatives)]
            elif pool:
                neg = rng.choice(pool)
            else:
                continue
            examples.append(
                PreferenceExample(
                    id=f"{user}:{pos}:{neg}",
                    task=f"Which asset better matches {user}'s taste?",
                    candidates=[
                        Candidate(id="A", content=_asset_text(engine, pos)),
                        Candidate(id="B", content=_asset_text(engine, neg)),
                    ],
                    judgments=[ExpertJudgment(expert_id=user, choice="A")],
                )
            )
    return examples
