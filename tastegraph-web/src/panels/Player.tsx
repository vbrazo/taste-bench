import { useEffect, useRef, useState } from "react";
import type { AssetVector, EngagementAction } from "@tastegraph/sdk";

interface Props {
  assets: AssetVector[];
  queue: string[];
  onEngage: (assetId: string, action: EngagementAction, dwellMs?: number) => void;
}

const TASKS = ["Video", "Image", "Text", "Audio"] as const;

export function Player({ assets, queue, onEngage }: Props) {
  const [task, setTask] = useState<(typeof TASKS)[number]>("Video");
  const [idx, setIdx] = useState(0);
  const enteredAt = useRef<number>(Date.now());

  const byId = new Map(assets.map((a) => [a.id, a]));
  const all = queue.map((id) => byId.get(id)).filter((a): a is AssetVector => !!a);
  // filter by TASK media type; fall back to all if nothing matches (text-only demo)
  const wantType = task.toLowerCase();
  const filtered = all.filter((a) => (a.type ?? "text") === wantType);
  const ordered = filtered.length ? filtered : all;
  const current = ordered[idx % Math.max(1, ordered.length)];

  // dwell: when the current asset changes, emit dwell for the previous one
  useEffect(() => {
    enteredAt.current = Date.now();
    return () => {
      const dwellMs = Date.now() - enteredAt.current;
      if (current && dwellMs > 300) onEngage(current.id, "dwell", dwellMs);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id]);

  if (!current) return <div className="player empty">No assets loaded.</div>;

  const advance = (delta: number) => setIdx((i) => (i + delta + ordered.length) % ordered.length);

  return (
    <div className="player">
      <div className="task-bar">
        <span className="task-label">TASK</span>
        <select value={task} onChange={(e) => setTask(e.target.value as any)}>
          {TASKS.map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>
      <div className="stage" data-testid="stage">
        {current.type === "video" && current.mediaUri ? (
          <video
            className="stage-media"
            src={current.mediaUri}
            poster={current.posterUri ?? undefined}
            autoPlay
            muted
            loop
            playsInline
          />
        ) : current.type === "image" && current.mediaUri ? (
          <img className="stage-media" src={current.mediaUri} alt={current.caption || current.id} />
        ) : (
          <div className="stage-fill" style={{ background: paletteBg(current) }} />
        )}
        <div className="caption">{current.caption || current.id}</div>
        <div className="clip-meta">
          {task.toUpperCase()} CLIP · {current.tags.slice(0, 3).map((t) => t.toUpperCase()).join(" · ")}
        </div>
      </div>
      <div className="controls">
        <button onClick={() => { onEngage(current.id, "like"); advance(1); }}>♥ Like</button>
        <button onClick={() => { onEngage(current.id, "save"); }}>⭑ Save</button>
        <button onClick={() => { onEngage(current.id, "deep_scroll"); }}>↧ Deep scroll</button>
        <button onClick={() => { onEngage(current.id, "dismiss"); advance(1); }}>✕ Dismiss</button>
        <button className="ghost" onClick={() => advance(1)}>Next ⏭</button>
      </div>
    </div>
  );
}

function paletteBg(a: AssetVector): string {
  const hexes = a.tags.filter((t) => /^#/.test(t));
  if (hexes.length >= 2) return `linear-gradient(135deg, ${hexes[0]}, ${hexes[1]})`;
  return "linear-gradient(135deg, #3a3a3a, #1a1a1a)";
}
