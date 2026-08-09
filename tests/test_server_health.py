import pytest

pytest.importorskip("numpy")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient


def test_health_endpoint_unauthenticated():
    from tastebench.tastegraph import TasteGraphEngine
    from tastebench.tastegraph.api.app import create_app

    client = TestClient(create_app(TasteGraphEngine()))
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_server_factory_builds_app_from_env(monkeypatch):
    # memory backend, no auth, no limits -> a working app
    monkeypatch.delenv("TASTEGRAPH_API_KEYS", raising=False)
    monkeypatch.setenv("TASTEGRAPH_BACKEND", "memory")
    import importlib

    from tastebench.tastegraph import server as server_module

    importlib.reload(server_module)
    client = TestClient(server_module.build_app())
    assert client.get("/health").status_code == 200
    # full loop still works through the env-built app
    assert client.post("/v1/entity", json={"id": "u1", "type": "user"}).status_code == 200


def test_server_factory_enforces_env_rate_limit(monkeypatch):
    monkeypatch.setenv("TASTEGRAPH_BACKEND", "memory")
    monkeypatch.setenv("TASTEGRAPH_RATE_PER_MIN", "60")
    monkeypatch.setenv("TASTEGRAPH_RATE_BURST", "1")
    import importlib

    from tastebench.tastegraph import server as server_module

    importlib.reload(server_module)
    client = TestClient(server_module.build_app())
    assert client.get("/metrics").status_code == 200
    assert client.get("/metrics").status_code == 429
