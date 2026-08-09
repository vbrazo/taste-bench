import { useState } from "react";
import type { Region, UserTaste } from "@tastegraph/sdk";
import { getEndpoint, fetchExplain } from "../api";

const ENDPOINT = getEndpoint();

interface Props {
  taste: UserTaste;
  regions: Region[];
  themes: string[];
  userId: string;
}

function localSummary(taste: UserTaste, regions: Region[], themes: string[]): string {
  if (taste.nSignals === 0) return "No taste yet — engage with a few clips and I'll describe your affinity.";
  const top = regions.slice(0, 3).map((r) => r.label).join(", ");
  const th = themes.slice(0, 3).join(", ");
  const strength = taste.confidence > 0.7 ? "strong" : taste.confidence > 0.4 ? "emerging" : "faint";
  return `Your taste is ${strength} (confidence ${taste.confidence}). You gravitate toward ${top || "a few regions"}, with recurring themes of ${th || "—"}.`;
}

export function ExplainTaste({ taste, regions, themes, userId }: Props) {
  const [text, setText] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const explain = async () => {
    if (!ENDPOINT) {
      setText(localSummary(taste, regions, themes));
      return;
    }
    setLoading(true);
    try {
      setText(await fetchExplain(userId));
    } catch {
      setText(localSummary(taste, regions, themes));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-head"><span>▾ EXPLAIN</span></div>
      <button className="explain-btn" onClick={explain} disabled={loading}>
        {loading ? "Thinking…" : "Explain my taste"}
      </button>
      {text && <p className="explain-text">{text}</p>}
    </div>
  );
}
