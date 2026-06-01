/**
 * useProctoring - browser-native security guardrails for the candidate
 * workspace (Phase 11).
 * Location: frontend/src/hooks/useProctoring.ts
 *
 * Enforces (client side) and logs (server side) confidentiality guardrails
 * based on the assessment's permissions:
 *   - force fullscreen + detect exit
 *   - detect tab switch / window blur (visibilitychange + blur)
 *   - block copy / paste / right-click / clipboard
 * Each violation is reported to /workspace/events so the recruiter panel can
 * surface it. All free, no third-party SDKs.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { workspaceApi, type AssessmentPermissions, type ProctoringEventType } from "../api/platform";

export interface ProctoringState {
  fullscreen: boolean;
  violations: number;
  enterFullscreen: () => Promise<void>;
}

export function useProctoring(
  attemptId: string | null,
  permissions: AssessmentPermissions | null,
  active: boolean
): ProctoringState {
  const [fullscreen, setFullscreen] = useState(false);
  const [violations, setViolations] = useState(0);
  // throttle duplicate events so a single tab-switch isn't logged 5x
  const lastLogged = useRef<Record<string, number>>({});

  const log = useCallback(
    (type: ProctoringEventType, detail?: string) => {
      if (!attemptId) return;
      const now = Date.now();
      if (now - (lastLogged.current[type] || 0) < 1500) return;
      lastLogged.current[type] = now;
      setViolations((v) => v + 1);
      workspaceApi.logEvent(attemptId, type, detail).catch(() => {});
    },
    [attemptId]
  );

  const enterFullscreen = useCallback(async () => {
    try {
      await document.documentElement.requestFullscreen();
      setFullscreen(true);
    } catch {
      /* user denied — handled by detection below */
    }
  }, []);

  // Tab switch / window blur detection
  useEffect(() => {
    if (!active || !permissions?.block_tab_switch) return;
    const onVisibility = () => {
      if (document.hidden) log("tab_switch", "tab hidden");
    };
    const onBlur = () => log("tab_switch", "window blur");
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
    };
  }, [active, permissions?.block_tab_switch, log]);

  // Fullscreen exit detection
  useEffect(() => {
    if (!active || !permissions?.force_fullscreen) return;
    const onFsChange = () => {
      const isFs = !!document.fullscreenElement;
      setFullscreen(isFs);
      if (!isFs) log("fullscreen_exit", "left fullscreen");
    };
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, [active, permissions?.force_fullscreen, log]);

  // Copy / paste / context-menu blocking
  useEffect(() => {
    if (!active || !permissions?.block_copy_paste) return;
    const onCopy = (e: ClipboardEvent) => {
      e.preventDefault();
      log("copy_blocked", "copy attempt");
    };
    const onPaste = (e: ClipboardEvent) => {
      e.preventDefault();
      log("paste_blocked", "paste attempt");
    };
    const onContext = (e: MouseEvent) => e.preventDefault();
    document.addEventListener("copy", onCopy);
    document.addEventListener("paste", onPaste);
    document.addEventListener("contextmenu", onContext);
    return () => {
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("paste", onPaste);
      document.removeEventListener("contextmenu", onContext);
    };
  }, [active, permissions?.block_copy_paste, log]);

  return { fullscreen, violations, enterFullscreen };
}
