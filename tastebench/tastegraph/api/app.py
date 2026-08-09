"""FastAPI JSON service for TasteGraph (Layer 4; needs 'web' extra).

API-only: the frontend lives entirely in the React app (``tastegraph-web/``). Multi-tenant —
every route resolves a per-tenant engine from the ``X-API-Key`` header via a
:class:`TenantStore`. With no key config the app runs in single-tenant dev mode. CORS is
enabled so the browser SPA can call the API cross-origin.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ..assets.schema import Asset
from .engine import TasteGraphEngine
from .tenancy import TenantStore


def _require_fastapi():
    try:
        import fastapi  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "The TasteGraph API requires the 'web' extra: pip install 'tastebench[web]'"
        ) from exc


class IngestBody(BaseModel):
    assets: list[Asset]


class TrackBody(BaseModel):
    user_id: str
    asset_id: str
    action: str


class RerankBody(BaseModel):
    user_id: str
    candidates: list[str]
    cold_start_seed: Optional[str] = None


class RegionsBody(BaseModel):
    asset_ids: Optional[list[str]] = None


def create_app(
    engine: Optional[TasteGraphEngine] = None,
    tenant_store: Optional[TenantStore] = None,
    limiter=None,
    cors_origins: Optional[list[str]] = None,
):
    """Build the JSON API.

    Pass ``tenant_store`` for multi-tenant auth. For backward compatibility, passing a bare
    ``engine`` (or nothing) creates a single-tenant dev store wrapping it. ``limiter`` is an
    optional :class:`RateLimiter`. ``cors_origins`` sets the allowed browser origins
    (defaults to ``["*"]`` for local dev).
    """
    _require_fastapi()
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse

    if tenant_store is None:
        base = engine or TasteGraphEngine()
        tenant_store = TenantStore(engine_factory=lambda _t: base)

    app = FastAPI(title="TasteGraph")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if limiter is not None and limiter.enabled:
        @app.middleware("http")
        async def _rate_limit(request: Request, call_next):
            if request.url.path == "/health":
                return await call_next(request)
            key = request.headers.get("x-api-key") or "__anon__"
            retry = limiter.check(key)
            if retry is not None:
                return JSONResponse(
                    {"detail": "Rate limit exceeded."},
                    status_code=429,
                    headers={"Retry-After": str(retry)},
                )
            return await call_next(request)

    def require_engine(x_api_key: Optional[str] = Header(default=None)) -> TasteGraphEngine:
        eng = tenant_store.resolve(x_api_key)
        if eng is None:
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")
        return eng

    @app.get("/health")
    def health():
        """Unauthenticated liveness probe (used by the Docker HEALTHCHECK)."""
        return {"status": "ok", "tenants": len(tenant_store._engines)}

    @app.get("/")
    def root():
        """API index — the UI lives in the React app (tastegraph-web/)."""
        return {"service": "tastegraph", "docs": "/docs", "health": "/health", "api": "/v1"}

    @app.post("/ingest")
    def ingest(body: IngestBody, eng: TasteGraphEngine = Depends(require_engine)):
        n = eng.ingest(body.assets)
        return {"ingested": n, "assets_in_graph": len(eng.index)}

    @app.post("/track")
    def track(body: TrackBody, eng: TasteGraphEngine = Depends(require_engine)):
        eng.track_event(body.user_id, body.asset_id, body.action)
        return {"ok": True}

    @app.post("/rerank")
    def rerank(body: RerankBody, eng: TasteGraphEngine = Depends(require_engine)):
        ranked = eng.rerank(body.user_id, body.candidates, cold_start_seed=body.cold_start_seed)
        return {"ranked": [{"asset_id": a, "score": s} for a, s in ranked]}

    @app.get("/retrieve")
    def retrieve(user_id: str, k: int = 10, eng: TasteGraphEngine = Depends(require_engine)):
        return {"results": [{"asset_id": a, "score": s} for a, s in eng.retrieve(user_id, k=k)]}

    @app.get("/agent-context/{user_id}")
    def agent_context(user_id: str, eng: TasteGraphEngine = Depends(require_engine)):
        return eng.agent_context(user_id)

    @app.get("/metrics")
    def metrics(eng: TasteGraphEngine = Depends(require_engine)):
        return eng.metrics()

    @app.post("/regions")
    def regions(body: RegionsBody, eng: TasteGraphEngine = Depends(require_engine)):
        from ..graph.clustering import cluster_assets

        # cluster the engaged subset if given, else the whole catalog
        ids = body.asset_ids or eng.store.ids()
        ids = [i for i in ids if i in eng.store and i in eng.index]
        if not ids:
            return {"regions": []}
        vecs = [list(eng.index.vector(i)) for i in ids]
        tags = [eng.store.get(i).tags() for i in ids]
        regs = cluster_assets(vecs, ids, tags)
        return {"regions": [r.to_dict() for r in regs]}

    @app.get("/explain/{user_id}")
    def explain(user_id: str, eng: TasteGraphEngine = Depends(require_engine)):
        from .explain import explain_taste

        return explain_taste(eng, user_id)

    # Galya-inspired /v1 entity API (facade over the same per-tenant engines).
    from .v1 import build_v1_router

    app.include_router(build_v1_router(require_engine))

    return app
