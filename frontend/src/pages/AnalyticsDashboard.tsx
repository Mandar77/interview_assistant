/**
 * AnalyticsDashboard — performance overview (/progress).
 * Location: frontend/src/pages/AnalyticsDashboard.tsx
 *
 * Aggregates locally-stored mock-interview sessions into a premium dashboard:
 * stat row, token-driven radar + skill bars, focus areas, and a recent-sessions
 * table. Robust empty state; never blanks out.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, BarChart3, Plus, Target } from "lucide-react";
import { Badge, Button, Card, EmptyState } from "../ui";
import { BrandMark } from "../ui/AppShell";
import ThemeToggle from "../theme/ThemeToggle";
import { cn } from "../lib/utils";

interface SessionSummary {
  session_id: string;
  date: string;
  interview_type: string;
  overall_score: number;
  rubric_scores: Record<string, number>;
  questions_count: number;
}
interface DashboardData {
  total_sessions: number;
  avg_score: number;
  score_trend: number;
  recent_sessions: SessionSummary[];
  skill_breakdown: Record<string, number>;
  improvement_areas: string[];
}

const initials = (label: string) =>
  label.split("_").filter(Boolean).map((w) => w[0].toUpperCase()).join("");

/* Token-driven radar chart */
function RadarChart({ data, labels }: { data: number[]; labels: string[] }) {
  const size = 280, center = size / 2, maxRadius = 110, levels = 5;
  const slice = (2 * Math.PI) / Math.max(labels.length, 1);
  const point = (v: number, i: number) => {
    const a = slice * i - Math.PI / 2;
    const r = (v / 5) * maxRadius;
    return { x: center + r * Math.cos(a), y: center + r * Math.sin(a) };
  };
  const pts = data.map(point);
  const path = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="mx-auto w-full max-w-xs">
      {Array.from({ length: levels }).map((_, i) => (
        <circle key={i} cx={center} cy={center} r={(maxRadius / levels) * (i + 1)} fill="none" stroke="var(--border)" />
      ))}
      {labels.map((_, i) => {
        const a = slice * i - Math.PI / 2;
        return <line key={i} x1={center} y1={center} x2={center + maxRadius * Math.cos(a)} y2={center + maxRadius * Math.sin(a)} stroke="var(--border)" />;
      })}
      <path d={path} fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth={2} />
      {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r={4} fill="var(--accent)" stroke="var(--surface)" strokeWidth={2} />)}
      {labels.map((label, i) => {
        const a = slice * i - Math.PI / 2;
        const r = maxRadius + 22;
        return (
          <text key={i} x={center + r * Math.cos(a)} y={center + r * Math.sin(a)} textAnchor="middle" dominantBaseline="middle" fontSize={11} fill="var(--text-muted)" fontWeight={600}>
            {initials(label)}
          </text>
        );
      })}
    </svg>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = (value / 5) * 100;
  const tone = value >= 4 ? "var(--success)" : value >= 3 ? "var(--accent)" : value >= 2 ? "var(--warning)" : "var(--error)";
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="capitalize text-[var(--text-secondary)]">{label.replace(/_/g, " ")}</span>
        <span className="font-mono font-medium text-[var(--text)]">{value.toFixed(1)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[var(--surface-3)]">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: tone }} />
      </div>
    </div>
  );
}

function Stat({ label, value, sub, trend }: { label: string; value: string | number; sub?: string; trend?: number }) {
  return (
    <Card className="px-5 py-4">
      <p className="text-sm text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 font-mono text-2xl font-semibold text-[var(--text)]">{value}</p>
      {sub && <p className="text-xs text-[var(--text-muted)]">{sub}</p>}
      {trend !== undefined && Number.isFinite(trend) && (
        <p className={cn("mt-1 text-xs font-medium", trend >= 0 ? "text-[var(--success)]" : "text-[var(--error)]")}>
          {trend >= 0 ? "↑" : "↓"} {Math.abs(trend).toFixed(1)}% vs last
        </p>
      )}
    </Card>
  );
}

export default function AnalyticsDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    const empty: DashboardData = {
      total_sessions: 0, avg_score: 0, score_trend: 0, recent_sessions: [],
      skill_breakdown: {}, improvement_areas: [],
    };
    try {
      const sessions = JSON.parse(localStorage.getItem("interview_sessions") || "[]") as SessionSummary[];
      if (!sessions.length) return setData(empty);

      const avg = sessions.reduce((s, x) => s + (x.overall_score || 0), 0) / sessions.length;
      const lastTwo = sessions.slice(-2);
      const trend = lastTwo.length === 2 && lastTwo[0].overall_score
        ? ((lastTwo[1].overall_score - lastTwo[0].overall_score) / lastTwo[0].overall_score) * 100 : 0;

      const totals: Record<string, number[]> = {};
      sessions.forEach((s) =>
        Object.entries(s.rubric_scores || {}).forEach(([k, v]) => {
          (totals[k] ||= []).push(v as number);
        })
      );
      const breakdown: Record<string, number> = {};
      Object.entries(totals).forEach(([k, v]) => (breakdown[k] = v.reduce((a, b) => a + b, 0) / v.length));
      const areas = Object.entries(breakdown).filter(([, s]) => s < 3.5).sort((a, b) => a[1] - b[1]).slice(0, 3).map(([k]) => k);

      setData({
        total_sessions: sessions.length, avg_score: avg, score_trend: trend,
        recent_sessions: sessions.slice(-5).reverse(), skill_breakdown: breakdown, improvement_areas: areas,
      });
    } catch {
      setData(empty);
    }
  }, []);

  const hasData = data && data.total_sessions > 0;

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border)] glass">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate("/")} className="flex items-center gap-1.5 rounded-[var(--radius-sm)] px-2 py-1 text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text)]">
              <ArrowLeft size={16} /> Home
            </button>
            <div className="flex items-center gap-2">
              <BrandMark size={22} />
              <span className="text-base font-semibold tracking-tight text-[var(--text)]">Progress</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button size="sm" onClick={() => navigate("/")} leftIcon={<Plus size={15} />}>New interview</Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight text-[var(--text)]">Performance dashboard</h1>
        <p className="mb-6 text-sm text-[var(--text-muted)]">Track your interview preparation over time.</p>

        {!data ? null : !hasData ? (
          <EmptyState
            icon={<BarChart3 size={22} />}
            title="No sessions yet"
            description="Complete your first practice interview and your analytics will appear here."
            action={<Button onClick={() => navigate("/")}>Start your first interview</Button>}
          />
        ) : (
          <div className="space-y-6 animate-fade-in">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Stat label="Total sessions" value={data.total_sessions} />
              <Stat label="Average score" value={data.avg_score.toFixed(1)} sub="out of 5.0" trend={data.score_trend} />
              <Stat label="Questions answered" value={data.recent_sessions.reduce((s, x) => s + x.questions_count, 0)} />
              <Stat label="Focus areas" value={data.improvement_areas.length} />
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="px-6 py-5">
                <h2 className="mb-4 text-base font-semibold text-[var(--text)]">Skill radar</h2>
                {Object.keys(data.skill_breakdown).length > 0 ? (
                  <RadarChart data={Object.values(data.skill_breakdown)} labels={Object.keys(data.skill_breakdown)} />
                ) : (
                  <p className="py-10 text-center text-sm text-[var(--text-muted)]">No rubric data yet.</p>
                )}
              </Card>

              <Card className="px-6 py-5">
                <h2 className="mb-4 text-base font-semibold text-[var(--text)]">Skill breakdown</h2>
                <div className="space-y-3.5">
                  {Object.entries(data.skill_breakdown).sort(([, a], [, b]) => b - a).map(([k, v]) => (
                    <ScoreBar key={k} label={k} value={v} />
                  ))}
                </div>
              </Card>
            </div>

            {data.improvement_areas.length > 0 && (
              <Card className="px-6 py-5">
                <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-[var(--text)]">
                  <Target size={16} className="text-[var(--warning)]" /> Focus areas
                </h2>
                <div className="grid gap-3 sm:grid-cols-3">
                  {data.improvement_areas.map((area, i) => (
                    <div key={area} className="flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--warning-soft)] text-sm font-semibold text-[var(--warning)]">{i + 1}</span>
                      <div>
                        <p className="text-sm font-medium capitalize text-[var(--text)]">{area.replace(/_/g, " ")}</p>
                        <p className="text-xs text-[var(--text-muted)]">{data.skill_breakdown[area]?.toFixed(1) ?? "—"}/5</p>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            <Card>
              <div className="border-b border-[var(--border)] px-6 py-4">
                <h2 className="text-base font-semibold text-[var(--text)]">Recent sessions</h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--text-muted)]">
                    <th className="px-6 py-3 font-medium">Date</th>
                    <th className="px-6 py-3 font-medium">Type</th>
                    <th className="px-6 py-3 font-medium">Questions</th>
                    <th className="px-6 py-3 font-medium">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {data.recent_sessions.map((s) => (
                    <tr key={s.session_id} className="transition-colors hover:bg-[var(--surface-2)]">
                      <td className="px-6 py-3 text-[var(--text-secondary)]">{new Date(s.date).toLocaleDateString()}</td>
                      <td className="px-6 py-3"><Badge tone="accent">{s.interview_type.replace(/_/g, " ")}</Badge></td>
                      <td className="px-6 py-3 text-[var(--text-secondary)]">{s.questions_count}</td>
                      <td className={cn("px-6 py-3 font-mono font-semibold", s.overall_score >= 4 ? "text-[var(--success)]" : s.overall_score >= 3 ? "text-[var(--accent)]" : "text-[var(--warning)]")}>
                        {s.overall_score.toFixed(1)}/5
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
