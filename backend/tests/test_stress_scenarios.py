# backend/tests/test_stress_scenarios.py
"""
Stress Testing - Specific Problem Scenarios
Tests system under stress conditions
"""

import requests
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"


def stress_test_rapid_submissions():
    """Test rapid repeated submissions."""
    print("\n" + "="*80)
    print("STRESS TEST: Rapid Repeated Submissions")
    print("="*80 + "\n")
    
    print("Simulating user rapidly clicking 'Run Code' button 20 times...")
    
    code = "print('test')"
    failures = 0
    response_times = []
    
    for i in range(20):
        try:
            start = time.time()
            response = requests.post(f"{BASE_URL}/code-execution/execute", json={
                "code": code,
                "language": "python"
            }, timeout=10)
            
            elapsed = time.time() - start
            response_times.append(elapsed)
            
            if response.status_code != 200:
                failures += 1
                print(f"  ❌ Request {i+1} failed: HTTP {response.status_code}")
            elif (i + 1) % 5 == 0:
                print(f"  ✅ {i+1}/20 requests completed")
                
        except Exception as e:
            failures += 1
            print(f"  ❌ Request {i+1} error: {e}")
    
    print(f"\n📊 Results:")
    print(f"   Success rate: {((20-failures)/20*100):.1f}%")
    print(f"   Avg response time: {sum(response_times)/len(response_times):.3f}s" if response_times else "   No successful requests")
    
    if failures > 2:
        print(f"   ⚠️  WARNING: {failures} failures suggests rate limiting or resource issues")
    else:
        print(f"   ✅ PASS: System handled rapid submissions well")


def stress_test_concurrent_users():
    """Simulate multiple concurrent users."""
    print("\n" + "="*80)
    print("STRESS TEST: 10 Concurrent Users")
    print("="*80 + "\n")
    
    print("Simulating 10 users all starting interviews simultaneously...")
    
    def simulate_user(user_id: int):
        """Simulate one user's flow."""
        try:
            # Generate questions
            gen_response = requests.post(f"{BASE_URL}/questions/generate", json={
                "job_description": f"User {user_id} job description",
                "interview_type": random.choice(["technical", "oa", "behavioral"]),
                "num_questions": 1
            }, timeout=45)
            
            if gen_response.status_code != 200:
                return (user_id, False, "Generation failed")
            
            # Quick evaluation
            eval_response = requests.post(f"{BASE_URL}/evaluation/evaluate", json={
                "session_id": f"user_{user_id}",
                "question_id": "q1",
                "question_text": "Test question",
                "answer_text": "Test answer",
                "interview_type": "technical"
            }, timeout=60)
            
            if eval_response.status_code != 200:
                return (user_id, False, "Evaluation failed")
            
            return (user_id, True, "")
            
        except Exception as e:
            return (user_id, False, str(e))
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(simulate_user, i) for i in range(10)]
        results = [f.result() for f in futures]
    
    elapsed = time.time() - start_time
    
    successful = sum(1 for _, success, _ in results if success)
    
    print(f"\n📊 Results ({elapsed:.2f}s total):")
    print(f"   Successful users: {successful}/10")
    print(f"   Failed users: {10-successful}/10")
    
    if successful < 8:
        print(f"   ⚠️  WARNING: System struggled with concurrent load")
        for user_id, success, error in results:
            if not success:
                print(f"      User {user_id}: {error}")
    else:
        print(f"   ✅ PASS: System handled concurrent users well")


def stress_test_large_payloads():
    """Test with very large payloads."""
    print("\n" + "="*80)
    print("STRESS TEST: Large Payloads")
    print("="*80 + "\n")
    
    # Test 1: Very long transcript (10,000 words)
    print("Test 1: 10,000 word transcript...")
    long_transcript = " ".join(random.choices(string.ascii_lowercase, k=50000))
    
    try:
        start = time.time()
        response = requests.post(f"{BASE_URL}/evaluation/evaluate", json={
            "session_id": "large_payload_test",
            "question_id": "q1",
            "question_text": "Test",
            "answer_text": long_transcript,
            "interview_type": "technical"
        }, timeout=120)
        
        elapsed = time.time() - start
        
        if response.status_code == 200:
            print(f"   ✅ PASS: Handled 50KB transcript in {elapsed:.2f}s")
        else:
            print(f"   ❌ FAIL: HTTP {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"   ❌ FAIL: Timeout (>120s)")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    # Test 2: Very large code file (5000 lines)
    print("\nTest 2: 5000-line code file...")
    large_code = "# Comment\n" * 5000 + "print('test')"
    
    try:
        start = time.time()
        response = requests.post(f"{BASE_URL}/code-execution/execute", json={
            "code": large_code,
            "language": "python"
        }, timeout=30)
        
        elapsed = time.time() - start
        
        if response.status_code == 200:
            print(f"   ✅ PASS: Handled large code file in {elapsed:.2f}s")
        else:
            print(f"   ⚠️  Status: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")


def stress_test_edge_case_combinations():
    """Test unusual combinations of inputs."""
    print("\n" + "="*80)
    print("STRESS TEST: Edge Case Combinations")
    print("="*80 + "\n")
    
    test_cases = [
        {
            "name": "All metrics at extremes (high)",
            "payload": {
                "session_id": "extreme_high",
                "question_id": "q1",
                "question_text": "Test",
                "answer_text": "Test",
                "speech_metrics": {
                    "words_per_minute": 300,  # Very fast
                    "filler_word_percentage": 25.0  # High fillers
                },
                "language_metrics": {
                    "grammar_score": 5.0,
                    "clarity_score": 5.0
                },
                "body_language_metrics": {
                    "eye_contact_percentage": 100,
                    "posture_score": 5.0
                }
            }
        },
        {
            "name": "All metrics at extremes (low)",
            "payload": {
                "session_id": "extreme_low",
                "question_id": "q1",
                "question_text": "Test",
                "answer_text": "Test",
                "speech_metrics": {
                    "words_per_minute": 50,  # Very slow
                    "filler_word_percentage": 0.0
                },
                "language_metrics": {
                    "grammar_score": 0.0,
                    "clarity_score": 0.0
                },
                "body_language_metrics": {
                    "eye_contact_percentage": 0,
                    "posture_score": 0.0
                }
            }
        },
        {
            "name": "Missing optional metrics",
            "payload": {
                "session_id": "minimal",
                "question_id": "q1",
                "question_text": "Test",
                "answer_text": "Test",
                "interview_type": "technical"
                # No metrics provided
            }
        },
        {
            "name": "Unicode and special characters",
            "payload": {
                "session_id": "unicode_test",
                "question_id": "q1",
                "question_text": "Explain 数据结构 and algorithmes 🚀",
                "answer_text": "The answer includes émojis 😊 and spëcial çhars",
                "interview_type": "technical"
            }
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/evaluation/evaluate",
                json=test['payload'],
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                score = data.get('overall_score', -1)
                
                if 0 <= score <= 5:
                    print(f"   ✅ PASS: Valid score {score}/5")
                else:
                    print(f"   ❌ FAIL: Invalid score {score}")
            else:
                print(f"   ❌ FAIL: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ FAIL: {e}")


def run_all_stress_tests():
    """Run all stress tests."""
    print("\n")
    print("💪" * 40)
    print("STRESS TESTING SUITE")
    print("💪" * 40)
    print("\n")
    
    print("⚠️  WARNING: These tests will stress the system")
    print("   Monitor backend logs and resource usage\n")
    
    stress_test_rapid_submissions()
    stress_test_concurrent_users()
    stress_test_large_payloads()
    stress_test_edge_case_combinations()
    
    print("\n" + "="*80)
    print("✅ STRESS TESTING COMPLETE")
    print("="*80)
    print("\nCheck for:")
    print("  • No crashes or hangs")
    print("  • Graceful error handling")
    print("  • Reasonable response times under load")
    print("  • Memory usage remains stable")


if __name__ == "__main__":
    run_all_stress_tests()