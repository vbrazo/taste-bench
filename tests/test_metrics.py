import pytest

from tastebench import Candidate, ExpertJudgment, Judgment, PreferenceExample
from tastebench.evaluation.metrics import (
    criterion_accuracy,
    pairwise_accuracy,
)


def _ex(id, choice, dominant=None):
    return PreferenceExample(
        id=id,
        task="t",
        candidates=[Candidate(id="A", content="a"), Candidate(id="B", content="b")],
        dominant_criterion=dominant,
        judgments=[ExpertJudgment(expert_id="1", choice=choice)],
    )


def test_pairwise_accuracy():
    examples = [_ex("1", "A"), _ex("2", "B"), _ex("3", "A")]
    preds = [Judgment(choice="A"), Judgment(choice="A"), Judgment(choice="A")]
    assert pairwise_accuracy(examples, preds) == pytest.approx(2 / 3)


def test_pairwise_accuracy_length_mismatch():
    with pytest.raises(ValueError):
        pairwise_accuracy([_ex("1", "A")], [])


def test_criterion_accuracy_grouping():
    examples = [_ex("1", "A", "hierarchy"), _ex("2", "B", "hierarchy"), _ex("3", "A", "restraint")]
    preds = [Judgment(choice="A"), Judgment(choice="A"), Judgment(choice="B")]
    scores = criterion_accuracy(examples, preds)
    assert scores["hierarchy"].accuracy == pytest.approx(0.5)
    assert scores["restraint"].accuracy == pytest.approx(0.0)


def test_untagged_examples_go_to_overall():
    examples = [_ex("1", "A")]
    preds = [Judgment(choice="A")]
    scores = criterion_accuracy(examples, preds)
    assert "overall" in scores
    assert scores["overall"].accuracy == 1.0
