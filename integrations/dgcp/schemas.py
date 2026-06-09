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


class DGCPPaginatedResponse(BaseModel):
    content: list[DGCPProcesoRecord]
    page: int
    limit: int
    total_results: int
    pages: int
