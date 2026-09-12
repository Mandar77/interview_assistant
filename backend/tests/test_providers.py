"""
Provider contract tests.
Location: backend/tests/test_providers.py

Runs in CI with no model, no server and no Docker.

Guards the thing that makes two deployment tiers off one codebase safe: every
provider must satisfy the same surface, and swapping one must not change how
the application behaves. A provider that silently returned a different shape
would produce zeroed metrics or fabricated scores rather than an obvious error.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Must be set before importing anything that reads settings.
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("STT_PROVIDER", "groq")
os.environ.setdefault("EXEC_PROVIDER", "disabled")

import json  # noqa: E402

from utils.llm_providers import KNOWN_PROVIDERS, build_provider  # noqa: E402
from utils.llm_providers.base import LLMProvider, extract_json_object  # noqa: E402
from utils.llm_providers.gemini_provider import to_gemini_schema  # noqa: E402

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  [PASS] {label}")
    else:
        FAILED += 1
        print(f"  [FAIL] {label} {detail}")


# =============================================================================
# 1. Registry
# =============================================================================
print("\n[1] provider registry")

# A provider whose backing library is not installed must fail with a clean
# ModuleNotFoundError and nothing else. That is not a defect — it is the lazy
# import working: the hosted image ships without `ollama` on purpose, and the
# self-hosted one needs no hosted-API client. Anything other than a missing
# module means the adapter is doing work at construction time that it should
# be deferring.
available = []
for name in KNOWN_PROVIDERS:
    try:
        provider = build_provider(name)
    except ModuleNotFoundError as exc:
        check(f"{name}: absent optional dependency handled cleanly", True, f"({exc.name} not installed)")
        continue
    except Exception as exc:  # pragma: no cover - a build failure is the finding
        check(f"{name}: builds without network/keys", False, f"raised {type(exc).__name__}: {exc}")
        continue
    available.append(name)
    check(f"{name}: builds without network/keys", isinstance(provider, LLMProvider))
    check(f"{name}: reports a name", bool(provider.name))

# Whatever the environment, the two that need no third-party client must work.
for required in ("fake", "gemini"):
    check(f"{required}: always constructible", required in available)

try:
    build_provider("nope")
    check("unknown provider rejected", False, "should have raised")
except ValueError:
    check("unknown provider rejected", True)

# Every provider that *can* be built here must implement the surface the app
# actually calls.
for name in available:
    provider = build_provider(name)
    for method in ("generate", "check_health", "get_embeddings", "generate_json", "generate_stream"):
        check(f"{name}: implements {method}()", callable(getattr(provider, method, None)))


# =============================================================================
# 2. Fake provider behaviour (the one CI actually runs on)
# =============================================================================
print("\n[2] fake provider")

fake = build_provider("fake")

check("health is up", fake.check_health() is True)

text = fake.generate(prompt="hello")
check("returns a string", isinstance(text, str) and len(text) > 0)

check(
    "deterministic for identical prompts",
    fake.generate(prompt="same") == fake.generate(prompt="same"),
)
check(
    "differs for different prompts",
    fake.generate(prompt="a") != fake.generate(prompt="b"),
)

emb = fake.get_embeddings("hello")
check("embeddings are a float vector", isinstance(emb, list) and len(emb) == 768)
check("embeddings deterministic", emb == fake.get_embeddings("hello"))

# json_mode must yield parseable JSON, because callers parse it.
parsed = extract_json_object(fake.generate(prompt="correctness_score", json_mode=True))
check("json_mode output parses", isinstance(parsed, dict), f"got {parsed!r}")

# Schema mode must satisfy the schema, or generation falls back to canned
# questions and the whole point of the fake provider is lost.
QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "skill_tags": {"type": "array", "items": {"type": "string"}},
                    "expected_duration_mins": {"type": "integer"},
                },
                "required": ["question", "skill_tags", "expected_duration_mins"],
            },
        }
    },
    "required": ["questions"],
}
doc = json.loads(fake.generate(prompt="gen", json_schema=QUESTION_SCHEMA))
check("schema: top-level key present", "questions" in doc)
check("schema: array populated", isinstance(doc["questions"], list) and len(doc["questions"]) > 0)
first = doc["questions"][0]
check("schema: required string field", isinstance(first.get("question"), str))
check("schema: required int field", isinstance(first.get("expected_duration_mins"), int))
check("schema: nested array field", isinstance(first.get("skill_tags"), list))

check("records calls for assertions", len(fake.calls) > 0)


# =============================================================================
# 3. Gemini schema translation (pure function - no key needed)
# =============================================================================
print("\n[3] gemini schema translation")

translated = to_gemini_schema(QUESTION_SCHEMA)
check("object type upper-cased", translated["type"] == "OBJECT")
check("nested array type upper-cased", translated["properties"]["questions"]["type"] == "ARRAY")
check(
    "deeply nested integer upper-cased",
    translated["properties"]["questions"]["items"]["properties"]["expected_duration_mins"]["type"]
    == "INTEGER",
)
check(
    "required list preserved",
    translated["properties"]["questions"]["items"]["required"]
    == ["question", "skill_tags", "expected_duration_mins"],
)
# Gemini rejects unknown keys outright, so they must be dropped not passed through.
check(
    "unsupported keys dropped",
    "additionalProperties" not in to_gemini_schema({"type": "object", "additionalProperties": False}),
)


# =============================================================================
# 4. JSON extraction (the parser that replaced the greedy regex)
# =============================================================================
print("\n[4] balanced-brace JSON extraction")

check("trailing prose ignored", extract_json_object('{"a": 1}  then commentary') == {"a": 1})
check("leading prose ignored", extract_json_object('Sure!\n{"a": 2}') == {"a": 2})
check("braces inside strings", extract_json_object('{"a": "x } y", "b": 1}') == {"a": "x } y", "b": 1})
check("nested objects", extract_json_object('{"a": {"b": {"c": 3}}}') == {"a": {"b": {"c": 3}}})
check("skips malformed, takes next", extract_json_object('{"bad": ,} {"good": 1}') == {"good": 1})
check("no json -> None", extract_json_object("nothing here") is None)
check("empty -> None", extract_json_object("") is None)


# =============================================================================
# 5. Code-execution gate
# =============================================================================
print("\n[5] code execution gate")

from services.code_execution_service.executor import (  # noqa: E402
    code_execution_enabled,
    disabled_result,
)

check("disabled when EXEC_PROVIDER=disabled", code_execution_enabled() is False)
result = disabled_result()
check("disabled result is labelled", result.status == "unavailable")
check("disabled result explains itself", bool(result.error_message))


# =============================================================================
# 6. The application actually runs on the fake provider
# =============================================================================
print("\n[6] application paths on the fake provider")

from models.schemas import DifficultyLevel, InterviewType, QuestionRequest  # noqa: E402
from services.evaluation_service.rubric_scorer import rubric_scorer  # noqa: E402
from services.question_service.generator import question_generator  # noqa: E402

JD = "Staff Backend Engineer. Payments ledger, 40k TPS, Kafka exactly-once, Postgres."
questions = question_generator.generate(
    QuestionRequest(
        job_description=JD,
        interview_type=InterviewType.TECHNICAL,
        difficulty=DifficultyLevel.MEDIUM,
        num_questions=2,
    )
)
check("generation returns questions", len(questions) > 0)
check(
    "generation did NOT fall back",
    all(not getattr(q, "is_fallback", False) for q in questions),
    "fake provider should satisfy the schema",
)

# The job description must reach the model - this is what stopped questions
# being generic, so a regression here is worth catching.
prompts = " ".join(c["prompt"] for c in question_generator.llm_client.calls) \
    if hasattr(question_generator.llm_client, "calls") else ""
check("job description is sent to the model", "40k TPS" in prompts, "JD grounding regressed")

evaluation = rubric_scorer.evaluate(
    session_id="ci",
    question_id="q1",
    question_text="Explain how a hash map achieves O(1) average lookup.",
    answer_text="A hash map hashes the key to a bucket index, so lookup is O(1) on average.",
    interview_type="technical",
)
technical = evaluation.engine("technical")
check("technical engine assessed", technical is not None and technical.assessed)
check("technical score in range", technical is not None and 0 <= (technical.score or -1) <= 100)
check(
    "engines without data are not scored",
    evaluation.engine("body_language").score is None,
    "absent camera must not be given a score",
)
check(
    "no combined score exists",
    not hasattr(evaluation, "overall_score") and not hasattr(evaluation, "weighted_score"),
)


# =============================================================================
print("\n" + "=" * 70)
print(f"RESULTS: {PASSED} passed, {FAILED} failed")
print("=" * 70)
sys.exit(1 if FAILED else 0)
