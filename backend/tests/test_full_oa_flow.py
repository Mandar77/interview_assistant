# backend/tests/test_full_oa_flow.py
"""
Test full OA interview flow with code execution
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_oa_question_generation():
    """Test generating OA questions with test cases."""
    print("🧪 Testing OA Question Generation with Test Cases\n")
    
    response = requests.post(f"{BASE_URL}/questions/generate", json={
        "job_description": "Looking for a Software Engineer with strong algorithms and data structures skills",
        "interview_type": "oa",
        "difficulty": "medium",
        "num_questions": 1
    })
    
    print("✅ Question Generation Response:")
    data = response.json()
    question = data['questions'][0]
    
    print(f"Question: {question['question'][:100]}...")
    print(f"Test Cases: {len(question.get('test_cases', []))}")
    print(f"Starter Code Languages: {list(question.get('starter_code', {}).keys())}")
    print()
    
    return question


def test_code_execution(question):
    """Test code execution with generated test cases."""
    print("🧪 Testing Code Execution\n")
    
    # Sample solution for two-sum
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
    
    response = requests.post(f"{BASE_URL}/code-execution/execute-tests", json={
        "code": code,
        "language": "python",
        "test_cases": question['test_cases']
    })
    
    result = response.json()
    print("✅ Execution Results:")
    print(f"Tests Passed: {result['passed']}/{result['total_tests']}")
    print(f"Pass Rate: {result['pass_rate']}%")
    print(f"Total Time: {result['total_time']}s")
    print()
    
    return result


def test_code_evaluation(question):
    """Test comprehensive code evaluation."""
    print("🧪 Testing Code Evaluation\n")
    
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
    
    response = requests.post(f"{BASE_URL}/code-execution/evaluate", json={
        "code": code,
        "language": "python",
        "problem_description": question['question'],
        "test_cases": question['test_cases']
    })
    
    evaluation = response.json()
    print("✅ Code Evaluation:")
    print(f"Correctness Score: {evaluation['correctness_score']}/5")
    print(f"Code Quality Score: {evaluation['code_quality_score']}/5")
    print(f"Complexity Score: {evaluation['complexity_score']}/5")
    print(f"Overall Score: {evaluation['overall_score']}/5")
    print(f"Time Complexity: {evaluation['time_complexity']}")
    print(f"Space Complexity: {evaluation['space_complexity']}")
    print(f"Feedback: {evaluation['feedback']}")
    print()


if __name__ == "__main__":
    print("🚀 Testing Full OA Interview Flow\n")
    print("="*60)
    
    # Step 1: Generate OA question
    question = test_oa_question_generation()
    
    # Step 2: Execute code with test cases
    test_code_execution(question)
    
    # Step 3: Comprehensive evaluation
    test_code_evaluation(question)
    
    print("="*60)
    print("✅ All OA flow tests completed!")