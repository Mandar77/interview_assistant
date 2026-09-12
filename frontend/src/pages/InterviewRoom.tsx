// frontend/src/pages/InterviewRoom.tsx
// COMPLETE FILE WITH ALL FIXES:
// - Fix 1: questionsLoadedRef prevents double question generation
// - Fix 2: Polling for session data instead of fixed wait
// - Fix 3: answerStartedRef for synchronous state tracking

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useInterviewSession } from "../hooks/useInterviewSession";
import { useSpeechWebSocket } from "../hooks/useSpeechWebSocket";
import { api } from "../api/client";
import AudioRecorder from "../components/AudioRecorder";
import CameraPreview, { BodyLanguageMetrics } from "../components/CameraPreview";
import CodeEditor from "../components/CodeEditor";
import TestResults from "../components/TestResults";
import DiagramCanvas from "../components/DiagramCanvas";
import ScreenCaptureManager from "../components/ScreenCaptureManager";
import { Select } from "../ui";
import { formatScore, getScoreTone } from "../lib/utils";
import {
  AlertTriangle, Check, Clock, Code2, Eye, Hand, LayoutGrid, Lightbulb,
  ListChecks, Mic, MicOff, Network, ScanLine, Search, Smile, Target,
} from "lucide-react";

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
  
  // FIX 3: Track if answer was started (state for UI, ref for sync checks)
  const [answerStarted, setAnswerStarted] = useState(false);
  const answerStartedRef = useRef(false);

  // Body language metrics tracking
  const [currentMetrics, setCurrentMetrics] = useState<BodyLanguageMetrics | null>(null);
  const metricsHistoryRef = useRef<Map<number, BodyLanguageMetrics[]>>(new Map());

  // Code execution state
  const [currentCode, setCurrentCode] = useState<string>('');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('python');

  // Languages this question actually ships starter code for. The generator picks
  // these per question, so they can differ from the 'python' default.
  const availableLanguages = useMemo(
    () => Object.keys(currentQuestion?.starter_code ?? {}),
    [currentQuestion]
  );

  // OA problem statements are long (description + examples + constraints), so they
  // render in full by default; collapsing trades reading room for editor room.
  const [statementCollapsed, setStatementCollapsed] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [codeEvaluation, setCodeEvaluation] = useState<any>(null);
  const codeHistoryRef = useRef<Map<number, { code: string; language: string; evaluation: any }[]>>(new Map());

  // Screen capture state
  const [diagramCaptures, setDiagramCaptures] = useState<string[]>([]);
  const [diagramAnalysis, setDiagramAnalysis] = useState<any>(null);
  const diagramHistoryRef = useRef<Map<number, { screenshot: string; analysis: any; timestamp: number }[]>>(new Map());

  // FIX 1: Prevent double question generation
  const questionsLoadedRef = useRef(false);
  
  const isRecordingRef = useRef(isRecording);
  const currentQuestionIndexRef = useRef(currentQuestionIndex);

  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  // Reset answer tracking when question changes
  useEffect(() => {
    currentQuestionIndexRef.current = currentQuestionIndex;
    setAnswerStarted(false);
    answerStartedRef.current = false;
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

  // FIX 1: Prevent double execution with ref guard
  useEffect(() => {
    if (questionsLoadedRef.current) return;
    
    const fetchQuestions = async () => {
      try {
        const config = location.state as any;
        if (!config?.jobDescription) {
          alert("Please configure your interview first");
          navigate("/");
          return;
        }

        // Mark as loading BEFORE the API call
        questionsLoadedRef.current = true;

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
        questionsLoadedRef.current = false; // Reset on error to allow retry
        alert("Failed to load questions. Please try again.");
        navigate("/");
      }
    };

    fetchQuestions();
  }, [location.state, navigate, loadQuestions]);

  // Load starter code when question changes (for OA)
  useEffect(() => {
    if (currentQuestion?.interview_type !== 'oa' || !currentQuestion.starter_code) return;

    // The language carried over from the previous question may not be offered by
    // this one. Without this the <select> holds a value matching no <option>, and
    // the browser renders the control blank.
    if (availableLanguages.length > 0 && !availableLanguages.includes(selectedLanguage)) {
      setSelectedLanguage(availableLanguages[0]);
      return;
    }

    setCurrentCode(currentQuestion.starter_code[selectedLanguage] || '');
    setTestResults(null);
    setCodeEvaluation(null);
  }, [currentQuestion, selectedLanguage, availableLanguages]);

  // Always start a new coding question with the whole problem on screen.
  useEffect(() => {
    setStatementCollapsed(false);
  }, [currentQuestion?.id]);

  // Reset diagram captures when question changes (for system design)
  useEffect(() => {
    if (currentQuestion?.interview_type === 'system_design') {
      setDiagramCaptures([]);
      setDiagramAnalysis(null);
    }
  }, [currentQuestion]);

  // Timer countdown
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

  const getAverageMetrics = useCallback((questionIndex: number): BodyLanguageMetrics | null => {
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
  }, []);

  // Handle diagram capture
  const handleDiagramCapture = useCallback(async (base64: string, method: string) => {
    if (!currentQuestion) return;

    setDiagramCaptures(prev => [...prev, base64]);

    if (!diagramHistoryRef.current.has(currentQuestionIndex)) {
      diagramHistoryRef.current.set(currentQuestionIndex, []);
    }
    
    diagramHistoryRef.current.get(currentQuestionIndex)!.push({
      screenshot: base64,
      analysis: null,
      timestamp: Date.now(),
    });

    console.log(`📸 Diagram capture stored (total: ${diagramCaptures.length + 1})`);
  }, [currentQuestion, currentQuestionIndex, diagramCaptures.length]);

  // Analyze latest diagram
  const handleAnalyzeDiagram = useCallback(async () => {
    if (diagramCaptures.length === 0) {
      alert("Please capture a diagram first");
      return;
    }

    const latestScreenshot = diagramCaptures[diagramCaptures.length - 1];
    const currentTranscript = answers[currentQuestionIndex]?.transcript || "";

    try {
      const response = await api.post('/vision/critique-diagram', {
        session_id: sessionId,
        question_id: currentQuestion?.id,
        question_text: currentQuestion?.question,
        interview_type: currentQuestion?.interview_type || 'system_design',
        image_base64: latestScreenshot,
        capture_method: 'manual',
        transcript: currentTranscript,
      });

      setDiagramAnalysis(response.data);
      console.log("Diagram analysis:", response.data);

      const history = diagramHistoryRef.current.get(currentQuestionIndex);
      if (history && history.length > 0) {
        history[history.length - 1].analysis = response.data;
      }

    } catch (error: any) {
      console.error("Diagram analysis failed:", error);
      alert(`Analysis failed: ${error.response?.data?.detail || error.message}`);
    }
  }, [diagramCaptures, answers, currentQuestionIndex, sessionId, currentQuestion]);

  // Run code with test cases
  const handleRunCode = useCallback(async (code: string) => {
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
  }, [currentQuestion, selectedLanguage, currentQuestionIndex]);

  // Evaluate code comprehensively
  const handleEvaluateCode = useCallback(async () => {
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
      
      // FIX 3: Mark answer as started for OA questions after evaluation
      answerStartedRef.current = true;
      setAnswerStarted(true);

    } catch (error: any) {
      console.error("Code evaluation failed:", error);
      alert(`Evaluation failed: ${error.response?.data?.detail || error.message}`);
    }
  }, [currentQuestion, currentCode, selectedLanguage]);

  // FIX 3: Improved handleStartAnswer with ref for sync check
  const handleStartAnswer = useCallback(async () => {
    if (!currentQuestion) return;
    
    // Use ref for synchronous check (prevents race conditions)
    if (answerStartedRef.current) {
      console.log("Answer already started (ref check), skipping");
      return;
    }

    const questionType = currentQuestion.interview_type;

    // For technical/behavioral/system_design questions, require WebSocket connection
    if (questionType !== 'oa') {
      if (!isConnected) {
        console.log("WebSocket not connected, cannot start");
        return;
      }
      wsStartQuestion(currentQuestion.id, currentQuestion.question);
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // Set ref FIRST (synchronous) then state (async)
    answerStartedRef.current = true;
    
    metricsHistoryRef.current.delete(currentQuestionIndex);
    setCurrentMetrics(null);

    startAnswer();
    setAnswerStarted(true);
    setTimeRemaining(currentQuestion.expected_duration_mins * 60);
    setTimerRunning(true);
    setTimeUp(false);
    
    // Only record audio for non-OA questions
    if (questionType !== 'oa') {
      setIsRecording(true);
    }
    
    console.log("✅ handleStartAnswer completed");
  }, [currentQuestion, isConnected, wsStartQuestion, currentQuestionIndex, startAnswer]);

  // FIX 3: Improved handleStopAnswer with ref for sync check
  const handleStopAnswer = useCallback(() => {
    const questionType = currentQuestion?.interview_type;
    
    // For OA questions, just complete the answer
    if (questionType === 'oa') {
      answerStartedRef.current = true;
      setAnswerStarted(true);
      completeCurrentAnswer();
      return;
    }
    
    // Use ref for synchronous check
    if (!answerStartedRef.current) {
      console.log("Answer not started (ref check), nothing to stop");
      return;
    }
    
    console.log("⏹️ handleStopAnswer - stopping answer");
    
    // Send end signal to WebSocket
    wsEndQuestion();
    
    // Complete the answer
    completeCurrentAnswer();
    
    // Update states
    setTimerRunning(false);
    setIsRecording(false);
    // Don't reset answerStartedRef here - we want to know the answer was completed
  }, [currentQuestion, wsEndQuestion, completeCurrentAnswer]);

  // FIX 2: Polling instead of fixed wait for session data
  const handleSubmitInterview = useCallback(async () => {
    setSubmitting(true);
    try {
      // Signal session end
      wsEndSession();
      
      // Poll for session data with timeout
      let sessionData = null;
      let attempts = 0;
      const maxAttempts = 30; // Up to 30 seconds
      
      console.log("Waiting for session finalization...");
      
      while (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        attempts++;
        
        try {
          const sessionResponse = await api.get(`/speech/session/${sessionId}/for-evaluation`);
          sessionData = sessionResponse.data;
          
          // Check if session has meaningful data
          const questionCount = sessionData.questions?.length || 0;
          const hasTranscripts = sessionData.questions?.some(
            (q: any) => q.transcript && q.transcript.trim().length > 0
          );
          
          console.log(`Attempt ${attempts}: ${questionCount} questions, hasTranscripts: ${hasTranscripts}`);
          
          // Proceed if we have transcripts OR waited long enough (10s minimum)
          if (hasTranscripts || attempts >= 10) {
            console.log("Session data ready, proceeding to results");
            break;
          }
          
        } catch (err: any) {
          if (err.response?.status === 404) {
            console.log(`Session not ready yet (attempt ${attempts}/${maxAttempts})`);
            continue;
          }
          throw err;
        }
      }
      
      if (!sessionData) {
        throw new Error("Failed to retrieve session data after 30 seconds");
      }

      // Enrich with body language and code metrics
      if (sessionData.questions) {
        sessionData.questions = sessionData.questions.map((q: any, idx: number) => {
          const avgMetrics = getAverageMetrics(idx);
          const codeHistory = codeHistoryRef.current.get(idx);
          const diagramHistory = diagramHistoryRef.current.get(idx);
          
          return {
            ...q,
            body_language_metrics: avgMetrics || undefined,
            code_submissions: codeHistory || undefined,
            diagram_screenshots: diagramHistory || undefined,
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
  }, [wsEndSession, sessionId, getAverageMetrics, navigate, questions, answers]);

  const handleNextQuestion = useCallback(() => {
    if (isLastQuestion) {
      handleSubmitInterview();
    } else {
      nextQuestion();
      setTimeUp(false);
      // Reset for next question
      setAnswerStarted(false);
      answerStartedRef.current = false;
    }
  }, [isLastQuestion, nextQuestion, handleSubmitInterview]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const isOAQuestion = currentQuestion?.interview_type === 'oa';
  const isSystemDesignQuestion = currentQuestion?.interview_type === 'system_design';
  
  // FIX 3: Better condition for showing Next button (use ref as backup)
  const canProceedToNext = (answerStarted || answerStartedRef.current) && !isRecording;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[var(--background)]">
        <div className="bg-[var(--surface)] rounded-2xl shadow-[var(--shadow-lg)] p-8 max-w-md text-center">
          <div className="w-16 h-16 border-4 border-[var(--accent)] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-xl font-semibold text-[var(--text)] mb-2">Generating Questions...</p>
          <p className="text-sm text-[var(--text-muted)]">Analyzing job description with AI</p>
        </div>
      </div>
    );
  }

  if (!currentQuestion) {
    return <div className="flex items-center justify-center min-h-screen">No questions available</div>;
  }

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-[var(--border)] shadow-[var(--shadow-sm)]">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-bold text-[var(--text)]">Interview Assistant</h1>
              <span className="px-3 py-1 bg-[var(--accent-soft)] text-[var(--accent)] rounded-full text-sm font-semibold">
                Question {currentQuestionIndex + 1} of {questions.length}
              </span>
            </div>

            <div className="flex items-center gap-4">
              {!isOAQuestion && (
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "flex items-center gap-1.5 rounded-[var(--radius-sm)] px-2.5 py-1.5 text-sm",
                    isRecording ? "text-[var(--text)]" : "text-[var(--text-muted)]"
                  )}>
                    {isRecording
                      ? <Mic size={14} style={{ color: "var(--success)" }} />
                      : <MicOff size={14} />}
                    Mic
                  </div>
                  <div className="flex items-center gap-1.5 rounded-[var(--radius-sm)] px-2.5 py-1.5 text-sm text-[var(--text-muted)]">
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ background: isConnected ? "var(--success)" : "var(--error)" }}
                      aria-hidden
                    />
                    {isConnected ? "Connected" : "Offline"}
                  </div>
                </div>
              )}

              <div className={cn(
                "flex items-center gap-2 rounded-[var(--radius-sm)] border px-3 py-1.5 font-mono text-base font-semibold tabular-nums",
                timeRemaining < 60
                  ? "border-[var(--error)] text-[var(--error)]"
                  : "border-[var(--border)] text-[var(--text-secondary)]"
              )}>
                <Clock size={14} aria-hidden />
                {formatTime(timeRemaining)}
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="pt-24 pb-8 px-6 container mx-auto max-w-[1800px]">
        {currentQuestion?.is_fallback && (
          <div className="mb-5 flex items-start gap-2.5 rounded-[var(--radius-md)] border border-[var(--warning)] bg-[var(--warning-soft)] px-4 py-3">
            <AlertTriangle size={15} className="mt-0.5 shrink-0 text-[var(--warning)]" aria-hidden />
            <div>
              <p className="text-sm font-medium text-[var(--warning)]">Showing a standard practice question</p>
              <p className="mt-0.5 text-sm text-[var(--text-secondary)]">
                We couldn't generate questions tailored to this job description, so this is a
                generic one. Check that Ollama is running, then start a new interview.
              </p>
            </div>
          </div>
        )}
        <div className={cn(
          "grid gap-6",
          isOAQuestion ? "grid-cols-12" : isSystemDesignQuestion ? "grid-cols-12" : "grid-cols-12"
        )}>
          
          {/* Left Column - Camera/Test Results/Screen Capture Controls */}
          <div className={cn(
            "space-y-4",
            isOAQuestion ? "col-span-5" : isSystemDesignQuestion ? "col-span-4" : "col-span-4"
          )}>
            {isSystemDesignQuestion ? (
              <>
                <CameraPreview 
                  isRecording={isRecording}
                  onMetricsUpdate={handleMetricsUpdate}
                  enableMediaPipe={true}
                />

                <ScreenCaptureManager
                  sessionId={sessionId}
                  questionId={currentQuestion.id}
                  isRecording={isRecording}
                  captureInterval={10}
                  onCapture={handleDiagramCapture}
                  enableAutoCapture={true}
                />

                {diagramAnalysis && (
                  <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-sm)] p-4">
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text)]"><ScanLine size={14} className="text-[var(--text-muted)]" aria-hidden /> Diagram analysis</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--text-secondary)]">Completeness:</span>
                        <span className="font-bold text-[var(--accent)]">{formatScore(diagramAnalysis.completeness_score)}/100</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--text-secondary)]">Clarity:</span>
                        <span className="font-bold text-[var(--accent)]">{formatScore(diagramAnalysis.clarity_score)}/100</span>
                      </div>
                    </div>
                    <div className="mt-3 p-2 bg-[var(--accent-soft)] rounded text-xs text-[var(--text-secondary)] max-h-32 overflow-y-auto">
                      {diagramAnalysis.detailed_feedback}
                    </div>
                  </div>
                )}

                <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-md)] p-4">
                  <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-[var(--text)]"><Mic size={15} className="text-[var(--text-muted)]" aria-hidden /> Recording controls</h3>
                  <AudioRecorder
                    onStart={handleStartAnswer}
                    onStop={handleStopAnswer}
                    onAudioChunk={sendAudioChunk}
                    autoStop={timeUp}
                    disabled={!isConnected || submitting}
                  />
                  <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3">
                    <p className="text-sm text-[var(--text-secondary)]">
                      {!answerStartedRef.current 
                        ? "Click 'Start Answer' to begin. Explain your design while drawing."
                        : isRecording
                        ? "Explain your design — diagrams are captured every 10s."
                        : "Answer recorded. Click 'Next Question' to continue."}
                    </p>
                  </div>
                </div>

                {diagramCaptures.length > 0 && (
                  <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-sm)] p-4">
                    <button
                      onClick={handleAnalyzeDiagram}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-contrast)] transition-colors hover:bg-[var(--accent-hover)]"
                    >
                      <Search size={15} /> Analyze diagram
                    </button>
                    <p className="text-xs text-[var(--text-muted)] mt-2 text-center">
                      {diagramCaptures.length} diagram{diagramCaptures.length > 1 ? 's' : ''} captured
                    </p>
                  </div>
                )}
              </>
            ) : !isOAQuestion ? (
              <>
                <CameraPreview 
                  isRecording={isRecording}
                  onMetricsUpdate={handleMetricsUpdate}
                  enableMediaPipe={true}
                />

                {SHOW_LIVE_METRICS && currentMetrics && isRecording && (
                  <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-sm)] p-4 border-2 border-[var(--border)]">
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text)]"><LayoutGrid size={14} className="text-[var(--text-muted)]" aria-hidden /> Live metrics</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="flex items-center gap-1.5 text-[var(--text-secondary)]"><Eye size={13} className="text-[var(--text-muted)]" aria-hidden /> Eye contact</span>
                        <span className="font-bold text-[var(--accent)]">{currentMetrics.eye_contact_percentage}%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="flex items-center gap-1.5 text-[var(--text-secondary)]"><ScanLine size={13} className="text-[var(--text-muted)]" aria-hidden /> Posture</span>
                        <span className="font-bold text-[var(--accent)]">{formatScore(currentMetrics.posture_score)}/100</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="flex items-center gap-1.5 text-[var(--text-secondary)]"><Hand size={13} className="text-[var(--text-muted)]" aria-hidden /> Gestures</span>
                        <span className="font-bold text-[var(--accent)]">{currentMetrics.gesture_frequency.toFixed(1)}/s</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="flex items-center gap-1.5 text-[var(--text-secondary)]"><Smile size={13} className="text-[var(--text-muted)]" aria-hidden /> Nods</span>
                        <span className="font-bold text-[var(--accent)]">{currentMetrics.facial_confidence_signals.nod_count}</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-md)] p-4">
                  <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-[var(--text)]"><Mic size={15} className="text-[var(--text-muted)]" aria-hidden /> Recording controls</h3>
                  <AudioRecorder
                    onStart={handleStartAnswer}
                    onStop={handleStopAnswer}
                    onAudioChunk={sendAudioChunk}
                    autoStop={timeUp}
                    disabled={!isConnected || submitting}
                  />
                  <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3">
                    <p className="text-sm text-[var(--text-secondary)]">
                      {!answerStartedRef.current 
                        ? "Click 'Start Answer' when ready."
                        : isRecording
                        ? "Speak clearly. Click 'Stop Answer' when done."
                        : "Answer recorded. Click 'Next Question' to continue."}
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <>
                <TestResults results={testResults} loading={isRunningCode} />

                {codeEvaluation && (
                  <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-sm)] p-4">
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text)]"><Target size={14} className="text-[var(--text-muted)]" aria-hidden /> Code evaluation</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--text)] font-semibold">Correctness:</span>
                        <span className="font-bold text-lg" style={{ color: getScoreTone(codeEvaluation.correctness_score) }}>
                          {formatScore(codeEvaluation.correctness_score)}/100
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--text-secondary)]">Code Quality:</span>
                        <span className="font-bold text-[var(--accent)]">{formatScore(codeEvaluation.code_quality_score)}/100</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--text-secondary)]">Complexity:</span>
                        <span className="font-bold text-[var(--accent)]">{formatScore(codeEvaluation.complexity_score)}/100</span>
                      </div>
                      <p className="pt-2 border-t border-[var(--border)] text-xs text-[var(--text-muted)]">
                        Correctness comes from the tests. Quality and complexity are shown next to
                        it and never raise it.
                      </p>
                    </div>
                    <div className="mt-3 p-2 bg-[var(--accent-soft)] rounded text-xs text-[var(--text-secondary)]">
                      {codeEvaluation.feedback}
                    </div>
                  </div>
                )}

                {availableLanguages.length > 0 && (
                  <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-sm)] p-4">
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--text)]"><Code2 size={14} className="text-[var(--text-muted)]" aria-hidden /> Language</h4>
                    <Select
                      aria-label="Programming language"
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                    >
                      {availableLanguages.map((lang) => (
                        <option key={lang} value={lang}>
                          {lang.toUpperCase()}
                        </option>
                      ))}
                    </Select>
                  </div>
                )}

                <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-sm)] p-4 space-y-2">
                  <button
                    onClick={handleEvaluateCode}
                    disabled={!testResults || isRunningCode}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-contrast)] transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-50"
                  >
                    <Target size={15} /> Evaluate solution
                  </button>
                  {(canProceedToNext || codeEvaluation) && (
                    <button
                      onClick={handleNextQuestion}
                      disabled={submitting}
                      className="w-full rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-contrast)] transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-50"
                    >
                      {submitting ? "Submitting..." : isLastQuestion ? "Submit Interview →" : "Next Question →"}
                    </button>
                  )}
                </div>
              </>
            )}

            {/* Progress */}
            <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-md)] p-4">
              <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-[var(--text)]"><ListChecks size={15} className="text-[var(--text-muted)]" aria-hidden /> Progress</h3>
              <div className="space-y-2">
                {questions.map((q, idx) => {
                  const answer = answers[idx];
                  const isCurrent = idx === currentQuestionIndex;
                  const isComplete = answer?.endedAt;

                  return (
                    <div
                      key={idx}
                      className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                        isCurrent
                          ? "border border-[var(--accent)] bg-[var(--accent-soft)]"
                          : "border border-transparent bg-[var(--surface-2)]"
                      }`}
                    >
                      <div className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                        isComplete
                          ? "bg-[var(--success-soft)] text-[var(--success)]"
                          : isCurrent
                          ? "bg-[var(--accent)] text-[var(--accent-contrast)]"
                          : "bg-[var(--surface-3)] text-[var(--text-muted)]"
                      }`}>
                        {isComplete ? <Check size={14} aria-hidden /> : idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium truncate ${
                          isCurrent ? "text-[var(--text)]" : "text-[var(--text-secondary)]"
                        }`}>
                          {q.question.slice(0, 40)}...
                        </p>
                        {answer?.transcript && (
                          <p className="text-xs text-[var(--text-muted)]">
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

          {/* Right Column - Question/Code Editor/Diagram Canvas */}
          <div className={cn(
            "",
            isOAQuestion ? "col-span-7" : isSystemDesignQuestion ? "col-span-8" : "col-span-8"
          )}>
            <div className="bg-[var(--surface)] rounded-xl shadow-[var(--shadow-md)] overflow-hidden" style={{ minHeight: '600px' }}>
              {isOAQuestion ? (
                <div className="flex flex-col">
                  <div className="p-6 border-b border-[var(--border)]">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--accent-soft)] px-2.5 py-1 text-sm font-medium text-[var(--accent)]">
                        <Code2 size={13} aria-hidden /> Coding challenge
                      </span>
                      <span className={`rounded-full px-2.5 py-1 text-sm font-medium capitalize ${
                        currentQuestion.difficulty === "easy" ? "bg-[var(--success-soft)] text-[var(--success)]" :
                        currentQuestion.difficulty === "hard" ? "bg-[var(--error-soft)] text-[var(--error)]" :
                        "bg-[var(--warning-soft)] text-[var(--warning)]"
                      }`}>
                        {currentQuestion.difficulty}
                      </span>
                      <span className="flex items-center gap-1.5 text-sm text-[var(--text-muted)]">
                        <Clock size={13} aria-hidden /> {currentQuestion.expected_duration_mins} min
                      </span>
                      <button
                        type="button"
                        onClick={() => setStatementCollapsed((collapsed) => !collapsed)}
                        aria-expanded={!statementCollapsed}
                        title={statementCollapsed ? "Show the full problem statement" : "Collapse the problem statement"}
                        className="ml-auto px-3 py-1 rounded-full text-sm font-semibold text-[var(--text-secondary)] hover:text-[var(--text)] hover:bg-[var(--surface-3)] transition-colors"
                      >
                        {statementCollapsed ? "⌄ Expand problem" : "⌃ Collapse problem"}
                      </button>
                    </div>
                    <div className={cn(
                      "prose prose-sm max-w-none",
                      statementCollapsed && "max-h-40 overflow-y-auto"
                    )}>
                      <pre className="whitespace-pre-wrap break-words text-sm text-[var(--text)] font-sans leading-relaxed">
                        {currentQuestion.question}
                      </pre>
                    </div>
                  </div>

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
              ) : isSystemDesignQuestion ? (
                <div className="h-full flex flex-col">
                  <div className="p-6 border-b border-[var(--border)]">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--accent-soft)] px-2.5 py-1 text-sm font-medium text-[var(--accent)]">
                        <Network size={13} aria-hidden /> System design
                      </span>
                      <span className={`rounded-full px-2.5 py-1 text-sm font-medium capitalize ${
                        currentQuestion.difficulty === "easy" ? "bg-[var(--success-soft)] text-[var(--success)]" :
                        currentQuestion.difficulty === "hard" ? "bg-[var(--error-soft)] text-[var(--error)]" :
                        "bg-[var(--warning-soft)] text-[var(--warning)]"
                      }`}>
                        {currentQuestion.difficulty}
                      </span>
                      <span className="flex items-center gap-1.5 text-sm text-[var(--text-muted)]">
                        <Clock size={13} aria-hidden /> {currentQuestion.expected_duration_mins} min
                      </span>
                    </div>
                    <p className="text-lg text-[var(--text)] font-semibold leading-relaxed">
                      {currentQuestion.question}
                    </p>
                  </div>

                  <div className="flex-1">
                    <DiagramCanvas
                      onCapture={handleDiagramCapture}
                      autoCapture={false}
                      isRecording={isRecording}
                    />
                  </div>
                </div>
              ) : (
                <div className="p-8">
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="px-3 py-1 bg-[var(--accent-soft)] text-[var(--accent)] rounded-full text-sm font-semibold capitalize">
                        {currentQuestion.interview_type}
                      </span>
                      <span className={`rounded-full px-2.5 py-1 text-sm font-medium capitalize ${
                        currentQuestion.difficulty === "easy" ? "bg-[var(--success-soft)] text-[var(--success)]" :
                        currentQuestion.difficulty === "hard" ? "bg-[var(--error-soft)] text-[var(--error)]" :
                        "bg-[var(--warning-soft)] text-[var(--warning)]"
                      }`}>
                        {currentQuestion.difficulty}
                      </span>
                      <span className="flex items-center gap-1.5 text-sm text-[var(--text-muted)]">
                        <Clock size={13} aria-hidden /> {currentQuestion.expected_duration_mins} min
                      </span>
                    </div>
                    
                    {currentQuestion.skill_tags.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-4">
                        {currentQuestion.skill_tags.map((tag, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 bg-[var(--surface-3)] text-[var(--text)] rounded-lg text-xs font-semibold"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="mb-8">
                    <p className="text-2xl leading-relaxed text-[var(--text)] font-semibold">
                      {currentQuestion.question}
                    </p>
                  </div>

                  {timeUp && (
                    <div className="mb-6 flex items-center gap-2.5 rounded-[var(--radius-md)] border border-[var(--error)] bg-[var(--error-soft)] px-4 py-3">
                      <AlertTriangle size={16} className="shrink-0 text-[var(--error)]" aria-hidden />
                      <p className="text-sm font-medium text-[var(--error)]">
                        Time's up — please conclude your answer.
                      </p>
                    </div>
                  )}

                  {currentQuestion.evaluation_criteria && currentQuestion.evaluation_criteria.length > 0 && (
                    <div className="p-4 bg-[var(--accent-soft)] rounded-xl border border-[var(--border)]">
                      <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-[var(--text)]">
                        <Lightbulb size={14} className="text-[var(--text-muted)]" aria-hidden /> Evaluation focus
                      </p>
                      <ul className="text-sm text-[var(--accent)] space-y-1">
                        {currentQuestion.evaluation_criteria.map((criterion: string, i: number) => (
                          <li key={i} className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]"></div>
                            {criterion.replace(/_/g, " ")}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            {!isOAQuestion && (
              <div className="flex items-center justify-between mt-6">
                <button
                  onClick={() => navigate("/")}
                  disabled={isRecording || submitting}
                  className="px-6 py-3 text-[var(--text-muted)] hover:text-[var(--text)] font-medium disabled:opacity-50 transition-colors"
                >
                  ← Exit Interview
                </button>

                {canProceedToNext && (
                  <button
                    onClick={handleNextQuestion}
                    disabled={isRecording || submitting}
                    className="px-8 py-4 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-lg font-semibold rounded-xl shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transform hover:scale-105 transition-all disabled:opacity-50 disabled:transform-none disabled:cursor-not-allowed"
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