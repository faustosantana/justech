from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LLMProviderError
from app.llm.router import LLMRouter
from app.schemas.llm import LLMCompletionRequest, LLMMessage
from app.services.dgcp_classifier_rules import COMPANY_LABELS, build_classification_text, extract_article_tokens
from integrations.dgcp.schemas import DGCPProcesoRecord

VALID_COMPANIES = set(COMPANY_LABELS.keys())

CLASSIFIER_PROMPT = """Eres el clasificador de oportunidades DGCP para el grupo empresarial dominicano JAIOS.

Clasifica el proceso de compra pública en EXACTAMENTE una de estas empresas:
- justech → Justech SRL (TI, software, hardware, redes, telecomunicaciones, ciberseguridad, equipos de cómputo)
- just_office → Just Office SRL (suministros de oficina, mobiliario, papelería, limpieza, alimentos institucionales, útiles)
- mf_plug_safe → MF Plug & Safe Services SRL (electricidad, plantas eléctricas, UPS, CCTV, alarmas, seguridad física, instalaciones)
- omni_solutions → Omni Solutions SRL (consultoría, integración de sistemas, ERP, CRM, gestión documental, transformación digital)

Responde SOLO con JSON válido:
{"company":"justech|just_office|mf_plug_safe|omni_solutions|unclassified","confidence_score":0-100,"reason":"explicación breve en español"}
"""


@dataclass
class AIClassificationResult:
    company: str
    confidence_score: int
    classification_reason: str


def _build_user_prompt(record: DGCPProcesoRecord) -> str:
    text = build_classification_text(record)
    articles = extract_article_tokens(text)
    return (
        f"Código: {record.codigo_proceso}\n"
        f"Institución: {record.unidad_compra}\n"
        f"Título: {record.titulo}\n"
        f"Descripción: {record.descripcion or 'N/A'}\n"
        f"Objeto: {record.objeto_proceso or 'N/A'}\n"
        f"Subobjeto: {record.subobjeto_proceso or 'N/A'}\n"
        f"Modalidad: {record.modalidad or 'N/A'}\n"
        f"Artículos detectados: {', '.join(articles) if articles else 'N/A'}\n"
        f"Monto estimado: {record.monto_estimado} {record.divisa}"
    )


def _parse_ai_response(content: str) -> AIClassificationResult | None:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]+\}", content, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return None

    company = str(data.get("company", "unclassified")).strip().lower()
    if company not in VALID_COMPANIES and company != "unclassified":
        return None

    confidence = int(data.get("confidence_score", 0))
    confidence = max(0, min(100, confidence))
    reason = str(data.get("reason", "Clasificación IA")).strip()
    label = COMPANY_LABELS.get(company, "Sin clasificar")
    return AIClassificationResult(
        company=company,
        confidence_score=confidence,
        classification_reason=f"IA: {label} — {reason}",
    )


async def classify_with_ai(
    record: DGCPProcesoRecord,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> AIClassificationResult | None:
    router = LLMRouter(db)
    request = LLMCompletionRequest(
        messages=[
            LLMMessage(role="system", content=CLASSIFIER_PROMPT),
            LLMMessage(role="user", content=_build_user_prompt(record)),
        ],
        temperature=0.1,
        max_tokens=256,
    )
    try:
        response = await router.complete(request, tenant_id=tenant_id)
    except LLMProviderError:
        return None

    return _parse_ai_response(response.content)
