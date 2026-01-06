"""
Evaluation Service - Rubric-based scoring and hallucination checking
Location: backend/services/evaluation_service/__init__.py
"""

from services.evaluation_service.rubric_scorer import (
    RubricScorer,
    rubric_scorer,
    evaluate_response,
    RubricScore,
    EvaluationResult,
    RUBRIC_CATEGORIES,
    SCORE_LEVELS
)
from services.evaluation_service.hallucination_checker import (
    HallucinationChecker,
    hallucination_checker,
    check_hallucinations,
    ClaimVerification,
    HallucinationCheckResult
)
from services.evaluation_service.routes import router

__all__ = [
    # Rubric Scorer
    "RubricScorer",
    "rubric_scorer",
    "evaluate_response",
    "RubricScore",
    "EvaluationResult",
    "RUBRIC_CATEGORIES",
    "SCORE_LEVELS",
    # Hallucination Checker
    "HallucinationChecker",
    "hallucination_checker",
    "check_hallucinations",
    "ClaimVerification",
    "HallucinationCheckResult",
    # Routes
    "router"
]