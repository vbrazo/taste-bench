"""Per-tenant JSONL durability for TasteGraph state (Phase 1).

Process-local state — the entity registry, engine signals, and fingerprint store — is
snapshotted to a tenant directory so a restart (or a new process pointed at the same
``TASTEGRAPH_DATA_DIR``) rebuilds the taste graph:

    {data_dir}/{tenant}/
      entities.jsonl      # registered types + Entity rows (tagged)
      signals.jsonl       # flattened Signal rows
      fingerprints.jsonl  # FingerprintStore.save / load

Saves are full rewrites (MVP): cheap at pilot scale and trivially consistent. ``load_tenant``
rebuilds vectors from persisted fingerprints via ``joint_embedding`` (no re-analysis, so a VLM
analyzer is never re-invoked), and only adds ids the vector backend is missing — idempotent for
both the in-memory and Qdrant backends.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

from .assets.store import FingerprintStore
from .entities.registry import get_registry
from .entities.schema import Entity, EntityType
from .graph.embedding import joint_embedding
from .signals.schema import Signal

PathLike = Union[str, Path]

DATA_DIR_ENV = "TASTEGRAPH_DATA_DIR"
DEFAULT_DATA_DIR = "./data/tastegraph_state"

ENTITIES_FILE = "entities.jsonl"
SIGNALS_FILE = "signals.jsonl"
FINGERPRINTS_FILE = "fingerprints.jsonl"


def data_root() -> Path:
    """Base directory for all tenant state, from the env (or the default)."""
    return Path(os.environ.get(DATA_DIR_ENV) or DEFAULT_DATA_DIR)


def tenant_dir(tenant: str, root: PathLike | None = None) -> Path:
    return Path(root or data_root()) / tenant


# ---- save ------------------------------------------------------------------


def save_tenant(engine, path: PathLike) -> None:
    """Full-rewrite snapshot of one engine's state to ``path`` (a tenant directory)."""
    reg = get_registry(engine)
    d = Path(path)
    d.mkdir(parents=True, exist_ok=True)

    # entities.jsonl — types first (so a load can resolve kinds), then entities.
    lines = [f'{{"rec":"type","data":{et.model_dump_json()}}}' for et in reg.list_types()]
    lines += [
        f'{{"rec":"entity","data":{ent.model_dump_json()}}}'
        for ent in reg._entities.values()
    ]
    (d / ENTITIES_FILE).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # signals.jsonl — flattened across users (user_id lives on each Signal).
    sig_lines = [
        sig.model_dump_json()
        for sigs in engine._signals.values()
        for sig in sigs
    ]
    (d / SIGNALS_FILE).write_text("\n".join(sig_lines) + ("\n" if sig_lines else ""), encoding="utf-8")

    # fingerprints.jsonl — reuse the store's own serializer.
    engine.store.save(d / FINGERPRINTS_FILE)


# ---- load ------------------------------------------------------------------


def load_tenant(engine, path: PathLike) -> bool:
    """Rebuild ``engine`` state from a tenant directory. Returns False if nothing was there.

    Populates the registry, signals, fingerprint store, and vector index directly (bypassing
    the create/track mutation methods) so no autosave fires and no content is re-analyzed.
    """
    d = Path(path)
    if not d.exists():
        return False

    reg = get_registry(engine)

    # 1. fingerprints -> store + vector index (rebuild vectors from fingerprints).
    fp_path = d / FINGERPRINTS_FILE
    if fp_path.exists():
        engine.store = FingerprintStore.load(fp_path)
        for fp in engine.store:
            if fp.asset_id not in engine.index:
                engine.index.add(fp.asset_id, joint_embedding(fp))

    # 2. entities + registered types.
    ent_path = d / ENTITIES_FILE
    if ent_path.exists():
        import json

        for line in ent_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("rec") == "type":
                et = EntityType.model_validate(rec["data"])
                reg._types[et.name] = et
            elif rec.get("rec") == "entity":
                ent = Entity.model_validate(rec["data"])
                reg._entities[ent.id] = ent

    # 3. signals.
    sig_path = d / SIGNALS_FILE
    if sig_path.exists():
        for line in sig_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                sig = Signal.model_validate_json(line)
                engine._signals[sig.user_id].append(sig)

    return True


def attach_persistence(engine, tenant: str, root: PathLike | None = None) -> None:
    """Load any persisted state for ``tenant`` then arm autosave on this engine."""
    d = tenant_dir(tenant, root)
    load_tenant(engine, d)
    engine._persist_dir = d
