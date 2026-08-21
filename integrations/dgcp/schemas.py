from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class DGCPProcesoRecord(BaseModel):
    codigo_proceso: str
    codigo_unidad_compra: int | None = None
    unidad_compra: str
    modalidad: str | None = None
    tipo_excepcion: str | None = None
    titulo: str
    descripcion: str | None = None
    estado_proceso: str | None = None
    divisa: str = "DOP"
    monto_estimado: float | Decimal = 0
    fecha_publicacion: datetime | None = None
    fecha_enmienda: datetime | None = None
    fecha_fin_recepcion_ofertas: datetime | None = None
    fecha_apertura_ofertas: datetime | None = None
    fecha_estimada_adjudicacion: datetime | None = None
    fecha_suscripcion: datetime | None = None
    fecha_habilitacion_oferente: datetime | None = None
    dirigido_mipymes: str | None = None
    dirigido_mipymes_mujeres: str | None = None
    proceso_lotificado: str | None = None
    area_requiriente: str | None = None
    url: str | None = None
    objeto_proceso: str | None = None
    subobjeto_proceso: str | None = None
    compra_verde: str | None = None
    duracion_contrato: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "DGCPProcesoRecord":
        known = cls.model_fields.keys() - {"extra"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(**{k: v for k, v in data.items() if k in known}, extra=extra)


class DGCPContratoRecord(BaseModel):
    codigo_contrato: str
    codigo_proceso: str
    estado_contrato: str | None = None
    estado_adjudicacion: str | None = None
    fecha_adjudicacion: datetime | None = None
    divisa: str = "DOP"
    valor_contratado: float | Decimal = 0
    descripcion: str | None = None
    url_contrato: str | None = None
    unidad_compra: str
    codigo_unidad_compra: str | int | None = None
    rpe: str | None = None
    razon_social: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "DGCPContratoRecord":
        known = cls.model_fields.keys() - {"extra"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(**{k: v for k, v in data.items() if k in known}, extra=extra)


class DGCPContratoArticuloRecord(BaseModel):
    codigo_contrato: str
    codigo_proceso: str
    descripcion_articulo: str | None = None
    descripcion_usuario: str | None = None
    unidad_medida: str | None = None
    cantidad: float | Decimal = 0
    precio_unitario: float | Decimal = 0
    costo_total: float | Decimal = 0
    familia: str | None = None
    clase: str | None = None
    subclase: str | None = None
    fecha_creacion_contrato: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "DGCPContratoArticuloRecord":
        known = cls.model_fields.keys() - {"extra"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(**{k: v for k, v in data.items() if k in known}, extra=extra)


class DGCPProcesoArticuloRecord(BaseModel):
    codigo_proceso: str
    descripcion_articulo: str | None = None
    descripcion_usuario: str | None = None
    cantidad: float | Decimal = 0
    unidad_medida: str | None = None
    precio_unitario_estimado: float | Decimal = 0
    precio_total_estimado: float | Decimal = 0
    familia_unspsc: str | None = None
    clase_unspsc: str | None = None
    subclase_unspsc: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "DGCPProcesoArticuloRecord":
        known = cls.model_fields.keys() - {"extra"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(**{k: v for k, v in data.items() if k in known}, extra=extra)


class DGCPPaginatedResponse(BaseModel):
    content: list[
        DGCPProcesoRecord
        | DGCPContratoRecord
        | DGCPContratoArticuloRecord
        | DGCPProcesoArticuloRecord
    ]
    page: int
    limit: int
    total_results: int
    pages: int
