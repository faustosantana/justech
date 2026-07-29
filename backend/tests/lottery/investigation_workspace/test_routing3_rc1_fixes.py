"""RC1 — lottery canonicalization, explicit new investigation, pending clarification."""

from __future__ import annotations

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecisionEngine
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.conversational_router import ConversationalRouter
from app.lottery.ai.investigation_workspace.materialize import materialize_same_day_table
from app.lottery.ai.investigation_workspace.operations import apply_filters, lottery_canonical_key
from app.lottery.ai.investigation_workspace.schemas import AssetFilters
from app.lottery.ai.investigation_workspace.speech_acts import WorkspaceSpeechActDetector
from app.lottery.ai.investigation_workspace.store import clear_assets, get_active_asset, save_asset
from app.lottery.ai.official_lottery_scope import canonicalize_lottery_name
from app.lottery.ai.understanding import understand


def test_topic_switch_clears_same_day_sticky():
    """T08 after coincidence must not leave relation=same_day on the new subject."""
    st = ConversationState(
        active_numbers=["54", "94"],
        active_pair=["54", "94"],
        active_relation="same_day",
        active_filters={"relation": "same_day"},
    )
    inv = ActiveInvestigationSession(subjects=["54", "94"], relation="same_day")
    msg = "Últimas 3 del 35 en Nacional."
    from app.lottery.ai.analyst.intent_resolver import IntentResolver
    from app.lottery.ai.active_investigation.state_manager import InvestigationStateManager

    res = IntentResolver.resolve(msg, st)
    h = HermesDecisionEngine.decide(msg, state=st, investigation=inv, resolution=res)
    assert h.turn_type == "topic_switch"
    assert h.inherited_subjects == ["35"]
    assert h.inherited_relation is None
    inv2 = InvestigationStateManager().begin_or_continue(st, decision=h, message=msg)
    assert st.active_relation is None
    assert inv2 is not None and inv2.relation is None
    assert inv2.subjects == ["35"]

    # T09 refine must stay last_n on 35 — not EXPLICIT_NEW / not same_day pair
    st.last_intent = "last_n_occurrences"
    st.last_analysis = {"limit": 3, "observed": "35", "items": [{"number": "35"}] * 3}
    msg9 = "Ahora en todas las posiciones."
    r9 = ConversationalRouter.route(msg9, state=st, investigation=inv2)
    assert r9.path != "explicit_new_investigation"
    assert r9.path != "workspace_action"
    h9 = HermesDecisionEngine.decide(
        msg9, state=st, investigation=inv2, resolution=IntentResolver.resolve(msg9, st)
    )
    assert h9.inherited_subjects == ["35"]
    assert h9.inherited_relation is None


def test_factual_refine_is_not_explicit_new_research():
    st = ConversationState(active_numbers=["35"], last_intent="last_n_occurrences")
    inv = ActiveInvestigationSession(subjects=["35"])
    for msg in (
        "Ahora en todas las posiciones.",
        "Ahora en todas las loterías.",
        "En Nacional.",
    ):
        r = ConversationalRouter.route(msg, state=st, investigation=inv)
        assert r.path != "explicit_new_investigation", msg
    # Fresh last-time ask (no prior inv) is default research, not EXPLICIT_NEW
    r0 = ConversationalRouter.route("Última del 55.", state=ConversationState(), investigation=None)
    assert r0.path == "default_research"


def test_gana_mas_canonical_variants():
    variants = ["Gana Más", "Gana Mas", "gana más", "GANAMAS", "GanaMás", "gana_mas", "gana-mas"]
    keys = {lottery_canonical_key(v) for v in variants}
    assert len(keys) == 1
    assert canonicalize_lottery_name("Gana Más") == "Gana Más"
    assert canonicalize_lottery_name("GANAMAS") == "Gana Más"
    assert canonicalize_lottery_name("Gana Mas") == "Gana Más"


def test_workspace_filter_gana_mas_not_zero():
    rows = [
        {"loteria": "Gana Mas", "fecha": "2024-01-01", "numero_a": "50", "numero_b": "90"},
        {"loteria": "Quiniela Loteka", "fecha": "2024-01-02", "numero_a": "50", "numero_b": "90"},
        {"loteria": "Gana Más", "fecha": "2024-02-01", "numero_a": "50", "numero_b": "90"},
    ]
    for label in ("Gana Más", "Gana Mas", "GANAMAS", "gana más"):
        out = apply_filters(rows, AssetFilters(lottery=canonicalize_lottery_name(label) or label))
        assert len(out) >= 1, label
        assert all(lottery_canonical_key(r["loteria"]) == "gana mas" for r in out)


def test_speech_act_solo_gana_mas():
    d = WorkspaceSpeechActDetector.detect(
        "Solo Gana Más.", has_active_asset=True, has_active_investigation=True
    )
    assert d is not None
    assert d.action == "filter_results"
    assert canonicalize_lottery_name(d.filters.lottery) == "Gana Más"


def test_ahora_analiza_el_35_explicit():
    state = ConversationState(
        active_numbers=["50", "90"], active_pair=["50", "90"], active_relation="same_day"
    )
    inv = ActiveInvestigationSession(subjects=["50", "90"], relation="same_day", metric="same_day")
    items = [
        {
            "date": "2024-01-15",
            "appearances": [
                {"number": "50", "lottery": "Gana Mas", "position": 1},
                {"number": "90", "lottery": "Gana Mas", "position": 2},
            ],
        }
    ]
    save_asset(state, materialize_same_day_table(items=items, subjects=["50", "90"]))
    assert get_active_asset(state) is not None

    r = ConversationalRouter.route("Ahora analiza el 35.", state=state, investigation=inv)
    assert r.path == "explicit_new_investigation"
    d = HermesDecisionEngine.decide("Ahora analiza el 35.", state=state, investigation=inv)
    assert d.reason_code == "EXPLICIT_NEW_RESEARCH"
    assert d.inherited_subjects == ["35"]
    assert d.requires_research is True
    assert d.reuse_evidence is False

    from app.lottery.ai.active_investigation.state_manager import InvestigationStateManager

    mgr = InvestigationStateManager()
    new_inv = mgr.begin_or_continue(
        state, decision=d, message="Ahora analiza el 35.", conversation_id="t"
    )
    assert new_inv is not None
    assert new_inv.subjects == ["35"]
    assert state.active_numbers == ["35"]
    assert get_active_asset(state) is None


def test_pending_clarification_subjects_flow():
    state = ConversationState()
    u1, s1 = understand("Analiza coincidencias.", state)
    assert u1.needs_clarification is True
    assert s1.pending_intent == "same_day_coincidence"
    assert set(s1.pending_slots) >= {"number_a", "number_b"}
    assert (u1.params or {}).get("routing_reason_code") == "PENDING_CLARIFICATION_ASK"

    r = ConversationalRouter.route(
        "50 y 90", state=s1, investigation=None, pending_clarification=True
    )
    assert r.path == "analytical_clarification"
    assert r.reason_code == "PENDING_CLARIFICATION_MATCH"

    u2, s2 = understand("50 y 90", s1)
    assert s2.pending_slots == []
    assert s2.pending_intent is None
    assert s2.active_numbers[:2] == ["50", "90"]
    assert (u2.params or {}).get("routing_reason_code") == "PENDING_CLARIFICATION_MATCH"
    assert (u2.params or {}).get("relation") == "same_day"


def test_pending_clarification_lottery_flow():
    state = ConversationState(
        pending_intent="last_occurrence",
        pending_slots=["lottery"],
        clarification_question="¿Qué lotería deseas consultar?",
        active_numbers=["54"],
        pending_params={"number": "54"},
    )
    r = ConversationalRouter.route(
        "Gana Más.", state=state, investigation=None, pending_clarification=True
    )
    assert r.path == "analytical_clarification"
    assert r.reason_code == "PENDING_CLARIFICATION_MATCH"
    u, s = understand("Gana Más.", state)
    assert "lottery" not in (s.pending_slots or [])
    assert canonicalize_lottery_name(s.active_lotteries[0]) == "Gana Más"
