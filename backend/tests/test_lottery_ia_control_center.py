"""Control Center I-1..I-6 — unit tests (no Production / no sync)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.lottery.ai.control_center_benchmark import run_intent_benchmark
from app.lottery.ai.prompt_studio import (
    compile_prompt_from_blocks,
    prompt_schema,
    scan_secrets,
)
from app.lottery.numeric_relations.api_schemas import enrich_table_rows, number_detail
from app.lottery.predictions import MOTOR_CATALOG, catalog_by_key
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent
from app.services.lottery_ai_contracts import LotteryToolName


def test_i1_table1_and_table2_100_separate():
    t1 = enrich_table_rows("table1")
    t2 = enrich_table_rows("table2")
    assert len(t1) == 100 and len(t2) == 100
    assert all(r["table"] == "table_1" and r["read_only"] is True for r in t1)
    assert all(r["table"] == "table_2" and r["editable"] is False for r in t2)
    assert "÷ 1220" in t1[0]["formula"] or "1220" in t1[0]["formula"]
    assert "1220 ÷" in t2[0]["formula"] or "1220" in t2[0]["formula"]


def test_i1_number_detail_and_groups_codes():
    d1 = number_detail(34, "table1")
    assert d1["detail"]["code"] == d1["code"]
    assert 34 in d1["detail"]["group_members"] or d1["number"] == 34
    d2 = number_detail(53, "table2")
    assert d2["detail"]["read_only"] is True
    assert d2["tables_are_separate"] is True
    # groups distinct maps
    from app.lottery.numeric_relations.catalog import build_catalog

    cat = build_catalog()
    assert 34 in cat.table1_code_to_numbers
    assert 53 in cat.table2_code_to_numbers


def test_i1_invalid_table_rejected():
    with pytest.raises(ValueError):
        enrich_table_rows("table3")


def test_i2_motor_catalog_states():
    by = catalog_by_key()
    nr = by["numeric_relations"]
    assert nr["implemented"] is True and nr["status"] == "ACTIVO"
    freq = by["frequencies"]
    assert freq["implemented"] is False and freq["status"] == "NO_IMPLEMENTADO"
    assert freq["weight"] is None
    assert len(MOTOR_CATALOG) >= 7


def test_i2_prediction_intent_routes_to_nr():
    ctx = LotterySessionContext()
    intent = resolve_intent(
        "Dame la predicción del 34 en Leidsa usando las últimas 20",
        ctx,
    )
    assert intent.kind == "tool"
    assert intent.tool == LotteryToolName.ANALYZE_NUMERIC_RELATIONS
    assert intent.params.get("observed_number") == 34
    assert intent.params.get("occurrence_k") == 20


def test_i2_pure_prediction_still_refused():
    ctx = LotterySessionContext()
    intent = resolve_intent("¿Qué número va a salir mañana en Leidsa?", ctx)
    assert intent.kind == "prediction_refused"


def test_i3_prompt_schema_and_compile():
    schema = prompt_schema()
    keys = [b["key"] for b in schema["blocks"]]
    assert "identidad" in keys and "reglas_prediccion" in keys
    assert all(b.get("what_is") for b in schema["blocks"])
    compiled = compile_prompt_from_blocks(
        {"identidad": "Eres Lottery IA.", "dominio": "Solo loterías históricas."}
    )
    assert "Identidad" in compiled["body"]
    assert compiled["tokens_estimated"] > 0


def test_i4_secret_scan_blocks():
    hits = scan_secrets("api_key=sk-abcdefghijklmnopqrstuvwxyz123456")
    assert hits
    assert not scan_secrets("Eres Lottery IA sin secretos.")


def test_i5_version_guide_in_schema():
    schema = prompt_schema()
    assert "fotografía completa" in schema["guide"]
    assert "BORRADOR" in schema["version_states"]


def test_i6_benchmark_gates():
    result = run_intent_benchmark()
    assert result["coverage"] >= 10
    assert "gates" in result
    # P0 must pass for the suite itself on intent layer
    assert result["p0_failures"] == 0, result
    assert result["can_approve"] is True
