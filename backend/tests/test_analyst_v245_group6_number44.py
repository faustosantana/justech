"""v2.4.5 Grupo 6 — F.2 «El 44.» after ¿Cuándo salió?

Root cause: pending number fill fell through to chat-service default
COMPARE_LOTTERIES (asc order / wrong catalog surface → La Primera Tarde 2025)
instead of last_n across DEFAULT_ALL_HISTORY (2026-07-20 Leidsa).
"""

from __future__ import annotations

from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.nlp_stability import DEFAULT_ALL_HISTORY_LOTTERIES
from app.lottery.ai.understanding import _resume_pending, understand
from app.services.lottery_ai_contracts import LotteryToolName


def test_f2_resume_pending_uses_last_n_default_scope():
    st = ConversationState(
        active_numbers=["44"],
        pending_intent="last_occurrence",
        pending_slots=[],
        pending_params={"number": "44"},
        scope="all",
    )
    result, _ = _resume_pending(st)
    assert result.tool == LotteryToolName.GET_NUMBER_OCCURRENCES.value
    assert result.params.get("mode") == "last_n"
    assert result.params.get("order") == "desc"
    assert "Gana Más" in (result.params.get("lotteries") or [])
    assert set(DEFAULT_ALL_HISTORY_LOTTERIES).issubset(
        set(result.params.get("lotteries") or [])
    )


def test_f2_clarification_response_pending_also_resumes_last_n():
    st = ConversationState(
        active_numbers=["44"],
        pending_intent="clarification_response",
        pending_slots=[],
        pending_params={"number": "44"},
    )
    result, _ = _resume_pending(st)
    assert result.intent == "last_occurrence"
    assert result.tool == LotteryToolName.GET_NUMBER_OCCURRENCES.value
    assert result.params.get("mode") == "last_n"


def test_f1_f2_understand_chain_fills_number_and_resumes():
    st = ConversationState(
        pending_intent="last_occurrence",
        pending_slots=["number"],
    )
    result, st2 = understand("El 44.", st)
    assert "44" in (result.numbers or st2.active_numbers or [])
    assert result.tool == LotteryToolName.GET_NUMBER_OCCURRENCES.value
    assert result.params.get("mode") == "last_n"
    assert result.needs_clarification is False


def test_f2_send_message_does_not_shadow_lottery_tool_name_import():
    """Local `import LotteryToolName` inside send_message caused UnboundLocalError (F.2)."""
    import inspect

    from app.services.lottery_chat_service import LotteryChatService

    src = inspect.getsource(LotteryChatService.send_message)
    assert "from app.services.lottery_ai_contracts import LotteryToolName\n" not in src
    # Aliased local imports are OK; bare name must resolve to module-level import
    assert "LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES" in src

