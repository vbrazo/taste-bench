from pathlib import Path

import pytest

from tastebench.tastegraph.assets.analyzer import MockAssetAnalyzer
from tastebench.tastegraph.assets.schema import Asset, AssetFingerprint
from tastebench.tastegraph.assets.store import FingerprintStore, load_assets
from tastebench.tastegraph.signals.capture import TasteGraphSDK, load_signals
from tastebench.tastegraph.signals.schema import Signal

DATA = Path(__file__).resolve().parents[1] / "data"

pytestmark = pytest.mark.filterwarnings("ignore")


# ---- Layer 1: assets (no numpy needed) ------------------------------------

def test_mock_analyzer_is_deterministic():
    a = Asset(id="x", type="text", content="a minimal linen dress")
    fp1 = MockAssetAnalyzer().analyze(a)
    fp2 = MockAssetAnalyzer().analyze(a)
    assert fp1.model_dump() == fp2.model_dump()
    assert fp1.aesthetic.style
    assert len(fp1.advanced.embedding) == 32


def test_fingerprint_store_round_trip(tmp_path):
    store = FingerprintStore()
    for a in load_assets(DATA / "tastegraph_assets.jsonl"):
        store.add(MockAssetAnalyzer().analyze(a))
    assert len(store) == 12
    path = tmp_path / "fp.jsonl"
    store.save(path)
    reloaded = FingerprintStore.load(path)
    assert reloaded.ids() == store.ids()


# ---- Layer 2: signals ------------------------------------------------------

def test_signal_weights():
    assert Signal(user_id="u", asset_id="a", action="save").effective_weight() > 0
    assert Signal(user_id="u", asset_id="a", action="dismiss").effective_weight() < 0


def test_sdk_logs_signals(tmp_path):
    log = tmp_path / "events.jsonl"
    sdk = TasteGraphSDK(log)
    sdk.track("u1", "asset_01", "like")
    sdk.track("u1", "asset_03", "dismiss")
    loaded = load_signals(log)
    assert len(loaded) == 2
    assert loaded[0].action == "like"


# ---- Layer 3 + 4: graph, affinity, engine (numpy) --------------------------

@pytest.fixture
def engine():
    pytest.importorskip("numpy")
    from tastebench.tastegraph import TasteGraphEngine

    eng = TasteGraphEngine()
    eng.ingest(load_assets(DATA / "tastegraph_assets.jsonl"))
    for sig in load_signals(DATA / "tastegraph_signals.jsonl"):
        eng.track(sig)
    return eng


def test_index_knn_self_is_top(engine):
    vec = engine.index.vector("asset_01")
    top = engine.index.knn(vec, k=1)
    assert top[0][0] == "asset_01"
    assert top[0][1] == pytest.approx(1.0, abs=1e-6)


def test_rerank_puts_on_taste_first(engine):
    # u_minimal liked/saved minimal+luxe items, dismissed streetwear.
    # Among a mixed candidate set, a minimal item should outrank a streetwear one.
    ranked = engine.rerank("u_minimal", ["asset_03", "asset_09", "asset_10", "asset_01"])
    order = [aid for aid, _ in ranked]
    assert order.index("asset_09") < order.index("asset_03")
    assert order.index("asset_01") < order.index("asset_10")


def test_cold_start_user_still_ranks_with_seed(engine):
    # brand-new user, zero signals -> rank by content similarity to a seed asset
    ranked = engine.rerank("brand_new_user", ["asset_10", "asset_09"], cold_start_seed="asset_01")
    # asset_09 (minimal luxe) is closer to asset_01 (minimal) than asset_10 (streetwear)
    assert ranked[0][0] == "asset_09"


def test_cold_start_without_seed_is_total(engine):
    ranked = engine.rerank("brand_new_user", ["asset_10", "asset_09"])
    assert {a for a, _ in ranked} == {"asset_10", "asset_09"}


def test_agent_context_structure(engine):
    ctx = engine.agent_context("u_minimal")
    assert ctx["resolved"] is True
    assert ctx["n_signals"] == 4
    assert 0.0 <= ctx["confidence"] <= 1.0
    assert isinstance(ctx["principles"], list)
    assert "asset_01" not in ctx["top_assets"]  # engaged assets excluded from retrieval


def test_metrics(engine):
    m = engine.metrics()
    assert m["assets_in_graph"] == 12
    assert m["people_in_graph"] == 2
    assert m["signals_ingested"] == 8


def test_retrieve_excludes_engaged(engine):
    results = engine.retrieve("u_minimal", k=5)
    ids = {a for a, _ in results}
    assert "asset_01" not in ids and "asset_09" not in ids


# ---- API -------------------------------------------------------------------

def test_api_endpoints(engine):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tastebench.tastegraph.api.app import create_app

    client = TestClient(create_app(engine))
    assert client.get("/").status_code == 200
    r = client.post("/rerank", json={"user_id": "u_minimal", "candidates": ["asset_03", "asset_09"]})
    assert r.status_code == 200
    ranked = r.json()["ranked"]
    assert ranked[0]["asset_id"] == "asset_09"
    assert client.get("/agent-context/u_minimal").status_code == 200
    assert client.get("/metrics").json()["assets_in_graph"] == 12


def test_llm_retrieval_prompt(engine):
    from tastebench.tastegraph.api.llm_retrieval import retrieval_prompt

    prompt = retrieval_prompt(engine, "u_minimal")
    assert "taste profile" in prompt.lower()
