/**
 * AppShell — consistent chrome for authenticated portals (employer + candidate).
 * Location: frontend/src/ui/AppShell.tsx
 *
 * A slim sticky top bar with brand, primary nav, theme toggle, and the user
 * menu. Content sits in a centered, breathing container. Responsive: nav
 * collapses to icons on small screens.
 */

import { type ReactNode } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { cn } from "../lib/utils";
import ThemeToggle from "../theme/ThemeToggle";
import { useAuth } from "../auth/AuthContext";

export interface NavItem {
  label: string;
  to: string;
  icon?: ReactNode;
}

export function BrandMark({ size = 24 }: { size?: number }) {
  return (
    <div
      className="flex items-center justify-center rounded-[var(--radius-sm)] bg-[var(--accent)] text-[var(--accent-contrast)] font-bold"
      style={{ width: size, height: size, fontSize: size * 0.55 }}
    >
      ◆
    </div>
  );
}

export default function AppShell({
  nav = [],
  title,
  children,
  maxWidth = "max-w-6xl",
}: {
  nav?: NavItem[];
  title?: string;
  children: ReactNode;
  maxWidth?: string;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="sticky top-0 z-40 border-b border-[var(--border)] glass">
        <div className={cn("mx-auto flex h-14 items-center gap-4 px-5", "max-w-7xl")}>
          {/* Brand */}
          <button
            onClick={() => navigate(user?.role === "candidate" ? "/workspace" : "/employer")}
            className="flex items-center gap-2.5 transition-opacity hover:opacity-80"
          >
            <BrandMark />
            <span className="text-base font-semibold tracking-tight text-[var(--text)]">
              {title || "Interview Assistant"}
            </span>
          </button>

          {/* Primary nav */}
          <nav className="ml-2 hidden items-center gap-1 md:flex">
            {nav.map((item) => {
              const active = location.pathname === item.to;
              return (
                <button
                  key={item.to}
                  onClick={() => navigate(item.to)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-[var(--radius-sm)] px-3 py-1.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-[var(--surface-3)] text-[var(--text)]"
                      : "text-[var(--text-muted)] hover:bg-[var(--surface-3)] hover:text-[var(--text)]"
                  )}
                >
                  {item.icon}
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            {user && (
              <div className="flex items-center gap-2 pl-1">
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-medium leading-tight text-[var(--text)]">
                    {user.full_name || user.username}
                  </p>
                  <p className="text-2xs uppercase tracking-wide text-[var(--text-muted)]">
                    {user.role.replace("_", " ")}
                  </p>
                </div>
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-soft)] text-sm font-semibold text-[var(--accent)]">
                  {(user.username[0] || "?").toUpperCase()}
                </div>
                <button
                  onClick={logout}
                  className="rounded-[var(--radius-sm)] px-2.5 py-1.5 text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text)]"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Mobile nav row */}
        {nav.length > 0 && (
          <nav className="flex items-center gap-1 overflow-x-auto border-t border-[var(--border)] px-3 py-2 md:hidden">
            {nav.map((item) => {
              const active = location.pathname === item.to;
              return (
                <button
                  key={item.to}
                  onClick={() => navigate(item.to)}
                  className={cn(
                    "flex shrink-0 items-center gap-1.5 rounded-[var(--radius-sm)] px-3 py-1.5 text-sm font-medium transition-colors",
                    active ? "bg-[var(--surface-3)] text-[var(--text)]" : "text-[var(--text-muted)]"
                  )}
                >
                  {item.icon}
                  {item.label}
                </button>
              );
            })}
          </nav>
        )}
      </header>

      <main className={cn("mx-auto px-5 py-8", maxWidth)}>{children}</main>
    </div>
  );
}
