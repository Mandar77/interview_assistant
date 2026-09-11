/**
 * Utility functions for Interview Assistant
 * Location: frontend/src/lib/utils.ts
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Score helpers. Every score in the app is 0-100 and belongs to exactly one
 * evaluation engine — there is no combined rating to format.
 */
export const SCORE_MAX = 100;

export function getScoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-[var(--text-muted)]";
  if (score >= 75) return "text-[var(--success)]";
  if (score >= 60) return "text-[var(--accent)]";
  if (score >= 40) return "text-[var(--warning)]";
  return "text-[var(--error)]";
}

/** CSS colour token for a score, for inline styles and chart fills. */
export function getScoreTone(score: number | null | undefined): string {
  if (score === null || score === undefined) return "var(--text-muted)";
  if (score >= 75) return "var(--success)";
  if (score >= 60) return "var(--accent)";
  if (score >= 40) return "var(--warning)";
  return "var(--error)";
}

export function getScoreLabel(score: number | null | undefined): string {
  if (score === null || score === undefined) return "Not assessed";
  if (score >= 90) return "Exceptional";
  if (score >= 75) return "Strong";
  if (score >= 60) return "Adequate";
  if (score >= 40) return "Weak";
  return "Poor";
}

/** Format a score for display, or an em dash when it was not assessed. */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || !Number.isFinite(score)) return "—";
  return String(Math.round(score));
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}