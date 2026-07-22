"""Contratos tipados Lotería IA — tools, permisos y system prompt (Fase 4)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LotteryToolName(str, Enum):
    LIST_LOTTERIES = "lottery_list_lotteries"
    RESOLVE_LOTTERY = "lottery_resolve_lottery"
    GET_RESULT_BY_DATE = "lottery_get_result_by_date"
    GET_FOLLOWING_DAYS = "lottery_get_following_days"
    GET_FOLLOWING_DRAWS = "lottery_get_following_draws"
    GET_PREVIOUS_DAYS = "lottery_get_previous_days"
    GET_PREVIOUS_DRAWS = "lottery_get_previous_draws"
    GET_RESULTS_RANGE = "lottery_get_results_range"
    GET_NUMBER_OCCURRENCES = "lottery_get_number_occurrences"
    COMPARE_LOTTERIES = "lottery_compare_lotteries"
    CALCULATE_FREQUENCIES = "lottery_calculate_frequencies"
    FIND_REPETITIONS = "lottery_find_repetitions"
    FIND_NEXT_OCCURRENCES = "lottery_find_next_occurrences"
    CROSS_LOTTERY_ANALYSIS = "lottery_cross_lottery_analysis"
    GET_COVERAGE = "lottery_get_coverage"
    SAVE_QUERY = "lottery_save_query"
    GET_SAVED_QUERIES = "lottery_get_saved_queries"
    GET_LATEST_RESULTS = "lottery_get_latest_results"
    GET_DRAW_COUNT = "lottery_get_draw_count"
    GET_TOP_NUMBERS = "lottery_get_top_numbers"
    GET_BOTTOM_NUMBERS = "lottery_get_bottom_numbers"
    GET_LAST_OCCURRENCE = "lottery_get_last_occurrence"
    GET_INTERVAL_STATISTICS = "lottery_get_interval_statistics"
    GET_SYNC_STATUS = "lottery_get_sync_status"


# Permisos mínimos por tool (cualquiera de la tupla basta)
TOOL_PERMISSIONS: dict[LotteryToolName, tuple[str, ...]] = {
    LotteryToolName.LIST_LOTTERIES: ("lottery.access", "lottery.search"),
    LotteryToolName.RESOLVE_LOTTERY: ("lottery.search",),
    LotteryToolName.GET_RESULT_BY_DATE: ("lottery.search",),
    LotteryToolName.GET_FOLLOWING_DAYS: ("lottery.search",),
    LotteryToolName.GET_FOLLOWING_DRAWS: ("lottery.search",),
    LotteryToolName.GET_PREVIOUS_DAYS: ("lottery.search",),
    LotteryToolName.GET_PREVIOUS_DRAWS: ("lottery.search",),
    LotteryToolName.GET_RESULTS_RANGE: ("lottery.search",),
    LotteryToolName.GET_NUMBER_OCCURRENCES: ("lottery.search",),
    LotteryToolName.CALCULATE_FREQUENCIES: ("lottery.statistics",),
    LotteryToolName.FIND_REPETITIONS: ("lottery.statistics",),
    LotteryToolName.FIND_NEXT_OCCURRENCES: ("lottery.statistics",),
    LotteryToolName.COMPARE_LOTTERIES: ("lottery.compare",),
    LotteryToolName.CROSS_LOTTERY_ANALYSIS: ("lottery.compare", "lottery.statistics"),
    LotteryToolName.GET_COVERAGE: ("lottery.access", "lottery.search"),
    LotteryToolName.SAVE_QUERY: ("lottery.saved_queries",),
    LotteryToolName.GET_SAVED_QUERIES: ("lottery.saved_queries",),
    LotteryToolName.GET_LATEST_RESULTS: ("lottery.search",),
    LotteryToolName.GET_DRAW_COUNT: ("lottery.access", "lottery.search"),
    LotteryToolName.GET_TOP_NUMBERS: ("lottery.statistics",),
    LotteryToolName.GET_BOTTOM_NUMBERS: ("lottery.statistics",),
    LotteryToolName.GET_LAST_OCCURRENCE: ("lottery.statistics", "lottery.search"),
    LotteryToolName.GET_INTERVAL_STATISTICS: ("lottery.statistics",),
    LotteryToolName.GET_SYNC_STATUS: ("lottery.access",),
}


class LotteryToolContract(BaseModel):
    name: LotteryToolName
    description: str
    permissions: tuple[str, ...]
    implemented: bool = True


LOTTERY_TOOL_CATALOG: list[LotteryToolContract] = [
    LotteryToolContract(
        name=LotteryToolName.LIST_LOTTERIES,
        description="Lista loterías del catálogo histórico.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.LIST_LOTTERIES],
    ),
    LotteryToolContract(
        name=LotteryToolName.RESOLVE_LOTTERY,
        description="Resuelve alias/nombre a lotería canónica o ambigüedad.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.RESOLVE_LOTTERY],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_RESULT_BY_DATE,
        description="Resultados de una lotería en una fecha exacta.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_RESULT_BY_DATE],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_FOLLOWING_DAYS,
        description="Días calendario siguientes a una fecha base.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_FOLLOWING_DAYS],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_FOLLOWING_DRAWS,
        description="Próximos N sorteos existentes (no días calendario).",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_FOLLOWING_DRAWS],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_PREVIOUS_DAYS,
        description="Días calendario anteriores a una fecha base.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_PREVIOUS_DAYS],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_PREVIOUS_DRAWS,
        description="Anteriores N sorteos existentes.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_PREVIOUS_DRAWS],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_RESULTS_RANGE,
        description="Resultados en un rango de fechas paginado.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_RESULTS_RANGE],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_NUMBER_OCCURRENCES,
        description="Apariciones de un número (preserva ceros iniciales).",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_NUMBER_OCCURRENCES],
    ),
    LotteryToolContract(
        name=LotteryToolName.CALCULATE_FREQUENCIES,
        description="Frecuencias históricas informativas (no predicción).",
        permissions=TOOL_PERMISSIONS[LotteryToolName.CALCULATE_FREQUENCIES],
    ),
    LotteryToolContract(
        name=LotteryToolName.FIND_REPETITIONS,
        description="Números repetidos en un rango.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.FIND_REPETITIONS],
    ),
    LotteryToolContract(
        name=LotteryToolName.FIND_NEXT_OCCURRENCES,
        description="Próxima aparición histórica de un número tras una fecha.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.FIND_NEXT_OCCURRENCES],
    ),
    LotteryToolContract(
        name=LotteryToolName.COMPARE_LOTTERIES,
        description="Compara loterías (same_date, repeated_numbers, etc.).",
        permissions=TOOL_PERMISSIONS[LotteryToolName.COMPARE_LOTTERIES],
    ),
    LotteryToolContract(
        name=LotteryToolName.CROSS_LOTTERY_ANALYSIS,
        description="Análisis cruzado same_day / within_range / after_occurrence.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.CROSS_LOTTERY_ANALYSIS],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_COVERAGE,
        description="Cobertura del histórico (conteos y rango de fechas).",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_COVERAGE],
    ),
    LotteryToolContract(
        name=LotteryToolName.SAVE_QUERY,
        description="Guarda la consulta actual del usuario.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.SAVE_QUERY],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_SAVED_QUERIES,
        description="Lista consultas guardadas del usuario en el tenant.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_SAVED_QUERIES],
    ),
]


LOTTERY_SYSTEM_PROMPT = """Eres Lotería IA 2.0, asistente analítico de consulta histórica dentro de JAIOS.

Pipeline interno (obligatorio):
1) Clasifica la intención (resultado, rango, frecuencia, comparación, cobertura, seguimiento).
2) Extrae entidades (lotería, fecha, número, días vs sorteos).
3) Resuelve lotería con tools (aliases). Si es ambiguo, pregunta.
4) Planifica 1..N tools tipadas. Ejecuta solo tools.
5) Valida consistencia (ceros iniciales, días calendario ≠ sorteos).
6) Compón respuesta con datos reales, tablas cuando ayuden, cobertura y limitaciones.
7) Indica confianza cualitativa solo si hay datos suficientes.

Reglas:
1. Responde únicamente con datos de tools. Nunca inventes.
2. Distingue días calendario vs sorteos existentes.
3. Conserva ceros iniciales (00, 01, 05).
4. Usa contexto de seguimiento (lotería/fecha previa) cuando el usuario diga «y los siguientes…».
5. «Nacional Día» permanece AMBIGUOUS (La Primera Tarde 20 vs La Suerte MD 21).
6. No SQL libre. No predicción. No consejos de apuestas.
7. Si no hay datos, dilo. Si excede límites, pide reducir.
8. Toda cifra debe citar lotería/rango/fuente de la tool.

Texto obligatorio al final de análisis estadísticos:
Los resultados históricos y las estadísticas son únicamente informativos. No garantizan resultados futuros ni constituyen recomendación de apuestas.
"""


# Back-compat alias
LOTTERY_SYSTEM_PROMPT_SKELETON = LOTTERY_SYSTEM_PROMPT


class LotteryToolInvocationBlocked(BaseModel):
    """Reservado: tools no implementadas o denegadas."""

    allowed: bool = False
    reason: str = Field(default="Tool de lotería no autorizada o no implementada")
    details: dict[str, Any] = Field(default_factory=dict)
