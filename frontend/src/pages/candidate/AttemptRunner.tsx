/**
 * AttemptRunner - secure proctored assessment-taking environment (Phase 11).
 * Location: frontend/src/pages/candidate/AttemptRunner.tsx
 *
 * Launches an assigned assessment, applies the proctoring guardrails declared
 * by the assessment's permissions (fullscreen, tab-switch, copy/paste block,
 * watermark), collects answers (MCQ + text/video transcript), and submits for
 * scoring. Designed to degrade gracefully: missing permissions simply skip the
 * corresponding guardrail.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { workspaceApi, type Assessment } from "../../api/platform";
import { useAuth } from "../../auth/AuthContext";
import { useProctoring } from "../../hooks/useProctoring";

export default function AttemptRunner() {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [started, setStarted] = useState(false);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<number | null>(null);
  const [error, setError] = useState("");

  const permissions = assessment?.permissions ?? null;
  const { fullscreen, violations, enterFullscreen } = useProctoring(
    attemptId,
    permissions,
    started
  );

  // Flatten questions for a simple single-page runner.
  const questions = useMemo(
    () => (assessment?.sections ?? []).flatMap((s) => s.questions),
    [assessment]
  );

  const begin = useCallback(async () => {
    if (!assignmentId) return;
    try {
      const res = await workspaceApi.startAttempt(assignmentId);
      setAttemptId(res.attempt_id);
      setAssessment(res.assessment);
      setStarted(true);
      if (res.assessment.permissions?.force_fullscreen) {
        await enterFullscreen();
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not start the assessment");
    }
  }, [assignmentId, enterFullscreen]);

  // Best-effort: exit fullscreen on unmount.
  useEffect(() => {
    return () => {
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    };
  }, []);

  const setAnswer = (qid: string, value: any) =>
    setAnswers((prev) => ({ ...prev, [qid]: value }));

  const submit = async () => {
    if (!attemptId) return;
    setSubmitting(true);
    try {
      const payload = questions.map((q) => {
        if (q.type === "mcq") {
          return {
            question_id: q.id,
            type: "mcq",
            selected_option_ids: answers[q.id] ? [answers[q.id]] : [],
          };
        }
        if (q.type === "coding") {
          return {
            question_id: q.id,
            type: "coding",
            code: answers[q.id] || "",
            language: "python",
          };
        }
        return {
          question_id: q.id,
          type: q.type,
          transcript: answers[q.id] || "",
        };
      });
      const res = await workspaceApi.submit(attemptId, payload);
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
      setResult(res.overall_score);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  // ---- Pre-start gate ----
  if (!started) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white px-4">
        <div className="bg-slate-800 rounded-2xl p-8 max-w-md text-center">
          <h1 className="text-2xl font-bold mb-3">Secure Assessment</h1>
          <p className="text-sm text-slate-300 mb-6">
            This assessment is proctored. Once you begin, tab switching, leaving fullscreen, and
            copy/paste may be monitored and reported to the employer.
          </p>
          {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
          <button onClick={begin} className="w-full py-3 bg-blue-600 rounded-lg font-semibold">
            Begin assessment
          </button>
          <button onClick={() => navigate("/workspace")} className="mt-3 text-sm text-slate-400">
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // ---- Result ----
  if (result !== null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Submitted ✓</h1>
          <p className="text-gray-500 mb-4">Your responses have been sent to the employer.</p>
          <p className="text-5xl font-bold text-blue-600 mb-6">
            {result}<span className="text-xl text-gray-400">/5</span>
          </p>
          <button onClick={() => navigate("/workspace")} className="px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-lg">
            Back to workspace
          </button>
        </div>
      </div>
    );
  }

  // ---- Active proctored runner ----
  return (
    <div className="min-h-screen bg-slate-100 relative select-none">
      {/* Watermark overlay */}
      {permissions?.watermark && (
        <div className="pointer-events-none fixed inset-0 z-40 overflow-hidden opacity-[0.06]">
          <div className="grid grid-cols-3 gap-20 rotate-[-30deg] scale-150">
            {Array.from({ length: 30 }).map((_, i) => (
              <span key={i} className="text-lg font-bold text-black whitespace-nowrap">
                {user?.username} · {new Date().toLocaleDateString()}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Proctoring status bar */}
      <header className="sticky top-0 z-50 bg-slate-900 text-white px-6 py-3 flex items-center justify-between">
        <h1 className="font-semibold">{assessment?.title}</h1>
        <div className="flex items-center gap-4 text-xs">
          {permissions?.force_fullscreen && (
            <span className={fullscreen ? "text-green-400" : "text-red-400"}>
              {fullscreen ? "● Fullscreen" : "○ Not fullscreen"}
            </span>
          )}
          {violations > 0 && <span className="text-amber-400">{violations} flag(s) logged</span>}
        </div>
      </header>

      {/* Fullscreen re-entry nudge */}
      {permissions?.force_fullscreen && !fullscreen && (
        <div className="bg-red-600 text-white text-center py-2 text-sm">
          You left fullscreen — this was recorded.{" "}
          <button onClick={enterFullscreen} className="underline font-semibold">
            Re-enter fullscreen
          </button>
        </div>
      )}

      <main className="container mx-auto px-6 py-8 max-w-3xl relative z-30">
        <div className="space-y-6">
          {questions.map((q, idx) => (
            <div key={q.id} className="bg-white rounded-xl shadow p-6">
              <div className="flex items-center gap-2 mb-3">
                <span className="px-2 py-0.5 rounded text-xs bg-indigo-100 text-indigo-700 font-semibold uppercase">
                  {q.type}
                </span>
                <span className="text-xs text-gray-400">Question {idx + 1}</span>
              </div>
              <p className="text-gray-900 font-medium mb-4 whitespace-pre-wrap">{q.prompt}</p>

              {q.type === "mcq" && q.options ? (
                <div className="space-y-2">
                  {q.options.map((o) => (
                    <label
                      key={o.id}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer ${
                        answers[q.id] === o.id ? "border-blue-500 bg-blue-50" : "border-gray-200"
                      }`}
                    >
                      <input
                        type="radio"
                        name={q.id}
                        checked={answers[q.id] === o.id}
                        onChange={() => setAnswer(q.id, o.id)}
                      />
                      <span className="text-sm text-gray-800">{o.text}</span>
                    </label>
                  ))}
                </div>
              ) : q.type === "coding" ? (
                <textarea
                  value={answers[q.id] || ""}
                  onChange={(e) => setAnswer(q.id, e.target.value)}
                  placeholder="Write your solution…"
                  rows={8}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                />
              ) : (
                <textarea
                  value={answers[q.id] || ""}
                  onChange={(e) => setAnswer(q.id, e.target.value)}
                  placeholder="Type your answer (transcript)…"
                  rows={5}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                />
              )}
            </div>
          ))}

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <button
            onClick={submit}
            disabled={submitting}
            className="w-full py-3 bg-green-600 text-white font-semibold rounded-xl disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Submit assessment"}
          </button>
        </div>
      </main>
    </div>
  );
}
