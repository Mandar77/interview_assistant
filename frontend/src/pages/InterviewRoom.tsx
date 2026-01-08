/**
 * Professional Interview Room - Simplified (No ShadCN)
 * Location: frontend/src/pages/InterviewRoom.tsx
 */

import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useInterviewSession } from "../hooks/useInterviewSession";
import { useSpeechWebSocket } from "../hooks/useSpeechWebSocket";
import { useMediaStream } from "../hooks/useMediaStream";
import { api } from "../api/client";
import AudioRecorder from "../components/AudioRecorder";

// Inline cn utility
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

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

  // Camera feed
  const { videoRef, stream, error: cameraError, isReady } = useMediaStream();

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

        // Update questions with correct duration based on difficulty
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

  const handleStartAnswer = async () => {
    if (!currentQuestion || isRecording || !isConnected) return;

    wsStartQuestion(currentQuestion.id, currentQuestion.question);
    await new Promise((resolve) => setTimeout(resolve, 100));

    startAnswer();
    setTimeRemaining(currentQuestion.expected_duration_mins * 60);
    setTimerRunning(true);
    setTimeUp(false);
    setIsRecording(true);
  };

  const handleStopAnswer = () => {
    if (!isRecording) return;
    wsEndQuestion();
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
      navigate("/results", {
        state: {
          sessionId,
          sessionData: sessionResponse.data,
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
      {/* Fixed Header */}
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
              {/* Connection Status */}
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${
                isConnected ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
                }`}></div>
                {isConnected ? "Connected" : "Offline"}
              </div>

              {/* Timer */}
              <div className={`px-4 py-2 rounded-lg font-mono text-lg font-bold ${
                timeRemaining < 60
                  ? "bg-red-100 text-red-700 animate-pulse"
                  : "bg-blue-100 text-blue-700"
              }`}>
                ⏱️ {formatTime(timeRemaining)}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - 2 Column */}
      <div className="pt-24 pb-8 px-6 container mx-auto">
        <div className="grid grid-cols-12 gap-6">
          
          {/* LEFT - Media & Controls */}
          <div className="col-span-4 space-y-4">
            {/* Camera Preview - Live Feed */}
            <div className="bg-white rounded-xl shadow-xl p-4">
              <h3 className="text-lg font-bold mb-3 flex items-center gap-2 text-gray-900">
                📹 Video Feed
              </h3>
              <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden relative">
                {/* Live video feed */}
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
                
                {/* Loading state */}
                {!isReady && !cameraError && (
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
                    <div className="text-center text-white">
                      <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                      <p className="text-sm font-semibold">Initializing camera...</p>
                    </div>
                  </div>
                )}
                
                {/* Camera error overlay */}
                {cameraError && (
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-900 backdrop-blur-sm">
                    <div className="text-center text-white p-6">
                      <div className="text-5xl mb-3">⚠️</div>
                      <p className="text-sm font-semibold mb-2">{cameraError}</p>
                      <p className="text-xs text-gray-300">Check browser permissions and try refreshing</p>
                    </div>
                  </div>
                )}
                
                {/* 
                  TODO for Anjali: MediaPipe overlay layer goes here
                  Add a canvas element positioned absolutely over the video
                  to draw body language landmarks, eye tracking, etc.
                  
                  Example:
                  <canvas 
                    ref={canvasRef}
                    className="absolute inset-0 w-full h-full"
                  />
                */}
                
                {/* Recording indicator */}
                {isRecording && isReady && (
                  <div className="absolute top-4 right-4 flex items-center gap-2 bg-red-600 text-white px-3 py-1.5 rounded-full text-sm font-semibold shadow-lg">
                    <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
                    REC
                  </div>
                )}

                {/* Camera status indicator */}
                {isReady && !cameraError && (
                  <div className="absolute bottom-4 left-4 flex items-center gap-2 bg-green-600/90 text-white px-3 py-1.5 rounded-full text-xs font-semibold">
                    <div className="w-2 h-2 bg-white rounded-full" />
                    Camera Active
                  </div>
                )}
              </div>
            </div>

            {/* Recording Controls */}
            <div className="bg-white rounded-xl shadow-xl p-4">
              <h3 className="text-lg font-bold mb-3">🎙️ Recording Controls</h3>
              <AudioRecorder
                onStart={handleStartAnswer}
                onStop={handleStopAnswer}
                onAudioChunk={sendAudioChunk}
                autoStop={timeUp}
                disabled={!isConnected || submitting}
              />
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-900">
                  {!isRecording 
                    ? "💡 Click 'Start Answer' when ready"
                    : "🎤 Speak clearly. Click 'Stop Answer' when done."}
                </p>
              </div>
            </div>

            {/* Progress */}
            <div className="bg-white rounded-xl shadow-xl p-4">
              <h3 className="text-lg font-bold mb-3">📋 Progress</h3>
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

          {/* RIGHT - Question */}
          <div className="col-span-8">
            <div className="bg-white rounded-xl shadow-2xl p-8 min-h-[600px]">
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
                <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
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

            {/* Navigation */}
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
          </div>
        </div>
      </div>
    </div>
  );
}