# Interview Assistant 🎯

A multi-modal AI interview coaching and evaluation platform that generates and conducts mock interviews based on job descriptions!

## Features

- **Question Generation**: Parse job descriptions and generate adaptive interview questions
- **Speech Analysis**: Real-time transcription with Whisper, fluency metrics, filler word detection
- **Language Evaluation**: Grammar checking, readability scores, vocabulary analysis
- **Body Language Analysis**: Eye contact, posture, gesture tracking via MediaPipe
- **Code Evaluation**: Diagram critique, code correctness, complexity analysis
- **Unified Scoring**: 9-category rubric-based evaluation (0-5 scale)
- **Feedback Synthesis**: Actionable improvement recommendations

## Tech Stack

| Layer | Tools |
|-------|-------|
| LLM | Ollama (Llama3.2 / Mistral / DeepSeek) |
| Speech | Whisper (local) |
| NLP | spaCy, Gramformer, textstat |
| Vision | Florence-2, Qwen-VL |
| Body Language | MediaPipe |
| Backend | FastAPI |
| Database | Supabase / PostgreSQL |
| Infra | AWS CDK (Free Tier) |

## Project Structure

```
interview-assistant/
├── backend/
│   ├── services/
│   │   ├── question_service/    # JD parsing, question generation
│   │   ├── speech_service/      # Whisper, speech metrics
│   │   ├── evaluation_service/  # Rubric scoring, hallucination check
│   │   └── feedback_service/    # Feedback synthesis
│   ├── models/                  # Pydantic schemas
│   ├── utils/                   # LLM client, helpers
│   ├── config/                  # Settings
│   └── app.py                   # FastAPI entry point
├── infra/                       # AWS CDK
├── shared/                      # Prompts, rubrics
├── tests/                       # Unit & integration tests
└── docs/                        # Documentation
```

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running
- PostgreSQL (or Supabase account)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Mandar77/interview_assistant.git
   cd interview_assistant
   ```

2. **Create virtual environment**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

4. **Setup Ollama**
   ```bash
   # In a separate terminal
   ollama serve
   
   # Pull required models
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```

5. **Configure environment**
   ```bash
   copy .env.example .env
   # Edit .env with your settings
   ```

6. **Run the server**
   ```bash
   python app.py
   # Or: uvicorn app:app --reload
   ```

7. **Access API docs**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Development Roadmap

| Phase | Weeks | Focus |
|-------|-------|-------|
| 1 | 1-2 | Foundations & Research |
| 2 | 3-4 | Question Generation Engine |
| 3 | 5-6 | Live Interview Interface |
| 4 | 7 | Speech & Language Understanding |
| 5 | 8 | Camera & Body Language |
| 6 | 9-10 | Screen & Code Understanding |
| 7 | 11 | Unified Evaluation Engine |
| 8 | 12 | Dashboard & AWS Deployment |

## Team

- **Mandar**: Lead ML + Backend + Infra
- **Anjali**: Lead Frontend + CV + Streaming + QA

## License

MIT