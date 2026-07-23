"""Human-facing labels and catalogs for Lottery AI Admin Center UI."""

from __future__ import annotations

from typing import Any

TOOL_LABELS_ES: dict[str, dict[str, str]] = {
    "lottery_resolve_lottery": {
        "label": "Resolver lotería",
        "description": "Identifica la lotería a partir de un nombre o alias comercial.",
        "examples": "«en la Real», «Leidsa», «Nacional»",
    },
    "lottery_get_result_by_date": {
        "label": "Resultado por fecha",
        "description": "Obtiene el resultado de una lotería en una fecha concreta.",
        "examples": "«¿Qué salió el 15 de junio en Leidsa?»",
    },
    "lottery_last_occurrence": {
        "label": "Última aparición",
        "description": "Fecha de la última vez que salió un número en una lotería.",
        "examples": "«¿Cuándo salió el 57 por última vez?»",
    },
    "lottery_number_occurrences": {
        "label": "Historial de un número",
        "description": "Lista apariciones de un número en un período.",
        "examples": "«Historial del 24 en Real este año»",
    },
    "lottery_calculate_frequencies": {
        "label": "Calcular frecuencias",
        "description": "Frecuencia absoluta y relativa de números en una muestra.",
        "examples": "«Frecuencia del 57 en Leidsa últimos 100 sorteos»",
    },
    "lottery_hot_numbers": {
        "label": "Números calientes",
        "description": "Ranking por alta frecuencia relativa en la muestra.",
        "examples": "«¿Cuáles están calientes en Loteka?»",
    },
    "lottery_cold_numbers": {
        "label": "Números fríos",
        "description": "Ranking por baja frecuencia relativa (no confundir con atrasados).",
        "examples": "«Números fríos en Real»",
    },
    "lottery_overdue_numbers": {
        "label": "Números atrasados",
        "description": "Números con más días sin aparecer (intervalo).",
        "examples": "«¿Cuál lleva más tiempo sin salir?»",
    },
    "lottery_compare_lotteries": {
        "label": "Comparar loterías",
        "description": "Compara métricas o apariciones entre varias loterías.",
        "examples": "«Compara el 57 en Real y Leidsa»",
    },
    "lottery_post_occurrence_window": {
        "label": "Ventana posterior",
        "description": "Números en días o sorteos posteriores a una aparición.",
        "examples": "«Siete días después en esas loterías»",
    },
    "lottery_coverage_summary": {
        "label": "Resumen de cobertura",
        "description": "Cobertura de datos, fechas disponibles y calidad.",
        "examples": "«¿Hasta qué fecha tienen Leidsa?»",
    },
    "lottery_sync_status": {
        "label": "Estado de sincronización",
        "description": "Estado funcional de sync (sin detalles de infraestructura).",
        "examples": "«¿Está actualizado hoy?»",
    },
}

PACK_META: dict[str, dict[str, Any]] = {
    "LAST_OCCURRENCE_PACK": {
        "display_name": "Última aparición",
        "intent": "last_occurrence",
        "description": "Última aparición de un número, comparación multilotería e intervalos.",
        "tools": ["lottery_last_occurrence", "lottery_compare_lotteries"],
    },
    "POST_OCCURRENCE_PACK": {
        "display_name": "Resultados posteriores",
        "intent": "post_occurrence_window",
        "description": "Ventana de días o sorteos posteriores a una aparición recordada.",
        "tools": ["lottery_post_occurrence_window", "lottery_last_occurrence"],
    },
    "FREQUENCY_PACK": {
        "display_name": "Frecuencia",
        "intent": "frequencies",
        "description": "Frecuencias absolutas/relativas y contraste por período.",
        "tools": ["lottery_calculate_frequencies"],
    },
    "RESULT_BY_DATE_PACK": {
        "display_name": "Resultado por fecha",
        "intent": "result_by_date",
        "description": "Resultado de una fecha y contexto cercano.",
        "tools": ["lottery_get_result_by_date"],
    },
    "HOT_COLD_PACK": {
        "display_name": "Calientes y fríos",
        "intent": "hot_cold",
        "description": "Calientes por frecuencia y fríos/atrasados con definición explícita.",
        "tools": ["lottery_hot_numbers", "lottery_cold_numbers", "lottery_overdue_numbers"],
    },
    "LOTTERY_SUMMARY_PACK": {
        "display_name": "Resumen",
        "intent": "lottery_summary",
        "description": "Resumen de cobertura, últimos resultados y calidad de datos.",
        "tools": ["lottery_coverage_summary", "lottery_sync_status"],
    },
    "CROSS_LOTTERY_PACK": {
        "display_name": "Comparación multilotería",
        "intent": "compare_numbers",
        "description": "Cruce y coincidencias entre varias loterías.",
        "tools": ["lottery_compare_lotteries"],
    },
    "DEEP_ANALYSIS_PACK": {
        "display_name": "Análisis profundo",
        "intent": "deep_analysis",
        "description": "Análisis multi-métrica con mayor profundidad e insights.",
        "tools": [
            "lottery_calculate_frequencies",
            "lottery_overdue_numbers",
            "lottery_compare_lotteries",
            "lottery_post_occurrence_window",
        ],
    },
}

# Preferred Justech default slots (commercial names to resolve against catalog)
JUSTECH_DEFAULT_LOTTERY_NAMES: list[str] = [
    "Quiniela Real",
    "Quiniela Leidsa",
    "Quiniela Loteka",
    "Lotería Nacional",
    "Gana Más",
    "Quiniela LoteDom",
]

JUSTECH_DEFAULT_ALIASES: dict[str, list[str]] = {
    "Quiniela Real": ["Real", "Quiniela Real", "La Real"],
    "Quiniela Leidsa": ["Leidsa", "Quiniela Leidsa"],
    "Quiniela Loteka": ["Loteka", "Quiniela Loteka"],
    "Lotería Nacional": ["Nacional", "Loteria Nacional", "Lotería Nacional"],
    "Gana Más": ["Gana Mas", "Gana Más", "Ganamas"],
    "Quiniela LoteDom": ["LoteDom", "Lotedom", "Quiniela LoteDom", "Lote Dom"],
}

SAFETY_CONTROLS: list[dict[str, Any]] = [
    {
        "key": "strict_domain",
        "label": "Dominio exclusivo de loterías",
        "state_when_true": "ACTIVO",
        "state_when_false": "INACTIVO",
        "impact": "Fuera de loterías se rechaza y se redirige al dominio.",
        "classification": "E",
        "locked": True,
    },
    {
        "key": "reject_out_of_domain",
        "label": "Respuestas fuera de dominio",
        "state_when_true": "BLOQUEADAS",
        "state_when_false": "PERMITIDAS",
        "impact": "Evita respuestas generalistas a capitales, clima, política, etc.",
        "classification": "E",
        "locked": True,
    },
    {
        "key": "block_prediction",
        "label": "Predicciones",
        "state_when_true": "BLOQUEADAS",
        "state_when_false": "PERMITIDAS",
        "impact": "No predice números futuros ni los presenta como certeza.",
        "classification": "E",
        "locked": True,
    },
    {
        "key": "block_betting_advice",
        "label": "Recomendaciones de apuestas",
        "state_when_true": "BLOQUEADAS",
        "state_when_false": "PERMITIDAS",
        "impact": "No sugiere qué jugar ni consejos de apuesta.",
        "classification": "E",
        "locked": True,
    },
    {
        "key": "protect_infrastructure",
        "label": "Infraestructura",
        "state_when_true": "PROTEGIDA",
        "state_when_false": "EXPUESTA",
        "impact": "Oculta BD, contenedores, IPs y stack.",
        "classification": "E",
        "locked": True,
    },
    {
        "key": "protect_sql",
        "label": "SQL",
        "state_when_true": "PROTEGIDO",
        "state_when_false": "EXPUESTO",
        "impact": "No genera ni revela SQL.",
        "classification": "E",
        "locked": True,
    },
    {
        "key": "protect_prompts",
        "label": "Prompt interno",
        "state_when_true": "PROTEGIDO",
        "state_when_false": "EXPUESTO",
        "impact": "No revela el system prompt a usuarios finales.",
        "classification": "E",
        "locked": True,
    },
    {
        "key": "protect_credentials",
        "label": "Credenciales",
        "state_when_true": "PROTEGIDAS",
        "state_when_false": "EXPUESTAS",
        "impact": "Nunca muestra API keys ni secretos.",
        "classification": "E",
        "locked": True,
    },
    {
        "key": "hide_technical_json",
        "label": "JSON técnico",
        "state_when_true": "OCULTO",
        "state_when_false": "VISIBLE",
        "impact": "El renderer no muestra dumps de tools al usuario.",
        "classification": "E",
        "locked": True,
        "default": True,
    },
    {
        "key": "hide_traces",
        "label": "Trazas para usuario",
        "state_when_true": "OCULTAS",
        "state_when_false": "VISIBLES",
        "impact": "Stack traces y errores internos no llegan al chat.",
        "classification": "E",
        "locked": True,
        "default": True,
    },
    {
        "key": "tenant_isolation",
        "label": "Aislamiento tenant",
        "state_when_true": "ACTIVO",
        "state_when_false": "INACTIVO",
        "impact": "Sesiones y memoria no cruzan tenants.",
        "classification": "E",
        "locked": True,
    },
]

PROMPT_BLOCKS = [
    "identidad",
    "dominio",
    "memoria",
    "aclaraciones",
    "analisis",
    "seguridad",
    "formato",
    "tono",
]


def tool_label(name: str) -> str:
    meta = TOOL_LABELS_ES.get(name)
    if meta:
        return meta["label"]
    # Fallback: humanize
    return name.replace("lottery_", "").replace("_", " ").strip().capitalize()


def empty_metric(label: str, reason: str = "Sin datos suficientes en la ventana actual") -> dict[str, Any]:
    return {"label": label, "value": None, "display": reason, "available": False}
