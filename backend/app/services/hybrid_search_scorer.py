"""Hybrid search scoring — BM25-inspired + entity boost (Fase 4)."""

from __future__ import annotations

import math
import re
from typing import Iterable

from app.schemas.search import SearchResultItem
from app.services.entity_resolution_engine import ResolvedEntity, _normalize


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"\s+", _normalize(text)) if len(t) >= 2]


def bm25_score(query_tokens: list[str], doc_tokens: list[str], *, k1: float = 1.2, b: float = 0.75) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    avgdl = max(doc_len, 8)
    tf_map: dict[str, int] = {}
    for t in doc_tokens:
        tf_map[t] = tf_map.get(t, 0) + 1
    score = 0.0
    for qt in query_tokens:
        tf = tf_map.get(qt, 0)
        if tf == 0:
            continue
        idf = math.log(1 + 1.0 / (1 + tf))
        denom = tf + k1 * (1 - b + b * doc_len / avgdl)
        score += idf * (tf * (k1 + 1)) / denom
    return score


class HybridSearchScorer:
    """Prioridad: entidad exacta > alias > semántica > BM25 texto."""

    def score_item(
        self,
        item: SearchResultItem,
        query: str,
        *,
        entities: Iterable[ResolvedEntity] | None = None,
        expanded_terms: list[str] | None = None,
    ) -> float:
        text = " ".join(
            filter(None, [item.title, item.subtitle, item.description, str(item.metadata)])
        )
        doc_tokens = _tokenize(text)
        q_tokens = _tokenize(query)
        terms = expanded_terms or [query]
        all_q_tokens = list(dict.fromkeys(_tokenize(" ".join(terms))))

        bm25 = bm25_score(all_q_tokens, doc_tokens)
        text_score = item.score
        entity_boost = 0.0

        text_norm = _normalize(text)
        for ent in entities or []:
            for alias in [_normalize(ent.canonical_name), *ent.aliases]:
                if not alias:
                    continue
                if alias == _normalize(query):
                    entity_boost = max(entity_boost, 100.0)
                elif alias in text_norm or text_norm in alias:
                    mult = {"exact": 95.0, "alias": 88.0, "semantic": 75.0, "token": 60.0}.get(
                        ent.match_kind, 70.0
                    )
                    entity_boost = max(entity_boost, mult * ent.confidence)

        for qt in q_tokens:
            if qt in text_norm:
                text_score = max(text_score, 70.0)

        hybrid = entity_boost * 0.55 + max(bm25 * 12.0, text_score * 0.35) + bm25 * 8.0
        return round(min(hybrid, 100.0), 2)

    def rerank_items(
        self,
        items: list[SearchResultItem],
        query: str,
        *,
        entities: list[ResolvedEntity] | None = None,
        expanded_terms: list[str] | None = None,
    ) -> list[SearchResultItem]:
        scored = [
            item.model_copy(
                update={
                    "score": self.score_item(
                        item, query, entities=entities, expanded_terms=expanded_terms
                    ),
                    "metadata": {
                        **(item.metadata or {}),
                        "hybrid_ranked": True,
                    },
                }
            )
            for item in items
        ]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored
