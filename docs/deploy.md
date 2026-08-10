# Deploying TasteGraph (pilot)

A checklist for standing up an **authenticated, LLM-backed, durable** TasteGraph instance with
Docker Compose. The image builds `app` from environment variables
([`tastebench/tastegraph/server.py`](../tastebench/tastegraph/server.py)); Compose wires Qdrant,
a data volume, and env.

## 1. Configure environment

```bash
cp .env.example .env
```

Set, in `.env`:

- **Auth** — `TASTEGRAPH_API_KEYS` as a JSON map of api-key → tenant, e.g.
  `{"rose_key":"rose"}`. Unset = single-tenant dev mode (no key required).
- **Durability** — `TASTEGRAPH_DATA_DIR=/data/tastegraph_state` (already set; matches the
  Compose mount). Per-tenant JSONL snapshots live here and survive restarts.
- **LLM quality** — `TASTEGRAPH_ENHANCE_MODEL` / `TASTEGRAPH_JUDGE_MODEL` (e.g. `gpt-4o`) plus
  the provider secret the model needs (e.g. `OPENAI_API_KEY`). Unset ⇒ heuristic mode, and
  every enhance/judge response carries `"mode":"heuristic"` so consumers don't mistake stubs for
  LLM quality.
- **Backend** — `TASTEGRAPH_BACKEND=qdrant` with `QDRANT_URL=http://qdrant:6333` (Compose
  default). `memory` also works but isn't shared across replicas.

## 2. Data directory permissions

The container runs as a non-root user (uid `10001`). The bind mount
`./data/tastegraph_state:/data/tastegraph_state` must be writable by it:

```bash
mkdir -p data/tastegraph_state
sudo chown -R 10001:10001 data/tastegraph_state   # or: chmod -R 777 for a quick pilot
```

(Alternatively switch the Compose mount to a named volume to sidestep host permissions.)

## 3. Bring it up

```bash
docker compose up -d --build
curl -s localhost:8000/health          # {"status":"ok","tenants":N}
```

## 4. Verify an authenticated, LLM-backed call

```bash
# With TASTEGRAPH_API_KEYS={"rose_key":"rose"} set, calls require the header:
curl -sX POST localhost:8000/v1/judge \
  -H 'Content-Type: application/json' -H 'X-API-Key: rose_key' \
  -d '{"subject_id":"voice","candidates":["warm specific note","BLAST NOW!!!"]}'
```

Check the response `"mode"`: `"llm"` means the model ran; `"heuristic"` means no model/secret
was configured (or the call fell back). Access logs (JSON lines, tenant/method/path/status/
latency) print to stdout — `docker compose logs -f api`.

## 5. Confirm durability

Seed or drive some traffic, then `docker compose restart api` and re-query — subjects, links,
and taste survive because state is persisted under `TASTEGRAPH_DATA_DIR`.

---

**Done when:** an operator can stand up an authenticated, LLM-backed, durable instance from this
doc alone. For the API surface see [v1-api.md](v1-api.md); for Rose specifics see
[rose-integration.md](rose-integration.md).
