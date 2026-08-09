"""TasteBench — open-source infrastructure for subjective AI evaluation."""

from __future__ import annotations

__version__ = "0.1.0"

from .benchmarks.benchmark import Benchmark, Results
from .datasets.loader import iter_jsonl, load_jsonl, write_jsonl
from .datasets.schema import Candidate, ExpertJudgment, PreferenceExample
from .judges.base import Judge, Judgment
from .judges.human import HumanJudge
from .judges.llm import LLMJudge
from .judges.mock import MockJudge
from .profiles.taste_profile import TasteProfile

__all__ = [
    "__version__",
    "Benchmark",
    "Results",
    "PreferenceExample",
    "Candidate",
    "ExpertJudgment",
    "Judge",
    "Judgment",
    "MockJudge",
    "LLMJudge",
    "HumanJudge",
    "TasteProfile",
    "load_jsonl",
    "iter_jsonl",
    "write_jsonl",
]
