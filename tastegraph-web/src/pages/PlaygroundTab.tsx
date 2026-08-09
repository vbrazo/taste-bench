import { useCallback, useEffect, useState } from "react";
import { v1 } from "../api";
import { useAuth } from "../auth";

interface Entity { id: string; type: string; content?: string }

/** Server-backed /v1 explorer: create entities, link, then query the taste graph. */
export function PlaygroundTab() {
  const { mode } = useAuth();
  if (mode !== "connected") {
    return (
      <div className="pg-empty" data-testid="playground-tab">
        <div className="pg-card">
          <h3>Connect to a server</h3>
          <p className="hint">The playground calls the live <b>/v1</b> API. Log out and sign in with an
            API key (or run <code>tastebench tastegraph serve</code> and connect to it) to create
            entities, build taste, and query the graph.</p>
        </div>
      </div>
    );
  }
  return <PlaygroundInner />;
}

function PlaygroundInner() {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [user, setUser] = useState("u1");
  const [contentId, setContentId] = useState("");
  const [contentText, setContentText] = useState("");
  const [question, setQuestion] = useState("what should I recommend?");
  const [out, setOut] = useState<unknown>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await v1.listEntities();
      setEntities(data.entities || []);
    } catch (e) {
      setErr(String(e));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true); setErr(null);
    try {
      const r = await fn();
      setOut({ [label]: r });
      await refresh();
    } catch (e) {
      const status = (e as { status?: number }).status;
      setErr(status === 401 ? "Unauthorized — check your API key." : String(e));
    } finally {
      setBusy(false);
    }
  };

  const users = entities.filter((e) => e.type === "user");
  const content = entities.filter((e) => e.type !== "user");

  return (
    <div className="playground" data-testid="playground-tab">
      <div className="pg-controls">
        <section className="pg-card">
          <h3>1 · Create a user</h3>
          <div className="row">
            <input value={user} onChange={(e) => setUser(e.target.value)} placeholder="user id" />
            <button className="gold sm" disabled={busy} onClick={() => run("createUser", () => v1.createEntity(user, "user"))}>Create user</button>
          </div>
        </section>

        <section className="pg-card">
          <h3>2 · Add content</h3>
          <div className="row">
            <input value={contentId} onChange={(e) => setContentId(e.target.value)} placeholder="content id" />
          </div>
          <div className="row">
            <input value={contentText} onChange={(e) => setContentText(e.target.value)} placeholder="describe the content…" />
            <button className="gold sm" disabled={busy || !contentId} onClick={() => run("createContent", () => v1.createEntity(contentId, "content", contentText))}>Add</button>
          </div>
        </section>

        <section className="pg-card">
          <h3>3 · Build taste (link)</h3>
          <p className="hint">Click an action next to a content item to link it to <b>{user}</b>.</p>
          <div className="chips">
            {content.length === 0 && <span className="hint">No content yet.</span>}
            {content.map((c) => (
              <div key={c.id} className="chip-row">
                <span className="cid">{c.id}</span>
                {["like", "save", "click", "dismiss"].map((a) => (
                  <button key={a} className="tag-btn" disabled={busy} onClick={() => run(`link:${a}`, () => v1.link(user, c.id, a))}>{a}</button>
                ))}
              </div>
            ))}
          </div>
        </section>

        <section className="pg-card">
          <h3>4 · Query the taste graph</h3>
          <div className="row wrap">
            <button className="ghost sm" disabled={busy} onClick={() => run("search", () => v1.search(user))}>Search</button>
            <button className="ghost sm" disabled={busy} onClick={() => run("rerank", () => v1.rerank(user, content.map((c) => c.id)))}>Rerank all</button>
            <button className="ghost sm" disabled={busy} onClick={() => run("explain", () => v1.explain(user))}>Explain</button>
            <button className="ghost sm" disabled={busy} onClick={() => run("clusters", () => v1.clusters())}>Clusters</button>
          </div>
          <div className="row">
            <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="ask a question…" />
            <button className="gold sm" disabled={busy} onClick={() => run("ask", () => v1.ask(user, question))}>Ask</button>
          </div>
        </section>
      </div>

      <div className="pg-side">
        <section className="pg-card">
          <h3>Graph</h3>
          <p className="hint">{users.length} users · {content.length} content</p>
          <div className="ent-list">
            {entities.map((e) => (
              <div key={e.id} className={`ent ${e.type === "user" ? "u" : "c"}`}>
                <b>{e.id}</b><span>{e.type}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="pg-card grow">
          <h3>Response</h3>
          {err && <div className="pg-err">{err}</div>}
          <pre className="pg-out">{out ? JSON.stringify(out, null, 2) : "// results appear here"}</pre>
        </section>
      </div>
    </div>
  );
}
