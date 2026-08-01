"""Conversational integrity — explicit subjects override sticky assets."""

from __future__ import annotations

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecisionEngine
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
from app.lottery.ai.active_investigation.state_manager import InvestigationStateManager
from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackageBuilder
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.conversational_integrity import (
    asset_matches_current,
    explicit_subjects_override,
)
from app.lottery.ai.conversational_router import ConversationalRouter
from app.lottery.ai.investigation_workspace.materialize import materialize_same_day_table
from app.lottery.ai.investigation_workspace.schemas import InvestigationAsset
from app.lottery.ai.investigation_workspace.store import clear_assets, get_active_asset, save_asset
from app.lottery.ai.turn_policy import extract_subject_numbers


def _sticky_35_54() -> tuple[ConversationState, ActiveInvestigationSession, InvestigationAsset]:
    state = ConversationState(
        active_numbers=["35", "54"],
        active_pair=["35", "54"],
        active_relation="same_day",
    )
    inv = ActiveInvestigationSession(
        subjects=["35", "54"], relation="same_day", metric="same_day"
    )
    items = [
        {
            "date": "2024-01-01",
            "lottery": "Leidsa",
            "numbers": ["35", "54"],
        }
    ] * 3
    asset = materialize_same_day_table(items=items, subjects=["35", "54"], title="35 y 54")
    save_asset(state, asset)
    return state, inv, asset


def _assert_subjects(got, want):
    assert sorted(got[: len(want)]) == sorted(want)


def test_helper_override_and_asset_match():
    assert explicit_subjects_override(["78", "14"], ["35", "54"]) == ["78", "14"]
    assert explicit_subjects_override(["35", "54"], ["35", "54"]) is None
    assert explicit_subjects_override(["35"], ["35", "54"]) is None
    assert explicit_subjects_override(["35"], ["50", "90"]) == ["35"]
    assert explicit_subjects_override([], ["35", "54"]) is None
    # No sticky subjects → no override (fresh research stays default_research)
    assert explicit_subjects_override(["55"], []) is None
    assert explicit_subjects_override(["78", "14"], []) is None
    a = InvestigationAsset(subjects=["35", "54"], relation="same_day", scope="official_seven")
    assert asset_matches_current(a, subjects=["35", "54"], relation="same_day")
    assert not asset_matches_current(a, subjects=["78", "14"], relation="same_day")


def test_1_35_54_then_78_14_new_investigation():
    state, inv, _asset = _sticky_35_54()
    q = "¿Cuándo fue la última vez que salieron el 78 y el 14 el mismo día?"
    parsed = extract_subject_numbers(q)
    _assert_subjects(parsed[:2], ["78", "14"])
    assert ConversationalRouter._is_new_investigation(
        q, active_pair=["35", "54"], inv_active=True
    )
    route = ConversationalRouter.route(q, state=state, investigation=inv)
    assert route.path == "explicit_new_investigation"
    _assert_subjects(route.inherited_subjects[:2], ["78", "14"])
    d = HermesDecisionEngine.decide(q, state=state, investigation=inv)
    assert d.turn_type == "new_investigation"
    assert d.reason_code == "explicit_pair_or_topic"
    _assert_subjects(d.inherited_subjects[:2], ["78", "14"])
    inv2 = InvestigationStateManager().begin_or_continue(
        state, decision=d, message=q
    )
    assert inv2 is not None
    _assert_subjects(inv2.subjects[:2], ["78", "14"])
    _assert_subjects(state.active_pair[:2], ["78", "14"])
    assert get_active_asset(state) is None  # prior asset cleared
    pkg_subjects = EvidencePackageBuilder._subjects(q, state, d, {"numbers": ["78", "14"]})
    _assert_subjects(pkg_subjects[:2], ["78", "14"])
    assert "35" not in pkg_subjects and "54" not in pkg_subjects


def test_2_50_90_then_22_38_new_investigation():
    state = ConversationState(
        active_numbers=["50", "90"], active_pair=["50", "90"], active_relation="same_day"
    )
    inv = ActiveInvestigationSession(subjects=["50", "90"], relation="same_day")
    asset = materialize_same_day_table(
        items=[{"date": "2024-01-01", "lottery": "Nacional", "numbers": ["50", "90"]}],
        subjects=["50", "90"],
    )
    save_asset(state, asset)
    q = "¿Han coincidido el 22 y el 38 el mismo día?"
    route = ConversationalRouter.route(q, state=state, investigation=inv)
    assert route.path == "explicit_new_investigation"
    _assert_subjects(route.inherited_subjects[:2], ["22", "38"])
    d = HermesDecisionEngine.decide(q, state=state, investigation=inv)
    _assert_subjects(d.inherited_subjects[:2], ["22", "38"])
    InvestigationStateManager().begin_or_continue(state, decision=d, message=q)
    _assert_subjects(state.active_pair[:2], ["22", "38"])
    assert get_active_asset(state) is None


def test_3_35_54_show_dates_reuses_asset():
    state, inv, asset = _sticky_35_54()
    q = "Muéstrame las fechas"
    assert not ConversationalRouter._is_new_investigation(
        q, active_pair=["35", "54"], inv_active=True
    )
    route = ConversationalRouter.route(q, state=state, investigation=inv)
    assert route.path == "workspace_action"
    _assert_subjects(route.inherited_subjects[:2], ["35", "54"])
    d = HermesDecisionEngine.decide(q, state=state, investigation=inv)
    assert d.turn_type == "asset_action"
    _assert_subjects(d.inherited_subjects[:2], ["35", "54"])
    assert get_active_asset(state) is not None
    assert asset_matches_current(
        get_active_asset(state), subjects=["35", "54"], relation="same_day"
    )
    # Frontend action subjects = sticky pair
    _assert_subjects(route.inherited_subjects[:2], asset.subjects[:2])


def test_4_35_54_ahora_analiza_35_individual():
    state, inv, _asset = _sticky_35_54()
    q = "Ahora analiza el 35"
    route = ConversationalRouter.route(q, state=state, investigation=inv)
    assert route.path == "explicit_new_investigation"
    d = HermesDecisionEngine.decide(q, state=state, investigation=inv)
    assert d.turn_type in {"topic_switch", "new_investigation"}
    assert d.inherited_subjects[:1] == ["35"]
    InvestigationStateManager().begin_or_continue(state, decision=d, message=q)
    assert state.active_numbers[:1] == ["35"]
    assert get_active_asset(state) is None


def test_5_greeting_then_show_dates_keeps_35_54():
    state, inv, asset = _sticky_35_54()
    r_hi = ConversationalRouter.route("Hola", state=state, investigation=inv)
    assert r_hi.path == "social_chitchat"
    assert r_hi.inherited_subjects == []
    # Sticky state unchanged by social
    assert state.active_pair == ["35", "54"]
    assert get_active_asset(state) is not None
    q = "Muéstrame las fechas"
    route = ConversationalRouter.route(q, state=state, investigation=inv)
    assert route.path == "workspace_action"
    _assert_subjects(route.inherited_subjects[:2], ["35", "54"])
    d = HermesDecisionEngine.decide(q, state=state, investigation=inv)
    assert d.turn_type == "asset_action"
    _assert_subjects(d.inherited_subjects[:2], ["35", "54"])
    assert asset_matches_current(asset, subjects=["35", "54"], relation="same_day")


def test_show_boot_with_new_pair_does_not_reuse_old_asset():
    state, inv, old = _sticky_35_54()
    q = "Muéstrame las fechas del 78 y el 14"
    route = ConversationalRouter.route(q, state=state, investigation=inv)
    assert route.path == "explicit_new_investigation"
    _assert_subjects(route.inherited_subjects[:2], ["78", "14"])
    d = HermesDecisionEngine.decide(q, state=state, investigation=inv)
    assert d.turn_type == "new_investigation"
    _assert_subjects(d.inherited_subjects[:2], ["78", "14"])
    InvestigationStateManager().begin_or_continue(state, decision=d, message=q)
    assert get_active_asset(state) is None
    assert not asset_matches_current(old, subjects=state.active_pair, relation="same_day")
