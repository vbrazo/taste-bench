"""Turn preference examples into training pairs (no heavy dependency).

Each example yields one ``PairwiseSample`` derived from the expert *consensus*: the
consensus candidate is ``chosen``, the other is ``rejected``. The sample ``weight`` is
the human agreement fraction, so pairs the experts themselves split on contribute less
(spec §13: model ambiguity should not be treated as clean signal).

Only two-candidate examples produce a pair; examples with more candidates are skipped
(pairwise ranking expansion is a later concern).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..datasets.schema import Candidate, PreferenceExample


@dataclass
class PairwiseSample:
    prompt: str
    chosen: str
    rejected: str
    weight: float
    example_id: str


def _render(candidate: Candidate) -> str:
    return candidate.render()


def to_pairwise_pairs(examples: list[PreferenceExample]) -> list[PairwiseSample]:
    samples: list[PairwiseSample] = []
    for ex in examples:
        if len(ex.candidates) != 2:
            continue
        winner = ex.preference
        chosen = next(c for c in ex.candidates if c.id == winner)
        rejected = next(c for c in ex.candidates if c.id != winner)
        samples.append(
            PairwiseSample(
                prompt=ex.task,
                chosen=_render(chosen),
                rejected=_render(rejected),
                weight=ex.agreement,
                example_id=ex.id,
            )
        )
    return samples
