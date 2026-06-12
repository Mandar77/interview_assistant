"""
Platform E2E + unit tests (Phases 9-13) - the two-sided hiring platform.
Location: backend/tests/test_platform_e2e.py

Runs fully in-process via FastAPI's TestClient against an ISOLATED temp storage
directory, so no running server / Ollama / Judge0 is required. Auto-scored
paths (MCQ) and the full employer->candidate->recruiter flow are validated
deterministically. AI/coding scoring degrades gracefully (heuristic / skip) so
the flow never blocks when the LLM or Judge0 are offline.

Run directly:
    python tests/test_platform_e2e.py
Or via pytest:
    pytest tests/test_platform_e2e.py -v
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure backend root on path and isolate storage BEFORE importing app/db.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

_TMP = tempfile.mkdtemp(prefix="ia_platform_test_")
os.environ["STORAGE_BACKEND"] = "json"

# Point the repository + culture store at the temp dir by monkeypatching the
# module-level paths before they are first used.
import db.repository as repo_mod  # noqa: E402

repo_mod.PLATFORM_DIR = Path(_TMP)
repo_mod._repository = repo_mod.JsonRepository(Path(_TMP))

import services.culture_service.crawler as crawler_mod  # noqa: E402

crawler_mod.CULTURE_DIR = Path(_TMP) / "culture"
crawler_mod.CULTURE_DIR.mkdir(parents=True, exist_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

import app as app_mod  # noqa: E402

client = TestClient(app_mod.app)


# --------------------------------------------------------------------------
# tiny assertion helpers
# --------------------------------------------------------------------------
_passed = 0
_failed = 0


def check(name, condition, detail=""):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _failed += 1
        print(f"  [FAIL] {name} {detail}")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# UNIT TESTS - repository, security, scorer (no network)
# --------------------------------------------------------------------------
def test_unit_security():
    print("\n[UNIT] auth security primitives")
    from services.auth_service.security import (
        create_access_token,
        decode_access_token,
        hash_password,
        verify_password,
    )

    h = hash_password("hunter2hunter2")
    check("hash != plaintext", h != "hunter2hunter2")
    check("verify correct password", verify_password("hunter2hunter2", h))
    check("reject wrong password", not verify_password("nope", h))
    tok = create_access_token("u1", "candidate", None)
    payload = decode_access_token(tok)
    check("token roundtrip subject", payload and payload["sub"] == "u1")
    check("garbage token rejected", decode_access_token("garbage.token.xyz") is None)


def test_unit_scorer():
    print("\n[UNIT] attempt scorer (MCQ deterministic)")
    from services.proctoring_service.scorer import score_attempt

    assessment = {
        "id": "a1",
        "sections": [
            {
                "id": "s1",
                "questions": [
                    {
                        "id": "q1",
                        "type": "mcq",
                        "max_score": 5.0,
                        "scoring_mode": "auto",
                        "options": [
                            {"id": "o1", "text": "A", "is_correct": True},
                            {"id": "o2", "text": "B", "is_correct": False},
                        ],
                    },
                    {
                        "id": "q2",
                        "type": "mcq",
                        "max_score": 5.0,
                        "scoring_mode": "auto",
                        "options": [
                            {"id": "x1", "text": "A", "is_correct": False},
                            {"id": "x2", "text": "B", "is_correct": True},
                        ],
                    },
                ],
            }
        ],
    }
    answers = [
        {"question_id": "q1", "type": "mcq", "selected_option_ids": ["o1"]},
        {"question_id": "q2", "type": "mcq", "selected_option_ids": ["x1"]},  # wrong
    ]
    result = score_attempt(assessment, answers)
    check("scored 2 questions", len(result["per_question"]) == 2)
    check("q1 correct -> 5.0", result["per_question"][0]["score"] == 5.0)
    check("q2 wrong -> 0.0", result["per_question"][1]["score"] == 0.0)
    # half correct on 0-5 scale => 2.5
    check("overall = 2.5", result["overall_score"] == 2.5, f"got {result['overall_score']}")


def test_unit_culture_keyword_fallback():
    print("\n[UNIT] culture store keyword retrieval (offline fallback)")
    from services.culture_service.crawler import CultureStore

    store = CultureStore("unit-org")
    store.build(
        [
            "We value radical transparency and customer obsession above all.",
            "Our engineering culture prizes ownership and bias for action.",
            "We host weekly potlucks and care about work life balance.",
        ]
    )
    results = store.query("transparency and customer focus", k=2)
    check("returns up to k results", 0 < len(results) <= 2)
    check(
        "top result is relevant",
        any("transparency" in r.lower() for r in results),
        f"got {results}",
    )


# --------------------------------------------------------------------------
# E2E - full two-sided flow
# --------------------------------------------------------------------------
def test_e2e_full_platform():
    print("\n[E2E] employer -> assessment -> assign -> candidate -> submit -> recruiter")

    # 1. Employer signs up (creates org)
    r = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "recruiter@acme.com",
            "username": "recruiter1",
            "password": "password123",
            "role": "employer_admin",
            "organization_name": "Acme Test Corp",
        },
    )
    check("employer signup 200", r.status_code == 200, r.text)
    emp = r.json()
    emp_tok = emp["access_token"]
    org_id = emp["user"]["org_id"]
    check("org created", bool(org_id))

    # 2. Candidate signs up
    r = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "alice@cand.com",
            "username": "alice",
            "password": "password123",
            "role": "candidate",
        },
    )
    check("candidate signup 200", r.status_code == 200, r.text)
    cand_tok = r.json()["access_token"]

    # 3. Employer creates an assessment
    r = client.post(
        "/api/v1/assessments",
        headers=auth(emp_tok),
        json={"title": "SDE Intern Screen", "description": "45 min"},
    )
    check("create assessment 200", r.status_code == 200, r.text)
    assessment_id = r.json()["id"]

    # 4. Add an MCQ section manually (deterministic, no LLM)
    section = {
        "id": "sec1",
        "title": "Fundamentals",
        "questions": [
            {
                "id": "mcq1",
                "type": "mcq",
                "prompt": "What is the time complexity of binary search?",
                "max_score": 5.0,
                "scoring_mode": "auto",
                "options": [
                    {"id": "a", "text": "O(n)", "is_correct": False},
                    {"id": "b", "text": "O(log n)", "is_correct": True},
                    {"id": "c", "text": "O(n^2)", "is_correct": False},
                ],
                "expected_duration_mins": 2,
                "skill_tags": ["algorithms"],
                "evaluation_criteria": [],
            }
        ],
    }
    r = client.patch(
        f"/api/v1/assessments/{assessment_id}",
        headers=auth(emp_tok),
        json={
            "sections": [section],
            "permissions": {"force_fullscreen": True, "block_tab_switch": True, "watermark": True},
        },
    )
    check("add section + permissions 200", r.status_code == 200, r.text)

    # 5. Publish it
    r = client.patch(
        f"/api/v1/assessments/{assessment_id}",
        headers=auth(emp_tok),
        json={"status": "published"},
    )
    check("publish 200", r.status_code == 200, r.text)

    # 6. Cannot assign before publish is enforced (assign now should work)
    r = client.post(
        f"/api/v1/assessments/{assessment_id}/assign",
        headers=auth(emp_tok),
        json={"candidate_usernames": ["alice"]},
    )
    check("assign 200", r.status_code == 200, r.text)
    assignment_id = r.json()[0]["id"]
    check("assignment linked to candidate id", r.json()[0]["candidate_user_id"] is not None)

    # 7. Data isolation: a second org cannot see this assessment
    r = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "other@evil.com",
            "username": "otheradmin",
            "password": "password123",
            "role": "employer_admin",
            "organization_name": "Other Corp",
        },
    )
    other_tok = r.json()["access_token"]
    r = client.get(f"/api/v1/assessments/{assessment_id}", headers=auth(other_tok))
    check("cross-org access blocked (404)", r.status_code == 404, r.text)
    r = client.get("/api/v1/assessments", headers=auth(other_tok))
    check("other org sees no assessments", r.json() == [], r.text)

    # 8. Candidate sees the assignment
    r = client.get("/api/v1/workspace/my-assignments", headers=auth(cand_tok))
    check("candidate has 1 assignment", len(r.json()) == 1, r.text)

    # 9. Candidate starts the attempt; assessment view hides correct answers
    r = client.post(
        "/api/v1/workspace/attempts/start",
        headers=auth(cand_tok),
        json={"assignment_id": assignment_id},
    )
    check("start attempt 200", r.status_code == 200, r.text)
    attempt_id = r.json()["attempt_id"]
    served_q = r.json()["assessment"]["sections"][0]["questions"][0]
    check(
        "correct-answer keys stripped for candidate",
        all("is_correct" not in o for o in served_q["options"]),
        str(served_q["options"]),
    )

    # 10. Candidate triggers a proctoring event (tab switch)
    r = client.post(
        "/api/v1/workspace/events",
        headers=auth(cand_tok),
        json={"attempt_id": attempt_id, "type": "tab_switch", "detail": "switched away"},
    )
    check("log proctoring event 200", r.status_code == 200, r.text)

    # 11. Candidate submits the correct MCQ answer
    r = client.post(
        "/api/v1/workspace/attempts/submit",
        headers=auth(cand_tok),
        json={
            "attempt_id": attempt_id,
            "answers": [
                {"question_id": "mcq1", "type": "mcq", "selected_option_ids": ["b"]}
            ],
        },
    )
    check("submit attempt 200", r.status_code == 200, r.text)
    check("perfect MCQ -> overall 5.0", r.json()["overall_score"] == 5.0, r.text)

    # 12. Recruiter panel shows the candidate with score + flags
    r = client.get("/api/v1/recruiter/candidates", headers=auth(emp_tok))
    check("recruiter sees 1 candidate", len(r.json()) == 1, r.text)
    panel = r.json()[0]
    check("recruiter sees score 5.0", panel["overall_score"] == 5.0)
    check("recruiter sees tab_switch flag", panel["proctoring_summary"].get("tab_switch") == 1)

    # 13. Recruiter detail has the proctoring event timeline
    r = client.get(f"/api/v1/recruiter/candidates/{attempt_id}", headers=auth(emp_tok))
    check("recruiter detail 200", r.status_code == 200, r.text)
    check("event timeline present", len(r.json()["events"]) == 1, r.text)

    # 14. Recruiter records ADVANCE verdict + auto-email (logged, no SMTP)
    r = client.post(
        "/api/v1/recruiter/decision",
        headers=auth(emp_tok),
        json={"attempt_id": attempt_id, "verdict": "advance", "send_email": True},
    )
    check("decision 200", r.status_code == 200, r.text)
    check(
        "advance email logged/sent",
        r.json()["email"] and r.json()["email"]["status"] in ("logged", "sent"),
        r.text,
    )

    # 15. Recruiter can't decide on another org's attempt
    r = client.post(
        "/api/v1/recruiter/decision",
        headers=auth(other_tok),
        json={"attempt_id": attempt_id, "verdict": "reject"},
    )
    check("cross-org decision blocked (404)", r.status_code == 404, r.text)

    return {"org_id": org_id, "assessment_id": assessment_id, "attempt_id": attempt_id}


def test_e2e_templates_scheduler_ats():
    print("\n[E2E] templates + scheduler + ATS webhook")

    # employer
    r = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "tpl@acme.com",
            "username": "tpladmin",
            "password": "password123",
            "role": "employer_admin",
            "organization_name": "Template Corp",
        },
    )
    tok = r.json()["access_token"]
    org_id = r.json()["user"]["org_id"]

    # create + section + publish assessment
    aid = client.post(
        "/api/v1/assessments", headers=auth(tok), json={"title": "Backend L3 60min"}
    ).json()["id"]
    client.patch(
        f"/api/v1/assessments/{aid}",
        headers=auth(tok),
        json={
            "sections": [
                {
                    "id": "s",
                    "title": "Core",
                    "questions": [
                        {
                            "id": "m",
                            "type": "mcq",
                            "prompt": "Pick TCP",
                            "max_score": 5.0,
                            "scoring_mode": "auto",
                            "options": [
                                {"id": "t", "text": "TCP", "is_correct": True},
                                {"id": "u", "text": "UDP", "is_correct": False},
                            ],
                        }
                    ],
                }
            ],
            "status": "published",
        },
    )

    # save as template, list, create-from-template
    r = client.post(
        f"/api/v1/assessments/{aid}/save-as-template",
        headers=auth(tok),
        json={"name": "Backend L3 60min", "description": "reusable"},
    )
    check("save template 200", r.status_code == 200, r.text)
    template_id = r.json()["id"]
    r = client.get("/api/v1/assessments/templates/list", headers=auth(tok))
    check("list templates has 1", len(r.json()) == 1, r.text)
    r = client.post(f"/api/v1/assessments/from-template/{template_id}", headers=auth(tok))
    check("create from template 200", r.status_code == 200, r.text)
    check("template copied sections", len(r.json()["sections"]) == 1, r.text)

    # scheduler: create slot with mock meeting link
    r = client.post(
        "/api/v1/scheduler/slots",
        headers=auth(tok),
        json={
            "candidate_username": "alice",
            "start_time": "2026-06-10T10:00:00",
            "end_time": "2026-06-10T11:00:00",
            "provider": "meet",
        },
    )
    check("create slot 200", r.status_code == 200, r.text)
    check("mock meet link generated", "meet.google.com" in (r.json()["meeting_link"] or ""), r.text)
    r = client.get("/api/v1/scheduler/slots", headers=auth(tok))
    check("list slots has 1", len(r.json()) == 1, r.text)

    # ATS webhook auto-assigns
    r = client.post(
        "/api/v1/ats/webhook",
        json={
            "source": "greenhouse",
            "candidate_email": "bob@cand.com",
            "candidate_name": "Bob",
            "assessment_id": aid,
            "org_id": org_id,
        },
    )
    check("ATS webhook 200", r.status_code == 200, r.text)
    check("ATS created assignment", bool(r.json().get("assignment_id")), r.text)
    check("ATS invite email recorded", r.json()["invite_email"]["status"] in ("logged", "sent"))

    # ATS rejects unpublished/unknown assessment
    r = client.post(
        "/api/v1/ats/webhook",
        json={
            "source": "workday",
            "candidate_email": "x@y.com",
            "candidate_name": "X",
            "assessment_id": "does-not-exist",
            "org_id": org_id,
        },
    )
    check("ATS unknown assessment 404", r.status_code == 404, r.text)


def test_e2e_authz_guards():
    print("\n[E2E] authorization guards")
    # candidate cannot access employer endpoints
    r = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "guard@cand.com",
            "username": "guardcand",
            "password": "password123",
            "role": "candidate",
        },
    )
    cand_tok = r.json()["access_token"]
    r = client.get("/api/v1/assessments", headers=auth(cand_tok))
    check("candidate blocked from employer list (403)", r.status_code == 403, r.text)
    r = client.post("/api/v1/assessments", headers=auth(cand_tok), json={"title": "x"})
    check("candidate blocked from create (403)", r.status_code == 403, r.text)
    # no token at all
    r = client.get("/api/v1/assessments")
    check("no-token blocked (401)", r.status_code == 401, r.text)


def main():
    print("=" * 70)
    print("PLATFORM E2E + UNIT TEST SUITE (Phases 9-13)")
    print(f"Isolated storage: {_TMP}")
    print("=" * 70)

    test_unit_security()
    test_unit_scorer()
    test_unit_culture_keyword_fallback()
    test_e2e_full_platform()
    test_e2e_templates_scheduler_ats()
    test_e2e_authz_guards()

    print("\n" + "=" * 70)
    print(f"RESULTS: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return _failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
