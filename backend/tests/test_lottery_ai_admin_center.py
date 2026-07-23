"""Tests for Lottery AI Admin Center (unit-level, no DB)."""

from __future__ import annotations

from app.core.admin_permissions import role_has_permission
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.understanding import understand
from app.services.lottery_ai_admin_service import MEMORY_UAT_CASES, SAFETY_TEST_CASES
from app.lottery.ai.domain_classifier import classify_domain


def test_ai_admin_permissions_for_owner():
    assert role_has_permission("owner", "lottery_admin_ai")
    assert role_has_permission("admin", "lottery_admin_prompts")
    assert not role_has_permission("lottery_client", "lottery_admin_ai")
    assert not role_has_permission("lottery_client", "lottery_admin_safety")


def test_safety_cases_pass():
    for case in SAFETY_TEST_CASES:
        d = classify_domain(case["q"])
        assert d.classification == case["expect"], (case["q"], d.classification)


def test_permanent_memory_uat_case_shape():
    case = MEMORY_UAT_CASES[0]
    assert len(case["turns"]) == 3
    state = ConversationState()
    r1, state = understand(case["turns"][0], state)
    assert r1.intent == "last_occurrence"
    r2, state = understand(case["turns"][1], state)
    assert set(r2.lotteries or state.active_lotteries) >= {"Real", "Leidsa"}
    for lot in ["Real", "Leidsa"]:
        state.remember_occurrence(lottery=lot, number="24", draw_date="2026-06-15" if lot == "Real" else "2026-07-04")
    state.active_lotteries = ["Real", "Leidsa"]
    state.active_numbers = ["24"]
    state.last_intent = "last_occurrence"
    r3, _ = understand(case["turns"][2], state)
    assert r3.intent == "post_occurrence_window"
    assert not r3.needs_clarification
