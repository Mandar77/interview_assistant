"""
LLM provider registry.
Location: backend/utils/llm_providers/__init__.py

`LLM_PROVIDER` selects the adapter at startup. Providers are imported lazily so
a deployment never needs the other backends' dependencies installed — the
hosted tier ships without `ollama`, and CI needs neither.
"""

from __future__ import annotations

import logging
from typing import Dict, Type

from utils.llm_providers.base import LLMProvider, extract_json_object

logger = logging.getLogger(__name__)

__all__ = ["LLMProvider", "extract_json_object", "build_provider", "KNOWN_PROVIDERS"]

KNOWN_PROVIDERS = ("ollama", "gemini", "fake")


def build_provider(name: str) -> LLMProvider:
    """
    Instantiate the named provider.

    Raises ValueError on an unknown name rather than silently falling back —
    a typo in LLM_PROVIDER should fail loudly at boot, not quietly serve
    something other than what was configured.
    """
    key = (name or "").strip().lower()

    if key == "fake":
        from utils.llm_providers.fake_provider import FakeProvider

        return FakeProvider()

    if key == "gemini":
        from utils.llm_providers.gemini_provider import GeminiProvider

        return GeminiProvider()

    if key == "ollama":
        from utils.llm_providers.ollama_provider import OllamaProvider

        return OllamaProvider()

    raise ValueError(
        f"Unknown LLM_PROVIDER {name!r}. Expected one of: {', '.join(KNOWN_PROVIDERS)}"
    )
