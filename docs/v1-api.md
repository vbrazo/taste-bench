# TasteGraph `/v1` API

An open-source, entity-based API for **taste graphs**. The model is one unified `Entity`
(users, content, or a custom type) and one loop:

> **create a user → give them content → build their taste (link) → query it**

Everything is a thin facade over the in-process `TasteGraphEngine`, so it runs offline with
the mock analyzer and needs no keys. Interactive OpenAPI docs are served at `/docs`.

> **Stable contract (frozen for consumers).** These routes are the integration surface downstream
> agents (e.g. Rose) build against — their paths and response shapes are held stable:
> `GET /agent-context/{id}` · `POST /v1/search` · `POST /v1/rerank` · `POST /v1/brand/ingest` ·
> `POST /v1/enhance` · `POST /v1/judge` · `GET /v1/skills`. Integration guide:
> [rose-integration.md](rose-integration.md).

## Start the server

```bash
pip install -e ".[tastegraph,web]"
tastebench tastegraph serve --assets data/tastegraph_assets.jsonl --port 8000
# add --api-keys keys.json for per-tenant auth (X-API-Key header)
```

Seed the demo graph in one command (idempotent): `tastebench tastegraph seed-demo`.
Wire an agent with the installable skill: [`skills/tastegraph/SKILL.md`](../skills/tastegraph/SKILL.md).

**Agent walkthrough (context → search/rerank → ask → judge):** [agent-demo.md](agent-demo.md)

## The loop (curl)

```bash
# 1. create a user entity
curl -sX POST localhost:8000/v1/entity -d '{"id":"u1","type":"user"}' -H 'Content-Type: application/json'

# 2. create content entities
curl -sX POST localhost:8000/v1/entity \
  -d '{"id":"c1","type":"content","content":"minimal linen quiet-luxury dress"}' -H 'Content-Type: application/json'

# 3. build taste by linking (action ∈ view|click|like|save|dismiss)
curl -sX POST localhost:8000/v1/entity/u1/link \
  -d '{"target_id":"c1","action":"like"}' -H 'Content-Type: application/json'

# 4. query
curl -sX POST localhost:8000/v1/search  -d '{"user_id":"u1","k":5}'                 -H 'Content-Type: application/json'
curl -sX POST localhost:8000/v1/rerank  -d '{"user_id":"u1","candidates":["c1"]}'    -H 'Content-Type: application/json'
curl -sX POST localhost:8000/v1/ask     -d '{"user_id":"u1","question":"what should I wear?"}' -H 'Content-Type: application/json'
curl -sX POST localhost:8000/v1/explain -d '{"user_id":"u1","candidates":[]}'        -H 'Content-Type: application/json'
curl -s     localhost:8000/v1/clusters
```

## Routes

| Route | Purpose |
|---|---|
| `POST /v1/entity` | Create a user / content / custom entity |
| `GET /v1/entities` | List entities (optional `?type=` filter) |
| `GET`·`DELETE /v1/entity/{id}` | Fetch / soft-delete an entity |
| `POST /v1/entity/type` · `GET /v1/entity/types` | Register / list custom entity types |
| `POST /v1/entity/{id}/link` | Build taste: link a user to content |
| `POST /v1/search` | Discovery by taste (`user_id`) or content similarity (`seed_id`) |
| `POST /v1/rerank` | Reorder candidate content by a user's taste (`"mode"`: `affinity`, or `reward` when a trained reward model is loaded) |
| `POST /v1/ask` | Taste-personalized Q&A (LLM via `TASTEGRAPH_ASK_MODEL`; templated fallback) |
| `POST /v1/explain` | Natural-language taste summary (`TASTEGRAPH_EXPLAIN_MODEL`) |
| `GET /v1/clusters` · `GET /v1/cluster/{id}` | Taste clusters over the catalog |
| `GET /v1/skills` | OpenAI-style agent tool schemas (`taste_context`, `taste_search`, …); installable skill at [`skills/tastegraph`](../skills/tastegraph/SKILL.md) |
| `POST /v1/brand/ingest` | Create/update a brand or voice subject from reference texts |
| `POST /v1/enhance` | Rewrite a draft on-taste for a user/brand `subject_id` |
| `POST /v1/judge` | Score draft candidates against a user/brand `subject_id` (`"mode"`: `heuristic` / `llm` / `trained`) |
| `GET /v1/export/pairs` | Preference pairs from accumulated signals (`?format=json\|jsonl`) — training data |
| `GET /v1/export/features` | Per-subject taste feature vectors (`subject_id`, `vector`, `confidence`) |

## Python client

```python
from tastebench.tastegraph import TasteGraphClient

tg = TasteGraphClient("http://127.0.0.1:8000", api_key="key_a")  # api_key optional
tg.create_entity("u1", type="user")
tg.create_entity("c1", type="content", content="minimal linen dress")
tg.link("u1", "c1", action="like")
tg.search(user_id="u1")
tg.ask("u1", "what should I wear to a gallery opening?")
```

## Deploy

The API ships with a Dockerfile and a compose bundle (API + Qdrant). The container entrypoint
runs `tastebench.tastegraph.server:app`, an ASGI factory configured entirely from environment
variables (see [`.env.example`](../.env.example)).

```bash
cp .env.example .env      # edit as needed
docker compose up --build # API on :8000, Qdrant on :6333
curl localhost:8000/health
```

Full pilot checklist (auth + LLM + durable state, with the non-root volume caveat):
[deploy.md](deploy.md).

Key environment variables:

| Var | Meaning |
|---|---|
| `TASTEGRAPH_API_KEYS` | JSON `{api-key: tenant}` — enables auth. Unset = dev mode (no key). |
| `TASTEGRAPH_DATA_DIR` | Directory for durable per-tenant JSONL state. Unset = in-memory only. |
| `TASTEGRAPH_BACKEND` | `memory` (default) or `qdrant`. |
| `QDRANT_URL` · `QDRANT_API_KEY` | Qdrant connection (when backend = qdrant). |
| `TASTEGRAPH_RATE_PER_MIN` · `TASTEGRAPH_RATE_BURST` | Per-key token-bucket rate limit (0 = off). |
| `TASTEGRAPH_QUOTA_PER_DAY` | Per-key daily quota (0 = off). |
| `TASTEGRAPH_ASK_MODEL` · `TASTEGRAPH_EXPLAIN_MODEL` | LLM for `/ask` · `/explain`. |
| `TASTEGRAPH_ENHANCE_MODEL` · `TASTEGRAPH_JUDGE_MODEL` | LLM for `/v1/enhance` · `/v1/judge` (else heuristic mode). |

- `GET /health` is unauthenticated (used by the Docker `HEALTHCHECK`).
- When limits are exceeded the API returns **429** with a `Retry-After` header. Rate limiting is
  **in-process** (per container) — run a shared store for multi-replica enforcement (out of scope).

## Notes

- **Auth**: with `--api-keys`, every `/v1` route requires `X-API-Key`; each tenant gets an
  isolated engine + entity registry. Without it, the server runs single-tenant dev mode.
- **Delete**: user delete clears the user's signals; content delete is a **hard delete** —
  the vector is removed from the index (and compacted) and the fingerprint dropped, on both the
  in-memory and Qdrant backends. It falls back to a soft-hide only if a backend can't remove.
- **LLM**: `/ask` and `/explain` return a templated answer when no model/key is configured,
  so the loop always works offline.
