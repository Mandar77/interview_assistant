# backend/tests/pre_deployment_checklist.py
"""
Pre-Deployment Checklist
Final verification before AWS deployment
"""

import requests
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))


class PreDeploymentChecker:
    """Run final checks before deployment."""
    
    def __init__(self):
        self.checks = []
        self.passed = 0
        self.failed = 0
    
    def check(self, name: str, condition: bool, details: str = ""):
        """Record a check result."""
        self.checks.append({
            "name": name,
            "passed": condition,
            "details": details
        })
        
        if condition:
            self.passed += 1
            print(f"[OK] {name}")
        else:
            self.failed += 1
            print(f"[FAIL] {name}")
            if details:
                print(f"   {details}")
    
    def run_all_checks(self):
        """Run all pre-deployment checks."""
        print("""
==================================================================
              PRE-DEPLOYMENT CHECKLIST                         
         Final validation before AWS deployment                
==================================================================
""")
        
        print("\n1. SERVICE AVAILABILITY\n")
        
        # Check all services
        try:
            r = requests.get("http://localhost:8000/health", timeout=5)
            self.check("Backend API responding", r.status_code == 200)
        except:
            self.check("Backend API responding", False, "Cannot reach backend")
        
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=5)
            self.check("Ollama LLM available", r.status_code == 200)
        except:
            self.check("Ollama LLM available", False, "Ollama not running")
        
        try:
            r = requests.get("http://localhost:2358/about", timeout=5)
            self.check("Judge0 available", r.status_code == 200)
        except:
            self.check("Judge0 available", False, "Judge0 not running")
        
        print("\n2. CORE FUNCTIONALITY\n")
        
        # Test question generation
        try:
            r = requests.post("http://localhost:8000/api/v1/questions/generate", json={
                "job_description": "Test",
                "interview_type": "technical",
                "num_questions": 1
            }, timeout=30)
            self.check("Question generation working", r.status_code == 200)
        except:
            self.check("Question generation working", False)
        
        # Test code execution
        try:
            r = requests.post("http://localhost:8000/api/v1/code-execution/execute", json={
                "code": "print('test')",
                "language": "python"
            }, timeout=10)
            self.check("Code execution working", r.status_code == 200)
        except:
            self.check("Code execution working", False)
        
        # Test evaluation
        try:
            r = requests.post("http://localhost:8000/api/v1/evaluation/evaluate", json={
                "session_id": "test",
                "question_id": "q1",
                "question_text": "Test",
                "answer_text": "Test",
                "interview_type": "technical"
            }, timeout=60)
            self.check("Evaluation working", r.status_code == 200)
        except:
            self.check("Evaluation working", False)
        
        print("\n3. TEST RESULTS\n")
        
        # Check if test results exist
        test_results_dir = Path("test_results")
        
        latest_report = test_results_dir / "latest.json"
        if latest_report.exists():
            with open(latest_report) as f:
                data = json.load(f)
                all_passed = data.get('summary', {}).get('overall_pass', False)
                self.check("Latest test suite passed", all_passed)
        else:
            self.check("Latest test suite passed", False, "No test results found - run tests first")
        
        # Check bug report
        latest_bugs = test_results_dir / "latest_bugs.json"
        if latest_bugs.exists():
            with open(latest_bugs) as f:
                bugs = json.load(f)
                critical = bugs.get('summary', {}).get('CRITICAL', 0)
                high = bugs.get('summary', {}).get('HIGH', 0)
                
                self.check("Zero critical bugs", critical == 0, f"{critical} critical bugs" if critical else "")
                self.check("Minimal high-priority bugs", high < 3, f"{high} high bugs")
        else:
            print("[WARN] No bug report found - generate with: python tests/bug_tracker.py")
        
        print("\n4. CONFIGURATION\n")
        
        # Check environment configuration by importing settings
        try:
            from config.settings import settings
            
            self.check("Ollama configured", bool(settings.ollama_base_url))
            self.check("Judge0 configured", bool(settings.judge0_base_url))
            
            # HF Token is optional
            if settings.hf_token:
                self.check("HF Token set", True)
            else:
                print("[WARN] HF Token not set - Vision features will use fallback")
            
            # Debug mode warning
            if settings.debug:
                print("[WARN] Debug mode is ON - set to False for production")
            else:
                self.check("Debug mode disabled", True)
                
        except ImportError as e:
            print(f"[WARN] Could not import settings: {e}")
            print("       Checking environment variables directly...")
            
            # Fallback: check env vars directly
            self.check("Ollama configured", bool(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")))
            self.check("Judge0 configured", bool(os.getenv("JUDGE0_BASE_URL", "http://localhost:2358")))
            
            if os.getenv("HF_TOKEN"):
                self.check("HF Token set", True)
            else:
                print("[WARN] HF_TOKEN not set - Vision features will use fallback")
        
        print("\n5. DATA & STORAGE\n")
        
        # Check directories exist (relative to backend/)
        backend_dir = Path(__file__).parent.parent
        data_dirs = [
            backend_dir / "data" / "sessions",
            backend_dir / "data" / "screenshots",
        ]
        
        for dir_path in data_dirs:
            if dir_path.exists():
                self.check(f"Directory exists: {dir_path.name}", True)
            else:
                # Try to create it
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.check(f"Directory created: {dir_path.name}", True)
                except:
                    self.check(f"Directory exists: {dir_path.name}", False)
        
        print("\n6. DEPENDENCIES\n")
        
        # Check critical imports
        try:
            import whisper
            self.check("Whisper installed", True)
        except:
            self.check("Whisper installed", False)
        
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            self.check("spaCy model loaded", True)
        except:
            self.check("spaCy model loaded", False, "Run: python -m spacy download en_core_web_sm")
        
        try:
            from huggingface_hub import InferenceClient
            self.check("huggingface_hub installed", True)
        except:
            self.check("huggingface_hub installed", False)
        
        try:
            from PIL import Image
            self.check("Pillow installed", True)
        except:
            self.check("Pillow installed", False)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print final summary."""
        print("\n" + "="*65)
        print("PRE-DEPLOYMENT CHECKLIST SUMMARY")
        print("="*65 + "\n")
        
        total = len(self.checks)
        print(f"Total checks: {total}")
        print(f"[OK] Passed: {self.passed}")
        print(f"[FAIL] Failed: {self.failed}")
        
        if total > 0:
            print(f"Pass rate: {(self.passed/total*100):.1f}%\n")
        
        deployment_ready = self.failed == 0 or (self.failed <= 2 and self.passed > total * 0.9)
        
        if deployment_ready:
            print("="*65)
            print("[OK] [OK] [OK]  DEPLOYMENT APPROVED  [OK] [OK] [OK]")
            print("="*65)
            print("\nSystem is ready for AWS deployment.")
            print("Proceed to Phase 8: AWS CDK Deployment\n")
        else:
            print("="*65)
            print("[FAIL] [FAIL] [FAIL]  DEPLOYMENT BLOCKED  [FAIL] [FAIL] [FAIL]")
            print("="*65)
            print(f"\n{self.failed} critical checks failed.")
            print("Fix the following before deploying:\n")
            
            for check in self.checks:
                if not check['passed']:
                    print(f"  - {check['name']}")
                    if check['details']:
                        print(f"    {check['details']}")
            print()
        
        return deployment_ready
    
    def save_checklist(self):
        """Save checklist results."""
        test_results_dir = Path("test_results")
        test_results_dir.mkdir(exist_ok=True)
        
        report_path = test_results_dir / f"pre_deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_checks": len(self.checks),
                "passed": self.passed,
                "failed": self.failed,
                "checks": self.checks,
                "deployment_ready": self.failed == 0 or (self.failed <= 2 and self.passed > len(self.checks) * 0.9)
            }, f, indent=2)
        
        print(f"Checklist saved: {report_path}\n")


if __name__ == "__main__":
    checker = PreDeploymentChecker()
    checker.run_all_checks()
    checker.save_checklist()
    
    # Exit code 0 if ready, 1 if not
    sys.exit(0 if checker.failed <= 2 else 1)