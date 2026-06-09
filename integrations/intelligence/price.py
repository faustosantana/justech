"""Price Intelligence Center — interfaces futuras (Fase 4+)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from integrations.intelligence.supplier import SupplierQuote


class PriceSource(ABC):
    """Fuente de precios externa (Ingram, Omega Tech, Excel, PDF, etc.)."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @abstractmethod
    async def search(self, query: str, *, limit: int = 20) -> list[SupplierQuote]:
        pass


class PriceRecommendation:
    """Recomendación de compra/venta (sin escritura en Odoo)."""

    def __init__(
        self,
        *,
        best_supplier: str | None,
        best_price: Decimal | None,
        last_cost: Decimal | None,
        recommended_margin_pct: float | None,
        equivalent_products: list[str] | None = None,
    ):
        self.best_supplier = best_supplier
        self.best_price = best_price
        self.last_cost = last_cost
        self.recommended_margin_pct = recommended_margin_pct
        self.equivalent_products = equivalent_products or []
