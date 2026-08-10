"""Phase 4: a TasteBench-style pairwise voice eval against /v1/judge.

Runs the fixture pairs through the judge and measures pairwise accuracy (how often the
on-voice draft outscores the hype draft). Heuristic mode is deterministic and used in CI;
set TASTEGRAPH_JUDGE_MODEL to score with a real LLM for a truer number.
"""

import json
from pathlib import Path

import pytest

pytest.importorskip("numpy")

from tastebench.tastegraph.api.brand import BrandIngestBody, RefBody, ingest_brand, judge
from tastebench.tastegraph.api.engine import TasteGraphEngine

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "eval" / "voice_outreach.jsonl"

# References that establish the founder voice (mock fingerprints -> warm / quiet-luxury tokens).
VOICE_REFS = [
    "Warm specific quiet-luxury outreach, never a blast",
    "Personal concrete intro path before any cold ask",
]


def _voice_engine(monkeypatch):
    monkeypatch.delenv("TASTEGRAPH_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("TASTEGRAPH_ASK_MODEL", raising=False)
    engine = TasteGraphEngine()
    ingest_brand(
        engine,
        BrandIngestBody(id="voice", type="voice", references=[RefBody(content=c) for c in VOICE_REFS]),
    )
    return engine


def test_voice_eval_pairwise_accuracy(monkeypatch):
    engine = _voice_engine(monkeypatch)
    pairs = [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert pairs, "fixture must contain pairs"

    correct = 0
    for pair in pairs:
        out = judge(engine, "voice", [pair["prefer"], pair["reject"]])
        assert out["mode"] == "heuristic"  # no model -> transparent about quality mode
        by_text = {r["text"]: r["score"] for r in out["results"]}
        if by_text[pair["prefer"]] > by_text[pair["reject"]]:
            correct += 1

    accuracy = correct / len(pairs)
    assert accuracy == 1.0, f"heuristic voice accuracy regressed: {accuracy}"
