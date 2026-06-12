"""
Proctoring & Attempt API Routes - Candidate "Interview Workspace" (Phase 11).
Location: backend/services/proctoring_service/routes.py

Candidate-facing: launch an assigned assessment, log proctoring violations,
submit answers (auto + AI scored). Employer-facing reads live in the recruiter
panel (Phase 13C) but attempt scoring happens here so the candidate flow owns
its lifecycle.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_repository
from models.platform_schemas import (
    AnswerSubmission,
    AssessmentAttempt,
    ProctoringEvent,
    ProctoringEventType,
    PublicUser,
)
from services.auth_service.dependencies import get_current_user
from services.proctoring_service.scorer import score_attempt

logger = logging.getLogger(__name__)

router = APIRouter()

ASSESSMENTS = "assessments"
ASSIGNMENTS = "assignments"
ATTEMPTS = "attempts"
EVENTS = "proctoring_events"


# =============================================================================
# Request models
# =============================================================================

class StartAttemptRequest(BaseModel):
    assignment_id: str


class LogEventRequest(BaseModel):
    attempt_id: str
    type: ProctoringEventType
    detail: Optional[str] = None


class SubmitAttemptRequest(BaseModel):
    attempt_id: str
    answers: List[AnswerSubmission]


# =============================================================================
# Helpers
# =============================================================================

async def _owned_attempt(attempt_id: str, user: PublicUser) -> dict:
    repo = get_repository()
    attempt = await repo.get(ATTEMPTS, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    # Candidate owns their attempt; employer of the org may also read it.
    if user.role == "candidate" and attempt.get("candidate_user_id") not in (user.id, None):
        if attempt.get("candidate_username") != user.username:
            raise HTTPException(status_code=403, detail="Not your attempt")
    elif user.role in ("employer_admin", "employer_member") and attempt.get("org_id") != user.org_id:
        raise HTTPException(status_code=403, detail="Not your organization's attempt")
    return attempt


def _candidate_safe_assessment(assessment: dict) -> dict:
    """Strip answer keys (correct MCQ options, hidden test outputs) for candidates."""
    sections = []
    for section in assessment.get("sections", []):
        questions = []
        for q in section.get("questions", []):
            safe = dict(q)
            if safe.get("options"):
                safe["options"] = [
                    {"id": o["id"], "text": o["text"]} for o in safe["options"]
                ]
            if safe.get("test_cases"):
                safe["test_cases"] = [
                    tc for tc in safe["test_cases"] if not tc.get("is_hidden")
                ]
            questions.append(safe)
        sections.append({**section, "questions": questions})
    return {
        "id": assessment["id"],
        "title": assessment.get("title"),
        "description": assessment.get("description"),
        "sections": sections,
        "permissions": assessment.get("permissions", {}),
        "setup_guides": assessment.get("setup_guides", []),
    }


# =============================================================================
# Candidate endpoints
# =============================================================================

@router.get("/my-assignments")
async def my_assignments(user: PublicUser = Depends(get_current_user)):
    """List assessments assigned to the current candidate (by username or id)."""
    repo = get_repository()
    by_username = await repo.find(ASSIGNMENTS, where={"candidate_username": user.username})
    by_id = await repo.find(ASSIGNMENTS, where={"candidate_user_id": user.id})
    seen = {}
    for a in by_username + by_id:
        seen[a["id"]] = a
    out = []
    for assignment in seen.values():
        assessment = await repo.get(ASSESSMENTS, assignment["assessment_id"])
        out.append(
            {
                "assignment": assignment,
                "assessment_title": assessment.get("title") if assessment else None,
            }
        )
    return out


@router.post("/attempts/start", response_model=dict)
async def start_attempt(
    req: StartAttemptRequest, user: PublicUser = Depends(get_current_user)
):
    """Begin an attempt for an assigned assessment; returns a candidate-safe view."""
    repo = get_repository()
    assignment = await repo.get(ASSIGNMENTS, req.assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Verify the assignment is for this candidate.
    if assignment.get("candidate_username") != user.username and assignment.get(
        "candidate_user_id"
    ) not in (user.id, None):
        raise HTTPException(status_code=403, detail="Assignment not for this candidate")

    assessment = await repo.get(ASSESSMENTS, assignment["assessment_id"])
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    attempt = AssessmentAttempt(
        assignment_id=assignment["id"],
        assessment_id=assessment["id"],
        org_id=assignment["org_id"],
        candidate_user_id=user.id,
        candidate_username=user.username,
    )
    await repo.insert(ATTEMPTS, attempt.model_dump())
    await repo.update(ASSIGNMENTS, assignment["id"], {"status": "started"})

    return {
        "attempt_id": attempt.id,
        "assessment": _candidate_safe_assessment(assessment),
    }


@router.post("/events", response_model=ProctoringEvent)
async def log_event(req: LogEventRequest, user: PublicUser = Depends(get_current_user)):
    """Append-only proctoring event log for an attempt."""
    await _owned_attempt(req.attempt_id, user)
    event = ProctoringEvent(attempt_id=req.attempt_id, type=req.type, detail=req.detail)
    await get_repository().insert(EVENTS, event.model_dump())
    return event


@router.post("/attempts/submit", response_model=dict)
async def submit_attempt(
    req: SubmitAttemptRequest, user: PublicUser = Depends(get_current_user)
):
    """Submit answers, auto/AI-score them, and persist results."""
    repo = get_repository()
    attempt = await _owned_attempt(req.attempt_id, user)
    if attempt.get("status") == "submitted":
        raise HTTPException(status_code=409, detail="Attempt already submitted")

    assessment = await repo.get(ASSESSMENTS, attempt["assessment_id"])
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    answers = [a.model_dump() for a in req.answers]
    # carry attempt id into each answer for AI scoring traceability
    for a in answers:
        a["attempt_id"] = req.attempt_id

    scoring = score_attempt(assessment, answers)

    # Aggregate proctoring events into a summary.
    events = await repo.find(EVENTS, where={"attempt_id": req.attempt_id})
    summary: dict = {}
    for ev in events:
        summary[ev["type"]] = summary.get(ev["type"], 0) + 1

    from datetime import datetime

    updated = await repo.update(
        ATTEMPTS,
        req.attempt_id,
        {
            "status": "submitted",
            "answers": answers,
            "overall_score": scoring["overall_score"],
            "scoring": scoring,
            "proctoring_summary": summary,
            "submitted_at": datetime.utcnow().isoformat(),
        },
    )
    await repo.update(ASSIGNMENTS, attempt["assignment_id"], {"status": "submitted"})

    # Candidate sees their own overall score; full per-question detail is for employer.
    return {
        "attempt_id": req.attempt_id,
        "overall_score": scoring["overall_score"],
        "submitted_at": updated.get("submitted_at"),
    }


@router.get("/attempts/{attempt_id}", response_model=dict)
async def get_attempt(attempt_id: str, user: PublicUser = Depends(get_current_user)):
    """Full attempt detail. Employers see scoring + proctoring; candidates see their own."""
    attempt = await _owned_attempt(attempt_id, user)
    events = await get_repository().find(EVENTS, where={"attempt_id": attempt_id}, order_by="at", descending=False)
    return {"attempt": attempt, "events": events}


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "proctoring"}
