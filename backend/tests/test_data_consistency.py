# backend/tests/test_data_consistency.py
"""
Data Consistency Testing
Validates data integrity across the entire pipeline
"""

import os
import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"
# LLM-bound calls: generous on purpose so a timeout means 'hung', not
# 'slower than the old 3B model'. See test_integration_complete.py.
LLM_TIMEOUT = int(os.environ.get('IA_TEST_LLM_TIMEOUT', '240'))


class DataValidator:
    """Validate data consistency across services."""
    
    def __init__(self):
        self.issues = []
    
    def log_issue(self, component: str, issue: str, severity: str = "MEDIUM"):
        self.issues.append({
            "component": component,
            "issue": issue,
            "severity": severity
        })
        print(f"  ⚠️  [{severity}] {component}: {issue}")
    
    def validate_question_structure(self, question: Dict[str, Any], interview_type: str):
        """Validate question data structure."""
        print(f"\n🔍 Validating {interview_type} question structure...")
        
        # Common fields
        required_common = ['id', 'question', 'interview_type', 'difficulty', 'skill_tags', 'expected_duration_mins']
        
        for field in required_common:
            if field not in question:
                self.log_issue("Question Structure", f"Missing field: {field}", "HIGH")
            elif question[field] is None:
                self.log_issue("Question Structure", f"Null value: {field}", "MEDIUM")
            elif field in ['id', 'question'] and not question[field]:
                self.log_issue("Question Structure", f"Empty {field}", "HIGH")
        
        # Type-specific validation
        if interview_type == 'oa':
            if 'test_cases' not in question:
                self.log_issue("OA Question", "Missing test_cases", "CRITICAL")
            elif not question['test_cases']:
                self.log_issue("OA Question", "Empty test_cases array", "CRITICAL")
            else:
                # Validate test case structure
                for i, tc in enumerate(question['test_cases']):
                    if 'input' not in tc or 'expected_output' not in tc:
                        self.log_issue("Test Case", f"Test case {i} missing input/output", "HIGH")
            
            if 'starter_code' not in question:
                self.log_issue("OA Question", "Missing starter_code", "HIGH")
            elif not question['starter_code']:
                self.log_issue("OA Question", "Empty starter_code", "HIGH")
            else:
                # Check supported languages
                expected_langs = ['python', 'java', 'cpp']
                for lang in expected_langs:
                    if lang not in question['starter_code']:
                        self.log_issue("Starter Code", f"Missing {lang} template", "MEDIUM")
        
        if interview_type == 'system_design':
            if 'evaluation_criteria' not in question:
                self.log_issue("System Design", "Missing evaluation_criteria", "MEDIUM")
        
        if not self.issues:
            print("  ✅ Question structure valid")
    
    def validate_evaluation_structure(self, evaluation: Dict[str, Any]):
        """Validate evaluation data structure."""
        print(f"\n🔍 Validating evaluation structure...")
        
        required = ['engines', 'scores', 'strengths', 'weaknesses', 'evaluation_available']

        for field in required:
            if field not in evaluation:
                self.log_issue("Evaluation", f"Missing field: {field}", "HIGH")

        # A combined score must NOT come back - engines are independent.
        for banned in ('overall_score', 'weighted_score'):
            if banned in evaluation:
                self.log_issue(
                    "Evaluation",
                    f"Combined score '{banned}' should no longer be returned",
                    "HIGH"
                )

        # Every engine score is 0-100, or null when not assessed.
        engines = evaluation.get('engines', [])
        for item in engines:
            score = item.get('score')
            if score is None:
                if item.get('assessed'):
                    self.log_issue(
                        "Engine Scores",
                        f"{item.get('engine', 'unknown')} is assessed but has no score",
                        "HIGH"
                    )
                continue
            if not (0 <= score <= 100):
                self.log_issue(
                    "Engine Scores",
                    f"{item.get('engine', 'unknown')} score {score} out of range [0,100]",
                    "MEDIUM"
                )

        # The critical technical engine must always be present.
        engine_ids = [e.get('engine') for e in engines]
        if engines and 'technical' not in engine_ids:
            self.log_issue(
                "Engine Completeness",
                "Missing the critical 'technical' engine",
                "HIGH"
            )
        
        if not self.issues:
            print("  ✅ Evaluation structure valid")
    
    def validate_code_evaluation_structure(self, evaluation: Dict[str, Any]):
        """Validate code evaluation structure."""
        print(f"\n🔍 Validating code evaluation structure...")
        
        required = [
            'correctness_score', 'code_quality_score', 'complexity_score',
            'test_pass_rate', 'time_complexity', 'space_complexity',
            'passed_tests', 'total_tests', 'feedback'
        ]
        
        for field in required:
            if field not in evaluation:
                self.log_issue("Code Evaluation", f"Missing field: {field}", "HIGH")
        
        # Validate test results included
        if 'test_results' not in evaluation:
            self.log_issue("Code Evaluation", "Missing test_results field", "MEDIUM")
        
        if not self.issues:
            print("  ✅ Code evaluation structure valid")
    
    def validate_data_flow_consistency(self):
        """Validate data flows consistently through entire pipeline."""
        print("\n" + "="*80)
        print("VALIDATING: Complete Data Flow Consistency")
        print("="*80)
        
        session_id = f"consistency_test_{int(time.time())}"
        
        # Flow: Question → Answer → Evaluation → Feedback
        try:
            # Step 1: Generate
            print("\n1️⃣  Generating question...")
            gen_response = requests.post(f"{BASE_URL}/questions/generate", json={
                "job_description": "Test",
                "interview_type": "technical",
                "num_questions": 1
            }, timeout=LLM_TIMEOUT)
            
            question = gen_response.json()['questions'][0]
            question_id = question['id']
            question_text = question['question']
            
            self.validate_question_structure(question, "technical")
            
            # Step 2: Evaluate
            print("\n2️⃣  Evaluating answer...")
            eval_response = requests.post(f"{BASE_URL}/evaluation/evaluate", json={
                "session_id": session_id,
                "question_id": question_id,
                "question_text": question_text,
                "answer_text": "This is a test answer",
                "interview_type": "technical"
            }, timeout=LLM_TIMEOUT)
            
            evaluation = eval_response.json()
            
            self.validate_evaluation_structure(evaluation)
            
            # Validate session_id propagation
            if evaluation.get('session_id') != session_id:
                self.log_issue(
                    "Data Flow",
                    f"Session ID mismatch: {evaluation.get('session_id')} != {session_id}",
                    "HIGH"
                )
            
            if evaluation.get('question_id') != question_id:
                self.log_issue(
                    "Data Flow",
                    f"Question ID mismatch: {evaluation.get('question_id')} != {question_id}",
                    "HIGH"
                )
            
            # Step 3: Generate feedback
            print("\n3️⃣  Generating feedback...")
            feedback_response = requests.post(f"{BASE_URL}/feedback/generate", json={
                "session_id": session_id,
                "evaluation_result": evaluation,
                "question_text": question_text,
                "answer_text": "This is a test answer",
                "interview_type": "technical"
            }, timeout=LLM_TIMEOUT)
            
            if feedback_response.status_code == 200:
                feedback = feedback_response.json()
                
                # Validate feedback references evaluation
                if feedback.get('session_id') != session_id:
                    self.log_issue(
                        "Feedback Consistency",
                        "Session ID doesn't match",
                        "MEDIUM"
                    )
                
                # Check if feedback is meaningful
                if not feedback.get('summary'):
                    self.log_issue("Feedback Quality", "Empty summary", "MEDIUM")
                
                if not feedback.get('improvement_tips'):
                    self.log_issue("Feedback Quality", "No improvement tips", "LOW")
            
            print("\n✅ Data flow validation complete")
            
        except Exception as e:
            self.log_issue("Data Flow", f"Exception: {e}", "HIGH")
    
    def validate_oa_complete_flow(self):
        """Validate complete OA flow end-to-end."""
        print("\n" + "="*80)
        print("VALIDATING: Complete OA Data Flow")
        print("="*80)
        
        try:
            # Generate OA question
            print("\n1️⃣  Generating OA question...")
            gen_response = requests.post(f"{BASE_URL}/questions/generate", json={
                "job_description": "Algorithms expert",
                "interview_type": "oa",
                "num_questions": 1
            }, timeout=LLM_TIMEOUT)
            
            question = gen_response.json()['questions'][0]
            self.validate_question_structure(question, "oa")
            
            # Execute code
            print("\n2️⃣  Executing code...")
            exec_response = requests.post(f"{BASE_URL}/code-execution/execute-tests", json={
                "code": "print('test')",
                "language": "python",
                "test_cases": question['test_cases'][:1]  # Just test with first case
            }, timeout=15)
            
            if exec_response.status_code == 200:
                test_results = exec_response.json()
                
                # Validate structure
                if 'test_results' not in test_results:
                    self.log_issue("Test Execution", "Missing test_results array", "HIGH")
                
                # Check individual test result structure
                for tr in test_results.get('test_results', []):
                    required = ['passed', 'status', 'expected_output', 'actual_output']
                    missing = [f for f in required if f not in tr]
                    if missing:
                        self.log_issue("Test Result", f"Missing fields: {missing}", "MEDIUM")
            
            # Evaluate code
            print("\n3️⃣  Evaluating code...")
            eval_response = requests.post(f"{BASE_URL}/code-execution/evaluate", json={
                "code": "print('test')",
                "language": "python",
                "problem_description": question['question'],
                "test_cases": question['test_cases']
            }, timeout=LLM_TIMEOUT)
            
            if eval_response.status_code == 200:
                evaluation = eval_response.json()
                self.validate_code_evaluation_structure(evaluation)
            
            print("\n✅ OA flow validation complete")
            
        except Exception as e:
            self.log_issue("OA Flow", f"Exception: {e}", "HIGH")
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*80)
        print("DATA CONSISTENCY VALIDATION SUMMARY")
        print("="*80 + "\n")
        
        if not self.issues:
            print(f"✅ NO ISSUES FOUND - Data structures are consistent!\n")
            return True
        
        # Group by severity
        critical = [i for i in self.issues if i['severity'] == 'CRITICAL']
        high = [i for i in self.issues if i['severity'] == 'HIGH']
        medium = [i for i in self.issues if i['severity'] == 'MEDIUM']
        low = [i for i in self.issues if i['severity'] == 'LOW']
        
        print(f"Total issues: {len(self.issues)}\n")
        
        if critical:
            print(f"❌ CRITICAL ({len(critical)}) - Must fix:")
            for issue in critical:
                print(f"   • [{issue['component']}] {issue['issue']}")
        
        if high:
            print(f"\n⚠️  HIGH ({len(high)}) - Should fix:")
            for issue in high:
                print(f"   • [{issue['component']}] {issue['issue']}")
        
        if medium:
            print(f"\n💡 MEDIUM ({len(medium)}) - Nice to fix:")
            for issue in medium:
                print(f"   • [{issue['component']}] {issue['issue']}")
        
        if low:
            print(f"\n📝 LOW ({len(low)}) - Optional:")
            for issue in low:
                print(f"   • [{issue['component']}] {issue['issue']}")
        
        return len(critical) == 0 and len(high) == 0


def run_data_consistency_tests():
    """Run all data consistency validations."""
    print("\n")
    print("🔬" * 40)
    print("DATA CONSISTENCY VALIDATION SUITE")
    print("🔬" * 40)
    print("\n")
    
    validator = DataValidator()
    
    # Run validations
    validator.validate_data_flow_consistency()
    validator.validate_oa_complete_flow()
    
    # Print summary
    success = validator.print_summary()
    
    # Save report
    if validator.issues:
        from pathlib import Path
        report_path = Path("test_results") / f"data_consistency_{int(time.time())}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(validator.issues, f, indent=2)
        
        print(f"\n📄 Report saved: {report_path}\n")
    
    return success


if __name__ == "__main__":
    import sys
    success = run_data_consistency_tests()
    sys.exit(0 if success else 1)