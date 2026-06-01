"""
Recruiter Decision Panel + Comms API Routes (Phase 13C, 13D).
Location: backend/services/comms_service/routes.py

Employer-facing: review candidate attempts (scores + proctoring flags), record
a verdict, and optionally fire an automated email (advance / reject / schedule).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from db import get_repository
from models.platform_schemas import (
    DecisionRequest,
    PublicUser,
    RecruiterVerdict,
)
from services.auth_service.dependencies import get_employer_user
from services.comms_service.mailer import (
    invite_email,
    result_email,
    send_email,
)

logger = logging.getLogger(__name__)

router = APIRouter()

ATTEMPTS = "attempts"
ASSESSMENTS = "assessments"
ASSIGNMENTS = "assignments"
EVENTS = "proctoring_events"
DECISIONS = "decisions"
USERS = "users"


class SendInviteRequest(BaseModel):
    candidate_email: EmailStr
    candidate_name: str
    assessment_id: str
    assignment_id: Optional[str] = None


# =============================================================================
# Recruiter Decision Panel
# =============================================================================

@router.get("/candidates")
async def list_candidates(
    assessment_id: Optional[str] = None,
    user: PublicUser = Depends(get_employer_user),
):
    """List submitted attempts for the org (optionally filtered by assessment),
    each with score summary + proctoring flags for the decision panel."""
    repo = get_repository()
    where = {"org_id": user.org_id}
    if assessment_id:
        where["assessment_id"] = assessment_id
    attempts = await repo.find(ATTEMPTS, where=where, order_by="submitted_at")

    panel = []
    for att in attempts:
        decision = await repo.get(DECISIONS, att["id"])
        panel.append(
            {
                "attempt_id": att["id"],
                "assessment_id": att["assessment_id"],
                "candidate_username": att.get("candidate_username"),
                "status": att.get("status"),
                "overall_score": att.get("overall_score"),
                "proctoring_summary": att.get("proctoring_summary", {}),
                "submitted_at": att.get("submitted_at"),
                "verdict": (decision or {}).get("verdict", RecruiterVerdict.PENDING.value),
            }
        )
    return panel


@router.get("/candidates/{attempt_id}")
async def candidate_detail(
    attempt_id: str, user: PublicUser = Depends(get_employer_user)
):
    """Full per-question scoring + proctoring event timeline for one candidate."""
    repo = get_repository()
    att = await repo.get(ATTEMPTS, attempt_id)
    if not att or att.get("org_id") != user.org_id:
        raise HTTPException(status_code=404, detail="Attempt not found")
    events = await repo.find(EVENTS, where={"attempt_id": attempt_id}, order_by="at", descending=False)
    assessment = await repo.get(ASSESSMENTS, att["assessment_id"])
    decision = await repo.get(DECISIONS, attempt_id)
    return {
        "attempt": att,
        "events": events,
        "assessment_title": assessment.get("title") if assessment else None,
        "decision": decision,
    }


@router.post("/decision")
async def record_decision(
    req: DecisionRequest, user: PublicUser = Depends(get_employer_user)
):
    """Record a recruiter verdict; optionally email the candidate."""
    repo = get_repository()
    att = await repo.get(ATTEMPTS, req.attempt_id)
    if not att or att.get("org_id") != user.org_id:
        raise HTTPException(status_code=404, detail="Attempt not found")

    decision = {
        "id": req.attempt_id,  # one decision per attempt
        "attempt_id": req.attempt_id,
        "org_id": user.org_id,
        "verdict": req.verdict.value,
        "note": req.note,
        "decided_by": user.id,
    }
    await repo.insert(DECISIONS, decision)

    email_result = None
    if req.send_email:
        assessment = await repo.get(ASSESSMENTS, att["assessment_id"])
        title = assessment.get("title", "Assessment") if assessment else "Assessment"
        candidate_name = att.get("candidate_username", "Candidate")
        # Resolve candidate email if we have a user record.
        email = None
        if att.get("candidate_user_id"):
            cu = await repo.get(USERS, att["candidate_user_id"])
            email = cu.get("email") if cu else None
        if email and req.verdict in (RecruiterVerdict.ADVANCE, RecruiterVerdict.REJECT):
            subject, body = result_email(
                candidate_name, title, advanced=req.verdict == RecruiterVerdict.ADVANCE
            )
            email_result = send_email(email, subject, body)
        else:
            email_result = {"status": "skipped", "reason": "no email or verdict not emailable"}

    return {"decision": decision, "email": email_result}


# =============================================================================
# Automated Communication
# =============================================================================

@router.post("/send-invite")
async def send_invite(
    req: SendInviteRequest, user: PublicUser = Depends(get_employer_user)
):
    """Email an assessment invite + link to a candidate."""
    from config.settings import settings

    repo = get_repository()
    assessment = await repo.get(ASSESSMENTS, req.assessment_id)
    if not assessment or assessment.get("org_id") != user.org_id:
        raise HTTPException(status_code=404, detail="Assessment not found")

    link = f"{settings.app_base_url}/workspace"
    if req.assignment_id:
        link = f"{settings.app_base_url}/workspace?assignment={req.assignment_id}"
    subject, body = invite_email(req.candidate_name, assessment.get("title", "Assessment"), link)
    result = send_email(req.candidate_email, subject, body)
    return {"email": result, "link": link}


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "comms"}
