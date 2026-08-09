"""LLM-backed judge via LiteLLM.

A single class works across OpenAI / Anthropic / Gemini / local models by passing a
LiteLLM model string (e.g. ``"gpt-4o"``, ``"anthropic/claude-sonnet-5"``,
``"gemini/gemini-1.5-pro"``, ``"ollama/llama3"``).

The prompt, temperature, and criteria are all configurable and recorded in
:meth:`reproducibility` so runs can be reproduced (spec section 10).
"""

from __future__ import annotations

import json
import re
from typing import Optional

from ..datasets.schema import PreferenceExample
from .base import Judge, Judgment

DEFAULT_PROMPT = """\
You are evaluating candidate outputs for a subjective task.

Task:
{task}

Criteria:
{criteria}

{candidates}

Which candidate better satisfies the task? Consider the criteria above.

Respond with ONLY a JSON object of the form:
{{"choice": "<candidate id>", "confidence": <0-1 float>, "rationale": "<concise explanation>"}}
"""


class LLMJudge(Judge):
    def __init__(
        self,
        model: str,
        *,
        prompt_template: str = DEFAULT_PROMPT,
        temperature: float = 0.0,
        criteria: Optional[list[str]] = None,
        max_tokens: int = 512,
    ):
        self.model = model
        self.name = model
        self.prompt_template = prompt_template
        self.temperature = temperature
        self.criteria_override = criteria
        self.max_tokens = max_tokens

    # ---- prompt construction ----------------------------------------------

    def _render_candidates(self, example: PreferenceExample) -> str:
        blocks = []
        for c in example.candidates:
            blocks.append(f"Candidate {c.id}:\n{c.render()}")
        return "\n\n".join(blocks)

    def build_prompt(self, example: PreferenceExample) -> str:
        criteria = self.criteria_override or example.criteria
        criteria_str = ", ".join(criteria) if criteria else "(none specified)"
        return self.prompt_template.format(
            task=example.task,
            criteria=criteria_str,
            candidates=self._render_candidates(example),
        )

    # ---- inference ---------------------------------------------------------

    def predict(self, example: PreferenceExample) -> Judgment:
        import litellm  # imported lazily so the package imports without a key

        prompt = self.build_prompt(example)
        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        text = response["choices"][0]["message"]["content"]
        valid_ids = [c.id for c in example.candidates]
        return _parse_judgment(text, valid_ids)

    def reproducibility(self) -> dict:
        return {
            "judge": self.name,
            "model": self.model,
            "temperature": self.temperature,
            "prompt_template": self.prompt_template,
            "criteria_override": self.criteria_override,
        }


def _parse_judgment(text: str, valid_ids: list[str]) -> Judgment:
    """Parse a model response into a Judgment, tolerating loose formatting."""
    choice: Optional[str] = None
    confidence: Optional[float] = None
    rationale: Optional[str] = None

    # 1) Try to find a JSON object anywhere in the text.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            raw_choice = data.get("choice")
            if raw_choice is not None:
                choice = str(raw_choice).strip()
            if data.get("confidence") is not None:
                confidence = float(data["confidence"])
            if data.get("rationale") is not None:
                rationale = str(data["rationale"])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # 2) Normalise / recover the choice against the known candidate ids.
    if choice not in valid_ids:
        choice = _recover_choice(text, valid_ids)

    if rationale is None:
        rationale = text.strip()[:500]

    return Judgment(choice=choice, confidence=confidence, rationale=rationale)


def _recover_choice(text: str, valid_ids: list[str]) -> str:
    """Best-effort recovery of a candidate id from free text."""
    # Prefer an explicit "choice: X" style mention.
    m = re.search(r"choice\s*[:=]\s*['\"]?([A-Za-z0-9_\-]+)", text, re.IGNORECASE)
    if m and m.group(1) in valid_ids:
        return m.group(1)
    # Otherwise, the first candidate id that appears as a whole token.
    for cid in valid_ids:
        if re.search(rf"\b{re.escape(cid)}\b", text):
            return cid
    # Give up: default to the first candidate so downstream code stays total.
    return valid_ids[0]
