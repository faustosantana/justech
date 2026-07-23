"""Lottery 3.0 unit tests — no DB required."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.lottery.sync.multi_source import compare_candidates, select_with_failover
from app.lottery.sync.window_planner import SyncWindowPhase, plan_lottery_window


def _lot(**kwargs):
    base = dict(
        id="00000000-0000-0000-0000-000000000001",
        source_id=5,
        timezone="America/Santo_Domingo",
        draw_times="20:55",
        draw_days="daily",
        sync_interval_minutes=60,
        sync_post_draw_delay_minutes=45,
        sync_pre_window_minutes=15,
        sync_live_window_minutes=10,
        sync_post_window_minutes=45,
        sync_pre_interval_minutes=5,
        sync_live_interval_minutes=1,
        sync_post_interval_minutes=1,
        sync_priority=10,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _cand(nums, ref="1"):
    return SimpleNamespace(
        source_id=5,
        lottery_name="Leidsa",
        draw_date="2026-07-21",
        source_reference=ref,
        numbers=nums,
    )


def test_window_idle_far_from_draw():
    tz = ZoneInfo("America/Santo_Domingo")
    now = datetime(2026, 7, 23, 10, 0, tzinfo=tz)
    d = plan_lottery_window(_lot(), now=now)
    assert d.phase == SyncWindowPhase.IDLE
    assert d.should_poll is True
    assert d.interval_minutes == 60


def test_window_pre_near_draw():
    tz = ZoneInfo("America/Santo_Domingo")
    now = datetime(2026, 7, 23, 20, 45, tzinfo=tz)
    d = plan_lottery_window(_lot(), now=now)
    assert d.phase in (SyncWindowPhase.PRE, SyncWindowPhase.LIVE)
    assert d.should_poll is True
    assert d.interval_minutes <= 5


def test_window_paused_when_validated():
    tz = ZoneInfo("America/Santo_Domingo")
    now = datetime(2026, 7, 23, 21, 30, tzinfo=tz)
    d = plan_lottery_window(_lot(), now=now, result_validated_for_date=date(2026, 7, 23))
    assert d.phase == SyncWindowPhase.PAUSED
    assert d.should_poll is False


def test_multisource_failover_to_secondary():
    res = select_with_failover(
        [
            ("api", "primary", Exception("timeout"), 1200.0),
            ("sqlite", "secondary", [_cand(["01", "02", "03"])], 40.0),
        ]
    )
    assert res.chosen_source == "sqlite"
    assert res.blocked_write is False
    assert len(res.candidates) == 1


def test_multisource_conflict_blocks_write():
    a = [_cand(["01", "02", "03"])]
    b = [_cand(["01", "02", "99"])]
    assert compare_candidates(a, b, other_source="sqlite")
    res = select_with_failover(
        [
            ("api", "primary", a, 10.0),
            ("sqlite", "secondary", b, 12.0),
        ]
    )
    assert res.blocked_write is True
    assert res.block_reason == "source_conflict"


if __name__ == "__main__":
    test_window_idle_far_from_draw()
    test_window_pre_near_draw()
    test_window_paused_when_validated()
    test_multisource_failover_to_secondary()
    test_multisource_conflict_blocks_write()
    print("ALL_PASS")
