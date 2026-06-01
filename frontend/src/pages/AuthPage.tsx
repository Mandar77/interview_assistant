/**
 * AuthPage - login + signup (candidate / employer) (Phase 9).
 * Location: frontend/src/pages/AuthPage.tsx
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import type { UserRole } from "../api/platform";

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

  const routeForRole = (r: UserRole) =>
    r === "candidate" ? "/workspace" : "/employer";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") {
        const user = await login(email || username, password);
        navigate(routeForRole(user.role));
      } else {
        const user = await signup({
          email,
          username,
          password,
          role,
          organization_name: role === "employer_admin" ? orgName : undefined,
        });
        navigate(routeForRole(user.role));
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-indigo-100 px-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          {mode === "login"
            ? "Log in to your Interview Assistant account"
            : "Sign up as a candidate or an employer"}
        </p>

        {mode === "signup" && (
          <div className="flex gap-2 mb-4">
            {(["candidate", "employer_admin"] as UserRole[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold border transition-colors ${
                  role === r
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-300"
                }`}
              >
                {r === "candidate" ? "Candidate" : "Employer"}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required={mode === "signup"}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          {mode === "signup" && (
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          )}
          {mode === "signup" && role === "employer_admin" && (
            <input
              type="text"
              placeholder="Organization name"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              required
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          )}
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg disabled:opacity-50"
          >
            {busy ? "Please wait…" : mode === "login" ? "Log in" : "Sign up"}
          </button>
        </form>

        <p className="text-sm text-gray-500 mt-6 text-center">
          {mode === "login" ? "No account?" : "Already have an account?"}{" "}
          <button
            onClick={() => {
              setMode(mode === "login" ? "signup" : "login");
              setError("");
            }}
            className="text-blue-600 font-semibold"
          >
            {mode === "login" ? "Sign up" : "Log in"}
          </button>
        </p>

        <p className="text-xs text-gray-400 mt-4 text-center">
          Or{" "}
          <button onClick={() => navigate("/")} className="underline">
            continue with a free mock interview
          </button>
        </p>
      </div>
    </div>
  );
}
