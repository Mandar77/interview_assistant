/**
 * RecruiterPanel — candidate decision panel.
 * Location: frontend/src/pages/employer/RecruiterPanel.tsx
 *
 * A scannable candidate table (score + proctoring flags), with a side drawer
 * for per-question scoring, the proctoring timeline, and verdict actions.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, ShieldAlert, Users } from "lucide-react";
import { recruiterApi, type CandidatePanelRow } from "../../api/platform";
import AppShell from "../../ui/AppShell";
import { Badge, Button, EmptyState, Skeleton } from "../../ui";
import { EMPLOYER_NAV } from "./nav";
import { cn } from "../../lib/utils";

const FLAG_LABELS: Record<string, string> = {
  tab_switch: "Tab switch",
  fullscreen_exit: "Fullscreen exit",
  face_lost: "Face lost",
  multi_face_detected: "Multiple faces",
  mic_muted: "Mic muted",
  permission_revoked: "Permission revoked",
  copy_blocked: "Copy blocked",
  paste_blocked: "Paste blocked",
};

const scoreColor = (s: number | null) =>
  s == null ? "text-[var(--text-muted)]" : s >= 4 ? "text-[var(--success)]" : s >= 3 ? "text-[var(--warning)]" : "text-[var(--error)]";

export default function RecruiterPanel() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<CandidatePanelRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<any | null>(null);
  const [working, setWorking] = useState(false);

  const load = () => {
    setLoading(true);
    recruiterApi.candidates().then(setRows).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openDetail = async (attemptId: string) => setDetail(await recruiterApi.candidateDetail(attemptId));

  const decide = async (attemptId: string, verdict: string) => {
    setWorking(true);
    try {
      await recruiterApi.decision(attemptId, verdict, undefined, verdict !== "schedule_live");
      if (verdict === "schedule_live") return navigate("/employer/scheduler", { state: { attemptId } });
      setDetail(null);
      load();
    } finally {
      setWorking(false);
    }
  };

  return (
    <AppShell nav={EMPLOYER_NAV} title="Recruiter Panel">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight text-[var(--text)]">Candidates</h1>
      <p className="mb-6 text-sm text-[var(--text-muted)]">
        Review submitted attempts, inspect proctoring flags, and make a decision.
      </p>

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-14 w-full" />)}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<Users size={22} />}
          title="No submissions yet"
          description="When candidates complete an assigned assessment, they'll appear here for review."
        />
      ) : (
        <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--text-muted)]">
                <th className="px-5 py-3 font-medium">Candidate</th>
                <th className="px-5 py-3 font-medium">Score</th>
                <th className="px-5 py-3 font-medium">Integrity</th>
                <th className="px-5 py-3 font-medium">Verdict</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {rows.map((r) => {
                const flags = Object.values(r.proctoring_summary || {}).reduce((a, b) => a + b, 0);
                return (
                  <tr key={r.attempt_id} className="transition-colors hover:bg-[var(--surface-2)]">
                    <td className="px-5 py-3.5 font-medium text-[var(--text)]">{r.candidate_username}</td>
                    <td className={cn("px-5 py-3.5 font-mono font-semibold", scoreColor(r.overall_score))}>
                      {r.overall_score ?? "—"}<span className="text-[var(--text-muted)]">/5</span>
                    </td>
                    <td className="px-5 py-3.5">
                      {flags === 0 ? (
                        <span className="inline-flex items-center gap-1.5 text-[var(--success)]">
                          <CheckCircle2 size={14} /> Clean
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-[var(--error)]">
                          <ShieldAlert size={14} /> {flags} flag{flags > 1 ? "s" : ""}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 capitalize text-[var(--text-secondary)]">
                      {r.verdict?.replace("_", " ")}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Button variant="ghost" size="sm" onClick={() => openDetail(r.attempt_id)}>
                        Review
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail drawer */}
      {detail && (
        <div className="fixed inset-0 z-50 flex justify-end" style={{ background: "var(--overlay)" }} onClick={() => setDetail(null)}>
          <div
            className="h-full w-full max-w-md animate-slide-up overflow-y-auto border-l border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-lg)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[var(--text)]">{detail.attempt.candidate_username}</h2>
                <p className="text-sm text-[var(--text-muted)]">{detail.assessment_title}</p>
              </div>
              <button onClick={() => setDetail(null)} className="rounded-[var(--radius-xs)] p-1 text-[var(--text-muted)] hover:bg-[var(--surface-3)] hover:text-[var(--text)]">
                ✕
              </button>
            </div>

            <div className="mb-5 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Overall score</p>
              <p className={cn("mt-0.5 font-mono text-3xl font-semibold", scoreColor(detail.attempt.overall_score))}>
                {detail.attempt.overall_score ?? "—"}<span className="text-lg text-[var(--text-muted)]">/5</span>
              </p>
            </div>

            <h3 className="mb-2 text-sm font-semibold text-[var(--text-secondary)]">Per-question</h3>
            <ul className="mb-5 space-y-1">
              {(detail.attempt.scoring?.per_question ?? []).map((pq: any, i: number) => (
                <li key={i} className="flex items-center justify-between border-b border-[var(--border)] py-1.5 text-sm">
                  <span className="text-[var(--text-secondary)]">{pq.type} · {pq.scoring_mode}</span>
                  <span className="font-mono font-medium text-[var(--text)]">{pq.score}/{pq.max_score}</span>
                </li>
              ))}
            </ul>

            <h3 className="mb-2 text-sm font-semibold text-[var(--text-secondary)]">Proctoring timeline</h3>
            {detail.events.length === 0 ? (
              <p className="mb-5 inline-flex items-center gap-1.5 text-sm text-[var(--success)]">
                <CheckCircle2 size={14} /> No violations recorded
              </p>
            ) : (
              <ul className="mb-5 space-y-1">
                {detail.events.map((ev: any) => (
                  <li key={ev.id} className="flex items-center justify-between text-sm text-[var(--error)]">
                    <span>{FLAG_LABELS[ev.type] || ev.type}</span>
                    <span className="text-xs text-[var(--text-muted)]">{new Date(ev.at).toLocaleTimeString()}</span>
                  </li>
                ))}
              </ul>
            )}

            <div className="grid grid-cols-3 gap-2 pt-2">
              <Button size="sm" onClick={() => decide(detail.attempt.id, "advance")} loading={working}>Advance</Button>
              <Button size="sm" variant="secondary" onClick={() => decide(detail.attempt.id, "schedule_live")} loading={working}>Schedule</Button>
              <Button size="sm" variant="danger" onClick={() => decide(detail.attempt.id, "reject")} loading={working}>Reject</Button>
            </div>
            <p className="mt-2 text-center text-xs text-[var(--text-muted)]">Advance / Reject email the candidate automatically.</p>
          </div>
        </div>
      )}
    </AppShell>
  );
}
