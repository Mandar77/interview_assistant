"""
Evaluation Service API Routes
Location: backend/services/evaluation_service/routes.py
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from dataclasses import asdict

from services.evaluation_service.rubric_scorer import (
    rubric_scorer,
    evaluate_response,
    RUBRIC_CATEGORIES,
    SCORE_LEVELS
)
from services.evaluation_service.hallucination_checker import (
    hallucination_checker,
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


class RubricScoreResponse(BaseModel):
    """Response model for a single rubric score."""
    category: str
    category_name: str
    score: float
    weight: float
    feedback: str
    evidence: List[str] = []


class EvaluationResponse(BaseModel):
    """Response for evaluation endpoint."""
    session_id: str
    question_id: str
    rubric_scores: List[RubricScoreResponse]
    overall_score: float
    weighted_score: float
    strengths: List[str]
    weaknesses: List[str]
    confidence_index: float
    pass_threshold: bool
    excellence_threshold: bool


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
# Endpoints
# =============================================================================

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_interview_response(request: EvaluationRequest):
    """
    Evaluate an interview response using the full rubric.
    
    Aggregates scores from:
    - LLM evaluation (technical, problem-solving, system design)
    - Speech metrics (confidence, pacing)
    - Language metrics (communication, grammar)
    - Body language metrics (if provided)
    - Timing metrics (if provided)
    
    Returns comprehensive rubric-based scores and feedback.
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
        
        # Convert dataclass to response model
        rubric_scores = [
            RubricScoreResponse(
                category=s.category,
                category_name=s.category_name,
                score=s.score,
                weight=s.weight,
                feedback=s.feedback,
                evidence=s.evidence
            )
            for s in result.rubric_scores
        ]
        
        return EvaluationResponse(
            session_id=result.session_id,
            question_id=result.question_id,
            rubric_scores=rubric_scores,
            overall_score=result.overall_score,
            weighted_score=result.weighted_score,
            strengths=result.strengths,
            weaknesses=result.weaknesses,
            confidence_index=result.confidence_index,
            pass_threshold=result.pass_threshold,
            excellence_threshold=result.excellence_threshold
        )
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/evaluate-quick")
async def quick_evaluate(request: QuickEvaluationRequest):
    """
    Quick evaluation without additional metrics.
    
    Uses only LLM-based evaluation for a fast assessment.
    Useful for testing or when speech/body metrics aren't available.
    """
    try:
        result = evaluate_response(
            session_id="quick_eval",
            question_id="quick_q",
            question_text=request.question,
            answer_text=request.answer,
            interview_type=request.interview_type
        )
        
        return {
            "overall_score": result.overall_score,
            "weighted_score": result.weighted_score,
            "pass": result.pass_threshold,
            "excellence": result.excellence_threshold,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "scores": {s.category: s.score for s in result.rubric_scores}
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
    """Get the evaluation rubric categories and weights."""
    return {
        "categories": [
            {
                "id": cat_id,
                "name": cat_info["name"],
                "weight": cat_info["weight"],
                "description": cat_info["description"],
                "source": cat_info["source"]
            }
            for cat_id, cat_info in RUBRIC_CATEGORIES.items()
        ],
        "score_levels": SCORE_LEVELS,
        "pass_threshold": 3.0,
        "excellence_threshold": 4.5
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
        "rubric_categories": len(RUBRIC_CATEGORIES)
    }