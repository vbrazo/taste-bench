"""Judge-gaming / reward-hacking guard (spec §23, §25).

A system that scores 95% against an automated judge but 65% against a held-out human
set is not successful — it has learned the judge, not human taste. This computes the gap
between performance measured against the judge and against an independent human holdout,
and flags a suspicious divergence.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HackingReport:
    judge_score: float
    human_holdout_score: float
    gap: float
    flagged: bool
    threshold: float

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        verdict = "POSSIBLE REWARD HACKING" if self.flagged else "ok"
        return (
            f"judge={self.judge_score:.2%} human_holdout={self.human_holdout_score:.2%} "
            f"gap={self.gap:.2%} [{verdict}]"
        )


def judge_vs_human_gap(
    judge_score: float, human_holdout_score: float, *, threshold: float = 0.15
) -> HackingReport:
    """Flag when the judge score exceeds the human-holdout score by ``threshold``."""
    gap = judge_score - human_holdout_score
    return HackingReport(
        judge_score=judge_score,
        human_holdout_score=human_holdout_score,
        gap=gap,
        flagged=gap > threshold,
        threshold=threshold,
    )
