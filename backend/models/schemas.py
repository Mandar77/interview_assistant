"""
Pydantic Schemas - Data Models for Interview Assistant
Defines request/response models for all API endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime
import uuid

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

class TestCase(BaseModel):
    """Test case for OA questions."""
    input: str = Field(..., description="Input for the test case")
    expected_output: str = Field(..., description="Expected output")
    description: Optional[str] = Field(None, description="Test case description")
    is_hidden: bool = Field(False, description="Whether this is a hidden test case for evaluation")


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
    # ✅ NEW: Add test cases for OA questions
    test_cases: Optional[List[TestCase]] = None
    starter_code: Optional[Dict[str, str]] = None  # Language -> code template

# =============================================================================
# Screen Capture & Vision Schemas
# =============================================================================

class ScreenshotMetadata(BaseModel):
    """Metadata for a captured screenshot."""
    screenshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    question_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    capture_method: str = "auto"  # auto, manual, interval
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None


class DiagramAnalysisResult(BaseModel):
    """Result from Vision-LLM diagram analysis."""
    screenshot_id: str
    analysis_type: str  # system_design, flowchart, architecture, erd
    components_identified: List[str]
    relationships_detected: List[str]
    completeness_score: float = Field(..., ge=0, le=5)
    clarity_score: float = Field(..., ge=0, le=5)
    scalability_assessment: str
    missing_elements: List[str]
    strengths: List[str]
    weaknesses: List[str]
    overall_score: float = Field(..., ge=0, le=5)
    detailed_feedback: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class ScreenCaptureRequest(BaseModel):
    """Request to analyze a screenshot."""
    session_id: str
    question_id: str
    question_text: str
    interview_type: str = "system_design"
    image_base64: str  # Base64 encoded image
    capture_method: str = "manual"
    transcript: Optional[str] = None  # What user said while drawing

# =============================================================================
# Speech Service Schemas
# =============================================================================

class TranscriptionResult(BaseModel):
    """Result from speech transcription."""
    text: str
    duration_seconds: float
    language: str = "en"
    confidence: float = Field(..., ge=0, le=1)
    word_count: int = 0
    segments: Optional[List[dict]] = None  # Word-level timestamps


class SpeechMetrics(BaseModel):
    """Analyzed speech metrics."""
    words_per_minute: float
    total_words: int
    total_duration_seconds: float
    filler_word_count: int
    filler_word_percentage: float
    filler_words_found: List[str]
    pause_count: int
    avg_pause_duration_ms: float
    longest_pause_ms: float
    speaking_rate_category: str  # slow, normal, fast


class LanguageMetrics(BaseModel):
    """Language quality metrics."""
    grammar_errors: List[dict]  # {error, suggestion, position}
    grammar_score: float = Field(..., ge=0, le=5)
    vocabulary_level: str  # basic, intermediate, advanced
    unique_word_ratio: float
    avg_sentence_length: float
    readability_flesch: float
    readability_flesch_grade: float
    readability_gunning_fog: float
    clarity_score: float = Field(..., ge=0, le=5)
    conciseness_score: float = Field(..., ge=0, le=5)


# =============================================================================
# Evaluation Service Schemas
# =============================================================================

class RubricScore(BaseModel):
    """Score for a single rubric category."""
    category: str
    category_name: str
    score: float = Field(..., ge=0, le=5)
    weight: float = Field(..., ge=0, le=1)
    feedback: str
    evidence: List[str] = []


class EvaluationRequest(BaseModel):
    """Request to evaluate an interview response."""
    session_id: str
    question_id: str
    question: GeneratedQuestion
    transcript: str
    speech_metrics: Optional[SpeechMetrics] = None
    language_metrics: Optional[LanguageMetrics] = None
    body_language_metrics: Optional[dict] = None
    timing_metrics: Optional[dict] = None


class EvaluationResult(BaseModel):
    """Complete evaluation result."""
    session_id: str
    question_id: str
    rubric_scores: List[RubricScore]
    overall_score: float = Field(..., ge=0, le=5)
    weighted_score: float = Field(..., ge=0, le=5)
    strengths: List[str]
    weaknesses: List[str]
    hallucination_flags: List[dict] = []
    confidence_index: float = Field(..., ge=0, le=1)
    pass_threshold: bool
    excellence_threshold: bool
    evaluated_at: datetime


# =============================================================================
# Feedback Service Schemas
# =============================================================================

class FeedbackRequest(BaseModel):
    """Request to generate feedback."""
    session_id: str
    evaluation_result: dict
    question_text: str
    answer_text: str
    interview_type: str = "technical"
    verbosity: str = "detailed"  # brief, detailed, comprehensive


class ImprovementTip(BaseModel):
    """A specific improvement tip."""
    area: str
    tip: str
    example: Optional[str] = None
    resources: List[str] = []


class FeedbackResponse(BaseModel):
    """Generated feedback for the candidate."""
    session_id: str
    summary: str
    overall_performance: str
    detailed_feedback: List[dict]
    improvement_tips: List[ImprovementTip]
    strengths_highlight: List[str]
    priority_areas: List[str]
    recommended_topics: List[str]
    next_steps: List[str]
    encouragement: str
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