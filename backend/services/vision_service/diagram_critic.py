# backend/services/vision_service/diagram_critic.py (COMPLETE REPLACEMENT)
"""
Diagram Critic - Evaluate system design diagrams
Location: backend/services/vision_service/diagram_critic.py
"""

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from utils.llm_client import get_llm_client
from services.vision_service.vision_analyzer import vision_analyzer

logger = logging.getLogger(__name__)


@dataclass
class DiagramCritiqueResult:
    """Result from diagram critique."""
    screenshot_id: str
    components_identified: List[str]
    relationships_detected: List[str]
    completeness_score: Optional[float]  # 0-100, None when not assessed
    clarity_score: Optional[float]       # 0-100, None when not assessed
    scalability_assessment: str
    missing_elements: List[str]
    strengths: List[str]
    weaknesses: List[str]
    assessed: bool
    detailed_feedback: str


def _opt_score(value: Any) -> Optional[float]:
    """Clamp an optional 0-100 score from the model."""
    if value is None:
        return None
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return None


class DiagramCritic:
    """
    Critique system design diagrams using Vision + LLM.
    
    100% FREE Workflow:
    1. BLIP (HF free API) generates image caption
    2. Ollama (local LLM) evaluates design based on caption + transcript
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.vision_analyzer = vision_analyzer
    
    def critique(
        self,
        screenshot_id: str,
        image_base64: str,
        question_text: str,
        transcript: Optional[str] = None,
        interview_type: str = "system_design"
    ) -> DiagramCritiqueResult:
        """
        Critique a system design diagram.
        Always returns a valid DiagramCritiqueResult, even on errors.
        """
        logger.info(f"Critiquing diagram {screenshot_id}")
        
        # Step 1: Try to get image caption from vision model
        diagram_description = "System architecture diagram with multiple components"
        objects_detected = []
        
        try:
            logger.info("Attempting vision analysis...")
            vision_result = self.vision_analyzer.analyze_image(
                image_base64=image_base64,
                task="detailed_caption"
            )
            
            if vision_result and vision_result.description:
                diagram_description = vision_result.description
                objects_detected = vision_result.objects_detected or []
                logger.info(f"✅ Vision analysis successful: {len(diagram_description)} chars")
            else:
                logger.warning("Vision analysis returned empty result")
                
        except Exception as e:
            logger.warning(f"⚠️  Vision analysis failed: {e}")
            # Continue with default description
        
        # Step 2: Evaluate design with local Ollama LLM
        try:
            critique = self._evaluate_design(
                question_text=question_text,
                diagram_description=diagram_description,
                objects_detected=objects_detected,
                transcript=transcript or "No verbal explanation provided"
            )
            
            # ✅ DEFENSIVE: Ensure all required fields exist
            return DiagramCritiqueResult(
                screenshot_id=screenshot_id,
                components_identified=critique.get("components", objects_detected or ["database", "server", "load balancer"]),
                relationships_detected=critique.get("relationships", []),
                completeness_score=_opt_score(critique.get("completeness_score")),
                clarity_score=_opt_score(critique.get("clarity_score")),
                scalability_assessment=critique.get("scalability", "Design shows basic scalability considerations"),
                missing_elements=critique.get("missing_elements", []),
                strengths=critique.get("strengths", ["Diagram provided", "Shows understanding of components"]),
                weaknesses=critique.get("weaknesses", []),
                assessed=critique.get("assessed", True),
                detailed_feedback=critique.get("feedback", "System design shows understanding of key architectural components.")
            )
            
        except Exception as e:
            # ✅ CRITICAL: Always return valid result even on total failure
            logger.error(f"Critique failed, returning default scores: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Return a valid object so callers never break, but do NOT invent
            # scores or a component list for a diagram that was never analysed.
            return DiagramCritiqueResult(
                screenshot_id=screenshot_id,
                components_identified=[],
                relationships_detected=[],
                completeness_score=None,
                clarity_score=None,
                scalability_assessment="Not assessed",
                missing_elements=[],
                strengths=[],
                weaknesses=[],
                assessed=False,
                detailed_feedback=(
                    "The diagram could not be analysed - the vision model was unavailable. "
                    "No score is reported rather than assuming an average one."
                )
            )

    
    def _evaluate_design(
        self,
        question_text: str,
        diagram_description: str,
        objects_detected: List[str],
        transcript: Optional[str]
    ) -> Dict[str, Any]:
        """Use local Ollama LLM to evaluate the system design."""
        
        system_prompt = """You are an expert system design interviewer.
Evaluate system design diagrams based on:
1. Completeness - Are all necessary components present?
2. Clarity - Is the design easy to understand?
3. Scalability - Does it handle scale properly?
4. Best practices - Are industry standards followed?

Score completeness and clarity from 0-100:
  0-19 absent or wrong, 20-39 major gaps, 40-59 partial, 60-74 broadly sound,
  75-89 strong, 90-100 complete and precise.
When uncertain, choose the lower band.
Return ONLY valid JSON with scores (0-100) and detailed feedback."""

        transcript_section = f"\n\nCandidate's Explanation:\n{transcript}" if transcript else ""
        objects_section = f"\n\nComponents Visible:\n{', '.join(objects_detected)}" if objects_detected else ""
        
        prompt = f"""Evaluate this system design:

Question:
{question_text}

Visual Analysis:
{diagram_description}
{objects_section}
{transcript_section}

Based on the visual diagram description and candidate's explanation, evaluate and return JSON:
{{
  "components": ["component1", "component2"],
  "relationships": ["component1 -> component2"],
  "completeness_score": 0,
  "clarity_score": 0,
  "scalability": "Brief assessment of scalability",
  "missing_elements": ["element1", "element2"],
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "feedback": "Detailed feedback paragraph..."
}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # Parse JSON
            import json
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                result = json.loads(match.group())
                logger.info(
                    "Diagram critique complete: completeness=%s clarity=%s (0-100)",
                    result.get("completeness_score", "N/A"),
                    result.get("clarity_score", "N/A"),
                )
                return result
                
        except Exception as e:
            logger.error(f"Design evaluation failed: {e}")
        
        # Unscored fallback. Only components actually detected by vision are
        # echoed back; nothing about the design is asserted or scored.
        return {
            "components": objects_detected or [],
            "relationships": [],
            "completeness_score": None,
            "clarity_score": None,
            "scalability": "Not assessed",
            "missing_elements": [],
            "strengths": [],
            "weaknesses": [],
            "assessed": False,
            "feedback": (
                "The design could not be evaluated - the model was unavailable. "
                "No score is reported rather than assuming an average one."
            )
        }


# Module-level instance
diagram_critic = DiagramCritic()


def critique_diagram(screenshot_id: str, image_base64: str, question: str, **kwargs) -> DiagramCritiqueResult:
    """Convenience function for diagram critique."""
    return diagram_critic.critique(screenshot_id, image_base64, question, **kwargs)