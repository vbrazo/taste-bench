"""Core data model for TasteBench.

The fundamental unit is a :class:`PreferenceExample`: a task, a set of candidate
artifacts, and one or more expert judgments over those candidates. The spec's
single-expert form (one ``preference`` + one ``expert``) is supported through the
:meth:`PreferenceExample.single` constructor, which wraps a lone judgment. The
canonical internal representation always keeps a *list* of judgments so that human
agreement, the human-ceiling metric, and disagreement analysis have the raw signal
they need (spec sections 11-13).
"""

from __future__ import annotations

from collections import Counter
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

CandidateType = Literal["text", "image"]


class Candidate(BaseModel):
    """One candidate artifact in a comparison.

    Exactly one of ``content`` (inline text) or ``uri`` (external reference, e.g. an
    image path/URL) must be set. Keeping ``type`` explicit lets image candidates slot
    in later without changing the on-disk format.
    """

    id: str
    type: CandidateType = "text"
    content: Optional[str] = None
    uri: Optional[str] = None

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "Candidate":
        has_content = self.content is not None
        has_uri = self.uri is not None
        if has_content == has_uri:
            raise ValueError(
                f"Candidate {self.id!r} must set exactly one of 'content' or 'uri'."
            )
        if self.type == "text" and not has_content and has_uri:
            # A text candidate may legitimately point at an external text file via uri;
            # allow it, but images must use uri.
            pass
        if self.type == "image" and has_content:
            raise ValueError(f"Image candidate {self.id!r} must use 'uri', not 'content'.")
        return self

    def render(self) -> str:
        """A prompt-friendly textual representation of the candidate."""
        if self.content is not None:
            return self.content
        return f"[{self.type} artifact: {self.uri}]"


class ExpertJudgment(BaseModel):
    """A single expert's decision on a comparison."""

    expert_id: str
    domain: Optional[str] = None
    choice: str
    confidence: Optional[float] = None
    rationale: Optional[str] = None


class PreferenceExample(BaseModel):
    """A task + candidates + one or more expert judgments."""

    id: str
    task: str
    candidates: list[Candidate] = Field(min_length=2)
    criteria: list[str] = Field(default_factory=list)
    judgments: list[ExpertJudgment] = Field(min_length=1)
    # Optional: which single criterion this example most sharply tests. Enables
    # criterion-level accuracy without per-criterion labels on every example.
    dominant_criterion: Optional[str] = None

    @model_validator(mode="after")
    def _choices_reference_candidates(self) -> "PreferenceExample":
        ids = {c.id for c in self.candidates}
        for j in self.judgments:
            if j.choice not in ids:
                raise ValueError(
                    f"Example {self.id!r}: judgment choice {j.choice!r} is not a candidate id {sorted(ids)}."
                )
        return self

    # ---- consensus helpers -------------------------------------------------

    def vote_counts(self) -> Counter:
        return Counter(j.choice for j in self.judgments)

    @property
    def preference(self) -> str:
        """Majority-vote consensus choice. Ties broken by candidate order."""
        counts = self.vote_counts()
        top = max(counts.values())
        for c in self.candidates:  # stable, deterministic tie-break
            if counts.get(c.id, 0) == top:
                return c.id
        # unreachable given validation, but keep mypy/readers happy
        return self.candidates[0].id

    @property
    def agreement(self) -> float:
        """Fraction of experts agreeing with the consensus choice (1.0 == unanimous)."""
        counts = self.vote_counts()
        return counts[self.preference] / len(self.judgments)

    @property
    def is_unanimous(self) -> bool:
        return self.agreement == 1.0

    @classmethod
    def single(
        cls,
        *,
        id: str,
        task: str,
        candidates: list[Candidate],
        preference: str,
        criteria: Optional[list[str]] = None,
        expert_id: str = "expert_0",
        domain: Optional[str] = None,
        confidence: Optional[float] = None,
        rationale: Optional[str] = None,
        dominant_criterion: Optional[str] = None,
    ) -> "PreferenceExample":
        """Build an example from a single expert's decision (spec section 6 form)."""
        return cls(
            id=id,
            task=task,
            candidates=candidates,
            criteria=criteria or [],
            dominant_criterion=dominant_criterion,
            judgments=[
                ExpertJudgment(
                    expert_id=expert_id,
                    domain=domain,
                    choice=preference,
                    confidence=confidence,
                    rationale=rationale,
                )
            ],
        )
