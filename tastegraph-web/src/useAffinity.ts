import { useCallback, useEffect, useMemo, useState } from "react";
import {
  buildUserTaste,
  computeRegions,
  rankCandidates,
  topThemes,
  TasteGraph,
  type AssetVector,
  type EngagementAction,
  type EngagementEvent,
  type Region,
  type UserTaste,
} from "@tastegraph/sdk";
import { getEndpoint, fetchServerRegions, getApiKey } from "./api";

const ENDPOINT = getEndpoint();

const STORAGE_KEY = "tastegraph_events";

function loadEvents(): EngagementEvent[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as EngagementEvent[]) : [];
  } catch {
    return [];
  }
}

export interface AffinityState {
  events: EngagementEvent[];
  taste: UserTaste;
  regions: Region[];
  themes: string[];
  vectors: Map<string, AssetVector>;
  serverSync: boolean;
  regionSource: "local" | "server";
  track: (assetId: string, action: EngagementAction, dwellMs?: number) => void;
  rank: (candidateIds: string[]) => Array<[string, number]>;
  reset: () => void;
}

/** Local-first affinity state. Recomputes taste/regions/themes on each engagement event.
 * ``bundleRegions`` are the catalog-level regions precomputed by the Python exporter; used as
 * the initial offline regions until the user's own engagement produces local/server regions. */
export function useAffinity(assets: AssetVector[], bundleRegions: Region[] = []): AffinityState {
  const [events, setEvents] = useState<EngagementEvent[]>(() => loadEvents());
  const [serverRegions, setServerRegions] = useState<Region[] | null>(null);

  const vectors = useMemo(() => new Map(assets.map((a) => [a.id, a])), [assets]);

  const sdk = useMemo(
    () => (ENDPOINT ? new TasteGraph({ endpoint: ENDPOINT, apiKey: getApiKey() ?? undefined, flushIntervalMs: 2000 }) : null),
    [],
  );

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
  }, [events]);

  const taste = useMemo(() => buildUserTaste(events, vectors), [events, vectors]);
  const localRegions = useMemo(() => computeRegions(events, vectors), [events, vectors]);
  const themes = useMemo(() => topThemes(events, vectors), [events, vectors]);

  // Server-refine regions (debounced) when connected and the user has engaged.
  useEffect(() => {
    if (!ENDPOINT || events.length === 0) return;
    const engaged = [...new Set(events.map((e) => e.assetId))];
    const t = setTimeout(() => {
      fetchServerRegions(engaged)
        .then(setServerRegions)
        .catch(() => setServerRegions(null));
    }, 600);
    return () => clearTimeout(t);
  }, [events]);

  const regions: Region[] =
    serverRegions && serverRegions.length
      ? serverRegions
      : localRegions.length
        ? localRegions
        : bundleRegions;
  const regionSource: "local" | "server" = serverRegions && serverRegions.length ? "server" : "local";

  const track = useCallback(
    (assetId: string, action: EngagementAction, dwellMs?: number) => {
      setEvents((prev) => [...prev, { assetId, action, dwellMs, ts: Date.now() / 1000 }]);
      // optional server sync for wire-format actions only
      if (sdk && action !== "dwell" && action !== "deep_scroll" && action !== "deep_read") {
        sdk.track(assetId, action);
      }
    },
    [sdk],
  );

  const rank = useCallback(
    (candidateIds: string[]) => rankCandidates(taste, candidateIds, vectors, assets[0]?.id),
    [taste, vectors, assets],
  );

  const reset = useCallback(() => {
    setEvents([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return { events, taste, regions, themes, vectors, serverSync: !!sdk, regionSource, track, rank, reset };
}
