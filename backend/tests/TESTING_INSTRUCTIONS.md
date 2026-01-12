# backend/tests/TESTING_INSTRUCTIONS.md

# 🧪 Complete Testing Protocol

## Pre-Deployment Testing Checklist

This guide ensures thorough testing before AWS deployment.

---

## 🎯 Testing Phases

### Phase 1: Environment Verification (5 minutes)
```powershell
# 1. Check all services are running
docker ps  # Should show 4 Judge0 containers

# 2. Test backend health
curl http://localhost:8000/health

# 3. Test frontend loads
# Open browser: http://localhost:5173

# 4. Check Ollama
ollama list  # Should show llama3.2
```

**✅ Checkpoint:** All services responding

---

### Phase 2: Automated Backend Tests (20-30 minutes)

Run tests in this order:
```powershell
cd backend

# Test 1: E2E Interview Flows (most important)
python tests\test_e2e_interview_flow.py
# Expected: ALL TESTS PASSED in ~110-150s
# ✅ All 7 test suites should pass

# Test 2: Integration Tests
python tests\test_integration_complete.py
# Expected: 40-50 tests pass
# ⚠️  Watch for any FAIL messages

# Test 3: Frontend Flow Simulation
python tests\test_frontend_e2e_simulation.py
# Expected: All flows complete successfully
# ⚠️  Check for CRITICAL bugs

# Test 4: Data Consistency
python tests\test_data_consistency.py
# Expected: No critical/high issues

# Test 5: Code Execution Specific
python tests\test_code_execution.py
# Expected: All 4 tests pass with 100% success
```

**After each test:**
- [ ] Note any failures
- [ ] Check backend logs for errors
- [ ] Document any bugs found

---

### Phase 3: Stress Testing (30-45 minutes)

**⚠️  Warning:** These tests create heavy load. Close other applications.
```powershell
# Stress tests
python tests\test_stress_scenarios.py
# Watch for:
# - System doesn't crash
# - Response times stay reasonable
# - No memory leaks

# Performance tests
python tests\test_performance_load.py
# Warning: This will take 10-15 minutes
# Watch Task Manager/Activity Monitor for memory spikes
```

**Monitor during stress tests:**
- [ ] Backend memory usage (should stay <1GB)
- [ ] CPU usage (spikes are OK, but should return to normal)
- [ ] Response times don't degrade significantly
- [ ] No crashes or hangs

---

### Phase 4: Manual UI Testing (45-60 minutes)

Follow the detailed checklist in `frontend/TESTING_GUIDE.md`

**Test each interview type:**

#### 4.1 Technical Interview (15 min)
- [ ] Complete from start to finish
- [ ] Verify camera works
- [ ] Verify audio recording works
- [ ] Check MediaPipe metrics update
- [ ] Verify results display correctly

#### 4.2 OA (Coding) Interview (15 min)
- [ ] Test code editor loads
- [ ] Write and execute code
- [ ] Test multiple languages (Python, Java, C++)
- [ ] Verify test results display
- [ ] Check code evaluation scores

#### 4.3 System Design Interview (15 min)
- [ ] Test Excalidraw loads
- [ ] Draw a simple diagram
- [ ] Capture diagram (test both manual and auto)
- [ ] Verify diagram analysis works
- [ ] Check results include diagram critique

#### 4.4 Error Scenarios (10 min)
- [ ] Deny microphone permission
- [ ] Deny camera permission
- [ ] Deny screen share permission
- [ ] Test with empty inputs
- [ ] Test rapid button clicking
- [ ] Test browser refresh mid-interview

---

### Phase 5: Integration Testing (15 minutes)

Test frontend-backend integration:
```powershell
# Run while frontend is open and you're doing manual testing
cd backend
python tests\test_integration_complete.py

# This runs while you use the UI to catch integration bugs
```

---

### Phase 6: Generate Bug Reports (5 minutes)
```powershell
# Aggregate all bug reports
python tests\bug_tracker.py

# This creates:
# - test_results/LATEST_BUG_REPORT.md (human-readable)
# - test_results/latest_bugs.json (machine-readable)
```

**Review the report:**
- [ ] Check CRITICAL bugs (must fix)
- [ ] Check HIGH bugs (should fix)
- [ ] Prioritize fixes

---

## 📊 Success Criteria

### ✅ Ready for Deployment When:

- [ ] **All automated tests pass** (0 failures)
- [ ] **0 CRITICAL bugs**
- [ ] **<3 HIGH bugs** (and documented)
- [ ] **Manual UI tests complete** with no blockers
- [ ] **Performance acceptable**:
  - Question generation: <20s
  - Code execution: <5s
  - Evaluation: <60s
  - Page loads: <3s
- [ ] **No memory leaks** detected
- [ ] **Concurrent load handled** (>90% success rate)
- [ ] **Error handling graceful** (no crashes)

### ⚠️  Acceptable Issues:

- Medium/Low priority bugs (if documented)
- Cosmetic UI issues
- Performance slightly above targets under heavy load
- Vision API degraded (has fallback)

### ❌ Deployment Blockers:

- Any CRITICAL bugs
- >5 HIGH bugs
- System crashes under normal load
- Data loss or corruption
- Security vulnerabilities (XSS, injection)
- Broken core features (recording, evaluation, code execution)

---

## 🐛 Bug Reporting Template

For manual testing bugs, use this template:
```markdown
## Bug #[NUMBER]

**Severity:** [CRITICAL/HIGH/MEDIUM/LOW]
**Component:** [Frontend/Backend/Integration]
**Discovered During:** [Which test/scenario]

### Steps to Reproduce
1. 
2. 
3. 

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Console Errors
```
[Paste any console errors]
```

### Screenshots/Video
[Attach if helpful]

### Workaround
[If any workaround exists]

### Fix Priority
- [ ] Must fix before deployment
- [ ] Should fix before deployment
- [ ] Can fix post-deployment
```

---

## 📈 Tracking Progress

Create a simple tracking sheet:

| Bug ID | Severity | Component | Description | Status | Fixed By |
|--------|----------|-----------|-------------|--------|----------|
| 1 | CRITICAL | Backend | Session data loss | 🔴 Open | - |
| 2 | HIGH | Frontend | Camera restart loop | ✅ Fixed | Mandar |
| 3 | MEDIUM | UI | Button alignment off | 🔴 Open | - |

---

## 🚀 Final Sign-Off

Before deployment, ensure:

- [ ] All test suites run successfully
- [ ] Bug report reviewed and triaged
- [ ] Critical/High bugs fixed or mitigated
- [ ] Performance benchmarks met
- [ ] Manual UI testing complete
- [ ] Team review of test results
- [ ] Backup plan documented
- [ ] Rollback procedure defined

**Signed off by:** ___________________
**Date:** ___________________
**Deployment approved:** YES / NO