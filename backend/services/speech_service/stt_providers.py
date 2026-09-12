"""
Speech-to-text providers.
Location: backend/services/speech_service/stt_providers.py

Two backends behind one surface, selected by `STT_PROVIDER`:

    whisper_local   openai-whisper on this machine — the "owned" tier.
                    Accurate and private, but drags in torch (~2GB installed),
                    which is most of the container image size.
    groq            Groq's hosted Whisper — free tier, no credit card.
                    Lets the hosted tier ship without torch at all.

Both return the identical dict shape, because `analyzer.py` reads `segments`
for pause analysis and `text` for everything else. A provider that returned a
different shape would silently produce zeroed speech metrics.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


def empty_result(language: str = "en") -> Dict[str, Any]:
    """The shape every provider must return, with nothing in it."""
    return {
        "text": "",
        "language": language,
        "duration_seconds": 0.0,
        "confidence": 0.0,
        "segments": [],
        "word_count": 0,
    }


class GroqSTTProvider:
    """
    Hosted Whisper via Groq's OpenAI-compatible transcription endpoint.

    Free tier covers 2,000 audio requests/day with no credit card, which is far
    beyond what a demo needs.
    """

    name = "groq"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_stt_model
        self.base_url = (base_url or settings.groq_base_url).rstrip("/")
        self.timeout = timeout or settings.llm_request_timeout_seconds

    def _require_key(self) -> str:
        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to backend/.env — get a free "
                "key (no credit card) at https://console.groq.com/keys"
            )
        return self.api_key

    def transcribe(
        self,
        audio_path: str,
        word_timestamps: bool = False,
        language: Optional[str] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        key = self._require_key()

        # verbose_json is required to get segment timings; without them the
        # pause metrics in analyzer.py silently come back as zero.
        granularities = ["segment"]
        if word_timestamps:
            granularities.append("word")

        data = {
            "model": self.model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": granularities,
        }
        if language:
            data["language"] = language

        try:
            with open(audio_path, "rb") as handle:
                files = {"file": (os.path.basename(audio_path), handle, "application/octet-stream")}
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {key}"},
                        data=data,
                        files=files,
                    )
                    response.raise_for_status()
                    payload = response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300] if exc.response is not None else ""
            logger.error("Groq STT HTTP %s: %s", exc.response.status_code, body)
            raise
        except Exception as exc:
            logger.error("Groq STT request failed: %s", exc)
            raise

        return self._normalise(payload, language or "en")

    @staticmethod
    def _normalise(payload: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Map Groq's verbose_json onto the local Whisper result shape."""
        text = (payload.get("text") or "").strip()

        segments: List[Dict[str, Any]] = []
        confidences: List[float] = []
        for seg in payload.get("segments") or []:
            segments.append(
                {
                    "start": seg.get("start", 0.0),
                    "end": seg.get("end", 0.0),
                    "text": (seg.get("text") or "").strip(),
                }
            )
            # Whisper reports avg_logprob; convert to a rough 0-1 confidence so
            # the field means the same thing as the local provider's.
            if "avg_logprob" in seg:
                try:
                    import math

                    confidences.append(math.exp(float(seg["avg_logprob"])))
                except (ValueError, OverflowError):
                    pass

        duration = float(payload.get("duration") or (segments[-1]["end"] if segments else 0.0))
        confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "text": text,
            "language": payload.get("language", language),
            "duration_seconds": round(duration, 2),
            "confidence": round(confidence, 2),
            "segments": segments,
            "word_count": len(text.split()),
        }

    def transcribe_bytes(
        self, audio_bytes: bytes, file_extension: str = ".webm", **kwargs: Any
    ) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            return self.transcribe(tmp_path, **kwargs)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def get_audio_duration(self, audio_path: str) -> float:
        """Not needed for the hosted path — duration comes back with the result."""
        return 0.0

    def check_health(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "unconfigured", "provider": self.name, "model": self.model}
        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            healthy = response.status_code == 200
        except Exception as exc:
            logger.error("Groq STT health check failed: %s", exc)
            healthy = False
        return {
            "status": "healthy" if healthy else "unhealthy",
            "provider": self.name,
            "model": self.model,
        }


def build_stt_provider(name: str):
    """
    Instantiate the configured STT backend.

    `whisper_local` is imported lazily so the hosted image can omit torch and
    openai-whisper entirely without this module failing to import.
    """
    key = (name or "").strip().lower()

    if key == "groq":
        return GroqSTTProvider()

    if key in ("whisper_local", "local", "whisper"):
        from services.speech_service.transcriber import WhisperTranscriber

        return WhisperTranscriber()

    raise ValueError(f"Unknown STT_PROVIDER {name!r}. Expected: groq | whisper_local")
