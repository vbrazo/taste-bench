/**
 * Lightweight in-browser clustering into "taste regions" + "top themes".
 *
 * Regions come from a tiny k-means over the engaged assets' vectors; each region is named by
 * the two dominant tags of its members (screenshot style: "Hand Gold", "Anime Dark"). Themes
 * are the most frequent tags across engaged assets.
 */

import { cosine, unit, weightedAssets } from "./affinity";
import type { AssetVector, EngagementEvent, Region } from "./types";

function titleCase(tag: string): string {
  return tag
    .replace(/[#_]/g, " ")
    .trim()
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Distinctive-tag label: tf * idf against the whole engaged set (mirrors server clustering). */
const HEX = /^#?[0-9a-f]{6}$/i;

function labelFor(members: AssetVector[], globalDf: Map<string, number>, nDocs: number): string {
  const tf = new Map<string, number>();
  for (const m of members) for (const t of new Set(m.tags)) {
    if (HEX.test(t.trim())) continue;
    tf.set(t, (tf.get(t) ?? 0) + 1);
  }
  const scored: Array<[number, string]> = [];
  for (const [tag, freq] of tf) {
    const idf = Math.log((1 + nDocs) / (1 + (globalDf.get(tag) ?? 0))) + 1;
    scored.push([freq * idf, tag]);
  }
  scored.sort((a, b) => b[0] - a[0]);
  const top = scored.slice(0, 2).map(([, t]) => titleCase(t)).filter(Boolean);
  return top.join(" ") || "Region";
}

function centroid(members: AssetVector[]): number[] {
  const dim = members[0].vec.length;
  const acc = new Array(dim).fill(0);
  for (const m of members) for (let d = 0; d < dim; d++) acc[d] += m.vec[d];
  return unit(acc.map((x) => x / members.length));
}

/** Silhouette-lite k selection over cosine distance: pick k in [2, min(6, n-1)]. */
function chooseK(items: AssetVector[]): number {
  const n = items.length;
  if (n < 3) return 1;
  const dist = (a: number[], b: number[]) => 1 - cosine(a, b);
  let bestK = 2;
  let bestScore = -Infinity;
  for (let k = 2; k <= Math.min(6, n - 1); k++) {
    const asn = kmeansAssign(items, k);
    const groups: number[][] = Array.from({ length: k }, () => []);
    asn.forEach((c, i) => groups[c].push(i));
    if (groups.some((g) => g.length === 0)) continue;
    let total = 0;
    for (let i = 0; i < n; i++) {
      const own = groups[asn[i]].filter((j) => j !== i);
      const a = own.length ? own.reduce((s, j) => s + dist(items[i].vec, items[j].vec), 0) / own.length : 0;
      let b = Infinity;
      groups.forEach((g, c) => {
        if (c === asn[i] || !g.length) return;
        const avg = g.reduce((s, j) => s + dist(items[i].vec, items[j].vec), 0) / g.length;
        b = Math.min(b, avg);
      });
      const s = b === Infinity ? 0 : (b - a) / Math.max(a, b || 1);
      total += s;
    }
    const score = total / n;
    if (score > bestScore) {
      bestScore = score;
      bestK = k;
    }
  }
  return bestK;
}

function kmeansAssign(items: AssetVector[], k: number): number[] {
  let centers = Array.from({ length: k }, (_, i) => items[Math.floor((i * items.length) / k)].vec);
  let assignment = new Array(items.length).fill(0);
  for (let iter = 0; iter < 6; iter++) {
    assignment = items.map((a) => {
      let best = 0;
      let bestSim = -Infinity;
      centers.forEach((c, ci) => {
        const s = cosine(a.vec, c);
        if (s > bestSim) {
          bestSim = s;
          best = ci;
        }
      });
      return best;
    });
    centers = centers.map((c, ci) => {
      const members = items.filter((_, i) => assignment[i] === ci);
      return members.length ? centroid(members) : c;
    });
  }
  return assignment;
}

/** k-means-lite (cosine) with a fixed seed and a few iterations. */
export function computeRegions(
  events: EngagementEvent[],
  vectors: Map<string, AssetVector>,
  k?: number,
): Region[] {
  const engaged = [...weightedAssets(events).keys()]
    .map((id) => vectors.get(id))
    .filter((v): v is AssetVector => !!v);
  if (engaged.length === 0) return [];
  const kk = Math.min(k ?? chooseK(engaged), engaged.length);

  // deterministic seeding: spread picks across the list
  let centers = Array.from({ length: kk }, (_, i) => engaged[Math.floor((i * engaged.length) / kk)].vec);

  let assignment = new Array(engaged.length).fill(0);
  for (let iter = 0; iter < 8; iter++) {
    // assign
    assignment = engaged.map((a) => {
      let best = 0;
      let bestSim = -Infinity;
      centers.forEach((c, ci) => {
        const s = cosine(a.vec, c);
        if (s > bestSim) {
          bestSim = s;
          best = ci;
        }
      });
      return best;
    });
    // update
    const next: number[][] = [];
    for (let ci = 0; ci < kk; ci++) {
      const members = engaged.filter((_, i) => assignment[i] === ci);
      next.push(members.length ? centroid(members) : centers[ci]);
    }
    centers = next;
  }

  const globalDf = new Map<string, number>();
  for (const a of engaged) for (const t of new Set(a.tags)) globalDf.set(t, (globalDf.get(t) ?? 0) + 1);

  const regions: Region[] = [];
  for (let ci = 0; ci < kk; ci++) {
    const members = engaged.filter((_, i) => assignment[i] === ci);
    if (!members.length) continue;
    regions.push({
      id: `region_${ci}`,
      label: labelFor(members, globalDf, engaged.length),
      memberIds: members.map((m) => m.id),
      size: members.length,
      centroid: centers[ci],
    });
  }
  return regions.sort((a, b) => b.size - a.size);
}

/** Most frequent tags across engaged assets (the TOP THEMES list). */
export function topThemes(events: EngagementEvent[], vectors: Map<string, AssetVector>, n = 6): string[] {
  const freq = new Map<string, number>();
  for (const id of weightedAssets(events).keys()) {
    const av = vectors.get(id);
    if (!av) continue;
    for (const t of av.tags) freq.set(t, (freq.get(t) ?? 0) + 1);
  }
  return [...freq.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([t]) => titleCase(t));
}
