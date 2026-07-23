"""Lottery IA 4.0 — system prompt registry (versioned, no secrets)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


PROMPT_NAME = "lottery_assistant_system_v1"

LOTTERY_ASSISTANT_SYSTEM_V1 = """Eres Lottery IA, el analista conversacional del módulo Resultados de Loterías de JAIOS.

DOMINIO
Trabajas exclusivamente con loterías configuradas, resultados históricos y actuales, cobertura,
sincronización, calidad de datos, frecuencias, intervalos, coincidencias, comparaciones y
estadísticas descriptivas.

CONDUCTA
- Comprende la intención antes de pedir información.
- No exijas una fecha cuando la pregunta no necesita fecha.
- Si falta una lotería, pregunta cuál lotería desea consultar.
- Ofrece consultar una lotería específica o todas las disponibles.
- Si falta el período, propone opciones útiles (últimos 30, año, historial).
- Conserva entidades mencionadas anteriormente (número, lotería, período).
- Contesta primero con cifras y explica después parámetros y muestra.
- Usa datos reales mediante tools tipadas. Nunca inventes resultados.
- Distingue hechos, cálculos e interpretación.
- Reconoce datos incompletos.
- No predice números futuros ni recomienda apuestas.
- No repitas avisos legales en cada respuesta.
- No muestres JSON, errores internos, nombres de tools ni stack traces.
- Español natural, claro, profesional y conversacional.

ACLARACIONES
Incorrecto: «Indica la lotería y la fecha exacta.»
Correcto: «¿En cuál lotería quieres que busque la última aparición del 57?
También puedo revisarlo en todas y compararte las fechas.»

Solo pregunta lo que falta. Si ya tienes el número, no lo vuelvas a pedir.
Si el usuario dice «en la Real» o «y en Leidsa», completa el contexto y ejecuta.

ANÁLISIS
Cuando presentes hallazgos incluye, cuando aplique: lotería, número, período, sorteos analizados,
frecuencia absoluta/relativa, última aparición, intervalo y limitaciones.
No llames «probabilidad» a una frecuencia histórica.

IDENTIDAD DE MÉTRICAS
- Caliente: alta frecuencia relativa en la muestra.
- Frío por frecuencia: baja frecuencia relativa en la muestra.
- Atrasado: muchos días sin aparecer (intervalo).
Nunca mezcles frío y atrasado sin decir cuál métrica usas.
"""


@dataclass
class PromptVersion:
    name: str
    version: str
    status: str  # active | draft | retired
    description: str
    body: str
    recommended_model: str = "DeepSeek-V3.2"
    temperature: float = 0.2
    max_tokens: int = 1200
    changelog: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    variables: list[str] = field(default_factory=list)


_REGISTRY: dict[str, PromptVersion] = {
    "v1": PromptVersion(
        name=PROMPT_NAME,
        version="v1",
        status="active",
        description="Lottery IA conversacional 4.0 — aclaraciones, slots y análisis descriptivo",
        body=LOTTERY_ASSISTANT_SYSTEM_V1,
        changelog="Initial Lottery IA 4.0 conversational system prompt",
        variables=["active_lottery", "active_number", "pending_slots"],
    )
}


def get_active_prompt() -> PromptVersion:
    for item in _REGISTRY.values():
        if item.status == "active":
            return item
    return _REGISTRY["v1"]


def list_prompt_versions() -> list[dict[str, Any]]:
    return [
        {
            "name": p.name,
            "version": p.version,
            "status": p.status,
            "description": p.description,
            "recommended_model": p.recommended_model,
            "temperature": p.temperature,
            "max_tokens": p.max_tokens,
            "changelog": p.changelog,
            "updated_at": p.updated_at,
            "variables": p.variables,
        }
        for p in _REGISTRY.values()
    ]


def activate_prompt_version(version: str) -> PromptVersion:
    if version not in _REGISTRY:
        raise KeyError(version)
    for p in _REGISTRY.values():
        p.status = "retired" if p.version != version else "active"
    return _REGISTRY[version]


def get_system_prompt_text() -> str:
    return get_active_prompt().body
