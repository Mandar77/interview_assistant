/**
 * Platform API client + types (Phases 9-13).
 * Location: frontend/src/api/platform.ts
 *
 * Reuses the shared axios instance from client.ts and attaches the JWT bearer
 * token (stored in localStorage) on every request. Keeps the anonymous
 * mock-interview flow untouched: requests without a token simply omit the
 * Authorization header.
 */

import { api } from "./client";

const TOKEN_KEY = "ia_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Attach bearer token to all requests when present.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type UserRole = "candidate" | "employer_admin" | "employer_member";

export interface PublicUser {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  role: UserRole;
  org_id?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: PublicUser;
}

export type QuestionType =
  | "mcq"
  | "coding"
  | "video_answer"
  | "system_design"
  | "file_upload"
  | "live_interview";

export type ScoringMode = "auto" | "ai" | "manual";

export interface MCQOption {
  id: string;
  text: string;
  is_correct?: boolean;
}

export interface AssessmentQuestion {
  id: string;
  type: QuestionType;
  prompt: string;
  options?: MCQOption[];
  starter_code?: Record<string, string>;
  test_cases?: any[];
  expected_duration_mins: number;
  scoring_mode: ScoringMode;
  max_score: number;
  skill_tags: string[];
  evaluation_criteria: string[];
}

export interface AssessmentSection {
  id: string;
  title: string;
  questions: AssessmentQuestion[];
}

export interface AssessmentPermissions {
  require_mic?: boolean;
  require_camera?: boolean;
  require_screen_share?: boolean;
  force_fullscreen?: boolean;
  block_tab_switch?: boolean;
  block_copy_paste?: boolean;
  watermark?: boolean;
}

export interface Assessment {
  id: string;
  org_id: string;
  title: string;
  description?: string;
  status: "draft" | "published" | "archived";
  sections: AssessmentSection[];
  permissions: AssessmentPermissions;
  setup_guides: any[];
  job_description?: string;
  created_at: string;
}

export interface Assignment {
  id: string;
  assessment_id: string;
  org_id: string;
  candidate_username: string;
  candidate_user_id?: string | null;
  status: string;
  invited_at: string;
}

export interface CandidatePanelRow {
  attempt_id: string;
  assessment_id: string;
  candidate_username: string;
  status: string;
  /** Percentage of available assessment points earned, 0-100. Not a blended rating. */
  overall_score: number | null;
  proctoring_summary: Record<string, number>;
  submitted_at: string | null;
  verdict: string;
}

export type ProctoringEventType =
  | "tab_switch"
  | "fullscreen_exit"
  | "face_lost"
  | "multi_face_detected"
  | "mic_muted"
  | "permission_revoked"
  | "copy_blocked"
  | "paste_blocked";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const authApi = {
  signup: (body: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
    role: UserRole;
    organization_name?: string;
  }) => api.post<TokenResponse>("/auth/signup", body).then((r) => r.data),

  login: (body: { email_or_username: string; password: string }) =>
    api.post<TokenResponse>("/auth/login", body).then((r) => r.data),

  me: () => api.get<PublicUser>("/auth/me").then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Employer - assessments
// ---------------------------------------------------------------------------

export const assessmentApi = {
  list: () => api.get<Assessment[]>("/assessments").then((r) => r.data),
  get: (id: string) => api.get<Assessment>(`/assessments/${id}`).then((r) => r.data),
  create: (body: { title: string; description?: string; job_description?: string }) =>
    api.post<Assessment>("/assessments", body).then((r) => r.data),
  update: (id: string, body: Partial<Assessment>) =>
    api.patch<Assessment>(`/assessments/${id}`, body).then((r) => r.data),
  remove: (id: string) => api.delete(`/assessments/${id}`).then((r) => r.data),
  generateFromJd: (
    id: string,
    body: {
      job_description: string;
      interview_type?: string;
      difficulty?: string;
      num_questions?: number;
      section_title?: string;
      use_culture_grounding?: boolean;
    }
  ) => api.post<Assessment>(`/assessments/${id}/generate-from-jd`, body).then((r) => r.data),
  assign: (id: string, candidate_usernames: string[], due_at?: string) =>
    api
      .post<Assignment[]>(`/assessments/${id}/assign`, { candidate_usernames, due_at })
      .then((r) => r.data),
  assignments: (id: string) =>
    api.get<Assignment[]>(`/assessments/${id}/assignments`).then((r) => r.data),
  saveAsTemplate: (id: string, name: string, description?: string) =>
    api.post(`/assessments/${id}/save-as-template`, { name, description }).then((r) => r.data),
  templates: () => api.get("/assessments/templates/list").then((r) => r.data),
  fromTemplate: (templateId: string) =>
    api.post<Assessment>(`/assessments/from-template/${templateId}`).then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Candidate - workspace
// ---------------------------------------------------------------------------

export const workspaceApi = {
  myAssignments: () => api.get("/workspace/my-assignments").then((r) => r.data),
  startAttempt: (assignment_id: string) =>
    api
      .post<{ attempt_id: string; assessment: Assessment }>("/workspace/attempts/start", {
        assignment_id,
      })
      .then((r) => r.data),
  logEvent: (attempt_id: string, type: ProctoringEventType, detail?: string) =>
    api.post("/workspace/events", { attempt_id, type, detail }).then((r) => r.data),
  submit: (attempt_id: string, answers: any[]) =>
    api
      // overall_score is the percentage of available points earned (0-100).
      .post<{ attempt_id: string; overall_score: number }>("/workspace/attempts/submit", {
        attempt_id,
        answers,
      })
      .then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Recruiter + culture + scheduler + ats
// ---------------------------------------------------------------------------

export const recruiterApi = {
  candidates: (assessment_id?: string) =>
    api
      .get<CandidatePanelRow[]>("/recruiter/candidates", {
        params: assessment_id ? { assessment_id } : {},
      })
      .then((r) => r.data),
  candidateDetail: (attempt_id: string) =>
    api.get(`/recruiter/candidates/${attempt_id}`).then((r) => r.data),
  decision: (attempt_id: string, verdict: string, note?: string, send_email = false) =>
    api
      .post("/recruiter/decision", { attempt_id, verdict, note, send_email })
      .then((r) => r.data),
  sendInvite: (body: {
    candidate_email: string;
    candidate_name: string;
    assessment_id: string;
    assignment_id?: string;
  }) => api.post("/recruiter/send-invite", body).then((r) => r.data),
};

export const cultureApi = {
  crawl: (root_url: string, max_pages = 6) =>
    api.post("/culture/crawl", { root_url, max_pages }).then((r) => r.data),
  summary: () => api.get("/culture/summary").then((r) => r.data),
};

export const schedulerApi = {
  createSlot: (body: {
    candidate_username: string;
    start_time: string;
    end_time: string;
    interviewer?: string;
    attempt_id?: string;
    provider?: string;
    send_email?: boolean;
  }) => api.post("/scheduler/slots", body).then((r) => r.data),
  listSlots: () => api.get("/scheduler/slots").then((r) => r.data),
};
