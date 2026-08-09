"""Hugging Face ``datasets`` interop (optional; requires ``tastebench[hf]``).

A :class:`~tastebench.datasets.schema.PreferenceExample` maps to one row. Candidates
and judgments are stored as lists-of-structs, which HF types natively. Conversion goes
through the same ``model_dump`` / ``model_validate`` round-trip used by the JSONL loader,
so the two formats stay in lock-step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .schema import PreferenceExample

if TYPE_CHECKING:  # pragma: no cover
    from datasets import Dataset


def _require_datasets():
    try:
        import datasets  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Hugging Face export requires the 'hf' extra: pip install 'tastebench[hf]'"
        ) from exc
    return datasets


def to_hf_dataset(examples: list[PreferenceExample]) -> "Dataset":
    datasets = _require_datasets()
    rows = [ex.model_dump(exclude_none=False) for ex in examples]
    return datasets.Dataset.from_list(rows)


def from_hf_dataset(ds: "Dataset") -> list[PreferenceExample]:
    return [PreferenceExample.model_validate(row) for row in ds]


def push_to_hub(examples: list[PreferenceExample], repo_id: str, **kwargs) -> None:
    ds = to_hf_dataset(examples)
    ds.push_to_hub(repo_id, **kwargs)


def load_from_hub(repo_id: str, split: str = "train", **kwargs) -> list[PreferenceExample]:
    datasets = _require_datasets()
    ds = datasets.load_dataset(repo_id, split=split, **kwargs)
    return from_hf_dataset(ds)
