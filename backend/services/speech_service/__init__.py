"""
Speech Service - Audio transcription, analysis, and real-time streaming
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
from services.speech_service.streaming import (
    SpeechStreamingHandler,
    streaming_handler,
    StreamingSession
)
from services.speech_service.session_store import (
    SessionStore,
    session_store,
    save_session,
    get_session,
    get_session_for_evaluation
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
    # Streaming
    "SpeechStreamingHandler",
    "streaming_handler",
    "StreamingSession",
    # Session Store
    "SessionStore",
    "session_store",
    "save_session",
    "get_session",
    "get_session_for_evaluation",
    # Routes
    "router"
]