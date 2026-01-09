# backend/services/code_execution_service/__init__.py (COMPLETE FILE)

"""
Code Execution Service - Execute and evaluate code submissions
"""

from services.code_execution_service.executor import (
    code_executor,
    CodeExecutor,
    ExecutionResult,
    TestCase,
    Language
)

from services.code_execution_service.complexity_analyzer import (
    complexity_analyzer,
    ComplexityAnalyzer,
    ComplexityAnalysis
)

from services.code_execution_service.correctness_evaluator import (
    code_evaluator,
    CodeCorrectnessEvaluator,
    CodeEvaluationResult
)

# ✅ NEW: Import and export router
from services.code_execution_service.routes import router

__all__ = [
    "code_executor",
    "CodeExecutor",
    "ExecutionResult",
    "TestCase",
    "Language",
    "complexity_analyzer",
    "ComplexityAnalyzer",
    "ComplexityAnalysis",
    "code_evaluator",
    "CodeCorrectnessEvaluator",
    "CodeEvaluationResult",
    "router",  # ✅ Export router
]