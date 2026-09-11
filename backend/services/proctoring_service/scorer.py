"""
Attempt scorer - auto/AI scoring for submitted assessment attempts.
Location: backend/services/proctoring_service/scorer.py

Routes each answer to the right engine based on the question's scoring mode:
  - MCQ (auto): exact-match of selected options against the correct set.
  - Coding (auto): runs the existing code-execution test harness (Judge0).
  - AI: spoken/video/system-design answers -> existing evaluation engine
    (best-effort; degrades gracefully if the LLM is unavailable).

Each question keeps its author-defined point value (`max_score`); the overall
is the percentage of available points earned, on 0-100.

AI-scored answers take the TECHNICAL engine score only. Language, delivery and
body-language ratings are returned alongside for the recruiter to read, but they
never move the points awarded - a fluent wrong answer scores as a wrong answer.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _index_questions(assessment: dict) -> Dict[str, dict]:
    """Flatten an assessment's sections into a question_id -> question map."""
    index: Dict[str, dict] = {}
    for section in assessment.get("sections", []):
        for q in section.get("questions", []):
            index[q["id"]] = q
    return index


def _score_mcq(question: dict, answer: dict) -> Tuple[float, str]:
    options = question.get("options") or []
    correct = {o["id"] for o in options if o.get("is_correct")}
    selected = set(answer.get("selected_option_ids") or [])
    if not correct:
        return 0.0, "No correct option configured"
    is_correct = selected == correct
    score = question.get("max_score", 5.0) if is_correct else 0.0
    return score, ("Correct" if is_correct else "Incorrect")


def _score_coding(question: dict, answer: dict) -> Tuple[float, str]:
    test_cases = question.get("test_cases") or []
    code = answer.get("code")
    language = answer.get("language") or "python"
    if not code or not test_cases:
        return 0.0, "No code or test cases"
    try:
        from services.code_execution_service.executor import (
            Language,
            TestCase,
            code_executor,
        )

        tcs = [
            TestCase(
                input=tc.get("input", ""),
                expected_output=tc.get("expected_output", ""),
                description=tc.get("description"),
                is_hidden=tc.get("is_hidden", False),
            )
            for tc in test_cases
        ]
        valid_langs = [l.value for l in Language]
        lang = Language(language) if language in valid_langs else Language.PYTHON
        result = code_executor.execute_with_test_cases(code, lang, tcs, timeout=5)
        passed = result.get("passed", 0)
        total = result.get("total_tests", 0) or 1
        pct = passed / total
        return (
            round(pct * question.get("max_score", 5.0), 2),
            f"{passed}/{total} tests passed ({result.get('pass_rate', 0)}%)",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Coding auto-score failed: %s", e)
        return 0.0, f"Execution error: {e}"


def _score_ai(question: dict, answer: dict) -> Tuple[float, str, Optional[dict]]:
    """
    Grade a free-form answer.

    Returns (points, detail, engine_scores). Points come from the technical
    engine alone; `engine_scores` carries every axis for display.
    """
    transcript = answer.get("transcript")
    if not transcript:
        return 0.0, "No answer recorded", None
    try:
        from services.evaluation_service.rubric_scorer import rubric_scorer

        result = rubric_scorer.evaluate(
            session_id=answer.get("attempt_id", "attempt"),
            question_id=question.get("id", "q"),
            question_text=question.get("prompt", ""),
            answer_text=transcript,
            speech_metrics=answer.get("speech_metrics"),
            body_language_metrics=answer.get("body_language_metrics"),
            interview_type="behavioral"
            if question.get("type") == "video_answer"
            else "system_design"
            if question.get("type") == "system_design"
            else "technical",
        )
        engine_scores = {
            engine.engine: engine.score
            for engine in result.engines
            if engine.assessed and engine.score is not None
        }

        technical = result.engine("technical")
        if technical is None or technical.score is None:
            # Do not guess. Flag for manual review instead of awarding points.
            return (
                0.0,
                "AI grading unavailable - needs manual review",
                engine_scores or None,
            )

        # Technical correctness alone converts into points for this question.
        points = round((technical.score / 100.0) * question.get("max_score", 5.0), 2)
        return points, f"AI evaluated - technical {technical.score:.0f}/100", engine_scores
    except Exception as e:  # noqa: BLE001
        logger.info("AI scoring unavailable: %s", e)
        # No length-based fallback: word count is not evidence of a correct
        # answer, and scoring one would reintroduce exactly the inflation this
        # engine split removed. Submission still succeeds; the answer is queued
        # for manual review.
        return 0.0, "AI grading unavailable - needs manual review", None


def score_attempt(assessment: dict, answers: List[dict]) -> dict:
    """Score every answer and return per-question + overall results."""
    qindex = _index_questions(assessment)
    per_question: List[dict] = []
    total_score = 0.0
    total_weight = 0.0

    for ans in answers:
        q = qindex.get(ans.get("question_id"))
        if not q:
            continue
        scoring_mode = q.get("scoring_mode", "ai")
        qtype = q.get("type")

        engine_scores: Optional[dict] = None
        if qtype == "mcq":
            score, detail = _score_mcq(q, ans)
        elif qtype == "coding" and scoring_mode == "auto":
            score, detail = _score_coding(q, ans)
        elif scoring_mode == "manual":
            score, detail = 0.0, "Pending manual review"
        else:
            score, detail, engine_scores = _score_ai(q, ans)

        max_score = q.get("max_score", 5.0) or 5.0
        entry = {
            "question_id": q["id"],
            "type": qtype,
            "scoring_mode": scoring_mode,
            "score": score,
            "max_score": max_score,
            "detail": detail,
        }
        if engine_scores:
            # Per-axis ratings for display only; they do not affect `score`.
            entry["engine_scores"] = engine_scores
        per_question.append(entry)
        total_score += score
        total_weight += max_score

    # Percentage of available points earned, on the 0-100 scale.
    overall = round((total_score / total_weight) * 100.0, 2) if total_weight else 0.0
    return {
        "per_question": per_question,
        "overall_score": overall,
        "scale": {"min": 0, "max": 100},
        "raw_total": round(total_score, 2),
        "max_total": round(total_weight, 2),
    }
