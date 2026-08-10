"""TasteGraphEngine — the façade wiring all four layers together (Layer 4)."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from ..assets.analyzer import MockAssetAnalyzer
from ..assets.schema import Asset
from ..assets.store import FingerprintStore
from ..graph.affinity import UserTaste, build_user_taste, rank_candidates
from ..graph.backends.memory import MemoryBackend
from ..graph.embedding import joint_embedding
from ..signals.profiles import taste_card, weighted_assets
from ..signals.schema import Signal


class TasteGraphEngine:
    """Taste infrastructure: ingest → track → rerank/retrieve/agent_context.

    ``analyzer`` defaults to the offline MockAssetAnalyzer so the engine runs with no keys;
    pass a VLMAssetAnalyzer for real fingerprints. ``backend`` is any VectorBackend (the
    default MemoryBackend needs no external service; pass a QdrantBackend to scale out).
    """

    def __init__(self, analyzer=None, backend=None):
        self.analyzer = analyzer or MockAssetAnalyzer()
        self.store = FingerprintStore()
        self.index = backend or MemoryBackend()
        self._signals: dict[str, list[Signal]] = defaultdict(list)
        self._api_calls = 0
        self._persist_dir = None  # set by persist.attach_persistence to arm autosave

    def _autosave(self) -> None:
        """Snapshot state to disk if durability is armed (see tastegraph.persist)."""
        if self._persist_dir is None:
            return
        from ..persist import save_tenant

        save_tenant(self, self._persist_dir)

    # ---- ingest / track ----------------------------------------------------

    def ingest(self, assets: list[Asset]) -> int:
        for asset in assets:
            fp = self.analyzer.analyze(asset)
            self.store.add(fp)
            self.index.add(asset.id, joint_embedding(fp))
        self._autosave()
        return len(assets)

    def remove_asset(self, asset_id: str) -> bool:
        """Hard-delete a content asset from both the vector index and the fingerprint store."""
        removed = self.index.remove(asset_id)
        self.store.remove(asset_id)
        return removed

    def track(self, signal: Signal) -> None:
        self._signals[signal.user_id].append(signal)
        self._autosave()

    def track_event(
        self,
        user_id: str,
        asset_id: str,
        action: str,
        *,
        weight: Optional[float] = None,
        dwell_ms: Optional[float] = None,
        session_id: Optional[str] = None,
    ) -> Signal:
        sig = Signal(
            user_id=user_id,
            asset_id=asset_id,
            action=action,  # type: ignore[arg-type]
            weight=weight,
            dwell_ms=dwell_ms,
            session_id=session_id,
        )
        self.track(sig)
        return sig

    # ---- taste -------------------------------------------------------------

    def user_taste(self, user_id: str) -> UserTaste:
        wa = weighted_assets(self._signals.get(user_id, []))
        return build_user_taste(user_id, wa, self.index)

    # ---- integration surface ----------------------------------------------

    def rerank(
        self, user_id: str, candidate_asset_ids: list[str], *, cold_start_seed: Optional[str] = None
    ) -> list[tuple[str, float]]:
        self._api_calls += 1
        taste = self.user_taste(user_id)
        return rank_candidates(taste, candidate_asset_ids, self.index, cold_start_seed=cold_start_seed)

    def retrieve(self, user_id: str, k: int = 10) -> list[tuple[str, float]]:
        """Top-k assets for a user by affinity (engaged assets excluded)."""
        self._api_calls += 1
        taste = self.user_taste(user_id)
        if taste.vector is None:
            return []
        engaged = {aid for aid, _ in weighted_assets(self._signals.get(user_id, []))}
        return self.index.knn(taste.vector, k=k, exclude=engaged)

    def similar_to(self, asset_id: str, k: int = 10) -> list[tuple[str, float]]:
        self._api_calls += 1
        if asset_id not in self.index:
            return []
        return self.index.knn(self.index.vector(asset_id), k=k, exclude={asset_id})

    def agent_context(self, subject_id: str) -> dict:
        """Structured taste read for an LLM/agent (user or brand subject)."""
        self._api_calls += 1
        taste = self.user_taste(subject_id)
        card = taste_card(subject_id, self._signals.get(subject_id, []), self.store)
        top = self.retrieve(subject_id, k=5)
        return {
            "user_id": subject_id,  # backward-compatible alias
            "subject_id": subject_id,
            "confidence": taste.confidence,
            "n_signals": len(self._signals.get(subject_id, [])),
            "resolved": taste.vector is not None,
            "principles": card.principles,
            "avoid": card.avoid,
            "top_assets": [aid for aid, _ in top],
        }

    # ---- dashboard metrics (slide 3) --------------------------------------

    def metrics(self) -> dict:
        import statistics

        confidences = [self.user_taste(u).confidence for u in self._signals] or [0.0]
        resolved = sum(1 for u in self._signals if self.user_taste(u).vector is not None)
        coverage = round(resolved / len(self._signals), 3) if self._signals else 0.0
        return {
            "people_in_graph": len(self._signals),
            "assets_in_graph": len(self.index),
            "signals_ingested": sum(len(v) for v in self._signals.values()),
            "api_calls": self._api_calls,
            "median_confidence": round(statistics.median(confidences), 3),
            "affinity_coverage": coverage,
        }
