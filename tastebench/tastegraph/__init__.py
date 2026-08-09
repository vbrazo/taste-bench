"""TasteGraph — production taste infrastructure built on TasteBench.

Fingerprints assets across 7 VLM dimensions, captures behavioral signals, fuses both into
a joint-embedding taste graph, and exposes reranking / retrieval / agent-context.
Mock-first: everything runs offline; real VLM/embedding providers are optional.
"""

from __future__ import annotations

from .api.engine import TasteGraphEngine
from .assets.analyzer import MockAssetAnalyzer, VLMAssetAnalyzer
from .client import TasteGraphClient
from .entities.registry import EntityRegistry, get_registry
from .entities.schema import Entity, EntityType, Link
from .assets.schema import Asset, AssetFingerprint
from .assets.store import FingerprintStore, load_assets
from .graph.index import TasteGraphIndex
from .signals.capture import TasteGraphSDK, load_signals
from .signals.schema import Signal

__all__ = [
    "TasteGraphEngine",
    "Asset",
    "AssetFingerprint",
    "FingerprintStore",
    "load_assets",
    "MockAssetAnalyzer",
    "VLMAssetAnalyzer",
    "TasteGraphIndex",
    "TasteGraphSDK",
    "Signal",
    "load_signals",
    "TasteGraphClient",
    "Entity",
    "EntityType",
    "Link",
    "EntityRegistry",
    "get_registry",
]
