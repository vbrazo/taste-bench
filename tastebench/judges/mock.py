"""Deterministic, offline judge.

MockJudge needs no API keys and always returns the same choice for the same example,
so the entire pipeline (and CI) runs without network access. Useful as a baseline and
for testing metrics/reporting end to end.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from ..datasets.schema import PreferenceExample
from .base import Judge, Judgment

Strategy = Literal["longer", "hash", "first"]


class MockJudge(Judge):
    """A deterministic judge with a few simple strategies.

    - ``longer``: prefer the candidate with more textual content (a crude proxy that
      deliberately over-values length, which makes disagreement analysis interesting).
    - ``hash``: pick pseudo-randomly but deterministically from the example id.
    - ``first``: always choose the first candidate.
    """

    def __init__(self, strategy: Strategy = "longer", name: str = "mock"):
        self.strategy = strategy
        self.name = name

    def predict(self, example: PreferenceExample) -> Judgment:
        if self.strategy == "first":
            choice = example.candidates[0].id
            rationale = "Always selects the first candidate."
        elif self.strategy == "hash":
            digest = hashlib.sha256(example.id.encode("utf-8")).digest()
            idx = digest[0] % len(example.candidates)
            choice = example.candidates[idx].id
            rationale = "Deterministic pseudo-random choice from example id."
        else:  # "longer"
            choice = max(
                example.candidates, key=lambda c: len(c.render())
            ).id
            rationale = "Prefers the candidate with more visual/textual content."

        return Judgment(choice=choice, confidence=0.6, rationale=rationale)

    def reproducibility(self) -> dict:
        return {"judge": self.name, "strategy": self.strategy}
