"""
Mailer - send candidate communications via SMTP, log-only when unconfigured.
Location: backend/services/comms_service/mailer.py

Uses plain SMTP (Gmail SMTP / SES sandbox, both free). If SMTP settings are
not provided, emails are logged and recorded as "logged" rather than sent, so
the recruiting workflow works end-to-end in dev without credentials.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> dict:
    """Send (or log) an email. Returns a delivery record."""
    sender = settings.smtp_from or settings.smtp_user or "no-reply@interview-assistant.local"

    if not settings.smtp_host or not settings.smtp_user:
        logger.info("[EMAIL:LOGGED] to=%s subject=%s\n%s", to, subject, body)
        return {"status": "logged", "to": to, "subject": subject}

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password or "")
            server.sendmail(sender, [to], msg.as_string())
        logger.info("[EMAIL:SENT] to=%s subject=%s", to, subject)
        return {"status": "sent", "to": to, "subject": subject}
    except Exception as e:  # noqa: BLE001
        logger.error("Email send failed to %s: %s", to, e)
        return {"status": "error", "to": to, "subject": subject, "error": str(e)}


# --- Templated messages -----------------------------------------------------

def invite_email(candidate_name: str, assessment_title: str, link: str) -> tuple[str, str]:
    subject = f"You've been invited to an assessment: {assessment_title}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"You've been invited to complete the assessment \"{assessment_title}\".\n\n"
        f"Start here: {link}\n\n"
        f"Good luck!\n"
    )
    return subject, body


def result_email(candidate_name: str, assessment_title: str, advanced: bool) -> tuple[str, str]:
    subject = f"Update on your assessment: {assessment_title}"
    if advanced:
        body = (
            f"Hi {candidate_name},\n\n"
            f"Great news — based on your \"{assessment_title}\" assessment, "
            f"we'd like to move you to the next round. We'll be in touch with next steps.\n\n"
            f"Best regards,\nThe Hiring Team\n"
        )
    else:
        body = (
            f"Hi {candidate_name},\n\n"
            f"Thank you for completing the \"{assessment_title}\" assessment and for your "
            f"interest. After careful review, we won't be moving forward at this time. "
            f"We genuinely appreciate your effort and wish you the best.\n\n"
            f"Best regards,\nThe Hiring Team\n"
        )
    return subject, body


def schedule_email(candidate_name: str, start_time: str, link: Optional[str]) -> tuple[str, str]:
    subject = "Your live interview is scheduled"
    body = (
        f"Hi {candidate_name},\n\n"
        f"Your live interview is scheduled for {start_time}.\n"
        + (f"Join link: {link}\n\n" if link else "\n")
        + "Looking forward to speaking with you!\n"
    )
    return subject, body
