/**
 * Local affinity engine — a TypeScript port of the Python rules in
 * tastebench/tastegraph/graph/affinity.py and signals/schema.py.
 *
 * A user's taste vector is the signal-weighted mean of the vectors of assets they engaged
 * with; confidence saturates with total positive evidence. Everything is computed in the
 * browser ("LOCAL ONLY"); parity with the Python engine is enforced by a fixture test.
 */

import type { AssetVector, EngagementAction, EngagementEvent, UserTaste } from "./types";

/** Implicit affinity weights. Mirrors Python ACTION_WEIGHTS, plus engagement-derived actions. */
export const ACTION_WEIGHTS: Record<EngagementAction, number> = {
  view: 0.2,
  click: 0.5,
  like: 1.0,
  save: 1.2,
  dismiss: -1.0,
  // engagement-derived (web only)
  dwell: 0.0, // base 0; scaled by dwellMs, see effectiveWeight
  deep_scroll: 0.6,
  deep_read: 0.8,
};

/** Dwell contributes up to ~+0.8, saturating around 30s of attention. */
export function dwellWeight(dwellMs: number): number {
  const seconds = Math.max(0, dwellMs) / 1000;
  return 0.8 * (1 - 1 / (1 + seconds / 8));
}

export function effectiveWeight(event: EngagementEvent): number {
  if (event.action === "dwell") return dwellWeight(event.dwellMs ?? 0);
  return ACTION_WEIGHTS[event.action] ?? 0;
}

/** Sum effective weights per asset (mirrors signals/profiles.weighted_assets). */
export function weightedAssets(events: EngagementEvent[]): Map<string, number> {
  const totals = new Map<string, number>();
  for (const e of events) {
    totals.set(e.assetId, (totals.get(e.assetId) ?? 0) + effectiveWeight(e));
  }
  return totals;
}

export function norm(v: number[]): number {
  return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}

export function unit(v: number[]): number[] {
  const n = norm(v);
  return n ? v.map((x) => x / n) : v;
}

export function cosine(a: number[], b: number[]): number {
  const na = norm(a);
  const nb = norm(b);
  if (!na || !nb) return 0;
  let dot = 0;
  for (let i = 0; i < Math.min(a.length, b.length); i++) dot += a[i] * b[i];
  return dot / (na * nb);
}

/** confidence = 1 - 1/(1+evidence), evidence = sum of positive weights (mirrors _confidence). */
function confidence(weights: number[]): number {
  const evidence = weights.reduce((s, w) => s + Math.max(0, w), 0);
  const c = 1 - 1 / (1 + evidence);
  return Math.round(c * 1000) / 1000;
}

export function buildUserTaste(events: EngagementEvent[], vectors: Map<string, AssetVector>): UserTaste {
  const totals = weightedAssets(events);
  const vecs: number[][] = [];
  const weights: number[] = [];
  for (const [assetId, w] of totals) {
    const av = vectors.get(assetId);
    if (av) {
      vecs.push(av.vec);
      weights.push(w);
    }
  }
  if (vecs.length === 0) return { vec: null, confidence: 0, nSignals: 0 };

  const dim = vecs[0].length;
  const acc = new Array(dim).fill(0);
  let wsum = weights.reduce((s, w) => s + w, 0);
  if (wsum === 0) wsum = 1;
  for (let i = 0; i < vecs.length; i++) {
    for (let d = 0; d < dim; d++) acc[d] += vecs[i][d] * weights[i];
  }
  const taste = unit(acc.map((x) => x / wsum));
  return { vec: taste, confidence: confidence(weights), nSignals: vecs.length };
}

/** Score a subset of assets against the user's taste vector. */
export function scoreIds(userVec: number[], ids: string[], vectors: Map<string, AssetVector>): Map<string, number> {
  const out = new Map<string, number>();
  for (const id of ids) {
    const av = vectors.get(id);
    if (av) out.set(id, cosine(userVec, av.vec));
  }
  return out;
}

/** Rank candidates by affinity (desc). Cold start: rank by similarity to coldStartSeed if given. */
export function rankCandidates(
  taste: UserTaste,
  candidateIds: string[],
  vectors: Map<string, AssetVector>,
  coldStartSeed?: string,
): Array<[string, number]> {
  const present = candidateIds.filter((c) => vectors.has(c));
  let scores: Map<string, number>;
  if (taste.vec) {
    scores = scoreIds(taste.vec, present, vectors);
  } else if (coldStartSeed && vectors.has(coldStartSeed)) {
    scores = scoreIds(vectors.get(coldStartSeed)!.vec, present, vectors);
  } else {
    scores = new Map(present.map((c) => [c, 0]));
  }
  const ranked = [...present].sort((a, b) => (scores.get(b) ?? 0) - (scores.get(a) ?? 0));
  const unknown = candidateIds.filter((c) => !vectors.has(c));
  return [...ranked, ...unknown].map((c) => [c, Math.round((scores.get(c) ?? 0) * 10000) / 10000]);
}
