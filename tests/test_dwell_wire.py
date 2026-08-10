"""dwell / deep_* on the /track wire."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from tastebench.tastegraph import TasteGraphEngine
from tastebench.tastegraph.api.app import create_app
from tastebench.tastegraph.assets.schema import Asset
from tastebench.tastegraph.signals.schema import Signal, dwell_weight


def test_dwell_affects_user_taste():
    eng = TasteGraphEngine()
    eng.ingest([Asset(id="a1", type="text", content="quiet linen editorial")])
    before = eng.user_taste("u1")
    assert before.vector is None
    eng.track(Signal(user_id="u1", asset_id="a1", action="dwell", dwell_ms=20000))
    after = eng.user_taste("u1")
    assert after.vector is not None
    assert after.confidence > 0
    w = eng._signals["u1"][0].effective_weight()
    assert abs(w - dwell_weight(20000)) < 1e-9


def test_track_api_accepts_dwell_ms():
    eng = TasteGraphEngine()
    eng.ingest([Asset(id="a1", type="text", content="soft ceramic still")])
    client = TestClient(create_app(eng))
    r = client.post(
        "/track",
        json={
            "user_id": "u1",
            "asset_id": "a1",
            "action": "deep_read",
            "dwell_ms": None,
        },
    )
    assert r.status_code == 200
    assert eng.user_taste("u1").vector is not None
