"""Load locally-trained models back into the serving path (train -> serve bridge).

A trained reward model (rerank) or classifier judge (/v1/judge) is picked up from a directory
named by an env var. Loading is lazy, process-cached by path, and **never hard-fails**: if the
env is unset, the dir is missing, or the ``train`` extra (torch) isn't installed, the loader
returns ``None`` and callers fall back to the heuristic/affinity path.

    TASTEGRAPH_JUDGE_MODEL_DIR   -> TrainedJudge (classifier, A-vs-B)
    TASTEGRAPH_REWARD_MODEL_DIR  -> RewardModel  (Bradley-Terry scalar score)
"""

from __future__ import annotations

import os
from pathlib import Path

JUDGE_DIR_ENV = "TASTEGRAPH_JUDGE_MODEL_DIR"
REWARD_DIR_ENV = "TASTEGRAPH_REWARD_MODEL_DIR"

_judge_cache: dict[str, object] = {}
_reward_cache: dict[str, object] = {}


def load_judge():
    """Return a TrainedJudge for TASTEGRAPH_JUDGE_MODEL_DIR, or None if unavailable."""
    directory = os.environ.get(JUDGE_DIR_ENV)
    if not directory or not Path(directory).exists():
        return None
    if directory not in _judge_cache:
        try:
            from ...judges.trained import TrainedJudge

            _judge_cache[directory] = TrainedJudge.from_dir(directory)
        except Exception:  # noqa: BLE001 - torch missing / bad dir -> graceful fallback
            _judge_cache[directory] = None
    return _judge_cache[directory]


def load_reward():
    """Return a RewardModel for TASTEGRAPH_REWARD_MODEL_DIR, or None if unavailable."""
    directory = os.environ.get(REWARD_DIR_ENV)
    if not directory or not Path(directory).exists():
        return None
    if directory not in _reward_cache:
        try:
            from ...training.reward import RewardModel

            _reward_cache[directory] = RewardModel.load(directory)
        except Exception:  # noqa: BLE001
            _reward_cache[directory] = None
    return _reward_cache[directory]


def reset_cache() -> None:
    """Clear cached models (tests that swap env between model dirs)."""
    _judge_cache.clear()
    _reward_cache.clear()
