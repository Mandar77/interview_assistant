"""
LLM client facade.
Location: backend/utils/llm_client.py

Every LLM call site in the application imports from here, so this module stays
the stable public surface while the actual backend is selected by the
`LLM_PROVIDER` setting:

    gemini  hosted "fast" tier — free tier, no credit card, 1M context
    ollama  self-hosted "owned" tier — local inference on your own hardware
    fake    deterministic, no network — used by CI

Nothing downstream knows which one is active. Adding a backend means adding a
file under `utils/llm_providers/`, not touching callers.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from config.settings import settings
from utils.llm_providers import LLMProvider, build_provider, extract_json_object

logger = logging.getLogger(__name__)

__all__ = ["LLMProvider", "extract_json_object", "get_llm_client", "reset_llm_client"]

_client: Optional[LLMProvider] = None
_lock = threading.Lock()


def get_llm_client() -> LLMProvider:
    """
    Return the process-wide LLM provider.

    Built on first use rather than at import time so that importing this module
    never requires a configured API key or a running Ollama — which is what
    lets the test suite import the app without a model available.
    """
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = build_provider(settings.llm_provider)
                logger.info(
                    "LLM provider initialised: %s (model=%s)",
                    _client.name,
                    getattr(_client, "model", "n/a"),
                )
    return _client


def reset_llm_client() -> None:
    """
    Drop the cached provider so the next call rebuilds from current settings.

    Used by tests that switch providers mid-process.
    """
    global _client
    with _lock:
        _client = None
