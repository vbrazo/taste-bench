"""Export a static asset+vector bundle for the browser SPA (Part B).

Runs the existing analyzer + joint_embedding over an asset set and writes a JSON bundle the
local-first web UI imports, so the browser can score affinity with no backend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from .assets.analyzer import MockAssetAnalyzer
from .assets.store import load_assets
from .graph.embedding import joint_embedding

PathLike = Union[str, Path]


def build_bundle(assets_path: PathLike, analyzer=None) -> dict:
    analyzer = analyzer or MockAssetAnalyzer()
    assets = load_assets(assets_path)
    out = []
    for a in assets:
        fp = analyzer.analyze(a)
        vec = joint_embedding(fp)
        out.append(
            {
                "id": a.id,
                "vec": [float(x) for x in vec],
                "tags": fp.tags(),
                "caption": fp.semantic.caption,
                "type": a.type,
                "uri": a.uri,
                # media playback fields (Item 2): pass through metadata when present
                "mediaUri": a.metadata.get("mediaUri") or (a.uri if a.type in ("video", "audio", "image") else None),
                "posterUri": a.metadata.get("posterUri"),
            }
        )
    bundle = {"assets": out}
    regions = _precompute_regions(out)
    if regions is not None:
        bundle["regions"] = regions
    return bundle


def _precompute_regions(assets: list[dict]):
    """Catalog-level regions for the offline app. Returns None if sklearn is unavailable."""
    try:
        from .graph.clustering import cluster_assets
    except ImportError:  # pragma: no cover
        return None
    try:
        regions = cluster_assets(
            [a["vec"] for a in assets],
            [a["id"] for a in assets],
            [a["tags"] for a in assets],
        )
    except ImportError:
        return None
    return [r.to_dict() for r in regions]


def export_bundle(assets_path: PathLike, out_json: PathLike, analyzer=None) -> int:
    bundle = build_bundle(assets_path, analyzer=analyzer)
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return len(bundle["assets"])
