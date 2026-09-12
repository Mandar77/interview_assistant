"""
Evaluation Service API Routes
Location: backend/services/evaluation_service/routes.py

Every response reports one independent 0-100 rating per engine. No endpoint
returns a combined/overall score - that was removed on purpose, because
averaging language and delivery into the technical verdict let a fluent but
wrong answer read as a pass.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from services.evaluation_service.rubric_scorer import (
    evaluate_response,
    EvaluationResult,
    EVALUATION_ENGINES,
    ENGINE_PASS_MARKS,
    SCORE_LEVELS,
    SCALE_MIN,
    SCALE_MAX,
)
from services.evaluation_service.hallucination_checker import (
    check_hallucinations
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class EvaluationRequest(BaseModel):
    """Request for evaluating an interview response."""
    session_id: str
    question_id: str
    question_text: str
    answer_text: str
    interview_type: str = "technical"
    speech_metrics: Optional[Dict[str, Any]] = None
    language_metrics: Optional[Dict[str, Any]] = None
    body_language_metrics: Optional[Dict[str, Any]] = None
    timing_metrics: Optional[Dict[str, Any]] = None


class DimensionScoreResponse(BaseModel):
    """One measured dimension inside an engine."""
    dimension: str
    dimension_name: str
    score: Optional[float] = Field(None, ge=SCALE_MIN, le=SCALE_MAX)
    feedback: str
    evidence: List[str] = []


class EngineScoreResponse(BaseModel):
    """Independent rating for one evaluation axis."""
    engine: str
    engine_name: str
    score: Optional[float] = Field(None, ge=SCALE_MIN, le=SCALE_MAX)
    band: str
    assessed: bool
    critical: bool
    met_bar: Optional[bool] = None
    description: str
    feedback: str
    dimensions: List[DimensionScoreResponse] = []
    evidence: List[str] = []


class ScaleResponse(BaseModel):
    """The scale every score in this payload uses."""
    min: int = SCALE_MIN
    max: int = SCALE_MAX


class EvaluationResponse(BaseModel):
    """
    Per-question evaluation.

    Note the absence of overall_score / weighted_score: engines are reported
    side by side and are never blended.
    """
    session_id: str
    question_id: str
    scale: ScaleResponse
    engines: List[EngineScoreResponse]
    scores: Dict[str, Optional[float]]
    strengths: List[str]
    weaknesses: List[str]
    evaluation_available: bool
    notes: List[str] = []


class HallucinationCheckRequest(BaseModel):
    """Request for hallucination checking."""
    response_text: str
    question_context: Optional[str] = None
    domain: str = "software_engineering"


class ClaimVerificationResponse(BaseModel):
    """Response model for claim verification."""
    claim: str
    verification_status: str
    confidence: float
    explanation: str


class HallucinationCheckResponse(BaseModel):
    """Response for hallucination check endpoint."""
    total_claims: int
    verified_claims: int
    unverified_claims: int
    false_claims: int
    uncertain_claims: int
    hallucination_score: float
    flagged_claims: List[ClaimVerificationResponse]
    overall_assessment: str


class QuickEvaluationRequest(BaseModel):
    """Simplified request for quick evaluation."""
    question: str
    answer: str
    interview_type: str = "technical"


# =============================================================================
# Serialisation
# =============================================================================

def _to_response(result: EvaluationResult) -> EvaluationResponse:
    """Map the dataclass result onto the API model."""
    return EvaluationResponse(
        session_id=result.session_id,
        question_id=result.question_id,
        scale=ScaleResponse(min=result.scale_min, max=result.scale_max),
        engines=[
            EngineScoreResponse(
                engine=engine.engine,
                engine_name=engine.engine_name,
                score=engine.score,
                band=engine.band,
                assessed=engine.assessed,
                critical=engine.critical,
                met_bar=engine.met_bar,
                description=engine.description,
                feedback=engine.feedback,
                dimensions=[
                    DimensionScoreResponse(
                        dimension=d.dimension,
                        dimension_name=d.dimension_name,
                        score=d.score,
                        feedback=d.feedback,
                        evidence=d.evidence,
                    )
                    for d in engine.dimensions
                ],
                evidence=engine.evidence,
            )
            for engine in result.engines
        ],
        scores=result.scores,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        evaluation_available=result.evaluation_available,
        notes=result.notes,
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_interview_response(request: EvaluationRequest):
    """
    Evaluate an interview response with every engine reported separately.

    Engines and their inputs:
    - technical       <- LLM grading of correctness (CRITICAL, relevance-gated)
    - language        <- language metrics (grammar, vocabulary, clarity)
    - speech_delivery <- speech metrics (pace, fillers, pauses)
    - body_language   <- camera metrics (eye contact, posture, gestures)
    - time_management <- timing metrics

    Each returns its own 0-100 score. Engines with no input data report
    assessed=false and score=null rather than a neutral placeholder.
    """
    try:
        logger.info(f"Evaluating response for session {request.session_id}")

        result = evaluate_response(
            session_id=request.session_id,
            question_id=request.question_id,
            question_text=request.question_text,
            answer_text=request.answer_text,
            speech_metrics=request.speech_metrics,
            language_metrics=request.language_metrics,
            body_language_metrics=request.body_language_metrics,
            timing_metrics=request.timing_metrics,
            interview_type=request.interview_type
        )

        return _to_response(result)

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/evaluate-quick")
async def quick_evaluate(request: QuickEvaluationRequest):
    """
    Quick evaluation without speech/camera metrics.

    Only the technical engine can produce a score here; the others report
    assessed=false because their inputs were not supplied.
    """
    try:
        result = evaluate_response(
            session_id="quick_eval",
            question_id="quick_q",
            question_text=request.question,
            answer_text=request.answer,
            interview_type=request.interview_type
        )

        technical = result.engine("technical")

        return {
            "scale": {"min": SCALE_MIN, "max": SCALE_MAX},
            "scores": result.scores,
            "technical_score": technical.score if technical else None,
            "technical_band": technical.band if technical else "Not assessed",
            "technical_met_bar": technical.met_bar if technical else None,
            "evaluation_available": result.evaluation_available,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "notes": result.notes,
        }

    except Exception as e:
        logger.error(f"Quick evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-hallucinations", response_model=HallucinationCheckResponse)
async def check_for_hallucinations(request: HallucinationCheckRequest):
    """
    Check an interview response for potential hallucinations.

    Extracts factual claims and verifies them against known information.
    Returns verification status for each claim.
    """
    try:
        result = check_hallucinations(
            response_text=request.response_text,
            question_context=request.question_context,
            domain=request.domain
        )

        flagged = [
            ClaimVerificationResponse(
                claim=c.claim,
                verification_status=c.verification_status,
                confidence=c.confidence,
                explanation=c.explanation
            )
            for c in result.flagged_claims
        ]

        return HallucinationCheckResponse(
            total_claims=result.total_claims,
            verified_claims=result.verified_claims,
            unverified_claims=result.unverified_claims,
            false_claims=result.false_claims,
            uncertain_claims=result.uncertain_claims,
            hallucination_score=result.hallucination_score,
            flagged_claims=flagged,
            overall_assessment=result.overall_assessment
        )

    except Exception as e:
        logger.error(f"Hallucination check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rubric")
async def get_rubric():
    """Describe the evaluation engines, their inputs and the scoring scale."""
    return {
        "scale": {"min": SCALE_MIN, "max": SCALE_MAX},
        "combined_score": None,
        "combined_score_note": (
            "Engines are reported independently and are never averaged. Strong "
            "language or delivery cannot raise the technical rating."
        ),
        "engines": [
            {
                "id": engine_id,
                "name": meta["name"],
                "description": meta["description"],
                "critical": meta["critical"],
                "source": meta["source"],
                "dimensions": meta["dimensions"],
                "pass_mark": ENGINE_PASS_MARKS.get(engine_id),
            }
            for engine_id, meta in EVALUATION_ENGINES.items()
        ],
        "score_levels": SCORE_LEVELS,
    }


@router.get("/health")
async def health_check():
    """Health check for evaluation service."""
    from utils.llm_client import get_llm_client

    llm_healthy = get_llm_client().check_health()

    return {
        "service": "evaluation_service",
        "status": "healthy" if llm_healthy else "degraded",
        "llm_available": llm_healthy,
        "engines": len(EVALUATION_ENGINES),
        "scale_max": SCALE_MAX,
    }
