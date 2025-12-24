"""
Pydantic Schemas - Data Models for Interview Assistant
Defines request/response models for all API endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# =============================================================================
# Enums
# =============================================================================

class InterviewType(str, Enum):
    OA = "oa"                      # Online Assessment (coding)
    TECHNICAL = "technical"        # Technical interview
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"
    MIXED = "mixed"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADAPTIVE = "adaptive"


class SkillCategory(str, Enum):
    PROGRAMMING = "programming"
    DATA_STRUCTURES = "data_structures"
    ALGORITHMS = "algorithms"
    SYSTEM_DESIGN = "system_design"
    DATABASE = "database"
    CLOUD = "cloud"
    SOFT_SKILLS = "soft_skills"


# =============================================================================
# Question Service Schemas
# =============================================================================

class JobDescriptionInput(BaseModel):
    """Input for parsing a job description."""
    job_description: str = Field(..., min_length=50, description="Full job description text")
    company_name: Optional[str] = None
    role_title: Optional[str] = None


class SkillTag(BaseModel):
    """Extracted skill from job description."""
    skill: str
    category: SkillCategory
    importance: float = Field(..., ge=0, le=1, description="Importance score 0-1")
    keywords: List[str] = []


class QuestionRequest(BaseModel):
    """Request to generate interview questions."""
    job_description: str
    interview_type: InterviewType
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    num_questions: int = Field(default=5, ge=1, le=20)
    focus_skills: Optional[List[str]] = None


class GeneratedQuestion(BaseModel):
    """A generated interview question."""
    id: str
    question: str
    interview_type: InterviewType
    difficulty: DifficultyLevel
    skill_tags: List[str]
    expected_duration_mins: int
    evaluation_criteria: List[str]
    sample_answer_points: Optional[List[str]] = None


# =============================================================================
# Speech Service Schemas
# =============================================================================

class TranscriptionResult(BaseModel):
    """Result from speech transcription."""
    text: str
    duration_seconds: float
    language: str = "en"
    confidence: float = Field(..., ge=0, le=1)
    segments: Optional[List[dict]] = None  # Word-level timestamps


class SpeechMetrics(BaseModel):
    """Analyzed speech metrics."""
    words_per_minute: float
    total_words: int
    filler_word_count: int
    filler_word_percentage: float
    filler_words_found: List[str]
    pause_count: int
    avg_pause_duration_ms: float
    longest_pause_ms: float


class LanguageMetrics(BaseModel):
    """Language quality metrics."""
    grammar_errors: List[dict]  # {error, suggestion, position}
    grammar_score: float = Field(..., ge=0, le=5)
    vocabulary_level: str  # basic, intermediate, advanced
    readability_flesch: float
    readability_gunning_fog: float
    clarity_score: float = Field(..., ge=0, le=5)
    conciseness_score: float = Field(..., ge=0, le=5)


# =============================================================================
# Evaluation Service Schemas
# =============================================================================

class RubricScore(BaseModel):
    """Score for a single rubric category."""
    category: str
    score: float = Field(..., ge=0, le=5)
    feedback: str
    evidence: List[str] = []  # Supporting evidence from response


class EvaluationRequest(BaseModel):
    """Request to evaluate an interview response."""
    question: GeneratedQuestion
    transcript: str
    speech_metrics: Optional[SpeechMetrics] = None
    language_metrics: Optional[LanguageMetrics] = None
    body_language_metrics: Optional[dict] = None  # From collaborator's service


class EvaluationResult(BaseModel):
    """Complete evaluation result."""
    session_id: str
    question_id: str
    rubric_scores: List[RubricScore]
    overall_score: float = Field(..., ge=0, le=5)
    strengths: List[str]
    weaknesses: List[str]
    hallucination_flags: List[dict] = []  # Flagged claims
    confidence_index: float = Field(..., ge=0, le=1)
    evaluated_at: datetime


# =============================================================================
# Feedback Service Schemas
# =============================================================================

class FeedbackRequest(BaseModel):
    """Request to generate feedback."""
    evaluation: EvaluationResult
    include_improvement_tips: bool = True
    verbosity: str = "detailed"  # brief, detailed, comprehensive


class FeedbackResponse(BaseModel):
    """Generated feedback for the candidate."""
    session_id: str
    summary: str
    detailed_feedback: str
    improvement_tips: List[str]
    recommended_topics: List[str]  # Topics to study
    next_steps: List[str]
    generated_at: datetime


# =============================================================================
# Session Schemas
# =============================================================================

class InterviewSession(BaseModel):
    """Complete interview session data."""
    id: str
    user_id: Optional[str] = None
    job_description: str
    interview_type: InterviewType
    questions: List[GeneratedQuestion]
    status: str = "created"  # created, in_progress, completed, evaluated
    created_at: datetime
    completed_at: Optional[datetime] = None


class SessionArtifact(BaseModel):
    """Stored artifact from a session."""
    session_id: str
    artifact_type: str  # audio, transcript, screenshot, evaluation
    s3_key: str
    created_at: datetime