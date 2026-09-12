"""
Feedback Service API Routes
Location: backend/services/feedback_service/routes.py
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from services.feedback_service.synthesizer import (
    performance_band,
    synthesize_feedback
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class FeedbackRequest(BaseModel):
    """Request for generating feedback."""
    session_id: str
    evaluation_result: Dict[str, Any]
    question_text: str
    answer_text: str
    interview_type: str = "technical"
    verbosity: str = "detailed"  # brief, detailed, comprehensive


class FeedbackSectionResponse(BaseModel):
    """Response model for a feedback section."""
    title: str
    content: str
    priority: str
    category: str


class ImprovementTipResponse(BaseModel):
    """Response model for an improvement tip."""
    area: str
    tip: str
    example: Optional[str] = None
    resources: List[str] = []


class FeedbackResponse(BaseModel):
    """
    Response for feedback generation.

    `technical_performance` is the correctness verdict and stands alone;
    `engine_performance` carries one label per axis. There is no blended
    performance level.
    """
    session_id: str
    summary: str
    technical_performance: str
    engine_performance: Dict[str, str] = {}
    detailed_sections: List[FeedbackSectionResponse]
    improvement_tips: List[ImprovementTipResponse]
    strengths_highlight: List[str]
    priority_areas: List[str]
    recommended_topics: List[str]
    next_steps: List[str]
    encouragement: str
    generated_at: datetime


class QuickFeedbackRequest(BaseModel):
    """Simplified request for quick feedback."""
    question: str
    answer: str
    score: float = Field(..., ge=0, le=100, description="Technical score on the 0-100 scale")
    interview_type: str = "technical"


class SessionFeedbackRequest(BaseModel):
    """Request for session-level feedback (multiple questions)."""
    session_id: str
    evaluations: List[Dict[str, Any]]
    interview_type: str = "technical"


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/generate", response_model=FeedbackResponse)
def generate_feedback(request: FeedbackRequest):
    """
    Generate comprehensive feedback from evaluation results.
    
    Synthesizes:
    - Summary of performance
    - Detailed feedback per category
    - Specific improvement tips
    - Recommended study topics
    - Actionable next steps
    """
    try:
        logger.info(f"Generating feedback for session {request.session_id}")
        
        result = synthesize_feedback(
            session_id=request.session_id,
            evaluation_result=request.evaluation_result,
            question_text=request.question_text,
            answer_text=request.answer_text,
            interview_type=request.interview_type,
            verbosity=request.verbosity
        )
        
        # Convert dataclasses to response models
        detailed_sections = [
            FeedbackSectionResponse(
                title=s.title,
                content=s.content,
                priority=s.priority,
                category=s.category
            )
            for s in result.detailed_sections
        ]
        
        improvement_tips = [
            ImprovementTipResponse(
                area=t.area,
                tip=t.tip,
                example=t.example,
                resources=t.resources
            )
            for t in result.improvement_tips
        ]
        
        return FeedbackResponse(
            session_id=result.session_id,
            summary=result.summary,
            technical_performance=result.technical_performance,
            engine_performance=result.engine_performance,
            detailed_sections=detailed_sections,
            improvement_tips=improvement_tips,
            strengths_highlight=result.strengths_highlight,
            priority_areas=result.priority_areas,
            recommended_topics=result.recommended_topics,
            next_steps=result.next_steps,
            encouragement=result.encouragement,
            generated_at=result.generated_at
        )
        
    except Exception as e:
        logger.error(f"Feedback generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Feedback generation failed: {str(e)}")


@router.post("/generate-quick")
def generate_quick_feedback(request: QuickFeedbackRequest):
    """
    Generate quick feedback without full evaluation.
    
    Useful for rapid assessment or when full metrics aren't available.
    """
    try:
        # Minimal evaluation payload: one technical engine carrying the score
        # the caller supplied. Nothing is blended.
        evaluation_result = {
            "engines": [
                {
                    "engine": "technical",
                    "engine_name": "Technical Correctness",
                    "score": request.score,
                    "assessed": True,
                    "critical": True,
                    "feedback": "Score supplied by the caller.",
                    "dimensions": [],
                    "evidence": [],
                }
            ],
            "strengths": [],
            "weaknesses": []
        }
        
        result = synthesize_feedback(
            session_id="quick_feedback",
            evaluation_result=evaluation_result,
            question_text=request.question,
            answer_text=request.answer,
            interview_type=request.interview_type,
            verbosity="brief"
        )
        
        return {
            "summary": result.summary,
            "technical_performance": result.technical_performance,
            "engine_performance": result.engine_performance,
            "improvement_tips": [
                {"area": t.area, "tip": t.tip}
                for t in result.improvement_tips[:3]
            ],
            "next_steps": result.next_steps[:3],
            "encouragement": result.encouragement
        }
        
    except Exception as e:
        logger.error(f"Quick feedback generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session-summary")
async def generate_session_summary(request: SessionFeedbackRequest):
    """
    Generate summary feedback for an entire interview session.
    
    Aggregates feedback across multiple questions.
    """
    try:
        if not request.evaluations:
            raise HTTPException(status_code=400, detail="No evaluations provided")
        
        # Aggregate per engine. Each axis is averaged across questions on its
        # own - engines are never averaged into a single session number.
        per_engine: Dict[str, List[float]] = {}
        engine_names: Dict[str, str] = {}
        all_strengths = []
        all_weaknesses = []

        for eval_data in request.evaluations:
            for engine in eval_data.get("engines", []):
                if not engine.get("assessed", True):
                    continue
                score = engine.get("score")
                if score is None:
                    continue
                engine_id = engine.get("engine", "unknown")
                per_engine.setdefault(engine_id, []).append(float(score))
                engine_names[engine_id] = engine.get("engine_name", engine_id)
            all_strengths.extend(eval_data.get("strengths", []))
            all_weaknesses.extend(eval_data.get("weaknesses", []))

        engine_summary = {
            engine_id: {
                "name": engine_names.get(engine_id, engine_id),
                "average": round(sum(values) / len(values), 1),
                "highest": round(max(values), 1),
                "lowest": round(min(values), 1),
                "questions_scored": len(values),
            }
            for engine_id, values in per_engine.items()
        }

        # The session verdict tracks technical correctness only.
        technical_scores = per_engine.get("technical", [])
        technical_avg = (
            round(sum(technical_scores) / len(technical_scores), 1)
            if technical_scores
            else None
        )
        performance = performance_band(technical_avg)
                
        # Count strength/weakness themes
        from collections import Counter
        strength_themes = Counter(all_strengths).most_common(3)
        weakness_themes = Counter(all_weaknesses).most_common(3)
        
        # Generate session-level feedback
        summary = {
            "session_id": request.session_id,
            "questions_evaluated": len(request.evaluations),
            "scale": {"min": 0, "max": 100},
            "engines": engine_summary,
            "technical_average": technical_avg,
            "performance_level": performance,
            "performance_basis": "technical",
            "top_strengths": [s[0] for s in strength_themes],
            "areas_for_improvement": [w[0] for w in weakness_themes],
            "recommendations": _get_session_recommendations(performance, weakness_themes),
            "overall_feedback": _get_session_feedback(performance, technical_avg)
        }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tips/{category}")
async def get_improvement_tips(category: str):
    """Get improvement tips for a specific category."""
    
    tips_db = {
        "technical": [
            {"tip": "Review fundamental data structures and algorithms", "priority": "high"},
            {"tip": "Practice coding problems daily on LeetCode or HackerRank", "priority": "high"},
            {"tip": "Explain your thought process as you solve problems", "priority": "medium"}
        ],
        "communication": [
            {"tip": "Use the STAR method for behavioral questions", "priority": "high"},
            {"tip": "Practice explaining technical concepts to non-technical people", "priority": "medium"},
            {"tip": "Record yourself and review for clarity", "priority": "medium"}
        ],
        "system_design": [
            {"tip": "Study the System Design Primer on GitHub", "priority": "high"},
            {"tip": "Always start by clarifying requirements", "priority": "high"},
            {"tip": "Practice drawing architecture diagrams", "priority": "medium"}
        ],
        "confidence": [
            {"tip": "Practice mock interviews with peers", "priority": "high"},
            {"tip": "Prepare and rehearse your introduction", "priority": "medium"},
            {"tip": "Use power poses before interviews", "priority": "low"}
        ]
    }
    
    if category not in tips_db:
        available = list(tips_db.keys())
        raise HTTPException(
            status_code=404, 
            detail=f"Category not found. Available: {available}"
        )
    
    return {
        "category": category,
        "tips": tips_db[category]
    }


@router.get("/health")
def health_check():
    """Health check for feedback service."""
    from utils.llm_client import get_llm_client
    
    llm_healthy = get_llm_client().check_health()
    
    return {
        "service": "feedback_service",
        "status": "healthy" if llm_healthy else "degraded",
        "llm_available": llm_healthy
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _get_session_recommendations(performance: str, weaknesses: List) -> List[str]:
    """Generate recommendations based on session performance."""
    base_recs = {
        "excellent": [
            "Consider practicing advanced topics to push your limits",
            "Help others prepare - teaching reinforces learning"
        ],
        "good": [
            "Focus on consistency across all question types",
            "Practice 2-3 mock interviews per week"
        ],
        "satisfactory": [
            "Dedicate focused study time to weak areas",
            "Review fundamentals before attempting advanced topics"
        ],
        "needs_improvement": [
            "Start with basics and build up gradually",
            "Consider working with a mentor or study group",
            "Practice daily, even for short periods"
        ]
    }
    
    recs = base_recs.get(performance, base_recs["satisfactory"])
    
    # Add weakness-specific recommendations
    if weaknesses:
        top_weakness = weaknesses[0][0] if weaknesses[0] else None
        if top_weakness:
            recs.insert(0, f"Priority: Address {top_weakness}")
    
    return recs


def _get_session_feedback(performance: str, technical_avg: Optional[float]) -> str:
    """Session message, anchored on technical correctness rather than a blend."""
    if technical_avg is None:
        return (
            "Technical correctness could not be graded for this session, so there is no "
            "verdict to report. Check that the evaluation model is running and try again."
        )

    messages = {
        "excellent": f"Outstanding session! Technical correctness averaged {technical_avg}/100. You're well-prepared for real interviews.",
        "good": f"Great work! Technical correctness averaged {technical_avg}/100, which shows solid preparation. A bit more precision will make you interview-ready.",
        "satisfactory": f"Good effort - technical correctness averaged {technical_avg}/100. Focus on accuracy and you'll improve quickly.",
        "needs_improvement": f"Technical correctness averaged {technical_avg}/100. Don't be discouraged - the fundamentals are where the score moves most.",
    }

    return messages.get(performance, messages["satisfactory"])