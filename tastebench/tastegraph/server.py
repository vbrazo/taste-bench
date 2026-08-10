"""Env-driven ASGI factory for hosting the TasteGraph API (Item 3).

Reads configuration from the environment so the same image runs locally and in a container:

  TASTEGRAPH_API_KEYS     JSON map of api-key -> tenant id (enables auth). Unset = dev mode.
  TASTEGRAPH_BACKEND      "memory" (default) or "qdrant".
  QDRANT_URL              Qdrant server URL (when backend=qdrant).
  QDRANT_API_KEY          Optional Qdrant auth.
  TASTEGRAPH_RATE_PER_MIN Per-key request rate (0/unset = unlimited).
  TASTEGRAPH_RATE_BURST   Burst size (defaults to the per-min rate).
  TASTEGRAPH_QUOTA_PER_DAY Per-key daily quota (0/unset = unlimited).

Usage: ``uvicorn tastebench.tastegraph.server:app`` (the module builds ``app`` on import).
"""

from __future__ import annotations

import json
import os

from .api.app import create_app
from .api.ratelimit import RateLimiter
from .api.tenancy import ApiKeyRegistry, TenantStore
from .api.engine import TasteGraphEngine
from .persist import DATA_DIR_ENV


def _backend_factory():
    kind = os.environ.get("TASTEGRAPH_BACKEND", "memory")
    if kind == "memory":
        return lambda _tenant: None  # None -> engine default (MemoryBackend)
    if kind == "qdrant":
        from .graph.backends.qdrant import QdrantBackend

        url = os.environ.get("QDRANT_URL")
        api_key = os.environ.get("QDRANT_API_KEY")

        def make(tenant: str):
            return QdrantBackend(collection=f"tg_{tenant}", url=url, api_key=api_key)

        return make
    raise ValueError(f"Unknown TASTEGRAPH_BACKEND {kind!r}")


def _limiter() -> RateLimiter:
    return RateLimiter(
        rate_per_min=float(os.environ.get("TASTEGRAPH_RATE_PER_MIN", 0) or 0),
        burst=int(os.environ["TASTEGRAPH_RATE_BURST"]) if os.environ.get("TASTEGRAPH_RATE_BURST") else None,
        max_per_day=int(os.environ.get("TASTEGRAPH_QUOTA_PER_DAY", 0) or 0),
    )


def build_app():
    backend_make = _backend_factory()
    keys_raw = os.environ.get("TASTEGRAPH_API_KEYS")
    registry = ApiKeyRegistry(json.loads(keys_raw)) if keys_raw else ApiKeyRegistry()

    def engine_factory(tenant: str) -> TasteGraphEngine:
        engine = TasteGraphEngine(backend=backend_make(tenant))
        if os.environ.get(DATA_DIR_ENV):
            from .persist import attach_persistence

            attach_persistence(engine, tenant)
        return engine

    store = TenantStore(registry, engine_factory=engine_factory)
    return create_app(tenant_store=store, limiter=_limiter())


app = build_app()
