/**
 * ResultsDashboard — post-interview evaluation report.
 * Location: frontend/src/pages/ResultsDashboard.tsx
 *
 * Shows one independent 0-100 rating per evaluation engine. There is
 * deliberately no combined score: technical correctness is presented on its own
 * so a strong language or delivery result can never read as compensating for a
 * wrong answer.
 */

import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Code2, Lightbulb, Mic, Target } from "lucide-react";
import { api } from "../api/client";
import { Badge, Button, Card } from "../ui";
import { BrandMark } from "../ui/AppShell";
import ThemeToggle from "../theme/ThemeToggle";
import { getScoreLabel, getScoreTone, formatScore } from "../lib/utils";
import { useAuth } from "../auth/AuthContext";
import { saveSession, type EngineScores } from "../lib/sessionHistory";

/** One engine's rating, averaged across the questions that produced it. */
interface EngineSummary {
  engine: string;
  engine_name: string;
  score: number | null;
  critical: boolean;
  description: string;
  questions_scored: number;
  feedback: string[];
  dimensions: Record<string, { name: string; score: number }>;
}

interface CodeEvaluation {
  question_id: string;
  correctness_score: number;
  code_quality_score: number | null;
  complexity_score: number | null;
  test_pass_rate: number;
  time_complexity: string;
  space_complexity: string;
  passed_tests: number;
  total_tests: number;
  feedback: string;
}

interface EvaluationReport {
  engines: EngineSummary[];
  strengths: string[];
  weaknesses: string[];
  improvement_suggestions: string[];
  notes: string[];
  code_evaluations: CodeEvaluation[];
  evaluated_questions: number;
}

/** Averages a list of numbers, or null when there is nothing to average. */
function mean(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export default function ResultsDashboard() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { sessionId, sessionData, questions } = location.state || {};

  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!sessionId || !sessionData) {
      navigate("/");
      return;
    }
    const fetchEvaluation = async () => {
      try {
        if (!sessionData.questions || !Array.isArray(sessionData.questions)) {
          alert("Session data is incomplete");
          navigate("/");
          return;
        }
        const evaluations = await Promise.all(
          sessionData.questions.map(async (q: any, idx: number) => {
            try {
              const questionData = questions[idx];
              const isCodeQuestion = questionData?.interview_type === "oa";
              if (isCodeQuestion && q.code_submissions && q.code_submissions.length > 0) {
                const lastSubmission = q.code_submissions[q.code_submissions.length - 1];
                const codeEvalResponse = await api.post("/code-execution/evaluate", {
                  code: lastSubmission.code,
                  language: lastSubmission.language,
                  problem_description: questionData.question,
                  test_cases:
                    questionData.test_cases?.map((tc: any) => ({
                      input: tc.input,
                      expected_output: tc.expected_output,
                      description: tc.description,
                      is_hidden: tc.is_hidden,
                    })) || [],
                  timeout: 5,
                });
                return { ...codeEvalResponse.data, question_id: q.question_id, is_code_question: true };
              }
              const response = await api.post("/evaluation/evaluate", {
                session_id: sessionId,
                question_id: q.question_id,
                question_text: q.question_text,
                answer_text: q.transcript,
                interview_type: questionData?.interview_type || "technical",
                speech_metrics: q.speech_metrics,
                language_metrics: q.language_metrics,
                body_language_metrics: q.body_language_metrics,
              });
              return { ...response.data, is_code_question: false };
            } catch (error) {
              console.error(`Evaluation failed for question ${idx}:`, error);
              // Record the failure. Do NOT substitute a mid-band score — an
              // unevaluated answer must not look like an average one.
              return {
                engines: [],
                strengths: [],
                weaknesses: [],
                notes: [`Question ${idx + 1} could not be evaluated.`],
                evaluation_available: false,
                is_code_question: false,
              };
            }
          })
        );
        const built = buildReport(evaluations);
        setReport(built);

        const engineScores: EngineScores = {};
        built.engines.forEach((e) => {
          engineScores[e.engine] = e.score;
        });
        // Scope history to the signed-in user (or the anonymous guest bucket).
        saveSession(user?.id, {
          session_id: sessionId,
          date: new Date().toISOString(),
          interview_type: questions?.[0]?.interview_type || "technical",
          engine_scores: engineScores,
          questions_count: questions?.length || 0,
        });
        setSaved(true);
        setLoading(false);
      } catch (error) {
        console.error("Evaluation failed:", error);
        setLoading(false);
      }
    };
    fetchEvaluation();
  }, [sessionId, sessionData, navigate, questions, user?.id]);

  /**
   * Collect per-engine results across questions.
   *
   * Each engine is averaged only over the questions where it was actually
   * assessed, and engines are never averaged with each other.
   */
  const buildReport = (evaluations: any[]): EvaluationReport => {
    const buckets: Record<string, { meta: EngineSummary; values: number[] }> = {};
    const codeEvaluations: CodeEvaluation[] = [];
    const notes: string[] = [];
    let evaluatedQuestions = 0;

    evaluations.forEach((result) => {
      if (result.is_code_question) {
        codeEvaluations.push({
          question_id: result.question_id,
          correctness_score: result.correctness_score,
          code_quality_score: result.code_quality_score ?? null,
          complexity_score: result.complexity_score ?? null,
          test_pass_rate: result.test_pass_rate ?? 0,
          time_complexity: result.time_complexity,
          space_complexity: result.space_complexity,
          passed_tests: result.passed_tests,
          total_tests: result.total_tests,
          feedback: result.feedback,
        });
        evaluatedQuestions += 1;
        return;
      }

      (result.notes || []).forEach((n: string) => notes.push(n));
      const engines = Array.isArray(result.engines) ? result.engines : [];
      if (engines.length > 0) evaluatedQuestions += 1;

      engines.forEach((engine: any) => {
        const id = engine.engine;
        if (!buckets[id]) {
          buckets[id] = {
            meta: {
              engine: id,
              engine_name: engine.engine_name || id,
              score: null,
              critical: Boolean(engine.critical),
              description: engine.description || "",
              questions_scored: 0,
              feedback: [],
              dimensions: {},
            },
            values: [],
          };
        }
        const bucket = buckets[id];
        if (!engine.assessed || engine.score === null || engine.score === undefined) return;

        bucket.values.push(Number(engine.score));
        if (engine.feedback) bucket.meta.feedback.push(engine.feedback);
        (engine.dimensions || []).forEach((d: any) => {
          if (d.score === null || d.score === undefined) return;
          const prev = bucket.meta.dimensions[d.dimension];
          // Running mean per dimension across questions.
          const count = prev ? 1 : 0;
          bucket.meta.dimensions[d.dimension] = {
            name: d.dimension_name || d.dimension,
            score: prev ? (prev.score * count + Number(d.score)) / (count + 1) : Number(d.score),
          };
        });
      });
    });

    const engines = Object.values(buckets).map(({ meta, values }) => ({
      ...meta,
      score: mean(values),
      questions_scored: values.length,
      feedback: [...new Set(meta.feedback)].slice(0, 3),
    }));

    // Critical engine first, then by score ascending so weak axes are visible.
    engines.sort((a, b) => {
      if (a.critical !== b.critical) return a.critical ? -1 : 1;
      return (a.score ?? 101) - (b.score ?? 101);
    });

    const allStrengths: string[] = [];
    const allWeaknesses: string[] = [];
    const allSuggestions: string[] = [];
    evaluations.forEach((e) => {
      if (e.strengths) allStrengths.push(...e.strengths);
      if (e.weaknesses) allWeaknesses.push(...e.weaknesses);
      if (e.improvement_suggestions) allSuggestions.push(...e.improvement_suggestions);
    });

    return {
      engines,
      strengths: [...new Set(allStrengths)].slice(0, 5),
      weaknesses: [...new Set(allWeaknesses)].slice(0, 5),
      improvement_suggestions: [...new Set(allSuggestions)].slice(0, 5),
      notes: [...new Set(notes)],
      code_evaluations: codeEvaluations,
      evaluated_questions: evaluatedQuestions,
    };
  };

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[var(--background)]">
        <div className="h-9 w-9 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
        <div className="text-center">
          <p className="font-medium text-[var(--text)]">Evaluating your performance…</p>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Grading correctness, language, delivery and code separately</p>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const technical = report.engines.find((e) => e.critical) || null;
  const scoredEngines = report.engines.filter((e) => e.score !== null);
  // The report is "empty" when nothing at all was graded — almost always
  // because the local LLM (Ollama) wasn't running during evaluation.
  const evaluationUnavailable =
    scoredEngines.length === 0 && report.code_evaluations.length === 0;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border)] glass print:hidden">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-5">
          <div className="flex items-center gap-2">
            <BrandMark size={22} />
            <span className="text-base font-semibold tracking-tight text-[var(--text)]">Interview Results</span>
            {saved && <Badge tone="success" dot>Saved to progress</Badge>}
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="secondary" size="sm" onClick={() => navigate("/progress")}>Progress</Button>
            <Button size="sm" onClick={() => navigate("/")} leftIcon={<ArrowLeft size={15} />}>New</Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-5 py-8 animate-fade-in">
        {evaluationUnavailable && (
          <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--warning-soft)] px-5 py-4">
            <p className="text-sm font-medium text-[var(--warning)]">AI evaluation was unavailable</p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              We couldn't reach the local evaluation model (Ollama), so no scores were
              generated. Your transcript was still saved. Start Ollama
              (<code className="rounded bg-[var(--surface-3)] px-1 py-0.5 text-xs">ollama serve</code>)
              and run another interview to get a full report.
            </p>
          </div>
        )}

        {report.notes.length > 0 && !evaluationUnavailable && (
          <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-5 py-3">
            {report.notes.map((n, i) => (
              <p key={i} className="text-sm text-[var(--text-secondary)]">{n}</p>
            ))}
          </div>
        )}

        {/* Technical result — the critical axis, shown alone */}
        {technical && (
          <Card elevated className="overflow-hidden">
            <div className="relative px-8 py-9 text-center">
              <div className="bg-grid pointer-events-none absolute inset-0 opacity-40" />
              <div className="relative">
                <Target size={22} className="mx-auto mb-3 text-[var(--accent)]" />
                <p className="text-xs uppercase tracking-wider text-[var(--text-muted)]">
                  {technical.engine_name}
                </p>
                <p className="mt-2 font-mono text-6xl font-semibold" style={{ color: getScoreTone(technical.score) }}>
                  {formatScore(technical.score)}
                  {technical.score !== null && (
                    <span className="text-2xl text-[var(--text-muted)]">/100</span>
                  )}
                </p>
                <p className="mt-1 text-lg font-medium text-[var(--text-secondary)]">
                  {getScoreLabel(technical.score)}
                </p>
                {technical.score !== null && (
                  <div className="mx-auto mt-5 h-2 max-w-md overflow-hidden rounded-full bg-[var(--surface-3)]">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${technical.score}%`, background: getScoreTone(technical.score) }}
                    />
                  </div>
                )}
                <p className="mx-auto mt-4 max-w-lg text-sm text-[var(--text-muted)]">
                  Scored on correctness alone. How clearly or confidently you spoke is rated
                  separately below and does not change this number.
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Every engine, side by side */}
        {report.engines.length > 0 && (
          <div>
            <h2 className="mb-1 text-lg font-semibold text-[var(--text)]">Ratings by area</h2>
            <p className="mb-3 text-sm text-[var(--text-muted)]">
              Each area is scored independently on 0-100. They are never combined into a single number.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              {report.engines.map((engine) => (
                <Card key={engine.engine} className="px-6 py-5">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold text-[var(--text)]">{engine.engine_name}</h3>
                      {engine.critical && <Badge tone="accent">Critical</Badge>}
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-3xl font-semibold" style={{ color: getScoreTone(engine.score) }}>
                        {formatScore(engine.score)}
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">{getScoreLabel(engine.score)}</p>
                    </div>
                  </div>

                  {engine.score !== null ? (
                    <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-[var(--surface-3)]">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${engine.score}%`, background: getScoreTone(engine.score) }}
                      />
                    </div>
                  ) : (
                    <p className="mb-3 text-sm text-[var(--text-muted)]">
                      Not assessed — no data was captured for this area.
                    </p>
                  )}

                  {Object.keys(engine.dimensions).length > 0 && (
                    <div className="space-y-1.5">
                      {Object.entries(engine.dimensions).map(([key, dim]) => (
                        <div key={key} className="flex items-center justify-between text-sm">
                          <span className="text-[var(--text-secondary)]">{dim.name}</span>
                          <span className="font-mono font-medium" style={{ color: getScoreTone(dim.score) }}>
                            {formatScore(dim.score)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {engine.feedback.length > 0 && (
                    <p className="mt-3 rounded-[var(--radius-md)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text-secondary)]">
                      {engine.feedback[0]}
                    </p>
                  )}
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Coding results */}
        {report.code_evaluations.length > 0 && (
          <div>
            <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-[var(--text)]">
              <Code2 size={18} className="text-[var(--accent)]" /> Coding results
            </h2>
            <p className="mb-3 text-sm text-[var(--text-muted)]">
              Correctness comes from the test suite. Quality and complexity are reported next to
              it and never raise it.
            </p>
            <div className="space-y-4">
              {report.code_evaluations.map((c, i) => (
                <Card key={i} className="px-6 py-5">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="font-semibold text-[var(--text)]">Question {i + 1}</h3>
                    <Badge tone={c.passed_tests === c.total_tests ? "success" : "error"}>
                      {c.passed_tests}/{c.total_tests} tests
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      ["Correctness", c.correctness_score],
                      ["Quality", c.code_quality_score],
                      ["Complexity", c.complexity_score],
                    ].map(([label, val]) => (
                      <div key={label as string}>
                        <p className="text-xs text-[var(--text-muted)]">{label}</p>
                        <p className="font-mono text-2xl font-semibold" style={{ color: getScoreTone(val as number | null) }}>
                          {formatScore(val as number | null)}
                          <span className="text-sm text-[var(--text-muted)]">/100</span>
                        </p>
                      </div>
                    ))}
                  </div>
                  {c.feedback && <p className="mt-4 rounded-[var(--radius-md)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-secondary)]">{c.feedback}</p>}
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Speech metrics per question */}
        {sessionData?.questions?.some((q: any) => q.speech_metrics) && (
          <Card className="px-6 py-5">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-[var(--text)]">
              <Mic size={18} className="text-[var(--accent)]" /> Speech metrics
            </h2>
            <div className="space-y-2">
              {sessionData.questions.filter((q: any) => q.speech_metrics).map((q: any, i: number) => (
                <div key={i} className="flex flex-wrap gap-x-8 gap-y-1 rounded-[var(--radius-md)] bg-[var(--surface-2)] px-4 py-3 text-sm">
                  <span className="text-[var(--text-muted)]">Q{i + 1}</span>
                  <span className="text-[var(--text-secondary)]">WPM <b className="font-mono text-[var(--text)]">{q.speech_metrics?.words_per_minute?.toFixed(0)}</b></span>
                  <span className="text-[var(--text-secondary)]">Fillers <b className="font-mono text-[var(--text)]">{q.speech_metrics?.filler_word_percentage?.toFixed(1)}%</b></span>
                  <span className="text-[var(--text-secondary)]">Grammar <b className="font-mono text-[var(--text)]">{formatScore(q.language_metrics?.grammar_score)}/100</b></span>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Strengths / weaknesses */}
        <div className="grid gap-4 sm:grid-cols-2">
          <Card className="px-6 py-5">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-[var(--success)]">
              <CheckCircle2 size={16} /> Strengths
            </h3>
            <ul className="space-y-2">
              {report.strengths.length ? report.strengths.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm text-[var(--text-secondary)]">
                  <span className="text-[var(--success)]">✓</span> {s}
                </li>
              )) : <li className="text-sm text-[var(--text-muted)]">—</li>}
            </ul>
          </Card>
          <Card className="px-6 py-5">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-[var(--warning)]">
              <Lightbulb size={16} /> Areas to improve
            </h3>
            <ul className="space-y-2">
              {report.weaknesses.length ? report.weaknesses.map((w, i) => (
                <li key={i} className="flex gap-2 text-sm text-[var(--text-secondary)]">
                  <span className="text-[var(--warning)]">→</span> {w}
                </li>
              )) : <li className="text-sm text-[var(--text-muted)]">—</li>}
            </ul>
          </Card>
        </div>

        {/* Next steps */}
        {report.improvement_suggestions.length > 0 && (
          <Card className="px-6 py-5">
            <h3 className="mb-3 font-semibold text-[var(--text)]">Recommended next steps</h3>
            <ol className="space-y-2.5">
              {report.improvement_suggestions.map((s, i) => (
                <li key={i} className="flex gap-3 text-sm text-[var(--text-secondary)]">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs font-semibold text-[var(--accent)]">{i + 1}</span>
                  {s}
                </li>
              ))}
            </ol>
          </Card>
        )}
      </main>
    </div>
  );
}
