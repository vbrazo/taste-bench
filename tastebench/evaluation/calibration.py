"""Confidence calibration (spec section 11).

Does the judge know when it is uncertain? We bin predictions by stated confidence and
compare mean confidence against empirical accuracy in each bin. Expected Calibration
Error (ECE) summarises the gap.

A judge reporting 0.95 confidence while only being right 51% of the time is badly
calibrated; this surfaces that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..datasets.schema import PreferenceExample
from ..judges.base import Judgment


@dataclass
class CalibrationBin:
    lower: float
    upper: float
    count: int = 0
    sum_confidence: float = 0.0
    sum_correct: int = 0

    @property
    def mean_confidence(self) -> float:
        return self.sum_confidence / self.count if self.count else 0.0

    @property
    def accuracy(self) -> float:
        return self.sum_correct / self.count if self.count else 0.0

    @property
    def gap(self) -> float:
        return abs(self.mean_confidence - self.accuracy)


@dataclass
class CalibrationReport:
    bins: list[CalibrationBin]
    ece: float
    n_with_confidence: int

    @property
    def score(self) -> float:
        """A 0-1 "calibration score" = 1 - ECE, for a friendlier report number."""
        return max(0.0, 1.0 - self.ece)


def calibration_report(
    examples: list[PreferenceExample],
    predictions: list[Judgment],
    n_bins: int = 10,
) -> CalibrationReport:
    if len(examples) != len(predictions):
        raise ValueError("examples and predictions must align.")

    edges = [i / n_bins for i in range(n_bins + 1)]
    bins = [CalibrationBin(edges[i], edges[i + 1]) for i in range(n_bins)]

    n_conf = 0
    for ex, pred in zip(examples, predictions):
        if pred.confidence is None:
            continue
        n_conf += 1
        conf = min(max(pred.confidence, 0.0), 1.0)
        # index; the top edge (1.0) falls into the last bin
        idx = min(int(conf * n_bins), n_bins - 1)
        b = bins[idx]
        b.count += 1
        b.sum_confidence += conf
        b.sum_correct += int(pred.choice == ex.preference)

    ece = 0.0
    if n_conf:
        ece = sum(b.count / n_conf * b.gap for b in bins if b.count)

    return CalibrationReport(bins=bins, ece=ece, n_with_confidence=n_conf)
