"""
LLM provider interface.
Location: backend/utils/llm_providers/base.py

Every provider implements the same three-method surface that the rest of the
application already uses. Call sites never import a provider directly — they
call `get_llm_client()`, which returns whichever adapter `LLM_PROVIDER` selects.

Keeping the surface this small is deliberate: all 11 LLM call sites in the
codebase go through `generate()`, so adding a provider is a new file here and
nothing else.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Pull the first complete JSON object out of a model reply.

    Scans for balanced braces (ignoring braces inside strings) rather than
    regex-matching to the last "}" in the response, which breaks whenever the
    model appends commentary or emits a second object. Returns None when the
    reply contains no parseable object at all - callers must treat that as
    "not assessed" rather than substituting a default score.
    """
    if not text:
        return None
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break  # Malformed; try the next "{".
                    if isinstance(parsed, dict):
                        return parsed
                    break
        start = text.find("{", start + 1)
    return None


class LLMProvider(ABC):
    """Common surface every LLM backend must satisfy."""

    #: Human-readable name, surfaced on /health so you can tell which adapter
    #: a deployed instance is actually running.
    name: str = "unknown"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        num_ctx: Optional[int] = None,
    ) -> str:
        """
        Return a completion as raw text.

        `json_schema` constrains the reply to an exact shape where the backend
        supports it — that is what stops small models emitting raw newlines
        inside strings. `json_mode` is the weaker "valid JSON, any shape"
        fallback. Providers that support neither must still return valid text;
        callers parse defensively with `extract_json_object`.

        `num_ctx` is Ollama-specific and ignored by hosted providers.
        """

    @abstractmethod
    def check_health(self) -> bool:
        """True when the backend is reachable and the configured model exists."""

    @abstractmethod
    def get_embeddings(self, text: str) -> List[float]:
        """Embed a single string (used by the culture crawler's FAISS store)."""

    # ---------------------------------------------------------------- shared

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Generate and parse a JSON object. Raises ValueError if unparseable."""
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            json_mode=True,
        )
        parsed = extract_json_object(response)
        if parsed is None:
            raise ValueError(f"Could not extract valid JSON from response: {response[:200]}...")
        return parsed

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """
        Stream a completion.

        Default implementation yields the whole reply as one chunk so that
        providers without streaming still satisfy callers.
        """
        yield self.generate(prompt=prompt, system_prompt=system_prompt, temperature=temperature)

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed several strings. Providers may override with a batch endpoint."""
        return [self.get_embeddings(t) for t in texts]
