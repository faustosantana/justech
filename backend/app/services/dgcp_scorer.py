from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.services.dgcp_classifier import ClassificationResult
from integrations.dgcp.schemas import DGCPProcesoRecord


@dataclass
class ScoringResult:
    score: int
    probability: int
    priority: str
    potential_amount: Decimal
    risks: list[dict[str, str]]
    recommendations: list[str]
    suggested_action: str


def _days_until_deadline(record: DGCPProcesoRecord) -> int:
    deadline = record.fecha_fin_recepcion_ofertas or record.fecha_apertura_ofertas
    if not deadline:
        return 30
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    delta = deadline - datetime.now(UTC)
    return max(0, delta.days)


def score_proceso(record: DGCPProcesoRecord, classification: ClassificationResult) -> ScoringResult:
    amount = Decimal(str(record.monto_estimado or 0))
    days_left = _days_until_deadline(record)
    risks: list[dict[str, str]] = []
    recommendations: list[str] = []
    score = 0

    if classification.company != "unclassified":
        score += min(40, classification.confidence_score)
    else:
        risks.append({"nivel": "medio", "descripcion": "Sin clasificación empresarial clara"})

    if amount >= Decimal("50000000"):
        score += 25
        recommendations.append("Oportunidad de alto valor — priorizar análisis de requisitos")
    elif amount >= Decimal("5000000"):
        score += 18
    elif amount >= Decimal("500000"):
        score += 12
    else:
        score += 5

    if days_left <= 3:
        score += 5
        risks.append({"nivel": "alto", "descripcion": f"Plazo crítico: {days_left} días restantes"})
        recommendations.append("Evaluar capacidad de respuesta inmediata")
    elif days_left <= 10:
        score += 12
    elif days_left <= 30:
        score += 18
    else:
        score += 10

    modalidad = (record.modalidad or "").lower()
    if "menor" in modalidad or "debajo del umbral" in modalidad:
        score += 15
        recommendations.append("Modalidad accesible — evaluar participación directa")
    elif "excepción" in modalidad or "emergencia" in modalidad:
        score -= 10
        risks.append({"nivel": "alto", "descripcion": "Proceso de excepción o emergencia"})

    objeto = (record.objeto_proceso or "").lower()
    if objeto == "servicios" and classification.company in ("justech", "omni_solutions"):
        score += 10
    if objeto == "obras":
        score -= 8
        risks.append({"nivel": "medio", "descripcion": "Proceso de obras — mayor complejidad operativa"})

    if record.dirigido_mipymes == "Si":
        score += 5
        recommendations.append("Proceso dirigido a MIPYMES — ventaja competitiva potencial")

    score = max(0, min(100, score))
    probability = max(0, min(100, score - 5 + (classification.confidence_score // 5)))

    if score >= 75:
        priority = "critical"
    elif score >= 55:
        priority = "high"
    elif score >= 35:
        priority = "medium"
    else:
        priority = "low"

    share = {"justech": 0.35, "just_office": 0.25, "mf_plug_safe": 0.30, "omni_solutions": 0.40}
    pct = share.get(classification.company, 0.15)
    potential = (amount * Decimal(str(pct))).quantize(Decimal("0.01"))

    if score >= 70 and days_left <= 15:
        action = "licitar"
    elif score >= 50:
        action = "revisar"
    elif score < 30:
        action = "descartar"
    else:
        action = "analizar"

    if not recommendations:
        recommendations.append(f"Clasificado para {classification.company} — revisar pliego en DGCP")

    return ScoringResult(
        score=score,
        probability=probability,
        priority=priority,
        potential_amount=potential,
        risks=risks,
        recommendations=recommendations,
        suggested_action=action,
    )
