"""Dataset-level validation.

Per-example invariants are enforced by the Pydantic models in :mod:`schema`. This
module checks cross-example properties useful before running a benchmark.
"""

from __future__ import annotations

from collections import Counter

from .schema import PreferenceExample


class DatasetValidationError(ValueError):
    pass


def validate_dataset(examples: list[PreferenceExample], *, require_unique_ids: bool = True) -> None:
    """Raise :class:`DatasetValidationError` if the dataset is malformed."""
    if not examples:
        raise DatasetValidationError("Dataset is empty.")

    if require_unique_ids:
        id_counts = Counter(ex.id for ex in examples)
        dupes = [i for i, n in id_counts.items() if n > 1]
        if dupes:
            raise DatasetValidationError(f"Duplicate example ids: {sorted(dupes)}")


def dataset_summary(examples: list[PreferenceExample]) -> dict:
    """A quick, human-readable summary of a dataset."""
    n_judgments = [len(ex.judgments) for ex in examples]
    multi = sum(1 for n in n_judgments if n > 1)
    criteria = Counter(c for ex in examples for c in ex.criteria)
    return {
        "examples": len(examples),
        "with_multiple_experts": multi,
        "avg_experts_per_example": (sum(n_judgments) / len(examples)) if examples else 0.0,
        "criteria": dict(criteria),
    }
