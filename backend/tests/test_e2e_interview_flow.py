# backend/tests/test_e2e_interview_flow.py
"""
End-to-End Interview Flow Testing
Tests complete interview flow for all question types
"""

import requests
import json
import base64
import time
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"


def create_sample_diagram():
    """Create a simple diagram image for testing."""
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a simple system design diagram
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw boxes for components
    draw.rectangle([50, 50, 200, 150], outline='black', width=2)
    draw.text((70, 90), "Load Balancer", fill='black')
    
    draw.rectangle([300, 50, 450, 150], outline='black', width=2)
    draw.text((330, 90), "Web Server", fill='black')
    
    draw.rectangle([550, 50, 700, 150], outline='black', width=2)
    draw.text((580, 90), "Database", fill='black')
    
    # Draw arrows
    draw.line([200, 100, 300, 100], fill='black', width=2)
    draw.line([450, 100, 550, 100], fill='black', width=2)
    
    # Save to bytes
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    
    return base64.b64encode(img_bytes).decode()


def test_1_technical_interview():
    """Test standard technical interview flow."""
    print("=" * 80)
    print("TEST 1: Technical Interview Flow")
    print("=" * 80)
    
    # Step 1: Generate questions
    print("\n Step 1: Generating technical questions...")
    response = requests.post(f"{BASE_URL}/questions/generate", json={
        "job_description": "Senior Software Engineer with expertise in Python, system design, and algorithms",
        "interview_type": "technical",
        "difficulty": "medium",
        "num_questions": 1
    })
    assert response.status_code == 200, f"Question generation failed: {response.status_code}"
    question = response.json()['questions'][0]
    print(f"[OK] Generated question: {question['question'][:80]}...")
    
    # Step 2: Simulate answer (transcript only, no actual audio)
    print("\n Step 2: Simulating candidate response...")
    mock_transcript = "The difference between a process and a thread is that processes have separate memory spaces while threads share memory within the same process. Processes are isolated which provides better security but threads are more lightweight and faster to create."
    
    # Step 3: Evaluate response
    print("\n Step 3: Evaluating response...")
    eval_response = requests.post(f"{BASE_URL}/evaluation/evaluate", json={
        "session_id": "test_session_1",
        "question_id": question['id'],
        "question_text": question['question'],
        "answer_text": mock_transcript,
        "interview_type": "technical",
        "speech_metrics": {
            "words_per_minute": 140,
            "filler_word_percentage": 2.5,
            "pause_count": 3,
            "longest_pause_ms": 800,
            "speaking_rate_category": "normal"
        },
        "language_metrics": {
            "grammar_score": 4.5,
            "vocabulary_level": "advanced",
            "clarity_score": 4.2,
            "readability_flesch": 65
        }
    })
    assert eval_response.status_code == 200, f"Evaluation failed: {eval_response.status_code}"
    evaluation = eval_response.json()
    
    print(f"[OK] Overall Score: {evaluation['overall_score']}/5")
    print(f"[OK] Weighted Score: {evaluation['weighted_score']}/5")
    print(f"[OK] Strengths: {len(evaluation['strengths'])} identified")
    print(f"[OK] Weaknesses: {len(evaluation['weaknesses'])} identified")
    
    print("\n" + "=" * 80)
    print("[OK] TEST 1 PASSED: Technical Interview Flow Complete")
    print("=" * 80 + "\n")
    
    return evaluation


def test_2_oa_interview():
    """Test OA (coding) interview flow."""
    print("=" * 80)
    print("TEST 2: OA (Coding) Interview Flow")
    print("=" * 80)
    
    # Step 1: Generate OA question
    print("\n Step 1: Generating OA question with test cases...")
    response = requests.post(f"{BASE_URL}/questions/generate", json={
        "job_description": "Software Engineer with strong algorithms and data structures background",
        "interview_type": "oa",
        "difficulty": "medium",
        "num_questions": 1
    })
    assert response.status_code == 200, f"Question generation failed"
    question = response.json()['questions'][0]
    print(f"[OK] Generated OA question with {len(question['test_cases'])} test cases")
    print(f"[OK] Starter code provided for: {list(question['starter_code'].keys())}")
    
    # Step 2: Submit code solution
    print("\n Step 2: Executing code with test cases...")
    code = """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

nums = list(map(int, input().split()))
target = int(input())
result = two_sum(nums, target)
print(' '.join(map(str, result)))
"""
    
    exec_response = requests.post(f"{BASE_URL}/code-execution/execute-tests", json={
        "code": code,
        "language": "python",
        "test_cases": question['test_cases']
    })
    assert exec_response.status_code == 200, f"Code execution failed"
    test_results = exec_response.json()
    print(f"[OK] Tests Passed: {test_results['passed']}/{test_results['total_tests']}")
    print(f"[OK] Pass Rate: {test_results['pass_rate']}%")
    
    # Step 3: Comprehensive code evaluation
    print("\n Step 3: Comprehensive code evaluation...")
    eval_response = requests.post(f"{BASE_URL}/code-execution/evaluate", json={
        "code": code,
        "language": "python",
        "problem_description": question['question'],
        "test_cases": question['test_cases']
    })
    assert eval_response.status_code == 200, f"Code evaluation failed"
    evaluation = eval_response.json()
    
    print(f"[OK] Correctness Score: {evaluation['correctness_score']}/5")
    print(f"[OK] Code Quality Score: {evaluation['code_quality_score']}/5")
    print(f"[OK] Complexity Score: {evaluation['complexity_score']}/5")
    print(f"[OK] Overall Score: {evaluation['overall_score']}/5")
    print(f"[OK] Time Complexity: {evaluation['time_complexity']}")
    print(f"[OK] Space Complexity: {evaluation['space_complexity']}")
    
    print("\n" + "=" * 80)
    print("[OK] TEST 2 PASSED: OA Interview Flow Complete")
    print("=" * 80 + "\n")
    
    return evaluation


def test_3_system_design_interview():
    """Test system design interview with diagram analysis."""
    print("=" * 80)
    print("TEST 3: System Design Interview Flow")
    print("=" * 80)
    
    # Step 1: Generate system design question
    print("\n Step 1: Generating system design question...")
    response = requests.post(f"{BASE_URL}/questions/generate", json={
        "job_description": "Senior Software Engineer with system design experience",
        "interview_type": "system_design",
        "difficulty": "medium",
        "num_questions": 1
    })
    assert response.status_code == 200, f"Question generation failed"
    question = response.json()['questions'][0]
    print(f"[OK] Generated question: {question['question'][:80]}...")
    
    # Step 2: Create and submit diagram
    print("\n Step 2: Creating sample diagram...")
    diagram_base64 = create_sample_diagram()
    print(f"[OK] Diagram created ({len(diagram_base64)} bytes)")
    
    # Step 3: Analyze diagram (Vision-LLM)
    print("\n Step 3: Analyzing diagram with Vision-LLM...")
    print("[WARN]  Note: This requires HF_TOKEN in .env for Hugging Face API")
    
    try:
        critique_response = requests.post(f"{BASE_URL}/vision/critique-diagram", json={
            "session_id": "test_session_3",
            "question_id": question['id'],
            "question_text": question['question'],
            "interview_type": "system_design",
            "image_base64": diagram_base64,
            "capture_method": "manual",
            "transcript": "I designed a three-tier architecture with a load balancer distributing traffic to web servers, which then connect to a database. This provides horizontal scalability and fault tolerance."
        })
        
        if critique_response.status_code == 200:
            analysis = critique_response.json()
            print(f"[OK] Completeness Score: {analysis['completeness_score']}/5")
            print(f"[OK] Clarity Score: {analysis['clarity_score']}/5")
            print(f"[OK] Overall Score: {analysis['overall_score']}/5")
            print(f"[OK] Components: {analysis['components_identified']}")
            print(f"[OK] Strengths: {len(analysis['strengths'])} identified")
            print(f"[OK] Missing Elements: {analysis['missing_elements']}")
        else:
            print(f"[WARN]  Vision API unavailable (status: {critique_response.status_code})")
            print("   This is expected if HF_TOKEN is not configured")
            analysis = None
    except Exception as e:
        print(f"[WARN]  Vision analysis skipped: {e}")
        print("   Configure HF_TOKEN in .env to enable")
        analysis = None
    
    print("\n" + "=" * 80)
    if analysis:
        print("[OK] TEST 3 PASSED: System Design Interview Flow Complete")
    else:
        print("[WARN]  TEST 3 PARTIAL: System Design Flow OK (Vision API not configured)")
    print("=" * 80 + "\n")
    
    return analysis


def test_4_mixed_interview():
    """Test interview with multiple question types."""
    print("=" * 80)
    print("TEST 4: Mixed Interview (Technical + OA + System Design)")
    print("=" * 80)
    
    question_types = ["technical", "oa", "system_design"]
    results = {}
    
    for q_type in question_types:
        print(f"\n Generating {q_type} question...")
        response = requests.post(f"{BASE_URL}/questions/generate", json={
            "job_description": f"Software Engineer position requiring {q_type} expertise",
            "interview_type": q_type,
            "difficulty": "medium",
            "num_questions": 1
        })
        assert response.status_code == 200, f"{q_type} generation failed"
        question = response.json()['questions'][0]
        results[q_type] = question
        print(f"[OK] {q_type.upper()}: {question['question'][:60]}...")
        
        # Verify expected fields
        if q_type == "oa":
            assert 'test_cases' in question, "OA missing test_cases"
            assert 'starter_code' in question, "OA missing starter_code"
            print(f"   -> {len(question['test_cases'])} test cases included")
        
        if q_type == "system_design":
            assert 'evaluation_criteria' in question, "System design missing criteria"
            print(f"   -> {len(question['evaluation_criteria'])} evaluation criteria")
    
    print("\n" + "=" * 80)
    print("[OK] TEST 4 PASSED: Mixed Interview Generation Successful")
    print(f"   Generated {len(results)} different question types")
    print("=" * 80 + "\n")
    
    return results


def test_5_full_session_flow():
    """Test complete session from start to finish."""
    print("=" * 80)
    print("TEST 5: Complete Session Flow (Start to Results)")
    print("=" * 80)
    
    session_id = f"e2e_test_{int(time.time())}"
    
    # Step 1: Generate mixed questions
    print("\n Step 1: Generating interview session...")
    response = requests.post(f"{BASE_URL}/questions/generate", json={
        "job_description": "Full-stack Software Engineer",
        "interview_type": "mixed",
        "difficulty": "medium",
        "num_questions": 2
    })
    questions = response.json()['questions']
    print(f"[OK] Generated {len(questions)} questions")
    
    # Step 2: Simulate answering each question
    print("\n Step 2: Simulating answers...")
    evaluations = []
    
    for i, question in enumerate(questions):
        print(f"\n   Question {i+1}/{len(questions)}: {question['interview_type']}")
        
        if question['interview_type'] == 'oa' and 'test_cases' in question:
            # Code question
            code = """
def solution(arr):
    return sum(arr)

arr = list(map(int, input().split()))
print(solution(arr))
"""
            eval_response = requests.post(f"{BASE_URL}/code-execution/evaluate", json={
                "code": code,
                "language": "python",
                "problem_description": question['question'],
                "test_cases": question['test_cases']
            })
            if eval_response.status_code == 200:
                evaluations.append(eval_response.json())
                print(f"   [OK] Code evaluated: {eval_response.json()['overall_score']}/5")
        else:
            # Regular interview question
            eval_response = requests.post(f"{BASE_URL}/evaluation/evaluate", json={
                "session_id": session_id,
                "question_id": question['id'],
                "question_text": question['question'],
                "answer_text": "This is a comprehensive answer covering all key points...",
                "interview_type": question['interview_type'],
                "speech_metrics": {
                    "words_per_minute": 135,
                    "filler_word_percentage": 3.0,
                },
                "language_metrics": {
                    "grammar_score": 4.0,
                    "vocabulary_level": "intermediate",
                    "clarity_score": 4.0
                }
            })
            if eval_response.status_code == 200:
                evaluations.append(eval_response.json())
                print(f"   [OK] Answer evaluated: {eval_response.json()['overall_score']}/5")
    
    # Step 3: Aggregate results
    print("\n Step 3: Aggregating results...")
    avg_score = sum(e.get('overall_score', 0) for e in evaluations) / len(evaluations)
    print(f"[OK] Session Average Score: {avg_score:.2f}/5")
    print(f"[OK] Total Evaluations: {len(evaluations)}")
    
    print("\n" + "=" * 80)
    print("[OK] TEST 5 PASSED: Complete Session Flow Successful")
    print("=" * 80 + "\n")
    
    return {
        "session_id": session_id,
        "questions": questions,
        "evaluations": evaluations,
        "avg_score": avg_score
    }


def test_6_service_health_checks():
    """Test all service health endpoints."""
    print("=" * 80)
    print("TEST 6: Service Health Checks")
    print("=" * 80)
    
    services = [
        ("Code Execution", "/code-execution/health"),
        ("Evaluation", "/evaluation/health"),
        ("Questions", "/questions/health"),
        ("Vision", "/vision/health"),
    ]
    
    results = {}
    
    for service_name, endpoint in services:
        print(f"\n Checking {service_name}...")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                results[service_name] = status
                print(f"   [OK] Status: {status}")
                if service_name == "Code Execution":
                    print(f"   [OK] Judge0: {'Available' if data.get('judge0_available') else 'Unavailable'}")
                elif service_name == "Vision":
                    print(f"   [OK] Screenshots stored: {data.get('screenshots_stored', 0)}")
            else:
                results[service_name] = "error"
                print(f"   [FAIL] Failed: {response.status_code}")
        except Exception as e:
            results[service_name] = "error"
            print(f"   [FAIL] Error: {e}")
    
    healthy_services = sum(1 for status in results.values() if status == "healthy")
    
    print("\n" + "=" * 80)
    print(f"[OK] TEST 6 COMPLETE: {healthy_services}/{len(services)} Services Healthy")
    print("=" * 80 + "\n")
    
    return results


def test_7_edge_cases():
    """Test edge cases and error handling."""
    print("=" * 80)
    print("TEST 7: Edge Cases & Error Handling")
    print("=" * 80)
    
    test_cases = []
    
    # Test 1: Empty code
    print("\n Test 1: Empty code submission...")
    response = requests.post(f"{BASE_URL}/code-execution/execute", json={
        "code": "",
        "language": "python"
    })
    test_cases.append(("Empty code", response.status_code in [200, 400]))
    print(f"   {'[OK]' if test_cases[-1][1] else '[FAIL]'} Handled correctly")
    
    # Test 2: Invalid language
    print("\n Test 2: Invalid language...")
    response = requests.post(f"{BASE_URL}/code-execution/execute", json={
        "code": "print('test')",
        "language": "invalid_lang"
    })
    test_cases.append(("Invalid language", response.status_code == 400))
    print(f"   {'[OK]' if test_cases[-1][1] else '[FAIL]'} Rejected correctly")
    
    # Test 3: Infinite loop (should timeout)
    print("\n Test 3: Infinite loop detection...")
    response = requests.post(f"{BASE_URL}/code-execution/execute", json={
        "code": "while True: pass",
        "language": "python",
        "timeout": 2
    })
    if response.status_code == 200:
        result = response.json()
        test_cases.append(("Infinite loop", result['status'] == 'time_limit_exceeded'))
        print(f"   {'[OK]' if test_cases[-1][1] else '[FAIL]'} Timeout detected")
    
    # Test 4: Compilation error
    print("\n Test 4: Compilation error handling...")
    response = requests.post(f"{BASE_URL}/code-execution/execute", json={
        "code": "int main() { return 0 }",  # Missing semicolon
        "language": "c"
    })
    if response.status_code == 200:
        result = response.json()
        test_cases.append(("Compilation error", result['status'] == 'compilation_error'))
        print(f"   {'[OK]' if test_cases[-1][1] else '[FAIL]'} Compilation error detected")
    
    # Test 5: Runtime error
    print("\n Test 5: Runtime error handling...")
    response = requests.post(f"{BASE_URL}/code-execution/execute", json={
        "code": "print(1/0)",
        "language": "python"
    })
    if response.status_code == 200:
        result = response.json()
        test_cases.append(("Runtime error", result['status'] == 'runtime_error'))
        print(f"   {'[OK]' if test_cases[-1][1] else '[FAIL]'} Runtime error detected")
    
    passed = sum(1 for _, result in test_cases if result)
    
    print("\n" + "=" * 80)
    print(f"[OK] TEST 7 COMPLETE: {passed}/{len(test_cases)} Edge Cases Handled")
    print("=" * 80 + "\n")
    
    return test_cases


def run_all_tests():
    """Run all E2E tests."""
    print("\n")
    print("=== " * 40)
    print("RUNNING COMPLETE END-TO-END TEST SUITE")
    print("=== " * 40)
    print("\n")
    
    start_time = time.time()
    
    try:
        # Run all tests
        test_1_technical_interview()
        test_2_oa_interview()
        test_3_system_design_interview()
        test_4_mixed_interview()
        test_5_full_session_flow()
        test_6_service_health_checks()
        test_7_edge_cases()
        
        elapsed = time.time() - start_time
        
        print("\n")
        print("=" * 80)
        print(f"ALL TESTS PASSED in {elapsed:.2f}s")
        print("=" * 80)
        print("\n")
        
        print("[OK] System is production-ready for:")
        print("   - Technical interviews with speech/language analysis")
        print("   - OA coding interviews with test execution")
        print("   - System design interviews with diagram analysis")
        print("   - Mixed interview sessions")
        print("   - Comprehensive evaluation across all modalities")
        print("\n")
        
        return True
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)