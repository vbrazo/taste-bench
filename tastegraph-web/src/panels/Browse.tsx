import type { Region } from "@tastegraph/sdk";

interface Props {
  regions: Region[];
  themes: string[];
  selected: string | null;
  onSelect: (regionId: string | null) => void;
}

export function Browse({ regions, themes, selected, onSelect }: Props) {
  return (
    <div className="panel">
      <div className="panel-head"><span>▾ BROWSE</span></div>
      <div className="list-label">TASTE REGIONS</div>
      <div className="browse-list">
        {regions.length === 0 && <div className="empty">Engage with media to build regions.</div>}
        {regions.map((r) => (
          <button
            key={r.id}
            className={`row ${selected === r.id ? "row-active" : ""}`}
            onClick={() => onSelect(selected === r.id ? null : r.id)}
          >
            {r.label}
          </button>
        ))}
      </div>
      <div className="list-label">TOP THEMES</div>
      <div className="browse-list">
        {themes.map((t) => (
          <div key={t} className="row row-static">{t}</div>
        ))}
      </div>
    </div>
  );
}
