import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { v1 } from "../api";
import { useAuth } from "../auth";

interface Metrics {
  people_in_graph?: number;
  assets_in_graph?: number;
  signals_ingested?: number;
  api_calls?: number;
  median_confidence?: number;
  affinity_coverage?: number;
}

interface Cluster {
  id: string;
  label: string;
  size?: number;
  memberIds?: string[];
}

/** Server-backed customer intelligence: metrics tiles + taste clusters. */
export function IntelligenceTab() {
  const { mode } = useAuth();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (mode !== "connected") return;
    let cancelled = false;
    (async () => {
      setBusy(true);
      setErr(null);
      try {
        const [m, c] = await Promise.all([v1.metrics(), v1.clusters()]);
        if (cancelled) return;
        setMetrics(m);
        setClusters(c.clusters || []);
      } catch (e) {
        if (!cancelled) setErr(String(e));
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mode]);

  if (mode !== "connected") {
    return (
      <div className="pg-empty" data-testid="intelligence-tab">
        <div className="pg-card">
          <h3>Connect to a server</h3>
          <p className="hint">
            Customer intelligence reads live <code>/metrics</code> and <code>/v1/clusters</code>.
            {" "}Log out and <Link to="/login">sign in</Link> with a TasteGraph endpoint to see graph health.
          </p>
        </div>
      </div>
    );
  }

  const tiles: { label: string; value: string }[] = [
    { label: "People in graph", value: fmt(metrics?.people_in_graph) },
    { label: "Behavioral signals", value: fmt(metrics?.signals_ingested) },
    { label: "Assets in graph", value: fmt(metrics?.assets_in_graph) },
    { label: "Median confidence", value: fmtNum(metrics?.median_confidence) },
    { label: "Affinity coverage", value: fmtNum(metrics?.affinity_coverage) },
    { label: "API calls", value: fmt(metrics?.api_calls) },
  ];

  return (
    <div className="intel" data-testid="intelligence-tab">
      {err && <div className="pg-err">{err}</div>}
      {busy && !metrics && <p className="hint">Loading graph intelligence…</p>}

      <div className="intel-tiles">
        {tiles.map((t) => (
          <div key={t.label} className="intel-tile">
            <div className="intel-val">{t.value}</div>
            <div className="intel-label">{t.label}</div>
          </div>
        ))}
      </div>

      <div className="pg-card" style={{ marginTop: 18 }}>
        <h3>Taste clusters</h3>
        {clusters.length === 0 ? (
          <p className="hint">No clusters yet — ingest content and build taste links.</p>
        ) : (
          <ul className="intel-clusters">
            {clusters.map((c) => (
              <li key={c.id}>
                <span className="cid">{c.id}</span>
                <strong>{c.label || c.id}</strong>
                <span className="muted">{c.size ?? c.memberIds?.length ?? 0} members</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function fmt(n: number | undefined): string {
  if (n === undefined || n === null) return "—";
  return Number(n).toLocaleString();
}

function fmtNum(n: number | undefined): string {
  if (n === undefined || n === null) return "—";
  return Number(n).toFixed(2);
}
