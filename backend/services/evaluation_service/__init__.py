"""
Evaluation Service - Independent per-axis scoring and hallucination checking
Location: backend/services/evaluation_service/__init__.py

Scores are 0-100 and are reported per engine. There is no combined score;
see rubric_scorer's module docstring for why.
"""

from services.evaluation_service.rubric_scorer import (
    RubricScorer,
    rubric_scorer,
    evaluate_response,
    DimensionScore,
    EngineScore,
    EvaluationResult,
    EVALUATION_ENGINES,
    ENGINE_PASS_MARKS,
    SCORE_LEVELS,
    SCORE_BANDS,
    SCALE_MIN,
    SCALE_MAX,
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
    "DimensionScore",
    "EngineScore",
    "EvaluationResult",
    "EVALUATION_ENGINES",
    "ENGINE_PASS_MARKS",
    "SCORE_LEVELS",
    "SCORE_BANDS",
    "SCALE_MIN",
    "SCALE_MAX",
    # Hallucination Checker
    "HallucinationChecker",
    "hallucination_checker",
    "check_hallucinations",
    "ClaimVerification",
    "HallucinationCheckResult",
    # Routes
    "router"
]
