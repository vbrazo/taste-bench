import type { Region } from "@tastegraph/sdk";

const KEY_STORAGE = "tastegraph_api_key";
const ENDPOINT_STORAGE = "tastegraph_endpoint";
const ENV_ENDPOINT = import.meta.env.VITE_TASTEGRAPH_ENDPOINT as string | undefined;

export function getEndpoint(): string {
  try {
    return localStorage.getItem(ENDPOINT_STORAGE) || ENV_ENDPOINT || "";
  } catch {
    return ENV_ENDPOINT || "";
  }
}
export function setEndpoint(url: string): void {
  localStorage.setItem(ENDPOINT_STORAGE, url.replace(/\/$/, ""));
}
export function getApiKey(): string | null {
  try {
    return localStorage.getItem(KEY_STORAGE);
  } catch {
    return null;
  }
}
export function setApiKey(key: string): void {
  localStorage.setItem(KEY_STORAGE, key);
}
export function clearApiKey(): void {
  localStorage.removeItem(KEY_STORAGE);
}

/** Fetch against the configured endpoint with the stored API key. Throws on non-2xx. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const endpoint = getEndpoint();
  if (!endpoint) throw new Error("No endpoint configured");
  const headers = new Headers(init.headers);
  const key = getApiKey();
  if (key) headers.set("X-API-Key", key);
  headers.set("Content-Type", "application/json");
  const res = await fetch(`${endpoint}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res;
}

async function json(path: string, init?: RequestInit) {
  return (await apiFetch(path, init)).json();
}
const post = (path: string, body: unknown) => json(path, { method: "POST", body: JSON.stringify(body) });

/** Validate an endpoint + key. Returns tenant metrics on success; throws with .status on 401. */
export async function checkAuth(endpoint: string, key: string): Promise<{ ok: boolean }> {
  const res = await fetch(`${endpoint.replace(/\/$/, "")}/metrics`, {
    headers: key ? { "X-API-Key": key } : {},
  });
  if (res.status === 401) {
    const err = new Error("Invalid API key") as Error & { status?: number };
    err.status = 401;
    throw err;
  }
  if (!res.ok) throw new Error(`Server responded ${res.status}`);
  return { ok: true };
}

// ---- /v1 client (server-backed playground) --------------------------------

export const v1 = {
  health: () => json("/health"),
  metrics: () => json("/metrics"),
  createEntity: (id: string, type: string, content?: string, metadata: Record<string, unknown> = {}) =>
    post("/v1/entity", { id, type, content, metadata }),
  listEntities: (type?: string) => json(`/v1/entities${type ? `?type=${encodeURIComponent(type)}` : ""}`),
  link: (userId: string, targetId: string, action = "like") =>
    post(`/v1/entity/${encodeURIComponent(userId)}/link`, { target_id: targetId, action }),
  search: (userId: string, k = 8) => post("/v1/search", { user_id: userId, k }),
  rerank: (userId: string, candidates: string[]) => post("/v1/rerank", { user_id: userId, candidates }),
  ask: (userId: string, question: string) => post("/v1/ask", { user_id: userId, question }),
  explain: (userId: string) => post("/v1/explain", { user_id: userId, candidates: [] }),
  clusters: () => json("/v1/clusters"),
  brandIngest: (id: string, references: { id?: string; content: string }[], type = "brand", label?: string) =>
    post("/v1/brand/ingest", { id, type, label, references }),
  enhance: (subjectId: string, prompt: string) => post("/v1/enhance", { subject_id: subjectId, prompt }),
  judge: (subjectId: string, candidates: string[]) => post("/v1/judge", { subject_id: subjectId, candidates }),
};

// ---- helpers used by the local heatmap ------------------------------------

export async function fetchServerRegions(assetIds: string[]): Promise<Region[]> {
  const res = await apiFetch("/regions", { method: "POST", body: JSON.stringify({ asset_ids: assetIds }) });
  const data = await res.json();
  return (data.regions as Array<{ id: string; label: string; memberIds: string[]; centroid: number[] }>).map((r) => ({
    id: r.id,
    label: r.label,
    memberIds: r.memberIds,
    size: r.memberIds.length,
    centroid: r.centroid,
  }));
}

export async function fetchExplain(userId: string): Promise<string> {
  const res = await apiFetch(`/explain/${encodeURIComponent(userId)}`);
  const data = await res.json();
  return data.explanation as string;
}
