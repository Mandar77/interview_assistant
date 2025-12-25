"""
Speech Service API Routes
Location: backend/services/speech_service/routes.py
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
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

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class TranscriptionResponse(BaseModel):
    """Response for transcription endpoint."""
    text: str
    language: str
    duration_seconds: float
    confidence: float
    word_count: int
    segments: Optional[list] = None


class SpeechMetricsResponse(BaseModel):
    """Response for speech metrics."""
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
    """Response for language metrics."""
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
    """Complete analysis response."""
    transcription: TranscriptionResponse
    speech_metrics: SpeechMetricsResponse
    language_metrics: LanguageMetricsResponse


class TextAnalysisRequest(BaseModel):
    """Request for analyzing text directly."""
    text: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (wav, mp3, webm, m4a)"),
    language: str = Form(default="en", description="Language code"),
    include_segments: bool = Form(default=False, description="Include word-level segments")
):
    """
    Transcribe an audio file to text using Whisper.
    
    Supported formats: wav, mp3, webm, m4a, ogg, flac
    """
    # Validate file type
    allowed_types = {".wav", ".mp3", ".webm", ".m4a", ".ogg", ".flac", ".mp4"}
    file_ext = os.path.splitext(audio.filename)[1].lower() if audio.filename else ".webm"
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_ext}. Allowed: {allowed_types}"
        )
    
    try:
        # Read audio bytes
        audio_bytes = await audio.read()
        logger.info(f"Received audio: {audio.filename}, size: {len(audio_bytes)} bytes")
        
        # Transcribe
        result = transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            file_extension=file_ext,
            language=language,
            word_timestamps=include_segments
        )
        
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
    language: str = Form(default="en", description="Language code")
):
    """
    Full analysis: transcribe audio and compute all metrics.
    
    Returns:
    - Transcription with timestamps
    - Speech metrics (WPM, fillers, pauses)
    - Language metrics (grammar, readability, vocabulary)
    """
    # Validate file type
    allowed_types = {".wav", ".mp3", ".webm", ".m4a", ".ogg", ".flac", ".mp4"}
    file_ext = os.path.splitext(audio.filename)[1].lower() if audio.filename else ".webm"
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_ext}"
        )
    
    try:
        # Read and transcribe
        audio_bytes = await audio.read()
        logger.info(f"Analyzing audio: {audio.filename}, size: {len(audio_bytes)} bytes")
        
        transcription = transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            file_extension=file_ext,
            language=language,
            word_timestamps=True
        )
        
        # Analyze speech patterns
        speech_metrics = analyze_speech(transcription)
        
        # Analyze language quality
        language_metrics = analyze_language(transcription["text"])
        
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
    """
    Analyze text directly (without audio).
    
    Useful for analyzing written responses or pre-transcribed text.
    """
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
    """
    Compute speech metrics from an existing transcription.
    
    Useful when you already have transcription and just need metrics.
    """
    try:
        speech_metrics = analyze_speech(transcription)
        return SpeechMetricsResponse(**asdict(speech_metrics))
        
    except Exception as e:
        logger.error(f"Speech metrics computation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for speech service."""
    whisper_health = transcriber.check_health()
    spacy_loaded = speech_analyzer.nlp is not None
    
    status = "healthy" if whisper_health["status"] == "healthy" and spacy_loaded else "degraded"
    
    return {
        "service": "speech_service",
        "status": status,
        "whisper": whisper_health,
        "spacy_loaded": spacy_loaded
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
        "notes": "WebRTC typically outputs .webm format"
    }