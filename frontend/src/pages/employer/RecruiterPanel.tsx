/**
 * RecruiterPanel - candidate decision panel (Phase 13C).
 * Location: frontend/src/pages/employer/RecruiterPanel.tsx
 *
 * Shows submitted candidates with score + proctoring flags, a detail drawer
 * with the proctoring event timeline, and verdict buttons (advance / schedule /
 * reject) that can fire an auto-email.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { recruiterApi, type CandidatePanelRow } from "../../api/platform";

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

export default function RecruiterPanel() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<CandidatePanelRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<any | null>(null);
  const [working, setWorking] = useState(false);

  const load = () => {
    setLoading(true);
    recruiterApi
      .candidates()
      .then(setRows)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const openDetail = async (attemptId: string) => {
    const d = await recruiterApi.candidateDetail(attemptId);
    setDetail(d);
  };

  const decide = async (attemptId: string, verdict: string) => {
    setWorking(true);
    try {
      await recruiterApi.decision(attemptId, verdict, undefined, verdict !== "schedule_live");
      if (verdict === "schedule_live") {
        navigate("/employer/scheduler", { state: { attemptId } });
        return;
      }
      setDetail(null);
      load();
    } finally {
      setWorking(false);
    }
  };

  const scoreColor = (s: number | null) =>
    s == null ? "text-gray-400" : s >= 4 ? "text-green-600" : s >= 3 ? "text-amber-600" : "text-red-600";

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-6 py-4 flex items-center gap-3">
          <button onClick={() => navigate("/employer")} className="text-gray-500">← Back</button>
          <h1 className="text-lg font-bold text-gray-900">Recruiter Decision Panel</h1>
        </div>
      </header>

      <main className="container mx-auto px-6 py-6 max-w-5xl">
        {loading ? (
          <p className="text-gray-500">Loading…</p>
        ) : rows.length === 0 ? (
          <div className="bg-white rounded-xl shadow p-10 text-center text-gray-500">
            No submitted attempts yet.
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-left">
                <tr>
                  <th className="px-4 py-3">Candidate</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Flags</th>
                  <th className="px-4 py-3">Verdict</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const flagCount = Object.values(r.proctoring_summary || {}).reduce((a, b) => a + b, 0);
                  return (
                    <tr key={r.attempt_id} className="border-t border-gray-100">
                      <td className="px-4 py-3 font-medium text-gray-800">{r.candidate_username}</td>
                      <td className={`px-4 py-3 font-bold ${scoreColor(r.overall_score)}`}>
                        {r.overall_score ?? "—"}/5
                      </td>
                      <td className="px-4 py-3">
                        {flagCount === 0 ? (
                          <span className="text-green-600">Clean</span>
                        ) : (
                          <span className="text-red-600 font-semibold">{flagCount} flag{flagCount > 1 ? "s" : ""}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 capitalize">{r.verdict?.replace("_", " ")}</td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => openDetail(r.attempt_id)} className="text-blue-700 font-semibold">
                          Review →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* Detail drawer */}
      {detail && (
        <div className="fixed inset-0 bg-black/40 flex justify-end z-50" onClick={() => setDetail(null)}>
          <div className="bg-white w-full max-w-md h-full overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">{detail.attempt.candidate_username}</h2>
              <button onClick={() => setDetail(null)} className="text-gray-400">✕</button>
            </div>
            <p className="text-sm text-gray-500 mb-1">{detail.assessment_title}</p>
            <p className="text-3xl font-bold text-blue-600 mb-4">
              {detail.attempt.overall_score ?? "—"}<span className="text-base text-gray-400">/5</span>
            </p>

            <h3 className="font-semibold text-gray-800 mb-2">Per-question</h3>
            <ul className="space-y-1 mb-4 text-sm">
              {(detail.attempt.scoring?.per_question ?? []).map((pq: any, i: number) => (
                <li key={i} className="flex justify-between border-b border-gray-100 py-1">
                  <span className="text-gray-600">{pq.type} ({pq.scoring_mode})</span>
                  <span className="font-semibold">{pq.score}/{pq.max_score}</span>
                </li>
              ))}
            </ul>

            <h3 className="font-semibold text-gray-800 mb-2">Proctoring timeline</h3>
            {detail.events.length === 0 ? (
              <p className="text-sm text-green-600 mb-4">No violations recorded.</p>
            ) : (
              <ul className="space-y-1 mb-4 text-sm">
                {detail.events.map((ev: any) => (
                  <li key={ev.id} className="flex justify-between text-red-600">
                    <span>{FLAG_LABELS[ev.type] || ev.type}</span>
                    <span className="text-gray-400 text-xs">{new Date(ev.at).toLocaleTimeString()}</span>
                  </li>
                ))}
              </ul>
            )}

            <div className="grid grid-cols-3 gap-2 mt-6">
              <button onClick={() => decide(detail.attempt.id, "advance")} disabled={working} className="py-2 bg-green-600 text-white text-sm font-semibold rounded-lg disabled:opacity-50">
                Advance
              </button>
              <button onClick={() => decide(detail.attempt.id, "schedule_live")} disabled={working} className="py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg disabled:opacity-50">
                Schedule
              </button>
              <button onClick={() => decide(detail.attempt.id, "reject")} disabled={working} className="py-2 bg-red-600 text-white text-sm font-semibold rounded-lg disabled:opacity-50">
                Reject
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-2 text-center">Advance/Reject send an auto-email to the candidate.</p>
          </div>
        </div>
      )}
    </div>
  );
}
