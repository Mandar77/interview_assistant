/**
 * HomePage — landing + mock interview configuration.
 * Location: frontend/src/pages/HomePage.tsx
 *
 * Public entry. A focused configurator on a quiet canvas with a subtle grid
 * hero. Anonymous flow (no auth required); links into the platform for accounts.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  AudioLines,
  BrainCircuit,
  Code2,
  LayoutGrid,
  MessagesSquare,
  Terminal,
  Sparkles,
} from "lucide-react";
import { Button, Textarea } from "../ui";
import { BrandMark } from "../ui/AppShell";
import ThemeToggle from "../theme/ThemeToggle";

const INTERVIEW_TYPES = [
  { value: "technical", label: "Technical", icon: BrainCircuit },
  { value: "system_design", label: "System Design", icon: LayoutGrid },
  { value: "behavioral", label: "Behavioral", icon: MessagesSquare },
  { value: "oa", label: "Coding (OA)", icon: Terminal },
] as const;

const FEATURES = [
  { icon: AudioLines, title: "Speech analysis", desc: "Pace, clarity, filler words, and confidence — measured in real time." },
  { icon: BrainCircuit, title: "AI evaluation", desc: "Technical accuracy, problem-solving, and communication, scored on a rubric." },
  { icon: Code2, title: "Detailed feedback", desc: "A structured report with per-category scores and concrete next steps." },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [jobDescription, setJobDescription] = useState("");
  const [interviewType, setInterviewType] = useState("technical");
  const [difficulty, setDifficulty] = useState("medium");
  const [numQuestions, setNumQuestions] = useState(3);
  const [sessionCount, setSessionCount] = useState(0);

  useEffect(() => {
    const stored = localStorage.getItem("interview_sessions");
    if (stored) {
      try {
        setSessionCount(JSON.parse(stored).length);
      } catch {
        setSessionCount(0);
      }
    }
  }, []);

  const getDurationPerQuestion = () =>
    difficulty === "easy" ? 5 : difficulty === "hard" ? 9 : 7;
  const totalDuration = numQuestions * getDurationPerQuestion();

  const handleStartInterview = () => {
    if (!jobDescription.trim()) return;
    navigate("/interview", {
      state: { jobDescription, interviewType, difficulty, numQuestions },
    });
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--background)]">
      {/* Hero backdrop */}
      <div className="bg-grid pointer-events-none absolute inset-x-0 top-0 h-[520px] opacity-70" />

      {/* Top bar */}
      <header className="relative z-10 mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <div className="flex items-center gap-2.5">
          <BrandMark size={26} />
          <span className="text-base font-semibold tracking-tight text-[var(--text)]">
            Interview Assistant
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button variant="ghost" size="sm" onClick={() => navigate("/login")}>
            Log in
          </Button>
          <Button size="sm" onClick={() => navigate("/signup")} rightIcon={<ArrowRight size={15} />}>
            Get started
          </Button>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-6 pb-24">
        {/* Hero copy */}
        <section className="mx-auto max-w-2xl pt-16 text-center animate-slide-up">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)] shadow-[var(--shadow-sm)]">
            <Sparkles size={13} className="text-[var(--accent)]" />
            Multi-modal AI interview coaching
          </span>
          <h1 className="mt-6 text-4xl font-semibold leading-[1.08] tracking-tight text-[var(--text)] sm:text-5xl">
            Practice interviews that
            <br />
            <span className="text-gradient">feel completely real.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-md leading-relaxed text-[var(--text-secondary)]">
            Paste a job description and we generate a tailored mock interview — then analyze your
            speech, code, and delivery with the same engine employers use to assess candidates.
          </p>
        </section>

        {/* Returning user */}
        {sessionCount > 0 && (
          <div className="mx-auto mt-8 max-w-2xl animate-fade-in">
            <button
              onClick={() => navigate("/progress")}
              className="flex w-full items-center justify-between rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] px-5 py-3.5 text-left shadow-[var(--shadow-sm)] transition-all hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-md)]"
            >
              <div>
                <p className="text-sm font-medium text-[var(--text)]">Welcome back 👋</p>
                <p className="text-sm text-[var(--text-muted)]">
                  You've completed {sessionCount} practice session{sessionCount > 1 ? "s" : ""}
                </p>
              </div>
              <span className="flex items-center gap-1.5 text-sm font-medium text-[var(--accent)]">
                View progress <ArrowRight size={15} />
              </span>
            </button>
          </div>
        )}

        {/* Configurator */}
        <section className="mx-auto mt-10 max-w-2xl rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] p-7 shadow-[var(--shadow-lg)] animate-scale-in">
          <h2 className="text-xl font-semibold tracking-tight text-[var(--text)]">
            Configure your interview
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            We'll extract the skills and generate matching questions.
          </p>

          {/* JD */}
          <div className="mt-6">
            <label className="mb-1.5 block text-sm font-medium text-[var(--text-secondary)]">
              Job description
            </label>
            <Textarea
              rows={5}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the role description… e.g. Senior Python engineer with FastAPI, PostgreSQL, AWS, and strong system-design skills."
              className="font-mono text-sm"
            />
          </div>

          {/* Type */}
          <div className="mt-6">
            <label className="mb-2 block text-sm font-medium text-[var(--text-secondary)]">
              Interview type
            </label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {INTERVIEW_TYPES.map((t) => {
                const active = interviewType === t.value;
                const Icon = t.icon;
                return (
                  <button
                    key={t.value}
                    onClick={() => setInterviewType(t.value)}
                    className={`flex flex-col items-center gap-2 rounded-[var(--radius-md)] border px-3 py-4 transition-all ${
                      active
                        ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-muted)] hover:border-[var(--border-strong)] hover:text-[var(--text)]"
                    }`}
                  >
                    <Icon size={20} strokeWidth={1.75} />
                    <span className="text-sm font-medium">{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Difficulty + count */}
          <div className="mt-6 grid gap-6 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-[var(--text-secondary)]">
                Difficulty
              </label>
              <div className="flex gap-1 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-1">
                {["easy", "medium", "hard"].map((level) => (
                  <button
                    key={level}
                    onClick={() => setDifficulty(level)}
                    className={`flex-1 rounded-[var(--radius-sm)] py-1.5 text-sm font-medium capitalize transition-all ${
                      difficulty === level
                        ? "bg-[var(--surface)] text-[var(--text)] shadow-[var(--shadow-sm)]"
                        : "text-[var(--text-muted)] hover:text-[var(--text)]"
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Questions</label>
                <span className="font-mono text-sm font-semibold text-[var(--accent)]">{numQuestions}</span>
              </div>
              <input
                type="range"
                min={1}
                max={5}
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
                className="mt-2.5 w-full cursor-pointer accent-[var(--accent)]"
              />
              <div className="mt-1.5 flex justify-between text-2xs text-[var(--text-muted)]">
                <span>Quick</span>
                <span>Standard</span>
                <span>Deep</span>
              </div>
            </div>
          </div>

          <div className="mt-7">
            <Button
              size="lg"
              className="w-full"
              onClick={handleStartInterview}
              disabled={!jobDescription.trim()}
              rightIcon={<ArrowRight size={17} />}
            >
              Start practice interview
            </Button>
            <p className="mt-3 text-center text-sm text-[var(--text-muted)]">
              ≈ {totalDuration} min · {numQuestions} question{numQuestions > 1 ? "s" : ""} ·{" "}
              {getDurationPerQuestion()} min each
            </p>
          </div>
        </section>

        {/* Features */}
        <section className="mx-auto mt-20 grid max-w-4xl gap-4 sm:grid-cols-3 stagger">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)] transition-all hover:-translate-y-0.5 hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-md)]"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--accent-soft)] text-[var(--accent)]">
                  <Icon size={18} strokeWidth={1.75} />
                </div>
                <h3 className="mt-4 text-base font-semibold text-[var(--text)]">{f.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-[var(--text-muted)]">{f.desc}</p>
              </div>
            );
          })}
        </section>

        <footer className="mt-20 text-center text-sm text-[var(--text-muted)]">
          Built with FastAPI, Whisper, Ollama & React · © 2026 Interview Assistant
        </footer>
      </main>
    </div>
  );
}
