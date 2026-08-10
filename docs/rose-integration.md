# Rose ↔ TasteGraph integration contract

One doc for a Rose engineer to integrate against TasteGraph. Rose (warm-first outbound) calls
TasteGraph at inference for **fit**, **voice**, and **whether to send** — TasteGraph never owns
CRM, approval, or sending.

## Base URL & auth

- Base URL: `TASTEGRAPH_BASE_URL` (pilot default `http://127.0.0.1:8000`).
- Auth: header `X-API-Key: <rose_key>` when the server has `TASTEGRAPH_API_KEYS` set (e.g.
  `{"rose_key":"rose"}`). Omit only against a dev-mode server.
- Content type: `application/json`. All bodies and responses are JSON.

## Rose needs → routes

| Rose need | Call | Subject |
|---|---|---|
| Who fits the thesis | `POST /v1/rerank`, `POST /v1/search` | ICP / account subject |
| Warm angle / why-them | `GET /agent-context/{subject_id}` | lead (and/or account) |
| Draft in founder voice | `POST /v1/enhance` | `founder_voice` |
| Send vs wait / rewrite | `POST /v1/judge` | voice (candidates = drafts) |
| Build the voice subject | `POST /v1/brand/ingest` | `founder_voice` from reference copy |
| Discover tools at runtime | `GET /v1/skills` | — |

**Boundary:** sales workflow, CRM, approval UX, and actually sending stay in Rose. TasteGraph
stays domain-agnostic — no lead storage, no send.

## Routes: request → success shape

Below, `$B` is the base URL; add `-H 'X-API-Key: rose_key'` when auth is on.

### `GET /agent-context/{subject_id}` — taste read
```json
{ "subject_id": "lead_318", "confidence": 0.82, "n_signals": 4, "resolved": true,
  "principles": ["warm","specific","concrete"], "avoid": ["hype"], "top_assets": ["c_warm"] }
```

### `POST /v1/rerank` — order candidates by taste
Request: `{ "user_id": "icp_acme", "candidates": ["lead_a","lead_b"] }`
```json
{ "results": [ {"id":"lead_a","score":0.71}, {"id":"lead_b","score":0.44} ] }
```
(`POST /v1/search` with `{ "user_id","k" }` returns the same `{"results":[{id,score}]}` shape.)

### `POST /v1/brand/ingest` — build a voice subject
Request: `{ "id":"founder_voice", "type":"voice", "references":[{"content":"warm, specific, concrete"}] }`
```json
{ "brand": {"id":"founder_voice","type":"voice"}, "linked": ["founder_voice_ref_0"], "n_signals": 1 }
```

### `POST /v1/enhance` — rewrite a draft on-voice
Request: `{ "subject_id":"founder_voice", "prompt":"hey wanted to connect" }`
```json
{ "enhanced": "…on-voice rewrite…", "source": "template", "mode": "heuristic", "subject_id": "founder_voice" }
```
`mode` is `"llm"` when `TASTEGRAPH_ENHANCE_MODEL` is configured, else `"heuristic"` (a
deterministic stub) — never treat heuristic output as production-quality copy.

### `POST /v1/judge` — score drafts before send
Request: `{ "subject_id":"founder_voice", "candidates":["draft A","draft B"] }`
```json
{ "results": [ {"id":"c0","text":"draft A","score":0.71,"rationale":"…"},
               {"id":"c1","text":"draft B","score":0.44,"rationale":"…"} ],
  "source": "template", "mode": "heuristic", "subject_id": "founder_voice" }
```
Results are sorted best-first. Use `mode` to decide whether the score is LLM- or heuristic-grade.

### `GET /v1/skills` — live tool schemas
Returns `{ "tools": [ …OpenAI-style function schemas… ], "names": ["taste_context", …] }`.

## Common errors

| Status | When |
|---|---|
| `400` | Unknown entity type, entity already exists, bad link (source must be user/brand, target must be content), empty `candidates`. Detail string explains. |
| `401` | Missing/invalid `X-API-Key` while auth is enforced. |
| `429` | Rate/quota exceeded — honor the `Retry-After` header. |

## Two ways to wire it

- **HTTP / SKILL.md** (default) — the installable skill
  [`skills/tastegraph/SKILL.md`](../skills/tastegraph/SKILL.md) teaches an agent the curl recipes
  above. Best when Rose already speaks HTTP.
- **MCP** — `tastebench tastegraph mcp` (needs the `mcp` extra) exposes the same builder tools
  (context, search, rerank, ask, enhance, judge, brand_ingest) over stdio for MCP-native hosts.
  It is a thin wrapper over the same HTTP API — identical behavior, different transport.

## Durability & state

State is per-tenant and durable when the server runs with `TASTEGRAPH_DATA_DIR` set (see
[deploy.md](deploy.md)); a restart preserves the voice subject and any built taste.

**Done when:** a Rose engineer can integrate from this one doc.
