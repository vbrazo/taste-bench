"""Build LiteLLM/OpenAI-style message content parts from candidates.

A text candidate becomes a ``{"type": "text", ...}`` part; an image candidate becomes
a ``{"type": "image_url", ...}`` part with its URI resolved (local files inlined as
base64 data URIs). This is the single place that knows how a candidate maps onto a
provider message, so both the text-only and multimodal judge paths share it.
"""

from __future__ import annotations

from ..datasets.schema import Candidate, PreferenceExample
from .image_utils import resolve_image_uri

ContentPart = dict


def text_part(text: str) -> ContentPart:
    return {"type": "text", "text": text}


def to_message_content(candidate: Candidate) -> ContentPart:
    """One content part for a single candidate's artifact."""
    if candidate.type == "image":
        uri = candidate.uri or ""
        return {"type": "image_url", "image_url": {"url": resolve_image_uri(uri)}}
    # text candidate: prefer inline content; fall back to its render()
    return text_part(candidate.render())


def has_image(example: PreferenceExample) -> bool:
    return any(c.type == "image" for c in example.candidates)


def build_multimodal_content(preamble: str, example: PreferenceExample, trailer: str) -> list[ContentPart]:
    """Interleave a text preamble, labeled candidate parts, and a trailing instruction."""
    parts: list[ContentPart] = [text_part(preamble)]
    for c in example.candidates:
        parts.append(text_part(f"Candidate {c.id}:"))
        parts.append(to_message_content(c))
    parts.append(text_part(trailer))
    return parts
