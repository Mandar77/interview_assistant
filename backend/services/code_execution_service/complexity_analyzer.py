# backend/services/code_execution_service/complexity_analyzer.py
"""
Complexity Analyzer - Estimate time and space complexity using LLM
Location: backend/services/code_execution_service/complexity_analyzer.py
"""

import re
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class ComplexityAnalysis:
    """Complexity analysis result."""
    time_complexity: str  # O(n), O(n log n), etc.
    space_complexity: str
    explanation: str
    is_optimal: bool
    optimal_complexity: Optional[str] = None
    improvement_suggestions: list = None


class ComplexityAnalyzer:
    """
    Analyze algorithmic complexity of code using LLM.
    Estimates Big-O for time and space complexity.
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    def analyze(
        self,
        code: str,
        language: str,
        problem_description: Optional[str] = None
    ) -> ComplexityAnalysis:
        """
        Analyze time and space complexity of code.
        
        Args:
            code: Source code to analyze
            language: Programming language
            problem_description: Optional problem context
            
        Returns:
            ComplexityAnalysis with Big-O estimates
        """
        logger.info(f"Analyzing complexity for {language} code")
        
        system_prompt = """You are an expert in algorithm analysis and Big-O complexity.
Analyze code and provide accurate time and space complexity estimates.
Be specific about the complexity class (constant, logarithmic, linear, linearithmic, quadratic, cubic, exponential).
Return ONLY valid JSON."""

        problem_context = f"\nProblem: {problem_description}" if problem_description else ""
        
        prompt = f"""Analyze the time and space complexity of this code:
{problem_context}

Language: {language}
Code:
```{language}
{code}
```

Analyze:
1. Time complexity (worst case)
2. Space complexity (auxiliary space, not counting input)
3. Whether this is optimal for the problem
4. Suggestions for improvement (if not optimal)

Return JSON:
{{
  "time_complexity": "O(n)",
  "space_complexity": "O(1)",
  "explanation": "Detailed analysis of why...",
  "is_optimal": true,
  "optimal_complexity": "O(n)",
  "improvement_suggestions": ["Suggestion 1", "Suggestion 2"]
}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )
            
            # Parse JSON
            import json
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                result = json.loads(match.group())
                
                return ComplexityAnalysis(
                    time_complexity=result.get("time_complexity", "O(n)"),
                    space_complexity=result.get("space_complexity", "O(1)"),
                    explanation=result.get("explanation", ""),
                    is_optimal=result.get("is_optimal", True),
                    optimal_complexity=result.get("optimal_complexity"),
                    improvement_suggestions=result.get("improvement_suggestions", [])
                )
                
        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Return default analysis on failure
        return ComplexityAnalysis(
            time_complexity="Unknown",
            space_complexity="Unknown",
            explanation="Unable to analyze complexity",
            is_optimal=False
        )
    
    def compare_complexities(self, c1: str, c2: str) -> str:
        """
        Compare two complexity notations.
        Returns: 'better', 'worse', 'same', 'incomparable'
        """
        # Complexity ordering (lower index = better)
        complexity_order = [
            "O(1)",
            "O(log n)",
            "O(sqrt(n))",
            "O(n)",
            "O(n log n)",
            "O(n^2)",
            "O(n^3)",
            "O(2^n)",
            "O(n!)"
        ]
        
        try:
            idx1 = complexity_order.index(c1)
            idx2 = complexity_order.index(c2)
            
            if idx1 < idx2:
                return "better"
            elif idx1 > idx2:
                return "worse"
            else:
                return "same"
        except ValueError:
            return "incomparable"


# Module-level instance
complexity_analyzer = ComplexityAnalyzer()


def analyze_complexity(code: str, language: str, problem: Optional[str] = None) -> ComplexityAnalysis:
    """Convenience function for complexity analysis."""
    return complexity_analyzer.analyze(code, language, problem)