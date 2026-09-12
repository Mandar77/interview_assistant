"""
Deterministic in-process LLM provider.
Location: backend/utils/llm_providers/fake_provider.py

Exists so CI can exercise the real code paths without a model. The hosted
runners cannot start Ollama, and the whole test suite previously required a
live model plus a live server — which is why there was no CI at all.

It is deliberately *schema-aware*: when a caller passes a `json_schema` it
synthesises a reply that satisfies that schema, so question generation and
rubric scoring parse successfully and exercise their real downstream logic
instead of falling into their error branches.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from utils.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768


def _stable_float(seed: str, index: int) -> float:
    """Deterministic pseudo-random in [-1, 1] — same input, same vector."""
    digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).digest()
    return (int.from_bytes(digest[:4], "big") / 0xFFFFFFFF) * 2.0 - 1.0


def _score_for(seed: str, low: int = 55, high: int = 95) -> int:
    """Deterministic score in a plausible band, so assertions are stable."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return low + (int.from_bytes(digest[:2], "big") % max(1, (high - low + 1)))


class FakeProvider(LLMProvider):
    """Returns deterministic, schema-valid responses. No network, no model."""

    name = "fake"

    def __init__(self, model: str = "fake-1") -> None:
        self.model = model
        #: Every prompt seen, so tests can assert on what was actually sent
        #: (e.g. that the job description really was included in the prompt).
        self.calls: List[Dict[str, Any]] = []

    # ------------------------------------------------------------- generate

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
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "json_mode": json_mode,
                "json_schema": json_schema,
            }
        )

        seed = hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()[:16]

        if json_schema is not None:
            return json.dumps(self._synthesize(json_schema, seed))

        if json_mode:
            return json.dumps(self._guess_shape(prompt, seed))

        return f"[fake:{self.model}] deterministic response for seed {seed}."

    # --------------------------------------------------------- schema filler

    def _synthesize(self, schema: Dict[str, Any], seed: str, depth: int = 0) -> Any:
        """Build the smallest value satisfying `schema`."""
        if depth > 8:  # guard against pathological/recursive schemas
            return None

        stype = schema.get("type")

        if stype == "object":
            props: Dict[str, Any] = schema.get("properties", {}) or {}
            required = schema.get("required") or list(props.keys())
            return {
                key: self._synthesize(props[key], f"{seed}:{key}", depth + 1)
                for key in required
                if key in props
            }

        if stype == "array":
            item_schema = schema.get("items", {"type": "string"})
            # Two items: enough to exercise list handling, cheap to assert on.
            return [
                self._synthesize(item_schema, f"{seed}:{i}", depth + 1)
                for i in range(2)
            ]

        if stype == "integer":
            return _score_for(seed)

        if stype == "number":
            return float(_score_for(seed))

        if stype == "boolean":
            return False

        return f"fake-{seed[:8]}"

    def _guess_shape(self, prompt: str, seed: str) -> Dict[str, Any]:
        """
        Best-effort JSON for callers that asked for json_mode without a schema.

        Covers the two shapes the codebase asks for that way: the flat grader
        reply and the code-quality reply.
        """
        lowered = (prompt or "").lower()

        if "quality_score" in lowered:
            return {"quality_score": _score_for(seed), "feedback": "fake quality review"}
        if "approach_score" in lowered:
            return {"approach_score": _score_for(seed), "feedback": "fake approach review"}

        if "relevance_score" in lowered or "correctness_score" in lowered:
            return {
                "relevance_score": _score_for(seed + "rel", 70, 95),
                "relevance_note": "fake: answer addresses the question",
                "correctness_score": _score_for(seed + "cor"),
                "correctness_note": "fake: broadly correct",
                "correctness_quote": "",
                "problem_solving_score": _score_for(seed + "ps"),
                "problem_solving_note": "fake: structured reasoning",
                "factual_accuracy_score": _score_for(seed + "fa"),
                "factual_accuracy_note": "fake: no unsupported claims",
                "summary": "fake: deterministic grade",
            }

        return {"result": f"fake-{seed[:8]}"}

    # --------------------------------------------------------------- health

    def check_health(self) -> bool:
        return True

    # ------------------------------------------------------------ embeddings

    def get_embeddings(self, text: str) -> List[float]:
        seed = hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]
        return [_stable_float(seed, i) for i in range(EMBEDDING_DIM)]
