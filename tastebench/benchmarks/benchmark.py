"""Benchmark orchestration and the Results object (spec section 18).

    benchmark = Benchmark.from_jsonl("design_1k.jsonl")
    results = benchmark.evaluate(judge=judge)
    results.report()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from ..datasets.loader import load_jsonl
from ..datasets.schema import PreferenceExample
from ..datasets.validation import validate_dataset
from ..evaluation.agreement import dataset_agreement_summary, human_agreement_ceiling
from ..evaluation.calibration import CalibrationReport, calibration_report
from ..evaluation.disagreement import DisagreementReport, analyze_disagreements
from ..evaluation.metrics import CriterionScore, criterion_accuracy, pairwise_accuracy
from ..judges.base import Judge, Judgment
from .runner import run_judge

PathLike = Union[str, Path]


@dataclass
class Results:
    """Everything computed for one judge on one dataset."""

    dataset_name: str
    judge_name: str
    n_examples: int
    accuracy: float
    human_ceiling: float
    calibration: CalibrationReport
    criterion_scores: dict[str, CriterionScore]
    disagreement: DisagreementReport
    predictions: list[Judgment]
    reproducibility: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset_name,
            "judge": self.judge_name,
            "n_examples": self.n_examples,
            "accuracy": self.accuracy,
            "human_ceiling": self.human_ceiling,
            "calibration_score": self.calibration.score,
            "ece": self.calibration.ece,
            "criterion_scores": {
                k: {"accuracy": v.accuracy, "correct": v.correct, "total": v.total}
                for k, v in self.criterion_scores.items()
            },
            "disagreements": {
                "n_model_error": self.disagreement.n_model_error,
                "n_ambiguous": self.disagreement.n_ambiguous,
                "top_patterns": self.disagreement.top_patterns,
                "semantic_clusters": [
                    {"label": c.label, "size": c.size, "representative": c.representative}
                    for c in (self.disagreement.semantic_clusters or [])
                ],
            },
            "predictions": [p.model_dump() for p in self.predictions],
            "reproducibility": self.reproducibility,
        }

    def report(self) -> str:
        from ..reporting.report import format_report

        text = format_report(self)
        print(text)
        return text

    def save(self, directory: PathLike) -> Path:
        """Persist results as JSON under ``directory``. Returns the file path."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        safe_judge = self.judge_name.replace("/", "_").replace(":", "_")
        path = directory / f"{safe_judge}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


class Benchmark:
    def __init__(self, examples: list[PreferenceExample], name: str = "dataset"):
        validate_dataset(examples)
        self.examples = examples
        self.name = name

    @classmethod
    def from_jsonl(cls, path: PathLike, name: Optional[str] = None) -> "Benchmark":
        path = Path(path)
        return cls(load_jsonl(path), name=name or path.stem)

    def evaluate(
        self, judge: Judge, *, max_workers: Optional[int] = None, semantic: bool = False
    ) -> Results:
        predictions = run_judge(judge, self.examples, max_workers=max_workers)
        return Results(
            dataset_name=self.name,
            judge_name=judge.name,
            n_examples=len(self.examples),
            accuracy=pairwise_accuracy(self.examples, predictions),
            human_ceiling=human_agreement_ceiling(self.examples),
            calibration=calibration_report(self.examples, predictions),
            criterion_scores=criterion_accuracy(self.examples, predictions),
            disagreement=analyze_disagreements(self.examples, predictions, semantic=semantic),
            predictions=predictions,
            reproducibility=judge.reproducibility(),
        )

    def compare(
        self, judges: list[Judge], *, max_workers: Optional[int] = None
    ) -> list[Results]:
        return [self.evaluate(j, max_workers=max_workers) for j in judges]

    def agreement_summary(self) -> dict:
        return dataset_agreement_summary(self.examples)
