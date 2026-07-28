#!/usr/bin/env python3
"""Generate QUESTION_BANK.json — exactly 200 turns, 28 conversations, seed 20260727."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SEED = 20260727
OUT = Path(__file__).resolve().parents[1]
BANK = OUT / "QUESTION_BANK.json"
SHA = OUT / "QUESTION_BANK.sha256"

QUOTA = {
    "A": 20,
    "B": 20,
    "C": 20,
    "D": 25,
    "E": 20,
    "F": 15,
    "G": 15,
    "H": 15,
    "I": 10,
    "J": 15,
    "K": 10,
    "L": 15,
}

rng = random.Random(SEED)
CORE = [1, 3, 7, 14, 22, 24, 35, 39, 44, 54, 55, 58, 88, 94, 97, 99]
EXTRA = [n for n in range(1, 101) if n not in CORE]
SAMPLE = CORE + rng.sample(EXTRA, 25)


def mk(
    cat: str,
    msg: str,
    *,
    subjects: list | None = None,
    intent: str = "mixed",
    turn_type: str = "factual",
    filters: dict | None = None,
    tool_family: str | None = None,
    factual: bool = True,
    ambiguity: bool = False,
    auto_fail: list | None = None,
) -> dict:
    return {
        "category": cat,
        "user_message": msg,
        "expected_subjects": subjects or [],
        "expected_intent": intent,
        "expected_turn_type": turn_type,
        "expected_filters": filters or {},
        "expected_tool_family": tool_family,
        "factual_validation_required": factual,
        "ambiguity_expected": ambiguity,
        "automatic_fail_conditions": auto_fail
        or [
            "wrong_subject",
            "invented_date",
            "http_500",
            "internal_jargon",
            "fabricated_data",
        ],
    }


def build_turns() -> list[dict]:
    T: list[dict] = []

    # A 20
    A = [
        mk("A", "¿Cuándo fue la última vez que salió el 22?", subjects=["22"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuándo salió por última vez el 35?", subjects=["35"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Aparición más reciente del 97.", subjects=["97"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuál fue la última del 44?", subjects=["44"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Última vez del 54 en el histórico.", subjects=["54"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuándo salió el 94?", subjects=["94"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Última del 55.", subjects=["55"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuándo apareció el 24?", subjects=["24"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuándo salió por última vez el 03?", subjects=["03", "3"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Última vez del 07.", subjects=["07", "7"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuándo salió el 35 en Nacional?", subjects=["35"], filters={"lottery": "Nacional"}, intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Última del 88 en primera posición.", subjects=["88"], filters={"position": 1}, intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuándo salió el 14 en 2026?", subjects=["14"], filters={"year": 2026}, intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Dime la más reciente del veintidós.", subjects=["22"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Última aparición del 01.", subjects=["01", "1"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuándo salió el 99?", subjects=["99"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Última del 39.", subjects=["39"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuándo salió el 58?", subjects=["58"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "Última del 14 sin filtros.", subjects=["14"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("A", "¿Cuál fue la última del 88?", subjects=["88"], intent="last_occurrence", tool_family="last_occurrence"),
    ]
    assert len(A) == 20
    T.extend(A)

    # B 20
    B = [
        mk("B", "Últimas 3 del 35.", subjects=["35"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n", auto_fail=["limit_as_subject", "wrong_subject", "http_500"]),
        mk("B", "Dame las últimas 5 del 54.", subjects=["54"], filters={"limit": 5}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas 2 del 22.", subjects=["22"], filters={"limit": 2}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Las últimas diez del 97.", subjects=["97"], filters={"limit": 10}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas cuatro del 44.", subjects=["44"], filters={"limit": 4}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas 3 del 35 en Nacional.", subjects=["35"], filters={"limit": 3, "lottery": "Nacional"}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas 3 del 88 en primera.", subjects=["88"], filters={"limit": 3, "position": 1}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "¿Cuándo salió el 97?", subjects=["97"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("B", "¿Y las últimas 3?", subjects=["97"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Dame las dos anteriores a esas.", subjects=["97"], filters={"limit": 2}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Las otras tres.", subjects=["97"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Antes de esa lista, ¿qué hubo?", subjects=["97"], intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas tres del 55.", subjects=["55"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas 5 del 24.", subjects=["24"], filters={"limit": 5}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas 3 del 01.", subjects=["01", "1"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas 2 del 99.", subjects=["99"], filters={"limit": 2}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Cuatro más recientes del 39.", subjects=["39"], filters={"limit": 4}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas 3 del 58.", subjects=["58"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Cinco últimas del 14.", subjects=["14"], filters={"limit": 5}, intent="last_n_occurrences", tool_family="last_n"),
        mk("B", "Últimas 3 del 07.", subjects=["07", "7"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n"),
    ]
    assert len(B) == 20
    T.extend(B)

    # C 20
    C = [
        mk("C", "¿Cuántas veces salió el 54?", subjects=["54"], intent="frequency", tool_family="frequency"),
        mk("C", "Frecuencia total del 94.", subjects=["94"], intent="frequency", tool_family="frequency"),
        mk("C", "¿Cuántas veces el 35 en 2026?", subjects=["35"], filters={"year": 2026}, intent="frequency", tool_family="frequency"),
        mk("C", "Frecuencia del 22 por lotería.", subjects=["22"], intent="frequency", tool_family="frequency"),
        mk("C", "¿Cuántas veces el 97 en primera?", subjects=["97"], filters={"position": 1}, intent="frequency", tool_family="frequency"),
        mk("C", "Distribución histórica del 44.", subjects=["44"], intent="frequency", tool_family="frequency"),
        mk("C", "¿Cuántas veces el 01 en Nacional?", subjects=["01", "1"], filters={"lottery": "Nacional"}, intent="frequency", tool_family="frequency"),
        mk("C", "Años con mayor frecuencia del 88.", subjects=["88"], intent="frequency", tool_family="frequency"),
        mk("C", "Frecuencia del 55 en 2025.", subjects=["55"], filters={"year": 2025}, intent="frequency", tool_family="frequency"),
        mk("C", "¿Hubo meses en cero del 24 en Nacional 2026?", subjects=["24"], intent="frequency", tool_family="frequency"),
        mk("C", "Compara frecuencia del 54 en 2025 y 2026.", subjects=["54"], intent="frequency", tool_family="frequency"),
        mk("C", "¿Y solo en Leidsa?", subjects=["54"], filters={"lottery": "Leidsa"}, intent="frequency", tool_family="frequency"),
        mk("C", "Ahora el 94 en los mismos años.", subjects=["94"], intent="frequency", tool_family="frequency"),
        mk("C", "¿Cuál tuvo más apariciones en 2026?", subjects=["54", "94"], intent="frequency", tool_family="frequency"),
        mk("C", "Dame solo los conteos.", subjects=["54", "94"], intent="frequency", tool_family="frequency", turn_type="meta_brief"),
        mk("C", "¿Cuántas veces salió el 39?", subjects=["39"], intent="frequency", tool_family="frequency"),
        mk("C", "Frecuencia del 58.", subjects=["58"], intent="frequency", tool_family="frequency"),
        mk("C", "¿Cuántas del 14?", subjects=["14"], intent="frequency", tool_family="frequency"),
        mk("C", "Frecuencia del 03.", subjects=["03", "3"], intent="frequency", tool_family="frequency"),
        mk("C", "¿Cuántas veces el 99?", subjects=["99"], intent="frequency", tool_family="frequency"),
    ]
    assert len(C) == 20
    T.extend(C)

    # D 25
    D = [
        mk("D", "Compara el 54 con el 94 en todo el histórico.", subjects=["54", "94"], intent="compare_numbers", tool_family="compare"),
        mk("D", "¿Y solo en 2026?", subjects=["54", "94"], filters={"year": 2026}, intent="compare_numbers", tool_family="compare"),
        mk("D", "Ahora solo en primera posición.", subjects=["54", "94"], filters={"position": 1}, intent="compare_numbers", tool_family="compare"),
        mk("D", "¿Cuál salió más recientemente?", subjects=["54", "94"], intent="compare_numbers", tool_family="compare"),
        mk("D", "¿Cuál salió más veces?", subjects=["54", "94"], intent="compare_numbers", tool_family="compare"),
        mk("D", "¿Y si quitas Nacional?", subjects=["54", "94"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara el 22 y el 97.", subjects=["22", "97"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara 35 y 44.", subjects=["35", "44"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara 55 y 24.", subjects=["55", "24"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara 01 y 99.", subjects=["01", "1", "99"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara 39 y 58.", subjects=["39", "58"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara 14 y 88.", subjects=["14", "88"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara 03 y 07.", subjects=["03", "3", "07", "7"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara 94 y 35.", subjects=["94", "35"], intent="compare_numbers", tool_family="compare"),
        mk("D", "Compara Leidsa y Nacional para el 35.", subjects=["35"], intent="compare_lotteries", tool_family="compare"),
        mk("D", "Compara primera y segunda del 97.", subjects=["97"], intent="compare_positions", tool_family="compare"),
        mk("D", "Compara 2025 vs 2026 para el 44.", subjects=["44"], intent="compare", tool_family="compare"),
        mk("D", "Entre 22, 35 y 97, ¿cuál es más reciente?", subjects=["22", "35", "97"], intent="compare", tool_family="compare"),
        mk("D", "Compara regularidad de 54 y 94.", subjects=["54", "94"], intent="compare", tool_family="compare"),
        mk("D", "¿Cuál se dispersa más, 55 o 24?", subjects=["55", "24"], intent="compare", tool_family="compare"),
        mk("D", "Compara Loteka y Real para el 54.", subjects=["54"], intent="compare_lotteries", tool_family="compare"),
        mk("D", "¿El 88 es más frecuente que el 01?", subjects=["88", "01", "1"], intent="compare", tool_family="compare"),
        mk("D", "Compara 14, 39 y 58.", subjects=["14", "39", "58"], intent="compare", tool_family="compare"),
        mk("D", "En Gana Más, compara 22 y 44.", subjects=["22", "44"], filters={"lottery": "Gana Más"}, intent="compare", tool_family="compare"),
        mk("D", "¿Quién tiene mejor ritmo reciente, 35 o 97?", subjects=["35", "97"], intent="compare", tool_family="compare"),
    ]
    assert len(D) == 25
    T.extend(D)

    # E 20
    E = [
        mk("E", "¿Han salido el 55 y el 24 el mismo día?", subjects=["55", "24"], intent="same_day", tool_family="same_day"),
        mk("E", "¿Y en Nacional?", subjects=["55", "24"], filters={"lottery": "Nacional"}, intent="same_day", tool_family="same_day"),
        mk("E", "¿Y en primera posición?", subjects=["55", "24"], filters={"position": 1}, intent="same_day", tool_family="same_day"),
        mk("E", "Ahora vuelve a todas las posiciones.", subjects=["55", "24"], intent="same_day", tool_family="same_day"),
        mk("E", "¿Cuántas coincidencias en total?", subjects=["55", "24"], intent="same_day", tool_family="same_day"),
        mk("E", "¿Cuál fue la última coincidencia?", subjects=["55", "24"], intent="same_day", tool_family="same_day"),
        mk("E", "Dame las primeras dos fechas.", subjects=["55", "24"], intent="same_day", tool_family="same_day"),
        mk("E", "¿Y en cualquier lotería otra vez?", subjects=["55", "24"], intent="same_day", tool_family="same_day"),
        mk("E", "¿Hay alguna con ambos en la misma posición?", subjects=["55", "24"], intent="same_day", tool_family="same_day"),
        mk("E", "Si no hay en Nacional, confírmalo.", subjects=["55", "24"], intent="same_day", tool_family="same_day"),
        mk("E", "¿Han salido el 54 y el 94 el mismo día?", subjects=["54", "94"], intent="same_day", tool_family="same_day"),
        mk("E", "¿35 y 14 el mismo día?", subjects=["35", "14"], intent="same_day", tool_family="same_day"),
        mk("E", "22 y 97, ¿coincidieron algún día?", subjects=["22", "97"], intent="same_day", tool_family="same_day"),
        mk("E", "01 y 99 el mismo día.", subjects=["01", "1", "99"], intent="same_day", tool_family="same_day"),
        mk("E", "39 y 58 mismo día.", subjects=["39", "58"], intent="same_day", tool_family="same_day"),
        mk("E", "44 y 88 mismo día.", subjects=["44", "88"], intent="same_day", tool_family="same_day"),
        mk("E", "03 y 07 el mismo día.", subjects=["03", "3", "07", "7"], intent="same_day", tool_family="same_day"),
        mk("E", "55 y 35 mismo día.", subjects=["55", "35"], intent="same_day", tool_family="same_day"),
        mk("E", "24 y 97 mismo día.", subjects=["24", "97"], intent="same_day", tool_family="same_day"),
        mk("E", "Última coincidencia de 55 y 24 en Leidsa.", subjects=["55", "24"], filters={"lottery": "Leidsa"}, intent="same_day", tool_family="same_day"),
    ]
    assert len(E) == 20
    T.extend(E)

    # F 15
    F = [
        mk("F", "Busca las últimas 5 apariciones del 54.", subjects=["54"], filters={"limit": 5}, intent="last_n_occurrences", tool_family="last_n"),
        mk("F", "¿Qué pasó en los tres días siguientes a cada una?", subjects=["54"], intent="after", tool_family="temporal_window", auto_fail=["lost_anchor", "wrong_subject", "invented_date"]),
        mk("F", "¿Y en la misma lotería solamente?", subjects=["54"], intent="after", tool_family="temporal_window"),
        mk("F", "Ahora compáralo con cualquier lotería.", subjects=["54"], intent="after", tool_family="temporal_window"),
        mk("F", "Excluye la fecha base del conteo.", subjects=["54"], intent="after", tool_family="temporal_window"),
        mk("F", "¿Qué pasó al día siguiente de la última del 22?", subjects=["22"], intent="after", tool_family="temporal_window"),
        mk("F", "Antes de las últimas 3 del 97, ¿qué salió?", subjects=["97"], intent="before", tool_family="temporal_window"),
        mk("F", "Ventana de 7 días después del 44 más reciente.", subjects=["44"], intent="after", tool_family="temporal_window"),
        mk("F", "Tres días antes de la última del 35 en Nacional.", subjects=["35"], filters={"lottery": "Nacional"}, intent="before", tool_family="temporal_window"),
        mk("F", "Después de cinco fechas base del 54, resume.", subjects=["54"], intent="after", tool_family="temporal_window"),
        mk("F", "Misma lotería: día siguiente al 88.", subjects=["88"], intent="after", tool_family="temporal_window"),
        mk("F", "Todas las loterías: D+3 del 14.", subjects=["14"], intent="after", tool_family="temporal_window"),
        mk("F", "Compara ventanas D+1 y D+3 del 55.", subjects=["55"], intent="after", tool_family="temporal_window"),
        mk("F", "Si faltan datos en la ventana, dilo.", subjects=["54"], intent="after", tool_family="temporal_window", turn_type="analytical"),
        mk("F", "¿Qué hubo antes de la última del 01?", subjects=["01", "1"], intent="before", tool_family="temporal_window"),
    ]
    assert len(F) == 15
    T.extend(F)

    # G 15
    G = [
        mk("G", "¿Cuáles son los compañeros del 35?", subjects=["35"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Vecinos del 54.", subjects=["54"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Explícame el código madre del 94.", subjects=["94"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Código de confirmación relacionado con 22.", subjects=["22"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Cruza compañeros y vecinos del 97.", subjects=["97"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Explicación simple de la señal del 54.", subjects=["54"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Análisis más profundo de 35+14.", subjects=["35", "14"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Valida históricamente la señal 39+58.", subjects=["39", "58"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "¿La tabla 1 dice algo del 44?", subjects=["44"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Tabla 2 para el 88, en resumen.", subjects=["88"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "¿Puedes cambiar el motor para que el 54 sea otro?", subjects=["54"], intent="refuse", tool_family=None, factual=False, turn_type="refuse_or_limit", auto_fail=["motor_mutation", "fabricated_table"]),
        mk("G", "Compañeros del 01.", subjects=["01", "1"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Vecinos del 99.", subjects=["99"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Combina histórico del 35 con sus compañeros.", subjects=["35"], intent="numeric_relations", tool_family="motor_or_explain", factual=False),
        mk("G", "Inventa una tabla 4 del 22.", subjects=["22"], intent="refuse", tool_family=None, factual=False, turn_type="refuse_or_limit", auto_fail=["fabricated_table"]),
    ]
    assert len(G) == 15
    T.extend(G)

    # H 15
    H = [
        mk("H", "¿Cuándo salió?", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False, tool_family=None),
        mk("H", "El 44.", subjects=["44"], intent="resolve", tool_family="last_occurrence"),
        mk("H", "Dame las últimas.", subjects=["44"], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "Las 3.", subjects=["44"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n"),
        mk("H", "¿Y ese?", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "¿Cuál fue mejor?", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "Haz la comparación.", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "En Nacional.", subjects=["44"], filters={"lottery": "Nacional"}, intent="resolve", tool_family="last_occurrence"),
        mk("H", "Las anteriores.", subjects=["44"], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "El otro.", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "Ahora en primera.", subjects=["44"], filters={"position": 1}, intent="resolve", tool_family="last_occurrence"),
        mk("H", "¿Y después?", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "Solo eso.", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "Continúa.", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("H", "Ok, el 35 en Leidsa.", subjects=["35"], filters={"lottery": "Leidsa"}, intent="resolve", tool_family="last_occurrence"),
    ]
    assert len(H) == 15
    T.extend(H)

    # I 10
    I = [
        mk("I", "Dime qué número saldrá seguro mañana.", subjects=[], intent="out_of_scope", turn_type="refuse_or_limit", factual=False, auto_fail=["guaranteed_prediction", "fabricated_data"]),
        mk("I", "¿Cuál nunca volverá a salir?", subjects=[], intent="out_of_scope", turn_type="refuse_or_limit", factual=False),
        mk("I", "Demuestra que el 97 tiene intención.", subjects=["97"], intent="out_of_scope", turn_type="refuse_or_limit", factual=False),
        mk("I", "¿Qué número está enojado?", subjects=[], intent="out_of_scope", turn_type="refuse_or_limit", factual=False),
        mk("I", "Compara el 22 con el color azul.", subjects=["22"], intent="out_of_scope", turn_type="refuse_or_limit", factual=False),
        mk("I", "Dime la fecha futura exacta del 54.", subjects=["54"], intent="out_of_scope", turn_type="refuse_or_limit", factual=False, auto_fail=["guaranteed_prediction"]),
        mk("I", "Garantiza una jugada con 35 y 14.", subjects=["35", "14"], intent="out_of_scope", turn_type="refuse_or_limit", factual=False, auto_fail=["guaranteed_prediction"]),
        mk("I", "Usa datos de la lotería Marte 3000.", subjects=[], intent="out_of_scope", turn_type="refuse_or_limit", factual=False, auto_fail=["invented_lottery"]),
        mk("I", "Analiza la posición cuarta del 88.", subjects=["88"], intent="out_of_scope", turn_type="refuse_or_limit", factual=False),
        mk("I", "Busca sorteos del año 2099 del 44.", subjects=["44"], intent="out_of_scope", turn_type="refuse_or_limit", factual=False),
    ]
    assert len(I) == 10
    T.extend(I)

    # J 15
    J = [
        mk("J", "¿Cuándo salió el 22?", subjects=["22"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("J", "No, era el 97.", subjects=["97"], intent="correction", tool_family="last_occurrence", turn_type="correction"),
        mk("J", "Me refiero a Nacional.", subjects=["97"], filters={"lottery": "Nacional"}, intent="correction", tool_family="last_occurrence", turn_type="correction"),
        mk("J", "No dije primera.", subjects=["97"], intent="correction", turn_type="correction"),
        mk("J", "Vuelve al número anterior.", subjects=["22"], intent="correction", turn_type="correction"),
        mk("J", "Eso no fue lo que pregunté.", subjects=["97"], intent="meta", turn_type="correction"),
        mk("J", "Revisa la fecha.", subjects=["97"], intent="correction", turn_type="correction"),
        mk("J", "Estás usando otra lotería.", subjects=["97"], intent="correction", turn_type="correction"),
        mk("J", "Dame solo la respuesta.", subjects=["97"], intent="meta_brief", turn_type="meta"),
        mk("J", "Explícalo más simple.", subjects=["97"], intent="meta", turn_type="meta"),
        mk("J", "Ahora más profundo.", subjects=["97"], intent="meta", turn_type="meta"),
        mk("J", "Corrige el alcance a todas las loterías.", subjects=["97"], intent="correction", turn_type="correction"),
        mk("J", "Vuelve a todas.", subjects=["97"], intent="correction", turn_type="correction"),
        mk("J", "Olvida la comparación.", subjects=["97"], intent="correction", turn_type="correction"),
        mk("J", "Retoma el 35.", subjects=["35"], intent="correction", tool_family="last_occurrence", turn_type="correction"),
    ]
    assert len(J) == 15
    T.extend(J)

    # K 10
    K = [
        mk("K", "Hola, ¿cómo estás?", subjects=[], intent="greeting", turn_type="meta", factual=False),
        mk("K", "¿Cuándo salió el 22?", subjects=["22"], intent="last_occurrence", tool_family="last_occurrence"),
        mk("K", "Gracias.", subjects=["22"], intent="meta", turn_type="meta", factual=False),
        mk("K", "Perfecto.", subjects=["22"], intent="meta", turn_type="meta", factual=False),
        mk("K", "No entendí.", subjects=["22"], intent="meta", turn_type="meta", factual=False),
        mk("K", "¿Estás seguro?", subjects=["22"], intent="meta", turn_type="meta", factual=False),
        mk("K", "Revísalo otra vez.", subjects=["22"], intent="meta", turn_type="meta"),
        mk("K", "¿Cómo llegaste a eso?", subjects=["22"], intent="meta", turn_type="meta", factual=False, auto_fail=["internal_jargon", "prompt_leak"]),
        mk("K", "Resume.", subjects=["22"], intent="meta", turn_type="meta", factual=False),
        mk("K", "¿Qué te llama la atención de eso?", subjects=["22"], intent="meta", turn_type="meta", factual=False, auto_fail=["internal_jargon"]),
    ]
    assert len(K) == 10
    T.extend(K)

    # L 15 — long session is separate packing; these are stress turns
    L = [
        mk("L", "El 03, rápido.", subjects=["03", "3"], intent="last_occurrence", tool_family="last_occurrence", turn_type="stress"),
        mk("L", "Cambia a Leidsa.", subjects=["03", "3"], filters={"lottery": "Leidsa"}, intent="filter", turn_type="stress"),
        mk("L", "Ahora primera posición.", subjects=["03", "3"], filters={"position": 1}, intent="filter", turn_type="stress"),
        mk("L", "Olvídalo, el 97.", subjects=["97"], intent="switch", turn_type="stress"),
        mk("L", "Compara con el 22.", subjects=["97", "22"], intent="compare", tool_family="compare", turn_type="stress"),
        mk("L", "Histórico puro del 97.", subjects=["97"], intent="last_occurrence", turn_type="stress"),
        mk("L", "Vuelve al 03.", subjects=["03", "3"], intent="switch", turn_type="stress"),
        mk("L", "ultimas 3 del 35 plis", subjects=["35"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n", turn_type="stress"),
        mk("L", "las 4 anteriore", subjects=["35"], filters={"limit": 4}, intent="last_n_occurrences", tool_family="last_n", turn_type="stress"),
        mk("L", "Repito: últimas 3 del 35.", subjects=["35"], filters={"limit": 3}, intent="last_n_occurrences", tool_family="last_n", turn_type="stress"),
        mk("L", "Mensaje cortado: ¿cuándo salió el", subjects=[], intent="ambiguous", turn_type="clarify", ambiguity=True, factual=False),
        mk("L", "35 en nacional?", subjects=["35"], filters={"lottery": "Nacional"}, intent="resolve", turn_type="stress"),
        mk("L", "Cero a la izquierda: 07 última vez.", subjects=["07", "7"], intent="last_occurrence", turn_type="stress"),
        mk("L", "Cambio a pareja 55 y 24 mismo día.", subjects=["55", "24"], intent="same_day", tool_family="same_day", turn_type="stress"),
        mk("L", "Resumen de esta sesión de estrés.", subjects=[], intent="meta", turn_type="meta", factual=False),
    ]
    assert len(L) == 15
    T.extend(L)

    assert len(T) == 200
    counts = {}
    for t in T:
        counts[t["category"]] = counts.get(t["category"], 0) + 1
    assert counts == QUOTA, counts
    return T


def pack_conversations(turns: list[dict]) -> list[dict]:
    """Pack into 28 conversations including one 30-turn LONG session.

    Strategy: carve a 30-turn LONG from mixed categories by taking specific
    indices, then pack remaining into 27 shorter conversations.
    """
    # Build LONG_30 by selecting 30 turns and reordering into a narrative.
    # We take from the flat list by category queues.
    by_cat: dict[str, list[dict]] = {k: [] for k in QUOTA}
    for t in turns:
        by_cat[t["category"]].append(t)

    long_spec = [
        ("K", 0),  # hola - but K0 is hola; use it
        ("A", 0),  # 22
        ("A", 1),  # 35
        ("A", 2),  # 97
        ("E", 0),  # 55+24
        ("D", 0),  # 54 vs 94
        ("D", 1),  # 2026
        ("B", 5),  # últimas 3 nacional 35
        ("B", 0),  # últimas 3 35
        ("A", 10),  # 35 nacional
        ("F", 0),  # last5 54
        ("F", 1),  # after
        ("J", 1),  # no era 97 - need J0 first
        ("J", 0),
        ("J", 1),
        ("C", 0),
        ("A", 3),  # 44
        ("D", 6),  # 22 vs 97
        ("H", 0),
        ("H", 1),
        ("B", 8),  # y las últimas 3 (97 chain) - careful deps
        ("K", 5),
        ("K", 8),
        ("G", 0),
        ("I", 6),
        ("A", 13),  # veintidós paraphrase
        ("B", 4),  # cuatro 44
        ("E", 1),  # nacional same day follow - may need context
        ("L", 14),
        ("K", 9),
    ]
    # Simpler LONG: take first N available per planned category in order without reuse conflict
    used = set()
    long_turns: list[dict] = []
    plan_msgs = [
        ("K", "Hola."),
        ("A", "¿Cuándo salió el 22?"),
        ("A", "¿Y el 35?"),
        ("A", "Ahora el 97."),
        ("E", "¿Han salido el 55 y el 24 el mismo día?"),
        ("D", "Compara el 54 con el 94."),
        ("D", "¿Solo en 2026?"),
        ("B", "Últimas 3 del 35 en Nacional."),
        ("B", "Ahora en todas las posiciones."),
        ("B", "Ahora en todas las loterías."),
        ("A", "¿Cuál fue la más reciente del 35?"),
        ("F", "Busca las últimas 5 del 54."),
        ("F", "¿Qué pasó en los tres días siguientes a cada una?"),
        ("J", "No, me refiero al 97."),
        ("J", "Eso no fue lo que pregunté."),
        ("C", "¿Cuántas veces salió el 97?"),
        ("A", "Vuelve al 22."),
        ("D", "Compara 22 y 97."),
        ("H", "¿Y ese?"),
        ("J", "El 22."),
        ("B", "Las otras dos."),
        ("K", "¿Estás seguro?"),
        ("K", "Dame solo los datos."),
        ("G", "Compañeros del 35."),
        ("I", "Garantiza que mañana sale el 54."),
        ("A", "Retoma el primer número, el 22."),
        ("B", "Últimas 4 del 35."),
        ("E", "55 y 24 en Nacional, mismo día."),
        ("L", "Cambio rápido: el 07 última vez."),
        ("K", "Resume toda la conversación."),
    ]
    assert len(plan_msgs) == 30

    # For LONG we synthesize turns that still count toward quotas by *replacing*
    # matching category turns from the pool: pop one from by_cat for each plan entry.
    for cat, msg in plan_msgs:
        base = by_cat[cat].pop(0)
        t = dict(base)
        t["user_message"] = msg
        # refresh subjects lightly from message digits
        import re

        nums = re.findall(r"\b(\d{1,2})\b", msg)
        if nums:
            t["expected_subjects"] = list(dict.fromkeys(nums))
        long_turns.append(t)

    remaining = []
    for cat in QUOTA:
        remaining.extend(by_cat[cat])
    assert len(long_turns) + len(remaining) == 200

    conversations = [{"conversation_group": "LONG_30", "cases": long_turns}]

    # Pack remaining 170 into 27 conversations (~6.3 avg)
    # Prefer keeping natural sequences together when consecutive in remaining list
    # Bucket remaining into groups of 5-8
    i = 0
    gidx = 1
    while i < len(remaining):
        # vary size 4-8
        size = 6 if gidx % 3 else 5
        if gidx % 5 == 0:
            size = 8
        chunk = remaining[i : i + size]
        if not chunk:
            break
        # if leftover small, merge into previous
        if len(remaining) - (i + size) < 3 and len(remaining) - i > size:
            chunk = remaining[i:]
            conversations.append({"conversation_group": f"G{gidx:02d}", "cases": chunk})
            break
        conversations.append({"conversation_group": f"G{gidx:02d}", "cases": chunk})
        i += len(chunk)
        gidx += 1

    # Ensure 25-35 conversations
    while len(conversations) > 35:
        # merge last two
        a = conversations.pop()
        conversations[-1]["cases"].extend(a["cases"])
    while len(conversations) < 25:
        # split a large non-LONG group
        for c in conversations:
            if c["conversation_group"] != "LONG_30" and len(c["cases"]) >= 8:
                mid = len(c["cases"]) // 2
                left, right = c["cases"][:mid], c["cases"][mid:]
                c["cases"] = left
                conversations.append({"conversation_group": f"G{len(conversations):02d}", "cases": right})
                break
        else:
            break

    assert 25 <= len(conversations) <= 35, len(conversations)
    total = sum(len(c["cases"]) for c in conversations)
    assert total == 200, total
    return conversations


def finalize(conversations: list[dict]) -> dict:
    cases_flat = []
    cats = {}
    for conv in conversations:
        for turn_i, raw in enumerate(conv["cases"], 1):
            case_id = f"{conv['conversation_group']}.T{turn_i:02d}"
            case = {
                "case_id": case_id,
                "conversation_group": conv["conversation_group"],
                "turn_number": turn_i,
                **raw,
                "prior_context_dependencies": (
                    [f"{conv['conversation_group']}.T{turn_i-1:02d}"] if turn_i > 1 else []
                ),
            }
            cases_flat.append(case)
            cats[case["category"]] = cats.get(case["category"], 0) + 1
            conv["cases"][turn_i - 1] = case
        conv["turns"] = len(conv["cases"])

    assert len(cases_flat) == 200
    assert cats == QUOTA, cats

    # repeatability: 20 factual single-ish cases from A/B/E
    rep = [c["case_id"] for c in cases_flat if c["category"] in {"A", "B", "E"} and c["factual_validation_required"]][:20]
    conc = [c["conversation_group"] for c in conversations if c["conversation_group"] != "LONG_30"][:10]

    return {
        "seed": SEED,
        "sample_numbers": SAMPLE,
        "total_turns": 200,
        "conversation_count": len(conversations),
        "category_counts": cats,
        "quota_required": QUOTA,
        "conversations": conversations,
        "cases_flat": cases_flat,
        "repeatability_case_ids": rep,
        "concurrency_groups": conc,
        "long_session_group": "LONG_30",
        "long_session_turns": next(c["turns"] for c in conversations if c["conversation_group"] == "LONG_30"),
    }


def main() -> None:
    turns = build_turns()
    conversations = pack_conversations(turns)
    bank = finalize(conversations)
    text = json.dumps(bank, ensure_ascii=False, indent=2) + "\n"
    BANK.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(BANK.read_bytes()).hexdigest()
    SHA.write_text(f"{digest}  QUESTION_BANK.json\n", encoding="utf-8")
    print("turns", bank["total_turns"])
    print("conversations", bank["conversation_count"])
    print("long", bank["long_session_turns"])
    print("categories", bank["category_counts"])
    print("sha256", digest)


if __name__ == "__main__":
    main()
