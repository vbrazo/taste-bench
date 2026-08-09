"""Taste profiles and Taste Cards (spec sections 14-15).

Minimal for this phase: a data structure plus YAML (Taste Card) load/dump. The
personalized reward-model machinery is deferred.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import yaml
from pydantic import BaseModel, Field

PathLike = Union[str, Path]


class TasteProfile(BaseModel):
    """A human-readable, inspectable description of a taste (a "Taste Card")."""

    name: str
    principles: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    # Ids of preferred / rejected examples, for later preference-learning.
    preferred_examples: list[str] = Field(default_factory=list)
    rejected_examples: list[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: PathLike) -> "TasteProfile":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def to_yaml(self, path: Optional[PathLike] = None) -> str:
        text = yaml.safe_dump(self.model_dump(exclude_none=True), sort_keys=False)
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text

    def as_prompt_context(self) -> str:
        """Render the card as text suitable for injecting into a judge prompt."""
        parts = [f"Taste profile: {self.name}"]
        if self.principles:
            parts.append("Principles: " + ", ".join(self.principles))
        if self.preferences:
            parts.append("Prefers: " + ", ".join(self.preferences))
        if self.avoid:
            parts.append("Avoids: " + ", ".join(self.avoid))
        return "\n".join(parts)
