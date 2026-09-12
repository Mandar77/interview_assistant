# backend/services/question_service/generator.py (UPDATE existing file)

"""
Question Generator - Generate interview questions using LLM
Location: backend/services/question_service/generator.py
"""

import uuid
import logging
from typing import List, Optional, Dict, Any

from models.schemas import (
    GeneratedQuestion,
    QuestionRequest,
    InterviewType,
    DifficultyLevel,
    TestCase  # ✅ NEW: Import TestCase
)
from utils.llm_client import extract_json_object, get_llm_client
from services.question_service.skill_parser import parse_job_description

logger = logging.getLogger(__name__)

# Below this 0-100 score a category counts as a weak area worth drilling.
WEAK_AREA_THRESHOLD = 60.0


# =============================================================================
# Prompt Templates (UPDATED)
# =============================================================================

# JSON schema handed to Ollama's structured-output mode. This is what stops the
# model emitting raw newlines inside starter_code strings, which made OA
# generation fail 100% of the time and silently serve the hardcoded fallback.
def build_question_schema(interview_type: str) -> Dict[str, Any]:
    """JSON schema for a question batch; OA additionally needs tests + starters."""
    question_props: Dict[str, Any] = {
        "question": {"type": "string"},
        "skill_tags": {"type": "array", "items": {"type": "string"}},
        "expected_duration_mins": {"type": "integer"},
        "evaluation_criteria": {"type": "array", "items": {"type": "string"}},
        "sample_answer_points": {"type": "array", "items": {"type": "string"}},
    }
    required = ["question", "skill_tags", "expected_duration_mins", "evaluation_criteria"]

    if interview_type == "oa":
        question_props["test_cases"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "input": {"type": "string"},
                    "expected_output": {"type": "string"},
                    "description": {"type": "string"},
                    "is_hidden": {"type": "boolean"},
                },
                "required": ["input", "expected_output"],
            },
        }
        question_props["starter_code"] = {
            "type": "object",
            "properties": {
                "python": {"type": "string"},
                "java": {"type": "string"},
                "cpp": {"type": "string"},
            },
            "required": ["python"],
        }
        required += ["test_cases", "starter_code"]

    return {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": question_props,
                    "required": required,
                },
            }
        },
        "required": ["questions"],
    }


# How much raw job-description text to ground on. Skill keywords alone give the
# model "PyTorch, Kafka" but not "200 drones streaming 4K" or "40k TPS", so
# questions come out skill-shaped rather than scenario-specific.
JD_EXCERPT_CHARS = 1200


QUESTION_GENERATOR_SYSTEM = """You are an expert technical interviewer who creates high-quality interview questions.
Your questions should:
1. Be clear, specific, and unambiguous
2. Test real-world applicable skills
3. Have measurable evaluation criteria
4. Be appropriate for the specified difficulty level
5. Include follow-up prompts to probe deeper understanding

Ground every question in the specific job description you are given: reference
its real systems, scale numbers and domain. A question that could have been
asked of any candidate in any company is a failed question.

Never reuse the wording, skills or examples shown in the format sample - it
describes the shape of the response only, never its content.

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


# ✅ UPDATED: OA prompt with test cases
OA_QUESTION_PROMPT = """Generate {num_questions} Online Assessment coding questions for a {role} position.

Skills to test: {skills}
Difficulty: {difficulty}

Requirements:
- Each question should be a self-contained coding problem
- Include clear input/output format
- Specify time and space complexity expectations
- Provide 3-5 test cases (mix of basic, edge cases, and hidden)
- Include starter code templates for Python, Java, C++

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
      "sample_answer_points": ["Use specific approach", "Handle edge cases"],
      "test_cases": [
        {{
          "input": "5\\n1 2 3 4 5",
          "expected_output": "15",
          "description": "Basic test case",
          "is_hidden": false
        }},
        {{
          "input": "0\\n",
          "expected_output": "0",
          "description": "Edge case: empty array",
          "is_hidden": true
        }}
      ],
      "starter_code": {{
        "python": "def solve(arr):\\n    # Your code here\\n    pass",
        "java": "public static int solve(int[] arr) {{\\n    // Your code here\\n    return 0;\\n}}",
        "cpp": "int solve(vector<int>& arr) {{\\n    // Your code here\\n    return 0;\\n}}"
      }}
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
    role: str = "Software Engineer",
    job_description: str = "",
    avoid_questions: Optional[List[str]] = None,
) -> str:
    """
    Build a complete prompt for question generation.

    `job_description` is included verbatim (truncated). Extracted skill names
    carry some signal, but they strip the scale, domain and constraints that
    make a question specific to this role rather than generic.
    """
    template = get_prompt_for_type(interview_type)
    difficulty_context = DIFFICULTY_CONTEXT.get(difficulty, DIFFICULTY_CONTEXT["medium"])

    skills_str = ", ".join(skills) if skills else "general programming"

    prompt = template.format(
        num_questions=num_questions,
        skills=skills_str,
        difficulty=difficulty,
        role=role
    )

    sections = [f"Difficulty level: {difficulty_context}"]

    jd = (job_description or "").strip()
    if jd:
        excerpt = jd[:JD_EXCERPT_CHARS]
        sections.append(
            "JOB DESCRIPTION (ground your questions in these specifics — the "
            "systems, the scale, the domain):\n"
            f"\"\"\"\n{excerpt}\n\"\"\""
        )

    sections.append(prompt)

    if avoid_questions:
        already = "\n".join(f"- {q[:160]}" for q in avoid_questions[:8])
        sections.append(
            "Do NOT repeat or paraphrase any of these already-asked questions:\n"
            f"{already}"
        )

    return "\n\n".join(sections)


# =============================================================================
# Question Generator Class
# =============================================================================

class QuestionGenerator:
    """Generate interview questions based on job descriptions and parameters."""
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    def generate(
        self,
        request: QuestionRequest,
        avoid_questions: Optional[List[str]] = None,
    ) -> List[GeneratedQuestion]:
        """
        Generate interview questions based on the request.

        Args:
            request: QuestionRequest with job description and parameters
            avoid_questions: question texts already asked this session, so the
                model is told not to repeat itself

        Returns:
            List of GeneratedQuestion objects. Questions carry is_fallback=True
            when generation failed and the canned question was substituted.
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
            role=self._extract_role(request.job_description),
            job_description=request.job_description,
            avoid_questions=avoid_questions,
        )
        
        # Step 3: Generate questions using LLM
        logger.info(f"Generating {request.num_questions} {request.interview_type.value} questions...")
        logger.debug(f"Prompt length: {len(prompt)} chars")
        logger.debug(f"Full prompt:\n{prompt[:500]}...")
        
        # Schema-constrained output. Free-form JSON from a small local model was
        # malformed ~25% of the time for technical questions and 100% of the
        # time for OA (raw newlines inside starter_code), and every failure fell
        # through to the same canned question - which is what made generated
        # interviews feel repetitive and generic.
        schema = build_question_schema(request.interview_type.value)

        last_error: Optional[str] = None
        for attempt in (1, 2):
            try:
                raw_response = self.llm_client.generate(
                    prompt=prompt,
                    system_prompt=QUESTION_GENERATOR_SYSTEM,
                    # Enough headroom for an OA batch with tests + starter code.
                    max_tokens=4096,
                    # Nudge variety up on the retry rather than resampling the
                    # same near-deterministic answer.
                    temperature=0.7 if attempt == 1 else 0.9,
                    json_schema=schema,
                )
            except Exception as e:
                logger.error(f"Question generation call failed: {type(e).__name__}: {e}")
                last_error = str(e)
                continue

            response = extract_json_object(raw_response)
            if response is None:
                last_error = f"unparseable response: {(raw_response or '')[:160]}"
                logger.warning(
                    "Question generation returned unparseable JSON (attempt %d/2)", attempt
                )
                continue

            questions = self._parse_response(
                response, request.interview_type, request.difficulty
            )
            if not questions:
                last_error = "no questions in parsed response"
                logger.warning(
                    "No questions parsed from LLM response (attempt %d/2)", attempt
                )
                continue

            logger.info(f"Successfully generated {len(questions)} questions")
            return questions

        logger.error(
            "Question generation failed after 2 attempts, serving fallback. Last error: %s",
            last_error,
        )
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
        target_categories: Optional[List[str]] = None,
        asked_questions: Optional[List[str]] = None,
    ) -> List[GeneratedQuestion]:
        """
        Generate questions that adapt based on previous performance.

        `previous_scores` maps an engine or skill id to a 0-100 score. Pass
        the technical engine rather than a blend - difficulty should track
        what the candidate got right, not how well they spoke.
        """
        weak_areas = [cat for cat, score in previous_scores.items() if score < WEAK_AREA_THRESHOLD]
        avg_score = sum(previous_scores.values()) / len(previous_scores) if previous_scores else 50.0

        if avg_score < 40:
            difficulty = DifficultyLevel.EASY
        elif avg_score < 70:
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

        # Adaptive rounds follow earlier ones, so pass what has already been
        # asked - otherwise the model drifts back to the same few questions for
        # whichever skills it considers weak.
        return self.generate(request, avoid_questions=asked_questions)
    
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
                
                # ✅ NEW: Parse test cases if present
                test_cases = None
                if "test_cases" in q and q["test_cases"]:
                    test_cases = [
                        TestCase(
                            input=tc.get("input", ""),
                            expected_output=tc.get("expected_output", ""),
                            description=tc.get("description"),
                            is_hidden=tc.get("is_hidden", False)
                        )
                        for tc in q["test_cases"]
                    ]
                
                question = GeneratedQuestion(
                    id=q_id,
                    question=q.get("question", ""),
                    interview_type=q_type,
                    difficulty=q_diff,
                    skill_tags=q.get("skill_tags", []),
                    expected_duration_mins=q.get("expected_duration_mins", 15),
                    evaluation_criteria=q.get("evaluation_criteria", []),
                    sample_answer_points=q.get("sample_answer_points", []),
                    test_cases=test_cases,  # ✅ NEW
                    starter_code=q.get("starter_code")  # ✅ NEW
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
        
        # ✅ UPDATED: Add test cases to fallback OA question
        fallback = {
            InterviewType.OA: GeneratedQuestion(
                id="fallback_oa_1",
                question="""Given an array of integers, find two numbers that add up to a target sum. Return their indices.

Example:
Input: nums = [2, 7, 11, 15], target = 9
Output: [0, 1]
Explanation: nums[0] + nums[1] = 2 + 7 = 9

Constraints:
- 2 ≤ nums.length ≤ 10^4
- -10^9 ≤ nums[i] ≤ 10^9
- -10^9 ≤ target ≤ 10^9
- Only one valid answer exists

Input Format:
- First line: space-separated integers (array)
- Second line: target sum

Output Format:
- Space-separated indices""",
                interview_type=InterviewType.OA,
                difficulty=DifficultyLevel.MEDIUM,
                skill_tags=["array", "hash-map"],
                expected_duration_mins=20,
                evaluation_criteria=["correctness", "time_complexity", "edge_cases"],
                sample_answer_points=["Use hash map for O(n) solution", "Handle duplicates", "Consider empty array"],
                test_cases=[
                    TestCase(
                        input="2 7 11 15\n9",
                        expected_output="0 1",
                        description="Basic test case",
                        is_hidden=False
                    ),
                    TestCase(
                        input="3 2 4\n6",
                        expected_output="1 2",
                        description="Different indices",
                        is_hidden=False
                    ),
                    TestCase(
                        input="3 3\n6",
                        expected_output="0 1",
                        description="Same number twice",
                        is_hidden=True
                    ),
                ],
                starter_code={
                    "python": """def two_sum(nums, target):
    # Your code here
    pass

# Read input
nums = list(map(int, input().split()))
target = int(input())
result = two_sum(nums, target)
print(' '.join(map(str, result)))""",
                    "java": """import java.util.*;

public class Solution {
    public static int[] twoSum(int[] nums, int target) {
        // Your code here
        return new int[]{0, 0};
    }
    
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String[] input = sc.nextLine().split(" ");
        int[] nums = Arrays.stream(input).mapToInt(Integer::parseInt).toArray();
        int target = sc.nextInt();
        int[] result = twoSum(nums, target);
        System.out.println(result[0] + " " + result[1]);
    }
}""",
                    "cpp": """#include <iostream>
#include <vector>
#include <sstream>
using namespace std;

vector<int> twoSum(vector<int>& nums, int target) {
    // Your code here
    return {0, 0};
}

int main() {
    string line;
    getline(cin, line);
    istringstream iss(line);
    vector<int> nums;
    int num;
    while (iss >> num) nums.push_back(num);
    
    int target;
    cin >> target;
    
    vector<int> result = twoSum(nums, target);
    cout << result[0] << " " << result[1] << endl;
    return 0;
}"""
                }
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
        # Mark it. Previously this was indistinguishable from a real question, so
        # a failed generation looked to the candidate like a deliberately bland
        # question rather than an outage.
        base_question.is_fallback = True
        return [base_question]


# Module-level instance
question_generator = QuestionGenerator()


def generate_questions(request: QuestionRequest) -> List[GeneratedQuestion]:
    """Convenience function for generating questions."""
    return question_generator.generate(request)