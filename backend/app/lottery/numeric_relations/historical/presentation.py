"""Presentación metodológica en lenguaje simple (sin inventar números)."""

from __future__ import annotations

from typing import Any


def condition_verdict(
    *,
    candidates: list[int],
    combination_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Sí / No / Parcial según candidatos con al menos una confirmación.
    """
    confirmed = sorted({int(e["candidate"]) for e in combination_events})
    total = len(candidates)
    n_conf = len(confirmed)
    if total == 0:
        status = "no"
        headline = "NO SE DIO LA CONDICIÓN"
        reason = "No se encontraron candidatos de Tabla 1 para el número observado."
    elif n_conf == 0:
        status = "no"
        headline = "NO SE DIO LA CONDICIÓN"
        reason = (
            f"Se generaron {total} candidatos, pero ninguno recibió confirmación "
            "de Tabla 2 dentro de la ventana seleccionada."
        )
    elif n_conf == total:
        status = "yes"
        headline = "SÍ, SE DIO LA CONDICIÓN"
        reason = f"Los {total} candidatos de Tabla 1 recibieron al menos una confirmación."
    else:
        status = "partial"
        headline = "SE DIO PARCIALMENTE"
        reason = (
            f"De {total} candidatos analizados, {n_conf} recibieron confirmación "
            f"y {total - n_conf} quedaron sin confirmación."
        )
    return {
        "status": status,
        "headline": headline,
        "reason": reason,
        "candidates_total": total,
        "candidates_confirmed": n_conf,
        "candidates_without_confirmation": max(0, total - n_conf),
        "confirmed_numbers": confirmed,
    }


def format_rate_sentence(rate: dict[str, Any] | None, *, within_label: str) -> str:
    if not rate:
        return f"No hay datos suficientes para {within_label}."
    num = int(rate.get("numerator") or 0)
    den = int(rate.get("denominator") or 0)
    pct = rate.get("rate_percent")
    cens = int(rate.get("censored_count") or 0)
    warn = rate.get("sample_warning")
    if den <= 0:
        base = f"No hubo casos evaluables para {within_label}."
    else:
        pct_txt = f", equivalente a un {pct} %" if pct is not None else ""
        base = (
            f"El número apareció {within_label} en {num} de {den} casos evaluables"
            f"{pct_txt}."
        )
    if cens:
        base += f" Además, {cens} casos no tenían suficientes sorteos posteriores para concluir."
    if warn:
        base += f" {warn}"
    return base


def format_cycle_sentence(cycles: dict[str, Any] | None) -> str:
    if not cycles:
        return "No hay ciclo histórico calculado."
    med = cycles.get("median")
    mean = cycles.get("mean")
    n = int(cycles.get("events_with_response") or 0)
    cens = int(cycles.get("events_censored") or 0)
    none = int(cycles.get("events_without_response_in_window") or 0)
    parts = []
    if med is not None:
        parts.append(f"Normalmente tardó {int(med) if float(med).is_integer() else med} sorteos en aparecer.")
    if mean is not None and med is not None and abs(float(mean) - float(med)) >= 0.5:
        parts.append(f"El promedio fue de {round(float(mean), 1)} sorteos.")
    parts.append(f"Hubo respuesta en {n} casos.")
    if none:
        parts.append(f"En {none} casos no apareció dentro de la ventana máxima.")
    if cens:
        parts.append(
            f"En {cens} casos no había suficientes sorteos posteriores para saber qué ocurrió."
        )
    return " ".join(parts)


def sample_sentence(n: int, tier: str | None = None) -> str:
    if n <= 0:
        return "No encontramos casos de esta condición."
    if n <= 4:
        return f"Solo encontramos {n} casos. La muestra es muy baja y debe interpretarse con mucha cautela."
    if n <= 9:
        return f"Solo encontramos {n} casos. La muestra es pequeña y debe interpretarse con cautela."
    if n <= 29:
        return f"Encontramos {n} casos. La muestra es moderada."
    return f"Encontramos {n} casos. La muestra histórica es más sólida."


def build_relation_tree(
    *,
    observed_number: int,
    candidates: list[int],
    combination_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Árbol visual: observado → candidatos → confirmadores."""
    by_cand: dict[int, dict[str, Any]] = {}
    for e in combination_events:
        c = int(e["candidate"])
        slot = by_cand.setdefault(
            c,
            {"candidate": c, "confirmers": [], "confirmations": 0, "hits": []},
        )
        confs = [int(x) for x in (e.get("confirmers") or [])]
        for v in confs:
            if v not in slot["confirmers"]:
                slot["confirmers"].append(v)
        slot["confirmations"] = len(slot["confirmers"])
        for h in e.get("hits") or []:
            slot["hits"].append(
                {
                    "confirmador": h.get("confirmer_number"),
                    "loteria": h.get("confirmer_lottery_name"),
                    "fecha_hora": h.get("confirmer_datetime"),
                    "sorteo": h.get("confirmer_draw_id"),
                }
            )

    branches = []
    for c in candidates:
        info = by_cand.get(c)
        if not info:
            branches.append(
                {
                    "numero": c,
                    "estado": "Sin confirmación",
                    "confirmadores": [],
                    "confirmaciones": 0,
                    "detalle_confirmadores": [],
                }
            )
        else:
            branches.append(
                {
                    "numero": c,
                    "estado": "Confirmado",
                    "confirmadores": info["confirmers"],
                    "confirmaciones": info["confirmations"],
                    "detalle_confirmadores": info["hits"],
                }
            )
    return {
        "numero_que_salio": int(observed_number),
        "etiqueta": "Compañeros de Tabla 1",
        "candidatos": branches,
    }


def build_structured_explanation(
    *,
    observed_number: int,
    candidates: list[int],
    combination_events: list[dict[str, Any]],
    statistics: dict[str, Any] | None = None,
    lottery_names: dict[str, str] | None = None,
    window_label: str = "la ventana seleccionada",
) -> dict[str, Any]:
    """Explicación estructurada con datos calculados (la IA solo puede redactar, no cambiar números)."""
    verdict = condition_verdict(candidates=candidates, combination_events=combination_events)
    tree = build_relation_tree(
        observed_number=observed_number,
        candidates=candidates,
        combination_events=combination_events,
    )
    stats = statistics or {}
    aliases = stats.get("aliases") or {}
    cycles = stats.get("cycles") or {}

    if combination_events:
        scored = sorted(
            combination_events,
            key=lambda e: (-int(e.get("score_raw") or 0), int(e["candidate"])),
        )
        top = scored[0]
        confs = [int(x) for x in (top.get("confirmers") or [])]
        hits = top.get("hits") or []
        lot = hits[0].get("confirmer_lottery_name") if hits else None
        if len(confs) > 1:
            listed = ", ".join(str(x) for x in confs[:-1]) + f" y {confs[-1]}"
            top_sentence = (
                f"El número {top['candidate']} fue confirmado por {listed} "
                f"({len(confs)} confirmaciones)."
            )
        elif confs:
            top_sentence = (
                f"El número {top['candidate']} fue confirmado porque el {confs[0]} apareció"
                + (f" en {lot}" if lot else "")
                + f" dentro de {window_label}."
            )
        else:
            top_sentence = f"El número {top['candidate']} recibió confirmación."
    else:
        top_sentence = (
            f"Ninguno de los compañeros {', '.join(str(x) for x in candidates) or '—'} "
            f"recibió confirmación de Tabla 2 dentro de {window_label}."
        )

    n_events = len(combination_events)
    hist_n = None
    r3 = aliases.get("response_rate_within_3") or {}
    if r3.get("denominator") is not None:
        hist_n = int(r3.get("sample_size") or r3.get("denominator") or 0)

    lines: list[str] = [
        verdict["headline"] + ".",
        "",
        (
            f"Cuando salió el {observed_number}, sus compañeros de Tabla 1 fueron "
            f"{', '.join(str(x) for x in candidates) if candidates else 'ninguno'}."
        ),
        "",
        top_sentence,
        "",
    ]
    if hist_n is not None and hist_n > 0:
        lines.append(
            f"Históricamente esta relación se ha presentado en una muestra de {hist_n} casos evaluables."
        )
        lines.append(
            format_rate_sentence(aliases.get("response_rate_next_draw"), within_label="en el próximo sorteo")
        )
        lines.append(
            format_rate_sentence(
                aliases.get("response_rate_within_3"),
                within_label="dentro de los próximos 3 sorteos",
            )
        )
        lines.append(format_cycle_sentence(cycles))
        lines.append(sample_sentence(hist_n))
    elif n_events:
        lines.append(f"En este análisis se encontraron {n_events} condiciones con confirmación.")
    lines.extend(
        [
            "",
            "Esto representa una respuesta histórica, no una garantía de resultado futuro.",
            (
                "El número que aparece como confirmador no recibe automáticamente la fuerza. "
                "La fuerza la recibe el compañero de Tabla 1 al cual pertenece esa confirmación."
            ),
        ]
    )
    narrative = "\n".join(lines)

    cards = []
    for branch in tree["candidatos"]:
        force = "alta" if branch["confirmaciones"] >= 3 else "media" if branch["confirmaciones"] == 2 else "baja" if branch["confirmaciones"] == 1 else "ninguna"
        cards.append(
            {
                "numero": branch["numero"],
                "titulo": f"Número {branch['numero']}",
                "confirmaciones": branch["confirmaciones"],
                "confirmado_por": branch["confirmadores"],
                "fuerza": force,
                "estado": branch["estado"],
            }
        )

    return {
        "verdict": verdict,
        "tree": tree,
        "cards": cards,
        "narrative": narrative,
        "sentences": {
            "rate_next": format_rate_sentence(aliases.get("response_rate_next_draw"), within_label="en el próximo sorteo"),
            "rate_within_3": format_rate_sentence(aliases.get("response_rate_within_3"), within_label="dentro de los próximos 3 sorteos"),
            "rate_within_5": format_rate_sentence(aliases.get("response_rate_within_5"), within_label="dentro de los próximos 5 sorteos"),
            "rate_within_10": format_rate_sentence(aliases.get("response_rate_within_10"), within_label="dentro de los próximos 10 sorteos"),
            "cycle": format_cycle_sentence(cycles),
            "sample": sample_sentence(hist_n or n_events),
        },
        "charts": {
            "strengthened": [
                {"numero": c["numero"], "confirmaciones": c["confirmaciones"]} for c in cards
            ],
            "confirmers": _confirmer_counts(combination_events),
        },
        "disclaimer": (
            "Respuesta histórica del método de relaciones entre Tabla 1 y Tabla 2. "
            "No es una probabilidad de ganar ni una garantía de resultado futuro."
        ),
    }


def _confirmer_counts(combination_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[int, int] = {}
    for e in combination_events:
        for v in e.get("confirmers") or []:
            counts[int(v)] = counts.get(int(v), 0) + 1
    return [
        {"confirmador": k, "veces": v}
        for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


def natural_occurrence_line(event: dict[str, Any]) -> str:
    """Una ocasión en lenguaje natural."""
    anchor = event.get("anchor") or {}
    date = anchor.get("draw_date") or "fecha desconocida"
    lot = anchor.get("lottery_name") or "lotería"
    n = event.get("observed_number")
    c = event.get("candidate")
    confs = event.get("confirmers") or []
    hits = event.get("hits") or []
    post = event.get("posterior") or {}
    conf_bits = []
    for h in hits:
        conf_bits.append(
            f"el {h.get('confirmer_number')} apareció en {h.get('confirmer_lottery_name')}"
        )
    conf_txt = "; ".join(conf_bits) if conf_bits else (
        f"confirmadores {', '.join(str(x) for x in confs)}" if confs else "sin confirmadores"
    )
    offset = post.get("draws_until_response")
    if offset is None and post.get("censored"):
        after = "No había suficientes sorteos posteriores para saber qué ocurrió con el candidato."
    elif offset is None:
        after = f"El {c} no reapareció dentro de la ventana máxima."
    elif int(offset) == 1:
        after = f"El {c} reapareció en el próximo sorteo."
    else:
        after = f"El {c} reapareció {offset} sorteos después."
    return (
        f"El {date} salió el {n} en {lot}. {conf_txt.capitalize() if conf_bits else conf_txt} "
        f"y confirmó al candidato {c}. {after}"
    )
