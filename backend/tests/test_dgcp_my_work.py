"""Tests — Mis Licitaciones / traffic light / template dedup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.dgcp_my_work_service import traffic_light


def test_traffic_light_rules():
    now = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
    assert traffic_light(now - timedelta(hours=1), now=now)[0] == "black"
    assert traffic_light(now + timedelta(hours=12), now=now)[0] == "red"
    assert traffic_light(now + timedelta(hours=36), now=now)[0] == "orange"
    assert traffic_light(now + timedelta(days=4), now=now)[0] == "yellow"
    assert traffic_light(now + timedelta(days=10), now=now)[0] == "green"
    assert traffic_light(None, now=now)[0] == "none"


def test_default_template_keys_unique():
    from app.services.dgcp_my_work_service import DEFAULT_TEMPLATE_ITEMS

    keys = [k for k, *_ in DEFAULT_TEMPLATE_ITEMS]
    assert len(keys) == len(set(keys))
    assert "carta_fabricante" in keys
