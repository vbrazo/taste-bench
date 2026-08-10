/** Shared types for the local affinity engine. */

import type { Action } from "./index";

/** One catalog asset with its precomputed joint-embedding vector (from the Python exporter). */
export interface AssetVector {
  id: string;
  vec: number[];
  tags: string[];
  caption: string;
  type?: string;
  uri?: string;
  mediaUri?: string | null;
  posterUri?: string | null;
}

/** A local engagement event captured in the browser. */
export interface EngagementEvent {
  assetId: string;
  action: EngagementAction;
  dwellMs?: number;
  ts: number; // seconds since epoch
}

/** Actions on the TasteGraph wire format (Python Signal.action). */
export type EngagementAction = Action;

export interface UserTaste {
  vec: number[] | null; // null == cold start (no positive evidence)
  confidence: number;
  nSignals: number;
}

export interface Region {
  id: string;
  label: string;
  memberIds: string[];
  size: number;
  centroid: number[];
}
