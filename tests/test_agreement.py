import pytest

from tastebench import Candidate, ExpertJudgment, PreferenceExample
from tastebench.evaluation.agreement import (
    consensus_info,
    human_agreement_ceiling,
)


def _ex(choices):
    return PreferenceExample(
        id="e",
        task="t",
        candidates=[Candidate(id="A", content="a"), Candidate(id="B", content="b")],
        judgments=[ExpertJudgment(expert_id=str(i), choice=c) for i, c in enumerate(choices)],
    )


def test_unanimous_ceiling_is_one():
    assert human_agreement_ceiling([_ex(["A", "A", "A"])]) == 1.0


def test_split_ceiling():
    # choices A,A,B: holding out each ->
    #   hold A: rest {A,B} majority A (tie->A) == A  hit
    #   hold A: rest {A,B} -> A == A  hit
    #   hold B: rest {A,A} -> A != B  miss
    # 2/3
    assert human_agreement_ceiling([_ex(["A", "A", "B"])]) == pytest.approx(2 / 3)


def test_single_expert_excluded_from_ceiling():
    assert human_agreement_ceiling([_ex(["A"])]) == 0.0


def test_ambiguity_flag():
    info = consensus_info(_ex(["A", "B"]))  # 50% agreement
    assert info.is_ambiguous
    info2 = consensus_info(_ex(["A", "A", "A"]))
    assert not info2.is_ambiguous
