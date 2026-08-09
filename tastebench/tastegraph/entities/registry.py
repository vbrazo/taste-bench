"""Per-engine entity registry (Galya-inspired facade over TasteGraphEngine).

Maps the unified entity model onto engine primitives: content entities are ingested as
assets (fingerprinted + embedded), user entities are tracked ids, and a *link* is a signal
(the taste-building step). Custom types register a `kind` (user|content) that decides which
path an entity of that type follows.
"""

from __future__ import annotations

from typing import Optional

from ..assets.schema import Asset
from ..signals.schema import ACTION_WEIGHTS, Signal
from .schema import Entity, EntityType, Link


class EntityError(ValueError):
    pass


class EntityRegistry:
    """Attached to one TasteGraphEngine; isolates entity bookkeeping per tenant."""

    def __init__(self, engine):
        self.engine = engine
        self._entities: dict[str, Entity] = {}
        self._types: dict[str, EntityType] = {
            "user": EntityType(name="user", kind="user"),
            "content": EntityType(name="content", kind="content"),
        }

    # ---- types -------------------------------------------------------------

    def register_type(self, etype: EntityType) -> EntityType:
        self._types[etype.name] = etype
        return etype

    def list_types(self) -> list[EntityType]:
        return list(self._types.values())

    def kind_of(self, type_name: str) -> str:
        et = self._types.get(type_name)
        if et is None:
            raise EntityError(f"Unknown entity type {type_name!r}. Register it via /entity/type.")
        return et.kind

    # ---- entities ----------------------------------------------------------

    def create(self, entity: Entity) -> Entity:
        kind = self.kind_of(entity.type)
        if entity.id in self._entities and not self._entities[entity.id].hidden:
            raise EntityError(f"Entity {entity.id!r} already exists.")
        if kind == "content":
            if not (entity.content or entity.metadata.get("uri")):
                raise EntityError("Content entity requires 'content' or metadata.uri.")
            asset = Asset(
                id=entity.id,
                type=entity.metadata.get("asset_type", "text"),
                content=entity.content,
                uri=entity.metadata.get("uri"),
                metadata=entity.metadata,
            )
            self.engine.ingest([asset])
        # user entities need no engine work until they link
        self._entities[entity.id] = entity
        return entity

    def get(self, entity_id: str) -> Entity:
        ent = self._entities.get(entity_id)
        if ent is None or ent.hidden:
            raise EntityError(f"Entity {entity_id!r} not found.")
        return ent

    def list(self, type_name: Optional[str] = None) -> list[Entity]:
        return [
            e for e in self._entities.values()
            if not e.hidden and (type_name is None or e.type == type_name)
        ]

    def delete(self, entity_id: str) -> None:
        ent = self.get(entity_id)
        if self.kind_of(ent.type) == "user":
            self.engine._signals.pop(entity_id, None)
            self._entities.pop(entity_id, None)
        else:
            # hard delete: remove the vector + fingerprint, then drop the entity. Falls back
            # to a soft-delete (hide) only if the backend couldn't remove the vector.
            removed = self.engine.remove_asset(entity_id)
            if removed:
                self._entities.pop(entity_id, None)
            else:
                ent.hidden = True

    # ---- links (taste building) -------------------------------------------

    def link(self, link: Link) -> Signal:
        user = self._entities.get(link.source_id)
        content = self._entities.get(link.target_id)
        if user is None or self.kind_of(user.type) != "user":
            raise EntityError(f"Link source {link.source_id!r} must be a user entity.")
        if content is None or content.hidden or self.kind_of(content.type) != "content":
            raise EntityError(f"Link target {link.target_id!r} must be a content entity.")
        if link.action not in ACTION_WEIGHTS:
            raise EntityError(f"Unknown action {link.action!r}. One of {sorted(ACTION_WEIGHTS)}.")
        sig = Signal(user_id=link.source_id, asset_id=link.target_id, action=link.action, weight=link.weight)
        self.engine.track(sig)
        return sig

    def visible_content_ids(self) -> list[str]:
        return [e.id for e in self._entities.values() if not e.hidden and self.kind_of(e.type) == "content"]


def get_registry(engine) -> EntityRegistry:
    """Lazily attach a registry to an engine (per-tenant isolation for free)."""
    reg = getattr(engine, "entities", None)
    if reg is None:
        reg = EntityRegistry(engine)
        engine.entities = reg
    return reg
