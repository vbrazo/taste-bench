# TasteGraph HTTP reference

Full call surface for the `tastegraph` skill. Base URL from `TASTEGRAPH_BASE_URL`
(default `http://127.0.0.1:8000`); add `-H "X-API-Key: $KEY"` when the server is tenant-scoped.
The live, authoritative schemas are always at `GET /v1/skills`.

```bash
B="${TASTEGRAPH_BASE_URL:-http://127.0.0.1:8000}"
```

## Build a graph (entities + links)

```bash
# Create a subject and content
curl -sX POST "$B/v1/entity" -H 'Content-Type: application/json' \
  -d '{"id":"u_demo","type":"user"}'
curl -sX POST "$B/v1/entity" -H 'Content-Type: application/json' \
  -d '{"id":"c_warm","type":"content","content":"warm specific note — concrete, no hype"}'
curl -sX POST "$B/v1/entity" -H 'Content-Type: application/json' \
  -d '{"id":"c_hype","type":"content","content":"AMAZING platform!!! 🚀🚀 unlock growth now"}'

# Build taste (actions: like, save, view, click, dismiss)
curl -sX POST "$B/v1/entity/u_demo/link" -H 'Content-Type: application/json' \
  -d '{"target_id":"c_warm","action":"like"}'
curl -sX POST "$B/v1/entity/u_demo/link" -H 'Content-Type: application/json' \
  -d '{"target_id":"c_hype","action":"dismiss"}'
```

Or seed all of the above idempotently: `tastebench tastegraph seed-demo`.

## Personalize

```bash
# taste_context — structured taste read
curl -s "$B/agent-context/u_demo"

# taste_search — discover content by taste
curl -sX POST "$B/v1/search" -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","k":8}'

# taste_rerank — reorder candidates
curl -sX POST "$B/v1/rerank" -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","candidates":["c_warm","c_hype"]}'

# taste_ask — taste-personalized Q&A
curl -sX POST "$B/v1/ask" -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","question":"what should I read first?"}'

# taste_explain — why this taste
curl -sX POST "$B/v1/explain" -H 'Content-Type: application/json' \
  -d '{"user_id":"u_demo","candidates":[]}'
```

## Less slop (brand / voice)

```bash
# taste_brand_ingest — build a voice subject from reference snippets
curl -sX POST "$B/v1/brand/ingest" -H 'Content-Type: application/json' \
  -d '{"id":"voice","type":"voice","references":[{"content":"warm, specific, concrete"}]}'

# taste_enhance — rewrite a draft on-taste
curl -sX POST "$B/v1/enhance" -H 'Content-Type: application/json' \
  -d '{"subject_id":"voice","prompt":"hey!!! check out our amazing platform"}'

# taste_judge — score competing drafts before send
curl -sX POST "$B/v1/judge" -H 'Content-Type: application/json' \
  -d '{"subject_id":"voice","candidates":["c_warm","c_hype"]}'
```

## Docs

`docs/agent-demo.md` (10-minute demo) · `docs/v1-api.md` (API) · `docs/taste-os.md` (category).
