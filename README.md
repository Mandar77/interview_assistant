# Interview Assistant 🎯

A multi-modal AI interview coaching and evaluation platform that generates and conducts mock interviews based on job descriptions. Features real-time speech analysis, AI-powered evaluation, and a professional interview interface with live camera feed.

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

### Body Language Analysis (Phase 5 - In Progress)
- **Camera Integration**: Live video feed with mirror effect
- **MediaPipe Ready**: Component architecture prepared for:
  - Eye contact tracking
  - Posture analysis
  - Gesture detection
  - Confidence signal recognition

### Evaluation Engine
- **9-Category Rubric Scoring** (0-5 scale):
  - Technical Correctness
  - Problem-Solving Approach
  - System Design Quality
  - Communication Clarity
  - Grammar & Vocabulary
  - Confidence & Pacing
  - Body Language (when implemented)
  - Time Utilization
  - Claim Consistency
- **Hallucination Detection**: Verify factual claims
- **LLM-Powered Feedback**: Detailed strengths, weaknesses, and improvement suggestions

### Professional UI
- **Glassmorphism Design**: Modern aesthetic with gradient backgrounds and frosted glass effects
- **2-Column Interview Layout**: 
  - Left: Camera feed, recording controls, progress tracker
  - Right: Question display, evaluation criteria
- **Real-time Indicators**: Permission status (mic, camera, connection), live timer
- **Responsive Dashboard**: Score visualization, speech metrics, detailed feedback
- **Print-Optimized Results**: Professional PDF-ready output

---

## 🛠️ Tech Stack

| Layer | Tools |
|-------|-------|
| **LLM** | Ollama (Llama3.2 / Mistral / DeepSeek), local |
| **Speech** | Whisper (base model), local or Lambda preloaded |
| **Audio Processing** | pydub (WebM → WAV conversion) |
| **NLP** | spaCy (en_core_web_sm), Gramformer, textstat |
| **Vision** | Florence-2, Qwen-VL 2B (Phase 6) |
| **Body Language** | MediaPipe (Face Mesh, Pose) - Phase 5 |
| **Backend** | FastAPI, Python 3.10+ |
| **Frontend** | React 18, TypeScript, Tailwind CSS v4 |
| **Real-time** | WebSocket (speech streaming), Server-Sent Events (progress) |
| **Storage** | File-based sessions (PostgreSQL planned) |
| **Database** | Supabase / PostgreSQL (free tier) |
| **Deployment** | AWS CDK, Lambda, API Gateway, S3 (all free tier) |

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
│   │   │   ├── rubric_scorer.py       # 9-category scoring
│   │   │   ├── hallucination_checker.py # Claim verification
│   │   │   └── routes.py              # Evaluation endpoints
│   │   └── feedback_service/
│   │       ├── synthesizer.py         # LLM feedback generation
│   │       └── routes.py              # Feedback endpoints
│   ├── models/
│   │   └── schemas.py                 # Pydantic data models
│   ├── utils/
│   │   └── llm_client.py              # Ollama client wrapper
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
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```

6. **Configure environment**
   ```bash
   copy .env.example .env  # Windows
   # cp .env.example .env  # Linux/Mac
   
   # Edit .env file:
   # OLLAMA_BASE_URL=http://localhost:11434
   # OLLAMA_MODEL=llama3.2
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
- **Rubric scoring**: 9 categories evaluated by LLM + metrics
- **Aggregated scores**: Overall performance calculation
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
- Hero score card with animated progress bar
- Detailed 9-category breakdown
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
        "grammar_score": 4.2,
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
| **5** | 8 | Camera & Body Language | 🔄 In Progress |
| **6** | 9-10 | Screen & Code Understanding | 🔜 Planned |
| **7** | 11 | Unified Evaluation Engine | ✅ Complete |
| **8** | 12 | Dashboard & AWS Deployment | 🔜 Planned |

### Completed Features ✅

#### Backend (Mandar)
- ✅ Question generation with skill extraction (spaCy + LLM)
- ✅ SSE streaming for question generation progress
- ✅ WebSocket endpoint for real-time speech streaming
- ✅ Per-question session tracking
- ✅ Whisper transcription with pydub audio conversion
- ✅ Speech metrics (WPM, fillers, pauses)
- ✅ Language metrics (grammar, readability, vocabulary)
- ✅ Session persistence (file-based, PostgreSQL ready)
- ✅ Rubric-based evaluation engine (9 categories)
- ✅ Hallucination detection
- ✅ Feedback synthesis with LLM

#### Frontend (Anjali)
- ✅ Professional UI with Tailwind v4
- ✅ Home page with configuration options
- ✅ 2-column interview room layout
- ✅ Live camera feed integration
- ✅ Real-time WebSocket speech streaming
- ✅ Audio recording with 250ms chunking
- ✅ Session state management
- ✅ Question flow navigation
- ✅ Results dashboard with visualizations
- ✅ Print-optimized results page

### In Progress 🔄

- 🔄 MediaPipe body language analysis
- 🔄 Canvas overlay for landmark visualization

### Planned 🔜

- 🔜 Screen capture and sharing
- 🔜 Code execution sandbox (Judge0)
- 🔜 Diagram understanding (Vision-LLM)
- 🔜 AWS CDK deployment infrastructure
- 🔜 PostgreSQL database migration
- 🔜 Performance analytics dashboard

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
OLLAMA_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

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

| Category | Weight | Source |
|----------|--------|--------|
| Technical Correctness | 25% | LLM evaluation |
| Problem-Solving Approach | 20% | LLM evaluation |
| System Design Quality | 15% | LLM evaluation (if applicable) |
| Communication Clarity | 10% | Speech + language metrics |
| Grammar & Vocabulary | 10% | Language metrics |
| Confidence & Pacing | 10% | Speech metrics |
| Body Language | 5% | MediaPipe (Phase 5) |
| Time Utilization | 3% | Timer data |
| Claim Consistency | 2% | Hallucination checker |

**Scoring:** 0-5 scale
- 4.5-5.0: Excellent
- 4.0-4.4: Good
- 3.0-3.9: Satisfactory
- 2.0-2.9: Needs Improvement
- 0.0-1.9: Poor

---

## 🐛 Troubleshooting

### Issue: Question generation times out
**Cause:** Ollama LLM inference takes 10-60s depending on hardware  
**Solution:** Frontend uses 120s timeout. Consider using smaller model:
```bash
ollama pull llama3.2:1b  # Faster 1B parameter model
```

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

- **Local LLM Speed**: Question generation 10-60s depending on hardware
- **File-based Sessions**: Currently using JSON files; PostgreSQL migration planned
- **No Authentication**: Single-user development mode
- **MediaPipe Not Integrated**: Camera works, body language analysis pending (Phase 5)
- **No Screen Capture**: Phase 6 planned
- **Not Deployed**: Running locally only (AWS deployment in Phase 8)

---

## 🔄 Current Development Status

### What's Working ✅
- Complete question generation pipeline with progress streaming
- Real-time speech transcription via WebSocket
- Per-question session tracking
- Speech and language analysis with multiple metrics
- 9-category evaluation engine with LLM scoring
- Feedback generation with actionable suggestions
- Professional 2-column interview UI
- Live camera feed (MediaPipe integration ready)
- Results dashboard with visualizations

### What's Next 🔜
- **Immediate (Phase 5):** MediaPipe body language analysis
- **Next (Phase 6):** Screen capture, code execution sandbox, diagram critique
- **Final (Phase 8):** AWS CDK deployment, PostgreSQL database, monitoring

---

## 👥 Team

- **Mandar**: Lead ML + Backend + Infrastructure
  - LLM pipeline, evaluation engine, speech analysis
  - FastAPI backend, WebSocket implementation
  - Session management, AWS CDK (planned)

- **Anjali**: Lead Frontend + Computer Vision + QA
  - React UI, WebRTC integration, camera handling
  - MediaPipe body language analysis (in progress)
  - Screen capture, testing, UX polish

---

## 📚 Additional Documentation

- **MediaPipe Integration Guide**: `docs/MEDIAPIPE_INTEGRATION_GUIDE.md`
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