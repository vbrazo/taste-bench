"""Galya-inspired /v1 entity API — a thin facade over TasteGraphEngine.

The reference loop: create a user → create content → link (build taste) → query
(search / rerank / ask / explain / clusters). Every route resolves a per-tenant engine via
``require_engine`` and operates on its lazily-attached EntityRegistry.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ..entities.registry import EntityError, get_registry
from ..entities.schema import Entity, EntityType, Link
from .engine import TasteGraphEngine


class EntityBody(BaseModel):
    id: str
    type: str = "content"
    content: Optional[str] = None
    metadata: dict = {}


class TypeBody(BaseModel):
    name: str
    kind: str  # "user" | "content"


class LinkBody(BaseModel):
    target_id: str
    action: str = "like"
    weight: Optional[float] = None


class SearchBody(BaseModel):
    user_id: Optional[str] = None
    seed_id: Optional[str] = None
    k: int = 10


class RerankBody(BaseModel):
    user_id: str
    candidates: list[str]


class AskBody(BaseModel):
    user_id: str
    question: str
    k: int = 5


def build_v1_router(require_engine):
    """Return an APIRouter mounted at /v1, using the app's tenant auth dependency."""
    from fastapi import APIRouter, Depends, HTTPException

    router = APIRouter(prefix="/v1", tags=["v1"])

    def _reg(engine: TasteGraphEngine):
        return get_registry(engine)

    def _guard(fn):
        try:
            return fn()
        except EntityError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    def _asset_text(engine: TasteGraphEngine, asset_id: str) -> str:
        if asset_id in engine.store:
            cap = engine.store.get(asset_id).semantic.caption
            if cap:
                return cap
        return asset_id

    # ---- entities ----------------------------------------------------------

    @router.post("/entity")
    def create_entity(body: EntityBody, engine: TasteGraphEngine = Depends(require_engine)):
        reg = _reg(engine)
        ent = _guard(lambda: reg.create(Entity(**body.model_dump())))
        return ent.model_dump()

    @router.get("/entity/types")
    def list_types(engine: TasteGraphEngine = Depends(require_engine)):
        return {"types": [t.model_dump(by_alias=True) for t in _reg(engine).list_types()]}

    @router.get("/entities")
    def list_entities(type: Optional[str] = None, engine: TasteGraphEngine = Depends(require_engine)):
        return {"entities": [e.model_dump() for e in _reg(engine).list(type)]}

    @router.post("/entity/type")
    def create_type(body: TypeBody, engine: TasteGraphEngine = Depends(require_engine)):
        reg = _reg(engine)
        et = _guard(lambda: reg.register_type(EntityType(name=body.name, kind=body.kind)))  # type: ignore[arg-type]
        return et.model_dump(by_alias=True)

    @router.get("/entity/{entity_id}")
    def get_entity(entity_id: str, engine: TasteGraphEngine = Depends(require_engine)):
        return _guard(lambda: _reg(engine).get(entity_id)).model_dump()

    @router.delete("/entity/{entity_id}")
    def delete_entity(entity_id: str, engine: TasteGraphEngine = Depends(require_engine)):
        _guard(lambda: _reg(engine).delete(entity_id))
        return {"ok": True}

    @router.post("/entity/{entity_id}/link")
    def link_entity(entity_id: str, body: LinkBody, engine: TasteGraphEngine = Depends(require_engine)):
        reg = _reg(engine)
        sig = _guard(
            lambda: reg.link(Link(source_id=entity_id, target_id=body.target_id, action=body.action, weight=body.weight))
        )
        return {"linked": True, "action": sig.action, "weight": sig.effective_weight()}

    # ---- queries -----------------------------------------------------------

    @router.post("/search")
    def search(body: SearchBody, engine: TasteGraphEngine = Depends(require_engine)):
        if body.user_id:
            results = engine.retrieve(body.user_id, k=body.k)
        elif body.seed_id:
            results = engine.similar_to(body.seed_id, k=body.k)
        else:
            raise HTTPException(status_code=400, detail="Provide user_id or seed_id.")
        return {"results": [{"id": a, "score": s} for a, s in results]}

    @router.post("/rerank")
    def rerank(body: RerankBody, engine: TasteGraphEngine = Depends(require_engine)):
        from .trained_models import load_reward

        reward = load_reward()
        if reward is not None:
            task = f"Which asset better matches {body.user_id}'s taste?"
            scored = [
                (cid, reward.score(task, _asset_text(engine, cid)))
                for cid in body.candidates
            ]
            scored.sort(key=lambda t: t[1], reverse=True)
            return {"results": [{"id": a, "score": round(s, 4)} for a, s in scored], "mode": "reward"}
        ranked = engine.rerank(body.user_id, body.candidates)
        return {"results": [{"id": a, "score": s} for a, s in ranked], "mode": "affinity"}

    @router.post("/ask")
    def ask_route(body: AskBody, engine: TasteGraphEngine = Depends(require_engine)):
        from .ask import ask

        return ask(engine, body.user_id, body.question, k=body.k)

    @router.post("/explain")
    def explain_route(body: RerankBody, engine: TasteGraphEngine = Depends(require_engine)):
        from .explain import explain_taste

        return explain_taste(engine, body.user_id)

    @router.get("/clusters")
    def clusters(engine: TasteGraphEngine = Depends(require_engine)):
        return {"clusters": _compute_clusters(engine)}

    @router.get("/cluster/{cluster_id}")
    def cluster_detail(cluster_id: str, engine: TasteGraphEngine = Depends(require_engine)):
        for c in _compute_clusters(engine):
            if c["id"] == cluster_id:
                return c
        raise HTTPException(status_code=404, detail="No such cluster.")

    @router.get("/skills")
    def skills():
        """OpenAI-style agent tool schemas for TasteGraph."""
        from ..skills import skills_payload

        return skills_payload()

    @router.post("/brand/ingest")
    def brand_ingest(body: dict, engine: TasteGraphEngine = Depends(require_engine)):
        from .brand import BrandIngestBody, ingest_brand

        parsed = BrandIngestBody(**body)
        return _guard(lambda: ingest_brand(engine, parsed))

    @router.post("/enhance")
    def enhance_route(body: dict, engine: TasteGraphEngine = Depends(require_engine)):
        from .brand import EnhanceBody, enhance

        parsed = EnhanceBody(**body)
        return enhance(engine, parsed.subject_id, parsed.prompt)

    @router.post("/judge")
    def judge_route(body: dict, engine: TasteGraphEngine = Depends(require_engine)):
        from .brand import JudgeBody, judge

        parsed = JudgeBody(**body)
        return _guard(lambda: judge(engine, parsed.subject_id, parsed.candidates))

    # ---- training export (serve -> train bridge) ---------------------------

    @router.get("/export/pairs")
    def export_pairs(format: str = "json", engine: TasteGraphEngine = Depends(require_engine)):
        """Preference pairs derived from accumulated signals (feeds RewardModel/TrainableJudge)."""
        from dataclasses import asdict

        from ...training.dataset import to_pairwise_pairs
        from ...training.from_signals import signals_to_examples

        pairs = [asdict(p) for p in to_pairwise_pairs(signals_to_examples(engine))]
        if format == "jsonl":
            import json as _json

            from fastapi.responses import PlainTextResponse

            body = "".join(_json.dumps(p) + "\n" for p in pairs)
            return PlainTextResponse(body, media_type="application/x-ndjson")
        return {"pairs": pairs, "count": len(pairs)}

    @router.get("/export/features")
    def export_features(engine: TasteGraphEngine = Depends(require_engine)):
        """Per-subject taste feature vectors (for external models / offline analysis)."""
        features = []
        for subject_id in engine._signals:
            taste = engine.user_taste(subject_id)
            features.append(
                {
                    "subject_id": subject_id,
                    "confidence": taste.confidence,
                    "n_signals": len(engine._signals.get(subject_id, [])),
                    "vector": [float(x) for x in taste.vector] if taste.vector is not None else None,
                }
            )
        return {"features": features, "count": len(features)}

    return router


def _compute_clusters(engine: TasteGraphEngine) -> list[dict]:
    from ..graph.clustering import cluster_assets

    reg = get_registry(engine)
    ids = [i for i in reg.visible_content_ids() if i in engine.index] or [
        i for i in engine.store.ids() if i in engine.index
    ]
    if not ids:
        return []
    vecs = [list(engine.index.vector(i)) for i in ids]
    tags = [engine.store.get(i).tags() for i in ids]
    return [r.to_dict() for r in cluster_assets(vecs, ids, tags)]
