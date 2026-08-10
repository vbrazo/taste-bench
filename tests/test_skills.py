"""Agent skill pack (Taste OS Phase A)."""

pytest = __import__("pytest")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from tastebench.tastegraph import TasteGraphEngine
from tastebench.tastegraph.api.app import create_app
from tastebench.tastegraph.skills import list_tools, load_tools, skills_payload


EXPECTED = {
    "taste_context",
    "taste_search",
    "taste_rerank",
    "taste_ask",
    "taste_explain",
    "taste_metrics",
    "taste_brand_ingest",
    "taste_enhance",
    "taste_judge",
}


def test_load_tools_parses_expected_names():
    tools = load_tools()
    assert tools and all(t.get("type") == "function" for t in tools)
    assert set(list_tools()) == EXPECTED
    payload = skills_payload()
    assert set(payload["names"]) == EXPECTED


def test_v1_skills_route():
    client = TestClient(create_app(TasteGraphEngine()))
    r = client.get("/v1/skills")
    assert r.status_code == 200
    data = r.json()
    assert set(data["names"]) == EXPECTED
    assert len(data["tools"]) == len(EXPECTED)
