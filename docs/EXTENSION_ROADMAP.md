# Interview Assistant — Extension Roadmap (Phases 9–14)

> **Status of the original 12-week roadmap (Phases 1–8): ✅ COMPLETE & VERIFIED.**
> All 6 backend microservices (question, speech, evaluation, feedback, code-execution, vision),
> the full multi-modal React frontend (MediaPipe body language, Monaco code editor, diagram
> canvas, screen capture), the AWS CDK infra (EC2 + Ollama + S3 + CloudFront), and the
> end-to-end test suite (5 suites passing) are all in place. The README/PROGRESS_ANALYSIS.md
> were stale; this document supersedes them for forward planning.

This roadmap turns the single-user **mock-interview coaching tool** into a two-sided
**hiring assessment platform** with an employer side ("Assessment Studio") and a candidate
side ("Interview Workspace"), plus org culture grounding and recruiting-workflow modules.

The guiding constraint remains the original project's: **100% free / open-source / free-tier**.

---

## 0. Architectural Principles

1. **Backward compatible.** The existing anonymous "enter a JD → mock interview → results"
   flow must keep working without login. New features are additive.
2. **Multi-tenant from day one.** Every new persisted row is scoped to an `org_id` (employer)
   or a `user_id` (candidate). Data isolation is enforced at the query layer.
3. **Reuse the existing engines.** Question generation, evaluation, feedback, code execution,
   vision, and speech services are already built — the portals *orchestrate* them, they do not
   reimplement them.
4. **Storage abstraction.** A repository layer hides whether data lives in JSON files (dev
   default, already used) or Postgres/Supabase (prod). No service talks to the filesystem or DB
   directly anymore.
5. **Security guardrails are client-enforced + server-verified.** Proctoring signals (tab
   switch, face lost, fullscreen exit) are detected in the browser and logged to the backend as
   immutable events; the recruiter panel surfaces them.

---

## Phase 9 — Platform Foundation (Auth, Tenancy, Persistence)

**Goal:** Introduce accounts, organizations, and a real persistence layer without breaking the
anonymous mock flow.

### Backend
- `auth_service/` — JWT-based auth (PyJWT + passlib bcrypt). Roles: `candidate`, `employer_admin`,
  `employer_member`. Anonymous sessions get a synthetic guest identity.
- `db/` — SQLAlchemy 2.0 async models + a `repository` abstraction with two backends:
  - `JsonRepository` (default, dev — extends today's `data/` JSON approach)
  - `SqlRepository` (Supabase/Postgres via `asyncpg`, prod)
  - Selected by `STORAGE_BACKEND` env var (`json` | `sql`).
- Core tables/models: `organizations`, `users`, `memberships`, `audit_log`.

### Frontend
- `AuthContext` + `useAuth` hook, token storage, `<ProtectedRoute>` wrapper.
- Login / Signup pages, role-aware top-nav, org switcher.

**Done when:** A user can sign up as employer or candidate, log in, and the anonymous mock flow
still works untouched.

---

## Phase 10 — Employer Portal: "Assessment Studio"

**Goal:** Employers build, configure, and assign assessments.

### Data model
- `assessments` (org-scoped): title, description, status (draft/published/archived).
- `assessment_sections` → ordered list of `questions` of mixed types:
  `mcq | coding | video_answer | system_design | file_upload | live_interview`.
- `assessment_permissions`: mic / cam / screen / fullscreen / no-tab-switch toggles.
- `evaluation_rules`: per-section auto-scoring (MCQ/coding) vs AI-scoring (spoken + body language).
- `setup_guides`: YouTube unlisted URL or rich-text instructions.

### Backend (`assessment_service/`)
- CRUD for assessments / sections / questions.
- `POST /generate-from-jd` — reuse `question_service.generator` to auto-draft questions from a JD.
- `POST /{id}/assign` — assign to candidate usernames (collected at application time).
- Org-scoped queries everywhere → **question banks & results never leak across orgs or into the
  candidate mock portal.**

### Frontend (employer)
- Drag-and-configure assessment builder (ShadCN + dnd-kit).
- Question-type palette, per-question config drawer, permissions matrix, scoring rules, setup-guide editor.
- Assignment screen (paste/select usernames), assignment status table.

**Done when:** An employer can build a mixed-type assessment, set permissions/scoring, and assign
it to a candidate username; the data is isolated to their org.

---

## Phase 11 — Candidate Portal: "Interview Workspace" + Proctoring

**Goal:** A secure test-taking environment that runs both unlimited mock interviews and
employer-assigned assessments.

### Backend (`proctoring_service/` + assessment attempt flow)
- `assessment_attempts`: candidate × assessment, status, started/submitted timestamps.
- `proctoring_events` (append-only): tab_switch, fullscreen_exit, face_lost, mic_muted,
  permission_revoked, paste_blocked, copy_blocked, multi_face_detected — each with timestamp.
- Attempt submission aggregates per-question answers and triggers the existing evaluation engine.

### Frontend (candidate) — security guardrails (all free, browser-native)
- Disable copy/paste/right-click/clipboard inside the workspace.
- Force fullscreen test mode; detect exit via `fullscreenchange`.
- Tab-switch / blur detection via `visibilitychange` + `window.blur`.
- Face presence via existing MediaPipe Face Mesh → blur the test if no face; camera-confidence tracking.
- Watermark overlay (candidate id + timestamp) during the assessment.
- Permission-revocation detection on the active `MediaStream`.

**Done when:** A candidate can launch an assigned assessment in a locked-down fullscreen
workspace; proctoring violations are logged server-side; results are visible to the employer only,
while personal mock results stay in the candidate's history.

---

## Phase 12 — Org Culture Crawler & Question Grounding

**Goal:** Personalize question generation and value-alignment scoring using a company's public
culture pages.

### Backend (`culture_service/`)
- Scraper: BeautifulSoup + `httpx` (Jina Reader fallback) over **public** pages only
  (about / values / careers / CEO letters / CSR / blog). Respect `robots.txt`.
- Chunk + embed with Ollama `nomic-embed-text`; store in **FAISS** (local, free) keyed by `org_id`.
- `POST /crawl` (employer-triggered), `GET /culture/{org_id}` summary, `query(org_id, k)` retrieval API.
- Integrate into `question_service.generator`: inject retrieved culture context so questions align
  with company tone/principles.
- Integrate into `evaluation_service`: an optional "values alignment / relevance" signal
  (relevance, **not** bias).

**Done when:** An employer can crawl their culture pages; generated questions reflect company
values; evaluation can report value-alignment relevance.

---

## Phase 13 — Recruiting Workflow Modules (Product Expansions)

Each is independent and free-tier friendly.

- **A. ATS Integration Simulator** (`ats_service/`): mock Greenhouse/Workday/BambooHR webhook
  receiver; accept candidate-profile JSON → auto-trigger assessment → log result for the dashboard.
- **B. Coding Interview Evaluator:** already largely covered by `code_execution_service`; expose a
  candidate-paste/shared-snippet entry point that returns compile status, test pass %, quality
  summary, runtime/memory (Judge0 sandbox, already wired).
- **C. Recruiter Decision Panel:** UI panel per candidate — score summary, triggered proctoring
  flags, verdict buttons (Advance / Schedule live / Reject-with-auto-email).
- **D. Automated Candidate Communication** (`comms_service/`): invite emails, assessment links,
  result notifications, follow-ups (Gmail SMTP / SES sandbox, free).
- **E. Role-Based Assessment Templates:** reusable flows ("SDE Intern 45min", "Backend L3 60min",
  "System Design 40min", "DSA OA 90min") with permission/scoring/question-source presets.
- **F. Live Interview Scheduler** (`scheduler_service/`): React calendar UI, slot persistence,
  mock Zoom/Teams meeting-link generator.

**Done when:** An employer can run a candidate from ATS-webhook intake → assessment → recruiter
decision → auto-email, and schedule a live round, all within the platform.

---

## Phase 14 — Hardening, Analytics & Deployment

- Extend the AWS CDK stack: Supabase/RDS Postgres, S3 for recordings/screenshots/logs, optional
  Docker-on-EC2 code-execution sandbox.
- Employer analytics: funnel, per-assessment pass rates, flag frequency, score distributions
  (extends existing `AnalyticsDashboard`).
- Security review, rate limiting, audit logging, data-retention controls.
- Full regression + new e2e suites for the two-sided flows.

---

## Suggested Free Stack (per the brief)

| Concern | Choice |
|---|---|
| Employer/Candidate UI | React + Tailwind + ShadCN (existing frontend) |
| Backend | FastAPI (existing) — Lambda container / EC2 free tier |
| Recordings/screenshots/logs | S3 free tier |
| Relational DB | Supabase Postgres free tier (SQLAlchemy + asyncpg) |
| Vectors (culture) | FAISS (local) / Supabase pgvector |
| Code execution | Judge0 in Docker sandbox (already integrated) |
| LLM / embeddings | Ollama local (existing) |
| Email | Gmail SMTP / SES sandbox |

---

## Build Order (dependency-aware)

```
Phase 9 (auth+tenancy+persistence)   ← everything depends on this
   ├─ Phase 10 (Employer Assessment Studio)
   │     ├─ Phase 11 (Candidate Workspace + proctoring)   ← needs assigned assessments
   │     └─ Phase 13E (templates)                          ← needs assessment model
   ├─ Phase 12 (Culture crawler)                           ← enhances question gen
   └─ Phase 13 (ATS sim, recruiter panel, comms, scheduler)
Phase 14 (hardening + analytics + deploy)                  ← last
```

Implementation in this repo proceeds incrementally; each phase keeps the app importable and the
existing tests green.
