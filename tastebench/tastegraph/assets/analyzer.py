"""Asset analyzers (Layer 1): mock (offline) and VLM (LiteLLM-backed)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Optional, Protocol

from .schema import (
    Advanced,
    Aesthetic,
    Asset,
    AssetFingerprint,
    Contextual,
    Emotional,
    Intent,
    Semantic,
    Technical,
)

# Small deterministic vocabularies for the mock analyzer.
_STYLES = ["minimal", "editorial", "streetwear", "vintage", "luxe", "playful"]
_MOODS = ["calm", "bold", "moody", "warm", "energetic", "serene"]
_TRENDS = ["y2k", "quiet-luxury", "cottagecore", "techwear", "coastal", "grunge"]
_SILHOUETTES = ["relaxed", "tailored", "oversized", "fitted", "fluid"]
_TEXTURES = ["linen", "silk", "matte", "gloss", "knit", "denim"]
_LIGHTING = ["soft", "hard", "natural", "studio", "golden-hour"]
_DENSITY = ["sparse", "balanced", "dense"]
_SEASONS = ["spring", "summer", "fall", "winter", "all-season"]
_SETTINGS = ["studio", "street", "indoor", "outdoor", "editorial"]
_CHANNELS = ["social", "editorial", "pdp", "email", "ads"]
_FUNNEL = ["awareness", "consideration", "conversion"]
_PALETTES = [
    ["#2b2b2b", "#e8e2d6", "#8a8a8a"],
    ["#ff3366", "#111111", "#f5f5f5"],
    ["#7a9e7e", "#efe9dd", "#3b3b3b"],
    ["#1a237e", "#ff6f00", "#fafafa"],
]
_TOPICS = ["fashion", "lifestyle", "product", "portrait", "interior"]
_MATERIALS = ["cotton", "wool", "leather", "metal", "wood", "ceramic"]
_COLORS = ["sand", "ink", "blush", "olive", "ivory", "navy"]


class AssetAnalyzer(Protocol):
    def analyze(self, asset: Asset) -> AssetFingerprint: ...


def _hash_ints(key: str, n: int) -> list[int]:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return [digest[i % len(digest)] for i in range(n)]


class MockAssetAnalyzer:
    """Deterministic fingerprints from a hash of the asset id/content. No keys needed.

    ``embedding_dim`` controls the length of the pseudo-embedding so it lines up with the
    mock embedder used by the taste graph.
    """

    def __init__(self, embedding_dim: int = 32):
        self.embedding_dim = embedding_dim

    def analyze(self, asset: Asset) -> AssetFingerprint:
        key = f"{asset.id}:{asset.render()}"
        h = _hash_ints(key, 16)
        style = _STYLES[h[0] % len(_STYLES)]
        mood = _MOODS[h[1] % len(_MOODS)]
        trend = _TRENDS[h[2] % len(_TRENDS)]
        palette = _PALETTES[h[3] % len(_PALETTES)]
        score = round(0.4 + (h[4] % 60) / 100, 3)
        silhouette = _SILHOUETTES[h[8] % len(_SILHOUETTES)]
        texture = _TEXTURES[h[9] % len(_TEXTURES)]
        season = _SEASONS[h[10] % len(_SEASONS)]
        topic = _TOPICS[h[11] % len(_TOPICS)]

        emb = [((b / 255.0) * 2 - 1) for b in _hash_ints(key + ":emb", self.embedding_dim)]
        u01 = lambda i: round(h[i] / 255, 2)

        return AssetFingerprint(
            asset_id=asset.id,
            semantic=Semantic(
                caption=f"A {style} {asset.type} asset",
                entities=[style, trend],
                objects=["subject", "background"],
                topics=[topic, trend],
                materials=[_MATERIALS[h[12] % len(_MATERIALS)]],
                colors_named=[_COLORS[h[13] % len(_COLORS)], _COLORS[h[14] % len(_COLORS)]],
            ),
            emotional=Emotional(
                mood=mood,
                tone=mood,
                sentiment=round((h[5] % 200) / 100 - 1, 2),
                energy=u01(6),
                formality=u01(7),
            ),
            aesthetic=Aesthetic(
                style=style,
                palette=palette,
                composition="centered",
                silhouette=silhouette,
                texture=texture,
                lighting=_LIGHTING[h[15] % len(_LIGHTING)],
                density=_DENSITY[h[0] % len(_DENSITY)],
            ),
            technical=Technical(
                resolution="1024x1024",
                sharpness=round(h[6] / 255, 2),
                quality=score,
                aspect_ratio="1:1",
                noise=u01(8),
                compression="jpeg",
            ),
            contextual=Contextual(
                location="studio",
                era="contemporary",
                trend=trend,
                season=season,
                culture="global",
                setting=_SETTINGS[h[1] % len(_SETTINGS)],
                audience="general",
            ),
            intent=Intent(
                purpose="showcase",
                cta="shop",
                commercial=round(h[7] / 255, 2),
                channel=_CHANNELS[h[2] % len(_CHANNELS)],
                urgency=u01(9),
                funnel_stage=_FUNNEL[h[3] % len(_FUNNEL)],
            ),
            advanced=Advanced(
                saliency=round(h[0] / 255, 2),
                score=score,
                embedding=emb,
                complexity=u01(10),
                uniqueness=u01(11),
                coherence=u01(12),
            ),
        )


_VLM_PROMPT = """\
You are an expert visual/content analyst. Analyze the asset across SEVEN dimensions and
return ONLY a JSON object with exactly these keys:

{{
  "semantic": {{"caption": str, "entities": [str], "objects": [str], "topics": [str], "materials": [str], "colors_named": [str]}},
  "emotional": {{"mood": str, "tone": str, "sentiment": float -1..1, "energy": float 0..1, "formality": float 0..1}},
  "aesthetic": {{"style": str, "palette": [str hex], "composition": str, "silhouette": str, "texture": str, "lighting": str, "density": str}},
  "technical": {{"resolution": str, "sharpness": float 0..1, "quality": float 0..1, "aspect_ratio": str, "noise": float 0..1, "compression": str}},
  "contextual": {{"location": str, "era": str, "trend": str, "season": str, "culture": str, "setting": str, "audience": str}},
  "intent": {{"purpose": str, "cta": str, "commercial": float 0..1, "channel": str, "urgency": float 0..1, "funnel_stage": str}},
  "advanced": {{"saliency": float 0..1, "score": float 0..1, "complexity": float 0..1, "uniqueness": float 0..1, "coherence": float 0..1}}
}}

Task context: describe the asset's taste fingerprint for a personalization system.
"""


class VLMAssetAnalyzer:
    """LiteLLM-backed analyzer. Reuses the multimodal message builder from LLMJudge.

    The ``advanced.embedding`` is filled by ``embedder`` (a callable mapping a list of
    strings to vectors); if none is given the embedding is left empty and the taste graph
    falls back to attribute encoding only.
    """

    def __init__(self, model: str, embedder=None, temperature: float = 0.0, max_tokens: int = 700, media_probe=None):
        self.model = model
        self.embedder = embedder
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.media_probe = media_probe  # required for audio/video; see assets.media

    def _messages(self, asset: Asset) -> list[dict]:
        from ...judges.content import text_part, to_message_content
        from ...datasets.schema import Candidate

        if asset.type == "image" and asset.uri:
            cand = Candidate(id=asset.id, type="image", uri=asset.uri)
            return [{"role": "user", "content": [text_part(_VLM_PROMPT), to_message_content(cand)]}]

        if asset.type == "video" and asset.uri:
            # sample frames (pre-supplied or probed) + optional transcript, sent multimodally
            frames = asset.frame_uris
            transcript = ""
            if self.media_probe is not None:
                if not frames:
                    frames = self.media_probe.sample_frames(asset.uri)
                transcript = self.media_probe.transcribe(asset.uri)
            parts = [text_part(_VLM_PROMPT)]
            if transcript:
                parts.append(text_part("Transcript:\n" + transcript))
            for fi, furi in enumerate(frames):
                parts.append(text_part(f"Frame {fi}:"))
                parts.append(to_message_content(Candidate(id=f"{asset.id}#f{fi}", type="image", uri=furi)))
            return [{"role": "user", "content": parts}]

        if asset.type == "audio" and asset.uri:
            transcript = self.media_probe.transcribe(asset.uri) if self.media_probe else asset.render()
            return [{"role": "user", "content": _VLM_PROMPT + "\n\nAudio transcript:\n" + transcript}]

        return [{"role": "user", "content": _VLM_PROMPT + "\n\nAsset:\n" + asset.render()}]

    def analyze(self, asset: Asset) -> AssetFingerprint:
        import litellm  # lazy

        resp = litellm.completion(
            model=self.model,
            messages=self._messages(asset),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        text = resp["choices"][0]["message"]["content"]
        data = _parse_fingerprint_json(text)
        fp = AssetFingerprint(asset_id=asset.id, **data)
        if self.embedder is not None:
            vec = self.embedder([fp.semantic.caption or asset.render()])[0]
            fp.advanced.embedding = list(map(float, vec))
        return fp


def _parse_fingerprint_json(text: str) -> dict:
    """Tolerant JSON extraction, mirroring judges.llm._parse_judgment."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    # keep only recognised dimension keys; AssetFingerprint validates the rest
    allowed = {"semantic", "emotional", "aesthetic", "technical", "contextual", "intent", "advanced"}
    return {k: v for k, v in data.items() if k in allowed and isinstance(v, dict)}
