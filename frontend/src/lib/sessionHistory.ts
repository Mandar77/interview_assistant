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
 */

export interface StoredSession {
  session_id: string;
  date: string;
  interview_type: string;
  overall_score: number;
  rubric_scores: Record<string, number>;
  questions_count: number;
}

const KEY_PREFIX = "ia_sessions_v2:"; // v2 — namespaced + sanitized
const GUEST = "guest";
const LEGACY_KEY = "interview_sessions"; // pre-v2 global, unscoped bucket

// Drop the legacy unscoped store once. It was shown to everyone (incl. anon /
// pre-login) and could contain malformed records — superseded by per-user v2.
try {
  if (localStorage.getItem(LEGACY_KEY) !== null) localStorage.removeItem(LEGACY_KEY);
} catch {
  /* ignore */
}

function keyFor(userId?: string | null): string {
  return KEY_PREFIX + (userId || GUEST);
}

/** Coerce anything stored into a safe, fully-populated record. */
function sanitize(raw: any): StoredSession | null {
  if (!raw || typeof raw !== "object") return null;
  const score = Number(raw.overall_score);
  const rubric: Record<string, number> = {};
  if (raw.rubric_scores && typeof raw.rubric_scores === "object") {
    for (const [k, v] of Object.entries(raw.rubric_scores)) {
      const n = Number(v);
      if (Number.isFinite(n)) rubric[k] = n;
    }
  }
  return {
    session_id: String(raw.session_id || ""),
    date: String(raw.date || new Date(0).toISOString()),
    interview_type: String(raw.interview_type || "technical"),
    overall_score: Number.isFinite(score) ? score : 0,
    rubric_scores: rubric,
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
