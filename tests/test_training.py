import pytest

from tastebench import Candidate, ExpertJudgment, Judgment, PreferenceExample
from tastebench.judges.base import Judge
from tastebench.training.dataset import to_pairwise_pairs
from tastebench.training.rl import JudgeReward
from tastebench.evaluation.holdout import judge_vs_human_gap


# ---- dependency-free tests -------------------------------------------------

def _ex(id, choices):
    return PreferenceExample(
        id=id,
        task="t",
        candidates=[Candidate(id="A", content="short"), Candidate(id="B", content="a much longer answer")],
        judgments=[ExpertJudgment(expert_id=str(i), choice=c) for i, c in enumerate(choices)],
    )


def test_pair_generation_uses_consensus_and_weight():
    pairs = to_pairwise_pairs([_ex("1", ["B", "B", "A"])])
    assert len(pairs) == 1
    p = pairs[0]
    assert p.chosen == "a much longer answer"  # B is consensus
    assert p.rejected == "short"
    assert p.weight == pytest.approx(2 / 3)


def test_pair_generation_skips_non_binary():
    ex = PreferenceExample(
        id="m",
        task="t",
        candidates=[Candidate(id="A", content="a"), Candidate(id="B", content="b"), Candidate(id="C", content="c")],
        judgments=[ExpertJudgment(expert_id="1", choice="A")],
    )
    assert to_pairwise_pairs([ex]) == []


class _StubJudge(Judge):
    name = "stub"

    def __init__(self, choice, confidence):
        self._choice, self._conf = choice, confidence

    def predict(self, example):
        return Judgment(choice=self._choice, confidence=self._conf)


def test_judge_reward_win_and_loss():
    win = JudgeReward(_StubJudge("cand", 0.8), reference_artifact="ref", task="t")
    assert win.reward("my artifact") == pytest.approx(0.8)
    loss = JudgeReward(_StubJudge("ref", 0.9), reference_artifact="ref", task="t")
    assert loss.reward("my artifact") == pytest.approx(0.1)


def test_holdout_flags_reward_hacking():
    rep = judge_vs_human_gap(0.95, 0.65)
    assert rep.flagged
    ok = judge_vs_human_gap(0.80, 0.78)
    assert not ok.flagged


# ---- torch-dependent smoke test -------------------------------------------

def test_classifier_overfits_tiny_set():
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from tastebench.training.classifier import TrainableJudge
    from tastebench.judges.trained import TrainedJudge

    examples = [_ex(str(i), ["B", "B", "B"]) for i in range(4)]
    judge = TrainableJudge().fit(examples, epochs=5)
    wrapped = TrainedJudge(judge)
    pred = wrapped.predict(examples[0])
    assert pred.choice in {"A", "B"}
