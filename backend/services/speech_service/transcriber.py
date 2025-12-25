"""
Speech Transcriber - Whisper integration for audio transcription
Location: backend/services/speech_service/transcriber.py
"""

import whisper
import torch
import tempfile
import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Transcribe audio using OpenAI's Whisper model (local).
    Supports various audio formats: wav, mp3, webm, m4a, etc.
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if WhisperTranscriber._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load Whisper model based on settings."""
        model_size = settings.whisper_model_size
        device = settings.whisper_device
        
        logger.info(f"Loading Whisper model: {model_size} on {device}")
        
        try:
            # Check if CUDA is available
            if device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                device = "cpu"
            
            WhisperTranscriber._model = whisper.load_model(model_size, device=device)
            logger.info(f"Whisper model loaded successfully on {device}")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    @property
    def model(self):
        """Get the loaded Whisper model."""
        if WhisperTranscriber._model is None:
            self._load_model()
        return WhisperTranscriber._model
    
    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
        task: str = "transcribe",
        word_timestamps: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., "en", "es")
            task: "transcribe" or "translate"
            word_timestamps: Include word-level timestamps
            
        Returns:
            Dict with transcription results
        """
        logger.info(f"Transcribing: {audio_path}")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            result = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                word_timestamps=word_timestamps,
                verbose=False
            )
            
            # Extract segments with timestamps
            segments = []
            for seg in result.get("segments", []):
                segment_data = {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                }
                
                # Include word-level data if available
                if word_timestamps and "words" in seg:
                    segment_data["words"] = [
                        {
                            "word": w["word"],
                            "start": w["start"],
                            "end": w["end"],
                            "probability": w.get("probability", 0)
                        }
                        for w in seg["words"]
                    ]
                
                segments.append(segment_data)
            
            # Calculate duration and confidence
            duration = result.get("segments", [{}])[-1].get("end", 0) if result.get("segments") else 0
            
            # Estimate confidence from word probabilities
            all_probs = []
            for seg in result.get("segments", []):
                if "words" in seg:
                    all_probs.extend([w.get("probability", 0) for w in seg["words"]])
            avg_confidence = np.mean(all_probs) if all_probs else 0.8
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", language),
                "duration_seconds": round(duration, 2),
                "confidence": round(float(avg_confidence), 2),
                "segments": segments,
                "word_count": len(result["text"].split())
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        file_extension: str = ".webm",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio from bytes (for API uploads).
        
        Args:
            audio_bytes: Raw audio data
            file_extension: File extension for temp file
            **kwargs: Additional args for transcribe()
            
        Returns:
            Transcription results
        """
        # Write bytes to temp file
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        try:
            result = self.transcribe(tmp_path, **kwargs)
            return result
        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds."""
        import subprocess
        
        try:
            # Use ffprobe if available
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries",
                    "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path
                ],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except Exception:
            # Fallback: load audio and measure
            audio = whisper.load_audio(audio_path)
            return len(audio) / whisper.audio.SAMPLE_RATE
    
    def check_health(self) -> Dict[str, Any]:
        """Check if Whisper is ready."""
        try:
            model = self.model
            return {
                "status": "healthy",
                "model_size": settings.whisper_model_size,
                "device": settings.whisper_device,
                "cuda_available": torch.cuda.is_available()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Module-level instance
transcriber = WhisperTranscriber()


def transcribe_audio(audio_path: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for transcription."""
    return transcriber.transcribe(audio_path, **kwargs)


def transcribe_audio_bytes(audio_bytes: bytes, **kwargs) -> Dict[str, Any]:
    """Convenience function for transcribing bytes."""
    return transcriber.transcribe_bytes(audio_bytes, **kwargs)