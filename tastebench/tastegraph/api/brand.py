"""Brand ingest + generation steer (/v1/brand/ingest, enhance, judge)."""

from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field

from ..entities.registry import EntityError, get_registry
from ..entities.schema import Entity, Link
from .engine import TasteGraphEngine
from .llm_retrieval import retrieval_prompt

ENHANCE_MODEL_ENV = "TASTEGRAPH_ENHANCE_MODEL"
JUDGE_MODEL_ENV = "TASTEGRAPH_JUDGE_MODEL"
ASK_MODEL_ENV = "TASTEGRAPH_ASK_MODEL"


class RefBody(BaseModel):
    id: Optional[str] = None
    content: str


class BrandIngestBody(BaseModel):
    id: str
    type: str = "brand"  # brand | voice
    label: Optional[str] = None
    references: list[RefBody] = Field(default_factory=list)


class EnhanceBody(BaseModel):
    subject_id: str
    prompt: str


class JudgeBody(BaseModel):
    subject_id: str
    candidates: list[str]


def ingest_brand(engine: TasteGraphEngine, body: BrandIngestBody) -> dict:
    reg = get_registry(engine)
    if body.type not in ("brand", "voice"):
        raise EntityError("Brand ingest type must be 'brand' or 'voice'.")
    if not body.references:
        raise EntityError("Brand ingest requires at least one reference.")

    meta = {"label": body.label} if body.label else {}
    brand = Entity(id=body.id, type=body.type, content=body.label, metadata=meta)
    existing = reg._entities.get(body.id)
    if existing is not None and not existing.hidden:
        if not reg.is_subject(existing.type):
            raise EntityError(f"Entity {body.id!r} exists and is not a brand/voice subject.")
        reg._entities[body.id] = brand
    else:
        reg.create(brand)

    linked: list[str] = []
    for i, ref in enumerate(body.references):
        rid = ref.id or f"{body.id}_ref_{i}"
        try:
            reg.get(rid)
            # already exists — skip recreate; still ensure link
        except EntityError:
            reg.create(Entity(id=rid, type="content", content=ref.content, metadata={"brand_id": body.id}))
        reg.link(Link(source_id=body.id, target_id=rid, action="like"))
        linked.append(rid)

    return {"brand": brand.model_dump(), "linked": linked, "n_signals": len(engine._signals.get(body.id, []))}


def _model(primary: str, *fallbacks: str) -> Optional[str]:
    for key in (primary, *fallbacks):
        val = os.environ.get(key)
        if val:
            return val
    return None


def _templated_enhance(engine: TasteGraphEngine, subject_id: str, prompt: str) -> str:
    ctx = engine.agent_context(subject_id)
    prefers = ", ".join(ctx.get("principles", [])) or "established themes"
    avoid = ", ".join(ctx.get("avoid", [])) or "off-taste patterns"
    return (
        f"[On-taste for {subject_id}] Prefer {prefers}; avoid {avoid}.\n\n"
        f"Revised draft:\n{prompt.strip()}"
    )


def enhance(engine: TasteGraphEngine, subject_id: str, prompt: str) -> dict:
    model = _model(ENHANCE_MODEL_ENV, ASK_MODEL_ENV)
    if not model:
        return {
            "enhanced": _templated_enhance(engine, subject_id, prompt),
            "source": "template",
            "subject_id": subject_id,
        }
    try:
        import litellm  # lazy

        system = (
            "You rewrite drafts so they match a taste subject (brand or voice). "
            "Keep the user's intent; adjust tone, specificity, and style. Return only the rewritten text.\n\n"
            + retrieval_prompt(engine, subject_id)
        )
        resp = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=500,
        )
        text = resp["choices"][0]["message"]["content"].strip()
        return {"enhanced": text, "source": model, "subject_id": subject_id}
    except Exception:  # noqa: BLE001
        return {
            "enhanced": _templated_enhance(engine, subject_id, prompt),
            "source": "template-fallback",
            "subject_id": subject_id,
        }


def _score_template(engine: TasteGraphEngine, subject_id: str, text: str, idx: int) -> dict:
    ctx = engine.agent_context(subject_id)
    principles = [p.lower() for p in ctx.get("principles", [])]
    avoid = [a.lower() for a in ctx.get("avoid", [])]
    lower = text.lower()
    hit = sum(1 for p in principles if p and p in lower)
    miss = sum(1 for a in avoid if a and a in lower)
    base = 0.55 + 0.08 * hit - 0.12 * miss
    # slight length preference for non-empty substantive drafts
    if len(text.strip()) < 20:
        base -= 0.15
    score = max(0.0, min(1.0, round(base, 3)))
    rationale = (
        f"Matched {hit} principle token(s), hit {miss} avoid token(s) "
        f"for subject {subject_id}."
    )
    return {"id": f"c{idx}", "text": text, "score": score, "rationale": rationale}


def judge(engine: TasteGraphEngine, subject_id: str, candidates: list[str]) -> dict:
    if not candidates:
        raise EntityError("Judge requires at least one candidate.")
    model = _model(JUDGE_MODEL_ENV, ASK_MODEL_ENV)
    results = [_score_template(engine, subject_id, c, i) for i, c in enumerate(candidates)]
    results.sort(key=lambda r: r["score"], reverse=True)

    if not model:
        return {"results": results, "source": "template", "subject_id": subject_id}

    try:
        import litellm  # lazy
        import json

        prompt = (
            "Score each candidate draft 0..1 for fit to the taste subject. "
            "Return JSON: {\"results\":[{\"id\":\"c0\",\"score\":0.0,\"rationale\":\"...\"},...]}\n\n"
            + retrieval_prompt(engine, subject_id)
            + "\n\nCandidates:\n"
            + "\n".join(f"- c{i}: {c}" for i, c in enumerate(candidates))
        )
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600,
        )
        raw = resp["choices"][0]["message"]["content"]
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1]) if start >= 0 and end > start else {}
        llm_results = data.get("results") or []
        by_id = {r.get("id"): r for r in llm_results if isinstance(r, dict)}
        merged = []
        for i, c in enumerate(candidates):
            cid = f"c{i}"
            row = by_id.get(cid) or {}
            merged.append(
                {
                    "id": cid,
                    "text": c,
                    "score": float(row.get("score", results[i]["score"])),
                    "rationale": row.get("rationale") or results[i]["rationale"],
                }
            )
        merged.sort(key=lambda r: r["score"], reverse=True)
        return {"results": merged, "source": model, "subject_id": subject_id}
    except Exception:  # noqa: BLE001
        return {"results": results, "source": "template-fallback", "subject_id": subject_id}
