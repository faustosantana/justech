"""Tests Lottery 2.0 — admin flags and catalog filters."""

from __future__ import annotations

from app.core.admin_permissions import role_has_permission
from app.services.lottery_ai_contracts import LotteryToolName, TOOL_PERMISSIONS


def test_lottery_2_0_permissions_matrix():
    assert role_has_permission("owner", "lottery_admin_lotteries")
    assert role_has_permission("owner", "lottery_admin_sync")
    assert role_has_permission("lottery_client", "lottery_ai")
    assert role_has_permission("lottery_client", "lottery_view")
    assert not role_has_permission("lottery_client", "lottery_admin_lotteries")
    assert not role_has_permission("lottery_client", "lottery_admin_sync")
    assert not role_has_permission("lottery_client", "lottery.admin")


def test_lottery_2_0_new_tools_registered():
    for name in (
        LotteryToolName.GET_LATEST_RESULTS,
        LotteryToolName.GET_DRAW_COUNT,
        LotteryToolName.GET_TOP_NUMBERS,
        LotteryToolName.GET_BOTTOM_NUMBERS,
        LotteryToolName.GET_LAST_OCCURRENCE,
        LotteryToolName.GET_INTERVAL_STATISTICS,
        LotteryToolName.GET_SYNC_STATUS,
    ):
        assert name in TOOL_PERMISSIONS
