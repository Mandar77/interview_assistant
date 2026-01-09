# backend/services/code_execution_service/routes.py
"""
Code Execution Service API Routes
Location: backend/services/code_execution_service/routes.py
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from dataclasses import asdict

from services.code_execution_service.executor import (
    code_executor,
    TestCase,
    Language,
    ExecutionResult
)
from services.code_execution_service.complexity_analyzer import (
    complexity_analyzer,
    ComplexityAnalysis
)
from services.code_execution_service.correctness_evaluator import (
    code_evaluator,
    CodeEvaluationResult
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class TestCaseModel(BaseModel):
    """Test case input model."""
    input: str = Field(..., description="Input for the test case")
    expected_output: str = Field(..., description="Expected output")
    description: Optional[str] = Field(None, description="Test case description")
    is_hidden: bool = Field(False, description="Whether this is a hidden test case")


class ExecuteCodeRequest(BaseModel):
    """Request for code execution."""
    code: str = Field(..., description="Source code to execute")
    language: str = Field(..., description="Programming language (python, java, cpp, c, javascript)")
    stdin: Optional[str] = Field(None, description="Standard input for the program")
    timeout: int = Field(5, ge=1, le=10, description="Execution timeout in seconds")


class ExecuteWithTestsRequest(BaseModel):
    """Request for code execution with test cases."""
    code: str = Field(..., description="Source code to execute")
    language: str = Field(..., description="Programming language")
    test_cases: List[TestCaseModel] = Field(..., description="Test cases to run")
    timeout: int = Field(5, ge=1, le=10, description="Timeout per test case")


class AnalyzeComplexityRequest(BaseModel):
    """Request for complexity analysis."""
    code: str = Field(..., description="Source code to analyze")
    language: str = Field(..., description="Programming language")
    problem_description: Optional[str] = Field(None, description="Problem context")


class EvaluateCodeRequest(BaseModel):
    """Request for comprehensive code evaluation."""
    code: str = Field(..., description="Source code")
    language: str = Field(..., description="Programming language")
    problem_description: str = Field(..., description="Problem statement")
    test_cases: List[TestCaseModel] = Field(..., description="Test cases")
    timeout: int = Field(5, description="Timeout per test case")


class ExecutionResponse(BaseModel):
    """Response for single code execution."""
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    exit_code: Optional[int] = None
    time: Optional[float] = None
    memory: Optional[int] = None
    error_message: Optional[str] = None


class TestResultResponse(BaseModel):
    """Response for test execution."""
    total_tests: int
    passed: int
    failed: int
    errors: int
    pass_rate: float
    total_time: float
    max_memory: int
    all_passed: bool
    test_results: List[Dict[str, Any]]


class ComplexityResponse(BaseModel):
    """Response for complexity analysis."""
    time_complexity: str
    space_complexity: str
    explanation: str
    is_optimal: bool
    optimal_complexity: Optional[str] = None
    improvement_suggestions: List[str] = []


class CodeEvaluationResponse(BaseModel):
    """Response for code evaluation."""
    correctness_score: float
    code_quality_score: float
    complexity_score: float
    overall_score: float
    passed_tests: int
    total_tests: int
    feedback: str
    strengths: List[str]
    weaknesses: List[str]
    time_complexity: str
    space_complexity: str
    is_optimal: bool
    test_results: Dict[str, Any]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/execute", response_model=ExecutionResponse)
async def execute_code_endpoint(request: ExecuteCodeRequest):
    """
    Execute code with optional input.
    
    Simple execution endpoint for testing code without test cases.
    Returns execution result with stdout, stderr, and metrics.
    """
    try:
        logger.info(f"Executing {request.language} code")
        
        # Validate language
        try:
            language = Language(request.language.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}. Supported: {[l.value for l in Language]}"
            )
        
        # Execute code
        result = code_executor.execute(
            code=request.code,
            language=language,
            stdin=request.stdin,
            timeout=request.timeout
        )
        
        return ExecutionResponse(
            status=result.status,
            stdout=result.stdout,
            stderr=result.stderr,
            compile_output=result.compile_output,
            exit_code=result.exit_code,
            time=result.time,
            memory=result.memory,
            error_message=result.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post("/execute-tests", response_model=TestResultResponse)
async def execute_with_tests_endpoint(request: ExecuteWithTestsRequest):
    """
    Execute code against multiple test cases.
    
    Runs code with each test case and returns aggregated results.
    Useful for OA-style questions with predefined test cases.
    """
    try:
        logger.info(f"Executing {request.language} code with {len(request.test_cases)} test cases")
        
        # Validate language
        try:
            language = Language(request.language.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}"
            )
        
        # Convert test cases
        test_cases = [
            TestCase(
                input=tc.input,
                expected_output=tc.expected_output,
                description=tc.description,
                is_hidden=tc.is_hidden
            )
            for tc in request.test_cases
        ]
        
        # Execute with test cases
        results = code_executor.execute_with_test_cases(
            code=request.code,
            language=language,
            test_cases=test_cases,
            timeout=request.timeout
        )
        
        return TestResultResponse(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@router.post("/analyze-complexity", response_model=ComplexityResponse)
async def analyze_complexity_endpoint(request: AnalyzeComplexityRequest):
    """
    Analyze time and space complexity of code.
    
    Uses LLM to estimate Big-O complexity and suggest optimizations.
    Returns analysis with complexity classes and improvement suggestions.
    """
    try:
        logger.info(f"Analyzing complexity for {request.language} code")
        
        # Analyze complexity
        analysis = complexity_analyzer.analyze(
            code=request.code,
            language=request.language,
            problem_description=request.problem_description
        )
        
        return ComplexityResponse(
            time_complexity=analysis.time_complexity,
            space_complexity=analysis.space_complexity,
            explanation=analysis.explanation,
            is_optimal=analysis.is_optimal,
            optimal_complexity=analysis.optimal_complexity,
            improvement_suggestions=analysis.improvement_suggestions or []
        )
        
    except Exception as e:
        logger.error(f"Complexity analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/evaluate", response_model=CodeEvaluationResponse)
async def evaluate_code_endpoint(request: EvaluateCodeRequest):
    """
    Comprehensive code evaluation.
    
    Executes code with test cases, analyzes complexity, and evaluates quality.
    Returns detailed scores and feedback on:
    - Correctness (test results + approach)
    - Code quality (readability, style)
    - Complexity (Big-O analysis)
    - Overall performance
    
    This is the main endpoint for evaluating OA interview responses.
    """
    try:
        logger.info(f"Evaluating {request.language} code")
        
        # Validate language
        try:
            language = Language(request.language.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}"
            )
        
        # Step 1: Execute with test cases
        test_cases = [
            TestCase(
                input=tc.input,
                expected_output=tc.expected_output,
                description=tc.description,
                is_hidden=tc.is_hidden
            )
            for tc in request.test_cases
        ]
        
        test_results = code_executor.execute_with_test_cases(
            code=request.code,
            language=language,
            test_cases=test_cases,
            timeout=request.timeout
        )
        
        # Step 2: Analyze complexity
        complexity_analysis = complexity_analyzer.analyze(
            code=request.code,
            language=request.language,
            problem_description=request.problem_description
        )
        
        # Step 3: Comprehensive evaluation
        evaluation = code_evaluator.evaluate(
            code=request.code,
            language=request.language,
            problem_description=request.problem_description,
            test_results=test_results,
            complexity_analysis=complexity_analysis
        )
        
        return CodeEvaluationResponse(
            correctness_score=evaluation.correctness_score,
            code_quality_score=evaluation.code_quality_score,
            complexity_score=evaluation.complexity_score,
            overall_score=evaluation.overall_score,
            passed_tests=evaluation.passed_tests,
            total_tests=evaluation.total_tests,
            feedback=evaluation.feedback,
            strengths=evaluation.strengths,
            weaknesses=evaluation.weaknesses,
            time_complexity=evaluation.time_complexity,
            space_complexity=evaluation.space_complexity,
            is_optimal=evaluation.is_optimal,
            test_results=test_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code evaluation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported programming languages."""
    return {
        "languages": [
            {
                "id": lang.value,
                "name": lang.value.capitalize(),
                "judge0_id": LANGUAGE_IDS.get(lang)
            }
            for lang in Language
        ]
    }


@router.get("/health")
async def health_check():
    """Health check for code execution service."""
    judge0_healthy = code_executor.check_health()
    
    return {
        "service": "code_execution_service",
        "status": "healthy" if judge0_healthy else "degraded",
        "judge0_available": judge0_healthy,
        "supported_languages": len(Language)
    }


# Import LANGUAGE_IDS for the /supported-languages endpoint
from services.code_execution_service.executor import LANGUAGE_IDS