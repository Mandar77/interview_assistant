/**
 * Runtime capability discovery.
 * Location: frontend/src/api/config.ts
 *
 * The same frontend build serves both deployment tiers, so it cannot assume
 * which features the backend has. It asks.
 *
 * Concretely: the hosted tier runs without code execution (Judge0 needs
 * privileged Docker, which no free no-card host allows), so OA coding
 * questions must not be offered there — a candidate picking a coding interview
 * that cannot accept a submission is a worse experience than not seeing the
 * option at all.
 */

import { api } from "./client";

export interface RuntimeConfig {
  deployment_tier: "fast" | "owned";
  providers: { llm: string; stt: string; exec: string };
  features: {
    code_execution: boolean;
    oa_questions: boolean;
    websocket_streaming: boolean;
    body_language: boolean;
  };
  notices: Partial<Record<string, string>>;
}

/**
 * Assumed capabilities when /config cannot be reached.
 *
 * Deliberately optimistic on everything except code execution: hiding a
 * feature that exists is recoverable on the next load, whereas offering a
 * coding question that cannot be submitted wastes an entire interview.
 */
export const FALLBACK_CONFIG: RuntimeConfig = {
  deployment_tier: "fast",
  providers: { llm: "unknown", stt: "unknown", exec: "unknown" },
  features: {
    code_execution: false,
    oa_questions: false,
    websocket_streaming: true,
    body_language: true,
  },
  notices: {},
};

let cached: RuntimeConfig | null = null;
let inFlight: Promise<RuntimeConfig> | null = null;

/** Fetch (and cache) the backend's runtime capabilities. Never throws. */
export async function getRuntimeConfig(): Promise<RuntimeConfig> {
  if (cached) return cached;
  if (inFlight) return inFlight;

  inFlight = api
    .get<RuntimeConfig>("/config")
    .then((res) => {
      cached = res.data;
      return cached;
    })
    .catch((err) => {
      console.warn("Could not read backend /config; assuming reduced features.", err);
      cached = FALLBACK_CONFIG;
      return cached;
    })
    .finally(() => {
      inFlight = null;
    });

  return inFlight;
}

/** Drop the cache (used when switching backends during development). */
export function resetRuntimeConfig(): void {
  cached = null;
}
