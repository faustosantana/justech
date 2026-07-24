"""J-9 — Historial del Número: perfil, apariciones, 7 sorteos, por qué, comparador.

Reutiliza catálogo T1/T2 y motor histórico J-1→J-6. No recalcula fórmulas.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import date, timedelta, time
from typing import Any, Literal

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.historical.conditions import (
    build_events_for_anchor,
    collect_anchor_draws,
)
from app.lottery.numeric_relations.historical.confirmation import neighbors_for_candidate
from app.lottery.numeric_relations.historical.enums import SampleTier
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    DrawRef,
    LotteryScope,
    PosteriorOutcome,
)
from app.lottery.numeric_relations.historical.presentation import (
    build_structured_explanation,
    condition_verdict,
    format_cycle_sentence,
    format_rate_sentence,
    natural_occurrence_line,
)
from app.lottery.numeric_relations.historical.rates import rates_payload
from app.lottery.numeric_relations.historical.sample import classify_sample, sample_warning
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION

_SAMPLE_LABELS = {
    SampleTier.EMPTY: "Sin muestra",
    SampleTier.VERY_LOW: "Muestra muy baja",
    SampleTier.LOW: "Muestra baja",
    SampleTier.MODERATE: "Muestra moderada",
    SampleTier.SOLID: "Muestra más sólida",
}

WEEKDAYS_ES = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]
MONTHS_ES = [
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
]


def _trace_id() -> str:
    return str(uuid.uuid4())


def _date_label(d: date) -> str:
    return f"{d.day} de {MONTHS_ES[d.month]} de {d.year}"


class NumberExplorerService:
    """Expediente visual del número observado — orquesta servicios históricos existentes."""

    def __init__(
        self,
        *,
        universe: InMemoryDrawUniverse,
        catalog: TableCatalog | None = None,
    ) -> None:
        self.universe = universe
        self.catalog = catalog or build_catalog()

    def _anchors(
        self,
        number: int,
        scope: LotteryScope,
        date_from: date | None,
        date_to: date | None,
    ) -> list[DrawRef]:
        return collect_anchor_draws(
            self.universe,
            observed_number=number,
            primary_lottery_ids=list(scope.primary_lottery_ids),
            date_from=date_from,
            date_to=date_to,
        )

    def _analyze_anchor(
        self,
        *,
        number: int,
        anchor: DrawRef,
        scope: LotteryScope,
        window: ConfirmationWindowConfig,
        max_horizon: int,
    ) -> dict[str, Any]:
        atomics, combos = build_events_for_anchor(
            observed_number=number,
            anchor=anchor,
            scope=scope,
            window=window,
            universe=self.universe,
            catalog=self.catalog,
            max_horizon=max_horizon,
        )
        candidates = self.catalog.get_table1_companions(int(number))
        combo_dicts = [c.to_dict() for c in combos]
        atomic_dicts = [a.to_dict() for a in atomics]
        verdict = condition_verdict(candidates=candidates, combination_events=combo_dicts)
        tree = build_structured_explanation(
            observed_number=number,
            candidates=candidates,
            combination_events=combo_dicts,
            statistics=None,
        )
        # Full tree with all neighbors (appeared or not)
        full_tree = self._full_relation_tree(number, candidates, combo_dicts)
        return {
            "anchor": anchor.to_dict(),
            "candidates": candidates,
            "atomic_events": atomic_dicts,
            "combination_events": combo_dicts,
            "verdict": verdict,
            "explanation": tree,
            "relation_tree": full_tree,
            "natural_line": (
                natural_occurrence_line(combo_dicts[0])
                if combo_dicts
                else (
                    f"{_date_label(anchor.draw_date)} — {anchor.lottery_name}. "
                    f"Salió el {number}, pero ninguno de sus compañeros recibió confirmación "
                    "dentro de la ventana seleccionada."
                )
            ),
        }

    def _full_relation_tree(
        self,
        observed: int,
        candidates: list[int],
        combo_dicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        found_by_cand: dict[int, set[int]] = defaultdict(set)
        hit_detail: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for e in combo_dicts:
            c = int(e["candidate"])
            for h in e.get("hits") or []:
                v = int(h.get("confirmer_number"))
                found_by_cand[c].add(v)
                hit_detail[(c, v)].append(
                    {
                        "loteria": h.get("confirmer_lottery_name"),
                        "fecha_hora": h.get("confirmer_datetime"),
                        "sorteo": h.get("confirmer_draw_id"),
                    }
                )
        branches = []
        for c in candidates:
            _code, _group, neighbors = neighbors_for_candidate(self.catalog, int(c))
            kids = []
            for v in neighbors:
                appeared = v in found_by_cand.get(c, set())
                kids.append(
                    {
                        "numero": v,
                        "aparecio": appeared,
                        "etiqueta": "✓ apareció" if appeared else "✕ no apareció",
                        "evidencias": hit_detail.get((c, v), []),
                    }
                )
            confs = sorted(found_by_cand.get(c, set()))
            branches.append(
                {
                    "candidato": c,
                    "confirmaciones": len(confs),
                    "confirmadores_encontrados": confs,
                    "estado": "Confirmado" if confs else "Sin confirmación",
                    "fuerza": (
                        "alta"
                        if len(confs) >= 3
                        else "media"
                        if len(confs) == 2
                        else "baja"
                        if len(confs) == 1
                        else "ninguna"
                    ),
                    "vecinos_tabla2": kids,
                }
            )
        return {
            "numero_que_salio": int(observed),
            "candidatos": branches,
            "aclaracion": (
                "El confirmador aporta la evidencia. La fuerza la recibe el compañero de "
                "Tabla 1 al cual pertenece."
            ),
        }

    def profile(
        self,
        *,
        number: int,
        scope: LotteryScope,
        window: ConfirmationWindowConfig,
        date_from: date | None = None,
        date_to: date | None = None,
        max_horizon: int = 7,
    ) -> dict[str, Any]:
        n = int(number)
        anchors = self._anchors(n, scope, date_from, date_to)
        candidates = self.catalog.get_table1_companions(n)

        positive = 0
        negative = 0
        partial = 0
        by_year: Counter[str] = Counter()
        by_month: Counter[int] = Counter()
        by_weekday: Counter[int] = Counter()
        by_lottery: Counter[str] = Counter()
        cand_hist: Counter[int] = Counter()
        conf_hist: Counter[int] = Counter()
        posteriors = []

        for anchor in anchors:
            analyzed = self._analyze_anchor(
                number=n,
                anchor=anchor,
                scope=scope,
                window=window,
                max_horizon=max_horizon,
            )
            st = analyzed["verdict"]["status"]
            if st == "yes":
                positive += 1
            elif st == "partial":
                partial += 1
            else:
                negative += 1
            by_year[str(anchor.draw_date.year)] += 1
            by_month[anchor.draw_date.month] += 1
            by_weekday[anchor.draw_date.weekday()] += 1
            by_lottery[anchor.lottery_name] += 1
            for e in analyzed["combination_events"]:
                cand_hist[int(e["candidate"])] += 1
                for v in e.get("confirmers") or []:
                    conf_hist[int(v)] += 1
                p = e.get("posterior")
                if not p:
                    continue
                posteriors.append(
                    PosteriorOutcome(
                        candidate=int(p["candidate"]),
                        anchor_draw_id=str(p["anchor_draw_id"]),
                        confirmation_draw_ids=list(p.get("confirmation_draw_ids") or []),
                        follow_up_lottery_ids=list(p.get("follow_up_lottery_ids") or []),
                        first_response_draw_id=p.get("first_response_draw_id"),
                        draws_until_response=p.get("draws_until_response"),
                        responded_next_draw=p.get("responded_next_draw"),
                        responded_within_2=p.get("responded_within_2"),
                        responded_within_3=p.get("responded_within_3"),
                        responded_within_5=p.get("responded_within_5"),
                        responded_within_10=p.get("responded_within_10"),
                        censored=bool(p.get("censored")),
                        censored_horizons=list(p.get("censored_horizons") or []),
                        draws_examined=list(p.get("draws_examined") or []),
                        max_horizon=int(p.get("max_horizon") or max_horizon),
                    )
                )

        total = len(anchors)
        with_condition = positive + partial
        pct = round(100.0 * with_condition / total, 1) if total else None
        stats = rates_payload(posteriors)
        first = anchors[0] if anchors else None
        last = anchors[-1] if anchors else None
        sample_n = total
        tier = classify_sample(sample_n)

        header = {
            "titulo": f"EXPEDIENTE DEL NÚMERO {n}",
            "aparecio": total,
            "primera_aparicion": _date_label(first.draw_date) if first else None,
            "ultima_aparicion": _date_label(last.draw_date) if last else None,
            "loterias_donde_ha_salido": len(by_lottery),
            "periodo": (
                f"{first.draw_date.year}–{last.draw_date.year}" if first and last else None
            ),
            "nivel_evidencia": _SAMPLE_LABELS.get(tier, tier.value),
            "sample_warning": sample_warning(sample_n),
        }

        condition_summary = {
            "positivas": positive,
            "negativas": negative,
            "parciales": partial,
            "total_apariciones": total,
            "con_alguna_confirmacion": with_condition,
            "porcentaje_observado": pct,
            "texto": (
                f"En {with_condition} de las {total} veces que salió el número {n}, "
                f"al menos uno de sus compañeros de Tabla 1 recibió una confirmación de Tabla 2."
                if total
                else f"No hay apariciones del número {n} en el período y loterías seleccionados."
            ),
            "disclaimer": (
                "Estos son resultados históricos observados. No constituyen garantía de un resultado futuro."
            ),
        }

        charts = {
            "apariciones_por_anio": [
                {"anio": y, "cantidad": by_year[y]} for y in sorted(by_year.keys())
            ],
            "apariciones_por_loteria": [
                {
                    "loteria": k,
                    "cantidad": v,
                    "porcentaje": round(100.0 * v / total, 1) if total else 0,
                }
                for k, v in by_lottery.most_common()
            ],
            "condicion": [
                {"etiqueta": "Sí se dio la condición", "cantidad": positive},
                {"etiqueta": "Se dio parcialmente", "cantidad": partial},
                {"etiqueta": "No se dio la condición", "cantidad": negative},
            ],
            "condicion_censurados": 0,  # filled below with seven-draw censura
            "candidatos_fortalecidos": [
                {"candidato": k, "veces": v} for k, v in cand_hist.most_common()
            ],
            "confirmadores": [
                {"confirmador": k, "veces": v} for k, v in conf_hist.most_common(20)
            ],
            "por_mes": [
                {"mes": MONTHS_ES[m], "mes_num": m, "cantidad": by_month.get(m, 0)}
                for m in range(1, 13)
            ],
            "por_dia_semana": [
                {"dia": WEEKDAYS_ES[i], "cantidad": by_weekday.get(i, 0)} for i in range(7)
            ],
            "ciclos": stats.get("cycles"),
            "tasas": stats.get("aliases"),
        }

        # seven-draw response distribution from posteriors
        seven_dist = Counter()
        censored_7 = 0
        evaluable_7 = 0
        for p in posteriors:
            if p.draws_until_response is None:
                available = len(p.draws_examined)
                if p.censored or available < 7:
                    censored_7 += 1
                    continue
                evaluable_7 += 1
                seven_dist["no_aparecio_en_7"] += 1
            elif int(p.draws_until_response) <= 7:
                evaluable_7 += 1
                seven_dist[str(int(p.draws_until_response))] += 1
            else:
                evaluable_7 += 1
                seven_dist["no_aparecio_en_7"] += 1
        charts["condicion_censurados"] = censored_7
        charts["respuesta_en_siete_sorteos"] = {
            "casos_evaluables": evaluable_7,
            "por_posicion": [
                {
                    "sorteo": i,
                    "cantidad": seven_dist.get(str(i), 0),
                    "evaluables": evaluable_7,
                    "porcentaje": (
                        round(100.0 * seven_dist.get(str(i), 0) / evaluable_7, 1)
                        if evaluable_7
                        else 0
                    ),
                }
                for i in range(1, 8)
            ],
            "no_aparecio_en_7": seven_dist.get("no_aparecio_en_7", 0),
            "sin_seguimiento_suficiente": censored_7,
        }

        # Enrich candidatos with display-only historical hints from aliases when available
        r3 = (stats.get("aliases") or {}).get("response_rate_within_3") or {}
        r3_den = int(r3.get("denominator") or r3.get("sample_size") or 0) or None
        r3_num = int(r3.get("numerator") or 0) if r3_den else None
        charts["candidatos_fortalecidos"] = [
            {
                "candidato": k,
                "veces": v,
                "casos_evaluables": r3_den,
                "respuesta_en_3": (
                    f"{r3_num} de {r3_den}" if r3_den is not None and r3_num is not None else None
                ),
            }
            for k, v in cand_hist.most_common()
        ]

        # Señales para UI (orden de visualización; no es ranking oficial de fuerza)
        cycle = (stats.get("cycles") or {}).get("typical_cycle_draws")
        signals = []
        for k, v in cand_hist.most_common(12):
            signals.append(
                {
                    "number": int(k),
                    "confirmation_count": int(v),
                    "evaluable_cases": int(r3_den or v),
                    "rate_within_3": (
                        float(r3.get("rate")) if r3.get("rate") is not None else None
                    ),
                    "typical_cycle": float(cycle) if cycle is not None else None,
                    "evidence_level": header["nivel_evidencia"],
                    "activators_text": (
                        f"El número {n} activó fortalezas sobre el {k} en {v} ocasión(es) "
                        f"con confirmadores de Tabla 2."
                    ),
                    "historical_rate_label": (
                        format_rate_sentence(r3, within_label="dentro de tres sorteos")
                        if r3
                        else "Sin tasa histórica agregada para este período."
                    ),
                    "typical_cycle_label": (
                        format_cycle_sentence(stats.get("cycles") or {})
                        if stats.get("cycles")
                        else "Ciclo no calculado."
                    ),
                }
            )
        charts["senales"] = signals

        top_cand = cand_hist.most_common(1)[0][0] if cand_hist else None
        top_conf = conf_hist.most_common(1)[0][0] if conf_hist else None
        top_lot = by_lottery.most_common(1)[0] if by_lottery else None
        narrative = self._profile_narrative(
            n=n,
            total=total,
            top_lot=top_lot,
            with_condition=with_condition,
            top_cand=top_cand,
            top_conf=top_conf,
            r3=r3,
            cycles=stats.get("cycles") or {},
            first=first,
            last=last,
        )

        return {
            "methodology_version": METHODOLOGY_VERSION,
            "trace_id": _trace_id(),
            "effective_parameters": {
                "number": n,
                "mother_code": n,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "max_horizon": max_horizon,
                "confirmation_window": window.to_dict(),
                "lottery_scope": scope.to_dict(),
            },
            "header": header,
            "condition_summary": condition_summary,
            "table1_candidates": candidates,
            "charts": charts,
            "statistics": stats,
            "sample_size": sample_n,
            "evaluable_events": int((r3.get("denominator") if r3 else 0) or 0),
            "censored_events": int((r3.get("censored_count") if r3 else 0) or 0),
            "resumen_automatico": narrative,
            "methodology_steps": self._methodology_steps(n, candidates),
        }

    def _profile_narrative(self, **kw: Any) -> str:
        n = kw["n"]
        total = kw["total"]
        lines = []
        if not total:
            return (
                f"No se encontraron apariciones del número {n} con los filtros actuales.\n\n"
                "Estos son resultados históricos observados. No constituyen garantía de un resultado futuro."
            )
        first, last = kw["first"], kw["last"]
        lines.append(
            f"El número {n} apareció {total} veces entre {first.draw_date.year} y {last.draw_date.year}."
        )
        if kw["top_lot"]:
            lines.append(
                f"Salió con mayor frecuencia en {kw['top_lot'][0]}, con {kw['top_lot'][1]} apariciones."
            )
        lines.append(
            f"En {kw['with_condition']} ocasiones se produjo al menos una confirmación para sus compañeros de Tabla 1."
        )
        if kw["top_cand"] is not None:
            lines.append(f"El candidato fortalecido con mayor frecuencia fue el {kw['top_cand']}.")
        if kw["top_conf"] is not None and kw["top_cand"] is not None:
            lines.append(
                f"El confirmador más frecuente asociado fue el {kw['top_conf']}."
            )
        r3 = kw["r3"]
        if r3 and r3.get("denominator"):
            lines.append(
                f"Cuando hubo confirmación, el candidato apareció dentro de los siguientes tres sorteos "
                f"en {r3.get('numerator')} de {r3.get('denominator')} casos evaluables."
            )
        cycles = kw["cycles"]
        if cycles.get("median") is not None:
            med = cycles["median"]
            lines.append(
                f"El ciclo típico observado fue de {int(med) if float(med).is_integer() else med} sorteos."
            )
        if cycles.get("events_censored"):
            lines.append(
                f"En {cycles['events_censored']} casos no existían suficientes sorteos posteriores para determinar el resultado."
            )
        lines.append(
            "Estos son resultados históricos observados. No constituyen garantía de un resultado futuro."
        )
        return "\n\n".join(lines)

    def _methodology_steps(self, n: int, candidates: list[int]) -> list[dict[str, str]]:
        example_c = candidates[0] if candidates else None
        neighbors = (
            self.catalog.get_table2_neighbors(example_c, exclude_self=True) if example_c else []
        )
        return [
            {
                "paso": 1,
                "titulo": "Salió el número",
                "texto": f"Salió el {n} (código madre de Tabla 1 = {n}).",
            },
            {
                "paso": 2,
                "titulo": "Tabla 1 encuentra sus compañeros",
                "texto": f"Los compañeros del código {n} son: {', '.join(str(x) for x in candidates) or 'ninguno'}.",
            },
            {
                "paso": 3,
                "titulo": "Tabla 2 busca confirmadores",
                "texto": (
                    f"El compañero {example_c} puede ser confirmado por: {', '.join(str(x) for x in neighbors[:8])}."
                    if example_c
                    else "Cada compañero consulta su grupo en Tabla 2."
                ),
            },
            {
                "paso": 4,
                "titulo": "Se fortalece el compañero",
                "texto": (
                    "Si aparece un confirmador, la fuerza la recibe el compañero de Tabla 1. "
                    "El confirmador no se fortalece por confirmar."
                ),
            },
            {
                "paso": 5,
                "titulo": "Se revisa qué pasó después",
                "texto": "Se observan los sorteos posteriores reales de la lotería de seguimiento.",
            },
        ]

    def occurrences(
        self,
        *,
        number: int,
        scope: LotteryScope,
        window: ConfirmationWindowConfig,
        date_from: date | None = None,
        date_to: date | None = None,
        max_horizon: int = 7,
        page: int = 1,
        page_size: int = 20,
        year: int | None = None,
        lottery_id: str | None = None,
        condition: Literal["all", "positive", "negative", "partial"] = "all",
        candidate: int | None = None,
        confirmer: int | None = None,
        order: Literal["desc", "asc"] = "desc",
    ) -> dict[str, Any]:
        anchors = self._anchors(number, scope, date_from, date_to)
        if order == "desc":
            anchors = list(reversed(anchors))
        items_all = []
        for anchor in anchors:
            if year and anchor.draw_date.year != year:
                continue
            if lottery_id and str(anchor.lottery_id) != str(lottery_id):
                continue
            analyzed = self._analyze_anchor(
                number=number,
                anchor=anchor,
                scope=scope,
                window=window,
                max_horizon=max_horizon,
            )
            st = analyzed["verdict"]["status"]
            if condition == "positive" and st != "yes":
                continue
            if condition == "negative" and st != "no":
                continue
            if condition == "partial" and st != "partial":
                continue
            if candidate is not None:
                if not any(int(e["candidate"]) == int(candidate) for e in analyzed["combination_events"]):
                    if st != "no":
                        continue
                    # negative cases have no candidate match — skip if filtering by candidate
                    continue
            if confirmer is not None:
                if not any(
                    int(confirmer) in (e.get("confirmers") or [])
                    for e in analyzed["combination_events"]
                ):
                    continue
            items_all.append(
                {
                    "draw_id": str(anchor.draw_id),
                    "fecha": anchor.draw_date.isoformat(),
                    "fecha_texto": _date_label(anchor.draw_date),
                    "loteria": anchor.lottery_name,
                    "lottery_id": str(anchor.lottery_id),
                    "estado": analyzed["verdict"]["headline"],
                    "status": st,
                    "texto": analyzed["natural_line"],
                    "candidatos_confirmados": analyzed["verdict"]["confirmed_numbers"],
                }
            )
        total = len(items_all)
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        start = (page - 1) * page_size
        slice_items = items_all[start : start + page_size]
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "trace_id": _trace_id(),
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": slice_items,
            "effective_parameters": {
                "number": int(number),
                "year": year,
                "lottery_id": lottery_id,
                "condition": condition,
                "candidate": candidate,
                "confirmer": confirmer,
                "order": order,
            },
        }

    def occurrence_detail(
        self,
        *,
        number: int,
        draw_id: str,
        scope: LotteryScope,
        window: ConfirmationWindowConfig,
        max_horizon: int = 7,
    ) -> dict[str, Any]:
        anchor = self.universe.get_draw(str(draw_id))
        if not anchor:
            raise ValueError(f"draw_id no encontrado: {draw_id}")
        if int(number) not in anchor.numbers_1_to_100():
            raise ValueError(f"El número {number} no aparece en el sorteo {draw_id}")
        analyzed = self._analyze_anchor(
            number=number,
            anchor=anchor,
            scope=scope,
            window=window,
            max_horizon=max_horizon,
        )
        why = []
        for branch in analyzed["relation_tree"]["candidatos"]:
            if branch["confirmaciones"] > 0:
                why.append(self.why_strengthened(number=number, candidate=branch["candidato"], analyzed=analyzed))
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "trace_id": _trace_id(),
            "modo": "aparicion_especifica",
            **analyzed,
            "por_que_fortalecidos": why,
            "effective_parameters": {
                "number": int(number),
                "draw_id": str(draw_id),
                "max_horizon": max_horizon,
                "confirmation_window": window.to_dict(),
                "lottery_scope": scope.to_dict(),
            },
        }

    def why_strengthened(
        self,
        *,
        number: int,
        candidate: int,
        analyzed: dict[str, Any] | None = None,
        historical_sample: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Explicación determinista — la IA solo puede redactar, no cambiar números."""
        n = int(number)
        c = int(candidate)
        neighbors = self.catalog.get_table2_neighbors(c, exclude_self=True)
        found = []
        if analyzed:
            for e in analyzed.get("combination_events") or []:
                if int(e["candidate"]) == c:
                    found = [int(x) for x in (e.get("confirmers") or [])]
                    break
        steps = [
            f"Salió el número {n}.",
            f"Tabla 1 colocó al {c} entre sus compañeros del código {n}.",
            f"Tabla 2 relaciona al {c} con los números {', '.join(str(x) for x in neighbors) or '—'}.",
        ]
        if found:
            steps.append(
                f"En la ventana seleccionada aparecieron: {', '.join(str(x) for x in found)}."
            )
            steps.append(f"Por eso el {c} recibió {len(found)} confirmaciones.")
        else:
            steps.append("En esta ocasión no apareció ningún confirmador de Tabla 2.")
        hist_bits = []
        if historical_sample:
            hist_bits = [
                f"Esta misma relación se encontró {historical_sample.get('casos', '—')} veces en el histórico.",
                historical_sample.get("respuesta_3"),
                historical_sample.get("ciclo"),
            ]
            steps.extend([x for x in hist_bits if x])
        conclusion = (
            f"El sistema fortalece al {c} porque recibió evidencia de "
            f"{len(found)} número(s) relacionado(s) por Tabla 2"
            + (
                " y esa condición tiene antecedentes históricos trazables."
                if historical_sample
                else "."
            )
            if found
            else f"El {c} no fue fortalecido en esta ocasión."
        )
        return {
            "candidato": c,
            "observed_number": n,
            "table1_candidates": (
                list(analyzed.get("table1_candidates") or [])
                if analyzed and analyzed.get("table1_candidates")
                else (
                    [
                        int(b["candidato"])
                        for b in ((analyzed or {}).get("relation_tree") or {}).get("candidatos") or []
                    ]
                    if analyzed
                    else []
                )
            ),
            "related_confirmers": neighbors,
            "observed_confirmers": found,
            "confirmation_count": len(found),
            "historical_cases": (
                historical_sample.get("casos") if historical_sample else None
            ),
            "evaluable_cases": (
                historical_sample.get("evaluables") if historical_sample else None
            ),
            "response_within_3": (
                historical_sample.get("respuesta_3") if historical_sample else None
            ),
            "typical_cycle": (
                historical_sample.get("ciclo") if historical_sample else None
            ),
            "pasos": steps,
            "conclusion": conclusion,
            "confirmadores": found,
            "vecinos_tabla2": neighbors,
            "numeros_no_modificables_por_ia": True,
        }

    def next_draws(
        self,
        *,
        draw_id: str,
        follow_up_lottery_ids: list[str],
        count: int = 7,
        mode: Literal["DRAWS", "CALENDAR_DAYS"] = "DRAWS",
        tz_name: str = "America/Santo_Domingo",
        strengthened_candidates: list[int] | None = None,
        confirmer_watch: list[int] | None = None,
    ) -> dict[str, Any]:
        anchor = self.universe.get_draw(str(draw_id))
        if not anchor:
            raise ValueError(f"draw_id no encontrado: {draw_id}")
        count = max(1, min(30, int(count)))
        strengthened = set(int(x) for x in (strengthened_candidates or []))
        watch = set(int(x) for x in (confirmer_watch or []))

        sequence: list[DrawRef] = []
        if mode == "DRAWS":
            # merge follow-up lotteries chronologically after anchor
            pool: list[DrawRef] = []
            for lid in follow_up_lottery_ids:
                pool.extend(self.universe.draws_after(lid, after=anchor, k=count * 3, tz_name=tz_name))
            pool.sort(key=lambda d: (d.draw_date, d.draw_time or time(0, 0), str(d.draw_id)))
            seen = set()
            for d in pool:
                if str(d.draw_id) in seen:
                    continue
                seen.add(str(d.draw_id))
                sequence.append(d)
                if len(sequence) >= count:
                    break
        else:
            start = anchor.local_datetime(tz_name)
            end = start + timedelta(days=count)
            for lid in follow_up_lottery_ids:
                for d in self.universe.list_draws_for_lottery(lid):
                    dt = d.local_datetime(tz_name)
                    if start < dt <= end:
                        sequence.append(d)
            sequence.sort(key=lambda d: (d.draw_date, d.draw_time or time(0, 0), str(d.draw_id)))

        steps = []
        first_hit_offset = None
        for idx, d in enumerate(sequence, start=1):
            nums = d.numbers_1_to_100()
            hit_cands = sorted(set(nums) & strengthened)
            hit_confs = sorted(set(nums) & watch)
            if hit_cands and first_hit_offset is None:
                first_hit_offset = idx
            steps.append(
                {
                    "posicion": idx,
                    "etiqueta": f"Sorteo {idx}" if mode == "DRAWS" else f"Día/ventana {idx}",
                    "fecha": d.draw_date.isoformat(),
                    "fecha_texto": _date_label(d.draw_date),
                    "loteria": d.lottery_name,
                    "draw_id": str(d.draw_id),
                    "numeros_ganadores": nums,
                    "aparecio_candidato_fortalecido": hit_cands,
                    "aparecieron_confirmadores": hit_confs,
                    "texto": (
                        f"Apareció el {', '.join(str(x) for x in hit_cands)}."
                        if hit_cands
                        else (
                            f"Apareció el confirmador {', '.join(str(x) for x in hit_confs)}."
                            if hit_confs
                            else "No apareció el candidato fortalecido."
                        )
                    ),
                }
            )

        censored = mode == "DRAWS" and len(sequence) < count
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "trace_id": _trace_id(),
            "mode": mode,
            "mode_label": (
                "Próximos siete sorteos" if mode == "DRAWS" and count == 7 else f"Modo {mode}"
            ),
            "anchor_draw_id": str(draw_id),
            "requested_count": count,
            "returned_count": len(sequence),
            "censored": censored,
            "censored_texto": (
                "No había suficientes sorteos posteriores para completar la secuencia solicitada."
                if censored
                else None
            ),
            "first_response_offset": first_hit_offset,
            "steps": steps,
            "reproductor": [
                {"paso": 1, "titulo": "Aparece el número observado", "draw_id": str(draw_id)},
                {"paso": 2, "titulo": "Se consulta Tabla 1"},
                {"paso": 3, "titulo": "Aparecen los candidatos"},
                {"paso": 4, "titulo": "Se consulta Tabla 2"},
                {"paso": 5, "titulo": "Se encuentran los confirmadores"},
                {"paso": 6, "titulo": "Se fortalece el candidato correspondiente"},
                {
                    "paso": 7,
                    "titulo": "Se reproducen los sorteos posteriores",
                    "detalle": steps,
                },
                {
                    "paso": 8,
                    "titulo": "Resultado",
                    "texto": (
                        f"Respuesta observada: {first_hit_offset} sorteos."
                        if first_hit_offset
                        else (
                            "No apareció dentro de la secuencia."
                            if not censored
                            else "Seguimiento incompleto (censurado)."
                        )
                    ),
                },
            ],
        }

    def compare_numbers(
        self,
        *,
        number_a: int,
        number_b: int,
        scope: LotteryScope,
        window: ConfirmationWindowConfig,
        date_from: date | None = None,
        date_to: date | None = None,
        max_horizon: int = 7,
    ) -> dict[str, Any]:
        pa = self.profile(
            number=number_a,
            scope=scope,
            window=window,
            date_from=date_from,
            date_to=date_to,
            max_horizon=max_horizon,
        )
        pb = self.profile(
            number=number_b,
            scope=scope,
            window=window,
            date_from=date_from,
            date_to=date_to,
            max_horizon=max_horizon,
        )
        conclusions = []
        if pa["header"]["aparecio"] > pb["header"]["aparecio"]:
            conclusions.append(
                f"El número {number_a} tiene más apariciones ({pa['header']['aparecio']} vs {pb['header']['aparecio']})."
            )
        elif pb["header"]["aparecio"] > pa["header"]["aparecio"]:
            conclusions.append(
                f"El número {number_b} tiene más apariciones ({pb['header']['aparecio']} vs {pa['header']['aparecio']})."
            )
        ca = pa["condition_summary"]["con_alguna_confirmacion"]
        cb = pb["condition_summary"]["con_alguna_confirmacion"]
        if ca > cb:
            conclusions.append(f"El número {number_a} generó más condiciones positivas/parciales.")
        elif cb > ca:
            conclusions.append(f"El número {number_b} generó más condiciones positivas/parciales.")
        ra = (pa["charts"]["tasas"] or {}).get("response_rate_within_3") or {}
        rb = (pb["charts"]["tasas"] or {}).get("response_rate_within_3") or {}
        if ra.get("rate") is not None and rb.get("rate") is not None:
            if ra["rate"] > rb["rate"]:
                conclusions.append(
                    f"El número {number_a} tuvo una respuesta más frecuente dentro de tres sorteos."
                )
            elif rb["rate"] > ra["rate"]:
                conclusions.append(
                    f"El número {number_b} tuvo una respuesta más frecuente dentro de tres sorteos."
                )
        if pa["sample_size"] > pb["sample_size"]:
            conclusions.append(f"El número {number_a} tiene una muestra histórica mayor.")
        elif pb["sample_size"] > pa["sample_size"]:
            conclusions.append(f"El número {number_b} tiene una muestra histórica mayor.")
        if not conclusions:
            conclusions.append("Ambos números muestran un comportamiento histórico similar con estos filtros.")
        conclusions.append("No se declara un ganador absoluto.")
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "trace_id": _trace_id(),
            "number_a": pa,
            "number_b": pb,
            "conclusiones": conclusions,
        }
