/**
 * sessionHistory — per-user local storage of mock-interview results.
 * Location: frontend/src/lib/sessionHistory.ts
 *
 * Mock interviews can be run anonymously OR while logged in. History is scoped
 * by identity so one person's practice sessions never show up for another user
 * (or for an anonymous visitor). Logged-in users key by user id; anonymous
 * practice is kept in a separate "guest" bucket that is NOT shown on the
 * authenticated progress views.
 *
 * Stored records are sanitized on read so a malformed/legacy entry can never
 * crash a render (the previous `toFixed` of null bug).
 *
 * v3 stores one score per evaluation engine on the 0-100 scale and no combined
 * score. v2 records held a single 0-5 `overall_score`; those cannot be migrated
 * (the axes were already blended away and the scale differs), so the v2 bucket
 * is dropped rather than redrawn as near-zero on a 0-100 chart.
 */

/** Scores keyed by engine id: technical, language, speech_delivery, … */
export type EngineScores = Record<string, number | null>;

export interface StoredSession {
  session_id: string;
  date: string;
  interview_type: string;
  /** 0-100 per engine. `null` means that engine was not assessed. */
  engine_scores: EngineScores;
  questions_count: number;
}

const KEY_PREFIX = "ia_sessions_v3:"; // v3 — per-engine, 0-100, no combined score
const GUEST = "guest";
const LEGACY_KEYS = [
  "interview_sessions", // pre-v2 global, unscoped bucket
];
const LEGACY_PREFIX_V2 = "ia_sessions_v2:";

// Drop superseded stores once.
// - The pre-v2 global bucket was shown to everyone (incl. anon/pre-login).
// - v2 held blended 0-5 scores that have no meaning under the per-engine
//   0-100 model; keeping them would misrepresent past sessions.
try {
  for (const key of LEGACY_KEYS) {
    if (localStorage.getItem(key) !== null) localStorage.removeItem(key);
  }
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const key = localStorage.key(i);
    if (key && key.startsWith(LEGACY_PREFIX_V2)) localStorage.removeItem(key);
  }
} catch {
  /* ignore */
}

function keyFor(userId?: string | null): string {
  return KEY_PREFIX + (userId || GUEST);
}

/** Coerce anything stored into a safe, fully-populated record. */
function sanitize(raw: any): StoredSession | null {
  if (!raw || typeof raw !== "object") return null;
  const engines: EngineScores = {};
  if (raw.engine_scores && typeof raw.engine_scores === "object") {
    for (const [k, v] of Object.entries(raw.engine_scores)) {
      if (v === null) {
        engines[k] = null;
        continue;
      }
      const n = Number(v);
      // Clamp rather than drop: a stray out-of-range value should not make the
      // whole session unreadable.
      if (Number.isFinite(n)) engines[k] = Math.max(0, Math.min(100, n));
    }
  }
  return {
    session_id: String(raw.session_id || ""),
    date: String(raw.date || new Date(0).toISOString()),
    interview_type: String(raw.interview_type || "technical"),
    engine_scores: engines,
    questions_count: Number.isFinite(Number(raw.questions_count)) ? Number(raw.questions_count) : 0,
  };
}

export function getSessions(userId?: string | null): StoredSession[] {
  try {
    const raw = JSON.parse(localStorage.getItem(keyFor(userId)) || "[]");
    if (!Array.isArray(raw)) return [];
    return raw.map(sanitize).filter((s): s is StoredSession => s !== null && s.session_id !== "");
  } catch {
    return [];
  }
}

export function saveSession(userId: string | null | undefined, session: StoredSession) {
  const clean = sanitize(session);
  if (!clean) return;
  const sessions = getSessions(userId);
  if (!sessions.find((s) => s.session_id === clean.session_id)) {
    sessions.push(clean);
    localStorage.setItem(keyFor(userId), JSON.stringify(sessions.slice(-50)));
  }
}

export function sessionCount(userId?: string | null): number {
  return getSessions(userId).length;
}

/** Scores for one engine across sessions, oldest first, skipping unassessed. */
export function engineTrend(sessions: StoredSession[], engine: string): number[] {
  return sessions
    .map((s) => s.engine_scores[engine])
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
}
