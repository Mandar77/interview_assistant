# backend/services/code_execution_service/executor.py (COMPLETE FILE - COPY PASTE THIS)

"""
Code Executor - Execute code using Judge0 API
Location: backend/services/code_execution_service/executor.py
"""

import os
import time
import logging
import requests
import base64
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Language Configuration
# =============================================================================

class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    JAVASCRIPT = "javascript"


# Judge0 language IDs (for local instance v1.13.0)
LANGUAGE_IDS = {
    Language.PYTHON: 71,      # Python 3.8.1
    Language.JAVA: 62,        # Java 13.0.1
    Language.CPP: 54,         # C++ (GCC 9.2.0)
    Language.C: 50,           # C (GCC 9.2.0)
    Language.JAVASCRIPT: 63,  # Node.js 12.14.0
}


@dataclass
class ExecutionResult:
    """Result of code execution."""
    status: str  # accepted, wrong_answer, runtime_error, time_limit_exceeded, compilation_error
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    exit_code: Optional[int] = None
    time: Optional[float] = None  # seconds
    memory: Optional[int] = None  # KB
    token: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class TestCase:
    """Single test case."""
    input: str
    expected_output: str
    description: Optional[str] = None
    is_hidden: bool = False  # Hidden test cases for evaluation


# =============================================================================
# Judge0 Executor
# =============================================================================

class CodeExecutor:
    """
    Execute code using Judge0 API.
    Supports multiple languages and test case execution.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_hosted: bool = None):
        """
        Initialize code executor.
        
        Args:
            api_key: Judge0 API key (if using hosted)
            use_hosted: If True, use hosted API. If False, use local Docker instance
        """
        # Load from settings
        from config.settings import settings
        self.api_key = api_key or settings.judge0_api_key
        
        # Determine which endpoint to use
        if use_hosted is not None:
            self.use_hosted = use_hosted
        else:
            self.use_hosted = settings.judge0_use_hosted
        
        if self.use_hosted and self.api_key:
            # Hosted Judge0 API
            self.base_url = "https://judge0-ce.p.rapidapi.com"
            self.headers = {
                "content-type": "application/json",
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com"
            }
            logger.info("Using hosted Judge0 API")
        else:
            # Local Docker instance
            self.base_url = settings.judge0_base_url
            self.headers = {"content-type": "application/json"}
            logger.info(f"Using local Judge0 instance at {self.base_url}")
    
    def execute(
        self,
        code: str,
        language: Language,
        stdin: Optional[str] = None,
        timeout: int = 5
    ) -> ExecutionResult:
        """
        Execute code with optional input.
        
        Args:
            code: Source code to execute
            language: Programming language
            stdin: Standard input for the program
            timeout: Execution timeout in seconds (max 5)
            
        Returns:
            ExecutionResult with execution details
        """
        try:
            language_id = LANGUAGE_IDS.get(language)
            if not language_id:
                return ExecutionResult(
                    status="error",
                    error_message=f"Unsupported language: {language}"
                )
            
            # Use base64 encoding to avoid file path issues
            code_b64 = base64.b64encode(code.encode()).decode()
            stdin_b64 = base64.b64encode((stdin or "").encode()).decode() if stdin else ""
            
            # Create submission with base64 encoding
            submission_data = {
                "source_code": code_b64,
                "language_id": language_id,
                "stdin": stdin_b64,
                "cpu_time_limit": timeout,
                "wall_time_limit": timeout + 1,
                "memory_limit": 128000,  # 128 MB
            }
            
            # Use base64_encoded=true for local Judge0
            params = {
                "base64_encoded": "true",
                "wait": "true",
                "fields": "*"
            }
            
            logger.debug(f"Submitting to Judge0: language_id={language_id}")
            
            # Submit code
            response = requests.post(
                f"{self.base_url}/submissions",
                json=submission_data,
                headers=self.headers,
                params=params,
                timeout=timeout + 10
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Submission failed: {response.status_code} - {response.text}")
                return ExecutionResult(
                    status="error",
                    error_message=f"Submission failed: {response.status_code} - {response.text}"
                )
            
            result = response.json()
            
            # Decode base64 outputs safely
            def safe_b64_decode(value):
                """Safely decode base64 value."""
                if not value:
                    return None
                try:
                    return base64.b64decode(value).decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.warning(f"Base64 decode failed: {e}")
                    return None
            
            stdout = safe_b64_decode(result.get("stdout"))
            stderr = safe_b64_decode(result.get("stderr"))
            compile_output = safe_b64_decode(result.get("compile_output"))
            message = safe_b64_decode(result.get("message"))
            
            logger.debug(f"Judge0 response status: {result.get('status', {})}")
            
            # Map Judge0 status to our status
            status_mapping = {
                1: "in_queue",
                2: "processing",
                3: "accepted",           # Accepted
                4: "wrong_answer",       # Wrong Answer
                5: "time_limit_exceeded",
                6: "compilation_error",
                7: "runtime_error",      # Runtime Error (SIGSEGV)
                8: "runtime_error",      # Runtime Error (SIGXFSZ)
                9: "runtime_error",      # Runtime Error (SIGFPE)
                10: "runtime_error",     # Runtime Error (SIGABRT)
                11: "runtime_error",     # Runtime Error (NZEC)
                12: "runtime_error",     # Runtime Error (Other)
                13: "internal_error",
                14: "exec_format_error",
            }
            
            status_id = result.get("status", {}).get("id", 0)
            status = status_mapping.get(status_id, "error")
            
            # Get error message
            error_msg = message or stderr or compile_output or None
            
            return ExecutionResult(
                status=status,
                stdout=stdout,
                stderr=stderr,
                compile_output=compile_output,
                exit_code=result.get("exit_code"),
                time=result.get("time"),
                memory=result.get("memory"),
                token=result.get("token"),
                error_message=error_msg
            )
            
        except requests.exceptions.Timeout:
            logger.error("Execution timed out")
            return ExecutionResult(
                status="time_limit_exceeded",
                error_message="Execution timed out"
            )
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ExecutionResult(
                status="error",
                error_message=f"Execution error: {str(e)}"
            )
    
    def execute_with_test_cases(
        self,
        code: str,
        language: Language,
        test_cases: List[TestCase],
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Execute code against multiple test cases.
        
        Args:
            code: Source code to execute
            language: Programming language
            test_cases: List of test cases to run
            timeout: Execution timeout per test case
            
        Returns:
            Dict with test results and statistics
        """
        results = []
        passed = 0
        failed = 0
        errors = 0
        total_time = 0.0
        total_memory = 0
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"Running test case {i + 1}/{len(test_cases)}")
            
            result = self.execute(
                code=code,
                language=language,
                stdin=test_case.input,
                timeout=timeout
            )
            
            # Check if output matches expected
            actual_output = (result.stdout or "").strip()
            expected_output = test_case.expected_output.strip()
            
            test_passed = False
            if result.status == "accepted":
                # Flexible matching (handle whitespace differences)
                if self._outputs_match(actual_output, expected_output):
                    test_passed = True
                    passed += 1
                else:
                    result.status = "wrong_answer"
                    failed += 1
            else:
                if result.status in ["runtime_error", "compilation_error", "internal_error"]:
                    errors += 1
                else:
                    failed += 1
            
            # Track metrics (safe None handling)
            if result.time is not None:
                total_time += float(result.time)
            if result.memory is not None:
                total_memory = max(total_memory, int(result.memory))
            
            results.append({
                "test_case_index": i,
                "description": test_case.description or f"Test case {i + 1}",
                "is_hidden": test_case.is_hidden,
                "passed": test_passed,
                "status": result.status,
                "expected_output": expected_output if not test_case.is_hidden else "[Hidden]",
                "actual_output": actual_output if not test_case.is_hidden else "[Hidden]",
                "error": result.error_message or "",  # ✅ FIX: Default to empty string
                "time": result.time or 0.0,  # ✅ FIX: Default to 0.0
                "memory": result.memory or 0  # ✅ FIX: Default to 0
            })
        
        total = len(test_cases)
        pass_rate = (passed / total) * 100 if total > 0 else 0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": round(pass_rate, 2),
            "total_time": round(total_time, 3),
            "max_memory": total_memory,
            "test_results": results,
            "all_passed": passed == total
        }
    
    def _outputs_match(self, actual: str, expected: str) -> bool:
        """
        Compare outputs with flexible matching.
        Handles trailing whitespace, different line endings, etc.
        """
        # Normalize both outputs
        actual_lines = [line.strip() for line in actual.split('\n') if line.strip()]
        expected_lines = [line.strip() for line in expected.split('\n') if line.strip()]
        
        return actual_lines == expected_lines
    
    def check_health(self) -> bool:
        """Check if Judge0 API is accessible."""
        try:
            response = requests.get(
                f"{self.base_url}/about",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Module-level instance - will auto-detect from settings
code_executor = CodeExecutor()


def execute_code(code: str, language: str, test_cases: List[dict]) -> Dict[str, Any]:
    """Convenience function for code execution."""
    lang = Language(language.lower())
    tests = [TestCase(input=tc["input"], expected_output=tc["expected_output"]) for tc in test_cases]
    return code_executor.execute_with_test_cases(code, lang, tests)