"""Taste-personalized Q&A (/v1/ask).

Answers a natural-language question through the lens of a user's taste: builds the user's
agent-context + top retrieved content and prompts an LLM. Graceful templated fallback when
no model/key is configured, so the endpoint works offline.
"""

from __future__ import annotations

import os

from .engine import TasteGraphEngine
from .llm_retrieval import retrieval_prompt

ASK_MODEL_ENV = "TASTEGRAPH_ASK_MODEL"


def _templated(engine: TasteGraphEngine, user_id: str, question: str, used: list[str]) -> str:
    ctx = engine.agent_context(user_id)
    if ctx["n_signals"] == 0:
        return f"I don't know {user_id}'s taste yet — link them to some content first."
    prefers = ", ".join(ctx.get("principles", [])) or "a few themes"
    picks = ", ".join(used) or "nothing yet"
    return (
        f"Based on {user_id}'s taste (leaning toward {prefers}), the most relevant picks for "
        f'"{question}" are: {picks}.'
    )


def ask(engine: TasteGraphEngine, user_id: str, question: str, k: int = 5) -> dict:
    used = [aid for aid, _ in engine.retrieve(user_id, k=k)]
    model = os.environ.get(ASK_MODEL_ENV)
    if not model:
        return {"answer": _templated(engine, user_id, question, used), "source": "template", "used_assets": used}

    try:
        import litellm  # lazy

        prompt = (
            "You answer questions for a user through the lens of their taste. Use the taste "
            "profile and recommended items below. Be concise and concrete.\n\n"
            + retrieval_prompt(engine, user_id)
            + f"\n\nQuestion: {question}\nAnswer:"
        )
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        text = resp["choices"][0]["message"]["content"].strip()
        return {"answer": text, "source": model, "used_assets": used}
    except Exception:  # noqa: BLE001 - graceful fallback on any provider/import failure
        return {
            "answer": _templated(engine, user_id, question, used),
            "source": "template-fallback",
            "used_assets": used,
        }
