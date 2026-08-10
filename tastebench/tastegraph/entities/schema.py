"""Unified entity model (Galya-inspired).

Everything is an Entity: users, content, or a registered custom type. A user entity builds
taste by *linking* to content entities; content entities are what gets tasted/searched.
"""

from __future__ import annotations

import time
from typing import Literal, Optional

from pydantic import BaseModel, Field

EntityKind = Literal["user", "content", "brand"]


class EntityType(BaseModel):
    """A registered entity classification. ``kind`` decides taste behavior."""

    name: str
    kind: EntityKind
    schema_: Optional[dict] = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


class Entity(BaseModel):
    id: str
    type: str = "content"  # "user", "content", "brand", "voice", or a custom type name
    content: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: float = Field(default_factory=lambda: time.time())
    hidden: bool = False  # soft-delete flag


class Link(BaseModel):
    source_id: str  # user or brand entity
    target_id: str  # content entity
    action: str = "like"
    weight: Optional[float] = None
    ts: float = Field(default_factory=lambda: time.time())
