"""Adapter exposing a trained model as a Judge (optional; ``tastebench[train]``)."""

from __future__ import annotations

from ..datasets.schema import PreferenceExample
from .base import Judge, Judgment


class TrainedJudge(Judge):
    """Wraps a :class:`~tastebench.training.classifier.TrainableJudge` as a Judge.

    Only two-candidate examples are supported (the classifier is binary A-vs-B).
    """

    def __init__(self, trainable, name: str = "trained"):
        self.trainable = trainable
        self.name = name

    @classmethod
    def from_dir(cls, directory: str, name: str = "trained") -> "TrainedJudge":
        from ..training.classifier import TrainableJudge

        return cls(TrainableJudge.load(directory), name=name)

    def predict(self, example: PreferenceExample) -> Judgment:
        if len(example.candidates) != 2:
            raise ValueError("TrainedJudge supports exactly two candidates.")
        a, b = example.candidates
        choice, conf = self.trainable.predict_choice(
            example.task, a.id, a.render(), b.id, b.render()
        )
        return Judgment(choice=choice, confidence=conf, rationale="trained classifier")

    def reproducibility(self) -> dict:
        return {"judge": self.name, "kind": "trained_classifier"}
