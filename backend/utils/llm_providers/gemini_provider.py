"""
Google AI Studio (Gemini) provider.
Location: backend/utils/llm_providers/gemini_provider.py

Chosen for the hosted "fast" tier because its free tier needs no credit card
and carries a 1M-token context. That context size is the reason it beats the
alternatives here: providers with a tokens-per-minute cap throttle partway
through a multi-question interview, whereas the binding limit here is requests
per day.

Talks to the REST API directly with httpx rather than pulling in an SDK — the
surface we need is two endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from utils.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Gemini's responseSchema is an OpenAPI subset: types are upper-case and it
# rejects unknown keys, so a plain JSON Schema cannot be passed through as-is.
_TYPE_MAP = {
    "object": "OBJECT",
    "array": "ARRAY",
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
}
_ALLOWED_KEYS = {"type", "properties", "items", "required", "enum", "description", "nullable"}


def to_gemini_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a plain JSON Schema into Gemini's responseSchema dialect."""
    if not isinstance(schema, dict):
        return schema

    out: Dict[str, Any] = {}
    for key, value in schema.items():
        if key not in _ALLOWED_KEYS:
            continue  # drop keys Gemini rejects rather than erroring the call
        if key == "type" and isinstance(value, str):
            out["type"] = _TYPE_MAP.get(value.lower(), value.upper())
        elif key == "properties" and isinstance(value, dict):
            out["properties"] = {k: to_gemini_schema(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            out["items"] = to_gemini_schema(value)
        else:
            out[key] = value
    return out


class GeminiProvider(LLMProvider):
    """Google AI Studio REST client."""

    name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.base_url = (base_url or settings.gemini_base_url).rstrip("/")
        self.embedding_model = embedding_model or settings.gemini_embedding_model
        self.timeout = timeout or settings.llm_request_timeout_seconds

    # ------------------------------------------------------------- internals

    def _require_key(self) -> str:
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to backend/.env — get a free "
                "key (no credit card) at https://aistudio.google.com/apikey"
            )
        return self.api_key

    # ------------------------------------------------------------- generate

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        num_ctx: Optional[int] = None,  # Ollama-only; ignored here
    ) -> str:
        key = self._require_key()
        url = f"{self.base_url}/models/{self.model}:generateContent"

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if json_schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = to_gemini_schema(json_schema)
        elif json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, params={"key": key}, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300] if exc.response is not None else ""
            # 429 is the free tier's daily/per-minute cap; surface it clearly so
            # callers report "unavailable" rather than inventing a score.
            logger.error("Gemini HTTP %s: %s", exc.response.status_code, body)
            raise
        except Exception as exc:
            logger.error("Gemini request failed: %s", exc)
            raise

        return self._first_text(data)

    @staticmethod
    def _first_text(data: Dict[str, Any]) -> str:
        """Pull the text out of a generateContent response, defensively."""
        candidates = data.get("candidates") or []
        if not candidates:
            feedback = data.get("promptFeedback") or {}
            raise ValueError(f"Gemini returned no candidates (feedback: {feedback})")

        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts)
        if not text:
            finish = candidates[0].get("finishReason")
            raise ValueError(f"Gemini returned an empty completion (finishReason: {finish})")
        return text

    # --------------------------------------------------------------- health

    def check_health(self) -> bool:
        if not self.api_key:
            logger.warning("Gemini health check: no API key configured")
            return False
        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(
                    f"{self.base_url}/models/{self.model}", params={"key": self.api_key}
                )
                return response.status_code == 200
        except Exception as exc:
            logger.error("Gemini health check failed: %s", exc)
            return False

    # ------------------------------------------------------------ embeddings

    def get_embeddings(self, text: str) -> List[float]:
        key = self._require_key()
        url = f"{self.base_url}/models/{self.embedding_model}:embedContent"
        payload = {
            "model": f"models/{self.embedding_model}",
            "content": {"parts": [{"text": text}]},
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, params={"key": key}, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("Gemini embedding failed: %s", exc)
            raise
        return (data.get("embedding") or {}).get("values") or []
