/**
 * AuthPage — login + signup (candidate / employer).
 * Location: frontend/src/pages/AuthPage.tsx
 *
 * Split layout: a focused form panel on a quiet canvas with a subtle grid
 * backdrop and a brand/feature rail on wider screens. Fully themed.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Briefcase, User } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import type { UserRole } from "../api/platform";
import { Button, Input, Label } from "../ui";
import { BrandMark } from "../ui/AppShell";
import ThemeToggle from "../theme/ThemeToggle";

type Mode = "login" | "signup";

export default function AuthPage({ initialMode = "login" }: { initialMode?: Mode }) {
  const navigate = useNavigate();
  const { login, signup } = useAuth();

  const [mode, setMode] = useState<Mode>(initialMode);
  const [role, setRole] = useState<UserRole>("candidate");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const routeForRole = (r: UserRole) => (r === "candidate" ? "/workspace" : "/employer");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user =
        mode === "login"
          ? await login(email || username, password)
          : await signup({
              email,
              username,
              password,
              role,
              organization_name: role === "employer_admin" ? orgName : undefined,
            });
      navigate(routeForRole(user.role));
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--background)]">
      <div className="bg-grid pointer-events-none absolute inset-0 opacity-60" />

      <div className="absolute right-5 top-5 z-10">
        <ThemeToggle />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-6xl items-center justify-center gap-16 px-6 lg:justify-between">
        {/* Left rail — brand & value (desktop only) */}
        <div className="hidden max-w-md flex-1 lg:block animate-fade-in">
          <button onClick={() => navigate("/")} className="mb-8 flex items-center gap-2.5">
            <BrandMark size={28} />
            <span className="text-lg font-semibold tracking-tight text-[var(--text)]">
              Interview Assistant
            </span>
          </button>
          <h1 className="text-3xl font-semibold leading-tight tracking-tight text-[var(--text)]">
            Assessments that measure what actually matters.
          </h1>
          <p className="mt-4 text-md leading-relaxed text-[var(--text-secondary)]">
            Build proctored interviews, run candidates through a secure workspace, and review
            structured scoring — or just practice with unlimited AI mock interviews.
          </p>
          <ul className="mt-8 space-y-3">
            {[
              "Multi-modal scoring: speech, code, body language",
              "Proctored, confidential candidate workspace",
              "Recruiter decision panel with auto-comms",
            ].map((f) => (
              <li key={f} className="flex items-center gap-3 text-sm text-[var(--text-secondary)]">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)] text-xs">
                  ✓
                </span>
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* Form panel */}
        <div className="w-full max-w-md flex-1 animate-scale-in">
          <div className="rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] p-8 shadow-[var(--shadow-lg)]">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold tracking-tight text-[var(--text)]">
                {mode === "login" ? "Welcome back" : "Create your account"}
              </h2>
              <p className="mt-1 text-sm text-[var(--text-muted)]">
                {mode === "login"
                  ? "Sign in to continue to your workspace"
                  : "Get started as a candidate or an employer"}
              </p>
            </div>

            {mode === "signup" && (
              <div className="mb-5 grid grid-cols-2 gap-2">
                {([
                  { r: "candidate", label: "Candidate", icon: <User size={15} /> },
                  { r: "employer_admin", label: "Employer", icon: <Briefcase size={15} /> },
                ] as const).map((opt) => (
                  <button
                    key={opt.r}
                    type="button"
                    onClick={() => setRole(opt.r)}
                    className={`flex items-center justify-center gap-2 rounded-[var(--radius-sm)] border px-3 py-2.5 text-sm font-medium transition-all ${
                      role === opt.r
                        ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-muted)] hover:border-[var(--border-strong)] hover:text-[var(--text)]"
                    }`}
                  >
                    {opt.icon}
                    {opt.label}
                  </button>
                ))}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Email</Label>
                <Input
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required={mode === "signup"}
                  autoComplete="email"
                />
              </div>

              {mode === "signup" && (
                <div>
                  <Label>Username</Label>
                  <Input
                    placeholder="janedoe"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    autoComplete="username"
                  />
                </div>
              )}

              {mode === "signup" && role === "employer_admin" && (
                <div>
                  <Label>Organization</Label>
                  <Input
                    placeholder="Acme Inc."
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    required
                  />
                </div>
              )}

              <div>
                <Label>{mode === "login" ? "Email or username" : "Password"}</Label>
                <Input
                  type={mode === "login" ? "text" : "password"}
                  placeholder={mode === "login" ? "you@company.com" : "At least 8 characters"}
                  value={mode === "login" ? email : password}
                  onChange={(e) => (mode === "login" ? setEmail(e.target.value) : setPassword(e.target.value))}
                  required
                  minLength={mode === "login" ? undefined : 8}
                />
              </div>

              {mode === "login" && (
                <div>
                  <Label>Password</Label>
                  <Input
                    type="password"
                    placeholder="Your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                  />
                </div>
              )}

              {error && (
                <p className="rounded-[var(--radius-sm)] bg-[var(--error-soft)] px-3 py-2 text-sm text-[var(--error)]">
                  {error}
                </p>
              )}

              <Button type="submit" loading={busy} className="w-full" size="lg" rightIcon={<ArrowRight size={16} />}>
                {mode === "login" ? "Sign in" : "Create account"}
              </Button>
            </form>

            <p className="mt-6 text-center text-sm text-[var(--text-muted)]">
              {mode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
              <button
                onClick={() => {
                  setMode(mode === "login" ? "signup" : "login");
                  setError("");
                }}
                className="font-medium text-[var(--link)] transition-colors hover:text-[var(--accent-hover)]"
              >
                {mode === "login" ? "Sign up" : "Sign in"}
              </button>
            </p>
          </div>

          <p className="mt-5 text-center text-sm text-[var(--text-muted)]">
            or{" "}
            <button onClick={() => navigate("/")} className="font-medium text-[var(--text-secondary)] underline-offset-4 hover:underline">
              continue with a free mock interview
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
