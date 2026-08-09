"""Audio/video probing for ingestion (Item 4; needs 'av' extra).

``sample_frames`` extracts still frames from a video (PyAV); ``transcribe`` turns audio (or
a video's audio track) into text (faster-whisper). ``MockMediaProbe`` provides deterministic
offline stand-ins so the pipeline and tests run with no media libraries installed.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Protocol


class MediaProbe(Protocol):
    def sample_frames(self, video_uri: str, n: int = 4) -> list[str]: ...
    def transcribe(self, uri: str) -> str: ...


class MockMediaProbe:
    """Deterministic, dependency-free media probe for offline use/tests."""

    def sample_frames(self, video_uri: str, n: int = 4) -> list[str]:
        # tiny deterministic 1x1 PNG data URIs, one per "frame"
        out = []
        for i in range(n):
            seed = hashlib.sha256(f"{video_uri}:{i}".encode()).digest()[:3]
            png = _solid_png(seed)
            out.append("data:image/png;base64," + base64.b64encode(png).decode("ascii"))
        return out

    def transcribe(self, uri: str) -> str:
        h = hashlib.sha256(uri.encode()).hexdigest()[:8]
        return f"[mock transcript for {uri} #{h}]"


class AVMediaProbe:  # pragma: no cover - requires the 'av' extra + media files
    """Real probe using PyAV (frames) and faster-whisper (transcription)."""

    def __init__(self, whisper_model: str = "base"):
        self._whisper_model_name = whisper_model
        self._whisper = None

    def sample_frames(self, video_uri: str, n: int = 4) -> list[str]:
        import av

        container = av.open(video_uri)
        stream = container.streams.video[0]
        total = stream.frames or 0
        step = max(1, total // n) if total else 1
        frames: list[str] = []
        for i, frame in enumerate(container.decode(video=0)):
            if i % step == 0:
                img = frame.to_image()
                frames.append(_image_to_data_uri(img))
                if len(frames) >= n:
                    break
        container.close()
        return frames

    def transcribe(self, uri: str) -> str:
        from faster_whisper import WhisperModel

        if self._whisper is None:
            self._whisper = WhisperModel(self._whisper_model_name)
        segments, _ = self._whisper.transcribe(uri)
        return " ".join(seg.text for seg in segments).strip()


def _solid_png(rgb) -> bytes:
    import struct
    import zlib

    w = h = 1
    raw = b"\x00" + bytes(rgb)

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _image_to_data_uri(img) -> str:  # pragma: no cover - PIL path
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
