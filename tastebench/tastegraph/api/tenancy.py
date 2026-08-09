"""API-key auth and per-tenant isolation (Item 3).

A ``TenantStore`` holds one :class:`TasteGraphEngine` per tenant id, created on demand. An
``ApiKeyRegistry`` maps an ``X-API-Key`` header to a tenant id. When no key config is
supplied the store runs in **single-tenant dev mode**: any request (with or without a key)
resolves to one shared engine, so existing tests and the CLI keep working unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional, Union

from .engine import TasteGraphEngine

PathLike = Union[str, Path]
DEV_TENANT = "dev"


class ApiKeyRegistry:
    """Maps API keys to tenant ids. Empty registry == dev mode (auth disabled)."""

    def __init__(self, keys: Optional[dict[str, str]] = None):
        self._keys = dict(keys or {})

    @property
    def enforced(self) -> bool:
        return bool(self._keys)

    def tenant_for(self, api_key: Optional[str]) -> Optional[str]:
        if not self.enforced:
            return DEV_TENANT  # dev mode: everyone shares the dev tenant
        if api_key is None:
            return None
        return self._keys.get(api_key)

    @classmethod
    def from_file(cls, path: PathLike) -> "ApiKeyRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data)


class TenantStore:
    """Lazily creates and caches one engine per tenant."""

    def __init__(
        self,
        registry: Optional[ApiKeyRegistry] = None,
        engine_factory: Optional[Callable[[str], TasteGraphEngine]] = None,
    ):
        self.registry = registry or ApiKeyRegistry()
        self._factory = engine_factory or (lambda tenant: TasteGraphEngine())
        self._engines: dict[str, TasteGraphEngine] = {}

    def engine_for_tenant(self, tenant: str) -> TasteGraphEngine:
        if tenant not in self._engines:
            self._engines[tenant] = self._factory(tenant)
        return self._engines[tenant]

    def resolve(self, api_key: Optional[str]) -> Optional[TasteGraphEngine]:
        """Return the engine for the key, or None if auth is enforced and the key is bad."""
        tenant = self.registry.tenant_for(api_key)
        if tenant is None:
            return None
        return self.engine_for_tenant(tenant)
