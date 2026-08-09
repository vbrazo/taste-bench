import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useAffinity } from "./useAffinity";
import type { AssetVector } from "@tastegraph/sdk";

const ASSETS: AssetVector[] = [
  { id: "a1", vec: [1, 0, 0], tags: ["minimal", "sand"], caption: "minimal" },
  { id: "a2", vec: [0.9, 0.1, 0], tags: ["minimal", "luxe"], caption: "luxe" },
  { id: "a3", vec: [0, 1, 0], tags: ["street", "neon"], caption: "street" },
  { id: "a4", vec: [0, 0.9, 0.1], tags: ["street", "bold"], caption: "bold" },
];

beforeEach(() => localStorage.clear());

describe("useAffinity", () => {
  it("builds regions and themes after engagement events", () => {
    const { result } = renderHook(() => useAffinity(ASSETS));
    expect(result.current.regions).toHaveLength(0);

    act(() => result.current.track("a1", "like"));
    act(() => result.current.track("a2", "save"));

    expect(result.current.events).toHaveLength(2);
    expect(result.current.taste.vec).not.toBeNull();
    expect(result.current.regions.length).toBeGreaterThan(0);
    expect(result.current.themes).toContain("Minimal");
  });

  it("ranks on-taste assets above off-taste ones", () => {
    const { result } = renderHook(() => useAffinity(ASSETS));
    act(() => result.current.track("a1", "like"));
    act(() => result.current.track("a2", "save"));

    const ranked = result.current.rank(["a3", "a2", "a4", "a1"]);
    const order = ranked.map(([id]) => id);
    expect(order.indexOf("a2")).toBeLessThan(order.indexOf("a3"));
  });

  it("reset clears history", () => {
    const { result } = renderHook(() => useAffinity(ASSETS));
    act(() => result.current.track("a1", "like"));
    act(() => result.current.reset());
    expect(result.current.events).toHaveLength(0);
    expect(result.current.taste.vec).toBeNull();
  });
});
