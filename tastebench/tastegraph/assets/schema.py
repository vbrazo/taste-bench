"""Asset and 7-dimension fingerprint schema (Layer 1).

Every asset is fingerprinted across seven dimensions; the flattened leaf fields are the
"40+ attributes per asset". The schema is intentionally permissive (most leaves optional)
so both the mock analyzer and a real VLM can populate what they can.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, get_args, get_origin

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
    topics: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    colors_named: list[str] = Field(default_factory=list)


class Emotional(BaseModel):
    mood: str = ""
    tone: str = ""
    sentiment: float = 0.0  # -1..1
    energy: float = 0.0  # 0..1
    formality: float = 0.0  # 0..1


class Aesthetic(BaseModel):
    style: str = ""
    palette: list[str] = Field(default_factory=list)  # hex or names
    composition: str = ""
    silhouette: str = ""
    texture: str = ""
    lighting: str = ""
    density: str = ""


class Technical(BaseModel):
    resolution: str = ""
    sharpness: float = 0.0  # 0..1
    quality: float = 0.0  # 0..1
    aspect_ratio: str = ""
    noise: float = 0.0  # 0..1
    compression: str = ""


class Contextual(BaseModel):
    location: str = ""
    era: str = ""
    trend: str = ""
    season: str = ""
    culture: str = ""
    setting: str = ""
    audience: str = ""


class Intent(BaseModel):
    purpose: str = ""
    cta: str = ""
    commercial: float = 0.0  # 0..1
    channel: str = ""
    urgency: float = 0.0  # 0..1
    funnel_stage: str = ""


class Advanced(BaseModel):
    saliency: float = 0.0  # 0..1
    score: float = 0.0  # overall 0..1
    embedding: list[float] = Field(default_factory=list)
    complexity: float = 0.0  # 0..1
    uniqueness: float = 0.0  # 0..1
    coherence: float = 0.0  # 0..1


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
            self.aesthetic.silhouette,
            self.contextual.season,
            self.aesthetic.texture,
            self.contextual.setting,
            *self.aesthetic.palette,
            *self.semantic.topics[:3],
        ]
        return [t for t in out if t]


_DIM_MODELS = (Semantic, Emotional, Aesthetic, Technical, Contextual, Intent, Advanced)


def fingerprint_leaf_count() -> int:
    """Count scalar + list leaf fields across the seven dimension models (excludes nested models)."""
    n = 0
    for model in _DIM_MODELS:
        for name, field in model.model_fields.items():
            ann = field.annotation
            origin = get_origin(ann)
            if origin is list or ann in (str, float, int, bool) or (
                getattr(ann, "__origin__", None) is None and ann is not Any
            ):
                # count every declared leaf on the dimension models
                n += 1
            else:
                n += 1
        # simpler: every field on a dimension model is a leaf
    # Recalculate cleanly — every field on the seven dims is a leaf
    return sum(len(m.model_fields) for m in _DIM_MODELS)
