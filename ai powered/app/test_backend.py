import os
import shutil
import sys
import types

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "app"))

sys.modules.setdefault(
    "ollama",
    types.SimpleNamespace(chat=lambda *args, **kwargs: None, list=lambda: {"models": []}, pull=lambda model: None),
)
sys.modules.setdefault(
    "rag_engine",
    types.SimpleNamespace(get_relevant_context=lambda query, k=2: {
        "context_text": "",
        "kb_context_found": False,
        "retrieval_score": 0.0,
        "matches": [],
    }),
)

import auth_service
import database
import llm_engine
import ticket_service


def run_backend_checks():
    print("BACKEND FEATURE CHECK")
    print("=====================")

    temp_dir = os.path.join(os.getcwd(), ".tmp_test_backend")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    database.DB_NAME = os.path.join(temp_dir, "test_support_tickets.db")
    database.init_db()
    auth_service.create_default_users()

    original_analyze = llm_engine.analyze_ticket
    original_service_analyze = ticket_service.llm_engine.analyze_ticket

    scripted_results = iter([
        {
            "category": "Network",
            "resolution_text": "Restart the VPN client and verify MFA enrollment.",
            "confidence_score": 0.82,
            "resolution_status": "resolved",
            "retrieval_score": 0.71,
            "kb_context_found": True,
            "context_matches": [],
            "suggested_kb_filename": None,
            "error": None,
        },
        {
            "category": "Network",
            "resolution_text": "Try reconnecting VPN and check your account lockout status.",
            "confidence_score": 0.41,
            "resolution_status": "tentative",
            "retrieval_score": 0.18,
            "kb_context_found": False,
            "context_matches": [],
            "suggested_kb_filename": "reset_vpn_access_guide.md",
            "error": None,
        },
        {
            "category": "Network",
            "resolution_text": "Try reconnecting VPN and check your account lockout status.",
            "confidence_score": 0.39,
            "resolution_status": "tentative",
            "retrieval_score": 0.12,
            "kb_context_found": False,
            "context_matches": [],
            "suggested_kb_filename": "reset_vpn_access_guide.md",
            "error": None,
        },
    ])

    def fake_analyze_ticket(title, description, priority, category):
        return next(scripted_results)

    llm_engine.analyze_ticket = fake_analyze_ticket
    ticket_service.llm_engine.analyze_ticket = fake_analyze_ticket

    try:
        print("[1] Submitting resolved ticket")
        resolved_ticket = ticket_service.submit_ticket(
            "VPN connected but unstable",
            "Connection drops every 5 minutes.",
            "Network",
            "Medium",
            "testuser",
        )
        assert resolved_ticket["resolution_status"] == "resolved"
        assert resolved_ticket["confidence_score"] == 0.82

        print("[2] Submitting repeated low-confidence tickets")
        tentative_ticket_1 = ticket_service.submit_ticket(
            "How to reset VPN access?",
            "Cannot sign in after password change.",
            "Network",
            "High",
            "testuser",
        )
        tentative_ticket_2 = ticket_service.submit_ticket(
            "Reset VPN access help",
            "VPN keeps rejecting credentials after reset.",
            "Network",
            "High",
            "testuser",
        )
        assert tentative_ticket_1["resolution_status"] == "tentative"
        assert tentative_ticket_2["resolution_status"] == "tentative"

        print("[3] Verifying feedback update")
        assert ticket_service.submit_feedback(resolved_ticket["id"], "helpful", "testuser") is True
        assert ticket_service.submit_feedback(resolved_ticket["id"], "not_helpful", "testuser") is False

        print("[4] Checking analytics queries")
        kpis = ticket_service.get_admin_kpis()
        gaps = ticket_service.get_knowledge_gap_groups()
        top_questions = ticket_service.get_top_questions()
        confidence = ticket_service.get_confidence_by_category()
        feedback = ticket_service.get_feedback_rollup()

        assert kpis["total_tickets"] == 3
        assert kpis["resolved_tickets"] == 1
        assert kpis["tentative_tickets"] == 2
        assert not gaps.empty
        assert gaps.iloc[0]["occurrence_count"] == 2
        assert not top_questions.empty
        assert not confidence.empty
        assert not feedback.empty

        print("FINAL RESULT: PASS")
    finally:
        llm_engine.analyze_ticket = original_analyze
        ticket_service.llm_engine.analyze_ticket = original_service_analyze
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_backend_checks()
