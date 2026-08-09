"""JSONL read/write for preference datasets.

JSONL is the canonical format (spec section 7): streamable, Git-friendly, and
compatible with Hugging Face ``datasets``. Each line is one serialized
:class:`PreferenceExample`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator, Union

from .schema import PreferenceExample

PathLike = Union[str, Path]


def iter_jsonl(path: PathLike) -> Iterator[PreferenceExample]:
    """Stream examples from a JSONL file, skipping blank lines."""
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            yield PreferenceExample.model_validate(data)


def load_jsonl(path: PathLike) -> list[PreferenceExample]:
    """Load all examples from a JSONL file into a list."""
    return list(iter_jsonl(path))


def write_jsonl(path: PathLike, examples: Iterable[PreferenceExample]) -> int:
    """Write examples to a JSONL file. Returns the number of examples written."""
    count = 0
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex.model_dump_json(exclude_none=True))
            fh.write("\n")
            count += 1
    return count
