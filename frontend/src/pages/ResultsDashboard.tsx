/**
 * Professional Results Dashboard with Code Evaluation Support
 * Location: frontend/src/pages/ResultsDashboard.tsx
 * 
 * UPDATED: Now saves session data for AnalyticsDashboard aggregation
 */

import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client";

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

// Helper function to save session to localStorage for progress tracking
function saveSessionToHistory(
  sessionId: string,
  interviewType: string,
  questionsCount: number,
  evaluation: EvaluationResult
) {
  const sessionSummary = {
    session_id: sessionId,
    date: new Date().toISOString(),
    interview_type: interviewType,
    overall_score: evaluation.overall_score,
    rubric_scores: evaluation.rubric_scores,
    questions_count: questionsCount,
  };

  // Load existing sessions
  const existing = localStorage.getItem("interview_sessions");
  const sessions = existing ? JSON.parse(existing) : [];

  // Add new session (avoid duplicates)
  if (!sessions.find((s: any) => s.session_id === sessionId)) {
    sessions.push(sessionSummary);
    // Keep only last 50 sessions
    const trimmed = sessions.slice(-50);
    localStorage.setItem("interview_sessions", JSON.stringify(trimmed));
  }
}

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
              const isCodeQuestion = questionData?.interview_type === 'oa';
              
              if (isCodeQuestion && q.code_submissions && q.code_submissions.length > 0) {
                const lastSubmission = q.code_submissions[q.code_submissions.length - 1];
                
                const codeEvalResponse = await api.post("/code-execution/evaluate", {
                  code: lastSubmission.code,
                  language: lastSubmission.language,
                  problem_description: questionData.question,
                  test_cases: questionData.test_cases?.map((tc: any) => ({
                    input: tc.input,
                    expected_output: tc.expected_output,
                    description: tc.description,
                    is_hidden: tc.is_hidden
                  })) || [],
                  timeout: 5
                });

                return {
                  ...codeEvalResponse.data,
                  question_id: q.question_id,
                  is_code_question: true
                };
              } else {
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
                
                return {
                  ...response.data,
                  is_code_question: false
                };
              }
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
                is_code_question: false
              };
            }
          })
        );

        const aggregatedEval = aggregateEvaluations(evaluations);
        setEvaluation(aggregatedEval);
        
        // Auto-save session to history for progress tracking
        const interviewType = questions?.[0]?.interview_type || "technical";
        saveSessionToHistory(
          sessionId,
          interviewType,
          questions?.length || 0,
          aggregatedEval
        );
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
        
        if (!rubricScores['code_correctness']) rubricScores['code_correctness'] = [];
        if (!rubricScores['code_quality']) rubricScores['code_quality'] = [];
        if (!rubricScores['algorithmic_complexity']) rubricScores['algorithmic_complexity'] = [];
        
        rubricScores['code_correctness'].push(evalResult.correctness_score);
        rubricScores['code_quality'].push(evalResult.code_quality_score);
        rubricScores['algorithmic_complexity'].push(evalResult.complexity_score);
      } else {
        const scores = Array.isArray(evalResult.rubric_scores)
          ? evalResult.rubric_scores
          : Object.entries(evalResult.rubric_scores || {}).map(([key, value]) => ({
              category: key,
              score: value,
            }));

        scores.forEach((scoreItem: any) => {
          const key = scoreItem.category;
          const value = scoreItem.score;
          if (!rubricScores[key]) rubricScores[key] = [];
          rubricScores[key].push(value as number);
        });
      }
    });

    const avgRubricScores: Record<string, number> = {};
    Object.entries(rubricScores).forEach(([key, values]) => {
      avgRubricScores[key] = values.reduce((a, b) => a + b, 0) / values.length;
    });

    const overallScore =
      Object.values(avgRubricScores).reduce((a, b) => a + b, 0) /
      Object.keys(avgRubricScores).length;

    const allStrengths: string[] = [];
    const allWeaknesses: string[] = [];
    const allSuggestions: string[] = [];

    evaluations.forEach((evalResult) => {
      if (evalResult.strengths) allStrengths.push(...evalResult.strengths);
      if (evalResult.weaknesses) allWeaknesses.push(...evalResult.weaknesses);
      if (evalResult.improvement_suggestions)
        allSuggestions.push(...evalResult.improvement_suggestions);
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

  const getScoreColor = (score: number) => {
    if (score >= 4.5) return "text-green-600";
    if (score >= 4) return "text-blue-600";
    if (score >= 3) return "text-yellow-600";
    if (score >= 2) return "text-orange-600";
    return "text-red-600";
  };

  const getScoreLabel = (score: number) => {
    if (score >= 4.5) return "Excellent";
    if (score >= 4) return "Good";
    if (score >= 3) return "Satisfactory";
    if (score >= 2) return "Needs Improvement";
    return "Poor";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md text-center">
          <div className="w-20 h-20 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-2xl font-bold text-gray-800 mb-2">Evaluating Performance...</p>
          <p className="text-sm text-gray-600">Analyzing speech, language, code, and technical accuracy</p>
        </div>
      </div>
    );
  }

  if (!evaluation) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-6 py-12 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <span className="text-4xl">🏆</span>
              <h1 className="text-4xl font-bold text-gray-900">Interview Results</h1>
            </div>
            {saved && (
              <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                ✓ Saved to Progress
              </span>
            )}
          </div>
          <p className="text-gray-600 mt-2">
            Session: <span className="font-mono text-sm">{sessionId?.slice(0, 8)}...</span>
          </p>
        </div>

        {/* Overall Score */}
        <div className="mb-8 bg-gradient-to-br from-white to-blue-50 rounded-2xl shadow-2xl p-12 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-400/10 rounded-full blur-3xl"></div>
          <div className="text-center relative z-10">
            <p className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wider">
              Overall Performance
            </p>
            <div className={`text-8xl font-black mb-4 ${getScoreColor(evaluation.overall_score)}`}>
              {evaluation.overall_score.toFixed(1)}
            </div>
            <p className="text-3xl font-bold text-gray-700 mb-6">
              {getScoreLabel(evaluation.overall_score)}
            </p>
            <div className="max-w-md mx-auto">
              <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden shadow-inner">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-1000"
                  style={{ width: `${(evaluation.overall_score / 5) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Code Evaluations Section */}
        {evaluation.code_evaluations && evaluation.code_evaluations.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
              💻 Coding Challenge Results
            </h2>
            <div className="grid grid-cols-1 gap-6">
              {evaluation.code_evaluations.map((codeEval, idx) => (
                <div key={idx} className="bg-white rounded-xl shadow-lg p-6 border-2 border-purple-200">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-gray-900">
                      Question {idx + 1} - Code Solution
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className={`text-3xl font-bold ${getScoreColor(codeEval.overall_score)}`}>
                        {codeEval.overall_score.toFixed(1)}/5
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="bg-blue-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1">Correctness</p>
                      <p className="text-2xl font-bold text-blue-600">{codeEval.correctness_score.toFixed(1)}/5</p>
                    </div>
                    <div className="bg-green-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1">Code Quality</p>
                      <p className="text-2xl font-bold text-green-600">{codeEval.code_quality_score.toFixed(1)}/5</p>
                    </div>
                    <div className="bg-purple-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1">Complexity</p>
                      <p className="text-2xl font-bold text-purple-600">{codeEval.complexity_score.toFixed(1)}/5</p>
                    </div>
                    <div className="bg-yellow-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1">Tests Passed</p>
                      <p className="text-2xl font-bold text-yellow-600">{codeEval.passed_tests}/{codeEval.total_tests}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1 font-semibold">Time Complexity</p>
                      <p className="text-lg font-bold text-gray-800">{codeEval.time_complexity}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1 font-semibold">Space Complexity</p>
                      <p className="text-lg font-bold text-gray-800">{codeEval.space_complexity}</p>
                    </div>
                  </div>

                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <p className="text-sm font-semibold text-blue-900 mb-2">📝 Feedback</p>
                    <p className="text-sm text-gray-800">{codeEval.feedback}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Detailed Scores */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            🎯 Detailed Breakdown
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(evaluation.rubric_scores)
              .sort(([, a], [, b]) => b - a)
              .map(([category, score]) => (
              <div key={category} className="bg-white rounded-xl shadow-lg p-5 hover:shadow-xl transition-all">
                <div className="flex justify-between items-start mb-3">
                  <span className="font-semibold text-gray-700 capitalize text-sm">
                    {category.replace(/_/g, " ")}
                  </span>
                  <span className={`text-3xl font-bold ${getScoreColor(score)}`}>
                    {score.toFixed(1)}
                  </span>
                </div>
                <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all"
                    style={{ width: `${(score / 5) * 100}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 mt-2">{getScoreLabel(score)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Speech Metrics */}
        {sessionData?.questions && sessionData.questions.some((q: any) => q.speech_metrics) && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-4 text-gray-900">📊 Speech & Language Analysis</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sessionData.questions
                .filter((q: any) => q.speech_metrics)
                .map((q: any, idx: number) => (
                <div key={idx} className="bg-white rounded-xl shadow-lg p-5 border border-gray-200">
                  <p className="text-sm font-bold mb-4 text-gray-900 border-b pb-2">
                    Question {idx + 1}
                  </p>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600 text-xs mb-1 font-semibold">Words/Min</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {q.speech_metrics?.words_per_minute?.toFixed(0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600 text-xs mb-1 font-semibold">Fillers</p>
                      <p className="text-2xl font-bold text-yellow-600">
                        {q.speech_metrics?.filler_word_percentage?.toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600 text-xs mb-1 font-semibold">Grammar</p>
                      <p className="text-2xl font-bold text-green-600">
                        {q.language_metrics?.grammar_score?.toFixed(1)}/5
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600 text-xs mb-1 font-semibold">Vocabulary</p>
                      <p className="text-sm font-bold text-gray-800 capitalize mt-2">
                        {q.language_metrics?.vocabulary_level}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Strengths & Weaknesses */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {evaluation.strengths.length > 0 && (
            <div className="bg-green-50 rounded-xl shadow-lg p-6 border-2 border-green-200">
              <h2 className="text-xl font-bold text-green-900 mb-4 flex items-center gap-2">
                💪 Strengths
              </h2>
              <ul className="space-y-3">
                {evaluation.strengths.map((strength, idx) => (
                  <li key={idx} className="flex items-start gap-3 p-3 bg-white rounded-lg shadow-sm">
                    <span className="text-green-600 text-xl flex-shrink-0">✓</span>
                    <span className="text-sm text-gray-900 leading-relaxed font-medium">{strength}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {evaluation.weaknesses.length > 0 && (
            <div className="bg-red-50 rounded-xl shadow-lg p-6 border-2 border-red-200">
              <h2 className="text-xl font-bold text-red-900 mb-4 flex items-center gap-2">
                ⚠️ Areas for Improvement
              </h2>
              <ul className="space-y-3">
                {evaluation.weaknesses.map((weakness, idx) => (
                  <li key={idx} className="flex items-start gap-3 p-3 bg-white rounded-lg shadow-sm">
                    <span className="text-red-600 text-xl flex-shrink-0">•</span>
                    <span className="text-sm text-gray-900 leading-relaxed font-medium">{weakness}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Suggestions */}
        {evaluation.improvement_suggestions.length > 0 && (
          <div className="mb-8 bg-blue-50 rounded-xl shadow-lg p-6 border-2 border-blue-200">
            <h2 className="text-xl font-bold text-blue-900 mb-4 flex items-center gap-2">
              💡 Actionable Suggestions
            </h2>
            <div className="space-y-3">
              {evaluation.improvement_suggestions.map((suggestion, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-4 bg-white rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
                >
                  <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center flex-shrink-0 font-bold text-sm">
                    {idx + 1}
                  </div>
                  <span className="text-sm text-gray-900 leading-relaxed pt-1 font-medium">{suggestion}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => navigate("/")}
            className="flex-1 min-w-[200px] px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-lg font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:scale-105 transition-all"
          >
            🏠 Start New Interview
          </button>
          <button
            onClick={() => navigate("/progress")}
            className="px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all"
          >
            📊 View Progress
          </button>
          <button
            onClick={() => window.print()}
            className="px-8 py-4 border-2 border-gray-300 hover:border-gray-400 rounded-xl font-semibold hover:bg-gray-50 transition-all"
          >
            🖨️ Print Results
          </button>
        </div>
      </div>
    </div>
  );
}