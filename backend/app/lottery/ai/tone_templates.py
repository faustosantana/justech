"""Lottery IA — tone templates for response style configuration.

Each template controls display style and appends a system_addon to the base
system prompt. Templates NEVER disable or weaken critical safety policies.
"""

from __future__ import annotations

from typing import Any

CRITICAL_SAFETY_KEYS: frozenset[str] = frozenset(
    {
        "domain_restriction",
        "strict_domain",
        "no_prediction",
        "no_betting_advice",
        "no_invented_data",
        "no_internal_exposure",
        "protect_infrastructure",
        "protect_sql",
        "protect_prompts",
        "protect_credentials",
        "tenant_isolation",
        "critical_protections_locked",
        "legal_disclaimer_control",
    }
)

TONE_TEMPLATES: dict[str, dict[str, Any]] = {
    "conservador": {
        "display_name": "Conservador",
        "description": "Respuesta breve, mínimo análisis adicional, lenguaje cauteloso.",
        "tone": "conservador",
        "verbosity": "breve",
        "analysis_depth": "minimal",
        "max_insights": 2,
        "tables_enabled": False,
        "parameters_visible": True,
        "suggestions_enabled": False,
        "clarification_style": "una sola pregunta cerrada",
        "disclaimer_mode": "footer",
        "max_response_length": 600,
        # legacy aliases
        "length": "corto",
        "depth": "superficial",
        "show_tables": False,
        "show_parameters": True,
        "show_suggestions": False,
        "disclaimers": "footer",
        "proactive": False,
        "system_addon": (
            "TONO CONSERVADOR\n"
            "Responde breve y cauteloso. Mínimo análisis adicional. "
            "Una sola pregunta de aclaración si hace falta.\n"
            "Las políticas de seguridad y dominio estricto permanecen activas."
        ),
    },
    "conversacional": {
        "display_name": "Conversacional",
        "description": "Natural, cercano, seguimiento útil; tono dominicano profesional.",
        "tone": "conversacional",
        "verbosity": "media",
        "analysis_depth": "standard",
        "max_insights": 5,
        "tables_enabled": True,
        "parameters_visible": True,
        "suggestions_enabled": True,
        "clarification_style": "pregunta abierta con opciones",
        "disclaimer_mode": "minimal",
        "max_response_length": 1400,
        "length": "medio",
        "depth": "moderado",
        "show_tables": True,
        "show_parameters": True,
        "show_suggestions": True,
        "disclaimers": "minimal",
        "proactive": True,
        "system_addon": (
            "TONO CONVERSACIONAL\n"
            "Español natural y cercano (dominicano profesional). "
            "Ofrece seguimiento útil sin insistir.\n"
            "Las políticas de seguridad y dominio estricto permanecen activas."
        ),
    },
    "analitico": {
        "display_name": "Analítico",
        "description": "Métricas, tablas, parámetros, interpretación y limitaciones.",
        "tone": "analitico",
        "verbosity": "alta",
        "analysis_depth": "detailed",
        "max_insights": 8,
        "tables_enabled": True,
        "parameters_visible": True,
        "suggestions_enabled": True,
        "clarification_style": "slots faltantes con ejemplos",
        "disclaimer_mode": "footer",
        "max_response_length": 2200,
        "length": "largo",
        "depth": "detallado",
        "show_tables": True,
        "show_parameters": True,
        "show_suggestions": True,
        "disclaimers": "footer",
        "proactive": True,
        "system_addon": (
            "TONO ANALÍTICO\n"
            "Incluye métricas, parámetros visibles, tablas cuando aplique, "
            "interpretación y limitaciones.\n"
            "Las políticas de seguridad y dominio estricto permanecen activas."
        ),
    },
    "ejecutivo": {
        "display_name": "Ejecutivo",
        "description": "Resumen, KPIs, hallazgos, riesgos y puntos clave.",
        "tone": "ejecutivo",
        "verbosity": "media",
        "analysis_depth": "standard",
        "max_insights": 4,
        "tables_enabled": True,
        "parameters_visible": False,
        "suggestions_enabled": False,
        "clarification_style": "pregunta directa con dos opciones",
        "disclaimer_mode": "footer",
        "max_response_length": 1000,
        "length": "medio",
        "depth": "moderado",
        "show_tables": True,
        "show_parameters": False,
        "show_suggestions": False,
        "disclaimers": "footer",
        "proactive": False,
        "system_addon": (
            "TONO EJECUTIVO\n"
            "Resumen primero, luego KPIs/hallazgos/riesgos en bullets.\n"
            "Las políticas de seguridad y dominio estricto permanecen activas."
        ),
    },
    "profundo": {
        "display_name": "Profundo",
        "description": "Multi-tool, multilotería, antes/después, intervalos, cobertura, insights.",
        "tone": "profundo",
        "verbosity": "muy_alta",
        "analysis_depth": "deep",
        "max_insights": 12,
        "tables_enabled": True,
        "parameters_visible": True,
        "suggestions_enabled": True,
        "clarification_style": "menú de opciones de análisis",
        "disclaimer_mode": "footer",
        "max_response_length": 3500,
        "length": "muy_largo",
        "depth": "profundo",
        "show_tables": True,
        "show_parameters": True,
        "show_suggestions": True,
        "disclaimers": "footer",
        "proactive": True,
        "system_addon": (
            "TONO PROFUNDO\n"
            "Análisis multi-tool y multilotería con cobertura e insights.\n"
            "Las políticas de seguridad y dominio estricto permanecen activas."
        ),
    },
    "estricto": {
        "display_name": "Estricto",
        "description": "Dominio estricto, máxima seguridad, respuesta mínima sin expansión.",
        "tone": "estricto",
        "verbosity": "minima",
        "analysis_depth": "minimal",
        "max_insights": 3,
        "tables_enabled": True,
        "parameters_visible": True,
        "suggestions_enabled": False,
        "clarification_style": "solicitud explícita de parámetros faltantes",
        "disclaimer_mode": "footer",
        "max_response_length": 800,
        "length": "medio",
        "depth": "detallado",
        "show_tables": True,
        "show_parameters": True,
        "show_suggestions": False,
        "disclaimers": "footer",
        "proactive": False,
        "system_addon": (
            "TONO ESTRICTO\n"
            "Solo hechos solicitados; sin expansión no pedida; máxima seguridad.\n"
            "Las políticas de seguridad y dominio estricto permanecen activas."
        ),
    },
}


def list_tone_templates() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "display_name": tpl["display_name"],
            "description": tpl["description"],
            "tone": tpl["tone"],
            "verbosity": tpl["verbosity"],
            "analysis_depth": tpl["analysis_depth"],
            "max_insights": tpl["max_insights"],
            "tables_enabled": tpl["tables_enabled"],
            "parameters_visible": tpl["parameters_visible"],
            "suggestions_enabled": tpl["suggestions_enabled"],
            "clarification_style": tpl["clarification_style"],
            "disclaimer_mode": tpl["disclaimer_mode"],
            "max_response_length": tpl["max_response_length"],
        }
        for key, tpl in TONE_TEMPLATES.items()
    ]


def get_tone_template(key: str) -> dict[str, Any]:
    if key not in TONE_TEMPLATES:
        raise KeyError(f"Tone '{key}' not found. Available: {', '.join(TONE_TEMPLATES)}")
    return dict(TONE_TEMPLATES[key])


def apply_tone_to_prompt(base_prompt: str, tone_key: str) -> str:
    template = get_tone_template(tone_key)
    return f"{base_prompt}\n\n---\n{template['system_addon']}"


def sanitize_tone_overrides(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Strip any attempt to weaken critical safety via tone payload."""
    if not payload:
        return {}
    return {k: v for k, v in payload.items() if k not in CRITICAL_SAFETY_KEYS}


def resolve_tone_preference(
    *,
    tenant_tone: str | None,
    user_tone: str | None,
    allow_user_override: bool = True,
    fallback: str = "analitico",
) -> str:
    if allow_user_override and user_tone and user_tone in TONE_TEMPLATES:
        return user_tone
    if tenant_tone and tenant_tone in TONE_TEMPLATES:
        return tenant_tone
    return fallback if fallback in TONE_TEMPLATES else "analitico"
