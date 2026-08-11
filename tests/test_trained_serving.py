"""Train -> serve bridge: a locally-trained model changes /v1/judge and /v1/rerank behavior.

Skipped without the `train` extra. Trains tiny models in tmp_path, points the loader env at
them, and asserts the served responses switch to the trained/reward modes (and fall back
cleanly when no model dir is set).
"""

import pytest

pytest.importorskip("numpy")
pytest.importorskip("torch")
pytest.importorskip("transformers")

from fastapi.testclient import TestClient

from tastebench.datasets.schema import Candidate, ExpertJudgment, PreferenceExample
from tastebench.tastegraph.api.app import create_app
from tastebench.tastegraph.api.engine import TasteGraphEngine
from tastebench.tastegraph.api import trained_models
from tastebench.tastegraph.entities.registry import get_registry
from tastebench.tastegraph.entities.schema import Entity, Link


def _example(id_, a_text, b_text, choice):
    return PreferenceExample(
        id=id_,
        task="Which draft better matches the taste?",
        candidates=[Candidate(id="A", content=a_text), Candidate(id="B", content=b_text)],
        judgments=[ExpertJudgment(expert_id="e", choice=choice)],
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    trained_models.reset_cache()
    yield
    trained_models.reset_cache()


def _seed_engine():
    engine = TasteGraphEngine()
    reg = get_registry(engine)
    reg.create(Entity(id="u", type="user"))
    reg.create(Entity(id="c_warm", type="content", content="warm specific concrete note"))
    reg.create(Entity(id="c_hype", type="content", content="AMAZING blast buy now"))
    reg.link(Link(source_id="u", target_id="c_warm", action="like"))
    reg.link(Link(source_id="u", target_id="c_hype", action="dismiss"))
    return engine


def test_judge_uses_trained_classifier(tmp_path, monkeypatch):
    from tastebench.training.classifier import TrainableJudge

    warm, hype = "warm specific concrete note", "AMAZING blast buy now"
    model = TrainableJudge().fit([_example(f"e{i}", warm, hype, "A") for i in range(4)], epochs=4)
    out_dir = tmp_path / "judge"
    model.save(str(out_dir))

    monkeypatch.setenv(trained_models.JUDGE_DIR_ENV, str(out_dir))
    monkeypatch.delenv("TASTEGRAPH_JUDGE_MODEL", raising=False)
    client = TestClient(create_app(_seed_engine()))

    r = client.post("/v1/judge", json={"subject_id": "u", "candidates": [warm, hype]})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "trained"
    assert body["results"][0]["text"] == warm  # learned to prefer the on-taste draft


def test_judge_falls_back_without_model_dir(monkeypatch):
    monkeypatch.delenv(trained_models.JUDGE_DIR_ENV, raising=False)
    monkeypatch.delenv("TASTEGRAPH_JUDGE_MODEL", raising=False)
    client = TestClient(create_app(_seed_engine()))
    body = client.post("/v1/judge", json={"subject_id": "u", "candidates": ["a", "b"]}).json()
    assert body["mode"] == "heuristic"


def test_rerank_uses_reward_model(tmp_path, monkeypatch):
    from tastebench.training.reward import RewardModel

    engine = _seed_engine()
    from tastebench.training.from_signals import signals_to_examples

    rm = RewardModel().fit(signals_to_examples(engine) or [
        _example("e0", "warm specific concrete note", "AMAZING blast buy now", "A")
    ], epochs=1)
    out_dir = tmp_path / "reward"
    rm.save(str(out_dir))

    monkeypatch.setenv(trained_models.REWARD_DIR_ENV, str(out_dir))
    client = TestClient(create_app(engine))
    body = client.post("/v1/rerank", json={"user_id": "u", "candidates": ["c_warm", "c_hype"]}).json()
    assert body["mode"] == "reward"
    assert {r["id"] for r in body["results"]} == {"c_warm", "c_hype"}


def test_rerank_falls_back_to_affinity(monkeypatch):
    monkeypatch.delenv(trained_models.REWARD_DIR_ENV, raising=False)
    client = TestClient(create_app(_seed_engine()))
    body = client.post("/v1/rerank", json={"user_id": "u", "candidates": ["c_warm", "c_hype"]}).json()
    assert body["mode"] == "affinity"
