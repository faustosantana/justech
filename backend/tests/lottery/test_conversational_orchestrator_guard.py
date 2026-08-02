"""Unit tests for orchestrator schema + integrity guard (no LLM calls)."""

from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.conversational_orchestrator.guard import conversational_integrity_guard
from app.lottery.ai.conversational_orchestrator.schema import (
    OrchestratorDecision,
    parse_orchestrator_decision,
)
from app.lottery.ai.investigation_workspace.schemas import InvestigationAsset


def test_schema_rejects_extra_fields():
    d, err = parse_orchestrator_decision(
        {
            "turn_type": "new_investigation",
            "subjects": ["78", "14"],
            "answer": "el 78 salió ayer",
        }
    )
    assert d is None
    assert err and "schema_invalid" in err


def test_guard_rejects_wrong_subjects_on_switch():
    state = ConversationState(active_pair=["35", "54"], active_numbers=["35", "54"])
    dec = OrchestratorDecision(
        turn_type="contextual_follow_up",
        subjects=["35", "54"],
        reuse_asset=True,
        confidence=0.9,
    )
    g = conversational_integrity_guard(
        dec,
        message="¿Cuándo coincidieron el 78 y el 14?",
        state=state,
        active_asset=InvestigationAsset(subjects=["35", "54"], relation="same_day"),
    )
    assert g["decision_rejected"] is True
    assert "explicit_subjects_mismatch" in g["reason_codes"]


def test_guard_allows_matching_new_pair():
    state = ConversationState(active_pair=["35", "54"], active_numbers=["35", "54"])
    dec = OrchestratorDecision(
        turn_type="new_investigation",
        subjects=["78", "14"],
        relation="same_day",
        reuse_asset=False,
        confidence=0.9,
        reason_codes=["explicit_pair"],
    )
    g = conversational_integrity_guard(
        dec,
        message="¿Cuándo coincidieron el 78 y el 14?",
        state=state,
        active_asset=InvestigationAsset(subjects=["35", "54"], relation="same_day"),
    )
    assert g["guard_pass"] is True


def test_chitchat_cannot_inherit_subjects():
    state = ConversationState(active_pair=["35", "54"])
    dec = OrchestratorDecision(
        turn_type="social_chitchat",
        subjects=["35", "54"],
        confidence=0.9,
    )
    g = conversational_integrity_guard(dec, message="Hola", state=state, active_asset=None)
    assert g["decision_rejected"] is True
    assert "chitchat_inherited_subjects" in g["reason_codes"]
