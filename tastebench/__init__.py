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

# Heavy / optional-dependency symbols are exposed lazily so a bare ``import tastebench``
# never requires an extra (torch, datasets, sentence-transformers, ...).
_LAZY = {
    "to_hf_dataset": ("tastebench.datasets.hf", "to_hf_dataset"),
    "from_hf_dataset": ("tastebench.datasets.hf", "from_hf_dataset"),
    "cluster_rationales": ("tastebench.evaluation.clustering", "cluster_rationales"),
    "to_pairwise_pairs": ("tastebench.training.dataset", "to_pairwise_pairs"),
    "TrainableJudge": ("tastebench.training.classifier", "TrainableJudge"),
    "TrainedJudge": ("tastebench.judges.trained", "TrainedJudge"),
    "RewardModel": ("tastebench.training.reward", "RewardModel"),
    "JudgeReward": ("tastebench.training.rl", "JudgeReward"),
    "RewardModelReward": ("tastebench.training.rl", "RewardModelReward"),
    # TasteGraph product surface
    "TasteGraphEngine": ("tastebench.tastegraph", "TasteGraphEngine"),
    "MemoryBackend": ("tastebench.tastegraph.graph.backends", "MemoryBackend"),
    "QdrantBackend": ("tastebench.tastegraph.graph.backends.qdrant", "QdrantBackend"),
    "TenantStore": ("tastebench.tastegraph.api.tenancy", "TenantStore"),
    "signals_to_examples": ("tastebench.training.from_signals", "signals_to_examples"),
}


def __getattr__(name: str):  # PEP 562 lazy attribute access
    if name in _LAZY:
        import importlib

        module_name, attr = _LAZY[name]
        return getattr(importlib.import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    # lazy / optional
    "to_hf_dataset",
    "from_hf_dataset",
    "cluster_rationales",
    "to_pairwise_pairs",
    "TrainableJudge",
    "TrainedJudge",
    "RewardModel",
    "JudgeReward",
    "RewardModelReward",
    "TasteGraphEngine",
    "MemoryBackend",
    "QdrantBackend",
    "TenantStore",
    "signals_to_examples",
]
