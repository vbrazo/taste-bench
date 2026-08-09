import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from tastebench import Benchmark, MockJudge
from tastebench.web.app import create_app


def test_leaderboard_and_disagreements(tmp_path, sample_path):
    bench = Benchmark.from_jsonl(sample_path)
    bench.evaluate(MockJudge()).save(tmp_path)

    app = create_app(results_dir=str(tmp_path), dataset_path=str(sample_path))
    client = TestClient(app)

    r = client.get("/")
    assert r.status_code == 200
    assert "Leaderboard" in r.text
    assert "mock" in r.text

    r2 = client.get("/disagreements/mock")
    assert r2.status_code == 200
    assert "model errors" in r2.text

    r3 = client.get("/dataset")
    assert r3.status_code == 200
    assert "Consensus" in r3.text


def test_empty_results(tmp_path):
    app = create_app(results_dir=str(tmp_path))
    client = TestClient(app)
    assert client.get("/").status_code == 200
