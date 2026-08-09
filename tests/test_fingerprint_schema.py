"""Fingerprint schema depth (Taste OS Phase A)."""

from tastebench.tastegraph.assets.analyzer import MockAssetAnalyzer
from tastebench.tastegraph.assets.schema import Asset, fingerprint_leaf_count


def test_fingerprint_has_at_least_40_leaves():
    assert fingerprint_leaf_count() >= 40


def test_mock_analyzer_fills_new_leaves():
    fp = MockAssetAnalyzer().analyze(Asset(id="x1", content="minimal linen dress"))
    assert fp.semantic.topics
    assert fp.semantic.materials
    assert fp.semantic.colors_named
    assert 0 <= fp.emotional.energy <= 1
    assert fp.aesthetic.silhouette
    assert fp.aesthetic.texture
    assert fp.technical.aspect_ratio
    assert fp.contextual.season
    assert fp.intent.channel
    assert 0 <= fp.advanced.coherence <= 1
    tags = fp.tags()
    assert fp.aesthetic.style in tags or fp.emotional.mood in tags
