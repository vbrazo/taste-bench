"""Expose subjective judges as reward functions for post-training (spec §4, §22 RQ8).

Deliberately framework-agnostic: a :class:`RewardFunction` maps an artifact (+ optional
context) to a float. No trainer loop is shipped — plug the reward into whatever RL /
post-training code you use.

Two backings:
  * a :class:`~tastebench.training.reward.RewardModel` (absolute scalar score), or
  * any :class:`~tastebench.judges.base.Judge`, turned into a reward by pairwise
    win-probability against a fixed *reference* artifact (judge-as-reward).
"""

from __future__ import annotations

from typing import Optional, Protocol

from ..datasets.schema import Candidate, ExpertJudgment, PreferenceExample
from ..judges.base import Judge


class RewardFunction(Protocol):
    def reward(self, artifact: str, context: Optional[str] = None) -> float: ...


class RewardModelReward:
    """Reward = the reward model's scalar score for (context, artifact)."""

    def __init__(self, reward_model, default_context: str = ""):
        self.reward_model = reward_model
        self.default_context = default_context

    def reward(self, artifact: str, context: Optional[str] = None) -> float:
        return self.reward_model.score(context or self.default_context, artifact)


class JudgeReward:
    """Reward = probability that a Judge prefers ``artifact`` over a reference.

    The judge decides a two-candidate example (artifact vs reference). A win maps to the
    judge's confidence (defaulting to 1.0), a loss to ``1 - confidence``, giving a scalar
    in [0, 1]. ``task`` supplies the judging context.
    """

    def __init__(self, judge: Judge, reference_artifact: str, task: str, criteria: Optional[list[str]] = None):
        self.judge = judge
        self.reference_artifact = reference_artifact
        self.task = task
        self.criteria = criteria or []

    def reward(self, artifact: str, context: Optional[str] = None) -> float:
        example = PreferenceExample(
            id="reward_probe",
            task=context or self.task,
            criteria=self.criteria,
            candidates=[
                Candidate(id="cand", content=artifact),
                Candidate(id="ref", content=self.reference_artifact),
            ],
            # placeholder label; the judge ignores it and only reads the candidates
            judgments=[ExpertJudgment(expert_id="_", choice="cand")],
        )
        judgment = self.judge.predict(example)
        conf = judgment.confidence if judgment.confidence is not None else 1.0
        return conf if judgment.choice == "cand" else (1.0 - conf)
