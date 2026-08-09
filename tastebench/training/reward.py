"""Bradley-Terry reward model over preference pairs (optional; ``tastebench[train]``).

Learns a scalar ``score(prompt, artifact)`` such that the chosen candidate outscores the
rejected one. Trained with the pairwise logistic (Bradley-Terry) loss

    -log sigmoid( score(chosen) - score(rejected) )

weighted by human agreement. LoRA/PEFT is optional via ``lora=True``. When ``trl`` is
installed its ``RewardTrainer`` can be used instead, but the built-in loop keeps this
dependency-light and testable on tiny data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..datasets.schema import PreferenceExample
from .classifier import _require_torch
from .dataset import to_pairwise_pairs

DEFAULT_BASE_MODEL = "distilbert-base-uncased"


class RewardModel:
    def __init__(self, base_model: str = DEFAULT_BASE_MODEL, max_length: int = 512, lora: bool = False):
        _require_torch()
        self.base_model = base_model
        self.max_length = max_length
        self.lora = lora
        self.model = None
        self.tokenizer = None

    def _ensure_model(self):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        if self.model is None:
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.base_model, num_labels=1  # single scalar reward
            )
            if self.lora:
                self._apply_lora()

    def _apply_lora(self):  # pragma: no cover - exercised only with peft installed
        from peft import LoraConfig, get_peft_model

        self.model = get_peft_model(self.model, LoraConfig(task_type="SEQ_CLS"))

    def _score_batch(self, texts: list[str]):
        enc = self.tokenizer(
            texts, truncation=True, padding=True, max_length=self.max_length, return_tensors="pt"
        )
        return self.model(**enc).logits.squeeze(-1)

    def fit(self, examples: list[PreferenceExample], *, epochs: int = 3, lr: float = 5e-5):
        import torch
        import torch.nn.functional as F

        self._ensure_model()
        pairs = to_pairwise_pairs(examples)
        if not pairs:
            raise ValueError("No two-candidate examples to train on.")

        chosen = [f"{p.prompt}\n\n{p.chosen}" for p in pairs]
        rejected = [f"{p.prompt}\n\n{p.rejected}" for p in pairs]
        weights = torch.tensor([p.weight for p in pairs], dtype=torch.float)

        opt = torch.optim.AdamW(self.model.parameters(), lr=lr)
        self.model.train()
        for _ in range(epochs):
            opt.zero_grad()
            s_chosen = self._score_batch(chosen)
            s_rejected = self._score_batch(rejected)
            per = -F.logsigmoid(s_chosen - s_rejected)
            loss = (per * weights).mean()
            loss.backward()
            opt.step()
        self.model.eval()
        return self

    def score(self, prompt: str, artifact: str) -> float:
        import torch

        self._ensure_model()
        with torch.no_grad():
            return float(self._score_batch([f"{prompt}\n\n{artifact}"])[0])

    def save(self, directory: str):
        self._ensure_model()
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(directory)
        self.tokenizer.save_pretrained(directory)

    @classmethod
    def load(cls, directory: str, max_length: int = 512) -> "RewardModel":
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        obj = cls(base_model=directory, max_length=max_length)
        obj.tokenizer = AutoTokenizer.from_pretrained(directory)
        obj.model = AutoModelForSequenceClassification.from_pretrained(directory, num_labels=1)
        obj.model.eval()
        return obj
