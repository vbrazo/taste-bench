import pytest

pytest.importorskip("sklearn")
pytest.importorskip("numpy")

from tastebench.evaluation.clustering import cluster_rationales
from tastebench.evaluation.disagreement import Disagreement


def _dis(id, rationale, tags=None):
    return Disagreement(
        example_id=id,
        task="t",
        model_choice="A",
        consensus_choice="B",
        human_agreement=1.0,
        is_ambiguous=False,
        model_rationale=rationale,
        tags=tags or [],
    )


def _fake_embedder(texts):
    """Deterministic 2-D embedding: 'complex'-ish -> one corner, 'clean'-ish -> other."""
    import numpy as np

    out = []
    for t in texts:
        busy = float("complex" in t or "detailed" in t or "impact" in t)
        calm = float("clean" in t or "minimal" in t or "restrained" in t)
        out.append([busy, calm])
    return np.asarray(out)


def test_clusters_group_similar_rationales():
    disagreements = [
        _dis("1", "A has more complex detailed impact"),
        _dis("2", "A shows complex detailed visual impact"),
        _dis("3", "A is clean minimal and restrained"),
        _dis("4", "A feels clean minimal restrained"),
    ]
    clusters = cluster_rationales(disagreements, k=2, embedder=_fake_embedder)
    assert len(clusters) == 2
    # each cluster should hold the two like-minded rationales
    sizes = sorted(c.size for c in clusters)
    assert sizes == [2, 2]


def test_single_item_returns_one_cluster():
    clusters = cluster_rationales([_dis("1", "only one")], embedder=_fake_embedder)
    assert len(clusters) == 1
    assert clusters[0].size == 1
