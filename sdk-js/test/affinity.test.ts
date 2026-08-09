import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { describe, expect, it } from "vitest";
import { buildUserTaste, effectiveWeight, rankCandidates } from "../src/affinity";
import { computeRegions, topThemes } from "../src/regions";
import type { AssetVector, EngagementEvent } from "../src/types";

const here = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(join(here, "../fixtures/affinity_case.json"), "utf-8"));

function vectorMap(bundle: { assets: AssetVector[] }): Map<string, AssetVector> {
  return new Map(bundle.assets.map((a) => [a.id, a]));
}

function events(raw: Array<{ assetId: string; action: string }>): EngagementEvent[] {
  return raw.map((e) => ({ assetId: e.assetId, action: e.action as any, ts: 0 }));
}

describe("affinity engine — Python parity", () => {
  const vectors = vectorMap(fixture.bundle);
  const evs = events(fixture.events);

  it("reproduces the Python taste confidence and signal count", () => {
    const taste = buildUserTaste(evs, vectors);
    expect(taste.nSignals).toBe(fixture.expected.nSignals);
    expect(taste.confidence).toBeCloseTo(fixture.expected.confidence, 2);
  });

  it("reproduces the Python ranking order and scores", () => {
    const taste = buildUserTaste(evs, vectors);
    const candidateIds = fixture.expected.ranking.map((r: [string, number]) => r[0]);
    const ranked = rankCandidates(taste, candidateIds, vectors);
    const order = ranked.map(([id]) => id);
    expect(order).toEqual(fixture.expected.ranking.map((r: [string, number]) => r[0]));
    ranked.forEach(([, score], i) => {
      expect(score).toBeCloseTo(fixture.expected.ranking[i][1], 2);
    });
  });
});

describe("affinity weights", () => {
  it("dismiss is negative, save strong positive", () => {
    expect(effectiveWeight({ assetId: "a", action: "dismiss", ts: 0 })).toBeLessThan(0);
    expect(effectiveWeight({ assetId: "a", action: "save", ts: 0 })).toBeGreaterThan(0.9);
  });

  it("dwell scales with time", () => {
    const short = effectiveWeight({ assetId: "a", action: "dwell", dwellMs: 500, ts: 0 });
    const long = effectiveWeight({ assetId: "a", action: "dwell", dwellMs: 30000, ts: 0 });
    expect(long).toBeGreaterThan(short);
  });
});

describe("regions & themes", () => {
  const vectors = vectorMap(fixture.bundle);
  const evs = events([
    { assetId: "asset_01", action: "like" },
    { assetId: "asset_09", action: "save" },
    { assetId: "asset_10", action: "like" },
    { assetId: "asset_03", action: "like" },
  ]);

  it("produces named regions covering engaged assets", () => {
    const regions = computeRegions(evs, vectors, 2);
    expect(regions.length).toBeGreaterThan(0);
    const covered = regions.flatMap((r) => r.memberIds);
    expect(covered).toContain("asset_01");
    expect(regions[0].label.length).toBeGreaterThan(0);
  });

  it("lists top themes", () => {
    expect(topThemes(evs, vectors).length).toBeGreaterThan(0);
  });
});
