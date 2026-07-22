"""Tests — Entity Resolution Engine (Fase 4)."""

from __future__ import annotations

import pytest

from app.services.entity_resolution_engine import EntityResolutionEngine
from app.services.hybrid_search_scorer import HybridSearchScorer, bm25_score
from app.services.knowledge_engine_service import KnowledgeEngineService
from app.schemas.search import SearchResultItem


@pytest.fixture
def resolver():
    return EntityResolutionEngine()


@pytest.mark.parametrize(
    "query,expected_canonical",
    [
        ("ADEMI", "Banco Múltiple Ademi"),
        ("banco multiple ademi", "Banco Múltiple Ademi"),
        ("Capital", "Capital DBG"),
        ("Capital DBG", "Capital DBG"),
        ("Farmatrix", "Farma Trix"),
        ("Farma Trix", "Farma Trix"),
        ("papel 350", "Papel térmico 350"),
        ("rollo térmico 350", "Papel térmico 350"),
        ("RPE", "Registro de Proveedores del Estado (RPE)"),
        ("Registro Proveedor Estado", "Registro de Proveedores del Estado (RPE)"),
        ("DGII", "Certificación DGII"),
        ("Impuestos Internos", "Certificación DGII"),
        ("laptop dell", "Dell Latitude"),
        ("Latitude 5450", "Dell Latitude"),
    ],
)
def test_entity_resolution_aliases(resolver, query, expected_canonical):
    hits = resolver.resolve(query)
    assert hits, f"Sin resolución para {query}"
    assert hits[0].canonical_name == expected_canonical


def test_expand_search_terms_includes_aliases(resolver):
    entities = resolver.resolve("ADEMI")
    terms = resolver.expand_search_terms("ADEMI", entities)
    assert "ademi" in terms
    assert any("ademi" in t for t in terms)


def test_pick_orchestrator_query_uses_best_alias_for_short_query(resolver):
    entities = resolver.resolve("ADEMI")
    q = KnowledgeEngineService.pick_orchestrator_query("ADEMI", entities)
    assert "ademi" in q.lower()
    assert len(q.split()) >= 2


def test_pick_orchestrator_query_keeps_specific_user_query(resolver):
    entities = resolver.resolve("ADEMI")
    q = KnowledgeEngineService.pick_orchestrator_query(
        "cotización impresoras banco ademi sucursal norte",
        entities,
    )
    assert q == "cotización impresoras banco ademi sucursal norte"


def test_bm25_scores_matching_tokens():
    score = bm25_score(["papel", "350"], ["papel", "termico", "350", "rollo"])
    assert score > 0


def test_hybrid_scorer_entity_boost():
    scorer = HybridSearchScorer()
    entities = EntityResolutionEngine().resolve("ADEMI")
    item = SearchResultItem(
        id="1",
        type="cliente",
        title="Banco Múltiple Ademi S.A.",
        subtitle="Cliente activo",
        source="odoo",
        url="/odoo",
        score=40,
    )
    boosted = scorer.score_item(item, "ADEMI", entities=entities)
    assert boosted > 50
