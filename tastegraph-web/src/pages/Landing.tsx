import { useEffect } from "react";
import { Link } from "react-router-dom";

const cloud = "M3 4h1V3h1V2h3v1h2v1h2v2H1V5h2z";

export function Landing() {
  useEffect(() => {
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }),
      { threshold: 0.1 },
    );
    document.querySelectorAll(".lp .reveal:not(.in)").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <div className="lp">
      <svg className="cloud" style={{ top: 120, width: 70, animation: "lpdrift 60s linear infinite" }} viewBox="0 0 14 7" fill="#fff"><path d={cloud} /></svg>
      <svg className="cloud" style={{ top: 230, width: 52, opacity: .8, animation: "lpdrift 84s linear -30s infinite" }} viewBox="0 0 14 7" fill="#fff"><path d={cloud} /></svg>
      <svg className="cloud" style={{ top: 340, width: 88, animation: "lpdrift 72s linear -50s infinite" }} viewBox="0 0 14 7" fill="#fff"><path d={cloud} /></svg>

      <nav className="lpnav"><div className="wrap">
        <Link to="/" className="brand"><span className="mark" />TasteGraph</Link>
        <div className="navlinks">
          <a href="#concepts">Concepts</a><a href="#loop">The Loop</a><a href="#api">API</a><a href="#deploy">Deploy</a>
        </div>
        <Link className="gold sm" to="/login">Get&nbsp;started</Link>
      </div></nav>

      <header><div className="wrap">
        <div className="chip reveal in">OPEN-SOURCE TASTE INFRASTRUCTURE</div>
        <h1 className="reveal in">Give your AI a <span className="u">sense of taste</span></h1>
        <p className="sub reveal in">Turn behavior into structured, queryable taste — for
          {" "}<b>personalization</b>, <span className="b2">ranking</span>, and <span className="b3">agents</span>.</p>
        <p className="sub reveal in">Model the <span className="pill">why</span> behind a preference, not just the <span className="pill">what</span>.</p>
        <div className="cta reveal in">
          <Link className="gold" to="/login">Open the dashboard</Link>
          <a className="ghost" href="#api">Explore the API →</a>
        </div>

        <div className="term reveal in">
          <div className="bar"><i style={{ background: "#ff5f57" }} /><i style={{ background: "#febc2e" }} /><i style={{ background: "#28c840" }} /><span className="t">tastegraph — the loop</span></div>
          <div className="who">
            <svg style={{ width: 30, height: 30 }} viewBox="0 0 8 8" fill="#d98b6b"><path d="M1 3h1V2h1V1h2v1h1v1h1v3H6v1H2V6H1z" /><rect x="2" y="4" width="1" height="1" fill="#241f1c" /><rect x="5" y="4" width="1" height="1" fill="#241f1c" /></svg>
            <div className="meta"><b>TasteGraph engine</b><br />mock analyzer · no keys<br />~/tastegraph</div>
          </div>
          <pre>
<span className="co"># create a user → give them content → build taste → query it</span>{"\n"}
<span className="p">$</span> <span className="cmd">curl</span> -X POST :8000/<span className="fl">v1/entity</span> -d <span className="st">{'\'{"id":"u1","type":"user"}\''}</span>{"\n"}
<span className="p">$</span> <span className="cmd">curl</span> -X POST :8000/<span className="fl">v1/entity/u1/link</span> -d <span className="st">{'\'{"target_id":"c1","action":"like"}\''}</span>{"\n"}
<span className="p">$</span> <span className="cmd">curl</span> -X POST :8000/<span className="fl">v1/ask</span> -d <span className="st">{'\'{"user_id":"u1","question":"what to wear?"}\''}</span>{"\n"}
<span className="ar">→</span> <span className="st">"Leaning minimal & quiet-luxury — try the oatmeal cashmere knit."</span>
          </pre>
        </div>
      </div>

        <div className="scene" aria-hidden="true">
          <svg viewBox="0 0 1200 210" preserveAspectRatio="xMidYMax slice">
            <path d="M0 150 Q150 90 320 140 T640 130 T980 140 T1200 120 V210 H0 Z" fill="#bfe6b0" />
            <path d="M0 172 Q200 120 430 165 T860 158 T1200 168 V210 H0 Z" fill="#7cc36a" />
            <rect x="0" y="196" width="1200" height="14" fill="#59a84f" />
            <path d="M40 150 C220 60 340 60 520 150 S840 240 1160 120" fill="none" stroke="#2f6d63" strokeWidth="7" />
            <path d="M40 150 C220 60 340 60 520 150 S840 240 1160 120" fill="none" stroke="#3fae9c" strokeWidth="3" strokeDasharray="2 10" />
            <g stroke="#14202b" strokeWidth="2">
              <rect x="120" y="70" width="26" height="26" rx="3" fill="#efe4d3" />
              <rect x="300" y="66" width="26" height="26" rx="3" fill="#ff8fb0" />
              <rect x="505" y="126" width="26" height="26" rx="3" fill="#8fb7ff" />
              <rect x="700" y="176" width="26" height="26" rx="3" fill="#ffd66e" />
              <rect x="1010" y="112" width="26" height="26" rx="3" fill="#b79bff" />
            </g>
            <g transform="translate(432,150)"><rect x="-14" y="-14" width="30" height="16" rx="3" fill="#e0518a" stroke="#14202b" strokeWidth="2" /><circle cx="-6" cy="4" r="4" fill="#14202b" /><circle cx="8" cy="4" r="4" fill="#14202b" /></g>
            <g transform="translate(1120,120)"><rect x="-3" y="30" width="6" height="24" fill="#7a4a1e" /><path d="M-16 30 L0 0 L16 30 Z" fill="#3aa66a" stroke="#14202b" strokeWidth="2" /></g>
          </svg>
        </div>
      </header>

      <section className="band problem"><div className="wrap">
        <div className="kicker reveal" style={{ color: "var(--pink)" }}>THE PROBLEM</div>
        <h2 className="reveal">Engines memorize <em>what</em> people clicked, not <em>why</em> — so they break the moment a new person, or a new product, shows up.</h2>
      </div></section>

      <section id="concepts"><div className="wrap">
        <div className="kicker reveal">CORE CONCEPTS</div>
        <h2 className="reveal">A small, composable model of taste.</h2>
        <p className="lead reveal">Everything is an <b>entity</b>. Users build taste by <b>linking</b> to content. Both live in one <b>joint embedding</b> — so affinity works even for brand-new users and items.</p>
        <div className="grid">
          {[
            ["EN", "var(--violet)", "Unified entities", "One model for users, content, and your own custom types — each with a type, content, and metadata."],
            ["LK", "var(--teal)", "Links build taste", "A user links to content with an action — view, click, like, save, dismiss — each carrying an implicit weight."],
            ["GR", "var(--blue)", "Joint embedding", "Content is fingerprinted and embedded; a user is the signal-weighted mean of what they engage with."],
            ["AF", "var(--pink)", "Cold-start affinity", "Score any item by cosine to a user's taste vector. New users still rank sensibly by content similarity."],
            ["CL", "var(--gold2)", "Taste regions", "Silhouette-picked clusters with human-readable, distinctive-tag labels. Inspect a taste graph, don't just trust it."],
            ["FP", "#d98b6b", "7-dimension fingerprint", "Every asset scored across seven dimensions — 40+ attributes — by a vision-language model, or an offline mock."],
          ].map(([b, c, h, p]) => (
            <div className="card reveal" key={h}><div className="badge" style={{ background: c }}>{b}</div><h3>{h}</h3><p>{p}</p></div>
          ))}
        </div>
      </div></section>

      <section className="band"><div className="wrap">
        <div className="kicker reveal">THE FINGERPRINT</div>
        <h2 className="reveal">Every asset, seven dimensions.</h2>
        <p className="lead reveal">A multidimensional signature that turns a raw image, clip, or text into structured, comparable taste features.</p>
        <div className="dims">
          {[["01","Semantic","caption"],["02","Emotional","mood"],["03","Aesthetic","palette"],["04","Technical","quality"],["05","Contextual","era·trend"],["06","Intent","purpose"],["07","Advanced","embedding"]].map(([n,l,s]) => (
            <div className="dim reveal" key={n}><div className="n">{n}</div><div className="l">{l}</div><div className="s">{s}</div></div>
          ))}
        </div>
      </div></section>

      <section id="loop"><div className="wrap">
        <div className="kicker reveal">THE LOOP</div>
        <h2 className="reveal">Create → content → link → query.</h2>
        <p className="lead reveal">One integrated loop, four calls. The same primitives power reranking, discovery, agent context, and Q&amp;A.</p>
        <div className="loop">
          {[["Create a user","An opaque id — no PII required."],["Give them content","Ingest content; each is fingerprinted & embedded."],["Build their taste","Link the user to content they engage with."],["Query it","Search, rerank, ask, explain, clusters."]].map(([h,p]) => (
            <div className="step reveal" key={h}><span className="a">→</span><h4>{h}</h4><p>{p}</p></div>
          ))}
        </div>
      </div></section>

      <section id="api" className="band"><div className="wrap">
        <div className="kicker reveal">THE API</div>
        <h2 className="reveal">A taste graph you can query.</h2>
        <p className="lead reveal">A versioned <span style={{ fontFamily: "var(--mono)" }}>/v1</span> entity API over a local-first engine. Runs offline — no keys — and scales out to a real vector database when you're ready.</p>
        <div className="routes">
          {[["POST","/v1/entity","users · content · types"],["POST","/v1/entity/{id}/link","build taste"],["POST","/v1/search","discovery"],["POST","/v1/rerank","reorder shortlist"],["POST","/v1/ask","taste Q&A"],["POST","/v1/explain","why, in words"],["GET","/v1/clusters","taste regions"],["GET","/health · /docs","liveness · OpenAPI"]].map(([m,r,d]) => (
            <div className="route reveal" key={r}><span className="m">{m}</span><span>{r}</span><span className="d">{d}</span></div>
          ))}
        </div>
      </div></section>

      <section id="deploy" className="final"><div className="wrap">
        <div className="kicker reveal">QUICKSTART</div>
        <h2 className="reveal">Model taste. Query it. Ship it.</h2>
        <p className="lead reveal" style={{ margin: "0 auto 26px" }}>Sign in with an API key to explore your live taste graph, or jump into the local heatmap.</p>
        <div className="cta" style={{ justifyContent: "center" }}>
          <Link className="gold" to="/login">Open the dashboard</Link>
          <a className="ghost" href="#concepts">Learn the concepts</a>
        </div>
      </div></section>

      <footer><div className="wrap">
        <div className="brand" style={{ fontSize: 19 }}><span className="mark" />TasteGraph</div>
        <div>Open-source taste infrastructure · Apache&nbsp;2.0</div>
        <span className="ftag">create → content → link → query</span>
      </div></footer>
    </div>
  );
}
