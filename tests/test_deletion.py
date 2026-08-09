import pytest

pytest.importorskip("numpy")

from tastebench.tastegraph.graph.backends import MemoryBackend


def _make_qdrant():
    pytest.importorskip("qdrant_client")
    from tastebench.tastegraph.graph.backends.qdrant import QdrantBackend

    return QdrantBackend(collection="del_test", dim=3, location=":memory:")


def _backend(kind):
    return MemoryBackend() if kind == "memory" else _make_qdrant()


@pytest.fixture(params=["memory", "qdrant"])
def backend(request):
    b = _backend(request.param)
    b.add("a", [1.0, 0.0, 0.0])
    b.add("b", [0.0, 1.0, 0.0])
    b.add("c", [0.0, 0.0, 1.0])
    return b


def test_remove_deletes_and_compacts(backend):
    assert backend.remove("b") is True
    assert "b" not in backend
    assert len(backend) == 2
    # surviving vectors still score correctly (compaction didn't corrupt the index)
    top = backend.knn([1.0, 0.0, 0.0], k=3)
    ids = [i for i, _ in top]
    assert "b" not in ids and "a" in ids
    assert backend.score_ids([0.0, 0.0, 1.0], ["c"])["c"] == pytest.approx(1.0, abs=1e-5)


def test_remove_is_idempotent(backend):
    assert backend.remove("b") is True
    assert backend.remove("b") is False


def test_re_add_after_remove(backend):
    backend.remove("a")
    backend.add("a", [0.5, 0.5, 0.0])
    assert "a" in backend
    assert len(backend) == 3


def test_engine_and_registry_hard_delete():
    from tastebench.tastegraph import TasteGraphEngine
    from tastebench.tastegraph.entities.registry import EntityError, get_registry
    from tastebench.tastegraph.entities.schema import Entity

    reg = get_registry(TasteGraphEngine())
    reg.create(Entity(id="c1", type="content", content="minimal dress"))
    reg.create(Entity(id="c2", type="content", content="street hoodie"))
    assert "c1" in reg.engine.index

    reg.delete("c1")
    assert "c1" not in reg.engine.index  # hard-removed from the vector index
    assert "c1" not in reg.engine.store
    assert "c1" not in reg.visible_content_ids()
    with pytest.raises(EntityError):
        reg.get("c1")
