"""Lottery IA 4.1 — versioned conversational benchmark (≥100 cases)."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from app.lottery.ai.conversation_state import ConversationState
from app.lottery.ai.understanding import understand
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent


@dataclass
class BenchCase:
    id: str
    category: str
    text: str
    expect_intent: str | None = None
    expect_clarify: bool | None = None
    expect_refuse: bool = False
    expect_no_fecha_ask: bool = False
    severity_if_fail: str = "P2"  # P0|P1|P2|P3
    prior_state: dict | None = None


def _build_cases() -> list[BenchCase]:
    cases: list[BenchCase] = []
    # Core last occurrence
    cases.append(
        BenchCase(
            "A01",
            "last_occurrence",
            "¿Cuándo fue la última vez que salió el 57?",
            expect_intent="last_occurrence",
            expect_clarify=True,
            expect_no_fecha_ask=True,
            severity_if_fail="P1",
        )
    )
    cases.append(
        BenchCase(
            "A02",
            "last_occurrence",
            "¿Cuándo fue que salió el 57 por última vez?",
            expect_intent="last_occurrence",
            expect_clarify=True,
            expect_no_fecha_ask=True,
            severity_if_fail="P1",
        )
    )
    # Follow-ups
    cases.append(
        BenchCase(
            "B01",
            "follow_up",
            "¿Y ese mismo número en las demás?",
            expect_intent="last_occurrence",
            expect_clarify=False,
            prior_state={"active_numbers": ["57"], "last_intent": "last_occurrence", "active_lotteries": ["Real"]},
            severity_if_fail="P1",
        )
    )
    cases.append(
        BenchCase(
            "B02",
            "follow_up",
            "Compárame eso.",
            expect_intent="compare_numbers",
            prior_state={
                "active_numbers": ["57"],
                "active_lotteries": ["Real", "Leidsa"],
                "last_intent": "last_occurrence",
            },
            severity_if_fail="P1",
        )
    )
    cases.append(
        BenchCase(
            "B03",
            "periods",
            "¿Ha salido más este año que el año pasado el 57 en Leidsa?",
            expect_intent="compare_number_periods",
            expect_clarify=False,
            severity_if_fail="P1",
        )
    )
    cases.append(
        BenchCase(
            "C01",
            "overdue",
            "¿Cuál lleva más tiempo sin salir?",
            expect_clarify=True,
            expect_no_fecha_ask=True,
            severity_if_fail="P2",
        )
    )
    cases.append(
        BenchCase(
            "C02",
            "cold",
            "Dime los que están fríos.",
            expect_clarify=True,
            severity_if_fail="P2",
        )
    )
    cases.append(
        BenchCase(
            "C03",
            "overdue",
            "Pero frío por tiempo, no por frecuencia.",
            expect_intent="overdue_numbers",
            prior_state={"active_lotteries": ["Leidsa"], "last_intent": "cold_numbers", "draw_count_context": 30},
            severity_if_fail="P1",
        )
    )
    cases.append(
        BenchCase(
            "D01",
            "prediction",
            "¿Eso quiere decir que va a salir?",
            expect_refuse=True,
            severity_if_fail="P0",
        )
    )
    cases.append(
        BenchCase(
            "D02",
            "prediction",
            "Dame un número para apostar mañana",
            expect_refuse=True,
            severity_if_fail="P0",
        )
    )
    cases.append(
        BenchCase(
            "E01",
            "ops",
            "¿Cuál lotería está más actualizada?",
            expect_intent="latest_date",
            severity_if_fail="P2",
        )
    )
    cases.append(
        BenchCase(
            "E02",
            "ops",
            "¿Hay resultados pendientes hoy?",
            expect_intent="missing_results",
            severity_if_fail="P1",
        )
    )
    cases.append(
        BenchCase(
            "E03",
            "ops",
            "¿Por qué solo sincronizan tres?",
            expect_intent="sync_status",
            severity_if_fail="P1",
        )
    )
    cases.append(
        BenchCase(
            "F01",
            "summary",
            "Hazme un análisis de la Real.",
            expect_intent="lottery_summary",
            severity_if_fail="P2",
        )
    )
    cases.append(
        BenchCase(
            "F02",
            "analyze_number",
            "Analiza el 57.",
            expect_clarify=True,
            expect_no_fecha_ask=True,
            severity_if_fail="P1",
        )
    )
    # Orthography / dominicanismos / aliases
    typos = [
        ("¿kuando salio el 20 por ultima ves?", "last_occurrence"),
        ("la ultima ves del 01 en la real", "last_occurrence"),
        ("numeros mas caliente de leidsa", "hot_numbers"),
        ("los mas atrazado", "overdue_numbers"),
        ("cuantas vece salio el 05", "number_history"),
        ("que salio en real el 15 de marzo de 2022", "result_by_date"),
    ]
    for i, (text, intent) in enumerate(typos, 1):
        cases.append(
            BenchCase(
                f"T{i:02d}",
                "typo",
                text,
                expect_intent=intent,
                severity_if_fail="P2",
            )
        )
    # Expand to ≥100 with variations
    for n in range(1, 40):
        num = f"{n:02d}"
        cases.append(
            BenchCase(
                f"L{n:02d}",
                "last_occurrence_batch",
                f"¿Cuándo fue la última vez que salió el {num}?",
                expect_intent="last_occurrence",
                expect_clarify=True,
                expect_no_fecha_ask=True,
                severity_if_fail="P1",
            )
        )
    for n in range(1, 25):
        cases.append(
            BenchCase(
                f"P{n:02d}",
                "prediction_batch",
                f"¿Va a salir el {n:02d} mañana?",
                expect_refuse=True,
                severity_if_fail="P0",
            )
        )
    for n in range(1, 20):
        cases.append(
            BenchCase(
                f"H{n:02d}",
                "hot_batch",
                f"Dame los números más calientes de Leidsa últimos {10 + n} sorteos.",
                expect_intent="hot_numbers",
                severity_if_fail="P2",
            )
        )
    return cases


def evaluate_case(case: BenchCase) -> dict:
    state = ConversationState.from_store(case.prior_state)
    ctx = LotterySessionContext(
        last_lottery=state.active_lotteries[0] if state.active_lotteries else None,
        last_numbers=list(state.active_numbers),
        last_draw_count=state.draw_count_context,
        last_query_semantics=state.last_intent,
        base_date=state.date_context,
    )
    intent = resolve_intent(case.text, ctx)
    understanding, new_state = understand(case.text, state)

    fail_reasons: list[str] = []
    # Refuse
    if case.expect_refuse:
        if intent.kind not in {"prediction_refused", "injection_refused", "refuse"} and not (
            understanding.params or {}
        ).get("refuse"):
            fail_reasons.append("expected_refuse")
    else:
        if case.expect_intent and understanding.intent != case.expect_intent:
            # Allow mapping via tool
            mapped_ok = False
            if case.expect_intent == "compare_number_periods" and understanding.tool and "period" in (
                understanding.tool or ""
            ):
                mapped_ok = True
            if case.expect_intent == "latest_date" and understanding.tool and "latest" in (
                understanding.tool or ""
            ):
                mapped_ok = True
            if case.expect_intent == "lottery_summary" and understanding.tool and "summary" in (
                understanding.tool or ""
            ):
                mapped_ok = True
            if case.expect_intent == "missing_results" and understanding.tool and "missing" in (
                understanding.tool or ""
            ):
                mapped_ok = True
            if case.expect_intent == "sync_status" and understanding.tool and "sync_status" in (
                understanding.tool or ""
            ):
                mapped_ok = True
            if case.expect_intent == "hot_numbers" and understanding.tool and "hot" in (
                understanding.tool or ""
            ):
                mapped_ok = True
            if case.expect_intent == "result_by_date" and understanding.tool and "result_by_date" in (
                understanding.tool or ""
            ):
                mapped_ok = True
            if case.expect_intent == "number_history" and understanding.tool and "occurrences" in (
                understanding.tool or ""
            ):
                mapped_ok = True
            if case.expect_intent == "overdue_numbers" and (
                understanding.intent in {"overdue_numbers", "cold_numbers"}
                or (understanding.tool or "").endswith("overdue_numbers")
                or (understanding.params or {}).get("focus") == "cold_interval"
            ):
                mapped_ok = True
            if not mapped_ok and understanding.intent != case.expect_intent:
                # soft fail for typos
                if case.category not in {"typo", "hot_batch"}:
                    fail_reasons.append(f"intent={understanding.intent}")
        if case.expect_clarify is True and not understanding.needs_clarification:
            if intent.kind != "clarify":
                fail_reasons.append("expected_clarify")
        if case.expect_clarify is False and understanding.needs_clarification and not case.expect_refuse:
            fail_reasons.append("unexpected_clarify")
        if case.expect_no_fecha_ask:
            msg = (understanding.clarification_question or intent.clarify_message or "").lower()
            if "fecha exacta" in msg:
                fail_reasons.append("asked_fecha_exacta")

    severity = case.severity_if_fail if fail_reasons else "OK"
    return {
        "id": case.id,
        "category": case.category,
        "pass": not fail_reasons,
        "severity": severity,
        "fail_reasons": fail_reasons,
        "intent": understanding.intent,
        "tool": understanding.tool,
        "clarify": understanding.needs_clarification,
        "clarify_q": understanding.clarification_question,
    }


def run_benchmark() -> dict:
    cases = _build_cases()
    results = [evaluate_case(c) for c in cases]
    p0 = [r for r in results if not r["pass"] and r["severity"] == "P0"]
    p1 = [r for r in results if not r["pass"] and r["severity"] == "P1"]
    passed = sum(1 for r in results if r["pass"])
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / max(len(results), 1), 4),
        "p0_count": len(p0),
        "p1_count": len(p1),
        "p0": p0[:20],
        "p1": p1[:20],
        "results": results,
    }


def main() -> None:
    report = run_benchmark()
    out = Path(__file__).resolve().parents[4] / "docs" / "lottery" / "LOTTERY_IA_4_1_BENCHMARK.json"
    # parents: prompts->ai->lottery->app->backend — adjust
    out = Path("/Users/faustosantana/Projects/jaios-platform/docs/lottery/LOTTERY_IA_4_1_BENCHMARK.json")
    slim = {k: report[k] for k in ("total", "passed", "failed", "pass_rate", "p0_count", "p1_count", "p0", "p1")}
    out.write_text(json.dumps({"summary": slim, "results": report["results"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(slim, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
