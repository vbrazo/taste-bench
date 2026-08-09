"""A trainable A-vs-B judge (optional; requires ``tastebench[train]``).

Wraps a Hugging Face sequence-classification model with two labels (candidate A wins /
candidate B wins). The rendered pair is fed as a single text; ``.fit`` runs a small
supervised loop, ``.save`` / ``.load`` persist it. Inference is exposed as a
:class:`~tastebench.judges.base.Judge` via :mod:`tastebench.judges.trained` so trained
judges drop straight into ``Benchmark.evaluate``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..datasets.schema import PreferenceExample

DEFAULT_BASE_MODEL = "distilbert-base-uncased"


def _require_torch():
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Training requires the 'train' extra: pip install 'tastebench[train]'"
        ) from exc


def render_pair(task: str, cand_a: str, cand_b: str) -> str:
    return f"Task: {task}\n\nCandidate A:\n{cand_a}\n\nCandidate B:\n{cand_b}"


class TrainableJudge:
    def __init__(self, base_model: str = DEFAULT_BASE_MODEL, max_length: int = 512):
        _require_torch()
        self.base_model = base_model
        self.max_length = max_length
        self.model = None
        self.tokenizer = None

    # ---- construction ------------------------------------------------------

    def _ensure_model(self):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        if self.model is None:
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.base_model, num_labels=2
            )

    @staticmethod
    def _encode_examples(examples: list[PreferenceExample]):
        """(texts, labels) where label 0 == first candidate wins, 1 == second wins."""
        texts, labels, weights = [], [], []
        for ex in examples:
            if len(ex.candidates) != 2:
                continue
            a, b = ex.candidates
            texts.append(render_pair(ex.task, a.render(), b.render()))
            labels.append(0 if ex.preference == a.id else 1)
            weights.append(ex.agreement)
        return texts, labels, weights

    # ---- training ----------------------------------------------------------

    def fit(self, examples: list[PreferenceExample], *, epochs: int = 3, lr: float = 5e-5):
        import torch

        self._ensure_model()
        texts, labels, weights = self._encode_examples(examples)
        if not texts:
            raise ValueError("No two-candidate examples to train on.")

        enc = self.tokenizer(
            texts, truncation=True, padding=True, max_length=self.max_length, return_tensors="pt"
        )
        y = torch.tensor(labels)
        w = torch.tensor(weights, dtype=torch.float)

        opt = torch.optim.AdamW(self.model.parameters(), lr=lr)
        self.model.train()
        for _ in range(epochs):
            opt.zero_grad()
            out = self.model(**enc)
            per = torch.nn.functional.cross_entropy(out.logits, y, reduction="none")
            loss = (per * w).mean()
            loss.backward()
            opt.step()
        self.model.eval()
        return self

    # ---- inference ---------------------------------------------------------

    def predict_choice(self, task: str, cand_a_id: str, cand_a: str, cand_b_id: str, cand_b: str):
        import torch

        self._ensure_model()
        enc = self.tokenizer(
            render_pair(task, cand_a, cand_b),
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        with torch.no_grad():
            logits = self.model(**enc).logits[0]
            probs = torch.softmax(logits, dim=-1)
        idx = int(torch.argmax(probs))
        choice = cand_a_id if idx == 0 else cand_b_id
        return choice, float(probs[idx])

    # ---- persistence -------------------------------------------------------

    def save(self, directory: str):
        self._ensure_model()
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(directory)
        self.tokenizer.save_pretrained(directory)

    @classmethod
    def load(cls, directory: str, max_length: int = 512) -> "TrainableJudge":
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        obj = cls(base_model=directory, max_length=max_length)
        obj.tokenizer = AutoTokenizer.from_pretrained(directory)
        obj.model = AutoModelForSequenceClassification.from_pretrained(directory)
        obj.model.eval()
        return obj
