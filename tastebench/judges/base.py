"""Judge abstraction.

A judge is any system that produces a preference prediction for a
:class:`~tastebench.datasets.schema.PreferenceExample`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

from ..datasets.schema import PreferenceExample


class Judgment(BaseModel):
    """A judge's prediction on a single example."""

    choice: str
    confidence: Optional[float] = None
    rationale: Optional[str] = None


class Judge(ABC):
    """Base class for all judges."""

    #: Human-readable identifier used in reports (e.g. "gpt-4o", "mock").
    name: str = "judge"

    @abstractmethod
    def predict(self, example: PreferenceExample) -> Judgment:
        """Return a preference prediction for ``example``."""

    def predict_batch(self, examples: list[PreferenceExample]) -> list[Judgment]:
        """Predict over many examples. Override for provider-side batching/parallelism."""
        return [self.predict(ex) for ex in examples]

    def reproducibility(self) -> dict:
        """Metadata identifying this judge configuration for reproducible runs."""
        return {"judge": self.name}
