# backend/tests/quick_test.py
"""
Quick Test Runner
Fast validation during development (runs in <60s)
"""

import sys
import requests


class Colors:
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def quick_test():
    """Run quick validation tests."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    QUICK VALIDATION TEST                      ║
║              (For rapid development iteration)                ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    print("Running quick validation...\n")
    
    all_passed = True
    
    # Test 1: Services Health
    print("Testing Services Health...", end=" ")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print(f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} (HTTP {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} ({e})")
        all_passed = False
    
    # Test 2: Ollama LLM
    print("Testing Ollama LLM...", end=" ")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print(f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} (HTTP {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} ({e})")
        all_passed = False
    
    # Test 3: Judge0
    print("Testing Judge0...", end=" ")
    try:
        response = requests.get("http://localhost:2358/about", timeout=5)
        if response.status_code == 200:
            print(f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} (HTTP {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} ({e})")
        all_passed = False
    
    # Test 4: Code Execution
    print("Testing Code Execution...", end=" ")
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/code-execution/execute",
            json={"code": "print(1)", "language": "python"},
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "accepted":
                print(f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} (status: {data.get('status')})")
                all_passed = False
        else:
            print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} (HTTP {response.status_code})")
            all_passed = False
    except Exception as e:
        print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} ({e})")
        all_passed = False
    
    # Test 5: Question Generation (longer timeout)
    print("Testing Question Generation...", end=" ")
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/questions/generate",
            json={
                "job_description": "Software Engineer",
                "interview_type": "technical",
                "num_questions": 1
            },
            timeout=45  # LLM can be slow
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("questions") and len(data["questions"]) > 0:
                print(f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} (no questions generated)")
                all_passed = False
        else:
            print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} (HTTP {response.status_code})")
            all_passed = False
    except requests.exceptions.Timeout:
        print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} (timeout - LLM might be slow)")
        all_passed = False
    except Exception as e:
        print(f"{Colors.FAIL}❌ FAIL{Colors.ENDC} ({e})")
        all_passed = False
    
    # Summary
    print("\n" + "="*65)
    if all_passed:
        print(f"{Colors.OKGREEN}{Colors.BOLD}✅ QUICK TEST PASSED - Core functionality working{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}❌ QUICK TEST FAILED - Check services above{Colors.ENDC}")
    print("="*65 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)