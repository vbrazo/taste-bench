import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { HeatmapTab } from "./HeatmapTab";
import { PlaygroundTab } from "./PlaygroundTab";

type Tab = "heatmap" | "playground";

export function Dashboard() {
  const { mode, endpoint, logout } = useAuth();
  const nav = useNavigate();
  const [tab, setTab] = useState<Tab>("heatmap");

  const onLogout = () => {
    logout();
    nav("/login");
  };

  return (
    <div className="dash">
      <header className="dash-nav">
        <Link to="/" className="brand"><span className="mark" />TasteGraph</Link>
        <div className="tabs">
          <button className={tab === "heatmap" ? "tab on" : "tab"} onClick={() => setTab("heatmap")}>Taste heatmap</button>
          <button className={tab === "playground" ? "tab on" : "tab"} onClick={() => setTab("playground")}>API playground</button>
        </div>
        <div className="dash-right">
          <span className="status-pill">
            {mode === "connected" ? `● ${endpoint.replace(/^https?:\/\//, "")}` : "○ local mode"}
          </span>
          <button className="ghost sm" onClick={onLogout}>Log out</button>
        </div>
      </header>
      <div className="dash-body">
        {tab === "heatmap" ? <HeatmapTab /> : <PlaygroundTab />}
      </div>
    </div>
  );
}
