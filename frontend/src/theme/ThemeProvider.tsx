/**
 * ThemeProvider — light/dark theme with persistence + system preference.
 * Location: frontend/src/theme/ThemeProvider.tsx
 *
 * - Default: follows the OS preference ("system").
 * - User choice persists to localStorage and toggles `.dark` on <html>.
 * - A small inline script in index.html applies the class before first paint
 *   to avoid a flash of the wrong theme (FOUC).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type ThemeChoice = "light" | "dark" | "system";
type ResolvedTheme = "light" | "dark";

interface ThemeState {
  theme: ThemeChoice;          // user's stored choice
  resolved: ResolvedTheme;     // what's actually applied
  setTheme: (t: ThemeChoice) => void;
  toggle: () => void;          // cycles light <-> dark
}

const STORAGE_KEY = "ia_theme";
const ThemeContext = createContext<ThemeState | undefined>(undefined);

function systemPrefersDark(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? true;
}

function resolve(choice: ThemeChoice): ResolvedTheme {
  if (choice === "system") return systemPrefersDark() ? "dark" : "light";
  return choice;
}

function apply(resolved: ResolvedTheme) {
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeChoice>(() => {
    return (localStorage.getItem(STORAGE_KEY) as ThemeChoice | null) ?? "system";
  });
  const [resolved, setResolved] = useState<ResolvedTheme>(() => resolve(theme));

  // Apply + persist whenever the choice changes.
  useEffect(() => {
    const r = resolve(theme);
    setResolved(r);
    apply(r);
    if (theme === "system") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  // React to OS changes while on "system".
  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const r = systemPrefersDark() ? "dark" : "light";
      setResolved(r);
      apply(r);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((t: ThemeChoice) => setThemeState(t), []);
  const toggle = useCallback(
    () => setThemeState(resolve(theme) === "dark" ? "light" : "dark"),
    [theme]
  );

  return (
    <ThemeContext.Provider value={{ theme, resolved, setTheme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}
