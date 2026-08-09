import pytest

pytest.importorskip("numpy")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from tastebench.tastegraph import TasteGraphEngine
from tastebench.tastegraph.api.app import create_app
from tastebench.tastegraph.api.tenancy import ApiKeyRegistry, TenantStore


@pytest.fixture
def client():
    return TestClient(create_app(TasteGraphEngine()))


CONTENT = {
    "c_minimal": "minimal linen quiet-luxury dress in warm sand",
    "c_minimal2": "understated minimal cashmere knit, restrained luxe",
    "c_street": "neon streetwear bold graphic hoodie, high energy",
    "c_street2": "bright color-blocked windbreaker, energetic streetwear",
}


def _seed(client):
    client.post("/v1/entity", json={"id": "u1", "type": "user"})
    for cid, text in CONTENT.items():
        client.post("/v1/entity", json={"id": cid, "type": "content", "content": text})


def test_full_loop_search(client):
    _seed(client)
    # build taste: like minimal, dismiss street
    assert client.post("/v1/entity/u1/link", json={"target_id": "c_minimal", "action": "like"}).status_code == 200
    client.post("/v1/entity/u1/link", json={"target_id": "c_street", "action": "dismiss"})

    # liked content outranks dismissed content (deterministic under the mock analyzer)
    r = client.post("/v1/rerank", json={"user_id": "u1", "candidates": ["c_street", "c_minimal"]})
    results = r.json()["results"]
    order = [x["id"] for x in results]
    assert order.index("c_minimal") < order.index("c_street")
    scores = {x["id"]: x["score"] for x in results}
    assert scores["c_minimal"] > scores["c_street"]

    s = client.post("/v1/search", json={"user_id": "u1", "k": 5})
    assert s.status_code == 200
    ids = {x["id"] for x in s.json()["results"]}
    assert "c_minimal" not in ids  # engaged content excluded from retrieval


def test_entity_crud_and_custom_type(client):
    client.post("/v1/entity/type", json={"name": "product", "kind": "content"})
    types = {t["name"] for t in client.get("/v1/entity/types").json()["types"]}
    assert "product" in types

    client.post("/v1/entity", json={"id": "p1", "type": "product", "content": "a product"})
    assert client.get("/v1/entity/p1").json()["id"] == "p1"
    assert client.delete("/v1/entity/p1").status_code == 200
    assert client.get("/v1/entity/p1").status_code == 400  # hidden after soft delete


def test_list_entities(client):
    _seed(client)
    all_ents = client.get("/v1/entities")
    assert all_ents.status_code == 200
    ids = {e["id"] for e in all_ents.json()["entities"]}
    assert "u1" in ids and "c_minimal" in ids

    users = client.get("/v1/entities", params={"type": "user"})
    assert users.status_code == 200
    assert {e["id"] for e in users.json()["entities"]} == {"u1"}


def test_clusters(client):
    _seed(client)
    r = client.get("/v1/clusters")
    assert r.status_code == 200
    clusters = r.json()["clusters"]
    assert clusters and all(c["label"] for c in clusters)
    one = client.get(f"/v1/cluster/{clusters[0]['id']}")
    assert one.status_code == 200


def test_ask_and_explain_templated(client, monkeypatch):
    monkeypatch.delenv("TASTEGRAPH_ASK_MODEL", raising=False)
    _seed(client)
    client.post("/v1/entity/u1/link", json={"target_id": "c_minimal", "action": "like"})

    a = client.post("/v1/ask", json={"user_id": "u1", "question": "what should I wear?"})
    assert a.status_code == 200
    assert a.json()["source"] == "template"
    assert "answer" in a.json()

    e = client.post("/v1/explain", json={"user_id": "u1", "candidates": []})
    assert e.status_code == 200
    assert "explanation" in e.json()


def test_bad_link_is_400(client):
    _seed(client)
    r = client.post("/v1/entity/u1/link", json={"target_id": "nonexistent", "action": "like"})
    assert r.status_code == 400


def test_auth_enforced_on_v1():
    store = TenantStore(ApiKeyRegistry({"key_a": "tenant_a"}))
    client = TestClient(create_app(tenant_store=store))
    assert client.post("/v1/entity", json={"id": "u1", "type": "user"}).status_code == 401
    ok = client.post("/v1/entity", json={"id": "u1", "type": "user"}, headers={"X-API-Key": "key_a"})
    assert ok.status_code == 200
