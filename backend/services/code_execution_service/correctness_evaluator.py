# backend/services/code_execution_service/correctness_evaluator.py
"""
Code Correctness Evaluator - Score code based on test results and trajectory
Location: backend/services/code_execution_service/correctness_evaluator.py
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from utils.llm_client import extract_json_object, get_llm_client
from services.code_execution_service.complexity_analyzer import complexity_analyzer

logger = logging.getLogger(__name__)


@dataclass
class CodeEvaluationResult:
    """
    Code evaluation result. Three independent 0-100 scores, no blended overall.

    Correctness is the critical axis and is driven by the test suite. Quality and
    complexity are reported next to it and never raise it - clean, elegant code
    that fails the tests is still wrong code.
    """
    correctness_score: float            # 0-100, test-driven
    code_quality_score: Optional[float]  # 0-100, None when not assessed
    complexity_score: Optional[float]    # 0-100, None when not assessed
    test_pass_rate: float                # 0-100, raw share of tests passed
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
        
        # No combined score: the three axes are reported side by side so that
        # quality and complexity cannot compensate for failing tests.

        # 4. Generate feedback
        feedback = self._generate_feedback(
            correctness_score,
            quality_score,
            complexity_score,
            test_results,
            complexity_analysis
        )
        
        # 5. Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(
            correctness_score,
            quality_score,
            complexity_score,
            test_results,
            complexity_analysis
        )
        
        passed = test_results.get("passed", 0)
        total = test_results.get("total_tests", 0)

        return CodeEvaluationResult(
            correctness_score=round(correctness_score, 1),
            code_quality_score=round(quality_score, 1) if quality_score is not None else None,
            complexity_score=round(complexity_score, 1) if complexity_score is not None else None,
            test_pass_rate=round((passed / total) * 100.0, 1) if total else 0.0,
            passed_tests=passed,
            total_tests=total,
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
        Score correctness 0-100, driven by the test suite.

        Partial credit for a sound approach exists but is deliberately small and
        capped: a submission that passes no tests cannot be called correct no
        matter how plausible the code looks.
        """
        passed = test_results.get("passed", 0)
        total = test_results.get("total_tests", 1)
        errors = test_results.get("errors", 0)

        pass_rate = passed / total if total > 0 else 0
        base_score = pass_rate * 100.0

        # All tests passed - full credit.
        if total > 0 and passed == total:
            return 100.0

        # Struggling submission: allow a limited approach credit on top.
        if errors > 0 or passed < total * 0.5:
            approach_score = self._assess_approach(code, problem)
            if approach_score is None:
                return base_score
            blended = (base_score * 0.85) + (approach_score * 0.15)
            if passed == 0:
                # Nothing works: approach credit alone tops out well short of
                # a passing correctness score.
                return min(blended, 35.0)
            return blended

        return base_score
    
    def _assess_approach(self, code: str, problem: str) -> Optional[float]:
        """
        Use LLM to assess if the solution approach is correct,
        even if implementation has bugs.

        Returns None when the model is unavailable, so the caller falls back to
        the test results rather than to an invented score.
        """
        system_prompt = """You are a coding interview expert.
Assess if the candidate's approach to solving the problem is fundamentally correct,
even if there are implementation bugs or edge case issues.
Return a score from 0-100 based on approach quality. When uncertain, score lower."""

        prompt = f"""Problem:
{problem}

Candidate's Code:
```
{code}
```

Is the algorithmic approach fundamentally correct?
Score from 0-100:
- 0-19: Completely wrong approach
- 20-39: Very flawed approach
- 40-59: Some correct ideas but major issues
- 60-74: Decent approach with implementation gaps
- 75-89: Good approach, minor bugs
- 90-100: Excellent approach

Return JSON:
{{"approach_score": 0, "reasoning": "Brief explanation"}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                # Without JSON mode the model answers in prose and the score is
                # lost entirely; see _score_code_quality for the same fix.
                json_mode=True,
            )

            result = extract_json_object(response)
            if result:
                raw = result.get("approach_score")
                if raw is not None:
                    return max(0.0, min(100.0, float(raw)))
            logger.warning("Approach assessment returned no parseable JSON")

        except Exception as e:
            logger.error(f"Approach assessment failed: {e}")

        return None  # Unknown - caller falls back to the test results
    
    def _score_code_quality(self, code: str, language: str) -> Optional[float]:
        """
        Score code quality 0-100 (readability, style, best practices).

        Returns None when the model is unavailable - quality is reported as
        "not assessed" rather than as an average-looking number.
        """
        
        system_prompt = """You are a code review expert.
Evaluate code quality based on:
- Readability and clarity
- Proper naming conventions
- Code structure and organization
- Use of language best practices
- Comments (if needed)

Score from 0-100."""

        prompt = f"""Evaluate the quality of this {language} code:
```{language}
{code}
```

Return JSON:
{{"quality_score": 0, "feedback": "Brief feedback"}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                # Local models answer this in markdown prose unless JSON mode is
                # on, which silently cost every submission its quality score.
                json_mode=True,
            )

            result = extract_json_object(response)
            if result:
                raw = result.get("quality_score")
                if raw is not None:
                    return max(0.0, min(100.0, float(raw)))
            logger.warning("Quality scoring returned no parseable JSON")

        except Exception as e:
            logger.error(f"Quality scoring failed: {e}")

        return None
    
    def _score_complexity(self, complexity_analysis: Any) -> float:
        """Score algorithmic complexity 0-100."""
        if hasattr(complexity_analysis, 'is_optimal') and complexity_analysis.is_optimal:
            return 100.0
        
        # Parse time complexity and score accordingly
        time_c = complexity_analysis.time_complexity if hasattr(complexity_analysis, 'time_complexity') else "O(n)"
        
        complexity_scores = {
            "O(1)": 100.0,
            "O(log n)": 100.0,
            "O(n)": 90.0,
            "O(n log n)": 80.0,
            "O(n^2)": 60.0,
            "O(n^3)": 40.0,
            "O(2^n)": 20.0,
        }

        for pattern, score in complexity_scores.items():
            if pattern in time_c:
                return score

        return 60.0  # Default
    
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
        if quality is None:
            feedback_parts.append("Code quality was not assessed.")
        elif quality >= 75:
            feedback_parts.append("Code quality is good with clear structure.")
        elif quality < 60:
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
        quality: Optional[float],
        complexity: Optional[float],
        test_results: Dict,
        complexity_analysis: Any
    ) -> tuple[List[str], List[str]]:
        """Identify strengths and weaknesses on the 0-100 scale."""
        strengths = []
        weaknesses = []

        if correctness >= 90:
            strengths.append("Solution is correct for all test cases")
        elif correctness < 60:
            weaknesses.append("Solution fails several test cases")

        if quality is not None:
            if quality >= 75:
                strengths.append("Clean, readable code")
            elif quality < 60:
                weaknesses.append("Code readability could be improved")

        if complexity is not None:
            if complexity >= 80:
                strengths.append("Efficient algorithmic approach")
            elif complexity < 60:
                weaknesses.append("Algorithm could be more efficient")

        return strengths, weaknesses


# Module-level instance
code_evaluator = CodeCorrectnessEvaluator()


def evaluate_code(code: str, language: str, problem: str, test_results: Dict) -> CodeEvaluationResult:
    """Convenience function for code evaluation."""
    return code_evaluator.evaluate(code, language, problem, test_results)