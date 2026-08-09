import { useEffect, useMemo, useState } from "react";
import type { AssetVector, Region } from "@tastegraph/sdk";
import { useAffinity } from "../useAffinity";
import { AffinityMap } from "../panels/AffinityMap";
import { Browse } from "../panels/Browse";
import { EngagementStream } from "../panels/EngagementStream";
import { Player } from "../panels/Player";
import { ExplainTaste } from "../panels/ExplainTaste";

interface Bundle {
  assets: AssetVector[];
  regions?: Region[];
}

const USER_ID = "web_user";

/** The local-first taste-heatmap: engage with media, watch affinity build in-browser. */
export function HeatmapTab() {
  const [assets, setAssets] = useState<AssetVector[]>([]);
  const [bundleRegions, setBundleRegions] = useState<Region[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    fetch("/taste-bundle.json")
      .then((r) => r.json())
      .then((b: Bundle) => {
        setAssets(b.assets);
        setBundleRegions(b.regions ?? []);
      })
      .catch(() => setAssets([]));
  }, []);

  const aff = useAffinity(assets, bundleRegions);

  const queue = useMemo(() => {
    const region = aff.regions.find((r) => r.id === selected);
    const ids = region ? region.memberIds : assets.map((a) => a.id);
    return aff.rank(ids).map(([id]) => id);
  }, [assets, aff, selected]);

  return (
    <div className="heatmap" data-testid="heatmap-tab">
      <main className="stage-col">
        <Player assets={assets} queue={queue} onEngage={aff.track} />
      </main>
      <aside className="sidebar">
        <header className="sidebar-head">
          <div className="eyebrow">LIVE AFFINITY · {aff.serverSync ? "CONNECTED" : "LOCAL ONLY"}</div>
          <h2 className="side-title">Taste heatmap</h2>
          <p className="sub">
            History is built locally with affinity rules (like / deep read / deep scroll / dwell).
            {" "}{aff.events.length} events · {aff.serverSync ? "SDK synced" : "SDK local"} · regions {aff.regionSource}.
          </p>
        </header>
        <AffinityMap regions={aff.regions} taste={aff.taste} selected={selected} onSelect={setSelected} />
        <Browse regions={aff.regions} themes={aff.themes} selected={selected} onSelect={setSelected} />
        <ExplainTaste taste={aff.taste} regions={aff.regions} themes={aff.themes} userId={USER_ID} />
        <EngagementStream events={aff.events} />
        <button className="reset-all" onClick={aff.reset}>Reset history</button>
      </aside>
    </div>
  );
}
