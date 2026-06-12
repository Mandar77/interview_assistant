/**
 * EmployerDashboard — "Assessment Studio" home.
 * Location: frontend/src/pages/employer/EmployerDashboard.tsx
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, FileText, Plus } from "lucide-react";
import { assessmentApi, type Assessment } from "../../api/platform";
import AppShell from "../../ui/AppShell";
import { Badge, Button, EmptyState, Input, SectionTitle, Skeleton } from "../../ui";
import { EMPLOYER_NAV } from "./nav";

const STATUS_TONE = { draft: "neutral", published: "success", archived: "warning" } as const;

export default function EmployerDashboard() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState("");
  const [creating, setCreating] = useState(false);

  const load = () => {
    setLoading(true);
    assessmentApi.list().then(setAssessments).finally(() => setLoading(false));
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

  return (
    <AppShell nav={EMPLOYER_NAV} title="Assessment Studio">
      {/* Create bar */}
      <div className="mb-8 flex flex-col gap-2 sm:flex-row">
        <Input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && create()}
          placeholder="Name a new assessment — e.g. SDE Intern · 45 min"
          className="flex-1"
        />
        <Button onClick={create} loading={creating} leftIcon={<Plus size={16} />}>
          Create
        </Button>
      </div>

      <SectionTitle hint={!loading ? `${assessments.length} total` : undefined}>
        Assessments
      </SectionTitle>

      {loading ? (
        <div className="grid gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-[76px] w-full" />
          ))}
        </div>
      ) : assessments.length === 0 ? (
        <EmptyState
          icon={<FileText size={22} />}
          title="No assessments yet"
          description="Create your first assessment to start building proctored interviews for candidates."
          action={
            <Button onClick={() => newTitle ? create() : (document.querySelector("input") as HTMLInputElement)?.focus()}>
              Create your first assessment
            </Button>
          }
        />
      ) : (
        <div className="grid gap-3 stagger">
          {assessments.map((a) => {
            const questionCount = a.sections.reduce((n, s) => n + s.questions.length, 0);
            return (
              <button
                key={a.id}
                onClick={() => navigate(`/employer/assessments/${a.id}`)}
                className="group flex items-center justify-between rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] px-5 py-4 text-left shadow-[var(--shadow-sm)] transition-all hover:-translate-y-0.5 hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-md)]"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2.5">
                    <h3 className="truncate text-base font-semibold text-[var(--text)]">{a.title}</h3>
                    <Badge tone={STATUS_TONE[a.status]} dot>
                      {a.status}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-sm text-[var(--text-muted)]">
                    {a.sections.length} section{a.sections.length !== 1 ? "s" : ""} · {questionCount}{" "}
                    question{questionCount !== 1 ? "s" : ""}
                  </p>
                </div>
                <ArrowRight
                  size={18}
                  className="shrink-0 text-[var(--text-muted)] transition-all group-hover:translate-x-0.5 group-hover:text-[var(--accent)]"
                />
              </button>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
