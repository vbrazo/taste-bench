"""Asset and 7-dimension fingerprint schema (Layer 1).

Every asset is fingerprinted across seven dimensions; the flattened leaf fields are the
"40+ attributes per asset". The schema is intentionally permissive (most leaves optional)
so both the mock analyzer and a real VLM can populate what they can.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

AssetType = Literal["text", "image", "audio", "video"]


class Asset(BaseModel):
    """A single catalog item to be fingerprinted."""

    id: str
    type: AssetType = "image"
    uri: Optional[str] = None
    content: Optional[str] = None
    duration_s: Optional[float] = None  # audio/video length
    frame_uris: list[str] = Field(default_factory=list)  # pre-sampled video frames, if any
    metadata: dict = Field(default_factory=dict)

    def render(self) -> str:
        if self.content is not None:
            return self.content
        return f"[{self.type} asset: {self.uri}]"


# ---- the seven dimensions --------------------------------------------------

class Semantic(BaseModel):
    caption: str = ""
    entities: list[str] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)


class Emotional(BaseModel):
    mood: str = ""
    tone: str = ""
    sentiment: float = 0.0  # -1..1


class Aesthetic(BaseModel):
    style: str = ""
    palette: list[str] = Field(default_factory=list)  # hex or names
    composition: str = ""


class Technical(BaseModel):
    resolution: str = ""
    sharpness: float = 0.0  # 0..1
    quality: float = 0.0  # 0..1


class Contextual(BaseModel):
    location: str = ""
    era: str = ""
    trend: str = ""


class Intent(BaseModel):
    purpose: str = ""
    cta: str = ""
    commercial: float = 0.0  # 0..1


class Advanced(BaseModel):
    saliency: float = 0.0  # 0..1
    score: float = 0.0  # overall 0..1
    embedding: list[float] = Field(default_factory=list)


class AssetFingerprint(BaseModel):
    asset_id: str
    semantic: Semantic = Field(default_factory=Semantic)
    emotional: Emotional = Field(default_factory=Emotional)
    aesthetic: Aesthetic = Field(default_factory=Aesthetic)
    technical: Technical = Field(default_factory=Technical)
    contextual: Contextual = Field(default_factory=Contextual)
    intent: Intent = Field(default_factory=Intent)
    advanced: Advanced = Field(default_factory=Advanced)

    def tags(self) -> list[str]:
        """Human-readable categorical tags used for profiles/agent-context."""
        out = [
            self.aesthetic.style,
            self.emotional.mood,
            self.contextual.trend,
            *self.aesthetic.palette,
        ]
        return [t for t in out if t]
