"""Human judge.

Replays a stored expert's decision. Its main use is computing the human-agreement
ceiling: treat one expert as the "judge" and measure how well they predict the
consensus of the *other* experts (leave-one-out). See :mod:`tastebench.evaluation.agreement`.
"""

from __future__ import annotations

from typing import Optional

from ..datasets.schema import PreferenceExample
from .base import Judge, Judgment


class HumanJudge(Judge):
    """Replays the judgment of a specific expert, if present on the example."""

    def __init__(self, expert_id: str):
        self.expert_id = expert_id
        self.name = f"human:{expert_id}"

    def _find(self, example: PreferenceExample):
        for j in example.judgments:
            if j.expert_id == self.expert_id:
                return j
        return None

    def predict(self, example: PreferenceExample) -> Judgment:
        j = self._find(example)
        if j is None:
            raise KeyError(
                f"Expert {self.expert_id!r} has no judgment on example {example.id!r}."
            )
        return Judgment(choice=j.choice, confidence=j.confidence, rationale=j.rationale)

    def predicts(self, example: PreferenceExample) -> bool:
        """Whether this expert judged the given example."""
        return self._find(example) is not None

    def reproducibility(self) -> dict:
        return {"judge": self.name, "expert_id": self.expert_id}
