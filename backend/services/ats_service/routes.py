"""
ATS Integration Simulator API Routes (Phase 13A).
Location: backend/services/ats_service/routes.py

A mock Greenhouse/Workday/BambooHR webhook receiver. Accepts a candidate-profile
JSON payload and auto-triggers an assessment assignment, demonstrating
ATS-readiness without a real integration. The webhook is intentionally
unauthenticated (like a real provider webhook) but validates that the target
assessment exists and is published.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from db import get_repository
from models.platform_schemas import (
    AssessmentAssignment,
    AssessmentStatus,
    ATSWebhookPayload,
)
from services.comms_service.mailer import invite_email, send_email

logger = logging.getLogger(__name__)

router = APIRouter()

ASSESSMENTS = "assessments"
ASSIGNMENTS = "assignments"
USERS = "users"


@router.post("/webhook")
async def ats_webhook(payload: ATSWebhookPayload):
    """Receive a candidate from a (mock) ATS and auto-assign the assessment."""
    repo = get_repository()
    assessment = await repo.get(ASSESSMENTS, payload.assessment_id)
    if not assessment or assessment.get("org_id") != payload.org_id:
        raise HTTPException(status_code=404, detail="Assessment not found for org")
    if assessment.get("status") != AssessmentStatus.PUBLISHED.value:
        raise HTTPException(status_code=400, detail="Assessment is not published")

    username = payload.candidate_username or payload.candidate_email.split("@")[0]
    matches = await repo.find(USERS, where={"username": username})
    candidate_id = matches[0]["id"] if matches else None

    assignment = AssessmentAssignment(
        assessment_id=payload.assessment_id,
        org_id=payload.org_id,
        candidate_username=username,
        candidate_user_id=candidate_id,
    )
    await repo.insert(ASSIGNMENTS, assignment.model_dump())

    # Fire-and-record an invite email (logged if SMTP unset).
    from config.settings import settings

    link = f"{settings.app_base_url}/workspace?assignment={assignment.id}"
    subject, body = invite_email(
        payload.candidate_name, assessment.get("title", "Assessment"), link
    )
    email = send_email(payload.candidate_email, subject, body)

    logger.info(
        "ATS intake from %s: assigned %s to %s",
        payload.source,
        payload.assessment_id,
        username,
    )
    return {
        "received_from": payload.source,
        "assignment_id": assignment.id,
        "candidate_username": username,
        "invite_email": email,
    }


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "ats"}
