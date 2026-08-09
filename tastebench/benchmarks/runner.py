"""Runs a judge over a list of examples.

Kept deliberately small: sequential by default, with optional thread-pool parallelism
for I/O-bound LLM judges. No on-disk cache in this phase (the reproducibility metadata
is captured in the Results object instead).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from ..datasets.schema import PreferenceExample
from ..judges.base import Judge, Judgment


def run_judge(
    judge: Judge,
    examples: list[PreferenceExample],
    *,
    max_workers: Optional[int] = None,
) -> list[Judgment]:
    """Return one Judgment per example, order-aligned with ``examples``."""
    if max_workers and max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(judge.predict, examples))
    return judge.predict_batch(examples)
