/**
 * UI primitives — the component library for the redesign.
 * Location: frontend/src/ui/index.tsx
 *
 * One cohesive, token-driven set used across every screen. Import as:
 *   import { Button, Card, Input, Badge, EmptyState } from "../ui";
 *
 * Everything references CSS variables (see index.css), so it themes
 * automatically in light & dark with no per-component theme logic.
 */

import {
  forwardRef,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../lib/utils";

/* ───────────────────────── Button ───────────────────────── */
type BtnVariant = "primary" | "secondary" | "ghost" | "danger" | "subtle";
type BtnSize = "sm" | "md" | "lg" | "icon";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: BtnVariant;
  size?: BtnSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const btnBase =
  "relative inline-flex items-center justify-center gap-2 font-medium whitespace-nowrap " +
  "rounded-[var(--radius-sm)] transition-all duration-150 select-none cursor-pointer " +
  "focus-visible:outline-2 focus-visible:outline-[var(--ring)] focus-visible:outline-offset-2 " +
  "disabled:opacity-45 disabled:pointer-events-none active:scale-[0.98]";

const btnVariants: Record<BtnVariant, string> = {
  primary:
    "bg-[var(--accent)] text-[var(--accent-contrast)] shadow-[var(--shadow-sm)] hover:bg-[var(--accent-hover)] hover:shadow-[var(--shadow-glow)] active:bg-[var(--accent-active)]",
  secondary:
    "bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] shadow-[var(--shadow-sm)] hover:bg-[var(--surface-3)] hover:border-[var(--border-strong)]",
  ghost: "bg-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-3)] hover:text-[var(--text)]",
  subtle: "bg-[var(--accent-soft)] text-[var(--accent)] hover:brightness-110",
  danger: "bg-[var(--error)] text-white shadow-[var(--shadow-sm)] hover:opacity-90",
};

const btnSizes: Record<BtnSize, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-9.5 px-4 text-base",
  lg: "h-11 px-5 text-md",
  icon: "h-9 w-9 p-0",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", loading, leftIcon, rightIcon, className, children, disabled, ...props }, ref) => (
    <button ref={ref} disabled={disabled || loading} className={cn(btnBase, btnVariants[variant], btnSizes[size], className)} {...props}>
      {loading && <Loader2 className="animate-spin" size={size === "sm" ? 14 : 16} />}
      {!loading && leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  )
);
Button.displayName = "Button";

/* ───────────────────────── Card ───────────────────────── */
export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
  elevated?: boolean;
}
export function Card({ interactive, elevated, className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)]",
        elevated ? "shadow-[var(--shadow-md)]" : "shadow-[var(--shadow-sm)]",
        interactive &&
          "transition-all duration-200 hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 pt-5 pb-3", className)} {...props} />;
}
export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4", className)} {...props} />;
}
export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-lg font-semibold text-[var(--text)]", className)} {...props} />;
}

/* ───────────────────────── Input / Textarea / Select ───────────────────────── */
const fieldBase =
  "w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] " +
  "text-[var(--text)] placeholder:text-[var(--text-muted)] transition-all duration-150 " +
  "focus:border-[var(--accent)] focus:bg-[var(--surface)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] " +
  "disabled:opacity-50 disabled:cursor-not-allowed";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref} className={cn(fieldBase, "h-9.5 px-3 text-base", className)} {...props} />
  )
);
Input.displayName = "Input";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea ref={ref} className={cn(fieldBase, "px-3 py-2.5 text-base resize-y leading-relaxed", className)} {...props} />
  )
);
Textarea.displayName = "Textarea";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select ref={ref} className={cn(fieldBase, "h-9.5 px-3 text-base cursor-pointer", className)} {...props}>
      {children}
    </select>
  )
);
Select.displayName = "Select";

export function Label({ className, ...props }: HTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("block text-sm font-medium text-[var(--text-secondary)] mb-1.5", className)} {...props} />;
}

/* ───────────────────────── Badge ───────────────────────── */
type BadgeTone = "neutral" | "accent" | "success" | "warning" | "error" | "info";
const badgeTones: Record<BadgeTone, string> = {
  neutral: "bg-[var(--surface-3)] text-[var(--text-secondary)] border-[var(--border)]",
  accent: "bg-[var(--accent-soft)] text-[var(--accent)] border-transparent",
  success: "bg-[var(--success-soft)] text-[var(--success)] border-transparent",
  warning: "bg-[var(--warning-soft)] text-[var(--warning)] border-transparent",
  error: "bg-[var(--error-soft)] text-[var(--error)] border-transparent",
  info: "bg-[var(--info-soft)] text-[var(--info)] border-transparent",
};
export function Badge({ tone = "neutral", className, children, dot }: { tone?: BadgeTone; className?: string; children: ReactNode; dot?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", badgeTones[tone], className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

/* ───────────────────────── Spinner / Skeleton ───────────────────────── */
export function Spinner({ size = 20, className = "" }: { size?: number; className?: string }) {
  return <Loader2 className={cn("animate-spin text-[var(--accent)]", className)} size={size} />;
}
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded-[var(--radius-sm)]", className)} />;
}
export function PageLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 animate-fade-in-fast">
      <Spinner size={28} />
      <p className="text-sm text-[var(--text-muted)]">{label}</p>
    </div>
  );
}

/* ───────────────────────── EmptyState ───────────────────────── */
export function EmptyState({
  icon, title, description, action,
}: { icon?: ReactNode; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[var(--radius-lg)] border border-dashed border-[var(--border-strong)] bg-[var(--surface-2)] px-8 py-16 text-center animate-fade-in">
      {icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-[var(--radius-md)] bg-[var(--surface-3)] text-[var(--text-muted)]">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-[var(--text)]">{title}</h3>
      {description && <p className="mt-1.5 max-w-sm text-sm text-[var(--text-muted)]">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

/* ───────────────────────── Modal ───────────────────────── */
export function Modal({
  open, onClose, title, children, footer, size = "md",
}: {
  open: boolean; onClose: () => void; title?: ReactNode; children: ReactNode; footer?: ReactNode;
  size?: "sm" | "md" | "lg";
}) {
  if (!open) return null;
  const maxW = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl" }[size];
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in-fast"
      style={{ background: "var(--overlay)", backdropFilter: "blur(2px)" }}
      onClick={onClose}
    >
      <div
        className={cn("w-full rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-lg)] animate-scale-in", maxW)}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
            <h2 className="text-lg font-semibold text-[var(--text)]">{title}</h2>
            <button onClick={onClose} className="rounded-[var(--radius-xs)] p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text)]">✕</button>
          </div>
        )}
        <div className="px-6 py-5">{children}</div>
        {footer && <div className="flex justify-end gap-3 border-t border-[var(--border)] px-6 py-4">{footer}</div>}
      </div>
    </div>
  );
}

/* ───────────────────────── Section heading ───────────────────────── */
export function SectionTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-4 flex items-end justify-between">
      <h2 className="text-xl font-semibold text-[var(--text)]">{children}</h2>
      {hint && <span className="text-sm text-[var(--text-muted)]">{hint}</span>}
    </div>
  );
}
