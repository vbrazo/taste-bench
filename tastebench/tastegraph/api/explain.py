"""LLM-backed "Explain my taste" (Item 3).

Formats the engine's structured agent-context into a prompt and asks an LLM (via LiteLLM)
for a natural-language taste summary. Falls back to a templated summary when no model is
configured or the call fails, so the endpoint always returns something useful.
"""

from __future__ import annotations

import os

from .engine import TasteGraphEngine
from .llm_retrieval import retrieval_prompt

EXPLAIN_MODEL_ENV = "TASTEGRAPH_EXPLAIN_MODEL"


def _templated(ctx: dict) -> str:
    if ctx["n_signals"] == 0:
        return "No taste yet — engage with a few items and I'll describe your affinity."
    strength = "strong" if ctx["confidence"] > 0.7 else "emerging" if ctx["confidence"] > 0.4 else "faint"
    prefers = ", ".join(ctx.get("principles", [])) or "a few themes"
    avoid = ", ".join(ctx.get("avoid", [])) or "—"
    return (
        f"Your taste is {strength} (confidence {ctx['confidence']}). "
        f"You gravitate toward {prefers}; you tend to avoid {avoid}."
    )


def explain_taste(engine: TasteGraphEngine, user_id: str) -> dict:
    ctx = engine.agent_context(user_id)
    model = os.environ.get(EXPLAIN_MODEL_ENV)
    if not model:
        return {"explanation": _templated(ctx), "source": "template", "context": ctx}

    try:
        import litellm  # lazy

        prompt = (
            "You are a taste analyst. In 2-3 sentences, describe this user's aesthetic taste "
            "warmly and concretely based on the profile below. Do not list raw tags verbatim.\n\n"
            + retrieval_prompt(engine, user_id)
        )
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        text = resp["choices"][0]["message"]["content"].strip()
        return {"explanation": text, "source": model, "context": ctx}
    except Exception:  # noqa: BLE001 - any provider/import failure falls back gracefully
        return {"explanation": _templated(ctx), "source": "template-fallback", "context": ctx}
