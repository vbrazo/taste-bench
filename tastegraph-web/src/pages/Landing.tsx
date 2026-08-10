import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

/** Landing — taste graph for builders: personalize, agent tools, less slop. */

/* ------------------------------------------------------------------ hooks */

function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    if (typeof matchMedia === "undefined") return;
    const mq = matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

/** rAF count-up that starts when `run` flips true. Honors reduced motion (jumps to end). */
function useCountUp(target: number, run: boolean, reduced: boolean, ms = 1100) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!run) return;
    if (reduced) return setN(target);
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(eased * target));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run, reduced, ms]);
  return n;
}

/* ---------------------------------------------------------------- hero graph */

type Node = { id: string; x: number; y: number; r: number; kind: "aud" | "brand" | "content"; label?: string };
type Edge = [string, string];

const NODES: Node[] = [
  { id: "aud", x: 250, y: 150, r: 26, kind: "aud", label: "audience" },
  { id: "brand", x: 690, y: 300, r: 26, kind: "brand", label: "brand · voice" },
  { id: "c1", x: 120, y: 300, r: 12, kind: "content" },
  { id: "c2", x: 400, y: 80, r: 14, kind: "content" },
  { id: "c3", x: 470, y: 250, r: 16, kind: "content" },
  { id: "c4", x: 590, y: 120, r: 12, kind: "content" },
  { id: "c5", x: 340, y: 340, r: 13, kind: "content" },
  { id: "c6", x: 800, y: 170, r: 12, kind: "content" },
  { id: "c7", x: 640, y: 420, r: 11, kind: "content" },
];

const EDGES: Edge[] = [
  ["aud", "c1"], ["aud", "c2"], ["aud", "c3"], ["aud", "c5"],
  ["c3", "brand"], ["c4", "brand"], ["c6", "brand"], ["brand", "c7"],
  ["c2", "c4"], ["c3", "c6"],
];

const byId = (id: string) => NODES.find((n) => n.id === id)!;

function HeroGraph({ reduced }: { reduced: boolean }) {
  const ref = useRef<SVGSVGElement>(null);
  // pointer parallax — transform-only, throttled by rAF
  useEffect(() => {
    if (reduced) return;
    const svg = ref.current;
    if (!svg) return;
    let raf = 0;
    let tx = 0, ty = 0;
    const onMove = (e: PointerEvent) => {
      const r = svg.getBoundingClientRect();
      tx = ((e.clientX - r.left) / r.width - 0.5) * 2;
      ty = ((e.clientY - r.top) / r.height - 0.5) * 2;
      if (!raf) raf = requestAnimationFrame(apply);
    };
    const apply = () => {
      raf = 0;
      svg.querySelectorAll<SVGGElement>("[data-depth]").forEach((g) => {
        const d = Number(g.dataset.depth);
        g.style.transform = `translate(${tx * d}px, ${ty * d}px)`;
      });
    };
    const host = svg.parentElement!;
    host.addEventListener("pointermove", onMove);
    return () => { host.removeEventListener("pointermove", onMove); cancelAnimationFrame(raf); };
  }, [reduced]);

  return (
    <svg
      ref={ref}
      className={`graph-svg${reduced ? " no-motion" : ""}`}
      viewBox="0 0 900 480"
      role="img"
      aria-label="A taste graph linking an audience subject and a brand-voice subject through shared content."
    >
      <defs>
        <radialGradient id="glowA" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.5" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* edges */}
      <g className="edges" data-depth="4">
        {EDGES.map(([a, b], i) => {
          const na = byId(a), nb = byId(b);
          return (
            <line
              key={a + b}
              x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
              className="gedge"
              style={{ ["--i" as string]: i } as React.CSSProperties}
            />
          );
        })}
      </g>

      {/* travelling signal pulse along a spine edge */}
      {!reduced && (
        <circle className="signal" r="4">
          <animateMotion dur="3.4s" repeatCount="indefinite"
            path={`M${byId("aud").x} ${byId("aud").y} L${byId("c3").x} ${byId("c3").y} L${byId("brand").x} ${byId("brand").y}`} />
        </circle>
      )}

      {/* nodes — parallax lives on the depth-layer wrappers so it never
          clobbers each node's own translate() positioning transform */}
      {([[9, "content"], [5, "subject"]] as const).map(([depth, layer]) => (
        <g className="nodes" data-depth={depth} key={layer}>
          {NODES.filter((n) => (layer === "content" ? n.kind === "content" : n.kind !== "content")).map((n, i) => (
            <g
              key={n.id}
              className={`gnode k-${n.kind}`}
              style={{ ["--i" as string]: i } as React.CSSProperties}
              transform={`translate(${n.x} ${n.y})`}
            >
              {n.kind !== "content" && <circle className="glow" r={n.r * 2.4} fill="url(#glowA)" />}
              <circle className="dot" r={n.r} />
              {n.label && (
                <text className="glabel" y={n.r + 18} textAnchor="middle">{n.label}</text>
              )}
            </g>
          ))}
        </g>
      ))}
    </svg>
  );
}

/* --------------------------------------------------------- dual-subject panel */

const DUAL = {
  aud: {
    tab: "Personalize",
    subject: "subject_id: u_318",
    kicker: "Rerank, ask, explain.",
    body: "Build a taste graph from signals, then discover and answer in the subject's preference — from the first click.",
    calls: [
      ["POST", "/v1/search", "on-taste discovery"],
      ["POST", "/v1/rerank", "candidate order"],
      ["POST", "/v1/ask", "taste Q&A"],
    ] as const,
    out: { title: "taste_context", lines: ["prefers: warm, specific, concrete", "avoids: hype, filler, emoji spam", "confidence: 0.82"] },
  },
  brand: {
    tab: "Less slop",
    subject: "subject_id: voice_founder",
    kicker: "Keep drafts on-taste.",
    body: "Same subject model for brand or voice. Enhance and judge so agents don't ship generic defaults.",
    calls: [
      ["POST", "/v1/brand/ingest", "voice from refs"],
      ["POST", "/v1/enhance", "on-taste rewrite"],
      ["POST", "/v1/judge", "score drafts"],
    ] as const,
    out: { title: "taste_judge", lines: ["draft A · 0.71  on-taste", "draft B · 0.44  generic", "verdict: send A"] },
  },
};

function DualPanel({ reduced }: { reduced: boolean }) {
  const [face, setFace] = useState<"aud" | "brand">("aud");
  const [touched, setTouched] = useState(false);
  useEffect(() => {
    if (reduced || touched) return;
    const t = setInterval(() => setFace((f) => (f === "aud" ? "brand" : "aud")), 4200);
    return () => clearInterval(t);
  }, [reduced, touched]);

  const pick = (f: "aud" | "brand") => { setTouched(true); setFace(f); };
  const d = DUAL[face];

  return (
    <div className="dualx">
      <div className="dualx-tabs" role="tablist" aria-label="Taste subject">
        {(["aud", "brand"] as const).map((f) => (
          <button
            key={f}
            role="tab"
            aria-selected={face === f}
            className={`dualx-tab${face === f ? " on" : ""}`}
            onClick={() => pick(f)}
          >
            {DUAL[f].tab}
          </button>
        ))}
      </div>

      <div className="dualx-engine">
        <div className="dualx-engine-tag">one engine · same /v1</div>
        <div key={face} className="dualx-body" role="tabpanel">
          <div className="dualx-in">
            <p className="dualx-subject mono">{d.subject}</p>
            <h3>{d.kicker}</h3>
            <p className="dualx-lead">{d.body}</p>
            <ul className="dualx-calls">
              {d.calls.map(([m, p, note]) => (
                <li key={p}>
                  <span className="m">{m}</span>
                  <span className="path mono">{p}</span>
                  <span className="note">{note}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="dualx-out">
            <div className="dualx-out-head mono">{d.out.title}</div>
            {d.out.lines.map((l) => (
              <div key={l} className="dualx-out-line mono">{l}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- demo loop */

type Step = { call: string; note: string };
const STEPS: Step[] = [
  { call: `POST /v1/entity/u1/link  { "target_id":"c1", "action":"like" }`, note: "Signal in — taste vector shifts toward warm + concrete." },
  { call: `POST /v1/rerank  { "user_id":"u1", "candidates":[…] }`, note: "Candidates reorder by affinity — personalization without memorizing clicks." },
  { call: `POST /v1/judge  { "subject_id":"u1", "candidates":[…] }`, note: "Score drafts against taste so agents ship less slop." },
];

// taste vector per step (0..1 bars)
const VECTORS = [
  [0.32, 0.5, 0.28, 0.6, 0.4],
  [0.44, 0.62, 0.35, 0.55, 0.52],
  [0.7, 0.82, 0.48, 0.66, 0.74],
];
const DIMS = ["warm", "specific", "playful", "concrete", "calm"];
const DRAFT_BEFORE = "hey!!! just wanted to reach out real quick about our amazing platform 🚀🚀";
const DRAFT_AFTER = "Hi Dana — noticed your team ships weekly. Here's the one thing that'd save you a day.";

function DemoLoop({ reduced }: { reduced: boolean }) {
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(!reduced);
  useEffect(() => {
    if (!playing || reduced) return;
    const t = setInterval(() => setStep((s) => (s + 1) % STEPS.length), 3200);
    return () => clearInterval(t);
  }, [playing, reduced]);

  const vec = VECTORS[step];
  return (
    <div className="demox">
      <div className="demox-left">
        <div className="demox-console">
          {STEPS.map((s, i) => (
            <div key={i} className={`demox-line${i === step ? " on" : ""}${i < step ? " done" : ""}`}>
              <span className="mono call">{s.call}</span>
            </div>
          ))}
        </div>
        <p className="demox-note" key={step}>{STEPS[step].note}</p>
        <div className="demox-ctrls">
          <button className="demox-btn" onClick={() => setPlaying((p) => !p)} aria-pressed={playing}>
            {playing ? "❚❚ Pause" : "► Play"}
          </button>
          <div className="demox-steps" role="tablist" aria-label="Loop step">
            {STEPS.map((_, i) => (
              <button
                key={i}
                role="tab"
                aria-selected={i === step}
                aria-label={`Step ${i + 1}`}
                className={`demox-pip${i === step ? " on" : ""}`}
                onClick={() => { setPlaying(false); setStep(i); }}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="demox-right">
        <div className="demox-vec">
          <div className="demox-vec-head mono">taste vector</div>
          {DIMS.map((dim, i) => (
            <div className="demox-bar" key={dim}>
              <span className="lbl">{dim}</span>
              <span className="track"><span className="fill" style={{ width: `${vec[i] * 100}%` }} /></span>
            </div>
          ))}
        </div>
        <div className="demox-draft">
          <div className={`demox-draft-row before${step >= 2 ? " out" : ""}`}>
            <span className="tag">draft</span>
            <span>{DRAFT_BEFORE}</span>
          </div>
          <div className={`demox-draft-row after${step >= 2 ? " in" : ""}`}>
            <span className="tag on">on-taste</span>
            <span>{DRAFT_AFTER}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- stat strip */

function Stat({ value, suffix, label, run, reduced }: { value: number; suffix?: string; label: string; run: boolean; reduced: boolean }) {
  const n = useCountUp(value, run, reduced);
  return (
    <div className="stat">
      <span className="stat-n">{n}{suffix}</span>
      <span className="stat-l">{label}</span>
    </div>
  );
}

/* --------------------------------------------------------------------- page */

export function Landing() {
  const reduced = useReducedMotion();
  const [statsRun, setStatsRun] = useState(false);
  const statsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const io = new IntersectionObserver(
      (es) =>
        es.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            if (e.target === statsRef.current) setStatsRun(true);
            io.unobserve(e.target);
          }
        }),
      { threshold: 0.14, rootMargin: "0px 0px -8% 0px" },
    );
    document.querySelectorAll(".lp .reveal:not(.in)").forEach((el) => io.observe(el));
    if (statsRef.current) io.observe(statsRef.current);
    return () => io.disconnect();
  }, []);

  return (
    <div className={`lp${reduced ? " reduced" : ""}`}>
      <div className="lp-grain" aria-hidden="true" />

      <nav className="lpnav">
        <div className="wrap">
          <Link to="/" className="brand">
            <span className="mark" />
            TasteGraph
          </Link>
          <div className="navlinks">
            <a href="#graph">Taste graph</a>
            <a href="#agents">Agent tools</a>
            <a href="#api">API</a>
          </div>
          <Link className="gold sm" to="/login">
            Open dashboard
          </Link>
        </div>
      </nav>

      <header className="hero">
        <div className="wrap">
          <div className="hero-grid">
            <div className="hero-copy">
              <p className="hero-brand reveal in">TasteGraph</p>
              <h1 className="reveal in">
                A taste graph builders can query — <em>and agents can call</em>
              </h1>
              <p className="sub reveal in">
                Personalize with rerank and ask. Ship agent skills. Keep judgment measurable so
                outputs stay on-taste.
              </p>
              <div className="cta reveal in">
                <Link className="gold" to="/login">
                  Open dashboard
                </Link>
                <a className="text-link" href="#agents">
                  Agent tools
                </a>
              </div>
              <div className="stat-strip" ref={statsRef}>
                <Stat value={43} label="fingerprint leaves" run={statsRun} reduced={reduced} />
                <Stat value={12} suffix="+" label="/v1 endpoints" run={statsRun} reduced={reduced} />
                <Stat value={7} label="core agent tools" run={statsRun} reduced={reduced} />
              </div>
            </div>

            <div className="hero-graph" aria-hidden={reduced ? undefined : true}>
              <HeroGraph reduced={reduced} />
            </div>
          </div>
        </div>
      </header>

      <main id="main">
        <section id="positioning" className="sec problem">
          <div className="wrap">
            <p className="eyebrow reveal">The problem</p>
            <div className="sec-head reveal">
              <h2>Click history is not taste. Prompting is not judgment.</h2>
              <p className="lead">
                Cold-start personalization fails. Agents invent preference as ad-hoc prompts.
                TasteGraph makes the <strong>why</strong> a graph you can rerank, ask, and wire as
                tools — with TasteBench so “less slop” is measurable.
              </p>
            </div>

            <div className="ps-grid">
              <article className="ps-card ps-before reveal">
                <header>
                  <span className="ps-dot bad" />
                  <h3>Without a taste graph</h3>
                </header>
                <ul className="ps-jitter">
                  <li>memorized clicks, no <em>why</em></li>
                  <li>cold start = empty ranking</li>
                  <li>agents guess preference</li>
                </ul>
                <div className="ps-draft off">
                  <span className="tag">draft</span>
                  “hey!!! check out our amazing platform 🚀🚀🚀”
                </div>
              </article>

              <div className="ps-arrow" aria-hidden="true">
                <span className="mono">taste_rerank()</span>
                <svg viewBox="0 0 60 24"><path d="M2 12 H50 M42 5 L52 12 L42 19" /></svg>
              </div>

              <article className="ps-card ps-after reveal">
                <header>
                  <span className="ps-dot good" />
                  <h3>With TasteGraph</h3>
                </header>
                <ul className="ps-card-list">
                  <li><span className="k">search / rerank</span><span>on-taste order</span></li>
                  <li><span className="k">ask / explain</span><span>why this fits</span></li>
                  <li><span className="k">skills</span><span className="conf"><i style={{ width: "82%" }} />agent-callable</span></li>
                </ul>
                <div className="ps-draft on">
                  <span className="tag ok">on-taste</span>
                  “Ranked for u_318 — warm, specific, concrete…”
                </div>
              </article>
            </div>
          </div>
        </section>

        <section id="graph" className="sec sec-tint">
          <div className="wrap">
            <p className="eyebrow reveal">For builders</p>
            <div className="sec-head reveal">
              <h2>Personalize first. Keep drafts on-taste.</h2>
              <p className="lead">
                Lead with the taste graph — search, rerank, ask. Use enhance and judge when you need
                less slop on generation. Same <span className="mono">/v1</span>, same subjects.
              </p>
            </div>
            <div className="reveal">
              <DualPanel reduced={reduced} />
            </div>
          </div>
        </section>

        <section className="sec sec-demo">
          <div className="wrap">
            <p className="eyebrow reveal">Live loop</p>
            <div className="sec-head reveal">
              <h2>Link a signal. Rerank. Judge slop.</h2>
              <p className="lead">
                Local-first engine with a mock analyzer — no keys required to try the loop. Every
                call is real <span className="mono">/v1</span>.
              </p>
            </div>
            <div className="reveal">
              <DemoLoop reduced={reduced} />
            </div>
          </div>
        </section>

        <section id="agents" className="sec">
          <div className="wrap">
            <p className="eyebrow reveal">Agent-native</p>
            <div className="sec-head reveal">
              <h2>Tools agents can call</h2>
              <p className="lead">
                Fetch <code>/v1/skills</code> or read <code>llm.txt</code>. Wire context, search,
                and rerank into any agent — enhance and judge when drafts need a taste check.
              </p>
            </div>
            <ul className="tool-rail">
              {[
                ["taste_context", "Principles, avoid list, confidence for a subject."],
                ["taste_search", "Discover content by subject taste."],
                ["taste_rerank", "Reorder candidates for a subject."],
                ["taste_ask", "Taste-personalized Q&A."],
                ["taste_judge", "Score drafts so agents ship less slop."],
              ].map(([name, desc], i) => (
                <li className="reveal" key={name} style={{ ["--d" as string]: `${i * 70}ms` } as React.CSSProperties}>
                  <code>{name}</code>
                  <span>{desc}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="loop" className="sec">
          <div className="wrap">
            <p className="eyebrow reveal">The loop</p>
            <div className="sec-head reveal">
              <h2>Create, link, query — then ship agents</h2>
              <p className="lead">
                Builder loop for personalization. Optional enhance/judge for less slop. Measurable
                with TasteBench.
              </p>
            </div>
            <div className="loop-flow">
              {[
                ["Ingest", "Create subjects and content, link engagement into the taste graph."],
                ["Personalize", "Search, rerank, ask, and explain relative to a subject."],
                ["Agents", "Expose /v1/skills — context, search, rerank, ask, judge."],
                ["Measure", "TasteBench pairs keep on-taste claims honest."],
              ].map(([h, p], i) => (
                <div className="flow-step reveal" key={h} style={{ ["--d" as string]: `${i * 70}ms` } as React.CSSProperties}>
                  <span className="n">{i + 1}</span>
                  <h4>{h}</h4>
                  <p>{p}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="api" className="sec sec-tint">
          <div className="wrap">
            <p className="eyebrow reveal">The API</p>
            <div className="sec-head reveal">
              <h2>A taste graph you can query</h2>
              <p className="lead">
                Versioned <span className="mono">/v1</span> over a mock-first engine. Offline
                without keys; swap in VLMs and Qdrant when ready.
              </p>
            </div>
            <div className="routes">
              {[
                ["POST", "/v1/entity", "users · content · subjects"],
                ["POST", "/v1/entity/{id}/link", "build taste"],
                ["POST", "/v1/search · /rerank", "personalize"],
                ["POST", "/v1/ask · /explain", "taste Q&A"],
                ["GET", "/v1/skills", "agent tools"],
                ["GET", "/agent-context/{id}", "structured taste"],
                ["POST", "/v1/enhance", "less-slop rewrite"],
                ["POST", "/v1/judge", "score drafts"],
                ["POST", "/v1/brand/ingest", "voice from refs"],
              ].map(([m, r, d]) => (
                <div className="route reveal" key={r}>
                  <span className="m">{m}</span>
                  <span className="path">{r}</span>
                  <span className="d">{d}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="deploy" className="sec final">
          <div className="wrap narrow">
            <p className="eyebrow reveal">Quickstart</p>
            <h2 className="reveal">Build the graph. Wire the agents. Ship less slop.</h2>
            <p className="lead reveal">
              Connect with an API key for the live graph, or explore the local heatmap — same
              TasteGraph.
            </p>
            <div className="cta reveal">
              <Link className="gold" to="/login">
                Open dashboard
              </Link>
              <a className="text-link" href="#agents">
                Agent tools
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer>
        <div className="wrap">
          <div className="brand">
            <span className="mark" />
            TasteGraph
          </div>
          <p>Taste graph for builders · Apache 2.0</p>
          <p className="ftag">personalize · agents · less slop</p>
        </div>
      </footer>
    </div>
  );
}
