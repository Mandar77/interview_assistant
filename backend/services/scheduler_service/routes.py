"""
Live Interview Scheduler API Routes (Phase 13F).
Location: backend/services/scheduler_service/routes.py

Org-scoped scheduling of live interview slots with a mock meeting-link
generator (free — no Zoom/Teams API needed). Optionally emails the candidate.
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_repository
from models.platform_schemas import InterviewSlot, PublicUser
from services.auth_service.dependencies import get_employer_user
from services.comms_service.mailer import schedule_email, send_email

logger = logging.getLogger(__name__)

router = APIRouter()

SLOTS = "interview_slots"
USERS = "users"


class CreateSlotRequest(BaseModel):
    candidate_username: str
    start_time: str
    end_time: str
    interviewer: Optional[str] = None
    attempt_id: Optional[str] = None
    provider: str = "meet"  # meet | zoom | teams (all mock links)
    send_email: bool = False


def _mock_meeting_link(provider: str) -> str:
    token = uuid.uuid4().hex[:11]
    return {
        "zoom": f"https://zoom.us/j/{token}",
        "teams": f"https://teams.microsoft.com/l/meetup-join/{token}",
    }.get(provider, f"https://meet.google.com/{token[:3]}-{token[3:7]}-{token[7:11]}")


@router.post("/slots", response_model=InterviewSlot)
async def create_slot(
    req: CreateSlotRequest, user: PublicUser = Depends(get_employer_user)
):
    slot = InterviewSlot(
        org_id=user.org_id,
        candidate_username=req.candidate_username,
        interviewer=req.interviewer or user.username,
        attempt_id=req.attempt_id,
        start_time=req.start_time,
        end_time=req.end_time,
        meeting_link=_mock_meeting_link(req.provider),
    )
    await get_repository().insert(SLOTS, slot.model_dump())

    if req.send_email:
        repo = get_repository()
        matches = await repo.find(USERS, where={"username": req.candidate_username})
        if matches and matches[0].get("email"):
            subject, body = schedule_email(
                req.candidate_username, req.start_time, slot.meeting_link
            )
            send_email(matches[0]["email"], subject, body)
    return slot


@router.get("/slots", response_model=List[InterviewSlot])
async def list_slots(user: PublicUser = Depends(get_employer_user)):
    docs = await get_repository().find(
        SLOTS, where={"org_id": user.org_id}, order_by="start_time", descending=False
    )
    return [InterviewSlot(**d) for d in docs]


@router.delete("/slots/{slot_id}")
async def cancel_slot(slot_id: str, user: PublicUser = Depends(get_employer_user)):
    repo = get_repository()
    slot = await repo.get(SLOTS, slot_id)
    if not slot or slot.get("org_id") != user.org_id:
        raise HTTPException(status_code=404, detail="Slot not found")
    await repo.update(SLOTS, slot_id, {"status": "cancelled"})
    return {"cancelled": True, "id": slot_id}


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "scheduler"}
