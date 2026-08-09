"""Human agreement and the human-agreement ceiling (spec sections 11, 13).

Expecting an AI judge to reach 100% agreement is meaningless when experts themselves
disagree. The human ceiling estimates how well a *human* predicts the consensus of the
other humans, giving a realistic upper bound for any judge.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..datasets.schema import PreferenceExample


@dataclass
class ConsensusInfo:
    example_id: str
    consensus: str
    agreement: float
    counts: dict[str, int]
    is_ambiguous: bool  # experts strongly split (no clear majority)


def consensus_info(example: PreferenceExample, ambiguity_threshold: float = 0.6) -> ConsensusInfo:
    """Consensus choice + agreement for one example.

    ``is_ambiguous`` is True when the consensus is supported by less than
    ``ambiguity_threshold`` of experts — i.e. the experts themselves strongly disagree.
    """
    return ConsensusInfo(
        example_id=example.id,
        consensus=example.preference,
        agreement=example.agreement,
        counts=dict(example.vote_counts()),
        is_ambiguous=example.agreement < ambiguity_threshold,
    )


def _majority(choices: list[str], candidate_order: list[str]) -> str:
    counts = Counter(choices)
    top = max(counts.values())
    for cid in candidate_order:  # deterministic tie-break by candidate order
        if counts.get(cid, 0) == top:
            return cid
    return candidate_order[0]


def human_agreement_ceiling(examples: list[PreferenceExample]) -> float:
    """Leave-one-expert-out agreement, averaged over all expert votes.

    For each example with >= 2 experts, hold out one expert at a time; check whether
    that expert's choice matches the majority of the remaining experts. The mean over
    all such holdouts is the ceiling.

    Examples with a single expert contribute nothing (there is no "rest" to compare
    against). Returns 0.0 if no example qualifies.
    """
    hits = 0
    total = 0
    for ex in examples:
        if len(ex.judgments) < 2:
            continue
        candidate_order = [c.id for c in ex.candidates]
        choices = [j.choice for j in ex.judgments]
        for i, held in enumerate(choices):
            rest = choices[:i] + choices[i + 1 :]
            if _majority(rest, candidate_order) == held:
                hits += 1
            total += 1
    return hits / total if total else 0.0


def dataset_agreement_summary(examples: list[PreferenceExample]) -> dict:
    infos = [consensus_info(ex) for ex in examples]
    ambiguous = [i for i in infos if i.is_ambiguous]
    return {
        "human_ceiling": human_agreement_ceiling(examples),
        "mean_agreement": sum(i.agreement for i in infos) / len(infos) if infos else 0.0,
        "n_ambiguous": len(ambiguous),
        "ambiguous_ids": [i.example_id for i in ambiguous],
    }
