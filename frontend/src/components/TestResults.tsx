// frontend/src/components/TestResults.tsx
//
// Test-run panel for coding questions.
//
// Status is carried by a small marker and a one-word label, not by flooding the
// row with colour. Earlier this panel filled each result with bg-green-900/30 or
// bg-red-900/30 on a hardcoded slate, which read as loud next to the rest of the
// themed UI. Rows now sit on normal surfaces with a 2px status rail, so a long
// list of results stays calm and scannable.

import { AlertTriangle, Check, Clock, Hammer, HelpCircle, X, Zap } from "lucide-react";

interface TestResult {
  test_case_index: number;
  description: string;
  is_hidden: boolean;
  passed: boolean;
  status: string;
  expected_output: string;
  actual_output: string;
  error?: string;
  time?: number;
  memory?: number;
}

interface TestResultsProps {
  results: {
    total_tests: number;
    passed: number;
    failed: number;
    errors: number;
    pass_rate: number;
    total_time: number;
    max_memory: number;
    test_results: TestResult[];
    all_passed: boolean;
  } | null;
  loading?: boolean;
}

/** Status marker, label and accent rail for one result row. */
function statusOf(status: string, passed: boolean) {
  if (passed) {
    return { Icon: Check, label: "Passed", tone: "var(--success)" };
  }
  switch (status) {
    case "compilation_error":
      return { Icon: Hammer, label: "Compile error", tone: "var(--warning)" };
    case "runtime_error":
      return { Icon: Zap, label: "Runtime error", tone: "var(--warning)" };
    case "time_limit_exceeded":
      return { Icon: Clock, label: "Timed out", tone: "var(--warning)" };
    case "wrong_answer":
      return { Icon: X, label: "Wrong output", tone: "var(--error)" };
    default:
      return { Icon: HelpCircle, label: "Unknown", tone: "var(--text-muted)" };
  }
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)]">
      {children}
    </div>
  );
}

export default function TestResults({ results, loading }: TestResultsProps) {
  if (loading) {
    return (
      <Shell>
        <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
          <p className="text-sm font-medium text-[var(--text-secondary)]">Running tests…</p>
        </div>
      </Shell>
    );
  }

  if (!results) {
    return (
      <Shell>
        <div className="px-6 py-10 text-center">
          <p className="text-sm text-[var(--text-muted)]">Run your code to see test results.</p>
        </div>
      </Shell>
    );
  }

  const allPassed = results.all_passed;
  // One accent for the whole header rather than a full-bleed colour wash.
  const headerTone = allPassed ? "var(--success)" : "var(--error)";

  return (
    <Shell>
      {/* Summary */}
      <div className="border-b border-[var(--border)] px-5 py-4">
        <div className="mb-2.5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ background: headerTone }}
              aria-hidden
            />
            <h3 className="text-sm font-semibold text-[var(--text)]">Test results</h3>
          </div>
          <span className="font-mono text-sm font-semibold" style={{ color: headerTone }}>
            {results.passed}
            <span className="text-[var(--text-muted)]">/{results.total_tests}</span>
          </span>
        </div>

        {/* Pass-rate rail: one thin bar instead of a coloured background */}
        <div className="mb-3 h-1 overflow-hidden rounded-full bg-[var(--surface-3)]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${Math.max(0, Math.min(100, results.pass_rate))}%`, background: headerTone }}
          />
        </div>

        <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--text-muted)]">
          <span>
            Pass rate <b className="font-mono font-medium text-[var(--text-secondary)]">{results.pass_rate.toFixed(0)}%</b>
          </span>
          <span>
            Time <b className="font-mono font-medium text-[var(--text-secondary)]">{results.total_time.toFixed(3)}s</b>
          </span>
          <span>
            Memory <b className="font-mono font-medium text-[var(--text-secondary)]">{(results.max_memory / 1024).toFixed(1)} MB</b>
          </span>
        </div>
      </div>

      {/* Test cases */}
      <div className="max-h-96 divide-y divide-[var(--border)] overflow-y-auto">
        {results.test_results.map((test, idx) => {
          const { Icon, label, tone } = statusOf(test.status, test.passed);
          return (
            <div key={idx} className="relative px-5 py-3.5 pl-6">
              {/* Status rail */}
              <span
                className="absolute left-0 top-0 h-full w-0.5"
                style={{ background: tone }}
                aria-hidden
              />

              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <Icon size={14} style={{ color: tone }} className="shrink-0" aria-hidden />
                  <span className="truncate text-sm font-medium text-[var(--text)]">
                    {test.description || `Test case ${test.test_case_index + 1}`}
                  </span>
                  {test.is_hidden && (
                    <span className="shrink-0 rounded-[var(--radius-xs)] bg-[var(--surface-3)] px-1.5 py-0.5 text-2xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
                      Hidden
                    </span>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-xs font-medium" style={{ color: tone }}>
                    {label}
                  </span>
                  {test.time != null && (
                    <span className="font-mono text-xs text-[var(--text-muted)]">
                      {test.time.toFixed(3)}s
                    </span>
                  )}
                </div>
              </div>

              {!test.is_hidden && !test.passed && (
                <div className="mt-2.5 space-y-2">
                  {test.status === "wrong_answer" && (
                    <div className="grid gap-2 sm:grid-cols-2">
                      <div>
                        <p className="mb-1 text-2xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
                          Expected
                        </p>
                        <pre className="overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-secondary)]">
                          {test.expected_output}
                        </pre>
                      </div>
                      <div>
                        <p className="mb-1 text-2xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
                          Received
                        </p>
                        <pre className="overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-secondary)]">
                          {test.actual_output}
                        </pre>
                      </div>
                    </div>
                  )}

                  {test.error && (
                    <div>
                      <p className="mb-1 flex items-center gap-1.5 text-2xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
                        <AlertTriangle size={11} style={{ color: tone }} aria-hidden /> Error
                      </p>
                      <pre className="overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-secondary)]">
                        {test.error}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Shell>
  );
}
