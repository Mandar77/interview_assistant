"""
Feedback Service - Synthesize actionable feedback from evaluations
Location: backend/services/feedback_service/__init__.py
"""

from services.feedback_service.synthesizer import (
    FeedbackSynthesizer,
    feedback_synthesizer,
    synthesize_feedback,
    SynthesizedFeedback,
    FeedbackSection,
    ImprovementTip
)
from services.feedback_service.routes import router

__all__ = [
    # Synthesizer
    "FeedbackSynthesizer",
    "feedback_synthesizer",
    "synthesize_feedback",
    "SynthesizedFeedback",
    "FeedbackSection",
    "ImprovementTip",
    # Routes
    "router"
]