# backend/tests/run_all_tests.py
"""
Master Test Runner
Runs all test suites and generates comprehensive report
"""

import subprocess
import sys
import time
import json
import requests  # <-- THIS WAS MISSING!
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class TestSuite:
    """Represents a test suite."""
    def __init__(self, name: str, script: str, timeout: int = 300):
        self.name = name
        self.script = script
        self.timeout = timeout
        self.passed = False
        self.execution_time = 0
        self.output = ""
        self.error = ""


class MasterTestRunner:
    """Runs all test suites and generates reports."""
    
    def __init__(self):
        self.suites = [
            TestSuite("E2E Interview Flows", "test_e2e_interview_flow.py", 180),
            TestSuite("Backend Integration", "test_integration_complete.py", 300),
            TestSuite("Frontend Flow Simulation", "test_frontend_e2e_simulation.py", 120),
            TestSuite("Code Execution", "test_code_execution.py", 60),
            TestSuite("Performance & Load", "test_performance_load.py", 600),
        ]
        self.start_time = None
        self.end_time = None
    
    def run_suite(self, suite: TestSuite) -> bool:
        """Run a single test suite."""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}Running: {suite.name}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}\n")
        
        start = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, suite.script],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=suite.timeout
            )
            
            suite.execution_time = time.time() - start
            suite.output = result.stdout
            suite.error = result.stderr
            suite.passed = result.returncode == 0
            
            # Print output
            print(suite.output)
            
            if suite.error:
                print(f"\n{Colors.WARNING}Stderr:{Colors.ENDC}")
                print(suite.error)
            
            if suite.passed:
                print(f"\n{Colors.OKGREEN}[OK] {suite.name} PASSED{Colors.ENDC} ({suite.execution_time:.2f}s)")
            else:
                print(f"\n{Colors.FAIL}[FAIL] {suite.name} FAILED{Colors.ENDC} ({suite.execution_time:.2f}s)")
            
            return suite.passed
            
        except subprocess.TimeoutExpired:
            suite.execution_time = suite.timeout
            suite.passed = False
            suite.error = f"Test suite timed out after {suite.timeout}s"
            print(f"\n{Colors.FAIL}[FAIL] {suite.name} TIMEOUT{Colors.ENDC}")
            return False
            
        except Exception as e:
            suite.execution_time = time.time() - start
            suite.passed = False
            suite.error = str(e)
            print(f"\n{Colors.FAIL}[FAIL] {suite.name} ERROR: {e}{Colors.ENDC}")
            return False
    
    def run_all(self, skip_load_tests: bool = False):
        """Run all test suites."""
        self.start_time = time.time()
        
        print("\n")
        print(f"{Colors.BOLD}{'='*40}{Colors.ENDC}")
        print(f"{Colors.BOLD}MASTER TEST RUNNER - COMPLETE VALIDATION SUITE{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*40}{Colors.ENDC}")
        print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total suites: {len(self.suites)}")
        
        if skip_load_tests:
            print(f"{Colors.WARNING}[WARN]  Skipping load tests (--skip-load flag){Colors.ENDC}")
            self.suites = [s for s in self.suites if "Load" not in s.name]
        
        print("\n")
        
        # Run each suite
        for suite in self.suites:
            self.run_suite(suite)
            time.sleep(2)  # Brief pause between suites
        
        self.end_time = time.time()
        
        # Generate summary
        self.print_summary()
        
        # Generate report
        self.generate_report()
        
        # Return overall success
        return all(suite.passed for suite in self.suites)
    
    def print_summary(self):
        """Print comprehensive summary."""
        print("\n")
        print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}MASTER TEST SUMMARY{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}\n")
        
        total_time = self.end_time - self.start_time
        passed_count = sum(1 for s in self.suites if s.passed)
        failed_count = len(self.suites) - passed_count
        
        print(f"Total execution time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
        print(f"\n{Colors.OKGREEN}Passed: {passed_count}/{len(self.suites)}{Colors.ENDC}")
        print(f"{Colors.FAIL}Failed: {failed_count}/{len(self.suites)}{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}Suite Breakdown:{Colors.ENDC}")
        print(f"{'Suite':<35} {'Status':<15} {'Time':<10}")
        print("-" * 65)
        
        for suite in self.suites:
            status = f"{Colors.OKGREEN}✅ PASSED{Colors.ENDC}" if suite.passed else f"{Colors.FAIL}[FAIL] FAILED{Colors.ENDC}"
            print(f"{suite.name:<35} {status:<24} {suite.execution_time:>6.2f}s")
        
        # Overall status
        print("\n" + "="*80)
        if all(suite.passed for suite in self.suites):
            print(f"{Colors.OKGREEN}{Colors.BOLD} ALL TESTS PASSED - READY FOR DEPLOYMENT 🎉{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}{Colors.BOLD}[FAIL] SOME TESTS FAILED - FIX BEFORE DEPLOYMENT{Colors.ENDC}")
            
            failed_suites = [s for s in self.suites if not s.passed]
            print(f"\n{Colors.FAIL}Failed suites:{Colors.ENDC}")
            for suite in failed_suites:
                print(f"  • {suite.name}")
                if suite.error:
                    print(f"    Error: {suite.error[:100]}")
        
        print("="*80 + "\n")
    
    def generate_report(self):
        """Generate detailed JSON report."""
        report_dir = Path("test_results")
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"test_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_time": self.end_time - self.start_time,
            "summary": {
                "total_suites": len(self.suites),
                "passed": sum(1 for s in self.suites if s.passed),
                "failed": sum(1 for s in self.suites if not s.passed),
                "overall_pass": all(s.passed for s in self.suites)
            },
            "suites": [
                {
                    "name": s.name,
                    "script": s.script,
                    "passed": s.passed,
                    "execution_time": s.execution_time,
                    "error": s.error if not s.passed else None
                }
                for s in self.suites
            ]
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Detailed report saved: {report_path}\n")
        
        # Also save summary to latest.json for easy access
        latest_path = report_dir / "latest.json"
        with open(latest_path, 'w') as f:
            json.dump(report, f, indent=2)


def check_prerequisites():
    """Check if all prerequisites are met."""
    print(f"\n{Colors.BOLD}Checking Prerequisites...{Colors.ENDC}\n")
    
    checks = []
    
    # Check backend is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            checks.append(("Backend API", True, ""))
        else:
            checks.append(("Backend API", False, f"HTTP {response.status_code}"))
    except Exception as e:
        checks.append(("Backend API", False, str(e)))
    
    # Check Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        checks.append(("Ollama LLM", response.status_code == 200, ""))
    except:
        checks.append(("Ollama LLM", False, "Not running"))
    
    # Check Judge0
    try:
        response = requests.get("http://localhost:2358/about", timeout=5)
        checks.append(("Judge0", response.status_code == 200, ""))
    except:
        checks.append(("Judge0", False, "Not running"))
    
    # Print results
    all_passed = True
    for name, passed, error in checks:
        status = f"{Colors.OKGREEN}[OK]{Colors.ENDC}" if passed else f"{Colors.FAIL}❌{Colors.ENDC}"
        print(f"  {status} {name:<20} {error}")
        if not passed:
            all_passed = False
    
    if not all_passed:
        print(f"\n{Colors.FAIL}❌ Prerequisites not met. Start required services:{Colors.ENDC}")
        print("   1. Backend: python app.py")
        print("   2. Ollama: ollama serve")
        print("   3. Judge0: docker-compose -f docker-compose.judge0.yml up -d")
        return False
    
    print(f"\n{Colors.OKGREEN}[OK] All prerequisites met{Colors.ENDC}\n")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run complete test suite")
    parser.add_argument("--skip-load", action="store_true", help="Skip load/performance tests")
    parser.add_argument("--quick", action="store_true", help="Run only essential tests")
    args = parser.parse_args()
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Run tests
    runner = MasterTestRunner()
    
    if args.quick:
        print(f"{Colors.WARNING}Running QUICK mode (essential tests only){Colors.ENDC}")
        runner.suites = runner.suites[:3]  # Only first 3 suites
    
    success = runner.run_all(skip_load_tests=args.skip_load or args.quick)
    
    sys.exit(0 if success else 1)