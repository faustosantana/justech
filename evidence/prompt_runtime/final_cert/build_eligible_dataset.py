#!/usr/bin/env python3
"""Build Shadow200 eligible dataset (static preflight via ReasoningModeSelector)."""
from __future__ import annotations

import json
from pathlib import Path

from app.lottery.ai.analyst_reasoning.reasoning_modes import ReasoningModeSelector, should_invoke_reasoning

OUT = Path(__file__).resolve().parent
EXPECTED_HASH = "41c64a0fc7c303222c2b492e82a0ea51cec6c16139bc2f0cde9ec9e9da642ff9"

# Distinct pairs — avoid workspace triggers (tabla/export/página)
_PAIRS = [
    (7, 38), (12, 50), (14, 54), (18, 63), (22, 77), (11, 25), (35, 2), (38, 3),
    (50, 90), (63, 19), (41, 25), (90, 35), (5, 44), (8, 61), (9, 72), (15, 28),
    (16, 33), (17, 49), (19, 55), (21, 66), (23, 70), (24, 81), (26, 88), (27, 4),
    (29, 6), (30, 48), (31, 52), (32, 57), (34, 68), (36, 73), (37, 79), (39, 82),
    (40, 85), (42, 91), (43, 1), (45, 10), (46, 13), (47, 20), (51, 53), (56, 58),
    (59, 60), (62, 64), (65, 67), (69, 71), (74, 75), (76, 78), (80, 83), (84, 86),
    (87, 89), (92, 93), (94, 95), (96, 97), (0, 98), (3, 99), (4, 41), (6, 50),
    (8, 22), (10, 35), (13, 63), (20, 77), (25, 38), (28, 54), (33, 90), (44, 12),
    (48, 7), (52, 18), (57, 11), (61, 14), (66, 2), (68, 19), (72, 5), (73, 9),
    (78, 15), (81, 16), (85, 17), (88, 21), (91, 23), (93, 24), (95, 26), (97, 27),
    (99, 29), (1, 30), (2, 31), (5, 32), (7, 34), (9, 36), (11, 37), (12, 39),
    (14, 40), (15, 42), (16, 43), (17, 45), (18, 46), (19, 47), (21, 51), (22, 56),
    (23, 59), (24, 62), (25, 65), (26, 69), (27, 74), (28, 76), (29, 80), (30, 84),
]


def _fmt(n: int) -> str:
    return f"{n:02d}"


def _pair(i: int) -> tuple[str, str]:
    a, b = _PAIRS[i % len(_PAIRS)]
    return _fmt(a), _fmt(b)


def build_cases() -> list[dict]:
    cases: list[dict] = []
    i = 0

    def add(category: str, user: str, setup: list[str] | None = None, relation: str = "same_day"):
        nonlocal i
        i += 1
        cid = f"E{i:04d}"
        setup = setup or []
        mode = ReasoningModeSelector.select(user, relation=relation, has_evidence=True)
        cases.append(
            {
                "id": cid,
                "category": category,
                "user": user,
                "setup": setup,
                "expect": {
                    "huawei_eligible": True,
                    "preflight_mode": mode,
                    "preflight_invoke": should_invoke_reasoning(mode),
                    "relation": relation,
                },
            }
        )

    _NO_INVENT = (
        " No inventes subtotales de posiciones, frecuencias parciales ni desgloses "
        "que no estén explícitos en la evidencia."
    )

    # 30 interpretación de coincidencias
    for k in range(30):
        a, b = _pair(k)
        add(
            "interp_coincidence",
            f"¿Han coincidido el {a} y el {b} el mismo día? Interpreta qué significa esa coincidencia same-day.{_NO_INVENT}",
        )

    # 25 análisis de frecuencia
    for k in range(25):
        a, b = _pair(30 + k)
        add(
            "freq_analysis",
            f"¿El {a} y el {b} han coincidido más de 40 veces el mismo día? Explica solo el conteo canónico y su alcance.{_NO_INVENT}",
        )

    # 20 comparación
    for k in range(20):
        a, b = _pair(55 + k)
        add(
            "compare_numbers",
            f"Compara históricamente el {a} y el {b}: ¿quién aparece más en coincidencias same-day con el otro? Interpreta.{_NO_INVENT}",
        )

    # 20 últimas apariciones (interpretative, not bare attribute)
    for k in range(20):
        a, b = _pair(75 + k)
        add(
            "recent_interp",
            f"¿Cuál fue la coincidencia más reciente del {a} y el {b} el mismo día según la evidencia? Interpreta limitaciones.{_NO_INVENT}",
        )

    # 20 posiciones (interpretative)
    for k in range(20):
        a, b = _pair(10 + k)
        add(
            "position_interp",
            f"Sobre las coincidencias same-day del {a} y el {b}, interpreta el significado general sin inventar subtotales de posición.{_NO_INVENT}",
        )

    # 15 evidencia insuficiente / limitaciones
    for k in range(15):
        a, b = _pair(40 + k)
        add(
            "insufficient_evidence",
            f"¿Qué significa el total de coincidencias same-day del {a} y el {b}? Incluye limitaciones y qué no se puede afirmar.{_NO_INVENT}",
        )

    # 15 múltiples loterías
    for k in range(15):
        a, b = _pair(60 + k)
        add(
            "multi_lottery",
            f"Dentro de las 7 loterías oficiales, ¿cuántas veces coincidieron el {a} y el {b} el mismo día? Interpreta el alcance multi-lotería.{_NO_INVENT}",
        )

    # 15 follow-ups interpretativos
    for k in range(15):
        a, b = _pair(80 + k)
        add(
            "followup_interp",
            "¿Qué significa ese resultado? No inventes desgloses ni subtotales.",
            setup=[f"¿Han coincidido el {a} y el {b} el mismo día? Interpreta el alcance."],
        )

    # 10 "Tabla 1" semantics without workspace page commands
    for k in range(10):
        a, b = _pair(5 + k)
        add(
            "tabla1_semantics",
            f"Sin exportar ni paginar: interpreta las coincidencias same-day del {a} y el {b} como si revisaras la primera vista de evidencia (fechas y loterías).",
        )

    # 10 "Tabla 2" semantics
    for k in range(10):
        a, b = _pair(90 + k)
        add(
            "tabla2_semantics",
            f"Sin exportar: interpreta un segundo corte de evidencia para el {a} y el {b} same-day (posiciones y loterías distintas).",
        )

    # 10 complejas
    for k in range(10):
        a, b = _pair(100 + k)
        c, d = _pair(110 + k)
        add(
            "complex",
            f"Analiza en profundidad las coincidencias same-day del {a} y el {b}, y compara el patrón con el del {c} y el {d}, sin inventar números.",
        )

    # 10 cambio de tema → reasoning
    for k in range(10):
        a, b = _pair(120 + k)
        c, d = _pair(130 + k)
        add(
            "topic_switch_reasoning",
            f"Cambia de tema: ¿han coincidido el {c} y el {d} el mismo día? Interpreta el nuevo resultado.",
            setup=[f"¿Han coincidido el {a} y el {b} el mismo día? Interpreta."],
        )

    return cases


def main() -> None:
    cases = build_cases()
    assert len(cases) == 200, len(cases)
    bad = [c for c in cases if not c["expect"]["preflight_invoke"]]
    suite = {
        "suite": "SHADOW200_ELIGIBLE",
        "version": "2.0",
        "frozen_prompt": "7.0.0-rc3.4",
        "expected_hash": EXPECTED_HASH,
        "eligibility_rule": (
            "Cases designed for ReasoningModeSelector to invoke Huawei "
            "(interpret/compare/explain/clarify), never skip/factual_answer."
        ),
        "n": len(cases),
        "preflight_invoke_pass": len(cases) - len(bad),
        "preflight_invoke_fail": len(bad),
        "cases": cases,
    }
    out = OUT / "SHADOW200_ELIGIBLE_DATASET.json"
    out.write_text(json.dumps(suite, indent=2, ensure_ascii=False) + "\n")
    report = OUT.parent.parent.parent / "docs" / "prompt_runtime" / "SHADOW200_ELIGIBILITY_REPORT.md"
    # path: evidence/prompt_runtime/final_cert -> docs is ../../../docs? 
    # OUT = .../evidence/prompt_runtime/final_cert
    # docs = .../docs/prompt_runtime
    docs = Path("/Users/faustosantana/Projects/justech-forensic-audit/docs/prompt_runtime/SHADOW200_ELIGIBILITY_REPORT.md")
    cats: dict[str, int] = {}
    for c in cases:
        cats[c["category"]] = cats.get(c["category"], 0) + 1
    docs.write_text(
        f"""# Shadow200 Eligibility Report

**Dataset:** `evidence/prompt_runtime/final_cert/SHADOW200_ELIGIBLE_DATASET.json`  
**Frozen prompt:** 7.0.0-rc3.4 / `{EXPECTED_HASH}`  
**Cases:** {len(cases)}  
**Static preflight invoke:** {suite['preflight_invoke_pass']}/{len(cases)}  
**Preflight fails:** {len(bad)} {([b['id'] for b in bad[:20]] if bad else '')}

## Category distribution

| Category | N |
|----------|---|
"""
        + "\n".join(f"| {k} | {v} |" for k, v in sorted(cats.items()))
        + """

## Eligibility definition (runtime)

A case counts toward Shadow200 only when:

1. Route uses Huawei reasoning (not local_template / workspace / social).
2. Legacy + Studio shadow both call the provider.
3. Same Evidence Package.
4. Complete responses + guards.
5. Studio prompt hash matches frozen hash.
6. No unexpected fallback.

Workspace / local_template / deterministic routes are tracked in **Routing200**, not in Shadow200 denominator.

## Concurrency policy

`concurrency=1` (sequential) against DEV uvicorn `--workers 1`, because dual Huawei shadow calls already serialize provider load per turn.

## Notes

- Tabla1/Tabla2 categories use **semantic** wording without export/pagination commands to avoid Investigation Workspace capture.
- Follow-ups keep a Huawei-eligible setup turn then an interpretative user turn.
""",
        encoding="utf-8",
    )
    print(json.dumps({"n": len(cases), "preflight_fail": len(bad), "cats": cats}, indent=2))


if __name__ == "__main__":
    main()
