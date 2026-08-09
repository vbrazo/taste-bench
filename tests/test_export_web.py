from pathlib import Path

import pytest

pytest.importorskip("numpy")

from tastebench.tastegraph.export_web import build_bundle, export_bundle

DATA = Path(__file__).resolve().parents[1] / "data"


def test_bundle_shape():
    bundle = build_bundle(DATA / "tastegraph_assets.jsonl")
    assert "assets" in bundle
    assert len(bundle["assets"]) == 12
    a = bundle["assets"][0]
    assert {"id", "vec", "tags", "caption", "type", "uri"} <= set(a.keys())
    assert isinstance(a["vec"], list) and len(a["vec"]) > 0
    assert all(isinstance(x, float) for x in a["vec"])


def test_export_writes_file(tmp_path):
    out = tmp_path / "bundle.json"
    n = export_bundle(DATA / "tastegraph_assets.jsonl", out)
    assert n == 12
    assert out.exists()
