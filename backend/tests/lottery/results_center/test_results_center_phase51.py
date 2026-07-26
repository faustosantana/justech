"""Phase 5.1 — Resultados center tests (reuse, no second scraper)."""

from __future__ import annotations

import inspect
from datetime import date, time
from types import SimpleNamespace

import pytest

from app.lottery.numeric_relations.analysis_engine import run_complete_analysis
from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
    get_prospective_store,
    reset_prospective_store,
)
from app.lottery.numeric_relations.analysis_engine.results_access import LotteryResultService
from app.lottery.numeric_relations.analysis_engine.signal_tracker import reset_signal_store
from app.lottery.numeric_relations.j11a import chat
from app.lottery.numeric_relations.j11a.memory_engine import reset_sessions
from app.services.lottery_result_service import flatten_draw


@pytest.fixture(autouse=True)
def _clean():
    reset_signal_store()
    reset_sessions()
    reset_prospective_store()
    yield
    reset_signal_store()
    reset_sessions()
    reset_prospective_store()


def test_flatten_draw_maps_primera_segunda_tercera():
    lottery = SimpleNamespace(
        id="x", name="Demo", slug="demo", country_code="DO", country="DO"
    )
    draw = SimpleNamespace(
        id="d1",
        draw_date=date(2026, 7, 1),
        draw_time=time(14, 30),
        game_name="quiniela",
        source_reference="api",
        source_url=None,
        scraped_at=None,
        numbers=[
            SimpleNamespace(position=1, number_value="35", number_type="principal"),
            SimpleNamespace(position=2, number_value="14", number_type="principal"),
            SimpleNamespace(position=3, number_value="54", number_type="principal"),
        ],
    )
    flat = flatten_draw(draw, lottery)  # type: ignore[arg-type]
    assert flat["primera"] == "35"
    assert flat["segunda"] == "14"
    assert flat["tercera"] == "54"


def test_lottery_result_service_is_facade_not_scraper():
    src = inspect.getsource(LotteryResultService)
    assert "BeautifulSoup" not in src
    assert "requests.get" not in src
    assert "self.repo" in src


def test_motor_still_runs_after_results_center():
    r = run_complete_analysis(
        {"numbers": [35, 14], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    assert r.primary_signal["number"] == 54


def test_prospective_still_works():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": date.today().isoformat()})
    assert store.lock(pred.prediction_id).status == "LOCKED"


def test_no_second_scraper_module_created():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    assert not list((root / "app" / "services").glob("*scraper*"))


def test_results_access_bridge_exports_service():
    from app.lottery.numeric_relations.analysis_engine import results_access as ra

    assert hasattr(ra, "LotteryResultService")


def test_j11a_reads_results_status_intent():
    out = chat("¿Cuántos sorteos tiene la base?")
    assert out["intent"] == "INVESTIGATE"


def test_production_not_modified_marker():
    from app.services.lottery_result_service import get_results_status_sync

    assert get_results_status_sync().get("production_modified") is False


def test_api_router_includes_resultados():
    from app.api.v1 import lottery_resultados

    paths = [getattr(r, "path", "") for r in lottery_resultados.router.routes]
    assert any("resultados" in (p or "") for p in paths)
    assert any("sync-status" in (p or "") for p in paths)
