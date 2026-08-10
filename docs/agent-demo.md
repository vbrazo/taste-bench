# Agent demo — personalize from TasteGraph in under 10 minutes

Goal: a running TasteGraph that an agent (or you, via curl) can call for **context**,
**search/rerank**, **ask**, and **judge** — the builder personalization path.

## 0. Prerequisites (~1 min)

```bash
# from repo root
python3 -m venv .venv && source .venv/bin/activate   # if needed
pip install -e ".[tastegraph,web]"
```

Optional: an LLM key only if you want real `/ask` / `/explain` / `/judge` prose.
Without keys, those routes still return a templated / heuristic response.

## 1. Start the server (~1 min)

```bash
tastebench tastegraph serve --assets data/tastegraph_assets.jsonl --port 8000
```

Check:

```bash
curl -s localhost:8000/health
curl -s localhost:8000/v1/skills | head -c 200   # agent tool schemas
```

Leave this terminal running. Base URL: `http://127.0.0.1:8000`.

## 2. Seed a subject (~1 min)

Seed the demo graph in one command (idempotent — safe to re-run):

```bash
tastebench tastegraph seed-demo   # creates u_demo, c_warm (liked), c_hype (dismissed)
```

<details>
<summary>Manual seed (curl equivalent)</summary>

```bash
BASE=http://127.0.0.1:8000

curl -sX POST $BASE/v1/entity -H 'Content-Type: application/json' \
  -d '{"id":"u_demo","type":"user"}'

curl -sX POST $BASE/v1/entity -H 'Content-Type: application/json' \
  -d '{"id":"c_warm","type":"content","content":"warm specific note — concrete, no hype"}'

curl -sX POST $BASE/v1/entity -H 'Content-Type: application/json' \
  -d '{"id":"c_hype","type":"content","content":"AMAZING platform!!! 🚀🚀 unlock growth now"}'

curl -sX POST $BASE/v1/entity/u_demo/link -H 'Content-Type: application/json' \
  -d '{"target_id":"c_warm","action":"like"}'

curl -sX POST $BASE/v1/entity/u_demo/link -H 'Content-Type: application/json' \
  -d '{"target_id":"c_hype","action":"dismiss"}'
```

</details>

## 3. Personalize (~2 min)

```bash
BASE=http://127.0.0.1:8000

# Structured taste for an agent
curl -s $BASE/agent-context/u_demo | python3 -m json.tool

# Discovery by taste
curl -sX POST $BASE/v1/search -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","k":5}' | python3 -m json.tool

# Reorder candidates
curl -sX POST $BASE/v1/rerank -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","candidates":["c_warm","c_hype"]}' | python3 -m json.tool

# Taste Q&A (templated offline; set TASTEGRAPH_ASK_MODEL for LLM)
curl -sX POST $BASE/v1/ask -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","question":"what tone should I use?"}' | python3 -m json.tool
```

Expect: `c_warm` ranks above `c_hype`; context shows principles / avoid / confidence.

## 4. Less slop check (~1 min)

```bash
curl -sX POST $BASE/v1/judge -H 'Content-Type: application/json' \
  -d '{
    "subject_id":"u_demo",
    "candidates":[
      "Hi — noticed you care about concrete detail. One idea that fits.",
      "hey!!! check out our AMAZING platform 🚀🚀🚀"
    ]
  }' | python3 -m json.tool
```

Prefer the first draft for `u_demo`.

## 5. Wire an agent (~3 min)

**Option A — Cursor / Claude Code skill**

1. Install the skill: `npx skills add <owner>/taste-bench --skill tastegraph`
   (or just open [`skills/tastegraph/SKILL.md`](../skills/tastegraph/SKILL.md)).
2. Point the agent at this server via `TASTEGRAPH_BASE_URL` (default `http://127.0.0.1:8000`).
   The skill also carries the live tool schemas (`GET /v1/skills` /
   [`tools.json`](../tastebench/tastegraph/skills/tools.json)) and exact curl recipes.
3. Prompt: *“For subject `u_demo`, call taste_context, then taste_rerank on c_warm and c_hype, then taste_judge two outreach drafts.”*

**Option B — Python client**

```python
from tastebench.tastegraph import TasteGraphClient

tg = TasteGraphClient("http://127.0.0.1:8000")
print(tg.ask("u_demo", "what tone should I use?"))
print(tg.rerank("u_demo", ["c_warm", "c_hype"]))
print(tg.judge("u_demo", [
    "Hi — concrete and specific.",
    "hey!!! AMAZING platform 🚀",
]))
```

**Option C — Dashboard**

```bash
cd tastegraph-web && npm install && npm run dev
```

Open `/login` → connect to `http://127.0.0.1:8000` (API key blank in dev) → **API playground**
for create / link / search / ask. Use **Taste heatmap** for local affinity exploration.

## Done when

- [ ] `/v1/skills` returns tool names including `taste_search`, `taste_rerank`, `taste_ask`
- [ ] `agent-context/u_demo` is non-empty and `resolved` / confidence look sane
- [ ] Rerank puts `c_warm` above `c_hype`
- [ ] An agent (or you) can repeat steps 3–4 without opening this doc twice

## Next (optional)

- Less slop: `POST /v1/brand/ingest` then `enhance` / `judge` against a voice or user subject  
- Category notes: [taste-os.md](taste-os.md)  
- Pitch outline: [pitch.md](pitch.md)
