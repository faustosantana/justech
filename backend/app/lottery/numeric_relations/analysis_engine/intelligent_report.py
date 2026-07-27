"""Assemble IntelligentAnalysisReport from existing Complete Analysis results.

Presentation-only. Does NOT change Tabla 1/2, ranking, tiebreak, or historical math.
"""

from __future__ import annotations

from typing import Any

DISCLAIMER = (
    "Los resultados históricos y las estadísticas son únicamente informativos. "
    "No garantizan resultados futuros."
)
EVIDENCE_LEVEL_HELP = (
    "El nivel describe la cantidad y calidad de las evidencias encontradas. "
    "No representa una probabilidad garantizada de que el número salga."
)
HISTORICAL_BEHAVIOR_NOTE = (
    "Esto describe eventos anteriores y no garantiza resultados futuros."
)

_POS_LABEL = {
    "primera": "Primera posición",
    "first": "Primera posición",
    "1": "Primera posición",
    "segunda": "Segunda posición",
    "second": "Segunda posición",
    "2": "Segunda posición",
    "tercera": "Tercera posición",
    "third": "Tercera posición",
    "3": "Tercera posición",
}


def _pos_label(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    key = str(raw).strip().lower()
    return _POS_LABEL.get(key) or str(raw)


def _fmt_date_es(iso: str | None) -> str | None:
    if not iso:
        return None
    s = str(iso)[:10]
    try:
        y, m, d = s.split("-")
        months = (
            "",
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        )
        return f"{int(d)} de {months[int(m)]} de {y}"
    except Exception:
        return s


def _sample_quality(n_cases: int | None) -> dict[str, Any]:
    n = int(n_cases or 0)
    if n < 5:
        return {
            "key": "insuficiente",
            "label": "Evidencia insuficiente",
            "cases": n,
            "message": "Se encontraron pocos casos equivalentes.",
        }
    if n < 15:
        return {
            "key": "limitada",
            "label": "Evidencia limitada",
            "cases": n,
            "message": "La muestra histórica es limitada.",
        }
    if n < 30:
        return {
            "key": "moderada",
            "label": "Evidencia moderada",
            "cases": n,
            "message": "La muestra histórica es moderada.",
        }
    return {
        "key": "amplia",
        "label": "Muestra histórica amplia",
        "cases": n,
        "message": "La muestra histórica es amplia.",
    }


def _evidence_level(
    *,
    has_t1: bool,
    has_t2: bool,
    same_day: bool,
    routes: int,
    lotteries: int,
    exact_cases: int,
) -> tuple[str, str]:
    """Explanatory only — does not affect ranking."""
    score = 0
    if has_t1:
        score += 3
    if has_t2:
        score += 2
    if same_day:
        score += 2
    if routes >= 2:
        score += 1
    if lotteries >= 2:
        score += 1
    if exact_cases >= 30:
        score += 2
    elif exact_cases >= 15:
        score += 1
    elif exact_cases >= 5:
        score += 0
    else:
        score -= 1 if exact_cases == 0 and not (has_t1 and has_t2) else 0

    if score >= 8 and has_t1 and (has_t2 or same_day):
        return "muy_alta", "Muy alta"
    if score >= 6 and has_t1:
        return "alta", "Alta"
    if score >= 4:
        return "moderada", "Moderada"
    if score >= 2:
        return "limitada", "Limitada"
    return "insuficiente", "Insuficiente"


def _why_bullets(
    *,
    observed: int | None,
    primary: int | None,
    t1_sources: list[int],
    t2_confirmers: list[int],
    same_day: bool,
    lotteries: list[str],
    routes: int,
    exact_cases: int,
) -> list[str]:
    out: list[str] = []
    if observed is not None and primary is not None and t1_sources:
        out.append(f"El {observed} lo relaciona mediante Tabla 1.")
    if t2_confirmers and primary is not None:
        conf = ", ".join(str(x) for x in t2_confirmers[:3])
        out.append(f"El {conf} lo confirma mediante Tabla 2.")
    if same_day:
        out.append("La confirmación ocurrió en otra lotería el mismo día.")
    if len(lotteries) >= 2:
        out.append(f"Participaron {len(lotteries)} loterías independientes.")
    if routes >= 2:
        out.append(f"Se encontraron {routes} rutas de evidencia sin duplicados.")
    elif routes == 1:
        out.append("Se encontró una ruta de evidencia principal.")
    if exact_cases > 0:
        out.append("Existe comportamiento histórico equivalente.")
    return out


def _comparison_row(
    *,
    number: int,
    table1: bool,
    table2: bool,
    same_day: bool,
    exact_cases: int | None,
    level_label: str,
) -> dict[str, Any]:
    return {
        "number": number,
        "table1_support": bool(table1),
        "table2_support": bool(table2),
        "same_day_cross": bool(same_day),
        "historical_equivalent_cases": exact_cases,
        "historical_label": (
            f"{exact_cases} casos"
            if exact_cases is not None and exact_cases > 0
            else "No encontrada"
        ),
        "evidence_level_label": level_label,
    }


def assemble_intelligent_analysis_report(
    analysis: dict[str, Any],
    *,
    origin_lottery: str | None = None,
    origin_position: str | None = None,
    manual_confirmer: int | None = None,
) -> dict[str, Any]:
    """Transform technical analysis dict into UI-safe IntelligentAnalysisReport."""
    observed_numbers = [int(x) for x in (analysis.get("observed_numbers") or []) if x is not None]
    observed = observed_numbers[0] if observed_numbers else None
    primary = analysis.get("primary_signal") or {}
    primary_n = primary.get("number")
    if primary_n is not None:
        primary_n = int(primary_n)

    t1_sources = [int(x) for x in (primary.get("table1_sources") or []) if x is not None]
    t2_confirmers = [int(x) for x in (primary.get("table2_confirmers") or []) if x is not None]
    same_day_flag = bool(primary.get("same_day_cross_support"))
    crosses = list(analysis.get("same_day_cross") or [])
    if crosses:
        same_day_flag = True

    hist = analysis.get("historical_evidence") if isinstance(analysis.get("historical_evidence"), dict) else {}
    hist_error = bool(hist.get("error")) if hist else False
    metrics = (hist.get("metrics") or {}) if hist and not hist_error else {}
    card = (hist.get("evidence_card") or {}) if hist and not hist_error else {}
    rival_card = (hist.get("rival_card") or {}) if hist and not hist_error else {}
    narrative = (hist.get("narrative") or {}) if hist and not hist_error else {}
    explanation = analysis.get("explanation") if isinstance(analysis.get("explanation"), dict) else {}

    # Prefer explicit exact cases; historical layer may store equivalents as
    # evaluable/structural when similarity is amplified (level-2). Presentation only.
    exact_cases = int(
        metrics.get("exact_cases")
        or card.get("exact_historical_cases")
        or metrics.get("evaluable_cases")
        or metrics.get("structural_cases")
        or card.get("structural_historical_cases")
        or 0
    )
    exact_hits = int(metrics.get("exact_hits") or card.get("exact_hits") or 0)
    t1_family = int(metrics.get("t1_family_hits") or card.get("t1_family_hits") or 0)
    t2_neighbors = int(metrics.get("t2_neighbor_hits") or card.get("t2_neighbor_hits") or 0)
    d1 = int(metrics.get("d1_hits") or card.get("d1_hits") or 0)
    d3 = int(metrics.get("d3_hits") or card.get("d3_hits") or 0)
    d7 = int(metrics.get("d7_hits") or card.get("d7_hits") or 0)

    routes = int(
        card.get("independent_routes")
        or (analysis.get("evidence_summary") or {}).get("independent_paths")
        or (1 if t1_sources else 0) + (1 if t2_confirmers else 0)
    )

    def _norm_lot(name: str) -> str:
        return (
            str(name)
            .strip()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .lower()
        )

    # Participating lotteries: origin + same-day cross parties only (not all draws that day)
    lots: list[str] = []
    lots_norm: set[str] = set()

    def _add_lot(v: Any) -> None:
        if not v:
            return
        s = str(v).strip()
        key = _norm_lot(s)
        if not key or key in lots_norm:
            return
        lots_norm.add(key)
        lots.append(s)

    _add_lot(origin_lottery)
    for c in crosses:
        _add_lot(c.get("lottery_x"))
        _add_lot(c.get("lottery_y"))
    ctx = analysis.get("same_day_context") if isinstance(analysis.get("same_day_context"), dict) else {}
    # Include confirmer lottery from context appearances only when it matches confirmer numbers
    confirmer_nums = {int(x) for x in t2_confirmers}
    for a in ctx.get("appearances") or []:
        if not isinstance(a, dict):
            continue
        try:
            n = int(a.get("number"))
        except (TypeError, ValueError):
            continue
        if n in confirmer_nums or (observed is not None and n == observed):
            _add_lot(a.get("lottery"))

    level_key, level_label = _evidence_level(
        has_t1=bool(t1_sources),
        has_t2=bool(t2_confirmers),
        same_day=same_day_flag,
        routes=routes,
        lotteries=len(lots),
        exact_cases=exact_cases,
    )

    # Header confirmer (prefer same-day cross, else manual)
    confirmer_info = None
    if crosses:
        c0 = crosses[0]
        confirmer_info = {
            "number": c0.get("confirmer_y"),
            "lottery": c0.get("lottery_y"),
            "position": _pos_label(c0.get("position_y")),
        }
    elif manual_confirmer is not None:
        confirmer_info = {
            "number": int(manual_confirmer),
            "lottery": None,
            "position": None,
        }
    elif t2_confirmers:
        confirmer_info = {
            "number": t2_confirmers[0],
            "lottery": None,
            "position": None,
        }

    analysis_date = analysis.get("analysis_date") or ctx.get("date")
    positions = analysis.get("positions") or []
    position_label = _pos_label(origin_position or (positions[0] if positions else None))

    why = _why_bullets(
        observed=observed,
        primary=primary_n,
        t1_sources=t1_sources,
        t2_confirmers=t2_confirmers,
        same_day=same_day_flag,
        lotteries=lots,
        routes=routes,
        exact_cases=exact_cases,
    )

    # Brief conclusion
    brief = None
    if primary_n is not None and observed is not None:
        if t1_sources and t2_confirmers and same_day_flag:
            conf_n = (confirmer_info or {}).get("number") or (t2_confirmers[0] if t2_confirmers else None)
            brief = (
                f"El {primary_n} es el número más fortalecido porque el {observed} lo relaciona "
                f"mediante Tabla 1 y el {conf_n}, encontrado en otra lotería el mismo día, "
                f"lo confirma mediante Tabla 2."
            )
        elif t1_sources and t2_confirmers:
            brief = (
                f"El {primary_n} es el número más fortalecido porque el {observed} lo relaciona "
                f"mediante Tabla 1 y existe confirmación de Tabla 2."
            )
        elif t1_sources:
            brief = (
                f"El {primary_n} es el número más fortalecido porque proviene de la relación "
                f"principal de Tabla 1 con el {observed}."
            )
        else:
            brief = (
                explanation.get("summary")
                or primary.get("reason")
                or f"El {primary_n} obtuvo el mayor respaldo estructural disponible."
            )

    # Special states
    special_notes: list[str] = []
    if hist_error:
        special_notes.append(
            "El análisis matemático está disponible, pero no fue posible consultar el histórico en este momento."
        )
    elif exact_cases < 5 and not hist_error:
        special_notes.append(
            "Se encontraron pocos casos equivalentes. La conclusión se basa principalmente "
            "en las relaciones actuales de Tabla 1 y Tabla 2."
        )
    if t1_sources and not t2_confirmers:
        special_notes.append(
            "El candidato proviene de Tabla 1, pero no se encontró confirmación adicional de Tabla 2."
        )
    if not t1_sources and t2_confirmers:
        special_notes.append(
            "Esta alternativa tiene relación de Tabla 2, pero no posee respaldo principal de Tabla 1."
        )
    if not analysis_date and not same_day_flag:
        special_notes.append(
            "No se realizó cruce entre loterías porque el análisis no tiene una fecha asociada."
        )

    def _flags_from_classification(cls: str) -> tuple[bool, bool]:
        c = str(cls or "")
        if "VECINO_T2" in c or c.startswith("VECINO"):
            return False, True
        t1 = "FUERTE" in c or "PRINCIPAL" in c or "FAMILIA_T1" in c or "T1" in c
        t2 = "T2" in c or "VECINO" in c
        if "FUERTE_T1_T2" in c:
            return True, True
        return t1, t2

    def _append_comparison(an: int, cls: str = "", *, force_cases: int | None = None) -> None:
        if any(row["number"] == an for row in comparisons):
            return
        alt_t1, alt_t2 = _flags_from_classification(cls)
        alt_same = False
        alt_cases = force_cases
        if rival_card and int(rival_card.get("candidate_number") or 0) == an:
            alt_t1 = bool(rival_card.get("table1_support"))
            alt_t2 = bool(rival_card.get("table2_support"))
            alt_same = bool(rival_card.get("same_day_cross_support"))
            alt_cases = rival_card.get("exact_historical_cases") or rival_card.get(
                "structural_historical_cases"
            )
        alt_level = _evidence_level(
            has_t1=alt_t1,
            has_t2=alt_t2,
            same_day=alt_same,
            routes=(1 if alt_t1 else 0) + (1 if alt_t2 else 0),
            lotteries=0,
            exact_cases=int(alt_cases or 0),
        )[1]
        comparisons.append(
            _comparison_row(
                number=an,
                table1=alt_t1,
                table2=alt_t2,
                same_day=alt_same,
                exact_cases=int(alt_cases) if alt_cases not in (None, "") else None,
                level_label=alt_level,
            )
        )

    # Alternatives comparison (preserve engine order; explain existing rank only)
    alts_raw = list(analysis.get("alternatives") or [])
    ranked_raw = list(analysis.get("ranked_candidates") or [])
    comparisons: list[dict[str, Any]] = []
    if primary_n is not None:
        comparisons.append(
            _comparison_row(
                number=primary_n,
                table1=bool(t1_sources),
                table2=bool(t2_confirmers),
                same_day=same_day_flag,
                exact_cases=exact_cases if exact_cases else None,
                level_label=level_label,
            )
        )
    for alt in alts_raw[:3]:
        if not isinstance(alt, dict) or alt.get("number") is None:
            continue
        an = int(alt["number"])
        if primary_n is not None and an == primary_n:
            continue
        _append_comparison(an, str(alt.get("classification") or ""))

    # Include first Tabla-2-only rival from ranking when present (e.g. 07) for contrast
    for cand in ranked_raw[:25]:
        if not isinstance(cand, dict) or cand.get("number") is None:
            continue
        an = int(cand["number"])
        if primary_n is not None and an == primary_n:
            continue
        cls = str(cand.get("classification") or "")
        t1, t2 = _flags_from_classification(cls)
        if t2 and not t1:
            _append_comparison(an, cls)
            break

    # Prefer deterministic comparison text aligned with shown rows (no % / rates)
    comparison_text = None
    raw_cmp = narrative.get("comparison") or explanation.get("comparison")
    if isinstance(raw_cmp, str) and "%" not in raw_cmp and "probabilidad" not in raw_cmp.lower():
        comparison_text = raw_cmp
    if primary_n is not None and len(comparisons) >= 2:
        # Prefer a T2-only contrast row when available (matches UAT 54 vs 07)
        rival = next(
            (
                row
                for row in comparisons[1:]
                if row.get("table2_support") and not row.get("table1_support")
            ),
            comparisons[1],
        )
        if comparisons[0]["table1_support"]:
            comparison_text = (
                f"El {primary_n} supera al {rival['number']} porque posee respaldo de Tabla 1"
                + (", confirmación de Tabla 2" if comparisons[0]["table2_support"] else "")
                + (", cruce entre loterías del mismo día" if same_day_flag else "")
                + (
                    f" y evidencia histórica equivalente ({exact_cases} casos)"
                    if exact_cases
                    else ""
                )
                + f". El {rival['number']} "
                + (
                    "solo presenta una relación directa de Tabla 2."
                    if rival["table2_support"] and not rival["table1_support"]
                    else "tiene menor respaldo estructural."
                )
            )

    # Mathematical routes
    routes_visual: list[dict[str, Any]] = []
    if observed is not None and primary_n is not None and t1_sources:
        routes_visual.append(
            {
                "kind": "table1",
                "label": "Tabla 1",
                "from_number": observed,
                "to_number": primary_n,
                "via": "Tabla 1",
            }
        )
    for c in crosses[:3]:
        if c.get("confirmer_y") is not None and c.get("companion_c") is not None:
            routes_visual.append(
                {
                    "kind": "table2",
                    "label": "Tabla 2",
                    "from_number": c.get("confirmer_y"),
                    "to_number": c.get("companion_c"),
                    "via": "Tabla 2",
                    "lottery_from": c.get("lottery_y"),
                    "lottery_to": c.get("lottery_x"),
                }
            )
    if not any(r["kind"] == "table2" for r in routes_visual) and t2_confirmers and primary_n is not None:
        for y in t2_confirmers[:2]:
            routes_visual.append(
                {
                    "kind": "table2",
                    "label": "Tabla 2",
                    "from_number": y,
                    "to_number": primary_n,
                    "via": "Tabla 2",
                }
            )

    converge_text = None
    if primary_n is not None and len(routes_visual) >= 2:
        converge_text = f"Ambas rutas convergen en {primary_n}."

    # Timeline
    timeline: list[dict[str, Any]] = []
    step = 1
    if observed is not None:
        timeline.append(
            {
                "step": step,
                "title": "Número observado",
                "detail": (
                    f"{observed} salió en {origin_lottery}."
                    if origin_lottery
                    else f"Se analizó el número {observed}."
                ),
            }
        )
        step += 1
    if t1_sources and primary_n is not None and observed is not None:
        timeline.append(
            {
                "step": step,
                "title": "Relación principal",
                "detail": f"Tabla 1 relacionó el {observed} con el {primary_n}.",
            }
        )
        step += 1
    conf_n = (confirmer_info or {}).get("number")
    conf_lot = (confirmer_info or {}).get("lottery")
    if conf_n is not None:
        timeline.append(
            {
                "step": step,
                "title": "Confirmación",
                "detail": (
                    f"El {conf_n} salió en {conf_lot}."
                    if conf_lot
                    else f"Se consideró el confirmador {conf_n}."
                ),
            }
        )
        step += 1
    if t2_confirmers and primary_n is not None and conf_n is not None:
        timeline.append(
            {
                "step": step,
                "title": "Cruce matemático",
                "detail": f"Tabla 2 relacionó el {conf_n} con el {primary_n}.",
            }
        )
        step += 1
    if same_day_flag and primary_n is not None:
        timeline.append(
            {
                "step": step,
                "title": "Cruce del mismo día",
                "detail": f"Las dos rutas coincidieron en el {primary_n}.",
            }
        )
        step += 1
    if exact_cases > 0 and not hist_error:
        timeline.append(
            {
                "step": step,
                "title": "Revisión histórica",
                "detail": f"Se encontraron {exact_cases} casos equivalentes.",
            }
        )
        step += 1
        if exact_hits > 0 and primary_n is not None:
            timeline.append(
                {
                    "step": step,
                    "title": "Comportamiento posterior",
                    "detail": (
                        f"En {exact_hits} casos apareció el {primary_n} dentro de D+7."
                    ),
                }
            )
            step += 1
    if primary_n is not None:
        timeline.append(
            {
                "step": step,
                "title": "Selección final",
                "detail": f"El {primary_n} quedó como número más fortalecido.",
            }
        )

    # Recent cases (max 5 for initial UI)
    recent_raw = list(metrics.get("recent_cases") or card.get("recent_cases") or [])
    recent_cases = []
    for row in recent_raw[:5]:
        if not isinstance(row, dict):
            continue
        obs = row.get("observed") or []
        recent_cases.append(
            {
                "date": row.get("date"),
                "primary_number": row.get("candidate"),
                "confirmer": obs[1] if isinstance(obs, list) and len(obs) > 1 else None,
                "observed": obs[0] if isinstance(obs, list) and obs else observed,
                "lotteries": None,
                "result_number": row.get("result_number") or row.get("candidate"),
                "result_label": row.get("result"),
                "window": row.get("window"),
                "result_lottery": row.get("lottery_result"),
            }
        )

    sample = _sample_quality(exact_cases if not hist_error else None)

    # Deterministic explanation
    parts: list[str] = []
    if brief:
        parts.append(brief)
    if exact_cases and primary_n is not None and not hist_error:
        parts.append(
            f"Esta coincidencia también tiene respaldo histórico: se identificaron "
            f"{exact_cases} casos equivalentes"
            + (
                f" y en {exact_hits} de ellos apareció el {primary_n} dentro de los siete días siguientes."
                if exact_hits
                else "."
            )
        )
    if comparison_text:
        parts.append(comparison_text)
    warning = narrative.get("warning") or explanation.get("warning")
    if warning:
        parts.append(str(warning))
    deterministic = " ".join(parts).strip() or (
        explanation.get("summary") or explanation.get("conclusion") or "Análisis completado."
    )

    return {
        "title": "Informe inteligente del análisis",
        "observed_numbers": observed_numbers,
        "analysis_date": analysis_date,
        "analysis_date_label": _fmt_date_es(str(analysis_date)[:10] if analysis_date else None),
        "origin_lottery": origin_lottery,
        "origin_position": position_label,
        "confirmer": confirmer_info,
        "primary_candidate": primary_n,
        "alternatives": [int(a["number"]) for a in alts_raw if isinstance(a, dict) and a.get("number") is not None][:6],
        "evidence_level": level_key,
        "evidence_level_label": level_label,
        "evidence_level_help": EVIDENCE_LEVEL_HELP,
        "evidence_level_reason": brief,
        "brief_conclusion": brief,
        "why_evidence": why,
        "table1_evidence": {
            "present": bool(t1_sources),
            "sources": t1_sources,
            "target": primary_n,
        },
        "table2_evidence": {
            "present": bool(t2_confirmers),
            "confirmers": t2_confirmers,
            "target": primary_n,
        },
        "same_day_evidence": {
            "present": same_day_flag,
            "crosses": [
                {
                    "observed": c.get("observed_x"),
                    "companion": c.get("companion_c"),
                    "confirmer": c.get("confirmer_y"),
                    "lottery_origin": c.get("lottery_x"),
                    "lottery_confirmer": c.get("lottery_y"),
                    "position_origin": _pos_label(c.get("position_x")),
                    "position_confirmer": _pos_label(c.get("position_y")),
                }
                for c in crosses[:6]
                if isinstance(c, dict)
            ],
        },
        "independent_evidence_count": routes,
        "participating_lotteries": lots,
        "historical_metrics": None
        if hist_error
        else {
            "exact_cases": exact_cases,
            "exact_hits": exact_hits,
            "t1_family_hits": t1_family,
            "t2_neighbor_hits": t2_neighbors,
            "d1_hits": d1,
            "d3_hits": d3,
            "d7_hits": d7,
            "period_label": hist.get("period_label"),
            "behavior_label": "Comportamiento observado en el histórico",
            "behavior_note": HISTORICAL_BEHAVIOR_NOTE,
        },
        "historical_sample_quality": sample if not hist_error else None,
        "historical_unavailable": hist_error,
        "candidate_comparison": comparisons,
        "comparison_explanation": comparison_text,
        "reasoning_timeline": timeline,
        "mathematical_routes": routes_visual,
        "routes_converge_text": converge_text,
        "recent_equivalent_cases": recent_cases,
        "recent_cases_total_hint": exact_cases,
        "deterministic_explanation": deterministic,
        "special_notes": special_notes,
        "disclaimer": DISCLAIMER,
    }
