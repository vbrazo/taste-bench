from pathlib import Path

import pytest

pytest.importorskip("numpy")

from tastebench.tastegraph import TasteGraphEngine, load_assets
from tastebench.tastegraph.signals.capture import load_signals
from tastebench.training.dataset import to_pairwise_pairs
from tastebench.training.from_signals import signals_to_examples

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def engine():
    eng = TasteGraphEngine()
    eng.ingest(load_assets(DATA / "tastegraph_assets.jsonl"))
    for sig in load_signals(DATA / "tastegraph_signals.jsonl"):
        eng.track(sig)
    return eng


def test_signals_become_preference_examples(engine):
    examples = signals_to_examples(engine)
    assert examples
    # every example prefers candidate A (the positively-engaged asset)
    assert all(ex.preference == "A" for ex in examples)
    # and converts cleanly into training pairs
    pairs = to_pairwise_pairs(examples)
    assert len(pairs) == len(examples)
    assert all(p.chosen and p.rejected for p in pairs)


def test_uses_explicit_dismiss_as_negative(engine):
    # u_minimal dismissed asset_03; a pair should pit a liked asset against asset_03's text
    examples = signals_to_examples(engine, users=["u_minimal"])
    dismissed_caption = engine.store.get("asset_03").semantic.caption
    assert any(ex.candidates[1].content == dismissed_caption for ex in examples)


def test_reward_smoke(engine):
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from tastebench.training.reward import RewardModel

    examples = signals_to_examples(engine)
    rm = RewardModel().fit(examples, epochs=1)
    score = rm.score("taste", "a minimal linen dress")
    assert isinstance(score, float)
