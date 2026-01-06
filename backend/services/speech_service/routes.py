"""
Speech Service API Routes (with WebSocket streaming support)
Location: backend/services/speech_service/routes.py
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, Query
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
import logging
import tempfile
import os
from dataclasses import asdict

from services.speech_service.transcriber import transcriber, transcribe_audio_bytes
from services.speech_service.analyzer import (
    speech_analyzer,
    analyze_speech,
    analyze_language,
    SpeechMetrics,
    LanguageMetrics
)
from services.speech_service.streaming import streaming_handler
from services.speech_service.session_store import session_store

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class TranscriptionResponse(BaseModel):
    text: str
    language: str
    duration_seconds: float
    confidence: float
    word_count: int
    segments: Optional[list] = None


class SpeechMetricsResponse(BaseModel):
    words_per_minute: float
    total_words: int
    total_duration_seconds: float
    filler_word_count: int
    filler_word_percentage: float
    filler_words_found: list
    pause_count: int
    avg_pause_duration_ms: float
    longest_pause_ms: float
    speaking_rate_category: str


class LanguageMetricsResponse(BaseModel):
    grammar_errors: list
    grammar_score: float
    vocabulary_level: str
    unique_word_ratio: float
    avg_sentence_length: float
    readability_flesch: float
    readability_flesch_grade: float
    readability_gunning_fog: float
    clarity_score: float
    conciseness_score: float


class FullAnalysisResponse(BaseModel):
    transcription: TranscriptionResponse
    speech_metrics: SpeechMetricsResponse
    language_metrics: LanguageMetricsResponse


class TextAnalysisRequest(BaseModel):
    text: str


class SessionDataResponse(BaseModel):
    session_id: str
    started_at: Optional[str]
    ended_at: Optional[str]
    transcript: Optional[str]
    speech_metrics: Optional[dict]
    language_metrics: Optional[dict]
    duration_seconds: Optional[float]


# =============================================================================
# WebSocket Endpoint for Real-Time Streaming
# =============================================================================

@router.websocket("/stream")
async def websocket_speech_stream(
    websocket: WebSocket,
    session_id: str = Query(..., description="Session ID for tracking")
):
    """
    WebSocket endpoint for real-time speech streaming.
    
    Protocol:
    1. Client connects with session_id as query param
    2. Client sends binary audio chunks (webm/opus format, ~250ms each)
    3. Server responds with partial transcripts:
       {"type": "partial_transcript", "partial_transcript": "...", "is_final": false}
    4. On disconnect, server finalizes and persists the full session
    
    Control messages (JSON):
    - {"type": "end_session"} - Explicitly end the session
    - {"type": "ping"} - Keep-alive ping
    - {"type": "get_status"} - Get current session status
    
    Example client usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/speech/stream?session_id=abc123');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'partial_transcript') {
            console.log('Transcript:', data.partial_transcript);
        }
    };
    // Send audio chunk
    ws.send(audioBlob);
    ```
    """
    await streaming_handler.handle_connection(websocket, session_id)


# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """
    Get stored session data including transcript and metrics.
    
    Use this after a streaming session ends to retrieve:
    - Full transcript
    - Speech metrics (WPM, fillers, pauses)
    - Language metrics (grammar, readability)
    """
    session = await session_store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return {
        "session_id": session_id,
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "transcription": session.get("transcription", {}),
        "speech_metrics": session.get("speech_metrics"),
        "language_metrics": session.get("language_metrics"),
        "partial_transcripts": session.get("partial_transcripts", []),
        "metadata": session.get("metadata", {})
    }


@router.get("/session/{session_id}/transcript")
async def get_session_transcript(session_id: str):
    """Get only the transcript for a session."""
    transcript = await session_store.get_session_transcript(session_id)
    
    if transcript is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return {
        "session_id": session_id,
        "transcript": transcript
    }


@router.get("/session/{session_id}/metrics")
async def get_session_metrics(session_id: str):
    """Get speech and language metrics for a session."""
    metrics = await session_store.get_session_metrics(session_id)
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return {
        "session_id": session_id,
        **metrics
    }


@router.get("/session/{session_id}/for-evaluation")
async def get_session_for_evaluation(session_id: str):
    """
    Get session data formatted for the evaluation service.
    
    Returns data ready to be passed to /api/v1/evaluation/evaluate
    """
    data = await session_store.get_session_for_evaluation(session_id)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return data


@router.get("/sessions")
async def list_sessions(limit: int = 50, offset: int = 0):
    """List all stored sessions."""
    sessions = await session_store.list_sessions(limit=limit, offset=offset)
    
    return {
        "sessions": sessions,
        "count": len(sessions),
        "limit": limit,
        "offset": offset
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a stored session."""
    success = await session_store.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")
    
    return {"message": f"Session {session_id} deleted"}


# =============================================================================
# Batch Processing Endpoints (existing functionality)
# =============================================================================

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (wav, mp3, webm, m4a)"),
    language: str = Form(default="en", description="Language code"),
    include_segments: bool = Form(default=False, description="Include word-level segments"),
    session_id: Optional[str] = Form(default=None, description="Optional session ID to store results")
):
    """
    Transcribe an audio file to text using Whisper.
    
    Supported formats: wav, mp3, webm, m4a, ogg, flac
    Optionally stores results in session store if session_id provided.
    """
    allowed_types = {".wav", ".mp3", ".webm", ".m4a", ".ogg", ".flac", ".mp4"}
    file_ext = os.path.splitext(audio.filename)[1].lower() if audio.filename else ".webm"
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_ext}. Allowed: {allowed_types}"
        )
    
    try:
        audio_bytes = await audio.read()
        logger.info(f"Received audio: {audio.filename}, size: {len(audio_bytes)} bytes")
        
        result = transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            file_extension=file_ext,
            language=language,
            word_timestamps=include_segments
        )
        
        # Store in session if session_id provided
        if session_id:
            await session_store.update_session(session_id, {
                "transcription": result
            })
        
        return TranscriptionResponse(
            text=result["text"],
            language=result["language"],
            duration_seconds=result["duration_seconds"],
            confidence=result["confidence"],
            word_count=result["word_count"],
            segments=result["segments"] if include_segments else None
        )
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/analyze", response_model=FullAnalysisResponse)
async def analyze_audio(
    audio: UploadFile = File(..., description="Audio file to analyze"),
    language: str = Form(default="en", description="Language code"),
    session_id: Optional[str] = Form(default=None, description="Optional session ID to store results")
):
    """
    Full analysis: transcribe audio and compute all metrics.
    
    Returns:
    - Transcription with timestamps
    - Speech metrics (WPM, fillers, pauses)
    - Language metrics (grammar, readability, vocabulary)
    
    Optionally stores results in session store if session_id provided.
    """
    allowed_types = {".wav", ".mp3", ".webm", ".m4a", ".ogg", ".flac", ".mp4"}
    file_ext = os.path.splitext(audio.filename)[1].lower() if audio.filename else ".webm"
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_ext}"
        )
    
    try:
        audio_bytes = await audio.read()
        logger.info(f"Analyzing audio: {audio.filename}, size: {len(audio_bytes)} bytes")
        
        transcription = transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            file_extension=file_ext,
            language=language,
            word_timestamps=True
        )
        
        speech_metrics = analyze_speech(transcription)
        language_metrics = analyze_language(transcription["text"])
        
        # Store in session if session_id provided
        if session_id:
            await session_store.save_session(session_id, {
                "session_id": session_id,
                "transcription": transcription,
                "speech_metrics": asdict(speech_metrics),
                "language_metrics": asdict(language_metrics)
            })
        
        return FullAnalysisResponse(
            transcription=TranscriptionResponse(
                text=transcription["text"],
                language=transcription["language"],
                duration_seconds=transcription["duration_seconds"],
                confidence=transcription["confidence"],
                word_count=transcription["word_count"],
                segments=transcription["segments"]
            ),
            speech_metrics=SpeechMetricsResponse(**asdict(speech_metrics)),
            language_metrics=LanguageMetricsResponse(**asdict(language_metrics))
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-text", response_model=LanguageMetricsResponse)
async def analyze_text_only(request: TextAnalysisRequest):
    """Analyze text directly (without audio)."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        language_metrics = analyze_language(request.text)
        return LanguageMetricsResponse(**asdict(language_metrics))
        
    except Exception as e:
        logger.error(f"Text analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/speech-metrics")
async def get_speech_metrics_from_transcription(transcription: dict):
    """Compute speech metrics from an existing transcription."""
    try:
        speech_metrics = analyze_speech(transcription)
        return SpeechMetricsResponse(**asdict(speech_metrics))
        
    except Exception as e:
        logger.error(f"Speech metrics computation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check for speech service."""
    whisper_health = transcriber.check_health()
    spacy_loaded = speech_analyzer.nlp is not None
    
    # Check active streaming sessions
    active_sessions = len(streaming_handler.active_sessions)
    
    status = "healthy" if whisper_health["status"] == "healthy" and spacy_loaded else "degraded"
    
    return {
        "service": "speech_service",
        "status": status,
        "whisper": whisper_health,
        "spacy_loaded": spacy_loaded,
        "active_streaming_sessions": active_sessions,
        "websocket_endpoint": "/api/v1/speech/stream"
    }


@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported audio formats."""
    return {
        "supported_formats": [
            {"extension": ".wav", "mime_type": "audio/wav"},
            {"extension": ".mp3", "mime_type": "audio/mpeg"},
            {"extension": ".webm", "mime_type": "audio/webm"},
            {"extension": ".m4a", "mime_type": "audio/mp4"},
            {"extension": ".ogg", "mime_type": "audio/ogg"},
            {"extension": ".flac", "mime_type": "audio/flac"},
        ],
        "recommended": ".webm",
        "notes": "WebRTC typically outputs .webm format. For streaming, use audio/webm;codecs=opus"
    }