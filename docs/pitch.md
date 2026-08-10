# TasteGraph pitch outline

Slide-by-slide narrative for TasteGraph / TasteBench. Structure mirrors category peers
(e.g. Galya) but claims only what this repo can defend: **open, local-first preference
infrastructure** that agents can call — with **TasteBench** so lift is measurable.

Use this as a deck outline or README narrative spine. Prefer numbers from your own evals;
do not invent cold-start benchmarks you have not run.

---

## 1. Title

**Open taste infrastructure for AI agents**

Sub: Self-host the preference graph. Wire it as a skill. Measure “less slop.”

Not: “The world model for taste.”

---

## 2. Problem

Today’s engines memorize *what* people clicked, not *why*.

They break when a **new person** or a **new product** shows up — and agents fall back to
generic defaults (fluent, off-taste slop).

---

## 3. Solution

**B2B / builder taste infrastructure:** model human preference as a **taste graph**, expose
it as structured context that apps and agents query — for personalization, ranking, and
on-taste decisions.

Local-first. Forkable. Agent-callable.

---

## 4. What it powers

Three product faces (same engine):

1. **Rerank & discovery** — on-taste items rise from the first signals, not months of history.
2. **Customer intelligence** — metrics, clusters, human-readable taste cards.
3. **Agent context** — structured read (`agent_context` / skills) so agents act on who the
   subject is, not a generic default. Optional **enhance / judge** for less-slop generation.

---

## 5. How it works

```text
Signals (SDK)          Processing                 Taste graph
assets + actions  →    content intel (7D+)   →    joint embeddings
                       audience / subject         subject ↔ content
                              │                          │
                              └──────────┬───────────────┘
                                         ▼
                    API  ·  LLM retrieval  ·  Agent skill
```

Install path for builders:

```bash
pip install -e ".[tastegraph,web]"
tastebench tastegraph serve --assets data/tastegraph_assets.jsonl --port 8000
tastebench tastegraph seed-demo
# install skill: skills/tastegraph/SKILL.md  (npx skills add … --skill tastegraph)
```

---

## 6. Why TasteGraph (not a closed API clone)

| Pillar | Claim |
|--------|--------|
| **Open & local-first** | Run offline with mock analyzer; swap VLM / Qdrant when ready |
| **Map perception** | Fingerprints + signals → principles / avoid / confidence — not click tables |
| **Cold-start shaped** | Content similarity + early signals; don’t require a closed world KG |
| **Measurable** | TasteBench pairwise eval — the differentiator closed decks often skip |
| **Agent-ready** | `GET /v1/skills` + installable `SKILL.md` + HTTP recipes |

Refuse: proprietary multi-billion entity catalog as the product; frontend “anti-slop” skill packs
(that’s a different market — e.g. tasteskill.dev).

---

## 7. Competitive map (axes)

**X:** Taste intelligence (fingerprint depth, affinity quality, eval lift)  
**Y:** Agent-readiness (skills, docs, MCP later, self-serve install)

| Player | Where they sit | Your move |
|--------|----------------|-----------|
| Closed taste APIs (Galya-like) | High taste claim, hosted | Match architecture story; win on open + measure |
| Rec infra / cultural KG | Taste without agent package | Stay agent-native |
| Persona / passport networks | Agent-ish, identity-heavy | Stay preference runtime, not identity network |
| Frontend taste skills | Agent-ready, **not** preference infra | Orthogonal — don’t compete |
| **TasteGraph** | Open graph + skills + TasteBench | Own bottom-right→top-right honestly |

---

## 8. Ideal customers

1. **The builder** — prototypes personalization; finds you on GitHub; plugs in via serve + skill.
2. **The AI engineer** — wires agents (Cursor, Claude Code, in-house) to `/v1` instead of ad-hoc prompts.
3. **The channel / product agent** — embeds TasteGraph (e.g. outreach, recommenders) so *their*
   customers get taste without building the graph.

Decision-maker / enterprise comes after **proven lift**, not before.

---

## 9. Monetization (open core + cloud)

| Tier | Who | What |
|------|-----|------|
| **Free / OSS** | Indie, research, hackers | Local serve, skills, TasteBench, single-tenant |
| **Cloud / Startup** | Early teams | Hosted graph, API keys, quotas, backups |
| **Growth / Scale** | Seed–A products | Multi-tenant, support, SLA |
| **Channel** | Agent platforms | Land → expand; revenue share / ACV per deployment |

Charge for **ops and reliability**, not for locking the personalize API.

---

## 10. Go-to-market

**Two motions, one flywheel**

- **Product-led:** free self-host → 10-min demo → measured lift → paid cloud  
- **Channel-led:** agent builders embed TasteGraph → their customers become yours  

Distribution: GitHub, agent skill install, Discord/X, design partners (not conference theater first).

---

## 11. Traction template (fill with real numbers)

- Built: API · skills · dashboard · seed-demo · TasteBench  
- Next: MCP · cold-start eval published · TasteGraph Cloud stub  
- Pipeline: design partners · LOIs · ACV range (your numbers)

---

## 12. Market size (honest wedge, not $393B)

**Wedge TAM (example structure — replace with your research):**

`ACV × # AI-native products that need preference memory`

Lead with the **AI-native personalization / agent tools** wedge. Expansion to “every LLM
system” is a later slide, not the ask.

---

## 13. Path (Land → Expand → Own)

| Phase | Focus |
|-------|--------|
| **Land** | OSS funnel + skill install; 10 design partners; cloud beta |
| **Expand** | Channel embeds; TasteBench case studies; multi-tenant |
| **Own** | Default preference layer agents call — still open core |

Skip year-5 $100M slides until Year-1 reality exists.

---

## 14. Use of funds (if raising)

Weight what compounds *this* product:

1. **Agent distribution + DX** — skill, MCP, demos, docs  
2. **Eval & fingerprint depth** — TasteBench datasets, better defaults  
3. **Hosted ops** — multi-tenant cloud, compliance when deals need it  
4. **GTM** — design partners, founder-led  

De-emphasize “world model R&D” as the hero line item.

---

## 15. The ask (optional)

State capital + runway goal only if fundraising. Otherwise end on:

> Clone it. Seed it. Call it from your agent. Measure it with TasteBench.

---

## Appendix — live proof path

See [agent-demo.md](agent-demo.md) and [skills/tastegraph/SKILL.md](../skills/tastegraph/SKILL.md).

Category / architecture detail: [taste-os.md](taste-os.md).

Agent integration (Rose) contract: [rose-integration.md](rose-integration.md) ·
Pilot deploy checklist: [deploy.md](deploy.md).
