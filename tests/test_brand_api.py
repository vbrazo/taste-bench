"""Phase B: brand ingest, enhance, judge."""

import pytest

pytest.importorskip("numpy")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from tastebench.tastegraph import TasteGraphEngine
from tastebench.tastegraph.api.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app(TasteGraphEngine()))


def test_brand_ingest_enhance_judge(client, monkeypatch):
    monkeypatch.delenv("TASTEGRAPH_ENHANCE_MODEL", raising=False)
    monkeypatch.delenv("TASTEGRAPH_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("TASTEGRAPH_ASK_MODEL", raising=False)

    r = client.post(
        "/v1/brand/ingest",
        json={
            "id": "voice_founder",
            "type": "voice",
            "label": "Founder voice",
            "references": [
                {"id": "ref_warm", "content": "Warm specific quiet-luxury outreach, never a blast"},
                {"content": "Personal intro path before any cold ask"},
            ],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["brand"]["id"] == "voice_founder"
    assert len(data["linked"]) == 2
    assert data["n_signals"] >= 2

    e = client.post(
        "/v1/enhance",
        json={
            "subject_id": "voice_founder",
            "prompt": "Hey, wanted to connect about a partnership.",
        },
    )
    assert e.status_code == 200
    assert e.json()["source"] == "template"
    assert "voice_founder" in e.json()["enhanced"]
    assert e.json()["subject_id"] == "voice_founder"

    j = client.post(
        "/v1/judge",
        json={
            "subject_id": "voice_founder",
            "candidates": [
                "Warm specific quiet-luxury note with a real intro path",
                "BLAST TO EVERYONE BUY NOW!!!",
            ],
        },
    )
    assert j.status_code == 200
    results = j.json()["results"]
    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]
    assert j.json()["source"] == "template"


def test_judge_requires_candidates(client):
    client.post(
        "/v1/brand/ingest",
        json={"id": "b1", "references": [{"content": "on brand"}]},
    )
    r = client.post("/v1/judge", json={"subject_id": "b1", "candidates": []})
    assert r.status_code == 400
