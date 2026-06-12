"""
Assessment Service API Routes - Employer "Assessment Studio" (Phase 10).
Location: backend/services/assessment_service/routes.py

All endpoints are org-scoped: an employer only ever sees/edits assessments,
assignments, and templates belonging to their own organization. This enforces
the data-isolation requirement (question banks & results are private per org
and never reusable in the candidate mock portal).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_repository
from models.platform_schemas import (
    Assessment,
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentStatus,
    AssessmentTemplate,
    PublicUser,
    QuestionType,
    ScoringMode,
)
from models.schemas import DifficultyLevel, InterviewType, QuestionRequest
from services.auth_service.dependencies import get_employer_user

logger = logging.getLogger(__name__)

router = APIRouter()

ASSESSMENTS = "assessments"
ASSIGNMENTS = "assignments"
TEMPLATES = "assessment_templates"
USERS = "users"


# =============================================================================
# Request models
# =============================================================================

class CreateAssessmentRequest(BaseModel):
    title: str
    description: Optional[str] = None
    job_description: Optional[str] = None


class UpdateAssessmentRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AssessmentStatus] = None
    sections: Optional[List[AssessmentSection]] = None
    permissions: Optional[dict] = None
    setup_guides: Optional[list] = None
    job_description: Optional[str] = None


class GenerateFromJDRequest(BaseModel):
    job_description: str
    interview_type: InterviewType = InterviewType.TECHNICAL
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    num_questions: int = 5
    section_title: Optional[str] = None
    use_culture_grounding: bool = False  # Phase 12: ground in org culture


class AssignRequest(BaseModel):
    candidate_usernames: List[str]
    due_at: Optional[str] = None


class SaveTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None


# =============================================================================
# Helpers
# =============================================================================

async def _owned_assessment(assessment_id: str, user: PublicUser) -> dict:
    repo = get_repository()
    doc = await repo.get(ASSESSMENTS, assessment_id)
    if not doc or doc.get("org_id") != user.org_id:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return doc


_INTERVIEW_TO_QTYPE = {
    InterviewType.OA: QuestionType.CODING,
    InterviewType.TECHNICAL: QuestionType.VIDEO_ANSWER,
    InterviewType.SYSTEM_DESIGN: QuestionType.SYSTEM_DESIGN,
    InterviewType.BEHAVIORAL: QuestionType.VIDEO_ANSWER,
    InterviewType.MIXED: QuestionType.VIDEO_ANSWER,
}


def _to_assessment_question(gen, interview_type: InterviewType) -> AssessmentQuestion:
    """Map a generated interview question onto an assessment question."""
    qtype = _INTERVIEW_TO_QTYPE.get(interview_type, QuestionType.VIDEO_ANSWER)
    scoring = ScoringMode.AUTO if qtype == QuestionType.CODING else ScoringMode.AI
    return AssessmentQuestion(
        type=qtype,
        prompt=gen.question,
        starter_code=gen.starter_code,
        test_cases=[tc.model_dump() for tc in gen.test_cases] if gen.test_cases else None,
        expected_duration_mins=gen.expected_duration_mins or 5,
        scoring_mode=scoring,
        skill_tags=gen.skill_tags or [],
        evaluation_criteria=gen.evaluation_criteria or [],
    )


# =============================================================================
# Assessment CRUD
# =============================================================================

@router.post("", response_model=Assessment)
async def create_assessment(
    req: CreateAssessmentRequest, user: PublicUser = Depends(get_employer_user)
):
    repo = get_repository()
    assessment = Assessment(
        org_id=user.org_id,
        title=req.title,
        description=req.description,
        job_description=req.job_description,
        created_by=user.id,
    )
    await repo.insert(ASSESSMENTS, assessment.model_dump())
    return assessment


@router.get("", response_model=List[Assessment])
async def list_assessments(user: PublicUser = Depends(get_employer_user)):
    repo = get_repository()
    docs = await repo.find(
        ASSESSMENTS, where={"org_id": user.org_id}, order_by="created_at"
    )
    return [Assessment(**d) for d in docs]


@router.get("/{assessment_id}", response_model=Assessment)
async def get_assessment(
    assessment_id: str, user: PublicUser = Depends(get_employer_user)
):
    return Assessment(**await _owned_assessment(assessment_id, user))


@router.patch("/{assessment_id}", response_model=Assessment)
async def update_assessment(
    assessment_id: str,
    req: UpdateAssessmentRequest,
    user: PublicUser = Depends(get_employer_user),
):
    await _owned_assessment(assessment_id, user)
    updates = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    repo = get_repository()
    updated = await repo.update(ASSESSMENTS, assessment_id, updates)
    return Assessment(**updated)


@router.delete("/{assessment_id}")
async def delete_assessment(
    assessment_id: str, user: PublicUser = Depends(get_employer_user)
):
    await _owned_assessment(assessment_id, user)
    await get_repository().delete(ASSESSMENTS, assessment_id)
    return {"deleted": True, "id": assessment_id}


# =============================================================================
# JD-based question generation (reuses Phase 2 generator)
# =============================================================================

@router.post("/{assessment_id}/generate-from-jd", response_model=Assessment)
async def generate_from_jd(
    assessment_id: str,
    req: GenerateFromJDRequest,
    user: PublicUser = Depends(get_employer_user),
):
    """Auto-draft a section of questions from a JD and append it to the assessment."""
    doc = await _owned_assessment(assessment_id, user)

    from services.question_service.generator import generate_questions

    # Phase 12: optionally enrich the JD with company-culture context so the
    # generated questions align with the org's tone and principles.
    job_description = req.job_description
    if req.use_culture_grounding:
        try:
            from services.culture_service.crawler import CultureStore

            culture_chunks = CultureStore(user.org_id).query(
                req.job_description, k=3
            )
            if culture_chunks:
                context = "\n".join(culture_chunks)[:2000]
                job_description = (
                    f"{req.job_description}\n\n"
                    f"--- COMPANY CULTURE CONTEXT (align question tone/values with this) ---\n"
                    f"{context}"
                )
                logger.info("Grounded JD generation with %d culture chunks", len(culture_chunks))
        except Exception as e:  # noqa: BLE001
            logger.warning("Culture grounding skipped: %s", e)

    try:
        generated = generate_questions(
            QuestionRequest(
                job_description=job_description,
                interview_type=req.interview_type,
                difficulty=req.difficulty,
                num_questions=req.num_questions,
            )
        )
    except Exception as e:  # noqa: BLE001
        logger.error("JD generation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Question generation failed: {e}")

    section = AssessmentSection(
        title=req.section_title or f"{req.interview_type.value.title()} Questions",
        questions=[_to_assessment_question(g, req.interview_type) for g in generated],
    )

    sections = doc.get("sections", [])
    sections.append(section.model_dump())
    updated = await get_repository().update(
        ASSESSMENTS, assessment_id, {"sections": sections}
    )
    return Assessment(**updated)


# =============================================================================
# Assignment
# =============================================================================

@router.post("/{assessment_id}/assign", response_model=List[AssessmentAssignment])
async def assign_assessment(
    assessment_id: str,
    req: AssignRequest,
    user: PublicUser = Depends(get_employer_user),
):
    """Assign a published assessment to candidate usernames."""
    doc = await _owned_assessment(assessment_id, user)
    if doc.get("status") != AssessmentStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=400, detail="Assessment must be published before assigning"
        )

    repo = get_repository()
    created: List[AssessmentAssignment] = []
    for username in req.candidate_usernames:
        username = username.strip()
        if not username:
            continue
        # Resolve candidate user id if the username exists (optional).
        matches = await repo.find(USERS, where={"username": username})
        candidate_id = matches[0]["id"] if matches else None
        assignment = AssessmentAssignment(
            assessment_id=assessment_id,
            org_id=user.org_id,
            candidate_username=username,
            candidate_user_id=candidate_id,
            due_at=req.due_at,
        )
        await repo.insert(ASSIGNMENTS, assignment.model_dump())
        created.append(assignment)
    return created


@router.get("/{assessment_id}/assignments", response_model=List[AssessmentAssignment])
async def list_assignments(
    assessment_id: str, user: PublicUser = Depends(get_employer_user)
):
    await _owned_assessment(assessment_id, user)
    repo = get_repository()
    docs = await repo.find(
        ASSIGNMENTS,
        where={"assessment_id": assessment_id, "org_id": user.org_id},
        order_by="invited_at",
    )
    return [AssessmentAssignment(**d) for d in docs]


# =============================================================================
# Templates (Phase 13E - role-based reusable flows)
# =============================================================================

@router.post("/{assessment_id}/save-as-template", response_model=AssessmentTemplate)
async def save_as_template(
    assessment_id: str,
    req: SaveTemplateRequest,
    user: PublicUser = Depends(get_employer_user),
):
    doc = await _owned_assessment(assessment_id, user)
    template = AssessmentTemplate(
        org_id=user.org_id,
        name=req.name,
        description=req.description,
        sections=[AssessmentSection(**s) for s in doc.get("sections", [])],
        permissions=doc.get("permissions", {}),
    )
    await get_repository().insert(TEMPLATES, template.model_dump())
    return template


@router.get("/templates/list", response_model=List[AssessmentTemplate])
async def list_templates(user: PublicUser = Depends(get_employer_user)):
    repo = get_repository()
    docs = await repo.find(TEMPLATES, where={"org_id": user.org_id}, order_by="created_at")
    return [AssessmentTemplate(**d) for d in docs]


@router.post("/from-template/{template_id}", response_model=Assessment)
async def create_from_template(
    template_id: str, user: PublicUser = Depends(get_employer_user)
):
    repo = get_repository()
    tmpl = await repo.get(TEMPLATES, template_id)
    if not tmpl or tmpl.get("org_id") != user.org_id:
        raise HTTPException(status_code=404, detail="Template not found")
    assessment = Assessment(
        org_id=user.org_id,
        title=f"{tmpl['name']} (from template)",
        description=tmpl.get("description"),
        sections=[AssessmentSection(**s) for s in tmpl.get("sections", [])],
        permissions=tmpl.get("permissions", {}),
        template_id=template_id,
        created_by=user.id,
    )
    await repo.insert(ASSESSMENTS, assessment.model_dump())
    return assessment


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "assessment"}
