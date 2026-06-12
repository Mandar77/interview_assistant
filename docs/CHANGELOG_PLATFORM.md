# Changelog — Hiring Platform Extension (Phases 9–13)

This document records the additive work that turned the single-user **mock
interview coaching tool** into a two-sided **hiring assessment platform**.
The original 12-week roadmap (Phases 1–8) was already complete and remains
fully functional; nothing in the anonymous mock flow changed.

## Summary

| Area | Before | After |
|---|---|---|
| API routes | 47 | **79** (+32 platform routes) |
| Accounts | none (anonymous) | candidates + employer orgs (JWT) |
| Persistence | per-session JSON files | + storage-agnostic repository (JSON/SQL) for platform data |
| Surfaces | mock interview only | + Employer "Assessment Studio" + Candidate "Interview Workspace" |
| Tests | 5 suites (need running server + Ollama) | + **in-process platform suite, 49 assertions, no external deps** |

All new code is free / open-source / free-tier, matching the project's constraint.

---

## Backend

### Phase 9 — Platform Foundation
- **`db/repository.py`** — async, collection-oriented document store with a
  `JsonRepository` (default) and a pluggable `SqlRepository` slot, selected by
  `STORAGE_BACKEND`. Atomic writes, per-collection locks, filtered `find`.
- **`models/platform_schemas.py`** — Pydantic models for orgs, users, assessments,
  attempts, proctoring, ATS, scheduling.
- **`services/auth_service/`** — bcrypt password hashing (direct `bcrypt`, not
  passlib, to avoid the bcrypt 5.x incompatibility), JWT issue/verify,
  FastAPI dependencies (`get_current_user`, `get_employer_user`, `require_roles`),
  and `/signup` `/login` `/me` routes.
- **`config/settings.py`** — added `storage_backend`, `jwt_*`, `smtp_*`, `app_base_url`.

### Phase 10 — Employer "Assessment Studio"
- **`services/assessment_service/routes.py`** — org-scoped CRUD for assessments;
  `generate-from-jd` (reuses the Phase 2 question generator); `assign` to
  candidate usernames; templates (save / list / instantiate). **Data isolation**
  enforced on every query (`org_id`).

### Phase 11 — Candidate "Interview Workspace" + Proctoring
- **`services/proctoring_service/scorer.py`** — routes each answer to the right
  engine: MCQ exact-match (deterministic), coding via the existing Judge0
  executor, AI answers via the existing rubric scorer. Degrades gracefully
  (heuristic / 0-score-with-detail) when Ollama/Judge0 are offline so the
  candidate flow never blocks.
- **`services/proctoring_service/routes.py`** — `my-assignments`, `attempts/start`
  (returns a **candidate-safe** assessment with correct-answer keys & hidden
  test cases stripped), append-only `events` log, `attempts/submit` (scores +
  aggregates proctoring flags), `attempts/{id}`.

### Phase 12 — Org Culture Crawler + Grounding
- **`services/culture_service/crawler.py`** — robots-respecting BeautifulSoup
  crawler over public culture pages; chunk + embed (Ollama `nomic-embed-text`)
  into a per-org **FAISS** index, with a keyword-retrieval fallback when
  embeddings are unavailable.
- **`services/culture_service/routes.py`** — `crawl`, `summary`, `query`.
- Integrated into `assessment_service.generate-from-jd` via
  `use_culture_grounding` (prepends retrieved culture context to the JD).

### Phase 13 — Recruiting Workflow Modules
- **`services/comms_service/`** — `mailer.py` (SMTP with log-only fallback) +
  Recruiter Decision Panel routes: `candidates`, `candidates/{id}` (per-question
  scoring + proctoring timeline), `decision` (advance/schedule/reject + auto-email),
  `send-invite`.
- **`services/ats_service/routes.py`** — mock Greenhouse/Workday/BambooHR
  `webhook` that auto-assigns an assessment and emails an invite.
- **`services/scheduler_service/routes.py`** — live-interview slots with a mock
  Meet/Zoom/Teams link generator.

### Wiring
- **`app.py`** — registered all 7 new routers under `/api/v1/{auth,assessments,
  workspace,culture,recruiter,ats,scheduler}`; updated root + health metadata.

---

## Frontend

- **`api/platform.ts`** — typed client for every platform endpoint; axios
  interceptor attaches the JWT bearer token from `localStorage`.
- **`auth/`** — `AuthContext` (rehydrates session via `/auth/me`), `useAuth`,
  `ProtectedRoute` (auth + role gating).
- **`pages/AuthPage.tsx`** — combined login/signup for candidate & employer.
- **Employer portal** (`pages/employer/`):
  - `EmployerDashboard` — list/create assessments, nav to recruiter/culture.
  - `AssessmentBuilder` — JD auto-generation, manual MCQ sections, proctoring
    permission matrix, publish, assign, save-as-template.
  - `RecruiterPanel` — candidate table (score + flags), detail drawer with
    proctoring timeline, verdict buttons.
  - `CultureScraper` — crawl + index culture pages.
  - `SchedulerPage` — schedule live interview slots.
- **Candidate workspace** (`pages/candidate/`):
  - `CandidateWorkspace` — assigned assessments + link to free mock interviews.
  - `AttemptRunner` — secure proctored runner (watermark, guardrails) + MCQ/
    text/coding answering + submission.
- **`hooks/useProctoring.ts`** — browser-native guardrails (fullscreen enforce +
  exit detection, tab-switch/blur, copy/paste/right-click block) that log
  throttled violations to the backend.
- **`App.tsx`** — wrapped in `AuthProvider`; added auth, employer, and candidate
  routes. The original anonymous routes (`/`, `/interview`, `/results`) are
  unchanged.

---

## Tests

- **`tests/test_platform_e2e.py`** — runs fully **in-process** via FastAPI
  `TestClient` against an isolated temp storage dir (no running server / Ollama /
  Judge0 needed). Covers:
  - **Unit:** auth security primitives, MCQ scorer determinism, culture keyword fallback.
  - **E2E:** employer signup→assessment→publish→assign; candidate
    start→proctoring event→submit; recruiter panel score+flags→decision+email;
    templates; scheduler; ATS webhook; cross-org data-isolation; authz guards.
  - **49 assertions, all passing.**
- Registered in `tests/run_all_tests.py` as the first suite.

---

## Dependencies added
`PyJWT`, `bcrypt`, `email-validator`, `beautifulsoup4`, `faiss-cpu`
(see `backend/requirements.txt`). New env vars documented in `backend/.env.example`.

---

## Verification performed
- Backend imports cleanly: **79 routes** across 13 services.
- Platform test suite: **49/49 passing** (re-run after all changes).
- Graceful degradation verified with Judge0 + Ollama offline.
- Frontend: `vite build` succeeds, **0 TypeScript errors** under `strict`.
