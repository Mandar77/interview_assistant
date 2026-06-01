/**
 * AssessmentBuilder - configure one assessment (Phase 10).
 * Location: frontend/src/pages/employer/AssessmentBuilder.tsx
 *
 * Build sections (auto-generate from a JD or add MCQs by hand), set proctoring
 * permissions + scoring, publish, assign to candidate usernames, and save as a
 * reusable template (Phase 13E).
 */

import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  assessmentApi,
  type Assessment,
  type AssessmentPermissions,
  type AssessmentQuestion,
} from "../../api/platform";

const PERMISSION_LABELS: { key: keyof AssessmentPermissions; label: string }[] = [
  { key: "require_mic", label: "Require microphone" },
  { key: "require_camera", label: "Require camera" },
  { key: "require_screen_share", label: "Require screen share" },
  { key: "force_fullscreen", label: "Force fullscreen" },
  { key: "block_tab_switch", label: "Block tab switching" },
  { key: "block_copy_paste", label: "Block copy / paste" },
  { key: "watermark", label: "Watermark overlay" },
];

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

export default function AssessmentBuilder() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState("");

  // JD generation form
  const [jd, setJd] = useState("");
  const [interviewType, setInterviewType] = useState("technical");
  const [difficulty, setDifficulty] = useState("medium");
  const [numQuestions, setNumQuestions] = useState(3);
  const [useCulture, setUseCulture] = useState(false);

  // assignment form
  const [usernames, setUsernames] = useState("");

  const load = useCallback(() => {
    if (!id) return;
    assessmentApi.get(id).then(setAssessment);
  }, [id]);

  useEffect(load, [load]);

  if (!assessment) {
    return <div className="p-10 text-gray-500">Loading…</div>;
  }

  const patch = async (body: Partial<Assessment>) => {
    setSaving(true);
    try {
      const updated = await assessmentApi.update(assessment.id, body);
      setAssessment(updated);
    } finally {
      setSaving(false);
    }
  };

  const togglePermission = (key: keyof AssessmentPermissions) => {
    patch({ permissions: { ...assessment.permissions, [key]: !assessment.permissions[key] } });
  };

  const generate = async () => {
    if (jd.trim().length < 50) {
      alert("JD must be at least 50 characters");
      return;
    }
    setBusy("Generating questions from JD…");
    try {
      const updated = await assessmentApi.generateFromJd(assessment.id, {
        job_description: jd,
        interview_type: interviewType,
        difficulty,
        num_questions: numQuestions,
        use_culture_grounding: useCulture,
      });
      setAssessment(updated);
      setJd("");
    } catch (e: any) {
      alert(e?.response?.data?.detail || "Generation failed (is Ollama running?)");
    } finally {
      setBusy("");
    }
  };

  const addMcqSection = () => {
    const question: AssessmentQuestion = {
      id: uid(),
      type: "mcq",
      prompt: "New multiple-choice question",
      options: [
        { id: uid(), text: "Option A", is_correct: true },
        { id: uid(), text: "Option B", is_correct: false },
      ],
      expected_duration_mins: 2,
      scoring_mode: "auto",
      max_score: 5,
      skill_tags: [],
      evaluation_criteria: [],
    };
    patch({
      sections: [
        ...assessment.sections,
        { id: uid(), title: "Multiple Choice", questions: [question] },
      ],
    });
  };

  const publish = () => patch({ status: "published" });

  const assign = async () => {
    const list = usernames
      .split(/[,\s]+/)
      .map((u) => u.trim())
      .filter(Boolean);
    if (!list.length) return;
    setBusy("Assigning…");
    try {
      await assessmentApi.assign(assessment.id, list);
      setUsernames("");
      alert(`Assigned to ${list.length} candidate(s)`);
    } catch (e: any) {
      alert(e?.response?.data?.detail || "Assign failed");
    } finally {
      setBusy("");
    }
  };

  const saveTemplate = async () => {
    const name = prompt("Template name:", assessment.title);
    if (!name) return;
    await assessmentApi.saveAsTemplate(assessment.id, name);
    alert("Saved as reusable template");
  };

  const totalQuestions = assessment.sections.reduce((n, s) => n + s.questions.length, 0);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate("/employer")} className="text-gray-500">
              ← Back
            </button>
            <h1 className="text-lg font-bold text-gray-900">{assessment.title}</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">
              {assessment.status}
            </span>
            {saving && <span className="text-xs text-gray-400">saving…</span>}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={saveTemplate} className="px-3 py-2 text-sm text-purple-700 bg-purple-50 rounded-lg">
              Save as template
            </button>
            {assessment.status !== "published" && (
              <button
                onClick={publish}
                disabled={totalQuestions === 0}
                className="px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-lg disabled:opacity-50"
              >
                Publish
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-6 max-w-5xl grid lg:grid-cols-3 gap-6">
        {/* Left: sections */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl shadow p-5">
            <h2 className="font-bold text-gray-900 mb-3">Auto-generate from JD</h2>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the job description…"
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <div className="flex flex-wrap gap-2 mt-3">
              <select value={interviewType} onChange={(e) => setInterviewType(e.target.value)} className="px-3 py-2 border rounded-lg text-sm">
                <option value="technical">Technical</option>
                <option value="oa">Coding (OA)</option>
                <option value="system_design">System Design</option>
                <option value="behavioral">Behavioral</option>
              </select>
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="px-3 py-2 border rounded-lg text-sm">
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
              <input
                type="number"
                min={1}
                max={10}
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
                className="w-20 px-3 py-2 border rounded-lg text-sm"
              />
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input type="checkbox" checked={useCulture} onChange={(e) => setUseCulture(e.target.checked)} />
                Ground in company culture
              </label>
              <button onClick={generate} disabled={!!busy} className="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg disabled:opacity-50">
                Generate
              </button>
            </div>
            {busy && <p className="text-sm text-blue-600 mt-2">{busy}</p>}
          </div>

          <div className="flex justify-between items-center">
            <h2 className="font-bold text-gray-900">Sections ({totalQuestions} questions)</h2>
            <button onClick={addMcqSection} className="px-3 py-2 text-sm font-semibold text-blue-700 bg-blue-50 rounded-lg">
              + Add MCQ section
            </button>
          </div>

          {assessment.sections.map((section) => (
            <div key={section.id} className="bg-white rounded-xl shadow p-5">
              <h3 className="font-semibold text-gray-800 mb-2">{section.title}</h3>
              <ul className="space-y-2">
                {section.questions.map((q, i) => (
                  <li key={q.id} className="border border-gray-100 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded text-xs bg-indigo-100 text-indigo-700 font-semibold uppercase">
                        {q.type}
                      </span>
                      <span className="text-xs text-gray-400">{q.scoring_mode} · {q.max_score} pts</span>
                    </div>
                    <p className="text-sm text-gray-800">{i + 1}. {q.prompt}</p>
                    {q.options && (
                      <ul className="mt-1 ml-4 text-xs text-gray-500">
                        {q.options.map((o) => (
                          <li key={o.id}>
                            {o.is_correct ? "✓ " : "• "}
                            {o.text}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Right: permissions + assign */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow p-5">
            <h2 className="font-bold text-gray-900 mb-3">Proctoring & Permissions</h2>
            <div className="space-y-2">
              {PERMISSION_LABELS.map(({ key, label }) => (
                <label key={key} className="flex items-center justify-between text-sm text-gray-700">
                  {label}
                  <input
                    type="checkbox"
                    checked={!!assessment.permissions[key]}
                    onChange={() => togglePermission(key)}
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow p-5">
            <h2 className="font-bold text-gray-900 mb-3">Assign to candidates</h2>
            {assessment.status !== "published" ? (
              <p className="text-sm text-amber-600">Publish first to assign.</p>
            ) : (
              <>
                <textarea
                  value={usernames}
                  onChange={(e) => setUsernames(e.target.value)}
                  placeholder="usernames, comma or space separated"
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                />
                <button onClick={assign} disabled={!!busy} className="mt-2 w-full px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg disabled:opacity-50">
                  Assign
                </button>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
