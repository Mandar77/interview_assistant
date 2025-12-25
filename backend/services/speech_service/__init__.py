"""
Speech Service - Audio transcription and speech analysis
Location: backend/services/speech_service/__init__.py
"""

from services.speech_service.transcriber import (
    WhisperTranscriber,
    transcriber,
    transcribe_audio,
    transcribe_audio_bytes
)
from services.speech_service.analyzer import (
    SpeechAnalyzer,
    speech_analyzer,
    analyze_speech,
    analyze_language,
    SpeechMetrics,
    LanguageMetrics
)
from services.speech_service.routes import router

__all__ = [
    # Transcriber
    "WhisperTranscriber",
    "transcriber",
    "transcribe_audio",
    "transcribe_audio_bytes",
    # Analyzer
    "SpeechAnalyzer",
    "speech_analyzer",
    "analyze_speech",
    "analyze_language",
    "SpeechMetrics",
    "LanguageMetrics",
    # Routes
    "router"
]