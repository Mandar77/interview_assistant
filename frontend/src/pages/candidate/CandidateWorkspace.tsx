/**
 * CandidateWorkspace — candidate home: assigned assessments + mock practice.
 * Location: frontend/src/pages/candidate/CandidateWorkspace.tsx
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ClipboardList, Sparkles } from "lucide-react";
import { workspaceApi } from "../../api/platform";
import AppShell from "../../ui/AppShell";
import { Badge, Button, Card, EmptyState, SectionTitle, Skeleton } from "../../ui";

export default function CandidateWorkspace() {
  const navigate = useNavigate();
  const [assignments, setAssignments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    workspaceApi.myAssignments().then(setAssignments).finally(() => setLoading(false));
  }, []);

  return (
    <AppShell title="Interview Workspace">
      {/* Mock practice CTA */}
      <Card elevated className="mb-8 overflow-hidden">
        <div className="relative flex flex-col items-start gap-4 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="bg-grid pointer-events-none absolute inset-0 opacity-40" />
          <div className="relative">
            <div className="mb-1 flex items-center gap-2">
              <Sparkles size={16} className="text-[var(--accent)]" />
              <h2 className="text-lg font-semibold text-[var(--text)]">Unlimited mock interviews</h2>
            </div>
            <p className="max-w-md text-sm text-[var(--text-muted)]">
              Practice with any job description. Your results are saved privately for your own improvement.
            </p>
          </div>
          <Button className="relative" onClick={() => navigate("/")} rightIcon={<ArrowRight size={16} />}>
            Start a mock
          </Button>
        </div>
      </Card>

      <SectionTitle>Assigned assessments</SectionTitle>

      {loading ? (
        <div className="space-y-3">
          {[0, 1].map((i) => <Skeleton key={i} className="h-[72px] w-full" />)}
        </div>
      ) : assignments.length === 0 ? (
        <EmptyState
          icon={<ClipboardList size={22} />}
          title="No assessments assigned"
          description="When an employer assigns you an assessment, it will appear here ready to start."
        />
      ) : (
        <div className="space-y-3 stagger">
          {assignments.map(({ assignment, assessment_title }) => {
            const submitted = assignment.status === "submitted";
            return (
              <Card key={assignment.id} className="flex items-center justify-between px-5 py-4">
                <div>
                  <h3 className="text-base font-semibold text-[var(--text)]">{assessment_title || "Assessment"}</h3>
                  <p className="mt-0.5 text-sm capitalize text-[var(--text-muted)]">Status: {assignment.status}</p>
                </div>
                {submitted ? (
                  <Badge tone="success" dot>Submitted</Badge>
                ) : (
                  <Button
                    onClick={() => navigate(`/workspace/attempt/${assignment.id}`)}
                    rightIcon={<ArrowRight size={16} />}
                  >
                    {assignment.status === "started" ? "Resume" : "Start"}
                  </Button>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
