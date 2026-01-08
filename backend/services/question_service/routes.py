"""
Question Service API Routes (with SSE streaming support)
Location: backend/services/question_service/routes.py
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional, AsyncGenerator
from pydantic import BaseModel, Field
import logging
import json
import asyncio

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
    skills: List[SkillTag]
    summary: dict
    total_count: int


class QuestionGenerationResponse(BaseModel):
    questions: List[GeneratedQuestion]
    skills_used: List[str]
    total_count: int


class AdaptiveQuestionRequest(BaseModel):
    job_description: str
    previous_scores: dict = Field(default_factory=dict)
    target_categories: Optional[List[str]] = None
    num_questions: int = Field(default=3, ge=1, le=10)


class SingleQuestionRequest(BaseModel):
    skill: str
    interview_type: InterviewType = InterviewType.TECHNICAL
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM


# =============================================================================
# SSE Streaming Helper
# =============================================================================

def format_sse(data: dict, event: str = None) -> str:
    """Format data as Server-Sent Event."""
    msg = ""
    if event:
        msg += f"event: {event}\n"
    msg += f"data: {json.dumps(data)}\n\n"
    return msg


async def generate_questions_with_progress(
    request: QuestionRequest
) -> AsyncGenerator[str, None]:
    """
    Generate questions with progress updates via SSE.
    
    Events emitted:
    - progress: Status updates during generation
    - complete: Final result with questions
    - error: If something goes wrong
    """
    try:
        # Step 1: Starting
        yield format_sse({
            "status": "starting",
            "message": "Starting question generation...",
            "progress": 0
        }, event="progress")
        
        await asyncio.sleep(0.1)  # Allow event to flush
        
        # Step 2: Parsing skills
        yield format_sse({
            "status": "parsing_skills",
            "message": "Analyzing job description...",
            "progress": 10
        }, event="progress")
        
        skills = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: parse_job_description(request.job_description, use_llm=False)
        )
        
        skill_names = request.focus_skills or [s.skill for s in skills[:10]]
        
        yield format_sse({
            "status": "skills_extracted",
            "message": f"Found {len(skills)} relevant skills",
            "skills": skill_names[:5],
            "progress": 25
        }, event="progress")
        
        await asyncio.sleep(0.1)
        
        # Step 3: LLM skill enhancement (if enabled)
        yield format_sse({
            "status": "enhancing_skills",
            "message": "Enhancing skill analysis with AI...",
            "progress": 35
        }, event="progress")
        
        # Re-parse with LLM for better skills
        skills = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: parse_job_description(request.job_description, use_llm=True)
        )
        
        skill_names = request.focus_skills or [s.skill for s in skills[:10]]
        
        yield format_sse({
            "status": "skills_ready",
            "message": f"Identified {len(skill_names)} key skills to test",
            "skills": skill_names,
            "progress": 50
        }, event="progress")
        
        await asyncio.sleep(0.1)
        
        # Step 4: Generating questions
        yield format_sse({
            "status": "generating_questions",
            "message": f"Generating {request.num_questions} {request.interview_type.value} questions...",
            "progress": 60
        }, event="progress")
        
        # This is the slow part - LLM generation
        questions = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: generate_questions(request)
        )
        
        yield format_sse({
            "status": "questions_generated",
            "message": f"Generated {len(questions)} questions",
            "progress": 90
        }, event="progress")
        
        await asyncio.sleep(0.1)
        
        # Step 5: Complete
        yield format_sse({
            "status": "complete",
            "message": "Question generation complete!",
            "progress": 100,
            "questions": [q.model_dump() for q in questions],
            "skills_used": skill_names,
            "total_count": len(questions)
        }, event="complete")
        
    except Exception as e:
        logger.error(f"Question generation stream error: {e}")
        yield format_sse({
            "status": "error",
            "message": str(e),
            "progress": 0
        }, event="error")


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/parse-skills", response_model=SkillParseResponse)
async def parse_skills(input_data: JobDescriptionInput):
    """
    Parse a job description and extract structured skill tags.
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
    
    Note: This can take 10-60 seconds depending on hardware.
    For progress updates, use POST /generate-stream instead.
    """
    try:
        logger.info(f"Generating {request.num_questions} {request.interview_type.value} questions")
        
        skills = parse_job_description(request.job_description, use_llm=False)
        skills_used = request.focus_skills or [s.skill for s in skills[:10]]
        
        questions = generate_questions(request)
        
        return QuestionGenerationResponse(
            questions=questions,
            skills_used=skills_used,
            total_count=len(questions)
        )
        
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")


@router.post("/generate-stream")
async def generate_interview_questions_stream(request: QuestionRequest):
    """
    Generate interview questions with real-time progress updates via SSE.
    
    Returns a Server-Sent Events stream with progress updates:
    
    ```
    event: progress
    data: {"status": "parsing_skills", "message": "...", "progress": 10}
    
    event: progress
    data: {"status": "generating_questions", "message": "...", "progress": 60}
    
    event: complete
    data: {"status": "complete", "questions": [...], "progress": 100}
    ```
    
    Frontend usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/questions/generate-stream');
    // or with POST:
    fetch('/api/v1/questions/generate-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    }).then(response => {
        const reader = response.body.getReader();
        // Process SSE stream...
    });
    ```
    """
    return StreamingResponse(
        generate_questions_with_progress(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering if proxied
        }
    )


@router.post("/generate-single", response_model=GeneratedQuestion)
async def generate_single_question(request: SingleQuestionRequest):
    """Generate a single question for a specific skill."""
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
    """Generate questions that adapt based on previous performance."""
    try:
        questions = question_generator.generate_adaptive(
            job_description=request.job_description,
            previous_scores=request.previous_scores,
            target_categories=request.target_categories
        )
        
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
        "spacy_loaded": skill_parser.nlp is not None,
        "streaming_endpoint": "/api/v1/questions/generate-stream"
    }