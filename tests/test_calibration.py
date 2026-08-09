import pytest

from tastebench import Candidate, ExpertJudgment, Judgment, PreferenceExample
from tastebench.evaluation.calibration import calibration_report


def _ex(id, choice="A"):
    return PreferenceExample(
        id=id,
        task="t",
        candidates=[Candidate(id="A", content="a"), Candidate(id="B", content="b")],
        judgments=[ExpertJudgment(expert_id="1", choice=choice)],
    )


def test_perfect_calibration_low_ece():
    # confidence 1.0 and always correct -> ece 0
    examples = [_ex(str(i), "A") for i in range(4)]
    preds = [Judgment(choice="A", confidence=1.0) for _ in range(4)]
    rep = calibration_report(examples, preds)
    assert rep.ece == pytest.approx(0.0)
    assert rep.score == pytest.approx(1.0)


def test_overconfident_high_ece():
    # confidence 0.95 but only 50% correct
    examples = [_ex("1", "A"), _ex("2", "A"), _ex("3", "A"), _ex("4", "A")]
    preds = [
        Judgment(choice="A", confidence=0.95),
        Judgment(choice="A", confidence=0.95),
        Judgment(choice="B", confidence=0.95),
        Judgment(choice="B", confidence=0.95),
    ]
    rep = calibration_report(examples, preds)
    assert rep.ece == pytest.approx(0.45, abs=0.01)


def test_missing_confidence_ignored():
    examples = [_ex("1")]
    preds = [Judgment(choice="A")]
    rep = calibration_report(examples, preds)
    assert rep.n_with_confidence == 0
    assert rep.ece == 0.0
