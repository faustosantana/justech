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
    GET_DATA_QUALITY = "lottery_get_data_quality"
    GET_ANOMALIES = "lottery_get_anomalies"
    GET_SOURCE_HEALTH = "lottery_get_source_health"
    GET_SYNC_WINDOWS = "lottery_get_sync_windows"
    GET_HOT_COLD = "lottery_get_hot_cold"
    GET_COINCIDENCES = "lottery_get_coincidences"
    GET_MISSING_TODAY = "lottery_get_missing_today"
    # Lottery IA 4.1 analytical coverage
    COMPARE_NUMBER_PERIODS = "lottery_compare_number_periods"
    COMPARE_NUMBER_ACROSS_LOTTERIES = "lottery_compare_number_across_lotteries"
    GET_POSITION_DISTRIBUTION = "lottery_get_position_distribution"
    GET_OVERDUE_NUMBERS = "lottery_get_overdue_numbers"
    GET_MONTHLY_TREND = "lottery_get_monthly_trend"
    GET_YEARLY_COMPARISON = "lottery_get_yearly_comparison"
    GET_LOTTERY_SUMMARY = "lottery_get_lottery_summary"
    GET_DATA_COMPLETENESS = "lottery_get_data_completeness"
    GET_EXPECTED_VS_RECEIVED = "lottery_get_expected_vs_received"
    GET_LATEST_AVAILABLE_DATE = "lottery_get_latest_available_date"
    EXPLAIN_ANALYSIS_METHOD = "lottery_explain_analysis_method"
    ANALYZE_NUMERIC_RELATIONS = "lottery_analyze_numeric_relations"
    HISTORICAL_RELATION_CONDITIONS = "lottery_historical_relation_conditions"
    CANDIDATE_RESPONSE_SUMMARY = "lottery_candidate_response_summary"
    CONFIRMER_COMBINATIONS = "lottery_confirmer_combinations"
    RELATION_PATTERN_DETAIL = "lottery_relation_pattern_detail"
    COMPARE_HISTORICAL_PATTERNS = "lottery_compare_historical_patterns"


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
    LotteryToolName.GET_DATA_QUALITY: ("lottery.statistics", "lottery.admin"),
    LotteryToolName.GET_ANOMALIES: ("lottery.statistics", "lottery.admin"),
    LotteryToolName.GET_SOURCE_HEALTH: ("lottery.access", "lottery.admin"),
    LotteryToolName.GET_SYNC_WINDOWS: ("lottery.access", "lottery.admin"),
    LotteryToolName.GET_HOT_COLD: ("lottery.statistics",),
    LotteryToolName.GET_COINCIDENCES: ("lottery.compare", "lottery.statistics"),
    LotteryToolName.GET_MISSING_TODAY: ("lottery.access", "lottery.search"),
    LotteryToolName.COMPARE_NUMBER_PERIODS: ("lottery.statistics",),
    LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES: ("lottery.compare", "lottery.statistics"),
    LotteryToolName.GET_POSITION_DISTRIBUTION: ("lottery.statistics",),
    LotteryToolName.GET_OVERDUE_NUMBERS: ("lottery.statistics",),
    LotteryToolName.GET_MONTHLY_TREND: ("lottery.statistics",),
    LotteryToolName.GET_YEARLY_COMPARISON: ("lottery.statistics",),
    LotteryToolName.GET_LOTTERY_SUMMARY: ("lottery.access", "lottery.search"),
    LotteryToolName.GET_DATA_COMPLETENESS: ("lottery.statistics", "lottery.access"),
    LotteryToolName.GET_EXPECTED_VS_RECEIVED: ("lottery.access", "lottery.search"),
    LotteryToolName.GET_LATEST_AVAILABLE_DATE: ("lottery.access", "lottery.search"),
    LotteryToolName.EXPLAIN_ANALYSIS_METHOD: ("lottery.access", "lottery.statistics"),
    LotteryToolName.ANALYZE_NUMERIC_RELATIONS: ("lottery.statistics", "lottery.search"),
    LotteryToolName.HISTORICAL_RELATION_CONDITIONS: ("lottery.statistics", "lottery.search"),
    LotteryToolName.CANDIDATE_RESPONSE_SUMMARY: ("lottery.statistics", "lottery.search"),
    LotteryToolName.CONFIRMER_COMBINATIONS: ("lottery.statistics", "lottery.search"),
    LotteryToolName.RELATION_PATTERN_DETAIL: ("lottery.statistics", "lottery.search"),
    LotteryToolName.COMPARE_HISTORICAL_PATTERNS: ("lottery.statistics", "lottery.search"),
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
    LotteryToolContract(
        name=LotteryToolName.GET_DATA_QUALITY,
        description="Calidad de datos y drift de metadata de una lotería.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_DATA_QUALITY],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_ANOMALIES,
        description="Anomalías detectadas (fechas futuras, duplicados, faltantes).",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_ANOMALIES],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_SOURCE_HEALTH,
        description="Salud de fuentes multi-source y circuit breakers.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_SOURCE_HEALTH],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_SYNC_WINDOWS,
        description="Ventanas inteligentes de sincronización y próxima consulta.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_SYNC_WINDOWS],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_HOT_COLD,
        description="Números calientes/fríos descriptivos (sin predicción).",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_HOT_COLD],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_COINCIDENCES,
        description="Coincidencias de números entre loterías en las mismas fechas.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_COINCIDENCES],
    ),
    LotteryToolContract(
        name=LotteryToolName.GET_MISSING_TODAY,
        description="Loterías sincronizadas que aún no tienen resultado de hoy (TZ local).",
        permissions=TOOL_PERMISSIONS[LotteryToolName.GET_MISSING_TODAY],
    ),
    LotteryToolContract(
        name=LotteryToolName.ANALYZE_NUMERIC_RELATIONS,
        description=(
            "Motor de Relaciones Numéricas: compañeros Tabla 1, vecinos Tabla 2 y "
            "ranking histórico anclado a ocurrencias reales del número observado N. "
            "No predice ni recomienda apuestas."
        ),
        permissions=TOOL_PERMISSIONS[LotteryToolName.ANALYZE_NUMERIC_RELATIONS],
    ),
    LotteryToolContract(
        name=LotteryToolName.HISTORICAL_RELATION_CONDITIONS,
        description=(
            "Busca condiciones históricas N→candidato T1→confirmador T2 con draw_id, "
            "tasas y ciclos. No inventa estadísticas."
        ),
        permissions=TOOL_PERMISSIONS[LotteryToolName.HISTORICAL_RELATION_CONDITIONS],
    ),
    LotteryToolContract(
        name=LotteryToolName.CANDIDATE_RESPONSE_SUMMARY,
        description=(
            "Resumen de respuesta posterior del candidato (horizontes 1/2/3/5/10), "
            "censura y ciclos. No es probabilidad de ganar."
        ),
        permissions=TOOL_PERMISSIONS[LotteryToolName.CANDIDATE_RESPONSE_SUMMARY],
    ),
    LotteryToolContract(
        name=LotteryToolName.CONFIRMER_COMBINATIONS,
        description=(
            "Combinaciones de confirmadores Tabla 2 (pares/tríos/conjunto) y soporte histórico."
        ),
        permissions=TOOL_PERMISSIONS[LotteryToolName.CONFIRMER_COMBINATIONS],
    ),
    LotteryToolContract(
        name=LotteryToolName.RELATION_PATTERN_DETAIL,
        description="Detalle de patrón atómico o combinación con evidencia calculada.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.RELATION_PATTERN_DETAIL],
    ),
    LotteryToolContract(
        name=LotteryToolName.COMPARE_HISTORICAL_PATTERNS,
        description="Compara patrones/candidatos/loterías usando agregados históricos calculados.",
        permissions=TOOL_PERMISSIONS[LotteryToolName.COMPARE_HISTORICAL_PATTERNS],
    ),
]


# Lottery IA 4.0 — canonical prompt lives in the versioned registry.
from app.lottery.ai.prompts.lottery_assistant_system_v1 import (  # noqa: E402
    get_system_prompt_text as _get_lottery_system_prompt,
)

LOTTERY_SYSTEM_PROMPT = _get_lottery_system_prompt()

# Back-compat alias
LOTTERY_SYSTEM_PROMPT_SKELETON = LOTTERY_SYSTEM_PROMPT


class LotteryToolInvocationBlocked(BaseModel):
    """Reservado: tools no implementadas o denegadas."""

    allowed: bool = False
    reason: str = Field(default="Tool de lotería no autorizada o no implementada")
    details: dict[str, Any] = Field(default_factory=dict)
