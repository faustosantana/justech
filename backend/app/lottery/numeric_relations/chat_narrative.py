"""Narrativa conversacional del motor — solo hechos del AnalysisResult (sin LLM math)."""

from __future__ import annotations

from typing import Any


def format_numeric_relations_reply(data: dict[str, Any]) -> str:
    """Plantilla determinística usada por Lottery IA / Huawei (no inventa datos)."""
    observed = data.get("observed_number")
    mother = data.get("mother_code")
    used = data.get("occurrences_used") or 0
    found = data.get("occurrences_found") or 0
    lots = ", ".join(str(x) for x in (data.get("lottery_names") or data.get("lottery_ids") or []))
    companions = data.get("direct_companions") or data.get("companions_analyzed") or []
    ranking = data.get("ranking") or []
    limit = data.get("occurrence_limit") or {}
    limit_s = (
        "todas las ocurrencias"
        if limit.get("mode") == "all"
        else f"últimas {limit.get('k')} ocurrencias"
    )
    if used == 0:
        return (
            f"Analicé el número observado {observed} (código madre {mother}) en {lots or 'las loterías indicadas'} "
            f"con límite «{limit_s}». No encontré ocurrencias históricas donde saliera ese número, "
            "así que no hay compañeros fortalecidos ni ranking que reportar. "
            "No invento compañeros, códigos, vecinos ni puntuaciones. "
            "Esto es una señal histórica del método, no una certeza ni garantía."
        )
    lines = [
        f"Analicé el número observado {observed} (código madre {mother}) en {lots}.",
        f"Límite solicitado: {limit_s}. Ocurrencias encontradas en histórico: {found}; usadas: {used}.",
        f"Compañeros de Tabla 1: {', '.join(str(c) for c in companions) or 'ninguno'}.",
    ]
    if ranking:
        top = ranking[0]
        lines.append(
            f"Primero en el ranking: {top.get('number')} con puntuación {top.get('score')}."
        )
        neigh = top.get("matched_neighbors") or []
        if neigh:
            lines.append(
                f"Vecinos que lo fortalecieron: {', '.join(str(x) for x in neigh)}."
            )
        match_bits = []
        for m in (top.get("matches") or [])[:6]:
            match_bits.append(
                f"{m.get('neighbor')} en {m.get('lottery_name')} "
                f"({m.get('draw_date')}, pos {m.get('position')})"
            )
        if match_bits:
            lines.append("Sorteos de refuerzo: " + "; ".join(match_bits) + ".")
        lines.append("Ranking completo (incluye score 0):")
        for i, c in enumerate(ranking, start=1):
            lines.append(
                f"{i}. {c.get('number')} — score {c.get('score')} "
                f"(T2={c.get('table2_code')}, vecinos {', '.join(str(x) for x in (c.get('neighbors') or []))})"
            )
    lines.append(
        "Aclaración: es una señal histórica del método de relaciones numéricas; "
        "no es certeza ni garantía de resultados futuros, ni recomendación de apuestas."
    )
    return "\n".join(lines)
