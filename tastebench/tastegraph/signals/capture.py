"""Signal capture client — Python stand-in for the JS capture SDK (Layer 2).

Wire format: one JSON object per line matching :class:`Signal`. A future JS ``@…/sdk``
shim would POST the identical JSON to ``POST /track``; this class writes the same records
to a local JSONL event log so the whole pipeline runs in-process and offline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .schema import Action, Signal

PathLike = Union[str, Path]


class TasteGraphSDK:
    """Append-only signal logger.

    Usage::

        sdk = TasteGraphSDK("events.jsonl")
        sdk.track("u1", "asset_3", "like")
    """

    def __init__(self, log_path: Optional[PathLike] = None):
        self.log_path = Path(log_path) if log_path else None
        self._buffer: list[Signal] = []
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def track(
        self,
        user_id: str,
        asset_id: str,
        action: Action,
        *,
        session_id: Optional[str] = None,
        weight: Optional[float] = None,
        dwell_ms: Optional[float] = None,
    ) -> Signal:
        sig = Signal(
            user_id=user_id,
            asset_id=asset_id,
            action=action,
            session_id=session_id,
            weight=weight,
            dwell_ms=dwell_ms,
        )
        self._buffer.append(sig)
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(sig.model_dump_json())
                fh.write("\n")
        return sig

    def signals(self) -> list[Signal]:
        return list(self._buffer)


def load_signals(path: PathLike) -> list[Signal]:
    out: list[Signal] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(Signal.model_validate_json(line))
    return out
