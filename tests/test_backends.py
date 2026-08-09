import pytest

pytest.importorskip("numpy")

from tastebench.tastegraph.graph.backends import MemoryBackend, make_backend


def _make_qdrant():
    pytest.importorskip("qdrant_client")
    from tastebench.tastegraph.graph.backends.qdrant import QdrantBackend

    return QdrantBackend(collection="test", dim=3, location=":memory:")


BACKENDS = ["memory", "qdrant"]


def _backend(kind):
    if kind == "memory":
        return MemoryBackend()
    return _make_qdrant()


@pytest.fixture(params=BACKENDS)
def backend(request):
    return _backend(request.param)


def _populate(b):
    b.add("a", [1.0, 0.0, 0.0])
    b.add("b", [0.9, 0.1, 0.0])
    b.add("c", [0.0, 1.0, 0.0])
    return b


def test_len_and_contains(backend):
    _populate(backend)
    assert len(backend) == 3
    assert "a" in backend and "z" not in backend


def test_knn_orders_by_cosine(backend):
    _populate(backend)
    top = backend.knn([1.0, 0.0, 0.0], k=2)
    assert top[0][0] == "a"
    assert top[0][1] == pytest.approx(1.0, abs=1e-5)
    assert top[1][0] == "b"  # closer than c


def test_knn_exclude(backend):
    _populate(backend)
    top = backend.knn([1.0, 0.0, 0.0], k=2, exclude={"a"})
    assert "a" not in {aid for aid, _ in top}


def test_score_ids_subset(backend):
    _populate(backend)
    scores = backend.score_ids([0.0, 1.0, 0.0], ["a", "c"])
    assert scores["c"] > scores["a"]


def test_factory_default_is_memory():
    assert isinstance(make_backend("memory"), MemoryBackend)


def test_factory_rejects_unknown():
    with pytest.raises(ValueError):
        make_backend("nope")
