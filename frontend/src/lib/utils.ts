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

export function getScoreColor(score: number): string {
  if (score >= 4.5) return "text-green-600";
  if (score >= 4) return "text-blue-600";
  if (score >= 3) return "text-yellow-600";
  if (score >= 2) return "text-orange-600";
  return "text-red-600";
}

export function getScoreLabel(score: number): string {
  if (score >= 4.5) return "Excellent";
  if (score >= 4) return "Good";
  if (score >= 3) return "Satisfactory";
  if (score >= 2) return "Needs Improvement";
  return "Poor";
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}