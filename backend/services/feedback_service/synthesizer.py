"""
Feedback Synthesizer - Generate actionable feedback from evaluation results
Location: backend/services/feedback_service/synthesizer.py
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


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
    """Complete synthesized feedback."""
    session_id: str
    summary: str
    overall_performance: str  # excellent, good, satisfactory, needs_improvement
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
            evaluation_result: Output from RubricScorer
            question_text: The interview question
            answer_text: Candidate's answer
            interview_type: Type of interview
            verbosity: Level of detail in feedback
            
        Returns:
            SynthesizedFeedback with all components
        """
        logger.info(f"Synthesizing feedback for session {session_id}")
        
        # Extract key metrics
        overall_score = evaluation_result.get("overall_score", 3.0)
        weighted_score = evaluation_result.get("weighted_score", 3.0)
        rubric_scores = evaluation_result.get("rubric_scores", [])
        strengths = evaluation_result.get("strengths", [])
        weaknesses = evaluation_result.get("weaknesses", [])
        
        # Determine overall performance level
        overall_performance = self._determine_performance_level(weighted_score)
        
        # Generate summary
        summary = self._generate_summary(
            overall_score=overall_score,
            performance_level=overall_performance,
            strengths=strengths,
            weaknesses=weaknesses
        )
        
        # Generate detailed sections
        detailed_sections = self._generate_detailed_sections(
            rubric_scores=rubric_scores,
            verbosity=verbosity
        )
        
        # Generate improvement tips
        improvement_tips = self._generate_improvement_tips(
            weaknesses=weaknesses,
            rubric_scores=rubric_scores,
            interview_type=interview_type
        )
        
        # Generate LLM-based personalized feedback
        llm_feedback = self._generate_llm_feedback(
            question_text=question_text,
            answer_text=answer_text,
            evaluation_result=evaluation_result,
            interview_type=interview_type
        )
        
        # Identify priority areas
        priority_areas = self._identify_priority_areas(rubric_scores)
        
        # Recommend topics to study
        recommended_topics = self._recommend_topics(
            weaknesses=weaknesses,
            rubric_scores=rubric_scores,
            interview_type=interview_type
        )
        
        # Generate next steps
        next_steps = self._generate_next_steps(
            performance_level=overall_performance,
            priority_areas=priority_areas
        )
        
        # Encouragement message
        encouragement = self._generate_encouragement(overall_performance)
        
        return SynthesizedFeedback(
            session_id=session_id,
            summary=summary,
            overall_performance=overall_performance,
            detailed_sections=detailed_sections,
            improvement_tips=improvement_tips,
            strengths_highlight=strengths[:3],
            priority_areas=priority_areas,
            recommended_topics=recommended_topics,
            next_steps=next_steps,
            encouragement=encouragement,
            generated_at=datetime.utcnow()
        )
    
    def _determine_performance_level(self, weighted_score: float) -> str:
        """Determine overall performance level from score."""
        if weighted_score >= 4.5:
            return "excellent"
        elif weighted_score >= 3.5:
            return "good"
        elif weighted_score >= 2.5:
            return "satisfactory"
        else:
            return "needs_improvement"
    
    def _generate_summary(
        self,
        overall_score: float,
        performance_level: str,
        strengths: List[str],
        weaknesses: List[str]
    ) -> str:
        """Generate a concise summary of performance."""
        
        level_descriptions = {
            "excellent": "demonstrated exceptional performance",
            "good": "showed strong competency",
            "satisfactory": "met basic expectations",
            "needs_improvement": "has areas that need development"
        }
        
        summary = f"Overall score: {overall_score}/5. You {level_descriptions[performance_level]}. "
        
        if strengths:
            summary += f"Key strengths include {strengths[0].split(':')[0].lower()}. "
        
        if weaknesses:
            summary += f"Focus area: {weaknesses[0].split(':')[0].lower()}."
        
        return summary
    
    def _generate_detailed_sections(
        self,
        rubric_scores: List[Dict],
        verbosity: str
    ) -> List[FeedbackSection]:
        """Generate detailed feedback sections for each rubric category."""
        
        sections = []
        
        for score_data in rubric_scores:
            # Handle both dict and dataclass
            if hasattr(score_data, '__dict__'):
                score_dict = score_data.__dict__
            else:
                score_dict = score_data
            
            score = score_dict.get("score", 3.0)
            category_name = score_dict.get("category_name", score_dict.get("category", "Unknown"))
            feedback = score_dict.get("feedback", "No specific feedback")
            evidence = score_dict.get("evidence", [])
            
            # Determine priority based on score
            if score < 3.0:
                priority = "high"
            elif score < 4.0:
                priority = "medium"
            else:
                priority = "low"
            
            # Build content based on verbosity
            if verbosity == "brief":
                content = f"Score: {score}/5. {feedback}"
            elif verbosity == "comprehensive":
                evidence_str = " Evidence: " + "; ".join(evidence) if evidence else ""
                content = f"Score: {score}/5. {feedback}{evidence_str}"
            else:  # detailed
                content = f"Score: {score}/5. {feedback}"
                if evidence:
                    content += f" ({evidence[0]})"
            
            sections.append(FeedbackSection(
                title=category_name,
                content=content,
                priority=priority,
                category=score_dict.get("category", "general")
            ))
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sections.sort(key=lambda x: priority_order.get(x.priority, 2))
        
        return sections
    
    def _generate_improvement_tips(
        self,
        weaknesses: List[str],
        rubric_scores: List[Dict],
        interview_type: str
    ) -> List[ImprovementTip]:
        """Generate specific improvement tips based on weaknesses."""
        
        tips = []
        
        # Generic tips based on common weak areas
        tip_templates = {
            "communication": ImprovementTip(
                area="Communication",
                tip="Structure your answers using the STAR method (Situation, Task, Action, Result) or a similar framework",
                example="Start with 'The situation was...' then explain your approach",
                resources=["Practice explaining technical concepts to non-technical friends"]
            ),
            "confidence_pacing": ImprovementTip(
                area="Confidence & Pacing",
                tip="Practice speaking at 130-150 words per minute. Pause intentionally instead of using filler words",
                example="Replace 'um' with a brief pause to collect your thoughts",
                resources=["Record yourself and listen back", "Practice with a metronome app"]
            ),
            "technical_correctness": ImprovementTip(
                area="Technical Knowledge",
                tip="Review fundamental concepts and practice explaining them clearly",
                example="Can you explain this concept to a junior developer?",
                resources=["LeetCode for coding", "System Design Primer for architecture"]
            ),
            "problem_solving": ImprovementTip(
                area="Problem Solving",
                tip="Always clarify requirements before diving into solutions. Think out loud to show your reasoning",
                example="Before solving, ask: What are the constraints? What's the expected scale?",
                resources=["Practice whiteboard problems", "Review common problem-solving patterns"]
            ),
            "time_utilization": ImprovementTip(
                area="Time Management",
                tip="Practice with a timer. Allocate time: 20% understanding, 60% solution, 20% review",
                example="For a 45-min question: 9 min clarify, 27 min solve, 9 min review",
                resources=["Use interview timer apps", "Practice under time pressure"]
            ),
            "body_language": ImprovementTip(
                area="Body Language",
                tip="Maintain eye contact with the camera (not screen), sit up straight, and use hand gestures naturally",
                example="Position camera at eye level, look at the lens when speaking",
                resources=["Practice with video recordings", "Watch TED talks for examples"]
            )
        }
        
        # Add tips for weak areas
        for score_data in rubric_scores:
            if hasattr(score_data, '__dict__'):
                score_dict = score_data.__dict__
            else:
                score_dict = score_data
                
            score = score_dict.get("score", 3.0)
            category = score_dict.get("category", "")
            
            if score < 3.5 and category in tip_templates:
                tips.append(tip_templates[category])
        
        # Limit to top 5 tips
        return tips[:5]
    
    def _generate_llm_feedback(
        self,
        question_text: str,
        answer_text: str,
        evaluation_result: Dict,
        interview_type: str
    ) -> Dict[str, str]:
        """Use LLM to generate personalized feedback."""
        
        system_prompt = """You are a supportive interview coach providing constructive feedback.
Be specific, actionable, and encouraging. Focus on improvement, not criticism.
Keep feedback concise but helpful."""

        scores_summary = f"Overall: {evaluation_result.get('overall_score', 3)}/5"
        
        prompt = f"""Generate brief, actionable feedback for this interview response:

Question ({interview_type}): {question_text[:500]}

Answer: {answer_text[:1000]}

Scores: {scores_summary}

Provide JSON with:
{{
  "what_went_well": "1-2 sentences on strengths",
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
    
    def _identify_priority_areas(self, rubric_scores: List[Dict]) -> List[str]:
        """Identify top priority areas for improvement."""
        
        priority_areas = []
        
        for score_data in rubric_scores:
            if hasattr(score_data, '__dict__'):
                score_dict = score_data.__dict__
            else:
                score_dict = score_data
                
            score = score_dict.get("score", 3.0)
            category_name = score_dict.get("category_name", score_dict.get("category", "Unknown"))
            
            if score < 3.0:
                priority_areas.append(f"{category_name} (score: {score}/5)")
        
        return priority_areas[:3]  # Top 3 priorities
    
    def _recommend_topics(
        self,
        weaknesses: List[str],
        rubric_scores: List[Dict],
        interview_type: str
    ) -> List[str]:
        """Recommend topics to study based on performance."""
        
        recommendations = []
        
        # Map categories to study topics
        topic_map = {
            "technical_correctness": ["Data Structures", "Algorithms", "System fundamentals"],
            "problem_solving": ["Problem-solving patterns", "Debugging techniques"],
            "system_design": ["Distributed systems", "Scalability patterns", "Database design"],
            "communication": ["Technical communication", "Presentation skills"],
            "grammar_vocabulary": ["Professional vocabulary", "Technical writing"]
        }
        
        for score_data in rubric_scores:
            if hasattr(score_data, '__dict__'):
                score_dict = score_data.__dict__
            else:
                score_dict = score_data
                
            score = score_dict.get("score", 3.0)
            category = score_dict.get("category", "")
            
            if score < 3.5 and category in topic_map:
                recommendations.extend(topic_map[category])
        
        # Deduplicate and limit
        return list(dict.fromkeys(recommendations))[:5]
    
    def _generate_next_steps(
        self,
        performance_level: str,
        priority_areas: List[str]
    ) -> List[str]:
        """Generate actionable next steps."""
        
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
            ]
        }
        
        steps = base_steps.get(performance_level, base_steps["satisfactory"])
        
        # Add specific steps for priority areas
        if priority_areas:
            steps.insert(0, f"Immediate focus: {priority_areas[0]}")
        
        return steps
    
    def _generate_encouragement(self, performance_level: str) -> str:
        """Generate an encouraging closing message."""
        
        messages = {
            "excellent": "Outstanding work! You're well-prepared for your interviews. Keep up the excellent performance!",
            "good": "Great job! You're on the right track. A bit more practice and you'll be interview-ready!",
            "satisfactory": "Good effort! With focused practice on your priority areas, you'll see significant improvement.",
            "needs_improvement": "Every expert was once a beginner. Stay consistent with your practice, and you'll get there!"
        }
        
        return messages.get(performance_level, messages["satisfactory"])


# Module-level instance
feedback_synthesizer = FeedbackSynthesizer()


def synthesize_feedback(**kwargs) -> SynthesizedFeedback:
    """Convenience function for feedback synthesis."""
    return feedback_synthesizer.synthesize(**kwargs)