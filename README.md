# TasteBench

AI can generate almost anything.

But can it tell what's actually *good*?

**TasteBench** is open-source infrastructure for evaluating subjective AI judgment.

Given:

```
Task + Candidate A + Candidate B
```

TasteBench measures:

```
Human preference
AI preference
Agreement
Confidence
Disagreement
```

Starting with design. Expanding to every domain where "good" is subjective.

> _lm-eval for taste._

---

## Why pairwise preference?

Absolute scores ("rate this 1–10") are poorly calibrated and mean different things to
different evaluators. TasteBench begins with the cleaner primitive:

```
A or B?
```

It captures not just the decision, but the **context**, the **criteria**, the
**evaluator**, their **confidence**, their **rationale**, and — crucially — the
**disagreement** between evaluators. The goal is not to find objective truth. It is to
model *who prefers what, under what context, and why.*

## Install

```bash
pip install -e ".[dev]"
```

## Quickstart (no API key required)

The bundled `MockJudge` runs the entire pipeline offline:

```bash
tastebench evaluate --dataset data/design_sample.jsonl --judge mock
```

Compare several judges (mix the mock with real LiteLLM model strings):

```bash
tastebench compare --dataset data/design_sample.jsonl --judges mock mock:first gpt-4o
```

Save and re-inspect results:

```bash
tastebench evaluate --dataset data/design_sample.jsonl --judge mock --results results/
tastebench disagreements --results results/
```

## Python API

```python
from tastebench import Benchmark, MockJudge

benchmark = Benchmark.from_jsonl("data/design_sample.jsonl")
results = benchmark.evaluate(judge=MockJudge())
results.report()
```

Use a real model via [LiteLLM](https://docs.litellm.ai/) — any provider works through a
single class:

```python
from tastebench import LLMJudge

results = benchmark.evaluate(LLMJudge(model="anthropic/claude-sonnet-5"))
```

## What it measures

- **Pairwise accuracy** — does the judge match the expert consensus?
- **Human-agreement ceiling** — how well do experts predict *each other*? (A judge can't
  beat this.)
- **Confidence calibration** — does the judge know when it's uncertain? (ECE)
- **Criterion-level accuracy** — *what kind* of taste does the judge lack?
- **Disagreement analysis** — separates genuine model error from subjective ambiguity,
  and surfaces systematic biases in the judge's rationales.

## Dataset format

One JSON object per line (JSONL). Each example carries a task, ≥2 candidates, the
criteria, and **one or more** expert judgments so agreement and disagreement can be
measured. See [`data/design_sample.jsonl`](data/design_sample.jsonl).

## Status

Phase 0 + Phase 1 (v0.1): schema, judges (mock / LiteLLM / human), evaluation metrics,
disagreement analysis, reproducible benchmark format, and a CLI. Text candidates for now;
the schema reserves an image `type` for multimodal later. Training and RL environments are
future phases.

## License

Apache 2.0.
