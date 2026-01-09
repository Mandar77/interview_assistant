# backend/services/code_execution_service/correctness_evaluator.py
"""
Code Correctness Evaluator - Score code based on test results and trajectory
Location: backend/services/code_execution_service/correctness_evaluator.py
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from utils.llm_client import get_llm_client
from services.code_execution_service.complexity_analyzer import complexity_analyzer

logger = logging.getLogger(__name__)


@dataclass
class CodeEvaluationResult:
    """Complete code evaluation result."""
    correctness_score: float  # 0-5 scale
    code_quality_score: float  # 0-5 scale
    complexity_score: float  # 0-5 scale
    overall_score: float  # 0-5 scale
    passed_tests: int
    total_tests: int
    feedback: str
    strengths: List[str]
    weaknesses: List[str]
    time_complexity: str
    space_complexity: str
    is_optimal: bool


class CodeCorrectnessEvaluator:
    """
    Evaluate code correctness with partial credit for incomplete solutions.
    Considers test results, code quality, complexity, and trajectory.
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    def evaluate(
        self,
        code: str,
        language: str,
        problem_description: str,
        test_results: Dict[str, Any],
        complexity_analysis: Optional[Dict] = None
    ) -> CodeEvaluationResult:
        """
        Evaluate code comprehensively.
        
        Args:
            code: Source code
            language: Programming language
            problem_description: Problem statement
            test_results: Results from test case execution
            complexity_analysis: Optional complexity analysis
            
        Returns:
            Complete evaluation with scores and feedback
        """
        logger.info("Evaluating code correctness and quality")
        
        # 1. Correctness score (based on test results)
        correctness_score = self._score_correctness(test_results, code, problem_description)
        
        # 2. Code quality score (based on LLM evaluation)
        quality_score = self._score_code_quality(code, language)
        
        # 3. Complexity score
        if not complexity_analysis:
            complexity_analysis = complexity_analyzer.analyze(code, language, problem_description)
        complexity_score = self._score_complexity(complexity_analysis)
        
        # 4. Overall score (weighted average)
        overall_score = (
            correctness_score * 0.5 +  # Correctness is most important
            quality_score * 0.3 +
            complexity_score * 0.2
        )
        
        # 5. Generate feedback
        feedback = self._generate_feedback(
            correctness_score,
            quality_score,
            complexity_score,
            test_results,
            complexity_analysis
        )
        
        # 6. Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(
            correctness_score,
            quality_score,
            complexity_score,
            test_results,
            complexity_analysis
        )
        
        return CodeEvaluationResult(
            correctness_score=round(correctness_score, 1),
            code_quality_score=round(quality_score, 1),
            complexity_score=round(complexity_score, 1),
            overall_score=round(overall_score, 1),
            passed_tests=test_results.get("passed", 0),
            total_tests=test_results.get("total_tests", 0),
            feedback=feedback,
            strengths=strengths,
            weaknesses=weaknesses,
            time_complexity=complexity_analysis.time_complexity if hasattr(complexity_analysis, 'time_complexity') else "Unknown",
            space_complexity=complexity_analysis.space_complexity if hasattr(complexity_analysis, 'space_complexity') else "Unknown",
            is_optimal=complexity_analysis.is_optimal if hasattr(complexity_analysis, 'is_optimal') else False
        )
    
    def _score_correctness(
        self,
        test_results: Dict[str, Any],
        code: str,
        problem: str
    ) -> float:
        """
        Score correctness with partial credit.
        Even if tests fail, give credit for correct approach.
        """
        passed = test_results.get("passed", 0)
        total = test_results.get("total_tests", 1)
        errors = test_results.get("errors", 0)
        
        # Base score from test results
        pass_rate = passed / total if total > 0 else 0
        base_score = pass_rate * 5
        
        # If all tests passed, full credit
        if passed == total:
            return 5.0
        
        # If compilation/runtime errors, check if approach is correct
        if errors > 0 or passed < total * 0.5:
            # Use LLM to assess if approach is on the right track
            approach_score = self._assess_approach(code, problem)
            # Blend test score with approach score (favor tests more)
            return (base_score * 0.7) + (approach_score * 0.3)
        
        return base_score
    
    def _assess_approach(self, code: str, problem: str) -> float:
        """
        Use LLM to assess if the solution approach is correct,
        even if implementation has bugs.
        """
        system_prompt = """You are a coding interview expert.
Assess if the candidate's approach to solving the problem is fundamentally correct,
even if there are implementation bugs or edge case issues.
Return a score from 0-5 based on approach quality."""

        prompt = f"""Problem:
{problem}

Candidate's Code:
```
{code}
```

Is the algorithmic approach fundamentally correct? 
Score from 0-5:
- 0: Completely wrong approach
- 1: Very flawed approach
- 2: Some correct ideas but major issues
- 3: Decent approach with implementation gaps
- 4: Good approach, minor bugs
- 5: Excellent approach

Return JSON:
{{"approach_score": 3.5, "reasoning": "Brief explanation"}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            import json
            import re
            match = re.search(r'\{[\s\S]*?\}', response)
            if match:
                result = json.loads(match.group())
                return float(result.get("approach_score", 2.5))
                
        except Exception as e:
            logger.error(f"Approach assessment failed: {e}")
        
        return 2.5  # Default middle score
    
    def _score_code_quality(self, code: str, language: str) -> float:
        """Score code quality (readability, style, best practices)."""
        
        system_prompt = """You are a code review expert.
Evaluate code quality based on:
- Readability and clarity
- Proper naming conventions
- Code structure and organization
- Use of language best practices
- Comments (if needed)

Score from 0-5."""

        prompt = f"""Evaluate the quality of this {language} code:
```{language}
{code}
```

Return JSON:
{{"quality_score": 4.0, "feedback": "Brief feedback"}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            import json
            import re
            match = re.search(r'\{[\s\S]*?\}', response)
            if match:
                result = json.loads(match.group())
                return float(result.get("quality_score", 3.0))
                
        except Exception as e:
            logger.error(f"Quality scoring failed: {e}")
        
        return 3.0
    
    def _score_complexity(self, complexity_analysis: Any) -> float:
        """Score based on algorithmic complexity."""
        if hasattr(complexity_analysis, 'is_optimal') and complexity_analysis.is_optimal:
            return 5.0
        
        # Parse time complexity and score accordingly
        time_c = complexity_analysis.time_complexity if hasattr(complexity_analysis, 'time_complexity') else "O(n)"
        
        complexity_scores = {
            "O(1)": 5.0,
            "O(log n)": 5.0,
            "O(n)": 4.5,
            "O(n log n)": 4.0,
            "O(n^2)": 3.0,
            "O(n^3)": 2.0,
            "O(2^n)": 1.0,
        }
        
        for pattern, score in complexity_scores.items():
            if pattern in time_c:
                return score
        
        return 3.0  # Default
    
    def _generate_feedback(
        self,
        correctness: float,
        quality: float,
        complexity: float,
        test_results: Dict,
        complexity_analysis: Any
    ) -> str:
        """Generate comprehensive feedback."""
        feedback_parts = []
        
        # Correctness feedback
        passed = test_results.get("passed", 0)
        total = test_results.get("total_tests", 0)
        if passed == total:
            feedback_parts.append(f"✓ All {total} test cases passed!")
        else:
            feedback_parts.append(f"✗ Passed {passed}/{total} test cases.")
        
        # Quality feedback
        if quality >= 4:
            feedback_parts.append("Code quality is good with clear structure.")
        elif quality < 3:
            feedback_parts.append("Code quality could be improved with better naming and structure.")
        
        # Complexity feedback
        if hasattr(complexity_analysis, 'is_optimal'):
            if complexity_analysis.is_optimal:
                feedback_parts.append(f"Complexity is optimal: {complexity_analysis.time_complexity}")
            else:
                feedback_parts.append(f"Current complexity: {complexity_analysis.time_complexity}. Can be optimized.")
        
        return " ".join(feedback_parts)
    
    def _identify_strengths_weaknesses(
        self,
        correctness: float,
        quality: float,
        complexity: float,
        test_results: Dict,
        complexity_analysis: Any
    ) -> tuple[List[str], List[str]]:
        """Identify strengths and weaknesses."""
        strengths = []
        weaknesses = []
        
        if correctness >= 4.5:
            strengths.append("Solution is correct for all test cases")
        elif correctness < 3:
            weaknesses.append("Solution fails several test cases")
        
        if quality >= 4:
            strengths.append("Clean, readable code")
        elif quality < 3:
            weaknesses.append("Code readability could be improved")
        
        if complexity >= 4:
            strengths.append("Efficient algorithmic approach")
        elif complexity < 3:
            weaknesses.append("Algorithm could be more efficient")
        
        return strengths, weaknesses


# Module-level instance
code_evaluator = CodeCorrectnessEvaluator()


def evaluate_code(code: str, language: str, problem: str, test_results: Dict) -> CodeEvaluationResult:
    """Convenience function for code evaluation."""
    return code_evaluator.evaluate(code, language, problem, test_results)