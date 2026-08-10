# TasteGraph system design

How the pieces in this repo fit together. Positioning: [taste-os.md](taste-os.md).
Try path: [agent-demo.md](agent-demo.md). API: [v1-api.md](v1-api.md).

---

## 1. System overview

Two products, one stack: **TasteBench** measures taste claims; **TasteGraph** runs preference
as infrastructure agents and apps can query.

```mermaid
flowchart LR
  subgraph capture [Capture]
    Media[Media and text]
    Actions[Engagement signals]
    VoiceRefs[Brand or voice refs]
    Sdk[sdk-js]
  end

  subgraph engine [TasteGraphEngine]
    direction TB
    FP[7D fingerprints]
    Profile[Subject taste profiles]
    Joint[Joint embedding space]
    FP --> Joint
    Profile --> Joint
  end

  subgraph durable [Durability]
    Idx[Memory or Qdrant]
    State["Tenant JSONL state"]
  end

  subgraph serve [Serve]
    API["REST /v1"]
    Ctx[agent-context]
    Skill[Agent skill]
    MCP[MCP server]
    Web[Dashboard SPA]
  end

  subgraph quality [TasteBench]
    Pairs[Preference pairs]
    JudgeEval[Pairwise judges]
  end

  Media --> FP
  Actions --> Profile
  VoiceRefs --> Profile
  Sdk --> Actions
  Joint --> Idx
  engine --> State
  Joint --> API
  Joint --> Ctx
  API --> Skill
  API --> MCP
  API --> Web
  Pairs --> JudgeEval
  JudgeEval -.->|eval loop| engine
```

**Read path (builders):** ingest content → link signals → `search` / `rerank` / `ask` /
`agent-context` → optional `enhance` / `judge`.

---

## 2. End-to-end request flow

```mermaid
sequenceDiagram
  participant App as App or agent
  participant API as FastAPI
  participant Ten as TenantStore
  participant Eng as Engine
  participant Vec as Vector index
  participant Disk as JSONL persist

  App->>API: X-API-Key + /v1 request
  API->>Ten: resolve tenant engine
  Ten->>Eng: per-tenant TasteGraphEngine

  alt Write entity or link
    App->>API: POST /v1/entity or link
    API->>Eng: ingest / track
    Eng->>Vec: update embeddings
    Eng->>Disk: save_tenant
  else Personalize
    App->>API: POST /v1/rerank or search
    API->>Eng: user_taste
    Eng->>Vec: score candidates
    API-->>App: ranked results
  else Agent read
    App->>API: GET /agent-context/id
    API->>Eng: taste_card
    API-->>App: principles avoid confidence
  else Less slop
    App->>API: POST /v1/enhance or judge
    API->>Eng: subject affinity plus optional LLM
    API-->>App: rewrite or scores
  end
```

---

## 3. Inside the engine

```mermaid
flowchart TB
  subgraph assets [Assets layer]
    Analyzer[Mock or VLM analyzer]
    Store[FingerprintStore]
  end

  subgraph signals [Signals layer]
    Track[track Signal]
    Weights[weighted_assets]
    Card[taste_card]
  end

  subgraph graph [Graph layer]
    Embed[joint_embedding]
    Affinity[UserTaste and rank_candidates]
    Cluster[cluster_assets]
  end

  subgraph entities [Entity façade]
    Reg[EntityRegistry]
    Kinds[user brand voice content]
  end

  Analyzer --> Store
  Store --> Embed
  Track --> Weights
  Weights --> Affinity
  Embed --> Affinity
  Store --> Card
  Track --> Card
  Reg --> Kinds
  Reg -->|create content| Analyzer
  Reg -->|link| Track
  Affinity --> Cluster
```

| Layer | Path | Role |
|-------|------|------|
| Assets | `tastebench/tastegraph/assets/` | Fingerprint content |
| Signals | `tastebench/tastegraph/signals/` | Engagement → profiles |
| Graph | `tastebench/tastegraph/graph/` | Embeddings, affinity, backends |
| Entities | `tastebench/tastegraph/entities/` | Typed subjects + links |
| API | `tastebench/tastegraph/api/` | HTTP, tenancy, rate limits |
| Persist | `tastebench/tastegraph/persist.py` | Per-tenant JSONL |
| Skills / MCP | `skills/tastegraph/`, `mcp_server.py` | Agent distribution |
| Web | `tastegraph-web/` | Landing + heatmap / playground / CI |

---

## 4. Tenancy and storage

```mermaid
flowchart LR
  Req[Incoming HTTP] --> Auth["X-API-Key"]
  Auth --> Map[ApiKeyRegistry]
  Map --> Tid[tenant_id]
  Tid --> TS[TenantStore]
  TS --> E[Isolated engine]
  E --> V[Vector backend]
  E --> D["DATA_DIR / tenant / *.jsonl"]
```

- No API keys → shared **dev** tenant (local demos).
- With keys → one engine + one state directory per tenant.
- Vectors: in-process memory or Qdrant. Graph metadata: JSONL on disk.

---

## 5. How agents attach

```mermaid
flowchart LR
  Agent[Coding agent]
  Agent --> Skill["SKILL.md install"]
  Agent --> MCP[MCP stdio]
  Agent --> Client[Python client]
  Skill --> HTTP[HTTP tools]
  MCP --> HTTP
  Client --> HTTP
  HTTP --> Server[tastegraph serve]
  Server --> Tools["context · search · rerank · ask · enhance · judge"]
```

Canonical loop: **context → rerank → judge**.

---

## 6. Repository layout

```text
taste-bench/
  tastebench/            # TasteBench eval + TasteGraph runtime
    tastegraph/
  tastegraph-web/        # Landing + dashboard
  sdk-js/                # Browser signal capture
  skills/tastegraph/     # Installable agent skill
  docs/                  # API, deploy, architecture
  data/                  # Sample assets, eval fixtures, persisted state
```

---

## 7. Critical path vs legacy

**Critical path:** durable graph → personalize API → skill / MCP → TasteBench.

Legacy or secondary modules (passport, packs, export, etc.) are not required for the builder
funnel; use [v1-api.md](v1-api.md) for the consumer contract.
