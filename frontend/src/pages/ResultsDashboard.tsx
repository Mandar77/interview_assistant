/**
 * ResultsDashboard — post-interview evaluation report.
 * Location: frontend/src/pages/ResultsDashboard.tsx
 *
 * Aggregates per-question evaluations (rubric + code) into a premium report:
 * hero score, rubric bars, code results, speech metrics, strengths/weaknesses,
 * and next steps. Data logic unchanged; visual layer fully themed.
 */

import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Code2, Lightbulb, Mic, Trophy } from "lucide-react";
import { api } from "../api/client";
import { Badge, Button, Card } from "../ui";
import { BrandMark } from "../ui/AppShell";
import ThemeToggle from "../theme/ThemeToggle";
import { getScoreLabel } from "../lib/utils";

interface EvaluationResult {
  overall_score: number;
  rubric_scores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
  improvement_suggestions: string[];
  code_evaluations?: Array<{
    question_id: string;
    correctness_score: number;
    code_quality_score: number;
    complexity_score: number;
    overall_score: number;
    time_complexity: string;
    space_complexity: string;
    passed_tests: number;
    total_tests: number;
    feedback: string;
  }>;
}

function saveSessionToHistory(sessionId: string, interviewType: string, questionsCount: number, evaluation: EvaluationResult) {
  const summary = {
    session_id: sessionId,
    date: new Date().toISOString(),
    interview_type: interviewType,
    overall_score: evaluation.overall_score,
    rubric_scores: evaluation.rubric_scores,
    questions_count: questionsCount,
  };
  const existing = localStorage.getItem("interview_sessions");
  const sessions = existing ? JSON.parse(existing) : [];
  if (!sessions.find((s: any) => s.session_id === sessionId)) {
    sessions.push(summary);
    localStorage.setItem("interview_sessions", JSON.stringify(sessions.slice(-50)));
  }
}

const scoreTone = (s: number) =>
  s >= 4 ? "var(--success)" : s >= 3 ? "var(--accent)" : s >= 2 ? "var(--warning)" : "var(--error)";

export default function ResultsDashboard() {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId, sessionData, questions } = location.state || {};

  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
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
              return {
                overall_score: 3.0,
                rubric_scores: [
                  { category: "technical_correctness", score: 3.0 },
                  { category: "communication", score: 3.0 },
                ],
                strengths: ["Completed answer"],
                weaknesses: [],
                improvement_suggestions: [],
                is_code_question: false,
              };
            }
          })
        );
        const aggregatedEval = aggregateEvaluations(evaluations);
        setEvaluation(aggregatedEval);
        const interviewType = questions?.[0]?.interview_type || "technical";
        saveSessionToHistory(sessionId, interviewType, questions?.length || 0, aggregatedEval);
        setSaved(true);
        setLoading(false);
      } catch (error) {
        console.error("Evaluation failed:", error);
        setLoading(false);
      }
    };
    fetchEvaluation();
  }, [sessionId, sessionData, navigate, questions]);

  const aggregateEvaluations = (evaluations: any[]): EvaluationResult => {
    const rubricScores: Record<string, number[]> = {};
    const codeEvaluations: any[] = [];
    evaluations.forEach((evalResult) => {
      if (evalResult.is_code_question) {
        codeEvaluations.push({
          question_id: evalResult.question_id,
          correctness_score: evalResult.correctness_score,
          code_quality_score: evalResult.code_quality_score,
          complexity_score: evalResult.complexity_score,
          overall_score: evalResult.overall_score,
          time_complexity: evalResult.time_complexity,
          space_complexity: evalResult.space_complexity,
          passed_tests: evalResult.passed_tests,
          total_tests: evalResult.total_tests,
          feedback: evalResult.feedback,
        });
        (rubricScores["code_correctness"] ||= []).push(evalResult.correctness_score);
        (rubricScores["code_quality"] ||= []).push(evalResult.code_quality_score);
        (rubricScores["algorithmic_complexity"] ||= []).push(evalResult.complexity_score);
      } else {
        const scores = Array.isArray(evalResult.rubric_scores)
          ? evalResult.rubric_scores
          : Object.entries(evalResult.rubric_scores || {}).map(([key, value]) => ({ category: key, score: value }));
        scores.forEach((scoreItem: any) => {
          (rubricScores[scoreItem.category] ||= []).push(scoreItem.score as number);
        });
      }
    });
    const avgRubricScores: Record<string, number> = {};
    Object.entries(rubricScores).forEach(([key, values]) => {
      avgRubricScores[key] = values.reduce((a, b) => a + b, 0) / values.length;
    });
    const rubricCount = Object.keys(avgRubricScores).length;
    const overallScore = rubricCount > 0 ? Object.values(avgRubricScores).reduce((a, b) => a + b, 0) / rubricCount : 0;
    const allStrengths: string[] = [];
    const allWeaknesses: string[] = [];
    const allSuggestions: string[] = [];
    evaluations.forEach((e) => {
      if (e.strengths) allStrengths.push(...e.strengths);
      if (e.weaknesses) allWeaknesses.push(...e.weaknesses);
      if (e.improvement_suggestions) allSuggestions.push(...e.improvement_suggestions);
    });
    return {
      overall_score: overallScore,
      rubric_scores: avgRubricScores,
      strengths: [...new Set(allStrengths)].slice(0, 5),
      weaknesses: [...new Set(allWeaknesses)].slice(0, 5),
      improvement_suggestions: [...new Set(allSuggestions)].slice(0, 5),
      code_evaluations: codeEvaluations.length > 0 ? codeEvaluations : undefined,
    };
  };

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[var(--background)]">
        <div className="h-9 w-9 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
        <div className="text-center">
          <p className="font-medium text-[var(--text)]">Evaluating your performance…</p>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Analyzing speech, language, code, and accuracy</p>
        </div>
      </div>
    );
  }

  if (!evaluation) return null;
  const pct = Math.min(100, (evaluation.overall_score / 5) * 100);

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
        {/* Hero score */}
        <Card elevated className="overflow-hidden">
          <div className="relative px-8 py-10 text-center">
            <div className="bg-grid pointer-events-none absolute inset-0 opacity-40" />
            <div className="relative">
              <Trophy size={22} className="mx-auto mb-3 text-[var(--accent)]" />
              <p className="text-xs uppercase tracking-wider text-[var(--text-muted)]">Overall performance</p>
              <p className="mt-2 font-mono text-6xl font-semibold" style={{ color: scoreTone(evaluation.overall_score) }}>
                {evaluation.overall_score.toFixed(1)}
              </p>
              <p className="mt-1 text-lg font-medium text-[var(--text-secondary)]">{getScoreLabel(evaluation.overall_score)}</p>
              <div className="mx-auto mt-5 h-2 max-w-md overflow-hidden rounded-full bg-[var(--surface-3)]">
                <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: scoreTone(evaluation.overall_score) }} />
              </div>
            </div>
          </div>
        </Card>

        {/* Code evaluations */}
        {evaluation.code_evaluations && evaluation.code_evaluations.length > 0 && (
          <div>
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-[var(--text)]">
              <Code2 size={18} className="text-[var(--accent)]" /> Coding results
            </h2>
            <div className="space-y-4">
              {evaluation.code_evaluations.map((c, i) => (
                <Card key={i} className="px-6 py-5">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="font-semibold text-[var(--text)]">Question {i + 1}</h3>
                    <Badge tone="neutral">{c.passed_tests}/{c.total_tests} tests</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                    {[
                      ["Correctness", c.correctness_score],
                      ["Quality", c.code_quality_score],
                      ["Complexity", c.complexity_score],
                      ["Overall", c.overall_score],
                    ].map(([label, val]) => (
                      <div key={label as string}>
                        <p className="text-xs text-[var(--text-muted)]">{label}</p>
                        <p className="font-mono text-2xl font-semibold" style={{ color: scoreTone(val as number) }}>
                          {(val as number).toFixed(1)}
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

        {/* Rubric breakdown */}
        <Card className="px-6 py-5">
          <h2 className="mb-4 text-lg font-semibold text-[var(--text)]">Rubric breakdown</h2>
          <div className="grid gap-x-8 gap-y-3.5 sm:grid-cols-2">
            {Object.entries(evaluation.rubric_scores).sort(([, a], [, b]) => b - a).map(([key, score]) => (
              <div key={key}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="capitalize text-[var(--text-secondary)]">{key.replace(/_/g, " ")}</span>
                  <span className="font-mono font-medium text-[var(--text)]">{score.toFixed(1)}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-[var(--surface-3)]">
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${(score / 5) * 100}%`, background: scoreTone(score) }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

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
                  <span className="text-[var(--text-secondary)]">Grammar <b className="font-mono text-[var(--text)]">{q.language_metrics?.grammar_score?.toFixed(1)}/5</b></span>
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
              {evaluation.strengths.length ? evaluation.strengths.map((s, i) => (
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
              {evaluation.weaknesses.length ? evaluation.weaknesses.map((w, i) => (
                <li key={i} className="flex gap-2 text-sm text-[var(--text-secondary)]">
                  <span className="text-[var(--warning)]">→</span> {w}
                </li>
              )) : <li className="text-sm text-[var(--text-muted)]">—</li>}
            </ul>
          </Card>
        </div>

        {/* Next steps */}
        {evaluation.improvement_suggestions.length > 0 && (
          <Card className="px-6 py-5">
            <h3 className="mb-3 font-semibold text-[var(--text)]">Recommended next steps</h3>
            <ol className="space-y-2.5">
              {evaluation.improvement_suggestions.map((s, i) => (
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
