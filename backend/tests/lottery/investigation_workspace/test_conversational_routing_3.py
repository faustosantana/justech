"""Conversational Routing 3.0 — social early-exit + Path A/B + cases 1–7."""

from __future__ import annotations

from app.lottery.ai.active_investigation.hermes_decision_engine import HermesDecisionEngine
from app.lottery.ai.active_investigation.session import ActiveInvestigationSession
from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.conversational_router import ConversationalRouter, detect_social_chitchat
from app.lottery.ai.investigation_workspace.materialize import materialize_same_day_table
from app.lottery.ai.investigation_workspace.speech_acts import WorkspaceSpeechActDetector
from app.lottery.ai.investigation_workspace.store import get_active_asset, save_asset
from app.lottery.ai.understanding import understand


def _inv_state() -> tuple[ConversationState, ActiveInvestigationSession]:
    state = ConversationState(
        active_numbers=["50", "90"],
        active_pair=["50", "90"],
        active_relation="same_day",
    )
    inv = ActiveInvestigationSession(
        subjects=["50", "90"], relation="same_day", metric="same_day"
    )
    return state, inv


# --- Social chitchat ---


def test_social_phrases_deterministic():
    phrases = [
        "Hola",
        "¿Cómo estás?",
        "Todo bien, ¿y tú?",
        "Gracias",
        "Perfecto",
        "Entendido",
        "Excelente",
        "Buenos días",
        "Buenas tardes",
        "Buenas noches",
        "Qué bueno",
        "Muy bien",
    ]
    for text in phrases:
        m = detect_social_chitchat(text)
        assert m is not None, text
        assert m.reason_code == "SOCIAL_CHITCHAT_MATCH"
        assert "Hallazgos" not in m.reply
        assert "50" not in m.reply and "90" not in m.reply


def test_todo_bien_not_clarification_with_sticky():
    state, _inv = _inv_state()
    understanding, out_state = understand("Todo bien, ¿y tú?", state)
    assert understanding.intent in {"greeting", "general_chat"}
    assert (understanding.params or {}).get("routing_intent") == "social_chitchat"
    assert understanding.numbers in (None, [], ())
    # Sticky preserved in state, not consumed into understanding numbers
    assert out_state.active_numbers == ["50", "90"]
    reply = (understanding.params or {}).get("conversational_reply") or ""
    assert "50" not in reply and "90" not in reply
    assert "Hallazgos" not in reply


def test_excelente_is_social_not_clarification():
    state = ConversationState(pending_intent="last_occurrence", pending_slots=["lottery"])
    r = ConversationalRouter.route("Excelente.", state=state, investigation=None)
    assert r.path == "social_chitchat"
    assert r.reason_code == "SOCIAL_CHITCHAT_MATCH"
    understanding, _ = understand("Excelente.", state)
    assert (understanding.params or {}).get("routing_intent") == "social_chitchat"


def test_gana_mas_pending_is_analytical_clarification():
    state = ConversationState(
        pending_intent="last_occurrence",
        pending_slots=["lottery"],
        clarification_question="¿Qué lotería deseas consultar?",
    )
    r = ConversationalRouter.route(
        "Gana Más.", state=state, investigation=None, pending_clarification=True
    )
    assert r.path == "analytical_clarification"
    assert r.reason_code == "PENDING_CLARIFICATION_MATCH"


def test_router_priority_social_before_workspace():
    state, inv = _inv_state()
    items = [
        {
            "date": "2024-01-15",
            "appearances": [
                {"number": "50", "lottery": "Quiniela Loteka", "position": 1},
                {"number": "90", "lottery": "Quiniela Loteka", "position": 2},
            ],
        }
    ]
    save_asset(state, materialize_same_day_table(items=items, subjects=["50", "90"]))
    r = ConversationalRouter.route("Gracias.", state=state, investigation=inv)
    assert r.path == "social_chitchat"
    assert r.inherited_subjects == []


def test_router_path_a_new_pair():
    state, inv = _inv_state()
    r = ConversationalRouter.route(
        "Han salido juntos el 50 y el 90", state=state, investigation=inv
    )
    assert r.path == "explicit_new_investigation"


def test_router_path_b_followups_without_prior_asset():
    """After same-day inv, follow-ups must be workspace even before materialize."""
    state, inv = _inv_state()
    cases = [
        ("Desglosar por posición", "sort_results"),
        ("Ver fechas", "show_dates"),
        ("Muéstrame las fechas", "show_dates"),
        ("Solo Nacional", "filter_results"),
        ("Ordenar por fecha", "sort_results"),
        ("Ordénalo desde la más reciente", "sort_results"),
        ("Mostrar primeras 20", "paginate_results"),
        ("Exportar Excel", "export_results"),
        ("Mostrar resultados", "show_results"),
        ("Ver coincidencias", "show_results"),
        ("Mostrar todas", "show_results"),
        ("Agrupar por posición", "sort_results"),
        ("Desglosa por posición", "sort_results"),
        ("Solo Gana Más", "filter_results"),
    ]
    for text, action in cases:
        r = ConversationalRouter.route(text, state=state, investigation=inv)
        assert r.path == "workspace_action", text
        assert r.workspace_action is not None, text
        assert r.workspace_action.action == action, (text, r.workspace_action)
        assert r.reason_code


def test_hermes_followups_not_narrative_research():
    state, inv = _inv_state()
    forbidden_narrative = {
        "default_research",
        "short_deictic",
        "attr:positions:research",
        "attr:date:research",
        "new_single_subject",
    }
    for text in (
        "Desglosar por posición",
        "Ver fechas",
        "Muéstrame las fechas",
        "Solo Nacional",
        "Ordenar por fecha",
        "Mostrar primeras 20",
        "Exportar Excel",
        "Mostrar resultados",
    ):
        d = HermesDecisionEngine.decide(text, state=state, investigation=inv)
        assert d.turn_type == "asset_action", text
        assert d.requires_research is False, text
        assert d.reason_code not in forbidden_narrative, (text, d.reason_code)
        assert d.workspace_action is not None, text


def test_hermes_social_empty_subjects():
    state, inv = _inv_state()
    d = HermesDecisionEngine.decide("Todo bien, ¿y tú?", state=state, investigation=inv)
    assert d.turn_type == "social_chitchat"
    assert d.inherited_subjects == []
    assert d.requires_research is False


def test_topic_switch_new_single_subject():
    state, inv = _inv_state()
    r = ConversationalRouter.route("Ahora analiza el 35.", state=state, investigation=inv)
    assert r.path == "explicit_new_investigation"
    d = HermesDecisionEngine.decide("Ahora analiza el 35.", state=state, investigation=inv)
    assert d.turn_type in {"topic_switch", "new_investigation"}
    assert "35" in (d.inherited_subjects or [])


def test_cert200_residuals_still_path_a():
    state, inv = _inv_state()
    items = [
        {
            "date": "2024-01-15",
            "appearances": [
                {"number": "50", "lottery": "Quiniela Loteka", "position": 1},
                {"number": "90", "lottery": "Quiniela Loteka", "position": 2},
            ],
        }
    ]
    save_asset(
        state,
        materialize_same_day_table(items=items, subjects=["50", "90"]),
    )
    for text in (
        "¿Solo en 2026?",
        "Últimas 3 del 35 en Nacional.",
        "Ahora en todas las posiciones.",
        "Ahora en todas las loterías.",
        "En Nacional.",
        "¿Y el 44?",
    ):
        r = ConversationalRouter.route(text, state=state, investigation=inv)
        assert r.path in {
            "explicit_new_investigation",
            "contextual_follow_up",
            "default_research",
            "new_investigation",
        }, text
        d = HermesDecisionEngine.decide(text, state=state, investigation=inv)
        assert d.turn_type != "asset_action", text


def test_speech_act_mostrar_infinitive_and_primeras():
    d = WorkspaceSpeechActDetector.detect(
        "Mostrar resultados", has_active_asset=True, has_active_investigation=True
    )
    assert d is not None and d.action == "show_results"
    d2 = WorkspaceSpeechActDetector.detect(
        "Mostrar primeras 20", has_active_asset=True, has_active_investigation=True
    )
    assert d2 is not None and d2.action == "paginate_results"
    assert d2.reason_code == "paginate_first_n"
    assert d2.pagination is not None and d2.pagination.page_size == 20
    d3 = WorkspaceSpeechActDetector.detect(
        "Muéstrame las fechas", has_active_asset=True, has_active_investigation=True
    )
    assert d3 is not None and d3.action == "show_dates"


def test_controlled_materialize_from_items():
    state = ConversationState()
    items = [
        {
            "date": "2024-01-15",
            "appearances": [
                {"number": "50", "lottery": "Quiniela Loteka", "position": 1},
                {"number": "90", "lottery": "Quiniela Loteka", "position": 2},
            ],
        }
    ]
    asset = materialize_same_day_table(items=items, subjects=["50", "90"])
    assert asset.row_count > 0
    save_asset(state, asset)
    loaded = get_active_asset(state)
    assert loaded is not None
    assert loaded.subjects == ["50", "90"]
    assert loaded.relation == "same_day"
