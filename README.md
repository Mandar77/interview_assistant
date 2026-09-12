# Interview Assistant 🎯

A multi-modal AI interview coaching and evaluation platform that generates and conducts mock interviews based on job descriptions. Features real-time speech analysis, AI-powered evaluation, and a professional interview interface with live camera feed.

> **Now a two-sided hiring platform.** In addition to the original anonymous mock-interview
> experience, the project includes an **Employer "Assessment Studio"** (build, configure, and
> assign proctored assessments) and a **Candidate "Interview Workspace"** (secure, proctored
> test-taking), plus an org culture crawler and full recruiting-workflow modules (ATS webhook,
> recruiter decision panel, automated email, templates, live-interview scheduler).
> See [docs/EXTENSION_ROADMAP.md](docs/EXTENSION_ROADMAP.md) and
> [docs/CHANGELOG_PLATFORM.md](docs/CHANGELOG_PLATFORM.md). The original mock flow is unchanged
> and still works without an account.

## ✨ Features

### Question Generation
- **Smart JD Parsing**: Extract skills using spaCy + LLM (rule-based + AI-enhanced)
- **Adaptive Difficulty**: Easy (5 min), Medium (7 min), Hard (9 min) per question
- **Multiple Interview Types**: Technical, System Design, Behavioral, OA (Online Assessment)
- **Real-time Progress**: Server-Sent Events streaming for question generation status

### Speech & Language Analysis
- **Real-time Transcription**: Whisper model with WebSocket streaming (sub-1.5s latency)
- **Speech Metrics**: 
  - Words per minute (WPM)
  - Filler word detection ("um", "uh", "like", etc.)
  - Pause analysis (count, duration)
  - Speaking rate categorization
- **Language Quality**:
  - Grammar scoring (spaCy + patterns)
  - Readability metrics (Flesch, Gunning Fog, Flesch-Kincaid)
  - Vocabulary level assessment (basic/intermediate/advanced)
  - Clarity and conciseness scoring

### Body Language Analysis
- **Camera Integration**: Live video feed with mirror effect
- **MediaPipe (Face Mesh + Pose)**:
  - Eye contact tracking
  - Posture analysis
  - Gesture detection
  - Confidence signal recognition

### Evaluation Engines
**Five independent engines, each scored 0-100. There is no combined score.**

Scores are reported side by side and are never averaged together. A previous
weighted-average design let a fluent, confident answer pass while being
technically wrong, because language and delivery points offset the technical gap.

| Engine | What it measures | Source |
|--------|------------------|--------|
| **Technical Correctness** *(critical)* | Is the answer right, and does it address the question? | LLM grading |
| **Language Quality** | Grammar, vocabulary, clarity, conciseness | Language metrics |
| **Speech Delivery** | Pace, filler words, pause control | Speech metrics |
| **Body Language** | Eye contact, posture, gestures | MediaPipe |
| **Time Management** | Use of the allotted time | Timer data |

- **Correctness-gated technical scoring**: the grader is instructed to ignore
  fluency entirely, and a relevance gate is applied in code afterwards — an
  off-topic answer cannot earn technical credit however well it is expressed.
- **No invented scores**: an engine with no input data reports
  `assessed: false` / `score: null` rather than a neutral mid-band placeholder.
- **Hallucination Detection**: Verify factual claims
- **LLM-Powered Feedback**: Detailed strengths, weaknesses, and improvement suggestions

### Hiring Platform (Phases 9–13)
A two-sided hiring layer built on top of the mock-interview engine. All org data is
multi-tenant and isolated server-side; the anonymous mock flow keeps working without an account.

- **Auth & tenancy**: JWT auth with roles (candidate / employer admin / member); organizations.
- **Employer "Assessment Studio"**: build assessments (MCQ / coding / video / system-design /
  file-upload / live), auto-generate questions from a JD, set proctoring permissions and scoring
  rules, assign to candidate usernames, and save reusable templates.
- **Candidate "Interview Workspace"**: launch assigned, proctored assessments — fullscreen
  enforcement, tab-switch / blur detection, copy-paste blocking, and a watermark overlay; every
  violation is logged for the recruiter.
- **Org Culture Crawler**: scrape public culture pages (robots-aware) into a per-org FAISS store
  and ground question generation in company values.
- **Recruiting workflow**: recruiter decision panel (score + proctoring flags + advance/schedule/
  reject), ATS webhook simulator, automated candidate email (SMTP, log-fallback in dev), and a
  live-interview scheduler with mock meeting links.

### Design System & UI
- **Premium dark-first design language** (Linear/Vercel-inspired): a single semantic token layer
  drives **full light & dark themes** with a persistent theme toggle that respects the OS setting.
- **Reusable component library** (`src/ui/`): Button, Card, Input, Badge, Modal, EmptyState,
  Spinner/Skeleton, AppShell, ErrorBoundary — all token-driven, no hardcoded colors.
- **Refined interactions**: hover/active/focus/disabled states, subtle motion, accessible focus
  rings, and a global error boundary so a render error never shows a blank page.
- **Responsive** across mobile → ultrawide; print-optimized results.

---

## 🛠️ Tech Stack

| Layer | Tools |
|-------|-------|
| **LLM** | Pluggable: Gemini 2.5 Flash (hosted) or Ollama `qwen2.5:7b` (local) |
| **Speech** | Pluggable: Groq Whisper (hosted) or `openai-whisper` (local) |
| **Audio Processing** | pydub (WebM → WAV conversion) |
| **NLP** | spaCy (en_core_web_sm), Gramformer, textstat |
| **Vision** | Florence-2, Qwen-VL 2B |
| **Body Language** | MediaPipe (Face Mesh, Pose) |
| **Code Execution** | Judge0 (Docker) |
| **Backend** | FastAPI, Python 3.10+ |
| **Frontend** | React 19, TypeScript, Tailwind CSS v4 |
| **Real-time** | WebSocket (speech streaming), Server-Sent Events (progress) |
| **Storage** | File-backed JSON store (default); Supabase/PostgreSQL backend wired, not yet default |
| **Deployment** | Render + Cloudflare Pages (hosted) or Tailscale Funnel (self-hosted) |
| **CI/CD** | GitHub Actions — gitleaks, ruff, tsc, Tier-1 suites per PR; live suites nightly |

---

## 📁 Project Structure

```
interview-assistant/
├── backend/
│   ├── services/
│   │   ├── question_service/
│   │   │   ├── generator.py           # Question generation with Ollama
│   │   │   ├── skill_parser.py        # JD skill extraction
│   │   │   └── routes.py              # API endpoints + SSE streaming
│   │   ├── speech_service/
│   │   │   ├── transcriber.py         # Whisper integration
│   │   │   ├── analyzer.py            # Speech + language metrics
│   │   │   ├── streaming.py           # WebSocket handler with per-question tracking
│   │   │   ├── session_store.py       # Session persistence
│   │   │   └── routes.py              # REST + WebSocket endpoints
│   │   ├── evaluation_service/
│   │   │   ├── rubric_scorer.py       # 5 independent 0-100 engines
│   │   │   ├── hallucination_checker.py # Claim verification
│   │   │   └── routes.py              # Evaluation endpoints
│   │   └── feedback_service/
│   │       ├── synthesizer.py         # LLM feedback generation
│   │       └── routes.py              # Feedback endpoints
│   ├── models/
│   │   └── schemas.py                 # Pydantic data models
│   ├── utils/
│   │   ├── llm_client.py              # Provider facade (LLM_PROVIDER selects)
│   │   └── llm_providers/             # gemini | ollama | fake adapters
│   ├── config/
│   │   └── settings.py                # Environment configuration
│   ├── data/
│   │   └── sessions/                  # Session storage (JSON files)
│   ├── app.py                         # FastAPI application entry point
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AudioRecorder.tsx      # MediaRecorder with chunk streaming
│   │   │   ├── CameraPreview.tsx      # Camera feed + MediaPipe integration point
│   │   │   ├── InterviewTimer.tsx     # Countdown timer
│   │   │   └── ui/                    # ShadCN-style components (optional)
│   │   ├── pages/
│   │   │   ├── HomePage.tsx           # Interview configuration
│   │   │   ├── InterviewRoom.tsx      # 2-column interview interface
│   │   │   ├── ResultsDashboard.tsx   # Evaluation results + metrics
│   │   │   └── AudioTestPage.tsx      # Mic/transcription testing
│   │   ├── hooks/
│   │   │   ├── useInterviewSession.ts # Session state management
│   │   │   ├── useSpeechWebSocket.ts  # WebSocket communication
│   │   │   ├── useMediaStream.ts      # Camera access
│   │   │   └── useScreenShare.ts      # Screen capture (Phase 6)
│   │   ├── api/
│   │   │   └── client.ts              # Axios instance with 120s timeout
│   │   ├── lib/
│   │   │   └── utils.ts               # Helper functions
│   │   ├── index.css                  # Tailwind v4 styles
│   │   ├── App.tsx                    # Router setup
│   │   └── main.tsx                   # React entry point
│   ├── postcss.config.js              # Tailwind v4 PostCSS config
│   ├── vite.config.ts                 # Vite configuration
│   └── package.json
│
├── infra/                             # AWS CDK (Phase 8)
├── shared/                            # Shared prompts, rubrics
├── tests/                             # Backend tests
├── docs/                              # Documentation
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **[Ollama](https://ollama.ai/)** installed and running
- **ffmpeg** (for audio processing)
- **PostgreSQL** (optional, currently using file storage)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Mandar77/interview_assistant.git
   cd interview_assistant/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   pip install pydub  # For audio processing
   ```

4. **Install ffmpeg**
   ```bash
   # Windows (using winget)
   winget install Gyan.FFmpeg
   
   # Or download from: https://www.gyan.dev/ffmpeg/builds/
   ```

5. **Setup Ollama**
   ```bash
   # In a separate terminal
   ollama serve
   
   # Pull required models
   ollama pull qwen2.5:7b        # ~4.7 GB
   ollama pull nomic-embed-text
   ```

   > **Model size matters here.** Question generation and answer grading both
   > use schema-constrained JSON output. 7B is roughly the floor: on a 3B model
   > (`llama3.2`) coding-question generation failed to produce valid JSON 100%
   > of the time and silently fell back to a canned question, and the grader
   > could not tell a partially-correct answer from a wrong one — both scored 0.
   > Needs ~5 GB of VRAM (or system RAM, more slowly).

6. **Configure environment**
   ```bash
   copy .env.example .env  # Windows
   # cp .env.example .env  # Linux/Mac
   
   # Edit .env file:
   # OLLAMA_BASE_URL=http://localhost:11434
   # OLLAMA_MODEL=qwen2.5:7b
   # OLLAMA_NUM_CTX=8192
   # WHISPER_MODEL_SIZE=base
   ```

7. **Run the backend server**
   ```bash
   python app.py
   # Server runs on http://localhost:8000
   ```

### Frontend Setup

1. **Navigate to frontend**
   ```bash
   cd ../frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   # Frontend runs on http://localhost:5173
   ```

4. **Access the application**
   - Open browser to http://localhost:5173
   - Allow camera and microphone permissions when prompted

---

## 📖 API Documentation

### Swagger UI
Visit http://localhost:8000/docs for interactive API documentation

### Key Endpoints

#### Question Service (`/api/v1/questions`)
- `POST /generate` - Generate interview questions
- `POST /generate-stream` - Generate with progress updates (SSE)
- `POST /parse-skills` - Extract skills from job description
- `GET /types` - Get available interview types

#### Speech Service (`/api/v1/speech`)
- `WS /stream?session_id=<uuid>` - Real-time transcription WebSocket
- `POST /transcribe` - Batch transcription
- `POST /analyze` - Full speech + language analysis
- `GET /session/{id}` - Retrieve session data
- `GET /session/{id}/for-evaluation` - Get evaluation-ready data

#### Evaluation Service (`/api/v1/evaluation`)
- `POST /evaluate` - Full rubric-based evaluation
- `POST /evaluate-quick` - Quick LLM-only evaluation
- `POST /check-hallucinations` - Verify factual claims
- `GET /rubric` - Get rubric categories and weights

#### Feedback Service (`/api/v1/feedback`)
- `POST /generate` - Generate comprehensive feedback
- `POST /generate-quick` - Quick feedback generation
- `GET /tips/{category}` - Get category-specific tips

#### Auth Service (`/api/v1/auth`) — Phase 9
- `POST /signup` - Register a candidate or employer (employer creates an org)
- `POST /login` - Authenticate by email/username + password → JWT
- `GET /me` - Current authenticated user

#### Assessment Service (`/api/v1/assessments`) — Phase 10 (employer)
- `POST /` · `GET /` · `GET /{id}` · `PATCH /{id}` · `DELETE /{id}` - Org-scoped CRUD
- `POST /{id}/generate-from-jd` - Auto-draft questions from a JD (optional culture grounding)
- `POST /{id}/assign` · `GET /{id}/assignments` - Assign to candidate usernames
- `POST /{id}/save-as-template` · `GET /templates/list` · `POST /from-template/{id}` - Templates

#### Workspace Service (`/api/v1/workspace`) — Phase 11 (candidate)
- `GET /my-assignments` - Assessments assigned to the candidate
- `POST /attempts/start` - Begin an attempt (returns answer-key-stripped assessment)
- `POST /events` - Log a proctoring event (tab switch, fullscreen exit, …)
- `POST /attempts/submit` - Submit answers (auto + AI scored)
- `GET /attempts/{id}` - Attempt detail

#### Culture Service (`/api/v1/culture`) — Phase 12 (employer)
- `POST /crawl` - Crawl public culture pages → per-org FAISS index
- `GET /summary` · `POST /query` - Inspect / query the culture store

#### Recruiter Service (`/api/v1/recruiter`) — Phase 13 (employer)
- `GET /candidates` · `GET /candidates/{attempt_id}` - Decision panel data
- `POST /decision` - Record verdict (advance/schedule/reject) + optional auto-email
- `POST /send-invite` - Email an assessment invite + link

#### ATS & Scheduler — Phase 13
- `POST /api/v1/ats/webhook` - Mock ATS intake → auto-assign + invite
- `POST /api/v1/scheduler/slots` · `GET /api/v1/scheduler/slots` - Live interview scheduling

---

## 🎬 How It Works

### 1. Configuration
- User pastes job description on home page
- Selects interview type, difficulty, and number of questions
- System calculates total duration based on difficulty

### 2. Question Generation
- **Skill Extraction**: Rule-based + spaCy + LLM extraction
- **Question Generation**: Ollama generates tailored questions
- **Progress Streaming**: Real-time updates via Server-Sent Events

### 3. Interview Session
- **One WebSocket Session**: Maintained for entire interview
- **Per-Question Tracking**: Backend segments audio/transcripts by question
- **Real-time Transcription**: 250ms audio chunks → partial transcripts
- **Camera Feed**: Live video with mirror effect (ready for MediaPipe)

### 4. Session Lifecycle
```
1. WebSocket connects (session_id generated)
2. For each question:
   ├─ Send start_question control message
   ├─ Stream 250ms audio chunks
   ├─ Receive partial transcripts (disabled by default)
   ├─ Send end_question control message
   └─ Backend finalizes transcript with WebM→WAV conversion
3. Send end_session control message
4. Backend aggregates all questions
5. Frontend fetches session data
6. Evaluation API called per question
7. Results displayed on dashboard
```

### 5. Evaluation & Results
- **Per-question analysis**: Speech metrics, language metrics, transcript
- **Engine scoring**: five independent 0-100 engines (LLM + metrics), never averaged
- **Per-engine results**: each axis reported on its own; no combined score
- **Actionable feedback**: Strengths, weaknesses, improvement suggestions
- **Professional dashboard**: Visualizations, charts, print-ready format

---

## 🎨 UI Screenshots & Features

### Home Page
- Animated gradient background with pulsing blobs
- Icon-based interview type selection
- Modern segmented difficulty control
- Dynamic duration calculation
- Feature showcase cards

### Interview Room (2-Column Layout)
**Left Column (33%):**
- Live camera feed (mirrored, ready for MediaPipe)
- Recording controls with visual feedback
- Progress tracker with checkmarks
- Debug info panel (removable)

**Right Column (67%):**
- Question display with skill tags
- Evaluation criteria hints
- Time warnings (pulsing when < 1 min)

**Fixed Header:**
- Permission indicators (mic, camera, connection)
- Live countdown timer with color coding
- Session progress badge

### Results Dashboard
- Side-by-side engine score cards (no single headline number)
- Per-engine breakdown (technical, language, delivery, body language, time)
- Per-question speech metrics
- Side-by-side strengths/weaknesses
- Numbered improvement suggestions
- Print-optimized layout

---

## 🔧 Architecture Details

### WebSocket Protocol (Speech Streaming)

**Endpoint:** `ws://localhost:8000/api/v1/speech/stream?session_id=<uuid>`

**Control Messages (JSON):**
```json
// Start a new question
{"type": "start_question", "question_id": "tech_1", "question_text": "..."}

// End current question (triggers transcription finalization)
{"type": "end_question"}

// End entire session (triggers session aggregation)
{"type": "end_session"}

// Keep-alive
{"type": "ping"}

// Get session status
{"type": "get_status"}
```

**Server Responses:**
```json
// Connection established
{"type": "connected", "session_id": "...", "message": "Ready to receive audio"}

// Question started
{"type": "question_started", "question_id": "...", "message": "..."}

// Partial transcript (disabled by default to avoid WebM chunk issues)
{"type": "partial_transcript", "partial_transcript": "...", "is_final": false}

// Question ended with final transcript
{"type": "question_ended", "question_id": "...", "final_transcript": "...", "word_count": 42}

// Session ended
{"type": "session_ended", "session_id": "...", "total_questions": 3}
```

### Session Data Structure

```json
{
  "session_id": "uuid",
  "started_at": "ISO timestamp",
  "ended_at": "ISO timestamp",
  "questions": [
    {
      "question_id": "tech_1",
      "question_text": "...",
      "started_at": "ISO timestamp",
      "ended_at": "ISO timestamp",
      "transcript": "Full answer text...",
      "speech_metrics": {
        "words_per_minute": 142.5,
        "filler_word_percentage": 2.5,
        "pause_count": 5,
        ...
      },
      "language_metrics": {
        "grammar_score": 84,
        "vocabulary_level": "intermediate",
        "readability_flesch": 65.3,
        ...
      },
      "chunk_count": 51
    }
  ],
  "full_transcript": "...",
  "total_questions": 3
}
```

### Audio Processing Pipeline

```
Browser MediaRecorder (250ms chunks)
  ↓ WebSocket
Backend receives audio/webm chunks
  ↓ Buffer per question
On end_question:
  ↓ pydub converts WebM → WAV
  ↓ Whisper transcribes WAV
  ↓ Analyze speech + language metrics
  ↓ Store in session JSON file
```

---

## 🎯 Development Roadmap & Status

| Phase | Weeks | Focus | Status |
|-------|-------|-------|--------|
| **1** | 1-2 | Foundations & Research | ✅ Complete |
| **2** | 3-4 | Question Generation Engine | ✅ Complete |
| **3** | 5-6 | Live Interview Interface | ✅ Complete |
| **4** | 7 | Speech & Language Understanding | ✅ Complete |
| **5** | 8 | Camera & Body Language (MediaPipe) | ✅ Complete |
| **6** | 9-10 | Screen & Code Understanding (Judge0 + Vision) | ✅ Complete |
| **7** | 11 | Unified Evaluation Engine | ✅ Complete |
| **8** | 12 | Dashboard & AWS Deployment (CDK) | ✅ Complete |

### Hiring Platform Extension (Phases 9–13)

| Phase | Focus | Status |
|-------|-------|--------|
| **9** | Platform Foundation — auth (JWT), orgs/users, storage repository | ✅ Complete |
| **10** | Employer "Assessment Studio" — build/assign assessments | ✅ Complete |
| **11** | Candidate "Interview Workspace" — proctored attempts | ✅ Complete |
| **12** | Org Culture Crawler — FAISS-grounded question generation | ✅ Complete |
| **13** | Recruiting workflow — ATS sim, recruiter panel, comms, templates, scheduler | ✅ Complete |
| **14** | Pluggable providers, two-tier deployment, CI/CD | 🚧 In progress |

See [docs/EXTENSION_ROADMAP.md](docs/EXTENSION_ROADMAP.md) for the full plan and
[docs/CHANGELOG_PLATFORM.md](docs/CHANGELOG_PLATFORM.md) for what shipped.

A feature-level breakdown of what is built and what is next lives in
[Current Development Status](#-current-development-status) below.

---

## 🧪 Testing

### Test Audio & Microphone
```bash
# Navigate to test page
http://localhost:5173/audio-test

# Record 10-15 seconds of speech
# Verify transcription accuracy
# Check audio playback quality
```

### Test Interview Flow
1. Enter job description (min 50 characters)
2. Select interview type and difficulty
3. Generate questions (watch SSE progress)
4. Start interview
5. Allow camera/mic permissions
6. Answer questions
7. Submit interview
8. View results dashboard

### Backend API Testing
```bash
# Via Swagger UI
http://localhost:8000/docs

# Via PowerShell
$body = @{
    job_description = "Python developer with FastAPI experience"
    interview_type = "technical"
    difficulty = "medium"
    num_questions = 3
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/questions/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 120
```

---

## 🔐 Environment Variables

**Backend `.env` file:**

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
# Ollama defaults to a 2048-token context; grounded prompts plus a full OA
# question with test cases and starter code need more than that.
OLLAMA_NUM_CTX=8192

# Whisper Configuration
WHISPER_MODEL_SIZE=base  # tiny, base, small, medium, large
WHISPER_DEVICE=cpu       # cpu or cuda

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# CORS (for development)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database (optional - currently using file storage)
DATABASE_URL=postgresql://user:pass@localhost:5432/interview_db
```

---

## 📊 Evaluation Rubric

Five independent engines. **Every score is 0-100, and no score is ever combined
with another.** Reference copy of the rubric: [`shared/rubrics/scoring_rubric.json`](shared/rubrics/scoring_rubric.json)
(descriptive only — the engine definitions live in `EVALUATION_ENGINES` in
`backend/services/evaluation_service/rubric_scorer.py`).

| Engine | Dimensions | Source | Pass mark |
|--------|-----------|--------|-----------|
| **Technical Correctness** *(critical)* | Relevance (gate), Technical Accuracy, Problem-Solving, System Design*, Factual Accuracy | LLM evaluation | 60 |
| **Language Quality** | Grammar & Vocabulary, Clarity, Conciseness | Language metrics | 55 |
| **Speech Delivery** | Pace, Filler Words, Pause Control | Speech metrics | 55 |
| **Body Language** | Eye Contact, Posture, Gestures | MediaPipe | 55 |
| **Time Management** | Time Utilization | Timer data | 50 |

\* System Design is only scored for `system_design` questions; it is omitted
rather than defaulted for other types.

**Scoring:** 0-100 scale
- 90-100: Exceptional — complete, precise, demonstrates mastery
- 75-89: Strong — correct and well reasoned, minor gaps
- 60-74: Adequate — broadly correct, noticeable gaps
- 40-59: Weak — partially correct, significant errors
- 0-39: Poor — wrong, or does not address what was asked

**Why no overall score?** Averaging the engines is what allowed a well-spoken but
incorrect answer to score as a pass. Technical correctness now stands alone; the
relevance gate scales it down when the answer does not address the question, so
the report reads `Technical 8 / Language 94` instead of a misleading single number.

**Coding (OA) questions** are scored the same way: `correctness` (driven by the
test suite), `code_quality` and `complexity` are reported separately on 0-100.
Quality and complexity never raise correctness — clean code that fails the tests
is still wrong code.

---

## 🐛 Troubleshooting

### Issue: Question generation times out
**Cause:** Ollama LLM inference takes 10-60s depending on hardware. Measured on
an RTX 4060 laptop with `qwen2.5:7b`: ~15-25s for 2 questions, ~7.5s per question
thereafter, ~150s for a 20-question batch.  
**Solution:** Frontend uses a 120s timeout and streams progress. Generate 3-5
questions per interview rather than 20.

Dropping to a smaller model trades accuracy for speed and is **not** recommended
below 7B — see the model note in Setup. If you must:
```bash
ollama pull qwen2.5:3b   # faster, noticeably worse at structured output
```

### Issue: Every interview shows the same generic question
**Cause:** Generation failed and the canned fallback was served. Most often this
is a model too small to emit valid JSON for the question schema.  
**Solution:** The interview screen shows a "Showing a standard practice question"
banner when this happens, and `POST /questions/generate` returns
`used_fallback: true`. Check Ollama is running and `OLLAMA_MODEL` is 7B or larger.

### Issue: WebSocket disconnects immediately (1006)
**Cause:** Frontend not sending `start_question` before audio chunks  
**Solution:** Ensure `wsStartQuestion()` is called before recording starts

### Issue: Transcription is gibberish
**Cause:** Small WebM chunks can't be transcribed individually  
**Solution:** Partial transcription is disabled. Full transcription happens on `end_question`

### Issue: Camera shows black screen
**Cause:** Browser permissions, camera in use, or ref timing issue  
**Solution:** 
- Check browser permissions (click lock icon in address bar)
- Close other apps using camera
- Check browser console for detailed error logs

### Issue: Styles not applying
**Cause:** Tailwind v4 requires specific PostCSS setup  
**Solution:** 
```bash
# Verify postcss.config.js has:
export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}

# Clear Vite cache
rm -r node_modules/.vite
npm run dev
```

---

## 🚧 Known Limitations

- **Local LLM required**: question generation & AI scoring need Ollama running
  (`ollama serve` + `ollama pull qwen2.5:7b`); the UI shows a clear "AI unavailable" notice if it's offline.
- **Storage backend**: platform data uses a file-backed JSON store by default (great for dev / a
  single EC2 instance). A `sql` backend (Postgres/Supabase) is wired but not yet the default — Phase 14.
- **Code execution needs Judge0**: OA coding-score path requires a local Judge0 (Docker); other
  paths degrade gracefully without it.
- **Practice history is local**: per-user mock history is stored in the browser (localStorage),
  not yet synced to the server.
- **Deployment**: CDK infra exists but the live deploy targeted a now-deleted AWS account; a redeploy
  to the current account is part of Phase 14.

---

## 🔄 Current Development Status

### What's Working ✅
- Question generation pipeline with SSE progress streaming
- Real-time speech transcription via WebSocket (single stable connection per session)
- Per-question session tracking; speech + language analysis
- Five independent 0-100 evaluation engines + feedback synthesis
- MediaPipe body-language analysis; Judge0 code execution; Vision diagram critique
- AWS CDK deployment infrastructure (EC2 + Ollama + S3 + CloudFront)
- **Hiring platform (Phases 9–13):** auth/tenancy, Assessment Studio, proctored
  Candidate Workspace, culture crawler, recruiter panel, ATS sim, comms, scheduler
- **Full light/dark design system** with theme toggle and reusable component library
- Per-user practice history; AI pipeline verified end-to-end on local Ollama

### Deployment (Phase 14) 🚀
The same branch deploys two ways, selected purely by environment variables —
see **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**. Both cost $0 and neither
requires a credit card.

| | `fast` | `owned` |
|---|---|---|
| Inference | Gemini 2.5 Flash (hosted) | Ollama `qwen2.5:7b` (own hardware) |
| Transcription | Groq Whisper | local `openai-whisper` |
| Code execution | unavailable | Judge0 in Docker |
| Hosting | Cloudflare Pages → Render | Tailscale Funnel |
| Always on | yes | while the machine is up |

`owned` is the feature-complete tier — Judge0 needs privileged Docker that no
free no-card host allows, so coding questions live there. Any deployment
reports its own capabilities at `GET /api/v1/config`, and the frontend hides
what the backend cannot serve.

**CI/CD:** every PR runs secret scanning (gitleaks), lint, typecheck and the
Tier-1 suites — 106 checks with no model, no server and no Docker, via a
deterministic `fake` provider. The live-model suites run nightly against Gemini.

### What's Next 🔜
- Phase 14 remainder: employer analytics, rate limiting, audit logging
- Coding questions on the hosted tier (blocked on a Piston API key)
- Richer charts; e2e tests for the two-sided flows

> Detailed plan: [docs/EXTENSION_ROADMAP.md](docs/EXTENSION_ROADMAP.md) ·
> what shipped: [docs/CHANGELOG_PLATFORM.md](docs/CHANGELOG_PLATFORM.md)

---

## 📚 Additional Documentation

- **Extension Roadmap**: [docs/EXTENSION_ROADMAP.md](docs/EXTENSION_ROADMAP.md)
- **Platform Changelog**: [docs/CHANGELOG_PLATFORM.md](docs/CHANGELOG_PLATFORM.md)
- **API Contracts**: `docs/API_CONTRACTS.md` (planned)
- **Deployment Guide**: `docs/AWS_DEPLOYMENT.md` (planned)

---

## 🤝 Contributing

This is a portfolio project. If you'd like to use or extend it:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **OpenAI Whisper** for speech transcription
- **Ollama** for local LLM inference
- **MediaPipe** for body language analysis
- **spaCy** for NLP processing
- **FastAPI** for the backend framework
- **React** and **Tailwind CSS** for the frontend

---

## 📞 Contact

For questions or collaboration:
- GitHub: [Mandar77](https://github.com/Mandar77)
- Project: [Interview Assistant](https://github.com/Mandar77/interview_assistant)

---

**Built with ❤️ using 100% free and open-source tools**