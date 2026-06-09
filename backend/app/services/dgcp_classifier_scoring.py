from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.dgcp_classifier_rules import (
    COMPANY_LABELS,
    INSTITUTION_RULES,
    KEYWORD_RULES,
    OBJETO_BIAS,
    RuleMatchResult,
    build_classification_text,
    extract_article_tokens,
)
from integrations.dgcp.schemas import DGCPProcesoRecord


@dataclass
class ScoringMatchResult:
    company: str
    confidence_score: int
    classification_reason: str
    matched_keywords: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)


def _score_patterns(text: str, patterns: list[tuple[str, int]]) -> tuple[float, list[str]]:
    total = 0.0
    matched: list[str] = []
    for pattern, weight in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            total += weight
            matched.append(pattern)
    return total, matched


def score_classification(record: DGCPProcesoRecord, rule_result: RuleMatchResult) -> ScoringMatchResult:
    text = build_classification_text(record)
    institution = _normalize_institution(record.unidad_compra)
    articles = rule_result.article_tokens or extract_article_tokens(text)
    article_text = " ".join(articles)
    combined = f"{text} {article_text}"

    scores: dict[str, float] = {c: 0.0 for c in COMPANY_LABELS}
    hits: dict[str, list[str]] = {c: [] for c in COMPANY_LABELS}

    for company, patterns in KEYWORD_RULES.items():
        pts, matched = _score_patterns(combined, patterns)
        scores[company] += pts * 3.5
        hits[company].extend(matched[:6])

    for company, patterns in INSTITUTION_RULES.items():
        pts, matched = _score_patterns(institution, patterns)
        scores[company] += pts * 4.0
        hits[company].extend([f"inst:{m}" for m in matched[:3]])

    objeto = (record.objeto_proceso or "").strip()
    if objeto in OBJETO_BIAS:
        for company, bias in OBJETO_BIAS[objeto].items():
            scores[company] += bias

    subobjeto = (record.subobjeto_proceso or "").lower()
    if subobjeto:
        for company, patterns in KEYWORD_RULES.items():
            pts, _ = _score_patterns(subobjeto, patterns)
            scores[company] += pts * 2.0

    for token in articles:
        for company, patterns in KEYWORD_RULES.items():
            pts, matched = _score_patterns(token, patterns)
            if pts:
                scores[company] += pts * 2.5
                hits[company].extend(matched[:2])

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_company, best_raw = ranked[0]
    second_raw = ranked[1][1] if len(ranked) > 1 else 0.0

    if best_raw < 6:
        return ScoringMatchResult(
            company="unclassified",
            confidence_score=0,
            classification_reason="Scoring: señales insuficientes en título, descripción, institución y artículos",
            scores=scores,
        )

    margin = best_raw - second_raw
    confidence = int(min(88, 28 + best_raw * 1.8 + margin * 2.5))
    top_hits = hits[best_company][:4]
    reason = (
        f"Scoring: {COMPANY_LABELS[best_company]} "
        f"(puntuación {best_raw:.1f}, margen {margin:.1f}"
        f"{'; ' + ', '.join(top_hits[:3]) if top_hits else ''})"
    )

    return ScoringMatchResult(
        company=best_company,
        confidence_score=confidence,
        classification_reason=reason,
        matched_keywords=top_hits,
        scores=scores,
    )


def _normalize_institution(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().strip())
