# Deployment

Two deployment tiers off **one branch**. Which one you get is decided entirely
by environment variables — there is no separate deployment branch to keep in
sync, and no code is duplicated between them.

| | `fast` | `owned` |
|---|---|---|
| Inference | Gemini 2.5 Flash (hosted) | Ollama `qwen2.5:7b` (your hardware) |
| Transcription | Groq Whisper (hosted) | `openai-whisper` (local) |
| Code execution | **unavailable** | Judge0 in Docker |
| Hosting | Cloudflare Pages → Render | Your machine → Tailscale Funnel |
| Always on | Yes | Only while your machine is |
| Cost | $0 | $0 |
| Credit card | **Not required** | **Not required** |

`owned` is the feature-complete tier: it is the one with coding questions,
because Judge0 needs privileged Docker that no free no-card host allows.

---

## Configuration surface

```
LLM_PROVIDER   = gemini | ollama | fake
STT_PROVIDER   = groq   | whisper_local
EXEC_PROVIDER  = judge0 | disabled
```

`fake` is a deterministic in-process provider used by CI. It is schema-aware,
so it exercises the real generation and scoring paths rather than their error
branches — which is how the test suite runs with no model, no server and no
Docker.

Ask any running deployment what it can do:

```bash
curl https://<host>/api/v1/config
```

The frontend calls this at boot and hides coding questions when the backend
cannot run them.

---

## Tier 1 — `fast` (hosted)

### 1. Get the two API keys (both free, neither needs a card)

| Key | Where | Free tier |
|---|---|---|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey | 1,500 requests/day, 1M context |
| `GROQ_API_KEY` | https://console.groq.com/keys | 2,000 audio requests/day |

Gemini is used rather than a chat provider with a tokens-per-minute cap: a
five-question interview runs roughly 15,000 tokens, which throttles on a
6K-TPM free tier partway through a demo. Gemini's limit is requests per day.

### 2. Backend → Render

```bash
cp backend/.env.fast.example backend/.env.fast   # then paste your keys
```

Deploy via `render.yaml` (blueprint), or point a new Web Service at
`backend/Dockerfile.hosted`. Set `GEMINI_API_KEY`, `GROQ_API_KEY`,
`JWT_SECRET_KEY` as dashboard secrets — never in the repo.

The image installs `requirements.ci.txt`, **not** `requirements.txt`: no torch,
no whisper, no ollama. That is what keeps it inside Render's free 512 MB and
lets it cold-start in seconds.

### 3. Defeat the cold start

Render free services spin down after 15 minutes idle and take 30–60s to wake —
which would ruin a demo. Render grants **750 instance-hours/month** and an
always-on service needs **744**, so a keep-warm ping fits inside the allowance:

- Add a free job at https://cron-job.org (no card) hitting
  `https://<your-service>.onrender.com/api/v1/evaluation/health` every 10 minutes.

Do **not** add a second always-on service — two would exceed the monthly hours.

### 4. Database → Supabase

Free tier, no card. Set `SUPABASE_URL` / `SUPABASE_KEY`. Leave blank to use the
file-backed JSON store (fine for a demo, lost on container restart).

> Free Supabase projects **pause after 7 days** with no database activity. Add a
> second daily cron that touches the DB, or the app returns errors after a quiet
> week.

### 5. Frontend → Cloudflare Pages

Build `frontend/`, output `dist/`. Copy `frontend/.env.fast.example` values into
the dashboard's build environment. Vite inlines `VITE_*` at build time, so
changing them needs a rebuild, not just a restart.

Use `wss://` for `VITE_WS_BASE_URL` — browsers block insecure sockets from an
HTTPS page.

---

## Tier 2 — `owned` (self-hosted inference)

### 1. Prerequisites

```bash
ollama serve
ollama pull qwen2.5:7b
docker compose up -d judge0 judge0-db redis judge0-workers
cp backend/.env.owned.example backend/.env      # no API keys needed
```

7B is the floor. Smaller models fail schema-constrained generation and fall back
to canned questions; a 3B model also cannot tell a partially-correct answer from
a wrong one.

### 2. Run

```bash
cd backend && uvicorn app:app --host 0.0.0.0 --port 8000
```

### 3. Expose it — Tailscale Funnel

Free Personal plan, **no credit card**, and a stable `*.ts.net` hostname:

```bash
tailscale funnel 8000
```

**Why not a Cloudflare quick tunnel:** the `trycloudflare.com` edge buffers
`text/event-stream`, so the question-generation progress stream never reaches
the browser. Its URL is also ephemeral, so it cannot be a stable link. A *named*
Cloudflare tunnel fixes both but requires a domain, which costs money.

**Why not ngrok:** its free tier injects an interstitial warning page on browser
traffic — the last thing you want when someone opens your link.

> Smoke-test SSE through whichever tunnel you pick before relying on it:
> `curl -N https://<host>/api/v1/questions/generate-stream` should emit events
> incrementally, not arrive in one buffered lump at the end.

---

## CI/CD

**Every PR** (`.github/workflows/ci.yml`) — runs in ~2 minutes, no model needed:

- `gitleaks` secret scan over full history
- `ruff` lint, `tsc --noEmit`, `eslint`
- Tier-1 tests: platform suite (49 checks) + provider contracts (57 checks)
- Frontend build

**Nightly** (`.github/workflows/nightly.yml`) — the live-model suites against
Gemini. Needs repository secret `GEMINI_API_KEY`; skips cleanly without it
rather than failing red.

The split exists because the integration suite takes ~20 minutes and generation
is LLM-bound at roughly 7.5s/question — and no hosted runner can load a 7B model.

### Branch protection worth enabling

On `main`: require the `secrets`, `backend` and `frontend` checks, and disallow
direct pushes. That is the "proper chain of actions" — it is a settings change,
not code.

---

## Measured latency

On an RTX 4060 laptop with `qwen2.5:7b` (`owned` tier):

| Operation | Time |
|---|---|
| 2 questions | 15–25s |
| Per question thereafter | ~7.5s |
| 20-question batch | ~150s |
| Grading one answer | 3–8s |
| Grading a 50KB transcript | ~69s (answers are capped at 8,000 chars) |

The honest expectation is that `fast` beats `owned` on both latency and quality —
Gemini is a frontier model on dedicated hardware. `owned` exists because it owns
the whole inference stack and has code execution, not because it is quicker.
