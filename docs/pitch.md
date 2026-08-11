# TasteGraph pitch outline

Slide-by-slide narrative for TasteGraph / TasteBench. Claims only what the repo can defend
today: **open, local-first preference infrastructure** agents can call — durable, skill/MCP
wired, measurable with TasteBench.

Use as a deck outline or README spine. Prefer your own eval numbers; do not invent cold-start
benchmarks you have not run.

Diagrams: [architecture.md](architecture.md). Pilot ops: [deploy.md](deploy.md).

---

## 1. Title

**Open taste infrastructure for AI agents**

Sub: Self-host the preference graph. Wire it as a skill or MCP. Measure “less slop.”

Not: “The world model for taste.” Not: a frontend anti-slop skill pack.

---

## 2. Problem

Today’s engines memorize *what* people clicked, not *why*.

They break when a **new person** or a **new product** shows up — and agents fall back to
generic defaults (fluent, off-taste slop).

Every product reinvents preference as ad-hoc prompting.

---

## 3. Solution

**Builder taste infrastructure:** model human preference as a **taste graph**, expose it as
structured context apps and agents query — for personalization, ranking, and on-taste
decisions.

Local-first. Forkable. Durable across restarts. Agent-callable (HTTP · skill · MCP).

---

## 4. What it powers

Three faces, one engine:

1. **Rerank & discovery** — on-taste items rise from early signals, not months of history.
2. **Customer intelligence** — metrics, clusters, human-readable taste cards.
3. **Agent context** — structured read so agents act on who the subject is; optional
   **enhance / judge** for less-slop generation (`mode: llm | heuristic` so quality is honest).

---

## 5. How it works

```text
Capture                     Engine                         Serve
media + signals + voice  →  fingerprints + taste profiles  →  /v1 · agent-context
refs                        joint embeddings                    skill · MCP · SPA
        │                         │                              │
        └─────────────────────────┴──────────────────────────────┘
                    Memory/Qdrant  ·  tenant JSONL persist
                    TasteBench eval loop (measure claims)
```

**10-minute builder path (shipped):**

```bash
pip install -e ".[tastegraph,web]"
tastebench tastegraph serve --assets data/tastegraph_assets.jsonl --port 8000
tastebench tastegraph seed-demo
# skill: skills/tastegraph/SKILL.md
# MCP:   tastebench tastegraph mcp   # optional extra
```

Pilot host: Docker Compose + API keys + data volume — see [deploy.md](deploy.md).

---

## 6. Why TasteGraph (not a closed API clone)

| Pillar | Claim (today) |
|--------|----------------|
| **Open & local-first** | Mock analyzer offline; swap VLM / Qdrant when ready |
| **Durable** | Per-tenant JSONL state + vector backend — survives restart |
| **Map perception** | Fingerprints + signals → principles / avoid / confidence |
| **Cold-start shaped** | Content similarity + early signals — no proprietary world KG |
| **Measurable** | TasteBench + voice outreach eval fixture |
| **Agent-ready** | `GET /v1/skills` · installable `SKILL.md` · thin MCP · Python client |

Refuse: closed hosted-only lock-in; frontend “taste skill” packs as the category (orthogonal).

---

## 7. Competitive map

**X:** Taste intelligence · **Y:** Agent-readiness

| Player | Your move |
|--------|-----------|
| Closed taste APIs | Match the architecture story; win on open + measure + self-host |
| Rec infra / cultural KG | Stay agent-native (skill + MCP), not catalog theater |
| Persona / passport networks | Stay preference runtime, not identity product |
| Frontend taste skills | Orthogonal — we store and query preference, not UI rules |
| **TasteGraph** | Open graph + durable serve + skill/MCP + TasteBench |

---

## 8. Ideal customers

1. **The builder** — GitHub → serve → seed-demo → skill in under 10 minutes.
2. **The AI engineer** — wires Cursor / Claude Code / in-house agents to `/v1` or MCP.
3. **The channel product** — embeds TasteGraph so *their* users get fit / voice / less slop
   without building a graph (outbound, recommenders, copilots).

Enterprise / C-suite after proven lift — not before.

---

## 9. Monetization (open core + cloud)

| Tier | What |
|------|------|
| **Free / OSS** | Local serve, skill, MCP, TasteBench, single-tenant |
| **Cloud / Startup** | Hosted graph, API keys, quotas, durable backups |
| **Growth / Scale** | Multi-tenant, support, SLA |
| **Channel** | Land → expand; rev-share / ACV per deployment |

Charge for **ops and reliability**, not for locking personalize APIs.

---

## 10. Go-to-market

- **Product-led:** free self-host → 10-min demo → measured lift → paid cloud  
- **Channel-led:** agent products embed TasteGraph → their customers become yours  

Distribution: GitHub, skill install, MCP, Discord/X, design partners.

---

## 11. Traction (update with real numbers)

**Built (in repo today):**

- Personalize API · enhance/judge · seed-demo  
- Installable agent skill · thin MCP  
- Tenant persistence · request logging · deploy checklist  
- Dashboard (heatmap / playground / intelligence) · TasteBench + voice eval fixture  
- Architecture + integration docs  

**Next:**

- Published cold-start / lift case study with numbers  
- TasteGraph Cloud (hosted)  
- Design partners / LOIs (your pipeline)

---

## 12. Market size (honest wedge)

`ACV × # AI-native products that need preference memory`

Lead with agent tools + personalization. Skip “every LLM / humanoid” TAM theater.

---

## 13. Path

| Phase | Focus |
|-------|--------|
| **Land** | OSS funnel + skill/MCP; design partners; cloud beta |
| **Expand** | Channel embeds; TasteBench case studies; multi-tenant |
| **Own** | Default preference layer agents call — still open core |

---

## 14. Use of funds (if raising)

1. **Agent distribution + DX** — skill, MCP, demos  
2. **Eval & fingerprint depth** — TasteBench datasets, better defaults  
3. **Hosted ops** — durable multi-tenant cloud, compliance when deals need it  
4. **GTM** — design partners, founder-led  

Not: “world model R&D” as the hero line.

---

## 15. Close

Fundraising ask only if raising. Otherwise:

> Clone it. Seed it. Call it from your agent (skill or MCP). Measure it with TasteBench.

---

## Appendix

| Doc | Use |
|-----|-----|
| [agent-demo.md](agent-demo.md) | 10-minute proof |
| [architecture.md](architecture.md) | System diagrams |
| [deploy.md](deploy.md) | Pilot Compose checklist |
| [v1-api.md](v1-api.md) | Frozen consumer routes |
| [taste-os.md](taste-os.md) | Category / roadmap |
| [rose-integration.md](rose-integration.md) | Example channel consumer contract |
| [`skills/tastegraph/SKILL.md`](../skills/tastegraph/SKILL.md) | Agent install |
