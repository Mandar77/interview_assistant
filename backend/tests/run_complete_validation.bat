# backend/tests/run_complete_validation.sh (or .bat for Windows)

#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         INTERVIEW ASSISTANT - COMPLETE VALIDATION            ║"
echo "║                  Pre-Deployment Testing                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Create results directory
mkdir -p test_results

# Step 1: Prerequisites
echo "Step 1/6: Checking prerequisites..."
python tests/pre_deployment_checklist.py --quick-check
if [ $? -ne 0 ]; then
    echo "❌ Prerequisites not met. Exiting."
    exit 1
fi

# Step 2: Quick smoke test
echo ""
echo "Step 2/6: Running quick smoke test..."
python tests/quick_test.py
if [ $? -ne 0 ]; then
    echo "⚠️  Quick test failed. Continue? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# Step 3: Core functionality tests
echo ""
echo "Step 3/6: Running core functionality tests..."
python tests/test_e2e_interview_flow.py
E2E_RESULT=$?

# Step 4: Integration tests
echo ""
echo "Step 4/6: Running integration tests..."
python tests/test_integration_complete.py
INTEGRATION_RESULT=$?

# Step 5: Data consistency
echo ""
echo "Step 5/6: Validating data consistency..."
python tests/test_data_consistency.py
DATA_RESULT=$?

# Step 6: Generate reports
echo ""
echo "Step 6/6: Generating bug reports..."
python tests/bug_tracker.py

# Final summary
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    VALIDATION COMPLETE                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [ $E2E_RESULT -eq 0 ] && [ $INTEGRATION_RESULT -eq 0 ] && [ $DATA_RESULT -eq 0 ]; then
    echo "✅ ✅ ✅  ALL AUTOMATED TESTS PASSED  ✅ ✅ ✅"
    echo ""
    echo "Next steps:"
    echo "  1. Run manual UI testing (see frontend/TESTING_GUIDE.md)"
    echo "  2. Review bug report: test_results/LATEST_BUG_REPORT.md"
    echo "  3. If all clear, proceed to Phase 8 deployment"
    echo ""
    exit 0
else
    echo "❌ SOME TESTS FAILED"
    echo ""
    echo "Review logs above and:"
    echo "  1. Fix failing tests"
    echo "  2. Re-run: ./tests/run_complete_validation.sh"
    echo "  3. Check bug report: test_results/LATEST_BUG_REPORT.md"
    echo ""
    exit 1
fi