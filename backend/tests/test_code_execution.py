# backend/tests/test_code_execution.py
"""
Test script for code execution service
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1/code-execution"

def test_simple_execution():
    """Test simple code execution."""
    code = """
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
"""
    
    response = requests.post(f"{BASE_URL}/execute", json={
        "code": code,
        "language": "python"
    })
    
    print("✅ Simple Execution Test")
    print(json.dumps(response.json(), indent=2))
    print()


def test_with_test_cases():
    """Test execution with test cases."""
    code = """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Read input
nums = list(map(int, input().split()))
target = int(input())
result = two_sum(nums, target)
print(' '.join(map(str, result)))
"""
    
    test_cases = [
        {
            "input": "2 7 11 15\n9",
            "expected_output": "0 1",
            "description": "Basic test case"
        },
        {
            "input": "3 2 4\n6",
            "expected_output": "1 2",
            "description": "Different indices"
        }
    ]
    
    response = requests.post(f"{BASE_URL}/execute-tests", json={
        "code": code,
        "language": "python",
        "test_cases": test_cases
    })
    
    print("✅ Test Cases Execution")
    print(json.dumps(response.json(), indent=2))
    print()


def test_complexity_analysis():
    """Test complexity analysis."""
    code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""
    
    response = requests.post(f"{BASE_URL}/analyze-complexity", json={
        "code": code,
        "language": "python",
        "problem_description": "Sort an array of integers"
    })
    
    print("✅ Complexity Analysis")
    print(json.dumps(response.json(), indent=2))
    print()


def test_full_evaluation():
    """Test comprehensive code evaluation."""
    code = """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

# Read input
arr = list(map(int, input().split()))
target = int(input())
result = binary_search(arr, target)
print(result)
"""
    
    test_cases = [
        {
            "input": "1 2 3 4 5 6 7 8 9\n5",
            "expected_output": "4"
        },
        {
            "input": "1 2 3 4 5 6 7 8 9\n1",
            "expected_output": "0"
        },
        {
            "input": "1 2 3 4 5 6 7 8 9\n10",
            "expected_output": "-1"
        }
    ]
    
    response = requests.post(f"{BASE_URL}/evaluate", json={
        "code": code,
        "language": "python",
        "problem_description": "Implement binary search in a sorted array",
        "test_cases": test_cases
    })
    
    print("✅ Full Code Evaluation")
    print(json.dumps(response.json(), indent=2))
    print()


if __name__ == "__main__":
    print("🧪 Testing Code Execution Service\n")
    
    test_simple_execution()
    test_with_test_cases()
    test_complexity_analysis()
    test_full_evaluation()
    
    print("✅ All tests completed!")