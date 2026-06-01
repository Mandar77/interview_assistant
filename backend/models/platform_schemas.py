"""
Platform Schemas - data models for the two-sided hiring platform (Phase 9+).
Location: backend/models/platform_schemas.py

These cover accounts/tenancy (Phase 9), assessments (Phase 10), candidate
attempts + proctoring (Phase 11), culture grounding (Phase 12), and the
recruiting-workflow modules (Phase 13). They are kept separate from the
original ``schemas.py`` so the existing mock-interview flow is untouched.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat()


# =============================================================================
# Phase 9 - Accounts & Tenancy
# =============================================================================

class UserRole(str, Enum):
    CANDIDATE = "candidate"
    EMPLOYER_ADMIN = "employer_admin"
    EMPLOYER_MEMBER = "employer_member"


class Organization(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
    slug: str
    website: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str = Field(default_factory=_now)


class User(BaseModel):
    id: str = Field(default_factory=_uuid)
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.CANDIDATE
    org_id: Optional[str] = None  # set for employer users
    password_hash: str = ""
    created_at: str = Field(default_factory=_now)


class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: UserRole = UserRole.CANDIDATE
    organization_name: Optional[str] = None  # required for employer_admin signup


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "PublicUser"


class PublicUser(BaseModel):
    """User shape safe to return to clients (no password hash)."""
    id: str
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    role: UserRole
    org_id: Optional[str] = None


# =============================================================================
# Phase 10 - Assessments (Employer "Assessment Studio")
# =============================================================================

class QuestionType(str, Enum):
    MCQ = "mcq"
    CODING = "coding"
    VIDEO_ANSWER = "video_answer"
    SYSTEM_DESIGN = "system_design"
    FILE_UPLOAD = "file_upload"
    LIVE_INTERVIEW = "live_interview"


class ScoringMode(str, Enum):
    AUTO = "auto"        # MCQ / coding — deterministic
    AI = "ai"            # spoken answers, body language, design
    MANUAL = "manual"    # recruiter scores by hand


class AssessmentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AssessmentPermissions(BaseModel):
    require_mic: bool = False
    require_camera: bool = False
    require_screen_share: bool = False
    force_fullscreen: bool = False
    block_tab_switch: bool = False
    block_copy_paste: bool = False
    watermark: bool = True


class MCQOption(BaseModel):
    id: str = Field(default_factory=_uuid)
    text: str
    is_correct: bool = False


class AssessmentQuestion(BaseModel):
    id: str = Field(default_factory=_uuid)
    type: QuestionType
    prompt: str
    # type-specific payloads (all optional)
    options: Optional[List[MCQOption]] = None          # mcq
    starter_code: Optional[Dict[str, str]] = None      # coding
    test_cases: Optional[List[dict]] = None            # coding
    expected_duration_mins: int = 5
    scoring_mode: ScoringMode = ScoringMode.AI
    max_score: float = 5.0
    skill_tags: List[str] = Field(default_factory=list)
    evaluation_criteria: List[str] = Field(default_factory=list)


class AssessmentSection(BaseModel):
    id: str = Field(default_factory=_uuid)
    title: str
    questions: List[AssessmentQuestion] = Field(default_factory=list)


class SetupGuide(BaseModel):
    kind: str = "text"  # text | youtube
    content: str = ""   # rich text or unlisted YouTube URL


class Assessment(BaseModel):
    id: str = Field(default_factory=_uuid)
    org_id: str
    title: str
    description: Optional[str] = None
    status: AssessmentStatus = AssessmentStatus.DRAFT
    sections: List[AssessmentSection] = Field(default_factory=list)
    permissions: AssessmentPermissions = Field(default_factory=AssessmentPermissions)
    setup_guides: List[SetupGuide] = Field(default_factory=list)
    job_description: Optional[str] = None
    template_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str = Field(default_factory=_now)


class AssessmentAssignment(BaseModel):
    id: str = Field(default_factory=_uuid)
    assessment_id: str
    org_id: str
    candidate_username: str
    candidate_user_id: Optional[str] = None
    status: str = "invited"  # invited | started | submitted | evaluated
    invited_at: str = Field(default_factory=_now)
    due_at: Optional[str] = None


class AssessmentTemplate(BaseModel):
    """Phase 13E - reusable assessment flow (presets)."""
    id: str = Field(default_factory=_uuid)
    org_id: str
    name: str
    description: Optional[str] = None
    sections: List[AssessmentSection] = Field(default_factory=list)
    permissions: AssessmentPermissions = Field(default_factory=AssessmentPermissions)
    created_at: str = Field(default_factory=_now)


# =============================================================================
# Phase 11 - Candidate Attempts & Proctoring
# =============================================================================

class ProctoringEventType(str, Enum):
    TAB_SWITCH = "tab_switch"
    FULLSCREEN_EXIT = "fullscreen_exit"
    FACE_LOST = "face_lost"
    MULTI_FACE = "multi_face_detected"
    MIC_MUTED = "mic_muted"
    PERMISSION_REVOKED = "permission_revoked"
    COPY_BLOCKED = "copy_blocked"
    PASTE_BLOCKED = "paste_blocked"


class ProctoringEvent(BaseModel):
    id: str = Field(default_factory=_uuid)
    attempt_id: str
    type: ProctoringEventType
    detail: Optional[str] = None
    at: str = Field(default_factory=_now)


class AnswerSubmission(BaseModel):
    question_id: str
    type: QuestionType
    # one of these is populated depending on type
    selected_option_ids: Optional[List[str]] = None
    code: Optional[str] = None
    language: Optional[str] = None
    transcript: Optional[str] = None
    file_ref: Optional[str] = None
    speech_metrics: Optional[dict] = None
    body_language_metrics: Optional[dict] = None


class AssessmentAttempt(BaseModel):
    id: str = Field(default_factory=_uuid)
    assignment_id: str
    assessment_id: str
    org_id: str
    candidate_user_id: Optional[str] = None
    candidate_username: str
    status: str = "started"  # started | submitted | evaluated
    answers: List[AnswerSubmission] = Field(default_factory=list)
    proctoring_summary: Dict[str, int] = Field(default_factory=dict)
    overall_score: Optional[float] = None
    started_at: str = Field(default_factory=_now)
    submitted_at: Optional[str] = None


class StartAttemptRequest(BaseModel):
    assignment_id: str


class SubmitAttemptRequest(BaseModel):
    attempt_id: str
    answers: List[AnswerSubmission]


# =============================================================================
# Phase 13 - Recruiting Workflow
# =============================================================================

class RecruiterVerdict(str, Enum):
    ADVANCE = "advance"
    SCHEDULE_LIVE = "schedule_live"
    REJECT = "reject"
    PENDING = "pending"


class DecisionRequest(BaseModel):
    attempt_id: str
    verdict: RecruiterVerdict
    note: Optional[str] = None
    send_email: bool = False


class ATSWebhookPayload(BaseModel):
    """Phase 13A - mock ATS candidate intake."""
    source: str = "greenhouse"  # greenhouse | workday | bamboohr
    candidate_email: EmailStr
    candidate_name: str
    candidate_username: Optional[str] = None
    job_title: Optional[str] = None
    assessment_id: str
    org_id: str


class InterviewSlot(BaseModel):
    """Phase 13F - live interview scheduler."""
    id: str = Field(default_factory=_uuid)
    org_id: str
    attempt_id: Optional[str] = None
    candidate_username: str
    interviewer: Optional[str] = None
    start_time: str
    end_time: str
    meeting_link: Optional[str] = None
    status: str = "scheduled"  # scheduled | completed | cancelled
    created_at: str = Field(default_factory=_now)


# Resolve forward reference (TokenResponse -> PublicUser)
TokenResponse.model_rebuild()
