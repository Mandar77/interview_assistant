/**
 * EmployerDashboard - "Assessment Studio" home (Phase 10).
 * Location: frontend/src/pages/employer/EmployerDashboard.tsx
 *
 * Lists the org's assessments, lets the employer create one, and links into
 * the builder and recruiter panel. All data is org-scoped server-side.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { assessmentApi, type Assessment } from "../../api/platform";
import { useAuth } from "../../auth/AuthContext";

export default function EmployerDashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState("");
  const [creating, setCreating] = useState(false);

  const load = () => {
    setLoading(true);
    assessmentApi
      .list()
      .then(setAssessments)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const create = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const a = await assessmentApi.create({ title: newTitle.trim() });
      setNewTitle("");
      navigate(`/employer/assessments/${a.id}`);
    } finally {
      setCreating(false);
    }
  };

  const statusColor: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    published: "bg-green-100 text-green-700",
    archived: "bg-amber-100 text-amber-700",
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Assessment Studio</h1>
            <p className="text-xs text-gray-500">{user?.full_name || user?.username}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/employer/recruiter")}
              className="px-4 py-2 text-sm font-semibold text-blue-700 bg-blue-50 rounded-lg"
            >
              Recruiter Panel
            </button>
            <button
              onClick={() => navigate("/employer/culture")}
              className="px-4 py-2 text-sm font-semibold text-purple-700 bg-purple-50 rounded-lg"
            >
              Culture Scraper
            </button>
            <button onClick={logout} className="px-4 py-2 text-sm text-gray-500">
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 max-w-5xl">
        <div className="bg-white rounded-xl shadow p-5 mb-6 flex gap-3">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && create()}
            placeholder="New assessment title (e.g. SDE Intern 45min)"
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={create}
            disabled={creating}
            className="px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-lg disabled:opacity-50"
          >
            + Create
          </button>
        </div>

        {loading ? (
          <p className="text-gray-500">Loading…</p>
        ) : assessments.length === 0 ? (
          <div className="bg-white rounded-xl shadow p-10 text-center text-gray-500">
            No assessments yet. Create your first one above.
          </div>
        ) : (
          <div className="grid gap-4">
            {assessments.map((a) => {
              const questionCount = a.sections.reduce(
                (n, s) => n + s.questions.length,
                0
              );
              return (
                <div
                  key={a.id}
                  className="bg-white rounded-xl shadow p-5 flex items-center justify-between hover:shadow-md transition-shadow"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-gray-900">{a.title}</h3>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                          statusColor[a.status]
                        }`}
                      >
                        {a.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">
                      {a.sections.length} section{a.sections.length !== 1 ? "s" : ""} ·{" "}
                      {questionCount} question{questionCount !== 1 ? "s" : ""}
                    </p>
                  </div>
                  <button
                    onClick={() => navigate(`/employer/assessments/${a.id}`)}
                    className="px-4 py-2 text-sm font-semibold text-blue-700 bg-blue-50 rounded-lg"
                  >
                    Open →
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
