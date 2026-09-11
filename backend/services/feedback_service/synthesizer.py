"""
Feedback Synthesizer - Generate actionable feedback from evaluation results
Location: backend/services/feedback_service/synthesizer.py

Consumes the per-engine evaluation output. Feedback is organised per engine and
scored 0-100; there is no combined verdict. The "are you ready" signal is the
technical engine, because that is the axis that says whether the answer was
right - not how well it was delivered.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)

# Performance bands on the 0-100 scale.
PERFORMANCE_BANDS = (
    (85, "excellent"),
    (70, "good"),
    (55, "satisfactory"),
    (0, "needs_improvement"),
)

# Below this an engine is called out as a priority area.
PRIORITY_THRESHOLD = 60.0
# Below this we attach a targeted improvement tip.
TIP_THRESHOLD = 70.0
# At or above this an engine counts as a strength.
STRENGTH_THRESHOLD = 75.0


def performance_band(score: Optional[float]) -> str:
    """Map a 0-100 score onto a performance label."""
    if score is None:
        return "not_assessed"
    for floor, label in PERFORMANCE_BANDS:
        if score >= floor:
            return label
    return "needs_improvement"


def _as_dict(item: Any) -> Dict[str, Any]:
    """Accept engines as dataclasses or plain dicts."""
    if isinstance(item, dict):
        return item
    if hasattr(item, "__dict__"):
        return dict(item.__dict__)
    return {}


@dataclass
class FeedbackSection:
    """A section of feedback."""
    title: str
    content: str
    priority: str  # high, medium, low
    category: str


@dataclass
class ImprovementTip:
    """A specific improvement tip."""
    area: str
    tip: str
    example: Optional[str] = None
    resources: List[str] = field(default_factory=list)


@dataclass
class SynthesizedFeedback:
    """
    Complete synthesized feedback.

    `engine_performance` holds one label per engine. `technical_performance` is
    called out separately because it is the axis that decides correctness -
    deliberately NOT an average of the engines.
    """
    session_id: str
    summary: str
    technical_performance: str
    engine_performance: Dict[str, str]
    detailed_sections: List[FeedbackSection]
    improvement_tips: List[ImprovementTip]
    strengths_highlight: List[str]
    priority_areas: List[str]
    recommended_topics: List[str]
    next_steps: List[str]
    encouragement: str
    generated_at: datetime


class FeedbackSynthesizer:
    """
    Synthesize comprehensive, actionable feedback from evaluation results.
    Uses LLM to generate personalized, constructive feedback.
    """

    def __init__(self):
        self.llm_client = get_llm_client()

    def synthesize(
        self,
        session_id: str,
        evaluation_result: Dict[str, Any],
        question_text: str,
        answer_text: str,
        interview_type: str = "technical",
        verbosity: str = "detailed"  # brief, detailed, comprehensive
    ) -> SynthesizedFeedback:
        """
        Synthesize comprehensive feedback from evaluation results.

        Args:
            session_id: Session identifier
            evaluation_result: Output from RubricScorer (per-engine, 0-100)
            question_text: The interview question
            answer_text: Candidate's answer
            interview_type: Type of interview
            verbosity: Level of detail in feedback

        Returns:
            SynthesizedFeedback with all components
        """
        logger.info(f"Synthesizing feedback for session {session_id}")

        engines = [_as_dict(e) for e in evaluation_result.get("engines", [])]
        strengths = evaluation_result.get("strengths", [])
        weaknesses = evaluation_result.get("weaknesses", [])

        engine_performance = {
            e.get("engine", "unknown"): performance_band(e.get("score"))
            for e in engines
            if e.get("assessed", True)
        }

        technical = next((e for e in engines if e.get("engine") == "technical"), {})
        technical_score = technical.get("score")
        technical_performance = performance_band(technical_score)

        summary = self._generate_summary(
            engines=engines,
            technical=technical,
            technical_performance=technical_performance,
        )

        detailed_sections = self._generate_detailed_sections(
            engines=engines,
            verbosity=verbosity
        )

        improvement_tips = self._generate_improvement_tips(engines=engines)

        # Generate LLM-based personalized feedback
        llm_feedback = self._generate_llm_feedback(
            question_text=question_text,
            answer_text=answer_text,
            engines=engines,
            interview_type=interview_type
        )

        priority_areas = self._identify_priority_areas(engines)

        recommended_topics = self._recommend_topics(
            engines=engines,
            interview_type=interview_type
        )

        next_steps = self._generate_next_steps(
            technical_performance=technical_performance,
            priority_areas=priority_areas,
            llm_feedback=llm_feedback,
        )

        encouragement = self._generate_encouragement(technical_performance)

        return SynthesizedFeedback(
            session_id=session_id,
            summary=summary,
            technical_performance=technical_performance,
            engine_performance=engine_performance,
            detailed_sections=detailed_sections,
            improvement_tips=improvement_tips,
            strengths_highlight=strengths[:3],
            priority_areas=priority_areas,
            recommended_topics=recommended_topics,
            next_steps=next_steps,
            encouragement=encouragement,
            generated_at=datetime.utcnow()
        )

    def _generate_summary(
        self,
        engines: List[Dict],
        technical: Dict,
        technical_performance: str,
    ) -> str:
        """
        Summarise each engine separately.

        The technical line comes first and stands alone, so a strong language
        score can never be read as compensating for a wrong answer.
        """
        level_descriptions = {
            "excellent": "the answer was correct and complete",
            "good": "the answer was largely correct",
            "satisfactory": "the answer was partially correct",
            "needs_improvement": "the answer did not hold up technically",
            "not_assessed": "technical correctness could not be assessed",
        }

        technical_score = technical.get("score")
        if technical_score is None:
            lead = "Technical correctness could not be assessed for this answer. "
        else:
            lead = (
                f"Technical correctness: {technical_score:.0f}/100 - "
                f"{level_descriptions[technical_performance]}. "
            )

        others = [
            f"{e.get('engine_name', e.get('engine'))} {e.get('score'):.0f}/100"
            for e in engines
            if e.get("engine") != "technical"
            and e.get("assessed", True)
            and e.get("score") is not None
        ]
        if others:
            lead += "Scored separately: " + ", ".join(others) + ". "
            lead += "These are reported on their own and do not change the technical rating."

        return lead.strip()

    def _generate_detailed_sections(
        self,
        engines: List[Dict],
        verbosity: str
    ) -> List[FeedbackSection]:
        """One section per engine, plus its dimensions when verbose."""
        sections = []

        for engine in engines:
            score = engine.get("score")
            name = engine.get("engine_name", engine.get("engine", "Unknown"))
            feedback = engine.get("feedback", "No specific feedback")
            evidence = engine.get("evidence", []) or []
            dimensions = [_as_dict(d) for d in (engine.get("dimensions") or [])]

            if not engine.get("assessed", True) or score is None:
                sections.append(FeedbackSection(
                    title=name,
                    content=f"Not assessed. {feedback}",
                    priority="low",
                    category=engine.get("engine", "general"),
                ))
                continue

            if score < PRIORITY_THRESHOLD:
                priority = "high"
            elif score < STRENGTH_THRESHOLD:
                priority = "medium"
            else:
                priority = "low"

            if verbosity == "brief":
                content = f"Score: {score:.0f}/100. {feedback}"
            elif verbosity == "comprehensive":
                evidence_str = " Evidence: " + "; ".join(str(e) for e in evidence) if evidence else ""
                breakdown = "; ".join(
                    f"{d.get('dimension_name')} {d.get('score'):.0f}"
                    for d in dimensions
                    if d.get("score") is not None
                )
                breakdown_str = f" Breakdown: {breakdown}." if breakdown else ""
                content = f"Score: {score:.0f}/100. {feedback}{breakdown_str}{evidence_str}"
            else:  # detailed
                content = f"Score: {score:.0f}/100. {feedback}"
                if evidence:
                    content += f" ({evidence[0]})"

            sections.append(FeedbackSection(
                title=name,
                content=content,
                priority=priority,
                category=engine.get("engine", "general")
            ))

        priority_order = {"high": 0, "medium": 1, "low": 2}
        sections.sort(key=lambda x: priority_order.get(x.priority, 2))

        return sections

    def _generate_improvement_tips(self, engines: List[Dict]) -> List[ImprovementTip]:
        """Attach targeted tips for any engine or dimension scoring low."""
        tips: List[ImprovementTip] = []

        engine_tips = {
            "technical": ImprovementTip(
                area="Technical Knowledge",
                tip="Answer the question that was asked first, then add depth. State the core mechanism in one sentence before elaborating",
                example="'A hash map is O(1) average because the hash function maps the key straight to a bucket' - then explain collisions",
                resources=["LeetCode for coding", "System Design Primer for architecture"]
            ),
            "language": ImprovementTip(
                area="Language Quality",
                tip="Structure answers with a framework (STAR, or claim-evidence-conclusion) and keep sentences to 15-20 words",
                example="Start with 'The situation was...' then explain your approach",
                resources=["Practice explaining technical concepts to non-technical friends"]
            ),
            "speech_delivery": ImprovementTip(
                area="Speech Delivery",
                tip="Aim for 120-160 words per minute. Pause intentionally instead of using filler words",
                example="Replace 'um' with a brief pause to collect your thoughts",
                resources=["Record yourself and listen back", "Practice with a metronome app"]
            ),
            "body_language": ImprovementTip(
                area="Body Language",
                tip="Maintain eye contact with the camera (not the screen), sit up straight, and use hand gestures naturally",
                example="Position camera at eye level, look at the lens when speaking",
                resources=["Practice with video recordings", "Watch TED talks for examples"]
            ),
            "time_management": ImprovementTip(
                area="Time Management",
                tip="Practice with a timer. Allocate time: 20% understanding, 60% solution, 20% review",
                example="For a 45-min question: 9 min clarify, 27 min solve, 9 min review",
                resources=["Use interview timer apps", "Practice under time pressure"]
            ),
        }

        dimension_tips = {
            "relevance": ImprovementTip(
                area="Answering the Question",
                tip="Restate the question in your own words before answering, then check your answer against it at the end",
                example="'So you're asking how the lookup stays O(1) even with collisions - here's how...'",
                resources=["Practice one-sentence answers before elaborating"]
            ),
            "problem_solving": ImprovementTip(
                area="Problem Solving",
                tip="Clarify requirements before solving. Think out loud so your reasoning is visible",
                example="Before solving, ask: What are the constraints? What's the expected scale?",
                resources=["Practice whiteboard problems", "Review common problem-solving patterns"]
            ),
            "system_design": ImprovementTip(
                area="System Design",
                tip="Name the trade-off behind every choice - a design without trade-offs reads as memorised",
                example="'I'd shard by user id; that costs cross-user queries but keeps writes local'",
                resources=["System Design Primer", "Designing Data-Intensive Applications"]
            ),
            "factual_accuracy": ImprovementTip(
                area="Factual Accuracy",
                tip="Say 'I'm not certain' rather than asserting. Confident wrong answers cost more than admitted gaps",
                example="'I believe it's O(log n), though I'd want to verify the rebalancing cost'",
                resources=["Review fundamentals you tend to state from memory"]
            ),
        }

        for engine in engines:
            if not engine.get("assessed", True):
                continue
            score = engine.get("score")
            if score is None or score >= TIP_THRESHOLD:
                continue

            engine_id = engine.get("engine", "")
            if engine_id in engine_tips:
                tips.append(engine_tips[engine_id])

            # Drill into the weakest dimensions of a weak engine.
            for dim in (engine.get("dimensions") or []):
                dim_dict = _as_dict(dim)
                dim_score = dim_dict.get("score")
                dim_id = dim_dict.get("dimension", "")
                if dim_score is not None and dim_score < TIP_THRESHOLD and dim_id in dimension_tips:
                    tips.append(dimension_tips[dim_id])

        # Deduplicate by area, keep the first five.
        seen = set()
        unique: List[ImprovementTip] = []
        for tip in tips:
            if tip.area in seen:
                continue
            seen.add(tip.area)
            unique.append(tip)
        return unique[:5]

    def _generate_llm_feedback(
        self,
        question_text: str,
        answer_text: str,
        engines: List[Dict],
        interview_type: str
    ) -> Dict[str, str]:
        """Use LLM to generate personalized feedback."""

        system_prompt = """You are a supportive interview coach providing constructive feedback.
Be specific, actionable, and encouraging. Focus on improvement, not criticism.

Each axis was scored independently. Never suggest that strong delivery or good
English makes up for a weak technical score - address them as separate things.
Keep feedback concise but helpful."""

        scores_summary = ", ".join(
            f"{e.get('engine_name', e.get('engine'))}: {e.get('score'):.0f}/100"
            for e in engines
            if e.get("assessed", True) and e.get("score") is not None
        ) or "no scores available"

        prompt = f"""Generate brief, actionable feedback for this interview response:

Question ({interview_type}): {question_text[:500]}

Answer: {answer_text[:1000]}

Independent scores (0-100): {scores_summary}

Provide JSON with:
{{
  "what_went_well": "1-2 sentences on strengths, naming which axis they are on",
  "key_improvement": "1 specific, actionable improvement",
  "suggested_addition": "What could have been added to the answer"
}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5
            )

            match = re.search(r'\{[\s\S]*?\}', response)
            if match:
                return json.loads(match.group())

        except Exception as e:
            logger.error(f"LLM feedback generation failed: {e}")

        return {
            "what_went_well": "You provided a structured response",
            "key_improvement": "Add more specific examples",
            "suggested_addition": "Consider discussing trade-offs"
        }

    def _identify_priority_areas(self, engines: List[Dict]) -> List[str]:
        """Weakest engines first, each labelled with its own axis."""
        scored = [
            e for e in engines
            if e.get("assessed", True) and e.get("score") is not None
        ]
        priority_areas = [
            f"{e.get('engine_name', e.get('engine'))} ({e.get('score'):.0f}/100)"
            for e in sorted(scored, key=lambda e: e.get("score", 0))
            if e.get("score", 0) < PRIORITY_THRESHOLD
        ]
        return priority_areas[:3]

    def _recommend_topics(
        self,
        engines: List[Dict],
        interview_type: str
    ) -> List[str]:
        """Recommend topics to study based on the weak dimensions."""
        topic_map = {
            "technical_correctness": ["Data Structures", "Algorithms", "System fundamentals"],
            "relevance": ["Answering the question asked", "Structured answer frameworks"],
            "problem_solving": ["Problem-solving patterns", "Debugging techniques"],
            "system_design": ["Distributed systems", "Scalability patterns", "Database design"],
            "factual_accuracy": ["Reviewing fundamentals", "Calibrated confidence"],
            "clarity": ["Technical communication", "Presentation skills"],
            "grammar_vocabulary": ["Professional vocabulary", "Technical writing"],
        }

        recommendations: List[str] = []
        for engine in engines:
            if not engine.get("assessed", True):
                continue
            for dim in (engine.get("dimensions") or []):
                dim_dict = _as_dict(dim)
                score = dim_dict.get("score")
                dim_id = dim_dict.get("dimension", "")
                if score is not None and score < TIP_THRESHOLD and dim_id in topic_map:
                    recommendations.extend(topic_map[dim_id])

        return list(dict.fromkeys(recommendations))[:5]

    def _generate_next_steps(
        self,
        technical_performance: str,
        priority_areas: List[str],
        llm_feedback: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """Actionable next steps, anchored on the technical result."""
        base_steps = {
            "excellent": [
                "Continue practicing to maintain your edge",
                "Consider mentoring others to reinforce your knowledge",
                "Explore advanced topics in your strong areas"
            ],
            "good": [
                "Focus on your priority areas for quick improvements",
                "Practice mock interviews weekly",
                "Review your weak areas with targeted study"
            ],
            "satisfactory": [
                "Dedicate focused time to each priority area",
                "Practice explaining concepts out loud",
                "Do at least 2-3 mock interviews per week"
            ],
            "needs_improvement": [
                "Start with fundamentals - review core concepts",
                "Practice daily, even for 30 minutes",
                "Consider finding a study partner or mentor",
                "Don't get discouraged - consistent practice leads to improvement"
            ],
            "not_assessed": [
                "Re-run the interview once the evaluation model is available",
                "Check that Ollama is running so answers can be graded",
            ],
        }

        steps = list(base_steps.get(technical_performance, base_steps["satisfactory"]))

        if llm_feedback and llm_feedback.get("key_improvement"):
            steps.insert(0, str(llm_feedback["key_improvement"]))

        if priority_areas:
            steps.insert(0, f"Immediate focus: {priority_areas[0]}")

        return steps

    def _generate_encouragement(self, technical_performance: str) -> str:
        """Generate an encouraging closing message."""
        messages = {
            "excellent": "Outstanding work! Your answers held up technically. Keep it up!",
            "good": "Great job! The substance was mostly there. A bit more precision and you'll be interview-ready!",
            "satisfactory": "Good effort! Tighten up the technical accuracy and you'll see a big jump.",
            "needs_improvement": "Every expert was once a beginner. Focus on the fundamentals - that's where the score moves most.",
            "not_assessed": "We couldn't grade the technical side this time. Re-run it and you'll get the full picture.",
        }

        return messages.get(technical_performance, messages["satisfactory"])


# Module-level instance
feedback_synthesizer = FeedbackSynthesizer()


def synthesize_feedback(**kwargs) -> SynthesizedFeedback:
    """Convenience function for feedback synthesis."""
    return feedback_synthesizer.synthesize(**kwargs)
