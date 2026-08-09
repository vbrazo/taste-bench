from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from tastebench.tastegraph import TasteGraphEngine, load_assets
from tastebench.tastegraph.api.app import create_app
from tastebench.tastegraph.api.tenancy import ApiKeyRegistry, TenantStore

DATA = Path(__file__).resolve().parents[1] / "data"


def _asset_body(ids):
    assets = [a for a in load_assets(DATA / "tastegraph_assets.jsonl") if a.id in ids]
    return {"assets": [a.model_dump() for a in assets]}


def test_dev_mode_no_key_ok():
    client = TestClient(create_app(TasteGraphEngine()))
    assert client.get("/").status_code == 200
    assert client.get("/metrics").status_code == 200


def test_enforced_requires_key():
    store = TenantStore(ApiKeyRegistry({"key_a": "tenant_a"}))
    client = TestClient(create_app(tenant_store=store))
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"X-API-Key": "bad"}).status_code == 401
    assert client.get("/metrics", headers={"X-API-Key": "key_a"}).status_code == 200


def test_tenants_are_isolated():
    store = TenantStore(ApiKeyRegistry({"key_a": "tenant_a", "key_b": "tenant_b"}))
    client = TestClient(create_app(tenant_store=store))
    ka = {"X-API-Key": "key_a"}
    kb = {"X-API-Key": "key_b"}

    client.post("/ingest", json=_asset_body({"asset_01", "asset_02"}), headers=ka)
    client.post("/ingest", json=_asset_body({"asset_03"}), headers=kb)

    assert client.get("/metrics", headers=ka).json()["assets_in_graph"] == 2
    assert client.get("/metrics", headers=kb).json()["assets_in_graph"] == 1

    # tenant B's rerank cannot see tenant A's assets
    r = client.post("/rerank", json={"user_id": "u", "candidates": ["asset_01"]}, headers=kb)
    ranked = r.json()["ranked"]
    # asset_01 is unknown to tenant B → returned but with score 0 (not scored against its graph)
    assert ranked[0]["score"] == 0.0
