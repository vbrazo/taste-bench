"""Behavioral signal schema (Layer 2).

Signals are the anonymized behavioral events the capture SDK emits. ``user_id`` is an
opaque key — no PII. Each action carries an implicit-affinity weight.
"""

from __future__ import annotations

import time
from typing import Literal, Optional

from pydantic import BaseModel, Field

Action = Literal["view", "click", "like", "save", "dismiss", "dwell", "deep_scroll", "deep_read"]

# Implicit affinity weights. save/like are strong positives; dismiss is negative.
# dwell base is 0 — scaled by dwell_ms via dwell_weight (mirrors sdk-js affinity.ts).
ACTION_WEIGHTS: dict[str, float] = {
    "view": 0.2,
    "click": 0.5,
    "like": 1.0,
    "save": 1.2,
    "dismiss": -1.0,
    "dwell": 0.0,
    "deep_scroll": 0.6,
    "deep_read": 0.8,
}


def dwell_weight(dwell_ms: float) -> float:
    """Dwell contributes up to ~+0.8, saturating around 30s of attention."""
    seconds = max(0.0, float(dwell_ms)) / 1000.0
    return 0.8 * (1.0 - 1.0 / (1.0 + seconds / 8.0))


class Signal(BaseModel):
    user_id: str
    asset_id: str
    action: Action
    weight: Optional[float] = None  # defaults from ACTION_WEIGHTS / dwell scaling
    timestamp: float = Field(default_factory=lambda: time.time())
    session_id: Optional[str] = None
    dwell_ms: Optional[float] = None

    def effective_weight(self) -> float:
        if self.weight is not None:
            return self.weight
        if self.action == "dwell":
            return dwell_weight(self.dwell_ms or 0.0)
        return ACTION_WEIGHTS[self.action]
