// frontend/src/pages/InterviewRoom.tsx (ADD code execution support)

import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useInterviewSession } from "../hooks/useInterviewSession";
import { useSpeechWebSocket } from "../hooks/useSpeechWebSocket";
import { api } from "../api/client";
import AudioRecorder from "../components/AudioRecorder";
import CameraPreview, { BodyLanguageMetrics } from "../components/CameraPreview";
import CodeEditor from "../components/CodeEditor";  // ✅ NEW
import TestResults from "../components/TestResults";  // ✅ NEW

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

const SHOW_LIVE_METRICS = import.meta.env.DEV;

export default function InterviewRoom() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    sessionId,
    questions,
    currentQuestion,
    currentQuestionIndex,
    answers,
    isLastQuestion,
    loadQuestions,
    startAnswer,
    updateCurrentTranscript,
    completeCurrentAnswer,
    nextQuestion,
  } = useInterviewSession();

  const [timerRunning, setTimerRunning] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [timeUp, setTimeUp] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Body language metrics tracking
  const [currentMetrics, setCurrentMetrics] = useState<BodyLanguageMetrics | null>(null);
  const metricsHistoryRef = useRef<Map<number, BodyLanguageMetrics[]>>(new Map());

  // ✅ NEW: Code execution state
  const [currentCode, setCurrentCode] = useState<string>('');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('python');
  const [testResults, setTestResults] = useState<any>(null);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [codeEvaluation, setCodeEvaluation] = useState<any>(null);
  const codeHistoryRef = useRef<Map<number, { code: string; language: string; evaluation: any }[]>>(new Map());

  const isRecordingRef = useRef(isRecording);
  const currentQuestionIndexRef = useRef(currentQuestionIndex);

  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  useEffect(() => {
    currentQuestionIndexRef.current = currentQuestionIndex;
  }, [currentQuestionIndex]);

  const {
    isConnected,
    sendAudioChunk,
    startQuestion: wsStartQuestion,
    endQuestion: wsEndQuestion,
    endSession: wsEndSession,
  } = useSpeechWebSocket({
    sessionId,
    onTranscript: (text) => updateCurrentTranscript(text),
    onConnected: () => console.log("WebSocket connected!"),
    onQuestionEnded: (questionId, finalTranscript) => {
      console.log(`Question ${questionId} ended:`, finalTranscript);
      updateCurrentTranscript(finalTranscript);
    },
  });

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        const config = location.state as any;
        if (!config?.jobDescription) {
          alert("Please configure your interview first");
          navigate("/");
          return;
        }

        const response = await api.post("/questions/generate", {
          job_description: config.jobDescription,
          interview_type: config.interviewType || "technical",
          difficulty: config.difficulty || "medium",
          num_questions: config.numQuestions || 3,
        });

        const questionsWithDuration = response.data.questions.map((q: any) => ({
          ...q,
          expected_duration_mins: 
            config.difficulty === "easy" ? 5 :
            config.difficulty === "hard" ? 9 : 7
        }));

        loadQuestions(questionsWithDuration);
        setLoading(false);
      } catch (error) {
        console.error("Failed to load questions:", error);
        alert("Failed to load questions. Please try again.");
        navigate("/");
      }
    };

    fetchQuestions();
  }, []);

  // ✅ NEW: Load starter code when question changes
  useEffect(() => {
    if (currentQuestion?.interview_type === 'oa' && currentQuestion.starter_code) {
      const starterCode = currentQuestion.starter_code[selectedLanguage] || '';
      setCurrentCode(starterCode);
      setTestResults(null);
      setCodeEvaluation(null);
    }
  }, [currentQuestion, selectedLanguage]);

  useEffect(() => {
    if (!timerRunning || timeRemaining <= 0) return;

    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          setTimeUp(true);
          setTimerRunning(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [timerRunning, timeRemaining]);

  const handleMetricsUpdate = useCallback((metrics: BodyLanguageMetrics) => {
    setCurrentMetrics(metrics);

    if (isRecordingRef.current) {
      const currentIndex = currentQuestionIndexRef.current;
      if (!metricsHistoryRef.current.has(currentIndex)) {
        metricsHistoryRef.current.set(currentIndex, []);
      }
      metricsHistoryRef.current.get(currentIndex)!.push(metrics);
    }
  }, []);

  const getAverageMetrics = (questionIndex: number): BodyLanguageMetrics | null => {
    const history = metricsHistoryRef.current.get(questionIndex);
    if (!history || history.length === 0) return null;

    const avg = history.reduce((acc, curr) => ({
      eye_contact_percentage: acc.eye_contact_percentage + curr.eye_contact_percentage,
      posture_score: acc.posture_score + curr.posture_score,
      gesture_frequency: acc.gesture_frequency + curr.gesture_frequency,
      head_movement_stability: acc.head_movement_stability + curr.head_movement_stability,
      facial_confidence_signals: {
        smile_detected: acc.facial_confidence_signals.smile_detected || curr.facial_confidence_signals.smile_detected,
        nod_count: acc.facial_confidence_signals.nod_count + curr.facial_confidence_signals.nod_count,
        nervous_ticks: acc.facial_confidence_signals.nervous_ticks + curr.facial_confidence_signals.nervous_ticks,
      },
      timestamp: curr.timestamp,
    }));

    const count = history.length;

    return {
      eye_contact_percentage: Math.round(avg.eye_contact_percentage / count),
      posture_score: parseFloat((avg.posture_score / count).toFixed(2)),
      gesture_frequency: parseFloat((avg.gesture_frequency / count).toFixed(2)),
      head_movement_stability: parseFloat((avg.head_movement_stability / count).toFixed(2)),
      facial_confidence_signals: {
        smile_detected: avg.facial_confidence_signals.smile_detected,
        nod_count: Math.round(avg.facial_confidence_signals.nod_count / count),
        nervous_ticks: Math.round(avg.facial_confidence_signals.nervous_ticks / count),
      },
      timestamp: Date.now(),
    };
  };

  // ✅ NEW: Run code with test cases
  const handleRunCode = async (code: string) => {
    if (!currentQuestion?.test_cases || currentQuestion.test_cases.length === 0) {
      alert("No test cases available for this question");
      return;
    }

    setIsRunningCode(true);
    setTestResults(null);

    try {
      const response = await api.post('/code-execution/execute-tests', {
        code: code,
        language: selectedLanguage,
        test_cases: currentQuestion.test_cases.map((tc: any) => ({
          input: tc.input,
          expected_output: tc.expected_output,
          description: tc.description,
          is_hidden: tc.is_hidden
        })),
        timeout: 5
      });

      setTestResults(response.data);

      // Store code submission history
      if (!codeHistoryRef.current.has(currentQuestionIndex)) {
        codeHistoryRef.current.set(currentQuestionIndex, []);
      }
      codeHistoryRef.current.get(currentQuestionIndex)!.push({
        code: code,
        language: selectedLanguage,
        evaluation: response.data
      });

    } catch (error: any) {
      console.error("Code execution failed:", error);
      alert(`Execution failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsRunningCode(false);
    }
  };

  // ✅ NEW: Evaluate code comprehensively
  const handleEvaluateCode = async () => {
    if (!currentQuestion?.test_cases || !currentCode) {
      alert("Please write code and run tests first");
      return;
    }

    try {
      const response = await api.post('/code-execution/evaluate', {
        code: currentCode,
        language: selectedLanguage,
        problem_description: currentQuestion.question,
        test_cases: currentQuestion.test_cases.map((tc: any) => ({
          input: tc.input,
          expected_output: tc.expected_output,
          description: tc.description,
          is_hidden: tc.is_hidden
        })),
        timeout: 5
      });

      setCodeEvaluation(response.data);
      console.log("Code evaluation:", response.data);

    } catch (error: any) {
      console.error("Code evaluation failed:", error);
      alert(`Evaluation failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleStartAnswer = async () => {
    if (!currentQuestion || isRecording || !isConnected) return;

    // For OA questions, don't require recording
    if (currentQuestion.interview_type !== 'oa') {
      wsStartQuestion(currentQuestion.id, currentQuestion.question);
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    metricsHistoryRef.current.delete(currentQuestionIndex);
    setCurrentMetrics(null);

    startAnswer();
    setTimeRemaining(currentQuestion.expected_duration_mins * 60);
    setTimerRunning(true);
    setTimeUp(false);
    
    if (currentQuestion.interview_type !== 'oa') {
      setIsRecording(true);
    }
  };

  const handleStopAnswer = () => {
    if (!isRecording && currentQuestion?.interview_type !== 'oa') return;
    
    if (currentQuestion?.interview_type !== 'oa') {
      wsEndQuestion();
    }
    
    completeCurrentAnswer();
    setTimerRunning(false);
    setIsRecording(false);
  };

  const handleNextQuestion = () => {
    if (isLastQuestion) {
      handleSubmitInterview();
    } else {
      nextQuestion();
      setTimeUp(false);
    }
  };

  const handleSubmitInterview = async () => {
    setSubmitting(true);
    try {
      wsEndSession();
      await new Promise((resolve) => setTimeout(resolve, 5000));

      const sessionResponse = await api.get(`/speech/session/${sessionId}/for-evaluation`);
      const sessionData = sessionResponse.data;

      if (sessionData.questions) {
        sessionData.questions = sessionData.questions.map((q: any, idx: number) => {
          const avgMetrics = getAverageMetrics(idx);
          const codeHistory = codeHistoryRef.current.get(idx);
          
          return {
            ...q,
            body_language_metrics: avgMetrics || undefined,
            code_submissions: codeHistory || undefined,  // ✅ NEW
          };
        });
      }

      navigate("/results", {
        state: {
          sessionId,
          sessionData,
          questions,
          answers,
        },
      });
    } catch (error: any) {
      console.error("Failed to submit interview:", error);
      alert(`Failed to submit: ${error.response?.data?.detail || error.message}`);
      setSubmitting(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const isOAQuestion = currentQuestion?.interview_type === 'oa';

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-xl font-semibold text-gray-800 mb-2">Generating Questions...</p>
          <p className="text-sm text-gray-600">Analyzing job description with AI</p>
        </div>
      </div>
    );
  }

  if (!currentQuestion) {
    return <div className="flex items-center justify-center min-h-screen">No questions available</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200 shadow-lg">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-bold text-gray-900">Interview Assistant</h1>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                Question {currentQuestionIndex + 1} of {questions.length}
              </span>
            </div>

            <div className="flex items-center gap-4">
              {!isOAQuestion && (
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium",
                    isRecording ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                  )}>
                    {isRecording ? "🎤" : "🔇"} Mic
                  </div>
                  <div className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium",
                    isConnected ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                  )}>
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      isConnected ? "bg-green-500 animate-pulse" : "bg-red-400"
                    )} />
                    {isConnected ? "Connected" : "Offline"}
                  </div>
                </div>
              )}

              <div className={cn(
                "px-4 py-2 rounded-lg font-mono text-lg font-bold",
                timeRemaining < 60
                  ? "bg-red-100 text-red-700 animate-pulse"
                  : "bg-blue-100 text-blue-700"
              )}>
                ⏱️ {formatTime(timeRemaining)}
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="pt-24 pb-8 px-6 container mx-auto max-w-[1800px]">
        <div className={cn("grid gap-6", isOAQuestion ? "grid-cols-12" : "grid-cols-12")}>
          
          {/* Left Column - Camera/Code Output */}
          <div className={cn("space-y-4", isOAQuestion ? "col-span-5" : "col-span-4")}>
            {!isOAQuestion ? (
              <>
                <CameraPreview 
                  isRecording={isRecording}
                  onMetricsUpdate={handleMetricsUpdate}
                  enableMediaPipe={true}
                />

                {SHOW_LIVE_METRICS && currentMetrics && isRecording && (
                  <div className="bg-white rounded-xl shadow-lg p-4 border-2 border-blue-200">
                    <h4 className="font-bold text-sm mb-3 text-gray-900">📊 Live Metrics</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">👁️ Eye Contact:</span>
                        <span className="font-bold text-blue-600">{currentMetrics.eye_contact_percentage}%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">📍 Posture:</span>
                        <span className="font-bold text-blue-600">{currentMetrics.posture_score.toFixed(1)}/5</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">🤝 Gestures:</span>
                        <span className="font-bold text-blue-600">{currentMetrics.gesture_frequency.toFixed(1)}/s</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">😊 Nods:</span>
                        <span className="font-bold text-blue-600">{currentMetrics.facial_confidence_signals.nod_count}</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="bg-white rounded-xl shadow-xl p-4">
                  <h3 className="text-lg font-bold mb-3 text-gray-900">🎙️ Recording Controls</h3>
                  <AudioRecorder
                    onStart={handleStartAnswer}
                    onStop={handleStopAnswer}
                    onAudioChunk={sendAudioChunk}
                    autoStop={timeUp}
                    disabled={!isConnected || submitting}
                  />
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <p className="text-sm text-blue-900 font-medium">
                      {!isRecording 
                        ? "💡 Click 'Start Answer' when ready"
                        : "🎤 Speak clearly. Click 'Stop Answer' when done."}
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <>
                {/* Test Results for OA */}
                <TestResults results={testResults} loading={isRunningCode} />

                {/* Code Evaluation Summary */}
                {codeEvaluation && (
                  <div className="bg-white rounded-xl shadow-lg p-4">
                    <h4 className="font-bold text-sm mb-3 text-gray-900">📊 Code Evaluation</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">Correctness:</span>
                        <span className="font-bold text-blue-600">{codeEvaluation.correctness_score}/5</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">Code Quality:</span>
                        <span className="font-bold text-blue-600">{codeEvaluation.code_quality_score}/5</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-700">Complexity:</span>
                        <span className="font-bold text-blue-600">{codeEvaluation.complexity_score}/5</span>
                      </div>
                      <div className="pt-2 border-t border-gray-200">
                        <div className="flex justify-between items-center">
                          <span className="text-gray-900 font-semibold">Overall:</span>
                          <span className="font-bold text-green-600 text-lg">{codeEvaluation.overall_score}/5</span>
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 p-2 bg-blue-50 rounded text-xs text-gray-700">
                      {codeEvaluation.feedback}
                    </div>
                  </div>
                )}

                {/* Language Selector */}
                {currentQuestion.starter_code && (
                  <div className="bg-white rounded-xl shadow-lg p-4">
                    <h4 className="font-bold text-sm mb-3 text-gray-900">💻 Language</h4>
                    <select
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      {Object.keys(currentQuestion.starter_code).map((lang) => (
                        <option key={lang} value={lang}>
                          {lang.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Actions for OA */}
                <div className="bg-white rounded-xl shadow-lg p-4 space-y-2">
                  <button
                    onClick={handleEvaluateCode}
                    disabled={!testResults || isRunningCode}
                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition-colors"
                  >
                    📊 Evaluate Solution
                  </button>
                  {!isRecording && answers.length > currentQuestionIndex && (
                    <button
                      onClick={handleNextQuestion}
                      disabled={submitting}
                      className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition-colors"
                    >
                      {submitting ? "Submitting..." : isLastQuestion ? "Submit Interview →" : "Next Question →"}
                    </button>
                  )}
                </div>
              </>
            )}

            {/* Progress */}
            <div className="bg-white rounded-xl shadow-xl p-4">
              <h3 className="text-lg font-bold mb-3 text-gray-900">📋 Progress</h3>
              <div className="space-y-2">
                {questions.map((q, idx) => {
                  const answer = answers[idx];
                  const isCurrent = idx === currentQuestionIndex;
                  const isComplete = answer?.endedAt;

                  return (
                    <div
                      key={idx}
                      className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                        isCurrent ? "bg-blue-50 border-2 border-blue-200" : "bg-gray-50"
                      }`}
                    >
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 font-bold ${
                        isComplete
                          ? "bg-green-500 text-white"
                          : isCurrent
                          ? "bg-blue-500 text-white"
                          : "bg-gray-300 text-gray-600"
                      }`}>
                        {isComplete ? "✓" : idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium truncate ${
                          isCurrent ? "text-blue-900" : "text-gray-700"
                        }`}>
                          {q.question.slice(0, 40)}...
                        </p>
                        {answer?.transcript && (
                          <p className="text-xs text-gray-500">
                            {answer.transcript.split(" ").length} words
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column - Question/Code Editor */}
          <div className={cn("", isOAQuestion ? "col-span-7" : "col-span-8")}>
            <div className="bg-white rounded-xl shadow-2xl overflow-hidden" style={{ minHeight: '600px' }}>
              {isOAQuestion ? (
                <div className="h-full flex flex-col">
                  {/* Question Display */}
                  <div className="p-6 border-b border-gray-200 max-h-64 overflow-y-auto">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-semibold">
                        💻 Coding Challenge
                      </span>
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                        currentQuestion.difficulty === "easy" ? "bg-green-100 text-green-800" :
                        currentQuestion.difficulty === "hard" ? "bg-red-100 text-red-800" :
                        "bg-yellow-100 text-yellow-800"
                      }`}>
                        {currentQuestion.difficulty}
                      </span>
                      <span className="text-sm text-gray-600 font-medium">
                        ⏱️ {currentQuestion.expected_duration_mins} min
                      </span>
                    </div>
                    <div className="prose prose-sm max-w-none">
                      <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans leading-relaxed">
                        {currentQuestion.question}
                      </pre>
                    </div>
                  </div>

                  {/* Code Editor */}
                  <div className="flex-1">
                    <CodeEditor
                      language={selectedLanguage}
                      initialCode={currentCode}
                      onChange={setCurrentCode}
                      onRun={handleRunCode}
                      height="calc(100vh - 400px)"
                      theme="vs-dark"
                    />
                  </div>
                </div>
              ) : (
                <div className="p-8">
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold capitalize">
                        {currentQuestion.interview_type}
                      </span>
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                        currentQuestion.difficulty === "easy" ? "bg-green-100 text-green-800" :
                        currentQuestion.difficulty === "hard" ? "bg-red-100 text-red-800" :
                        "bg-yellow-100 text-yellow-800"
                      }`}>
                        {currentQuestion.difficulty}
                      </span>
                      <span className="text-sm text-gray-600 font-medium">
                        ⏱️ {currentQuestion.expected_duration_mins} min
                      </span>
                    </div>
                    
                    {currentQuestion.skill_tags.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-4">
                        {currentQuestion.skill_tags.map((tag, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 bg-gray-100 text-gray-800 rounded-lg text-xs font-semibold"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="mb-8">
                    <p className="text-2xl leading-relaxed text-gray-900 font-semibold">
                      {currentQuestion.question}
                    </p>
                  </div>

                  {timeUp && (
                    <div className="flex items-center gap-3 p-4 bg-red-50 border-2 border-red-200 rounded-xl mb-6 animate-pulse">
                      <span className="text-2xl">⚠️</span>
                      <p className="text-sm text-red-900 font-semibold">
                        Time's up! Please conclude your answer.
                      </p>
                    </div>
                  )}

                  {currentQuestion.evaluation_criteria && currentQuestion.evaluation_criteria.length > 0 && (
                    <div className="p-4 bg-blue-50 rounded-xl border border-blue-200">
                      <p className="text-sm font-semibold text-blue-900 mb-2">
                        📌 Evaluation Focus:
                      </p>
                      <ul className="text-sm text-blue-800 space-y-1">
                        {currentQuestion.evaluation_criteria.map((criterion: string, i: number) => (
                          <li key={i} className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                            {criterion.replace(/_/g, " ")}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {!isOAQuestion && (
              <div className="flex items-center justify-between mt-6">
                <button
                  onClick={() => navigate("/")}
                  disabled={isRecording || submitting}
                  className="px-6 py-3 text-gray-600 hover:text-gray-900 font-medium disabled:opacity-50 transition-colors"
                >
                  ← Exit Interview
                </button>

                {!isRecording && answers.length > currentQuestionIndex && (
                  <button
                    onClick={handleNextQuestion}
                    disabled={isRecording || submitting}
                    className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-lg font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:scale-105 transition-all disabled:opacity-50 disabled:transform-none disabled:cursor-not-allowed"
                  >
                    {submitting ? (
                      <>
                        <span className="inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                        Evaluating...
                      </>
                    ) : isLastQuestion ? (
                      "Submit Interview →"
                    ) : (
                      "Next Question →"
                    )}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}