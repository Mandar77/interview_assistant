/**
 * AssessmentBuilder — configure one assessment.
 * Location: frontend/src/pages/employer/AssessmentBuilder.tsx
 *
 * Two-column builder: sections (JD auto-gen + manual MCQ) on the left, a sticky
 * settings rail (proctoring permissions + assignment) on the right. Sticky
 * toolbar carries publish / save-as-template. Fully themed.
 */

import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Save, Sparkles, Upload } from "lucide-react";
import {
  assessmentApi,
  type Assessment,
  type AssessmentPermissions,
  type AssessmentQuestion,
} from "../../api/platform";
import { Badge, Button, Card, Input, Label, PageLoader, Select, Textarea } from "../../ui";
import ThemeToggle from "../../theme/ThemeToggle";

const PERMISSION_LABELS: { key: keyof AssessmentPermissions; label: string; hint: string }[] = [
  { key: "require_mic", label: "Microphone", hint: "Record spoken answers" },
  { key: "require_camera", label: "Camera", hint: "Body-language signals" },
  { key: "require_screen_share", label: "Screen share", hint: "Capture the workspace" },
  { key: "force_fullscreen", label: "Force fullscreen", hint: "Detect exits" },
  { key: "block_tab_switch", label: "Block tab switching", hint: "Flag focus loss" },
  { key: "block_copy_paste", label: "Block copy / paste", hint: "Prevent pasting" },
  { key: "watermark", label: "Watermark overlay", hint: "Candidate id + time" },
];

const uid = () => Math.random().toString(36).slice(2, 10);
const STATUS_TONE = { draft: "neutral", published: "success", archived: "warning" } as const;

export default function AssessmentBuilder() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState("");

  const [jd, setJd] = useState("");
  const [interviewType, setInterviewType] = useState("technical");
  const [difficulty, setDifficulty] = useState("medium");
  const [numQuestions, setNumQuestions] = useState(3);
  const [useCulture, setUseCulture] = useState(false);
  const [usernames, setUsernames] = useState("");

  const load = useCallback(() => {
    if (!id) return;
    assessmentApi.get(id).then(setAssessment);
  }, [id]);
  useEffect(load, [load]);

  if (!assessment) return <PageLoader label="Loading assessment…" />;

  const patch = async (body: Partial<Assessment>) => {
    setSaving(true);
    try {
      setAssessment(await assessmentApi.update(assessment.id, body));
    } finally {
      setSaving(false);
    }
  };

  const togglePermission = (key: keyof AssessmentPermissions) =>
    patch({ permissions: { ...assessment.permissions, [key]: !assessment.permissions[key] } });

  const generate = async () => {
    if (jd.trim().length < 50) {
      alert("Job description must be at least 50 characters.");
      return;
    }
    setBusy("Generating questions…");
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
      alert(e?.response?.data?.detail || "Generation failed — is Ollama running?");
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
    patch({ sections: [...assessment.sections, { id: uid(), title: "Multiple Choice", questions: [question] }] });
  };

  const assign = async () => {
    const list = usernames.split(/[,\s]+/).map((u) => u.trim()).filter(Boolean);
    if (!list.length) return;
    setBusy("Assigning…");
    try {
      await assessmentApi.assign(assessment.id, list);
      setUsernames("");
      alert(`Assigned to ${list.length} candidate(s).`);
    } catch (e: any) {
      alert(e?.response?.data?.detail || "Assign failed.");
    } finally {
      setBusy("");
    }
  };

  const saveTemplate = async () => {
    const name = prompt("Template name:", assessment.title);
    if (!name) return;
    await assessmentApi.saveAsTemplate(assessment.id, name);
    alert("Saved as a reusable template.");
  };

  const totalQuestions = assessment.sections.reduce((n, s) => n + s.questions.length, 0);
  const published = assessment.status === "published";

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Toolbar */}
      <header className="sticky top-0 z-40 border-b border-[var(--border)] glass">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-5">
          <button
            onClick={() => navigate("/employer")}
            className="flex items-center gap-1.5 rounded-[var(--radius-sm)] px-2 py-1 text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text)]"
          >
            <ArrowLeft size={16} /> Back
          </button>
          <div className="flex min-w-0 items-center gap-2.5">
            <h1 className="truncate text-base font-semibold text-[var(--text)]">{assessment.title}</h1>
            <Badge tone={STATUS_TONE[assessment.status]} dot>{assessment.status}</Badge>
            {saving && <span className="text-xs text-[var(--text-muted)]">saving…</span>}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={saveTemplate} leftIcon={<Save size={15} />}>
              Save as template
            </Button>
            {!published && (
              <Button size="sm" onClick={() => patch({ status: "published" })} disabled={totalQuestions === 0} leftIcon={<Upload size={15} />}>
                Publish
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-5 py-6 lg:grid-cols-3">
        {/* Left: builder */}
        <div className="space-y-5 lg:col-span-2">
          {/* JD generation */}
          <Card>
            <div className="border-b border-[var(--border)] px-5 py-4">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-[var(--accent)]" />
                <h2 className="text-base font-semibold text-[var(--text)]">Generate from a job description</h2>
              </div>
            </div>
            <div className="space-y-3 px-5 py-4">
              <Textarea
                rows={4}
                value={jd}
                onChange={(e) => setJd(e.target.value)}
                placeholder="Paste the job description… (min 50 characters)"
                className="font-mono text-sm"
              />
              <div className="flex flex-wrap items-center gap-2">
                <Select value={interviewType} onChange={(e) => setInterviewType(e.target.value)} className="w-auto">
                  <option value="technical">Technical</option>
                  <option value="oa">Coding (OA)</option>
                  <option value="system_design">System Design</option>
                  <option value="behavioral">Behavioral</option>
                </Select>
                <Select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="w-auto">
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </Select>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(Number(e.target.value))}
                  className="w-20"
                />
                <label className="flex cursor-pointer items-center gap-2 text-sm text-[var(--text-secondary)]">
                  <input type="checkbox" checked={useCulture} onChange={(e) => setUseCulture(e.target.checked)} className="accent-[var(--accent)]" />
                  Ground in culture
                </label>
                <Button size="sm" onClick={generate} loading={busy === "Generating questions…"}>
                  Generate
                </Button>
              </div>
            </div>
          </Card>

          {/* Sections */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-[var(--text)]">
              Sections{" "}
              <span className="text-sm font-normal text-[var(--text-muted)]">· {totalQuestions} questions</span>
            </h2>
            <Button variant="secondary" size="sm" onClick={addMcqSection} leftIcon={<Plus size={15} />}>
              Add MCQ section
            </Button>
          </div>

          {assessment.sections.length === 0 ? (
            <Card className="px-5 py-10 text-center">
              <p className="text-sm text-[var(--text-muted)]">
                No questions yet. Generate from a JD above, or add an MCQ section.
              </p>
            </Card>
          ) : (
            assessment.sections.map((section) => (
              <Card key={section.id}>
                <div className="border-b border-[var(--border)] px-5 py-3">
                  <h3 className="text-sm font-semibold text-[var(--text-secondary)]">{section.title}</h3>
                </div>
                <ul className="divide-y divide-[var(--border)]">
                  {section.questions.map((q, i) => (
                    <li key={q.id} className="px-5 py-4">
                      <div className="mb-1.5 flex items-center gap-2">
                        <Badge tone="accent">{q.type}</Badge>
                        <span className="text-xs text-[var(--text-muted)]">
                          {q.scoring_mode} · {q.max_score} pts
                        </span>
                      </div>
                      <p className="text-sm text-[var(--text)]">
                        <span className="text-[var(--text-muted)]">{i + 1}.</span> {q.prompt}
                      </p>
                      {q.options && (
                        <ul className="mt-2 space-y-1 pl-4">
                          {q.options.map((o) => (
                            <li key={o.id} className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                              <span className={o.is_correct ? "text-[var(--success)]" : "text-[var(--text-disabled)]"}>
                                {o.is_correct ? "✓" : "○"}
                              </span>
                              {o.text}
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              </Card>
            ))
          )}
        </div>

        {/* Right: settings rail */}
        <div className="space-y-5">
          <Card>
            <div className="border-b border-[var(--border)] px-5 py-4">
              <h2 className="text-base font-semibold text-[var(--text)]">Proctoring & permissions</h2>
            </div>
            <div className="divide-y divide-[var(--border)]">
              {PERMISSION_LABELS.map(({ key, label, hint }) => {
                const on = !!assessment.permissions[key];
                return (
                  <button
                    key={key}
                    onClick={() => togglePermission(key)}
                    className="flex w-full items-center justify-between px-5 py-3 text-left transition-colors hover:bg-[var(--surface-2)]"
                  >
                    <div>
                      <p className="text-sm font-medium text-[var(--text)]">{label}</p>
                      <p className="text-xs text-[var(--text-muted)]">{hint}</p>
                    </div>
                    <span
                      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
                        on ? "bg-[var(--accent)]" : "bg-[var(--surface-3)]"
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
                          on ? "left-4" : "left-0.5"
                        }`}
                      />
                    </span>
                  </button>
                );
              })}
            </div>
          </Card>

          <Card>
            <div className="border-b border-[var(--border)] px-5 py-4">
              <h2 className="text-base font-semibold text-[var(--text)]">Assign candidates</h2>
            </div>
            <div className="px-5 py-4">
              {!published ? (
                <p className="text-sm text-[var(--warning)]">Publish the assessment to assign it.</p>
              ) : (
                <>
                  <Label>Usernames</Label>
                  <Textarea
                    rows={3}
                    value={usernames}
                    onChange={(e) => setUsernames(e.target.value)}
                    placeholder="alice, bob carol — comma or space separated"
                    className="text-sm"
                  />
                  <Button className="mt-3 w-full" onClick={assign} loading={busy === "Assigning…"}>
                    Assign
                  </Button>
                </>
              )}
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}
