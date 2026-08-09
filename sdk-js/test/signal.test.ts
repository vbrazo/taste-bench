import { describe, expect, it, vi } from "vitest";
import { TasteGraph } from "../src/index";

describe("TasteGraph SDK", () => {
  it("builds a Signal matching the wire format", () => {
    const tg = new TasteGraph({ endpoint: "http://x", userId: "u1", flushIntervalMs: 0 });
    const sig = tg.buildSignal("asset_01", "like", "s1");
    expect(sig.user_id).toBe("u1");
    expect(sig.asset_id).toBe("asset_01");
    expect(sig.action).toBe("like");
    expect(sig.session_id).toBe("s1");
    expect(typeof sig.timestamp).toBe("number");
    tg.dispose();
  });

  it("POSTs the signal JSON to /track with the api key header", async () => {
    const calls: any[] = [];
    (globalThis as any).fetch = vi.fn(async (url: string, init: any) => {
      calls.push({ url, init });
      return { ok: true } as any;
    });
    const tg = new TasteGraph({ endpoint: "http://api/", apiKey: "key_a", userId: "u1", flushIntervalMs: 0 });
    tg.like("asset_03");
    await tg.flush();

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe("http://api/track");
    expect(calls[0].init.headers["X-API-Key"]).toBe("key_a");
    const body = JSON.parse(calls[0].init.body);
    expect(body).toMatchObject({ user_id: "u1", asset_id: "asset_03", action: "like" });
    tg.dispose();
  });

  it("generates an anonymous user id when none supplied", () => {
    const tg = new TasteGraph({ endpoint: "http://x", flushIntervalMs: 0 });
    expect(tg.userId).toMatch(/^anon_/);
    tg.dispose();
  });
});
