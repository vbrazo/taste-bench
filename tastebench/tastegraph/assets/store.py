"""JSONL persistence for assets and fingerprints (Layer 1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Union

from .schema import Asset, AssetFingerprint

PathLike = Union[str, Path]


def load_assets(path: PathLike) -> list[Asset]:
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(Asset.model_validate_json(line))
    return out


class FingerprintStore:
    """In-memory fingerprint collection with JSONL save/load."""

    def __init__(self):
        self._by_id: dict[str, AssetFingerprint] = {}

    def add(self, fp: AssetFingerprint) -> None:
        self._by_id[fp.asset_id] = fp

    def get(self, asset_id: str) -> AssetFingerprint:
        return self._by_id[asset_id]

    def remove(self, asset_id: str) -> bool:
        return self._by_id.pop(asset_id, None) is not None

    def __contains__(self, asset_id: str) -> bool:
        return asset_id in self._by_id

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self) -> Iterator[AssetFingerprint]:
        return iter(self._by_id.values())

    def ids(self) -> list[str]:
        return list(self._by_id.keys())

    def save(self, path: PathLike) -> int:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for fp in self._by_id.values():
                fh.write(fp.model_dump_json())
                fh.write("\n")
        return len(self._by_id)

    @classmethod
    def load(cls, path: PathLike) -> "FingerprintStore":
        store = cls()
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    store.add(AssetFingerprint.model_validate_json(line))
        return store
