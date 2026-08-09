"""Disagreement analysis (spec sections 12-13).

Most evaluation stops at an accuracy number. TasteBench asks *why* the judge was
wrong, and distinguishes two very different cases:

- **model error**: the judge disagrees with a strong human consensus.
- **subjective ambiguity**: the experts themselves are strongly split, so any single
  answer is defensible.

We also do lightweight keyword-based grouping of the model's rationales on its errors,
to hint at systematic biases (e.g. over-valuing visual complexity). Semantic
clustering is left as a TODO.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional

from ..datasets.schema import PreferenceExample
from ..judges.base import Judgment

# Keyword buckets used for cheap rationale grouping. Deliberately small and
# design-domain flavoured; extend per domain.
_KEYWORD_PATTERNS: dict[str, tuple[str, ...]] = {
    "values_visual_complexity": ("complex", "detailed", "rich", "elaborate", "busy", "impact"),
    "values_novelty": ("novel", "unique", "original", "unconventional", "bold", "creative"),
    "values_content_volume": ("more", "comprehensive", "informative", "longer", "complete"),
    "values_restraint": ("clean", "minimal", "restrained", "simple", "whitespace", "sparse"),
    "values_brand_fit": ("brand", "premium", "luxury", "professional", "consistent"),
    "values_hierarchy": ("hierarchy", "structure", "clarity", "readable", "legible"),
}


@dataclass
class Disagreement:
    example_id: str
    task: str
    model_choice: str
    consensus_choice: str
    human_agreement: float
    is_ambiguous: bool
    model_rationale: Optional[str]
    tags: list[str]


def _tag_rationale(rationale: Optional[str]) -> list[str]:
    if not rationale:
        return []
    text = rationale.lower()
    return [name for name, kws in _KEYWORD_PATTERNS.items() if any(k in text for k in kws)]


def extract_disagreements(
    examples: list[PreferenceExample],
    predictions: list[Judgment],
    ambiguity_threshold: float = 0.6,
) -> list[Disagreement]:
    """All examples where the judge's choice differs from the expert consensus."""
    if len(examples) != len(predictions):
        raise ValueError("examples and predictions must align.")
    out: list[Disagreement] = []
    for ex, pred in zip(examples, predictions):
        if pred.choice == ex.preference:
            continue
        out.append(
            Disagreement(
                example_id=ex.id,
                task=ex.task,
                model_choice=pred.choice,
                consensus_choice=ex.preference,
                human_agreement=ex.agreement,
                is_ambiguous=ex.agreement < ambiguity_threshold,
                model_rationale=pred.rationale,
                tags=_tag_rationale(pred.rationale),
            )
        )
    return out


@dataclass
class DisagreementReport:
    disagreements: list[Disagreement]
    n_model_error: int  # disagreements on strong-consensus examples
    n_ambiguous: int  # disagreements where experts were split anyway
    pattern_counts: dict[str, int]  # tag -> frequency among model errors
    # Populated only when analyze_disagreements(..., semantic=True); each item is a
    # tastebench.evaluation.clustering.RationaleCluster.
    semantic_clusters: Optional[list] = None

    @property
    def top_patterns(self) -> list[tuple[str, int]]:
        return sorted(self.pattern_counts.items(), key=lambda kv: kv[1], reverse=True)


def analyze_disagreements(
    examples: list[PreferenceExample],
    predictions: list[Judgment],
    ambiguity_threshold: float = 0.6,
    *,
    semantic: bool = False,
) -> DisagreementReport:
    disagreements = extract_disagreements(examples, predictions, ambiguity_threshold)
    model_errors = [d for d in disagreements if not d.is_ambiguous]
    ambiguous = [d for d in disagreements if d.is_ambiguous]

    pattern_counts: Counter = Counter()
    for d in model_errors:  # only count patterns where the judge was genuinely wrong
        pattern_counts.update(d.tags)

    semantic_clusters = None
    if semantic:
        from .clustering import cluster_rationales  # lazy: optional dependency

        semantic_clusters = cluster_rationales(model_errors)

    return DisagreementReport(
        disagreements=disagreements,
        n_model_error=len(model_errors),
        n_ambiguous=len(ambiguous),
        pattern_counts=dict(pattern_counts),
        semantic_clusters=semantic_clusters,
    )
