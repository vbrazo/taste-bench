"""Behavioral signal schema (Layer 2).

Signals are the anonymized behavioral events the capture SDK emits. ``user_id`` is an
opaque key — no PII. Each action carries an implicit-affinity weight.
"""

from __future__ import annotations

import time
from typing import Literal, Optional

from pydantic import BaseModel, Field

Action = Literal["view", "click", "like", "save", "dismiss"]

# Implicit affinity weights. save/like are strong positives; dismiss is negative.
ACTION_WEIGHTS: dict[str, float] = {
    "view": 0.2,
    "click": 0.5,
    "like": 1.0,
    "save": 1.2,
    "dismiss": -1.0,
}


class Signal(BaseModel):
    user_id: str
    asset_id: str
    action: Action
    weight: Optional[float] = None  # defaults from ACTION_WEIGHTS
    timestamp: float = Field(default_factory=lambda: time.time())
    session_id: Optional[str] = None

    def effective_weight(self) -> float:
        return self.weight if self.weight is not None else ACTION_WEIGHTS[self.action]
