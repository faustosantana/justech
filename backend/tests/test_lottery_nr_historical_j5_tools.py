"""J-5 — historical tool enum values exist."""

from app.services.lottery_ai_contracts import LotteryToolName, TOOL_PERMISSIONS


def test_historical_tools_registered():
    assert LotteryToolName.HISTORICAL_RELATION_CONDITIONS.value.startswith("lottery_")
    assert LotteryToolName.CANDIDATE_RESPONSE_SUMMARY in TOOL_PERMISSIONS
    assert LotteryToolName.CONFIRMER_COMBINATIONS in TOOL_PERMISSIONS
    assert LotteryToolName.RELATION_PATTERN_DETAIL in TOOL_PERMISSIONS
    assert LotteryToolName.COMPARE_HISTORICAL_PATTERNS in TOOL_PERMISSIONS
