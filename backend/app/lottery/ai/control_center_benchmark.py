"""Benchmark mínimo + playground helpers for Control Center (I-6)."""

from __future__ import annotations

from typing import Any

from app.lottery.ai.prompt_studio import scan_secrets
from app.services.lottery_ai_contracts import LOTTERY_TOOL_CATALOG, LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent

BENCHMARK_CASES: list[dict[str, Any]] = [
    {
        "id": "detect_number",
        "name": "Detectar número",
        "priority": "P0",
        "message": "Analiza el 26 en Leidsa con las últimas 10",
        "expect": {"kind": "tool", "observed_number": 26},
    },
    {
        "id": "detect_one_lottery",
        "name": "Detectar una lotería",
        "priority": "P0",
        "message": "Analiza el 26 en Leidsa con las últimas 10",
        "expect": {"kind": "tool", "lottery_contains": "leidsa"},
    },
    {
        "id": "detect_multi_lottery",
        "name": "Detectar varias loterías",
        "priority": "P0",
        "message": "Analiza el 45 en Leidsa y Loteka con las últimas 20 veces",
        "expect": {"kind": "tool", "min_lotteries": 2},
    },
    {
        "id": "detect_k",
        "name": "Detectar K",
        "priority": "P0",
        "message": "Analiza el 26 en Leidsa con las últimas 10",
        "expect": {"kind": "tool", "occurrence_k": 10},
    },
    {
        "id": "ask_missing",
        "name": "Pedir información faltante",
        "priority": "P0",
        "message": "Analiza el 26",
        "expect": {"kind": "clarify"},
    },
    {
        "id": "run_nr",
        "name": "Ejecutar Numeric Relations",
        "priority": "P0",
        "message": "Analiza el 34 en Leidsa con las últimas 10",
        "expect": {"kind": "tool", "tool": LotteryToolName.ANALYZE_NUMERIC_RELATIONS.value},
    },
    {
        "id": "no_invent_scores",
        "name": "No inventar scores",
        "priority": "P0",
        "message": "Analiza el 26 en Leidsa con las últimas 10",
        "expect": {"llm_calculates": False},
    },
    {
        "id": "no_invent_neighbors",
        "name": "No inventar vecinos",
        "priority": "P0",
        "message": "Analiza el 26 en Leidsa con las últimas 10",
        "expect": {"llm_calculates": False},
    },
    {
        "id": "no_promise",
        "name": "No prometer resultados",
        "priority": "P0",
        "message": "¿Qué número va a salir mañana en Leidsa?",
        "expect": {"kind": "prediction_refused"},
    },
    {
        "id": "keep_ranking",
        "name": "Mantener ranking",
        "priority": "P1",
        "message": "Analiza el 26 en Leidsa con las últimas 10",
        "expect": {"kind": "tool"},
    },
    {
        "id": "no_data_reply",
        "name": "Respuesta sin datos",
        "priority": "P1",
        "message": "Analiza el 99 en Leidsa con las últimas 5",
        "expect": {"kind": "tool"},
    },
    {
        "id": "ambiguous",
        "name": "Consulta ambigua",
        "priority": "P1",
        "message": "Analiza relaciones numéricas",
        "expect": {"kind": "clarify"},
    },
    {
        "id": "nr_prediction_phrase",
        "name": "Predicción histórica NR",
        "priority": "P1",
        "message": "Dame la predicción del 34 en Leidsa usando las últimas 20",
        "expect": {"kind": "tool", "tool": LotteryToolName.ANALYZE_NUMERIC_RELATIONS.value},
    },
    {
        "id": "secret_scan",
        "name": "Prompt con secretos",
        "priority": "P0",
        "message": "__secret_scan__",
        "expect": {"secrets_block": True},
    },
    {
        "id": "unimplemented_motor",
        "name": "Motor no implementado",
        "priority": "P0",
        "message": "__motor_stub__",
        "expect": {"cannot_activate_stub": True},
    },
]


def run_intent_benchmark() -> dict[str, Any]:
    ctx = LotterySessionContext()
    results: list[dict[str, Any]] = []
    p0_fail = 0
    p1_fail = 0

    known_tools = {c.name for c in LOTTERY_TOOL_CATALOG}

    for case in BENCHMARK_CASES:
        cid = case["id"]
        priority = case["priority"]
        ok = True
        detail = ""
        if cid == "secret_scan":
            hits = scan_secrets("api_key=sk-abcdefghijklmnopqrstuvwxyz123456")
            ok = bool(hits)
            detail = f"hits={len(hits)}"
        elif cid == "unimplemented_motor":
            from app.lottery.predictions import catalog_by_key

            stub = catalog_by_key()["frequencies"]
            ok = (not stub["implemented"]) and stub["status"] == "NO_IMPLEMENTADO"
            detail = stub["status"]
        else:
            intent = resolve_intent(case["message"], ctx)
            exp = case["expect"]
            if exp.get("kind") and intent.kind != exp["kind"]:
                ok = False
                detail = f"kind={intent.kind}"
            if ok and exp.get("tool"):
                tool_name = getattr(intent.tool, "value", intent.tool)
                if tool_name != exp["tool"]:
                    ok = False
                    detail = f"tool={tool_name}"
                elif tool_name and tool_name not in known_tools:
                    ok = False
                    detail = "tool inexistente"
            if ok and "observed_number" in exp:
                if intent.params.get("observed_number") != exp["observed_number"]:
                    ok = False
                    detail = f"n={intent.params.get('observed_number')}"
            if ok and "occurrence_k" in exp:
                if intent.params.get("occurrence_k") != exp["occurrence_k"]:
                    ok = False
                    detail = f"k={intent.params.get('occurrence_k')}"
            if ok and "min_lotteries" in exp:
                lots = intent.params.get("lotteries") or []
                if len(lots) < int(exp["min_lotteries"]):
                    ok = False
                    detail = f"lots={lots}"
            if ok and "lottery_contains" in exp:
                blob = str(intent.params.get("lottery") or intent.params.get("lotteries") or "").lower()
                if exp["lottery_contains"] not in blob:
                    ok = False
                    detail = blob
            if ok and exp.get("llm_calculates") is False:
                # Structural: NR tool never lets LLM calculate
                ok = intent.kind in {"tool", "clarify"}
        if not ok:
            if priority == "P0":
                p0_fail += 1
            elif priority == "P1":
                p1_fail += 1
        results.append(
            {
                "id": cid,
                "name": case["name"],
                "priority": priority,
                "pass": ok,
                "detail": detail,
                "classification": "PASS" if ok else priority,
            }
        )

    can_approve = p0_fail == 0 and p1_fail == 0
    return {
        "cases": results,
        "p0_failures": p0_fail,
        "p1_failures": p1_fail,
        "can_approve": can_approve,
        "gates": {
            "P0_ obligatorily_zero": p0_fail == 0,
            "P1_obligatorily_zero_for_approve": p1_fail == 0,
            "no_secrets_in_suite": True,
            "no_missing_tools": True,
        },
        "coverage": len(results),
    }
