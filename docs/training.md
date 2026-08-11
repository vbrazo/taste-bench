# Training the model locally (the taste flywheel)

TasteGraph closes a loop: a durable server accumulates signals → you **export** preference pairs
→ **train** a reward model (rerank) and a classifier judge (`/v1/judge`) → **load** them back into
the API → **eval** whether they helped → repeat.

```
serve (durable) → GET /v1/export/pairs → train → model dir → env flag → mode:"trained"/"reward" → eval
```

All of this runs locally with no API keys. Training needs the extra:

```bash
pip install -e ".[tastegraph,web,train]"   # torch + transformers + peft
```

## 1. Get training data

Two sources, pick per model:

- **From a running server** (the serve→train bridge). Signals persist when the server runs with
  `TASTEGRAPH_DATA_DIR` (see [deploy.md](deploy.md)); pull them as pairs:
  ```bash
  curl -s "localhost:8000/v1/export/pairs?format=jsonl" > pairs.jsonl
  curl -s "localhost:8000/v1/export/features"           # per-subject taste vectors
  ```
- **From the bundled fixtures** (offline). `data/tastegraph_signals.jsonl` (5 users across the
  `data/tastegraph_assets.jsonl` catalog) and the expert-labeled `data/design_sample.jsonl`.

## 2. Train both models

**Reward model** (Bradley–Terry scalar — drives rerank), from the TasteGraph signals path:

```bash
tastebench tastegraph train --kind reward \
  --assets data/tastegraph_assets.jsonl \
  --signals data/tastegraph_signals.jsonl \
  --out models/tg_reward
```

**Classifier judge** (A-vs-B — drives `/v1/judge`), from the most complete expert-labeled set:

```bash
tastebench train --kind classifier --dataset data/design_sample.jsonl --out models/design_judge
```

Both write a model directory. `models/` is gitignored.

## 3. Serve the trained models

Point the API at the dirs and restart it — no code change:

```bash
export TASTEGRAPH_JUDGE_MODEL_DIR=models/design_judge
export TASTEGRAPH_REWARD_MODEL_DIR=models/tg_reward
tastebench tastegraph serve --assets data/tastegraph_assets.jsonl --port 8000
# (or `uvicorn tastebench.tastegraph.server:app` for the env-driven, durable path)
```

Now the responses report a trained mode:

```bash
# 2-candidate judge -> "mode":"trained"
curl -sX POST localhost:8000/v1/judge -H 'Content-Type: application/json' \
  -d '{"subject_id":"u_demo","candidates":["warm specific note","BLAST NOW!!!"]}'

# rerank scored by the reward model -> "mode":"reward"
curl -sX POST localhost:8000/v1/rerank -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","candidates":["c_warm","c_hype"]}'
```

Unset the env vars (or omit the `train` extra) and the same routes fall back to
`mode:"heuristic"` / `mode:"affinity"` — nothing hard-fails.

## 4. Did training help? (eval gate)

Use TasteBench's pairwise agreement as the gate. Compare the heuristic, trained, and (optional)
LLM judge on a labeled holdout:

```bash
tastebench compare --dataset data/design_sample.jsonl --judges mock trained
```

For the voice path, `tests/test_eval_voice.py` runs the fixture
`data/eval/voice_outreach.jsonl` through `/v1/judge` and asserts pairwise accuracy;
`tests/test_trained_serving.py` proves a locally-trained model flips the served `mode`.

## Notes & limits

- **Data volume is the real bottleneck.** The bundled signals are a smoke-scale set — enough to
  prove the pipeline, not to produce a strong model. Accumulate real signals via the capture SDK
  / a durable pilot, then re-export and retrain.
- The classifier judge is binary (A-vs-B); `/v1/judge` uses it only for exactly 2 candidates and
  falls back to heuristic/LLM for N>2.
- `TrainedJudge` ([tastebench/judges/trained.py](../tastebench/judges/trained.py)) and
  `RewardModel` ([tastebench/training/reward.py](../tastebench/training/reward.py)) are the
  adapters; the serving loaders live in
  [tastebench/tastegraph/api/trained_models.py](../tastebench/tastegraph/api/trained_models.py).
