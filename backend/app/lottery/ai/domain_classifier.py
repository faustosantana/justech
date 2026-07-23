"""Lottery IA 4.2 — domain / security classifier (runs before planner)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel


DomainClass = Literal[
    "lottery_domain",
    "lottery_operational",
    "restricted_technical",
    "out_of_domain",
    "prediction_request",
    "harmful_or_illegal",
    "ambiguous",
]


class DomainDecision(BaseModel):
    classification: DomainClass
    confidence: float = 0.9
    refuse_message: str | None = None


_OUT_OF_DOMAIN = re.compile(
    r"\b("
    r"capital\s+de|presidente|temperatura|clima|correo\s+electr[oó]nico|"
    r"escr[ií]beme\s+un\s+correo|f[uú]tbol|b[eé]isbol|pol[ií]tica|"
    r"medicina|diagn[oó]stico|criptomoneda|bitcoin|programaci[oó]n|"
    r"python\s+code|javascript|odoo\b|licitaci[oó]n|dgcp|sharepoint|"
    r"qui[eé]n\s+es|historia\s+de|franc[eé]s|par[ií]s"
    r")\b",
    re.I,
)

_RESTRICTED = re.compile(
    r"\b("
    r"base\s+de\s+datos|postgres|postgresql|mysql|mongodb|sql\b|"
    r"consulta\s+sql|query\s+sql|connection\s*string|credencial|"
    r"contrase[nñ]a|password|token\b|api\s*key|variable\s+de\s+entorno|"
    r"\.env\b|docker|contenedor|kubernetes|servidor|ip\s+del|"
    r"puerto\b|dump\b|checksum|system\s*prompt|prompt\s+interno|"
    r"esquema\s+de\s+tablas|nombre\s+de\s+tabla|host\s+de\s+bd|"
    r"secret[_-]?key|jwt_secret|ssh\b|root@|infraestructura"
    r")\b",
    re.I,
)

_PREDICTION = re.compile(
    r"\b("
    r"va\s+a\s+salir|saldr[aá]|predic|apostar|qu[eé]\s+juego|"
    r"n[uú]mero\s+ganador\s+de\s+ma[nñ]ana|seguro\s+que\s+sale|"
    r"recomendaci[oó]n\s+de\s+apuesta|qu[eé]\s+n[uú]mero\s+jugo"
    r")\b",
    re.I,
)

_OPERATIONAL = re.compile(
    r"\b("
    r"sincroniz|actualizad|faltan\s+hoy|pr[oó]xima\s+sync|"
    r"cobertura|calidad\s+de\s+(los\s+)?datos|fuente\s+degrad|"
    r"hasta\s+qu[eé]\s+fecha|cu[aá]ntos\s+sorteos|expected|recibidos"
    r")\b",
    re.I,
)

_LOTTERY_HINT = re.compile(
    r"\b("
    r"loter|quiniela|leidsa|loteka|nacional|gana\s+m[aá]s|lotedom|"
    r"sorteo|n[uú]mero\s+\d{1,2}|\b\d{1,2}\b|frecuencia|caliente|fr[ií]o|"
    r"atrasad|coinciden|aparici[oó]n|historial|intervalo|posici[oó]n|"
    r"compar|resultados?"
    r")\b",
    re.I,
)

OUT_OF_DOMAIN_MSG = (
    "Lottery IA está especializada exclusivamente en resultados y análisis de loterías. "
    "Esa consulta está fuera de su alcance. Puedo ayudarte con resultados, históricos, "
    "frecuencias, comparaciones, coincidencias o sincronización de loterías."
)

RESTRICTED_MSG = (
    "No puedo proporcionar detalles internos de infraestructura o configuración. "
    "Sí puedo indicarte la cobertura, actualización y calidad de los datos de lotería disponibles."
)

PREDICTION_MSG = (
    "No puedo predecir resultados futuros ni recomendar apuestas. "
    "Solo consulto el histórico verificado. Los resultados pasados no garantizan resultados futuros."
)

PROMPT_LEAK_MSG = (
    "No puedo revelar instrucciones internas. "
    "Puedo explicarte el alcance y las reglas generales de Lottery IA."
)


def classify_domain(text: str) -> DomainDecision:
    raw = (text or "").strip()
    if not raw:
        return DomainDecision(classification="ambiguous", confidence=0.5)

    if re.search(r"system\s*prompt|prompt\s+del\s+sistema|instrucciones\s+internas", raw, re.I):
        return DomainDecision(
            classification="restricted_technical",
            confidence=0.98,
            refuse_message=PROMPT_LEAK_MSG,
        )

    if _RESTRICTED.search(raw) and not _LOTTERY_HINT.search(raw):
        return DomainDecision(
            classification="restricted_technical",
            confidence=0.95,
            refuse_message=RESTRICTED_MSG,
        )
    # Technical ask mixed with lottery → still refuse technical specifics
    if _RESTRICTED.search(raw) and re.search(
        r"\b(sql|tabla|postgres|password|credencial|docker|ip\b|servidor)\b", raw, re.I
    ):
        return DomainDecision(
            classification="restricted_technical",
            confidence=0.96,
            refuse_message=RESTRICTED_MSG,
        )

    if _PREDICTION.search(raw):
        return DomainDecision(
            classification="prediction_request",
            confidence=0.92,
            refuse_message=PREDICTION_MSG,
        )

    if _OUT_OF_DOMAIN.search(raw) and not _LOTTERY_HINT.search(raw):
        return DomainDecision(
            classification="out_of_domain",
            confidence=0.93,
            refuse_message=OUT_OF_DOMAIN_MSG,
        )

    if _OPERATIONAL.search(raw):
        return DomainDecision(classification="lottery_operational", confidence=0.85)

    if _LOTTERY_HINT.search(raw):
        return DomainDecision(classification="lottery_domain", confidence=0.8)

    # Short replies that look like slot fills stay in domain
    if len(raw.split()) <= 6 and re.search(
        r"^(en\s+)?(la\s+|el\s+)?(real|leidsa|loteka|nacional|todas|s[ií]|no)\b",
        raw,
        re.I,
    ):
        return DomainDecision(classification="lottery_domain", confidence=0.75)

    if _OUT_OF_DOMAIN.search(raw):
        return DomainDecision(
            classification="out_of_domain",
            confidence=0.85,
            refuse_message=OUT_OF_DOMAIN_MSG,
        )

    return DomainDecision(classification="ambiguous", confidence=0.4)
