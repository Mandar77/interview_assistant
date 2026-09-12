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
import time
from typing import Any, Dict, List, Optional

import re

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

# 429 = rate limited (free tier, per-minute). 500/503 = transient server side.
RETRYABLE_STATUS = {429, 500, 503}


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


def _redact(text: str, secret: Optional[str]) -> str:
    """Strip an API key out of text before it reaches a log or an exception."""
    if not text:
        return ""
    if secret and secret in text:
        text = text.replace(secret, "<REDACTED>")
    # Belt and braces: kill any leftover ?key=... in a URL.
    return re.sub(r"([?&]key=)[^&\s\"']+", r"<REDACTED>", text)


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
        self.max_retries = settings.llm_max_retries
        self.retry_base_seconds = settings.llm_retry_base_seconds
        self.fallback_model = (settings.gemini_fallback_model or "").strip()

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

        # The free tier rate-limits per minute and the shared endpoints return
        # 503 under load. One interview arrives as a burst (generate questions,
        # then grade each answer), so without backoff those bursts fail and the
        # engine reports "not assessed" mid-demo — which reads as a broken
        # product rather than a throttle.
        try:
            data = self._post_with_retry(url, payload, key)
        except RuntimeError:
            # Persistent capacity failure on the primary model. A different
            # model is usually healthy, and a slightly different model is far
            # better than no evaluation at all.
            if not self.fallback_model or self.fallback_model == self.model:
                raise
            logger.warning(
                "Gemini model %s unavailable; falling back to %s",
                self.model, self.fallback_model,
            )
            fallback_url = f"{self.base_url}/models/{self.fallback_model}:generateContent"
            data = self._post_with_retry(fallback_url, payload, key)

        return self._first_text(data)

    def _post_with_retry(
        self, url: str, payload: Dict[str, Any], key: str
    ) -> Dict[str, Any]:
        """POST with backoff on transient throttling/unavailability."""
        last_body = ""
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    # Key goes in a header, never the query string. As a URL param
                    # it ends up in every exception message, log and stack trace.
                    response = client.post(
                        url, headers={"x-goog-api-key": key}, json=payload
                    )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                last_body = _redact(
                    exc.response.text[:300] if exc.response is not None else "", key
                )

                if status in RETRYABLE_STATUS and attempt < self.max_retries:
                    # Honour Retry-After when the server sends one; otherwise
                    # back off exponentially from the configured base.
                    delay = self.retry_base_seconds * (2 ** attempt)
                    header = (exc.response.headers or {}).get("retry-after") if exc.response else None
                    if header:
                        try:
                            delay = max(delay, float(header))
                        except ValueError:
                            pass
                    logger.warning(
                        "Gemini HTTP %s (attempt %d/%d) - retrying in %.1fs",
                        status, attempt + 1, self.max_retries + 1, delay,
                    )
                    time.sleep(delay)
                    continue

                logger.error("Gemini HTTP %s: %s", status, last_body)
                raise RuntimeError(
                    f"Gemini request failed with HTTP {status}: {last_body}"
                ) from None

            except Exception as exc:
                logger.error("Gemini request failed: %s", _redact(str(exc), key))
                raise RuntimeError(
                    f"Gemini request failed: {_redact(str(exc), key)}"
                ) from None

        raise RuntimeError(f"Gemini request failed after retries: {last_body}")

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
                    f"{self.base_url}/models/{self.model}",
                    headers={"x-goog-api-key": self.api_key},
                )
                return response.status_code == 200
        except Exception as exc:
            logger.error("Gemini health check failed: %s", _redact(str(exc), self.api_key))
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
                response = client.post(url, headers={"x-goog-api-key": key}, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("Gemini embedding failed: %s", _redact(str(exc), key))
            raise RuntimeError(f"Gemini embedding failed: {_redact(str(exc), key)}") from None
        return (data.get("embedding") or {}).get("values") or []
