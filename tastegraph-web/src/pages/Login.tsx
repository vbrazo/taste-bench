import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { getEndpoint } from "../api";

export function Login() {
  const { connect, continueLocal } = useAuth();
  const nav = useNavigate();
  const [endpoint, setEp] = useState(getEndpoint() || "http://127.0.0.1:8000");
  const [key, setKey] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const doConnect = async () => {
    setBusy(true); setErr(null);
    try {
      await connect(endpoint, key);
      nav("/dashboard");
    } catch (e) {
      const status = (e as { status?: number }).status;
      setErr(status === 401 ? "Invalid API key for that server." : "Couldn't reach that server.");
    } finally {
      setBusy(false);
    }
  };

  const doLocal = () => { continueLocal(); nav("/dashboard"); };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <Link to="/" className="brand"><span className="mark" />TasteGraph</Link>
        <h1>Sign in</h1>
        <p className="sub">Connect to a TasteGraph server with an API key, or explore the taste
          heatmap locally in your browser.</p>

        <label>Server endpoint</label>
        <input value={endpoint} onChange={(e) => setEp(e.target.value)} placeholder="http://127.0.0.1:8000" />

        <label>API key <span className="muted">(blank = dev mode)</span></label>
        <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="X-API-Key"
          onKeyDown={(e) => e.key === "Enter" && doConnect()} />

        {err && <div className="auth-err">{err}</div>}

        <button className="gold block" disabled={busy} onClick={doConnect}>
          {busy ? "Connecting…" : "Connect to server"}
        </button>
        <div className="or">or</div>
        <button className="ghost block" onClick={doLocal}>Continue in local mode →</button>
      </div>
    </div>
  );
}
