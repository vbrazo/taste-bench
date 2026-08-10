"""Tests for the shared seed-demo path (tastebench tastegraph seed-demo)."""

import urllib.error

import pytest

pytest.importorskip("numpy")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from tastebench.tastegraph import TasteGraphEngine  # noqa: E402
from tastebench.tastegraph.api.app import create_app  # noqa: E402
from tastebench.tastegraph.demo_seed import seed_demo  # noqa: E402


class _Shim:
    """Client-like adapter over TestClient that mirrors TasteGraphClient and, like the real
    urllib-based client, raises urllib.error.HTTPError on a non-2xx response."""

    def __init__(self, app):
        self.base_url = "http://testserver"
        self._c = TestClient(app)

    def _post(self, path, body):
        resp = self._c.post(path, json=body)
        if resp.status_code >= 300:
            raise urllib.error.HTTPError(path, resp.status_code, resp.text, hdrs=None, fp=None)
        return resp.json()

    def create_entity(self, id, type="content", content=None, metadata=None):
        return self._post("/v1/entity", {"id": id, "type": type, "content": content, "metadata": metadata or {}})

    def link(self, user_id, target_id, action="like", weight=None):
        return self._post(f"/v1/entity/{user_id}/link", {"target_id": target_id, "action": action, "weight": weight})

    def rerank(self, user_id, candidates):
        return self._post("/v1/rerank", {"user_id": user_id, "candidates": candidates})


@pytest.fixture
def client():
    return _Shim(create_app(TasteGraphEngine()))


def test_seed_demo_ranks_warm_over_hype(client):
    result = seed_demo(client)
    assert result["subject_id"] == "u_demo"
    assert set(result["created"]) == {"u_demo", "c_warm", "c_hype"}
    order = [r["id"] for r in result["rerank"]["results"]]
    assert order.index("c_warm") < order.index("c_hype")


def test_seed_demo_is_idempotent(client):
    first = seed_demo(client)
    assert first["created"] == ["u_demo", "c_warm", "c_hype"]
    # A second run must not raise on the duplicate creates.
    second = seed_demo(client)
    assert second["created"] == []
    assert set(second["existing"]) == {"u_demo", "c_warm", "c_hype"}
    order = [r["id"] for r in second["rerank"]["results"]]
    assert order.index("c_warm") < order.index("c_hype")
