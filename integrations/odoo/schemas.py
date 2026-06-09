from typing import Any

from pydantic import BaseModel, Field


class OdooRecord(BaseModel):
    model: str
    record_id: int | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class OdooConnectionStatus(BaseModel):
    connected: bool
    version: str | None = None
    database: str | None = None
    uid: int | None = None
    error: str | None = None
    read_only: bool = True
