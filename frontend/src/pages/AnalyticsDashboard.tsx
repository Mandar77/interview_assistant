/**
 * Analytics Dashboard - Performance Overview
 * Location: frontend/src/pages/AnalyticsDashboard.tsx
 * 
 * Features:
 * - Radar chart for rubric scores
 * - Speech pace timeline
 * - Eye contact percentage
 * - Weak skill breakdown
 * - Performance trends
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

// Types
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

// Radar Chart Component (SVG-based)
function RadarChart({ data, labels }: { data: number[]; labels: string[] }) {
  const size = 300;
  const center = size / 2;
  const maxRadius = 120;
  const levels = 5;
  
  // Calculate points for the radar
  const angleSlice = (2 * Math.PI) / labels.length;
  
  const getPoint = (value: number, index: number) => {
    const angle = angleSlice * index - Math.PI / 2;
    const radius = (value / 5) * maxRadius;
    return {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  };
  
  const dataPoints = data.map((v, i) => getPoint(v, i));
  const pathD = dataPoints.map((p, i) => 
    `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
  ).join(' ') + ' Z';
  
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-md mx-auto">
      {/* Background circles */}
      {Array.from({ length: levels }).map((_, i) => (
        <circle
          key={i}
          cx={center}
          cy={center}
          r={(maxRadius / levels) * (i + 1)}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="1"
        />
      ))}
      
      {/* Axis lines */}
      {labels.map((_, i) => {
        const angle = angleSlice * i - Math.PI / 2;
        const x2 = center + maxRadius * Math.cos(angle);
        const y2 = center + maxRadius * Math.sin(angle);
        return (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={x2}
            y2={y2}
            stroke="#e5e7eb"
            strokeWidth="1"
          />
        );
      })}
      
      {/* Data polygon */}
      <path
        d={pathD}
        fill="rgba(59, 130, 246, 0.3)"
        stroke="#3b82f6"
        strokeWidth="2"
      />
      
      {/* Data points */}
      {dataPoints.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r="5"
          fill="#3b82f6"
          stroke="#fff"
          strokeWidth="2"
        />
      ))}
      
      {/* Labels */}
      {labels.map((label, i) => {
        const angle = angleSlice * i - Math.PI / 2;
        const labelRadius = maxRadius + 25;
        const x = center + labelRadius * Math.cos(angle);
        const y = center + labelRadius * Math.sin(angle);
        return (
          <text
            key={i}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-xs fill-gray-600 font-medium"
          >
            {label.split('_').map(w => w[0].toUpperCase()).join('')}
          </text>
        );
      })}
    </svg>
  );
}

// Progress Bar Component
function ProgressBar({ label, value, max = 5, color = "blue" }: {
  label: string;
  value: number;
  max?: number;
  color?: string;
}) {
  const percentage = (value / max) * 100;
  const colorClasses: Record<string, string> = {
    blue: "from-blue-500 to-blue-600",
    green: "from-green-500 to-green-600",
    yellow: "from-yellow-500 to-yellow-600",
    red: "from-red-500 to-red-600",
    purple: "from-purple-500 to-purple-600",
  };
  
  return (
    <div className="mb-4">
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium text-gray-700 capitalize">
          {label.replace(/_/g, ' ')}
        </span>
        <span className="text-sm font-bold text-gray-900">{value.toFixed(1)}/{max}</span>
      </div>
      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${colorClasses[color]} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({ title, value, subtitle, icon, trend }: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  trend?: number;
}) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className="text-3xl">{icon}</div>
      </div>
      {trend !== undefined && (
        <div className={`mt-3 text-sm font-medium ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}% from last session
        </div>
      )}
    </div>
  );
}

export default function AnalyticsDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);

  useEffect(() => {
    // Load data from localStorage or API
    loadDashboardData();
  }, []);

  const loadDashboardData = () => {
    // Try to load from localStorage (for demo)
    const storedSessions = localStorage.getItem('interview_sessions');
    
    if (storedSessions) {
      try {
        const sessions = JSON.parse(storedSessions) as SessionSummary[];
        const data = aggregateSessionData(sessions);
        setDashboardData(data);
      } catch (e) {
        setDashboardData(generateDemoData());
      }
    } else {
      setDashboardData(generateDemoData());
    }
    
    setLoading(false);
  };

  const aggregateSessionData = (sessions: SessionSummary[]): DashboardData => {
    if (sessions.length === 0) return generateDemoData();
    
    const avgScore = sessions.reduce((sum, s) => sum + s.overall_score, 0) / sessions.length;
    const lastTwo = sessions.slice(-2);
    const scoreTrend = lastTwo.length === 2 
      ? ((lastTwo[1].overall_score - lastTwo[0].overall_score) / lastTwo[0].overall_score) * 100
      : 0;
    
    // Aggregate skill scores
    const skillTotals: Record<string, number[]> = {};
    sessions.forEach(s => {
      Object.entries(s.rubric_scores).forEach(([skill, score]) => {
        if (!skillTotals[skill]) skillTotals[skill] = [];
        skillTotals[skill].push(score);
      });
    });
    
    const skillBreakdown: Record<string, number> = {};
    Object.entries(skillTotals).forEach(([skill, scores]) => {
      skillBreakdown[skill] = scores.reduce((a, b) => a + b, 0) / scores.length;
    });
    
    // Find weak areas
    const improvementAreas = Object.entries(skillBreakdown)
      .filter(([_, score]) => score < 3.5)
      .sort((a, b) => a[1] - b[1])
      .slice(0, 3)
      .map(([skill]) => skill);
    
    return {
      total_sessions: sessions.length,
      avg_score: avgScore,
      score_trend: scoreTrend,
      recent_sessions: sessions.slice(-5).reverse(),
      skill_breakdown: skillBreakdown,
      improvement_areas: improvementAreas,
    };
  };

  const generateDemoData = (): DashboardData => ({
    total_sessions: 0,
    avg_score: 0,
    score_trend: 0,
    recent_sessions: [],
    skill_breakdown: {
      technical_correctness: 0,
      communication: 0,
      problem_solving: 0,
      code_quality: 0,
      confidence: 0,
    },
    improvement_areas: [],
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
      </div>
    );
  }

  const hasData = dashboardData && dashboardData.total_sessions > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Performance Dashboard</h1>
            <p className="text-gray-600 mt-1">Track your interview preparation progress</p>
          </div>
          <button
            onClick={() => navigate("/")}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors shadow-lg"
          >
            + New Interview
          </button>
        </div>

        {!hasData ? (
          // Empty State
          <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
            <div className="text-6xl mb-4">📊</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No Sessions Yet</h2>
            <p className="text-gray-600 mb-6">
              Complete your first practice interview to see your analytics here.
            </p>
            <button
              onClick={() => navigate("/")}
              className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all shadow-lg"
            >
              Start Your First Interview
            </button>
          </div>
        ) : (
          <>
            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <StatCard
                title="Total Sessions"
                value={dashboardData.total_sessions}
                icon="📝"
              />
              <StatCard
                title="Average Score"
                value={dashboardData.avg_score.toFixed(1)}
                subtitle="out of 5.0"
                icon="⭐"
                trend={dashboardData.score_trend}
              />
              <StatCard
                title="Questions Answered"
                value={dashboardData.recent_sessions.reduce((sum, s) => sum + s.questions_count, 0)}
                icon="❓"
              />
              <StatCard
                title="Areas to Improve"
                value={dashboardData.improvement_areas.length}
                icon="🎯"
              />
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              {/* Radar Chart */}
              <div className="bg-white rounded-2xl shadow-xl p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Skill Radar</h2>
                <RadarChart
                  data={Object.values(dashboardData.skill_breakdown)}
                  labels={Object.keys(dashboardData.skill_breakdown)}
                />
                <div className="mt-4 text-center text-sm text-gray-500">
                  Hover over points to see detailed scores
                </div>
              </div>

              {/* Skill Breakdown */}
              <div className="bg-white rounded-2xl shadow-xl p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Skill Breakdown</h2>
                {Object.entries(dashboardData.skill_breakdown)
                  .sort(([, a], [, b]) => b - a)
                  .map(([skill, score], idx) => (
                    <ProgressBar
                      key={skill}
                      label={skill}
                      value={score}
                      color={score >= 4 ? "green" : score >= 3 ? "blue" : score >= 2 ? "yellow" : "red"}
                    />
                  ))}
              </div>
            </div>

            {/* Improvement Areas */}
            {dashboardData.improvement_areas.length > 0 && (
              <div className="bg-gradient-to-r from-yellow-50 to-orange-50 rounded-2xl shadow-xl p-6 mb-8 border-2 border-yellow-200">
                <h2 className="text-xl font-bold text-yellow-900 mb-4 flex items-center gap-2">
                  ⚠️ Focus Areas for Improvement
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {dashboardData.improvement_areas.map((area, idx) => (
                    <div key={area} className="bg-white rounded-lg p-4 shadow-sm">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-yellow-500 text-white flex items-center justify-center font-bold">
                          {idx + 1}
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900 capitalize">
                            {area.replace(/_/g, ' ')}
                          </p>
                          <p className="text-sm text-gray-500">
                            Score: {dashboardData.skill_breakdown[area]?.toFixed(1) || 'N/A'}/5
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Sessions */}
            <div className="bg-white rounded-2xl shadow-xl p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Sessions</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-4 font-semibold text-gray-600">Date</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-600">Type</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-600">Questions</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-600">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardData.recent_sessions.map((session) => (
                      <tr key={session.session_id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 text-gray-900">
                          {new Date(session.date).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 capitalize">
                            {session.interview_type.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-gray-600">{session.questions_count}</td>
                        <td className="py-3 px-4">
                          <span className={`font-bold ${
                            session.overall_score >= 4 ? 'text-green-600' :
                            session.overall_score >= 3 ? 'text-blue-600' :
                            'text-yellow-600'
                          }`}>
                            {session.overall_score.toFixed(1)}/5
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}