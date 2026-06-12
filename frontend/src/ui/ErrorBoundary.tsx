/**
 * ErrorBoundary — turns a render crash into a readable screen instead of a
 * blank white page. Wraps the whole app.
 * Location: frontend/src/ui/ErrorBoundary.tsx
 */

import { Component, type ReactNode } from "react";

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown) {
    // Surface to the console for debugging; in prod this is where telemetry goes.
    console.error("Render error:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[var(--background)] p-6">
          <div className="w-full max-w-md rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] p-8 text-center shadow-[var(--shadow-lg)]">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--error-soft)] text-[var(--error)] text-xl">
              !
            </div>
            <h1 className="text-lg font-semibold text-[var(--text)]">
              Something broke on this screen
            </h1>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              The page hit an unexpected error. You can reload, or head back home.
            </p>
            <pre className="mt-4 max-h-32 overflow-auto rounded-[var(--radius-sm)] bg-[var(--surface-3)] p-3 text-left text-xs text-[var(--text-secondary)]">
              {this.state.error.message}
            </pre>
            <div className="mt-6 flex justify-center gap-3">
              <button
                onClick={() => window.location.reload()}
                className="rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-contrast)] transition hover:bg-[var(--accent-hover)]"
              >
                Reload
              </button>
              <button
                onClick={() => (window.location.href = "/")}
                className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-3)]"
              >
                Go home
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
