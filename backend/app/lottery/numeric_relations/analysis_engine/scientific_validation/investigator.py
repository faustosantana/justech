"""J-11A investigator mode — answers from Phase 2 artifacts only (no invented rules)."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.scientific_validation.explainability import (
    explain_analysis_decisions,
)
from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
    get_phase2_results,
)


def investigator_answer(question: str, *, numbers: list[int] | None = None) -> dict[str, Any]:
    q = (question or "").lower()
    data = get_phase2_results()
    if not data:
        return {
            "mode": "investigador",
            "message": (
                "No hay resultados de la Fase 2 cargados. "
                "Ejecuta scripts/run_scientific_validation_phase2.py primero."
            ),
            "source": None,
        }

    # Errors / failing rules first (before generic "qué regla")
    if any(
        k in q
        for k in (
            "falla más",
            "falla mas",
            "regla falla",
            "errores",
            "último mes",
            "ultimo mes",
        )
    ):
        err = data.get("error_analysis") or {}
        patterns = err.get("repetitive_patterns") or {}
        top = sorted(patterns.items(), key=lambda x: -x[1])[:5]
        recent = [
            c
            for c in (err.get("sample_cases") or [])
            if str(c.get("date", "")).startswith("2026-06")
            or str(c.get("date", "")).startswith("2026-07")
        ]
        return {
            "mode": "investigador",
            "message": (
                f"Fallos totales={err.get('n_failures')} (rate={err.get('failure_rate')}). "
                f"Patrones más frecuentes: {top}. "
                f"Casos recientes 2026-06/07 en muestra: {len(recent)}."
            ),
            "patterns": patterns,
            "recent_sample": recent[:10],
            "source": "error_analysis",
        }

    if any(
        k in q
        for k in (
            "regla hizo ganar",
            "qué regla",
            "que regla",
            "por qué ganó",
            "porque gano",
        )
    ):
        samples = data.get("explainability_samples") or {}
        key = "35_14" if ("54" in q or "35" in q) else ("39_58" if "94" in q else "35_14")
        sample = samples.get(key) or next(iter(samples.values()), {})
        decisions = (sample or {}).get("decisions") or {}
        first = decisions.get("first") or {}
        rules = [
            r
            for r in (data.get("rule_inventory") or {}).get("rules") or []
            if r.get("status") == "confirmada_por_evidencia"
            and r["id"]
            in {
                "R02_T1_MOTHER_COMPANIONS",
                "R03_T2_CONFIRMATION",
                "R06_FUERTE_REQUIRES_T1xT2_STRICT",
                "R01_FULL_GRAPH_BEFORE_DISCOVERY",
            }
        ]
        return {
            "mode": "investigador",
            "message": (
                f"El {first.get('number')} quedó primero por: {first.get('why')}. "
                f"Evidencia: T1={first.get('evidence_had', {}).get('table1_sources')}, "
                f"T2={first.get('evidence_had', {}).get('table2_confirmers')}. "
                "Reglas confirmadas involucradas: "
                + ", ".join(r["id"] for r in rules)
            ),
            "first": first,
            "rules": rules,
            "source": "explainability_samples+rule_inventory",
        }

    if any(k in q for k in ("segunda", "segundo", "segunda mejor", "segunda opción")):
        if numbers:
            exp = explain_analysis_decisions(numbers, mode="socio")
            second = (exp.get("decisions") or {}).get("second")
        else:
            second = (
                ((data.get("explainability_samples") or {}).get("35_14") or {}).get("decisions")
                or {}
            ).get("second")
        if not second:
            return {
                "mode": "investigador",
                "message": "No hay segunda opción registrada en el análisis de referencia.",
                "source": "explainability",
            }
        return {
            "mode": "investigador",
            "message": (
                f"La segunda mejor opción fue {second.get('number')} "
                f"({second.get('classification')}), score={second.get('score')}. "
                f"Le faltó: {second.get('evidence_lacked')}."
            ),
            "second": second,
            "source": "explainability",
        }

    if any(k in q for k in ("patrón nuevo", "patron nuevo", "descubriste", "patrones")):
        pat = data.get("patterns") or {}
        stable = (pat.get("stable_observed_combos") or [])[:5]
        hyp = pat.get("hypothesis_only") or []
        return {
            "mode": "investigador",
            "message": (
                f"Patrones con soporte≥{pat.get('min_support')} en train: "
                f"{len(pat.get('frequent_origin_fuerte') or [])} pares origen→fuerte; "
                f"{len(stable)} combos estables. "
                "Hipótesis pendientes (no inventadas como reglas): "
                + ", ".join(h["id"] for h in hyp)
            ),
            "stable_combos": stable,
            "hypothesis_only": hyp,
            "source": "patterns_discovered",
            "disclaimer": pat.get("disclaimer"),
        }

    if any(k in q for k in ("mejor perfil", "calibración", "calibracion", "benchmark")):
        cal = data.get("calibration") or {}
        bench = data.get("benchmark") or {}
        return {
            "mode": "investigador",
            "message": (
                f"Mejor perfil de calibración: {cal.get('best_methodology_reproduction')}. "
                f"{cal.get('recommendation')} "
                f"Mejor variante de benchmark ciego: {bench.get('best_blind_variant')}."
            ),
            "calibration_ranking": cal.get("ranking"),
            "benchmark_table": bench.get("blind_benchmark_table"),
            "source": "calibration+benchmark",
        }

    return {
        "mode": "investigador",
        "message": (
            "Modo investigador activo. Pregunta por reglas, segunda opción, errores, "
            "patrones, calibración o benchmark. Respondo solo con artefactos de Fase 2."
        ),
        "available_keys": sorted(data.keys()),
        "source": "phase2_summary",
    }
