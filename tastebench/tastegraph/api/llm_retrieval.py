"""Format taste context + retrieved assets into a prompt block (Layer 4).

This is the "LLM Retrieval" / "Agent Skill" integration surface: it turns the engine's
structured agent_context into text an LLM/agent can consume directly.
"""

from __future__ import annotations

from .engine import TasteGraphEngine


def retrieval_prompt(engine: TasteGraphEngine, user_id: str) -> str:
    ctx = engine.agent_context(user_id)
    lines = [
        f"User taste profile (id: {ctx['user_id']}, confidence: {ctx['confidence']}):",
    ]
    if not ctx["resolved"]:
        lines.append("  (cold start — no behavioral signals yet; rank by content relevance)")
    if ctx["principles"]:
        lines.append("  Prefers: " + ", ".join(ctx["principles"]))
    if ctx["avoid"]:
        lines.append("  Avoids: " + ", ".join(ctx["avoid"]))

    top = ctx["top_assets"]
    if top:
        lines.append("Recommended on-taste assets:")
        for aid in top:
            fp = engine.store.get(aid) if aid in engine.store else None
            desc = fp.semantic.caption if fp else aid
            lines.append(f"  - {aid}: {desc}")
    return "\n".join(lines)
