/**
 * CandidateWorkspace - candidate home: assigned assessments + mock interviews.
 * Location: frontend/src/pages/candidate/CandidateWorkspace.tsx (Phase 11)
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { workspaceApi } from "../../api/platform";
import { useAuth } from "../../auth/AuthContext";

export default function CandidateWorkspace() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [assignments, setAssignments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    workspaceApi
      .myAssignments()
      .then(setAssignments)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-100">
      <header className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Interview Workspace</h1>
            <p className="text-xs text-gray-500">{user?.username}</p>
          </div>
          <button onClick={logout} className="px-4 py-2 text-sm text-gray-500">Log out</button>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 max-w-4xl space-y-8">
        {/* Mock interview CTA - reuses the original anonymous flow */}
        <div className="bg-white rounded-xl shadow p-6 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-gray-900">Unlimited Mock Interviews</h2>
            <p className="text-sm text-gray-500">Practice by entering any job description. Results saved for your improvement.</p>
          </div>
          <button onClick={() => navigate("/")} className="px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-lg">
            Start mock →
          </button>
        </div>

        {/* Assigned assessments */}
        <div>
          <h2 className="font-bold text-gray-900 mb-3">Assigned Assessments</h2>
          {loading ? (
            <p className="text-gray-500">Loading…</p>
          ) : assignments.length === 0 ? (
            <div className="bg-white rounded-xl shadow p-8 text-center text-gray-500">
              No assessments assigned to you yet.
            </div>
          ) : (
            <div className="grid gap-4">
              {assignments.map(({ assignment, assessment_title }) => (
                <div key={assignment.id} className="bg-white rounded-xl shadow p-5 flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-gray-900">{assessment_title || "Assessment"}</h3>
                    <p className="text-sm text-gray-500 capitalize">Status: {assignment.status}</p>
                  </div>
                  {assignment.status === "submitted" ? (
                    <span className="px-4 py-2 text-sm font-semibold text-green-700 bg-green-50 rounded-lg">Submitted ✓</span>
                  ) : (
                    <button
                      onClick={() => navigate(`/workspace/attempt/${assignment.id}`)}
                      className="px-5 py-2.5 bg-indigo-600 text-white font-semibold rounded-lg"
                    >
                      {assignment.status === "started" ? "Resume" : "Start"} →
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
