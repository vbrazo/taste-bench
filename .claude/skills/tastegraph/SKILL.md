---
name: tastegraph
description: Query a local TasteGraph server for structured taste/preference — personalize (rerank, search, ask), read an agent-context card, and judge/enhance drafts to keep them on-taste ("less slop"). Use when the task involves ranking candidates by a user's or brand's preference, deciding which draft to send, or wiring an agent to a running TasteGraph API over HTTP. Not for building frontend UI or design mockups.
---

# TasteGraph agent skill

TasteGraph is open taste infrastructure: a running HTTP server that stores structured
preference for a subject (a user, a brand, or a voice) and answers taste queries. This skill
teaches you to call it directly. It is **not** a frontend/design skill.

## 1. Prerequisites

The server must be running and reachable. Base URL comes from `TASTEGRAPH_BASE_URL`
(default `http://127.0.0.1:8000`). An optional `X-API-Key` header is used for tenant auth.

```bash
export TASTEGRAPH_BASE_URL="${TASTEGRAPH_BASE_URL:-http://127.0.0.1:8000}"
curl -s "$TASTEGRAPH_BASE_URL/health"          # {"status":"ok",...}
curl -s "$TASTEGRAPH_BASE_URL/v1/skills" | head -c 200   # live tool schemas
```

If it is not running, start it (from the repo): `tastebench tastegraph serve --assets data/tastegraph_assets.jsonl --port 8000`.

## 2. Seed a demo graph if it's empty

If the subject is missing or the graph is empty (rerank returns nothing / agent-context is
sparse), seed the canonical demo (idempotent — safe to re-run):

```bash
tastebench tastegraph seed-demo   # creates u_demo, c_warm (liked), c_hype (dismissed)
```

This makes `taste_rerank` for `u_demo` rank `c_warm` above `c_hype`.

## 3. Tools → HTTP

Builder tools (mirror of `GET /v1/skills` / `tastebench/tastegraph/skills/tools.json`):

| Tool | HTTP | Body |
|------|------|------|
| `taste_context` | GET `/agent-context/{subject_id}` | — (note: **not** under `/v1`) |
| `taste_rerank` | POST `/v1/rerank` | `{"user_id","candidates":[...]}` |
| `taste_search` | POST `/v1/search` | `{"user_id","k"}` |
| `taste_ask` | POST `/v1/ask` | `{"user_id","question"}` |
| `taste_enhance` | POST `/v1/enhance` | `{"subject_id","prompt"}` |
| `taste_judge` | POST `/v1/judge` | `{"subject_id","candidates":[...]}` |

## 4. Canonical loop

`taste_context` → `taste_rerank` → `taste_judge`:

1. **Read** the subject's taste card before deciding.
2. **Rerank** your candidates so on-taste items rise.
3. **Judge** competing drafts and send the winner.

## 5. Exact curl recipes

Use these verbatim — do not invent paths. `$B` is the base URL.

```bash
B="${TASTEGRAPH_BASE_URL:-http://127.0.0.1:8000}"

# taste_context — structured taste read (principles / avoid / confidence)
curl -s "$B/agent-context/u_demo"

# taste_rerank — order candidates by the subject's taste
curl -sX POST "$B/v1/rerank" -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","candidates":["c_warm","c_hype"]}'

# taste_judge — score competing drafts before send
curl -sX POST "$B/v1/judge" -H 'Content-Type: application/json' \
  -d '{"subject_id":"u_demo","candidates":["c_warm","c_hype"]}'
```

See `reference.md` for the full call surface (search, ask, enhance, brand ingest, entity/link).
