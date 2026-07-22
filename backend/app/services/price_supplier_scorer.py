"""Scoring de proveedores 0–100 sobre ofertas indexadas."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.prices import PriceProductResponse


def _freshness_score(file_date: datetime | None) -> int:
    if not file_date:
        return 5
    now = datetime.now(timezone.utc)
    if file_date.tzinfo is None:
        file_date = file_date.replace(tzinfo=timezone.utc)
    days = (now - file_date).days
    if days <= 7:
        return 15
    if days <= 30:
        return 12
    if days <= 90:
        return 8
    return 4


def score_supplier_offer(
    product: PriceProductResponse,
    *,
    price_rank: int,
    total_offers: int,
    quantity_needed: int = 1,
) -> tuple[int, str, list[str]]:
    """Retorna (score 0-100, risk_level, reasons)."""
    reasons: list[str] = []
    score = 0

    if total_offers > 0 and price_rank == 0:
        score += 40
        reasons.append("Mejor precio entre proveedores indexados")
    elif total_offers > 0:
        pct = max(0, 40 - price_rank * 8)
        score += pct
        if pct >= 24:
            reasons.append("Precio competitivo")

    stock = product.stock or 0
    if stock >= quantity_needed:
        score += 30
        reasons.append(f"Stock suficiente ({stock} uds.)")
    elif stock > 0:
        score += 15
        reasons.append(f"Stock parcial ({stock}/{quantity_needed})")
    else:
        reasons.append("Sin stock confirmado en lista")

    score += _freshness_score(product.source_file_date)
    if product.source_file_date:
        reasons.append("Lista reciente" if _freshness_score(product.source_file_date) >= 12 else "Lista con antigüedad")

    if product.warranty:
        score += 10
        reasons.append(f"Garantía: {product.warranty[:40]}")
    elif product.is_cotizable:
        score += 5

    if (product.in_transit or 0) > 0:
        score += 5
        reasons.append("Unidades en tránsito")

    score = min(100, max(0, score))

    if score >= 75 and stock >= quantity_needed:
        risk = "bajo"
    elif score >= 50:
        risk = "medio"
    else:
        risk = "alto"

    return score, risk, reasons


def rank_offers_by_score(
    offers: list[tuple[PriceProductResponse, int, str, list[str], Decimal | None]],
) -> list[tuple[PriceProductResponse, int, str, list[str], Decimal | None]]:
    return sorted(offers, key=lambda x: (-x[1], x[4] or Decimal("999999")))
