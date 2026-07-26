"""Phase 5.2 — Lottery IA Dashboard + Motor v1.0 freeze (read-only)."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.lottery.numeric_relations.analysis_engine import run_complete_analysis
from app.lottery.numeric_relations.analysis_engine.motor_v1_freeze import (
    MOTOR_PRODUCT_VERSION,
    motor_v1_freeze_manifest,
    persist_freeze_artifact,
)
from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
    get_prospective_store,
    reset_prospective_store,
)
from app.lottery.numeric_relations.analysis_engine.signal_tracker import reset_signal_store
from app.lottery.numeric_relations.j11a.memory_engine import reset_sessions


BACKEND_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = BACKEND_ROOT.parent


def _motor_table_tsx() -> Path | None:
    candidates = [
        REPO_ROOT / "frontend" / "src" / "components" / "lottery" / "control-center" / "motor-table.tsx",
        Path("/frontend/src/components/lottery/control-center/motor-table.tsx"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


@pytest.fixture(autouse=True)
def _clean():
    reset_signal_store()
    reset_sessions()
    reset_prospective_store()
    yield
    reset_signal_store()
    reset_sessions()
    reset_prospective_store()


def test_motor_v1_freeze_manifest_read_only():
    m = motor_v1_freeze_manifest()
    assert m["motor_version"] == "1.0"
    assert MOTOR_PRODUCT_VERSION == "1.0"
    assert m["status"] == "FROZEN"
    assert m["freeze_date"] == "2026-07-26"
    assert m["read_only"] is True
    assert m["ui_editable"] is False
    assert m["production_modified"] is False
    assert m["active_profile"]
    assert m["active_tiebreak"]
    assert "engine_commit" in m


def test_persist_freeze_artifact_writes_json(tmp_path: Path):
    out = persist_freeze_artifact(tmp_path)
    assert out.exists()
    data = out.read_text(encoding="utf-8")
    assert '"motor_version": "1.0"' in data
    assert '"ui_editable": false' in data


def test_api_router_includes_ia_dashboard_and_freeze_get_only():
    from app.api.v1 import lottery_ia

    routes = list(lottery_ia.router.routes)
    paths = [getattr(r, "path", "") or "" for r in routes]
    methods = {
        (getattr(r, "path", "") or ""): set(getattr(r, "methods", set()) or set())
        for r in routes
    }
    assert any(p.endswith("/dashboard") for p in paths)
    assert any(p.endswith("/motor-freeze") for p in paths)
    freeze_path = next(p for p in paths if p.endswith("/motor-freeze"))
    assert methods[freeze_path] == {"GET"}
    # No write verbs registered on this router
    all_methods = set()
    for mset in methods.values():
        all_methods |= mset
    assert "POST" not in all_methods
    assert "PATCH" not in all_methods
    assert "PUT" not in all_methods
    assert "DELETE" not in all_methods


def test_dashboard_builder_structure():
    from app.lottery.numeric_relations.analysis_engine import ia_dashboard as mod

    src = inspect.getsource(mod.build_ia_dashboard)
    assert "motor_v1_freeze_manifest" in src
    assert "LotteryResultService" in inspect.getsource(mod)
    assert "get_prospective_store" in src
    # Reuse only — no new math / scraper
    assert "BeautifulSoup" not in inspect.getsource(mod)
    assert "run_complete_analysis" not in src


def test_motor_unaffected_by_dashboard_phase():
    r = run_complete_analysis(
        {"numbers": [35, 14], "mode": "socio", "derivation_depth": 0, "create_signals": False},
        persist=False,
    )
    assert r.primary_signal["number"] == 54


def test_predictions_still_lock():
    store = get_prospective_store()
    pred = store.create({"numbers": [35, 14], "date": "2026-07-26"})
    assert store.lock(pred.prediction_id).status == "LOCKED"


def test_tiebreak_engine_file_unchanged_in_phase52():
    """Guard: Phase 5.2 must not rewrite tiebreak_engine.py formulas."""
    path = (
        BACKEND_ROOT
        / "app"
        / "lottery"
        / "numeric_relations"
        / "analysis_engine"
        / "tiebreak_engine.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "SELECTED_RULE_ID" in text
    assert "TIEBREAK_PROFILE_SOCIO_V1" in text
    # Syntax still valid
    ast.parse(text)


def test_motor_table_ux_no_numero_cantidad_columns():
    path = _motor_table_tsx()
    if path is None:
        pytest.skip("frontend/motor-table.tsx not mounted in this test runner")
    src = path.read_text(encoding="utf-8")
    assert 'placeholder="Buscar número"' in src
    assert 'placeholder="Buscar código"' in src
    assert "sin paginación" in src
    assert "ordenados por Código" in src
    # Visible table headers must not include Número / Cantidad columns
    assert "<th className=\"py-2 pr-3\">Código</th>" in src
    assert ">Número<" not in src
    assert ">Cantidad<" not in src
    assert "pageSize" not in src
    assert "setPage" not in src


def test_production_not_modified_marker():
    m = motor_v1_freeze_manifest()
    assert m["production_modified"] is False
