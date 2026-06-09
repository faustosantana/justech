"""Interface para conectores de proveedores externos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class SupplierProduct:
    sku: str
    name: str
    price: Decimal | None
    currency: str
    stock: int | None
    source: str
    updated_at: datetime | None = None
    raw: dict | None = None


class SupplierConnector(ABC):
    """Contrato para Ingram, Omega y otros mayoristas."""

    provider_id: str
    integration_type: str  # api | excel | scraper

    @abstractmethod
    async def search_products(self, query: str, *, limit: int = 20) -> list[SupplierProduct]:
        ...

    @abstractmethod
    async def get_price(self, sku: str) -> SupplierProduct | None:
        ...

    @abstractmethod
    async def get_stock(self, sku: str) -> int | None:
        ...

    @abstractmethod
    async def sync_catalog(self) -> dict:
        ...
