import pytest

from tastebench import Candidate, ExpertJudgment, PreferenceExample


def _cands():
    return [Candidate(id="A", content="a"), Candidate(id="B", content="bb")]


def test_candidate_requires_exactly_one_source():
    with pytest.raises(ValueError):
        Candidate(id="A")  # neither
    with pytest.raises(ValueError):
        Candidate(id="A", content="x", uri="y")  # both
    Candidate(id="A", content="x")  # ok
    Candidate(id="B", type="image", uri="img.png")  # ok


def test_image_candidate_rejects_inline_content():
    with pytest.raises(ValueError):
        Candidate(id="A", type="image", content="not allowed")


def test_consensus_majority_and_agreement():
    ex = PreferenceExample(
        id="e",
        task="t",
        candidates=_cands(),
        criteria=[],
        judgments=[
            ExpertJudgment(expert_id="1", choice="B"),
            ExpertJudgment(expert_id="2", choice="B"),
            ExpertJudgment(expert_id="3", choice="A"),
        ],
    )
    assert ex.preference == "B"
    assert ex.agreement == pytest.approx(2 / 3)
    assert not ex.is_unanimous


def test_tie_breaks_by_candidate_order():
    ex = PreferenceExample(
        id="e",
        task="t",
        candidates=_cands(),
        judgments=[
            ExpertJudgment(expert_id="1", choice="A"),
            ExpertJudgment(expert_id="2", choice="B"),
        ],
    )
    assert ex.preference == "A"  # first candidate wins the tie


def test_choice_must_reference_candidate():
    with pytest.raises(ValueError):
        PreferenceExample(
            id="e",
            task="t",
            candidates=_cands(),
            judgments=[ExpertJudgment(expert_id="1", choice="Z")],
        )


def test_single_constructor():
    ex = PreferenceExample.single(
        id="e", task="t", candidates=_cands(), preference="B", confidence=0.9
    )
    assert ex.preference == "B"
    assert len(ex.judgments) == 1
    assert ex.judgments[0].confidence == 0.9
