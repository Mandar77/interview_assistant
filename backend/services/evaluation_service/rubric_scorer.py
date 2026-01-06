"""
Rubric Scorer - Aggregate scores from all modalities into unified evaluation
Location: backend/services/evaluation_service/rubric_scorer.py
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


# =============================================================================
# Rubric Configuration
# =============================================================================

RUBRIC_CATEGORIES = {
    "technical_correctness": {
        "name": "Technical Correctness",
        "weight": 0.20,
        "description": "Accuracy of technical concepts, code, and solutions",
        "source": "llm_evaluation"
    },
    "problem_solving": {
        "name": "Problem-Solving Approach",
        "weight": 0.15,
        "description": "Methodology, structure, and logical reasoning",
        "source": "llm_evaluation"
    },
    "system_design": {
        "name": "System Design Quality",
        "weight": 0.15,
        "description": "Architecture decisions, scalability, trade-offs",
        "source": "llm_evaluation"
    },
    "communication": {
        "name": "Communication Clarity",
        "weight": 0.12,
        "description": "Clarity, structure, and effectiveness of explanation",
        "source": "language_metrics"
    },
    "grammar_vocabulary": {
        "name": "Grammar & Vocabulary",
        "weight": 0.08,
        "description": "Language correctness and professional vocabulary",
        "source": "language_metrics"
    },
    "confidence_pacing": {
        "name": "Confidence & Pacing",
        "weight": 0.10,
        "description": "Speaking confidence, pace, and filler word usage",
        "source": "speech_metrics"
    },
    "body_language": {
        "name": "Body Language Signals",
        "weight": 0.08,
        "description": "Eye contact, posture, gestures, facial expressions",
        "source": "body_language_metrics"
    },
    "time_utilization": {
        "name": "Time Utilization",
        "weight": 0.07,
        "description": "Effective use of allotted time",
        "source": "timing_metrics"
    },
    "claim_consistency": {
        "name": "Claim Consistency",
        "weight": 0.05,
        "description": "Factual accuracy and consistency of claims",
        "source": "hallucination_check"
    }
}

SCORE_LEVELS = {
    0: "No attempt or completely incorrect",
    1: "Major issues, significant gaps",
    2: "Some correct elements but incomplete",
    3: "Mostly correct with minor issues",
    4: "Good performance with strong understanding",
    5: "Excellent, demonstrates mastery"
}


@dataclass
class RubricScore:
    """Score for a single rubric category."""
    category: str
    category_name: str
    score: float
    weight: float
    feedback: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Complete evaluation result."""
    session_id: str
    question_id: str
    rubric_scores: List[RubricScore]
    overall_score: float
    weighted_score: float
    strengths: List[str]
    weaknesses: List[str]
    confidence_index: float
    pass_threshold: bool
    excellence_threshold: bool


class RubricScorer:
    """
    Score interview responses using a multi-category rubric.
    Aggregates metrics from speech, language, body language, and LLM evaluation.
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.categories = RUBRIC_CATEGORIES
        self.pass_threshold = 3.0
        self.excellence_threshold = 4.5
    
    def evaluate(
        self,
        session_id: str,
        question_id: str,
        question_text: str,
        answer_text: str,
        speech_metrics: Optional[Dict] = None,
        language_metrics: Optional[Dict] = None,
        body_language_metrics: Optional[Dict] = None,
        timing_metrics: Optional[Dict] = None,
        interview_type: str = "technical"
    ) -> EvaluationResult:
        """
        Evaluate an interview response across all rubric categories.
        
        Args:
            session_id: Unique session identifier
            question_id: Question being answered
            question_text: The interview question
            answer_text: Transcribed answer
            speech_metrics: Output from speech analyzer
            language_metrics: Output from language analyzer
            body_language_metrics: Output from MediaPipe analyzer
            timing_metrics: Time taken vs expected
            interview_type: Type of interview question
            
        Returns:
            Complete EvaluationResult with all scores
        """
        logger.info(f"Evaluating response for session {session_id}, question {question_id}")
        
        rubric_scores = []
        
        # 1. Get LLM-based scores (technical, problem-solving, system design)
        llm_scores = self._evaluate_with_llm(
            question_text=question_text,
            answer_text=answer_text,
            interview_type=interview_type
        )
        
        for category in ["technical_correctness", "problem_solving", "system_design"]:
            if category in llm_scores:
                rubric_scores.append(RubricScore(
                    category=category,
                    category_name=self.categories[category]["name"],
                    score=llm_scores[category]["score"],
                    weight=self.categories[category]["weight"],
                    feedback=llm_scores[category]["feedback"],
                    evidence=llm_scores[category].get("evidence", [])
                ))
        
        # 2. Score communication from language metrics
        comm_score = self._score_communication(language_metrics)
        rubric_scores.append(comm_score)
        
        # 3. Score grammar & vocabulary from language metrics
        grammar_score = self._score_grammar(language_metrics)
        rubric_scores.append(grammar_score)
        
        # 4. Score confidence & pacing from speech metrics
        confidence_score = self._score_confidence(speech_metrics)
        rubric_scores.append(confidence_score)
        
        # 5. Score body language (if available)
        body_score = self._score_body_language(body_language_metrics)
        rubric_scores.append(body_score)
        
        # 6. Score time utilization
        time_score = self._score_time_utilization(timing_metrics)
        rubric_scores.append(time_score)
        
        # 7. Score claim consistency (from LLM evaluation)
        consistency_score = RubricScore(
            category="claim_consistency",
            category_name=self.categories["claim_consistency"]["name"],
            score=llm_scores.get("claim_consistency", {}).get("score", 4.0),
            weight=self.categories["claim_consistency"]["weight"],
            feedback=llm_scores.get("claim_consistency", {}).get("feedback", "No major inconsistencies detected"),
            evidence=[]
        )
        rubric_scores.append(consistency_score)
        
        # Calculate overall scores
        overall_score = sum(s.score for s in rubric_scores) / len(rubric_scores)
        weighted_score = sum(s.score * s.weight for s in rubric_scores)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(rubric_scores)
        
        # Calculate confidence index
        confidence_index = self._calculate_confidence_index(
            rubric_scores, speech_metrics, language_metrics
        )
        
        return EvaluationResult(
            session_id=session_id,
            question_id=question_id,
            rubric_scores=rubric_scores,
            overall_score=round(overall_score, 2),
            weighted_score=round(weighted_score, 2),
            strengths=strengths,
            weaknesses=weaknesses,
            confidence_index=round(confidence_index, 2),
            pass_threshold=weighted_score >= self.pass_threshold,
            excellence_threshold=weighted_score >= self.excellence_threshold
        )
    
    def _evaluate_with_llm(
        self,
        question_text: str,
        answer_text: str,
        interview_type: str
    ) -> Dict[str, Any]:
        """Use LLM to evaluate technical aspects of the answer."""
        
        system_prompt = """You are an expert technical interviewer evaluating candidate responses.
Score each category from 0-5 based on the rubric:
- 0: No attempt or completely incorrect
- 1: Major issues, significant gaps
- 2: Some correct elements but incomplete
- 3: Mostly correct with minor issues
- 4: Good performance with strong understanding
- 5: Excellent, demonstrates mastery

Be fair but rigorous. Provide specific evidence for your scores.
Return ONLY valid JSON."""

        prompt = f"""Evaluate this interview response:

QUESTION ({interview_type}):
{question_text}

CANDIDATE'S ANSWER:
{answer_text}

Score these categories (0-5 scale):
1. technical_correctness: Accuracy of technical concepts and solutions
2. problem_solving: Methodology, structure, logical reasoning
3. system_design: Architecture thinking, scalability awareness (if applicable)
4. claim_consistency: Are claims factually accurate and internally consistent?

Return JSON:
{{
  "technical_correctness": {{
    "score": 4.0,
    "feedback": "Specific feedback here",
    "evidence": ["Evidence point 1", "Evidence point 2"]
  }},
  "problem_solving": {{
    "score": 3.5,
    "feedback": "Specific feedback here",
    "evidence": ["Evidence point 1"]
  }},
  "system_design": {{
    "score": 3.0,
    "feedback": "Specific feedback here",
    "evidence": []
  }},
  "claim_consistency": {{
    "score": 4.5,
    "feedback": "Claims are consistent and accurate",
    "evidence": []
  }}
}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
        
        # Return default scores on failure
        return {
            "technical_correctness": {"score": 3.0, "feedback": "Unable to evaluate", "evidence": []},
            "problem_solving": {"score": 3.0, "feedback": "Unable to evaluate", "evidence": []},
            "system_design": {"score": 3.0, "feedback": "Unable to evaluate", "evidence": []},
            "claim_consistency": {"score": 4.0, "feedback": "Unable to verify claims", "evidence": []}
        }
    
    def _score_communication(self, language_metrics: Optional[Dict]) -> RubricScore:
        """Score communication clarity from language metrics."""
        if not language_metrics:
            return RubricScore(
                category="communication",
                category_name=self.categories["communication"]["name"],
                score=3.0,
                weight=self.categories["communication"]["weight"],
                feedback="No language metrics available",
                evidence=[]
            )
        
        clarity = language_metrics.get("clarity_score", 3.0)
        readability = language_metrics.get("readability_flesch", 50)
        avg_sentence = language_metrics.get("avg_sentence_length", 15)
        
        # Combine factors
        readability_factor = min(readability / 20, 5)  # Scale 0-100 to 0-5
        sentence_factor = 5.0 if 10 <= avg_sentence <= 20 else 3.0
        
        score = (clarity * 0.5) + (readability_factor * 0.3) + (sentence_factor * 0.2)
        score = min(max(score, 0), 5)
        
        feedback_parts = []
        if clarity >= 4:
            feedback_parts.append("Clear and well-structured explanations")
        elif clarity < 3:
            feedback_parts.append("Could improve clarity of explanations")
        
        if readability >= 60:
            feedback_parts.append("Good readability level")
        elif readability < 40:
            feedback_parts.append("Consider simplifying language")
        
        return RubricScore(
            category="communication",
            category_name=self.categories["communication"]["name"],
            score=round(score, 1),
            weight=self.categories["communication"]["weight"],
            feedback=". ".join(feedback_parts) if feedback_parts else "Adequate communication",
            evidence=[f"Clarity score: {clarity}/5", f"Readability: {readability}"]
        )
    
    def _score_grammar(self, language_metrics: Optional[Dict]) -> RubricScore:
        """Score grammar and vocabulary from language metrics."""
        if not language_metrics:
            return RubricScore(
                category="grammar_vocabulary",
                category_name=self.categories["grammar_vocabulary"]["name"],
                score=3.0,
                weight=self.categories["grammar_vocabulary"]["weight"],
                feedback="No language metrics available",
                evidence=[]
            )
        
        grammar_score = language_metrics.get("grammar_score", 3.0)
        vocab_level = language_metrics.get("vocabulary_level", "intermediate")
        unique_ratio = language_metrics.get("unique_word_ratio", 0.5)
        
        # Vocabulary bonus
        vocab_bonus = {"basic": 0, "intermediate": 0.3, "advanced": 0.5}.get(vocab_level, 0)
        
        score = grammar_score + vocab_bonus
        score = min(max(score, 0), 5)
        
        feedback = f"Grammar score: {grammar_score}/5. Vocabulary level: {vocab_level}."
        if unique_ratio > 0.6:
            feedback += " Good vocabulary diversity."
        
        return RubricScore(
            category="grammar_vocabulary",
            category_name=self.categories["grammar_vocabulary"]["name"],
            score=round(score, 1),
            weight=self.categories["grammar_vocabulary"]["weight"],
            feedback=feedback,
            evidence=[f"Unique word ratio: {unique_ratio:.2f}"]
        )
    
    def _score_confidence(self, speech_metrics: Optional[Dict]) -> RubricScore:
        """Score confidence and pacing from speech metrics."""
        if not speech_metrics:
            return RubricScore(
                category="confidence_pacing",
                category_name=self.categories["confidence_pacing"]["name"],
                score=3.0,
                weight=self.categories["confidence_pacing"]["weight"],
                feedback="No speech metrics available",
                evidence=[]
            )
        
        wpm = speech_metrics.get("words_per_minute", 130)
        filler_pct = speech_metrics.get("filler_word_percentage", 5)
        pause_count = speech_metrics.get("pause_count", 5)
        longest_pause = speech_metrics.get("longest_pause_ms", 1000)
        rate_category = speech_metrics.get("speaking_rate_category", "normal")
        
        # WPM score (ideal: 120-160)
        if 120 <= wpm <= 160:
            wpm_score = 5.0
        elif 100 <= wpm <= 180:
            wpm_score = 4.0
        elif 80 <= wpm <= 200:
            wpm_score = 3.0
        else:
            wpm_score = 2.0
        
        # Filler word penalty
        filler_penalty = min(filler_pct / 2, 2)  # Max 2 point penalty
        
        # Pause penalty (long pauses indicate uncertainty)
        pause_penalty = 0
        if longest_pause > 3000:
            pause_penalty = 1.0
        elif longest_pause > 2000:
            pause_penalty = 0.5
        
        score = wpm_score - filler_penalty - pause_penalty
        score = min(max(score, 0), 5)
        
        feedback_parts = []
        if rate_category == "normal":
            feedback_parts.append("Good speaking pace")
        elif rate_category == "fast":
            feedback_parts.append("Consider slowing down slightly")
        else:
            feedback_parts.append("Could speak with more energy")
        
        if filler_pct < 3:
            feedback_parts.append("Minimal filler words")
        elif filler_pct > 5:
            feedback_parts.append(f"Reduce filler words ({filler_pct:.1f}%)")
        
        return RubricScore(
            category="confidence_pacing",
            category_name=self.categories["confidence_pacing"]["name"],
            score=round(score, 1),
            weight=self.categories["confidence_pacing"]["weight"],
            feedback=". ".join(feedback_parts),
            evidence=[f"WPM: {wpm}", f"Filler words: {filler_pct:.1f}%", f"Speaking rate: {rate_category}"]
        )
    
    def _score_body_language(self, body_metrics: Optional[Dict]) -> RubricScore:
        """Score body language from MediaPipe metrics."""
        if not body_metrics:
            return RubricScore(
                category="body_language",
                category_name=self.categories["body_language"]["name"],
                score=3.0,  # Neutral score when not available
                weight=self.categories["body_language"]["weight"],
                feedback="Body language analysis not available",
                evidence=[]
            )
        
        eye_contact = body_metrics.get("eye_contact_percentage", 50)
        posture_score = body_metrics.get("posture_score", 3.0)
        gesture_freq = body_metrics.get("gesture_frequency", 5)
        
        # Eye contact score (ideal: 60-80%)
        if 60 <= eye_contact <= 80:
            eye_score = 5.0
        elif 40 <= eye_contact <= 90:
            eye_score = 4.0
        elif 20 <= eye_contact:
            eye_score = 3.0
        else:
            eye_score = 2.0
        
        # Combined score
        score = (eye_score * 0.4) + (posture_score * 0.4) + (min(gesture_freq / 2, 5) * 0.2)
        score = min(max(score, 0), 5)
        
        feedback_parts = []
        if eye_contact >= 60:
            feedback_parts.append("Good eye contact")
        else:
            feedback_parts.append("Maintain more eye contact with camera")
        
        if posture_score >= 4:
            feedback_parts.append("Professional posture")
        elif posture_score < 3:
            feedback_parts.append("Work on maintaining steady posture")
        
        return RubricScore(
            category="body_language",
            category_name=self.categories["body_language"]["name"],
            score=round(score, 1),
            weight=self.categories["body_language"]["weight"],
            feedback=". ".join(feedback_parts),
            evidence=[f"Eye contact: {eye_contact}%", f"Posture score: {posture_score}/5"]
        )
    
    def _score_time_utilization(self, timing_metrics: Optional[Dict]) -> RubricScore:
        """Score time utilization."""
        if not timing_metrics:
            return RubricScore(
                category="time_utilization",
                category_name=self.categories["time_utilization"]["name"],
                score=3.5,
                weight=self.categories["time_utilization"]["weight"],
                feedback="Timing metrics not available",
                evidence=[]
            )
        
        time_taken = timing_metrics.get("time_taken_seconds", 0)
        expected_time = timing_metrics.get("expected_time_seconds", 300)
        
        if expected_time == 0:
            return RubricScore(
                category="time_utilization",
                category_name=self.categories["time_utilization"]["name"],
                score=3.5,
                weight=self.categories["time_utilization"]["weight"],
                feedback="No expected time specified",
                evidence=[]
            )
        
        ratio = time_taken / expected_time
        
        # Score based on time ratio (ideal: 80-100% of expected time)
        if 0.8 <= ratio <= 1.0:
            score = 5.0
            feedback = "Excellent time management"
        elif 0.6 <= ratio <= 1.2:
            score = 4.0
            feedback = "Good time utilization"
        elif 0.4 <= ratio <= 1.5:
            score = 3.0
            feedback = "Could improve time management"
        elif ratio < 0.4:
            score = 2.0
            feedback = "Response was too brief"
        else:
            score = 2.0
            feedback = "Exceeded expected time significantly"
        
        return RubricScore(
            category="time_utilization",
            category_name=self.categories["time_utilization"]["name"],
            score=score,
            weight=self.categories["time_utilization"]["weight"],
            feedback=feedback,
            evidence=[f"Time taken: {time_taken}s", f"Expected: {expected_time}s", f"Ratio: {ratio:.1%}"]
        )
    
    def _identify_strengths_weaknesses(
        self,
        rubric_scores: List[RubricScore]
    ) -> tuple[List[str], List[str]]:
        """Identify top strengths and weaknesses from scores."""
        sorted_scores = sorted(rubric_scores, key=lambda x: x.score, reverse=True)
        
        strengths = []
        weaknesses = []
        
        for score in sorted_scores[:3]:  # Top 3
            if score.score >= 4.0:
                strengths.append(f"{score.category_name}: {score.feedback}")
        
        for score in sorted_scores[-3:]:  # Bottom 3
            if score.score < 3.5:
                weaknesses.append(f"{score.category_name}: {score.feedback}")
        
        return strengths, weaknesses
    
    def _calculate_confidence_index(
        self,
        rubric_scores: List[RubricScore],
        speech_metrics: Optional[Dict],
        language_metrics: Optional[Dict]
    ) -> float:
        """
        Calculate confidence index based on consistency of scores and signals.
        Higher = more confident in the evaluation accuracy.
        """
        scores = [s.score for s in rubric_scores]
        
        if not scores:
            return 0.5
        
        # Score consistency (lower variance = higher confidence)
        import statistics
        if len(scores) > 1:
            variance = statistics.variance(scores)
            consistency_factor = max(0, 1 - (variance / 5))
        else:
            consistency_factor = 0.5
        
        # Data completeness factor
        data_points = 0
        if speech_metrics:
            data_points += 1
        if language_metrics:
            data_points += 1
        completeness_factor = data_points / 2
        
        # Combine factors
        confidence = (consistency_factor * 0.6) + (completeness_factor * 0.4)
        
        return min(max(confidence, 0), 1)


# Module-level instance
rubric_scorer = RubricScorer()


def evaluate_response(**kwargs) -> EvaluationResult:
    """Convenience function for evaluation."""
    return rubric_scorer.evaluate(**kwargs)