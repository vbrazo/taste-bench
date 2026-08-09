from pathlib import Path

import pytest

pytest.importorskip("numpy")

from tastebench.tastegraph import TasteGraphEngine, load_assets
from tastebench.tastegraph.export_web import build_bundle

DATA = Path(__file__).resolve().parents[1] / "data"


# ---- clustering ------------------------------------------------------------

def test_cluster_assets_covers_inputs():
    pytest.importorskip("sklearn")
    from tastebench.tastegraph.graph.clustering import cluster_assets

    bundle = build_bundle(DATA / "tastegraph_assets.jsonl")
    ids = [a["id"] for a in bundle["assets"]]
    regions = cluster_assets(
        [a["vec"] for a in bundle["assets"]],
        ids,
        [a["tags"] for a in bundle["assets"]],
    )
    assert regions
    covered = [m for r in regions for m in r.member_ids]
    assert set(covered) == set(ids)  # every asset assigned exactly one region
    assert len(covered) == len(ids)
    assert all(r.label for r in regions)  # non-empty labels


def test_bundle_includes_regions_and_media_fields():
    pytest.importorskip("sklearn")
    bundle = build_bundle(DATA / "tastegraph_assets.jsonl")
    assert "regions" in bundle and bundle["regions"]
    a = bundle["assets"][0]
    assert "mediaUri" in a and "posterUri" in a


# ---- endpoints -------------------------------------------------------------

@pytest.fixture
def client():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tastebench.tastegraph.api.app import create_app

    eng = TasteGraphEngine()
    eng.ingest(load_assets(DATA / "tastegraph_assets.jsonl"))
    eng.track_event("u1", "asset_01", "like")
    eng.track_event("u1", "asset_09", "save")
    return TestClient(create_app(eng))


def test_regions_endpoint(client):
    pytest.importorskip("sklearn")
    r = client.post("/regions", json={})
    assert r.status_code == 200
    regions = r.json()["regions"]
    assert regions and all(reg["label"] for reg in regions)


def test_regions_endpoint_subset(client):
    pytest.importorskip("sklearn")
    r = client.post("/regions", json={"asset_ids": ["asset_01", "asset_09", "asset_03"]})
    assert r.status_code == 200
    covered = [m for reg in r.json()["regions"] for m in reg["memberIds"]]
    assert set(covered) <= {"asset_01", "asset_09", "asset_03"}


def test_explain_falls_back_without_model(client, monkeypatch):
    monkeypatch.delenv("TASTEGRAPH_EXPLAIN_MODEL", raising=False)
    r = client.get("/explain/u1")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "template"
    assert "confidence" in body["explanation"] or "taste" in body["explanation"].lower()
