"""
Question Service API Routes
Location: backend/services/question_service/routes.py
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from models.schemas import (
    GeneratedQuestion,
    QuestionRequest,
    JobDescriptionInput,
    SkillTag,
    InterviewType,
    DifficultyLevel
)
from services.question_service.skill_parser import parse_job_description, skill_parser
from services.question_service.generator import generate_questions, question_generator

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class SkillParseResponse(BaseModel):
    """Response for skill parsing endpoint."""
    skills: List[SkillTag]
    summary: dict
    total_count: int


class QuestionGenerationResponse(BaseModel):
    """Response for question generation endpoint."""
    questions: List[GeneratedQuestion]
    skills_used: List[str]
    total_count: int


class AdaptiveQuestionRequest(BaseModel):
    """Request for adaptive question generation."""
    job_description: str
    previous_scores: dict = Field(default_factory=dict, description="Category -> score mapping")
    target_categories: Optional[List[str]] = None
    num_questions: int = Field(default=3, ge=1, le=10)


class SingleQuestionRequest(BaseModel):
    """Request for single question generation."""
    skill: str
    interview_type: InterviewType = InterviewType.TECHNICAL
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/parse-skills", response_model=SkillParseResponse)
async def parse_skills(input_data: JobDescriptionInput):
    """
    Parse a job description and extract structured skill tags.
    
    - Extracts technical and soft skills
    - Categorizes skills (programming, data_structures, algorithms, etc.)
    - Calculates importance scores
    """
    try:
        logger.info(f"Parsing job description ({len(input_data.job_description)} chars)")
        
        skills = parse_job_description(
            input_data.job_description,
            use_llm=True
        )
        
        summary = skill_parser.get_skill_summary(skills)
        
        return SkillParseResponse(
            skills=skills,
            summary=summary,
            total_count=len(skills)
        )
        
    except Exception as e:
        logger.error(f"Skill parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Skill parsing failed: {str(e)}")


@router.post("/generate", response_model=QuestionGenerationResponse)
async def generate_interview_questions(request: QuestionRequest):
    """
    Generate interview questions based on job description and parameters.
    
    - Supports OA, Technical, System Design, Behavioral, and Mixed types
    - Adapts to specified difficulty level
    - Uses extracted skills to generate relevant questions
    """
    try:
        logger.info(f"Generating {request.num_questions} {request.interview_type.value} questions")
        
        # Parse skills for logging
        skills = parse_job_description(request.job_description, use_llm=False)
        skills_used = request.focus_skills or [s.skill for s in skills[:10]]
        
        # Generate questions
        questions = generate_questions(request)
        
        return QuestionGenerationResponse(
            questions=questions,
            skills_used=skills_used,
            total_count=len(questions)
        )
        
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")


@router.post("/generate-single", response_model=GeneratedQuestion)
async def generate_single_question(request: SingleQuestionRequest):
    """
    Generate a single question for a specific skill.
    
    Useful for quick question generation or filling gaps.
    """
    try:
        question = question_generator.generate_single(
            skill=request.skill,
            interview_type=request.interview_type,
            difficulty=request.difficulty
        )
        
        if not question:
            raise HTTPException(status_code=500, detail="Failed to generate question")
        
        return question
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single question generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-adaptive", response_model=QuestionGenerationResponse)
async def generate_adaptive_questions(request: AdaptiveQuestionRequest):
    """
    Generate questions that adapt based on previous performance.
    
    - Focuses on weak areas (score < 3)
    - Adjusts difficulty based on average performance
    - Useful for practice sessions
    """
    try:
        questions = question_generator.generate_adaptive(
            job_description=request.job_description,
            previous_scores=request.previous_scores,
            target_categories=request.target_categories
        )
        
        # Determine which skills were targeted
        weak_areas = [cat for cat, score in request.previous_scores.items() if score < 3]
        skills_used = request.target_categories or weak_areas or ["general"]
        
        return QuestionGenerationResponse(
            questions=questions,
            skills_used=skills_used,
            total_count=len(questions)
        )
        
    except Exception as e:
        logger.error(f"Adaptive question generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_interview_types():
    """Get available interview types and their descriptions."""
    return {
        "types": [
            {
                "value": "oa",
                "name": "Online Assessment",
                "description": "Coding problems with test cases",
                "typical_duration": "30-60 mins"
            },
            {
                "value": "technical",
                "name": "Technical Interview",
                "description": "Conceptual and practical questions",
                "typical_duration": "45-60 mins"
            },
            {
                "value": "system_design",
                "name": "System Design",
                "description": "Architecture and scalability problems",
                "typical_duration": "45-60 mins"
            },
            {
                "value": "behavioral",
                "name": "Behavioral",
                "description": "STAR format situational questions",
                "typical_duration": "30-45 mins"
            },
            {
                "value": "mixed",
                "name": "Mixed",
                "description": "Combination of all types",
                "typical_duration": "60-90 mins"
            }
        ],
        "difficulties": [
            {"value": "easy", "description": "Entry-level, fundamental concepts"},
            {"value": "medium", "description": "Mid-level, combined concepts"},
            {"value": "hard", "description": "Senior-level, complex problems"},
            {"value": "adaptive", "description": "Adjusts based on performance"}
        ]
    }


@router.get("/health")
async def health_check():
    """Health check for the question service."""
    from utils.llm_client import get_llm_client
    
    llm_healthy = get_llm_client().check_health()
    
    return {
        "service": "question_service",
        "status": "healthy" if llm_healthy else "degraded",
        "llm_available": llm_healthy,
        "spacy_loaded": skill_parser.nlp is not None
    }