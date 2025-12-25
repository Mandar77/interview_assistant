"""
Question Generator - Generate interview questions using LLM
Location: backend/services/question_service/generator.py
"""

import uuid
import logging
import json
import re
from typing import List, Optional, Dict, Any

from models.schemas import (
    GeneratedQuestion,
    QuestionRequest,
    InterviewType,
    DifficultyLevel,
    SkillTag
)
from utils.llm_client import get_llm_client
from services.question_service.skill_parser import parse_job_description

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt Templates (inlined to avoid import issues)
# =============================================================================

QUESTION_GENERATOR_SYSTEM = """You are an expert technical interviewer who creates high-quality interview questions.
Your questions should:
1. Be clear, specific, and unambiguous
2. Test real-world applicable skills
3. Have measurable evaluation criteria
4. Be appropriate for the specified difficulty level
5. Include follow-up prompts to probe deeper understanding

IMPORTANT: You must respond ONLY with valid JSON. No markdown, no explanation, just JSON."""


TECHNICAL_QUESTION_PROMPT = """Generate {num_questions} technical interview questions for a {role} position.

Skills to test: {skills}
Difficulty: {difficulty}

Requirements:
- Mix of conceptual and practical questions
- Include follow-up questions to probe deeper
- Cover both breadth and depth of the skill
- Questions should reveal problem-solving approach

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
  "questions": [
    {{
      "id": "tech_1",
      "question": "Your detailed question here",
      "interview_type": "technical",
      "difficulty": "{difficulty}",
      "skill_tags": ["python", "oop"],
      "expected_duration_mins": 15,
      "evaluation_criteria": ["conceptual_clarity", "practical_knowledge", "depth"],
      "sample_answer_points": ["Key point 1", "Key point 2", "Advanced insight"],
      "follow_ups": ["How would this change if...?", "What are the trade-offs?"]
    }}
  ]
}}"""


OA_QUESTION_PROMPT = """Generate {num_questions} Online Assessment coding questions for a {role} position.

Skills to test: {skills}
Difficulty: {difficulty}

Requirements:
- Each question should be a self-contained coding problem
- Include clear input/output format
- Specify time and space complexity expectations

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
  "questions": [
    {{
      "id": "oa_1",
      "question": "Full problem statement with examples and constraints",
      "interview_type": "oa",
      "difficulty": "{difficulty}",
      "skill_tags": ["array", "algorithm"],
      "expected_duration_mins": 30,
      "evaluation_criteria": ["correctness", "time_complexity", "code_quality"],
      "sample_answer_points": ["Use specific approach", "Handle edge cases"]
    }}
  ]
}}"""


SYSTEM_DESIGN_PROMPT = """Generate {num_questions} system design interview questions for a {role} position.

Skills to test: {skills}
Difficulty: {difficulty}

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
  "questions": [
    {{
      "id": "sd_1",
      "question": "Design a system that... Include specific requirements and scale.",
      "interview_type": "system_design",
      "difficulty": "{difficulty}",
      "skill_tags": ["distributed_systems", "database", "caching"],
      "expected_duration_mins": 45,
      "evaluation_criteria": ["requirements_gathering", "high_level_design", "scalability", "trade_offs"],
      "sample_answer_points": ["Clarify requirements", "Estimate scale", "Design components"]
    }}
  ]
}}"""


BEHAVIORAL_QUESTION_PROMPT = """Generate {num_questions} behavioral interview questions for a {role} position.

Traits to assess: {skills}

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
  "questions": [
    {{
      "id": "beh_1",
      "question": "Tell me about a time when...",
      "interview_type": "behavioral",
      "difficulty": "medium",
      "skill_tags": ["leadership", "communication"],
      "expected_duration_mins": 10,
      "evaluation_criteria": ["situation_clarity", "action_ownership", "result_impact"],
      "sample_answer_points": ["Clear situation", "Specific actions", "Measurable results"]
    }}
  ]
}}"""


DIFFICULTY_CONTEXT = {
    "easy": "Focus on fundamental concepts. Entry-level appropriate.",
    "medium": "Combine 2-3 concepts. Mid-level appropriate.",
    "hard": "Complex multi-step problems. Senior-level appropriate.",
    "adaptive": "Start medium, include hints and harder follow-ups."
}


def get_prompt_for_type(interview_type: str) -> str:
    """Get the appropriate prompt template for an interview type."""
    prompts = {
        "oa": OA_QUESTION_PROMPT,
        "technical": TECHNICAL_QUESTION_PROMPT,
        "system_design": SYSTEM_DESIGN_PROMPT,
        "behavioral": BEHAVIORAL_QUESTION_PROMPT,
        "mixed": TECHNICAL_QUESTION_PROMPT
    }
    return prompts.get(interview_type, TECHNICAL_QUESTION_PROMPT)


def build_generation_prompt(
    interview_type: str,
    skills: list,
    difficulty: str,
    num_questions: int,
    role: str = "Software Engineer"
) -> str:
    """Build a complete prompt for question generation."""
    
    template = get_prompt_for_type(interview_type)
    difficulty_context = DIFFICULTY_CONTEXT.get(difficulty, DIFFICULTY_CONTEXT["medium"])
    
    skills_str = ", ".join(skills) if skills else "general programming"
    
    prompt = template.format(
        num_questions=num_questions,
        skills=skills_str,
        difficulty=difficulty,
        role=role
    )
    
    prompt = f"Difficulty level: {difficulty_context}\n\n{prompt}"
    
    return prompt


# =============================================================================
# Question Generator Class
# =============================================================================

class QuestionGenerator:
    """Generate interview questions based on job descriptions and parameters."""
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    def generate(self, request: QuestionRequest) -> List[GeneratedQuestion]:
        """
        Generate interview questions based on the request.
        
        Args:
            request: QuestionRequest with job description and parameters
            
        Returns:
            List of GeneratedQuestion objects
        """
        # Step 1: Parse job description to extract skills
        logger.info("Parsing job description for skills...")
        skills = parse_job_description(request.job_description)
        
        # Get top skills (by importance) or use focus skills if provided
        if request.focus_skills:
            skill_names = request.focus_skills
        else:
            skill_names = [s.skill for s in skills[:10]]
        
        logger.info(f"Using skills: {skill_names}")
        
        # Step 2: Build the generation prompt
        prompt = build_generation_prompt(
            interview_type=request.interview_type.value,
            skills=skill_names,
            difficulty=request.difficulty.value,
            num_questions=request.num_questions,
            role=self._extract_role(request.job_description)
        )
        
        # Step 3: Generate questions using LLM
        logger.info(f"Generating {request.num_questions} {request.interview_type.value} questions...")
        logger.debug(f"Prompt length: {len(prompt)} chars")
        logger.debug(f"Full prompt:\n{prompt[:500]}...")
        
        try:
            raw_response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=QUESTION_GENERATOR_SYSTEM,
                temperature=0.7,
                json_mode=False
            )
            
            logger.debug(f"Raw LLM response (first 500 chars): {raw_response[:500]}")
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                try:
                    response = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # Try to fix common JSON issues
                    json_str = json_match.group()
                    json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                    json_str = re.sub(r',\s*]', ']', json_str)
                    response = json.loads(json_str)
            else:
                logger.error(f"No JSON found in response")
                return self._get_fallback_questions(request)
            
            questions = self._parse_response(response, request.interview_type, request.difficulty)
            
            if not questions:
                logger.warning("No questions parsed from LLM response, using fallback")
                return self._get_fallback_questions(request)
                
            logger.info(f"Successfully generated {len(questions)} questions")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return self._get_fallback_questions(request)
        except Exception as e:
            logger.error(f"Question generation failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_fallback_questions(request)
    
    def generate_single(
        self,
        skill: str,
        interview_type: InterviewType,
        difficulty: DifficultyLevel
    ) -> GeneratedQuestion:
        """Generate a single question for a specific skill."""
        
        request = QuestionRequest(
            job_description=f"Looking for expertise in {skill}",
            interview_type=interview_type,
            difficulty=difficulty,
            num_questions=1,
            focus_skills=[skill]
        )
        
        questions = self.generate(request)
        return questions[0] if questions else None
    
    def generate_adaptive(
        self,
        job_description: str,
        previous_scores: Dict[str, float],
        target_categories: Optional[List[str]] = None
    ) -> List[GeneratedQuestion]:
        """Generate questions that adapt based on previous performance."""
        
        weak_areas = [cat for cat, score in previous_scores.items() if score < 3]
        avg_score = sum(previous_scores.values()) / len(previous_scores) if previous_scores else 2.5
        
        if avg_score < 2:
            difficulty = DifficultyLevel.EASY
        elif avg_score < 3.5:
            difficulty = DifficultyLevel.MEDIUM
        else:
            difficulty = DifficultyLevel.HARD
        
        focus_skills = target_categories if target_categories else weak_areas
        
        if not focus_skills:
            focus_skills = None
        
        request = QuestionRequest(
            job_description=job_description,
            interview_type=InterviewType.MIXED,
            difficulty=difficulty,
            num_questions=3,
            focus_skills=focus_skills
        )
        
        return self.generate(request)
    
    def _parse_response(
        self,
        response: Dict[str, Any],
        interview_type: InterviewType,
        difficulty: DifficultyLevel
    ) -> List[GeneratedQuestion]:
        """Parse LLM response into GeneratedQuestion objects."""
        
        questions = []
        raw_questions = response.get("questions", [])
        
        for i, q in enumerate(raw_questions):
            try:
                q_id = q.get("id", f"{interview_type.value}_{uuid.uuid4().hex[:8]}")
                
                q_type_str = q.get("interview_type", interview_type.value)
                try:
                    q_type = InterviewType(q_type_str)
                except ValueError:
                    q_type = interview_type
                
                q_diff_str = q.get("difficulty", difficulty.value)
                try:
                    q_diff = DifficultyLevel(q_diff_str)
                except ValueError:
                    q_diff = difficulty
                
                question = GeneratedQuestion(
                    id=q_id,
                    question=q.get("question", ""),
                    interview_type=q_type,
                    difficulty=q_diff,
                    skill_tags=q.get("skill_tags", []),
                    expected_duration_mins=q.get("expected_duration_mins", 15),
                    evaluation_criteria=q.get("evaluation_criteria", []),
                    sample_answer_points=q.get("sample_answer_points", [])
                )
                
                if question.question:
                    questions.append(question)
                    
            except Exception as e:
                logger.warning(f"Failed to parse question {i}: {e}")
                continue
        
        return questions
    
    def _extract_role(self, job_description: str) -> str:
        """Extract role title from job description."""
        lines = job_description.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 100:
                for keyword in ['engineer', 'developer', 'architect', 'manager', 'analyst']:
                    if keyword.lower() in line.lower():
                        return line
        return "Software Engineer"
    
    def _get_fallback_questions(self, request: QuestionRequest) -> List[GeneratedQuestion]:
        """Return fallback questions if generation fails."""
        
        fallback = {
            InterviewType.OA: GeneratedQuestion(
                id="fallback_oa_1",
                question="Given an array of integers, find two numbers that add up to a target sum. Return their indices.",
                interview_type=InterviewType.OA,
                difficulty=DifficultyLevel.MEDIUM,
                skill_tags=["array", "hash-map"],
                expected_duration_mins=20,
                evaluation_criteria=["correctness", "time_complexity", "edge_cases"],
                sample_answer_points=["Use hash map for O(n) solution", "Handle duplicates", "Consider empty array"]
            ),
            InterviewType.TECHNICAL: GeneratedQuestion(
                id="fallback_tech_1",
                question="Explain the difference between a process and a thread. When would you use one over the other?",
                interview_type=InterviewType.TECHNICAL,
                difficulty=DifficultyLevel.MEDIUM,
                skill_tags=["operating-systems", "concurrency"],
                expected_duration_mins=10,
                evaluation_criteria=["conceptual_clarity", "practical_examples", "trade_offs"],
                sample_answer_points=["Memory isolation", "Context switching cost", "Use cases for each"]
            ),
            InterviewType.SYSTEM_DESIGN: GeneratedQuestion(
                id="fallback_sd_1",
                question="Design a URL shortening service like bit.ly. Consider scalability, uniqueness, and analytics.",
                interview_type=InterviewType.SYSTEM_DESIGN,
                difficulty=DifficultyLevel.MEDIUM,
                skill_tags=["system-design", "distributed-systems", "database"],
                expected_duration_mins=45,
                evaluation_criteria=["requirements", "high_level_design", "scalability", "trade_offs"],
                sample_answer_points=["Base62 encoding", "Database choice", "Caching strategy", "Analytics pipeline"]
            ),
            InterviewType.BEHAVIORAL: GeneratedQuestion(
                id="fallback_beh_1",
                question="Tell me about a time when you had to deal with a difficult team member. How did you handle it?",
                interview_type=InterviewType.BEHAVIORAL,
                difficulty=DifficultyLevel.MEDIUM,
                skill_tags=["teamwork", "conflict-resolution"],
                expected_duration_mins=10,
                evaluation_criteria=["situation_clarity", "action_ownership", "result", "learning"],
                sample_answer_points=["Specific situation", "Direct communication", "Positive outcome", "Lesson learned"]
            ),
        }
        
        fallback[InterviewType.MIXED] = fallback[InterviewType.TECHNICAL]
        
        base_question = fallback.get(request.interview_type, fallback[InterviewType.TECHNICAL])
        return [base_question]


# Module-level instance
question_generator = QuestionGenerator()


def generate_questions(request: QuestionRequest) -> List[GeneratedQuestion]:
    """Convenience function for generating questions."""
    return question_generator.generate(request)