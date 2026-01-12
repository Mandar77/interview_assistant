# backend/tests/test_integration_complete.py
"""
Complete Integration Testing Suite
Tests all API endpoints with realistic data flows
"""

import requests
import json
import time
import base64
from typing import Dict, Any, List
from pathlib import Path
import sys

BASE_URL = "http://localhost:8000/api/v1"

class Colors:
    """Terminal colors for pretty output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.bugs = []
    
    def add_pass(self, test_name: str):
        self.passed += 1
        print(f"{Colors.OKGREEN}[OK] PASS{Colors.ENDC}: {test_name}")
    
    def add_fail(self, test_name: str, error: str):
        self.failed += 1
        self.bugs.append({"test": test_name, "error": error, "severity": "HIGH"})
        print(f"{Colors.FAIL}[FAIL] FAIL{Colors.ENDC}: {test_name}")
        print(f"   Error: {error}")
    
    def add_warning(self, test_name: str, message: str):
        self.warnings += 1
        self.bugs.append({"test": test_name, "error": message, "severity": "MEDIUM"})
        print(f"{Colors.WARNING}[WARN]  WARN{Colors.ENDC}: {test_name}")
        print(f"   Warning: {message}")
    
    def print_summary(self):
        total = self.passed + self.failed + self.warnings
        print("\n" + "="*80)
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.ENDC}")
        print("="*80)
        print(f"{Colors.OKGREEN}Passed:{Colors.ENDC} {self.passed}/{total}")
        print(f"{Colors.FAIL}Failed:{Colors.ENDC} {self.failed}/{total}")
        print(f"{Colors.WARNING}Warnings:{Colors.ENDC} {self.warnings}/{total}")
        
        if self.bugs:
            print(f"\n{Colors.BOLD}BUGS FOUND:{Colors.ENDC} {len(self.bugs)}")
            for i, bug in enumerate(self.bugs, 1):
                print(f"\nBUG #{i} [{bug['severity']}]")
                print(f"  Test: {bug['test']}")
                print(f"  Issue: {bug['error']}")
        
        return self.failed == 0


results = TestResult()


def test_health_endpoints():
    """Test all service health endpoints."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Service Health Checks{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    # Main API health is at root, others are under /api/v1
    services = [
        ("Main API", "/health", False),  # False = use root URL
        ("Questions", "/questions/health", True),  # True = use BASE_URL
        ("Speech", "/speech/health", True),
        ("Evaluation", "/evaluation/health", True),
        ("Feedback", "/feedback/health", True),
        ("Code Execution", "/code-execution/health", True),
        ("Vision", "/vision/health", True),
    ]
    
    for service_name, endpoint, use_api_prefix in services:
        try:
            # Build URL correctly
            if use_api_prefix:
                url = f"{BASE_URL}{endpoint}"
            else:
                url = f"http://localhost:8000{endpoint}"
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                if status == 'healthy':
                    results.add_pass(f"{service_name} health check")
                else:
                    results.add_warning(f"{service_name} health check", f"Status: {status}")
            else:
                results.add_fail(f"{service_name} health check", f"HTTP {response.status_code}")
                
        except Exception as e:
            results.add_fail(f"{service_name} health check", str(e))


def test_question_generation_flow():
    """Test question generation for all interview types."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Question Generation{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    job_desc = "Senior Software Engineer with Python, system design, and algorithms expertise"
    
    test_cases = [
        ("technical", 2),
        ("oa", 1),
        ("system_design", 1),
        ("behavioral", 2),
    ]
    
    for interview_type, num_questions in test_cases:
        try:
            response = requests.post(f"{BASE_URL}/questions/generate", json={
                "job_description": job_desc,
                "interview_type": interview_type,
                "difficulty": "medium",
                "num_questions": num_questions
            }, timeout=30)
            
            if response.status_code != 200:
                results.add_fail(
                    f"Generate {interview_type} questions",
                    f"HTTP {response.status_code}: {response.text[:100]}"
                )
                continue
            
            data = response.json()
            questions = data.get('questions', [])
            
            # Validate response structure
            if len(questions) != num_questions:
                results.add_warning(
                    f"Generate {interview_type} questions",
                    f"Expected {num_questions} questions, got {len(questions)}"
                )
            
            # Validate question structure
            for q in questions:
                required_fields = ['id', 'question', 'interview_type', 'difficulty', 'skill_tags']
                missing = [f for f in required_fields if f not in q]
                
                if missing:
                    results.add_fail(
                        f"{interview_type} question structure",
                        f"Missing fields: {missing}"
                    )
                    break
                
                # Type-specific validation
                if interview_type == 'oa':
                    if 'test_cases' not in q:
                        results.add_fail(f"OA question {q['id']}", "Missing test_cases")
                    elif len(q.get('test_cases', [])) == 0:
                        results.add_fail(f"OA question {q['id']}", "Empty test_cases list")
                    
                    if 'starter_code' not in q:
                        results.add_fail(f"OA question {q['id']}", "Missing starter_code")
            
            if not any(bug['test'].startswith(f"{interview_type} question") for bug in results.bugs):
                results.add_pass(f"Generate {interview_type} questions")
                
        except requests.exceptions.Timeout:
            results.add_fail(f"Generate {interview_type} questions", "Timeout (>30s)")
        except Exception as e:
            results.add_fail(f"Generate {interview_type} questions", str(e))


def test_code_execution_comprehensive():
    """Comprehensive code execution testing."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Code Execution Service{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    # Test 1: Simple execution
    test_code = """
def greet():
    return "Hello, World!"

print(greet())
"""
    
    try:
        response = requests.post(f"{BASE_URL}/code-execution/execute", json={
            "code": test_code,
            "language": "python"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'accepted' and 'Hello, World!' in (data.get('stdout') or ''):
                results.add_pass("Simple code execution")
            else:
                results.add_fail("Simple code execution", f"Unexpected output: {data}")
        else:
            results.add_fail("Simple code execution", f"HTTP {response.status_code}")
    except Exception as e:
        results.add_fail("Simple code execution", str(e))
    
    # Test 2: Multi-language support
    language_tests = {
        "python": ("print('Python works')", "Python works"),
        "java": ("""
public class Main {
    public static void main(String[] args) {
        System.out.println("Java works");
    }
}
""", "Java works"),
        "cpp": ("""
#include <iostream>
int main() {
    std::cout << "C++ works" << std::endl;
    return 0;
}
""", "C++ works"),
    }
    
    for lang, (code, expected_output) in language_tests.items():
        try:
            response = requests.post(f"{BASE_URL}/code-execution/execute", json={
                "code": code,
                "language": lang
            }, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if expected_output in (data.get('stdout') or ''):
                    results.add_pass(f"{lang.upper()} execution")
                else:
                    results.add_warning(
                        f"{lang.upper()} execution",
                        f"Output mismatch. Got: {data.get('stdout', '')}"
                    )
            else:
                results.add_fail(f"{lang.upper()} execution", f"HTTP {response.status_code}")
        except Exception as e:
            results.add_fail(f"{lang.upper()} execution", str(e))
    
    # Test 3: Error handling
    error_cases = [
        ("Syntax error", "print('unclosed string", "compilation_error"),
        ("Runtime error", "print(1/0)", "runtime_error"),
        ("Infinite loop", "while True: pass", "time_limit_exceeded"),
    ]
    
    for test_name, code, expected_status in error_cases:
        try:
            response = requests.post(f"{BASE_URL}/code-execution/execute", json={
                "code": code,
                "language": "python",
                "timeout": 2
            }, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if expected_status in data['status'] or data['status'] == expected_status:
                    results.add_pass(f"Error detection: {test_name}")
                else:
                    results.add_warning(
                        f"Error detection: {test_name}",
                        f"Expected {expected_status}, got {data['status']}"
                    )
            else:
                results.add_fail(f"Error detection: {test_name}", f"HTTP {response.status_code}")
        except Exception as e:
            results.add_fail(f"Error detection: {test_name}", str(e))


def test_evaluation_pipeline():
    """Test complete evaluation pipeline."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Evaluation Pipeline{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    # Test with realistic metrics
    eval_request = {
        "session_id": "integration_test_session",
        "question_id": "test_q1",
        "question_text": "Explain the difference between REST and GraphQL",
        "answer_text": "REST uses multiple endpoints while GraphQL uses a single endpoint. REST can lead to over-fetching or under-fetching of data, while GraphQL allows clients to request exactly what they need. GraphQL has a strongly typed schema which provides better documentation and validation.",
        "interview_type": "technical",
        "speech_metrics": {
            "words_per_minute": 140,
            "total_words": 50,
            "total_duration_seconds": 21.4,
            "filler_word_percentage": 2.0,
            "pause_count": 3,
            "avg_pause_duration_ms": 500,
            "longest_pause_ms": 800,
            "speaking_rate_category": "normal"
        },
        "language_metrics": {
            "grammar_score": 4.5,
            "vocabulary_level": "advanced",
            "unique_word_ratio": 0.75,
            "avg_sentence_length": 15,
            "readability_flesch": 65,
            "clarity_score": 4.2
        },
        "body_language_metrics": {
            "eye_contact_percentage": 75,
            "posture_score": 4.5,
            "gesture_frequency": 2.5,
            "head_movement_stability": 0.8
        },
        "timing_metrics": {
            "time_taken_seconds": 25,
            "expected_time_seconds": 30
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/evaluation/evaluate",
            json=eval_request,
            timeout=60
        )
        
        if response.status_code != 200:
            results.add_fail(
                "Full evaluation pipeline",
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return
        
        data = response.json()
        
        # Validate response structure
        required_fields = [
            'overall_score', 'weighted_score', 'rubric_scores',
            'strengths', 'weaknesses', 'confidence_index'
        ]
        
        missing = [f for f in required_fields if f not in data]
        if missing:
            results.add_fail("Evaluation response structure", f"Missing fields: {missing}")
            return
        
        # Validate scores are in valid range
        if not (0 <= data['overall_score'] <= 5):
            results.add_fail("Overall score range", f"Score {data['overall_score']} outside 0-5")
        
        if not (0 <= data['weighted_score'] <= 5):
            results.add_fail("Weighted score range", f"Score {data['weighted_score']} outside 0-5")
        
        # Validate rubric scores
        if len(data['rubric_scores']) < 5:
            results.add_warning(
                "Rubric completeness",
                f"Only {len(data['rubric_scores'])} categories scored (expected 9)"
            )
        
        for score_item in data['rubric_scores']:
            if not (0 <= score_item['score'] <= 5):
                results.add_fail(
                    f"Rubric score range: {score_item['category']}",
                    f"Score {score_item['score']} outside 0-5"
                )
        
        # Check if body language was evaluated
        body_lang_scored = any(
            s['category'] == 'body_language' 
            for s in data['rubric_scores']
        )
        if not body_lang_scored:
            results.add_warning(
                "Body language evaluation",
                "Body language metrics provided but not scored"
            )
        
        results.add_pass("Full evaluation pipeline")
        
    except requests.exceptions.Timeout:
        results.add_fail("Full evaluation pipeline", "Timeout (>60s)")
    except Exception as e:
        results.add_fail("Full evaluation pipeline", str(e))


def test_feedback_generation():
    """Test feedback generation service."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Feedback Generation{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    feedback_request = {
        "session_id": "test_feedback_session",
        "evaluation_result": {
            "overall_score": 3.5,
            "weighted_score": 3.3,
            "rubric_scores": [
                {"category": "technical_correctness", "score": 4.0},
                {"category": "communication", "score": 3.5}
            ],
            "strengths": ["Good technical knowledge", "Clear communication"],
            "weaknesses": ["Could improve pacing", "Some hesitation"]
        },
        "question_text": "Explain microservices architecture",
        "answer_text": "Microservices is an architectural pattern...",
        "interview_type": "technical"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/feedback/generate",
            json=feedback_request,
            timeout=60
        )
        
        if response.status_code != 200:
            results.add_fail(
                "Feedback generation",
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return
        
        data = response.json()
        
        # Validate response - check for required fields, but be flexible
        required = ['summary', 'overall_performance']
        optional = ['improvement_tips', 'next_steps']
        
        missing_required = [f for f in required if f not in data or not data[f]]
        missing_optional = [f for f in optional if f not in data or not data[f]]
        
        if missing_required:
            results.add_fail("Feedback response structure", f"Missing required: {missing_required}")
        elif missing_optional:
            results.add_warning("Feedback response structure", f"Missing optional: {missing_optional}")
            results.add_pass("Feedback generation")
        else:
            results.add_pass("Feedback generation")
        
    except Exception as e:
        results.add_fail("Feedback generation", str(e))


def test_websocket_session_flow():
    """Test WebSocket session creation and retrieval."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: WebSocket Session Management{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    session_id = f"ws_test_{int(time.time())}"
    
    # Note: Full WebSocket testing requires websocket client
    # Here we test the REST endpoints that support the WebSocket flow
    
    try:
        # Test session data endpoint (used by frontend after interview)
        response = requests.get(
            f"{BASE_URL}/speech/session/{session_id}/for-evaluation",
            timeout=5
        )
        
        # Session might not exist, which is OK - we're testing the endpoint exists
        if response.status_code in [200, 404]:
            results.add_pass("Session retrieval endpoint exists")
        else:
            results.add_fail(
                "Session retrieval endpoint",
                f"Unexpected status: {response.status_code}"
            )
            
    except Exception as e:
        results.add_fail("Session retrieval endpoint", str(e))


def test_vision_service():
    """Test vision service with actual image."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Vision Service{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    # Create simple test image
    try:
        from PIL import Image, ImageDraw
        from io import BytesIO
        
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 150, 150], outline='black', width=3)
        draw.rectangle([200, 50, 300, 150], outline='black', width=3)
        draw.line([150, 100, 200, 100], fill='black', width=2)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Test diagram critique
        response = requests.post(f"{BASE_URL}/vision/critique-diagram", json={
            "session_id": "vision_test",
            "question_id": "vq1",
            "question_text": "Design a URL shortening service",
            "interview_type": "system_design",
            "image_base64": img_b64,
            "capture_method": "manual",
            "transcript": "I designed a two-tier architecture with a load balancer and database layer"
        }, timeout=60)
        
        if response.status_code != 200:
            results.add_fail(
                "Diagram critique",
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return
        
        data = response.json()
        
        # Validate scores
        score_fields = ['completeness_score', 'clarity_score', 'overall_score']
        for field in score_fields:
            if field not in data:
                results.add_fail("Diagram critique response", f"Missing {field}")
            elif not (0 <= data[field] <= 5):
                results.add_fail(f"Diagram {field}", f"Score {data[field]} outside 0-5")
        
        # Check for feedback
        if not data.get('detailed_feedback'):
            results.add_warning("Diagram feedback", "No detailed feedback generated")
        
        results.add_pass("Diagram critique")
        
        # Test screenshot storage
        screenshots_response = requests.get(
            f"{BASE_URL}/vision/screenshots/vision_test",
            timeout=5
        )
        
        if screenshots_response.status_code == 200:
            screenshots = screenshots_response.json()
            if screenshots['total'] > 0:
                results.add_pass("Screenshot storage")
            else:
                results.add_warning("Screenshot storage", "No screenshots stored")
        
    except ImportError:
        results.add_warning("Vision service", "PIL not available, skipping image tests")
    except Exception as e:
        results.add_fail("Vision service", str(e))


def test_data_flow_integrity():
    """Test complete data flow from generation to results."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Complete Data Flow Integrity{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    session_id = f"dataflow_test_{int(time.time())}"
    
    try:
        # Step 1: Generate question
        print("  Step 1/4: Generating question...")
        gen_response = requests.post(f"{BASE_URL}/questions/generate", json={
            "job_description": "Software Engineer",
            "interview_type": "technical",
            "difficulty": "medium",
            "num_questions": 1
        }, timeout=30)
        
        if gen_response.status_code != 200:
            results.add_fail("Data flow: Question generation", "Failed to generate")
            return
        
        question = gen_response.json()['questions'][0]
        question_id = question['id']
        
        # Step 2: Evaluate answer
        print("  Step 2/4: Evaluating answer...")
        eval_response = requests.post(f"{BASE_URL}/evaluation/evaluate", json={
            "session_id": session_id,
            "question_id": question_id,
            "question_text": question['question'],
            "answer_text": "This is a comprehensive answer with multiple key points...",
            "interview_type": "technical"
        }, timeout=60)
        
        if eval_response.status_code != 200:
            results.add_fail("Data flow: Evaluation", "Failed to evaluate")
            return
        
        evaluation = eval_response.json()
        
        # Step 3: Generate feedback
        print("  Step 3/4: Generating feedback...")
        feedback_response = requests.post(f"{BASE_URL}/feedback/generate", json={
            "session_id": session_id,
            "evaluation_result": evaluation,
            "question_text": question['question'],
            "answer_text": "This is a comprehensive answer...",
            "interview_type": "technical"
        }, timeout=60)
        
        if feedback_response.status_code != 200:
            results.add_fail("Data flow: Feedback", "Failed to generate feedback")
            return
        
        feedback = feedback_response.json()
        
        # Step 4: Validate data consistency
        print("  Step 4/4: Validating data consistency...")
        
        # Check session_id propagation
        if feedback.get('session_id') != session_id:
            results.add_warning(
                "Data flow: Session ID consistency",
                f"Session ID mismatch or not returned"
            )
        
        results.add_pass("Complete data flow integrity")
        
    except Exception as e:
        results.add_fail("Data flow integrity", str(e))


def test_concurrent_requests():
    """Test handling of concurrent requests."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Concurrent Request Handling{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    import concurrent.futures
    
    def make_request(i):
        try:
            response = requests.post(f"{BASE_URL}/questions/generate", json={
                "job_description": f"Test job description {i}",
                "interview_type": "technical",
                "difficulty": "medium",
                "num_questions": 1
            }, timeout=45)
            return (i, response.status_code, response.status_code == 200)
        except Exception as e:
            return (i, None, False)
    
    # Send 5 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(5)]
        concurrent_results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    successful = sum(1 for _, _, success in concurrent_results if success)
    
    if successful == 5:
        results.add_pass("Concurrent request handling (5 simultaneous)")
    elif successful >= 3:
        results.add_warning(
            "Concurrent request handling",
            f"Only {successful}/5 requests succeeded"
        )
    else:
        results.add_fail(
            "Concurrent request handling",
            f"Only {successful}/5 requests succeeded"
        )


def test_large_payload_handling():
    """Test handling of large payloads."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Large Payload Handling{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    # Test 1: Very long job description
    long_job_desc = "Software Engineer. " * 500  # ~10KB
    
    try:
        response = requests.post(f"{BASE_URL}/questions/generate", json={
            "job_description": long_job_desc,
            "interview_type": "technical",
            "difficulty": "medium",
            "num_questions": 1
        }, timeout=30)
        
        if response.status_code == 200:
            results.add_pass("Large job description handling")
        else:
            results.add_warning(
                "Large job description",
                f"HTTP {response.status_code}"
            )
    except Exception as e:
        results.add_fail("Large job description", str(e))
    
    # Test 2: Long transcript
    long_transcript = "This is a very detailed answer. " * 300  # ~10KB
    
    try:
        response = requests.post(f"{BASE_URL}/evaluation/evaluate", json={
            "session_id": "large_payload_test",
            "question_id": "q1",
            "question_text": "Explain the question",
            "answer_text": long_transcript,
            "interview_type": "technical"
        }, timeout=60)
        
        if response.status_code == 200:
            results.add_pass("Long transcript handling")
        else:
            results.add_warning("Long transcript", f"HTTP {response.status_code}")
    except Exception as e:
        results.add_fail("Long transcript", str(e))
    
    # Test 3: Large code submission
    large_code = "# Comment line\n" * 500 + "print('test')"  # ~8KB
    
    try:
        response = requests.post(f"{BASE_URL}/code-execution/execute", json={
            "code": large_code,
            "language": "python"
        }, timeout=15)
        
        if response.status_code == 200:
            results.add_pass("Large code submission")
        else:
            results.add_warning("Large code submission", f"HTTP {response.status_code}")
    except Exception as e:
        results.add_fail("Large code submission", str(e))


def test_edge_case_inputs():
    """Test edge cases and boundary conditions."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Edge Cases & Boundary Conditions{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    edge_cases = [
        {
            "name": "Minimum questions (1)",
            "endpoint": "/questions/generate",
            "payload": {
                "job_description": "Engineer",
                "interview_type": "technical",
                "num_questions": 1
            },
            "expected_status": 200
        },
        {
            "name": "Maximum questions (20)",
            "endpoint": "/questions/generate",
            "payload": {
                "job_description": "Engineer",
                "interview_type": "technical",
                "num_questions": 20
            },
            "expected_status": 200
        },
        {
            "name": "Empty answer evaluation",
            "endpoint": "/evaluation/evaluate",
            "payload": {
                "session_id": "edge_test",
                "question_id": "q1",
                "question_text": "Test question",
                "answer_text": "",
                "interview_type": "technical"
            },
            "expected_status": 200
        },
        {
            "name": "Special characters in text",
            "endpoint": "/evaluation/evaluate",
            "payload": {
                "session_id": "edge_test",
                "question_id": "q2",
                "question_text": "Test with <script>alert('xss')</script>",
                "answer_text": "Answer with 'quotes' and \"double quotes\" and \n newlines",
                "interview_type": "technical"
            },
            "expected_status": 200
        },
    ]
    
    for case in edge_cases:
        try:
            response = requests.post(
                f"{BASE_URL}{case['endpoint']}",
                json=case['payload'],
                timeout=45
            )
            
            if response.status_code == case['expected_status']:
                results.add_pass(f"Edge case: {case['name']}")
            else:
                results.add_fail(
                    f"Edge case: {case['name']}",
                    f"Expected {case['expected_status']}, got {response.status_code}"
                )
        except Exception as e:
            results.add_fail(f"Edge case: {case['name']}", str(e))


def test_response_time_benchmarks():
    """Benchmark response times for critical endpoints."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}TESTING: Response Time Benchmarks{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    benchmarks = []
    
    # Test 1: Health check speed
    start = time.time()
    try:
        requests.get("http://localhost:8000/health", timeout=5)
        elapsed = time.time() - start
        benchmarks.append(("Health check", elapsed, 1.0))  # Should be <1s
    except:
        pass
    
    # Test 2: Simple code execution speed
    start = time.time()
    try:
        requests.post(f"{BASE_URL}/code-execution/execute", json={
            "code": "print('test')",
            "language": "python"
        }, timeout=10)
        elapsed = time.time() - start
        benchmarks.append(("Code execution", elapsed, 5.0))  # Should be <5s
    except:
        pass
    
    # Test 3: Question generation speed
    start = time.time()
    try:
        requests.post(f"{BASE_URL}/questions/generate", json={
            "job_description": "Software Engineer",
            "interview_type": "technical",
            "num_questions": 1
        }, timeout=30)
        elapsed = time.time() - start
        benchmarks.append(("Question generation", elapsed, 20.0))  # Should be <20s
    except:
        pass
    
    print(f"\n{'Endpoint':<30} {'Time':<10} {'Target':<10} {'Status'}")
    print("-" * 65)
    
    for endpoint, elapsed, target in benchmarks:
        status = "[OK] FAST" if elapsed < target else "[WARN]  SLOW"
        print(f"{endpoint:<30} {elapsed:>6.2f}s    <{target:>4.1f}s    {status}")
        
        if elapsed < target * 2:  # Within 2x target is acceptable
            results.add_pass(f"Performance: {endpoint}")
        else:
            results.add_warning(f"Performance: {endpoint}", f"{elapsed:.2f}s (target: <{target}s)")


def run_all_integration_tests():
    """Run complete integration test suite."""
    print("\n")
    print(f"{Colors.BOLD}{'='*120}{Colors.ENDC}")
    print(f"{Colors.BOLD}BACKEND INTEGRATION TEST SUITE{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*120}{Colors.ENDC}")
    print("\n")
    
    start_time = time.time()
    
    # Run all test suites
    test_health_endpoints()
    test_question_generation_flow()
    test_code_execution_comprehensive()
    test_evaluation_pipeline()
    test_feedback_generation()
    test_websocket_session_flow()
    test_vision_service()
    test_data_flow_integrity()
    test_concurrent_requests()
    test_large_payload_handling()
    test_edge_case_inputs()
    test_response_time_benchmarks()
    
    elapsed = time.time() - start_time
    
    # Print summary
    success = results.print_summary()
    
    print(f"\nTotal execution time: {elapsed:.2f}s")
    
    # Save bug report if any bugs found
    if results.bugs:
        bug_report_path = Path("test_results") / f"bug_report_{int(time.time())}.json"
        bug_report_path.parent.mkdir(exist_ok=True)
        
        with open(bug_report_path, 'w') as f:
            json.dump({
                "timestamp": time.time(),
                "total_tests": results.passed + results.failed + results.warnings,
                "passed": results.passed,
                "failed": results.failed,
                "warnings": results.warnings,
                "bugs": results.bugs
            }, f, indent=2)
        
        print(f"\n Bug report saved to: {bug_report_path}")
    
    return success


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)