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

## Optional extras

The core install stays light (`pydantic`, `litellm`, `pyyaml`). Everything heavier is
behind an extra and imported lazily — a bare `import tastebench` never pulls them in.

| Extra | Install | Enables |
|-------|---------|---------|
| `hf` | `pip install 'tastebench[hf]'` | Hugging Face dataset import/export (`tastebench export/import`) |
| `embeddings` | `pip install 'tastebench[embeddings]'` | Semantic clustering of disagreement rationales (`--semantic`) |
| `train` | `pip install 'tastebench[train]'` | Trainable judge, Bradley–Terry reward model, RL reward functions (`tastebench train`) |
| `web` | `pip install 'tastebench[web]'` | Read-only leaderboard + disagreement browser (`tastebench serve`) |
| `scrape` | `pip install 'tastebench[scrape]'` | Dataset collection connectors |

A few examples:

```bash
# Image/multimodal judging (schema keeps a `type` field; MockJudge works offline too)
tastebench evaluate --dataset data/design_image_sample.jsonl --judge gpt-4o

# Semantic disagreement clusters instead of keyword tags
tastebench evaluate --dataset data/design_sample.jsonl --judge mock:first --semantic

# Train a domain-specific judge, then use it like any other judge
tastebench train --dataset data/design_sample.jsonl --kind classifier --out models/design_judge
```

```python
from tastebench import Benchmark, RewardModel, JudgeReward, MockJudge

# A reward model learns a scalar score from preference pairs (Bradley–Terry)
rm = RewardModel().fit(Benchmark.from_jsonl("data/design_sample.jsonl").examples)
score = rm.score("Design a luxury hero", "a clean, restrained layout")

# Or turn ANY judge into a reward function for post-training (spec RQ8)
reward_fn = JudgeReward(MockJudge(), reference_artifact="baseline design", task="Design a hero")
r = reward_fn.reward("my candidate design")  # -> float in [0, 1]
```

Growing expert-labeled data (the sanctioned path — TasteBench does **not** scrape
third-party sites):

```bash
tastebench annotate --csv pairs.csv --out my_dataset.jsonl --expert designer_1
```

## TasteGraph — taste infrastructure (production sibling)

Where TasteBench *evaluates* taste, **TasteGraph** *serves* it: a mock-first backend that
fingerprints every asset across 7 VLM dimensions, captures behavioral signals, fuses both
into a joint-embedding taste graph, and exposes reranking / retrieval / agent-context. It
models the *why* behind engagement, so it works for new users and new products from the
first click instead of memorizing click history.

**Taste OS** — TasteBench + TasteGraph define an open category: *open taste infrastructure
for agents* (equal **audience** and **brand/voice** taste, agent-agnostic subjects, local
and measurable). Category definition and phased roadmap: [docs/taste-os.md](docs/taste-os.md).
Phase A agent tools: `GET /v1/skills` and [`tastebench/tastegraph/skills/llm.txt`](tastebench/tastegraph/skills/llm.txt).

```bash
pip install -e ".[tastegraph]"   # numpy; add [web] for the API, [embeddings] for real vectors

# Ingest assets → track signals → rerank by taste (all offline, no keys)
tastebench tastegraph ingest --assets data/tastegraph_assets.jsonl
tastebench tastegraph rerank  --assets data/tastegraph_assets.jsonl \
    --signals data/tastegraph_signals.jsonl --user u_minimal \
    --candidates asset_03,asset_09,asset_10,asset_01
tastebench tastegraph agent-context --assets data/tastegraph_assets.jsonl \
    --signals data/tastegraph_signals.jsonl --user u_minimal
tastebench tastegraph serve --assets data/tastegraph_assets.jsonl --port 8000   # needs [web]
```

```python
from tastebench.tastegraph import TasteGraphEngine, Asset

eng = TasteGraphEngine()                      # MockAssetAnalyzer by default; pass VLMAssetAnalyzer for real
eng.ingest([Asset(id="a1", content="minimal linen slip dress, quiet luxury")])
eng.track_event("u1", "a1", "like")
eng.rerank("u1", ["a1", "a2", "a3"])          # on-taste items rise
eng.agent_context("u1")                        # structured taste read for an LLM/agent
```

**Cold start** is handled by design: a brand-new user with zero signals still ranks
sensibly via content similarity in the shared embedding space (`--seed <asset_id>`), rather
than breaking the way click-memorizing engines do.

### Toward production

- **Pluggable vector backend** — the in-memory numpy index is the default; swap in Qdrant
  (`pip install 'tastebench[vectordb]'`, `--backend qdrant`) behind the same interface.
- **Auth & multi-tenancy** — the API gates every route on an `X-API-Key` header and isolates
  each tenant's assets/signals/graph. Run `tastebench tastegraph serve --api-keys keys.json`
  (a JSON map of `api-key → tenant`); with no key file it stays in single-tenant dev mode.
- **Audio & video** — assets can be `audio`/`video`; the VLM analyzer samples frames and
  transcribes (`pip install 'tastebench[av]'`) into the same 7-dimension fingerprint. The
  mock analyzer fingerprints A/V offline.
- **React SPA** — [`tastegraph-web/`](tastegraph-web/) is the product UI: landing → API-key /
  local login → dashboard (taste heatmap + `/v1` playground). The Python server is API-only.
- **Learn from behavior** — `tastebench tastegraph train --assets … --signals … --out DIR`
  turns signals into preference pairs and trains a reward/judge model via the `train` extra.
- **JS capture SDK** — [`sdk-js/`](sdk-js/) is `@tastegraph/sdk`, a browser/Node client that
  POSTs the exact `Signal` wire format to `/track`. A Python contract test keeps the two in sync.

### TasteGraph `/v1` — entity API for taste graphs

An open-source, Galya-inspired **entity API**: one unified `Entity` (user / content / custom
type) and the loop *create a user → give them content → build their taste (link) → query it*.
It's a thin facade over the same engine, mounted at `/v1` on `tastebench tastegraph serve`
(interactive OpenAPI at `/docs`). Full reference + curl walkthrough: [docs/v1-api.md](docs/v1-api.md).

```python
from tastebench.tastegraph import TasteGraphClient

tg = TasteGraphClient("http://127.0.0.1:8000")
tg.create_entity("u1", type="user")
tg.create_entity("c1", type="content", content="minimal linen dress")
tg.link("u1", "c1", action="like")          # build taste
tg.search(user_id="u1")                       # discovery by taste
tg.ask("u1", "what should I wear to a gallery opening?")  # taste-personalized Q&A
```

Routes: `POST /v1/entity`, `GET /v1/entities`, `/v1/entity/type`, `POST /v1/entity/{id}/link`,
`/v1/search`, `/v1/rerank`, `/v1/ask`, `/v1/explain`, `GET /v1/clusters`. Tenant-scoped via
`X-API-Key`; `/ask` + `/explain` use an LLM when `TASTEGRAPH_ASK_MODEL`/`TASTEGRAPH_EXPLAIN_MODEL`
are set, templated fallback otherwise.

### TasteGraph Web — interactive local-first UI

[`tastegraph-web/`](tastegraph-web/) is a React + Vite SPA: a marketing **landing**, **login**
(API key / tenant or local mode), then a **dashboard** with a taste-heatmap tab and a server
`/v1` playground. The heatmap is a media player plus sidebar (hex **affinity map**, **taste
regions**, **top themes**, **engagement stream**, **Explain my taste**). Affinity is computed
**in the browser** by a TypeScript port of the Python rules (in `@tastegraph/sdk`); a
Python-generated fixture parity-tests the two so they can't drift.

```bash
# 1. build the SDK (provides the local affinity engine) and export the asset+vector bundle
cd sdk-js && npm install && npm run build && cd ..
tastebench tastegraph export-web --assets data/tastegraph_assets.jsonl \
    --out tastegraph-web/public/taste-bundle.json

# 2. run the app (fully standalone — no backend needed)
cd tastegraph-web && npm install && npm run dev   # http://localhost:5173
```

Engaging with clips (like / save / deep-scroll / dwell) updates the hex map, regions,
themes, and stream live, persisted to `localStorage`. The player renders **real sample
video** (`public/media/`, synthetic ffmpeg clips) filtered by the TASK selector.

**Connected mode** — from `/login`, connect to a running `tastebench tastegraph serve` with
an API key (or leave blank in single-tenant dev mode). The SDK syncs signals, and:

- **Regions refine server-side** via `POST /regions` — higher-quality clustering
  (silhouette-picked *k*, agglomerative, distinctive-tag labels) from the Python
  `embeddings` stack; the browser falls back to local clustering offline.
- **"Explain my taste"** calls `GET /explain/{user}`, which runs an LLM over the user's
  agent-context (set `TASTEGRAPH_EXPLAIN_MODEL`, e.g. `gpt-4o`); templated summary offline.
- **API playground** tab exercises live `/v1` entity/link/search/ask endpoints.

The layout is responsive — it stacks to a single column on mobile widths.

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

v0.1: schema, judges (mock / LiteLLM / human / trained), text **and image** candidates,
evaluation metrics, keyword + semantic disagreement analysis, a reward-hacking guard,
Hugging Face import/export, judge & reward-model training, RL reward functions, a read-only
web leaderboard, and dataset-collection tooling. The core stays dependency-light; each of
these lives behind an optional extra.

## License

Apache 2.0.
