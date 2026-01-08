/**
 * Professional Home Page - Simplified (No ShadCN dependency)
 * Location: frontend/src/pages/HomePage.tsx
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function HomePage() {
  const navigate = useNavigate();
  const [jobDescription, setJobDescription] = useState("");
  const [interviewType, setInterviewType] = useState("technical");
  const [difficulty, setDifficulty] = useState("medium");
  const [numQuestions, setNumQuestions] = useState(3);

  // Calculate total duration based on difficulty and number of questions
  const getDurationPerQuestion = () => {
    switch (difficulty) {
      case "easy": return 5;
      case "medium": return 7;
      case "hard": return 9;
      default: return 7;
    }
  };

  const totalDuration = numQuestions * getDurationPerQuestion();

  const handleStartInterview = () => {
    if (!jobDescription.trim()) {
      alert("Please enter a job description");
      return;
    }

    navigate("/interview", {
      state: {
        jobDescription,
        interviewType,
        difficulty,
        numQuestions,
      },
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 relative overflow-hidden">
      {/* Animated background blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-blue-400/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-400/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="container mx-auto px-4 py-12 relative z-10 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-6xl font-bold text-gradient mb-4">
            Interview Assistant
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-6">
            AI-powered mock interview coaching with real-time multimodal feedback
          </p>
          <div className="flex items-center justify-center gap-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-green-100 text-green-800">
              ✓ Speech Analysis
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-blue-100 text-blue-800">
              ✓ AI Evaluation
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-yellow-100 text-yellow-800">
              🚧 Body Language (Coming Soon)
            </span>
          </div>
        </div>

        {/* Main Card */}
        <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-2xl p-8 border border-gray-200">
          <h2 className="text-3xl font-bold mb-2 text-gray-900">Configure Your Practice Interview</h2>
          <p className="text-gray-700 mb-8">Paste a job description and we'll generate tailored questions</p>

          {/* Job Description */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Job Description *
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the job description here...

Example: Senior Python Developer with 5+ years experience in FastAPI, PostgreSQL, and AWS. Strong system design skills required."
              className="w-full h-40 px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none transition-all shadow-sm hover:shadow-md font-mono text-sm text-gray-900 placeholder:text-gray-500"
              required
            />
            <p className="mt-2 text-sm text-gray-500">
              ✨ AI will extract skills and generate relevant questions
            </p>
          </div>

          {/* Interview Type */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              Interview Type
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { value: "technical", label: "Technical", emoji: "💻" },
                { value: "system_design", label: "System Design", emoji: "🏗️" },
                { value: "behavioral", label: "Behavioral", emoji: "💬" },
                { value: "oa", label: "Coding (OA)", emoji: "⌨️" },
              ].map((type) => (
                <button
                  key={type.value}
                  onClick={() => setInterviewType(type.value)}
                  className={`relative p-4 rounded-xl border-2 transition-all hover:scale-105 ${
                    interviewType === type.value
                      ? "border-blue-500 bg-blue-50 shadow-lg"
                      : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-md"
                  }`}
                >
                  <div className="text-3xl mb-2">{type.emoji}</div>
                  <div className={`text-sm font-medium ${
                    interviewType === type.value ? "text-blue-900" : "text-gray-700"
                  }`}>
                    {type.label}
                  </div>
                  {interviewType === type.value && (
                    <div className="absolute -top-2 -right-2 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs">✓</span>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Difficulty */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              Difficulty Level
            </label>
            <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
              {["easy", "medium", "hard"].map((level) => (
                <button
                  key={level}
                  onClick={() => setDifficulty(level)}
                  className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-all ${
                    difficulty === level
                      ? "bg-white text-blue-700 shadow-md"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Number of Questions */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-semibold text-gray-700">
                Number of Questions
              </label>
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg">
                <span className="text-3xl font-bold text-white">{numQuestions}</span>
              </div>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-2 px-1">
              <span>Quick</span>
              <span>Standard</span>
              <span>Comprehensive</span>
            </div>
          </div>

          {/* Start Button */}
          <div className="pt-4">
            <button
              onClick={handleStartInterview}
              disabled={!jobDescription.trim()}
              className="w-full py-4 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-lg font-semibold rounded-xl shadow-xl hover:shadow-2xl transform hover:scale-[1.02] transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              ✨ Start Practice Interview
            </button>
            <p className="text-center text-sm text-gray-600 mt-3 font-medium">
              Estimated duration: {totalDuration} minutes ({numQuestions} question{numQuestions > 1 ? 's' : ''} × {getDurationPerQuestion()} min each)
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="max-w-5xl mx-auto mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              emoji: "🎤",
              title: "Speech Analysis",
              description: "Real-time analysis of pace, clarity, filler words, and confidence"
            },
            {
              emoji: "🧠",
              title: "AI Evaluation",
              description: "Technical accuracy, problem-solving approach, and communication skills"
            },
            {
              emoji: "📊",
              title: "Detailed Feedback",
              description: "Comprehensive dashboard with scores, metrics, and improvement tips"
            }
          ].map((feature, idx) => (
            <div key={idx} className="group relative">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-400 rounded-2xl blur-xl opacity-20 group-hover:opacity-30 transition-opacity"></div>
              <div className="relative h-full bg-white rounded-2xl p-6 shadow-xl hover:shadow-2xl transition-all transform hover:scale-105">
                <div className="text-5xl mb-4 text-center">{feature.emoji}</div>
                <h3 className="text-xl font-bold mb-2 text-center text-gray-900">{feature.title}</h3>
                <p className="text-gray-700 text-sm text-center leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-20 text-center text-sm text-gray-500">
          <p>Built with FastAPI, Whisper, Ollama, and React</p>
          <p className="mt-1">© 2026 Interview Assistant</p>
        </div>
      </div>
    </div>
  );
}