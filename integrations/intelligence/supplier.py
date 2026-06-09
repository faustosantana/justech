"""Supplier Intelligence — esquema futuro (Fase 4+)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class SupplierQuote:
    """Cotización de proveedor para comparación de precios."""

    proveedor: str
    sku: str | None = None
    mpn: str | None = None
    marca: str | None = None
    descripcion: str = ""
    precio: Decimal = Decimal("0")
    disponibilidad: int | None = None
    moneda: str = "USD"
    fecha_actualizacion: datetime | None = None
    fuente: str = ""
    archivo_origen: str | None = None
    proveedor_origen: str | None = None
    enlace_producto: str | None = None
    condiciones_comerciales: dict = field(default_factory=dict)
