"""Image loading helpers for multimodal judges.

No third-party dependency: images are read from disk and base64-encoded into ``data:``
URIs, with MIME sniffed from the file extension. HTTP(S) URIs and existing data URIs
are passed through untouched (the provider fetches them).
"""

from __future__ import annotations

import base64
from pathlib import Path

_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
}


def is_remote_or_data_uri(uri: str) -> bool:
    return uri.startswith(("http://", "https://", "data:"))


def mime_for(path: str) -> str:
    return _MIME_BY_EXT.get(Path(path).suffix.lower(), "application/octet-stream")


def load_as_data_uri(path: str) -> str:
    """Read a local image file and return a base64 ``data:`` URI."""
    raw = Path(path).read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_for(path)};base64,{b64}"


def resolve_image_uri(uri: str) -> str:
    """Return a provider-ready URI: remote/data URIs pass through, local paths inline."""
    if is_remote_or_data_uri(uri):
        return uri
    return load_as_data_uri(uri)
