/**
 * AttemptRunner — secure proctored assessment-taking environment.
 * Location: frontend/src/pages/candidate/AttemptRunner.tsx
 *
 * Applies proctoring guardrails declared by the assessment (fullscreen,
 * tab-switch, copy/paste block, watermark), collects answers, and submits for
 * scoring. Degrades gracefully when a permission is unset.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CheckCircle2, Maximize2, ShieldCheck } from "lucide-react";
import { workspaceApi, type Assessment } from "../../api/platform";
import { useAuth } from "../../auth/AuthContext";
import { useProctoring } from "../../hooks/useProctoring";
import { Badge, Button, Textarea } from "../../ui";

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
  const { fullscreen, violations, enterFullscreen } = useProctoring(attemptId, permissions, started);

  const questions = useMemo(() => (assessment?.sections ?? []).flatMap((s) => s.questions), [assessment]);

  const begin = useCallback(async () => {
    if (!assignmentId) return;
    try {
      const res = await workspaceApi.startAttempt(assignmentId);
      setAttemptId(res.attempt_id);
      setAssessment(res.assessment);
      setStarted(true);
      if (res.assessment.permissions?.force_fullscreen) await enterFullscreen();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not start the assessment.");
    }
  }, [assignmentId, enterFullscreen]);

  useEffect(() => () => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  }, []);

  const setAnswer = (qid: string, value: any) => setAnswers((prev) => ({ ...prev, [qid]: value }));

  const submit = async () => {
    if (!attemptId) return;
    setSubmitting(true);
    try {
      const payload = questions.map((q) => {
        if (q.type === "mcq")
          return { question_id: q.id, type: "mcq", selected_option_ids: answers[q.id] ? [answers[q.id]] : [] };
        if (q.type === "coding")
          return { question_id: q.id, type: "coding", code: answers[q.id] || "", language: "python" };
        return { question_id: q.id, type: q.type, transcript: answers[q.id] || "" };
      });
      const res = await workspaceApi.submit(attemptId, payload);
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
      setResult(res.overall_score);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  /* ── Pre-start gate ── */
  if (!started) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--background)] px-4">
        <div className="bg-grid pointer-events-none fixed inset-0 opacity-50" />
        <div className="relative w-full max-w-md rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] p-8 text-center shadow-[var(--shadow-lg)] animate-scale-in">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-[var(--radius-md)] bg-[var(--accent-soft)] text-[var(--accent)]">
            <ShieldCheck size={22} />
          </div>
          <h1 className="text-xl font-semibold text-[var(--text)]">Secure assessment</h1>
          <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
            This assessment is proctored. Once you begin, tab switching, leaving fullscreen, and
            copy / paste may be monitored and reported to the employer.
          </p>
          {error && (
            <p className="mt-4 rounded-[var(--radius-sm)] bg-[var(--error-soft)] px-3 py-2 text-sm text-[var(--error)]">
              {error}
            </p>
          )}
          <Button className="mt-6 w-full" size="lg" onClick={begin}>
            Begin assessment
          </Button>
          <button onClick={() => navigate("/workspace")} className="mt-3 text-sm text-[var(--text-muted)] hover:text-[var(--text)]">
            Cancel
          </button>
        </div>
      </div>
    );
  }

  /* ── Result ── */
  if (result !== null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--background)] px-4">
        <div className="w-full max-w-md rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] p-8 text-center shadow-[var(--shadow-lg)] animate-scale-in">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--success-soft)] text-[var(--success)]">
            <CheckCircle2 size={24} />
          </div>
          <h1 className="text-xl font-semibold text-[var(--text)]">Submitted</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Your responses were sent to the employer.</p>
          <p className="mt-1 text-xs text-[var(--text-muted)]">Percentage of available points earned.</p>
          <p className="mt-6 font-mono text-5xl font-semibold text-[var(--accent)]">
            {Math.round(result)}<span className="text-xl text-[var(--text-muted)]">/100</span>
          </p>
          <Button className="mt-8" onClick={() => navigate("/workspace")}>
            Back to workspace
          </Button>
        </div>
      </div>
    );
  }

  /* ── Active runner ── */
  return (
    <div className="relative min-h-screen select-none bg-[var(--background)]">
      {/* Watermark */}
      {permissions?.watermark && (
        <div className="pointer-events-none fixed inset-0 z-30 overflow-hidden opacity-[0.045]">
          <div className="grid -rotate-[24deg] scale-150 grid-cols-3 gap-16">
            {Array.from({ length: 36 }).map((_, i) => (
              <span key={i} className="whitespace-nowrap text-base font-semibold text-[var(--text)]">
                {user?.username} · {new Date().toLocaleDateString()}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Proctoring bar */}
      <header className="sticky top-0 z-50 border-b border-[var(--border)] glass">
        <div className="mx-auto flex h-13 max-w-3xl items-center justify-between px-5 py-2.5">
          <h1 className="truncate text-sm font-semibold text-[var(--text)]">{assessment?.title}</h1>
          <div className="flex items-center gap-3 text-xs">
            {permissions?.force_fullscreen &&
              (fullscreen ? (
                <Badge tone="success" dot>Fullscreen</Badge>
              ) : (
                <Badge tone="error" dot>Not fullscreen</Badge>
              ))}
            {violations > 0 && <Badge tone="warning">{violations} flag{violations > 1 ? "s" : ""}</Badge>}
          </div>
        </div>
      </header>

      {/* Fullscreen nudge */}
      {permissions?.force_fullscreen && !fullscreen && (
        <div className="flex items-center justify-center gap-2 bg-[var(--error)] px-4 py-2 text-sm text-white">
          You left fullscreen — this was recorded.
          <button onClick={enterFullscreen} className="inline-flex items-center gap-1 font-semibold underline">
            <Maximize2 size={13} /> Re-enter
          </button>
        </div>
      )}

      <main className="relative z-40 mx-auto max-w-3xl px-5 py-8">
        <div className="space-y-5">
          {questions.map((q, idx) => (
            <div key={q.id} className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-sm)]">
              <div className="mb-3 flex items-center gap-2">
                <Badge tone="accent">{q.type}</Badge>
                <span className="text-xs text-[var(--text-muted)]">Question {idx + 1} of {questions.length}</span>
              </div>
              <p className="mb-4 whitespace-pre-wrap font-medium text-[var(--text)]">{q.prompt}</p>

              {q.type === "mcq" && q.options ? (
                <div className="space-y-2">
                  {q.options.map((o) => {
                    const selected = answers[q.id] === o.id;
                    return (
                      <label
                        key={o.id}
                        className={`flex cursor-pointer items-center gap-3 rounded-[var(--radius-sm)] border px-4 py-3 text-sm transition-all ${
                          selected
                            ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--text)]"
                            : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-secondary)] hover:border-[var(--border-strong)]"
                        }`}
                      >
                        <input
                          type="radio"
                          name={q.id}
                          checked={selected}
                          onChange={() => setAnswer(q.id, o.id)}
                          className="accent-[var(--accent)]"
                        />
                        {o.text}
                      </label>
                    );
                  })}
                </div>
              ) : (
                <Textarea
                  rows={q.type === "coding" ? 8 : 5}
                  value={answers[q.id] || ""}
                  onChange={(e) => setAnswer(q.id, e.target.value)}
                  placeholder={q.type === "coding" ? "Write your solution…" : "Type your answer…"}
                  className={q.type === "coding" ? "font-mono text-sm" : "text-sm"}
                />
              )}
            </div>
          ))}

          {error && <p className="text-sm text-[var(--error)]">{error}</p>}

          <Button size="lg" className="w-full" onClick={submit} loading={submitting}>
            Submit assessment
          </Button>
        </div>
      </main>
    </div>
  );
}
