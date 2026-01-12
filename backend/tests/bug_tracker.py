# backend/tests/bug_tracker.py
"""
Bug Tracking and Reporting System
Aggregates bugs from all test suites and generates reports
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import os


class BugTracker:
    """Track and report bugs found during testing."""
    
    def __init__(self):
        self.bugs = []
        self.test_results_dir = Path("test_results")
        self.test_results_dir.mkdir(exist_ok=True)
    
    def load_all_bug_reports(self):
        """Load bugs from all test result files."""
        print("Loading bug reports from all test suites...")
        
        bug_files = list(self.test_results_dir.glob("*bugs*.json")) + \
                   list(self.test_results_dir.glob("*bug_report*.json"))
        
        for bug_file in bug_files:
            try:
                with open(bug_file, 'r') as f:
                    data = json.load(f)
                    
                    if isinstance(data, list):
                        self.bugs.extend(data)
                    elif isinstance(data, dict) and 'bugs' in data:
                        self.bugs.extend(data['bugs'])
                
                print(f"  ✅ Loaded: {bug_file.name}")
            except Exception as e:
                print(f"  ⚠️  Failed to load {bug_file.name}: {e}")
        
        print(f"\nTotal bugs loaded: {len(self.bugs)}\n")
    
    def categorize_bugs(self) -> Dict[str, List]:
        """Categorize bugs by severity and component."""
        categorized = {
            "CRITICAL": [],
            "HIGH": [],
            "MEDIUM": [],
            "LOW": []
        }
        
        for bug in self.bugs:
            severity = bug.get('severity', 'MEDIUM')
            categorized[severity].append(bug)
        
        return categorized
    
    def generate_markdown_report(self) -> str:
        """Generate markdown bug report."""
        categorized = self.categorize_bugs()
        
        report = f"""# 🐛 Bug Report - Interview Assistant
        
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Bugs:** {len(self.bugs)}

## Summary

| Severity | Count | Action Required |
|----------|-------|-----------------|
| CRITICAL | {len(categorized['CRITICAL'])} | ❌ Must fix before deployment |
| HIGH | {len(categorized['HIGH'])} | ⚠️  Should fix before deployment |
| MEDIUM | {len(categorized['MEDIUM'])} | 💡 Nice to fix |
| LOW | {len(categorized['LOW'])} | 📝 Optional improvements |

---

"""
        
        # Add each category
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            bugs = categorized[severity]
            if not bugs:
                continue
            
            emoji = {
                'CRITICAL': '❌',
                'HIGH': '⚠️',
                'MEDIUM': '💡',
                'LOW': '📝'
            }[severity]
            
            report += f"## {emoji} {severity} Priority\n\n"
            
            for i, bug in enumerate(bugs, 1):
                component = bug.get('component', 'Unknown')
                description = bug.get('description', bug.get('issue', 'No description'))
                details = bug.get('details', bug.get('error', ''))
                test = bug.get('test', 'Unknown test')
                
                report += f"### {i}. [{component}] {description}\n\n"
                report += f"**Test:** {test}\n\n"
                
                if details:
                    report += f"**Details:**\n```\n{details}\n```\n\n"
                
                report += "**Status:** 🔴 Open\n\n"
                report += "---\n\n"
        
        return report
    
    def generate_json_report(self) -> Dict[str, Any]:
        """Generate structured JSON report."""
        categorized = self.categorize_bugs()
        
        return {
            "generated_at": datetime.now().isoformat(),
            "total_bugs": len(self.bugs),
            "summary": {
                severity: len(bugs)
                for severity, bugs in categorized.items()
            },
            "deployment_ready": len(categorized['CRITICAL']) == 0 and len(categorized['HIGH']) < 3,
            "bugs_by_severity": categorized,
            "bugs_by_component": self._group_by_component()
        }
    
    def _group_by_component(self) -> Dict[str, List]:
        """Group bugs by component."""
        by_component = {}
        
        for bug in self.bugs:
            component = bug.get('component', 'Unknown')
            if component not in by_component:
                by_component[component] = []
            by_component[component].append(bug)
        
        return by_component
    
    def save_reports(self):
        """Save all reports."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Markdown report
        md_report = self.generate_markdown_report()
        md_path = self.test_results_dir / f"BUG_REPORT_{timestamp}.md"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_report)
        
        print(f"📄 Markdown report: {md_path}")
        
        # JSON report
        json_report = self.generate_json_report()
        json_path = self.test_results_dir / f"bug_report_{timestamp}.json"
        
        with open(json_path, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        print(f"📄 JSON report: {json_path}")
        
        # Latest symlink
        latest_md = self.test_results_dir / "LATEST_BUG_REPORT.md"
        latest_json = self.test_results_dir / "latest_bugs.json"
        
        with open(latest_md, 'w', encoding='utf-8') as f:
            f.write(md_report)
        
        with open(latest_json, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        print(f"📄 Latest reports updated")
        
        return json_report
    
    def print_summary(self):
        """Print summary to console."""
        categorized = self.categorize_bugs()
        
        print("\n" + "="*80)
        print("BUG TRACKER SUMMARY")
        print("="*80 + "\n")
        
        if not self.bugs:
            print("✅ NO BUGS FOUND - System is clean!\n")
            return True
        
        print(f"Total bugs tracked: {len(self.bugs)}\n")
        
        # Print by severity
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            bugs = categorized[severity]
            if bugs:
                print(f"{severity}: {len(bugs)} bugs")
                for bug in bugs[:3]:  # Show first 3
                    print(f"  • [{bug.get('component', 'Unknown')}] {bug.get('description', bug.get('issue', 'Unknown'))}")
                if len(bugs) > 3:
                    print(f"  ... and {len(bugs) - 3} more")
                print()
        
        # Deployment readiness
        critical_count = len(categorized['CRITICAL'])
        high_count = len(categorized['HIGH'])
        
        if critical_count == 0 and high_count == 0:
            print("✅ DEPLOYMENT READY: No critical or high-priority bugs")
            return True
        elif critical_count == 0 and high_count <= 2:
            print("⚠️  DEPLOYMENT CAUTION: Some high-priority bugs exist")
            return True
        else:
            print("❌ NOT DEPLOYMENT READY: Critical/high-priority bugs must be fixed")
            return False


def generate_all_reports():
    """Generate all bug reports."""
    print("\n")
    print("📊" * 40)
    print("BUG REPORT GENERATOR")
    print("📊" * 40)
    print("\n")
    
    tracker = BugTracker()
    tracker.load_all_bug_reports()
    
    if not tracker.bugs:
        print("✅ No bugs found in any test suite!\n")
        return True
    
    json_report = tracker.save_reports()
    deployment_ready = tracker.print_summary()
    
    return deployment_ready


if __name__ == "__main__":
    import sys
    ready = generate_all_reports()
    sys.exit(0 if ready else 1)