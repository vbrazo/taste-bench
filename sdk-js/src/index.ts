/**
 * @tastegraph/sdk — capture behavioral signals and send them to the taste graph.
 *
 * The emitted payload is byte-compatible with the Python `Signal` model
 * (tastebench/tastegraph/signals/schema.py). Keep the two in sync; the Python-side
 * contract test (tests/test_sdk_contract.py) validates the fixture in fixtures/signal.json.
 */

export type Action =
  | "view"
  | "click"
  | "like"
  | "save"
  | "dismiss"
  | "dwell"
  | "deep_scroll"
  | "deep_read";

export interface Signal {
  user_id: string;
  asset_id: string;
  action: Action;
  weight?: number | null;
  timestamp: number; // seconds since epoch (matches Python time.time())
  session_id?: string | null;
  dwell_ms?: number | null;
}

export interface TasteGraphOptions {
  endpoint: string; // base URL of the TasteGraph API
  apiKey?: string; // sent as X-API-Key
  userId?: string; // anonymous id generated + persisted if omitted
  sessionId?: string;
  flushIntervalMs?: number; // batch flush cadence (default 3000)
  batchSize?: number; // flush when queue reaches this size (default 20)
}

const STORAGE_KEY = "tastegraph_uid";

function nowSeconds(): number {
  return Date.now() / 1000;
}

function hasLocalStorage(): boolean {
  try {
    return typeof localStorage !== "undefined";
  } catch {
    return false;
  }
}

function genId(): string {
  const rand = Math.random().toString(36).slice(2);
  return `anon_${Date.now().toString(36)}_${rand}`;
}

function resolveUserId(explicit?: string): string {
  if (explicit) return explicit;
  if (hasLocalStorage()) {
    const existing = localStorage.getItem(STORAGE_KEY);
    if (existing) return existing;
    const fresh = genId();
    localStorage.setItem(STORAGE_KEY, fresh);
    return fresh;
  }
  return genId();
}

export class TasteGraph {
  private endpoint: string;
  private apiKey?: string;
  readonly userId: string;
  private sessionId?: string;
  private queue: Signal[] = [];
  private batchSize: number;
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(opts: TasteGraphOptions) {
    this.endpoint = opts.endpoint.replace(/\/$/, "");
    this.apiKey = opts.apiKey;
    this.userId = resolveUserId(opts.userId);
    this.sessionId = opts.sessionId;
    this.batchSize = opts.batchSize ?? 20;
    const interval = opts.flushIntervalMs ?? 3000;
    if (typeof setInterval !== "undefined" && interval > 0) {
      this.timer = setInterval(() => void this.flush(), interval);
    }
  }

  /** Build a Signal for the current user without sending it (used by track + tests). */
  buildSignal(
    assetId: string,
    action: Action,
    sessionId?: string,
    opts?: { dwellMs?: number; weight?: number | null },
  ): Signal {
    return {
      user_id: this.userId,
      asset_id: assetId,
      action,
      timestamp: nowSeconds(),
      session_id: sessionId ?? this.sessionId ?? null,
      weight: opts?.weight ?? null,
      dwell_ms: opts?.dwellMs ?? null,
    };
  }

  track(
    assetId: string,
    action: Action,
    opts?: { sessionId?: string; dwellMs?: number; weight?: number | null },
  ): void {
    this.queue.push(this.buildSignal(assetId, action, opts?.sessionId, opts));
    if (this.queue.length >= this.batchSize) void this.flush();
  }

  view(assetId: string): void { this.track(assetId, "view"); }
  click(assetId: string): void { this.track(assetId, "click"); }
  like(assetId: string): void { this.track(assetId, "like"); }
  save(assetId: string): void { this.track(assetId, "save"); }
  dismiss(assetId: string): void { this.track(assetId, "dismiss"); }

  /** Send queued signals to POST {endpoint}/track. Uses fetch; sendBeacon as fallback. */
  async flush(): Promise<void> {
    if (this.queue.length === 0) return;
    const batch = this.queue.splice(0, this.queue.length);
    const url = `${this.endpoint}/track`;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) headers["X-API-Key"] = this.apiKey;

    for (const signal of batch) {
      try {
        if (typeof fetch !== "undefined") {
          await fetch(url, { method: "POST", headers, body: JSON.stringify(signal), keepalive: true });
        } else if (typeof navigator !== "undefined" && navigator.sendBeacon) {
          navigator.sendBeacon(url, JSON.stringify(signal));
        }
      } catch {
        this.queue.unshift(signal); // requeue on failure
      }
    }
  }

  dispose(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }
}

export default TasteGraph;

// Local affinity engine (browser-side "LOCAL ONLY" mode).
export * from "./types";
export * from "./affinity";
export * from "./regions";
