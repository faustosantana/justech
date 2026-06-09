from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dgcp_classifier_ai import classify_with_ai
from app.services.dgcp_classifier_rules import COMPANY_LABELS, apply_keyword_rules, build_classification_text
from app.services.dgcp_classifier_scoring import score_classification
from integrations.dgcp.schemas import DGCPProcesoRecord

RULE_CONFIDENCE_THRESHOLD = 65
SCORING_CONFIDENCE_THRESHOLD = 42
AI_TRIGGER_THRESHOLD = 50


@dataclass
class ClassificationResult:
    company: str
    confidence_score: int
    classification_reason: str
    method: str
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> int:
        return self.confidence_score


def classify_proceso(record: DGCPProcesoRecord) -> ClassificationResult:
    """Clasificación síncrona (reglas + scoring). Usada cuando no hay sesión DB."""
    return _classify_layers(record)


async def classify_proceso_async(
    record: DGCPProcesoRecord,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    use_ai: bool = True,
) -> ClassificationResult:
    base = _classify_layers(record)
    if not use_ai:
        return base
    if base.company != "unclassified" and base.confidence_score >= AI_TRIGGER_THRESHOLD:
        return base

    ai_result = await classify_with_ai(record, db, tenant_id)
    if not ai_result:
        if base.company != "unclassified":
            return base
        return ClassificationResult(
            company="unclassified",
            confidence_score=base.confidence_score,
            classification_reason=f"{base.classification_reason}; IA no disponible",
            method=base.method,
            matched_keywords=base.matched_keywords,
        )

    if ai_result.company != "unclassified":
        merged_confidence = max(ai_result.confidence_score, base.confidence_score)
        if base.company == ai_result.company:
            merged_confidence = min(100, merged_confidence + 8)
            reason = f"{base.classification_reason} + {ai_result.classification_reason}"
            method = "hybrid"
        else:
            reason = ai_result.classification_reason
            method = "ai"
        return ClassificationResult(
            company=ai_result.company,
            confidence_score=merged_confidence,
            classification_reason=reason,
            method=method,
            matched_keywords=base.matched_keywords,
        )

    if base.company != "unclassified":
        return ClassificationResult(
            company=base.company,
            confidence_score=max(base.confidence_score, ai_result.confidence_score // 2),
            classification_reason=f"{base.classification_reason}; IA sin convicción",
            method="scoring",
            matched_keywords=base.matched_keywords,
        )

    return ClassificationResult(
        company="unclassified",
        confidence_score=ai_result.confidence_score,
        classification_reason=ai_result.classification_reason,
        method="ai",
        matched_keywords=base.matched_keywords,
    )


def _classify_layers(record: DGCPProcesoRecord) -> ClassificationResult:
    text = build_classification_text(record)
    rule_result = apply_keyword_rules(text, record.unidad_compra)

    if rule_result.company and rule_result.confidence_score >= RULE_CONFIDENCE_THRESHOLD:
        return ClassificationResult(
            company=rule_result.company,
            confidence_score=rule_result.confidence_score,
            classification_reason=rule_result.classification_reason,
            method="rules",
            matched_keywords=rule_result.matched_keywords,
        )

    scoring = score_classification(record, rule_result)

    if rule_result.company and scoring.company == rule_result.company:
        combined_confidence = min(
            98,
            max(rule_result.confidence_score, scoring.confidence_score) + 10,
        )
        return ClassificationResult(
            company=rule_result.company,
            confidence_score=combined_confidence,
            classification_reason=(
                f"Híbrido reglas+scoring: {COMPANY_LABELS[rule_result.company]} "
                f"({rule_result.classification_reason}; {scoring.classification_reason})"
            ),
            method="hybrid",
            matched_keywords=rule_result.matched_keywords + scoring.matched_keywords,
        )

    if scoring.company != "unclassified" and scoring.confidence_score >= SCORING_CONFIDENCE_THRESHOLD:
        return ClassificationResult(
            company=scoring.company,
            confidence_score=scoring.confidence_score,
            classification_reason=scoring.classification_reason,
            method="scoring",
            matched_keywords=scoring.matched_keywords,
        )

    if rule_result.company:
        return ClassificationResult(
            company=rule_result.company,
            confidence_score=max(rule_result.confidence_score, scoring.confidence_score),
            classification_reason=rule_result.classification_reason,
            method="rules",
            matched_keywords=rule_result.matched_keywords,
        )

    return ClassificationResult(
        company="unclassified",
        confidence_score=scoring.confidence_score,
        classification_reason=scoring.classification_reason or "Sin señales de clasificación",
        method="scoring",
        matched_keywords=scoring.matched_keywords,
    )
