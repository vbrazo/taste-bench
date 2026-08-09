import { useMemo, useState } from "react";
import type { Region, UserTaste } from "@tastegraph/sdk";
import { cosine } from "@tastegraph/sdk";

interface Props {
  regions: Region[];
  taste: UserTaste;
  selected: string | null;
  onSelect: (regionId: string | null) => void;
}

/** A small cluster of hexes at (cx, cy), opacity encoding affinity strength. */
function HexCluster({ cx, cy, label, strength, active, onClick }: {
  cx: number; cy: number; label: string; strength: number; active: boolean; onClick: () => void;
}) {
  const r = 15;
  const offsets = [
    [0, 0], [r * 1.5, -r * 0.9], [r * 1.5, r * 0.9],
    [0, r * 1.8], [-r * 1.5, r * 0.9], [-r * 1.5, -r * 0.9], [0, -r * 1.8],
  ];
  const hex = (x: number, y: number) => {
    const pts = Array.from({ length: 6 }, (_, i) => {
      const a = (Math.PI / 3) * i + Math.PI / 6;
      return `${(x + r * Math.cos(a)).toFixed(1)},${(y + r * Math.sin(a)).toFixed(1)}`;
    });
    return pts.join(" ");
  };
  const alpha = 0.15 + 0.75 * Math.max(0, strength);
  return (
    <g onClick={onClick} style={{ cursor: "pointer" }} data-testid="region-node">
      {offsets.map(([dx, dy], i) => (
        <polygon
          key={i}
          points={hex(cx + dx, cy + dy)}
          fill={`rgba(74,110,126,${alpha.toFixed(2)})`}
          stroke={active ? "#e8e2d6" : "rgba(255,255,255,0.15)"}
          strokeWidth={active ? 2 : 1}
        />
      ))}
      <text x={cx} y={cy - r * 2.4} textAnchor="middle" className="hex-label">{label}</text>
    </g>
  );
}

export function AffinityMap({ regions, taste, selected, onSelect }: Props) {
  const [tick, setTick] = useState(0); // reset view
  const layout = useMemo(() => {
    // radial layout around a central "current user" node
    const W = 560, H = 340, cx = W / 2, cy = H / 2;
    return regions.map((reg, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, regions.length) + tick * 0.0001;
      const rad = 110 + (i % 2) * 30;
      const strength = taste.vec ? Math.max(0, cosine(taste.vec, reg.centroid)) : 0.2;
      return { reg, x: cx + rad * Math.cos(angle), y: cy + rad * Math.sin(angle), strength };
    });
  }, [regions, taste, tick]);

  return (
    <div className="panel">
      <div className="panel-head">
        <span>▾ AFFINITY MAP</span>
        <button className="ghost" onClick={() => { onSelect(null); setTick((t) => t + 1); }}>Reset view</button>
      </div>
      <svg viewBox="0 0 560 340" className="affinity-svg" role="img" aria-label="affinity map">
        {layout.map(({ reg, x, y }) => (
          <line key={`l-${reg.id}`} x1={280} y1={170} x2={x} y2={y} stroke="rgba(255,255,255,0.12)" />
        ))}
        <circle cx={280} cy={170} r={7} fill="#e8e2d6" />
        <text x={280} y={150} textAnchor="middle" className="hex-label">Current user</text>
        {layout.map(({ reg, x, y, strength }) => (
          <HexCluster
            key={reg.id}
            cx={x}
            cy={y}
            label={reg.label}
            strength={strength}
            active={selected === reg.id}
            onClick={() => onSelect(selected === reg.id ? null : reg.id)}
          />
        ))}
      </svg>
    </div>
  );
}
