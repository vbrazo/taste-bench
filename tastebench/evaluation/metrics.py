"""Core evaluation metrics (spec section 11).

All metrics compare a judge's predicted choice against the *consensus* of the expert
judgments on each example.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..datasets.schema import PreferenceExample
from ..judges.base import Judgment


@dataclass
class CriterionScore:
    criterion: str
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def pairwise_accuracy(
    examples: list[PreferenceExample], predictions: list[Judgment]
) -> float:
    """Fraction of examples where the judge matches the expert consensus."""
    _check_lengths(examples, predictions)
    if not examples:
        return 0.0
    correct = sum(
        1 for ex, pred in zip(examples, predictions) if pred.choice == ex.preference
    )
    return correct / len(examples)


def agreement_rate(
    examples: list[PreferenceExample], predictions: list[Judgment]
) -> float:
    """Alias for :func:`pairwise_accuracy`; reported separately for clarity."""
    return pairwise_accuracy(examples, predictions)


def criterion_accuracy(
    examples: list[PreferenceExample], predictions: list[Judgment]
) -> dict[str, CriterionScore]:
    """Per-criterion accuracy, keyed by ``dominant_criterion``.

    Only examples tagged with a ``dominant_criterion`` contribute. Examples without a
    tag are aggregated under the ``"overall"`` key so nothing is silently dropped.
    """
    _check_lengths(examples, predictions)
    scores: dict[str, CriterionScore] = {}
    for ex, pred in zip(examples, predictions):
        key = ex.dominant_criterion or "overall"
        score = scores.setdefault(key, CriterionScore(key, 0, 0))
        score.total += 1
        if pred.choice == ex.preference:
            score.correct += 1
    return scores


def _check_lengths(examples: list, predictions: list) -> None:
    if len(examples) != len(predictions):
        raise ValueError(
            f"examples ({len(examples)}) and predictions ({len(predictions)}) must align."
        )
